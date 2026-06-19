"""
Router agent: account -> engagement strategy + adapted questions.

Spec: specs/03-agent-loop.md (Router section). Prompt: prompts/router.md.

The strategy mapping is deliberate BA logic, not vibes:
  low usage  + renewal soon  -> save
  high usage + renewal soon  -> upsell
  average                    -> nurture
  healthy + far renewal      -> standard_renewal
The model personalizes the question phrasing per strategy but the 3 dimensions
(renewal, feedback, upsell) must always be covered.
"""

from __future__ import annotations

from agents import load_prompt
from agents.llm import complete_json
from pipeline.models import Account, RouterDecision


def route(account: Account) -> RouterDecision:
    system = load_prompt("router")
    user = (
        f"Account context (JSON):\n{account.model_dump_json(indent=2)}\n\n"
        f"Return a RouterDecision as JSON."
    )
    # Fallback keeps the loop alive if the model misbehaves (E8 handled upstream).
    fallback = RouterDecision(
        strategy="nurture",
        rationale="Fallback: model output invalid; defaulting to nurture for safe review.",
        questions=[
            "How has your experience with the Automation Success Platform been recently?",
            "Are there features or use cases you'd like to see supported?",
            "Would support scaling automation across more teams be useful this year?",
        ],
    )
    decision, _ok = complete_json(system, user, RouterDecision, fallback=fallback)
    return decision
