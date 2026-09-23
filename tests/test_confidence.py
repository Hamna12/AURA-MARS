"""
AURA Mars — Confidence Scoring Unit Tests

Tests every scoring function with known inputs and expected outputs.
This is the most critical test module — confidence scoring must be
deterministic and verifiable.
"""

import pytest
from src.confidence import (
    calc_retrieval_match_strength,
    calc_source_count_score,
    calc_source_quality_score,
    final_confidence,
    confidence_label,
)
from src.models import RetrievedChunk


class TestRetrievalMatchStrength:
    """Tests for calc_retrieval_match_strength."""

    def test_perfect_match(self):
        """Distance of 0 → similarity of 1.0."""
        chunks = [
            RetrievedChunk(text="t", metadata={}, distance=0.0),
        ]
        assert calc_retrieval_match_strength(chunks) == 1.0

    def test_worst_match(self):
        """Distance of 2.0 (max cosine distance) → similarity of 0.0."""
        chunks = [
            RetrievedChunk(text="t", metadata={}, distance=2.0),
        ]
        assert calc_retrieval_match_strength(chunks) == 0.0

    def test_average_of_multiple(self):
        """Averages similarities across multiple chunks."""
        chunks = [
            RetrievedChunk(text="t", metadata={}, distance=0.0),   # sim = 1.0
            RetrievedChunk(text="t", metadata={}, distance=1.0),   # sim = 0.5
        ]
        result = calc_retrieval_match_strength(chunks)
        assert abs(result - 0.75) < 0.001

    def test_empty_chunks(self):
        """Returns 0.0 for empty input."""
        assert calc_retrieval_match_strength([]) == 0.0


class TestSourceCountScore:
    """Tests for calc_source_count_score."""

    def test_zero_sources(self):
        assert calc_source_count_score(0) == 0.0

    def test_one_source(self):
        assert calc_source_count_score(1) == 0.2  # 1/5

    def test_five_sources(self):
        assert calc_source_count_score(5) == 1.0  # 5/5

    def test_more_than_max(self):
        """Score caps at 1.0 even with more sources than normaliser."""
        assert calc_source_count_score(10) == 1.0

    def test_negative(self):
        assert calc_source_count_score(-1) == 0.0


class TestSourceQualityScore:
    """Tests for calc_source_quality_score."""

    def test_all_peer_reviewed(self):
        metas = [{"source_type": "peer-reviewed"}, {"source_type": "peer-reviewed"}]
        assert calc_source_quality_score(metas) == 1.0

    def test_mixed_quality(self):
        metas = [
            {"source_type": "peer-reviewed"},  # 1.0
            {"source_type": "preprint"},       # 0.6
        ]
        result = calc_source_quality_score(metas)
        assert abs(result - 0.8) < 0.001

    def test_empty_input(self):
        assert calc_source_quality_score([]) == 0.0

    def test_unknown_type(self):
        """Unknown source types default to 0.5."""
        metas = [{"source_type": "unknown_type"}]
        assert calc_source_quality_score(metas) == 0.5

    def test_missing_source_type_key(self):
        """Missing source_type key defaults to 'general' → 0.6."""
        metas = [{}]
        assert calc_source_quality_score(metas) == 0.6


class TestFinalConfidence:
    """Tests for final_confidence fusion."""

    def test_equal_scores(self):
        """When both inputs are 1.0, final should be 1.0."""
        assert final_confidence(1.0, 1.0) == 1.0

    def test_zero_scores(self):
        assert final_confidence(0.0, 0.0) == 0.0

    def test_weighted_fusion(self):
        """0.6 × 0.8 + 0.4 × 0.5 = 0.48 + 0.20 = 0.68."""
        result = final_confidence(0.8, 0.5)
        assert abs(result - 0.68) < 0.001


class TestConfidenceLabel:
    """Tests for confidence_label."""

    def test_high(self):
        assert confidence_label(0.75) == "High"
        assert confidence_label(0.70) == "High"
        assert confidence_label(1.0) == "High"

    def test_medium(self):
        assert confidence_label(0.50) == "Medium"
        assert confidence_label(0.40) == "Medium"
        assert confidence_label(0.69) == "Medium"

    def test_low(self):
        assert confidence_label(0.30) == "Low"
        assert confidence_label(0.0) == "Low"
        assert confidence_label(0.39) == "Low"
