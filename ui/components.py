"""Reusable Streamlit UI helpers for ScoutAI."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit

import streamlit as st

from config import Settings
from models import AgentMode, FollowUpTurn, PlaceEvidence, ProductEvidence, SourceEvidence
from processors.evidence_processor import build_google_maps_url
from services.gemini_service import GeminiService
from services.serpapi_service import SerpApiService




def clean_display_answer(answer_text: str) -> str:
    """Remove any trailing ## Sources section from display text while preserving all citations."""
    if not answer_text:
        return ""
    # Remove trailing ## Sources or ### Sources and all subsequent content
    cleaned = re.sub(r"\n#{1,3}\s*Sources\b[\s\S]*$", "", answer_text, flags=re.IGNORECASE).strip()
    return cleaned if cleaned else answer_text


def render_status(message: str) -> None:
    """Render a friendly status message."""
    st.info(message)


def render_header() -> None:
    """Render the compact, modern ScoutAI header."""
    st.markdown(
        """
        <div class="scout-header-row">
            <div class="scout-brand">
                <span class="scout-mark"></span>
                <span class="scout-name">ScoutAI</span>
            </div>
        </div>
        <div class="scout-subheading">Live Research & Decision Agent</div>
        <div class="scout-tagline">Ask. Verify. Decide with live web evidence.</div>
        """,
        unsafe_allow_html=True,
    )


STARTER_EXAMPLES = [
    (
        "Gemini-ready AI-agent frameworks",
        "Compare beginner-friendly Python AI-agent frameworks that work with Gemini.",
    ),
    (
        "Current Indian stock-market trends",
        "What are the current trends in the Indian stock market today?",
    ),
    (
        "Streamlit vs FastAPI for a beginner AI agent",
        "Compare Streamlit and FastAPI for a beginner building an AI agent.",
    ),
]


