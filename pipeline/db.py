"""
DuckDB persistence layer. Mostly complete — Claude Code should only need to wire the
`load_results` mapping if AccountResult field names change.

    from pipeline import db
    con = db.connect()            # opens data/renewal.duckdb, applies schema.sql
    db.load_results(con, results) # writes account_results + exceptions_queue
    db.load_eval(con, eval_records)
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from pipeline.models import AccountResult, EvalRecord, OutreachDraft

DB_PATH = Path("data/renewal.duckdb")
SCHEMA = Path("pipeline/schema.sql")


def connect(path: Path = DB_PATH) -> duckdb.DuckDBPyConnection:
    path.parent.mkdir(exist_ok=True)
    con = duckdb.connect(str(path))
    con.execute(SCHEMA.read_text())
    return con


def reset(con: duckdb.DuckDBPyConnection) -> None:
    for t in ("account_results", "exceptions_queue", "eval_metrics"):
        con.execute(f"DROP TABLE IF EXISTS {t}")
    con.execute(SCHEMA.read_text())


def load_results(
    con: duckdb.DuckDBPyConnection,
    results: list[AccountResult],
    outreaches: list[OutreachDraft],
) -> None:
    reset(con)
    for r, o in zip(results, outreaches):
        a, an, nba, rt = r.account, r.analysis, r.next_best_action, r.routing
        con.execute(
            """INSERT INTO account_results VALUES
               (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [
                a.account_id, a.account_name, a.industry, a.arr_usd, a.usage_tier,
                a.days_to_renewal, r.strategy, r.reply.replied,
                an.sentiment if an else None,
                an.renewal_likelihood if an else None,
                an.upsell_signal if an else False,
                an.upsell_type if an else "none",
                nba.action if nba else None,
                nba.play if nba else None,
                nba.priority if nba else None,
                nba.estimated_value_usd if nba else 0.0,
                rt.decision, rt.queue, rt.confidence,
                ",".join(rt.exception_codes),
                o.subject,
                o.body,
                r.reply.body,
            ],
        )
        for code in rt.exception_codes:
            con.execute(
                "INSERT INTO exceptions_queue VALUES (?,?,?,?)",
                [a.account_id, code, rt.queue, "; ".join(rt.reasons)],
            )


def load_eval(con: duckdb.DuckDBPyConnection, records: list[EvalRecord]) -> None:
    for e in records:
        con.execute(
            "INSERT OR REPLACE INTO eval_metrics VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                e.account_id, e.pred_sentiment, e.true_sentiment, e.sentiment_correct,
                e.pred_renewal_likelihood, e.true_disposition, e.disposition_bucket_correct,
                e.pred_upsell_type, e.true_upsell_fit, e.upsell_correct,
                e.confidence, e.was_escalated,
            ],
        )
