"""
AURA Mars — Confidence Scoring (Phase 3)

ALL scoring is deterministic Python. This module contains ZERO LLM calls.
This is a non-negotiable architectural rule.

Implements:
    Section 6.1 — Evidence Confidence (from retrieval)
    Section 6.2 — Generation Consistency (from model outputs)
    Section 6.3 — Final Confidence Fusion
"""

from typing import List, Dict
from itertools import combinations

import numpy as np

from src.config import (
    WEIGHT_SOURCE_AGREEMENT,
    WEIGHT_RETRIEVAL_MATCH,
    WEIGHT_SOURCE_COUNT,
    WEIGHT_SOURCE_QUALITY,
    WEIGHT_EVIDENCE,
    WEIGHT_CONSISTENCY,
    CONFIDENCE_HIGH_THRESHOLD,
    CONFIDENCE_MEDIUM_THRESHOLD,
    SOURCE_QUALITY_MAP,
    SOURCE_COUNT_NORMALISER,
    OLLAMA_EMBED_MODEL,
)
from src.models import RetrievedChunk, ConfidenceBreakdown
from src.utils import cosine_similarity, get_ollama_client



# ===================================================================
# Section 6.1 — Evidence Confidence
# ===================================================================

def calc_source_agreement(chunks: List[RetrievedChunk]) -> float:
    """
    Measure the fraction of retrieved chunks that agree with each other.

    Uses pairwise semantic similarity between chunk texts (via embeddings)
    as a proxy for agreement. Reuses pre-computed chunk embeddings from ChromaDB
    for maximum efficiency, falling back to live embedding if unavailable.

    Returns a float in [0.0, 1.0].
    """
    if len(chunks) < 2:
        return 1.0 if chunks else 0.0

    embeddings = []
    client = None

    for chunk in chunks:
        # Check if we already have the pre-computed embedding from ChromaDB query
        if chunk.embedding is not None:
            embeddings.append(chunk.embedding)
        else:
            # Fallback to computing embedding via Ollama
            if client is None:
                client = get_ollama_client()
            try:
                response = client.embed(model=OLLAMA_EMBED_MODEL, input=chunk.text)
                embeddings.append(response["embeddings"][0])
            except Exception as e:
                # If embedding computation fails, log and skip/fallback
                print(f"Warning: Failed to compute fallback chunk embedding: {e}")
                # We can append a dummy vector or continue
                continue

    # Compute pairwise cosine similarities
    similarities = []
    for (e1, e2) in combinations(embeddings, 2):
        sim = cosine_similarity(e1, e2)
        similarities.append(sim)

    if not similarities:
        return 0.0

    # Average pairwise similarity, clamped to [0, 1]
    avg_sim = float(np.mean(similarities))
    return max(0.0, min(1.0, avg_sim))



def calc_retrieval_match_strength(chunks: List[RetrievedChunk]) -> float:
    """
    Average ChromaDB distance of top-k chunks, normalised to [0.0, 1.0].

    ChromaDB cosine distance ranges from 0 (identical) to 2 (opposite).
    We convert: similarity = 1 - (distance / 2).

    Returns a float in [0.0, 1.0].
    """
    if not chunks:
        return 0.0

    similarities = [1.0 - (chunk.distance / 2.0) for chunk in chunks]
    avg = float(np.mean(similarities))
    return max(0.0, min(1.0, avg))


def calc_source_count_score(count: int) -> float:
    """
    Normalised function of the number of relevant sources retrieved.

    Formula: min(count / SOURCE_COUNT_NORMALISER, 1.0)

    Returns a float in [0.0, 1.0].
    """
    if count <= 0:
        return 0.0
    return min(count / SOURCE_COUNT_NORMALISER, 1.0)


