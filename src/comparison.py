"""
AURA Mars — Region Comparison Engine

Deterministic, Pandas-driven comparison of candidate Mars regions.
This is NOT LLM-driven — all scoring uses the weighted formula in Python.
"""

import json
from typing import Dict, List, Optional

import pandas as pd

from src.config import REGION_METADATA_PATH
from src.models import RegionScore


_cached_metadata = None

def load_region_metadata() -> dict:
    """
    Load region metadata from the JSON file. Caches the result in memory
    for efficiency and includes a robust fallback if loading fails.

    Returns
    -------
    dict
        The parsed region metadata.
    """
    global _cached_metadata
    if _cached_metadata is not None:
        return _cached_metadata

    try:
        with open(REGION_METADATA_PATH, "r", encoding="utf-8") as f:
            _cached_metadata = json.load(f)
            return _cached_metadata
    except Exception as e:
        print(f"Error loading region metadata from {REGION_METADATA_PATH}: {e}")
        # Fallback to minimal hardcoded default schema to prevent app crash
        return {
            "regions": [
                {
                    "name": "Jezero Crater",
                    "lat": 18.4386,
                    "lon": 77.4508,
                    "description": "Ancient river delta and lake bed. Astrobiology focus.",
                    "criteria": {"water_ice_evidence": 0.75, "terrain_accessibility": 0.65, "scientific_interest": 0.95},
                },
                {
                    "name": "Arcadia Planitia",
                    "lat": 46.7,
                    "lon": -180.0,
                    "description": "Smooth plains. Subsurface water ice focus.",
                    "criteria": {"water_ice_evidence": 0.90, "terrain_accessibility": 0.85, "scientific_interest": 0.55},
                },
                {
                    "name": "Hellas Planitia",
                    "lat": -42.4,
                    "lon": 70.5,
                    "description": "Deep impact basin. High atmospheric pressure focus.",
                    "criteria": {"water_ice_evidence": 0.60, "terrain_accessibility": 0.35, "scientific_interest": 0.80},
                }
            ],
            "criteria_definitions": {
                "water_ice_evidence": "Accessible water ice evidence",
                "terrain_accessibility": "Ease of landing and traverse",
                "scientific_interest": "Scientific research interest"
            },
            "default_weights": {
                "water_ice_evidence": 0.40,
                "terrain_accessibility": 0.30,
                "scientific_interest": 0.30
            }
        }



def get_region_names() -> List[str]:
    """Return the list of available region names."""
    data = load_region_metadata()
    return [r["name"] for r in data["regions"]]


def get_criteria_definitions() -> Dict[str, str]:
    """Return the criteria names and their descriptions."""
    data = load_region_metadata()
    return data["criteria_definitions"]


def get_default_weights() -> Dict[str, float]:
    """Return the default criteria weights."""
    data = load_region_metadata()
    return data["default_weights"]


# ---------------------------------------------------------------------------
# Comparison Objective Presets
# ---------------------------------------------------------------------------
# Deterministic, hand-authored weight presets for the Compare tab's
# "objective" selector. Purely a UI convenience — the underlying scoring
# engine (score_region / compare_regions) is unchanged; presets just
# supply alternative starting weights for the same criteria. Every
# preset's weights sum to 1.0.
OBJECTIVE_WEIGHT_PRESETS = {
    "Balanced": {
        "water_ice_evidence": 0.25,
        "radiation_shielding": 0.15,
        "terrain_accessibility": 0.20,
        "scientific_interest": 0.15,
        "resource_availability": 0.15,
        "atmospheric_conditions": 0.10,
    },
    "Safety-first": {
        "water_ice_evidence": 0.10,
        "radiation_shielding": 0.25,
        "terrain_accessibility": 0.30,
        "scientific_interest": 0.05,
        "resource_availability": 0.10,
        "atmospheric_conditions": 0.20,
    },
    "Science-first": {
        "water_ice_evidence": 0.25,
        "radiation_shielding": 0.10,
        "terrain_accessibility": 0.10,
        "scientific_interest": 0.35,
        "resource_availability": 0.10,
        "atmospheric_conditions": 0.10,
    },
    "Resource-first": {
        "water_ice_evidence": 0.30,
        "radiation_shielding": 0.05,
        "terrain_accessibility": 0.15,
        "scientific_interest": 0.05,
        "resource_availability": 0.30,
        "atmospheric_conditions": 0.15,
    },
}


