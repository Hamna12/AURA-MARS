"""
AURA Mars — LLM Generation & Verification (Phase 4)

This is the ONLY module that calls the LLM for text generation.
The LLM is never asked to produce confidence numbers — only to
synthesise answers, verify claims, and explain externally-calculated scores.
"""

import re
import time
from typing import Callable, List, Optional

from src.config import (
    OLLAMA_LLM_MODEL,
    GENERATION_RUNS,
)
from src.models import RetrievedChunk, VerificationResult
from src.prompts import (
    GROUNDED_ANSWER_PROMPT,
    VERIFICATION_PROMPT,
    SCORE_EXPLANATION_PROMPT,
)
from src.utils import get_ollama_client


# ---------------------------------------------------------------------------
# Core LLM Call
# ---------------------------------------------------------------------------

def call_llm(prompt: str, num_predict: Optional[int] = None) -> str:
    """
    Send a single prompt to the Ollama LLM and return the response text.

    Parameters
    ----------
    prompt : str
        The full prompt to send.
    num_predict : int, optional
        Caps the model's maximum output tokens. Without this, Ollama uses
        its own default and a run can occasionally ramble far longer than
        the prompt actually calls for, adding minutes on CPU-only
        hardware for no benefit — callers pass a purpose-sized cap (see
        generate_answer / verify_answer / explain_score below) generous
        enough that it never truncates a normal response.

    Returns
    -------
    str
        The model's response text, or fallback explanation if failed.
    """
    started = time.perf_counter()
    print(f"[AURA][LLM] Calling {OLLAMA_LLM_MODEL} ({len(prompt)} chars prompt)...")
    try:
        client = get_ollama_client()
        options = {"num_predict": num_predict} if num_predict is not None else None
        response = client.generate(model=OLLAMA_LLM_MODEL, prompt=prompt, options=options)
        elapsed = time.perf_counter() - started
        text = response["response"]
        print(f"[AURA][LLM] {OLLAMA_LLM_MODEL} responded in {elapsed:.1f}s ({len(text)} chars)")
        return text
    except Exception as e:
        elapsed = time.perf_counter() - started
        print(f"[AURA][LLM] Error calling Ollama LLM ({OLLAMA_LLM_MODEL}) after {elapsed:.1f}s: {e}")
        # Return a structured fallback response to prevent parsing issues down the line
        return f"Error: Unable to generate response due to local LLM communication failure. Details: {str(e)}"



# ---------------------------------------------------------------------------
# Prompt Formatting Helpers
# ---------------------------------------------------------------------------

