"""
AURA Mars — Journey to Mars: Three.js Hero Scene

A 3D Sun/Earth/Mars/spacecraft scene rendered in Three.js instead of
Plotly, for the "hero" module. Critically: **no orbital physics is
computed in JavaScript.** Every position the spacecraft, Earth, and
Mars occupy at every animation frame is precomputed in Python by the
exact same, already-validated Kepler-equation solver used by the
original Plotly simulation (app/components/journey_scene.py —
_solve_kepler / _true_anomaly_and_radius, reused here, not
reimplemented) and handed to the JS scene as a JSON array of frames.
The JavaScript side only interpolates between/steps through those real
numbers and draws them — it never derives a trajectory itself.

Telemetry shown (transfer type, transfer duration, phase angle,
mission day) all reads from src.orbital_mechanics / the precomputed
frames — nothing is a hard-coded visual placeholder.
"""

import json
import math

import streamlit as st

from app.components.journey_scene import _solve_kepler, _true_anomaly_and_radius
from app.components.planet_textures import (
    ATTRIBUTION,
    PLANET_BUILDER_JS,
    earth_clouds_uri,
    earth_daymap_uri,
    earth_night_uri,
    earth_normal_uri,
    earth_specular_uri,
    mars_uri,
    sun_uri,
)
from app.components.vendor_libs import three_addons_source, three_js_source
from src.orbital_mechanics import (
    R_EARTH_AU,
    R_MARS_AU,
    A_TRANSFER_AU,
    E_TRANSFER,
    TRANSFER_DAYS,
    LAUNCH_PHASE_ANGLE_DEG,
    EARTH_PERIOD_DAYS,
    MARS_PERIOD_DAYS,
    get_journey_facts,
)

_N_FRAMES = 140
_OMEGA_EARTH = 360.0 / EARTH_PERIOD_DAYS
_OMEGA_MARS = 360.0 / MARS_PERIOD_DAYS

# Visual scale: orbit radii are exaggerated for on-screen visibility, but
# the RATIO between them is kept exactly real (Mars really is R_MARS_AU /
# R_EARTH_AU times farther out than Earth) rather than picked arbitrarily.
_SCENE_UNITS_PER_AU = 4.2


def _compute_frames():
    """
    Precompute every animation frame's real body positions, in AU,
    using the exact Kepler-equation solver already validated in
    app/components/journey_scene.py. Returns a list of dicts, JSON-ready.
    """
    import numpy as np

    frames = []
    for i in range(_N_FRAMES + 1):
        t_days = TRANSFER_DAYS * (i / _N_FRAMES)

        earth_ang = math.radians(_OMEGA_EARTH * t_days)
        mars_ang = math.radians(LAUNCH_PHASE_ANGLE_DEG) + math.radians(_OMEGA_MARS * t_days)
        earth_pos = (R_EARTH_AU * math.cos(earth_ang), R_EARTH_AU * math.sin(earth_ang))
        mars_pos = (R_MARS_AU * math.cos(mars_ang), R_MARS_AU * math.sin(mars_ang))

        mean_anom = np.array([math.pi * (t_days / TRANSFER_DAYS)])
        nu, r = _true_anomaly_and_radius(mean_anom, A_TRANSFER_AU, E_TRANSFER)
        craft_ang = float(nu[0])
        craft_pos = (float(r[0]) * math.cos(craft_ang), float(r[0]) * math.sin(craft_ang))

        frames.append({
            "day": round(t_days, 1),
            "earth": [earth_pos[0], earth_pos[1]],
            "mars": [mars_pos[0], mars_pos[1]],
            "craft": [craft_pos[0], craft_pos[1]],
        })
    return frames


def _compute_transfer_path():
    """Static transfer-ellipse points, for the dashed trajectory line — same real geometry as journey_scene.py."""
    points = []
    for i in range(121):
        nu = math.pi * i / 120
        r = A_TRANSFER_AU * (1 - E_TRANSFER ** 2) / (1 + E_TRANSFER * math.cos(nu))
        points.append([r * math.cos(nu), r * math.sin(nu)])
    return points


_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { width: 100%; height: 100%; overflow: hidden; background: #050710; }
  #scene-root { position: absolute; inset: 0; }
  canvas { display: block; }

  #hud {
    position: absolute; top: 16px; left: 16px;
    display: flex;
    gap: 10px;
  }
  .hud-item {
    font-family: 'JetBrains Mono', monospace;
    color: #E9EEF5;
    background: rgba(9, 11, 16, 0.6);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    border: 1px solid rgba(77, 216, 232, 0.22);
    border-radius: 8px;
    padding: 9px 16px;
    box-shadow: 0 4px 18px rgba(0,0,0,0.35);
  }
  .hud-item .l { font-size: 9.5px; letter-spacing: 0.1em; text-transform: uppercase; color: #4DD8E8; }
  .hud-item .v { font-size: 15px; font-weight: 600; margin-top: 3px; font-variant-numeric: tabular-nums; }

  #controls {
    position: absolute; bottom: 16px; left: 16px;
    display: flex; gap: 8px;
  }
  #controls button {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase;
    background: rgba(26, 34, 48, 0.8);
    color: #E9EEF5;
    border: 1px solid rgba(77, 216, 232, 0.3);
    border-radius: 6px;
    padding: 8px 14px;
    cursor: pointer;
  }
  #controls button:hover { border-color: #4DD8E8; color: #4DD8E8; }

  #legend {
    position: absolute; bottom: 16px; right: 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10.5px; color: #929CAA;
    background: rgba(9, 11, 16, 0.5);
    border: 1px solid rgba(43, 55, 72, 0.6);
    border-radius: 8px;
    padding: 8px 12px;
    line-height: 1.7;
  }
  #legend span { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
