"""Configuration helpers for environment-based settings."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


class MissingSettingsError(ValueError):
    """Raised when a workflow requires configuration that is not set."""


@dataclass(frozen=True)
class Settings:
    """Environment-backed application settings."""

    gemini_api_key: str = ""
    serpapi_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    app_env: str = "development"
    shopping_gl: str = "in"
    shopping_hl: str = "en"
    shopping_market_label: str = "India"


def get_settings(require_api_keys: bool = False) -> Settings:
    """Return validated settings for the application.

    Args:
        require_api_keys: when True, require the configured API values for a workflow.
    """
    settings = Settings(
        gemini_api_key=(os.getenv("GEMINI_API_KEY") or "").strip(),
        serpapi_api_key=(os.getenv("SERPAPI_API_KEY") or "").strip(),
        gemini_model=(os.getenv("GEMINI_MODEL") or "gemini-3.5-flash-lite").strip(),
        app_env=(os.getenv("APP_ENV") or "development").strip(),
        shopping_gl=(os.getenv("SHOPPING_GL") or "in").strip().lower(),
        shopping_hl=(os.getenv("SHOPPING_HL") or "en").strip().lower(),
        shopping_market_label=(os.getenv("SHOPPING_MARKET_LABEL") or "India").strip(),
    )

    if require_api_keys:
        missing = []
        if not settings.gemini_api_key:
            missing.append("GEMINI_API_KEY")
        if not settings.serpapi_api_key:
            missing.append("SERPAPI_API_KEY")
        if not settings.gemini_model:
            missing.append("GEMINI_MODEL")
        if missing:
            joined = ", ".join(missing)
            raise MissingSettingsError(
                f"Missing required configuration for an API workflow: {joined}. "
                "Set the values in a local .env file before starting the workflow."
            )

    return settings
