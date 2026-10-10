"""Unit tests for GeminiService connectivity testing with mocked Gemini API."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from google.genai import errors

from config import Settings
from services.gemini_service import GeminiService


def test_test_connection_missing_api_key():
    settings = Settings(gemini_api_key="", gemini_model="gemini-3.5-flash")
    service = GeminiService(settings)
    result = service.test_connection()

    assert result["success"] is False
    assert "GEMINI_API_KEY is missing" in result["message"]
    assert result["response_text"] is None


def test_test_connection_missing_model():
    settings = Settings(gemini_api_key="mock_key", gemini_model="")
    service = GeminiService(settings)
    result = service.test_connection()

    assert result["success"] is False
    assert "GEMINI_MODEL is missing" in result["message"]
    assert result["response_text"] is None


@patch("google.genai.Client")
def test_test_connection_success(mock_client_cls):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Gemini connection successful."
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    settings = Settings(gemini_api_key="mock_key", gemini_model="gemini-3.5-flash")
    service = GeminiService(settings)
    result = service.test_connection()

    assert result["success"] is True
    assert "Successfully connected to Gemini" in result["message"]
    assert result["response_text"] == "Gemini connection successful."
    mock_client.models.generate_content.assert_called_once_with(
        model="gemini-3.5-flash",
        contents="Respond with 'Gemini connection successful.' in 5 words or less.",
    )


@patch("google.genai.Client")
def test_test_connection_empty_response(mock_client_cls):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = ""
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    settings = Settings(gemini_api_key="mock_key", gemini_model="gemini-3.5-flash")
    service = GeminiService(settings)
    result = service.test_connection()

    assert result["success"] is False
    assert "empty response" in result["message"].lower()
    assert result["response_text"] is None


@patch("google.genai.Client")
def test_test_connection_invalid_api_key(mock_client_cls):
    mock_client = MagicMock()
    err = errors.APIError(401, {"error": {"message": "API_KEY_INVALID"}})
    mock_client.models.generate_content.side_effect = err
    mock_client_cls.return_value = mock_client

    settings = Settings(gemini_api_key="mock_key", gemini_model="gemini-3.5-flash")
    service = GeminiService(settings)
    result = service.test_connection()

    assert result["success"] is False
    assert "authentication failed" in result["message"].lower()


@patch("google.genai.Client")
def test_test_connection_quota_exceeded(mock_client_cls):
    mock_client = MagicMock()
    err = errors.APIError(429, {"error": {"message": "RESOURCE_EXHAUSTED"}})
    mock_client.models.generate_content.side_effect = err
    mock_client_cls.return_value = mock_client

    settings = Settings(gemini_api_key="mock_key", gemini_model="gemini-3.5-flash")
    service = GeminiService(settings)
    result = service.test_connection()

    assert result["success"] is False
    assert "quota or rate limit exceeded" in result["message"].lower()


@patch("google.genai.Client")
def test_test_connection_model_not_found(mock_client_cls):
    mock_client = MagicMock()
    err = errors.APIError(404, {"error": {"message": "models/invalid-model is not found"}})
    mock_client.models.generate_content.side_effect = err
    mock_client_cls.return_value = mock_client

    settings = Settings(gemini_api_key="mock_key", gemini_model="invalid-model")
    service = GeminiService(settings)
    result = service.test_connection()

    assert result["success"] is False
    assert "unavailable or not found" in result["message"].lower()


@patch("google.genai.Client")
def test_test_connection_timeout(mock_client_cls):
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = TimeoutError("Connection timed out")
    mock_client_cls.return_value = mock_client

    settings = Settings(gemini_api_key="mock_key", gemini_model="gemini-3.5-flash")
    service = GeminiService(settings)
    result = service.test_connection()

    assert result["success"] is False
    assert "timeout" in result["message"].lower()


@patch("google.genai.Client")
def test_test_connection_503_high_demand(mock_client_cls):
    mock_client = MagicMock()
    err_payload = {
        "error": {
            "code": 503,
            "message": "This model is currently experiencing high demand. Spikes in demand are usually temporary.",
            "status": "UNAVAILABLE",
        }
    }
    err = errors.APIError(503, err_payload)
    mock_client.models.generate_content.side_effect = err
    mock_client_cls.return_value = mock_client

    settings = Settings(gemini_api_key="mock_key", gemini_model="gemini-2.5-flash")
    service = GeminiService(settings)
    result = service.test_connection()

    assert result["success"] is False
    assert result["message"] == "Gemini is temporarily busy. Please wait a moment and try the same request again."
    # Assert raw payload / error dict does not leak
    assert "503" not in result["message"]
    assert "UNAVAILABLE" not in result["message"]
    assert "payload" not in result["message"]


def test_normalize_gemini_error_helper():
    from services.gemini_service import normalize_gemini_error

    err_503 = Exception("503 UNAVAILABLE. {'error': {'message': 'high demand'}}")
    msg_503 = normalize_gemini_error(err_503)
    assert msg_503 == "Gemini is temporarily busy. Please wait a moment and try the same request again."

    err_auth = Exception("API_KEY_INVALID: Key not valid")
    msg_auth = normalize_gemini_error(err_auth)
    assert "authentication failed" in msg_auth.lower()

    err_quota = Exception("RESOURCE_EXHAUSTED: quota exceeded")
    msg_quota = normalize_gemini_error(err_quota)
    assert "quota or rate limit" in msg_quota.lower()

