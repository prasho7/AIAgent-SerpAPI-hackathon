"""Deterministic evidence-processing helpers."""

from __future__ import annotations

from urllib.parse import quote, urlsplit

from models import PlaceEvidence, ProductEvidence, SourceEvidence



def normalise_text(value: str) -> str:
    """Normalise whitespace and lowercase text for deterministic comparisons."""
    return " ".join((value or "").strip().split()).lower()


def _normalise_url(value: str) -> str:
    """Return a stable URL string for deduplication."""
    if not value:
        return ""
    parsed = urlsplit(value.strip())
    if not parsed.scheme or not parsed.netloc:
        return normalise_text(value)
    return normalise_text(parsed.geturl())


def deduplicate_sources(sources: list[SourceEvidence]) -> list[SourceEvidence]:
    """Remove duplicate sources by URL first, then fallback title/snippet."""
    seen: set[str] = set()
    distinct: list[SourceEvidence] = []

    for source in sources:
        url_key = _normalise_url(source.url)
        title_key = normalise_text(source.title)
        snippet_key = normalise_text(source.snippet)
        dedupe_key = url_key if url_key else f"{title_key}|{snippet_key}"

        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        distinct.append(source)

    return distinct


def assign_source_ids(sources: list[SourceEvidence]) -> list[SourceEvidence]:
    """Assign deterministic S1, S2, S3 IDs in order to source evidence."""
    assigned: list[SourceEvidence] = []
    for index, source in enumerate(sources, start=1):
        updated = source.model_copy(deep=True)
        updated.source_id = f"S{index}"
        assigned.append(updated)
    return assigned


def process_evidence(sources: list[SourceEvidence], max_sources: int = 12) -> list[SourceEvidence]:
    """Deduplicate, cap to max_sources, and assign deterministic S1, S2 IDs."""
    deduped = deduplicate_sources(sources)
    capped = deduped[:max_sources]
    return assign_source_ids(capped)


def format_evidence_for_llm(sources: list[SourceEvidence]) -> str:
    """Format evidence into readable blocks suitable for LLM prompting."""
    if not sources:
        return "No evidence retrieved."

    blocks: list[str] = []
    for source in assign_source_ids(sources):
        blocks.append(
            f"[{source.source_id}] Title: {source.title}\n"
            f"URL: {source.url}\n"
            f"Query: {source.query}\n"
            f"Snippet: {source.snippet}\n"
        )
    return "\n".join(blocks)


def deduplicate_places(places: list[PlaceEvidence]) -> list[PlaceEvidence]:
    """Deduplicate places by maps_url, website, or normalized name + address."""
    seen: set[str] = set()
    distinct: list[PlaceEvidence] = []

    for place in places:
        maps_key = _normalise_url(place.maps_url or "")
        website_key = _normalise_url(place.website or "")
        name_key = normalise_text(place.name)
        addr_key = normalise_text(place.address or "")

        dedupe_key = (
            maps_key
            if maps_key
            else (website_key if website_key else f"{name_key}|{addr_key}")
        )

        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        distinct.append(place)

    return distinct


def assign_place_ids(places: list[PlaceEvidence]) -> list[PlaceEvidence]:
    """Assign deterministic P1, P2, P3 IDs in order to place evidence."""
    assigned: list[PlaceEvidence] = []
    for index, place in enumerate(places, start=1):
        updated = place.model_copy(deep=True)
        updated.source_id = f"P{index}"
        assigned.append(updated)
    return assigned


def rank_and_curate_places(
    places: list[PlaceEvidence],
    criteria: list[str] | None = None,
    max_places: int = 5,
) -> list[PlaceEvidence]:
    """Deduplicate, rank deterministically by rating and review count, cap at max_places, and assign P1..P5."""
    deduped = deduplicate_places(places)

    def sort_key(item: PlaceEvidence) -> tuple[int, float, int, int]:
        has_rating = 1 if item.rating is not None else 0
        rating_val = item.rating if item.rating is not None else 0.0
        reviews_val = item.review_count if item.review_count is not None else 0
        rank_val = -item.rank  # lower original rank number is better
        return (has_rating, rating_val, reviews_val, rank_val)

    sorted_places = sorted(deduped, key=sort_key, reverse=True)
    capped = sorted_places[:max_places]
    return assign_place_ids(capped)


def format_places_for_llm(places: list[PlaceEvidence]) -> str:
    """Format place evidence into clean structured blocks for LLM prompting."""
    if not places:
        return "No place evidence retrieved."

    blocks: list[str] = []
    for place in assign_place_ids(places):
        lines = [f"[{place.source_id}] Place: {place.name}"]
        if place.category:
            lines.append(f"Category: {place.category}")
        if place.rating is not None:
            rev_str = f" ({place.review_count} reviews)" if place.review_count is not None else ""
            lines.append(f"Rating: {place.rating}/5.0{rev_str}")
        if place.address:
            lines.append(f"Address: {place.address}")
        if place.price_range:
            lines.append(f"Price Level: {place.price_range}")
        if place.opening_hours:
            lines.append(f"Hours: {place.opening_hours}")
        if place.phone:
            lines.append(f"Phone: {place.phone}")
        if place.website:
            lines.append(f"Website: {place.website}")
        if place.maps_url:
            lines.append(f"Google Maps Link: {place.maps_url}")
        if place.snippet:
            lines.append(f"Description/Snippet: {place.snippet}")

        blocks.append("\n".join(lines))

    return "\n\n".join(blocks)


