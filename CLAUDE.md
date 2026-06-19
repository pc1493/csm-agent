# CLAUDE.md — Project Context for Claude Code

You are implementing a take-home assignment prototype. Read this, then `specs/00-overview.md`,
then build in the listed order. Planning and architecture were done separately (Opus); your
job is implementation and verification on Sonnet, kept tightly in scope.

## What this is
An autonomous renewal agent for Automation Anywhere's low-ARR (<$20k) customer tail. A closed
loop: segment account → draft outreach → simulate customer reply → analyze sentiment/signals →
recommend next best action with a $ value → decide auto-handle vs escalate-to-human → score
accuracy vs hidden ground truth → render a CSM report in Streamlit. Customers are simulated;
everything runs locally.

## The one thing that matters most
The **reliability layer** (`agents/reliability.py`) is the differentiator. The grading bar is
"AI is dumb" — so the value is not that the agent works, it's that it works *consistently and
safely*: validated outputs + retry/fallback, a confidence gate, exception taxonomy E1–E8,
human escalation queues, and a measured accuracy number. Do not dilute this.

## Ground rules (full version in METHODOLOGY.md)
- Specs are contracts. Don't add out-of-scope features.
- `pipeline/models.py` is the canonical schema; change it only repo-wide + a DECISIONS entry.
- All model calls go through `agents/llm.py::complete_json`. Retry lives only there.
- Routing/exception logic lives only in `agents/reliability.py`. Agents emit signals, not decisions.
- The analysis agent must NEVER receive `GroundTruth`. This keeps the accuracy number honest.
- Fix prompts before code. Prefer boring, projector-legible Python.
- Verify acceptance criteria for real before calling anything done.

## Current status
Runnable as-is: models, data_gen, db, reliability, orchestrator (control flow).
Needs work: `agents/llm.py` (two TODOs — the actual Anthropic call), per-agent verification,
and the Streamlit dashboard polish + outreach/reply surfacing.

## Commands
```
python -m pipeline.data_gen          # regenerate synthetic accounts + ground truth
python -m pipeline.orchestrator      # run the full loop -> data/renewal.duckdb
python -m pipeline.orchestrator --account ACME-012   # single account (live demo)
streamlit run app/dashboard.py       # the report
pytest                               # smoke test
```

## Stack
Python · Anthropic API (claude-sonnet-4-6) · Pydantic (validation) · DuckDB (store) ·
Streamlit (report). No agent framework, no dbt — deliberate (DECISIONS #001, #002).

## Out of scope
Real Salesforce/Gmail · real email sending · auth · multi-user · production hardening.
If production-necessary but missing, note it in DECISIONS as a follow-up; don't build it.
