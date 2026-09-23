"""
AURA Mars — Illustrated, Clickable Solar System Scene

A literal, illustrated Sun/Earth/Mars/transfer-path diagram — click the
Sun, Earth, Mars, or the spacecraft to see real facts about each. Built
in plain HTML/CSS/JS (not Plotly), rendered as a self-contained
Streamlit component; all click interactivity is client-side.

Orbit radii are drawn in the real ratio (Mars' orbit is genuinely
1.524x Earth's in this scene, matching src/orbital_mechanics.py), and
the dashed transfer path is the real Hohmann transfer ellipse — not a
decorative arc. Only absolute sizes (how big the circles/orbits are on
screen) are illustrative. Earth and Mars are shown frozen at their real
launch-day positions (see the Journey to Mars animated simulation below
for the full time-evolving version) — the spacecraft glides along the
fixed transfer path for ambient motion instead.
"""

import json
import math
import random

import streamlit as st

from src.orbital_mechanics import (
    R_EARTH_AU,
    R_MARS_AU,
    A_TRANSFER_AU,
    E_TRANSFER,
    LAUNCH_PHASE_ANGLE_DEG,
    EARTH_PERIOD_DAYS,
    MARS_PERIOD_DAYS,
    TRANSFER_DAYS,
)

_EARTH_ORBIT_PCT = 26.0  # visual radius, percent of scene half-width
_MARS_ORBIT_PCT = _EARTH_ORBIT_PCT * (R_MARS_AU / R_EARTH_AU)


def _generate_stars(n: int, seed: int) -> str:
    rng = random.Random(seed)
    return "".join(
        f'<circle cx="{rng.randint(0, 100)}%" cy="{rng.randint(0, 100)}%" '
        f'r="{rng.choice([1, 1, 1, 2])}" fill="#fff" opacity="{rng.uniform(0.3, 0.9):.2f}"/>'
        for _ in range(n)
    )


def _orbit_point(radius_pct: float, angle_deg: float, cx: float = 50.0, cy: float = 50.0):
    rad = math.radians(angle_deg)
    return cx + radius_pct * math.cos(rad), cy - radius_pct * math.sin(rad)


def _transfer_path_points(n: int = 60):
    """Real Hohmann transfer ellipse points, mapped to the same visual scale as the orbits."""
    points = []
    for i in range(n + 1):
        nu = math.pi * i / n
        r_au = A_TRANSFER_AU * (1 - E_TRANSFER ** 2) / (1 + E_TRANSFER * math.cos(nu))
        r_pct = _EARTH_ORBIT_PCT * (r_au / R_EARTH_AU)
        angle_deg = math.degrees(nu)  # launch at angle 0
        points.append(_orbit_point(r_pct, angle_deg))
    return points


