"""
AURA Mars — Streamlit Main Application

Entry point for the web UI. Run with:
    streamlit run app/app.py

Flow: a one-time cinematic "mission entry" gate (landing -> transition ->
dashboard), tracked in st.session_state["mission_phase"], stands in front
of the existing six-module dashboard. This is presentation-only — the
dashboard's modules, and everything they call into `src/`, are unchanged.
"""

import sys
import time
from pathlib import Path

# Ensure the project root is at the FRONT of sys.path, on every single
# script run, not just the first. Streamlit's own script runner inserts
# this script's own directory (app/) at sys.path[0] before each rerun and
# removes it again afterward (streamlit/runtime/scriptrunner/exec_code.py,
# `modified_sys_path`). Since app/ also contains this very file (app.py),
# "insert once and skip if already present" loses that race from the
# second rerun onward: PROJECT_ROOT stays wherever it landed on the first
# run while app/ gets freshly re-inserted ahead of it every time, so
# `import app` starts resolving to the app.py *file* instead of the app/
# *package* — breaking every `from app.* import ...` with "'app' is not a
# package" on the very first interaction after initial page load.
# Unconditionally re-promoting PROJECT_ROOT to index 0 every run fixes it.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
_project_root_str = str(PROJECT_ROOT)
if _project_root_str in sys.path:
    sys.path.remove(_project_root_str)
sys.path.insert(0, _project_root_str)

import streamlit as st

from app.theme import apply_aura_theme, apply_cinematic_chrome, render_aura_header

if "mission_phase" not in st.session_state:
    st.session_state["mission_phase"] = "landing"  # landing -> transition -> dashboard

_phase = st.session_state["mission_phase"]

# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AURA Mars",
    page_icon="🔴",
    layout="wide",
    initial_sidebar_state="collapsed" if _phase != "dashboard" else "expanded",
)

# Load custom CSS (legacy overrides), then apply the AURA Mars console theme
# on top of it — theme.py is the source of truth for the dark Mars palette.
css_path = Path(__file__).parent / "assets" / "style.css"
if css_path.exists():
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

apply_aura_theme()

# ---------------------------------------------------------------------------
# Cinematic mission-entry gate (landing / transition)
# ---------------------------------------------------------------------------
if _phase == "landing":
    apply_cinematic_chrome()

    from app.components.landing_experience import render_landing_scene, BOOT_SEQUENCE_SECONDS
    render_landing_scene()

    # The CTA is a real Streamlit button (st.iframe has no event channel
    # back to Python), styled to match the scene and revealed via a timed
    # CSS delay so it reads as part of the same sequence. Positioned with
    # `position: fixed` against the true browser viewport (the landing
    # iframe itself is forced to the same fixed/100vh treatment in
    # apply_cinematic_chrome()) rather than a document-flow negative
    # margin, so it stays fully on-screen and centered at any window size.
    st.markdown(
        f"""
        <style>
        /* !important throughout: Streamlit's own default widget CSS (button
           kind/variant styling, container width:100% for vertical-block
           children) otherwise wins on specificity and leaves stray full-width
           borders/backgrounds showing around the actual button. */
        div[data-testid="stButton"] {{
            position: fixed !important;
            left: 50% !important;
            right: auto !important;
            top: auto !important;
            bottom: 6vh !important;
            width: fit-content !important;
            max-width: fit-content !important;
            transform: translateX(-50%) !important;
            z-index: 20;
            border: none !important;
            background: transparent !important;
            box-shadow: none !important;
            opacity: 0;
            animation: auraCtaReveal 0.9s ease forwards;
            animation-delay: {BOOT_SEQUENCE_SECONDS}s;
        }}
        @keyframes auraCtaReveal {{ to {{ opacity: 1; }} }}
        div[data-testid="stButton"] button {{
            width: auto !important;
            background: rgba(10, 12, 20, 0.35) !important;
            backdrop-filter: blur(6px);
            -webkit-backdrop-filter: blur(6px);
            border: 1px solid var(--aura-orange) !important;
            color: var(--aura-orange) !important;
            padding: 0.7rem 1.7rem !important;
            font-family: 'JetBrains Mono', monospace !important;
            letter-spacing: 0.1em;
            font-size: 0.76rem !important;
            border-radius: 4px !important;
            box-shadow: none !important;
            white-space: nowrap;
            transition: background 0.2s ease, border-color 0.2s ease;
        }}
        div[data-testid="stButton"] button:hover {{
            background: rgba(217, 104, 58, 0.12) !important;
            color: var(--aura-orange) !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    if st.button("ENTER THE MISSION →", key="enter_mission_btn"):
        st.session_state["mission_phase"] = "transition"
        st.rerun()
    st.stop()

if _phase == "transition":
    apply_cinematic_chrome()

    from app.components.mission_transition import render_transition_scene, TRANSITION_SECONDS
    render_transition_scene()

    time.sleep(TRANSITION_SECONDS)
    st.session_state["mission_phase"] = "dashboard"
    st.rerun()

# ---------------------------------------------------------------------------
# Dashboard (unchanged six-module console)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.image(
        str(Path(__file__).parent / "assets" / "logo.png"),
        width="stretch",
    ) if (Path(__file__).parent / "assets" / "logo.png").exists() else None

    st.title("AURA Mars")
    st.caption("Augmented Understanding & Research Assistant for Mars Exploration")
    st.divider()
    st.markdown(
        "**Confidence scores are calculated, never generated by the AI.**  \n"
        "All claims are grounded in retrieved scientific sources."
    )
    st.divider()
    st.markdown(
        "Built with Ollama · ChromaDB · Streamlit  \n"
        "100% local · $0 cost"
    )

# ---------------------------------------------------------------------------
# Header banner
# ---------------------------------------------------------------------------
render_aura_header()

# ---------------------------------------------------------------------------
# Tab Navigation
#
# NOTE: tab content modules live in app/views/ (not app/pages/) on purpose.
# Streamlit auto-detects any directory literally named "pages" sibling to
# the entrypoint script and builds its own native multipage sidebar nav
# from it — which would silently compete with the st.tabs() below and
# render each module standalone (blank, since these modules only define
# render_*_tab() and rely on being called from within a `with tab_x:`
# block). Do not rename this back to "pages".
# ---------------------------------------------------------------------------
tab_journey, tab_planner, tab_ask, tab_evidence, tab_compare, tab_mission = st.tabs(
    ["Journey to Mars", "Mission Planner", "Ask", "Evidence", "Compare", "Mission Console"]
)

with tab_journey:
    from app.views.journey import render_journey_tab
    render_journey_tab()

with tab_planner:
    from app.views.mission_planner import render_mission_planner_tab
    render_mission_planner_tab()

with tab_ask:
    from app.views.ask import render_ask_tab
    render_ask_tab()

with tab_evidence:
    from app.views.evidence import render_evidence_tab
    render_evidence_tab()

with tab_compare:
    from app.views.compare import render_compare_tab
    render_compare_tab()

with tab_mission:
    from app.views.mission_console import render_mission_console_tab
    render_mission_console_tab()
