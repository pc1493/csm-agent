# Demo Run-Sheet — Low-ARR Renewal Agent

45 min total: **30 demo + 15 Q&A.** Hold this during the call. Companion to
`presentation-outline.md` (prose rationale); this is the operational card.

**The spine — say it early, call back to it:**
> The model is the dumbest, least reliable part of the system, so I engineer around it *twice* —
> at **build time** (specs, layered instructions, a decisions log) and at **run time** (schema
> validation, a confidence gate, a measured accuracy number). Same discipline, two layers.

---

## Pre-flight (morning of)
- [ ] **Close DBeaver** — it locks `data/renewal.duckdb` and breaks the dashboard read.
- [ ] `streamlit run app/dashboard.py` → click all 3 tabs; open drill-downs for **ACME-004 / ACME-019 / ACME-012**; confirm the emails render.
- [ ] If running live: rehearse `python -m pipeline.orchestrator --account ACME-013` 2–3× → confirm it lands `auto` each time.
- [ ] `docs/apa_flow.md` preview open; VS Code on `agents/reliability.py`.
- [ ] `ANTHROPIC_API_KEY` set (only needed for a live run).
- [ ] **Freeze the DB you rehearsed on** — don't re-run the full batch right before the call (live LLM = numbers move).

---

## Running order (30 min)
| # | Beat | Min | Show |
|---|------|-----|------|
| 1 | Frame + money reframe | 3 | talk |
| 2 | Spec-driven context engineering | 5 | `METHODOLOGY.md`, `DECISIONS.md` |
| 3 | Architecture: loop + branches | 4 | `docs/apa_flow.md` |
| 4 | Live demo — the report | 10 | Streamlit |
| 5 | The differentiator up close | 3 | `agents/reliability.py`, `agents/llm.py` |
| 6 | Defend decisions + close | 5 | `DECISIONS.md` |

**1 — Frame.** Sub-$20k tail, zero-touch today. Baseline is zero → any retention/expansion is
incremental ARR at near-zero marginal cost. Not "make CSMs faster" — there are none. Three
dimensions: renewal likelihood, product feedback, upsell.

**2 — How I worked.** Two main causes of hallucination: missing context, ambiguous instruction.
Fixes: layered instructions (methodology → CLAUDE.md → spec-per-task) and load only what a task
needs; every task is a **spec = a contract** (goal, inputs, outputs, acceptance criteria,
out-of-scope); append-only decisions log with the *why*. Punchline: the same distrust-the-model
philosophy reappears in the running system. (If pushed: also *training gaps* + *completion pressure*.)

**3 — Architecture.** Trace the happy path once, fast. Then spend the time on the branches:
bounce, opt-out, no-response, detractor, conflict, low-confidence, malformed, smart-upsell — each
a typed exception with its own human queue. "AI is dumb → the design is mostly about what happens
when it's wrong or the call is delicate."

**5 — Differentiator.** Routing is deterministic Python, **not** an LLM call → auditable, instant,
free, unit-testable. Agents emit signals; decisions are made here. Every model call goes through
one chokepoint that validates JSON against a schema, retries stricter, then falls back to a safe
default that **forces escalation (E8)**. The loop can't crash on a bad generation; a confused
model can't silently auto-act.

**6 — Decisions + close.** No framework (#001, transparency). Simulated customers (#007:
self-contained *and* manufactures the ground truth that makes accuracy real). Autonomous not
co-pilot (#008: approve-everything defeats the cost case; the sophistication is the guardrail).
Thresholds are knobs (#003/#004). Close: shipped this gate pattern before (email classification);
production swaps the two simulated seams (Salesforce pull, customer reply) for real ones and
offline accuracy for sampled human QA + renewal backtesting — **mechanism unchanged.** Invite
their comparison.

---

## Beat 4 — Demo click path
1. **Portfolio** — 20 previously zero-touch accounts, sorted by $ at stake. 3 auto / 17 escalate.
   Own the silence: ~8 never replied — realistic for this tail, and exactly why the E3
   manual-outreach queue exists (flags who a human must chase before the renewal silently lapses).
2. **ACME-004** — clean auto-handle (positive, confident, no exceptions). Read the drafted email + the reply.
3. **ACME-019** — detractor → `save_call`. Negative, low renewal, ~$19k ARR. It *refused* to auto-act. The judgment.
4. **ACME-012** ⭐ — $6k ARR (smallest account), happy, but ~$18k pro-services expansion surfaced →
   escalated to AE **despite** sub-$20k ARR. Value at stake drives attention, not current revenue. The BA call.
5. **Reliability tab** — read it as below.

## The accounts (from the current run — re-verify if you regenerate)
| Account | Shows | Decision | Code |
|---|---|---|---|
| **ACME-004** | clean auto-handle (sentiment + renewal both right) | auto | — |
| **ACME-013** | strongest auto (conf 0.88) — best live-run pick | auto | — |
| **ACME-019** | detractor → human save; ~$19k at risk | escalate `save_call` | E4 |
| **ACME-012** ⭐ | smart threshold: $6k ARR, ~$18k upsell surfaced | escalate `ae_upsell` | E7 |
| **ACME-016** | second E7 (AI Studio) — backup | escalate `ae_upsell` | E7 |
| **ACME-003** | bounce / stale contact | escalate `data_hygiene` | E1 |
| **ACME-006** | opt-out / suppress | escalate `data_hygiene` | E2 |
| **ACME-001/002/008/011** | low confidence → review | escalate `human_review` | E5 |

## Reading the Reliability tab
- Lead with **Renewal-call accuracy ~91%** — the business question. Upsell-fit ~91%.
- **Sentiment ~36% — name it as the noisy channel.** 3-class tone; "neutral vs positive" is
  genuinely ambiguous in one line. Actions gate on confidence + the renewal call, not tone.
- **The money line:** *zero incorrect autonomous actions* — the accounts it auto-handled were
  100% right on the renewal call; the one miss (ACME-019) was already escalated.
- The left table proves the gate concentrates autonomy on the cases it read right. Confusion
  matrix = the noisy channel shown honestly. Queue = what it declined to touch, and why.

---

## Q&A bank
- **Sarcastic / ambiguous reply?** → low confidence → escalate; that's what the gate is for.
- **Stop re-emailing a furious customer?** → opt-out suppression (E2) + detractor escalation (E4); never auto-re-contacts.
- **Trust the sentiment read?** → "I don't ask you to — I measure it and gate actions on confidence + the renewal call, and route the uncertain ones to a human."
- **Cost at scale?** → single model now; documented lever (#006) routes persona-gen/triage to Haiku, reserves Sonnet for low-confidence re-analysis.
- **Why so many escalations?** → conservative 0.75 gate by design + a realistically silent tail; relax the knob as observed precision rises.
- **How long did it take?** → skeleton ~1h; the reliability/eval layer + the exception judgment is where the real time went — the part a model won't produce on its own.

## Commands
```
python -m pipeline.orchestrator                      # full batch -> data/renewal.duckdb
python -m pipeline.orchestrator --account ACME-013   # robust live auto-handle
streamlit run app/dashboard.py                       # the report
```
