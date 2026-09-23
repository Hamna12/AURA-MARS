"""
AURA Mars — Cinematic Landing Experience (video-first)

The full-screen entry sequence shown on first launch, before the
dashboard. The video IS the hero — no Three.js scene, no 3D planets,
no spacecraft model, and no GSAP renders on top of it. That interactive
3D environment lives entirely in the Journey to Mars tab, after the
user has clicked through; the two are deliberately kept as separate
systems (see app/components/journey_3d.py), not layered on top of one
another here.

Sequence: real video plays full-screen -> "AURA MARS" fades in -> the
subtitle fades in -> the tagline fades in -> the CTA (a real Streamlit
button rendered by the caller, see below) fades/slides in. Timed with
plain CSS `@keyframes`/`animation-delay`, not GSAP — there is nothing
here complex enough to need a JS animation library, and skipping it
keeps this component's payload small and genuinely independent of the
Three.js/GSAP toolkit the interactive scene uses.

WHERE TO PUT YOUR VIDEO FILE
-----------------------------
Place it at:  app/static/landing_hero.mp4  (see LANDING_VIDEO_FILENAME)

That's it — no code change needed.

The video is embedded directly in the page as a base64 data URI (see
_landing_video_uri()), the same way fonts/textures/vendored JS are
handled elsewhere in this project — NOT served via Streamlit's
/app/static/* route. That route depends on `enableStaticServing` in
.streamlit/config.toml actually being picked up, which in turn depends
on Streamlit being launched with the project root as its working
directory; a data URI needs no separate HTTP request at all, so it
can't be broken by a working-directory mismatch, a missed config
reload, a browser extension blocking the request, or any same-origin/
sandbox subtlety of the iframe it lives in. At ~4-8MB (base64 adds
~33% over the raw file), this is comfortably under Streamlit's default
200MB WebSocket message-size limit, and this page no longer carries
the Three.js/GSAP payload the old cinematic version did, so the total
transfer is still modest — trivial besides on localhost either way.

If the file isn't there yet, render_landing_scene() falls back to a
plain dark gradient at render time (a real Python check, not a
client-side guess) — it never ships a broken/empty video tag.

Once the real file is in place, the exact composition here (scrim
strength, brand-cluster position, fade timing) is a best-effort default
that should be re-checked against where the footage actually places
its subject (Earth/spacecraft/Mars) — see the module-level TODO note
near BOOT_SEQUENCE_SECONDS.

The actual "ENTER THE MISSION" control is a real Streamlit button
rendered by the caller (app/app.py) directly below this component, not
a button inside the iframe — st.iframe/components.html is one-way
(renders HTML, no events back to Python), so the moment that needs to
trigger a real page-state change has to be a native Streamlit widget.
Both the iframe and the button are positioned with `position: fixed`
against the true browser viewport (see apply_cinematic_chrome() in
app/theme.py) rather than a document-flow negative-margin hack, so the
button stays fully on-screen and centered at any window size.

BOOT_SEQUENCE_SECONDS below is the single source of truth both this
component's own CSS timeline AND app.py's button-reveal delay are built
from, so they can't drift out of sync — if you retime the @keyframes
delays inside _TEMPLATE, update this constant to match the tagline's
finish time.
"""

import base64
from functools import lru_cache
from pathlib import Path

import streamlit as st

_STATIC_DIR = Path(__file__).parent.parent / "static"

# Drop your video file at app/static/landing_hero.mp4 — nothing else to
# configure. See the module docstring for details.
LANDING_VIDEO_FILENAME = "landing_hero.mp4"

# TODO once the real video is in place: confirm its actual duration/aspect
# ratio and where it visually "settles" (does it have a natural pause or
# ending beat?), then retune the fade delays below and this constant to
# match — these are reasonable, easy-to-adjust defaults, not a measurement
# of real footage.
BOOT_SEQUENCE_SECONDS = 5.3


def landing_video_path() -> Path:
    """Absolute filesystem path where the landing video is expected."""
    return _STATIC_DIR / LANDING_VIDEO_FILENAME


def landing_video_available() -> bool:
    """Whether the video file has been placed yet."""
    return landing_video_path().exists()


