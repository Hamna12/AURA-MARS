"""
AURA Mars — Mission Planner Calculations

Deterministic, source-grounded calculations for four mission-planning
tools: the real Mars 2020 (Perseverance) entry-descent-landing sequence,
Earth-Mars communication delay, upcoming launch windows, and a rocket
equation / life-support consumables estimator.

Every number here is either:
    (a) sourced from real published NASA data (EDL timeline, consumables
        rates, launch history) — cited in comments, or
    (b) computed from real physics (Kepler's laws, the rocket equation,
        light-time delay) using inputs from (a).

Nothing here is invented. Where a figure is illustrative rather than a
specific real mission's design (e.g. the reference vehicle in the
Delta-v calculator), that is labelled explicitly in the UI layer, not
just in this module.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional

from src.orbital_mechanics import (  # noqa: F401  (re-exported for convenience)
    AU_KM,
    R_EARTH_AU,
    R_MARS_AU,
    SYNODIC_PERIOD_DAYS,
    STRAIGHT_LINE_DISTANCE_MIN_KM,
    STRAIGHT_LINE_DISTANCE_MAX_KM,
)

SPEED_OF_LIGHT_KM_S = 299_792.458


# ===========================================================================
# 1. Entry, Descent & Landing — real Mars 2020 (Perseverance) sequence
# ===========================================================================
# Source-verified against multiple NASA/JPL materials (science.nasa.gov,
# mars.nasa.gov EDL pages, NASA press kit figures reported by
# spaceflightnow.com and others). Times are seconds relative to Entry
# Interface (E+0). Perseverance landed in Jezero Crater, 2021-02-18.

@dataclass
class EDLStage:
    name: str
    time_s: Optional[float]     # seconds relative to Entry Interface (E+0)
    time_label: str             # human-readable time label
    altitude_km: Optional[float] = None
    velocity_ms: Optional[float] = None
    note: str = ""


EDL_STAGES: List[EDLStage] = [
    EDLStage("Cruise Stage Separation", -600, "E − 10 min",
             note="Solar panels, fuel tanks, and radio antennas are jettisoned before atmospheric entry."),
    EDLStage("Entry Interface", 0, "E + 0 s", altitude_km=128.7, velocity_ms=5410,
             note="Spacecraft reaches the top of the Martian atmosphere at ~12,100 mph (19,500 km/h)."),
    EDLStage("Peak Heating", 80, "E + 80 s",
             note="Heat shield reaches roughly 1,300°C (2,370°F) from atmospheric friction."),
    EDLStage("Peak Deceleration", 90, "E + 90 s", velocity_ms=444,
             note="Deceleration g-forces peak; speed drops below ~1,600 km/h (1,000 mph)."),
    EDLStage("Parachute Deploy", 240, "E + 4 min", altitude_km=11.0, velocity_ms=420,
             note="A 21.5 m (70.5 ft) supersonic parachute deploys at ~940 mph (1,510 km/h)."),
    EDLStage("Heat Shield Separation", 260, "E + 4 min 20 s",
             note="Heat shield is released; the rover's landing radar can now sense the terrain below."),
    EDLStage("Radar-Guided Terrain Navigation", 350, "E + 5 min 50 s", altitude_km=4.2,
             note="Terrain-Relative Navigation compares camera images to onboard maps to pick a safe landing target."),
    EDLStage("Backshell Separation / Powered Descent", 355, "E + 5 min 55 s", altitude_km=2.1, velocity_ms=110,
             note="Backshell and parachute fall away; the descent stage ignites its eight engines."),
    EDLStage("Sky Crane Maneuver / Rover Separation", 405, "E + 6 min 45 s", altitude_km=0.0213, velocity_ms=0.75,
             note="The descent stage lowers the rover on cables ~6.4 m (21 ft) long."),
    EDLStage("Mobility Deploy", 407, "E + 6 min 47 s", altitude_km=0.0207, velocity_ms=0.75,
             note="The rover's wheels unfold into landing position while still on the cables."),
    EDLStage("Touchdown", 410, "E + 6 min 50 s", altitude_km=0.0, velocity_ms=0.75,
             note="Rover touches down softly in Jezero Crater — February 18, 2021."),
    EDLStage("Flyaway", 412, "E + 6 min 52 s",
             note="The descent stage cuts the cables and flies off to crash-land a safe distance away."),
]

EDL_SOURCE_MISSION = "Mars 2020 (Perseverance rover) — landed Jezero Crater, 2021-02-18"


# ===========================================================================
# 2. Communication delay (real physics: light-time delay)
# ===========================================================================

def one_way_delay_minutes(distance_km: float) -> float:
    """One-way radio signal delay for a given Earth-Mars distance."""
    return distance_km / SPEED_OF_LIGHT_KM_S / 60.0


@dataclass
class CommDelayRange:
    min_distance_km: float
    max_distance_km: float
    min_delay_min: float
    max_delay_min: float


def get_comm_delay_range() -> CommDelayRange:
    """Real range of one-way Earth-Mars communication delay across an orbit."""
    return CommDelayRange(
        min_distance_km=STRAIGHT_LINE_DISTANCE_MIN_KM,
        max_distance_km=STRAIGHT_LINE_DISTANCE_MAX_KM,
        min_delay_min=one_way_delay_minutes(STRAIGHT_LINE_DISTANCE_MIN_KM),
        max_delay_min=one_way_delay_minutes(STRAIGHT_LINE_DISTANCE_MAX_KM),
    )


# ===========================================================================
# 3. Launch windows (real anchor date + real synodic-period cadence)
# ===========================================================================
# Anchor: Mars 2020 (Perseverance) launched 2020-07-30 — a real, historical
# Mars launch. Future windows are projected forward using the synodic
# period (~779.7 days, computed in src/journey_scene.py from Kepler's
# third law) — NOT specific announced mission dates, since real launch
# dates depend on engineering readiness, not orbital mechanics alone.

PERSEVERANCE_LAUNCH_DATE = date(2020, 7, 30)


@dataclass
class LaunchWindow:
    approx_date: date
    label: str
    is_past: bool


def get_launch_windows(n_before: int = 1, n_after: int = 3, from_date: Optional[date] = None) -> List[LaunchWindow]:
    """
    Project approximate Hohmann-transfer launch windows forward/backward
    from the real Perseverance launch anchor, spaced by the synodic period.

    These are approximate windows based on orbital geometry alone — real
    missions may launch anywhere within a multi-week window around these
    dates, and actual announced mission dates may differ.
    """
    from_date = from_date or date.today()
    windows = []
    # Walk backward and forward from the anchor in synodic-period steps.
    k = -6
    while k <= 6:
        approx = PERSEVERANCE_LAUNCH_DATE + timedelta(days=SYNODIC_PERIOD_DAYS * k)
        windows.append(LaunchWindow(
            approx_date=approx,
            label=approx.strftime("%B %Y"),
            is_past=approx < from_date,
        ))
        k += 1

    past = [w for w in windows if w.is_past][-n_before:] if n_before > 0 else []
    future = [w for w in windows if not w.is_past][:n_after]
    return past + future


# ===========================================================================
# 4. Rocket equation (Tsiolkovsky) — illustrative reference vehicle
# ===========================================================================
# The equation itself is exact physics. Isp and Δv-budget figures below
# are real, commonly published reference ranges for chemical propulsion
# Mars transfers (NOT a specific real mission's vehicle design) — the UI
# must label this as illustrative, using a reference vehicle the user can
# adjust, not a claimed real mission.

REFERENCE_TMI_DELTA_V_MS = 3_600   # Trans-Mars Injection from LEO, typical published range ~3.5-3.9 km/s
REFERENCE_CHEMICAL_ISP_S = 380     # Typical high-performance chemical (LOX/LH2) engine vacuum Isp
G0_MS2 = 9.80665


def propellant_mass_fraction(delta_v_ms: float, isp_s: float) -> float:
    """
    Fraction of initial mass that must be propellant to achieve delta_v,
    via the Tsiolkovsky rocket equation: delta_v = Isp*g0*ln(m0/mf).

    Returns a value in [0, 1). Values approaching 1.0 mean almost the
    entire vehicle mass must be propellant.
    """
    import math
    mass_ratio = math.exp(delta_v_ms / (isp_s * G0_MS2))
    return 1.0 - (1.0 / mass_ratio)


def propellant_mass_kg(payload_mass_kg: float, delta_v_ms: float, isp_s: float) -> float:
    """Propellant mass (kg) needed to send a given payload through delta_v."""
    import math
    mass_ratio = math.exp(delta_v_ms / (isp_s * G0_MS2))
    m0 = payload_mass_kg * mass_ratio  # solving mf=payload, m0 = mf * ratio... see note below
    # Note: this treats payload_mass_kg as the FINAL (dry) mass after burn,
    # consistent with "payload + structure remaining after the burn".
    return m0 - payload_mass_kg


# ===========================================================================
# 5. Life-support consumables — real published NASA baseline rates
# ===========================================================================
# Source: NASA long-duration life-support references (commonly cited
# baseline: ~31.0 kg total daily consumables per crew member without
# recycling — oxygen ~0.83 kg, food (dry) ~0.62 kg, drinking/food-prep
# water ~3.56 kg, hygiene/flush/laundry water ~26.0 kg).
# Recycling comparison: NASA announced the ISS water recovery system
# reached ~98% water recovery efficiency (2023 milestone) — included here
# to show how dramatically closed-loop life support changes the mass
# budget, a real and current reference point, not a guess.

OXYGEN_KG_PER_PERSON_DAY = 0.83
FOOD_DRY_KG_PER_PERSON_DAY = 0.62
DRINKING_WATER_KG_PER_PERSON_DAY = 3.56
HYGIENE_WATER_KG_PER_PERSON_DAY = 26.0
ISS_WATER_RECOVERY_EFFICIENCY = 0.98  # NASA's 2023 ISS water recovery milestone


@dataclass
class ConsumablesEstimate:
    crew_size: int
    duration_days: int
    oxygen_kg: float
    food_kg: float
    water_kg_no_recycling: float
    water_kg_with_recycling: float
    total_kg_no_recycling: float
    total_kg_with_recycling: float


def estimate_consumables(crew_size: int, duration_days: int) -> ConsumablesEstimate:
    """
    Estimate total life-support consumable mass for a crew over a mission
    duration, using real published NASA baseline daily rates, compared
    with and without ISS-comparable (~98%) water recycling.
    """
    total_water_per_day = DRINKING_WATER_KG_PER_PERSON_DAY + HYGIENE_WATER_KG_PER_PERSON_DAY

    oxygen_kg = OXYGEN_KG_PER_PERSON_DAY * crew_size * duration_days
    food_kg = FOOD_DRY_KG_PER_PERSON_DAY * crew_size * duration_days
    water_no_recycling = total_water_per_day * crew_size * duration_days
    water_with_recycling = water_no_recycling * (1.0 - ISS_WATER_RECOVERY_EFFICIENCY)

    return ConsumablesEstimate(
        crew_size=crew_size,
        duration_days=duration_days,
        oxygen_kg=oxygen_kg,
        food_kg=food_kg,
        water_kg_no_recycling=water_no_recycling,
        water_kg_with_recycling=water_with_recycling,
        total_kg_no_recycling=oxygen_kg + food_kg + water_no_recycling,
        total_kg_with_recycling=oxygen_kg + food_kg + water_with_recycling,
    )
