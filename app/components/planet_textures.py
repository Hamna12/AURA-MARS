"""
AURA Mars — Real Planet Textures, Static Asset URLs & Shared Three.js
Scene-Building Toolkit

Real NASA-derived imagery and models, not procedural placeholders:
    - Earth day/night/normal/specular/cloud maps: from the Three.js
      project's own repo examples (MIT-licensed, NASA Blue
      Marble/Black Marble-derived).
    - Mars and Sun color maps: Solar System Scope
      (https://www.solarsystemscope.com/textures/), CC BY 4.0,
      NASA-imagery-derived. Attribution is required by that license —
      see ATTRIBUTION below, surfaced in the UI wherever these assets
      are used (Journey to Mars tab, landing scene, mission transition).
    - Spacecraft: a real NASA Mars Reconnaissance Orbiter glTF model
      (nasa/NASA-3D-Resources, public domain), served from
      app/static/ (see SPACECRAFT_GLB_URL) rather than inlined — too
      large to sensibly inline as base64 the way the textures below
      are. Loaded client-side via THREE.GLTFLoader with a primitive-
      geometry fallback if the load ever fails (see
      auraLoadSpacecraft in PLANET_BUILDER_JS).
    - Landing sequence opening video: real NASA "Earth from Orbit
      2014" footage (public domain), also static-served — see
      EARTH_ORBIT_VIDEO_URL.

The five Earth/Mars/Sun texture images are downsized locally (1024x512
or 768x384, JPEG) to keep the app responsive, then inlined as base64
data URIs here for the same reason fonts and vendored JS are inlined
elsewhere in this project: st.iframe renders a fully self-contained
document with no access to the app's own static file paths for small
embedded assets. The GLB and MP4 are the two exceptions — large enough
that inlining them would bloat every scene's HTML payload, so they're
served instead via Streamlit's static-file route (configured in
.streamlit/config.toml) and referenced by absolute URL from inside the
iframe. That works because Streamlit's st.iframe sandbox includes
`allow-same-origin`, so a srcdoc iframe's relative/absolute-path
requests resolve against the real app origin, not a null origin.

This module also provides PLANET_BUILDER_JS: a shared block of
JavaScript reused by every 3D scene in the app (landing, transition,
Journey to Mars) instead of duplicating shader/material/loader code
three times — real day/night Earth material, Mars terrain + haze,
an emissive/bloom-ready Sun, a multi-layer parallax starfield with a
faint Milky Way band, the GLTFLoader-based spacecraft loader (with
fallback to the original primitive-geometry builder), and a bloom
post-processing pipeline helper (EffectComposer + RenderPass +
UnrealBloomPass).
"""

import base64
from functools import lru_cache
from pathlib import Path

_TEXTURE_DIR = Path(__file__).parent.parent / "assets" / "textures"

ATTRIBUTION = (
    "Earth/Mars/Sun imagery: NASA-derived textures via three.js and "
    "Solar System Scope (solarsystemscope.com/textures), CC BY 4.0. "
    "Spacecraft model and orbital footage: NASA (public domain)."
)

# Served by Streamlit's static-file route (app/static/ -> /app/static/*,
# enabled in .streamlit/config.toml) rather than inlined — see module
# docstring for why.
SPACECRAFT_GLB_URL = "/app/static/mro_spacecraft.glb"
EARTH_ORBIT_VIDEO_URL = "/app/static/earth_orbit.mp4"


@lru_cache(maxsize=None)
def _data_uri(filename: str, mime: str = "image/jpeg") -> str:
    path = _TEXTURE_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Texture not found: {path}")
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def earth_daymap_uri() -> str:
    return _data_uri("earth_daymap.jpg")


def earth_night_uri() -> str:
    return _data_uri("earth_night.jpg")


def earth_normal_uri() -> str:
    return _data_uri("earth_normal.jpg")


def earth_specular_uri() -> str:
    return _data_uri("earth_specular.jpg")


def earth_clouds_uri() -> str:
    return _data_uri("earth_clouds.jpg")


def mars_uri() -> str:
    return _data_uri("mars.jpg")


def sun_uri() -> str:
    return _data_uri("sun.jpg")


