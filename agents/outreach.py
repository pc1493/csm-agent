"""
Outreach agent: account + strategy + questions -> drafted email.

Spec: specs/03-agent-loop.md (Outreach). Prompt: prompts/outreach.md.
The draft must read like a real digital-CSM touch (warm, concise, low-pressure) and
embed the router's questions naturally. It covers renewal + feedback + upsell.
"""

from __future__ import annotations

from agents import load_prompt
from agents.llm import complete_json
from pipeline.models import Account, OutreachDraft, RouterDecision


def draft(account: Account, decision: RouterDecision) -> OutreachDraft:
    system = load_prompt("outreach")
    user = (
        f"Account (JSON):\n{account.model_dump_json(indent=2)}\n\n"
        f"Strategy: {decision.strategy}\nRationale: {decision.rationale}\n"
        f"Questions to weave in:\n- " + "\n- ".join(decision.questions) + "\n\n"
        f"Return an OutreachDraft as JSON."
    )
    fallback = OutreachDraft(
        subject=f"Checking in on your Automation Success Platform renewal",
        body="Fallback template body — replace via review.",
        dimensions_covered=["renewal", "feedback", "upsell"],
    )
    out, _ok = complete_json(system, user, OutreachDraft, fallback=fallback)
    return out
