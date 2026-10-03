"""
Core AI-based matching engine for financial reconciliation.

Matching strategy (this is the "AI" layer of the system):
  1. Exact pass      - identical amount + identical date -> auto-matched, 100% confidence.
  2. Fuzzy pass       - for everything left unmatched, score every bank-vs-ledger pair using:
                           - text similarity on the description (Levenshtein-ratio based)
                           - date closeness (within a configurable tolerance window)
                           - amount closeness (within a configurable tolerance)
                        combine into one weighted confidence score, and accept the
                        best mutual match above a threshold (classic bipartite greedy matching).
  3. Anomaly pass     - run an Isolation Forest (unsupervised ML) over the *unmatched*
                        transactions' amounts to flag statistical outliers, and a
                        duplicate-payment check (same vendor description + same amount
                        appearing more than once) on the full dataset.

No external AI/LLM API calls are required - this keeps the engine runnable fully offline,
which is also honest for a "not yet built/tested in production" IDF: the logic is real,
testable, and demonstrable with the included sample_data/ files.
"""

from __future__ import annotations
import re
import difflib
from dataclasses import dataclass, field
from datetime import timedelta
import pandas as pd

try:
    from rapidfuzz import fuzz as _rapidfuzz_fuzz
    _HAS_RAPIDFUZZ = True
except ImportError:
    _HAS_RAPIDFUZZ = False


# ----------------------------------------------------------------------
# Text similarity (uses rapidfuzz if installed - much faster - otherwise
# falls back to Python's built-in difflib so the engine never hard-fails)
# ----------------------------------------------------------------------
def text_similarity(a: str, b: str) -> float:
    """Returns a 0-100 similarity score between two strings."""
    if _HAS_RAPIDFUZZ:
        return _rapidfuzz_fuzz.token_sort_ratio(a, b)
    return difflib.SequenceMatcher(None, a, b).ratio() * 100


def normalize_description(text: str) -> str:
    """Lowercase, strip punctuation/extra whitespace so wording differences
    ('Sharma Traders Payment' vs 'VENDOR PAYMT SHARMA TRADER') still compare well."""
    text = str(text).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


@dataclass
class MatchConfig:
    date_tolerance_days: int = 3
    amount_tolerance_pct: float = 0.005       # 0.5% tolerance for rounding differences
    amount_tolerance_abs: float = 1.0          # or flat Rs. 1 absolute tolerance, whichever is looser
    min_confidence: float = 70.0               # minimum weighted score (0-100) to accept a fuzzy match
    weight_text: float = 0.5
    weight_date: float = 0.2
    weight_amount: float = 0.3


@dataclass
class ReconciliationResult:
    matched: pd.DataFrame
    unmatched_bank: pd.DataFrame
    unmatched_ledger: pd.DataFrame
    anomalies: pd.DataFrame
    summary: dict = field(default_factory=dict)


def _load_and_clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    df["Description"] = df["Description"].astype(str)
    df["_norm_desc"] = df["Description"].apply(normalize_description)
    df = df.dropna(subset=["Date", "Amount"]).reset_index(drop=True)
    return df


def _amount_close(a: float, b: float, cfg: MatchConfig) -> bool:
    tol = max(cfg.amount_tolerance_abs, abs(a) * cfg.amount_tolerance_pct)
    return abs(a - b) <= tol


def _date_score(d1, d2, cfg: MatchConfig) -> float:
    diff_days = abs((d1 - d2).days)
    if diff_days > cfg.date_tolerance_days:
        return 0.0
    return 100.0 * (1 - diff_days / (cfg.date_tolerance_days + 1))