def is_google_maps_url(url: str) -> bool:
    """Check if a URL points to Google Maps."""
    if not url:
        return False
    try:
        parsed = urlsplit(url.strip())
        if parsed.scheme not in ("http", "https"):
            return False
        netloc = parsed.netloc.lower()
        path = parsed.path.lower()
        if "maps.google" in netloc or "maps.app.goo.gl" in netloc or "goo.gl/maps" in f"{netloc}{path}":
            return True
        if "google." in netloc and ("/maps" in path or "maps" in netloc):
            return True
        return False
    except Exception:
        return False


def build_google_maps_url(place: PlaceEvidence) -> str | None:
    """Build or validate a reliable Google Maps URL for a place using safe priority rules.

    Priority A: Valid Google Maps URL from SerpApi
    Priority B: Place ID (query_place_id)
    Priority C: Place name and address
    Priority D: Place name only
    Priority E: None (if name is missing)
    """
    # Priority A: Valid Google Maps URL from SerpApi
    if place.maps_url and is_google_maps_url(place.maps_url):
        return place.maps_url

    name = (place.name or "").strip()
    if not name:
        return None

    # Priority B: Place ID
    if place.place_id and place.place_id.strip():
        encoded_name = quote(name)
        encoded_place_id = quote(place.place_id.strip())
        return f"https://www.google.com/maps/search/?api=1&query={encoded_name}&query_place_id={encoded_place_id}"

    # Priority C: Place name and address
    address = (place.address or "").strip()
    if address:
        encoded_query = quote(f"{name}, {address}")
        return f"https://www.google.com/maps/search/?api=1&query={encoded_query}"

    # Priority D: Place name only
    encoded_query = quote(name)
    return f"https://www.google.com/maps/search/?api=1&query={encoded_query}"


def deduplicate_products(products: list[ProductEvidence]) -> list[ProductEvidence]:
    """Deduplicate products by product_url, or normalized title + merchant."""
    seen: set[str] = set()
    distinct: list[ProductEvidence] = []

    for product in products:
        url_key = _normalise_url(product.product_url or "")
        title_key = normalise_text(product.title)
        merchant_key = normalise_text(product.merchant or "")

        dedupe_key = (
            url_key
            if url_key
            else f"{title_key}|{merchant_key}"
        )

        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        distinct.append(product)

    return distinct


def assign_product_ids(products: list[ProductEvidence]) -> list[ProductEvidence]:
    """Assign deterministic I1, I2, I3 IDs in order to product evidence."""
    assigned: list[ProductEvidence] = []
    for index, product in enumerate(products, start=1):
        updated = product.model_copy(deep=True)
        updated.source_id = f"I{index}"
        assigned.append(updated)
    return assigned


def rank_and_curate_products(
    products: list[ProductEvidence],
    budget_amount: float | None = None,
    criteria: list[str] | None = None,
    max_products: int = 5,
) -> list[ProductEvidence]:
    """Deduplicate, rank deterministically (budget fit, rating, reviews, rank), cap at max_products, and assign I1..I5."""
    deduped = deduplicate_products(products)

    def sort_key(item: ProductEvidence) -> tuple[int, int, float, int, int]:
        # Priority 1: within budget (if budget is specified)
        if budget_amount is not None:
            if item.price is not None:
                within_budget = 1 if item.price <= budget_amount else 0
            else:
                within_budget = 1  # unknown price treated neutrally
        else:
            within_budget = 1

        # Priority 2: has rating
        has_rating = 1 if item.rating is not None else 0

        # Priority 3: rating score
        rating_val = item.rating if item.rating is not None else 0.0

        # Priority 4: review count
        reviews_val = item.reviews if item.reviews is not None else 0

        # Priority 5: SerpApi original ranking position (lower is better)
        rank_val = -item.rank

        return (within_budget, has_rating, rating_val, reviews_val, rank_val)

    sorted_products = sorted(deduped, key=sort_key, reverse=True)
    capped = sorted_products[:max_products]
    return assign_product_ids(capped)


def format_products_for_llm(products: list[ProductEvidence]) -> str:
    """Format product evidence into clean structured blocks for LLM prompting."""
    if not products:
        return "No product evidence retrieved."

    blocks: list[str] = []
    for product in assign_product_ids(products):
        lines = [f"[{product.source_id}] Product: {product.title}"]
        if product.price_text or product.price is not None:
            price_str = product.price_text or f"{product.currency or ''} {product.price}".strip()
            lines.append(f"Price: {price_str}")
        if product.merchant:
            lines.append(f"Merchant/Seller: {product.merchant}")
        if product.rating is not None:
            rev_str = f" ({product.reviews} reviews)" if product.reviews is not None else ""
            lines.append(f"Rating: {product.rating}/5.0{rev_str}")
        if product.delivery_info:
            lines.append(f"Delivery: {product.delivery_info}")
        if product.condition:
            lines.append(f"Condition: {product.condition}")
        if product.product_url:
            lines.append(f"Listing URL: {product.product_url}")
        if product.snippet:
            lines.append(f"Description/Snippet: {product.snippet}")

        blocks.append("\n".join(lines))

    return "\n\n".join(blocks)

