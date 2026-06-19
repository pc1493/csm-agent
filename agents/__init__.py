"""Agent package. Each module is one node in the renewal loop."""
from pathlib import Path

_PROMPTS = Path("prompts")


def load_prompt(name: str) -> str:
    """Load a prompt template by stem, e.g. load_prompt('analysis') -> prompts/analysis.md."""
    return (_PROMPTS / f"{name}.md").read_text()
