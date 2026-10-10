"""Tests for the deterministic router."""

from __future__ import annotations

from models import AgentMode
from workflows.router import detect_likely_mode


def test_obvious_research_local_and_shopping_questions_map_correctly() -> None:
    """The fallback router should pick the expected mode for obvious keywords."""
    assert detect_likely_mode("Compare modern LLM frameworks for Python") == AgentMode.RESEARCH
    assert detect_likely_mode("Find quiet cafés near Koramangala for studying under ₹500") == AgentMode.LOCAL
    assert detect_likely_mode("Recommend highly rated vegetarian restaurants in Indiranagar.") == AgentMode.LOCAL
    assert detect_likely_mode("Find coworking spaces near HSR Layout open late.") == AgentMode.LOCAL
    assert detect_likely_mode("Suggest family-friendly places to visit in Bengaluru this weekend.") == AgentMode.LOCAL
    assert detect_likely_mode("Compare laptop prices under 60000 for coding") == AgentMode.SHOPPING

