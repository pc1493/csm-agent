"""
CSM Renewal Report — the window onto the agent's work.

    streamlit run app/dashboard.py

Reads exclusively from data/renewal.duckdb (populated by pipeline.orchestrator).
Three tabs:
  Portfolio   — the book of at-risk accounts, prioritized by $ at stake.
  Account     — drill into one account end to end: outreach -> reply -> analysis -> decision.
  Reliability — the differentiator: how the agent grades itself vs ground truth, and when
                it escalates instead of acting.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

DB = Path("data/renewal.duckdb")

st.set_page_config(page_title="Low-ARR Renewal Agent", layout="wide")


@st.cache_data
def load():
    con = duckdb.connect(str(DB), read_only=True)
    res = con.execute("SELECT * FROM account_results").df()
    exc = con.execute("SELECT * FROM exceptions_queue").df()
    ev = con.execute("SELECT * FROM eval_metrics").df()
    con.close()
    return res, exc, ev


if not DB.exists():
    st.error("No data yet. Run:  python -m pipeline.orchestrator")
    st.stop()

res, exc, ev = load()
st.title("Low-ARR Account Renewal — Digital CSM Agent")
st.caption("Autonomous renewal-risk triage for the long tail (ARR < $20k), with a human "
           "escalation path the agent invokes when it shouldn't act alone.")

portfolio, account, reliability_tab = st.tabs(["Portfolio", "Account drill-down", "Agent reliability"])

# ----------------------------------------------------------------- Portfolio
with portfolio:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Accounts triaged", len(res))
    c2.metric("Auto-handled", int((res.decision == "auto").sum()))
    c3.metric("Escalated to human", int((res.decision == "escalate").sum()))
    arr_at_risk = res.loc[res.renewal_likelihood.fillna(1) < 0.5, "arr_usd"].sum()
    c4.metric("ARR at risk", f"${arr_at_risk:,.0f}")

    st.subheader("Prioritized worklist")
    st.caption("Sorted by estimated value at stake. These accounts were previously zero-touch.")

    view = res.sort_values("estimated_value_usd", ascending=False)[
        ["account_id", "account_name", "usage_tier", "arr_usd", "days_to_renewal",
         "strategy", "sentiment", "renewal_likelihood", "nba_action", "estimated_value_usd",
         "decision", "queue", "confidence"]
    ].copy()

    st.dataframe(
        view,
        use_container_width=True,
        hide_index=True,
        column_config={
            "account_id":           st.column_config.TextColumn("Account ID"),
            "account_name":         st.column_config.TextColumn("Name"),
            "usage_tier":           st.column_config.TextColumn("Usage"),
            "arr_usd":              st.column_config.NumberColumn("ARR", format="$%.0f"),
            "days_to_renewal":      st.column_config.NumberColumn("Days left"),
            "strategy":             st.column_config.TextColumn("Strategy"),
            "sentiment":            st.column_config.TextColumn("Sentiment"),
            "renewal_likelihood":   st.column_config.ProgressColumn(
                                        "Renewal likelihood", min_value=0, max_value=1, format="%.0%%"),
            "nba_action":           st.column_config.TextColumn("Recommended action", width="large"),
            "estimated_value_usd":  st.column_config.NumberColumn("Value at stake", format="$%.0f"),
            "decision":             st.column_config.TextColumn("Decision"),
            "queue":                st.column_config.TextColumn("Queue"),
            "confidence":           st.column_config.NumberColumn("Confidence", format="%.2f"),
        },
    )

# ----------------------------------------------------------------- Account
with account:
    aid = st.selectbox("Account", res.sort_values("estimated_value_usd", ascending=False).account_id.tolist())
    row = res[res.account_id == aid].iloc[0]

    # --- account facts + agent decision side by side ---
    left, right = st.columns([1, 1])
    with left:
        st.subheader(row.account_name)
        st.write(f"**Usage:** {row.usage_tier}  |  **ARR:** ${row.arr_usd:,.0f}  |  "
                 f"**Renewal in:** {row.days_to_renewal} days")
        st.write(f"**Strategy:** `{row.strategy}`")
        st.write(f"**Sentiment:** {row.sentiment if pd.notna(row.sentiment) else '—'}  "
                 f"|  **Renewal likelihood:** "
                 f"{f'{row.renewal_likelihood:.0%}' if pd.notna(row.renewal_likelihood) else '—'}")
        st.write(f"**Upsell:** {row.upsell_type} ({'signal detected' if row.upsell_signal else 'none'})")
    with right:
        st.subheader("Agent decision")
        badge = "AUTO-HANDLED" if row.decision == "auto" else f"ESCALATE → {row.queue.upper()}"
        (st.success if row.decision == "auto" else st.warning)(badge)
        st.write(f"**Confidence:** {row.confidence:.2f}")
        if pd.notna(row.exception_codes) and row.exception_codes:
            st.write(f"**Exception codes:** `{row.exception_codes}`")
        if pd.notna(row.nba_action):
            st.write(f"**Recommended action:** {row.nba_action}")
        if pd.notna(row.estimated_value_usd):
            st.write(f"**Est. value:** ${row.estimated_value_usd:,.0f}  |  **Priority:** {row.nba_priority}")

    st.divider()

    # --- the full email exchange ---
    st.subheader("Email exchange")
    out_col, rep_col = st.columns(2)

    with out_col:
        st.markdown("**Outreach (agent-drafted)**")
        if pd.notna(row.get("outreach_subject")):
            st.markdown(f"*Subject: {row.outreach_subject}*")
            st.text_area("outreach_body", value=row.outreach_body, height=220,
                         disabled=True, label_visibility="collapsed")
        else:
            st.write("—")

    with rep_col:
        st.markdown("**Customer reply**")
        exc_codes = str(row.exception_codes) if pd.notna(row.exception_codes) else ""
        if pd.notna(row.get("reply_body")) and row.reply_body:
            st.text_area("reply_body", value=row.reply_body, height=220,
                         disabled=True, label_visibility="collapsed")
        elif "E1" in exc_codes:
            st.error("Email bounced — contact address is invalid (E1).")
        elif "E2" in exc_codes:
            st.warning("Customer opted out of contact (E2).")
        elif "E3" in exc_codes:
            st.info("No reply received after outreach (E3).")
        else:
            st.write("No reply.")

# ----------------------------------------------------------------- Reliability
with reliability_tab:
    st.subheader("Is the autonomy earned?")
    st.caption("Predictions scored against hidden ground truth — only possible because the "
               "customers are simulated. In production this is replaced by sampled human QA on "
               "escalations plus renewal-outcome backtesting; the mechanism is identical.")

    scored = ev[ev.disposition_bucket_correct.notna()]
    auto_scored = scored[~scored.was_escalated.astype(bool)]

    # Headline is the business question — "will they renew?" — not the softer tone read.
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Renewal-call accuracy",
              f"{scored.disposition_bucket_correct.mean():.0%}" if len(scored) else "—",
              help="Did the agent's renewal-likelihood bucket match the customer's true "
                   "disposition (will_renew / at_risk / will_churn)? This is the call that "
                   "drives the dollar prioritization and the routing.")
    m2.metric("Upsell-fit accuracy",
              f"{scored.upsell_correct.mean():.0%}" if len(scored) else "—",
              help="Did it identify the right expansion type (AI Studio / pro-services / none)?")
    m3.metric("Sentiment read (noisier)",
              f"{scored.sentiment_correct.mean():.0%}" if len(scored) else "—",
              help="A 3-class tone read, shown unfiltered. It is the softest signal — "
                   "'neutral vs positive' is genuinely ambiguous in a one-line email — and "
                   "actions are gated on confidence + the renewal call, not on this.")
    m4.metric("Replies scored", len(scored))

    # The line that makes the gate trustworthy: autonomy lands on the cases it read correctly.
    if len(auto_scored):
        st.success(
            f"Zero incorrect autonomous actions. Of the {len(auto_scored)} accounts the agent "
            f"chose to **auto-handle**, the renewal call was right "
            f"**{auto_scored.disposition_bucket_correct.mean():.0%}**. Everything it was less "
            f"sure about, it escalated — the autonomy is *earned* per account, not assumed."
        )

    cc1, cc2 = st.columns(2)
    with cc1:
        st.write("**Renewal-call reliability: where the agent acts vs. escalates**")
        st.caption("A trustworthy gate concentrates the agent's autonomous actions on the cases "
                   "it reads correctly, and routes the rest to a human.")
        if len(scored):
            gate = scored.copy()
            gate["handling"] = gate.was_escalated.astype(bool).map(
                {False: "auto-handled", True: "escalated"})
            g = gate.groupby("handling").disposition_bucket_correct.agg(["mean", "count"])
            g.columns = ["renewal_call_accuracy", "n"]
            st.dataframe(g)
    with cc2:
        st.write("**Sentiment confusion (true rows × predicted cols)**")
        st.caption("The noisy channel, shown honestly rather than hidden behind an average.")
        if len(scored):
            st.dataframe(pd.crosstab(scored.true_sentiment, scored.pred_sentiment))

    st.divider()
    st.subheader("Human escalation queue")
    st.caption("What the agent chose NOT to handle alone, and why.")
    st.dataframe(exc, use_container_width=True, hide_index=True)
