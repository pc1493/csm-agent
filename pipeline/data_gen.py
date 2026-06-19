"""
Synthetic Salesforce-shaped accounts for the Low-ARR Renewal Agent.

FULLY IMPLEMENTED AND RUNNABLE — no LLM, deterministic via SEED. Claude Code should
NOT need to rewrite this; use it as the data source. Run it first to confirm the data
layer before implementing any agent:

    python -m pipeline.data_gen        # writes data/accounts.json + data/ground_truth.json

Design intent:
  - usage_tier correlates with disposition/sentiment but NOT perfectly. The noise is
    the point: if low-usage always meant churn, the analysis agent would be trivial and
    the accuracy number would be meaningless. Real accounts surprise you.
  - A handful of edge cases are injected on purpose to exercise exception handling:
    one bounce, one opt-out, one silent responder, and one "happy but low ARR with a
    real upsell signal" (the smart-threshold case E7).
"""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

from pipeline.models import Account, GroundTruth

SEED = 42
N_ACCOUNTS = 20
DATA_DIR = Path("data")

INDUSTRIES = [
    "Insurance", "Healthcare", "Logistics", "Retail", "Manufacturing",
    "Banking", "Telecom", "Utilities", "Public Sector", "Hospitality",
]
FIRST = ["Priya", "Marcus", "Elena", "David", "Sofia", "James", "Aisha", "Chen", "Liam", "Nadia"]
LAST = ["Okafor", "Reyes", "Novak", "Patel", "Lindqvist", "Tanaka", "Mbeki", "Costa", "Haddad", "Walsh"]

# disposition/sentiment priors per usage tier (probabilities sum to 1)
DISPOSITION_PRIORS = {
    "high":    {"will_renew": 0.70, "at_risk": 0.22, "will_churn": 0.08},
    "average": {"will_renew": 0.45, "at_risk": 0.38, "will_churn": 0.17},
    "low":     {"will_renew": 0.18, "at_risk": 0.42, "will_churn": 0.40},
}
SENTIMENT_BY_DISPOSITION = {
    "will_renew": {"positive": 0.6, "neutral": 0.35, "negative": 0.05},
    "at_risk":    {"positive": 0.2, "neutral": 0.5, "negative": 0.3},
    "will_churn": {"positive": 0.05, "neutral": 0.25, "negative": 0.7},
}
REASONS = {
    "will_renew": [
        "Seeing strong ROI on invoice-processing bots; team is happy.",
        "Embedded in daily ops; switching cost is high and value is clear.",
        "Champion is an internal advocate and wants to expand use cases.",
    ],
    "at_risk": [
        "Only one use case live; hasn't seen enough value to justify spend.",
        "Lost the original champion to a reorg; new owner is lukewarm.",
        "Budget scrutiny this cycle; needs to defend the line item.",
    ],
    "will_churn": [
        "Bots keep breaking on UI changes; maintenance burden too high.",
        "Evaluating a cheaper competitor; price is the sticking point.",
        "Sponsoring exec left; project lost air cover and usage collapsed.",
    ],
}


def _pick(rng: random.Random, dist: dict[str, float]) -> str:
    r, cum = rng.random(), 0.0
    for k, p in dist.items():
        cum += p
        if r <= cum:
            return k
    return list(dist)[-1]


