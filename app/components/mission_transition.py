"""
AURA Mars — Mission Entry Transition

The short (~2.2s) cinematic played once, right after "ENTER THE MISSION"
is clicked: the spacecraft accelerates, starfield streaks into a warp
tunnel, Mars grows in frame, then the screen fades to black. Streamlit
has no client-to-server event bridge for a plain st.iframe, so this
can't be a single continuous WebGL scene handed off into the dashboard
render — it's an honest two-stage transition instead: this animation
plays out fully client-side while the Python side sleeps for the same
duration (see app/app.py), then reruns into the dashboard.

TRANSITION_SECONDS is shared with app.py's sleep duration so the two
can't drift out of sync.
"""

import streamlit as st

from app.components.planet_textures import PLANET_BUILDER_JS, mars_uri
from app.components.vendor_libs import three_addons_source, three_js_source

TRANSITION_SECONDS = 2.2

_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { width: 100%; height: 100%; overflow: hidden; background: #000; }
  #scene-root { position: fixed; inset: 0; }
  canvas { display: block; }
  #fade {
    position: fixed; inset: 0; background: #000; opacity: 0;
    pointer-events: none;
    animation: fadeOut 0.5s ease-in 1.7s forwards;
  }
  @keyframes fadeOut { from { opacity: 0; } to { opacity: 1; } }
  #label {
    position: fixed; left: 24px; bottom: 24px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase;
    color: #7FE3EE; opacity: 0.85;
  }
</style>
</head>
<body>
  <div id="scene-root"></div>
  <div id="fade"></div>
  <div id="label">TRANS-MARS INJECTION — BURN INITIATED</div>
<script>__THREE_JS__</script>
<script>__THREE_ADDONS_JS__</script>
<script>__PLANET_BUILDER_JS__</script>
<script>
(function () {
  var root = document.getElementById('scene-root');
  var scene = new THREE.Scene();
  var camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.05, 100);
  camera.position.set(0, 0, 4);

  var renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setClearColor(0x000000, 1);
  auraApplyCinematicRenderer(renderer, 1.1);
  root.appendChild(renderer.domElement);

  // Selective bloom: only Mars' atmospheric rim and the spacecraft's
  // thruster highlight glow; the spacecraft body and Mars' surface render
  // at normal exposure (see AURA_BLOOM_LAYER in planet_textures.py).
  var bloom = auraSetupSelectiveBloom(renderer, scene, camera, 0.9, 0.45, 0.15);

  scene.add(new THREE.AmbientLight(0x30354a, 0.55));
  var sunLight = new THREE.DirectionalLight(0xfff2df, 2.2);
  sunLight.position.set(3, 2, 4);
  scene.add(sunLight);

  // --- Warp starfield: particles streak past as the camera accelerates ---
  var STAR_COUNT = 1400;
  var geo = new THREE.BufferGeometry();
  var positions = new Float32Array(STAR_COUNT * 3);
  for (var i = 0; i < STAR_COUNT; i++) {
    positions[i * 3] = (Math.random() - 0.5) * 30;
    positions[i * 3 + 1] = (Math.random() - 0.5) * 30;
    positions[i * 3 + 2] = -Math.random() * 60;
  }
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  var starMat = new THREE.PointsMaterial({ color: 0xffffff, size: 0.05, transparent: true, opacity: 0.9 });
  var stars = new THREE.Points(geo, starMat);
  scene.add(stars);

  // --- Mars, growing as the camera approaches (real texture, see ATTRIBUTION in Python) ---
  var marsBody = auraBuildMars(0.9, '__MARS_TEX__');
  marsBody.glow.layers.enable(AURA_BLOOM_LAYER);
  var mars = marsBody.group;
  mars.position.set(0.4, 0, -14);
  scene.add(mars);

  // --- Spacecraft accelerating ahead of the camera: real GLTF model,
  // primitive fallback if it fails to load ---
  var craft = auraLoadSpacecraft(2.6, function (group) {
    var thruster = auraGlowSprite('#7fe3ee', 0.62, 0.85);
    thruster.position.set(-0.42, 0, 0);
    thruster.layers.enable(AURA_BLOOM_LAYER);
    group.add(thruster);
  });
  craft.rotation.y = Math.PI / 2; // point nose toward -Z, the direction of travel
  craft.position.set(0, 0, 1.2);
  scene.add(craft);

  var clock = new THREE.Clock();
  var speed = 2.0;
  function animate() {
    requestAnimationFrame(animate);
    var dt = clock.getDelta();
    var t = clock.getElapsedTime();
    speed += dt * 14.0; // accelerating burn

    var pos = geo.attributes.position.array;
    for (var i = 0; i < STAR_COUNT; i++) {
      pos[i * 3 + 2] += dt * speed;
      if (pos[i * 3 + 2] > 4) { pos[i * 3 + 2] = -60; }
    }
    geo.attributes.position.needsUpdate = true;

    craft.position.z = 1.2 - t * 0.3;
    craft.position.y = Math.sin(t * 3) * 0.02;
    mars.position.z = -14 + t * 3.4;
    mars.rotation.y = t * 0.3;
    camera.fov = 60 + Math.min(t * 6, 18);
    camera.updateProjectionMatrix();

    bloom.render();
  }
  animate();

  window.addEventListener('resize', function () {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
    bloom.setSize(window.innerWidth, window.innerHeight);
  });
})();
</script>
</body>
</html>
"""


def render_transition_scene(height: int = 640) -> None:
    """Render the ~2.2s spacecraft-accelerates-toward-Mars transition scene."""
    html = (
        _TEMPLATE
        .replace("__THREE_JS__", three_js_source())
        .replace("__THREE_ADDONS_JS__", three_addons_source())
        .replace("__PLANET_BUILDER_JS__", PLANET_BUILDER_JS)
        .replace("__MARS_TEX__", mars_uri())
    )
    st.iframe(html, height=height)
