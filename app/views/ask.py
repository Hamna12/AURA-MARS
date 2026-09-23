"""
AURA Mars — Ask Tab

The primary interaction screen. Users enter a question, the full pipeline
runs, and the structured, evidence-grounded output is displayed: answer,
mission relevance, evidence strength, known/unknown/conflicting/limitations,
sources with links, and suggested follow-up questions.
"""

import streamlit as st

from src.pipeline import run_pipeline
from src.config import GENERATION_RUNS
from app.theme import render_pill, render_pills, section_label
from app.components.confidence_gauge import render_confidence_gauge
from app.components.source_card import render_source_card
from app.components.report_export import render_export_button


EXAMPLE_QUESTIONS = [
    "What terrain features matter most when selecting a Mars landing or rover exploration site?",
    "What evidence exists for subsurface water ice in Arcadia Planitia?",
    "What radiation risks do crewed Mars missions need to shield against?",
    "What geological evidence supports ancient water activity in Jezero Crater?",
]

NO_EVIDENCE_MESSAGE = (
    "No sufficiently relevant sources were found in the current collection. "
    "Try a broader question or ingest additional papers."
)


def _apply_pending_question():
    """Apply a question queued by an example-question button before the
    text_area widget is instantiated this run."""
    pending = st.session_state.pop("pending_question", None)
    if pending is not None:
        st.session_state["ask_question_input"] = pending


def _render_info_card(title: str, body: str, empty_message: str = "Not addressed by the retrieved sources.") -> None:
    """Render a titled card for LLM-derived text. Uses a native Streamlit
    bordered container (not raw HTML) so LLM/user-influenced text is
    always rendered through st.markdown's safe path, never injected as
    HTML."""
    section_label(title)
    content = body.strip() if body and body.strip() else empty_message
    with st.container(border=True):
        st.markdown(content)


_STRENGTH_VARIANT = {"High": "green", "Medium": "amber", "Low": "orange"}


def _render_result(result) -> None:
    """
    Render a PipelineResult as a tight, at-a-glance research summary:
    question, mission relevance, answer, evidence strength, what's known
    vs. unknown, sources (with links), and follow-ups are always visible.
    Everything else that supports an audit trail — full score breakdown,
    conflicts/limitations, verification detail, raw responses — sits
    behind clearly labelled expanders rather than being force-shown, so
    the default view stays readable instead of a wall of stacked cards.
    The Evidence tab remains the place for the complete, always-expanded
    breakdown.

    Deliberately NOT gated on "was the Ask button just clicked" — it's
    called unconditionally from st.session_state on every script run, so
    the last answer stays visible across tab switches and any other
    rerun-triggering interaction, until a new question is submitted and
    overwrites st.session_state["last_result"].
    """
    st.divider()
    st.caption(f"Showing results for: **{result.question}**")

    # --- No-evidence guardrail: never present an unsupported answer ---
    if not result.retrieved_chunks:
        st.warning(NO_EVIDENCE_MESSAGE)
        return

    # --- Mission relevance pills ---
    render_pills(result.mission_areas, variant="orange")

    # --- Main answer card ---
    st.subheader("Answer")
    with st.container(border=True):
        st.markdown(result.claim)
        if result.evidence_summary:
            st.caption(result.evidence_summary)

    # --- Evidence strength: one-line badge, full breakdown on demand ---
    conf = result.confidence
    variant = _STRENGTH_VARIANT.get(conf.label, "muted")
    st.markdown(
        f"**Evidence Strength:** {render_pill(conf.label, variant)} {conf.final_confidence * 100:.1f}%",
        unsafe_allow_html=True,
    )
    if result.score_explanation:
        st.caption(result.score_explanation)
    with st.expander("Show full scoring breakdown"):
        render_confidence_gauge(conf, key_prefix="ask")

    # --- Known vs. Unknown: the two things a researcher needs first ---
    st.subheader("Known vs. Unknown")
    info_cols = st.columns(2)
    with info_cols[0]:
        _render_info_card(
            "Known",
            result.known,
            empty_message="No directly supported facts were isolated for this question.",
        )
    with info_cols[1]:
        _render_info_card(
            "Unknown",
            result.unknowns,
            empty_message="All aspects of the question appear to be addressed by the sources.",
        )

    with st.expander("More context: conflicts, limitations, mission relevance"):
        _render_info_card(
            "Conflicting",
            result.conflicting,
            empty_message="No conflicts identified in the retrieved passages.",
        )
        _render_info_card(
            "Limitations",
            result.limitations,
            empty_message="No specific limitations were called out for this question.",
        )
        if result.mission_relevance_text:
            section_label("Why this matters for Mars missions")
            st.markdown(result.mission_relevance_text)

    # --- Sources: the trust/authenticity anchor, always visible ---
    st.subheader("Sources")
    for i, chunk in enumerate(result.retrieved_chunks):
        render_source_card(chunk, index=i)

    # --- Verification: one-line badge, flagged claims on demand ---
    st.subheader("Verification")
    if result.verification.verified:
        st.success("All claims verified against source passages.")
    else:
        st.warning(f"{len(result.verification.unsupported_claims)} claim(s) flagged for review.")
        with st.expander("Show flagged claims"):
            for claim in result.verification.unsupported_claims:
                st.markdown(f"- {claim}")

    # --- Follow-up questions ---
    if result.follow_up_questions:
        st.subheader("Suggested Follow-Up Questions")
        for j, fq in enumerate(result.follow_up_questions):
            fq_cols = st.columns([5, 1])
            fq_cols[0].markdown(f"- {fq}")
            if fq_cols[1].button("Ask", key=f"followup_{j}"):
                st.session_state["pending_question"] = fq
                st.rerun()

    st.divider()
    render_export_button(result)
    st.caption(
        "For the complete evidence breakdown — all retrieved passages, sub-scores, and raw "
        "generation runs, always expanded — switch to the **Evidence** tab above."
    )


