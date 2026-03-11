"""
Entity Presence Validator — for 'summarize' alias.
Ensures summaries retain key entities (dollar amounts, dates, proper nouns, percentages).
Threshold: 60% entity overlap between original and summary.

Deploy to: /opt/litellm/validators/entity_presence.py
"""

import re
from typing import Set, Tuple


def extract_entities(text: str) -> Set[str]:
    """Extract notable entities from text for overlap comparison."""
    entities: Set[str] = set()

    # Dollar amounts: $1,234.56
    entities.update(re.findall(r"\$[\d,.]+", text))

    # Percentages: 12.5%
    entities.update(re.findall(r"\d+\.?\d*%", text))

    # Dates — MM/DD/YYYY or MM/DD/YY
    entities.update(re.findall(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", text))

    # Dates — Month DD, YYYY
    entities.update(
        re.findall(
            r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s+\d{4}\b",
            text,
        )
    )

    # Dates — YYYY-MM-DD
    entities.update(re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text))

    # Proper nouns (capitalized multi-word sequences, 2+ words)
    entities.update(re.findall(r"\b[A-Z][a-z]+ (?:[A-Z][a-z]+ ?)+", text))

    # ASC / IRC references (common in tax documents)
    entities.update(re.findall(r"\bASC\s+\d+", text))
    entities.update(re.findall(r"\bIRC\s+(?:Section\s+)?\d+", text))

    return entities


def validate_summary(
    output: str, original: str = "", threshold: float = 0.6
) -> Tuple[bool, str]:
    """Validate summary retains key entities from original.

    Args:
        output: The generated summary text.
        original: The original source text. Must be passed via request metadata.
                  If empty, validation passes gracefully.
        threshold: Minimum entity overlap ratio (default 0.6 = 60%).

    Returns:
        (passed, error_message) — True if valid, False with details if not.
    """
    if not original:
        return True, ""

    original_entities = extract_entities(original)
    if not original_entities:
        return True, ""

    summary_entities = extract_entities(output)
    overlap = len(original_entities & summary_entities) / len(original_entities)

    if overlap >= threshold:
        return True, ""

    missing = original_entities - summary_entities
    return (
        False,
        f"Entity overlap {overlap:.0%} < {threshold:.0%}. Missing: {sorted(missing)[:5]}",
    )
