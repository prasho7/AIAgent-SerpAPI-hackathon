"""Unit tests for Follow-up Questions MVP."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from models import (
    AgentMode,
    FollowUpContext,
    FollowUpTurn,
    PlaceEvidence,
    ProductEvidence,
    SourceEvidence,
)
from workflows.follow_up import (
    ADDITIONAL_EVIDENCE_NOTICE,
    FRESH_EVIDENCE_NOTICE,
    requires_fresh_evidence,
    run_follow_up,
)


def test_follow_up_context_and_turn_models():
    """FollowUpContext and FollowUpTurn should validate and preserve only safe, compact fields."""
    now = datetime.now(timezone.utc)
    source = SourceEvidence(
        source_id="S1",
        title="Test Source",
        url="https://example.com",
        snippet="Snippet here",
        query="test query",
        rank=1,
        retrieved_at=now,
    )

    ctx = FollowUpContext(
        mode=AgentMode.RESEARCH,
        original_question="Compare Python agent frameworks",
        preferences="",
        plan_goal="Compare frameworks",
        plan_criteria=["Ease of use", "Performance"],
        prior_answer="LangChain [S1] is popular.",
        sources=[source],
        limitations=[],
        created_at=now,
    )
    assert ctx.mode == AgentMode.RESEARCH
    assert len(ctx.sources) == 1
    assert ctx.sources[0].source_id == "S1"

    turn = FollowUpTurn(
        question="Which is better for beginners?",
        answer="LangChain [S1] is recommended for beginners.",
        citation_warning=None,
        created_at=now,
    )
    assert turn.question == "Which is better for beginners?"
    assert turn.citation_warning is None


def test_freshness_keyword_detection():
    """Freshness keyword detection flags queries asking for live, updated, or re-search data."""
    # Positive triggers
    assert requires_fresh_evidence("What is the latest price?") is True
    assert requires_fresh_evidence("Is it open now?") is True
    assert requires_fresh_evidence("Find more options for me") is True
    assert requires_fresh_evidence("Is this in stock today?") is True
    assert requires_fresh_evidence("Check online right now") is True
    assert requires_fresh_evidence("Search again for laptops") is True
    assert requires_fresh_evidence("What are the opening hours today?") is True
    assert requires_fresh_evidence("Can you re-search this?") is True

    # Negative triggers (grounded follow-ups from current evidence)
    assert requires_fresh_evidence("Compare the first two options in more detail.") is False
    assert requires_fresh_evidence("Which option is cheapest?") is False
    assert requires_fresh_evidence("Which option has the strongest rating?") is False
    assert requires_fresh_evidence("Summarize this for a beginner.") is False
    assert requires_fresh_evidence("Why did you recommend this one?") is False
    assert requires_fresh_evidence("What could not be verified?") is False


def test_freshness_follow_up_bypasses_gemini_and_serpapi():
    """When a freshness trigger occurs, run_follow_up returns the exact notice with zero API calls."""
    now = datetime.now(timezone.utc)
    ctx = FollowUpContext(
        mode=AgentMode.SHOPPING,
        original_question="Find laptop under 60k",
        preferences="",
        plan_goal="Find laptop",
        plan_criteria=["Price"],
        prior_answer="Laptop A [I1] is ₹55,000.",
        sources=[
            ProductEvidence(
                source_id="I1",
                title="Laptop A",
                price=55000.0,
                merchant="Amazon",
                query="laptop",
                rank=1,
                retrieved_at=now,
            )
        ],
        limitations=[],
        created_at=now,
    )

    mock_gemini = MagicMock()

    turn, error = run_follow_up(
        context=ctx,
        follow_up_question="Is it in stock today with new price?",
        history=[],
        gemini_service=mock_gemini,
    )

    assert turn is None
    assert error == FRESH_EVIDENCE_NOTICE
    mock_gemini.write_follow_up.assert_not_called()


def test_out_of_evidence_follow_up_returns_additional_evidence_notice():
    """When a follow-up asks about an entity/topic not present in evidence, it returns the additional-evidence notice."""
    now = datetime.now(timezone.utc)
    ctx = FollowUpContext(
        mode=AgentMode.RESEARCH,
        original_question="FastAPI vs Streamlit",
        preferences="",
        plan_goal="Compare tools",
        plan_criteria=["Ease of use"],
        prior_answer="FastAPI [S1] and Streamlit [S2] are compared.",
        sources=[
            SourceEvidence(
                source_id="S1",
                title="FastAPI Documentation",
                url="https://fastapi.tiangolo.com",
                snippet="High performance web framework for building APIs.",
                query="fastapi",
                rank=1,
                retrieved_at=now,
            ),
            SourceEvidence(
                source_id="S2",
                title="Streamlit Documentation",
                url="https://streamlit.io",
                snippet="Fastest way to build data apps in Python.",
                query="streamlit",
                rank=2,
                retrieved_at=now,
            ),
        ],
        limitations=[],
        created_at=now,
    )

    mock_gemini = MagicMock()

    # Query asking about completely unmentioned topic "Django"
    turn, error = run_follow_up(
        context=ctx,
        follow_up_question="What about Django?",
        history=[],
        gemini_service=mock_gemini,
    )

    assert turn is None
    assert error == ADDITIONAL_EVIDENCE_NOTICE
    assert "additional live evidence" in error
    mock_gemini.write_follow_up.assert_not_called()


def test_normal_follow_up_executes_grounded_writer_with_citations():
    """Grounded follow-up calls Gemini once with existing evidence and validates citations."""
    now = datetime.now(timezone.utc)
    ctx = FollowUpContext(
        mode=AgentMode.LOCAL,
        original_question="Quiet cafes in Koramangala",
        preferences="",
        plan_goal="Find cafes",
        plan_criteria=["Quiet atmosphere"],
        prior_answer="Third Wave Coffee [P1] is highly rated.",
        sources=[
            PlaceEvidence(
                source_id="P1",
                name="Third Wave Coffee",
                rating=4.5,
                review_count=500,
                query="quiet cafes",
                rank=1,
                retrieved_at=now,
            )
        ],
        limitations=[],
        created_at=now,
    )

    mock_gemini = MagicMock()
    mock_gemini.write_follow_up.return_value = (
        "Third Wave Coffee [P1] has a 4.5 rating with 500 reviews."
    )

    turn, error = run_follow_up(
        context=ctx,
        follow_up_question="Why did you recommend the first cafe?",
        history=[],
        gemini_service=mock_gemini,
    )

    assert error is None
    assert turn is not None
    assert turn.question == "Why did you recommend the first cafe?"
    assert "[P1]" in turn.answer
    assert turn.citation_warning is None
    mock_gemini.write_follow_up.assert_called_once()


def test_follow_up_citation_warning_on_invalid_id():
    """Invalid citations produce a non-blocking warning without discarding the response."""
    now = datetime.now(timezone.utc)
    ctx = FollowUpContext(
        mode=AgentMode.RESEARCH,
        original_question="Streamlit vs FastAPI",
        preferences="",
        plan_goal="Compare tools",
        plan_criteria=["Ease of use"],
        prior_answer="Streamlit [S1] is easier.",
        sources=[
            SourceEvidence(
                source_id="S1",
                title="Streamlit Docs",
                url="https://streamlit.io",
                snippet="Documentation",
                query="streamlit",
                rank=1,
                retrieved_at=now,
            )
        ],
        limitations=[],
        created_at=now,
    )

    mock_gemini = MagicMock()
    mock_gemini.write_follow_up.return_value = (
        "Streamlit [S1] is easier, but [S99] is faster."
    )

    turn, error = run_follow_up(
        context=ctx,
        follow_up_question="Which is faster?",
        history=[],
        gemini_service=mock_gemini,
    )

    assert error is None
    assert turn is not None
    assert turn.citation_warning is not None
    assert "could not be validated" in turn.citation_warning


def test_follow_up_empty_question_handling():
    """Empty follow-up question returns an explicit client warning without calling services."""
    now = datetime.now(timezone.utc)
    ctx = FollowUpContext(
        mode=AgentMode.RESEARCH,
        original_question="Topic",
        preferences="",
        plan_goal="Goal",
        plan_criteria=["Criteria"],
        prior_answer="Answer",
        sources=[],
        limitations=[],
        created_at=now,
    )

    mock_gemini = MagicMock()
    turn, error = run_follow_up(
        context=ctx,
        follow_up_question="   ",
        history=[],
        gemini_service=mock_gemini,
    )

    assert turn is None
    assert error == "Enter a follow-up question first."
    mock_gemini.write_follow_up.assert_not_called()


def test_follow_up_input_state_reset_on_success_and_preservation_on_failure():
    """Prove that success clears the next follow-up input while failure preserves typed text."""
    now = datetime.now(timezone.utc)
    ctx = FollowUpContext(
        mode=AgentMode.RESEARCH,
        original_question="Topic",
        preferences="",
        plan_goal="Goal",
        plan_criteria=["Criteria"],
        prior_answer="Answer [S1]",
        sources=[
            SourceEvidence(
                source_id="S1",
                title="Source 1",
                url="https://example.com",
                snippet="Snippet",
                query="topic",
                rank=1,
                retrieved_at=now,
            )
        ],
        limitations=[],
        created_at=now,
    )

    # Simulated Streamlit session state
    session_state = {
        "follow_up_input_box": "Why is option 1 better?",
        "_clear_follow_up_input": False,
        "follow_up_history": [],
    }

    def simulate_render_input_step(state: dict) -> None:
        """Helper mirroring app.py pre-widget input reset logic."""
        if state.get("_clear_follow_up_input"):
            state["follow_up_input_box"] = ""
            state["_clear_follow_up_input"] = False

    # 1. SUCCESS SCENARIO
    mock_gemini = MagicMock()
    mock_gemini.write_follow_up.return_value = "Option 1 [S1] is better because of simplicity."

    # Execute follow-up logic
    turn, error_msg = run_follow_up(
        context=ctx,
        follow_up_question=session_state["follow_up_input_box"],
        history=session_state["follow_up_history"],
        gemini_service=mock_gemini,
    )

    assert error_msg is None
    assert turn is not None

    # App logic on success: append turn and flag pending reset
    session_state["follow_up_history"].append(turn)
    session_state["_clear_follow_up_input"] = True

    # Next rerun: pre-widget logic clears the text input
    simulate_render_input_step(session_state)

    assert session_state["follow_up_input_box"] == ""
    assert session_state["_clear_follow_up_input"] is False
    assert len(session_state["follow_up_history"]) == 1

    # 2. FAILURE / FRESHNESS NOTICE SCENARIO
    # User types a question that triggers a freshness warning
    session_state["follow_up_input_box"] = "Is it in stock right now?"

    turn, error_msg = run_follow_up(
        context=ctx,
        follow_up_question=session_state["follow_up_input_box"],
        history=session_state["follow_up_history"],
        gemini_service=mock_gemini,
    )

    assert turn is None
    assert error_msg == FRESH_EVIDENCE_NOTICE

    # App logic on error: no pending reset is set, no rerun is triggered
    assert session_state.get("_clear_follow_up_input") is False

    # Next render still preserves the user's typed question for editing/retry
    simulate_render_input_step(session_state)
    assert session_state["follow_up_input_box"] == "Is it in stock right now?"