def _format_chunks_for_prompt(chunks: List[RetrievedChunk]) -> str:
    """Format retrieved chunks into a numbered list for prompt injection."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.metadata.get("source", "Unknown")
        parts.append(f"[Passage {i} — Source: {source}]\n{chunk.text}")
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# 7.1 — Grounded Answer Generation
# ---------------------------------------------------------------------------

def generate_answer(
    question: str,
    chunks: List[RetrievedChunk],
) -> str:
    """
    Generate a grounded answer using only the provided evidence chunks.

    Uses the prompt template from Section 7.1. The LLM is instructed
    to use ONLY the passages and respond in Claim/Source/Unknown format.

    Parameters
    ----------
    question : str
        The user's question.
    chunks : List[RetrievedChunk]
        Retrieved evidence chunks.

    Returns
    -------
    str
        The raw model response (Claim/Source/Unknown formatted).
    """
    formatted_chunks = _format_chunks_for_prompt(chunks)
    prompt = GROUNDED_ANSWER_PROMPT.format(
        retrieved_chunks=formatted_chunks,
        user_question=question,
    )
    # 900 tokens comfortably covers the full 8-section structured answer
    # (observed real responses run ~500-600 tokens) while bounding the
    # worst case instead of leaving it uncapped.
    return call_llm(prompt, num_predict=900)


def generate_multiple(
    question: str,
    chunks: List[RetrievedChunk],
    n: int = GENERATION_RUNS,
    on_run_complete: Optional[Callable[[int, int], None]] = None,
) -> List[str]:
    """
    Generate N independent answers for consistency scoring (Section 6.2).

    Each call is independent — the model sees the same prompt each time
    but may produce slightly different outputs due to sampling.

    Parameters
    ----------
    question : str
        The user's question.
    chunks : List[RetrievedChunk]
        Retrieved evidence chunks.
    n : int
        Number of independent generation runs.
    on_run_complete : callable, optional
        Called as on_run_complete(run_index_1_based, n) after each run
        finishes, so callers (e.g. the Streamlit UI) can show live
        progress across the N sequential LLM calls.

    Returns
    -------
    List[str]
        The N generated responses.
    """
    answers = []
    for i in range(n):
        answer = generate_answer(question, chunks)
        answers.append(answer)
        if on_run_complete:
            on_run_complete(i + 1, n)
    return answers


# ---------------------------------------------------------------------------
# 7.2 — Verification Pass
# ---------------------------------------------------------------------------

# Lines that are pure LLM scaffolding/meta-commentary rather than an actual
# claim — filtered out so they never show up in the UI as if they were a
# real unsupported claim (e.g. "**Claims Supported:**", "Conclusion:").
_VERIFICATION_META_LINE_DENYLIST = {
    "claims supported", "claim supported", "conclusion", "answer",
    "unsupported claims", "unsupported claim", "verified", "summary",
    "analysis", "reasoning", "explanation", "note",
}
# Substrings that mark a line as restating the verdict / intro preamble
# rather than quoting an actual claim (e.g. "Answer: Some claims
# verified.", "Here's an analysis of the provided answer..."). Only
# checked on shorter lines so a genuinely long Mars-science claim that
# happens to contain one of these words isn't accidentally dropped.
_VERIFICATION_META_PHRASES = (
    "claims supported", "claim supported", "unsupported claims",
    "unsupported claim", "claims verified", "some claims", "all claims",
    "here's an analysis", "here is an analysis", "here's a breakdown",
    "here is a breakdown",
)
_MAX_UNSUPPORTED_CLAIMS_SHOWN = 6


def _clean_verification_line(line: str) -> str:
    """Strip markdown bold/italic/heading noise a small local LLM tends to
    add even when told not to (e.g. '**Conclusion:**' -> 'Conclusion')."""
    cleaned = line.strip().lstrip("-•*#").strip()
    cleaned = cleaned.strip("*_").strip()
    cleaned = cleaned.rstrip(":*").strip()
    return cleaned


def _is_verification_meta_line(cleaned: str) -> bool:
    """True if a line looks like a header/label/preamble rather than a
    real quoted claim."""
    if len(cleaned) < 15:
        return True
    normalized = cleaned.lower().rstrip(":").strip()
    if normalized in _VERIFICATION_META_LINE_DENYLIST:
        return True
    if len(normalized) < 90 and any(phrase in normalized for phrase in _VERIFICATION_META_PHRASES):
        return True
    if normalized.startswith("here") and ("analysis" in normalized or "breakdown" in normalized):
        return True
    return False


def _parse_unsupported_claims(raw_response: str) -> List[str]:
    """
    Extract unsupported-claim strings from a verification response.

    ONLY trusts the strict "UNSUPPORTED:\\n- claim" format (see
    VERIFICATION_PROMPT) — deliberately does NOT fall back to scanning
    arbitrary free-form text. A model that ignores the format might
    structure its response with a "Claims Supported:" section followed
    by a "Conclusion:" — a naive line-scan can't tell those apart from
    genuinely unsupported claims, and mislabeling a *supported* claim as
    *unsupported* is worse than surfacing nothing. Callers should treat
    an empty return as "could not parse cleanly", not "nothing flagged".
    """
    claims: List[str] = []
    seen = set()

    def _add(candidate: str) -> None:
        cleaned = _clean_verification_line(candidate)
        if not cleaned or _is_verification_meta_line(cleaned):
            return
        key = cleaned.lower()
        if key in seen:
            return
        seen.add(key)
        claims.append(cleaned)

    match = re.search(r"UNSUPPORTED:\s*(.*)", raw_response, re.DOTALL | re.IGNORECASE)
    if match:
        for line in match.group(1).strip().split("\n"):
            line = line.strip()
            if line.startswith(("-", "•", "*")):
                _add(line)

    return claims[:_MAX_UNSUPPORTED_CLAIMS_SHOWN]


def verify_answer(
    answer: str,
    chunks: List[RetrievedChunk],
) -> VerificationResult:
    """
    Check whether every claim in the answer is supported by source passages.

    Uses the prompt template from Section 7.2.

    Parameters
    ----------
    answer : str
        The generated answer to verify.
    chunks : List[RetrievedChunk]
        The original source passages.

    Returns
    -------
    VerificationResult
        Whether verification passed and any unsupported claims found.
        unsupported_claims is capped and filtered for readability — the
        full unfiltered model output is always available in raw_response.
    """
    formatted_chunks = _format_chunks_for_prompt(chunks)
    prompt = VERIFICATION_PROMPT.format(
        generated_answer=answer,
        retrieved_chunks=formatted_chunks,
    )
    # Verification only needs a verdict plus a short list of unsupported
    # claims (observed real responses run ~150-200 tokens) — 400 is a
    # generous cap, not a typical target.
    raw_response = call_llm(prompt, num_predict=400)

    # "VERIFIED: yes" (strict format) or the old free-form phrasing, both accepted.
    verified = bool(re.search(r"VERIFIED:\s*yes", raw_response, re.IGNORECASE)) or (
        "all claims verified" in raw_response.lower()
    )

    unsupported = [] if verified else _parse_unsupported_claims(raw_response)

    # The model said "no" (or gave an unparseable free-form response) but
    # we couldn't cleanly extract which specific claims it meant. Say so
    # honestly rather than guessing — never mislabel a claim the model
    # actually said WAS supported as unsupported (see
    # _parse_unsupported_claims docstring).
    if not verified and not unsupported:
        unsupported = [
            "The verification pass did not return a clearly structured list of "
            "unsupported claims — see the raw response below for the model's full reasoning."
        ]

    return VerificationResult(
        verified=verified,
        unsupported_claims=unsupported,
        raw_response=raw_response,
    )


# ---------------------------------------------------------------------------
# 7.3 — Score Explanation
# ---------------------------------------------------------------------------

def explain_score(
    final_confidence: float,
    evidence_summary: str,
) -> str:
    """
    Ask the LLM to explain a confidence score it did NOT generate.

    The LLM receives the externally-calculated score and a summary of
    the evidence, then provides a one-sentence human-readable explanation.

    Parameters
    ----------
    final_confidence : float
        The calculated confidence score (0.0–1.0).
    evidence_summary : str
        A brief text summary of the evidence used.

    Returns
    -------
    str
        One-sentence explanation of the score.
    """
    prompt = SCORE_EXPLANATION_PROMPT.format(
        final_confidence=f"{final_confidence * 100:.1f}",
        evidence_summary=evidence_summary,
    )
    # One sentence, by design (observed real responses run ~50 tokens).
    return call_llm(prompt, num_predict=120).strip()


# ---------------------------------------------------------------------------
# Response Parsing Helpers
# ---------------------------------------------------------------------------

def parse_answer_sections(raw_answer: str) -> dict:
    """
    Parse a raw LLM response into Claim / Source / Unknown sections.

    Legacy parser kept for backward compatibility with the original
    Claim/Source/Unknown prompt format. Returns a dict with keys
    'claim', 'sources', 'unknowns'. Falls back to the full text as
    'claim' if parsing fails.
    """
    result = {"claim": "", "sources": "", "unknowns": ""}

    # Try to find each section using case-insensitive regex
    claim_match = re.search(
        r"Claim:\s*(.*?)(?=Source:|Unknown|Not covered|$)",
        raw_answer, re.DOTALL | re.IGNORECASE
    )
    source_match = re.search(
        r"Source:\s*(.*?)(?=Unknown|Not covered|$)",
        raw_answer, re.DOTALL | re.IGNORECASE
    )
    unknown_match = re.search(
        r"(?:Unknown|Not covered)[:/]?\s*(.*?)$",
        raw_answer, re.DOTALL | re.IGNORECASE
    )

    result["claim"] = claim_match.group(1).strip() if claim_match else raw_answer.strip()
    result["sources"] = source_match.group(1).strip() if source_match else ""
    result["unknowns"] = unknown_match.group(1).strip() if unknown_match else ""

    return result


# ---------------------------------------------------------------------------
# Structured Section Parsing (ANSWER / EVIDENCE / KNOWN / UNKNOWN / ...)
# ---------------------------------------------------------------------------

_STRUCTURED_SECTION_ORDER = [
    "answer",
    "evidence",
    "known",
    "unknown",
    "conflicting",
    "mission_relevance",
    "limitations",
    "follow_up",
]

# Maps internal key -> regex alternation of header text as it appears in
# the prompt (see src.prompts.GROUNDED_ANSWER_PROMPT).
_STRUCTURED_SECTION_HEADERS = {
    "answer": r"ANSWER",
    "evidence": r"EVIDENCE",
    "known": r"KNOWN",
    "unknown": r"UNKNOWN",
    "conflicting": r"CONFLICTING",
    "mission_relevance": r"MISSION_RELEVANCE",
    "limitations": r"LIMITATIONS",
    "follow_up": r"FOLLOW_UP",
}

_NO_CONFLICTS_FALLBACK = "No conflicts identified in the retrieved passages."


def _extract_section(raw_answer: str, key: str) -> str:
    """Extract a single labelled section's body text, or '' if absent.

    Headers must appear at the start of a line and be followed by a colon
    (e.g. "ANSWER:"). This is intentionally strict: a looser match (bare
    word, optional colon) would false-positive on ordinary prose — e.g.
    the word "answer" appearing mid-sentence in a free-text response —
    and silently mangle the fallback path for malformed/legacy responses.
    """
    header = _STRUCTURED_SECTION_HEADERS[key]
    other_headers = "|".join(
        h for k, h in _STRUCTURED_SECTION_HEADERS.items() if k != key
    )
    pattern = rf"^[ \t]*{header}[ \t]*:[ \t]*(.*?)(?=^[ \t]*(?:{other_headers})[ \t]*:|\Z)"
    match = re.search(pattern, raw_answer, re.DOTALL | re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else ""


def _parse_follow_up_list(section_text: str) -> List[str]:
    """Parse the FOLLOW_UP section body into a list of question strings."""
    if not section_text:
        return []

    questions = []
    for line in section_text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # Strip common bullet/number prefixes: "-", "*", "•", "1.", "1)"
        cleaned = re.sub(r"^[\-\*•]\s*|^\d+[\.\)]\s*", "", line).strip()
        if cleaned:
            questions.append(cleaned)

    return questions


def parse_structured_sections(raw_answer: str) -> dict:
    """
    Parse a raw LLM response into the structured Mission Console sections.

    Expects the ANSWER/EVIDENCE/KNOWN/UNKNOWN/CONFLICTING/MISSION_RELEVANCE/
    LIMITATIONS/FOLLOW_UP format produced by the current
    src.prompts.GROUNDED_ANSWER_PROMPT. Tolerant of missing sections —
    each missing section resolves to an empty string (or empty list for
    follow_up_questions), never raises.

    Returns
    -------
    dict
        Keys: answer, evidence, known, unknown, conflicting,
        mission_relevance, limitations, follow_up_questions (list[str]).
    """
    result = {key: "" for key in _STRUCTURED_SECTION_ORDER if key != "follow_up"}

    for key in _STRUCTURED_SECTION_ORDER:
        if key == "follow_up":
            continue
        result[key] = _extract_section(raw_answer, key)

    # Fallback: if nothing parsed at all (e.g. legacy-format or free-text
    # response), treat the whole response as the answer so the UI never
    # shows a blank card.
    if not any(result.values()):
        result["answer"] = raw_answer.strip()

    if not result["conflicting"]:
        result["conflicting"] = _NO_CONFLICTS_FALLBACK

    follow_up_raw = _extract_section(raw_answer, "follow_up")
    result["follow_up_questions"] = _parse_follow_up_list(follow_up_raw)

    return result