def get_objective_presets() -> Dict[str, Dict[str, float]]:
    """Return the available comparison-objective weight presets."""
    return OBJECTIVE_WEIGHT_PRESETS


CRITERIA_QUERIES = {
    "water_ice_evidence": "subsurface water ice, ice sheets, glacial deposits, clay minerals, hydration, liquid water stability",
    "radiation_shielding": "cosmic rays, solar particle events, radiation dose, regolith shielding, lava tubes, caves, atmospheric shielding",
    "terrain_accessibility": "slopes, rock density, landing safety, hazard avoidance, topography, flat terrain, traverse accessibility",
    "scientific_interest": "astrobiology, biosignatures, geological history, ancient lake bed, habitable environments, clay minerals, stratigraphy",
    "resource_availability": "in-situ resource utilization, ISRU, oxygen production, propellant, regolith building, water extraction, mineral resources",
    "atmospheric_conditions": "atmospheric pressure, density, temperature range, wind speeds, dust storms, atmospheric composition"
}


def score_region(
    region: dict,
    criteria_weights: Dict[str, float],
) -> RegionScore:
    """
    Score a single region dynamically against the vector store using criteria weights.

    Total score = sum(criterion_score × criterion_weight) for all criteria.

    Parameters
    ----------
    region : dict
        Region data from region_metadata.json (must have 'name' key).
    criteria_weights : dict
        Mapping of criterion name → weight (should sum to 1.0).

    Returns
    -------
    RegionScore
        The scoring result for this region.
    """
    from src.retrieval import retrieve
    from src.confidence import calc_retrieval_match_strength

    criteria_scores = {}
    weighted_scores = {}
    total = 0.0

    region_name = region["name"]

    for criterion, weight in criteria_weights.items():
        # Construct search query focused on the region and the criterion concepts
        query_str = f"{region_name} {CRITERIA_QUERIES.get(criterion, '')}"
        
        try:
            # Retrieve the top matching chunks for this region + criterion
            chunks = retrieve(query_str, top_k=3)
            
            # Calculate the score from the retrieval match strength (0.0 to 1.0)
            if chunks:
                raw_score = calc_retrieval_match_strength(chunks)
            else:
                raw_score = 0.0
        except Exception as e:
            print(f"Error evaluating {criterion} for {region_name}: {e}")
            raw_score = 0.0

        criteria_scores[criterion] = raw_score
        weighted = raw_score * weight
        weighted_scores[criterion] = weighted
        total += weighted

    return RegionScore(
        region_name=region_name,
        criteria_scores=criteria_scores,
        weighted_scores=weighted_scores,
        total_score=total,
    )


def compare_regions(
    criteria_weights: Optional[Dict[str, float]] = None,
    region_names: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Compare multiple candidate regions on adjustable weighted criteria.

    Scores are dynamically calculated in real-time from the vector database.

    Parameters
    ----------
    criteria_weights : dict, optional
        Mapping of criterion → weight. Defaults to the weights in region_metadata.json.
    region_names : list, optional
        Subset of regions to compare. Defaults to all available regions.

    Returns
    -------
    pd.DataFrame
        Comparison table with one row per region, columns for each criterion
        (raw and weighted), and a total score column. Sorted by total descending.
    """
    data = load_region_metadata()
    weights = criteria_weights or data["default_weights"]
    regions = data["regions"]

    # Filter to requested regions if specified
    if region_names:
        regions = [r for r in regions if r["name"] in region_names]

    # Score each region dynamically
    results = []
    for region in regions:
        region_score = score_region(region, weights)
        row = {"Region": region_score.region_name}

        # Add raw criterion scores
        for criterion in weights:
            row[f"{criterion}"] = region_score.criteria_scores.get(criterion, 0.0)

        # Add weighted scores
        for criterion in weights:
            row[f"{criterion}_weighted"] = region_score.weighted_scores.get(criterion, 0.0)

        row["Total Score"] = region_score.total_score
        results.append(row)

    df = pd.DataFrame(results)
    df = df.sort_values("Total Score", ascending=False).reset_index(drop=True)
    return df

