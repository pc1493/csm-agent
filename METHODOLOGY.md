# Methodology

How this project is built. Modeled on the author's spec-driven workflow. Claude Code:
follow this exactly. It exists to keep a fast, cheap model on rails.

## 1. Specs are contracts
Every unit of work has a spec in `specs/` written before code. The spec names inputs,
outputs, steps, acceptance criteria, and — importantly — **what is out of scope**. Do not
"helpfully" add things the spec excludes. If a spec is wrong or incomplete, say so and
propose an edit; don't silently improvise around it.

## 2. The schema is sacred
`pipeline/models.py` is the single source of truth for data shapes. If you believe a field
must change, do not change it locally — grep every reference (`specs/`, `prompts/`,
`pipeline/`, `agents/`, `app/`), update all of them, and record the change in DECISIONS.

## 3. Prompt first, code second
When an agent misbehaves, the fix is almost always in its `prompts/*.md` file, not in Python.
Tune the instruction before adding code-side patches.

## 4. One mechanism per concern
- All model calls go through `agents/llm.py::complete_json`. No ad-hoc client calls.
- All retry/validation lives in `complete_json`. Don't sprinkle retries into agents.
- All escalation/exception logic lives in `agents/reliability.py`. Agents don't decide
  routing; they produce signals.

## 5. Decisions are logged, not buried
Architectural choices (thresholds, schema, model routing, scope cuts) go in `DECISIONS.md`
as append-only numbered entries with a rationale. The *why* is the deliverable — the grading
is about judgment, so make the judgment legible.

## 6. Verify before you commit
Before declaring a task done, re-read its acceptance criteria and check each box for real
(run the command, inspect the output). The definition of done is "the acceptance criteria
pass," not "the code looks right."

## 7. Keep it demo-legible
This is presented live to a panel that values critical thinking over cleverness. Prefer
boring, readable, debuggable code over abstractions. No async, no frameworks, no metaprogramming
unless a spec asks for it. If you can't explain a line on a projector in one sentence, simplify it.

## 8. Stay in the prototype's lane
Out of scope is out of scope (real CRM, email sending, auth, multi-user, dbt, agent
frameworks). If something feels missing for production, note it in DECISIONS as a "production
follow-up," don't build it.
