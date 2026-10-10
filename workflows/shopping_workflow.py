"""Smart shopping workflow implementation coordinating planning, product search, ranking, and grounded writing."""

from __future__ import annotations

from typing import Callable

from config import Settings, get_settings
from models import AgentAnswer, AgentMode, AgentRunResult, ProductEvidence, ShoppingPlan
from processors.citation_validator import validate_citations
from processors.evidence_processor import rank_and_curate_products
from services.gemini_service import GeminiService
from services.serpapi_service import SerpApiService


class ShoppingWorkflow:
    """End-to-end Smart Shopping pipeline:

    1. Planning -> Gemini creates structured ShoppingPlan with category & budget validation
    2. Product Search -> SerpApi executes Google Shopping search for listings
    3. Processing & Ranking -> Deduplication, budget fit, rating/review ranking, ID assignment (I1..I5)
    4. Grounded Writing -> Gemini writes product comparison and recommendation brief citing [I1], [I2]
    5. Citation Check -> Deterministic validator checks [I1]..[I5] product citations
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
        """Run the complete 5-stage smart shopping workflow."""
        cleaned_question = (question or "").strip()
        if not cleaned_question:
            plan = ShoppingPlan(
                mode=AgentMode.SHOPPING,
                goal="Await valid user shopping question.",
                product_query="missing question",
                budget_amount=None,
                currency=None,
                budget_text=None,
                criteria=["Input validation", "Route to shopping search"],
                needs_clarification=True,
                clarifying_question="What product category are you shopping for?",
            )
            return AgentRunResult(
                plan=plan,
                answer=None,
                requires_clarification=True,
                clarification_question=plan.clarifying_question,
                status_message="No shopping question provided.",
            )

        # Stage 1: Planning and category/budget validation
        if progress_callback:
            progress_callback(1, "Analyzing product requirements and budget constraints...")

        plan = self.gemini_service.create_shopping_plan(cleaned_question, preferences)

        # Check if clarification is needed for category or budget
        if plan.needs_clarification or not plan.product_query or plan.product_query.lower().strip() in {"product", "item", "shopping", "buy"}:
            clarification_q = (
                plan.clarifying_question
                if plan.clarifying_question
                else "What budget should I use? You can provide an amount and currency, such as ₹60,000 or $800, or say 'no budget limit.'"
            )
            plan.needs_clarification = True
            plan.clarifying_question = clarification_q
            return AgentRunResult(
                plan=plan,
                answer=None,
                requires_clarification=True,
                clarification_question=clarification_q,
                status_message="Clarification needed on product category or budget limit.",
            )

        # Stage 2: Searching Google Shopping
        if progress_callback:
            progress_callback(2, f"Searching Google Shopping for '{plan.product_query}'...")

        raw_products = self.serpapi_service.search_products(plan.product_query)

        # Stage 3: Processing, deduplicating, and ranking products
        if progress_callback:
            progress_callback(3, "Deduplicating and ranking products by budget fit and rating...")

        curated_products = rank_and_curate_products(
            raw_products,
            budget_amount=plan.budget_amount,
            criteria=plan.criteria,
            max_products=5,
        )

        if not curated_products:
            limitations = ["No matching product listings found on Google Shopping for this query."]
            fallback_answer = AgentAnswer(
                answer_markdown=(
                    "### Shopping Recommendations\n\n"
                    "I could not find matching product listings with the current search. "
                    "Try specifying a broader product category, different keywords, or adjusting the budget."
                ),
                sources=[],
                limitations=limitations,
                mode=AgentMode.SHOPPING,
            )
            return AgentRunResult(
                plan=plan,
                answer=fallback_answer,
                requires_clarification=False,
                clarification_question=None,
                status_message="No matching products found on Google Shopping.",
            )

        # Stage 4: Writing grounded shopping recommendation
        if progress_callback:
            progress_callback(4, f"Writing grounded comparison from {len(curated_products)} verified product listings...")

        answer_markdown = self.gemini_service.write_shopping_grounded_answer(
            cleaned_question,
            plan.budget_text,
            plan.criteria,
            curated_products,
        )

        # Stage 5: Validating citations
        if progress_callback:
            progress_callback(5, "Validating inline product citations [I1], [I2]...")

        citation_report = validate_citations(answer_markdown, curated_products)
        limitations: list[str] = []
        if not citation_report["valid"]:
            invalid_ids = ", ".join(str(s) for s in citation_report.get("invalid_source_ids", []))
            limitations.append(f"Warning: The answer referenced unverified product IDs: {invalid_ids}")

        answer = AgentAnswer(
            answer_markdown=answer_markdown,
            sources=curated_products,
            limitations=limitations,
            mode=AgentMode.SHOPPING,
        )

        return AgentRunResult(
            plan=plan,
            answer=answer,
            requires_clarification=False,
            clarification_question=None,
            status_message=f"Found and analyzed {len(curated_products)} verified product listings.",
        )
