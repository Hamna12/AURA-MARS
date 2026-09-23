"""
AURA Mars — Vendored JS Library Loader

Three.js and GSAP are vendored locally (app/assets/vendor/) rather than
loaded from a CDN, matching the project's local-first principle and
guaranteeing the cinematic scenes work offline. Streamlit's
`st.iframe`/`components.html` renders a fully self-contained document
(no access to the app's own static file paths), so the library source
is read and inlined directly as `<script>` text rather than referenced
by URL.
"""

from functools import lru_cache
from pathlib import Path

_VENDOR_DIR = Path(__file__).parent.parent / "assets" / "vendor"


@lru_cache(maxsize=None)
def _read_vendor_file(filename: str) -> str:
    path = _VENDOR_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Vendored library not found: {path}. Expected app/assets/vendor/{filename}."
        )
    return path.read_text(encoding="utf-8")


def three_js_source() -> str:
    """Return the vendored Three.js r128 source (MIT licensed)."""
    return _read_vendor_file("three.min.js")


def gsap_js_source() -> str:
    """Return the vendored GSAP 3.12 core source."""
    return _read_vendor_file("gsap.min.js")


def three_addons_source() -> str:
    """
    Return every vendored Three.js r128 addon module needed for realistic
    rendering (GLTFLoader for the real spacecraft model, plus the
    EffectComposer/RenderPass/UnrealBloomPass post-processing chain for
    real bloom), concatenated in their required dependency order:

    GLTFLoader has no cross-addon dependency. EffectComposer defines
    THREE.Pass/THREE.EffectComposer/THREE.FullScreenQuad, which
    RenderPass, ShaderPass, and UnrealBloomPass each extend, so it must
    come first. CopyShader and LuminosityHighPassShader are plain
    THREE.ShaderPass-compatible shader definitions UnrealBloomPass reads
    from, so they must precede it.
    """
    ordered_files = [
        "three-gltfloader.js",
        "three-effectcomposer.js",
        "three-renderpass.js",
        "three-copyshader.js",
        "three-luminosityshader.js",
        "three-shaderpass.js",
        "three-unrealbloompass.js",
    ]
    return "\n".join(_read_vendor_file(name) for name in ordered_files)