def generate() -> tuple[list[Account], list[GroundTruth]]:
    rng = random.Random(SEED)
    accounts: list[Account] = []
    truths: list[GroundTruth] = []
    today = date.today()

    for i in range(N_ACCOUNTS):
        tier = rng.choices(["high", "average", "low"], weights=[0.3, 0.4, 0.3])[0]
        disposition = _pick(rng, DISPOSITION_PRIORS[tier])
        sentiment = _pick(rng, SENTIMENT_BY_DISPOSITION[disposition])
        upsell_fit = rng.choices(
            ["none", "ai_agent_studio", "professional_services"],
            weights=[0.55, 0.25, 0.20],
        )[0]

        seats_lic = rng.choice([5, 10, 15, 25, 50])
        # active-seat ratio tracks usage tier with noise
        ratio = {"high": 0.85, "average": 0.55, "low": 0.25}[tier] + rng.uniform(-0.12, 0.12)
        seats_active = max(1, min(seats_lic, round(seats_lic * ratio)))
        runs = {"high": rng.randint(800, 4000), "average": rng.randint(150, 800),
                "low": rng.randint(0, 150)}[tier]
        bots = {"high": rng.randint(4, 12), "average": rng.randint(2, 5),
                "low": rng.randint(0, 2)}[tier]

        arr = round(rng.uniform(4000, 19500), -2)
        term = rng.choice([12, 12, 24, 36])
        days_to_renewal = rng.choice([14, 21, 30, 45, 60, 75, 90])
        renewal = today + timedelta(days=days_to_renewal)
        contact = f"{rng.choice(FIRST)} {rng.choice(LAST)}"

        accounts.append(Account(
            account_id=f"ACME-{i+1:03d}",
            account_name=f"{rng.choice(INDUSTRIES)} Co {i+1}",
            industry=rng.choice(INDUSTRIES),
            arr_usd=arr,
            usage_tier=tier,
            seats_licensed=seats_lic,
            seats_active=seats_active,
            bots_in_production=bots,
            runs_last_30d=runs,
            contract_term_months=term,
            renewal_date=renewal,
            days_to_renewal=days_to_renewal,
            csm_owner="Pooled / Digital CSM",
            contact_name=contact,
            contact_email=f"{contact.split()[0].lower()}.{contact.split()[1].lower()}@example.com",
            last_qbr_days_ago=rng.choice([30, 60, 90, 120, 180, 365]),
            open_support_tickets=rng.randint(0, 4),
        ))
        truths.append(GroundTruth(
            account_id=f"ACME-{i+1:03d}",
            true_disposition=disposition,
            true_sentiment=sentiment,
            true_reason=rng.choice(REASONS[disposition]),
            true_upsell_fit=upsell_fit,
            responsiveness=rng.choices(["responsive", "slow", "silent"], weights=[0.6, 0.25, 0.15])[0],
        ))

    # ---- Inject deterministic edge cases (exercise exception handling) ----
    # E1 bounce
    truths[2].will_bounce = True
    # E2 opt-out
    truths[5].will_opt_out = True
    truths[5].true_sentiment = "negative"
    # E3 silent (no response after touches)
    truths[8].responsiveness = "silent"
    # E7 smart-threshold: tiny ARR, happy, but a genuine professional_services upsell
    accounts[11].arr_usd = 6000.0
    truths[11].true_disposition = "will_renew"
    truths[11].true_sentiment = "positive"
    truths[11].true_upsell_fit = "professional_services"
    truths[11].true_reason = (
        "Loves the product and wants help scaling to 3 new departments next quarter."
    )
    truths[11].responsiveness = "responsive"  # must reply or E7 never fires
    # E4/E6 conflicting: positive-sounding but actually churning on price
    truths[14].true_disposition = "will_churn"
    truths[14].true_sentiment = "neutral"
    truths[14].true_reason = "Polite but quietly evaluating a cheaper competitor; price is decisive."

    return accounts, truths


def write(accounts: list[Account], truths: list[GroundTruth]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / "accounts.json").write_text(
        json.dumps([json.loads(a.model_dump_json()) for a in accounts], indent=2)
    )
    (DATA_DIR / "ground_truth.json").write_text(
        json.dumps([json.loads(g.model_dump_json()) for g in truths], indent=2)
    )


if __name__ == "__main__":
    accts, gts = generate()
    write(accts, gts)
    tiers = {t: sum(1 for a in accts if a.usage_tier == t) for t in ("high", "average", "low")}
    disp = {d: sum(1 for g in gts if g.true_disposition == d) for d in ("will_renew", "at_risk", "will_churn")}
    print(f"Wrote {len(accts)} accounts to data/accounts.json")
    print(f"  usage tiers : {tiers}")
    print(f"  disposition : {disp}")
    print(f"  edge cases  : 1 bounce, 1 opt-out, 1 silent, 1 smart-threshold upsell, 1 hidden churn")
