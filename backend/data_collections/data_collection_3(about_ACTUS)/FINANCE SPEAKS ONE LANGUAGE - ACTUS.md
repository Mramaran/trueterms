FINANCE SPEAKS ONE LANGUAGE - ACTUS 

​

empowering efficient, transparent and consistent financial ecosystems



**​What is ACTUS?**

ACTUS — the Algorithmic Contract Types Unified Standards — is a global initiative to bring clarity, consistency, and precision to the way financial contracts are represented and analyzed.

At its core, ACTUS provides a standardized, machine-readable way to represent the logic behind all types of financial contracts — from simple loans to complex derivatives. Instead of relying on legal documents or custom code to understand how a contract behaves, ACTUS turns financial agreements into algorithms that computers can process, simulate, and analyze reliably.

Why does this matter? Because in today's fast-moving, interconnected financial world, understanding risk and value in real time is more critical than ever. ACTUS enables this by creating a common language for financial instruments — helping institutions, regulators, and developers make better decisions, faster.

ACTUS is not just a technical standard — it's a foundation for transparent, efficient, and resilient financial systems.



**Fundamentals**

ACTUS is based on a modeling paradigm, in which standardized Contract Types (CTs) are the granular building blocks of the financial world. ACTUS aims to raise this standardization to a universal/global level.

Central to the paradigm is a smart and machine-readable algorithmic representation of all legal agreements and a strict separation of the known from the unknown. The only knowns are the legal agreements and possibly the current state of the risk factors. The unknowns are the future states of the risk factors (in particular, the market, counterparty and behavioral risks).

The graphic illustrates this framework through three horizontal layers: Input Elements, Contract Events, and Analysis Elements. In the Input Elements layer, financial contracts stand at the center, receiving inputs from three risk factor categories. Markets (including yield curves and foreign exchange rates) influence contracts from above. Counterparties affect contracts from the left side, representing credit and default risks. Behavior impacts contracts from the right, capturing prepayment patterns and customer actions.

The graphic shows how financial contracts and current states of the risk factors (yield curves, FX rates etc.) are the core inputs. For analytical purposes, they are augmented with risk models that describe the possible future movements of the risk factors. ACTUS provides only the links to these models, not the models themselves.

The Contract Events layer displays a timeline running horizontally, marked with discrete event points labeled e₁, e₂, e₃, continuing through eₙ to time t. These events represent the predetermined schedule of contractual obligations such as payments, interest rate resets, and maturity dates. Given the state of contracts and a scenario of risk factors, it is possible to derive these contract events, which then generate the expected state-contingent cash flows.

The Analysis Elements layer branches into two parallel analytical pathways. The left pathway shows Liquidity analysis flowing downward to produce Liquidity at Risk (LaR) metrics. The right pathway shows Value analysis, which splits into two streams: one flowing through Income to generate Earnings at Risk (EaR), and another flowing through Sensitivity to produce Value at Risk (VaR). The Sensitivity stream also connects laterally to the Income stream, indicating the interrelationship between value sensitivity and earnings projections. From the expected state-contingent cash flows it is possible to derive the analytical metrics of interest, such as income, value and liquidity.



**ACTUS TAXONOMY**

**Overview**

The ACTUS Taxonomy presents a classification system where ACTUS Contract Types are defined based on underlying contractual algorithm patterns. Each Contract Type pattern covers different classes of financial products. With very few exceptions, virtually all financial instruments currently known can be represented by parameterizing and combining exactly **32 ACTUS Contract Types**.

The total count is 32 contract types, organized into two top-level categories:
- **Financial Contracts** (28 types) — covering Basic and Combined/Derivatives
- **Credit Enhancement** (4 types) — covering guarantee, collateral, margining and reporting



**Core Principle**

ACTUS breaks down the entirety of all existing financial instruments into distinct financial contract types. Each contract type covers a distinctive pattern of payment obligations found in financial instruments. These represent the basic financial building blocks — often referred to as "the periodic table of financial elements."



**Complete ACTUS Taxonomy — All 32 Contract Types**

The following is the complete and official taxonomy of all 32 ACTUS contract types, organized by category exactly as shown in the ACTUS taxonomy diagram.


---

## FINANCIAL CONTRACTS — BASIC

### Fixed Income — Maturities

These are fixed-income contracts that have a defined maturity date.

**PAM (Principal at Maturity)**
Interest paid periodically; full principal repaid at maturity.
Examples: Zero-coupon bonds, bullet loans, interest-only mortgages.

**ANN (Annuity)**
Equal periodic payments covering both interest and principal.
Examples: Fixed-rate mortgages, car loans, amortizing bonds.

**NAM (Negative Amortizer)**
Payments smaller than interest due, causing outstanding balance to grow.
Examples: Payment-option mortgages, graduated payment mortgages.

**LAM (Linear Amortizer)**
Regular equal principal repayments with decreasing interest over time.
Examples: Straight-line amortization loans.

**ANX (Annuity with exotic features)**
Annuity contract with exotic or non-standard payment schedules.

**NAX (Negative Amortizer exotic)**
Negative amortizer with exotic or non-standard structures.

