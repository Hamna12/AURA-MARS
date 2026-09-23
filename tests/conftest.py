"""
AURA Mars — Shared Pytest Fixtures

Provides sample chunks, embeddings, and other test data
used across multiple test modules.
"""

import pytest
from src.models import Chunk, RetrievedChunk, ConfidenceBreakdown, VerificationResult


# ---------------------------------------------------------------------------
# Sample Chunks
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_chunks():
    """A set of sample Chunk objects for testing ingestion."""
    return [
        Chunk(
            text="Water ice has been detected in the shallow subsurface of Arcadia Planitia.",
            source="arcadia_study_2023",
            page=1,
            region_tag="arcadia_planitia",
            source_type="peer-reviewed",
            chunk_index=0,
        ),
        Chunk(
            text="The terrain in Arcadia Planitia is relatively flat, suitable for landing.",
            source="arcadia_study_2023",
            page=3,
            region_tag="arcadia_planitia",
            source_type="peer-reviewed",
            chunk_index=1,
        ),
        Chunk(
            text="Jezero Crater contains an ancient river delta with clay mineral deposits.",
            source="jezero_delta_2022",
            page=1,
            region_tag="jezero_crater",
            source_type="peer-reviewed",
            chunk_index=0,
        ),
    ]


@pytest.fixture
def sample_retrieved_chunks():
    """A set of sample RetrievedChunk objects for testing retrieval and scoring."""
    return [
        RetrievedChunk(
            text="Water ice has been detected in the shallow subsurface of Arcadia Planitia.",
            metadata={
                "source": "arcadia_study_2023",
                "source_type": "peer-reviewed",
                "region_tag": "arcadia_planitia",
                "chunk_index": "0",
            },
            distance=0.25,
        ),
        RetrievedChunk(
            text="Radar sounding data confirms ice deposits at 1-2m depth in Arcadia.",
            metadata={
                "source": "radar_analysis_2024",
                "source_type": "nasa-report",
                "region_tag": "arcadia_planitia",
                "chunk_index": "0",
            },
            distance=0.30,
        ),
        RetrievedChunk(
            text="Subsurface water ice was mapped across northern lowland plains.",
            metadata={
                "source": "northern_ice_survey",
                "source_type": "peer-reviewed",
                "region_tag": "",
                "chunk_index": "5",
            },
            distance=0.40,
        ),
    ]


@pytest.fixture
def sample_confidence():
    """A sample ConfidenceBreakdown for testing display components."""
    return ConfidenceBreakdown(
        source_agreement=0.85,
        retrieval_match_strength=0.78,
        source_count_score=0.60,
        source_quality_score=0.95,
        evidence_confidence=0.80,
        generation_consistency=0.72,
        final_confidence=0.77,
        label="High",
    )


@pytest.fixture
def sample_verification_pass():
    """A passing verification result."""
    return VerificationResult(
        verified=True,
        unsupported_claims=[],
        raw_response="All claims verified.",
    )


@pytest.fixture
def sample_verification_fail():
    """A failing verification result."""
    return VerificationResult(
        verified=False,
        unsupported_claims=["Mars has a breathable atmosphere"],
        raw_response="The claim 'Mars has a breathable atmosphere' is not supported.",
    )
