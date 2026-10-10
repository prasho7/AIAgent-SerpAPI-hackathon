"""Grounded follow-up workflow and freshness detection."""

from __future__ import annotations

from datetime import datetime, timezone
import re

from config import Settings, get_settings
from models import FollowUpContext, FollowUpTurn
from processors.citation_validator import validate_citations
from services.gemini_service import GeminiService

FRESH_EVIDENCE_NOTICE = (
    "This follow-up needs fresh evidence. Start a new research request so ScoutAI can retrieve updated live sources."
)

ADDITIONAL_EVIDENCE_NOTICE = (
    "This follow-up needs additional live evidence. Start a new research request so ScoutAI can retrieve relevant sources."
)

FRESHNESS_PATTERNS = [
    r"\blatest\b",
    r"\bcurrent\b",
    r"\btoday\b",
    r"\bnow\b",
    r"\bright now\b",
    r"\blive\b",
    r"\bupdated\b",
    r"\bupdate\b",
    r"\bnew price\b",
    r"\bprice now\b",
    r"\bavailability\b",
    r"\bavailable\b",
    r"\bin stock\b",
    r"\bstock\b",
    r"\bdelivery\b",
    r"\bdelivered\b",
    r"\bshipping\b",
    r"\bopen now\b",
    r"\bopening hours\b",
    r"\bhours today\b",
    r"\bsearch again\b",
    r"\bfind more\b",
    r"\bmore options\b",
    r"\blook up\b",
    r"\bcheck online\b",
    r"\bre-search\b",
    r"\bresearch again\b",
]

ANALYSIS_STOPWORDS = {
    "a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or", "with", "is", "are",
    "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "can",
    "could", "should", "would", "will", "shall", "may", "might", "must", "it", "its", "they",
    "them", "their", "this", "that", "these", "those", "which", "what", "who", "whom", "whose",
    "why", "how", "where", "when", "all", "both", "each", "every", "other", "another", "such",
    "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "just", "more",
    "most", "some", "any", "compare", "comparison", "difference", "differences", "detail", "details",
    "summarize", "summary", "explain", "explanation", "pros", "cons", "recommend", "recommended",
    "recommendation", "beginner", "beginners", "cheaper", "cheapest", "better", "best", "worse",
    "worst", "option", "options", "first", "second", "third", "one", "two", "three", "about",
    "tell", "show", "give", "help", "list", "table", "versus", "vs", "between", "among", "fit",
    "fits", "good", "great", "fast", "faster", "fastest", "slow", "slower", "simple", "simpler",
    "easier", "easiest", "easy", "use", "using", "used", "work", "working", "works"
}


def requires_fresh_evidence(question: str) -> bool:
    """Check whether a follow-up question requests live/updated evidence or a new search."""
    text = (question or "").strip().lower()
    if not text:
        return False
    return any(re.search(pattern, text) for pattern in FRESHNESS_PATTERNS)


def is_out_of_evidence(context: FollowUpContext, question: str) -> bool:
    """Conservatively check if a follow-up explicitly asks about an entity/topic absent from evidence."""
    if not context or not context.sources:
        return True

    text = (question or "").strip().lower()
    if not text:
        return False

    corpus_parts: list[str] = [
        context.original_question.lower(),
        context.prior_answer.lower(),
    ]
    for s in context.sources:
        if hasattr(s, "title") and s.title:
            corpus_parts.append(s.title.lower())
        if hasattr(s, "snippet") and s.snippet:
            corpus_parts.append(s.snippet.lower())
        if hasattr(s, "name") and s.name:
            corpus_parts.append(s.name.lower())
        if hasattr(s, "address") and s.address:
            corpus_parts.append(s.address.lower())
        if hasattr(s, "merchant") and s.merchant:
            corpus_parts.append(s.merchant.lower())
        if hasattr(s, "category") and s.category:
            corpus_parts.append(s.category.lower())

    corpus = " ".join(corpus_parts)

    words = re.findall(r"\b[a-z0-9_\-\.]{3,}\b", text)
    query_terms = [w for w in words if w not in ANALYSIS_STOPWORDS]

    if query_terms and not any(term in corpus for term in query_terms):
        return True

    return False


def run_follow_up(
    context: FollowUpContext,
    follow_up_question: str,
    history: list[FollowUpTurn] | None = None,
    gemini_service: GeminiService | None = None,
    settings: Settings | None = None,
) -> tuple[FollowUpTurn | None, str | None]:
    """Execute a grounded follow-up query against existing curated context.

    Returns:
        (FollowUpTurn, None) on success
        (None, error_message) on client error, freshness trigger, or out-of-evidence query
    """
    cleaned_q = (follow_up_question or "").strip()
    if not cleaned_q:
        return None, "Enter a follow-up question first."

    # Step 1: Deterministic Freshness Check
    if requires_fresh_evidence(cleaned_q):
        return None, FRESH_EVIDENCE_NOTICE

    # Step 2: Deterministic Evidence Sufficiency Gate
    if is_out_of_evidence(context, cleaned_q):
        return None, ADDITIONAL_EVIDENCE_NOTICE

    # Step 3: Grounded Writing
    active_settings = settings or get_settings()
    service = gemini_service or GeminiService(active_settings)

    try:
        raw_answer = service.write_follow_up(
            context=context,
            follow_up_question=cleaned_q,
            history=history or [],
        )
    except Exception:
        return None, "Gemini is temporarily busy. Please wait a moment and try the same request again."

    # Step 4: Citation Validation
    citation_report = validate_citations(raw_answer, context.sources)
    citation_warning: str | None = None
    if not citation_report["valid"]:
        citation_warning = "Some follow-up citations could not be validated against the current sources."

    turn = FollowUpTurn(
        question=cleaned_q,
        answer=raw_answer,
        citation_warning=citation_warning,
        created_at=datetime.now(timezone.utc),
    )

    return turn, None
