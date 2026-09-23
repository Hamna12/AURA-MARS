"""
AURA Mars — Ingestion Unit Tests

Tests for PDF text extraction and text chunking.
"""

import pytest
from src.ingest import chunk_text


class TestChunkText:
    """Tests for the chunk_text function."""

    def test_basic_chunking(self):
        """Chunks a string into segments of the specified size."""
        text = " ".join([f"word{i}" for i in range(100)])
        chunks = chunk_text(text, chunk_size=20, overlap=5)
        assert len(chunks) > 1
        # First chunk should have approximately 20 words
        assert len(chunks[0].split()) == 20

    def test_overlap_creates_shared_words(self):
        """Consecutive chunks share words from the overlap region."""
        text = " ".join([f"word{i}" for i in range(50)])
        chunks = chunk_text(text, chunk_size=20, overlap=5)
        # Last 5 words of chunk 0 should appear at the start of chunk 1
        words_0 = chunks[0].split()
        words_1 = chunks[1].split()
        assert words_0[-5:] == words_1[:5]

    def test_empty_text(self):
        """Returns empty list for empty input."""
        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_text_shorter_than_chunk_size(self):
        """Returns single chunk when text is shorter than chunk_size."""
        text = "short text here"
        chunks = chunk_text(text, chunk_size=100, overlap=10)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_single_word(self):
        """Handles single-word input."""
        chunks = chunk_text("hello", chunk_size=10, overlap=2)
        assert len(chunks) == 1
        assert chunks[0] == "hello"

    def test_zero_overlap(self):
        """Works with zero overlap (no shared words)."""
        text = " ".join([f"w{i}" for i in range(20)])
        chunks = chunk_text(text, chunk_size=10, overlap=0)
        assert len(chunks) == 2
        # No shared words
        words_0 = set(chunks[0].split())
        words_1 = set(chunks[1].split())
        assert words_0.isdisjoint(words_1)