**LAX (Exotic Linear Amortizer)**
Linear amortizer with variable or exotic amortization schedules.

**CLM (Call Money)**
Callable deposits and short-term loans with variable rates.
Examples: Overnight lending, demand deposits.

**PBN (Principal at Maturity with BN)**
Principal-at-maturity variant with special principal breakdown features.


### Fixed Income — Non-Maturities

These are fixed-income contracts with no fixed maturity date.

**CSH (Cash)**
Simple cash position or cash account.
Examples: Cash holdings, money market instruments.

**UMP (Undefined Maturity Profile)**
Instruments with uncertain or undefined maturity.
Examples: Savings accounts, current accounts, revolving credit.


### Index Based

Contracts whose value or payments are linked to an index.

**STK (Stock)**
Equity instruments with dividends and capital gains.
Examples: Ordinary shares, preference shares.

**COM (Commodity)**
Physical commodity-based instruments.
Examples: Oil, gold, agricultural commodity contracts.


---

## FINANCIAL CONTRACTS — COMBINED / DERIVATIVES

### Symmetric Derivatives

Derivatives where both parties have equal obligations.

**SWAPS (Plain Vanilla Interest Rate Swap)**
Exchange of fixed interest payments for floating interest payments.

**SWPPV (Principal Value Swap)**
Interest rate swap that also involves exchange of notional principal.

**FXOUT (Foreign Exchange Outright)**
Forward foreign exchange contract — buy/sell currency at a fixed future rate.

**FUTUR (Futures)**
Standardized exchange-traded futures contract.


### Options — Plain Vanilla

Standard option contracts giving the right but not obligation to buy or sell.

**OPTNS (Options)**
Vanilla call and put options on any underlying asset.

**CAPFL (Cap/Floor)**
Interest rate cap (upper limit) or floor (lower limit) option.

**BNDCP (Bond with Cap)**
Bond contract combined with an embedded interest rate cap.

**BNDWR (Bond Warrant)**
Bond contract combined with an embedded warrant (option to buy equity).


### Options — Exotic

Non-standard options with complex payoff structures.

**EXOTi (Exotic Option)**
Options with non-standard, path-dependent or complex payoff structures.
Examples: Barrier options, Asian options, lookback options.


### Securitization — Credit

Credit-related securitization and structured credit instruments.

**CDSWP (Credit Default Swap)**
Contract providing credit protection — buyer pays premium, seller covers default loss.

**TRSWP (Total Return Swap)**
Swap where one party pays total return of an asset; other pays a fixed/floating rate.

**CLNTE (Credit Linked Note)**
A note whose repayment is linked to a credit event of a reference entity.


### Securitization — Market

Market-based securitization instruments.

**SCRMR (Securitization — Market Rate)**
Securitization instrument linked to market rate movements.

**SCRCR (Securitization — Credit)**
Securitization instrument linked to credit performance of underlying assets.


---

## CREDIT ENHANCEMENT

Contracts that transfer or reduce credit risk exposure.

**CEG (Credit Enhancement Guarantee)**
Guarantee contract — transfers exposure from debtor to guarantor.
Examples: Bank guarantees, surety bonds, letter of credit.

**CEC (Credit Enhancement Collateral)**
Collateral contract — creates a collateral relationship covering debtor exposure.
Examples: Pledged assets, margin accounts, repo collateral.

**MAR (Margining)**
Contract governing margin calls and collateral posting for derivative positions.
Examples: Variation margin, initial margin agreements.

**REP (Reporting)**
Contract type for reporting and reference obligations in structured transactions.


---

**Summary Count — All 32 ACTUS Contract Types**

| Category | Sub-Category | Count | Contract Types |
|---|---|---|---|
| Basic — Fixed Income Maturities | | 9 | PAM, ANN, NAM, LAM, ANX, NAX, LAX, CLM, PBN |
| Basic — Fixed Income Non-Maturities | | 2 | CSH, UMP |
| Basic — Index Based | | 2 | STK, COM |
| Combined — Symmetric | | 4 | SWAPS, SWPPV, FXOUT, FUTUR |
| Combined — Options Plain Vanilla | | 4 | OPTNS, CAPFL, BNDCP, BNDWR |
| Combined — Options Exotic | | 1 | EXOTi |
| Combined — Securitization Credit | | 3 | CDSWP, TRSWP, CLNTE |
| Combined — Securitization Market | | 2 | SCRMR, SCRCR |
| Credit Enhancement | | 4 | CEG, CEC, MAR, REP |
| **TOTAL** | | **32** | |


**Implementation Status**

According to the ACTUS Demo Application, the following contract types have working implementations with demo cases:

Fully Implemented: ANN, LAX, FXOUT, LAM, NAM, SWPPV, PAM, STK, SWAPS
Base Implementation: CLM, CAPFL, CSH, COM, UMP


**Additional Resources**

The complete taxonomy with all contract type specifications, algorithms, and applicability matrices can be accessed through:

Full Data Dictionary: https://github.com/actusfrf/actus-dictionary
Technical Specifications: https://www.actusfrf.org/techspecs
Demo Application: http://demo.actusfrf.org
