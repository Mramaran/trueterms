"""
xbrl_parser.py — TrueTerms XBRL Parser
==========================================
Supports: IFRS, US-GAAP, Inline XBRL (iXBRL) from any bank.
Fast for any file size — processes tag-by-tag, not on full content.
"""

import re
from datetime import datetime, timedelta
from typing import Optional
import xml.etree.ElementTree as ET


def _is_ixbrl(content: str) -> bool:
    cl = content.lower()
    return (
        ('ix:nonfraction' in cl or 'ix:nonnumeric' in cl or
         'ix:header' in cl or 'xmlns:ix' in cl) and
        ('<html' in cl or '<!doctype' in cl)
    )


# Fast compiled patterns — attribute order independent (name/contextRef can appear in any order)
_ATTR_NAME    = re.compile(r'name=["\']([^"\']+)["\']', re.IGNORECASE)
_ATTR_CTX     = re.compile(r'contextref=["\']([^"\']*)["\']', re.IGNORECASE)
_ATTR_UNIT    = re.compile(r'unitref=["\']([^"\']*)["\']', re.IGNORECASE)
_ATTR_DEC     = re.compile(r'decimals=["\']([^"\']*)["\']', re.IGNORECASE)
_TAG_VALUE    = re.compile(r'>([^<]*)</', re.IGNORECASE)
_IS_NONFRAC   = re.compile(r'^<ix:nonfraction\b', re.IGNORECASE)
_IS_NONNUMERIC= re.compile(r'^<ix:nonnumeric\b', re.IGNORECASE)
_CTX = re.compile(
    r'<xbrli:context\s[^>]*id=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</xbrli:context>',
    re.IGNORECASE
)
_SPLIT = re.compile(r'(?=<ix:non)', re.IGNORECASE)


