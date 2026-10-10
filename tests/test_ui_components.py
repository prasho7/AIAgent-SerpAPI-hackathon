"""Unit tests for UI components, session state helpers, and citation validation."""

from __future__ import annotations

from datetime import datetime, timezone

from models import AgentAnswer, AgentMode, AgentRunResult, ResearchPlan, SourceEvidence
from processors.citation_validator import extract_citations, validate_citations
from ui.components import clean_display_answer


def test_clean_display_answer_removes_trailing_sources():
    raw_markdown = (
        "## Executive Summary\n\nLangChain [S1] and CrewAI [S2] are great.\n\n"
        "| Tool | Score |\n|---|---|\n| CrewAI | High [S2] |\n\n"
        "## Sources\n- [S1] https://langchain.com\n- [S2] https://crewai.com"
    )
    cleaned = clean_display_answer(raw_markdown)

    assert "## Executive Summary" in cleaned
    assert "LangChain [S1]" in cleaned
    assert "| CrewAI | High [S2] |" in cleaned
    assert "## Sources" not in cleaned
    assert "https://langchain.com" not in cleaned


def test_clean_display_answer_preserves_text_without_sources():
    raw_markdown = "## Findings\n\nAll tools are viable [S1]."
    cleaned = clean_display_answer(raw_markdown)
    assert cleaned == raw_markdown


def test_citation_validator_extract_pure_stdlib():
    text = "LangChain [S1] and CrewAI [S2] are popular frameworks. Another source is [S10]."
    citations = extract_citations(text)
    assert citations == ["S1", "S2", "S10"]


def test_citation_validator_pure_stdlib_matches():
    now = datetime.now(timezone.utc)
    sources = [
        SourceEvidence(
            source_id="S1",
            title="Source 1",
            url="https://example.com/1",
            snippet="Snippet 1",
            query="q1",
            rank=1,
            retrieved_at=now,
        ),
        SourceEvidence(
            source_id="S2",
            title="Source 2",
            url="https://example.com/2",
            snippet="Snippet 2",
            query="q2",
            rank=2,
            retrieved_at=now,
        ),
    ]

    valid_text = "Claim supported by source [S1] and [S2]."
    report = validate_citations(valid_text, sources)
    assert report["valid"] is True
    assert report["invalid_source_ids"] == []

    invalid_text = "Claim supported by [S1] and nonexistent [S99]."
    report_invalid = validate_citations(invalid_text, sources)
    assert report_invalid["valid"] is False
    assert report_invalid["invalid_source_ids"] == ["S99"]


def test_source_evidence_safe_handling():
    now = datetime.now(timezone.utc)
    source = SourceEvidence(
        source_id="S1",
        title="A" * 300,
        url="https://subdomain.example.com/path/to/resource?query=123",
        snippet="S" * 500,
        query="test query",
        rank=1,
        retrieved_at=now,
    )
    assert len(source.title) == 300
    assert len(source.snippet) == 500


def test_agent_run_result_structure():
    now = datetime.now(timezone.utc)
    plan = ResearchPlan(
        mode=AgentMode.RESEARCH,
        goal="Test research goal.",
        queries=["query 1", "query 2"],
        criteria=["Criterion 1", "Criterion 2"],
        needs_clarification=False,
    )
    sources = [
        SourceEvidence(
            source_id="S1",
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet",
            query="query 1",
            rank=1,
            retrieved_at=now,
        )
    ]
    answer = AgentAnswer(
        answer_markdown="## Brief\n\nGrounded answer [S1].",
        sources=sources,
        limitations=[],
        mode=AgentMode.RESEARCH,
    )
    result = AgentRunResult(
        plan=plan,
        answer=answer,
        requires_clarification=False,
        status_message="Completed successfully.",
    )
    assert result.answer is not None
    assert result.answer.sources[0].source_id == "S1"
    assert result.requires_clarification is False


from unittest.mock import MagicMock, patch
from models import PlaceEvidence, ProductEvidence
from ui.components import (
    render_local_place_card,
    render_research_source_card,
    render_shopping_product_card,
    render_source_card,
    render_sources_panel,
)


@patch("streamlit.markdown")
def test_render_research_source_card(mock_md):
    """Research source card renders S-badge, domain, title, snippet, query/rank, and Open source link."""
    now = datetime.now(timezone.utc)
    source = SourceEvidence(
        source_id="S1",
        title="Python Frameworks for Agents",
        url="https://docs.python.org/3/library/asyncio.html",
        snippet="Asyncio is a library to write concurrent code using the async/await syntax.",
        query="python frameworks",
        rank=1,
        retrieved_at=now,
    )
    render_research_source_card(source)

    assert mock_md.called
    html_arg = mock_md.call_args[0][0]
    assert "S1" in html_arg
    assert "docs.python.org" in html_arg
    assert "Python Frameworks for Agents" in html_arg
    assert "Asyncio is a library" in html_arg
    assert "Open source ↗" in html_arg
    assert "https://docs.python.org/3/library/asyncio.html" in html_arg


