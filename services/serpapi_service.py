"""SerpApi service interface for web, maps, and shopping search."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests

from config import Settings
from models import PlaceEvidence, ProductEvidence, SourceEvidence



class SerpApiService:
    """SerpApi client interface for web, maps, and shopping search."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings


    def test_connection(self) -> dict[str, Any]:
        """Test API connectivity to SerpApi with a single fixed web search query.

        Fixed query: 'SerpApi official documentation'
        Returns:
            dict containing:
                - success (bool): True if request succeeded and results were parsed
                - message (str): Safe human-readable status message
                - results (list[dict[str, str]]): Up to 3 results with title, url, snippet
        """
        if not self.settings.serpapi_api_key:
            return {
                "success": False,
                "message": "SERPAPI_API_KEY is missing. Please set it in your .env file.",
                "results": [],
            }

        params = {
            "engine": "google",
            "q": "SerpApi official documentation",
            "api_key": self.settings.serpapi_api_key,
            "num": 3,
        }

        try:
            response = requests.get(
                "https://serpapi.com/search.json",
                params=params,
                timeout=30,
            )

            if response.status_code in (401, 403):
                return {
                    "success": False,
                    "message": "SerpApi authentication failed: Invalid or unauthorized API key.",
                    "results": [],
                }
            elif response.status_code == 429:
                return {
                    "success": False,
                    "message": "SerpApi quota or rate limit exceeded.",
                    "results": [],
                }

            try:
                data = response.json()
            except Exception:
                return {
                    "success": False,
                    "message": "SerpApi returned an invalid or malformed JSON response.",
                    "results": [],
                }

            if "error" in data:
                err_text = str(data["error"])
                err_lower = err_text.lower()
                if "invalid api key" in err_lower or "api key is invalid" in err_lower:
                    msg = "SerpApi authentication failed: Invalid or unauthorized API key."
                elif "limit" in err_lower or "quota" in err_lower or "searches per month" in err_lower:
                    msg = "SerpApi quota or search limit reached."
                else:
                    msg = f"SerpApi error: {err_text[:200]}"
                return {
                    "success": False,
                    "message": msg,
                    "results": [],
                }

            organic_results = data.get("organic_results", [])
            if not organic_results or not isinstance(organic_results, list):
                return {
                    "success": False,
                    "message": "SerpApi returned no organic search results for the test query.",
                    "results": [],
                }

            extracted_results = []
            for item in organic_results[:3]:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title", "")).strip() or "Untitled Result"
                url = str(item.get("link", "")).strip()
                snippet = str(item.get("snippet", "")).strip()
                extracted_results.append(
                    {
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                    }
                )

            if not extracted_results:
                return {
                    "success": False,
                    "message": "SerpApi returned empty result items.",
                    "results": [],
                }

            return {
                "success": True,
                "message": f"Successfully connected to SerpApi (retrieved {len(extracted_results)} results).",
                "results": extracted_results,
            }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "message": "SerpApi request timed out after 30 seconds.",
                "results": [],
            }
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "message": "Network error: Could not establish a connection to SerpApi.",
                "results": [],
            }
        except Exception as exc:
            return {
                "success": False,
                "message": f"Unexpected error connecting to SerpApi: {str(exc)[:200]}",
                "results": [],
            }

    def search_web(self, queries: list[str]) -> list[SourceEvidence]:
        """Search the web for up to 3 queries, returning raw SourceEvidence items."""
        if not self.settings.serpapi_api_key:
            raise ValueError("SERPAPI_API_KEY is not configured.")

        capped_queries = queries[:3]
        all_evidence: list[SourceEvidence] = []
        now = datetime.now(timezone.utc)

        for query_idx, query in enumerate(capped_queries, start=1):
            cleaned_query = (query or "").strip()
            if not cleaned_query:
                continue

            params = {
                "engine": "google",
                "q": cleaned_query,
                "api_key": self.settings.serpapi_api_key,
                "num": 5,
            }

            try:
                response = requests.get(
                    "https://serpapi.com/search.json",
                    params=params,
                    timeout=30,
                )
                if response.status_code != 200:
                    continue

                data = response.json()
                if "error" in data:
                    continue

                organic_results = data.get("organic_results", [])
                if not isinstance(organic_results, list):
                    continue

                for rank, item in enumerate(organic_results[:5], start=1):
                    if not isinstance(item, dict):
                        continue
                    title = str(item.get("title", "")).strip() or f"Source {rank}"
                    url = str(item.get("link", "")).strip()
                    snippet = str(item.get("snippet", "")).strip()
                    if not url:
                        continue

                    all_evidence.append(
                        SourceEvidence(
                            source_id=f"raw_{query_idx}_{rank}",
                            title=title,
                            url=url,
                            snippet=snippet or "No snippet provided.",
                            query=cleaned_query,
                            rank=rank,
                            retrieved_at=now,
                        )
                    )
            except Exception:
                # Continue fetching remaining queries if one query fails
                continue

        return all_evidence

    def search_places(self, query: str, location: str) -> list[PlaceEvidence]:
        """Search local places using SerpApi Google Maps engine, returning up to 5 places."""
        if not self.settings.serpapi_api_key:
            raise ValueError("SERPAPI_API_KEY is not configured.")

        cleaned_query = (query or "").strip()
        cleaned_loc = (location or "").strip()
        full_query = f"{cleaned_query} {cleaned_loc}".strip() if cleaned_loc else cleaned_query

        if not full_query:
            return []

        params = {
            "engine": "google_maps",
            "q": full_query,
            "api_key": self.settings.serpapi_api_key,
        }

        places: list[PlaceEvidence] = []
        now = datetime.now(timezone.utc)

        try:
            response = requests.get(
                "https://serpapi.com/search.json",
                params=params,
                timeout=30,
            )
            if response.status_code != 200:
                return []

            data = response.json()
            if "error" in data:
                return []

            local_results = data.get("local_results", [])
            if not isinstance(local_results, list) or not local_results:
                # Some Maps responses place the single place directly in 'place_results'
                place_result = data.get("place_results")
                if isinstance(place_result, dict):
                    local_results = [place_result]
                else:
                    return []

            for rank, item in enumerate(local_results[:5], start=1):
                if not isinstance(item, dict):
                    continue

                name = str(item.get("title") or item.get("name") or "").strip()
                if not name:
                    continue

                # Safely parse rating
                rating = None
                raw_rating = item.get("rating")
                if raw_rating is not None:
                    try:
                        rating = float(raw_rating)
                    except (ValueError, TypeError):
                        rating = None

                # Safely parse review count
                review_count = None
                raw_reviews = item.get("reviews") or item.get("reviews_original")
                if raw_reviews is not None:
                    try:
                        if isinstance(raw_reviews, str):
                            # extract digits if formatted as "1,234 reviews"
                            digits = "".join(ch for ch in raw_reviews if ch.isdigit())
                            review_count = int(digits) if digits else None
                        else:
                            review_count = int(raw_reviews)
                    except (ValueError, TypeError):
                        review_count = None

                # Safely extract operating hours
                hours_str = None
                raw_hours = item.get("operating_hours") or item.get("hours") or item.get("open_state")
                if isinstance(raw_hours, dict):
                    hours_str = ", ".join(f"{k}: {v}" for k, v in raw_hours.items() if isinstance(v, str))[:300]
                elif isinstance(raw_hours, str):
                    hours_str = raw_hours.strip()[:300]

                address = str(item.get("address") or "").strip() or None
                place_id = str(item.get("place_id") or item.get("data_id") or "").strip() or None
                price_range = str(item.get("price") or "").strip() or None
                phone = str(item.get("phone") or "").strip() or None
                website = str(item.get("website") or "").strip() or None
                maps_url = str(item.get("link") or item.get("place_url") or "").strip() or None
                category = str(item.get("type") or item.get("category") or "").strip() or None
                snippet = str(item.get("description") or item.get("snippet") or "").strip() or None

                places.append(
                    PlaceEvidence(
                        source_id=f"raw_p_{rank}",
                        name=name,
                        address=address,
                        place_id=place_id,
                        rating=rating,
                        review_count=review_count,
                        price_range=price_range,
                        opening_hours=hours_str,
                        phone=phone,
                        website=website,
                        maps_url=maps_url,
                        category=category,
                        snippet=snippet,
                        query=full_query,
                        rank=rank,
                        retrieved_at=now,
                    )
                )

        except Exception:
            return []

        return places

    def search_products(self, query: str, country: str | None = None) -> list[ProductEvidence]:
        """Search live products using SerpApi Google Shopping engine, returning up to 10 products."""
        if not self.settings.serpapi_api_key:
            raise ValueError("SERPAPI_API_KEY is not configured.")

        cleaned_query = (query or "").strip()
        if not cleaned_query:
            return []

        gl_val = country.strip().lower() if (country and country.strip()) else (getattr(self.settings, "shopping_gl", "in") or "in")
        hl_val = getattr(self.settings, "shopping_hl", "en") or "en"

        params: dict[str, Any] = {
            "engine": "google_shopping",
            "q": cleaned_query,
            "api_key": self.settings.serpapi_api_key,
            "num": 10,
            "gl": gl_val,
            "hl": hl_val,
        }

        products: list[ProductEvidence] = []
        now = datetime.now(timezone.utc)

        try:
            response = requests.get(
                "https://serpapi.com/search.json",
                params=params,
                timeout=30,
            )
            if response.status_code != 200:
                return []

            data = response.json()
            if "error" in data:
                return []

            raw_results = data.get("shopping_results") or data.get("inline_shopping_results") or []
            if not isinstance(raw_results, list) or not raw_results:
                return []

            for rank, item in enumerate(raw_results[:10], start=1):
                if not isinstance(item, dict):
                    continue

                title = str(item.get("title") or item.get("name") or "").strip()
                if not title:
                    continue

                # Safely extract price
                price = None
                raw_extracted = item.get("extracted_price")
                if raw_extracted is not None:
                    try:
                        price = float(raw_extracted)
                    except (ValueError, TypeError):
                        price = None

                price_text = None
                raw_price = item.get("price")
                if raw_price is not None:
                    price_text = str(raw_price).strip()
                    if price is None:
                        # Extract first numeric sequence with decimal if available
                        digits = "".join(ch for ch in price_text if ch.isdigit() or ch == ".")
                        try:
                            price = float(digits)
                        except (ValueError, TypeError):
                            price = None

                # Extract currency if detected in price_text
                currency = None
                if price_text:
                    if "₹" in price_text or "inr" in price_text.lower() or "rs" in price_text.lower():
                        currency = "INR"
                    elif "$" in price_text or "usd" in price_text.lower():
                        currency = "USD"
                    elif "€" in price_text or "eur" in price_text.lower():
                        currency = "EUR"
                    elif "£" in price_text or "gbp" in price_text.lower():
                        currency = "GBP"

                merchant = str(item.get("source") or item.get("merchant") or item.get("seller") or "").strip() or None
                product_url = str(item.get("link") or item.get("product_link") or "").strip() or None
                thumbnail_url = str(item.get("thumbnail") or "").strip() or None

                # Safely extract rating
                rating = None
                raw_rating = item.get("rating")
                if raw_rating is not None:
                    try:
                        rating = float(raw_rating)
                    except (ValueError, TypeError):
                        rating = None

                # Safely extract reviews
                reviews = None
                raw_reviews = item.get("reviews") or item.get("reviews_count")
                if raw_reviews is not None:
                    try:
                        if isinstance(raw_reviews, str):
                            digits = "".join(ch for ch in raw_reviews if ch.isdigit())
                            reviews = int(digits) if digits else None
                        else:
                            reviews = int(raw_reviews)
                    except (ValueError, TypeError):
                        reviews = None

                delivery_info = str(item.get("delivery") or item.get("shipping") or "").strip() or None
                condition = str(item.get("condition") or item.get("tag") or "").strip() or None
                snippet = str(item.get("snippet") or item.get("description") or "").strip() or None

                products.append(
                    ProductEvidence(
                        source_id=f"raw_i_{rank}",
                        title=title,
                        price=price,
                        currency=currency,
                        price_text=price_text,
                        merchant=merchant,
                        product_url=product_url,
                        thumbnail_url=thumbnail_url,
                        rating=rating,
                        reviews=reviews,
                        delivery_info=delivery_info,
                        condition=condition,
                        snippet=snippet,
                        query=cleaned_query,
                        rank=rank,
                        retrieved_at=now,
                    )
                )

        except Exception:
            return []

        return products


