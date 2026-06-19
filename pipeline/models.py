"""
Canonical data contracts for the Low-ARR Renewal Agent.

This module is THE schema. Specs, prompts, the orchestrator, the DuckDB schema,
and the Streamlit app all use these exact field names. If you (Claude Code) change
a field here, grep the repo and update every reference, then add a DECISIONS entry.

Design note for the eval layer:
  - `Account` holds only fields the agents are ALLOWED to see.
  - `GroundTruth` holds the hidden truth used ONLY to (a) generate the simulated
    customer reply and (b) score the analysis agent afterward. The analysis agent
    must NEVER receive a GroundTruth. This separation is what makes the accuracy
    number meaningful — see specs/04-reliability-eval.md.
"""

from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums (as Literals so they show up inline in every signature)
# ---------------------------------------------------------------------------
UsageTier = Literal["high", "average", "low"]
Strategy = Literal["save", "nurture", "upsell", "standard_renewal"]
Sentiment = Literal["positive", "neutral", "negative"]
Disposition = Literal["will_renew", "at_risk", "will_churn"]
UpsellType = Literal["none", "ai_agent_studio", "professional_services"]
Responsiveness = Literal["responsive", "slow", "silent"]
Priority = Literal["low", "medium", "high", "urgent"]
Decision = Literal["auto", "escalate"]
Queue = Literal[
    "none",
    "save_call",
    "ae_upsell",
    "data_hygiene",
    "manual_outreach",
    "human_review",
]


# ---------------------------------------------------------------------------
# Input: the Salesforce-shaped account (VISIBLE to agents)
# ---------------------------------------------------------------------------
class Account(BaseModel):
    account_id: str
    account_name: str
    industry: str
    arr_usd: float = Field(description="Annual recurring revenue. All < 20000 for this use case.")
    usage_tier: UsageTier
    seats_licensed: int
    seats_active: int
    bots_in_production: int
    runs_last_30d: int = Field(description="Automation Success Platform runs in the last 30 days.")
    contract_term_months: int
    renewal_date: date
    days_to_renewal: int
    csm_owner: str
    contact_name: str
    contact_email: str
    last_qbr_days_ago: int = Field(description="Days since last QBR / business review. High = neglected.")
    open_support_tickets: int


# ---------------------------------------------------------------------------
# Hidden ground truth (NEVER passed to the analysis agent)
# ---------------------------------------------------------------------------
class GroundTruth(BaseModel):
    account_id: str
    true_disposition: Disposition
    true_sentiment: Sentiment
    true_reason: str = Field(description="The real driver. Used to author a realistic reply.")
    true_upsell_fit: UpsellType
    responsiveness: Responsiveness
    will_bounce: bool = Field(default=False, description="Contact email is dead -> bounce exception.")
    will_opt_out: bool = Field(default=False, description="Customer asks to stop contact -> suppress.")


# ---------------------------------------------------------------------------
# Agent outputs (each is a strict contract; agents must return valid instances)
# ---------------------------------------------------------------------------
class RouterDecision(BaseModel):
    strategy: Strategy
    rationale: str
    questions: list[str] = Field(
        description="3-5 questions covering the 3 business dimensions: renewal likelihood, "
        "product feedback, upsell/pro-services interest. Phrasing adapts to strategy."
    )


class OutreachDraft(BaseModel):
    subject: str
    body: str
    dimensions_covered: list[Literal["renewal", "feedback", "upsell"]]


class CustomerReply(BaseModel):
    replied: bool
    body: Optional[str] = None
    bounced: bool = False
    opted_out: bool = False


class AnalysisResult(BaseModel):
    sentiment: Sentiment
    renewal_likelihood: float = Field(ge=0.0, le=1.0)
    reasons: list[str]
    product_feedback: list[str]
    upsell_signal: bool
    upsell_type: UpsellType
    confidence: float = Field(ge=0.0, le=1.0, description="Agent's own confidence in this analysis.")


class NextBestAction(BaseModel):
    action: str = Field(description="One-line recommended action for the CSM/AE.")
    play: str = Field(description="Named play, e.g. 'save_call', 'auto_confirm_renewal', 'send_ai_studio_brief'.")
    priority: Priority
    estimated_value_usd: float = Field(
        description="ARR at risk (churn) or upsell $ surfaced. Drives prioritization."
    )
    talking_points: list[str]


class RoutingOutcome(BaseModel):
    """Output of the reliability layer — the differentiator."""
    decision: Decision
    queue: Queue
    reasons: list[str]
    exception_codes: list[str] = Field(
        default_factory=list,
        description="Subset of E1..E8 from specs/04. Empty if clean auto-handle.",
    )
    confidence: float = Field(ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Assembled per-account result (one row in the report / DuckDB)
# ---------------------------------------------------------------------------
class AccountResult(BaseModel):
    account: Account
    strategy: Strategy
    reply: CustomerReply
    analysis: Optional[AnalysisResult]  # None if no reply / bounced
    next_best_action: Optional[NextBestAction]
    routing: RoutingOutcome


# ---------------------------------------------------------------------------
# Eval record (analysis prediction vs hidden ground truth)
# ---------------------------------------------------------------------------
class EvalRecord(BaseModel):
    account_id: str
    # predictions
    pred_sentiment: Optional[Sentiment]
    pred_renewal_likelihood: Optional[float]
    pred_upsell_type: Optional[UpsellType]
    confidence: Optional[float]
    # truth
    true_sentiment: Sentiment
    true_disposition: Disposition
    true_upsell_fit: UpsellType
    # derived correctness
    sentiment_correct: Optional[bool]
    disposition_bucket_correct: Optional[bool]  # likelihood bucket vs disposition
    upsell_correct: Optional[bool]
    was_escalated: bool
