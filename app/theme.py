"""
AURA Mars — Mission Console Theme

Injects the dark Mars research-console visual theme via CSS. This module
is purely presentational: it does not touch pipeline logic, scoring, or
data. Safe to import from any Streamlit page.
"""

import random

import streamlit as st


def _generate_starfield_shadows(n_stars: int, max_size: int, seed: int) -> str:
    """
    Generate a deterministic (fixed seed, so it's stable across redeploys
    and reruns) set of CSS box-shadow dots — the classic pure-CSS
    starfield technique. Returns a comma-separated box-shadow value.
    """
    rng = random.Random(seed)
    shadows = []
    for _ in range(n_stars):
        x = rng.randint(0, 1600)
        y = rng.randint(0, 1600)
        shadows.append(f"{x}px {y}px #E9EEF5")
    return ", ".join(shadows)


_STARS_SMALL = _generate_starfield_shadows(220, 1, seed=42)
_STARS_MEDIUM = _generate_starfield_shadows(90, 2, seed=43)
_STARS_LARGE = _generate_starfield_shadows(35, 3, seed=44)


# ---------------------------------------------------------------------------
# Palette (single source of truth for the theme)
# ---------------------------------------------------------------------------
COLORS = {
    "bg": "#090B10",
    "panel": "#121722",
    "panel_secondary": "#1A2230",
    "cyan": "#4DD8E8",
    "glass": "rgba(18, 23, 34, 0.55)",
    "glass_border": "rgba(77, 216, 232, 0.18)",
    "border": "#2B3748",
    "mars_orange": "#D9683A",
    "mars_sand": "#C88A63",
    "evidence_green": "#62D49B",
    "warning_amber": "#E8AD56",
    "unknown_purple": "#A98BFF",
    "info_blue": "#55B8D9",
    "text": "#E9EEF5",
    "text_muted": "#929CAA",
}


