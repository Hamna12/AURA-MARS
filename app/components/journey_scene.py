"""
AURA Mars — Earth-to-Mars Journey Scene

An animated, physically-grounded orbital diagram: Earth's orbit, Mars'
orbit, and a spacecraft flying a real Hohmann minimum-energy transfer
between them. Built for complete beginners — the goal is an honest,
intuitive answer to "what's actually between Earth and Mars, and how
long does it take to get there?"

Real physics used (not fabricated):
    - Earth and Mars orbital radii (1.0 AU / 1.524 AU) and periods
      (via Kepler's third law, T^2 = a^3 in AU/year units).
    - The Hohmann transfer ellipse: semi-major axis, eccentricity, and
      the ~259-day transfer time, all derived from the two orbital
      radii above — this matches the commonly cited real-world figure.
    - Motion along the transfer ellipse follows Kepler's equation
      (solved numerically), so the spacecraft correctly moves faster
      near Earth and slower near Mars (Kepler's 2nd law / equal areas),
      not a fake constant-speed animation.
    - The ~44° launch phase angle (how far ahead of Earth Mars must be
      at departure so it arrives exactly when the spacecraft does) is
      derived from the two periods, not looked up.

Simplifications, disclosed in the UI rather than hidden:
    - Earth's and Mars' own orbits are drawn as circles. Their real
      eccentricities are small (0.017 and 0.093) but non-zero.
    - Sun/Earth/Mars marker sizes are exaggerated for visibility — at
      true relative scale the planets would be invisible dots.
    - This is one specific transfer (minimum-energy Hohmann); real
      missions use a range of trajectories and the ~259-day figure
      varies somewhat by launch window.
"""

import numpy as np
import plotly.graph_objects as go

from src.orbital_mechanics import (  # noqa: F401 (re-exported for backward compatibility)
    AU_KM,
    R_EARTH_AU,
    R_MARS_AU,
    EARTH_PERIOD_DAYS,
    MARS_PERIOD_DAYS,
    A_TRANSFER_AU,
    E_TRANSFER,
    TRANSFER_DAYS,
    LAUNCH_PHASE_ANGLE_DEG,
    SYNODIC_PERIOD_DAYS,
    STRAIGHT_LINE_DISTANCE_MIN_KM,
    STRAIGHT_LINE_DISTANCE_MAX_KM,
    JourneyFacts,
    get_journey_facts,
)

_OMEGA_EARTH = 360.0 / EARTH_PERIOD_DAYS   # deg/day
_OMEGA_MARS = 360.0 / MARS_PERIOD_DAYS     # deg/day


# ---------------------------------------------------------------------------
# Kepler's equation (numerically solved — real non-uniform orbital motion)
# ---------------------------------------------------------------------------

def _solve_kepler(mean_anomaly: np.ndarray, eccentricity: float, iterations: int = 6) -> np.ndarray:
    """Solve M = E - e*sin(E) for E via Newton-Raphson."""
    E = mean_anomaly.copy()
    for _ in range(iterations):
        E = E - (E - eccentricity * np.sin(E) - mean_anomaly) / (1 - eccentricity * np.cos(E))
    return E


def _true_anomaly_and_radius(mean_anomaly: np.ndarray, a: float, e: float):
    """Given mean anomaly, return (true anomaly, radius) on an ellipse."""
    E = _solve_kepler(mean_anomaly, e)
    true_anom = 2 * np.arctan2(np.sqrt(1 + e) * np.sin(E / 2), np.sqrt(1 - e) * np.cos(E / 2))
    r = a * (1 - e * np.cos(E))
    return true_anom, r


# ---------------------------------------------------------------------------
# Scene construction
# ---------------------------------------------------------------------------

_N_FRAMES = 72
_SUN_COLOR = "#F5B942"
_EARTH_COLOR = "#3E8EDE"
_MARS_COLOR = "#D9683A"
_TRANSFER_COLOR = "#62D49B"
_ORBIT_LINE_COLOR = "#3A4457"


