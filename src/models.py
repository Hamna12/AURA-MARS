"""
AURA Mars — Shared Data Models

All dataclasses used across the pipeline live here to prevent circular imports.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class Chunk:
    """A text chunk extracted from a source document."""
    text: str
    source: str          # filename or document title
    page: Optional[int] = None
    region_tag: Optional[str] = None
    source_type: str = "general"  # peer-reviewed | nasa-dataset | nasa-report | preprint | general
    chunk_index: int = 0
    # --- Optional citation metadata (Mission Console presentation layer) ---
    # These are best-effort fields for nicer source cards. They default to
    # empty/derived values when not supplied at ingestion time — never
    # fabricated. See src/ingest.py for fallback derivation logic.
    title: str = ""
    year: str = ""
    authors: str = ""
    url: str = ""
    pdf_url: str = ""
    doi: str = ""


@dataclass
class RetrievedChunk:
    """A chunk returned from vector search, with its similarity distance."""
    text: str
    metadata: Dict[str, str]
    distance: float       # ChromaDB distance (lower = more similar)
    embedding: Optional[List[float]] = None



@dataclass
class VerificationResult:
    """Result of the LLM verification pass."""
    verified: bool
    unsupported_claims: List[str] = field(default_factory=list)
    raw_response: str = ""


@dataclass
class IngestReport:
    """Summary of a document ingestion run."""
    files_processed: int = 0
    chunks_created: int = 0
    errors: List[str] = field(default_factory=list)


@dataclass
class ConfidenceBreakdown:
    """Detailed breakdown of the confidence calculation."""
    source_agreement: float = 0.0
    retrieval_match_strength: float = 0.0
    source_count_score: float = 0.0
    source_quality_score: float = 0.0
    evidence_confidence: float = 0.0
    generation_consistency: float = 0.0
    final_confidence: float = 0.0
    label: str = "Low"


@dataclass
class PipelineResult:
    """Complete output of the AURA Mars pipeline for a single question."""
    question: str
    claim: str = ""
    sources: List[str] = field(default_factory=list)
    unknowns: str = ""
    confidence: ConfidenceBreakdown = field(default_factory=ConfidenceBreakdown)
    verification: VerificationResult = field(default_factory=lambda: VerificationResult(verified=False))
    score_explanation: str = ""
    retrieved_chunks: List[RetrievedChunk] = field(default_factory=list)
    raw_answers: List[str] = field(default_factory=list)
    # --- Structured presentation fields (Mission Console) ---
    # Populated from the structured LLM answer (see src/prompts.py
    # GROUNDED_ANSWER_PROMPT) via src.generation.parse_structured_sections.
    # All default to empty — purely additive, does not affect existing
    # `claim` / `sources` / `unknowns` behaviour.
    evidence_summary: str = ""       # EVIDENCE section
    known: str = ""                  # KNOWN section
    conflicting: str = ""            # CONFLICTING section
    mission_relevance_text: str = "" # MISSION_RELEVANCE section (LLM narrative)
    limitations: str = ""            # LIMITATIONS section
    follow_up_questions: List[str] = field(default_factory=list)  # FOLLOW_UP section
    # Deterministic (non-LLM) mission-area classification of the question.
    # See src/mission_relevance.py — keyword-based, explainable.
    mission_areas: List[str] = field(default_factory=list)


@dataclass
class RegionScore:
    """Scoring result for a single candidate Mars region."""
    region_name: str
    criteria_scores: Dict[str, float] = field(default_factory=dict)
    weighted_scores: Dict[str, float] = field(default_factory=dict)
    total_score: float = 0.0