def _ixbrl_to_xbrl_xml(html: str) -> str:
    import time
    t = time.time()
    facts = []
    contexts = {}

    # Split entire file into small per-tag chunks — works on minified 1-line files
    # Each chunk is tiny (~200 chars), so regex is instant per chunk
    chunks = _SPLIT.split(html)
    tag_chunks = [c for c in chunks if c.lower().startswith('<ix:non')]
    print(f'[IXBRL] Split {len(html)//1024}KB into {len(tag_chunks)} tag chunks in {time.time()-t:.2f}s')

    for chunk in tag_chunks:
        # Extract attributes regardless of order
        mn = _ATTR_NAME.search(chunk)
        mc = _ATTR_CTX.search(chunk)
        mv = _TAG_VALUE.search(chunk)
        if not mn or not mc or not mv:
            continue
        name  = mn.group(1)
        ctx   = mc.group(1)
        value = mv.group(1).strip()
        if _IS_NONFRAC.match(chunk):
            value = value.replace(',', '')
            if value and value not in ('', 'N/A'):
                mu = _ATTR_UNIT.search(chunk)
                md = _ATTR_DEC.search(chunk)
                facts.append((name, value, ctx,
                              mu.group(1) if mu else '',
                              md.group(1) if md else '0'))
        elif _IS_NONNUMERIC.match(chunk):
            if value and len(value) < 200:
                facts.append((name, value, ctx, '', ''))

    # Extract contexts from first 500KB only
    for m in _CTX.finditer(html[:500_000]):
        ctx_id, body = m.group(1), m.group(2)
        instant = re.search(r'<xbrli:instant>([^<]+)</xbrli:instant>', body, re.I)
        start   = re.search(r'<xbrli:startdate>([^<]+)</xbrli:startdate>', body, re.I)
        end     = re.search(r'<xbrli:enddate>([^<]+)</xbrli:enddate>', body, re.I)
        entity  = re.search(r'<xbrli:identifier[^>]*>([^<]+)</xbrli:identifier>', body, re.I)
        contexts[ctx_id] = {
            'instant': instant.group(1).strip() if instant else '',
            'start':   start.group(1).strip()   if start   else '',
            'end':     end.group(1).strip()     if end     else '',
            'entity':  entity.group(1).strip()  if entity  else 'UNKNOWN',
        }

    print(f'[IXBRL] {len(facts)} facts, {len(contexts)} contexts in {time.time()-t:.2f}s')

    if not facts:
        return '<?xml version="1.0" encoding="UTF-8"?><xbrl xmlns="http://www.xbrl.org/2003/instance"></xbrl>'

    # Dynamically extract all xmlns declarations from the source file
    # This handles ANY bank's custom namespaces (jpm:, bac:, wfc:, ecd:, srt:, etc.)
    ns_pattern = re.compile(r'xmlns:([a-zA-Z0-9_-]+)=["\']([^"\']+)["\']')
    dynamic_ns = {m.group(1): m.group(2) for m in ns_pattern.finditer(html[:5000])}

    # Base namespaces always needed
    base_ns = {
        'xbrli':    'http://www.xbrl.org/2003/instance',
        'us-gaap':  'http://fasb.org/us-gaap/2023-01-31',
        'ifrs-full':'https://xbrl.ifrs.org/taxonomy/2023-03-23/ifrs-full',
        'dei':      'http://xbrl.sec.gov/dei/2024',
        'iso4217':  'http://www.xbrl.org/2003/iso4217',
        'link':     'http://www.xbrl.org/2003/linkbase',
        'xlink':    'http://www.w3.org/1999/xlink',
    }
    all_ns = {**base_ns, **dynamic_ns}

    ns_lines = ['  xmlns="http://www.xbrl.org/2003/instance"']
    for prefix, uri in all_ns.items():
        ns_lines.append(f'  xmlns:{prefix}="{uri}"')

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<xbrl',
        *ns_lines,
        '>',
        '',
    ]

    for ctx_id, d in list(contexts.items())[:20]:
        lines += [
            f'  <xbrli:context id="{ctx_id}">',
            f'    <xbrli:entity>',
            f'      <xbrli:identifier scheme="http://www.sec.gov/CIK">{d["entity"]}</xbrli:identifier>',
            f'    </xbrli:entity>',
            f'    <xbrli:period>',
        ]
        if d['instant']:
            lines.append(f'      <xbrli:instant>{d["instant"]}</xbrli:instant>')
        elif d['start'] and d['end']:
            lines.append(f'      <xbrli:startDate>{d["start"]}</xbrli:startDate>')
            lines.append(f'      <xbrli:endDate>{d["end"]}</xbrli:endDate>')
        else:
            lines.append(f'      <xbrli:instant>2024-12-31</xbrli:instant>')
        lines += ['    </xbrli:period>', '  </xbrli:context>']

    lines += [
        '  <xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>',
        '  <xbrli:unit id="inr"><xbrli:measure>iso4217:INR</xbrli:measure></xbrli:unit>',
        '  <xbrli:unit id="pure"><xbrli:measure>xbrli:pure</xbrli:measure></xbrli:unit>',
        '',
    ]

    seen = set()
    for name, value, ctx, unit, decimals in facts:
        key = f'{name}::{ctx}'
        if key in seen:
            continue
        seen.add(key)
        safe = value.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')
        attrs = f'contextRef="{ctx}"'
        if unit:   attrs += f' unitRef="{unit}"'
        if decimals: attrs += f' decimals="{decimals}"'
        lines.append(f'  <{name} {attrs}>{safe}</{name}>')

    lines.append('</xbrl>')
    return '\n'.join(lines)


KNOWN_NS = {
    'ifrs-full': 'https://xbrl.ifrs.org/taxonomy/2023-03-23/ifrs-full',
    'us-gaap':   'http://fasb.org/us-gaap/2023',
    'dei':       'http://xbrl.sec.gov/dei/2023',
    'iso4217':   'http://www.xbrl.org/2003/iso4217',
}

