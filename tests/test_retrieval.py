"""
AURA Mars — Retrieval Unit Tests

Tests for retrieval functions (with mocked ChromaDB).
"""

import pytest
from unittest.mock import patch, MagicMock

from src.retrieval import retrieve
from src.models import RetrievedChunk


class TestRetrieve:
    """Tests for the retrieve function."""

    @patch("src.retrieval._embed_query")
    @patch("src.retrieval.get_collection")
    def test_retrieve_returns_chunks(self, mock_collection, mock_embed):
        """Returns RetrievedChunk objects from ChromaDB results."""
        mock_embed.return_value = [0.1] * 768

        mock_col = MagicMock()
        mock_col.query.return_value = {
            "documents": [["chunk text 1", "chunk text 2"]],
            "metadatas": [[
                {"source": "paper1", "source_type": "peer-reviewed"},
                {"source": "paper2", "source_type": "nasa-report"},
            ]],
            "distances": [[0.2, 0.4]],
        }
        mock_collection.return_value = mock_col

        results = retrieve("test question", top_k=2)

        assert len(results) == 2
        assert isinstance(results[0], RetrievedChunk)
        assert results[0].text == "chunk text 1"
        assert results[0].distance == 0.2
        assert results[1].metadata["source"] == "paper2"

    @patch("src.retrieval._embed_query")
    @patch("src.retrieval.get_collection")
    def test_retrieve_empty_results(self, mock_collection, mock_embed):
        """Returns empty list when no documents match."""
        mock_embed.return_value = [0.1] * 768

        mock_col = MagicMock()
        mock_col.query.return_value = {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }
        mock_collection.return_value = mock_col

        results = retrieve("obscure question", top_k=5)
        assert results == []
