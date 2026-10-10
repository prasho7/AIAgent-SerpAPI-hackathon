"""Research workflow implementation coordinating planning, search, processing, and writing."""

from __future__ import annotations

from typing import Callable

from config import Settings, get_settings
from models import AgentAnswer, AgentMode, AgentRunResult, ResearchPlan, SourceEvidence
from processors.citation_validator import validate_citations
from processors.evidence_processor import process_evidence
from services.gemini_service import GeminiService
from services.serpapi_service import SerpApiService


class ResearchWorkflow:
    """End-to-end research pipeline:

    1. Planning -> Gemini creates structured ResearchPlan
    2. Search -> SerpApi executes multi-query web search
    3. Evidence Processing -> Deduplication, source IDs (S1, S2, ...), selection
    4. Grounded Writing -> Gemini synthesizes answer strictly from evidence
    5. Citation Check -> Deterministic validator flags invalid source references
    """

    def __init__(
        self,
        settings: Settings | None = None,
        gemini_service: GeminiService | None = None,
        serpapi_service: SerpApiService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.gemini_service = gemini_service or GeminiService(self.settings)
        self.serpapi_service = serpapi_service or SerpApiService(self.settings)

    def run(
        self,
        question: str,
        preferences: str = "",
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> AgentRunResult:
        """Run the complete 5-stage research workflow."""
        cleaned_question = (question or "").strip()
        if not cleaned_question:
            plan = ResearchPlan(
                mode=AgentMode.RESEARCH,
                goal="Await valid user question.",
                queries=["missing user question"],
                criteria=["Input validation", "Route to research"],
                needs_clarification=True,
                clarifying_question="Please enter a research question before starting.",
            )
            return AgentRunResult(
                plan=plan,
                answer=None,
                requires_clarification=True,
                clarification_question=plan.clarifying_question,
                status_message="No question provided.",
            )

        # Stage 1: Planning
        if progress_callback:
            progress_callback(1, "Planning research strategy and search queries...")

        plan = self.gemini_service.create_research_plan(cleaned_question, preferences)

        if plan.needs_clarification and plan.clarifying_question:
            return AgentRunResult(
                plan=plan,
                answer=None,
                requires_clarification=True,
                clarification_question=plan.clarifying_question,
                status_message="Clarification needed to proceed with research.",
            )

        # Stage 2: Searching live sources
        if progress_callback:
            query_count = len(plan.queries)
            progress_callback(2, f"Searching live web sources with {query_count} focused queries...")

        raw_evidence = self.serpapi_service.search_web(plan.queries)

        # Stage 3: Preparing evidence
        if progress_callback:
            progress_callback(3, "Processing, deduplicating, and indexing evidence...")

        processed_evidence = process_evidence(raw_evidence, max_sources=12)

        if not processed_evidence:
            return AgentRunResult(
                plan=plan,
                answer=None,
                requires_clarification=False,
                clarification_question=None,
                status_message="I could not retrieve usable live sources for this request. Please try again, rephrase the question, or start a new request later.",
            )

        # Stage 4: Writing grounded answer
        if progress_callback:
            progress_callback(4, f"Writing grounded answer from {len(processed_evidence)} sources...")

        answer_markdown = self.gemini_service.write_grounded_answer(
            cleaned_question,
            plan.criteria,
            processed_evidence,
        )

        # Stage 5: Checking citations
        if progress_callback:
            progress_callback(5, "Validating inline source citations...")

        citation_report = validate_citations(answer_markdown, processed_evidence)
        limitations: list[str] = []
        if not citation_report["valid"]:
            invalid_ids = ", ".join(str(s) for s in citation_report.get("invalid_source_ids", []))
            limitations.append(f"Warning: The answer referenced unverified source IDs: {invalid_ids}")

        answer = AgentAnswer(
            answer_markdown=answer_markdown,
            sources=processed_evidence,
            limitations=limitations,
            mode=AgentMode.RESEARCH,
        )

        return AgentRunResult(
            plan=plan,
            answer=answer,
            requires_clarification=False,
            clarification_question=None,
            status_message=f"Research completed successfully with {len(processed_evidence)} live sources.",
        )
