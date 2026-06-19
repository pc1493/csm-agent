"""
Smoke tests that run WITHOUT an API key — they exercise the deterministic layers
(data generation + reliability routing + eval scoring). Claude Code should keep these
green and add agent-level tests once the LLM is wired.

    pytest
"""

from datetime import date

from agents import reliability
from pipeline import data_gen
from pipeline.models import (
    Account, AnalysisResult, CustomerReply, GroundTruth, NextBestAction,
)


def _account(arr=10000.0, tier="low"):
    return Account(
        account_id="TEST-001", account_name="Test Co", industry="Retail", arr_usd=arr,
        usage_tier=tier, seats_licensed=10, seats_active=3, bots_in_production=1,
        runs_last_30d=20, contract_term_months=12, renewal_date=date.today(),
        days_to_renewal=30, csm_owner="Digital", contact_name="A B",
        contact_email="a.b@example.com", last_qbr_days_ago=180, open_support_tickets=1,
    )


def test_data_gen_is_deterministic_and_complete():
    a1, g1 = data_gen.generate()
    a2, g2 = data_gen.generate()
    assert len(a1) == data_gen.N_ACCOUNTS
    assert [a.account_id for a in a1] == [a.account_id for a in a2]  # seeded
    assert all(a.arr_usd < 20000 for a in a1)
    assert any(g.will_bounce for g in g1)
    assert any(g.will_opt_out for g in g1)
    assert any(g.responsiveness == "silent" for g in g1)


def test_bounce_routes_to_data_hygiene():
    out = reliability.route(_account(), CustomerReply(replied=False, bounced=True), None, None)
    assert out.decision == "escalate" and out.queue == "data_hygiene" and "E1" in out.exception_codes


def test_no_reply_routes_to_manual_outreach():
    out = reliability.route(_account(), CustomerReply(replied=False), None, None)
    assert out.queue == "manual_outreach" and "E3" in out.exception_codes


def test_detractor_routes_to_save_call():
    an = AnalysisResult(sentiment="negative", renewal_likelihood=0.2, reasons=["price"],
                        product_feedback=[], upsell_signal=False, upsell_type="none", confidence=0.9)
    out = reliability.route(_account(), CustomerReply(replied=True, body="..."), an, None)
    assert out.queue == "save_call" and "E4" in out.exception_codes


def test_smart_threshold_escalates_despite_low_arr():
    an = AnalysisResult(sentiment="positive", renewal_likelihood=0.9, reasons=["loves it"],
                        product_feedback=[], upsell_signal=True, upsell_type="professional_services",
                        confidence=0.9)
    nba = NextBestAction(action="intro pro services", play="pro_services_intro", priority="high",
                         estimated_value_usd=8000.0, talking_points=["scale to 3 teams"])
    out = reliability.route(_account(arr=6000.0), CustomerReply(replied=True, body="..."), an, nba)
    assert out.queue == "ae_upsell" and "E7" in out.exception_codes


def test_low_confidence_never_auto_handles():
    an = AnalysisResult(sentiment="neutral", renewal_likelihood=0.6, reasons=["vague"],
                        product_feedback=[], upsell_signal=False, upsell_type="none", confidence=0.4)
    out = reliability.route(_account(), CustomerReply(replied=True, body="..."), an, None)
    assert out.decision == "escalate" and "E5" in out.exception_codes


def test_clean_confident_auto_handles():
    an = AnalysisResult(sentiment="positive", renewal_likelihood=0.85, reasons=["happy"],
                        product_feedback=[], upsell_signal=False, upsell_type="none", confidence=0.9)
    out = reliability.route(_account(), CustomerReply(replied=True, body="..."), an, None)
    assert out.decision == "auto" and out.queue == "none" and out.exception_codes == []


def test_eval_scores_against_truth():
    an = AnalysisResult(sentiment="negative", renewal_likelihood=0.2, reasons=[], product_feedback=[],
                        upsell_signal=False, upsell_type="none", confidence=0.9)
    truth = GroundTruth(account_id="TEST-001", true_disposition="will_churn",
                        true_sentiment="negative", true_reason="price", true_upsell_fit="none",
                        responsiveness="responsive")
    rec = reliability.score(truth, an, reliability.route(_account(), CustomerReply(replied=True, body="x"), an, None))
    assert rec.sentiment_correct is True
    assert rec.disposition_bucket_correct is True  # 0.2 -> will_churn
