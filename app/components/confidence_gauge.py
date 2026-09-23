"""
AURA Mars — Confidence Gauge Component

Renders a Plotly gauge/meter visualisation for the evidence-strength
score, plus the full deterministic sub-score breakdown.

All numbers displayed here are produced by src.confidence (pure Python,
no LLM). This component only formats and labels them.
"""

import plotly.graph_objects as go
import streamlit as st

from src.models import ConfidenceBreakdown

_MARS_COLORS = {
    "High": "#62D49B",
    "Medium": "#E8AD56",
    "Low": "#D9683A",
}

EVIDENCE_STRENGTH_EXPLANATION = (
    "This is an evidence-strength indicator based on retrieved source quality, "
    "agreement, relevance, and answer consistency. It is not a statistical "
    "probability that the answer is true."
)


def render_confidence_gauge(confidence: ConfidenceBreakdown, key_prefix: str = "default"):
    """
    Render an interactive Plotly gauge showing the final evidence-strength
    score, colour-coded by tier, plus a sub-metric breakdown beneath it.

    Parameters
    ----------
    confidence : ConfidenceBreakdown
        The full confidence breakdown from the pipeline (deterministic).
    key_prefix : str
        Unique prefix for this gauge's Streamlit element key. Required
        because this component is rendered from multiple tabs (Ask,
        Evidence) within the same script run — Streamlit's `st.tabs`
        renders every tab's body every run regardless of which is
        visually active, so two calls with the same auto-generated
        element ID collide (StreamlitDuplicateElementId) unless each
        caller passes a distinct prefix.
    """
    score_pct = confidence.final_confidence * 100
    bar_color = _MARS_COLORS.get(confidence.label, "#929CAA")

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score_pct,
        number={"suffix": "%", "font": {"size": 34, "color": "#E9EEF5"}},
        title={"text": f"Evidence Strength: {confidence.label}", "font": {"size": 16, "color": "#E9EEF5"}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#929CAA"},
            "bar": {"color": bar_color},
            "bgcolor": "#1A2230",
            "bordercolor": "#2B3748",
            "steps": [
                {"range": [0, 40], "color": "rgba(217, 104, 58, 0.15)"},
                {"range": [40, 70], "color": "rgba(232, 173, 86, 0.15)"},
                {"range": [70, 100], "color": "rgba(98, 212, 155, 0.15)"},
            ],
            "threshold": {
                "line": {"color": "#E9EEF5", "width": 2},
                "thickness": 0.75,
                "value": score_pct,
            },
        },
    ))

    fig.update_layout(
        height=230,
        margin=dict(t=45, b=10, l=30, r=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E9EEF5"),
    )
    st.plotly_chart(fig, width="stretch", key=f"{key_prefix}_confidence_gauge")

    st.caption(EVIDENCE_STRENGTH_EXPLANATION)

    # --- Top-level fused scores ---
    col1, col2 = st.columns(2)
    col1.metric(
        "Evidence Confidence",
        f"{confidence.evidence_confidence * 100:.1f}%",
        help="Based on source agreement, retrieval strength, count, and quality",
    )
    col2.metric(
        "Generation Consistency",
        f"{confidence.generation_consistency * 100:.1f}%",
        help="How stable the model's answers are across multiple independent runs",
    )

    # --- Sub-score breakdown ---
    st.markdown('<div class="aura-section-label">Evidence sub-scores</div>', unsafe_allow_html=True)
    sub_col1, sub_col2, sub_col3, sub_col4 = st.columns(4)
    sub_col1.metric("Source Agreement", f"{confidence.source_agreement * 100:.0f}%")
    sub_col2.metric("Retrieval Match", f"{confidence.retrieval_match_strength * 100:.0f}%")
    sub_col3.metric("Source Count", f"{confidence.source_count_score * 100:.0f}%")
    sub_col4.metric("Source Quality", f"{confidence.source_quality_score * 100:.0f}%")
