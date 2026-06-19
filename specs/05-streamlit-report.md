Task: 05 — CSM Report (Streamlit)

Context
app/dashboard.py is functional and reads from data/renewal.duckdb. It renders three tabs:
Portfolio, Account drill-down, Agent reliability. The Reliability tab is the centerpiece of
the demo — do not simplify it away. Your work: one real feature (surface the actual email
exchange per account) plus optional visual polish.

Required reading
@CLAUDE.md
app/dashboard.py
pipeline/db.py, pipeline/schema.sql
/mnt/skills/public/frontend-design/SKILL.md  (only if you do visual polish)

Inputs
data/renewal.duckdb (account_results, exceptions_queue, eval_metrics).

Goal
A reviewer can navigate from the portfolio worklist into a single account and read the
agent's entire reasoning chain — the outreach it sent, the reply it got, the analysis, and
the auto/escalate decision with exception codes.

Steps
1. Persist the outreach email and the raw customer reply so the Account tab can show them.
   Simplest path: add `outreach_subject`, `outreach_body`, `reply_body` columns to
   account_results in schema.sql, populate them in orchestrator.process/db.load_results,
   and render them in the Account tab where the TODO marker is. (Add a DECISIONS note if you
   change the schema.)
2. In the Account tab, show the exchange in reading order: outreach → reply → analysis →
   decision, so the chain is legible at a glance.
3. Optional polish: tighten the Portfolio worklist (color the decision column, format ARR/$,
   highlight urgent priority). Keep it readable on a projector — large text, high contrast.

Output
Modified: app/dashboard.py, pipeline/schema.sql, pipeline/db.py, pipeline/orchestrator.py
(only the persistence wiring). No new dependencies beyond streamlit + pandas + duckdb.

Acceptance criteria
[ ] Selecting an account shows its outreach email and the customer's reply text.
[ ] The reasoning chain reads top to bottom without hunting.
[ ] All three tabs render with no empty-state errors on a full run.
[ ] App launches with: streamlit run app/dashboard.py

Out of scope
No login, no multi-page routing, no live re-run button inside the app (the live demo runs
the orchestrator from the terminal). Do not fetch from any external API in the app.
Do not store raw replies anywhere other than the local DuckDB file.
