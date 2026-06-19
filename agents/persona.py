"""
Persona agent (simulated customer): account + GROUND TRUTH + outreach -> realistic reply.

Spec: specs/03-agent-loop.md (Persona) and specs/04 (why this is honest). Prompt:
prompts/persona.md.

This is the ONLY component that receives GroundTruth to generate text. It role-plays
the customer so the loop is self-contained. Responsiveness/bounce/opt-out are handled
here BEFORE any model call — a silent customer produces no text to analyze, which is
what triggers the no-response exception downstream.

The reply must NOT state its disposition outright ("I will churn"). It expresses the
true sentiment/reason the way a busy human would — sometimes obliquely. That obliqueness
is what the analysis agent has to see through, and what the eval then scores.
"""

from __future__ import annotations

from agents import load_prompt
from agents.llm import complete_json
from pipeline.models import Account, CustomerReply, GroundTruth, OutreachDraft


def reply(account: Account, truth: GroundTruth, outreach: OutreachDraft) -> CustomerReply:
    # Deterministic non-responses happen without a model call.
    if truth.will_bounce:
        return CustomerReply(replied=False, bounced=True)
    if truth.responsiveness == "silent":
        return CustomerReply(replied=False)
    if truth.will_opt_out:
        return CustomerReply(
            replied=True,
            opted_out=True,
            body="Please remove me from these emails. We're not interested in continuing right now.",
        )

    system = load_prompt("persona")
    user = (
        f"You are this customer. Hidden truth about you (do NOT quote it verbatim):\n"
        f"{truth.model_dump_json(indent=2)}\n\n"
        f"Account facts you'd plausibly know:\n{account.model_dump_json(indent=2)}\n\n"
        f"The CSM emailed you:\nSubject: {outreach.subject}\n{outreach.body}\n\n"
        f"Write your email reply as JSON: {{\"replied\": true, \"body\": \"...\"}}. "
        f"Be human and busy; express your real sentiment without naming it."
    )
    fallback = CustomerReply(replied=True, body="Thanks, will review and get back to you.")
    out, _ok = complete_json(system, user, CustomerReply, fallback=fallback)
    return out
