"""
AURA Mars — Pipeline Integration Tests

Tests the full pipeline orchestration with mocked external dependencies
(Ollama and ChromaDB).
"""

import pytest
from unittest.mock import patch, MagicMock

from src.pipeline import run_pipeline, _build_evidence_summary
from src.models import RetrievedChunk


class TestBuildEvidenceSummary:
    """Tests for _build_evidence_summary helper."""

    def test_summary_includes_count_and_sources(self):
        chunks = [
            RetrievedChunk(
                text="text1",
                metadata={"source": "paper1", "source_type": "peer-reviewed"},
                distance=0.3,
            ),
            RetrievedChunk(
                text="text2",
                metadata={"source": "paper2", "source_type": "nasa-report"},
                distance=0.4,
            ),
        ]
        summary = _build_evidence_summary(chunks)
        assert "2 passages" in summary
        assert "2 source(s)" in summary
        assert "paper1" in summary
        assert "paper2" in summary

    def test_empty_chunks(self):
        summary = _build_evidence_summary([])
        assert "0 passages" in summary


class TestRunPipeline:
    """Integration tests for run_pipeline (with mocked externals)."""

    @patch("src.pipeline.explain_score")
    @patch("src.pipeline.verify_answer")
    @patch("src.pipeline.generate_multiple")
    @patch("src.pipeline.generation_consistency")
    @patch("src.pipeline.evidence_confidence")
    @patch("src.pipeline.retrieve")
    def test_pipeline_with_no_results(
        self, mock_retrieve, mock_ev_conf, mock_gen_cons,
        mock_gen_multi, mock_verify, mock_explain,
    ):
        """Pipeline handles no retrieved documents gracefully."""
        mock_retrieve.return_value = []

        result = run_pipeline("test question")

        assert result.question == "test question"
        assert "No relevant documents" in result.claim
        assert result.confidence.label == "Low"
        # Should not call generation if no chunks retrieved
        mock_gen_multi.assert_not_called()
