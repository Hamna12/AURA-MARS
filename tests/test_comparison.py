"""
AURA Mars — Region Comparison Unit Tests

Tests for the deterministic, Pandas-driven region comparison engine.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.comparison import (
    load_region_metadata,
    get_region_names,
    get_default_weights,
    score_region,
    compare_regions,
)
from src.models import RegionScore



class TestLoadRegionMetadata:
    """Tests for loading region metadata."""

    def test_loads_successfully(self):
        """Metadata file loads and contains expected structure."""
        data = load_region_metadata()
        assert "regions" in data
        assert "criteria_definitions" in data
        assert "default_weights" in data
        assert len(data["regions"]) == 3

    def test_region_names(self):
        """Returns expected region names."""
        names = get_region_names()
        assert "Jezero Crater" in names
        assert "Arcadia Planitia" in names
        assert "Hellas Planitia" in names


class TestScoreRegion:
    """Tests for score_region."""

    @patch("src.comparison.retrieve")
    @patch("src.comparison.calc_retrieval_match_strength")
    def test_basic_scoring(self, mock_strength, mock_retrieve):
        """Correctly applies weights to retrieved match scores."""
        # Setup mocks
        mock_retrieve.return_value = [MagicMock()]
        mock_strength.return_value = 0.8

        region = {
            "name": "Test Region",
        }
        weights = {
            "water_ice_evidence": 0.5,
            "terrain_accessibility": 0.5,
        }
        
        result = score_region(region, weights)
        assert isinstance(result, RegionScore)
        assert result.region_name == "Test Region"
        # Since retrieve is mocked to succeed, both criteria score 0.8
        # 0.8 * 0.5 + 0.8 * 0.5 = 0.80
        assert abs(result.total_score - 0.80) < 0.001

    @patch("src.comparison.retrieve")
    def test_missing_retrieval_defaults_to_zero(self, mock_retrieve):
        """Missing or empty retrieval results default to 0.0."""
        mock_retrieve.return_value = []

        region = {
            "name": "Sparse Region",
        }
        weights = {
            "water_ice_evidence": 1.0,
        }
        result = score_region(region, weights)
        assert result.criteria_scores["water_ice_evidence"] == 0.0
        assert result.total_score == 0.0


class TestCompareRegions:
    """Tests for compare_regions."""

    @patch("src.comparison.retrieve")
    @patch("src.comparison.calc_retrieval_match_strength")
    def test_returns_dataframe(self, mock_strength, mock_retrieve):
        """Returns a DataFrame with all regions."""
        mock_retrieve.return_value = [MagicMock()]
        mock_strength.return_value = 0.6

        df = compare_regions()
        assert len(df) == 3
        assert "Region" in df.columns
        assert "Total Score" in df.columns
        # Each criteria gets 0.6. Since weights sum to 1.0, total score is 0.6.
        assert abs(df.iloc[0]["Total Score"] - 0.6) < 0.001

    @patch("src.comparison.retrieve")
    @patch("src.comparison.calc_retrieval_match_strength")
    def test_sorted_by_total_descending(self, mock_strength, mock_retrieve):
        """Results are sorted by Total Score in descending order."""
        mock_retrieve.return_value = [MagicMock()]
        # Return different scores for different regions using side_effect
        # 6 criteria per region, 3 regions = 18 calls
        # Let's mock scores so Jezero gets 0.9, Arcadia 0.7, Hellas 0.5
        scores = []
        for base in [0.9, 0.7, 0.5]:  # one base score per region
            scores.extend([base] * 6)
        mock_strength.side_effect = scores

        df = compare_regions()
        totals = df["Total Score"].tolist()
        assert totals == sorted(totals, reverse=True)
        assert df.iloc[0]["Region"] == "Jezero Crater"  # got 0.9 base scores
        assert df.iloc[2]["Region"] == "Hellas Planitia"  # got 0.5 base scores

    @patch("src.comparison.retrieve")
    @patch("src.comparison.calc_retrieval_match_strength")
    def test_subset_of_regions(self, mock_strength, mock_retrieve):
        """Can compare a subset of regions."""
        mock_retrieve.return_value = [MagicMock()]
        mock_strength.return_value = 0.5

        df = compare_regions(region_names=["Jezero Crater", "Hellas Planitia"])
        assert len(df) == 2
        assert "Jezero Crater" in df["Region"].values
        assert "Hellas Planitia" in df["Region"].values
        assert "Arcadia Planitia" not in df["Region"].values