def calc_source_quality_score(chunk_metadatas: List[Dict[str, str]]) -> float:
    """
    Weighted average quality score based on source type of each chunk.

    Source types map to quality scores defined in config.SOURCE_QUALITY_MAP.
    Unknown types default to 0.5.

    Returns a float in [0.0, 1.0].
    """
    if not chunk_metadatas:
        return 0.0

    scores = []
    for meta in chunk_metadatas:
        source_type = meta.get("source_type", "general")
        quality = SOURCE_QUALITY_MAP.get(source_type, 0.5)
        scores.append(quality)

    return float(np.mean(scores))


def evidence_confidence(chunks: List[RetrievedChunk]) -> ConfidenceBreakdown:
    """
    Calculate the Evidence Confidence score (Section 6.1).

    Evidence Confidence = (0.35 × Source Agreement)
                        + (0.30 × Retrieval Match Strength)
                        + (0.20 × Source Count Score)
                        + (0.15 × Source Quality Score)

    Parameters
    ----------
    chunks : List[RetrievedChunk]
        Retrieved chunks from the vector search.

    Returns
    -------
    ConfidenceBreakdown
        Partial breakdown with evidence-side fields populated.
    """
    source_agreement = calc_source_agreement(chunks)
    retrieval_match = calc_retrieval_match_strength(chunks)
    source_count = calc_source_count_score(len(chunks))
    source_quality = calc_source_quality_score(
        [c.metadata for c in chunks]
    )

    ev_conf = (
        WEIGHT_SOURCE_AGREEMENT * source_agreement
        + WEIGHT_RETRIEVAL_MATCH * retrieval_match
        + WEIGHT_SOURCE_COUNT * source_count
        + WEIGHT_SOURCE_QUALITY * source_quality
    )

    return ConfidenceBreakdown(
        source_agreement=source_agreement,
        retrieval_match_strength=retrieval_match,
        source_count_score=source_count,
        source_quality_score=source_quality,
        evidence_confidence=ev_conf,
    )


# ===================================================================
# Section 6.2 — Generation Consistency
# ===================================================================

def generation_consistency(answers: List[str]) -> float:
    """
    Measure how stable the model's outputs are across N generation runs.

    Embeds each answer via nomic-embed-text and computes the mean
    pairwise cosine similarity.

    Parameters
    ----------
    answers : List[str]
        The N generated answers from repeated runs of the same prompt.

    Returns
    -------
    float
        Consistency score in [0.0, 1.0].
    """
    if len(answers) < 2:
        return 1.0 if answers else 0.0

    client = get_ollama_client()

    embeddings = []
    for answer in answers:
        try:
            response = client.embed(model=OLLAMA_EMBED_MODEL, input=answer)
            embeddings.append(response["embeddings"][0])
        except Exception as e:
            print(f"Error computing embedding for answer consistency: {e}")
            continue

    similarities = []
    for (e1, e2) in combinations(embeddings, 2):
        sim = cosine_similarity(e1, e2)
        similarities.append(sim)

    if not similarities:
        return 0.0

    avg_sim = float(np.mean(similarities))
    return max(0.0, min(1.0, avg_sim))



# ===================================================================
# Section 6.3 — Final Confidence Fusion
# ===================================================================

def final_confidence(ev_conf: float, gen_consistency: float) -> float:
    """
    Fuse evidence confidence and generation consistency into a final score.

    Final Confidence = (0.6 × Evidence Confidence) + (0.4 × Generation Consistency)

    Returns a float in [0.0, 1.0].
    """
    return WEIGHT_EVIDENCE * ev_conf + WEIGHT_CONSISTENCY * gen_consistency


def confidence_label(score: float) -> str:
    """
    Map a 0.0–1.0 confidence score to a human-readable tier label.

    ≥ 0.70 → "High"
    ≥ 0.40 → "Medium"
    < 0.40 → "Low"
    """
    percentage = score * 100
    if percentage >= CONFIDENCE_HIGH_THRESHOLD:
        return "High"
    elif percentage >= CONFIDENCE_MEDIUM_THRESHOLD:
        return "Medium"
    else:
        return "Low"
