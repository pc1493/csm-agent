# Claude Code — Kickoff Prompt

Paste the block below as your FIRST message to Claude Code in this repo. It orients the model,
sets the build order, and fences the scope. After it runs spec 00 → 03, drive the rest spec by
spec ("now do specs/04 verification", "now specs/05").

---

```
You're implementing a 2-day take-home prototype. The architecture, schema, prompts, and the
orchestrator/reliability logic are already written. Your job is implementation + verification
on a tight scope — do NOT redesign anything or add features beyond the specs.

First, read these in order and then summarize back to me your understanding and your plan
before writing any code:
  1. CLAUDE.md
  2. METHODOLOGY.md
  3. DECISIONS.md
  4. specs/00-overview.md   (the build-order map + status of every file)
  5. specs/03-agent-loop.md (your first real task)

Key facts:
- pipeline/models.py is the canonical schema. Do not change field names without grepping the
  whole repo and adding a DECISIONS entry.
- The only genuinely unimplemented code is two functions in agents/llm.py (the Anthropic
  client + the messages call). Everything else is either done or one TODO away.
- All model calls go through agents/llm.py::complete_json. Retry/validation lives only there.
- The analysis agent must NEVER receive ground truth — verify this; it's what makes the
  accuracy number honest.
- Fix prompts (prompts/*.md) before code. Prefer boring, projector-legible Python. No async,
  no agent framework, no dbt. These are deliberate decisions, not omissions.

Verification gate: confirm data_gen runs first (python -m pipeline.data_gen). Then implement
spec 03, smoke-test one agent in isolation, then run the full orchestrator
(python -m pipeline.orchestrator) and show me 3-4 accounts by hand before moving on.

Start by reading the files and giving me your plan. Don't write code yet.
```

---

## Build sequence after kickoff
1. **spec 03** — wire `agents/llm.py`, verify each agent, run the full loop. This is the bulk.
2. **spec 04** — verify the reliability routing on the injected edge cases; confirm the eval
   numbers populate. Mostly checking, little coding.
3. **spec 05** — surface the outreach/reply in the dashboard, optional visual polish.
4. **docs review** — read `docs/apa_flow.md`, `docs/value_kpis.md`,
   `docs/presentation-outline.md`; make the wording yours so you can present it cold.

## A note on cost discipline
Keep Sonnet doing the implementation. When you need to rethink design — a new exception
type, a different KPI framing, a tradeoff to defend — bring that back to Opus rather than having
Sonnet improvise architecture. Sonnet executes specs; Opus writes them.
