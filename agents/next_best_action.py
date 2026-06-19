"""
Next-best-action agent: analysis + account -> recommended play + $ estimate + talking points.

Spec: specs/03-agent-loop.md (NBA). Prompt: prompts/next_best_action.md.

estimated_value_usd is what makes the report actionable and sortable:
  - churn risk  -> ARR at risk (account.arr_usd weighted by 1 - renewal_likelihood)
  - upsell      -> a surfaced expansion estimate
This dollar figure feeds prioritization in the report and the E7 smart-threshold rule.
"""

from __future__ import annotations

from agents import load_prompt
from agents.llm import complete_json
from pipeline.models import Account, AnalysisResult, NextBestAction


def recommend(account: Account, analysis: AnalysisResult, strategy: str) -> NextBestAction:
    system = load_prompt("next_best_action")
    user = (
        f"Account (JSON):\n{account.model_dump_json(indent=2)}\n\n"
        f"Strategy: {strategy}\n"
        f"Analysis (JSON):\n{analysis.model_dump_json(indent=2)}\n\n"
        f"Return a NextBestAction as JSON. estimated_value_usd should reflect ARR at risk "
        f"for churn cases or a reasonable expansion figure for upsell cases."
    )
    fallback = NextBestAction(
        action="Manual CSM review required.", play="human_review", priority="medium",
        estimated_value_usd=account.arr_usd, talking_points=["Model output invalid; review reply directly."],
    )
    out, _ok = complete_json(system, user, NextBestAction, fallback=fallback)
    return out
