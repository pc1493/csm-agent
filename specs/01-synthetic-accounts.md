Task: 01 — Synthetic Accounts & Hidden Ground Truth

Status: [DONE] — implemented in pipeline/data_gen.py. This spec is the contract of record;
do NOT rewrite the generator. Read it to understand why the data looks the way it does, and
treat the acceptance criteria as a regression check if you ever touch it.

Context
The use case starts from "Salesforce gives us at-risk low-ARR accounts." There is no real
Salesforce here, so pipeline/data_gen.py fabricates that input deterministically. It produces
two parallel objects per account: a visible Account (what agents may see) and a hidden
GroundTruth (what only the persona generator and the eval may see). Schema for both lives in
pipeline/models.py (spec 02).

Goal
A fixed, reproducible set of ~20 accounts (ARR < $20k) spanning usage tiers and dispositions,
realistic enough to exercise every branch of the loop, with ground truth that makes the eval
meaningful.

Design intent (the parts that matter, and why)
- SEED = 42, deterministic. Same accounts every run so demos and tests are stable.
- usage_tier correlates with disposition/sentiment via priors, but with deliberate NOISE
  (DISPOSITION_PRIORS + SENTIMENT_BY_DISPOSITION are probabilistic, not lookups). If low usage
  always meant churn, the analysis agent would be trivial and the accuracy number meaningless.
  Real accounts surprise you; the data has to as well.
- Active-seat ratio, runs_last_30d, and bots_in_production track the tier with jitter so the
  account facts are internally consistent with the assigned tier.
- Injected edge cases (deterministic, by index) so every exception path has a live example:
    ACME-003  -> bounce (will_bounce)              -> exercises E1
    ACME-006  -> opt-out (will_opt_out, negative)  -> exercises E2
    ACME-009  -> silent (responsiveness)           -> exercises E3
    ACME-012  -> ARR $6k, happy, real pro-services need -> exercises E7 (smart threshold)
    ACME-015  -> churning but neutral-sounding (price) -> exercises E4/E6 conflict detection

Inputs / outputs
Input: none (pure generator). Output: data/accounts.json, data/ground_truth.json.
Run: `python -m pipeline.data_gen`.

Acceptance criteria
[ ] Exactly N_ACCOUNTS (20) accounts; all arr_usd < 20000.
[ ] Re-running produces identical account_ids and field values (deterministic).
[ ] At least one of each: bounce, opt-out, silent responder.
[ ] ACME-012 is low-ARR, positive, with true_upsell_fit = professional_services.
[ ] Every Account validates against the Account model; every GroundTruth against GroundTruth.

Out of scope
No real Salesforce/CRM pull. No randomized seed (stability matters more than novelty here).
Do not move ground-truth fields onto Account — the visible/hidden split is load-bearing (spec 02).
Do not grow this past ~20 rows; volume adds demo time and DuckDB/dbt complexity for no benefit.
