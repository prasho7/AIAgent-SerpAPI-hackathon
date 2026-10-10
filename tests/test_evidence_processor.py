"""Tests for evidence processing helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from models import SourceEvidence
from processors.evidence_processor import assign_source_ids, deduplicate_sources, format_evidence_for_llm


def test_url_deduplication() -> None:
    """Duplicate sources with equivalent URLs should collapse to one entry."""
    now = datetime.now(timezone.utc)
    sources = [
        SourceEvidence(
            source_id="S1",
            title="AI article",
            url="https://example.com/ai",
            snippet="First summary.",
            query="AI",
            rank=1,
            retrieved_at=now,
        ),
        SourceEvidence(
            source_id="S2",
            title="AI article",
            url="HTTPS://EXAMPLE.com/ai",
            snippet="First summary.",
            query="AI",
            rank=2,
            retrieved_at=now,
        ),
    ]

    assert len(deduplicate_sources(sources)) == 1


def test_source_ids_become_s1_s2_etc() -> None:
    """Source IDs should be assigned deterministically in order."""
    now = datetime.now(timezone.utc)
    sources = [
        SourceEvidence(
            source_id="temp-1",
            title="One",
            url="https://example.com/one",
            snippet="One snippet.",
            query="one",
            rank=1,
            retrieved_at=now,
        ),
        SourceEvidence(
            source_id="temp-2",
            title="Two",
            url="https://example.com/two",
            snippet="Two snippet.",
            query="two",
            rank=2,
            retrieved_at=now,
        ),
    ]

    assigned = assign_source_ids(sources)
    assert [item.source_id for item in assigned] == ["S1", "S2"]


def test_evidence_formatting_contains_expected_values() -> None:
    """Formatting should include the source ID, title, URL, and snippet."""
    now = datetime.now(timezone.utc)
    sources = [
        SourceEvidence(
            source_id="old",
            title="Example article",
            url="https://example.com/example",
            snippet="This is a sample snippet.",
            query="sample query",
            rank=1,
            retrieved_at=now,
        )
    ]

    output = format_evidence_for_llm(sources)
    assert "[S1]" in output
    assert "Example article" in output
    assert "https://example.com/example" in output
    assert "This is a sample snippet." in output


def test_place_deduplication_and_ranking() -> None:
    """Places should be deduplicated by maps_url / name + address, and ranked by rating & review count."""
    from models import PlaceEvidence
    from processors.evidence_processor import (
        assign_place_ids,
        deduplicate_places,
        format_places_for_llm,
        rank_and_curate_places,
    )

    now = datetime.now(timezone.utc)
    places = [
        PlaceEvidence(
            source_id="p_temp_1",
            name="Cafe Sunshine",
            address="123 Main St",
            rating=4.0,
            review_count=100,
            maps_url="https://maps.google.com/?cid=111",
            query="cafes",
            rank=3,
            retrieved_at=now,
        ),
        PlaceEvidence(
            source_id="p_temp_2",
            name="Cafe Sunshine",
            address="123 Main St",
            rating=4.0,
            review_count=100,
            maps_url="https://maps.google.com/?cid=111",  # duplicate
            query="cafes",
            rank=4,
            retrieved_at=now,
        ),
        PlaceEvidence(
            source_id="p_temp_3",
            name="Star Roastery",
            address="456 Oak Ave",
            rating=4.8,
            review_count=500,
            maps_url="https://maps.google.com/?cid=222",
            query="cafes",
            rank=1,
            retrieved_at=now,
        ),
    ]

    deduped = deduplicate_places(places)
    assert len(deduped) == 2

    curated = rank_and_curate_places(places, max_places=5)
    assert len(curated) == 2
    # Highest rating (4.8) should be ranked first as P1
    assert curated[0].source_id == "P1"
    assert curated[0].name == "Star Roastery"
    assert curated[1].source_id == "P2"
    assert curated[1].name == "Cafe Sunshine"

    formatted = format_places_for_llm(curated)
    assert "[P1] Place: Star Roastery" in formatted
    assert "Rating: 4.8/5.0 (500 reviews)" in formatted
    assert "[P2] Place: Cafe Sunshine" in formatted


def test_build_google_maps_url_priorities() -> None:
    """Test all fallback priorities and safety checks for build_google_maps_url."""
    from datetime import datetime, timezone
    from models import PlaceEvidence
    from processors.evidence_processor import build_google_maps_url

    now = datetime.now(timezone.utc)

    # Priority A: Valid Google Maps URL
    p_a = PlaceEvidence(
        source_id="P1",
        name="Third Wave Coffee",
        maps_url="https://www.google.com/maps/place/Third+Wave+Coffee/@12.93,77.62,17z",
        website="https://thirdwavecoffee.in",
        query="cafes",
        rank=1,
        retrieved_at=now,
    )
    assert build_google_maps_url(p_a) == "https://www.google.com/maps/place/Third+Wave+Coffee/@12.93,77.62,17z"

    # Business website is NEVER used as maps_url if maps_url is non-Google
    p_bad_maps = PlaceEvidence(
        source_id="P1",
        name="Third Wave Coffee",
        maps_url="https://thirdwavecoffee.in/store-locator",  # non-google domain
        address="Koramangala",
        query="cafes",
        rank=1,
        retrieved_at=now,
    )
    # Should fall back to name+address Google Maps search URL
    assert "https://www.google.com/maps/search/?api=1" in (build_google_maps_url(p_bad_maps) or "")

    # Priority B: Place ID
    p_b = PlaceEvidence(
        source_id="P2",
        name="Dyu Art Cafe",
        place_id="ChIJ_w12345ABC",
        query="cafes",
        rank=2,
        retrieved_at=now,
    )
    assert build_google_maps_url(p_b) == "https://www.google.com/maps/search/?api=1&query=Dyu%20Art%20Cafe&query_place_id=ChIJ_w12345ABC"

    # Priority C: Place name + Address
    p_c = PlaceEvidence(
        source_id="P3",
        name="Star Cafe",
        address="100 Feet Rd, Indiranagar",
        query="cafes",
        rank=3,
        retrieved_at=now,
    )
    assert build_google_maps_url(p_c) == "https://www.google.com/maps/search/?api=1&query=Star%20Cafe%2C%20100%20Feet%20Rd%2C%20Indiranagar"

    # Priority D: Place name only
    p_d = PlaceEvidence(
        source_id="P4",
        name="Bistro Central",
        query="cafes",
        rank=4,
        retrieved_at=now,
    )
    assert build_google_maps_url(p_d) == "https://www.google.com/maps/search/?api=1&query=Bistro%20Central"

    # Priority E: Missing place name
    p_e = PlaceEvidence.model_construct(
        source_id="P5",
        name="",
        query="cafes",
        rank=5,
        retrieved_at=now,
    )
    assert build_google_maps_url(p_e) is None


def test_product_deduplication_and_ranking() -> None:
    """Products should be deduplicated by URL / title+merchant and ranked by budget fit, rating, reviews."""
    from models import ProductEvidence
    from processors.evidence_processor import (
        assign_product_ids,
        deduplicate_products,
        format_products_for_llm,
        rank_and_curate_products,
    )

    now = datetime.now(timezone.utc)
    products = [
        ProductEvidence(
            source_id="temp_1",
            title="Dell Inspiron 15",
            price=65000.0,
            currency="INR",
            price_text="₹65,000",
            merchant="Dell Store",
            product_url="https://dell.com/inspiron",
            rating=4.5,
            reviews=300,
            query="laptops",
            rank=1,
            retrieved_at=now,
        ),
        ProductEvidence(
            source_id="temp_2",
            title="Dell Inspiron 15",
            price=65000.0,
            currency="INR",
            price_text="₹65,000",
            merchant="Dell Store",
            product_url="https://dell.com/inspiron",  # duplicate
            rating=4.5,
            reviews=300,
            query="laptops",
            rank=2,
            retrieved_at=now,
        ),
        ProductEvidence(
            source_id="temp_3",
            title="HP Pavilion 14",
            price=55000.0,
            currency="INR",
            price_text="₹55,000",
            merchant="Amazon.in",
            product_url="https://amazon.in/hp-pavilion",
            rating=4.4,
            reviews=400,
            query="laptops",
            rank=3,
            retrieved_at=now,
        ),
        ProductEvidence(
            source_id="temp_4",
            title="Lenovo IdeaPad Slim 3",
            price=48000.0,
            currency="INR",
            price_text="₹48,000",
            merchant="Flipkart",
            product_url="https://flipkart.com/lenovo",
            rating=4.6,
            reviews=800,
            query="laptops",
            rank=4,
            retrieved_at=now,
        ),
    ]

    deduped = deduplicate_products(products)
    assert len(deduped) == 3

    # Rank with budget ₹60,000
    curated = rank_and_curate_products(products, budget_amount=60000.0, max_products=5)
    assert len(curated) == 3
    # Items within budget should come before Dell (65k > 60k). Lenovo (4.6 rating, 800 reviews) should be I1
    assert curated[0].source_id == "I1"
    assert curated[0].title == "Lenovo IdeaPad Slim 3"
    assert curated[1].source_id == "I2"
    assert curated[1].title == "HP Pavilion 14"
    assert curated[2].source_id == "I3"
    assert curated[2].title == "Dell Inspiron 15"

    formatted = format_products_for_llm(curated)
    assert "[I1] Product: Lenovo IdeaPad Slim 3" in formatted
    assert "Price: ₹48,000" in formatted
    assert "Merchant/Seller: Flipkart" in formatted
    assert "Rating: 4.6/5.0 (800 reviews)" in formatted




