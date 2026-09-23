"""
AURA Mars — Journey to Mars Tab (hero module)

A beginner-friendly answer to "what's actually between Earth and Mars,
and how do we get there?" The primary visual is a Three.js 3D scene
(app/components/journey_3d.py) — Sun, Earth, Mars, orbital paths, and a
spacecraft animating along the real transfer trajectory, with live
telemetry. Every position it draws is precomputed in Python by the
same Kepler-equation solver as the original Plotly simulation, not
re-derived in JavaScript (see journey_3d.py's module docstring).

The original animated, Kepler-accurate Plotly simulation
(app/components/journey_scene.py) and the clickable "click a body for
facts" illustration (app/components/solar_system_illustration.py) are
each independently validated, real, and still useful in their own way
— kept as opt-in deeper dives rather than deleted.
"""

import streamlit as st

from app.components.journey_scene import create_journey_scene, get_journey_facts
from app.components.journey_3d import render_journey_3d
from app.components.solar_system_illustration import render_solar_system_illustration


def render_journey_tab():
    """Render the Journey to Mars tab contents."""
    st.header("Journey to Mars")
    st.caption("A live 3D transfer simulation, built on the real Hohmann-transfer physics below.")

    render_journey_3d()

    st.divider()

    with st.expander("Click a body for facts (2D illustrated view)"):
        st.caption("Click the Sun, Earth, Mars, or the spacecraft below for real facts about each.")
        render_solar_system_illustration()

    st.divider()

    # --- What you're seeing, in plain language ---
    st.subheader("What's actually happening")
    step_cols = st.columns(3)
    with step_cols[0]:
        st.markdown("**1. Leaving Earth**")
        st.caption("Already moving at Earth's own orbital speed — ~107,000 km/h.")
    with step_cols[1]:
        st.markdown("**2. Crossing the gap**")
        st.caption("No other planets in between — just empty space for months.")
    with step_cols[2]:
        st.markdown("**3. Arriving at Mars**")
        st.caption("Aimed at where Mars *will be*, not where it is today.")

    st.divider()

    # --- Real numbers behind the animation ---
    st.subheader("The Real Numbers")
    facts = get_journey_facts()

    num_cols = st.columns(4)
    num_cols[0].metric("Transfer time", f"~{facts.transfer_days:.0f} days", help=f"~{facts.transfer_months:.1f} months, one-way")
    num_cols[1].metric("Distance traveled", f"{facts.distance_closest_km / 1e6:.0f}–{facts.distance_farthest_km / 1e6:.0f}M km", help="Earth-Mars straight-line distance varies with orbital position")
    num_cols[2].metric("Mars year", f"{facts.mars_period_years:.2f} Earth years", help=f"~{facts.mars_period_days:.0f} Earth days per Mars year")
    num_cols[3].metric("Next launch window", f"every ~{facts.synodic_period_months:.0f} months",
                        help=f"Mars must be ~{facts.launch_phase_angle_deg:.0f}° ahead of Earth at launch to be "
                             "waiting at the meeting point when the spacecraft arrives.")

    with st.expander("Watch a real-time animated simulation"):
        st.caption("Same real physics, fully animated — spacecraft and planets move in real time.")
        fig = create_journey_scene()
        st.plotly_chart(fig, width="stretch", key="journey_scene_chart")
        st.caption("▶ Press play below the chart · drag to rotate · scroll to zoom")

    with st.expander("How is this calculated? (for the curious)"):
        st.markdown(
            "- **Orbital radii**: Earth 1.0 AU, Mars 1.524 AU from the Sun (1 AU ≈ 150 million km).\n"
            "- **Orbital periods**: from Kepler's third law, T² = a³ (in AU/year units) — this alone "
            "gives Mars' real ~687-day year without needing to look it up.\n"
            "- **Transfer orbit**: an ellipse with the Sun at one focus, touching Earth's orbit at "
            "its near point and Mars' orbit at its far point. Its semi-major axis and eccentricity "
            "follow directly from the two orbital radii.\n"
            "- **Transfer time**: half the transfer ellipse's own orbital period (Kepler's third "
            "law again) — landing on the well-known real-world figure of ~259 days.\n"
            "- **Spacecraft motion in the animation**: solved from Kepler's equation, so it "
            "genuinely moves faster near Earth and slower near Mars — real orbital mechanics "
            "(Kepler's second law), not a smoothed animation.\n\n"
            "**Simplified for clarity**: Earth's and Mars' own orbits are drawn as perfect circles. "
            "Their real orbits are ellipses too, but nearly circular (eccentricity 0.017 and 0.093 "
            "respectively) — close enough that the difference wouldn't be visible here. This is one "
            "specific minimum-energy trajectory; real missions choose from a range of possible paths."
        )

    st.divider()
    st.caption("Curious about the Mars surface itself? Head to the **Ask** tab →")
