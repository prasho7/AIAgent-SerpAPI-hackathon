"""Gemini service interface for planning, writing, and connectivity testing."""

from __future__ import annotations

import json
import re
from typing import Any

from google import genai
from google.genai import errors, types

from config import Settings
from models import (
    AgentMode,
    FollowUpContext,
    FollowUpTurn,
    LocalSearchPlan,
    PlaceEvidence,
    ProductEvidence,
    ResearchPlan,
    ShoppingPlan,
    SourceEvidence,
)
from processors.evidence_processor import (
    format_evidence_for_llm,
    format_places_for_llm,
    format_products_for_llm,
)
from prompts.planner_prompt import (
    LOCAL_PLANNER_SYSTEM_PROMPT,
    PLANNER_SYSTEM_PROMPT,
    SHOPPING_PLANNER_SYSTEM_PROMPT,
    build_local_planner_user_prompt,
    build_planner_user_prompt,
    build_shopping_planner_user_prompt,
)
from prompts.writer_prompt import (
    FOLLOW_UP_SYSTEM_PROMPT,
    LOCAL_WRITER_SYSTEM_PROMPT,
    SHOPPING_WRITER_SYSTEM_PROMPT,
    WRITER_SYSTEM_PROMPT,
    build_follow_up_user_prompt,
    build_local_writer_user_prompt,
    build_shopping_writer_user_prompt,
    build_writer_user_prompt,
)


def normalize_gemini_error(exc: Exception, model_name: str = "") -> str:
    """Map raw Gemini SDK exceptions to user-safe, non-technical error messages."""
    err_str = str(exc)
    code = getattr(exc, "code", None)

    # 1. 503 / High Demand / Service Unavailable / Spikes in demand
    if (
        code == 503
        or "503" in err_str
        or "UNAVAILABLE" in err_str
        or "high demand" in err_str.lower()
        or "temporarily unavailable" in err_str.lower()
        or "service unavailable" in err_str.lower()
        or "spikes in demand" in err_str.lower()
    ):
        return "Gemini is temporarily busy. Please wait a moment and try the same request again."

    # 2. Authentication / API Key
    if code in (401, 403) or "API_KEY_INVALID" in err_str or "unauthorized" in err_str.lower() or "authentication" in err_str.lower():
        return "Gemini authentication failed: Invalid or unauthorized API key."

    # 3. Quota / Rate Limit
    if code == 429 or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower() or "rate limit" in err_str.lower():
        return "Gemini quota or rate limit exceeded. Please check your API quota or try again later."

    # 4. Model not found / unavailable
    if code == 404 or "NOT_FOUND" in err_str:
        m = f" '{model_name}'" if model_name else ""
        return f"Gemini model{m} is unavailable or not found."

    # 5. Network / Timeout
    if "timeout" in err_str.lower() or "timed out" in err_str.lower() or "connect" in err_str.lower():
        return "Network or timeout error while connecting to Gemini API."

    # 6. Fallback clean message
    return "Gemini service encountered an error. Please try your request again."


def _clean_json_text(text: str) -> str:
    """Strip markdown code fence blocks from JSON response if present."""
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


