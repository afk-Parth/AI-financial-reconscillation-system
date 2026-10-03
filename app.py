"""
AI-Based Financial Reconciliation System - Streamlit Dashboard
Light botanical dashboard styling.

Run with:
    streamlit run app.py
"""
import io
import hashlib
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from reconciliation.matcher import reconcile, MatchConfig

st.set_page_config(page_title="AI Financial Reconciliation", layout="wide")

LIME = "#527A50"
LIME_DIM = "#3E6545"
CARD_BG = "#FFFEFA"
CARD_BORDER = "#DFE8DB"
RED = "#B85445"
MUTED = "#718073"
INK = "#26372C"
PALE_GREEN = "#E2EDD9"
BLUE = "#7294A4"

# ---------------------------------------------------------------------
# Global CSS: soft paper canvas, botanical greens, and restrained panels
# ---------------------------------------------------------------------
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Lora:wght@500;600;700&display=swap');
html, body, [class*="css"] {{ font-family: 'DM Sans', sans-serif; color: {INK}; }}

[data-testid="stAppViewContainer"] {{
    background-color: #F4F7F0;
    background-image: repeating-linear-gradient(0deg, rgba(76,113,74,0.025) 0, rgba(76,113,74,0.025) 1px, transparent 1px, transparent 30px);
}}
[data-testid="stHeader"] {{ background: rgba(244,247,240,0.88); }}
[data-testid="stSidebar"] {{ background-color: #EAF1E5; border-right: 1px solid {CARD_BORDER}; }}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {{ color: {INK}; }}
[data-testid="stSidebar"] h4 {{ font-family: 'Lora', serif; color: {INK}; }}
[data-testid="stSidebar"] label {{ color: {INK} !important; }}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {{ color: {INK}; }}

.app-title {{ font: 600 2.05rem/1.2 'Lora', serif; color: {INK}; margin: 4px 0 6px; }}
.app-subtitle {{ color: {MUTED}; font-size: 0.94rem; margin-bottom: 24px; }}

[data-testid="stVerticalBlockBorderWrapper"] {{
    background-color: {CARD_BG};
    border: 1px solid {CARD_BORDER};
    border-radius: 10px;
    padding: 6px 8px;
    box-shadow: 0 2px 10px rgba(49,78,51,0.035);
}}

[data-testid="stMetric"] {{
    background-color: {CARD_BG};
    border: 1px solid {CARD_BORDER};
    border-radius: 10px;
    padding: 16px 18px 10px 18px;
}}
[data-testid="stMetricLabel"] {{ color: {MUTED} !important; font-weight: 500; }}
[data-testid="stMetricValue"] {{ color: {INK} !important; font-weight: 700; }}

button[kind="primary"] {{
    background-color: {LIME} !important;
    color: #FFFFFF !important;
    border-radius: 8px !important;
    border: none !important;
    font-weight: 700 !important;
}}
button[kind="primary"]:hover {{ background-color: {LIME_DIM} !important; }}
[data-testid="stDownloadButton"] button {{ border-radius: 8px; }}
[data-testid="stFileUploader"] section {{ background: rgba(255,254,250,0.75); border-color: #C9D8C4; }}
[data-baseweb="select"] > div, [data-baseweb="input"] > div {{ background: {CARD_BG}; border-color: #C9D8C4; }}
[data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] {{ background-color: {LIME}; }}
[data-testid="stTabs"] button {{ color: {MUTED}; }}
[data-testid="stTabs"] button[aria-selected="true"] {{ color: {LIME_DIM}; }}
[data-testid="stDataFrame"] {{ border: 1px solid {CARD_BORDER}; border-radius: 8px; overflow: hidden; }}

.panel-title {{ font: 600 1.04rem 'Lora', serif; color: {INK}; margin: 2px 0 10px 2px; }}
.panel-subtitle {{ font-size: 0.8rem; color: {MUTED}; margin-top: -8px; margin-bottom: 10px; line-height: 1.5; }}

.tx-row {{ display:flex; align-items:center; justify-content:space-between; gap:12px; padding:10px 4px; border-bottom:1px solid {CARD_BORDER}; }}
.tx-row:last-child {{ border-bottom:none; }}
.tx-left {{ display:flex; align-items:center; gap:12px; }}
.tx-avatar {{
    width:38px; height:38px; border-radius:12px;
    display:flex; align-items:center; justify-content:center;
    font-weight:700; font-size:0.85rem; flex-shrink:0;
}}
.tx-desc {{ color:{INK}; font-weight:600; font-size:0.88rem; }}
.tx-meta {{ color:{MUTED}; font-size:0.75rem; margin-top:2px; }}
.tx-amount-pos {{ color:{LIME_DIM}; font-weight:700; font-size:0.9rem; white-space:nowrap; }}
.tx-amount-neg {{ color:{INK}; font-weight:700; font-size:0.9rem; white-space:nowrap; }}
.badge {{
    display:inline-block; padding:2px 8px; border-radius:5px;
    font-size:0.68rem; font-weight:700; margin-left:8px;
}}
.badge-exact {{ background: #E5EFE0; color:{LIME_DIM}; }}
.badge-fuzzy {{ background: #E7EFF2; color:#527586; }}

.hero-card {{
    background: {PALE_GREEN};
    border: 1px solid #D1E0C9;
    border-left: 5px solid {LIME};
    border-radius: 10px;
    padding: 22px 26px;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
}}
.hero-label {{ color: #536C52; font-weight: 700; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; }}
.hero-value {{ color: #294C38; font: 700 2.6rem/1.1 'Lora', serif; margin: 8px 0 6px; }}
.hero-sub {{ color: #536C52; font-size: 0.82rem; font-weight: 500; }}

.stat-card {{
    background-color: {CARD_BG}; border: 1px solid {CARD_BORDER}; border-radius: 10px;
    padding: 12px 16px; height: 100%; display:flex; flex-direction:column; justify-content:center;
}}
.stat-label {{ color: {MUTED}; font-size: 0.78rem; font-weight: 500; }}
.stat-value {{ color: {INK}; font-size: 1.5rem; font-weight: 700; margin-top: 2px; }}
.stat-value-flag {{ color: {RED}; }}

@media (max-width: 700px) {{
    .app-title {{ font-size: 1.7rem; }}
    .hero-card {{ min-height: 150px; padding: 18px; }}
    .tx-row {{ align-items: flex-start; }}
    .tx-desc {{ line-height: 1.45; }}
}}
</style>
""", unsafe_allow_html=True)


def avatar_color(seed: str) -> str:
    """Deterministic color per vendor so the same vendor always gets the
    same avatar color across the dashboard."""
    palette = ["#527A50", "#7294A4", "#C17B59", "#8A9D62", "#B36F70", "#A58A52"]
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    return palette[h % len(palette)]


def initials(text: str) -> str:
    words = [w for w in str(text).split() if w.isalpha()]
    if not words:
        return "?"
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[0][0] + words[1][0]).upper()


# ---------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------
st.markdown("<div class='app-title'>AI Financial Reconciliation</div>", unsafe_allow_html=True)
st.markdown(
    f"<div class='app-subtitle'>A clearer view of your books, with thoughtful matching and anomaly detection.</div>",
    unsafe_allow_html=True
)

# ---------------------------------------------------------------------
# Sidebar: inputs & settings
# ---------------------------------------------------------------------
with st.sidebar:
    st.markdown("#### 1. Upload Data")
    use_sample = st.checkbox("Use bundled sample data", value=True)

    bank_file = None
    ledger_file = None
    if not use_sample:
        bank_file = st.file_uploader("Bank Statement (CSV)", type=["csv"])
        ledger_file = st.file_uploader("Ledger (CSV)", type=["csv"])

    st.markdown("#### 2. Matching Settings")
    date_tol = st.slider("Date tolerance (days)", 0, 10, 3)
    amount_tol_pct = st.slider("Amount tolerance (%)", 0.0, 2.0, 0.5, step=0.1) / 100
    min_conf = st.slider("Minimum match confidence (%)", 50, 95, 70)

    run_btn = st.button("Run Reconciliation", type="primary", use_container_width=True)
    st.markdown(
        f"<div class='panel-subtitle'>Adjusting a setting won't change the results below "
        f"until you click Run Reconciliation.</div>", unsafe_allow_html=True
    )
    st.markdown(
        f"<div class='panel-subtitle'>Expected columns: Date, Description, Amount, Reference "
        f"(negative = debit, positive = credit)</div>", unsafe_allow_html=True
    )

# ---------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------
bank_df = ledger_df = None
if use_sample:
    bank_df = pd.read_csv("sample_data/bank_statement.csv")
    ledger_df = pd.read_csv("sample_data/ledger.csv")
else:
    if bank_file is not None:
        bank_df = pd.read_csv(bank_file)
    if ledger_file is not None:
        ledger_df = pd.read_csv(ledger_file)

if bank_df is None or ledger_df is None:
    st.info("Upload a bank statement and a ledger CSV in the sidebar, or tick "
            "'Use bundled sample data' to try the demo instantly.")
    st.stop()

# Only re-run the matching engine when the button is clicked (or on first load) -
# NOT on every slider/checkbox tweak, since Streamlit re-executes this whole script
# on every widget interaction by default. Sliders will visibly change value as you
# drag them, but the results below only update once you click "Run Reconciliation".
if "result" not in st.session_state:
    st.session_state.result = None

if run_btn or st.session_state.result is None:
    cfg = MatchConfig(date_tolerance_days=date_tol, amount_tolerance_pct=amount_tol_pct, min_confidence=min_conf)
    st.session_state.result = reconcile(bank_df, ledger_df, cfg)

result = st.session_state.result
s = result.summary

# ---------------------------------------------------------------------
# KPI row - one featured hero card (Match Rate) + a 2x2 grid of smaller
# stat cards, instead of five identical boxes in a row.
# ---------------------------------------------------------------------
hero_col, grid_col = st.columns([1.3, 2])

with hero_col:
    st.markdown(f"""
    <div class="hero-card">
        <div class="hero-label">Match Rate</div>
        <div class="hero-value">{s['match_rate_pct']}%</div>
        <div class="hero-sub">{s['exact_matches'] + s['fuzzy_matches']} of {s['total_bank_transactions']} bank transactions reconciled</div>
    </div>
    """, unsafe_allow_html=True)

with grid_col:
    g1, g2 = st.columns(2)
    with g1:
        st.markdown(f"""<div class="stat-card"><div class="stat-label">Exact Matches</div>
            <div class="stat-value">{s['exact_matches']}</div></div>""", unsafe_allow_html=True)
        st.write("")
        st.markdown(f"""<div class="stat-card"><div class="stat-label">Unmatched (Bank)</div>
            <div class="stat-value">{s['unmatched_bank']}</div></div>""", unsafe_allow_html=True)
    with g2:
        st.markdown(f"""<div class="stat-card"><div class="stat-label">AI Fuzzy Matches</div>
            <div class="stat-value">{s['fuzzy_matches']}</div></div>""", unsafe_allow_html=True)
        st.write("")
        flag_class = "stat-value-flag" if s["anomalies_flagged"] > 0 else "stat-value"
        st.markdown(f"""<div class="stat-card"><div class="stat-label">Anomalies Flagged</div>
            <div class="{flag_class}">{s['anomalies_flagged']}</div></div>""", unsafe_allow_html=True)

st.write("")

# ---------------------------------------------------------------------
# Row 2: Recent matched transactions (left) + Match breakdown donut (right)
# ---------------------------------------------------------------------
col_left, col_right = st.columns([1.5, 1])

with col_left:
    with st.container(border=True):
        st.markdown("<div class='panel-title'>Recent Matched Transactions</div>", unsafe_allow_html=True)
        preview = result.matched.head(8)
        if len(preview) == 0:
            st.markdown(f"<div style='color:{MUTED}; padding:20px 4px;'>No matched transactions yet.</div>",
                         unsafe_allow_html=True)
        else:
            rows_html = ""
            for _, row in preview.iterrows():
                vendor = row["Bank Description"]
                color = avatar_color(vendor)
                amt = row["Bank Amount"]
                amt_class = "tx-amount-pos" if amt > 0 else "tx-amount-neg"
                amt_str = f"{'+' if amt > 0 else '-'} ₹{abs(amt):,.2f}"
                badge_class = "badge-exact" if row["Match Type"] == "Exact" else "badge-fuzzy"
                badge_label = "Exact" if row["Match Type"] == "Exact" else f"AI {row['Confidence (%)']}%"
                rows_html += f"""
                <div class="tx-row">
                    <div class="tx-left">
                        <div class="tx-avatar" style="background:{color}22; color:{color}; border:1px solid {color}55;">
                            {initials(vendor)}
                        </div>
                        <div>
                            <div class="tx-desc">{vendor[:38]}<span class="badge {badge_class}">{badge_label}</span></div>
                            <div class="tx-meta">{row['Bank Date']} · ref {row['Bank Reference']}</div>
                        </div>
                    </div>
                    <div class="{amt_class}">{amt_str}</div>
                </div>
                """
            st.markdown(rows_html, unsafe_allow_html=True)

with col_right:
    with st.container(border=True):
        st.markdown("<div class='panel-title'>Match Breakdown</div>", unsafe_allow_html=True)
        labels = ["Exact", "AI Fuzzy", "Unmatched"]
        values = [s["exact_matches"], s["fuzzy_matches"], s["unmatched_bank"]]
        colors = ["#527A50", BLUE, "#D8DFD4"]
        fig = go.Figure(data=[go.Pie(
            labels=labels, values=values, hole=0.65, sort=False, direction="clockwise",
            marker=dict(colors=colors, line=dict(color=CARD_BG, width=3)),
            textinfo="none",
        )])
        fig.update_layout(
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, font=dict(color=INK, size=11)),
            margin=dict(t=10, b=10, l=10, r=10), height=260,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            annotations=[dict(
                text=f"{s['match_rate_pct']}%<br><span style='font-size:11px;color:{MUTED}'>matched</span>",
                x=0.5, y=0.5, font=dict(size=20, color=INK), showarrow=False
            )],
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

st.write("")

# ---------------------------------------------------------------------
# Row 3: Reconciliation trend (cumulative matched amount over time)
# ---------------------------------------------------------------------
with st.container(border=True):
    st.markdown("<div class='panel-title'>Reconciliation Trend — Cumulative Matched Value</div>", unsafe_allow_html=True)
    if len(result.matched) > 0:
        trend = result.matched.copy()
        trend["Bank Date"] = pd.to_datetime(trend["Bank Date"])
        trend["AbsAmount"] = trend["Bank Amount"].abs()
        trend = trend.sort_values("Bank Date")
        trend["Cumulative"] = trend["AbsAmount"].cumsum()

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=trend["Bank Date"], y=trend["Cumulative"],
            mode="lines+markers", line=dict(color=LIME, width=3),
            marker=dict(size=6, color=LIME),
            fill="tozeroy", fillcolor="rgba(82,122,80,0.12)",
            hovertemplate="₹%{y:,.0f}<extra></extra>",
        ))
        fig2.update_layout(
            margin=dict(t=10, b=10, l=10, r=10), height=260,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, color=MUTED),
            yaxis=dict(showgrid=True, gridcolor="rgba(76,113,74,0.12)", color=MUTED),
        )
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
    else:
        st.markdown(f"<div style='color:{MUTED}; padding:10px 4px;'>No matched transactions to chart yet.</div>",
                     unsafe_allow_html=True)

st.write("")

# ---------------------------------------------------------------------
# Row 4: Unmatched + Anomalies + Export, tabbed
# ---------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["Unmatched — Bank", "Unmatched — Ledger", "Anomalies", "Export"])

with tab1:
    with st.container(border=True):
        st.dataframe(result.unmatched_bank, use_container_width=True, hide_index=True)

with tab2:
    with st.container(border=True):
        st.dataframe(result.unmatched_ledger, use_container_width=True, hide_index=True)

with tab3:
    with st.container(border=True):
        if len(result.anomalies) == 0:
            st.markdown(f"<span style='color:{LIME}'>No anomalies detected.</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"<span style='color:{RED}'>{len(result.anomalies)} potential issue(s) flagged for review.</span>",
                         unsafe_allow_html=True)
            st.dataframe(result.anomalies, use_container_width=True, hide_index=True)

with tab4:
    with st.container(border=True):
        st.markdown(f"<span style='color:{MUTED}'>Download the full reconciliation report as an Excel workbook "
                     f"(one sheet per category).</span>", unsafe_allow_html=True)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            result.matched.to_excel(writer, sheet_name="Matched", index=False)
            result.unmatched_bank.to_excel(writer, sheet_name="Unmatched_Bank", index=False)
            result.unmatched_ledger.to_excel(writer, sheet_name="Unmatched_Ledger", index=False)
            result.anomalies.to_excel(writer, sheet_name="Anomalies", index=False)
        st.download_button(
            "Download Reconciliation_Report.xlsx",
            data=buffer.getvalue(),
            file_name="Reconciliation_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )
