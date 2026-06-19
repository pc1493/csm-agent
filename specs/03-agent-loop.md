Task: 03 — Agent Loop (LLM wiring + five agents)

Context
The orchestrator (pipeline/orchestrator.py) already calls the five agents in sequence and
hands results to the reliability layer. Each agent module is written to call
`agents.llm.complete_json(system, user, Schema, fallback=...)`, which validates the model's
JSON against a Pydantic schema and retries on failure. The only genuinely unimplemented
code is the actual model call inside agents/llm.py. After that, your work is verifying and
tuning each agent's behavior against its prompt. This is the heart of the deliverable.

Required reading
@CLAUDE.md
@METHODOLOGY.md
@DECISIONS.md  (#001 framework-free, #003 confidence threshold, #006 single-model)
@specs/04-reliability-eval.md  (why analysis must never see ground truth)
prompts/*.md  (each agent's behavior contract)

Inputs
pipeline/models.py            — every input/output type.
prompts/{router,outreach,persona,analysis,next_best_action}.md — the agent instructions.
data/accounts.json, data/ground_truth.json — produced by data_gen.

Goal
Each agent reliably returns a valid, sensible instance of its output model, and the full
loop runs over all 20 accounts without an unhandled exception.

Steps
1. agents/llm.py — implement `_client()` and `_raw_complete(system, user)` against the
   Anthropic messages API (model = MODEL constant = "claude-sonnet-4-6", max_tokens 1024,
   `system=` for the prompt, single user message). Leave `complete_json` and `_extract_json`
   as-is; they encode the retry/fallback contract.
2. Smoke-test ONE agent in isolation (router) on one account; confirm valid JSON parses.
3. Walk the rest: outreach reads strategy+questions; persona receives ground truth and must
   produce oblique, human replies (verify a churn persona does NOT say "I will churn");
   analysis receives ONLY reply text + usage tier (assert no ground-truth field is in its
   prompt) and returns calibrated confidence; next_best_action returns a dollar figure
   anchored on real ARR.
4. Run the full orchestrator. Inspect 3–4 accounts by hand against their replies.
5. If any agent systematically misbehaves, fix the PROMPT first, code second.

Output
Modified: agents/llm.py (two functions). Possibly minor prompt edits in prompts/*.md.
No new files. No new dependencies beyond `anthropic`.

Acceptance criteria
[ ] One isolated agent call returns a valid model instance.
[ ] analysis.py's constructed user message contains no ground-truth fields (manual check).
[ ] A known-churn account (e.g. ACME-015) yields a reply that reads churn-y without stating it.
[ ] Full orchestrator run completes 20/20 accounts.
[ ] Fallbacks trigger gracefully if the model returns junk (test by temporarily breaking JSON).
[ ] Verification: re-read this spec's acceptance list before commit.

Out of scope
Do not change pipeline/models.py field names to suit a prompt — change the prompt.
Do not add per-agent retry logic; retry lives only in complete_json.
Do not introduce streaming, async, or batching — clarity over cleverness for the demo.
Do not route any agent to a different model yet; single-model is decision #006.