def reconcile(bank_df: pd.DataFrame, ledger_df: pd.DataFrame,
              cfg: MatchConfig | None = None) -> ReconciliationResult:
    cfg = cfg or MatchConfig()
    bank = _load_and_clean(bank_df)
    ledger = _load_and_clean(ledger_df)

    bank["_matched"] = False
    ledger["_matched"] = False

    matches = []

    # ---- Pass 1: exact match on amount + date ----
    for bi, brow in bank.iterrows():
        if bank.at[bi, "_matched"]:
            continue
        candidates = ledger[(~ledger["_matched"]) &
                             (ledger["Amount"] == brow["Amount"]) &
                             (ledger["Date"] == brow["Date"])]
        if len(candidates) > 0:
            li = candidates.index[0]
            matches.append({
                "bank_index": bi, "ledger_index": li,
                "confidence": 100.0, "match_type": "Exact",
            })
            bank.at[bi, "_matched"] = True
            ledger.at[li, "_matched"] = True

    # ---- Pass 2: fuzzy / weighted match ----
    remaining_bank = bank[~bank["_matched"]]
    remaining_ledger = ledger[~ledger["_matched"]]

    candidate_scores = []
    for bi, brow in remaining_bank.iterrows():
        for li, lrow in remaining_ledger.iterrows():
            if ledger.at[li, "_matched"]:
                continue
            if not _amount_close(brow["Amount"], lrow["Amount"], cfg):
                continue
            d_score = _date_score(brow["Date"], lrow["Date"], cfg)
            if d_score == 0.0:
                continue
            t_score = text_similarity(brow["_norm_desc"], lrow["_norm_desc"])
            amt_diff_pct = abs(brow["Amount"] - lrow["Amount"]) / max(abs(brow["Amount"]), 1e-6)
            a_score = max(0.0, 100.0 * (1 - amt_diff_pct / max(cfg.amount_tolerance_pct, 1e-6)))
            a_score = min(a_score, 100.0)
            weighted = (cfg.weight_text * t_score +
                        cfg.weight_date * d_score +
                        cfg.weight_amount * a_score)
            if weighted >= cfg.min_confidence:
                candidate_scores.append((weighted, bi, li))

    # Greedy assignment: highest confidence pairs first, one-to-one
    candidate_scores.sort(key=lambda x: -x[0])
    for score, bi, li in candidate_scores:
        if bank.at[bi, "_matched"] or ledger.at[li, "_matched"]:
            continue
        matches.append({
            "bank_index": bi, "ledger_index": li,
            "confidence": round(score, 1), "match_type": "AI Fuzzy Match",
        })
        bank.at[bi, "_matched"] = True
        ledger.at[li, "_matched"] = True

    # ---- Build matched output table ----
    matched_rows = []
    for m in matches:
        b = bank.loc[m["bank_index"]]
        l = ledger.loc[m["ledger_index"]]
        matched_rows.append({
            "Bank Date": b["Date"].date(), "Bank Description": b["Description"],
            "Bank Amount": b["Amount"], "Bank Reference": b.get("Reference", ""),
            "Ledger Date": l["Date"].date(), "Ledger Description": l["Description"],
            "Ledger Amount": l["Amount"], "Ledger Reference": l.get("Reference", ""),
            "Match Type": m["match_type"], "Confidence (%)": m["confidence"],
        })
    matched_df = pd.DataFrame(matched_rows)

    unmatched_bank_df = bank[~bank["_matched"]].drop(columns=["_matched", "_norm_desc"])
    unmatched_ledger_df = ledger[~ledger["_matched"]].drop(columns=["_matched", "_norm_desc"])

    anomalies_df = _detect_anomalies(bank, ledger, cfg)

    summary = {
        "total_bank_transactions": len(bank),
        "total_ledger_transactions": len(ledger),
        "exact_matches": sum(1 for m in matches if m["match_type"] == "Exact"),
        "fuzzy_matches": sum(1 for m in matches if m["match_type"] == "AI Fuzzy Match"),
        "unmatched_bank": len(unmatched_bank_df),
        "unmatched_ledger": len(unmatched_ledger_df),
        "match_rate_pct": round(100 * len(matches) / max(len(bank), 1), 1),
        "anomalies_flagged": len(anomalies_df),
    }

    return ReconciliationResult(
        matched=matched_df,
        unmatched_bank=unmatched_bank_df,
        unmatched_ledger=unmatched_ledger_df,
        anomalies=anomalies_df,
        summary=summary,
    )


def _detect_anomalies(bank: pd.DataFrame, ledger: pd.DataFrame, cfg: MatchConfig) -> pd.DataFrame:
    """
    Two kinds of anomalies on the BANK side (the side most relevant to fraud/error checks):
      (a) Statistical outliers in transaction amount, via Isolation Forest.
      (b) Duplicate-payment detection: same normalized description + same amount
          appearing more than once (classic double-payment error).
    """
    flags = []

    # (a) Isolation Forest outlier detection on amounts
    try:
        from sklearn.ensemble import IsolationForest
        if len(bank) >= 6:
            X = bank[["Amount"]].values
            model = IsolationForest(contamination=0.15, random_state=42)
            preds = model.fit_predict(X)
            for idx, pred in zip(bank.index, preds):
                if pred == -1:
                    row = bank.loc[idx]
                    flags.append({
                        "Date": row["Date"].date(), "Description": row["Description"],
                        "Amount": row["Amount"], "Reference": row.get("Reference", ""),
                        "Anomaly Type": "Unusual amount (statistical outlier)",
                    })
    except ImportError:
        pass

    # (b) Duplicate payment detection - same amount + similar description text,
    # which catches near-duplicates too (e.g. "Vendor Payment - Sharma Traders"
    # vs "Vendor Paymt Sharma Trader"), not just byte-identical descriptions.
    flagged_pairs = set()
    for amount, group in bank.groupby("Amount"):
        if len(group) < 2:
            continue
        idxs = list(group.index)
        for i in range(len(idxs)):
            for j in range(i + 1, len(idxs)):
                i1, i2 = idxs[i], idxs[j]
                sim = text_similarity(bank.at[i1, "_norm_desc"], bank.at[i2, "_norm_desc"])
                if sim >= 80.0:
                    flagged_pairs.add(i1)
                    flagged_pairs.add(i2)

    for idx in flagged_pairs:
        row = bank.loc[idx]
        flags.append({
            "Date": row["Date"].date(), "Description": row["Description"],
            "Amount": row["Amount"], "Reference": row.get("Reference", ""),
            "Anomaly Type": "Possible duplicate payment",
        })

    if not flags:
        return pd.DataFrame(columns=["Date", "Description", "Amount", "Reference", "Anomaly Type"])

    out = pd.DataFrame(flags).drop_duplicates(subset=["Date", "Description", "Amount", "Anomaly Type"])
    return out.reset_index(drop=True)
