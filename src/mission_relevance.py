"""
AURA Mars — Mission Relevance Classification

Deterministic, explainable keyword-based classifier that tags a piece of
text (typically a user question, sometimes combined with the generated
answer) with the Mars mission area(s) it relates to.

This is intentionally simple: no LLM call, no ML model. Keyword matching
only, so the result is fully reproducible and easy to explain to a
reviewer or in a presentation.
"""

from typing import List


# ---------------------------------------------------------------------------
# Keyword categories
# ---------------------------------------------------------------------------
MISSION_AREA_KEYWORDS = {
    "Landing": [
        "landing", "elevation", "slope", "rock abundance", "surface safety",
        "atmosphere", "entry, descent", "edl", "touchdown", "landing site",
        "landing ellipse",
    ],
    "Roving": [
        "rover", "traversability", "mobility", "terrain", "route", "roughness",
        "hazard", "traverse", "wheel", "drive distance",
    ],
    "Habitats": [
        "habitat", "radiation", "water ice", "temperature", "shielding",
        "isru", "life support", "regolith construction", "pressurized",
        "long-duration",
    ],
    "Robotics": [
        "autonomy", "navigation", "path planning", "obstacle avoidance",
        "sensor", "autonomous", "robotic arm", "manipulation", "slam",
    ],
    "Science": [
        "clay", "minerals", "sediment", "biosignature", "ancient water",
        "geology", "astrobiology", "stratigraphy", "mineralogy",
        "habitability", "organic",
    ],
}

FALLBACK_AREA = "General Mars Research"


def identify_mission_areas(text: str) -> List[str]:
    """
    Identify which Mars mission areas a piece of text relates to.

    Uses simple case-insensitive substring keyword matching against a
    fixed set of categories (Landing, Roving, Habitats, Robotics, Science).
    Deterministic and explainable — no LLM involvement.

    Parameters
    ----------
    text : str
        The text to classify (typically the user's question).

    Returns
    -------
    List[str]
        Matching mission area names, in a fixed priority order. Returns
        ["General Mars Research"] if no keywords match or input is empty.
    """
    if not text or not text.strip():
        return [FALLBACK_AREA]

    lowered = text.lower()
    matched = []
    for area, keywords in MISSION_AREA_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            matched.append(area)

    return matched if matched else [FALLBACK_AREA]