@patch("streamlit.markdown")
def test_render_local_place_card_with_maps_and_website(mock_md):
    """Local place card renders P-badge, name, rating, Maps link, and Website link."""
    now = datetime.now(timezone.utc)
    place = PlaceEvidence(
        source_id="P1",
        name="Third Wave Coffee",
        address="Koramangala 4th Block, Bengaluru",
        rating=4.5,
        review_count=1250,
        category="Coffee shop",
        website="https://thirdwavecoffee.in",
        maps_url="https://maps.google.com/?cid=123",
        snippet="Specialty coffee roasters.",
        query="quiet cafes",
        rank=1,
        retrieved_at=now,
    )
    render_local_place_card(place)

    assert mock_md.called
    html_arg = mock_md.call_args[0][0]
    assert "P1" in html_arg
    assert "Third Wave Coffee" in html_arg
    assert "4.5" in html_arg
    assert "(1250)" in html_arg
    assert "Open in Maps ↗" in html_arg
    assert "Website ↗" in html_arg
    assert "https://maps.google.com/?cid=123" in html_arg
    assert "https://thirdwavecoffee.in" in html_arg


@patch("streamlit.markdown")
def test_render_shopping_product_card(mock_md):
    """Shopping product card renders I-badge, title, price, merchant, rating, and View listing link."""
    now = datetime.now(timezone.utc)
    product = ProductEvidence(
        source_id="I1",
        title="Lenovo IdeaPad Slim 3",
        price=54990.0,
        currency="INR",
        price_text="₹54,990",
        merchant="Amazon.in",
        product_url="https://amazon.in/dp/sample",
        rating=4.4,
        reviews=800,
        delivery_info="Free Delivery",
        condition="New",
        snippet="16GB RAM, 512GB SSD.",
        query="coding laptop",
        rank=1,
        retrieved_at=now,
    )
    render_shopping_product_card(product)

    assert mock_md.called
    html_arg = mock_md.call_args[0][0]
    assert "I1" in html_arg
    assert "Lenovo IdeaPad Slim 3" in html_arg
    assert "₹54,990" in html_arg
    assert "Amazon.in" in html_arg
    assert "4.4" in html_arg
    assert "(800)" in html_arg
    assert "View listing ↗" in html_arg
    assert "https://amazon.in/dp/sample" in html_arg


@patch("streamlit.markdown")
def test_render_source_card_dispatcher(mock_md):
    """render_source_card dispatches correctly by mode and evidence type."""
    now = datetime.now(timezone.utc)
    s = SourceEvidence(source_id="S1", title="Res", url="https://example.com", snippet="Snip", query="q", rank=1, retrieved_at=now)
    p = PlaceEvidence(source_id="P1", name="Place", query="q", rank=1, retrieved_at=now)
    i = ProductEvidence(source_id="I1", title="Prod", query="q", rank=1, retrieved_at=now)

    render_source_card(s, mode=AgentMode.RESEARCH)
    assert "S1" in mock_md.call_args[0][0]

    render_source_card(p, mode=AgentMode.LOCAL)
    assert "P1" in mock_md.call_args[0][0]

    render_source_card(i, mode=AgentMode.SHOPPING)
    assert "I1" in mock_md.call_args[0][0]


@patch("streamlit.expander")
@patch("streamlit.markdown")
def test_render_sources_panel_all_modes(mock_md, mock_expander):
    """render_sources_panel creates appropriate headers and dispatches all sources."""
    now = datetime.now(timezone.utc)
    research_sources = [
        SourceEvidence(source_id=f"S{idx}", title=f"Title {idx}", url="https://example.com", snippet="Snippet", query="q", rank=idx, retrieved_at=now)
        for idx in range(1, 4)
    ]
    render_sources_panel(research_sources, mode=AgentMode.RESEARCH)
    assert any("Sources" in str(call) for call in mock_md.call_args_list)

    place_sources = [
        PlaceEvidence(source_id=f"P{idx}", name=f"Cafe {idx}", query="q", rank=idx, retrieved_at=now)
        for idx in range(1, 4)
    ]
    render_sources_panel(place_sources, mode=AgentMode.LOCAL)
    assert any("Places" in str(call) for call in mock_md.call_args_list)

    product_sources = [
        ProductEvidence(source_id=f"I{idx}", title=f"Laptop {idx}", query="q", rank=idx, retrieved_at=now)
        for idx in range(1, 4)
    ]
    render_sources_panel(product_sources, mode=AgentMode.SHOPPING)
    assert any("Products" in str(call) for call in mock_md.call_args_list)


def test_shopping_market_label_config():
    """Settings should properly provide shopping market defaults and accept overrides."""
    from config import Settings

    default_settings = Settings()
    assert default_settings.shopping_gl == "in"
    assert default_settings.shopping_hl == "en"
    assert default_settings.shopping_market_label == "India"

    custom_settings = Settings(shopping_gl="us", shopping_hl="en", shopping_market_label="United States")
    assert custom_settings.shopping_gl == "us"
    assert custom_settings.shopping_hl == "en"
    assert custom_settings.shopping_market_label == "United States"


