# AI-Based Financial Reconciliation System

An end-to-end system that automatically reconciles transactions between a **bank statement**
and an internal **ledger**, even when descriptions are worded differently, dates are off by a
day or two, or amounts differ by small rounding errors. Unmatched and suspicious transactions
are flagged for human review.

This matches the architecture described in the patent IDF:
`Data Sources → Ingestion → Preprocessing → AI Matching Engine → Anomaly Detection → Dashboard`.

## Streamlit dashboard walkthrough

The illustration below shows the main dashboard sections using the bundled sample data.

![Illustrated overview of the financial reconciliation Streamlit dashboard](docs/images/dashboard-overview.svg)

- **Upload Data** — use the included demo CSVs or upload a bank statement and ledger of your own.
- **Matching Settings** — set the allowed date difference, amount variance, and minimum confidence for fuzzy matches. Click **Run Reconciliation** to apply changed settings.
- **Match Rate and summary metrics** — see the percentage of bank transactions reconciled, with counts for exact matches, AI fuzzy matches, unmatched bank entries, and flagged anomalies.
- **Recent Matched Transactions** — review matched bank entries, dates, references, amounts, and whether each match was exact or fuzzy.
- **Match Breakdown** — compare exact, fuzzy, and unmatched bank transactions at a glance.
- **Reconciliation Trend** — follow the cumulative value of matched transactions over time.
- **Review and Export tabs** — inspect unmatched bank entries, unmatched ledger entries, and anomalies; use the Export tab to download the complete report as an Excel workbook.

## How the matching actually works (no black box)

1. **Exact pass** — transactions with identical amount + identical date are auto-matched
   instantly (100% confidence).
2. **AI fuzzy pass** — everything left over is scored pairwise on three signals, combined into
   one weighted confidence score:
   - **Text similarity** of the (normalized) description — e.g. "VENDOR PAYMT SHARMA TRADER"
     vs "Sharma Traders Payment" still scores highly similar.
   - **Date closeness** within a configurable tolerance window (handles bank-vs-book timing lag).
   - **Amount closeness** within a configurable tolerance (handles rounding/fee differences).

   Pairs above the confidence threshold are matched greedily, highest-confidence first,
   one-to-one (a transaction can't be "used" in two matches).
3. **Anomaly detection** — runs on top of the matching result:
   - An **Isolation Forest** (unsupervised ML, from scikit-learn) flags statistically unusual
     transaction amounts.
   - A **duplicate-payment check** flags same-amount transactions whose descriptions are highly
     similar — catching accidental double payments even when the wording isn't identical.

This is genuinely testable logic (not hand-waved) — see `sample_data/` and the test run below.

## Project structure

```
recon_project/
├── app.py                        # Streamlit dashboard (the UI)
├── reconciliation/
│   ├── __init__.py
│   └── matcher.py                 # Core matching + anomaly detection engine
├── sample_data/
│   ├── bank_statement.csv         # Demo data (15 transactions, some messy on purpose)
│   └── ledger.csv                 # Demo data (13 transactions)
├── requirements.txt
└── README.md
```

## Running it

```bash
pip install -r requirements.txt
streamlit run app.py
```

This opens a local web dashboard at `http://localhost:8501`. Tick **"Use bundled sample data"**
in the sidebar to see a working demo immediately, or uncheck it and upload your own
`Date, Description, Amount, Reference` CSV files for the bank statement and ledger.

## Running just the engine (no UI), e.g. to show it working in a terminal / viva

```bash
python3 -c "
import pandas as pd
from reconciliation.matcher import reconcile

bank = pd.read_csv('sample_data/bank_statement.csv')
ledger = pd.read_csv('sample_data/ledger.csv')
result = reconcile(bank, ledger)

print(result.summary)
print(result.matched)
print(result.anomalies)
"
```

## What to say about this in a placement interview

- It's a **hybrid AI system**: deterministic rule-based matching for the easy cases (fast, 100%
  reliable), falling back to a **weighted fuzzy-matching + ML anomaly detection** layer for the
  hard cases — a realistic design pattern used in real fintech reconciliation tools, not just a
  toy demo.
- You can explain **precision/recall trade-offs**: raising `min_confidence` reduces false
  matches but increases manual review load — a genuine tunable parameter, exposed as a slider
  in the dashboard.
- The **Isolation Forest** usage is real unsupervised ML (you can explain how it works: it
  isolates outliers by randomly partitioning the feature space — outliers get isolated in fewer
  splits than normal points).
- It's **extensible**: swapping the fuzzy-matching layer for an embedding-based semantic
  similarity model (e.g. sentence-transformers) would be the natural "v2" if asked about future
  improvements.

## Honesty note (for your patent IDF / project report)

This is a working prototype you built and can demo and explain end-to-end. If anyone asks
whether it's been tested in a real production environment, the honest answer is: it is tested
against sample/demo data only, not live production bank feeds — same as what's stated in your
IDF form.
