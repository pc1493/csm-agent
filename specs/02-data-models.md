Task: 02 — Data Models (the canonical schema)

Status: [DONE] — implemented in pipeline/models.py. This spec is the contract of record. The
schema is the single most depended-on artifact in the repo: specs, prompts, the DuckDB schema,
the orchestrator, and the dashboard all assume these exact field names. Changing it casually
breaks everything silently.

Context
Every object that moves through the loop is a Pydantic model. Using strict typed contracts is
half of the reliability story: an agent's output is only accepted if it validates against its
model, which is what agents/llm.py::complete_json enforces. Literals (not free strings) pin the
enums so invalid categories can't slip through.

The load-bearing split: visible vs hidden
- Account holds ONLY fields the agents are allowed to see.
- GroundTruth holds the hidden truth (true_disposition, true_sentiment, true_reason,
  true_upsell_fit, responsiveness, will_bounce, will_opt_out).
- GroundTruth is used in exactly two places: persona.py (to author a realistic reply) and
  reliability.score() (to grade the prediction). The analysis agent must NEVER receive it.
  If truth leaks into analysis, the accuracy number becomes a lie — this separation is the
  whole reason the eval is credible. See spec 04.

The models (summary — authoritative definition is the code)
- Inputs:  Account, GroundTruth
- Agent outputs: RouterDecision, OutreachDraft, CustomerReply, AnalysisResult, NextBestAction
- Reliability: RoutingOutcome (decision auto|escalate, queue, exception_codes, confidence)
- Assembled: AccountResult (one row of the report)
- Eval: EvalRecord (prediction vs truth + derived correctness flags)
Enums as Literals: UsageTier, Strategy, Sentiment, Disposition, UpsellType, Responsiveness,
Priority, Decision, Queue. AnalysisResult.renewal_likelihood and the confidence fields are
constrained to [0.0, 1.0].

Change protocol (read before editing models.py)
1. Grep the field name across specs/, prompts/, pipeline/, agents/, app/ — find every use.
2. Update all of them in the same change. A rename that misses schema.sql or db.py fails at
   insert time, not import time, so it won't show up until a full run.
3. Add a DECISIONS entry explaining the change. The schema is architecture.

Acceptance criteria
[ ] All models import without error (`python -c "import pipeline.models"`).
[ ] No ground-truth field appears on Account.
[ ] Literals reject out-of-set values (e.g. sentiment="meh" raises ValidationError).
[ ] Field names in schema.sql and db.py match the model attributes they persist.

Out of scope
No ORM, no database-generated models, no dynamic/optional mega-schema. Keep the models small,
explicit, and readable — they double as documentation of the domain for the panel.
