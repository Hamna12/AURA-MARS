"""
AURA Mars — Compare Tab

Weighted scoring table across candidate Mars regions with adjustable sliders.
All comparison logic is Pandas-driven, NOT LLM-driven.
"""

import streamlit as st
import plotly.express as px

from src.comparison import (
    load_region_metadata,
    get_region_names,
    get_criteria_definitions,
    get_default_weights,
    get_objective_presets,
    compare_regions,
)

DISCLAIMER = (
    "This is a literature-based exploratory comparison, not an actual mission recommendation."
)


def render_compare_tab():
    """Render the Compare tab contents."""
    st.header("Region Comparison")
    st.caption(f"Deterministic, weighted scoring — not AI-influenced. {DISCLAIMER}")

    # Load metadata
    try:
        criteria_defs = get_criteria_definitions()
        default_weights = get_default_weights()
        region_names = get_region_names()
        objective_presets = get_objective_presets()
    except Exception as e:
        st.error(f"Failed to load region metadata: {e}")
        return

    st.divider()

    # --- Explanation of criteria ---
    with st.expander("What each criterion means"):
        for criterion, description in criteria_defs.items():
            st.markdown(f"**{criterion.replace('_', ' ').title()}** — {description}")

    st.divider()

    # --- Comparison objective selector ---
    st.subheader("Comparison Objective")
    objective_options = ["Balanced", "Safety-first", "Science-first", "Resource-first"]
    objective = st.radio(
        "Objective",
        objective_options,
        index=0,
        horizontal=True,
        key="compare_objective",
        label_visibility="collapsed",
        help="Starting weight presets — fixed tables, not AI-generated. Fine-tune with the sliders below.",
    )
    preset_weights = objective_presets.get(objective, default_weights)

    # --- Weight Sliders ---
    st.subheader("Criteria Weights")

    weights = {}
    cols = st.columns(len(criteria_defs))
    for i, (criterion, description) in enumerate(criteria_defs.items()):
        with cols[i]:
            label = criterion.replace("_", " ").title()
            default = preset_weights.get(criterion, default_weights.get(criterion, 0.15))
            weights[criterion] = st.slider(
                label,
                min_value=0.0,
                max_value=1.0,
                value=default,
                step=0.05,
                help=description,
                key=f"weight_{criterion}_{objective}",
            )

    # Normalise weights to sum to 1.0
    total_weight = sum(weights.values())
    if total_weight > 0:
        normalised_weights = {k: v / total_weight for k, v in weights.items()}
    else:
        normalised_weights = {k: 1.0 / len(weights) for k in weights}

    st.caption(f"Normalised weights sum: {sum(normalised_weights.values()):.2f}")

    st.divider()

    # --- Recalculate Button ---
    st.subheader("Database Retrieval")
    recalculate = st.button(
        "Evaluate Regions from Ingested Resources", type="primary", key="btn_recalc_compare",
        help="Runs 18 vector searches (3 regions × 6 criteria) against your ingested documents.",
    )

    if recalculate or "comparison_raw_df" not in st.session_state:
        if recalculate:
            with st.spinner("Analyzing document resources..."):
                # Query the comparison engine using uniform weight to retrieve baseline scores for each criterion
                uniform_weights = {k: 1.0 for k in criteria_defs}
                try:
                    raw_df = compare_regions(criteria_weights=uniform_weights)
                    st.session_state["comparison_raw_df"] = raw_df
                except Exception as e:
                    st.error(f"Failed to query database for region evaluation: {e}")
                    return
        else:
            st.info("Click 'Evaluate Regions from Ingested Resources' above to analyze your vector database.")
            return

    # Load baseline scores from session state cache
    raw_df = st.session_state["comparison_raw_df"]

    if raw_df.empty:
        st.warning("No regions found to evaluate.")
        return

    # Calculate weighted scores and Total Score in memory based on the current sliders (Instant)
    df = raw_df.copy()
    total_scores = []
    for idx, row in df.iterrows():
        total = 0.0
        for criterion, weight in normalised_weights.items():
            raw_val = row.get(criterion, 0.0)
            weighted_val = raw_val * weight
            df.at[idx, f"{criterion}_weighted"] = weighted_val
            total += weighted_val
        total_scores.append(total)
    df["Total Score"] = total_scores

    # Re-sort based on newly computed total scores
    df = df.sort_values("Total Score", ascending=False).reset_index(drop=True)

    st.divider()

    # --- Comparison Table ---
    st.subheader("Comparison Results")

    # Display the table (raw scores only, not weighted columns)
    display_cols = ["Region"] + list(criteria_defs.keys()) + ["Total Score"]
    display_df = df[[c for c in display_cols if c in df.columns]].copy()

    # Format column names for display
    display_df.columns = [
        c.replace("_", " ").title() if c != "Region" else c
        for c in display_df.columns
    ]

    st.dataframe(
        display_df.style.format({col: "{:.2f}" for col in display_df.columns if col != "Region"}),
        width="stretch",
        hide_index=True,
    )

    # --- Bar Chart ---
    st.subheader("Total Score Comparison")
    fig = px.bar(
        df,
        x="Region",
        y="Total Score",
        color="Region",
        title="Weighted Region Scores",
        text="Total Score",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_traces(texttemplate="%{text:.3f}", textposition="outside")
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#121722",
        plot_bgcolor="#121722",
        yaxis_range=[0, max(df["Total Score"].max() * 1.2, 0.1)],
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch", key="compare_bar_chart")

    # --- Radar Chart ---
    st.subheader("Criteria Radar")
    radar_data = []
    for _, row in df.iterrows():
        for criterion in criteria_defs:
            if criterion in df.columns:
                radar_data.append({
                    "Region": row["Region"],
                    "Criterion": criterion.replace("_", " ").title(),
                    "Score": row[criterion],
                })

    if radar_data:
        import pandas as pd
        radar_df = pd.DataFrame(radar_data)
        fig_radar = px.line_polar(
            radar_df,
            r="Score",
            theta="Criterion",
            color="Region",
            line_close=True,
            range_r=[0, 1],
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig_radar.update_traces(fill="toself", opacity=0.5)
        fig_radar.update_layout(
            template="plotly_dark",
            paper_bgcolor="#121722",
            plot_bgcolor="#121722",
        )
        st.plotly_chart(fig_radar, width="stretch", key="compare_radar_chart")

