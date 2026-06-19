# Agentic Process Automation — Flow & Exception Handling

The closed loop, with every exception path. Renders on GitHub. This is deliverable #1.
The happy path is the spine; the branches off it are where the judgment lives.

```mermaid
flowchart TD
    A[Salesforce: at-risk accounts<br/>ARR &lt; $20k, renewal approaching] --> B[Router Agent<br/>segment + adapt questions]
    B -->|save / nurture / upsell / standard| C[Outreach Agent<br/>draft tailored email]
    C --> D[Send / simulate delivery]

    D -->|bounce| E1[E1 → data_hygiene queue]
    D -->|delivered| F[Customer Reply<br/>simulated persona]

    F -->|opt-out| E2[E2 → suppress + flag CSM]
    F -->|no reply| G{Touch count}
    G -->|&lt; 3| C
    G -->|= 3| E3[E3 → manual_outreach queue]
    F -->|reply text| H[Analysis Agent<br/>sentiment · renewal · feedback · upsell · confidence]

    H --> I[Next-Best-Action Agent<br/>play + $ value + talking points]
    I --> J{{Reliability Layer<br/>confidence gate + conflict + exception checks}}

    J -->|negative + low renewal| E4[E4 → save_call human]
    J -->|conflicting signals| E6[E6 → human_review]
    J -->|upsell ≥ $5k| E7[E7 → ae_upsell human<br/>escalate despite low ARR]
    J -->|confidence &lt; 0.75| E5[E5 → human_review]
    J -->|invalid model output| E8[E8 → human_review]
    J -->|clean · confident · no conflict| K[AUTO-HANDLE<br/>record recommendation]

    H -.hidden ground truth.-> EV[Eval: score prediction<br/>accuracy + calibration]
    K --> R[(DuckDB)]
    E1 --> R
    E2 --> R
    E3 --> R
    E4 --> R
    E5 --> R
    E6 --> R
    E7 --> R
    E8 --> R
    EV --> R
    R --> S[Streamlit CSM Report<br/>Portfolio · Account · Reliability]
```

## Reliability mechanisms layered on the flow
- **Schema validation + retry/fallback** at every agent (`agents/llm.py`): malformed output
  is retried with a stricter instruction, then falls back to a safe default that forces
  escalation (E8). The loop never crashes on a bad generation.
- **Confidence gate** (#003): only clean, confident, non-conflicting analyses auto-handle.
- **Exception taxonomy E1–E8** (`agents/reliability.py`): every off-happy-path case has a
  defined queue and reason, so nothing falls through silently.
- **Self-evaluation**: predictions are scored against hidden ground truth for an accuracy and
  calibration read — the proof the autonomy is earned, not assumed.

## The honest seam
Two things are simulated for the prototype: the Salesforce pull (replaced by `data_gen`) and
the customer reply (replaced by an LLM persona). In production: Salesforce is a real query and
the reply is a real inbound email/survey response routed back into the same loop. The eval's
offline accuracy is replaced by sampled human QA on escalations plus renewal-outcome
backtesting. **The mechanism — segment, engage, analyze, gate, escalate — is identical.**
