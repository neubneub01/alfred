"""
Batch-Triage Validator — JSON Schema Validation
Deploy to: /opt/litellm/validators/batch_triage.py

Validates that batch-triage responses conform to the required JSON schema.
Every email triage, job scoring, and notification filtering workflow
depends on structured JSON. Malformed JSON = silent data loss.

Deterministic, < 50ms, zero cost.
"""

import json

import jsonschema

TRIAGE_SCHEMA = {
    "type": "object",
    "required": ["category", "priority", "confidence", "reason"],
    "properties": {
        "category": {"type": "string"},
        "priority": {"type": "integer", "minimum": 1, "maximum": 5},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "reason": {"type": "string"},
    },
    "additionalProperties": False,
}


def validate_triage(output: str) -> tuple[bool, str]:
    """Validate batch-triage output against TRIAGE_SCHEMA.

    Returns:
        (True, "") on valid output.
        (False, error_message) on invalid output.
    """
    try:
        data = json.loads(output)
        jsonschema.validate(data, TRIAGE_SCHEMA)
        return True, ""
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"
    except jsonschema.ValidationError as e:
        return False, f"Schema violation: {e.message}"
