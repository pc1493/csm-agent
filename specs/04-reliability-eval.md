Task: 04 — Reliability Layer & Evaluation (the differentiator)

Context
"AI is dumb" is the explicit grading criterion. This layer is the answer: because the model
is unreliable, the system never acts autonomously on weak, conflicting, or high-stakes
signals, and it grades its own accuracy against hidden ground truth. agents/reliability.py
is already implemented (route + score). This spec exists so you understand it, can defend it
out loud, and verify it behaves. Treat code changes here as architectural — document via
DECISIONS.

Required reading
@DECISIONS.md (#003 threshold, #004 smart-threshold $, #005 no-response touches)
pipeline/models.py (RoutingOutcome, EvalRecord)

The two responsibilities
1. route(account, reply, analysis, nba) -> RoutingOutcome
   Decide AUTO vs ESCALATE and assign a queue, stamping exception codes:
     E1 bounce            -> data_hygiene    (no analysis exists)
     E2 opt-out           -> data_hygiene    (suppress, flag CSM)
     E3 no response (N=3) -> manual_outreach
     E4 detractor         -> save_call       (negative + renewal_likelihood < 0.4; ALWAYS human)
     E5 low confidence    -> human_review    (confidence < CONFIDENCE_THRESHOLD = 0.75)
     E6 conflicting       -> human_review    (e.g. positive tone but low likelihood)
     E7 upsell > $5,000   -> ae_upsell       (escalate DESPITE sub-$20k ARR — the smart bit)
     E8 malformed output  -> human_review    (analysis confidence forced to 0 in agents/analysis.py)
   Only a clean, confident, non-conflicting signal returns decision="auto", queue="none".

2. score(truth, analysis, routing) -> EvalRecord
   Compare the analysis prediction (which never saw truth) against GroundTruth:
     - sentiment_correct: predicted == true sentiment
     - disposition_bucket_correct: renewal_likelihood bucketed (>=.66 renew, >=.33 at_risk,
       else churn) == true_disposition
     - upsell_correct: predicted upsell_type == true_upsell_fit
   Aggregated across the batch by the dashboard's Reliability tab into accuracy + a sentiment
   confusion matrix + confidence calibration.

Why this is honest (be ready to say this)
The accuracy number is only meaningful because customers are simulated, giving us ground
truth we'd never have in production. State the seam plainly: in production this offline
accuracy is replaced by sampled human QA on a slice of escalations + renewal-outcome
backtesting. The mechanism (confidence gate, escalation queues, exception taxonomy) is
identical either way.

Acceptance criteria
[ ] The injected edge cases route correctly: ACME-003 -> E1/data_hygiene;
    ACME-006 -> E2/data_hygiene; ACME-009 -> E3/manual_outreach;
    ACME-012 -> E7/ae_upsell (happy, $6k ARR, real pro-services need).
[ ] No account with confidence < 0.75 is ever auto-handled.
[ ] score() returns null correctness fields (not False) when there was no reply.
[ ] The Reliability tab shows a non-trivial confusion matrix and a calibration table.

Out of scope
Do not move thresholds without a DECISIONS entry explaining why.
Do not let route() call the model — it is deterministic by design (auditable, instant, free).
Do not collapse the queues into a single "escalate" bucket — the queue routing is the value.