def render_starter_examples(on_select_callback: Any = None) -> None:
    """Render the clean 'Try an example' block with 3 clickable prompt buttons."""
    st.markdown(
        """
        <div class="scout-starter-section">
            <div class="scout-starter-title">Try an example</div>
            <div class="scout-starter-desc">
                Choose a starting point, or write your own research question above.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns(3, gap="small")
    cols = [col1, col2, col3]
    for i, (label, query) in enumerate(STARTER_EXAMPLES):
        with cols[i]:
            if on_select_callback:
                st.button(
                    label,
                    key=f"starter_ex_btn_{i}",
                    use_container_width=True,
                    on_click=on_select_callback,
                    args=(query,),
                )
            else:
                if st.button(label, key=f"starter_ex_btn_{i}", use_container_width=True):
                    st.session_state["query_input"] = query
                    st.rerun()


def render_empty_state(on_select_callback: Any = None) -> None:
    """Backward-compatible helper calling render_starter_examples."""
    render_starter_examples(on_select_callback=on_select_callback)


def render_metadata_line(query_count: int, source_count: int, citation_valid: bool) -> None:
    """Render the single metadata line above the research brief."""
    citation_str = "Citations checked" if citation_valid else "Citation warnings"
    st.markdown(
        f"""
        <div class="scout-meta-line">
            <span class="scout-meta-highlight">● Research complete</span>
            <span>·</span>
            <span>{query_count} queries</span>
            <span>·</span>
            <span>{source_count} sources</span>
            <span>·</span>
            <span>{citation_str}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_research_source_card(source: SourceEvidence) -> None:
    """Render a single compact research source card with safe truncation."""
    domain = ""
    if source.url:
        try:
            domain = urlsplit(source.url).netloc or ""
        except Exception:
            domain = ""

    title = (source.title[:95] + "...") if len(source.title) > 95 else (source.title or "Untitled Source")
    snippet_raw = source.snippet or "No snippet available."
    snippet = (snippet_raw[:160] + "...") if len(snippet_raw) > 160 else snippet_raw
    query_info = f"Query: {source.query[:35]}..." if len(source.query) > 35 else f"Query: {source.query}"
    rank_info = f"Rank #{source.rank}"

    link_html = (
        f'<a class="scout-source-link" href="{source.url}" target="_blank" rel="noopener noreferrer">Open source ↗</a>'
        if source.url and source.url.startswith(("http://", "https://"))
        else '<span style="color:#64748b;">No link</span>'
    )

    st.markdown(
        f"""
        <div class="scout-source-item">
            <div class="scout-source-top">
                <span class="scout-source-badge">{source.source_id}</span>
                <span class="scout-source-domain">{domain}</span>
            </div>
            <div class="scout-source-title">{title}</div>
            <div class="scout-source-snippet">{snippet}</div>
            <div class="scout-source-footer">
                <span>{query_info} · {rank_info}</span>
                {link_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_local_place_card(source: PlaceEvidence) -> None:
    """Render a single compact local place card with safe truncation."""
    title = (source.name[:95] + "...") if len(source.name) > 95 else (source.name or "Untitled Place")
    rating_str = f"★ {source.rating}" if source.rating is not None else ""
    if rating_str and source.review_count is not None:
        rating_str += f" ({source.review_count})"

    domain = source.category or "Google Maps"
    if rating_str:
        domain = f"{domain} · {rating_str}"

    snippet_raw = source.address or source.snippet or "No location description available."
    snippet = (snippet_raw[:160] + "...") if len(snippet_raw) > 160 else snippet_raw
    query_info = f"Query: {source.query[:35]}..." if len(source.query) > 35 else f"Query: {source.query}"
    rank_info = f"Rank #{source.rank}"

    maps_link_url = build_google_maps_url(source)
    website_url = (
        source.website.strip()
        if source.website and source.website.strip().startswith(("http://", "https://"))
        else None
    )

    action_links: list[str] = []
    if maps_link_url:
        action_links.append(
            f'<a class="scout-source-link" href="{maps_link_url}" target="_blank" rel="noopener noreferrer">Open in Maps ↗</a>'
        )
    if website_url:
        action_links.append(
            f'<a class="scout-source-link" href="{website_url}" target="_blank" rel="noopener noreferrer">Website ↗</a>'
        )

    link_html = " · ".join(action_links) if action_links else '<span style="color:#64748b;">No link</span>'

    st.markdown(
        f"""
        <div class="scout-source-item">
            <div class="scout-source-top">
                <span class="scout-source-badge">{source.source_id}</span>
                <span class="scout-source-domain">{domain}</span>
            </div>
            <div class="scout-source-title">{title}</div>
            <div class="scout-source-snippet">{snippet}</div>
            <div class="scout-source-footer">
                <span>{query_info} · {rank_info}</span>
                {link_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_shopping_product_card(source: ProductEvidence) -> None:
    """Render a single compact product card with safe truncation."""
    title = (source.title[:95] + "...") if len(source.title) > 95 else (source.title or "Untitled Product")
    rating_str = f"★ {source.rating}" if source.rating is not None else ""
    if rating_str and source.reviews is not None:
        rating_str += f" ({source.reviews})"

    price_display = source.price_text or (f"{source.currency or ''} {source.price}".strip() if source.price is not None else "")
    domain = source.merchant or "Google Shopping"
    if price_display:
        domain = f"{domain} · {price_display}"
    if rating_str:
        domain = f"{domain} · {rating_str}"

    snippet_raw = source.snippet or source.delivery_info or "No product description available."
    snippet = (snippet_raw[:160] + "...") if len(snippet_raw) > 160 else snippet_raw
    query_info = f"Query: {source.query[:35]}..." if len(source.query) > 35 else f"Query: {source.query}"
    rank_info = f"Rank #{source.rank}"

    listing_url = (
        source.product_url.strip()
        if source.product_url and source.product_url.strip().startswith(("http://", "https://"))
        else None
    )

    link_html = (
        f'<a class="scout-source-link" href="{listing_url}" target="_blank" rel="noopener noreferrer">View listing ↗</a>'
        if listing_url
        else '<span style="color:#64748b;">No link</span>'
    )

    st.markdown(
        f"""
        <div class="scout-source-item">
            <div class="scout-source-top">
                <span class="scout-source-badge">{source.source_id}</span>
                <span class="scout-source-domain">{domain}</span>
            </div>
            <div class="scout-source-title">{title}</div>
            <div class="scout-source-snippet">{snippet}</div>
            <div class="scout-source-footer">
                <span>{query_info} · {rank_info}</span>
                {link_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_source_card(
    source: SourceEvidence | PlaceEvidence | ProductEvidence,
    mode: AgentMode | None = None,
) -> None:
    """Dispatch and render a single compact source card by mode or evidence model."""
    if mode == AgentMode.RESEARCH or isinstance(source, SourceEvidence):
        render_research_source_card(source)
    elif mode == AgentMode.LOCAL or isinstance(source, PlaceEvidence):
        render_local_place_card(source)
    elif mode == AgentMode.SHOPPING or isinstance(source, ProductEvidence):
        render_shopping_product_card(source)
    else:
        # Fallback safe dispatch
        if hasattr(source, "merchant") or hasattr(source, "product_url"):
            render_shopping_product_card(source)  # type: ignore[arg-type]
        elif hasattr(source, "maps_url") or hasattr(source, "place_id"):
            render_local_place_card(source)  # type: ignore[arg-type]
        else:
            render_research_source_card(source)  # type: ignore[arg-type]


def render_sources_panel(
    sources: list[SourceEvidence | PlaceEvidence | ProductEvidence],
    mode: AgentMode | None = None,
) -> None:
    """Render the right-side Sources panel showing top 5 sources and an expander for the rest."""
    count = len(sources)
    if mode == AgentMode.SHOPPING or (sources and isinstance(sources[0], ProductEvidence)):
        panel_title = "Products"
    elif mode == AgentMode.LOCAL or (sources and isinstance(sources[0], PlaceEvidence)):
        panel_title = "Places"
    else:
        panel_title = "Sources"

    st.markdown(
        f"### {panel_title}\n<div style='font-size:0.82rem; color:#8b93a7; margin-top:-0.5rem; margin-bottom:0.75rem;'>{count} live {panel_title.lower()}</div>",
        unsafe_allow_html=True,
    )

    if not sources:
        st.caption("No usable live sources were retrieved for this request.")
        return

    # Render top 5 sources directly
    for source in sources[:5]:
        render_source_card(source, mode=mode)

    # Render remaining sources in a clean expander
    if len(sources) > 5:
        with st.expander(f"View all {panel_title.lower()} ({len(sources)})", expanded=False):
            for source in sources[5:]:
                render_source_card(source, mode=mode)


def render_follow_up_history(history: list[FollowUpTurn]) -> None:
    """Render the recent follow-up Q&A turns (capped at 2) in the main column."""
    if not history:
        return

    st.markdown("---")
    st.markdown("### Follow-up")
    for turn in history[-2:]:
        st.markdown(
            f"""
            <div style="margin-bottom: 1.25rem;">
                <div style="font-size: 0.85rem; font-weight: 600; color: #8b93a7; margin-bottom: 0.25rem;">You</div>
                <div style="font-size: 0.95rem; color: #f3f5f7; margin-bottom: 0.75rem; padding-left: 0.5rem; border-left: 2px solid #ff4b4b;">
                    {turn.question}
                </div>
                <div style="font-size: 0.85rem; font-weight: 600; color: #3ddc97; margin-bottom: 0.25rem;">ScoutAI</div>
                <div style="font-size: 0.95rem; color: #f3f5f7; line-height: 1.5; margin-bottom: 0.5rem;">
                    {turn.answer}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if turn.citation_warning:
            st.warning(f"⚠️ {turn.citation_warning}")


def render_follow_up_input() -> None:
    """Render the compact follow-up question input section."""
    st.markdown("<div style='margin-top: 1.25rem;'></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="font-size: 0.95rem; font-weight: 600; color: #f3f5f7; margin-bottom: 0.4rem;">
            Continue this analysis
        </div>
        """,
        unsafe_allow_html=True,
    )





def render_sidebar_diagnostics(
    settings: Settings,
    session_state: dict[str, Any],
) -> None:
    """Render the hidden diagnostics panel and health metrics in the Streamlit sidebar."""
    st.markdown("## Diagnostics")
    st.caption("Connection health and latest run metrics")

    searches_val = str(session_state.get("searches_count", "—"))
    sources_val = str(session_state.get("sources_count", "—"))
    latency_val = str(session_state.get("latency_str", "—"))

    serpapi_status = session_state.get("serpapi_status", "Not tested")
    if serpapi_status == "Connected":
        status_color = "#3ddc97"
    elif serpapi_status == "Unavailable" or serpapi_status == "Error":
        status_color = "#ff4b4b"
    else:
        status_color = "#8b93a7"

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"""
            <div class="scout-metric-card">
                <div class="scout-metric-label">Searches</div>
                <div class="scout-metric-val">{searches_val}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="scout-metric-card">
                <div class="scout-metric-label">Latency</div>
                <div class="scout-metric-val">{latency_val}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
            <div class="scout-metric-card">
                <div class="scout-metric-label">Sources Used</div>
                <div class="scout-metric-val">{sources_val}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="scout-metric-card">
                <div class="scout-metric-label">SerpApi</div>
                <div class="scout-metric-val" style="color:{status_color}; font-size:0.92rem;">{serpapi_status}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top: 0.75rem;'></div>", unsafe_allow_html=True)

    if st.button("Test Gemini", key="sb_test_gemini_btn", use_container_width=True):
        with st.spinner("Testing Gemini connection..."):
            gemini_svc = GeminiService(settings)
            res = gemini_svc.test_connection()
        if res["success"]:
            st.success(res["message"])
            if res.get("response_text"):
                st.info(f"Response: {res['response_text']}")
        else:
            st.error(res["message"])

    if st.button("Test SerpApi", key="sb_test_serpapi_btn", use_container_width=True):
        with st.spinner("Testing SerpApi connection..."):
            serpapi_svc = SerpApiService(settings)
            res = serpapi_svc.test_connection()
        if res["success"]:
            st.session_state["serpapi_status"] = "Connected"
            st.success(res["message"])
        else:
            st.session_state["serpapi_status"] = "Unavailable"
            st.error(res["message"])

    st.markdown("---")
    if st.button("Clear session", key="sb_clear_session_btn", use_container_width=True):
        st.session_state["query"] = ""
        st.session_state["research_result"] = None
        st.session_state["answer"] = None
        st.session_state["sources"] = []
        st.session_state["plan"] = None
        st.session_state["searches_count"] = "—"
        st.session_state["sources_count"] = "—"
        st.session_state["latency_str"] = "—"
        st.session_state["error"] = None
        st.rerun()
