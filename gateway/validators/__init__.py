"""
Validator Registry — AI Gateway
Deploy to: /opt/litellm/validators/__init__.py

Maps alias names to deterministic validators.
Validators are < 50ms, zero cost, no LLM evaluation.
"""

from __future__ import annotations

from typing import Callable

from .batch_triage import validate_triage
from .entity_presence import validate_summary

# alias → callable(output: str) -> (bool, error_message)
VALIDATORS: dict[str, Callable[[str], tuple[bool, str]]] = {
    "batch-triage": validate_triage,
    "summarize": validate_summary,
}
