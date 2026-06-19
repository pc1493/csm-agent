# Presentation — Speaker Outline (~30–45 min)

Live demo to the hiring panel. Grading is critical thinking, not polish. Show the machine
working, then make the *judgment* visible. Run order below; timings are a guide.

## Pre-flight (before the call)
- [ ] `python -m pipeline.orchestrator` already run; `data/renewal.duckdb` populated.
- [ ] `streamlit run app/dashboard.py` already open in a browser tab.
- [ ] A terminal ready on the repo for ONE live single-account run.
- [ ] `docs/apa_flow.md` open (the Mermaid diagram) for the architecture beat.
- [ ] Repo open in VS Code to show structure if asked.

## 1. Frame the problem and the money (~2 min)
- Restate it crisply: low-ARR tail, too small for human CSMs, **zero-touch today**.
- The reframe, said out loud: baseline is zero, so any retention or expansion is **incremental
  ARR at near-zero marginal cost**. We're monetizing an abandoned segment, not speeding up CSMs.
- Name the three dimensions the agent assesses: renewal likelihood, product feedback, upsell.

## 2. Walk the architecture (~5 min) — `docs/apa_flow.md`
- Trace the happy path once: segment → outreach → reply → analyze → next best action → report.
- Then spend the time on the **branches**: bounce, opt-out, no-response, detractor, conflict,
  low-confidence, the smart-threshold upsell, malformed output. "AI is dumb, so the design is
  mostly about what happens when it's wrong or the situation is delicate."
- Land the thesis: *an LLM one-shots a generic version of this; the engineering is making it
  consistent and safe enough to point at real customers autonomously.*

## 3. Demo — the report (~10 min) — Streamlit
- **Portfolio tab**: the worklist of previously-zero-touch accounts, sorted by $ at stake.
  Point out auto-handled vs escalated counts and ARR at risk. Own the no-response heaviness:
  ~8 of 20 never reply — realistic for a zero-touch tail, and exactly why the E3 manual-outreach
  queue exists (the agent flags who a human must chase before the renewal silently lapses).
- **Account drill-down**: pick one account, read the chain end to end — the outreach it sent,
  the customer's actual reply, the analysis, the decision + exception codes. Show a *clean
  auto-handle* and then an *escalation* so the contrast is visible.
- Pick the **smart-threshold account** (ACME-012: happy, ~$6k ARR, real pro-services need) and
  show it routed to the AE queue *despite* low ARR. This is the single best "BA thinking" beat.
- **Reliability tab** (the differentiator, spend real time here): lead with the renewal-call
  accuracy (~91% — the business question "will they renew?"), then the proof that no autonomous
  action was wrong (auto-handled accounts were 100% right on the renewal call; the one miss was
  escalated), the sentiment confusion shown honestly, and the escalation queue ("what it chose
  not to touch, and why"). Sentiment is the noisy 3-class channel — name it as such; never let
  that number lead.

## 4. Optional — prove it's real (~2 min)
- Run `python -m pipeline.orchestrator --account ACME-014` live. ~10–20s. Show the terminal
  trace, then refresh the dashboard. Only do this if the room wants it — don't risk the clock.

## 5. Defend the choices (~5 min) — `DECISIONS.md`
Have crisp answers ready (they're all in DECISIONS):
- Why no framework? Transparency + debuggability on a clock (#001).
- Why simulate customers? Self-contained + gives ground truth to measure against; here's the
  production seam (#007).
- Why autonomous, not co-pilot? The whole point is humans are too expensive for this tail;
  autonomy is *earned* per account by confidence + no exceptions (#008).
- Why these thresholds? Conservative starting knobs, tuned by calibration data (#003, #004, #005).
- What about cost at scale? Single model now; documented Haiku/Sonnet routing as the lever (#006).

## 6. Close (~2 min)
- This confidence-thresholded auto-vs-human pattern is one I've shipped before (email
  classification). Same instinct: let AI do the work, but measure it and gate it.
- What I'd build next for production: real Salesforce + inbound-email wiring, human QA sampling
  on escalations, renewal-outcome backtesting, model routing for cost. The mechanism doesn't change.
- Invite the comparison: I'd genuinely like to see how their team solved it (they offered).

## If asked "how long did this take?"
Be honest and confident: the skeleton is an hour; the differentiator (the reliability/eval
layer) and the judgment baked into the exception design is where the real time went. That's the
part that matters and the part an LLM won't produce on its own.

## Things to have one-liners ready for
- "What if the customer's reply is sarcastic?" → low confidence → escalate; calibration is why
  that's safe.
- "How do you stop it emailing a furious customer again?" → opt-out suppression (E2) +
  detractor escalation (E4); it never auto-re-contacts those.
- "Why should I trust the sentiment read?" → I don't ask you to — I measure it and gate actions
  on measured confidence, and route the uncertain ones to a human.
