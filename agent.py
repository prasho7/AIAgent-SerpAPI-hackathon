"""Agent coordinator routing user questions to appropriate workflows."""

from __future__ import annotations

from typing import Callable

from config import get_settings
from models import AgentMode, AgentRunResult, ResearchPlan
from workflows.local_workflow import LocalWorkflow
from workflows.research_workflow import ResearchWorkflow
from workflows.router import detect_likely_mode
from workflows.shopping_workflow import ShoppingWorkflow


def run_agent(
    question: str,
    preferences: str = "",
    progress_callback: Callable[[int, str], None] | None = None,
) -> AgentRunResult:
    """Coordinate input validation, mode routing, and workflow execution."""
    cleaned_question = (question or "").strip()

    if not cleaned_question:
        plan = ResearchPlan(
            mode=AgentMode.RESEARCH,
            goal="Await user input for research.",
            queries=["user question missing"],
            criteria=["Input validation", "Route to workflow"],
            needs_clarification=True,
            clarifying_question="Please enter a research question before starting.",
        )
        return AgentRunResult(
            plan=plan,
            answer=None,
            requires_clarification=True,
            clarification_question=plan.clarifying_question,
            status_message="Waiting for user question.",
        )

    if len(cleaned_question) > 500:
        plan = ResearchPlan(
            mode=AgentMode.RESEARCH,
            goal="Validate question length.",
            queries=[cleaned_question[:150]],
            criteria=["Input length validation", "Safety check"],
            needs_clarification=True,
            clarifying_question="Your question is too long. Please shorten it to under 500 characters.",
        )
        return AgentRunResult(
            plan=plan,
            answer=None,
            requires_clarification=True,
            clarification_question=plan.clarifying_question,
            status_message="Question exceeded maximum allowed length (500 characters).",
        )

    mode = detect_likely_mode(cleaned_question)

    if mode == AgentMode.LOCAL:
        workflow = LocalWorkflow(get_settings())
        return workflow.run(cleaned_question, preferences, progress_callback)

    if mode == AgentMode.RESEARCH:
        workflow = ResearchWorkflow(get_settings())
        return workflow.run(cleaned_question, preferences, progress_callback)

    if mode == AgentMode.SHOPPING:
        workflow = ShoppingWorkflow(get_settings())
        return workflow.run(cleaned_question, preferences, progress_callback)

    # Fallback to research workflow
    workflow = ResearchWorkflow(get_settings())
    return workflow.run(cleaned_question, preferences, progress_callback)