class GeminiService:
    """Gemini client interface for connectivity testing, planning, and grounded writing."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        """Lazily initialize and return the Google GenAI client."""
        if not self.settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")
        if self._client is None:
            self._client = genai.Client(api_key=self.settings.gemini_api_key)
        return self._client

    def test_connection(self) -> dict[str, Any]:
        """Test API connectivity to Gemini with a minimal prompt."""
        if not self.settings.gemini_api_key:
            return {
                "success": False,
                "message": "GEMINI_API_KEY is missing. Please set it in your .env file.",
                "response_text": None,
            }

        if not self.settings.gemini_model:
            return {
                "success": False,
                "message": "GEMINI_MODEL is missing. Please set it in your .env file.",
                "response_text": None,
            }

        try:
            client = self._get_client()
            response = client.models.generate_content(
                model=self.settings.gemini_model,
                contents="Respond with 'Gemini connection successful.' in 5 words or less.",
            )

            text = (response.text or "").strip()
            if not text:
                return {
                    "success": False,
                    "message": "Gemini returned an empty response.",
                    "response_text": None,
                }

            return {
                "success": True,
                "message": f"Successfully connected to Gemini ({self.settings.gemini_model}).",
                "response_text": text,
            }

        except Exception as exc:
            return {
                "success": False,
                "message": normalize_gemini_error(exc, self.settings.gemini_model),
                "response_text": None,
            }

    def create_research_plan(self, question: str, preferences: str = "") -> ResearchPlan:
        """Create a structured, validated ResearchPlan using Gemini."""
        client = self._get_client()
        user_prompt = build_planner_user_prompt(question, preferences)

        config = types.GenerateContentConfig(
            system_instruction=PLANNER_SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.2,
        )

        response = client.models.generate_content(
            model=self.settings.gemini_model,
            contents=user_prompt,
            config=config,
        )

        raw_text = (response.text or "").strip()
        cleaned_json = _clean_json_text(raw_text)

        try:
            plan = ResearchPlan.model_validate_json(cleaned_json)
        except Exception:
            # Fallback: parse JSON dict and repair common bounds
            parsed = json.loads(cleaned_json)
            mode = parsed.get("mode", "research")
            queries = parsed.get("queries", [])[:3] or [question[:160]]
            criteria = parsed.get("criteria", [])
            if len(criteria) < 2:
                criteria = ["Performance and capabilities", "Ease of integration and use"]
            elif len(criteria) > 4:
                criteria = criteria[:4]

            plan = ResearchPlan(
                mode=AgentMode(mode) if mode in {"research", "local", "shopping"} else AgentMode.RESEARCH,
                goal=parsed.get("goal", f"Research: {question[:100]}"),
                queries=queries,
                criteria=criteria,
                needs_clarification=bool(parsed.get("needs_clarification", False)),
                clarifying_question=parsed.get("clarifying_question"),
            )

        return plan

    def create_local_plan(self, question: str, preferences: str = "") -> LocalSearchPlan:
        """Create a structured, validated LocalSearchPlan using Gemini."""
        client = self._get_client()
        user_prompt = build_local_planner_user_prompt(question, preferences)

        config = types.GenerateContentConfig(
            system_instruction=LOCAL_PLANNER_SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.2,
        )

        response = client.models.generate_content(
            model=self.settings.gemini_model,
            contents=user_prompt,
            config=config,
        )

        raw_text = (response.text or "").strip()
        cleaned_json = _clean_json_text(raw_text)

        try:
            plan = LocalSearchPlan.model_validate_json(cleaned_json)
        except Exception:
            parsed = json.loads(cleaned_json)
            location = parsed.get("location")
            place_query = parsed.get("place_query") or question[:100]
            criteria = parsed.get("criteria", [])
            if len(criteria) < 2:
                criteria = ["Location and accessibility", "Rating and customer feedback"]
            elif len(criteria) > 4:
                criteria = criteria[:4]

            needs_clarification = bool(parsed.get("needs_clarification", False)) or not location
            clarifying_question = parsed.get("clarifying_question")
            if needs_clarification and not clarifying_question:
                clarifying_question = "Which city, neighborhood, or landmark should I search around?"

            plan = LocalSearchPlan(
                mode=AgentMode.LOCAL,
                goal=parsed.get("goal", f"Find places for: {question[:100]}"),
                location=location,
                place_query=place_query,
                criteria=criteria,
                needs_clarification=needs_clarification,
                clarifying_question=clarifying_question,
            )

        return plan

    def write_grounded_answer(
        self,
        question: str,
        criteria: list[str],
        evidence: list[SourceEvidence],
    ) -> str:
        """Write an evidence-grounded research answer using Gemini."""
        client = self._get_client()
        evidence_text = format_evidence_for_llm(evidence)
        user_prompt = build_writer_user_prompt(question, criteria, evidence_text)

        config = types.GenerateContentConfig(
            system_instruction=WRITER_SYSTEM_PROMPT,
            temperature=0.3,
        )

        response = client.models.generate_content(
            model=self.settings.gemini_model,
            contents=user_prompt,
            config=config,
        )

        answer_text = (response.text or "").strip()
        if not answer_text:
            raise ValueError("Gemini returned an empty grounded answer.")

        # Ensure no duplicate trailing Sources section is appended to answer
        cleaned_answer = re.sub(r"\n#{1,3}\s*Sources[\s\S]*$", "", answer_text, flags=re.IGNORECASE).strip()
        return cleaned_answer or answer_text

    def write_local_grounded_answer(
        self,
        question: str,
        location: str,
        criteria: list[str],
        places: list[PlaceEvidence],
    ) -> str:
        """Write an evidence-grounded local place recommendation brief using Gemini."""
        client = self._get_client()
        evidence_text = format_places_for_llm(places)
        user_prompt = build_local_writer_user_prompt(question, location, criteria, evidence_text)

        config = types.GenerateContentConfig(
            system_instruction=LOCAL_WRITER_SYSTEM_PROMPT,
            temperature=0.3,
        )

        response = client.models.generate_content(
            model=self.settings.gemini_model,
            contents=user_prompt,
            config=config,
        )

        answer_text = (response.text or "").strip()
        if not answer_text:
            raise ValueError("Gemini returned an empty local recommendation.")

        cleaned_answer = re.sub(r"\n#{1,3}\s*Sources[\s\S]*$", "", answer_text, flags=re.IGNORECASE).strip()
        return cleaned_answer or answer_text

    def create_shopping_plan(self, question: str, preferences: str = "") -> ShoppingPlan:
        """Create a structured, validated ShoppingPlan using Gemini."""
        client = self._get_client()
        user_prompt = build_shopping_planner_user_prompt(question, preferences)

        config = types.GenerateContentConfig(
            system_instruction=SHOPPING_PLANNER_SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.2,
        )

        response = client.models.generate_content(
            model=self.settings.gemini_model,
            contents=user_prompt,
            config=config,
        )

        raw_text = (response.text or "").strip()
        cleaned_json = _clean_json_text(raw_text)

        try:
            plan = ShoppingPlan.model_validate_json(cleaned_json)
        except Exception:
            parsed = json.loads(cleaned_json)
            product_query = parsed.get("product_query") or question[:100]
            budget_amount = parsed.get("budget_amount")
            if budget_amount is not None:
                try:
                    budget_amount = float(budget_amount)
                except (ValueError, TypeError):
                    budget_amount = None

            currency = parsed.get("currency")
            budget_text = parsed.get("budget_text")
            criteria = parsed.get("criteria", [])
            if len(criteria) < 2:
                criteria = ["Price within budget", "Product suitability and quality"]
            elif len(criteria) > 4:
                criteria = criteria[:4]

            needs_clarification = bool(parsed.get("needs_clarification", False))
            clarifying_question = parsed.get("clarifying_question")

            plan = ShoppingPlan(
                mode=AgentMode.SHOPPING,
                goal=parsed.get("goal", f"Find products for: {question[:100]}"),
                product_query=product_query,
                budget_amount=budget_amount,
                currency=currency,
                budget_text=budget_text,
                criteria=criteria,
                needs_clarification=needs_clarification,
                clarifying_question=clarifying_question,
            )

        return plan

    def write_shopping_grounded_answer(
        self,
        question: str,
        budget_text: str | None,
        criteria: list[str],
        products: list[ProductEvidence],
    ) -> str:
        """Write an evidence-grounded shopping recommendation brief using Gemini."""
        client = self._get_client()
        evidence_text = format_products_for_llm(products)
        user_prompt = build_shopping_writer_user_prompt(question, budget_text, criteria, evidence_text)

        config = types.GenerateContentConfig(
            system_instruction=SHOPPING_WRITER_SYSTEM_PROMPT,
            temperature=0.3,
        )

        response = client.models.generate_content(
            model=self.settings.gemini_model,
            contents=user_prompt,
            config=config,
        )

        answer_text = (response.text or "").strip()
        if not answer_text:
            raise ValueError("Gemini returned an empty shopping recommendation.")

        cleaned_answer = re.sub(r"\n#{1,3}\s*Sources[\s\S]*$", "", answer_text, flags=re.IGNORECASE).strip()
        return cleaned_answer or answer_text

    def write_follow_up(
        self,
        context: FollowUpContext,
        follow_up_question: str,
        history: list[FollowUpTurn] | None = None,
    ) -> str:
        """Write a grounded follow-up answer strictly based on the context's curated evidence."""
        client = self._get_client()

        # Format evidence according to mode
        if context.mode == AgentMode.LOCAL or (context.sources and isinstance(context.sources[0], PlaceEvidence)):
            evidence_text = format_places_for_llm(context.sources)  # type: ignore[arg-type]
        elif context.mode == AgentMode.SHOPPING or (context.sources and isinstance(context.sources[0], ProductEvidence)):
            evidence_text = format_products_for_llm(context.sources)  # type: ignore[arg-type]
        else:
            evidence_text = format_evidence_for_llm(context.sources)  # type: ignore[arg-type]

        # Format up to 2 most recent turns
        recent_turns = (history or [])[-2:]
        turn_lines: list[str] = []
        for t in recent_turns:
            turn_lines.append(f"User: {t.question}\nScoutAI: {t.answer}")
        recent_turns_text = "\n\n".join(turn_lines)

        mode_name = context.mode.value.capitalize()
        user_prompt = build_follow_up_user_prompt(
            original_question=context.original_question,
            mode_name=mode_name,
            plan_goal=context.plan_goal,
            plan_criteria=context.plan_criteria,
            prior_answer=context.prior_answer,
            evidence_text=evidence_text,
            recent_turns_text=recent_turns_text,
            follow_up_question=follow_up_question,
        )

        config = types.GenerateContentConfig(
            system_instruction=FOLLOW_UP_SYSTEM_PROMPT,
            temperature=0.2,
        )

        response = client.models.generate_content(
            model=self.settings.gemini_model,
            contents=user_prompt,
            config=config,
        )

        answer_text = (response.text or "").strip()
        if not answer_text:
            raise ValueError("Gemini returned an empty follow-up answer.")

        cleaned_answer = re.sub(r"\n#{1,3}\s*Sources[\s\S]*$", "", answer_text, flags=re.IGNORECASE).strip()
        return cleaned_answer or answer_text


