"""Verifier prompt placeholder for future validation phase."""

VERIFIER_SYSTEM_PROMPT = """
You are the ScoutAI verifier.

Future role:
- Confirm that cited source IDs exist.
- Identify unsupported claims from the retrieved evidence.
- Keep output structured and deterministic.
""".strip()


def build_verifier_user_prompt(question: str, evidence_text: str) -> str:
    """Build a placeholder verifier prompt."""
    return (
        f"Question: {question.strip()}\n\n"
        f"Retrieved evidence:\n{evidence_text}\n\n"
        "Check source IDs and unsupported claims in a future verifier phase."
    )
