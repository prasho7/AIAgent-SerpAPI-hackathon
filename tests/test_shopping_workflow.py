"""Unit tests for ShoppingWorkflow and Smart Shopping pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from models import AgentMode, ProductEvidence, ShoppingPlan
from workflows.shopping_workflow import ShoppingWorkflow


def test_shopping_workflow_missing_budget_clarification() -> None:
    """If no budget is provided and no 'no budget' statement, workflow must request clarification."""
    mock_gemini = MagicMock()
    mock_gemini.create_shopping_plan.return_value = ShoppingPlan(
        mode=AgentMode.SHOPPING,
        goal="Find laptop for coding",
        product_query="laptop for coding",
        budget_amount=None,
        currency=None,
        budget_text=None,
        criteria=["Performance", "Display"],
        needs_clarification=True,
        clarifying_question="What budget should I use? You can provide an amount and currency, such as ₹60,000 or $800, or say 'no budget limit.'",
    )
    mock_serpapi = MagicMock()

    workflow = ShoppingWorkflow(
        gemini_service=mock_gemini,
        serpapi_service=mock_serpapi,
    )

    result = workflow.run("Find me a good coding laptop")
    assert result.requires_clarification is True
    assert "What budget should I use?" in (result.clarification_question or "")
    mock_serpapi.search_products.assert_not_called()


def test_shopping_workflow_missing_category_clarification() -> None:
    """If no product category is specified, workflow must request clarification."""
    mock_gemini = MagicMock()
    mock_gemini.create_shopping_plan.return_value = ShoppingPlan(
        mode=AgentMode.SHOPPING,
        goal="Find products under 5000",
        product_query="item",
        budget_amount=5000.0,
        currency="INR",
        budget_text="under ₹5,000",
        criteria=["Budget fit", "Quality"],
        needs_clarification=True,
        clarifying_question="What product category are you shopping for?",
    )
    mock_serpapi = MagicMock()

    workflow = ShoppingWorkflow(
        gemini_service=mock_gemini,
        serpapi_service=mock_serpapi,
    )

    result = workflow.run("Find something under ₹5,000")
    assert result.requires_clarification is True
    assert "What product category are you shopping for?" in (result.clarification_question or "")
    mock_serpapi.search_products.assert_not_called()


def test_shopping_workflow_success_mocked() -> None:
    """End-to-end ShoppingWorkflow test with mocked Gemini and SerpApi."""
    now = datetime.now(timezone.utc)
    mock_gemini = MagicMock()
    mock_gemini.create_shopping_plan.return_value = ShoppingPlan(
        mode=AgentMode.SHOPPING,
        goal="Find coding laptops under ₹60,000",
        product_query="laptop for coding under 60000 inr",
        budget_amount=60000.0,
        currency="INR",
        budget_text="under ₹60,000",
        criteria=["price within budget", "coding performance", "merchant reliability"],
        needs_clarification=False,
        clarifying_question=None,
    )
    mock_gemini.write_shopping_grounded_answer.return_value = (
        "## Top Laptop Picks Under ₹60,000\n\n"
        "1. **Lenovo IdeaPad Slim 3** [I1] is the best overall choice at ₹54,990 with 16GB RAM for smooth compiling.\n"
        "2. **HP Pavilion 14** [I2] is a solid portable option at ₹58,000 [I2].\n\n"
        "| Product | Price | Merchant | Rating |\n"
        "|---|---|---|---|\n"
        "| Lenovo IdeaPad Slim 3 [I1] | ₹54,990 | Amazon.in | 4.4/5.0 |\n"
        "| HP Pavilion 14 [I2] | ₹58,000 | Flipkart | 4.3/5.0 |\n"
    )

    mock_serpapi = MagicMock()
    mock_serpapi.search_products.return_value = [
        ProductEvidence(
            source_id="raw_i_1",
            title="Lenovo IdeaPad Slim 3 15-inch Intel Core i5",
            price=54990.0,
            currency="INR",
            price_text="₹54,990",
            merchant="Amazon.in",
            product_url="https://amazon.in/dp/sample-lenovo",
            rating=4.4,
            reviews=1200,
            delivery_info="Free Prime delivery",
            condition="New",
            snippet="16GB DDR5 RAM, 512GB NVMe SSD, Full HD Anti-Glare display.",
            query="laptop for coding under 60000 inr",
            rank=1,
            retrieved_at=now,
        ),
        ProductEvidence(
            source_id="raw_i_2",
            title="HP Pavilion 14 AMD Ryzen 5",
            price=58000.0,
            currency="INR",
            price_text="₹58,000",
            merchant="Flipkart",
            product_url="https://flipkart.com/hp-pavilion",
            rating=4.3,
            reviews=650,
            delivery_info="Delivery in 2 days",
            condition="New",
            snippet="14-inch FHD IPS, 16GB RAM, Fast Charging.",
            query="laptop for coding under 60000 inr",
            rank=2,
            retrieved_at=now,
        ),
    ]

    workflow = ShoppingWorkflow(
        gemini_service=mock_gemini,
        serpapi_service=mock_serpapi,
    )

    progress_steps: list[tuple[int, str]] = []

    def on_progress(step: int, msg: str) -> None:
        progress_steps.append((step, msg))

    result = workflow.run("Find a laptop under ₹60,000 for coding", progress_callback=on_progress)

    assert result.requires_clarification is False
    assert result.answer is not None
    assert result.answer.mode == AgentMode.SHOPPING
    assert len(result.answer.sources) == 2
    assert result.answer.sources[0].source_id == "I1"
    assert result.answer.sources[1].source_id == "I2"
    assert "Lenovo IdeaPad Slim 3" in result.answer.answer_markdown
    assert len(result.answer.limitations) == 0
    assert len(progress_steps) == 5


def test_shopping_workflow_empty_results() -> None:
    """When no products are found on Google Shopping, workflow should return clean fallback."""
    mock_gemini = MagicMock()
    mock_gemini.create_shopping_plan.return_value = ShoppingPlan(
        mode=AgentMode.SHOPPING,
        goal="Find rare gadget",
        product_query="nonexistent gadget xyz123",
        budget_amount=100.0,
        currency="USD",
        budget_text="under $100",
        criteria=["Budget", "Availability"],
        needs_clarification=False,
    )
    mock_serpapi = MagicMock()
    mock_serpapi.search_products.return_value = []

    workflow = ShoppingWorkflow(
        gemini_service=mock_gemini,
        serpapi_service=mock_serpapi,
    )

    result = workflow.run("Buy nonexistent gadget xyz123 under $100")
    assert result.requires_clarification is False
    assert result.answer is not None
    assert len(result.answer.sources) == 0
    assert "could not find matching product listings" in result.answer.answer_markdown


def test_shopping_workflow_citation_warning() -> None:
    """If writer cites phantom [I9], limitations should include citation warning."""
    now = datetime.now(timezone.utc)
    mock_gemini = MagicMock()
    mock_gemini.create_shopping_plan.return_value = ShoppingPlan(
        mode=AgentMode.SHOPPING,
        goal="Find headphones",
        product_query="wireless headphones under 3000",
        budget_amount=3000.0,
        currency="INR",
        budget_text="under ₹3,000",
        criteria=["Sound quality", "Battery life"],
        needs_clarification=False,
    )
    mock_gemini.write_shopping_grounded_answer.return_value = (
        "Check [I1] and also hallucinated [I9]."
    )
    mock_serpapi = MagicMock()
    mock_serpapi.search_products.return_value = [
        ProductEvidence(
            source_id="raw_1",
            title="boAt Rockerz 450",
            price=1499.0,
            currency="INR",
            merchant="Amazon.in",
            rating=4.2,
            query="headphones",
            rank=1,
            retrieved_at=now,
        )
    ]

    workflow = ShoppingWorkflow(
        gemini_service=mock_gemini,
        serpapi_service=mock_serpapi,
    )

    result = workflow.run("Best headphones under ₹3,000")
    assert result.answer is not None
    assert len(result.answer.limitations) > 0
    assert "I9" in result.answer.limitations[0]
