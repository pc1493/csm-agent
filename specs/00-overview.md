Task: 00 — Build Order & Status Map

Context
This repo is scaffolded by the planning model (Opus). Contracts, prompts, the orchestrator
control flow, and the reliability/eval logic are written. Your job (Claude Code / Sonnet)
is to make the agent bodies real and verify the loop end to end. Build in the order below.
Read CLAUDE.md and METHODOLOGY.md before starting. The spec is the contract — if reality
forces a change to a contract in pipeline/models.py, update every reference and add a
DECISIONS entry.

Status legend: [DONE] runnable as-is · [WIRE] one or two TODOs to fill · [BUILD] real work.

Build order
1. [DONE]  pipeline/models.py            — canonical schema. Do not change casually.
2. [DONE]  pipeline/data_gen.py          — synthetic accounts + ground truth. Run it first.
3. [DONE]  pipeline/schema.sql, db.py    — DuckDB persistence.
4. [WIRE]  agents/llm.py                  — fill _client() and _raw_complete(); see spec 03.
5. [BUILD] agents/{router,outreach,persona,analysis,next_best_action}.py
                                          — bodies call complete_json already; verify each
                                            produces valid output against its prompt. spec 03.
6. [DONE]  agents/reliability.py          — route() + score(). Tune thresholds only via DECISIONS.
7. [DONE]  pipeline/orchestrator.py       — closed loop. Should not need structural edits.
8. [BUILD] app/dashboard.py               — functional; polish + add the outreach/reply
                                            surfacing TODO. spec 05.
9. [DONE]  docs/apa_flow.md, value_kpis.md, presentation-outline.md — review, make yours.

Goal
A reviewer can run two commands and watch the whole thing work:
    python -m pipeline.orchestrator
    streamlit run app/dashboard.py

Acceptance criteria
[ ] `python -m pipeline.data_gen` writes data/accounts.json + data/ground_truth.json.
[ ] `python -m pipeline.orchestrator` completes all 20 accounts with no unhandled exception.
[ ] At least one account auto-handles and at least one escalates to each major queue type
    that the injected edge cases imply (data_hygiene, manual_outreach, save_call, ae_upsell).
[ ] Streamlit renders all three tabs with populated data.
[ ] Sentiment accuracy on scored replies prints at the end of the orchestrator run.

Out of scope
Real Salesforce / Gmail integration. Real email sending. Auth. Multi-user. A web backend.
Do not add an agent framework (LangGraph/CrewAI) — plain Python is a deliberate choice (#001).
Do not add dbt — DuckDB only (#002).