# ---------------------------------------------------------------------------
# Shared Three.js scene-building toolkit — inlined verbatim into every
# scene that needs it. Requires THREE plus the addon modules loaded by
# vendor_libs.three_addons_source() (GLTFLoader, EffectComposer,
# RenderPass, ShaderPass, UnrealBloomPass and its shader dependencies)
# to already be present as globals before this script runs.
# ---------------------------------------------------------------------------
PLANET_BUILDER_JS = r"""
function auraFresnelMaterial(color, intensity) {
  return new THREE.ShaderMaterial({
    uniforms: { glowColor: { value: new THREE.Color(color) }, glowIntensity: { value: intensity } },
    vertexShader: [
      'varying float auraIntensity;',
      'void main() {',
      '  vec3 vNormal = normalize(normalMatrix * normal);',
      '  vec3 vNormel = normalize((modelViewMatrix * vec4(position, 1.0)).xyz);',
      '  auraIntensity = pow(0.68 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 3.0);',
      '  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);',
      '}'
    ].join('\n'),
    fragmentShader: [
      'varying float auraIntensity;',
      'uniform vec3 glowColor;',
      'uniform float glowIntensity;',
      'void main() {',
      '  gl_FragColor = vec4(glowColor, clamp(auraIntensity, 0.0, 1.0) * glowIntensity);',
      '}'
    ].join('\n'),
    side: THREE.BackSide,
    blending: THREE.AdditiveBlending,
    transparent: true,
    depthWrite: false,
  });
}

function auraGlowSprite(colorHex, scale, opacity) {
  var c = document.createElement('canvas');
  c.width = c.height = 128;
  var ctx = c.getContext('2d');
  var g = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
  g.addColorStop(0, colorHex + 'ff');
  g.addColorStop(0.4, colorHex + '55');
  g.addColorStop(1, colorHex + '00');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 128, 128);
  var tex = new THREE.CanvasTexture(c);
  var mat = new THREE.SpriteMaterial({
    map: tex, transparent: true, opacity: opacity, depthWrite: false, blending: THREE.AdditiveBlending
  });
  var sprite = new THREE.Sprite(mat);
  sprite.scale.set(scale, scale, 1);
  return sprite;
}

function auraBuildStarLayer(count, spread, size, colorHex, opacity) {
  var geo = new THREE.BufferGeometry();
  var positions = new Float32Array(count * 3);
  for (var i = 0; i < count; i++) {
    positions[i * 3] = (Math.random() - 0.5) * spread;
    positions[i * 3 + 1] = (Math.random() - 0.5) * spread;
    positions[i * 3 + 2] = (Math.random() - 0.5) * spread;
  }
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  var mat = new THREE.PointsMaterial({
    color: colorHex, size: size, transparent: true, opacity: opacity, sizeAttenuation: true
  });
  return new THREE.Points(geo, mat);
}

// Three depth layers, no background plane/quad of any kind — just point
// sprites. Deliberately understated (small sizes, moderate opacity) so it
// reads as a sky full of stars rather than a scattering of bright dots.
function auraBuildStarfield() {
  var group = new THREE.Group();
  group.add(auraBuildStarLayer(1600, 160, 0.075, 0xffffff, 0.55));
  group.add(auraBuildStarLayer(900, 110, 0.05, 0x9fb4c9, 0.4));
  group.add(auraBuildStarLayer(350, 70, 0.035, 0xffe8c8, 0.32));
  return group;
}

function auraBuildEarth(radius, dayUri, nightUri, normalUri, specUri, cloudsUri) {
  var loader = new THREE.TextureLoader();
  var group = new THREE.Group();

  var dayTex = loader.load(dayUri);
  dayTex.encoding = THREE.sRGBEncoding;
  var nightTex = loader.load(nightUri);
  nightTex.encoding = THREE.sRGBEncoding;
  var normalTex = loader.load(normalUri);
  var specTex = loader.load(specUri);

  var mesh = new THREE.Mesh(
    new THREE.SphereGeometry(radius, 64, 64),
    new THREE.MeshPhongMaterial({
      map: dayTex,
      normalMap: normalTex,
      normalScale: new THREE.Vector2(0.55, 0.55),
      specularMap: specTex,
      specular: new THREE.Color(0x2c3644),
      shininess: 10,
      // Kept low: emissiveMap adds unconditionally across the whole
      // sphere (three.js has no automatic day/night masking on
      // emissive), so this is deliberately faint — just enough for
      // night-side city lights to read as present, not enough to
      // lift the sunlit hemisphere's exposure.
      emissiveMap: nightTex,
      emissive: new THREE.Color(0xffffff),
      emissiveIntensity: 0.35,
    })
  );
  group.add(mesh);

  var cloudsTex = loader.load(cloudsUri);
  var clouds = new THREE.Mesh(
    new THREE.SphereGeometry(radius * 1.012, 64, 64),
    new THREE.MeshLambertMaterial({
      color: 0xffffff,
      alphaMap: cloudsTex,
      transparent: true,
      opacity: 0.6,
      depthWrite: false,
    })
  );
  group.add(clouds);

  // Atmospheric rim only — a separate thin shell, not the surface itself,
  // so it can be selectively bloomed without blowing out the planet's
  // texture (see auraSetupSelectiveBloom / AURA_BLOOM_LAYER below).
  var glow = new THREE.Mesh(new THREE.SphereGeometry(radius * 1.1, 32, 32), auraFresnelMaterial(0x6fb8ff, 0.55));
  group.add(glow);

  return { group: group, mesh: mesh, clouds: clouds, glow: glow };
}

function auraBuildMars(radius, marsUri) {
  var loader = new THREE.TextureLoader();
  var group = new THREE.Group();

  var marsTex = loader.load(marsUri);
  marsTex.encoding = THREE.sRGBEncoding;

  var mesh = new THREE.Mesh(
    new THREE.SphereGeometry(radius, 56, 56),
    new THREE.MeshPhongMaterial({ map: marsTex, shininess: 2, specular: new THREE.Color(0x140b08) })
  );
  group.add(mesh);

  var haze = new THREE.Mesh(new THREE.SphereGeometry(radius * 1.04, 40, 40), auraFresnelMaterial(0xd9a06a, 0.3));
  group.add(haze);
  var glow = new THREE.Mesh(new THREE.SphereGeometry(radius * 1.09, 28, 28), auraFresnelMaterial(0xe2794a, 0.35));
  group.add(glow);

  return { group: group, mesh: mesh, glow: glow };
}

function auraBuildSun(radius, sunUri) {
  var loader = new THREE.TextureLoader();
  var group = new THREE.Group();

  var sunTex = loader.load(sunUri);
  sunTex.encoding = THREE.sRGBEncoding;

  var mesh = new THREE.Mesh(
    new THREE.SphereGeometry(radius, 48, 48),
    new THREE.MeshBasicMaterial({ map: sunTex, color: new THREE.Color(0xfff4d6) })
  );
  group.add(mesh);

  var glow = new THREE.Mesh(new THREE.SphereGeometry(radius * 1.3, 24, 24), auraFresnelMaterial(0xffd27a, 1.1));
  group.add(glow);

  var corona = auraGlowSprite('#ffd27a', radius * 4.5, 0.4);
  group.add(corona);

  return { group: group, mesh: mesh, glow: glow, corona: corona };
}

function auraBuildSpacecraft(scale) {
  var group = new THREE.Group();
  var hullMat = new THREE.MeshPhongMaterial({ color: 0xd7dde6, shininess: 75, specular: 0x888888 });
  var darkMat = new THREE.MeshPhongMaterial({ color: 0x2a2f3a, shininess: 40 });
  var panelMat = new THREE.MeshPhongMaterial({ color: 0x1c3a5e, shininess: 90, emissive: 0x08172a });

  var hull = new THREE.Mesh(new THREE.CylinderGeometry(0.032 * scale, 0.05 * scale, 0.22 * scale, 10), hullMat);
  hull.rotation.z = Math.PI / 2;
  group.add(hull);

  var nose = new THREE.Mesh(new THREE.ConeGeometry(0.032 * scale, 0.09 * scale, 10), darkMat);
  nose.rotation.z = -Math.PI / 2;
  nose.position.x = 0.155 * scale;
  group.add(nose);

  var panelGeo = new THREE.BoxGeometry(0.16 * scale, 0.012 * scale, 0.05 * scale);
  var panelL = new THREE.Mesh(panelGeo, panelMat);
  panelL.position.set(-0.02 * scale, 0.11 * scale, 0);
  var panelR = new THREE.Mesh(panelGeo, panelMat);
  panelR.position.set(-0.02 * scale, -0.11 * scale, 0);
  group.add(panelL, panelR);

  var strutGeo = new THREE.CylinderGeometry(0.004 * scale, 0.004 * scale, 0.09 * scale, 6);
  var strutL = new THREE.Mesh(strutGeo, darkMat);
  strutL.rotation.x = Math.PI / 2;
  strutL.position.set(-0.02 * scale, 0.055 * scale, 0);
  var strutR = strutL.clone();
  strutR.position.set(-0.02 * scale, -0.055 * scale, 0);
  group.add(strutL, strutR);

  return group;
}

function auraLoadSpacecraft(scale, onReady) {
  var group = new THREE.Group();
  var settled = false;

  function useFallback() {
    if (settled) return;
    settled = true;
    var craft = auraBuildSpacecraft(scale);
    group.add(craft);
    if (onReady) onReady(group, false);
  }

  try {
    var loader = new THREE.GLTFLoader();
    loader.load(
      '/app/static/mro_spacecraft.glb',
      function (gltf) {
        if (settled) return;
        settled = true;
        var model = gltf.scene;
        var box = new THREE.Box3().setFromObject(model);
        var size = new THREE.Vector3();
        box.getSize(size);
        var maxDim = Math.max(size.x, size.y, size.z) || 1;
        var center = new THREE.Vector3();
        box.getCenter(center);
        model.position.sub(center);

        var normalized = new THREE.Group();
        normalized.add(model);
        // 0.3x matches auraBuildSpacecraft's approximate envelope at the
        // same "scale" argument, so already-tuned camera/composition math
        // stays valid whichever path loads.
        var targetSize = scale * 0.3;
        var factor = targetSize / maxDim;
        normalized.scale.setScalar(factor);
        group.add(normalized);

        if (onReady) onReady(group, true);
      },
      undefined,
      useFallback
    );
  } catch (e) {
    useFallback();
  }

  return group;
}

// ---------------------------------------------------------------------------
// Selective bloom: only objects explicitly placed on AURA_BLOOM_LAYER glow
// (the Sun, atmospheric rims, small thruster highlights). Everything else —
// planet surfaces, the spacecraft body, UI — renders at normal exposure
// with its texture detail intact. This replaces a flat, whole-frame bloom
// pass, which bloomed every bright pixel indiscriminately (lit planet
// surfaces, the spacecraft's light-colored hull) and made them look
// overexposed instead of textured and readable.
//
// Technique: render the scene twice. Pass 1 temporarily swaps every
// non-bloom-layer mesh's material for flat black, renders through a real
// UnrealBloomPass to get an isolated, blurred "glow-only" image, then
// restores the real materials. Pass 2 renders the scene normally. A small
// combine shader adds the glow image on top of the normal render. This is
// the standard three.js "selective bloom" pattern (see the engine's own
// webgl_postprocessing_unreal_bloom_selective example) — call
// `mesh.layers.enable(AURA_BLOOM_LAYER)` on exactly the meshes that should
// glow (never on planet surface or spacecraft body meshes).
// ---------------------------------------------------------------------------
var AURA_BLOOM_LAYER = 1;
var _auraBloomLayers = new THREE.Layers();
_auraBloomLayers.set(AURA_BLOOM_LAYER);
var _auraDarkMaterial = new THREE.MeshBasicMaterial({ color: 0x000000 });
var _auraMatCache = {};

function _auraDarkenNonBloomed(obj) {
  if (obj.isMesh && _auraBloomLayers.test(obj.layers) === false) {
    _auraMatCache[obj.uuid] = obj.material;
    obj.material = _auraDarkMaterial;
  }
}
function _auraRestoreMaterial(obj) {
  if (_auraMatCache[obj.uuid]) {
    obj.material = _auraMatCache[obj.uuid];
    delete _auraMatCache[obj.uuid];
  }
}

function auraSetupSelectiveBloom(renderer, scene, camera, strength, radius, threshold) {
  var renderScene = new THREE.RenderPass(scene, camera);

  var bloomPass = new THREE.UnrealBloomPass(
    new THREE.Vector2(window.innerWidth, window.innerHeight), strength, radius, threshold
  );

  var bloomComposer = new THREE.EffectComposer(renderer);
  bloomComposer.renderToScreen = false;
  bloomComposer.addPass(renderScene);
  bloomComposer.addPass(bloomPass);

  var mixMaterial = new THREE.ShaderMaterial({
    uniforms: {
      baseTexture: { value: null },
      bloomTexture: { value: bloomComposer.renderTarget2.texture }
    },
    vertexShader: [
      'varying vec2 vUv;',
      'void main() {',
      '  vUv = uv;',
      '  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);',
      '}'
    ].join('\n'),
    fragmentShader: [
      'uniform sampler2D baseTexture;',
      'uniform sampler2D bloomTexture;',
      'varying vec2 vUv;',
      'void main() {',
      '  gl_FragColor = texture2D(baseTexture, vUv) + vec4(1.0) * texture2D(bloomTexture, vUv);',
      '}'
    ].join('\n'),
  });
  var mixPass = new THREE.ShaderPass(mixMaterial, 'baseTexture');
  mixPass.needsSwap = true;

  var finalComposer = new THREE.EffectComposer(renderer);
  finalComposer.addPass(renderScene);
  finalComposer.addPass(mixPass);

  function render() {
    scene.traverse(_auraDarkenNonBloomed);
    bloomComposer.render();
    scene.traverse(_auraRestoreMaterial);
    finalComposer.render();
  }

  function setSize(w, h) {
    bloomComposer.setSize(w, h);
    finalComposer.setSize(w, h);
  }

  return { render: render, setSize: setSize, bloomPass: bloomPass };
}

function auraApplyCinematicRenderer(renderer, exposure) {
  renderer.outputEncoding = THREE.sRGBEncoding;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = exposure || 1.0;
}
"""