TAG_MAP = [
    # Principal / Notional — us-gaap + IFRS + JPMorgan + BofA + WFC + GS + Citi + HSBC + Indian
    (['loansprincipal','notionalprincipal','principalamount','loanamount',
      'facevalue','parvalue','outstandingprincipal','loansandadvances','borrowings',
      'loansnet','loansheldforinvestment','financingreceivable',
      'longtermdebt','shorttermborrowings','debtoutstanding',
      'loansandleasesreceivablenet','loansandleasesreceivablegross',
      'notesreceivablegross','mortgageloansoncrealestate',
      'principalamountofloansgranted','grosscarryingamount','amortisedcost',
      'beneficialinterestliabilitylongterm','borrowingsfromsubsidiaries',
      'financingreceivableexcludingaccruedinterestbeforeallowance',
      'redeemablelongtermdebt','zerocouponnotesaggregateprincipalatmaturity',
      'loansandleasesoutstanding','residentialmortgageloans',
      'loansheldforsale','loansheldforinvestmentnet',
      'loansheldatfairvalue','loansreceivableatfairvalue',
      'loanportfoliobalance','consumerloansnet','corporateloansnet',
      'loansandadvancestocustomers','loansandadvancestobanks',
      'financialassetsmeasuredatamortisedcost','loansandadvancesatamortisedcost',
      'advancesnet','advancesgross','totaladvances','loanportfolio','creditexposure'],
     'notionalPrincipal', float),

    # Interest Rate
    (['nominalinterestrate','interestrate','couponrate','effectiveinterestrate',
      'statedrate','annualpercentagerate','contractualinterestrate',
      'weightedaverageinterestrate','debtinstrumentinterestratestatedpercentage',
      'debtinstrumentinterestrate','mortgageloansonrealestateinterestrate',
      'longtermdebtweightedaverageinterestratepercentage',
      'financingreceivablemodifiedweightedaverageinterestrate',
      'debtinstrumentweightedaverageinterestrate',
      'weightedaveragecouponrate','averageloanrate','effectiveyield',
      'contractrate','statedinterestrate','effectiveinterestrateonfinancialassets',
      'yieldoncredit','interestrateonadvances'],
     'nominalInterestRate',
     lambda v: float(v) if float(v) <= 1.0 else float(v) / 100),

    # Maturity Date
    (['maturitydate','duedate','contractualmaturitydate','scheduledmaturitydate',
      'redemptiondate','finalmaturitydate','debtinstrumentmaturitydate',
      'loanmaturitydate','mortgagematuritydate','bondmaturitydate',
      'maturitydateoffinancialinstrument','expirydate',
      'loanrepaymentdate','creditfacilitymaturitydate'],
     'maturityDate', str),

    # Issue / Start Date
    (['issuedate','originationdate','settlementdate','loanoriginationdate',
      'tradedate','startdate','effectivedate','commencementdate',
      'debtinstrumentissuancedate','debtinstrumentdateofissuance',
      'mortgageoriginationdate','loanclosingdate',
      'initialissuancedate','inceptiondate','loandisbursementdate','sanctiondate'],
     'initialExchangeDate', str),

    # Currency
    (['currency','currencycode','reportingcurrency','functionalcurrency',
      'denominatedcurrency','entityreportingcurrencyisocode',
      'currencyofdenomination','presentationcurrency'],
     'currency', str),

    # Accrued interest
    (['accruedinterest','interestpayable','interestaccrued'], 'accruedInterest', float),

    # Contract type hints
    (['fixedrateinstrument','fixedratebond','fixedrateloan'],
     '_contractTypeHint', lambda _: 'PAM'),
    (['annuity','amortizingloan','mortgageloan','homeloan'],
     '_contractTypeHint', lambda _: 'ANN'),
    (['floatingrate','variablerate','adjustablerate'],
     '_riskFactorHint', lambda _: True),
]


def _strip_ns(tag: str) -> str:
    return re.sub(r'\{[^}]*\}', '', tag).lower().strip()


def _parse_date(value: str) -> Optional[str]:
    value = value.strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y%m%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(value, fmt).strftime('%Y-%m-%dT00:00:00')
        except ValueError:
            continue
    return value


def _match_tag(tag_clean: str):
    for keywords, actus_field, transform in TAG_MAP:
        for kw in keywords:
            if kw in tag_clean or tag_clean in kw:
                return actus_field, transform
    return None, None