def render_ask_tab():
    """Render the Ask tab contents."""
    _apply_pending_question()

    st.header("Ask a Mars Research Question")
    st.markdown(
        "Enter any question about Mars exploration. AURA retrieves real scientific sources, "
        "generates a grounded answer, and calculates an evidence-strength score — all locally."
    )

    # --- Question input ---
    question = st.text_area(
        "Your question:",
        placeholder=EXAMPLE_QUESTIONS[0],
        height=100,
        key="ask_question_input",
    )

    # --- Example question suggestions ---
    section_label("Try an example")
    ex_cols = st.columns(len(EXAMPLE_QUESTIONS))
    for i, ex_q in enumerate(EXAMPLE_QUESTIONS):
        short_label = ex_q if len(ex_q) <= 46 else ex_q[:43] + "..."
        if ex_cols[i].button(short_label, key=f"example_q_{i}", help=ex_q, width="stretch"):
            st.session_state["pending_question"] = ex_q
            st.rerun()

    col_submit, col_status = st.columns([1, 3])
    with col_submit:
        submit = st.button("Ask AURA", type="primary", key="ask_submit")

    if submit and question.strip():
        with col_status:
            st.info(
                f"Running pipeline on local Ollama models — {GENERATION_RUNS} generation runs + "
                "verification + score explanation. This can take several minutes on CPU-only hardware."
            )

        with st.status("Running AURA pipeline...", expanded=True) as status_box:
            status_box.write("Starting...")
            result = run_pipeline(question.strip(), on_progress=status_box.write)
            status_box.update(label="Pipeline complete", state="complete", expanded=False)

        # Store result in session state — this is what makes it persist
        # across tab switches and other reruns (see _render_result).
        st.session_state["last_result"] = result

    elif submit:
        st.warning("Please enter a question.")

    # Always render the most recently completed result, regardless of
    # whether *this* script run was triggered by the Ask button. This is
    # what keeps the last Q&A visible on screen until a new question is
    # submitted, instead of vanishing on the next unrelated rerun.
    last_result = st.session_state.get("last_result")
    if last_result is not None:
        _render_result(last_result)
