"""Local discovery workflow implementation coordinating planning, maps search, place ranking, and writing."""

from __future__ import annotations

from typing import Callable

from config import Settings, get_settings
from models import AgentAnswer, AgentMode, AgentRunResult, LocalSearchPlan, PlaceEvidence
from processors.citation_validator import validate_citations
from processors.evidence_processor import rank_and_curate_places
from services.gemini_service import GeminiService
from services.serpapi_service import SerpApiService


class LocalWorkflow:
    """End-to-end Local Discovery pipeline:

    1. Planning -> Gemini creates structured LocalSearchPlan with location validation
    2. Maps Search -> SerpApi executes Google Maps search for places in location
    3. Processing & Ranking -> Deduplication, rating/review ranking, ID assignment (P1..P5)
    4. Grounded Writing -> Gemini writes place recommendation brief citing [P1], [P2]
    5. Citation Check -> Deterministic validator checks [P1]..[P5] place citations
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
        """Run the complete 5-stage local discovery workflow."""
        cleaned_question = (question or "").strip()
        if not cleaned_question:
            plan = LocalSearchPlan(
                mode=AgentMode.LOCAL,
                goal="Await valid user place question.",
                location=None,
                place_query="missing question",
                criteria=["Input validation", "Route to local search"],
                needs_clarification=True,
                clarifying_question="Which city, neighborhood, or landmark should I search around?",
            )
            return AgentRunResult(
                plan=plan,
                answer=None,
                requires_clarification=True,
                clarification_question=plan.clarifying_question,
                status_message="No local question provided.",
            )

        # Stage 1: Planning and location validation
        if progress_callback:
            progress_callback(1, "Analyzing place requirements and location...")

        plan = self.gemini_service.create_local_plan(cleaned_question, preferences)

        # Check if location is missing or clarification needed
        if plan.needs_clarification or not plan.location or plan.location.lower().strip() in {"near me", "nearby", "here", "current location"}:
            clarification_q = (
                plan.clarifying_question
                if plan.clarifying_question
                else "Which city, neighborhood, or landmark should I search around?"
            )
            plan.needs_clarification = True
            plan.clarifying_question = clarification_q
            return AgentRunResult(
                plan=plan,
                answer=None,
                requires_clarification=True,
                clarification_question=clarification_q,
                status_message="Location clarification needed to search places.",
            )

        # Stage 2: Searching Google Maps places
        if progress_callback:
            progress_callback(2, f"Searching Google Maps for '{plan.place_query}' in {plan.location}...")

        raw_places = self.serpapi_service.search_places(plan.place_query, plan.location)

        # Stage 3: Processing, deduplicating, and ranking places
        if progress_callback:
            progress_callback(3, "Deduplicating and ranking places by rating and relevance...")

        curated_places = rank_and_curate_places(raw_places, criteria=plan.criteria, max_places=5)

        if not curated_places:
            limitations = ["No matching places found on Google Maps for this area and search criteria."]
            fallback_answer = AgentAnswer(
                answer_markdown=(
                    "### Place Recommendations\n\n"
                    "I could not find matching places with the current search. "
                    "Try a broader category, nearby area, or different budget."
                ),
                sources=[],
                limitations=limitations,
                mode=AgentMode.LOCAL,
            )
            return AgentRunResult(
                plan=plan,
                answer=fallback_answer,
                requires_clarification=False,
                clarification_question=None,
                status_message="No matching places found for this location.",
            )

        # Stage 4: Writing grounded local recommendation
        if progress_callback:
            progress_callback(4, f"Writing grounded place recommendations from {len(curated_places)} verified spots...")

        answer_markdown = self.gemini_service.write_local_grounded_answer(
            cleaned_question,
            plan.location,
            plan.criteria,
            curated_places,
        )

        # Stage 5: Validating citations
        if progress_callback:
            progress_callback(5, "Validating inline place citations [P1], [P2]...")

        citation_report = validate_citations(answer_markdown, curated_places)
        limitations: list[str] = []
        if not citation_report["valid"]:
            invalid_ids = ", ".join(str(s) for s in citation_report.get("invalid_source_ids", []))
            limitations.append(f"Warning: The answer referenced unverified place IDs: {invalid_ids}")

        answer = AgentAnswer(
            answer_markdown=answer_markdown,
            sources=curated_places,
            limitations=limitations,
            mode=AgentMode.LOCAL,
        )

        return AgentRunResult(
            plan=plan,
            answer=answer,
            requires_clarification=False,
            clarification_question=None,
            status_message=f"Found and analyzed {len(curated_places)} verified places in {plan.location}.",
        )

