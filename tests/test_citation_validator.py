"""Tests for citation validation helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from models import SourceEvidence
from processors.citation_validator import validate_citations


def test_valid_and_invalid_citation_ids() -> None:
    """Cited source IDs should validate against the evidence list."""
    now = datetime.now(timezone.utc)
    sources = [
        SourceEvidence(
            source_id="S1",
            title="One",
            url="https://example.com/one",
            snippet="Snippet one.",
            query="one",
            rank=1,
            retrieved_at=now,
        ),
        SourceEvidence(
            source_id="S2",
            title="Two",
            url="https://example.com/two",
            snippet="Snippet two.",
            query="two",
            rank=2,
            retrieved_at=now,
        ),
    ]

    valid_result = validate_citations("I checked [S1] and [S2].", sources)
    assert valid_result["valid"] is True
    assert valid_result["cited_source_ids"] == ["S1", "S2"]
    assert valid_result["invalid_source_ids"] == []

    invalid_result = validate_citations("This cites [S9].", sources)
    assert invalid_result["valid"] is False
    assert invalid_result["cited_source_ids"] == ["S9"]
    assert invalid_result["invalid_source_ids"] == ["S9"]


def test_place_citation_validation_p_series() -> None:
    """Cited place IDs [P1], [P2] should validate against place evidence."""
    from models import PlaceEvidence

    now = datetime.now(timezone.utc)
    places = [
        PlaceEvidence(
            source_id="P1",
            name="Cafe One",
            query="cafes",
            rank=1,
            retrieved_at=now,
        ),
        PlaceEvidence(
            source_id="P2",
            name="Cafe Two",
            query="cafes",
            rank=2,
            retrieved_at=now,
        ),
    ]

    valid_res = validate_citations("Recommended spots are [P1] and [P2].", places)
    assert valid_res["valid"] is True
    assert valid_res["cited_source_ids"] == ["P1", "P2"]

    invalid_res = validate_citations("Try [P1] and phantom [P5].", places)
    assert invalid_res["valid"] is False
    assert invalid_res["invalid_source_ids"] == ["P5"]


def test_product_citation_validation_i_series() -> None:
    """Cited product IDs [I1], [I2] should validate against product evidence."""
    from models import ProductEvidence

    now = datetime.now(timezone.utc)
    products = [
        ProductEvidence(
            source_id="I1",
            title="Laptop Alpha",
            query="laptops",
            rank=1,
            retrieved_at=now,
        ),
        ProductEvidence(
            source_id="I2",
            title="Laptop Beta",
            query="laptops",
            rank=2,
            retrieved_at=now,
        ),
    ]

    valid_res = validate_citations("Top laptops are [I1] and [I2].", products)
    assert valid_res["valid"] is True
    assert valid_res["cited_source_ids"] == ["I1", "I2"]

    invalid_res = validate_citations("Consider [I1] and [I9].", products)
    assert invalid_res["valid"] is False
    assert invalid_res["invalid_source_ids"] == ["I9"]