@lru_cache(maxsize=1)
def _landing_video_uri() -> str:
    """Base64 data: URI for the landing video. Only called when the file
    exists (see render_landing_scene) — cached so repeated Streamlit
    reruns don't re-read/re-encode a multi-MB file from disk every time."""
    data = landing_video_path().read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:video/mp4;base64,{b64}"


_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { width: 100%; height: 100%; overflow: hidden; background: #02030a; }
  body { font-family: 'Inter', -apple-system, sans-serif; }

  #video-bg, #fallback-bg {
    position: fixed; inset: 0;
    width: 100%; height: 100%;
    object-fit: cover;
  }
  #video-bg { background: #000; }
  #fallback-bg {
    background: radial-gradient(ellipse at 50% 38%, #17203a 0%, #070a14 55%, #02030a 100%);
  }

  /* Darkens the top edge (legibility for any future HUD) and the bottom
     third (legibility for branding/CTA); the middle is left relatively
     clear on the assumption the subject of the footage reads best there.
     Re-check this against the real video once it's in place. */
  #scrim {
    position: fixed; inset: 0; z-index: 1; pointer-events: none;
    background: linear-gradient(
      180deg,
      rgba(2,3,10,0.5) 0%,
      rgba(2,3,10,0.05) 26%,
      rgba(2,3,10,0.1) 55%,
      rgba(2,3,10,0.75) 100%
    );
  }

  @keyframes auraFadeUp {
    from { opacity: 0; transform: translateY(14px); }
    to { opacity: 1; transform: translateY(0); }
  }

  #brand-cluster {
    position: fixed; left: 50%; bottom: 14vh;
    transform: translateX(-50%);
    z-index: 2;
    text-align: center;
    max-width: 90vw;
  }
  #wordmark {
    font-weight: 700;
    font-size: clamp(28px, 3.6vw, 42px);
    letter-spacing: 0.1em;
    color: #F2EEE7;
    text-shadow: 0 2px 20px rgba(0, 0, 0, 0.6);
    opacity: 0;
    animation: auraFadeUp 0.9s ease forwards;
    animation-delay: 3.0s;
  }
  #wordmark .accent { color: #D9683A; }
  #subtitle {
    font-weight: 500;
    font-size: clamp(13px, 1.5vw, 16px);
    color: #C7CEDB;
    letter-spacing: 0.03em;
    margin-top: 10px;
    opacity: 0;
    animation: auraFadeUp 0.7s ease forwards;
    animation-delay: 3.9s;
  }
  #tagline {
    font-size: 13px;
    color: #8A93A6;
    margin-top: 8px;
    opacity: 0;
    animation: auraFadeUp 0.7s ease forwards;
    animation-delay: 4.6s;
  }
</style>
</head>
<body>
  __VIDEO_OR_FALLBACK__
  <div id="scrim"></div>

  <div id="brand-cluster">
    <div id="wordmark">AURA <span class="accent">MARS</span></div>
    <div id="subtitle">Evidence-Grounded Mission Intelligence</div>
    <div id="tagline">Explore the science. Understand the mission. Go beyond Earth.</div>
  </div>
</body>
</html>
"""

_VIDEO_TAG = """
  <video id="video-bg" autoplay muted loop playsinline>
    <source src="__VIDEO_URI__" type="video/mp4">
  </video>
  <script>
  (function () {
    var video = document.getElementById('video-bg');
    // The data: URI can't 404 or hit a routing/CORS issue — it's embedded
    // directly in this document. A play() promise can still reject
    // transiently (e.g. a timing race on first paint inside a sandboxed
    // srcdoc iframe); retry once rather than giving up, since the video
    // itself is known-good at this point.
    var playPromise = video.play();
    if (playPromise !== undefined) {
      playPromise.catch(function () {
        setTimeout(function () { video.play().catch(function () {}); }, 300);
      });
    }
  })();
  </script>
"""

_FALLBACK_TAG = '  <div id="fallback-bg"></div>'


def render_landing_scene(height: int = 720) -> None:
    """Render the cinematic landing scene (everything except the CTA button)."""
    video_block = (
        _VIDEO_TAG.replace("__VIDEO_URI__", _landing_video_uri())
        if landing_video_available()
        else _FALLBACK_TAG
    )
    html = _TEMPLATE.replace("__VIDEO_OR_FALLBACK__", video_block)
    st.iframe(html, height=height)