def _orbit_circle(radius_au: float, n_points: int = 200):
    theta = np.linspace(0, 2 * np.pi, n_points)
    return radius_au * np.cos(theta), radius_au * np.sin(theta)


def _sphere(radius: float, center=(0.0, 0.0, 0.0), n: int = 18):
    """Parametric sphere mesh for the Sun marker."""
    u = np.linspace(0, 2 * np.pi, n)
    v = np.linspace(0, np.pi, n)
    x = center[0] + radius * np.outer(np.cos(u), np.sin(v))
    y = center[1] + radius * np.outer(np.sin(u), np.sin(v))
    z = center[2] + radius * np.outer(np.ones_like(u), np.cos(v))
    return x, y, z


def create_journey_scene() -> go.Figure:
    """
    Build the animated Earth-to-Mars journey scene.

    Returns
    -------
    go.Figure
        A Plotly figure with static orbit/Sun traces plus per-frame
        animation of Earth, Mars, and the spacecraft along a real
        Kepler-accurate Hohmann transfer, with Play/Pause controls.
    """
    # Static geometry (computed once, not re-sent per frame)
    ex, ey = _orbit_circle(R_EARTH_AU)
    mx, my = _orbit_circle(R_MARS_AU)
    sun_x, sun_y, sun_z = _sphere(0.09)

    launch_angle = np.radians(0.0)
    mars_start_angle = np.radians(LAUNCH_PHASE_ANGLE_DEG)

    # Transfer ellipse path (for the static dashed trajectory line),
    # true anomaly sweeping 0 -> pi (perihelion at Earth -> aphelion at Mars)
    nu_path = np.linspace(0, np.pi, 200)
    r_path = A_TRANSFER_AU * (1 - E_TRANSFER ** 2) / (1 + E_TRANSFER * np.cos(nu_path))
    path_angle = nu_path + launch_angle
    tx, ty = r_path * np.cos(path_angle), r_path * np.sin(path_angle)

    # --- Static traces (indices 0-3) ---
    static_traces = [
        go.Scatter3d(
            x=ex, y=ey, z=np.zeros_like(ex), mode="lines",
            line=dict(color=_ORBIT_LINE_COLOR, width=3), name="Earth's orbit",
            hoverinfo="name",
        ),
        go.Scatter3d(
            x=mx, y=my, z=np.zeros_like(mx), mode="lines",
            line=dict(color=_ORBIT_LINE_COLOR, width=3), name="Mars' orbit",
            hoverinfo="name",
        ),
        go.Scatter3d(
            x=tx, y=ty, z=np.zeros_like(tx), mode="lines",
            line=dict(color=_TRANSFER_COLOR, width=3, dash="dot"),
            name="Transfer path (Hohmann orbit)", hoverinfo="name",
        ),
        go.Surface(
            x=sun_x, y=sun_y, z=sun_z,
            colorscale=[[0, _SUN_COLOR], [1, _SUN_COLOR]],
            showscale=False, hoverinfo="name", name="Sun",
            lighting=dict(ambient=0.9, diffuse=0.2),
        ),
    ]

    # --- Dynamic (animated) traces (indices 4-6): Earth, Mars, Spacecraft ---
    def _body_positions(t_days: float):
        earth_ang = launch_angle + np.radians(_OMEGA_EARTH * t_days)
        mars_ang = mars_start_angle + np.radians(_OMEGA_MARS * t_days)
        e_pos = (R_EARTH_AU * np.cos(earth_ang), R_EARTH_AU * np.sin(earth_ang))
        m_pos = (R_MARS_AU * np.cos(mars_ang), R_MARS_AU * np.sin(mars_ang))

        t_clamped = min(max(t_days, 0.0), TRANSFER_DAYS)
        mean_anom = np.array([np.pi * (t_clamped / TRANSFER_DAYS)])
        nu, r = _true_anomaly_and_radius(mean_anom, A_TRANSFER_AU, E_TRANSFER)
        s_ang = nu[0] + launch_angle
        s_pos = (r[0] * np.cos(s_ang), r[0] * np.sin(s_ang))
        return e_pos, m_pos, s_pos

    def _dynamic_traces(t_days: float):
        e_pos, m_pos, s_pos = _body_positions(t_days)
        return [
            go.Scatter3d(
                x=[e_pos[0]], y=[e_pos[1]], z=[0], mode="markers+text",
                marker=dict(size=9, color=_EARTH_COLOR), text=["Earth"],
                textposition="top center", textfont=dict(color="#E9EEF5", size=11),
                name="Earth", hoverinfo="name",
            ),
            go.Scatter3d(
                x=[m_pos[0]], y=[m_pos[1]], z=[0], mode="markers+text",
                marker=dict(size=7, color=_MARS_COLOR), text=["Mars"],
                textposition="top center", textfont=dict(color="#E9EEF5", size=11),
                name="Mars", hoverinfo="name",
            ),
            go.Scatter3d(
                x=[s_pos[0]], y=[s_pos[1]], z=[0], mode="markers",
                marker=dict(size=5, color="#E9EEF5", symbol="diamond"),
                name="Spacecraft", hoverinfo="name",
            ),
        ]

    initial = _dynamic_traces(0.0)
    fig = go.Figure(data=static_traces + initial)

    frames = []
    for i in range(_N_FRAMES + 1):
        t_days = TRANSFER_DAYS * (i / _N_FRAMES)
        day_label = f"Day {t_days:.0f} of ~{TRANSFER_DAYS:.0f}"
        frames.append(go.Frame(
            data=_dynamic_traces(t_days),
            traces=[4, 5, 6],
            name=str(i),
            layout=go.Layout(annotations=[dict(
                text=day_label, x=0.02, y=0.98, xref="paper", yref="paper",
                showarrow=False, font=dict(color="#E9EEF5", size=13),
                bgcolor="rgba(18,23,34,0.75)", bordercolor="#2B3748", borderpad=6,
            )]),
        ))
    fig.frames = frames

    axis_range = [-(R_MARS_AU * 1.15), R_MARS_AU * 1.15]
    fig.update_layout(
        scene=dict(
            xaxis=dict(visible=False, range=axis_range),
            yaxis=dict(visible=False, range=axis_range),
            zaxis=dict(visible=False, range=[-0.3, 0.3]),
            bgcolor="#090B10",
            camera=dict(eye=dict(x=0, y=0, z=2.1), up=dict(x=0, y=1, z=0)),
            aspectmode="cube",
        ),
        paper_bgcolor="#090B10",
        margin=dict(l=0, r=0, t=10, b=0),
        height=650,
        showlegend=True,
        legend=dict(
            font=dict(color="#E9EEF5", size=11),
            bgcolor="rgba(18, 23, 34, 0.75)",
            bordercolor="#2B3748", borderwidth=1,
            x=0.01, y=0.01,
        ),
        annotations=[dict(
            text="Day 0 of ~259", x=0.02, y=0.98, xref="paper", yref="paper",
            showarrow=False, font=dict(color="#E9EEF5", size=13),
            bgcolor="rgba(18,23,34,0.75)", bordercolor="#2B3748", borderpad=6,
        )],
        updatemenus=[dict(
            type="buttons",
            direction="left",
            x=0.01, y=0.08, xanchor="left", yanchor="bottom",
            bgcolor="#1A2230",
            font=dict(color="#E9EEF5"),
            buttons=[
                dict(
                    label="▶ Play the journey",
                    method="animate",
                    args=[None, dict(
                        frame=dict(duration=60, redraw=True),
                        fromcurrent=True, transition=dict(duration=0),
                    )],
                ),
                dict(
                    label="⏸ Pause",
                    method="animate",
                    args=[[None], dict(
                        frame=dict(duration=0, redraw=False),
                        mode="immediate", transition=dict(duration=0),
                    )],
                ),
                dict(
                    label="⟲ Restart",
                    method="animate",
                    args=[["0"], dict(
                        frame=dict(duration=0, redraw=True),
                        mode="immediate", transition=dict(duration=0),
                    )],
                ),
            ],
        )],
    )

    return fig
