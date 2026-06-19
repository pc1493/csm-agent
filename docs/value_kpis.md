# Value Dimensions & KPIs

Deliverable #3. The framing that makes this land: **this segment is zero-touch today, so the
baseline is zero.** We are not making CSMs faster — there are no CSMs here. We are capturing
value from a tail that is currently abandoned. Every KPI below is read against that baseline.

## Six value dimensions

### 1. Coverage — *reach the unreachable*
The agent touches accounts that received no human engagement at all. The first unit of value
is simply that the segment is now *covered*.
- **% of low-ARR renewals engaged** (target: ~100% vs ~0% today)
- **Accounts triaged per cycle** with zero added headcount
- **Time-to-first-touch** before renewal (was: never)

### 2. Retention — *save renewals that would have silently lapsed*
- **Renewal rate of engaged tail accounts** vs the historical no-touch lapse rate
- **ARR retained** = renewed ARR attributable to an agent-driven save
- **Save-rate on flagged detractors** (E4 accounts that a human call recovered)

### 3. Expansion — *surface the small-but-hungry accounts*
- **Upsell pipeline $ surfaced** (especially E7: sub-$20k accounts with ≥$5k expansion need)
- **Qualified expansion leads routed to AE** per cycle
- **Expansion conversion rate** on agent-surfaced opportunities

### 4. Efficiency — *value per dollar of attention*
- **Cost per account engaged** (model tokens + compute; effectively cents)
- **% auto-resolved vs escalated** — how much the agent absorbs without a human
- **Human-hours consumed** only on the escalations worth a human's time
- **ARR influenced per $ of agent cost** (the headline efficiency ratio)

### 5. Reliability — *is the autonomy earned?* (the differentiator's own scorecard)
- **Sentiment / disposition / upsell-fit accuracy** vs ground truth (prototype) → sampled
  human QA (production)
- **Confidence calibration** — when confident, how often right (validates the auto/escalate gate)
- **Escalation precision** — of escalated accounts, how many genuinely needed a human
- **Fallback/exception rate** — how often E8 (malformed output) fires; trending down = trust up

### 6. Insight — *aggregate the voice of the tail*
- **Top product-feedback themes** across the segment (a free byproduct of analysis)
- **Churn-reason distribution** — why the tail leaves, quantified for Product/Pricing
- **Feature-request signal** ranked by associated ARR

## How the prototype measures these today
The Streamlit **Reliability tab** computes accuracy + calibration + the exception queue live
from the run. Coverage, retention, expansion, and efficiency are shown as portfolio rollups
(accounts triaged, ARR at risk, $ surfaced, auto vs escalate split). The numbers are on
simulated data — their job is to prove the *measurement* exists and the mechanism produces
them, not to assert real-world figures.

## The one-sentence value statement
*Turn the abandoned long tail into a measured, self-correcting renewal channel that retains and
expands ARR at near-zero marginal cost, and routes the scarce human only to the accounts where
attention pays for itself.*