def parse_xbrl(file_content: str) -> dict:
    warnings = []
    raw_fields = {}
    extracted = {}

    if _is_ixbrl(file_content):
        print('[XBRL-PARSER] Detected iXBRL — converting...')
        file_content = _ixbrl_to_xbrl_xml(file_content)
        warnings.append('iXBRL detected and converted.')

    try:
        root = ET.fromstring(file_content)
    except ET.ParseError as e:
        return {'success': False, 'error': f'XML parse error: {e}',
                'instruments': [], 'raw_fields': {}, 'warnings': [], 'suggested_contracts': []}

    for elem in root.iter():
        tag_clean = _strip_ns(elem.tag)
        value = (elem.text or '').strip() or elem.get('contextRef', '') or elem.get('unitRef', '')
        if not value:
            continue
        raw_fields[tag_clean] = value
        actus_field, transform = _match_tag(tag_clean)
        if actus_field and transform:
            try:
                transformed = transform(value)
                if 'Date' in actus_field or 'date' in actus_field:
                    transformed = _parse_date(str(transformed))
                extracted[actus_field] = transformed
            except (ValueError, TypeError):
                warnings.append(f'Could not convert {tag_clean}={value}')

    if not extracted:
        warnings.append('No recognisable ACTUS fields found.')
        return {'success': True, 'instruments': [], 'raw_fields': raw_fields,
                'warnings': warnings, 'suggested_contracts': []}

    contract_type = extracted.pop('_contractTypeHint', None) or 'PAM'
    has_risk      = extracted.pop('_riskFactorHint', False)

    for df in ['initialExchangeDate', 'maturityDate', 'statusDate', 'contractDealDate']:
        v = extracted.get(df, '')
        if v and 'T' not in str(v):
            extracted[df] = str(v).strip() + 'T00:00:00'

    ied = extracted.get('initialExchangeDate')
    if ied:
        try:
            ied_dt = datetime.strptime(ied, '%Y-%m-%dT%H:%M:%S')
            extracted['statusDate'] = extracted['contractDealDate'] = (ied_dt - timedelta(days=1)).strftime('%Y-%m-%dT00:00:00')
        except ValueError:
            extracted['statusDate'] = extracted['contractDealDate'] = ied

    mat = extracted.get('maturityDate', '')
    if mat and 'T' not in str(mat):
        extracted['maturityDate'] = str(mat) + 'T00:00:00'

    rate = extracted.get('nominalInterestRate')
    if rate and rate > 1.0:
        extracted['nominalInterestRate'] = round(rate / 100, 6)

    contract_fields = {
        'contractType': contract_type, 'contractID': f'{contract_type.lower()}-xbrl-01',
        'contractRole': 'RPA', 'currency': extracted.get('currency', 'USD'),
        'dayCountConvention': '30E360', 'calendar': 'WEEKDAY',
        'businessDayConvention': 'SCF', 'premiumDiscountAtIED': 0,
        **{k: v for k, v in extracted.items() if k != 'accruedInterest'},
    }

    ied_str = contract_fields.get('initialExchangeDate', '')
    try:
        from dateutil.relativedelta import relativedelta
        anchor = (datetime.strptime(ied_str, '%Y-%m-%dT%H:%M:%S') + relativedelta(months=1)).strftime('%Y-%m-%dT00:00:00')
    except Exception:
        anchor = ied_str
    contract_fields['cycleAnchorDateOfInterestPayment'] = anchor
    contract_fields.setdefault('cycleOfInterestPayment', 'P1ML0')

    if contract_type == 'ANN':
        contract_fields['cycleAnchorDateOfPrincipalRedemption'] = contract_fields.get('initialExchangeDate', '')
        contract_fields['cycleOfPrincipalRedemption'] = 'P1ML0'

    risk_factors = []
    if has_risk:
        contract_fields.update({'cycleAnchorDateOfRateReset': contract_fields.get('initialExchangeDate', ''),
                                 'cycleOfRateReset': 'P1YL1', 'rateSpread': 0.0,
                                 'marketObjectCodeOfRateReset': 'LIBOR-3M'})
        risk_factors = [{'marketObjectCode': 'LIBOR-3M', 'base': 1.0,
                          'data': [{'time': contract_fields.get('initialExchangeDate', ''), 'value': 0.03}]}]

    required = ['notionalPrincipal', 'nominalInterestRate', 'maturityDate', 'initialExchangeDate', 'currency']
    confidence = round(sum(1 for f in required if f in contract_fields) / len(required) * 100)

    return {
        'success': True,
        'instruments': [contract_fields],
        'raw_fields': raw_fields,
        'warnings': warnings,
        'suggested_contracts': [{
            'contractType': contract_type, 'confidence': confidence,
            'hasRiskFactor': has_risk, 'fieldsFound': list(extracted.keys()),
            'payload': {'contracts': [contract_fields], 'riskFactors': risk_factors},
        }],
    }
