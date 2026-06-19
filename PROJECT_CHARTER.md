# Project Charter — Low-ARR Account Renewal Agent

## The problem (as given)
Automation Anywhere has a long tail of customers on the Automation Success Platform with
annual recurring revenue **under $20,000**. They are too small to justify a dedicated human
Customer Success Manager, so today they are effectively **zero-touch** at renewal. Customer
Success asked for an AI agent that engages this tail, using CRM best practices and the
customer's product-usage level (high / average / low), to assess three things per account:

1. Likelihood of contract renewal
2. Product feedback
3. Interest in upselling the AI platform or professional services

…and to return not just a report but **sentiment analysis + the next best action** for each
upcoming renewal.

## The value reframe (the headline of the KPI story)
Because these accounts get **no human attention today**, the baseline is zero. Any retention
or expansion this agent produces is **incremental ARR captured at near-zero marginal cost**.
This is not "make CSMs faster" — there are no CSMs on these accounts. It is **monetizing a
segment that is currently abandoned.** That framing drives every KPI in `docs/value_kpis.md`.

## What we are building
A self-contained, runnable **agentic process**: a closed loop that segments each at-risk
account, drafts tailored outreach, ingests the customer's reply, runs sentiment + signal
extraction, prescribes a next best action with a dollar value, and — critically — **decides
on its own whether it is safe to act autonomously or must escalate to a human**, scoring its
own accuracy as it goes. Output renders as a CSM worklist + reliability report in Streamlit.

Customer replies are simulated with LLM personas so the whole loop runs locally with no
external systems. This is a deliberate prototype choice and, as a bonus, gives us hidden
ground truth to measure the agent against.

## The differentiator
The reliability layer. "AI is dumb" is the stated grading bar, so the point of this build is
not that an agent *can* do the task — an LLM one-shots a generic version — but that it does
so **consistently and safely**: schema-validated outputs with retry/fallback, a confidence
gate, a typed exception taxonomy (E1–E8), human escalation queues, and a measured accuracy /
calibration number. This is a pattern the author has shipped before (confidence-thresholded
auto-vs-human routing) — see prior work in the email-classification project.

## Deliverables mapping (the assignment's four asks → where they live)
1. **Agentic process flow with exception handling** → `docs/apa_flow.md` (diagram) +
   `pipeline/orchestrator.py` (loop) + `agents/reliability.py` (exceptions E1–E8).
2. **AI agents & GenAI prompts** → `agents/*.py` + `prompts/*.md` (five agents).
3. **Value dimensions & KPIs** → `docs/value_kpis.md`.
4. **Working prototype + sample report** → the runnable repo + the Streamlit app.
5. **Send to the hiring panel** → submitted by hand; not automated.

## Success criteria
- Two commands run the whole thing: `python -m pipeline.orchestrator` then
  `streamlit run app/dashboard.py`.
- The flow visibly handles edge cases, not just the happy path.
- The reliability tab shows a real accuracy number and a human escalation queue.
- Every design choice is defensible out loud (that's the actual interview).

## Explicitly out of scope
Real Salesforce/Gmail integration · real email sending · authentication · multi-user ·
production hardening · an agent framework · dbt. See DECISIONS for the reasoning.

## Constraints
~2 calendar days, alongside a full-time job. Build with Claude Code on Sonnet for cost;
planning/architecture done with Opus. Single model (Sonnet) across all agents for the
prototype.
