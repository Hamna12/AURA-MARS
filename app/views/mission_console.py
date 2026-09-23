"""
AURA Mars — Mission Console Tab

An illustrative concept view that shows what a future mission-planning
layer could look like on top of the existing evidence-grounded RAG
pipeline. The route recommendation and 3D scene are illustrative only —
they are NOT derived from real terrain data or a validated mission
planner, and the page says so explicitly.
"""

import streamlit as st

from app.components.mission_scene import render_mission_scene, ILLUSTRATIVE_DISCLAIMER
from src.utils import format_confidence_display


def render_mission_console_tab():
    """Render the Mission Console tab contents."""
    st.header("Mission Console")
    st.caption(
        "Illustrative mission-planning concept — not a validated planner.",
        help="A concept view of how evidence-grounded research could feed a future "
             "mission-planning layer. Route logic and terrain shown here are illustrative.",
    )

    st.divider()

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown('<div class="aura-section-label">Mission objective</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="aura-card aura-card-accent">'
            'Reach a scientifically interesting outcrop identified from retrieved literature.'
            '</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="aura-section-label">Recommended route (illustrative)</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="aura-card aura-card-accent">'
            '<strong>Route B</strong>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Longer, lower-risk, avoids marked hazards.",
            help="A conceptual stand-in for how terrain/hazard evidence might one day inform "
                 "route choice — not a scientifically validated route for an actual mission.",
        )

    with col_right:
        result = st.session_state.get("last_result")

        st.markdown('<div class="aura-section-label">Evidence strength (last query)</div>', unsafe_allow_html=True)
        if result is not None:
            conf = result.confidence
            st.markdown(
                f'<div class="aura-card aura-card-accent">'
                f'<strong>{format_confidence_display(conf.final_confidence)}</strong> '
                f'&nbsp;·&nbsp; Confidence level: <strong>{conf.label}</strong>'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.caption(
                "From the most recent Ask-tab query.",
                help="Not the route recommendation itself — the route logic below is illustrative only.",
            )
        else:
            st.info("Run a query in the **Ask** tab to see evidence strength here.")

        st.markdown('<div class="aura-section-label">Main uncertainty</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="aura-card aura-card-accent">'
            'No real subsurface/terrain hazard data — scene markers are placeholders.'
            '</div>',
            unsafe_allow_html=True,
        )

    st.divider()

    st.subheader("Illustrative Terrain Scene")
    render_mission_scene()

    st.divider()

    st.caption(
        "Future: physical/simulated rover validation (ESP32, Webots) — not implemented.",
        help="This mission concept may later be connected to a physical or simulated rover "
             "platform for grounded traverse testing. Not implemented in this build.",
    )
    st.caption(ILLUSTRATIVE_DISCLAIMER)
