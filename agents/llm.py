"""
Shared LLM client + the validate-and-retry mechanism that makes the agents reliable.

This is the single chokepoint for every model call. The retry/validate logic here is
half of the "AI is dumb, so we wrap it" thesis (the other half is reliability.py).

Claude Code: the structure is here; fill in the two TODOs (the actual SDK call and the
JSON extraction). Keep ALL model calls going through `complete_json` so retry/fallback
behavior is uniform and the eval is honest.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Type, TypeVar

# Load .env from the project root if ANTHROPIC_API_KEY isn't already in the environment.
def _load_env() -> None:
    env_file = Path(__file__).parent.parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

_load_env()

from pydantic import BaseModel, ValidationError

# Single model for the whole prototype to keep token cost predictable (deliberate choice).
# DECISIONS #006 documents the production optimization: route persona-gen to Haiku.
MODEL = "claude-sonnet-4-6"
MAX_RETRIES = 2

T = TypeVar("T", bound=BaseModel)


def _client():
    from anthropic import Anthropic
    return Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def _raw_complete(system: str, user: str) -> str:
    """One model call -> raw text."""
    client = _client()
    msg = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text


def _extract_json(text: str) -> dict:
    """Strip code fences / prose and parse the JSON object. Be forgiving."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        text = text[4:] if text.startswith("json") else text
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start : end + 1])


def complete_json(system: str, user: str, schema: Type[T], fallback: T | None = None) -> tuple[T, bool]:
    """
    Call the model, parse + validate against `schema`, retrying on failure with an
    increasingly strict instruction. Returns (instance, ok). On total failure returns
    (fallback, False) if a fallback was supplied — this is exception code E8.

    The boolean is consumed by reliability.py: a fallback result is forced to escalate.
    """
    last_err = ""
    for attempt in range(MAX_RETRIES + 1):
        strictness = "" if attempt == 0 else (
            f"\n\nYour previous output failed validation ({last_err}). "
            f"Return ONLY a single valid JSON object matching the schema. No prose, no code fences."
        )
        try:
            raw = _raw_complete(system, user + strictness)
            return schema.model_validate(_extract_json(raw)), True
        except (ValidationError, json.JSONDecodeError, ValueError) as e:
            last_err = str(e)[:200]
    if fallback is not None:
        return fallback, False
    raise RuntimeError(f"complete_json exhausted retries with no fallback: {last_err}")
