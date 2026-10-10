"""Unit tests for ResearchWorkflow with mocked Gemini and SerpApi services."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from config import Settings
from models import AgentMode, ResearchPlan, SourceEvidence
from workflows.research_workflow import ResearchWorkflow


def _create_mock_evidence(count: int = 4) -> list[SourceEvidence]:
    now = datetime.now(timezone.utc)
    return [
        SourceEvidence(
            source_id=f"raw_{i}",
            title=f"Source Title {i}",
            url=f"https://example.com/source_{i}",
            snippet=f"Snippet describing topic {i} in detail.",
            query="test query",
            rank=i,
            retrieved_at=now,
        )
        for i in range(1, count + 1)
    ]


def test_research_workflow_success():
    settings = Settings(gemini_api_key="mock_key", serpapi_api_key="mock_key")
    mock_gemini = MagicMock()
    mock_serpapi = MagicMock()

    # Mock Planner
    mock_plan = ResearchPlan(
        mode=AgentMode.RESEARCH,
        goal="Compare Python AI frameworks.",
        queries=["python agent frameworks", "crewai vs autogen", "gemini agents"],
        criteria=["Ease of use", "Multi-agent support", "Gemini compatibility"],
        needs_clarification=False,
        clarifying_question=None,
    )
    mock_gemini.create_research_plan.return_value = mock_plan

    # Mock Search
    mock_serpapi.search_web.return_value = _create_mock_evidence(4)

    # Mock Writer
    mock_gemini.write_grounded_answer.return_value = (
        "## Overview\n\nLangChain and CrewAI are popular [S1]. CrewAI excels at multi-agent collaboration [S2].\n\n"
        "| Framework | Pros | Cons |\n|---|---|---|\n| CrewAI | Simple [S2] | Emerging |\n| AutoGen | Flexible [S3] | Complex |\n\n"
        "## Sources\n- [S1] Source 1\n- [S2] Source 2\n- [S3] Source 3"
    )

    workflow = ResearchWorkflow(
        settings=settings,
        gemini_service=mock_gemini,
        serpapi_service=mock_serpapi,
    )

    progress_steps = []

    def callback(step: int, msg: str):
        progress_steps.append((step, msg))

    result = workflow.run(
        question="Compare Python AI frameworks for agents",
        preferences="Focus on Gemini",
        progress_callback=callback,
    )

    assert result.requires_clarification is False
    assert result.answer is not None
    assert result.answer.mode == AgentMode.RESEARCH
    assert len(result.answer.sources) == 4
    assert result.answer.sources[0].source_id == "S1"
    assert result.answer.sources[1].source_id == "S2"
    assert "[S1]" in result.answer.answer_markdown
    assert len(progress_steps) == 5
    assert progress_steps[0][0] == 1
    assert progress_steps[4][0] == 5


def test_research_workflow_clarification_needed():
    settings = Settings(gemini_api_key="mock_key", serpapi_api_key="mock_key")
    mock_gemini = MagicMock()
    mock_serpapi = MagicMock()

    mock_plan = ResearchPlan(
        mode=AgentMode.RESEARCH,
        goal="Clarify vague query.",
        queries=["vague query"],
        criteria=["Topic specificity", "Scope"],
        needs_clarification=True,
        clarifying_question="Could you specify which programming language or domain you are interested in?",
    )
    mock_gemini.create_research_plan.return_value = mock_plan

    workflow = ResearchWorkflow(
        settings=settings,
        gemini_service=mock_gemini,
        serpapi_service=mock_serpapi,
    )

    result = workflow.run("tell me about frameworks")

    assert result.requires_clarification is True
    assert result.clarification_question == "Could you specify which programming language or domain you are interested in?"
    assert result.answer is None
    # Ensure search was NOT called when clarification is needed
    mock_serpapi.search_web.assert_not_called()


def test_research_workflow_empty_search_results():
    settings = Settings(gemini_api_key="mock_key", serpapi_api_key="mock_key")
    mock_gemini = MagicMock()
    mock_serpapi = MagicMock()

    mock_plan = ResearchPlan(
        mode=AgentMode.RESEARCH,
        goal="Obscure search topic.",
        queries=["obscure topic query"],
        criteria=["Availability", "Documentation"],
        needs_clarification=False,
    )
    mock_gemini.create_research_plan.return_value = mock_plan
    mock_serpapi.search_web.return_value = []

    workflow = ResearchWorkflow(
        settings=settings,
        gemini_service=mock_gemini,
        serpapi_service=mock_serpapi,
    )

    result = workflow.run("something very obscure")

    assert result.requires_clarification is False
    assert result.answer is None
    assert "could not retrieve usable live sources" in result.status_message.lower()
    # Ensure writer was NEVER called when evidence is empty
    mock_gemini.write_grounded_answer.assert_not_called()


def test_research_workflow_invalid_citation_flagged():
    settings = Settings(gemini_api_key="mock_key", serpapi_api_key="mock_key")
    mock_gemini = MagicMock()
    mock_serpapi = MagicMock()

    mock_plan = ResearchPlan(
        mode=AgentMode.RESEARCH,
        goal="Test citations.",
        queries=["test query"],
        criteria=["Criterion 1", "Criterion 2"],
        needs_clarification=False,
    )
    mock_gemini.create_research_plan.return_value = mock_plan
    mock_serpapi.search_web.return_value = _create_mock_evidence(2)  # Generates S1 and S2

    # Writer hallucinates [S99]
    mock_gemini.write_grounded_answer.return_value = (
        "Claim backed by S1 [S1]. Claim backed by nonexistent source [S99]."
    )

    workflow = ResearchWorkflow(
        settings=settings,
        gemini_service=mock_gemini,
        serpapi_service=mock_serpapi,
    )

    result = workflow.run("test citation validation")

    assert result.answer is not None
    assert len(result.answer.limitations) == 1
    assert "S99" in result.answer.limitations[0]
    mock_gemini.write_grounded_answer.assert_called_once()

