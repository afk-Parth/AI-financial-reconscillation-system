"""
Basic sanity tests for the reconciliation engine.
Run with:  python3 -m pytest tests/  (or just: python3 tests/test_matcher.py)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
from reconciliation.matcher import reconcile, MatchConfig, text_similarity, normalize_description


def make_dfs():
    bank = pd.DataFrame([
        {"Date": "2025-01-02", "Description": "AMAZON WEB SERVICES PAYMENT", "Amount": -4500.00, "Reference": "TXN1"},
        {"Date": "2025-01-05", "Description": "ELECTRICITY BOARD BILL PAY", "Amount": -3200.50, "Reference": "TXN2"},
        {"Date": "2025-01-15", "Description": "UNKNOWN WIRE TRANSFER", "Amount": 15750.00, "Reference": "TXN3"},
    ])
    ledger = pd.DataFrame([
        {"Date": "2025-01-02", "Description": "AWS Cloud Services - Jan", "Amount": -4500.00, "Reference": "LED1"},
        {"Date": "2025-01-06", "Description": "Electricity Board - Jan Bill", "Amount": -3200.50, "Reference": "LED2"},
    ])
    return bank, ledger


def test_exact_match():
    bank, ledger = make_dfs()
    result = reconcile(bank, ledger)
    exact = result.matched[result.matched["Match Type"] == "Exact"]
    assert len(exact) == 1
    assert exact.iloc[0]["Bank Reference"] == "TXN1"


def test_fuzzy_match_within_date_tolerance():
    bank, ledger = make_dfs()
    result = reconcile(bank, ledger, MatchConfig(date_tolerance_days=3))
    fuzzy = result.matched[result.matched["Match Type"] == "AI Fuzzy Match"]
    assert len(fuzzy) == 1
    assert fuzzy.iloc[0]["Bank Reference"] == "TXN2"


def test_unmatched_detected():
    bank, ledger = make_dfs()
    result = reconcile(bank, ledger)
    assert len(result.unmatched_bank) == 1
    assert result.unmatched_bank.iloc[0]["Reference"] == "TXN3"


def test_text_similarity_handles_wording_differences():
    a = normalize_description("VENDOR PAYMT SHARMA TRADER")
    b = normalize_description("Vendor Payment - Sharma Traders")
    assert text_similarity(a, b) > 80


def test_duplicate_anomaly_detected():
    bank = pd.DataFrame([
        {"Date": "2025-01-06", "Description": "VENDOR PAYMENT - SHARMA TRADERS", "Amount": -12000.0, "Reference": "T1"},
        {"Date": "2025-01-14", "Description": "VENDOR PAYMT SHARMA TRADER", "Amount": -12000.0, "Reference": "T2"},
    ])
    ledger = pd.DataFrame([
        {"Date": "2025-01-06", "Description": "Sharma Traders Payment", "Amount": -12000.0, "Reference": "L1"},
    ])
    result = reconcile(bank, ledger)
    dup_flags = result.anomalies[result.anomalies["Anomaly Type"] == "Possible duplicate payment"]
    assert len(dup_flags) == 2


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
        passed += 1
    print(f"\n{passed}/{len(tests)} tests passed.")
