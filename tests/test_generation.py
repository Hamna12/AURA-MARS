"""
AURA Mars — Generation Unit Tests

Tests for prompt construction, response parsing, and LLM call wrappers.
LLM calls are mocked to avoid requiring a running Ollama instance.
"""

import pytest
from unittest.mock import patch

from src.generation import (
    parse_answer_sections,
    _format_chunks_for_prompt,
)
from src.models import RetrievedChunk


class TestParseAnswerSections:
    """Tests for parse_answer_sections."""

    def test_well_formatted_response(self):
        """Parses a properly formatted Claim/Source/Unknown response."""
        raw = (
            "Claim: Water ice exists in Arcadia Planitia subsurface.\n"
            "Source: Passage 1, Passage 3\n"
            "Unknown/Not covered: Long-term stability of ice deposits."
        )
        parsed = parse_answer_sections(raw)
        assert "Water ice" in parsed["claim"]
        assert "Passage 1" in parsed["sources"]
        assert "stability" in parsed["unknowns"]

    def test_missing_sections(self):
        """Falls back gracefully when sections are missing."""
        raw = "Just a plain answer without sections."
        parsed = parse_answer_sections(raw)
        assert parsed["claim"] == raw.strip()
        assert parsed["sources"] == ""
        assert parsed["unknowns"] == ""

    def test_empty_input(self):
        """Handles empty string input."""
        parsed = parse_answer_sections("")
        assert parsed["claim"] == ""

    def test_only_claim(self):
        """Handles response with only a Claim section."""
        raw = "Claim: Mars has a thin atmosphere."
        parsed = parse_answer_sections(raw)
        assert "thin atmosphere" in parsed["claim"]


class TestFormatChunksForPrompt:
    """Tests for _format_chunks_for_prompt."""

    def test_formats_with_source_names(self):
        """Each chunk is labeled with its passage number and source."""
        chunks = [
            RetrievedChunk(
                text="Some text about Mars.",
                metadata={"source": "paper1"},
                distance=0.3,
            ),
            RetrievedChunk(
                text="More text about ice.",
                metadata={"source": "paper2"},
                distance=0.5,
            ),
        ]
        result = _format_chunks_for_prompt(chunks)
        assert "[Passage 1 — Source: paper1]" in result
        assert "[Passage 2 — Source: paper2]" in result
        assert "Some text about Mars." in result

    def test_empty_chunks(self):
        """Returns empty string for no chunks."""
        assert _format_chunks_for_prompt([]) == ""
