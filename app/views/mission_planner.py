"""
AURA Mars — Mission Planner Tab

Four grounded mission-planning tools: EDL sequence, communication delay,
launch windows, and a rocket-equation / life-support estimator. All
underlying data and math live in src/mission_planner.py — this module is
presentation only. Kept deliberately light on text — details live in
tooltips (hover) and one collapsed stage-timeline expander, not inline
prose.
"""

import streamlit as st

from app.components.edl_illustration import render_edl_illustration
from src.mission_planner import (
    EDL_STAGES,
    EDL_SOURCE_MISSION,
    get_comm_delay_range,
    get_launch_windows,
    propellant_mass_fraction,
    propellant_mass_kg,
    estimate_consumables,
    REFERENCE_TMI_DELTA_V_MS,
    REFERENCE_CHEMICAL_ISP_S,
)


def render_mission_planner_tab():
    """Render the Mission Planner tab contents."""
    st.header("Mars Mission Planner")
    st.caption("Landing, comms, launch timing, and fuel/life-support — all real physics.")

    st.divider()

    # =======================================================================
    # 1. Entry, Descent & Landing
    # =======================================================================
    st.subheader("Entry, Descent & Landing")
    st.caption(f"Real flight data · {EDL_SOURCE_MISSION}")

    render_edl_illustration()

    with st.expander("Full stage-by-stage timeline"):
        for stage in EDL_STAGES:
            measurements = []
            if stage.altitude_km is not None:
                measurements.append(f"alt {stage.altitude_km:.3g} km")
            if stage.velocity_ms is not None:
                measurements.append(f"{stage.velocity_ms:.0f} m/s")
            line = f"**{stage.name}** — {stage.time_label}"
            if measurements:
                line += f" — {', '.join(measurements)}"
            st.markdown(f"- {line}")
            if stage.note:
                st.caption(f"　{stage.note}")

    st.divider()

    # =======================================================================
    # 2. Communication Delay
    # =======================================================================
    st.subheader("Communication Delay")
    comm = get_comm_delay_range()
    delay_cols = st.columns(3)
    delay_cols[0].metric("Closest approach", f"{comm.min_distance_km / 1e6:.0f}M km")
    delay_cols[1].metric("Farthest apart", f"{comm.max_distance_km / 1e6:.0f}M km")
    delay_cols[2].metric(
        "One-way delay", f"{comm.min_delay_min:.1f}–{comm.max_delay_min:.1f} min",
        help="Real light-time physics: delay = distance ÷ speed of light. This is why every "
             "Mars landing is fully autonomous — nobody on Earth can react in time.",
    )

    st.divider()

    # =======================================================================
    # 3. Launch Windows
    # =======================================================================
    st.subheader("Launch Windows")
    windows = get_launch_windows(n_before=2, n_after=3)
    win_cols = st.columns(len(windows))
    for col, w in zip(win_cols, windows):
        with col:
            tag = "✓ past" if w.is_past else "upcoming"
            st.markdown(f"**{w.label}**")
            st.caption(tag)
    st.caption(
        "Every ~26 months, from Perseverance's real 2020 launch.",
        help="Projected using the real synodic period (how often Earth and Mars line up for "
             "an efficient transfer) from Perseverance's actual 2020-07-30 launch date — not "
             "announced mission dates. Real launches happen within a window around these dates.",
    )

    st.divider()

    # =======================================================================
    # 4. Fuel / Crew / Habitat Resource Estimator
    # =======================================================================
    st.subheader("Fuel & Life Support Estimator")
    st.caption(
        "Illustrative reference vehicle",
        help="The physics (rocket equation, consumables rates) is real, but these aren't a "
             "specific real mission's numbers. Adjust the sliders to explore the trade-offs.",
    )

    est_cols = st.columns(2)

    with est_cols[0]:
        st.markdown("**Propellant**")
        payload_kg = st.slider("Payload / dry mass (kg)", 1_000, 50_000, 10_000, step=1_000)
        isp_s = st.slider("Engine Isp (s)", 250, 450, REFERENCE_CHEMICAL_ISP_S, step=10,
                           help="Specific impulse — engine efficiency. Typical chemical propulsion range.")
        delta_v = st.slider("Δv budget (m/s)", 2_000, 5_000, REFERENCE_TMI_DELTA_V_MS, step=100,
                             help="Trans-Mars Injection from low Earth orbit typically needs ~3.5-3.9 km/s.")

        prop_kg = propellant_mass_kg(payload_kg, delta_v, isp_s)
        prop_fraction = propellant_mass_fraction(delta_v, isp_s)

        st.metric("Propellant required", f"{prop_kg:,.0f} kg")
        st.metric("Mass fraction", f"{prop_fraction * 100:.1f}%",
                   help="Share of total launch mass that must be propellant, not payload.")

    with est_cols[1]:
        st.markdown("**Life support**")
        crew_size = st.slider("Crew size", 1, 8, 4)
        duration_days = st.slider("Duration (days)", 30, 900, 180, step=10,
                                   help="A one-way transit is ~259 days.")

        cons = estimate_consumables(crew_size, duration_days)
        recycling_savings = (1 - cons.total_kg_with_recycling / cons.total_kg_no_recycling) * 100

        st.metric("Consumables — no recycling", f"{cons.total_kg_no_recycling / 1000:,.1f} t",
                   help=f"{cons.oxygen_kg:,.0f} kg oxygen + {cons.food_kg:,.0f} kg food + "
                        f"{cons.water_kg_no_recycling:,.0f} kg water")
        st.metric("Consumables — 98% water recycling", f"{cons.total_kg_with_recycling / 1000:,.1f} t",
                   delta=f"-{recycling_savings:.0f}%", delta_color="inverse",
                   help="98% is NASA's real 2023 ISS water recovery milestone. Lower is better here.")
