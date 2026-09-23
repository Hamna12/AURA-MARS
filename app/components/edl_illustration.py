"""
AURA Mars — Illustrated, Clickable EDL Scene

Replaces the abstract log-scale altitude chart with an actual
illustration: a spacecraft descending from black sky through Mars'
orange atmosphere to the surface, with each real EDL stage as a
clickable marker that reveals its info. Built in plain HTML/CSS/JS
(not Plotly) and rendered as a self-contained Streamlit component —
all interactivity is client-side in the embedded iframe; the stage
data (from src/mission_planner.py) is baked in as JSON, so clicking
needs no round-trip to the Python backend.
"""

import json
import math
import random

import streamlit as st

from src.mission_planner import EDL_STAGES, EDL_SOURCE_MISSION

_PHASE_COLORS = {
    "entry": "#D9683A",
    "descent": "#E8AD56",
    "landing": "#62D49B",
}

_STAGE_PHASE = {
    "Cruise Stage Separation": "entry",
    "Entry Interface": "entry",
    "Peak Heating": "entry",
    "Peak Deceleration": "entry",
    "Parachute Deploy": "descent",
    "Heat Shield Separation": "descent",
    "Radar-Guided Terrain Navigation": "descent",
    "Backshell Separation / Powered Descent": "landing",
    "Sky Crane Maneuver / Rover Separation": "landing",
    "Mobility Deploy": "landing",
    "Touchdown": "landing",
    "Flyaway": "landing",
}


def _generate_stars(n: int, seed: int) -> str:
    rng = random.Random(seed)
    dots = []
    for _ in range(n):
        x, y = rng.randint(0, 100), rng.randint(0, 100)
        size = rng.choice([1, 1, 1, 2])
        opacity = rng.uniform(0.3, 0.9)
        dots.append(f'<circle cx="{x}%" cy="{y}%" r="{size}" fill="#fff" opacity="{opacity:.2f}"/>')
    return "".join(dots)


_Y_TOP_PCT, _Y_BOTTOM_PCT = 6.0, 96.0


def _build_positions(stages):
    """
    Compute (x_pct, y_pct) for each stage: y is *equally* spaced by
    stage order (guaranteed readable, no overlap, always in bounds) —
    later stages sit visually lower/closer to the ground. x is a gentle
    S-curve for visual interest. Neither axis is a literal data scale;
    real per-stage timing/altitude/velocity is shown in the click-to-
    reveal detail panel and the "Full stage-by-stage timeline" expander,
    not implied by position on this illustration.
    """
    n = len(stages)
    positions = []
    for i in range(n):
        t = i / (n - 1) if n > 1 else 0.0
        y_pct = _Y_TOP_PCT + (_Y_BOTTOM_PCT - _Y_TOP_PCT) * t
        x_pct = 22 + 56 * (0.5 - 0.5 * math.cos(t * math.pi))
        positions.append((x_pct, y_pct))
    return positions