def apply_aura_theme() -> None:
    """
    Inject the AURA Mars dark research-console CSS theme.

    Call once near the top of the Streamlit entry point (app/app.py),
    after `st.set_page_config`. Safe to call multiple times.
    """
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

        :root {{
            --aura-bg: {COLORS["bg"]};
            --aura-panel: {COLORS["panel"]};
            --aura-panel-2: {COLORS["panel_secondary"]};
            --aura-border: {COLORS["border"]};
            --aura-orange: {COLORS["mars_orange"]};
            --aura-sand: {COLORS["mars_sand"]};
            --aura-green: {COLORS["evidence_green"]};
            --aura-amber: {COLORS["warning_amber"]};
            --aura-purple: {COLORS["unknown_purple"]};
            --aura-blue: {COLORS["info_blue"]};
            --aura-text: {COLORS["text"]};
            --aura-muted: {COLORS["text_muted"]};
            --aura-cyan: {COLORS["cyan"]};
            --aura-glass: {COLORS["glass"]};
            --aura-glass-border: {COLORS["glass_border"]};
        }}

        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
        }}

        /* ---------------- App shell ---------------- */
        .stApp {{
            background: var(--aura-bg);
            color: var(--aura-text);
        }}

        [data-testid="stHeader"] {{
            background: transparent;
        }}

        [data-testid="stSidebar"] {{
            background: var(--aura-panel);
            border-right: 1px solid var(--aura-border);
        }}

        [data-testid="stSidebar"] * {{
            color: var(--aura-text);
        }}

        section.main > div {{
            padding-top: 1.2rem;
        }}

        /* ---------------- Headings ---------------- */
        h1, h2, h3, h4 {{
            color: var(--aura-text) !important;
            font-weight: 600 !important;
            letter-spacing: 0.01em;
        }}

        h1 {{
            color: var(--aura-orange) !important;
        }}

        /* ---------------- Text ---------------- */
        p, li, span, label, .stMarkdown {{
            color: var(--aura-text);
        }}

        .stCaption, [data-testid="stCaptionContainer"] {{
            color: var(--aura-muted) !important;
        }}

        /* ---------------- Cards / containers ---------------- */
        .aura-card {{
            background: var(--aura-panel);
            border: 1px solid var(--aura-border);
            border-radius: 12px;
            padding: 1.1rem 1.3rem;
            margin-bottom: 0.9rem;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.25);
        }}

        .aura-card-secondary {{
            background: var(--aura-panel-2);
            border: 1px solid var(--aura-border);
            border-radius: 10px;
            padding: 0.9rem 1.1rem;
            margin-bottom: 0.7rem;
        }}

        .aura-card-accent {{
            border-left: 3px solid var(--aura-orange);
        }}

        [data-testid="stVerticalBlockBorderWrapper"] > div > div[data-testid="stVerticalBlock"] {{
            gap: 0.6rem;
        }}

        div[data-testid="stContainer"] {{
            border-radius: 12px;
        }}

        /* Streamlit's native bordered container (st.container(border=True))
           — used as the safe "card" surface for any LLM- or user-derived
           text, since it renders through st.markdown without raw HTML. */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div[data-testid="stVerticalBlock"]) {{
            background: var(--aura-panel-2);
            border: 1px solid var(--aura-border) !important;
            border-radius: 10px !important;
        }}

        /* ---------------- Status pills ---------------- */
        .aura-pill {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
            letter-spacing: 0.02em;
            margin: 0.15rem 0.35rem 0.15rem 0;
            border: 1px solid transparent;
        }}

        .aura-pill-orange {{
            background: rgba(217, 104, 58, 0.15);
            color: var(--aura-orange);
            border-color: rgba(217, 104, 58, 0.4);
        }}

        .aura-pill-green {{
            background: rgba(98, 212, 155, 0.12);
            color: var(--aura-green);
            border-color: rgba(98, 212, 155, 0.35);
        }}

        .aura-pill-amber {{
            background: rgba(232, 173, 86, 0.12);
            color: var(--aura-amber);
            border-color: rgba(232, 173, 86, 0.35);
        }}

        .aura-pill-purple {{
            background: rgba(169, 139, 255, 0.12);
            color: var(--aura-purple);
            border-color: rgba(169, 139, 255, 0.35);
        }}

        .aura-pill-blue {{
            background: rgba(85, 184, 217, 0.12);
            color: var(--aura-blue);
            border-color: rgba(85, 184, 217, 0.35);
        }}

        .aura-pill-muted {{
            background: rgba(146, 156, 170, 0.10);
            color: var(--aura-muted);
            border-color: rgba(146, 156, 170, 0.3);
        }}

        /* ---------------- Metrics ---------------- */
        [data-testid="stMetric"] {{
            background: var(--aura-panel-2);
            border: 1px solid var(--aura-border);
            border-radius: 10px;
            padding: 0.7rem 0.9rem;
        }}

        [data-testid="stMetricLabel"] {{
            color: var(--aura-muted) !important;
        }}

        [data-testid="stMetricValue"] {{
            color: var(--aura-text) !important;
            font-size: 1.25rem;
            font-weight: 600;
        }}

        /* ---------------- Tabs ----------------
           Targets both data-testid (stTabs/stTab/stTabPanel, confirmed for
           this Streamlit version) and the underlying data-baseweb
           attributes, since Streamlit wraps Base Web's tab components
           rather than replacing them. Minimal underline-indicator style
           (no boxed/notebook-tab chrome) to match the console's flat,
           glass-panel visual language elsewhere. */
        [data-testid="stTabs"] [data-baseweb="tab-list"] {{
            gap: 4px;
            border-bottom: 1px solid var(--aura-border);
        }}

        [data-testid="stTab"],
        [data-testid="stTabs"] [data-baseweb="tab"] {{
            background: transparent !important;
            border: none !important;
            border-radius: 0 !important;
            padding: 10px 18px !important;
            font-weight: 500;
            font-size: 0.92rem;
            color: var(--aura-muted) !important;
            transition: color 0.15s ease;
        }}

        [data-testid="stTab"]:hover,
        [data-testid="stTabs"] [data-baseweb="tab"]:hover {{
            color: var(--aura-text) !important;
        }}

        [data-testid="stTab"][aria-selected="true"],
        [data-testid="stTabs"] [aria-selected="true"] {{
            color: var(--aura-orange) !important;
            background: transparent !important;
            box-shadow: inset 0 -2px 0 0 var(--aura-orange) !important;
        }}

        [data-testid="stTabPanel"] {{
            padding-top: 1.3rem;
        }}

        /* ---------------- Expanders ---------------- */
        .stExpander, [data-testid="stExpander"] {{
            background: var(--aura-panel);
            border: 1px solid var(--aura-border) !important;
            border-radius: 10px;
        }}

        [data-testid="stExpander"] summary {{
            color: var(--aura-text) !important;
            font-weight: 500;
        }}

        /* ---------------- Buttons ---------------- */
        .stButton > button {{
            border-radius: 8px;
            border: 1px solid var(--aura-border);
            background: var(--aura-panel-2);
            color: var(--aura-text);
            font-weight: 500;
        }}

        .stButton > button:hover {{
            border-color: var(--aura-orange);
            color: var(--aura-orange);
        }}

        .stButton > button[kind="primary"] {{
            background: var(--aura-orange);
            border: 1px solid var(--aura-orange);
            color: #14100C;
            font-weight: 600;
        }}

        .stButton > button[kind="primary"]:hover {{
            background: #c25a2f;
            border-color: #c25a2f;
            color: #14100C;
        }}

        /* ---------------- Inputs ---------------- */
        .stTextArea textarea, .stTextInput input {{
            background: var(--aura-panel-2) !important;
            color: var(--aura-text) !important;
            border: 1px solid var(--aura-border) !important;
            border-radius: 8px !important;
        }}

        /* ---------------- Alerts ---------------- */
        .stAlert {{
            border-radius: 10px;
            border: 1px solid var(--aura-border);
        }}

        /* ---------------- Divider ---------------- */
        hr {{
            border-color: var(--aura-border) !important;
        }}

        /* ---------------- Dataframes ---------------- */
        [data-testid="stDataFrame"] {{
            border: 1px solid var(--aura-border);
            border-radius: 10px;
        }}

        /* ---------------- Header banner ---------------- */
        .aura-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 0.6rem;
            background: linear-gradient(135deg, var(--aura-panel) 0%, var(--aura-panel-2) 100%);
            border: 1px solid var(--aura-border);
            border-radius: 12px;
            padding: 1rem 1.4rem;
            margin-bottom: 1.2rem;
        }}

        .aura-header-title {{
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--aura-orange);
            letter-spacing: 0.04em;
            margin: 0;
        }}

        .aura-header-subtitle {{
            font-size: 0.88rem;
            color: var(--aura-muted);
            margin: 0.15rem 0 0 0;
        }}

        .aura-header-mode {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.72rem;
            letter-spacing: 0.08em;
            color: var(--aura-green);
            background: rgba(98, 212, 155, 0.10);
            border: 1px solid rgba(98, 212, 155, 0.35);
            border-radius: 999px;
            padding: 0.3rem 0.8rem;
            white-space: nowrap;
        }}

        /* ---------------- Section label ---------------- */
        .aura-section-label {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.72rem;
            letter-spacing: 0.1em;
            color: var(--aura-muted);
            text-transform: uppercase;
            margin-bottom: 0.3rem;
        }}

        /* ================================================================
           Animated space background — a real CSS keyframe animation
           (twinkling starfield), not just a static gradient. Fixed and
           behind all content; ignores pointer events so it never blocks
           clicks.
           ================================================================ */
        .aura-starfield, .aura-starfield::before, .aura-starfield::after {{
            content: "";
            position: fixed;
            inset: 0;
            z-index: -1;
            pointer-events: none;
        }}

        .aura-starfield {{
            background: transparent;
            box-shadow: {_STARS_SMALL};
            width: 1px; height: 1px;
            animation: aura-twinkle 4s ease-in-out infinite alternate;
        }}

        .aura-starfield::before {{
            box-shadow: {_STARS_MEDIUM};
            width: 2px; height: 2px;
            animation: aura-twinkle 6s ease-in-out infinite alternate-reverse;
        }}

        .aura-starfield::after {{
            box-shadow: {_STARS_LARGE};
            width: 3px; height: 3px;
            animation: aura-drift 90s linear infinite, aura-twinkle 5s ease-in-out infinite;
        }}

        @keyframes aura-twinkle {{
            from {{ opacity: 0.35; }}
            to {{ opacity: 0.9; }}
        }}

        @keyframes aura-drift {{
            from {{ transform: translateY(0); }}
            to {{ transform: translateY(-120px); }}
        }}

        /* Slow-pulsing Mars-orange glow behind the header banner */
        .aura-header {{
            position: relative;
            overflow: hidden;
        }}

        .aura-header::before {{
            content: "";
            position: absolute;
            top: -60%; right: -10%;
            width: 260px; height: 260px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(217,104,58,0.35) 0%, rgba(217,104,58,0) 70%);
            animation: aura-pulse 5s ease-in-out infinite;
            pointer-events: none;
        }}

        @keyframes aura-pulse {{
            0%, 100% {{ opacity: 0.6; transform: scale(1); }}
            50% {{ opacity: 1; transform: scale(1.15); }}
        }}

        /* Animated gradient shimmer on the main title */
        .aura-header-title {{
            background: linear-gradient(90deg, var(--aura-orange), var(--aura-sand), var(--aura-orange));
            background-size: 200% auto;
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            color: transparent;
            animation: aura-shimmer 6s linear infinite;
        }}

        @keyframes aura-shimmer {{
            0% {{ background-position: 0% center; }}
            100% {{ background-position: 200% center; }}
        }}

        /* Live pulsing status dot on the mode badge */
        .aura-header-mode {{
            position: relative;
            padding-left: 1.5rem !important;
        }}

        .aura-header-mode::before {{
            content: "";
            position: absolute;
            left: 0.7rem; top: 50%;
            width: 6px; height: 6px;
            border-radius: 50%;
            background: var(--aura-green);
            transform: translateY(-50%);
            box-shadow: 0 0 6px var(--aura-green);
            animation: aura-blink 1.8s ease-in-out infinite;
        }}

        @keyframes aura-blink {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.3; }}
        }}

        /* Smooth motion on interactive surfaces */
        .aura-card, .aura-card-secondary,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div[data-testid="stVerticalBlock"]),
        [data-testid="stMetric"], [data-testid="stExpander"], .stButton > button {{
            transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
        }}

        .aura-card:hover, .aura-card-secondary:hover,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div[data-testid="stVerticalBlock"]):hover,
        [data-testid="stMetric"]:hover {{
            border-color: rgba(217, 104, 58, 0.45) !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
        }}

        .stButton > button:hover {{
            transform: translateY(-1px);
        }}

        .aura-pill {{
            transition: transform 0.15s ease;
        }}

        .aura-pill:hover {{
            transform: scale(1.05);
        }}

        /* ---------------- Glass panels (deep-space / mission-console) ---------------- */
        .aura-glass {{
            background: var(--aura-glass);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid var(--aura-glass-border);
            border-radius: 10px;
            padding: 1rem 1.2rem;
            box-shadow: 0 4px 24px rgba(0, 0, 0, 0.35);
        }}

        .aura-glass-cyan-edge {{
            border-color: rgba(77, 216, 232, 0.35);
            box-shadow: 0 0 18px rgba(77, 216, 232, 0.08), 0 4px 24px rgba(0, 0, 0, 0.35);
        }}

        /* ---------------- Telemetry / mono readouts ---------------- */
        .aura-telemetry {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.74rem;
            letter-spacing: 0.09em;
            text-transform: uppercase;
            color: var(--aura-cyan);
        }}

        .aura-telemetry-muted {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.7rem;
            letter-spacing: 0.06em;
            color: var(--aura-muted);
        }}

        .aura-pill-cyan {{
            background: rgba(77, 216, 232, 0.10);
            color: var(--aura-cyan);
            border-color: rgba(77, 216, 232, 0.35);
        }}

        </style>
        <div class="aura-starfield"></div>
        """,
        unsafe_allow_html=True,
    )


def apply_cinematic_chrome() -> None:
    """
    Hide Streamlit's own UI shell (sidebar, header/toolbar, footer, content
    padding, scrollbars) for the full-screen cinematic landing/transition
    phases, so the scene reads as full-screen rather than "a Streamlit app
    with a widget in it". Call in addition to apply_aura_theme(), only
    while st.session_state["mission_phase"] != "dashboard" (see app/app.py).

    Critically, this also forces the phase's st.iframe element itself to
    `position: fixed; inset: 0` at true 100vw/100vh — bypassing Streamlit's
    own width/height plumbing, which sizes the iframe relative to its
    parent block's document-flow height, not the viewport. Doing this here
    means every real Streamlit widget rendered after the iframe (e.g. the
    "ENTER THE MISSION" button) can be positioned with plain `position:
    fixed` too and have it mean what it says — anchored to the actual
    browser viewport, responsive across window sizes — instead of needing
    a pixel-guessed negative margin-top to visually drag it into place.
    """
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
        [data-testid="stHeader"], [data-testid="stToolbar"], footer, #MainMenu {
            display: none !important;
        }
        [data-testid="stAppViewContainer"] > .main, .block-container {
            padding: 0 !important;
            max-width: 100% !important;
        }
        /* Scoped to html/body only, deliberately not to Streamlit's inner
           containers: if any of those establish a new CSS containing block
           (e.g. via a transform in Streamlit's own default styles), an
           overflow:hidden on that same element would clip position:fixed
           descendants — including the full-screen iframe — to its box
           instead of the true viewport. html/body carry no such risk. */
        html, body {
            overflow: hidden !important;
        }
        iframe[data-testid="stIFrame"] {
            position: fixed !important;
            inset: 0 !important;
            width: 100vw !important;
            height: 100vh !important;
            border: none !important;
            z-index: 1;
        }
        .stApp { background: #02030a; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_aura_header() -> None:
    """Render the standard AURA Mars mission-console header banner."""
    st.markdown(
        """
        <div class="aura-header">
            <div>
                <p class="aura-header-title">AURA MARS</p>
                <p class="aura-header-subtitle">Evidence-grounded mission intelligence console</p>
            </div>
            <div class="aura-header-mode">LOCAL RESEARCH MODE</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_pill(text: str, variant: str = "muted") -> str:
    """
    Return the HTML markup for a single status pill (does not render it).

    Parameters
    ----------
    text : str
        The label to display inside the pill.
    variant : str
        One of: orange, green, amber, purple, blue, muted.
    """
    variant = variant if variant in {"orange", "green", "amber", "purple", "blue", "muted"} else "muted"
    return f'<span class="aura-pill aura-pill-{variant}">{text}</span>'


def render_pills(items: list, variant: str = "orange") -> None:
    """Render a row of status pills."""
    if not items:
        return
    html = "".join(render_pill(item, variant) for item in items)
    st.markdown(f'<div>{html}</div>', unsafe_allow_html=True)


def section_label(text: str) -> None:
    """Render a small uppercase monospace section label above a block."""
    st.markdown(f'<div class="aura-section-label">{text}</div>', unsafe_allow_html=True)