</style>
</head>
<body>
  <div id="scene-root"></div>
  <div id="hud">
    <div class="hud-item"><div class="l">Transfer Type</div><div class="v">Hohmann</div></div>
    <div class="hud-item"><div class="l">Duration</div><div class="v">__TRANSFER_DAYS__ d</div></div>
    <div class="hud-item"><div class="l">Phase Angle</div><div class="v">__PHASE_ANGLE__°</div></div>
    <div class="hud-item"><div class="l">Mission Day</div><div class="v" id="day-readout">0.0</div></div>
  </div>
  <div id="controls">
    <button id="btn-play">▶ Play</button>
    <button id="btn-pause">⏸ Pause</button>
    <button id="btn-restart">⟲ Restart</button>
  </div>
  <div id="legend">
    <div><span style="background:#3E8EDE"></span>Earth</div>
    <div><span style="background:#D9683A"></span>Mars</div>
    <div><span style="background:#E9EEF5"></span>Spacecraft</div>
  </div>

<script>__THREE_JS__</script>
<script>__THREE_ADDONS_JS__</script>
<script>__PLANET_BUILDER_JS__</script>
<script>
(function () {
  var FRAMES = __FRAMES_JSON__;
  var TRANSFER_PATH = __TRANSFER_PATH_JSON__;
  var SCALE = __SCENE_SCALE__;

  var root = document.getElementById('scene-root');
  var scene = new THREE.Scene();
  var camera = new THREE.PerspectiveCamera(48, window.innerWidth / window.innerHeight, 0.1, 200);
  camera.position.set(0, 9, 11);
  camera.lookAt(0, 0, 0);

  var renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setClearColor(0x050710, 1);
  auraApplyCinematicRenderer(renderer, 1.05);
  root.appendChild(renderer.domElement);

  // Selective bloom: only the Sun and the thin atmospheric-rim shells glow;
  // planet surfaces and the spacecraft body render at normal exposure so
  // their real textures stay readable (see AURA_BLOOM_LAYER in
  // planet_textures.py).
  var bloom = auraSetupSelectiveBloom(renderer, scene, camera, 0.9, 0.5, 0.15);

  // One dominant light source — the Sun itself, as a point light at the
  // origin — with a low ambient fill so the far side of each body reads as
  // dim rather than glowing.
  scene.add(new THREE.AmbientLight(0x40465c, 0.5));
  var sunLight = new THREE.PointLight(0xfff2df, 2.6, 80);
  sunLight.position.set(0, 0, 0);
  scene.add(sunLight);

  scene.add(auraBuildStarfield());

  // --- Sun, Earth, Mars: real NASA-derived textures (see ATTRIBUTION in Python) ---
  var sunBody = auraBuildSun(0.55, '__SUN_TEX__');
  sunBody.mesh.layers.enable(AURA_BLOOM_LAYER);
  sunBody.glow.layers.enable(AURA_BLOOM_LAYER);
  sunBody.corona.layers.enable(AURA_BLOOM_LAYER);
  scene.add(sunBody.group);

  var earthBody = auraBuildEarth(
    0.28, '__EARTH_TEX__', '__EARTH_NIGHT_TEX__', '__EARTH_NORMAL_TEX__', '__EARTH_SPEC_TEX__', '__EARTH_CLOUDS_TEX__'
  );
  earthBody.glow.layers.enable(AURA_BLOOM_LAYER);
  scene.add(earthBody.group);

  var marsBody = auraBuildMars(0.22, '__MARS_TEX__');
  marsBody.glow.layers.enable(AURA_BLOOM_LAYER);
  scene.add(marsBody.group);

  // --- Spacecraft: real GLTF model (NASA MRO), primitive fallback if the
  // model ever fails to load ---
  var craft = auraLoadSpacecraft(1.0, function (group) {
    var thruster = auraGlowSprite('#7fe3ee', 0.24, 0.85);
    thruster.position.set(-0.16, 0, 0);
    thruster.layers.enable(AURA_BLOOM_LAYER);
    group.add(thruster);
  });
  scene.add(craft);

  // --- Orbit rings (built from the same real radii as the bodies below) ---
  function orbitRing(radiusAU, color) {
    var pts = [];
    for (var a = 0; a <= 128; a++) {
      var ang = (a / 128) * Math.PI * 2;
      pts.push(new THREE.Vector3(Math.cos(ang) * radiusAU * SCALE, 0, -Math.sin(ang) * radiusAU * SCALE));
    }
    var geo = new THREE.BufferGeometry().setFromPoints(pts);
    return new THREE.Line(geo, new THREE.LineBasicMaterial({ color: color, transparent: true, opacity: 0.35 }));
  }
  scene.add(orbitRing(__R_EARTH_AU__, 0x3A4457));
  scene.add(orbitRing(__R_MARS_AU__, 0x3A4457));

  // --- Transfer trajectory (real Hohmann ellipse points from Python) ---
  var transferPts = TRANSFER_PATH.map(function (p) {
    return new THREE.Vector3(p[0] * SCALE, 0, -p[1] * SCALE);
  });
  var transferGeo = new THREE.BufferGeometry().setFromPoints(transferPts);
  var transferLine = new THREE.Line(transferGeo, new THREE.LineDashedMaterial({ color: 0x62D49B, dashSize: 0.15, gapSize: 0.08, transparent: true, opacity: 0.85 }));
  transferLine.computeLineDistances();
  scene.add(transferLine);

  function setPos(group, xy) {
    group.position.set(xy[0] * SCALE, 0, -xy[1] * SCALE);
  }
  var earth = earthBody.group, mars = marsBody.group;

  // --- Playback state (steps through the precomputed real frames) ---
  var frameIndex = 0;
  var playing = false;
  var lastTick = 0;
  var dayReadout = document.getElementById('day-readout');

  function renderFrame(i) {
    var f = FRAMES[i];
    setPos(earth, f.earth);
    setPos(mars, f.mars);
    setPos(craft, f.craft);
    dayReadout.textContent = f.day.toFixed(1);
  }
  renderFrame(0);

  document.getElementById('btn-play').addEventListener('click', function () { playing = true; });
  document.getElementById('btn-pause').addEventListener('click', function () { playing = false; });
  document.getElementById('btn-restart').addEventListener('click', function () { frameIndex = 0; playing = false; renderFrame(0); });

  var clock = new THREE.Clock();
  var elapsed = 0;
  function animate() {
    requestAnimationFrame(animate);
    // Exactly one clock read per frame: THREE.Clock.getElapsedTime() calls
    // getDelta() internally, so also calling getDelta() again below (as
    // this used to) reset the clock's internal oldTime a moment earlier —
    // every subsequent getDelta() then measured only the sub-millisecond
    // gap between the two calls, never accumulating past the 0.045s
    // playback threshold. That's why Play never visibly advanced anything.
    var dt = clock.getDelta();
    elapsed += dt;
    var t = elapsed;

    if (playing) {
      lastTick += dt;
      if (lastTick > 0.045) {
        lastTick = 0;
        frameIndex = (frameIndex + 1) % FRAMES.length;
        renderFrame(frameIndex);
        if (frameIndex === FRAMES.length - 1) { playing = false; }
      }
    }

    earthBody.mesh.rotation.y = t * 0.4;
    earthBody.clouds.rotation.y = t * 0.46;
    marsBody.mesh.rotation.y = t * 0.35;
    sunBody.mesh.rotation.y = t * 0.08;
    camera.position.x = Math.sin(t * 0.03) * 1.0;
    camera.lookAt(0, 0, 0);

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


def render_journey_3d(height: int = 620) -> None:
    """Render the Three.js Journey to Mars hero scene, fed by real orbital mechanics."""
    frames = _compute_frames()
    transfer_path = _compute_transfer_path()
    facts = get_journey_facts()

    html = (
        _TEMPLATE
        .replace("__THREE_JS__", three_js_source())
        .replace("__THREE_ADDONS_JS__", three_addons_source())
        .replace("__PLANET_BUILDER_JS__", PLANET_BUILDER_JS)
        .replace("__SUN_TEX__", sun_uri())
        .replace("__EARTH_TEX__", earth_daymap_uri())
        .replace("__EARTH_NIGHT_TEX__", earth_night_uri())
        .replace("__EARTH_NORMAL_TEX__", earth_normal_uri())
        .replace("__EARTH_SPEC_TEX__", earth_specular_uri())
        .replace("__EARTH_CLOUDS_TEX__", earth_clouds_uri())
        .replace("__MARS_TEX__", mars_uri())
        .replace("__FRAMES_JSON__", json.dumps(frames))
        .replace("__TRANSFER_PATH_JSON__", json.dumps(transfer_path))
        .replace("__SCENE_SCALE__", json.dumps(_SCENE_UNITS_PER_AU))
        .replace("__R_EARTH_AU__", json.dumps(R_EARTH_AU))
        .replace("__R_MARS_AU__", json.dumps(R_MARS_AU))
        .replace("__TRANSFER_DAYS__", f"{facts.transfer_days:.0f}")
        .replace("__PHASE_ANGLE__", f"{facts.launch_phase_angle_deg:.0f}")
    )
    st.iframe(html, height=height)
    st.caption(ATTRIBUTION)
