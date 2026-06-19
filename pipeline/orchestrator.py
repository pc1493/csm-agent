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
import sys
import time
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


def demo_account(account: Account, truth: GroundTruth) -> None:
    """Verbose, live, single-account run for the demo. Prints every stage as it happens
    with per-call latency, and writes NOTHING to the database. The visible pause at each
    stage is real model latency — that is the proof the agent is running live, not replaying
    a cached result. Use via:  python -m pipeline.orchestrator --account ACME-013 --demo
    """
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # robust to any glyph the model emits
    except Exception:
        pass

    def stage(label, fn):
        print(f"\n-> {label} ...", end="", flush=True)   # printed BEFORE the call so the pause is visible
        t0 = time.perf_counter()
        out = fn()
        print(f"  [{time.perf_counter() - t0:.1f}s]", flush=True)
        return out

    def block(text):
        for line in (text or "").splitlines():
            print(f"      {line}")

    bar = "=" * 72
    print(f"\n{bar}")
    print(f"  LIVE AGENT RUN   {account.account_id}   {account.account_name}")
    print(f"  {account.usage_tier} usage | ${account.arr_usd:,.0f} ARR | renews in "
          f"{account.days_to_renewal} days | {account.open_support_tickets} open ticket(s)")
    print(bar, flush=True)

    decision = stage("ROUTER       segment + pick strategy", lambda: router_agent.route(account))
    print(f"      strategy = {decision.strategy.upper()}")
    print(f"      {decision.rationale}")

    outreach = stage("OUTREACH     draft the email", lambda: outreach_agent.draft(account, decision))
    print(f"      Subject: {outreach.subject}")
    block(outreach.body)

    reply = stage("CUSTOMER     reply (persona seeded with HIDDEN truth)",
                  lambda: persona_agent.reply(account, truth, outreach))
    if reply.bounced:
        print("      [email bounced - contact is dead]")
    elif reply.opted_out:
        print("      [customer opted out - suppress]")
    elif not reply.replied:
        print("      [no reply - silent]")
    else:
        block(reply.body)

    analysis = nba = None
    if reply.replied and reply.body:
        analysis = stage("ANALYSIS     read the reply (NO ground truth)",
                         lambda: analysis_agent.analyze(reply, account.usage_tier))
        print(f"      sentiment = {analysis.sentiment} | renewal likelihood = "
              f"{analysis.renewal_likelihood:.2f} | confidence = {analysis.confidence:.2f}")
        print(f"      upsell = {analysis.upsell_type} "
              f"({'signal detected' if analysis.upsell_signal else 'none'})")
        if analysis.product_feedback:
            print(f"      feedback: {'; '.join(analysis.product_feedback)}")
        nba = stage("NEXT ACTION  recommend the play + $ value",
                    lambda: nba_agent.recommend(account, analysis, decision.strategy))
        print(f"      {nba.action}")
        print(f"      ${nba.estimated_value_usd:,.0f} at stake | {nba.priority} priority")

    routing = reliability.route(account, reply, analysis, nba)
    print("\n-> RELIABILITY GATE   (deterministic - no model call, auditable)")
    verdict = "AUTO-HANDLE" if routing.decision == "auto" else f"ESCALATE -> {routing.queue}"
    codes = f" | codes {','.join(routing.exception_codes)}" if routing.exception_codes else ""
    print(f"      ==> {verdict}   (confidence {routing.confidence:.2f}{codes})")
    for r in routing.reasons:
        print(f"          - {r}")

    eval_rec = reliability.score(truth, analysis, routing)
    print(f"\n{'-' * 72}")
    print("  SCORED vs HIDDEN ground truth (the analysis agent never saw this):")
    if analysis is not None:
        dc = "MATCH" if eval_rec.disposition_bucket_correct else "MISS"
        sc = "MATCH" if eval_rec.sentiment_correct else "MISS"
        print(f"      renewal call : predicted ~{analysis.renewal_likelihood:.2f} "
              f"vs true '{truth.true_disposition}'   [{dc}]")
        print(f"      sentiment    : predicted '{analysis.sentiment}' "
              f"vs true '{truth.true_sentiment}'   [{sc}]")
        print("      (renewal call drives routing + $; sentiment is the softer, noisier signal)")
    else:
        print("      no reply to score - routed on the exception alone")
    print("-" * 72)
    print("  demo mode: database left untouched\n", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", default=None, help="Process a single account_id.")
    ap.add_argument("--demo", action="store_true",
                    help="Verbose live trace of one account; writes NOTHING to the DB. "
                         "Use with --account, e.g. --account ACME-013 --demo.")
    args = ap.parse_args()
    if args.demo:
        if not args.account:
            raise SystemExit("--demo needs an account, e.g.  --account ACME-013 --demo")
        accounts, truths = load_inputs()
        match = [a for a in accounts if a.account_id == args.account]
        if not match:
            raise SystemExit(f"No account {args.account}")
        demo_account(match[0], truths[args.account])
    else:
        run(args.account)
