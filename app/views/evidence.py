"""
AURA Mars — Evidence Tab

Full drill-down into the evidence behind the last query result: original
question, primary answer, evidence-strength breakdown, retrieved passages
with source metadata/links, raw generation runs, and verification detail.
"""

import streamlit as st

from app.theme import section_label
from app.components.confidence_gauge import render_confidence_gauge
from app.components.source_card import render_source_card


def render_evidence_tab():
    """Render the Evidence tab contents."""
    st.header("Evidence Explorer")
    st.caption(
        "Full evidence trail behind the most recent Ask-tab query — every retrieved passage, "
        "the deterministic score breakdown, and the raw model outputs used to compute it."
    )

    result = st.session_state.get("last_result")

    if result is None:
        st.info(
            "No results yet. Use the **Ask** tab to submit a question first, "
            "then return here to explore the evidence."
        )
        return

    section_label("Original question")
    with st.container(border=True):
        st.markdown(result.question)

    if not result.retrieved_chunks:
        st.warning(
            "No sufficiently relevant sources were found for this question, so no evidence "
            "trail is available."
        )
        return

    st.divider()

    # --- Primary answer ---
    st.subheader("Primary Answer")
    with st.container(border=True):
        st.markdown(result.claim)

    st.divider()

    # --- Evidence-strength breakdown ---
    st.subheader("Evidence-Strength Breakdown")
    render_confidence_gauge(result.confidence, key_prefix="evidence")

    st.divider()

    # --- Retrieved passages ---
    st.subheader("Retrieved Source Passages")
    for i, chunk in enumerate(result.retrieved_chunks):
        render_source_card(chunk, index=i, show_details=True)

    st.divider()

    # --- Raw generation runs ---
    st.subheader("Generation Consistency (Raw Runs)")
    st.caption(
        f"The model was run {len(result.raw_answers)} times with the same evidence. "
        "High similarity across runs indicates stable reasoning, and is what drives the "
        "Generation Consistency sub-score above."
    )
    if result.raw_answers:
        for i, answer in enumerate(result.raw_answers):
            with st.expander(f"Run {i + 1}"):
                st.text(answer)

    st.divider()

    # --- Verification details ---
    st.subheader("Verification Details")
    if result.verification.verified:
        st.success("All claims trace back to source passages.")
    else:
        st.warning("Unsupported claims detected — these could not be traced to a retrieved passage:")
        for claim in result.verification.unsupported_claims:
            st.markdown(f"- {claim}")

    if result.verification.raw_response:
        with st.expander("Raw verification response"):
            st.text(result.verification.raw_response)

    st.divider()

    # --- Direct vs inferred support ---
    st.subheader("Direct vs. Inferred Support")
    st.caption(
        "Each source card above is labelled Direct / Partial / Contextual support based on its "
        "retrieval relevance score — a deterministic signal, not an LLM judgement."
    )
    d_col1, d_col2 = st.columns(2)
    with d_col1:
        section_label("Known (directly supported)")
        with st.container(border=True):
            st.markdown(result.known.strip() or "No directly supported facts were isolated for this question.")
        section_label("Conflicting")
        with st.container(border=True):
            st.markdown(result.conflicting.strip() or "No conflicts identified in the retrieved passages.")
    with d_col2:
        section_label("Unknown / not covered")
        with st.container(border=True):
            st.markdown(result.unknowns.strip() or "All aspects of the question appear to be addressed by the sources.")
        section_label("Limitations")
        with st.container(border=True):
            st.markdown(result.limitations.strip() or "No specific limitations were called out for this question.")
