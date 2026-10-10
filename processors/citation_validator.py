"""Validation helpers for inline source citations."""

from __future__ import annotations

import re

from models import PlaceEvidence, ProductEvidence, SourceEvidence


def extract_citations(text: str) -> list[str]:
    """Extract inline citations such as [S1], [P1], and [I1]."""
    matches = re.findall(r"\[(S|P|I)(\d+)\]", text or "")
    return [f"{prefix}{num}" for prefix, num in matches]


def validate_citations(
    text: str,
    sources: list[SourceEvidence | PlaceEvidence | ProductEvidence],
) -> dict[str, object]:
    """Check that every cited source ID exists in the provided evidence list."""
    existing_ids = {source.source_id for source in sources}
    cited_unique: list[str] = []
    for source_id in extract_citations(text):
        if source_id not in cited_unique:
            cited_unique.append(source_id)

    invalid_source_ids = [source_id for source_id in cited_unique if source_id not in existing_ids]
    return {
        "valid": not invalid_source_ids,
        "cited_source_ids": cited_unique,
        "invalid_source_ids": invalid_source_ids,
    }

