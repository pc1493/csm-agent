# Low-ARR Account Renewal Agent

An autonomous renewal-risk agent for Automation Anywhere's long tail of customers (ARR
< $20k) on the Automation Success Platform. These accounts are too small for a human CSM, so
they're zero-touch at renewal today. This agent engages them, reads sentiment, recommends a
next best action, and — the point of the whole thing — **decides on its own whether it's safe
to act or must escalate to a human**, scoring its own accuracy as it goes.

Take-home prototype. Planning/architecture in Opus; implementation in Claude Code on Sonnet.

## What it does (the loop)
segment account → draft tailored outreach → ingest the customer's reply → analyze
sentiment/renewal/feedback/upsell → recommend next best action with a $ value → **confidence
gate: auto-handle or escalate** → score prediction vs hidden ground truth → render a CSM report.

Customers are simulated with LLM personas, so the whole thing runs locally with no Salesforce
or email integration. See `DECISIONS.md` #007 for why, and the production seam.

## Prerequisites
- Python 3.11+
- An Anthropic API key

## Setup
```
cp .env.example .env
# put your ANTHROPIC_API_KEY in .env
pip install -r requirements.txt
```

## Run
```
python -m pipeline.data_gen          # synthetic accounts + hidden ground truth -> data/
python -m pipeline.orchestrator      # run the full loop -> data/renewal.duckdb
streamlit run app/dashboard.py       # the CSM report (3 tabs)
```
Single account for the live demo: `python -m pipeline.orchestrator --account ACME-012`

## Project layout
```
PROJECT_CHARTER.md   the assignment, the value reframe, scope
METHODOLOGY.md       how this is built (spec-driven rules for Claude Code)
DECISIONS.md         architectural decisions + rationale (the "why" — graded)
CLAUDE.md            standing context for Claude Code
specs/               task specs — the contracts (00 overview, 03 agents, 04 reliability, 05 app)
prompts/             the five GenAI agent prompts (deliverable #2)
pipeline/            models (schema), data_gen, db, orchestrator (the loop)
agents/              router, outreach, persona, analysis, next_best_action, reliability, llm
app/                 dashboard.py — Streamlit report
docs/                apa_flow.md (#1), value_kpis.md (#3), presentation-outline.md, kickoff
tests/               smoke test
data/                DuckDB + generated JSON — gitignored
```

## Deliverables (assignment → location)
| # | Ask | Where |
|---|-----|-------|
| 1 | Agentic process flow + exception handling | `docs/apa_flow.md` + `pipeline/orchestrator.py` + `agents/reliability.py` |
| 2 | AI agents & GenAI prompts | `agents/*.py` + `prompts/*.md` |
| 3 | Value dimensions & KPIs | `docs/value_kpis.md` |
| 4 | Working prototype + sample report | this repo + the Streamlit app |
| 5 | Send to the reviewer | done by hand |

## Phases
| Phase | Status | Description |
|-------|--------|-------------|
| 1 | Done | Scaffold: schema, data, reliability/eval logic, orchestrator control flow |
| 2 | Active | Wire LLM calls, verify agents, polish dashboard (Claude Code, spec 03 & 05) |
| 3 | Planned | Tighten prompts against observed outputs; presentation rehearsal |
| 4 | Stretch | Live single-account demo path, calibration tuning |

## Design stance
Framework-free Python for transparency, DuckDB (no dbt), single model for cost, autonomous-
by-default with earned escalation. The differentiator is the reliability layer — validated
outputs, a confidence gate, an E1–E8 exception taxonomy, and a measured accuracy number.
Rationale for each in `DECISIONS.md`.
