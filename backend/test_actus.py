"""
Run this directly:  python test_actus.py
Sends a known-good PAM contract to ACTUS and prints the raw response.
"""
import requests, json

ACTUS_URL = "http://34.203.247.32:8083/eventsBatch"

# Known-good payload from l3PAMnoRF.txt example
payload = {
    "contracts": [{
        "calendar": "WEEKDAY",
        "businessDayConvention": "SCF",
        "contractType": "PAM",
        "statusDate": "2024-03-31T00:00:00",
        "contractRole": "RPA",
        "contractID": "pam-xbrl-test-01",
        "cycleAnchorDateOfInterestPayment": "2024-05-01T00:00:00",
        "cycleOfInterestPayment": "P1ML0",
        "nominalInterestRate": 0.0875,
        "dayCountConvention": "30E360",
        "currency": "INR",
        "contractDealDate": "2024-03-31T00:00:00",
        "initialExchangeDate": "2024-04-01T00:00:00",
        "maturityDate": "2029-03-31T00:00:00",
        "notionalPrincipal": 5000000,
        "premiumDiscountAtIED": 0
    }],
    "riskFactors": []
}

print("Sending to ACTUS:", ACTUS_URL)
print("Payload:", json.dumps(payload, indent=2))
print("-" * 60)

try:
    r = requests.post(ACTUS_URL, json=payload, timeout=30)
    print("Status:", r.status_code)
    print("Response:", json.dumps(r.json(), indent=2)[:2000])
except Exception as e:
    print("ERROR:", e)
