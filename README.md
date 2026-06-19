# Low-ARR Account Renewal Agent

A self-contained, runnable **agentic process** that re-engages Automation Anywhere's long tail of
customers (ARR < $20k) on the Automation Success Platform. These accounts are too small to justify
a human CSM, so today they are **zero-touch at renewal**. This agent engages each one, reads the
reply, recommends a next best action with a dollar value, and — the point of the build —
**decides on its own whether it is safe to act autonomously or must escalate to a human**, scoring
its own accuracy against hidden ground truth as it goes.

Take-home prototype. Planning/architecture in Opus; implementation in Claude Code on Sonnet.
Customers are simulated with LLM personas, so the whole loop runs locally with no Salesforce or
email integration.

## The value reframe
Because this segment gets no human attention today, the baseline is **zero**. Any renewal saved or
expansion surfaced is **incremental ARR at near-zero marginal cost** — this is not "make CSMs
faster" (there are none here), it is **monetizing a segment that is currently abandoned.** Every
KPI is read against that baseline.

## What it does — the closed loop
Per account, end to end:

```
Salesforce-shaped account
   |  Router             pick strategy (save / nurture / upsell / standard) + adapt questions
   |  Outreach           draft a tailored email covering renewal + feedback + upsell
   |  Customer (sim)     persona seeded with HIDDEN truth writes a realistic reply
   |                       (bounce / opt-out / silence short-circuit here, no model call)
   |  Analysis           sentiment - renewal likelihood - feedback - upsell - self-confidence
   |                       (never sees the ground truth)
   |  Next Best Action   named play + $ value + talking points
   |  Reliability gate   DETERMINISTIC: auto-handle vs escalate + exception code + queue
   |  Eval               score the prediction vs hidden truth (accuracy + calibration)
   v
 DuckDB  ->  Streamlit report
```

The full diagram with every exception branch is in `docs/apa_flow.md` (deliverable #1).

## The agents (deliverable #2)
Five small, single-purpose LLM agents. Each returns a strict, Pydantic-validated object — a
**signal**, never a decision. Prompts live in `prompts/*.md`.

| Agent | Input | Emits | Notes |
|---|---|---|---|
| **Router** | account | strategy + 3–5 adapted questions | low usage + renewal soon → save, high + soon → upsell, average → nurture, healthy + far → standard |
| **Outreach** | account + strategy | email (subject, body) | warm, concise, covers all three dimensions |
| **Customer persona** | account + **ground truth** + email | the reply | the *only* component that sees the truth; expresses sentiment obliquely, like a busy human |
| **Analysis** | reply text + usage tier | sentiment, renewal likelihood, feedback, upsell, **confidence** | **never** sees ground truth — that is what keeps the accuracy number honest |
| **Next Best Action** | account + analysis | play + **$ value** + talking points | the dollar figure drives prioritization and the E7 rule |

Every model call goes through one chokepoint (`agents/llm.py::complete_json`) that validates the
JSON against its schema, **retries with a stricter instruction on failure, then falls back to a
safe default that forces escalation** (E8). The loop never crashes on a bad generation.

## The reliability layer (the differentiator)
`agents/reliability.py` — **deterministic Python, not an LLM call**, so it is auditable, instant,
free, and unit-testable. It does two jobs.

**1. Route.** Only a clean, confident, non-conflicting signal is auto-handled; everything else is
escalated to a typed human queue, stamped with an exception code:

| Code | Trigger | Queue |
|---|---|---|
| E1 | email bounced / invalid contact | `data_hygiene` |
| E2 | customer opted out | `data_hygiene` (suppress) |
| E3 | no reply after 3 touches | `manual_outreach` |
| E4 | detractor (negative + renewal likelihood < 0.4) | `save_call` (always human) |
| E5 | confidence < 0.75 | `human_review` |
| E6 | conflicting signals (e.g. positive tone, low renewal) | `human_review` |
| E7 | upsell ≥ $5k on a sub-$20k account | `ae_upsell` (**escalate despite low ARR**) |
| E8 | malformed model output | `human_review` (confidence forced to 0) |

**E7 is the "smart threshold":** the naive rule is *low ARR = full automation, low priority*. That
misses the small, happy account with a real expansion need worth multiples of its current spend.
**Value at stake drives the human's attention, not current revenue.** Thresholds (0.75, $5k, 3
touches) are named constants, documented in `DECISIONS.md`, tuned by calibration data.

**2. Score.** Compares the analysis prediction (which never saw the truth) against the hidden
`GroundTruth`: renewal-call (disposition bucket), sentiment, and upsell-fit correctness.

## How it grades itself (the evaluation)
Because customers are simulated, every account carries a hidden `GroundTruth` the analysis agent
never sees — so the accuracy number is real, not asserted. The Reliability tab aggregates it:

- **Renewal-call accuracy** — did the renewal-likelihood bucket match the true disposition? *This
  is the headline — the business question, "will they renew?"*
- **Upsell-fit accuracy** — was the right expansion type identified?
- **Sentiment** — a softer, noisier 3-class tone read, shown honestly and *not* gated on.
- **The gate proof** — of the accounts it chose to auto-handle, how often the renewal call was
  right (everything it was unsure about, it escalated). That is the autonomy being *earned*.

**The honest seam:** in production the simulated Salesforce pull and customer reply become a real
query and a real inbound email/survey, and offline accuracy is replaced by **sampled human QA on
escalations + renewal-outcome backtesting.** The mechanism — segment, engage, analyze, gate,
escalate — is identical.

## The report (deliverable #4)
`streamlit run app/dashboard.py` — three tabs, reading only from DuckDB:

- **Portfolio** — the worklist of previously zero-touch accounts, sorted by $ at stake; auto vs
  escalate counts and ARR at risk.
- **Account drill-down** — one account end to end: the email it drafted, the customer's actual
  reply, the analysis, and the decision + exception codes.
- **Agent reliability** — the accuracy/calibration scorecard and the human escalation queue (what
  it declined to touch, and why).

## Value dimensions & KPIs (deliverable #3)
Six dimensions, all read against the zero baseline (full detail in `docs/value_kpis.md`):
**Coverage** (reach the unreachable), **Retention** (saves that would have silently lapsed),
**Expansion** (small-but-hungry accounts → AE), **Efficiency** (ARR influenced per $ of agent
cost), **Reliability** (is the autonomy earned?), and **Insight** (aggregate the voice of the tail).

## Run it
Prerequisites: **Python 3.11+** and an **Anthropic API key**.

```
cp .env.example .env          # add your ANTHROPIC_API_KEY
pip install -r requirements.txt

python -m pipeline.data_gen          # 20 synthetic accounts + hidden ground truth -> data/
python -m pipeline.orchestrator      # run the full loop over all accounts -> data/renewal.duckdb
streamlit run app/dashboard.py       # the CSM report (3 tabs)
pytest                               # smoke test
```

**Live demo trace** — watch one account go through the whole chain in real time (~30s), printing
each stage with its latency and its self-grade vs the hidden truth, **writing nothing to the DB**
(so a live run never disturbs the dashboard):

```
python -m pipeline.orchestrator --account ACME-012 --demo
```

## Data
20 deterministic synthetic accounts (seed 42). Usage tier correlates with disposition/sentiment
**with noise on purpose** — if low usage always meant churn the analysis would be trivial and the
accuracy number meaningless. Injected edge cases exercise the exception paths: one bounce, one
opt-out, one silent responder, one smart-threshold upsell (E7), one hidden churn. Generated `data/`
is gitignored.

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
docs/                apa_flow.md (#1), value_kpis.md (#3), presentation-outline.md, demo-runsheet.md
tests/               smoke test
data/                DuckDB + generated JSON — gitignored
```

## Design decisions (the "why" — graded)
Framework-free Python (transparency on a projector, control over the loop), DuckDB not dbt (~20
rows — dbt is ceremony at this scale), a single model (predictable cost), simulated customers
(self-contained *and* it manufactures the ground truth that makes the accuracy real), and
autonomous-by-default with earned escalation (a human-approves-everything design defeats the cost
rationale — the sophistication is the guardrail). Each with full rationale in `DECISIONS.md`.

## Deliverables (assignment → location)
| # | Ask | Where |
|---|-----|-------|
| 1 | Agentic process flow + exception handling | `docs/apa_flow.md` + `pipeline/orchestrator.py` + `agents/reliability.py` |
| 2 | AI agents & GenAI prompts | `agents/*.py` + `prompts/*.md` |
| 3 | Value dimensions & KPIs | `docs/value_kpis.md` |
| 4 | Working prototype + sample report | this repo + the Streamlit app |
| 5 | Send to the hiring panel | done by hand |

## Tech stack
Python · Anthropic API (`claude-sonnet-4-6`) · Pydantic (validation) · DuckDB (store) ·
Streamlit (report). No agent framework, no dbt — deliberate.

## Status & production roadmap
Complete, runnable prototype. For production: real Salesforce + inbound-email wiring, human QA
sampling on escalations, renewal-outcome backtesting, and model routing (Haiku for triage/persona,
Sonnet reserved for low-confidence re-analysis) as a cost lever. The mechanism does not change.

## Out of scope
Real Salesforce/Gmail integration · real email sending · authentication · multi-user · production
hardening · an agent framework · dbt. See `DECISIONS.md` for the reasoning.
