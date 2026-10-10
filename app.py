from __future__ import annotations

from datetime import datetime, timezone
import time

import streamlit as st

from agent import run_agent
from config import get_settings
from models import AgentMode, AgentRunResult, FollowUpContext, FollowUpTurn, LocalSearchPlan, ResearchPlan
from ui.components import (
    clean_display_answer,
    render_follow_up_history,
    render_follow_up_input,
    render_header,
    render_metadata_line,
    render_sidebar_diagnostics,
    render_sources_panel,
    render_starter_examples,
    render_status,
)
from services.gemini_service import normalize_gemini_error
from ui.styles import apply_custom_styles
from workflows.follow_up import run_follow_up



EXAMPLE_QUESTIONS = [
    "Compare beginner-friendly Python AI-agent frameworks that work with Gemini.",
    "What are the current trends in the Indian stock market today?",
    "Compare Streamlit and FastAPI for a beginner building an AI agent.",
]


def initialise_session_state() -> None:
    """Initialize all session state keys safely."""
    defaults = {
        "query_input": "",
        "research_result": None,
        "answer": None,
        "sources": [],
        "plan": None,
        "searches_count": "—",
        "sources_count": "—",
        "latency_str": "—",
        "serpapi_status": "Not tested",
        "error": None,
        "last_run_started_at": None,
        "last_run_finished_at": None,
        "follow_up_context": None,
        "follow_up_history": [],
        "follow_up_input": "",
        "follow_up_error": None,
        "_clear_follow_up_input": False,
        "follow_up_input_box": "",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def set_example_query(chosen_query: str) -> None:
    """Callback to set the query input text safely on example selection."""
    st.session_state["query_input"] = chosen_query


def clear_research_state() -> None:
    """Reset all UI result and query state."""
    st.session_state["query_input"] = ""
    st.session_state["research_result"] = None
    st.session_state["answer"] = None
    st.session_state["sources"] = []
    st.session_state["plan"] = None
    st.session_state["searches_count"] = "—"
    st.session_state["sources_count"] = "—"
    st.session_state["latency_str"] = "—"
    st.session_state["error"] = None
    st.session_state["follow_up_context"] = None
    st.session_state["follow_up_history"] = []
    st.session_state["follow_up_input"] = ""
    st.session_state["follow_up_error"] = None
    st.session_state["_clear_follow_up_input"] = False
    st.session_state["follow_up_input_box"] = ""


def store_research_result(result: AgentRunResult, latency_seconds: float) -> None:
    """Persist research execution results and metrics into session state."""
    st.session_state["research_result"] = result
    if result.answer:
        st.session_state["answer"] = result.answer.answer_markdown
        st.session_state["sources"] = result.answer.sources
        st.session_state["follow_up_context"] = FollowUpContext(
            mode=result.plan.mode,
            original_question=(st.session_state.get("query_input") or "").strip(),
            preferences="",
            plan_goal=result.plan.goal,
            plan_criteria=result.plan.criteria if hasattr(result.plan, "criteria") else [],
            prior_answer=result.answer.answer_markdown,
            sources=result.answer.sources,
            limitations=result.answer.limitations,
            created_at=datetime.now(timezone.utc),
        )
        st.session_state["follow_up_history"] = []
        st.session_state["follow_up_input"] = ""
        st.session_state["follow_up_error"] = None
        st.session_state["_clear_follow_up_input"] = False
        st.session_state["follow_up_input_box"] = ""
    else:
        st.session_state["answer"] = None
        st.session_state["sources"] = []
        st.session_state["follow_up_context"] = None
        st.session_state["follow_up_history"] = []
        st.session_state["follow_up_input"] = ""
        st.session_state["follow_up_error"] = None
        st.session_state["_clear_follow_up_input"] = False
        st.session_state["follow_up_input_box"] = ""

    st.session_state["plan"] = result.plan
    if hasattr(result.plan, "queries"):
        st.session_state["searches_count"] = len(result.plan.queries)
    else:
        st.session_state["searches_count"] = 1
    st.session_state["sources_count"] = len(result.answer.sources) if result.answer else 0
    st.session_state["latency_str"] = f"{latency_seconds:.1f}s"
    st.session_state["serpapi_status"] = "Connected"
    st.session_state["error"] = None


def main() -> None:
    """Main application entry point."""
    st.set_page_config(
        page_title="ScoutAI",
        page_icon="📡",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    apply_custom_styles()
    initialise_session_state()

    settings = get_settings()

    # Left Sidebar: Hidden diagnostics and run metrics
    with st.sidebar:
        render_sidebar_diagnostics(settings, st.session_state)

    # Main Header
    render_header()

    # Query Input and Action Bar
    query_col, action_col, examples_col = st.columns([7.8, 1.8, 1.4], gap="small")

    with query_col:
        st.text_input(
            "Research question",
            placeholder="Ask about a current topic, compare options, or investigate a decision…",
            label_visibility="collapsed",
            key="query_input",
        )

    with action_col:
        research_btn = st.button(
            "✦ Research",
            type="primary",
            use_container_width=True,
            key="main_research_btn",
        )

    with examples_col:
        with st.popover("Examples", use_container_width=True):
            st.caption("Select a prompt:")
            for idx, ex in enumerate(EXAMPLE_QUESTIONS):
                st.button(
                    ex,
                    key=f"ex_pop_{idx}",
                    use_container_width=True,
                    on_click=set_example_query,
                    args=(ex,),
                )

    # Handle Research Execution
    if research_btn:
        cleaned_question = (st.session_state.get("query_input") or "").strip()
        if not cleaned_question:
            st.warning("Please enter a research question before starting.")
        else:
            # Clear previous result and pending state before starting a new run
            st.session_state["research_result"] = None
            st.session_state["answer"] = None
            st.session_state["sources"] = []
            st.session_state["plan"] = None
            st.session_state["error"] = None
            st.session_state["follow_up_context"] = None
            st.session_state["follow_up_history"] = []
            st.session_state["follow_up_input"] = ""
            st.session_state["follow_up_input_box"] = ""
            st.session_state["_clear_follow_up_input"] = False

            status_placeholder = st.empty()
            with status_placeholder.status("Researching live sources…", expanded=True) as status_box:
                start_time = time.perf_counter()

                def update_progress(step: int, msg: str) -> None:
                    status_box.write(f"• {msg}")

                try:
                    result = run_agent(cleaned_question, progress_callback=update_progress)
                    elapsed = time.perf_counter() - start_time
                    store_research_result(result, elapsed)
                    if result.answer:
                        status_box.update(label="Research complete", state="complete", expanded=False)
                    else:
                        status_box.update(label="No live sources retrieved", state="error", expanded=False)
                except Exception as exc:
                    clean_msg = normalize_gemini_error(exc)
                    st.session_state["error"] = clean_msg
                    st.session_state["serpapi_status"] = "Error"
                    status_box.update(label="Request could not be completed", state="error", expanded=True)
                    st.error(clean_msg)

    # Render Result or Empty State
    result: AgentRunResult | None = st.session_state.get("research_result")

    if result and result.answer:
        citation_valid = not bool(result.answer.limitations)
        source_count = len(result.answer.sources)
        query_count = len(result.plan.queries) if hasattr(result.plan, "queries") else 1

        st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

        main_col, sources_col = st.columns([2.2, 1], gap="large")

        with main_col:
            render_metadata_line(query_count, source_count, citation_valid)

            if result.plan.mode == AgentMode.LOCAL:
                brief_title = "Local discovery brief"
            elif result.plan.mode == AgentMode.SHOPPING:
                brief_title = "Shopping decision brief"
            else:
                brief_title = "Research brief"
            st.markdown(f"## {brief_title}")
            if result.plan.mode == AgentMode.SHOPPING:
                market_label = getattr(settings, "shopping_market_label", "India")
                st.caption(f"Shopping market: {market_label} · Prices and availability may change.")
            display_answer = clean_display_answer(result.answer.answer_markdown)
            st.markdown(display_answer)


            if result.answer.limitations:
                st.markdown("## What could not be verified")
                for lim in result.answer.limitations:
                    st.warning(f"⚠️ {lim}")

            # Follow-up Section
            follow_up_history = st.session_state.get("follow_up_history", [])
            render_follow_up_history(follow_up_history)

            render_follow_up_input()
            col_f_in, col_f_btn = st.columns([8.2, 1.8], gap="small")
            with col_f_in:
                if st.session_state.get("_clear_follow_up_input"):
                    st.session_state["follow_up_input_box"] = ""
                    st.session_state["_clear_follow_up_input"] = False
                st.text_input(
                    "Follow-up question",
                    placeholder="Ask a follow-up about these sources…",
                    label_visibility="collapsed",
                    key="follow_up_input_box",
                )
            with col_f_btn:
                ask_btn = st.button("Ask", key="follow_up_ask_btn", use_container_width=True)

            if ask_btn:
                follow_q = (st.session_state.get("follow_up_input_box") or "").strip()
                if not follow_q:
                    st.warning("Enter a follow-up question first.")
                elif not st.session_state.get("follow_up_context"):
                    st.warning("No active context for follow-up.")
                else:
                    with st.spinner("Analyzing follow-up against sources…"):
                        turn, error_msg = run_follow_up(
                            context=st.session_state["follow_up_context"],
                            follow_up_question=follow_q,
                            history=follow_up_history,
                        )
                    if error_msg:
                        st.info(error_msg)
                    elif turn:
                        follow_up_history.append(turn)
                        st.session_state["follow_up_history"] = follow_up_history[-2:]
                        st.session_state["_clear_follow_up_input"] = True
                        st.rerun()

            st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
            st.caption(
                "ℹ️ Sources and the research plan are available in the panel on the right."
            )

        with sources_col:
            try:
                render_sources_panel(result.answer.sources, mode=result.plan.mode)
            except Exception:
                st.caption("Sources could not be loaded, but the research brief completed successfully.")


    elif result and result.requires_clarification:
        st.warning(f"🤔 **Clarification Needed:** {result.clarification_question}")
    elif result and not result.answer:
        st.warning(result.status_message or "I could not retrieve usable live sources for this request. Please try again, rephrase the question, or start a new request later.")
    else:
        render_starter_examples(on_select_callback=set_example_query)


if __name__ == "__main__":
    main()

