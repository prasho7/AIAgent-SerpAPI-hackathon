"""Unit tests for SerpApiService connectivity testing with mocked HTTP requests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests

from config import Settings
from services.serpapi_service import SerpApiService


def test_test_connection_missing_api_key():
    settings = Settings(serpapi_api_key="")
    service = SerpApiService(settings)
    result = service.test_connection()

    assert result["success"] is False
    assert "SERPAPI_API_KEY is missing" in result["message"]
    assert result["results"] == []


@patch("requests.get")
def test_test_connection_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "organic_results": [
            {
                "title": "SerpApi Documentation",
                "link": "https://serpapi.com/docs",
                "snippet": "Official documentation for SerpApi Google Search API.",
            },
            {
                "title": "SerpApi Python Library",
                "link": "https://github.com/serpapi/google-search-results-python",
                "snippet": "Python package for SerpApi.",
            },
            {
                "title": "SerpApi API Status",
                "link": "https://status.serpapi.com",
                "snippet": "Uptime and status for SerpApi.",
            },
            {
                "title": "Fourth Result - Should Be Excluded",
                "link": "https://serpapi.com/extra",
                "snippet": "Extra result.",
            },
        ]
    }
    mock_get.return_value = mock_resp

    settings = Settings(serpapi_api_key="mock_serpapi_key")
    service = SerpApiService(settings)
    result = service.test_connection()

    assert result["success"] is True
    assert "Successfully connected to SerpApi" in result["message"]
    assert len(result["results"]) == 3
    assert result["results"][0]["title"] == "SerpApi Documentation"
    assert result["results"][0]["url"] == "https://serpapi.com/docs"
    assert result["results"][0]["snippet"] == "Official documentation for SerpApi Google Search API."

    mock_get.assert_called_once_with(
        "https://serpapi.com/search.json",
        params={
            "engine": "google",
            "q": "SerpApi official documentation",
            "api_key": "mock_serpapi_key",
            "num": 3,
        },
        timeout=30,
    )


@patch("requests.get")
def test_test_connection_unauthorized_status_code(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_get.return_value = mock_resp

    settings = Settings(serpapi_api_key="invalid_key")
    service = SerpApiService(settings)
    result = service.test_connection()

    assert result["success"] is False
    assert "authentication failed" in result["message"].lower()
    assert result["results"] == []


@patch("requests.get")
def test_test_connection_quota_status_code(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_get.return_value = mock_resp

    settings = Settings(serpapi_api_key="mock_key")
    service = SerpApiService(settings)
    result = service.test_connection()

    assert result["success"] is False
    assert "quota or rate limit" in result["message"].lower()
    assert result["results"] == []


@patch("requests.get")
def test_test_connection_json_error_invalid_key(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"error": "Invalid API key"}
    mock_get.return_value = mock_resp

    settings = Settings(serpapi_api_key="invalid_key")
    service = SerpApiService(settings)
    result = service.test_connection()

    assert result["success"] is False
    assert "authentication failed" in result["message"].lower()


@patch("requests.get")
def test_test_connection_json_error_quota(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"error": "Your searches per month limit has been reached"}
    mock_get.return_value = mock_resp

    settings = Settings(serpapi_api_key="mock_key")
    service = SerpApiService(settings)
    result = service.test_connection()

    assert result["success"] is False
    assert "quota or search limit" in result["message"].lower()


@patch("requests.get")
def test_test_connection_empty_results(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"organic_results": []}
    mock_get.return_value = mock_resp

    settings = Settings(serpapi_api_key="mock_key")
    service = SerpApiService(settings)
    result = service.test_connection()

    assert result["success"] is False
    assert "no organic search results" in result["message"].lower()


@patch("requests.get")
def test_test_connection_malformed_json(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.side_effect = ValueError("Invalid JSON")
    mock_get.return_value = mock_resp

    settings = Settings(serpapi_api_key="mock_key")
    service = SerpApiService(settings)
    result = service.test_connection()

    assert result["success"] is False
    assert "invalid or malformed json" in result["message"].lower()


@patch("requests.get")
def test_test_connection_timeout(mock_get):
    mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

    settings = Settings(serpapi_api_key="mock_key")
    service = SerpApiService(settings)
    result = service.test_connection()

    assert result["success"] is False
    assert "timed out" in result["message"].lower()


@patch("requests.get")
def test_test_connection_connection_error(mock_get):
    mock_get.side_effect = requests.exceptions.ConnectionError("Failed to connect")

    settings = Settings(serpapi_api_key="mock_key")
    service = SerpApiService(settings)
    result = service.test_connection()

    assert result["success"] is False
    assert "network error" in result["message"].lower()


@patch("requests.get")
def test_search_places_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "local_results": [
            {
                "title": "Third Wave Coffee",
                "address": "Koramangala, Bengaluru",
                "rating": 4.5,
                "reviews": 1250,
                "price": "₹₹",
                "operating_hours": "8 AM - 11 PM",
                "phone": "+91 80 12345678",
                "website": "https://thirdwavecoffee.in",
                "link": "https://maps.google.com/?cid=123",
                "type": "Coffee shop",
                "description": "Specialty artisan coffee roasters.",
            }
        ]
    }
    mock_get.return_value = mock_resp

    settings = Settings(serpapi_api_key="mock_key")
    service = SerpApiService(settings)
    places = service.search_places("quiet cafes", "Koramangala")

    assert len(places) == 1
    p = places[0]
    assert p.name == "Third Wave Coffee"
    assert p.address == "Koramangala, Bengaluru"
    assert p.rating == 4.5
    assert p.review_count == 1250
    assert p.price_range == "₹₹"
    assert p.category == "Coffee shop"
    assert p.maps_url == "https://maps.google.com/?cid=123"


@patch("requests.get")
def test_search_places_error_handling(mock_get):
    mock_get.side_effect = requests.exceptions.Timeout("Timed out")

    settings = Settings(serpapi_api_key="mock_key")
    service = SerpApiService(settings)
    places = service.search_places("quiet cafes", "Koramangala")
    assert places == []


@patch("requests.get")
def test_search_products_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "shopping_results": [
            {
                "title": "Lenovo IdeaPad Slim 3 15-inch",
                "extracted_price": 54990.0,
                "currency": "INR",
                "price": "₹54,990",
                "source": "Amazon.in",
                "link": "https://amazon.in/dp/sample",
                "rating": 4.4,
                "reviews": 1200,
                "delivery": "Free delivery",
                "condition": "New",
                "snippet": "16GB RAM, 512GB SSD.",
            }
        ]
    }
    mock_get.return_value = mock_resp

    settings = Settings(serpapi_api_key="mock_key", shopping_gl="in", shopping_hl="en", shopping_market_label="India")
    service = SerpApiService(settings)
    products = service.search_products("laptop for coding under 60000 inr")

    assert len(products) == 1
    prod = products[0]
    assert prod.title == "Lenovo IdeaPad Slim 3 15-inch"
    assert prod.price == 54990.0
    assert prod.price_text == "₹54,990"
    assert prod.merchant == "Amazon.in"
    assert prod.rating == 4.4
    assert prod.reviews == 1200
    assert prod.delivery_info == "Free delivery"

    # Verify gl and hl parameters were explicitly sent
    called_params = mock_get.call_args[1]["params"]
    assert called_params["engine"] == "google_shopping"
    assert called_params["gl"] == "in"
    assert called_params["hl"] == "en"


@patch("requests.get")
def test_search_products_locale_isolation_from_research_and_maps(mock_get):
    """Confirm research and maps requests do NOT receive shopping-only gl/hl locale parameters."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"organic_results": [], "local_results": []}
    mock_get.return_value = mock_resp

    settings = Settings(serpapi_api_key="mock_key", shopping_gl="in", shopping_hl="en")
    service = SerpApiService(settings)

    # 1. Research query
    service.search_web(["test query"])
    research_params = mock_get.call_args[1]["params"]
    assert research_params["engine"] == "google"
    assert "gl" not in research_params
    assert "hl" not in research_params

    # 2. Local Maps query
    service.search_places("cafe", "Koramangala")
    maps_params = mock_get.call_args[1]["params"]
    assert maps_params["engine"] == "google_maps"
    assert "gl" not in maps_params
    assert "hl" not in maps_params


@patch("requests.get")
def test_search_products_error_handling(mock_get):
    mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

    settings = Settings(serpapi_api_key="mock_key")
    service = SerpApiService(settings)
    products = service.search_products("laptop for coding")
    assert products == []