def render_edl_illustration(height: int = 640) -> None:
    """Render the illustrated, clickable EDL descent scene."""
    # Cruise Stage Separation happens 10 minutes before atmospheric entry —
    # a very different phase (coasting in vacuum) from the ~7-minute
    # entry-to-landing sequence the scene actually depicts. It gets a
    # short caption above the scene instead of a spot on the curve.
    pre_entry_stages = [s for s in EDL_STAGES if s.time_s < 0]
    entry_stages = [s for s in EDL_STAGES if s.time_s >= 0]

    positions = _build_positions(entry_stages)

    stages_json = json.dumps([
        {
            "name": s.name,
            "time": s.time_label,
            "altitude": f"{s.altitude_km:.3g} km" if s.altitude_km is not None else None,
            "velocity": f"{s.velocity_ms:.0f} m/s" if s.velocity_ms is not None else None,
            "note": s.note,
            "phase": _STAGE_PHASE.get(s.name, "descent"),
        }
        for s in entry_stages
    ])

    markers_html = []
    path_points = []
    for i, (s, (x, y)) in enumerate(zip(entry_stages, positions)):
        color = _PHASE_COLORS[_STAGE_PHASE.get(s.name, "descent")]
        path_points.append((x, y))
        markers_html.append(
            f'<div class="stage-marker" style="left:{x:.1f}%; top:{y:.1f}%; '
            f'--marker-color:{color};" onclick="showStage({i})" id="marker-{i}">'
            f'<div class="marker-dot"></div>'
            f'<div class="marker-label">{s.name.split(" / ")[0].split(" (")[0]}</div>'
            f'</div>'
        )

    # Smooth-ish path: quadratic curve through consecutive midpoints
    path_d = f"M {path_points[0][0]:.1f} {path_points[0][1]:.1f} "
    for i in range(1, len(path_points)):
        x0, y0 = path_points[i - 1]
        x1, y1 = path_points[i]
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        path_d += f"Q {x0:.1f} {y0:.1f} {mx:.1f} {my:.1f} "
    path_d += f"T {path_points[-1][0]:.1f} {path_points[-1][1]:.1f}"

    stars_svg = _generate_stars(90, seed=7)

    pre_entry_html = " · ".join(
        f"{s.time_label}: {s.name} — {s.note}" for s in pre_entry_stages
    )

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
        height: {height - 140}px;
        border-radius: 14px;
        overflow: hidden;
        background: linear-gradient(to bottom,
            #05060a 0%, #0a0d16 25%, #150f14 55%, #3a1f14 78%, #7a3a20 92%, #a8532a 100%);
        border: 1px solid #2B3748;
    }}
    .stars {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
    .path-svg {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
    .path-svg path {{
        fill: none;
        stroke: #55B8D9;
        stroke-width: 0.4;
        stroke-dasharray: 1.5 1.2;
        opacity: 0.75;
    }}
    .stage-marker {{
        position: absolute;
        transform: translate(-50%, -50%);
        cursor: pointer;
        display: flex;
        flex-direction: column;
        align-items: center;
        z-index: 2;
    }}
    .marker-dot {{
        width: 14px; height: 14px;
        border-radius: 50%;
        background: var(--marker-color);
        box-shadow: 0 0 8px var(--marker-color);
        border: 2px solid rgba(255,255,255,0.85);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
        animation: aura-edl-pulse 2.4s ease-in-out infinite;
    }}
    .stage-marker:hover .marker-dot, .stage-marker.active .marker-dot {{
        transform: scale(1.4);
        box-shadow: 0 0 16px var(--marker-color);
    }}
    @keyframes aura-edl-pulse {{
        0%, 100% {{ opacity: 0.85; }}
        50% {{ opacity: 1; }}
    }}
    .marker-label {{
        font-size: 10px;
        color: #E9EEF5;
        background: rgba(9,11,16,0.7);
        padding: 1px 6px;
        border-radius: 6px;
        margin-top: 3px;
        white-space: nowrap;
        pointer-events: none;
        opacity: 0.85;
    }}
    .rover-icon {{
        position: absolute;
        width: 14px;
        height: 14px;
        border-radius: 50%;
        background: #E9EEF5;
        border: 2px solid #4DD8E8;
        box-shadow: 0 0 10px rgba(77, 216, 232, 0.8);
        transform: translate(-50%, -50%);
        z-index: 3;
        transition: left 0.3s ease, top 0.3s ease;
    }}
    .detail-panel {{
        margin-top: 12px;
        background: #121722;
        border: 1px solid #2B3748;
        border-radius: 12px;
        padding: 14px 18px;
        min-height: 88px;
        color: #E9EEF5;
    }}
    .detail-title {{
        font-weight: 700;
        font-size: 16px;
        margin-bottom: 4px;
    }}
    .detail-meta {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        color: #929CAA;
        margin-bottom: 6px;
    }}
    .detail-meta span {{
        margin-right: 14px;
    }}
    .detail-note {{
        font-size: 13px;
        color: #C9D2DE;
        line-height: 1.4;
    }}
    .hint {{
        font-size: 11px;
        color: #929CAA;
        text-align: center;
        margin-top: 6px;
    }}
    .pre-entry-note {{
        font-size: 11px;
        color: #929CAA;
        text-align: center;
        margin-bottom: 8px;
    }}
</style>
</head>
<body>
    <div class="pre-entry-note">{pre_entry_html}</div>
    <div class="scene">
        <svg class="stars" viewBox="0 0 100 100" preserveAspectRatio="none">{stars_svg}</svg>
        <svg class="path-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
            <path d="{path_d}"/>
        </svg>
        <div class="rover-icon" id="rover-icon" style="left:{positions[0][0]:.1f}%; top:{positions[0][1]:.1f}%;"></div>
        {"".join(markers_html)}
    </div>
    <div class="hint">Click any marker to see that stage's details</div>
    <div class="detail-panel" id="detail-panel">
        <div class="detail-title" id="detail-title">Entry Interface</div>
        <div class="detail-meta" id="detail-meta"></div>
        <div class="detail-note" id="detail-note"></div>
    </div>

<script>
const STAGES = {stages_json};
const POSITIONS = {json.dumps(positions)};

function showStage(i) {{
    const s = STAGES[i];
    document.getElementById('detail-title').textContent = s.name;
    document.getElementById('detail-title').style.color = s.phase === 'entry' ? '#D9683A' : (s.phase === 'descent' ? '#E8AD56' : '#62D49B');

    let meta = '<span>T+ ' + s.time + '</span>';
    if (s.altitude) meta += '<span>ALT ' + s.altitude + '</span>';
    if (s.velocity) meta += '<span>VEL ' + s.velocity + '</span>';
    document.getElementById('detail-meta').innerHTML = meta;
    document.getElementById('detail-note').textContent = s.note || '';

    document.querySelectorAll('.stage-marker').forEach(function(el) {{ el.classList.remove('active'); }});
    document.getElementById('marker-' + i).classList.add('active');

    const pos = POSITIONS[i];
    const rover = document.getElementById('rover-icon');
    rover.style.left = pos[0] + '%';
    rover.style.top = pos[1] + '%';
}}

showStage(0); // default to Entry Interface
</script>
</body>
</html>
    """

    st.iframe(html, height=height)
