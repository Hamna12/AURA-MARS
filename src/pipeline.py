"""
AURA Mars — End-to-End Pipeline Orchestration

Wires together: retrieve → generate (×N) → score → verify → explain.
Produces a complete PipelineResult for consumption by the UI or CLI.
"""

import time
from typing import Callable, Optional

from src.config import GENERATION_RUNS
from src.models import PipelineResult, RetrievedChunk
from src.retrieval import retrieve
from src.confidence import (
    evidence_confidence,
    generation_consistency,
    final_confidence,
    confidence_label,
)
from src.generation import (
    generate_multiple,
    verify_answer,
    explain_score,
    parse_structured_sections,
)
from src.mission_relevance import identify_mission_areas
from src.utils import format_confidence_display


def _build_evidence_summary(chunks: list[RetrievedChunk]) -> str:
    """Build a concise evidence summary string for the score explanation prompt."""
    unique_sources = set()
    for chunk in chunks:
        source = chunk.metadata.get("source", "Unknown")
        source_type = chunk.metadata.get("source_type", "unknown")
        unique_sources.add(f"{source} ({source_type})")

    return (
        f"{len(chunks)} passages retrieved from {len(unique_sources)} source(s): "
        + ", ".join(sorted(unique_sources))
    )


def run_pipeline(
    question: str,
    top_k: Optional[int] = None,
    generation_runs: Optional[int] = None,
    on_progress: Optional[Callable[[str], None]] = None,
) -> PipelineResult:
    """
    Run the full AURA Mars pipeline for a single question.

    Flow:
        1. Retrieve top-k evidence chunks from ChromaDB
        2. Generate N independent answers using the grounded prompt
        3. Calculate Evidence Confidence (deterministic Python)
        4. Calculate Generation Consistency (embed + compare N outputs)
        5. Fuse into Final Confidence score
        6. Select the best answer and run verification pass
        7. Generate a human-readable score explanation
        8. Package everything into a PipelineResult

    Parameters
    ----------
    question : str
        The user's natural-language question.
    top_k : int, optional
        Override the default retrieval count.
    generation_runs : int, optional
        Override the default number of generation runs.
    on_progress : callable, optional
        Called with a short status string at each major step. Every local
        LLM call in this pipeline is synchronous and can take a while, so
        this exists purely to give callers (e.g. the Streamlit UI) a way
        to show live progress instead of a silent wait. Always also
        printed to stdout regardless of whether this is supplied.

    Returns
    -------
    PipelineResult
        Complete structured result with claim, sources, confidence, unknowns, etc.
    """
    def _progress(message: str) -> None:
        print(f"[AURA] {message}")
        if on_progress:
            on_progress(message)

    n_runs = generation_runs or GENERATION_RUNS
    result = PipelineResult(question=question)
    pipeline_started = time.perf_counter()

    # Step 1: Retrieve
    _progress("Retrieving evidence from ChromaDB...")
    step_started = time.perf_counter()
    kwargs = {}
    if top_k is not None:
        kwargs["top_k"] = top_k
    chunks = retrieve(question, **kwargs)
    result.retrieved_chunks = chunks
    _progress(f"Retrieved {len(chunks)} passage(s) in {time.perf_counter() - step_started:.1f}s.")

    if not chunks:
        result.claim = "No relevant documents found for this question."
        result.unknowns = "The knowledge base does not contain documents related to this query."
        result.confidence.label = "Low"
        result.mission_areas = identify_mission_areas(question)
        return result

    # Step 2: Generate N answers for consistency scoring
    step_started = time.perf_counter()

    def _on_run_complete(run_index: int, total_runs: int) -> None:
        _progress(f"Generated answer {run_index}/{total_runs} ({time.perf_counter() - step_started:.1f}s elapsed).")

    raw_answers = generate_multiple(question, chunks, n=n_runs, on_run_complete=_on_run_complete)
    result.raw_answers = raw_answers

    # Step 3: Evidence Confidence (deterministic)
    ev_breakdown = evidence_confidence(chunks)

    # Step 4: Generation Consistency (embed + compare)
    _progress("Scoring generation consistency across runs...")
    gen_cons = generation_consistency(raw_answers)

    # Step 5: Final Confidence Fusion
    final_conf = final_confidence(ev_breakdown.evidence_confidence, gen_cons)
    label = confidence_label(final_conf)

    result.confidence = ev_breakdown
    result.confidence.generation_consistency = gen_cons
    result.confidence.final_confidence = final_conf
    result.confidence.label = label

    # Step 6: Select the primary answer (first run) and parse it
    primary_answer = raw_answers[0]
    parsed = parse_structured_sections(primary_answer)
    result.claim = parsed["answer"]
    result.unknowns = parsed["unknown"]
    result.evidence_summary = parsed["evidence"]
    result.known = parsed["known"]
    result.conflicting = parsed["conflicting"]
    result.mission_relevance_text = parsed["mission_relevance"]
    result.limitations = parsed["limitations"]
    result.follow_up_questions = parsed["follow_up_questions"]

    # Source list is always derived from retrieved chunk metadata — the
    # structured prompt no longer asks the LLM to list sources itself.
    seen = set()
    deduped_sources = []
    for c in chunks:
        src = c.metadata.get("source", "Unknown")
        if src not in seen:
            seen.add(src)
            deduped_sources.append(src)
    result.sources = deduped_sources

    # Deterministic (non-LLM) mission-area tagging of the question.
    result.mission_areas = identify_mission_areas(question)

    # Step 7: Verification pass
    _progress("Verifying claims against source passages...")
    result.verification = verify_answer(primary_answer, chunks)

    # Step 8: Score explanation
    _progress("Generating score explanation...")
    evidence_summary = _build_evidence_summary(chunks)
    result.score_explanation = explain_score(final_conf, evidence_summary)

    _progress(f"Pipeline complete in {time.perf_counter() - pipeline_started:.1f}s.")

    return result
