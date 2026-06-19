"""
Analysis agent: reply text ONLY -> structured signals + self-reported confidence.

Spec: specs/03-agent-loop.md (Analysis). Prompt: prompts/analysis.md.

HARD RULE: this function must NEVER receive a GroundTruth. It sees the reply body and
(optionally) non-leaking usage context. Everything it returns is later scored against
the hidden truth — if truth leaked in, the accuracy number would be a lie.

Confidence must be honest: ambiguous/short replies -> lower confidence. The reliability
layer uses that number to decide auto vs. escalate, so a miscalibrated confidence is a
real bug, not a cosmetic one.
"""

from __future__ import annotations

from agents import load_prompt
from agents.llm import complete_json
from pipeline.models import AnalysisResult, CustomerReply


def analyze(reply: CustomerReply, usage_tier: str) -> AnalysisResult | None:
    if not reply.replied or not reply.body:
        return None  # nothing to analyze; no-response path handled in orchestrator

    system = load_prompt("analysis")
    user = (
        f"Customer reply to analyze:\n\"\"\"\n{reply.body}\n\"\"\"\n\n"
        f"Non-leaking context: product usage tier is '{usage_tier}'.\n\n"
        f"Return an AnalysisResult as JSON. Lower your confidence if the reply is short, "
        f"ambiguous, or mixed-signal."
    )
    fallback = AnalysisResult(
        sentiment="neutral", renewal_likelihood=0.5, reasons=["unparseable analysis"],
        product_feedback=[], upsell_signal=False, upsell_type="none", confidence=0.0,
    )
    out, ok = complete_json(system, user, AnalysisResult, fallback=fallback)
    if not ok:
        out.confidence = 0.0  # force escalation on fallback (E8)
    return out
