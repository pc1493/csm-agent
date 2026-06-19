"""
Orchestrator: the closed renewal loop.

    python -m pipeline.orchestrator            # runs the full batch, writes DuckDB + report
    python -m pipeline.orchestrator --account ACME-012   # single account (for the live demo)

Per account:
    route -> draft outreach -> simulate reply -> analyze -> next best action
          -> reliability.route (auto/escalate) -> reliability.score (vs ground truth)
          -> persist

Control flow is COMPLETE. Claude Code's job is to make the agent bodies real (see
agents/llm.py TODOs); this file should not need structural changes.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agents import analysis as analysis_agent
from agents import next_best_action as nba_agent
from agents import outreach as outreach_agent
from agents import persona as persona_agent
from agents import reliability
from agents import router as router_agent
from pipeline import db
from pipeline.models import Account, AccountResult, EvalRecord, GroundTruth, OutreachDraft

DATA = Path("data")


def load_inputs() -> tuple[list[Account], dict[str, GroundTruth]]:
    if not (DATA / "accounts.json").exists():
        from pipeline import data_gen
        data_gen.write(*data_gen.generate())
    accounts = [Account.model_validate(a) for a in json.loads((DATA / "accounts.json").read_text())]
    truths = {g["account_id"]: GroundTruth.model_validate(g)
              for g in json.loads((DATA / "ground_truth.json").read_text())}
    return accounts, truths


def process(account: Account, truth: GroundTruth) -> tuple[AccountResult, EvalRecord, OutreachDraft]:
    decision = router_agent.route(account)
    outreach = outreach_agent.draft(account, decision)
    reply = persona_agent.reply(account, truth, outreach)
    analysis = analysis_agent.analyze(reply, account.usage_tier)
    nba = nba_agent.recommend(account, analysis, decision.strategy) if analysis else None
    routing = reliability.route(account, reply, analysis, nba)
    eval_rec = reliability.score(truth, analysis, routing)
    result = AccountResult(
        account=account, strategy=decision.strategy, reply=reply,
        analysis=analysis, next_best_action=nba, routing=routing,
    )
    return result, eval_rec, outreach


def run(account_id: str | None = None) -> None:
    accounts, truths = load_inputs()
    if account_id:
        accounts = [a for a in accounts if a.account_id == account_id]
        if not accounts:
            raise SystemExit(f"No account {account_id}")

    results: list[AccountResult] = []
    evals: list[EvalRecord] = []
    outreaches: list[OutreachDraft] = []
    for a in accounts:
        print(f"  processing {a.account_id} ({a.usage_tier} usage, ${a.arr_usd:,.0f} ARR)...")
        result, ev, outreach = process(a, truths[a.account_id])
        results.append(result)
        evals.append(ev)
        outreaches.append(outreach)

    con = db.connect()
    db.load_results(con, results, outreaches)
    db.load_eval(con, evals)
    con.close()

    escalated = sum(1 for r in results if r.routing.decision == "escalate")
    scored = [e for e in evals if e.sentiment_correct is not None]
    acc = (sum(e.sentiment_correct for e in scored) / len(scored)) if scored else 0.0
    print(f"\nDone. {len(results)} accounts | {escalated} escalated | "
          f"sentiment accuracy {acc:.0%} on {len(scored)} scored replies.")
    print("Report data in data/renewal.duckdb. Run: streamlit run app/dashboard.py")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", default=None, help="Process a single account_id.")
    args = ap.parse_args()
    run(args.account)
