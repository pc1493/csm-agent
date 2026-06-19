"""
Reliability layer — the differentiator. NOT an LLM call; deterministic guardrails.

Two jobs:
  1. route(): given the analysis + account, decide AUTO vs ESCALATE and assign a queue,
     stamping any exception codes (E1..E8). This is "AI is dumb, so we never let it act
     unsupervised when the signal is weak, conflicting, or high-stakes."
  2. score(): compare the analysis prediction against the HIDDEN ground truth to produce
     an EvalRecord. Aggregated across the batch this is the accuracy / calibration story.

Exception taxonomy (keep in sync with specs/04-reliability-eval.md):
  E1 bounce / invalid contact        -> data_hygiene
  E2 opt-out / unsubscribe           -> data_hygiene (suppress)
  E3 no response after N touches     -> manual_outreach
  E4 detractor (neg + churn)         -> save_call (always human)
  E5 low confidence (< threshold)    -> human_review
  E6 conflicting signals             -> human_review
  E7 upsell > $X on sub-$20k account -> ae_upsell (escalate DESPITE low ARR)
  E8 malformed model output          -> human_review (forced by confidence=0)

Thresholds live here as named constants and are documented in DECISIONS.
"""

from __future__ import annotations

from pipeline.models import (
    Account, AnalysisResult, CustomerReply, Disposition, EvalRecord,
    GroundTruth, NextBestAction, RoutingOutcome,
)

CONFIDENCE_THRESHOLD = 0.75      # DECISIONS #003
UPSELL_ESCALATION_USD = 5000.0   # DECISIONS #004 — E7 smart threshold
NO_RESPONSE_TOUCHES = 3          # DECISIONS #005


def route(
    account: Account,
    reply: CustomerReply,
    analysis: AnalysisResult | None,
    nba: NextBestAction | None,
    touches: int = NO_RESPONSE_TOUCHES,
) -> RoutingOutcome:
    codes: list[str] = []
    reasons: list[str] = []

    # --- non-response / contact exceptions (no analysis exists) ---
    if reply.bounced:
        return RoutingOutcome(decision="escalate", queue="data_hygiene",
                              reasons=["Email bounced; contact data is stale."],
                              exception_codes=["E1"], confidence=0.0)
    if reply.opted_out:
        return RoutingOutcome(decision="escalate", queue="data_hygiene",
                              reasons=["Customer opted out; suppress and flag CSM."],
                              exception_codes=["E2"], confidence=0.0)
    if not reply.replied or analysis is None:
        return RoutingOutcome(decision="escalate", queue="manual_outreach",
                              reasons=[f"No response after {touches} touches; needs manual outreach."],
                              exception_codes=["E3"], confidence=0.0)

    conf = analysis.confidence

    # --- detractor: always a human save motion ---
    if analysis.sentiment == "negative" and analysis.renewal_likelihood < 0.4:
        codes.append("E4")
        reasons.append("Detractor (negative sentiment + low renewal likelihood): human save call.")

    # --- conflicting signals: don't trust a clean auto-handle ---
    if analysis.sentiment == "positive" and analysis.renewal_likelihood < 0.4:
        codes.append("E6")
        reasons.append("Conflict: positive tone but low renewal likelihood.")
    if analysis.sentiment == "negative" and analysis.renewal_likelihood > 0.7:
        codes.append("E6")
        reasons.append("Conflict: negative tone but high renewal likelihood.")

    # --- smart threshold: tiny ARR but real expansion -> escalate to AE anyway ---
    if analysis.upsell_signal and nba and nba.estimated_value_usd >= UPSELL_ESCALATION_USD:
        codes.append("E7")
        reasons.append(
            f"Upsell ~${nba.estimated_value_usd:,.0f} exceeds ${UPSELL_ESCALATION_USD:,.0f}; "
            f"route to AE despite sub-$20k ARR."
        )

    # --- low confidence ---
    if conf < CONFIDENCE_THRESHOLD:
        codes.append("E5")
        reasons.append(f"Confidence {conf:.2f} below {CONFIDENCE_THRESHOLD:.2f} threshold.")

    # --- decide + assign queue (priority order) ---
    if "E4" in codes:
        return RoutingOutcome(decision="escalate", queue="save_call", reasons=reasons,
                              exception_codes=codes, confidence=conf)
    if "E7" in codes:
        return RoutingOutcome(decision="escalate", queue="ae_upsell", reasons=reasons,
                              exception_codes=codes, confidence=conf)
    if codes:  # E5 / E6 remain
        return RoutingOutcome(decision="escalate", queue="human_review", reasons=reasons,
                              exception_codes=codes, confidence=conf)

    # clean, confident, non-conflicting -> the agent handles it autonomously
    reasons.append("High-confidence, non-conflicting signal: auto-handled.")
    return RoutingOutcome(decision="auto", queue="none", reasons=reasons,
                          exception_codes=[], confidence=conf)


# ---------------------------------------------------------------------------
# Eval: prediction vs hidden ground truth
# ---------------------------------------------------------------------------
def _likelihood_to_disposition(p: float) -> Disposition:
    if p >= 0.66:
        return "will_renew"
    if p >= 0.33:
        return "at_risk"
    return "will_churn"


def score(
    truth: GroundTruth,
    analysis: AnalysisResult | None,
    routing: RoutingOutcome,
) -> EvalRecord:
    if analysis is None:
        return EvalRecord(
            account_id=truth.account_id, pred_sentiment=None, pred_renewal_likelihood=None,
            pred_upsell_type=None, confidence=None, true_sentiment=truth.true_sentiment,
            true_disposition=truth.true_disposition, true_upsell_fit=truth.true_upsell_fit,
            sentiment_correct=None, disposition_bucket_correct=None, upsell_correct=None,
            was_escalated=(routing.decision == "escalate"),
        )
    pred_disp = _likelihood_to_disposition(analysis.renewal_likelihood)
    return EvalRecord(
        account_id=truth.account_id,
        pred_sentiment=analysis.sentiment,
        pred_renewal_likelihood=analysis.renewal_likelihood,
        pred_upsell_type=analysis.upsell_type,
        confidence=analysis.confidence,
        true_sentiment=truth.true_sentiment,
        true_disposition=truth.true_disposition,
        true_upsell_fit=truth.true_upsell_fit,
        sentiment_correct=(analysis.sentiment == truth.true_sentiment),
        disposition_bucket_correct=(pred_disp == truth.true_disposition),
        upsell_correct=(analysis.upsell_type == truth.true_upsell_fit),
        was_escalated=(routing.decision == "escalate"),
    )
