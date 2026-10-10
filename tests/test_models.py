"""Tests for Pydantic model validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from models import AgentMode, ResearchPlan


def test_valid_research_plan() -> None:
    """A valid research plan should parse normally."""
    plan = ResearchPlan(
        mode=AgentMode.RESEARCH,
        goal="Compare beginner-friendly Python agent frameworks.",
        queries=["Python agent frameworks for beginners"],
        criteria=["Beginner-friendly", "Works with Gemini", "Accessible docs"],
        needs_clarification=False,
    )

    assert plan.mode == AgentMode.RESEARCH
    assert len(plan.queries) == 1


def test_more_than_three_queries_fails_validation() -> None:
    """More than three search queries should fail validation."""
    with pytest.raises(ValidationError):
        ResearchPlan(
            mode=AgentMode.RESEARCH,
            goal="Compare frameworks",
            queries=["q1", "q2", "q3", "q4"],
            criteria=["c1", "c2", "c3"],
        )


def test_valid_local_search_plan_and_place_evidence() -> None:
    """LocalSearchPlan and PlaceEvidence should instantiate and validate properly."""
    from datetime import datetime, timezone
    from models import LocalSearchPlan, PlaceEvidence

    plan = LocalSearchPlan(
        mode=AgentMode.LOCAL,
        goal="Find quiet cafes for studying in Koramangala",
        location="Koramangala, Bengaluru",
        place_query="quiet cafes for studying",
        criteria=["quiet atmosphere", "budget under ₹500"],
        needs_clarification=False,
    )
    assert plan.mode == AgentMode.LOCAL
    assert plan.location == "Koramangala, Bengaluru"
    assert len(plan.criteria) == 2

    place = PlaceEvidence(
        source_id="P1",
        name="Third Wave Coffee",
        address="Koramangala",
        rating=4.5,
        review_count=500,
        query="quiet cafes",
        rank=1,
        retrieved_at=datetime.now(timezone.utc),
    )
    assert place.source_id == "P1"
    assert place.rating == 4.5


def test_valid_shopping_plan_and_product_evidence() -> None:
    """ShoppingPlan and ProductEvidence should instantiate and validate properly."""
    from datetime import datetime, timezone
    from models import ProductEvidence, ShoppingPlan

    plan = ShoppingPlan(
        mode=AgentMode.SHOPPING,
        goal="Find coding laptops under ₹60,000",
        product_query="laptop for coding under 60000 inr",
        budget_amount=60000.0,
        currency="INR",
        budget_text="under ₹60,000",
        criteria=["price within budget", "coding suitability"],
        needs_clarification=False,
    )
    assert plan.mode == AgentMode.SHOPPING
    assert plan.budget_amount == 60000.0
    assert plan.currency == "INR"
    assert len(plan.criteria) == 2

    product = ProductEvidence(
        source_id="I1",
        title="Lenovo IdeaPad Slim 3 15-inch",
        price=54990.0,
        currency="INR",
        price_text="₹54,990",
        merchant="Amazon.in",
        product_url="https://amazon.in/dp/sample",
        rating=4.4,
        reviews=1200,
        delivery_info="Free delivery by Friday",
        condition="New",
        query="laptop for coding",
        rank=1,
        retrieved_at=datetime.now(timezone.utc),
    )
    assert product.source_id == "I1"
    assert product.price == 54990.0
    assert product.merchant == "Amazon.in"


def test_planner_prompt_query_quality_rules() -> None:
    """Verify that Research and Shopping planner prompts contain explicit category/entity query rules."""
    from prompts.planner_prompt import PLANNER_SYSTEM_PROMPT, SHOPPING_PLANNER_SYSTEM_PROMPT

    # Research query quality checks
    assert "Query Quality Rules:" in PLANNER_SYSTEM_PROMPT
    assert "explicitly include the relevant category, entity type, or topic type" in PLANNER_SYSTEM_PROMPT
    assert "Samsung Galaxy S24 smartphone specifications" in PLANNER_SYSTEM_PROMPT
    assert "iPhone 16 smartphone price India" in PLANNER_SYSTEM_PROMPT
    assert "Sony WH-1000XM5 wireless headphones review" in PLANNER_SYSTEM_PROMPT
    assert "Streamlit versus FastAPI Python web framework comparison" in PLANNER_SYSTEM_PROMPT

    # Shopping query quality checks
    assert "Product Query Quality Rules:" in SHOPPING_PLANNER_SYSTEM_PROMPT
    assert "explicitly include the product category or product type" in SHOPPING_PLANNER_SYSTEM_PROMPT
    assert "Samsung Galaxy S24 smartphone" in SHOPPING_PLANNER_SYSTEM_PROMPT
    assert "Sony WH-1000XM5 wireless headphones" in SHOPPING_PLANNER_SYSTEM_PROMPT
    assert "MacBook Air M3 laptop" in SHOPPING_PLANNER_SYSTEM_PROMPT