def render_solar_system_illustration(height: int = 620) -> None:
    """Render the illustrated, clickable Sun/Earth/Mars/transfer scene."""
    sun_pos = (50.0, 50.0)
    earth_pos = _orbit_point(_EARTH_ORBIT_PCT, 0.0)
    transfer_points = _transfer_path_points()
    craft_pos = transfer_points[len(transfer_points) // 2]  # midpoint of the transfer arc
    # Mars is shown at its ARRIVAL position (where the transfer path ends, 180°
    # from Earth's launch angle) rather than its launch-day position (44° ahead)
    # — this is a static scene, so showing Mars where the path visually leads
    # is correct; the "waiting there" concept from src.orbital_mechanics is
    # explained in the facts panel instead of depicted as two Mars positions.
    mars_pos = transfer_points[-1]

    bodies = {
        "sun": {
            "label": "The Sun",
            "facts": [
                "G-type star at the center of the Solar System",
                "Every orbit in this scene is real physics — Kepler's laws under the Sun's gravity",
            ],
        },
        "earth": {
            "label": "Earth",
            "facts": [
                f"{R_EARTH_AU:.2f} AU from the Sun (~150 million km)",
                f"Orbital period: {EARTH_PERIOD_DAYS:.1f} days",
                "Shown at the real launch-day position for this transfer",
            ],
        },
        "mars": {
            "label": "Mars",
            "facts": [
                f"{R_MARS_AU:.3f} AU from the Sun (~228 million km)",
                f"Orbital period: {MARS_PERIOD_DAYS:.0f} days (~{MARS_PERIOD_DAYS / 365.25:.2f} Earth years)",
                f"Shown at its real arrival-day position — at launch it's actually "
                f"~{LAUNCH_PHASE_ANGLE_DEG:.0f}° behind here, and moves into place during the transfer",
            ],
        },
        "craft": {
            "label": "Transfer spacecraft",
            "facts": [
                "Real Hohmann minimum-energy transfer orbit",
                f"Transfer time: ~{TRANSFER_DAYS:.0f} days (~{TRANSFER_DAYS / 30.44:.1f} months)",
                "Fastest near Earth, slowest near Mars — real orbital mechanics (Kepler's 2nd law)",
            ],
        },
    }

    orbit_path_d = f"M {transfer_points[0][0]:.2f} {transfer_points[0][1]:.2f} " + " ".join(
        f"L {x:.2f} {y:.2f}" for x, y in transfer_points[1:]
    )

    stars_svg = _generate_stars(110, seed=11)
    bodies_json = json.dumps(bodies)

    html = f"""
<!DOCTYPE html>
<html>
<head>
<style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Inter', -apple-system, sans-serif; overflow: hidden; }}
    .scene {{
        position: relative;
        width: 100%;
        height: {height - 130}px;
        border-radius: 14px;
        overflow: hidden;
        background: radial-gradient(ellipse at 50% 50%, #0d0f1a 0%, #05060a 75%);
        border: 1px solid #2B3748;
    }}
    .stars {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
    .orbit-svg {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
    .orbit-ring {{ fill: none; stroke: #2B3748; stroke-width: 0.15; }}
    .transfer-path {{
        fill: none; stroke: #62D49B; stroke-width: 0.35;
        stroke-dasharray: 1 1; opacity: 0.85;
    }}
    .body {{
        position: absolute;
        transform: translate(-50%, -50%);
        cursor: pointer;
        display: flex;
        flex-direction: column;
        align-items: center;
        z-index: 3;
    }}
    .body-dot {{
        border-radius: 50%;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }}
    .body:hover .body-dot, .body.active .body-dot {{ transform: scale(1.25); }}
    #dot-sun {{
        width: 34px; height: 34px;
        background: radial-gradient(circle at 35% 35%, #FFE9C4, #F5B942 60%, #D9683A 100%);
        box-shadow: 0 0 22px rgba(245,185,66,0.7);
        animation: aura-sun-pulse 3s ease-in-out infinite;
    }}
    @keyframes aura-sun-pulse {{
        0%, 100% {{ box-shadow: 0 0 18px rgba(245,185,66,0.6); }}
        50% {{ box-shadow: 0 0 28px rgba(245,185,66,0.9); }}
    }}
    #dot-earth {{
        width: 16px; height: 16px;
        background: radial-gradient(circle at 35% 35%, #8FD3F4, #3E8EDE 60%, #1d4e80 100%);
        box-shadow: 0 0 10px rgba(62,142,222,0.7);
    }}
    #dot-mars {{
        width: 12px; height: 12px;
        background: radial-gradient(circle at 35% 35%, #F0A578, #D9683A 60%, #8a3d1f 100%);
        box-shadow: 0 0 8px rgba(217,104,58,0.7);
    }}
    #dot-craft {{
        width: 10px; height: 10px;
        background: #E9EEF5;
        box-shadow: 0 0 8px #E9EEF5;
        animation: aura-craft-pulse 2s ease-in-out infinite;
    }}
    @keyframes aura-craft-pulse {{
        0%, 100% {{ opacity: 0.7; box-shadow: 0 0 6px #E9EEF5; }}
        50% {{ opacity: 1; box-shadow: 0 0 12px #E9EEF5; }}
    }}
    .body-label {{
        font-size: 10px;
        color: #E9EEF5;
        background: rgba(9,11,16,0.7);
        padding: 1px 6px;
        border-radius: 6px;
        margin-top: 3px;
        white-space: nowrap;
        pointer-events: none;
        opacity: 0.9;
    }}
    .detail-panel {{
        margin-top: 12px;
        background: #121722;
        border: 1px solid #2B3748;
        border-radius: 12px;
        padding: 14px 18px;
        min-height: 78px;
        color: #E9EEF5;
    }}
    .detail-title {{ font-weight: 700; font-size: 16px; margin-bottom: 6px; }}
    .detail-facts {{ font-size: 13px; color: #C9D2DE; line-height: 1.6; }}
    .detail-facts li {{ margin-left: 18px; }}
    .hint {{ font-size: 11px; color: #929CAA; text-align: center; margin-top: 6px; }}
</style>
</head>
<body>
    <div class="scene">
        <svg class="stars" viewBox="0 0 100 100" preserveAspectRatio="none">{stars_svg}</svg>
        <svg class="orbit-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
            <circle class="orbit-ring" cx="50" cy="50" r="{_EARTH_ORBIT_PCT}"/>
            <circle class="orbit-ring" cx="50" cy="50" r="{_MARS_ORBIT_PCT}"/>
            <path class="transfer-path" d="{orbit_path_d}"/>
        </svg>
        <div class="body" id="body-sun" style="left:{sun_pos[0]:.1f}%; top:{sun_pos[1]:.1f}%;" onclick="showBody('sun')">
            <div class="body-dot" id="dot-sun"></div>
            <div class="body-label">Sun</div>
        </div>
        <div class="body" id="body-earth" style="left:{earth_pos[0]:.1f}%; top:{earth_pos[1]:.1f}%;" onclick="showBody('earth')">
            <div class="body-dot" id="dot-earth"></div>
            <div class="body-label">Earth</div>
        </div>
        <div class="body" id="body-mars" style="left:{mars_pos[0]:.1f}%; top:{mars_pos[1]:.1f}%;" onclick="showBody('mars')">
            <div class="body-dot" id="dot-mars"></div>
            <div class="body-label">Mars</div>
        </div>
        <div class="body" id="body-craft" style="left:{craft_pos[0]:.1f}%; top:{craft_pos[1]:.1f}%;" onclick="showBody('craft')">
            <div class="body-dot" id="dot-craft"></div>
            <div class="body-label">Spacecraft</div>
        </div>
    </div>
    <div class="hint">Click the Sun, Earth, Mars, or the spacecraft for real facts</div>
    <div class="detail-panel" id="detail-panel">
        <div class="detail-title" id="detail-title">Earth</div>
        <ul class="detail-facts" id="detail-facts"></ul>
    </div>

<script>
const BODIES = {bodies_json};

function showBody(key) {{
    const b = BODIES[key];
    document.getElementById('detail-title').textContent = b.label;
    document.getElementById('detail-facts').innerHTML = b.facts.map(function(f) {{ return '<li>' + f + '</li>'; }}).join('');
    document.querySelectorAll('.body').forEach(function(el) {{ el.classList.remove('active'); }});
    document.getElementById('body-' + key).classList.add('active');
}}

showBody('earth');
</script>
</body>
</html>
    """

    st.iframe(html, height=height)
