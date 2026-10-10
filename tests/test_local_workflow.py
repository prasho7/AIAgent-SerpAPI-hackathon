"""Unit tests for LocalWorkflow and Local Discovery pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from models import AgentMode, LocalSearchPlan, PlaceEvidence
from workflows.local_workflow import LocalWorkflow


def test_local_workflow_missing_location_clarification():
    """If no location is provided or user says 'near me', workflow must request clarification and NOT search Maps."""
    mock_gemini = MagicMock()
    mock_gemini.create_local_plan.return_value = LocalSearchPlan(
        mode=AgentMode.LOCAL,
        goal="Find cafes near me",
        location=None,
        place_query="cafes",
        criteria=["Rating", "Distance"],
        needs_clarification=True,
        clarifying_question="Which city, neighborhood, or landmark should I search around?",
    )
    mock_serpapi = MagicMock()

    workflow = LocalWorkflow(
        gemini_service=mock_gemini,
        serpapi_service=mock_serpapi,
    )

    result = workflow.run("Find quiet cafes near me")
    assert result.requires_clarification is True
    assert "Which city, neighborhood, or landmark should I search around?" in (result.clarification_question or "")
    mock_serpapi.search_places.assert_not_called()


def test_local_workflow_success_mocked():
    """End-to-end LocalWorkflow test with mocked Gemini and SerpApi."""
    now = datetime.now(timezone.utc)
    mock_gemini = MagicMock()
    mock_gemini.create_local_plan.return_value = LocalSearchPlan(
        mode=AgentMode.LOCAL,
        goal="Find quiet cafes for studying in Koramangala",
        location="Koramangala, Bengaluru",
        place_query="quiet cafes for studying",
        criteria=["quiet atmosphere", "budget under ₹500", "ratings and reviews"],
        needs_clarification=False,
        clarifying_question=None,
    )
    mock_gemini.write_local_grounded_answer.return_value = (
        "## Top Cafés in Koramangala\n\n"
        "1. **Third Wave Coffee** [P1] is a great spot with high ratings (4.5/5.0) and comfortable seating.\n"
        "2. **Dyu Art Cafe** [P2] offers a peaceful garden vibe [P2].\n\n"
        "| Place | Rating | Area |\n"
        "|---|---|---|\n"
        "| Third Wave Coffee [P1] | 4.5 | Koramangala 4th Block |\n"
        "| Dyu Art Cafe [P2] | 4.4 | Koramangala 5th Block |\n"
    )

    mock_serpapi = MagicMock()
    mock_serpapi.search_places.return_value = [
        PlaceEvidence(
            source_id="raw_p_1",
            name="Third Wave Coffee",
            address="Koramangala 4th Block, Bengaluru",
            rating=4.5,
            review_count=1200,
            price_range="₹400 for two",
            opening_hours="8 AM - 11 PM",
            phone="+91 80 12345678",
            website="https://thirdwavecoffee.in",
            maps_url="https://maps.google.com/?cid=123",
            category="Cafe",
            snippet="Specialty coffee roaster with artisan brews.",
            query="quiet cafes for studying Koramangala, Bengaluru",
            rank=1,
            retrieved_at=now,
        ),
        PlaceEvidence(
            source_id="raw_p_2",
            name="Dyu Art Cafe",
            address="Koramangala 5th Block, Bengaluru",
            rating=4.4,
            review_count=3500,
            price_range="₹500 for two",
            opening_hours="10 AM - 10 PM",
            phone="+91 80 87654321",
            website="https://dyuartcafe.com",
            maps_url="https://maps.google.com/?cid=456",
            category="Art Cafe",
            snippet="Old house converted into an art cafe.",
            query="quiet cafes for studying Koramangala, Bengaluru",
            rank=2,
            retrieved_at=now,
        ),
    ]

    workflow = LocalWorkflow(
        gemini_service=mock_gemini,
        serpapi_service=mock_serpapi,
    )

    result = workflow.run("Find quiet cafés near Koramangala for studying under ₹500")

    assert result.requires_clarification is False
    assert result.answer is not None
    assert len(result.answer.sources) == 2
    assert result.answer.sources[0].source_id == "P1"
    assert result.answer.sources[0].name == "Third Wave Coffee"
    assert result.answer.sources[1].source_id == "P2"
    assert "Third Wave Coffee" in result.answer.answer_markdown
    assert result.answer.mode == AgentMode.LOCAL
    mock_serpapi.search_places.assert_called_once_with("quiet cafes for studying", "Koramangala, Bengaluru")


def test_local_workflow_empty_maps_results():
    """If SerpApi Maps returns no places, workflow should return a graceful fallback answer."""
    mock_gemini = MagicMock()
    mock_gemini.create_local_plan.return_value = LocalSearchPlan(
        mode=AgentMode.LOCAL,
        goal="Find non-existent spots",
        location="Remote Desert",
        place_query="luxury cafes",
        criteria=["Atmosphere", "Price"],
        needs_clarification=False,
        clarifying_question=None,
    )
    mock_serpapi = MagicMock()
    mock_serpapi.search_places.return_value = []

    workflow = LocalWorkflow(
        gemini_service=mock_gemini,
        serpapi_service=mock_serpapi,
    )

    result = workflow.run("Find luxury cafes in Remote Desert")
    assert result.requires_clarification is False
    assert result.answer is not None
    assert len(result.answer.sources) == 0
    assert "could not find matching places" in result.answer.answer_markdown.lower()


def test_local_workflow_invalid_place_citations_flagged():
    """Unverified place IDs should be caught by citation validation and appended to limitations."""
    now = datetime.now(timezone.utc)
    mock_gemini = MagicMock()
    mock_gemini.create_local_plan.return_value = LocalSearchPlan(
        mode=AgentMode.LOCAL,
        goal="Find cafes",
        location="Indiranagar",
        place_query="cafes",
        criteria=["Rating", "Coffee"],
        needs_clarification=False,
        clarifying_question=None,
    )
    # Gemini references hallucinated [P99]
    mock_gemini.write_local_grounded_answer.return_value = "Check out Place 1 [P1] and Phantom Cafe [P99]."

    mock_serpapi = MagicMock()
    mock_serpapi.search_places.return_value = [
        PlaceEvidence(
            source_id="raw_1",
            name="Real Cafe",
            address="Indiranagar",
            rating=4.2,
            review_count=100,
            query="cafes Indiranagar",
            rank=1,
            retrieved_at=now,
        )
    ]

    workflow = LocalWorkflow(
        gemini_service=mock_gemini,
        serpapi_service=mock_serpapi,
    )

    result = workflow.run("Find cafes in Indiranagar")
    assert result.answer is not None
    assert any("P99" in lim for lim in result.answer.limitations)
