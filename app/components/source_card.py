"""
AURA Mars — Source Card Component

Reusable card for displaying a retrieved source chunk with citation
metadata, relevance strength, and clickable links (when available).

Never fabricates a URL: if a source has no `url`/`pdf_url` in its
metadata, the card says so explicitly rather than guessing a link.
"""

import streamlit as st

from src.models import RetrievedChunk
from src.config import SOURCE_QUALITY_MAP


# Deterministic (non-LLM) support-strength labelling, based on the same
# ChromaDB cosine-distance-derived similarity used in confidence scoring.
# This is a presentational bucket, not part of the confidence formula.
_DIRECT_SUPPORT_THRESHOLD = 75.0
_PARTIAL_SUPPORT_THRESHOLD = 50.0


def _support_label(similarity_pct: float) -> tuple[str, str]:
    """Return (label, pill_variant) for a similarity percentage."""
    if similarity_pct >= _DIRECT_SUPPORT_THRESHOLD:
        return "Direct support", "green"
    elif similarity_pct >= _PARTIAL_SUPPORT_THRESHOLD:
        return "Partial support", "amber"
    else:
        return "Contextual support", "muted"


def _quality_badge(source_type: str) -> tuple[str, str]:
    """Return (label, pill_variant) for a source type / quality tier."""
    quality = SOURCE_QUALITY_MAP.get(source_type, 0.5)
    if quality >= 0.9:
        return "Peer-Reviewed / NASA", "green"
    elif quality >= 0.8:
        return "NASA Report", "blue"
    else:
        return "Preprint / General", "amber"


def render_source_card(
    chunk: RetrievedChunk,
    index: int = 0,
    show_details: bool = False,
):
    """
    Render a styled card for a retrieved source chunk.

    Parameters
    ----------
    chunk : RetrievedChunk
        The chunk to display.
    index : int
        Display index (1-based in the UI).
    show_details : bool
        If True, show additional metadata (similarity score, quality, tags).
    """
    meta = chunk.metadata or {}
    source = meta.get("source", "Unknown")
    source_type = meta.get("source_type", "general")
    region_tag = meta.get("region_tag", "")
    title = meta.get("title") or source.replace("_", " ")
    year = meta.get("year", "")
    url = meta.get("url", "")
    pdf_url = meta.get("pdf_url", "")
    takeaway = meta.get("takeaway", "")

    quality_label, quality_variant = _quality_badge(source_type)
    similarity_pct = max(0.0, min(100.0, (1.0 - chunk.distance / 2.0) * 100))
    support_label, support_variant = _support_label(similarity_pct)

    header_bits = [title]
    if year:
        header_bits.append(f"({year})")
    header = " ".join(header_bits)

    with st.expander(
        f"Passage {index + 1} — {header}",
        expanded=(index == 0),
    ):
        pill_html = (
            f'<span class="aura-pill aura-pill-{quality_variant}">{quality_label}</span>'
            f'<span class="aura-pill aura-pill-{support_variant}">{support_label}</span>'
        )
        st.markdown(f"<div>{pill_html}</div>", unsafe_allow_html=True)

        if takeaway:
            st.markdown(f"**Takeaway:** {takeaway}")

        st.markdown('<div class="aura-section-label">Evidence excerpt</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(chunk.text)

        # --- Links (never fabricated) ---
        link_lines = []
        if url:
            link_lines.append(f"[Open source]({url})")
        if pdf_url:
            link_lines.append(f"[Open PDF]({pdf_url})")

        if link_lines:
            st.markdown("  |  ".join(link_lines))
        else:
            st.caption("Source link unavailable in current metadata.")

        if show_details:
            st.divider()
            detail_cols = st.columns(3)
            detail_cols[0].caption(f"**Relevance / retrieval strength**: {similarity_pct:.1f}%")
            detail_cols[1].caption(f"**Source type**: {source_type}")
            if region_tag:
                detail_cols[2].caption(f"**Region tag**: {region_tag}")
