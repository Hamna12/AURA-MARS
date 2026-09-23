"""
AURA Mars — Shared Orbital Mechanics Constants

Real orbital constants (Earth/Mars orbital radii, periods via Kepler's
third law, Hohmann transfer geometry, synodic period, Earth-Mars distance
range) shared between the Journey to Mars visualization
(app/components/journey_scene.py) and the Mission Planner calculations
(src/mission_planner.py), so both draw from a single source of truth
instead of duplicating the same physics.

See app/components/journey_scene.py's module docstring for the full
explanation of what's real physics vs. disclosed simplification.
"""

from dataclasses import dataclass

AU_KM = 149_597_870.7

R_EARTH_AU = 1.0
R_MARS_AU = 1.524

EARTH_PERIOD_DAYS = 365.25
MARS_PERIOD_DAYS = (R_MARS_AU ** 1.5) * 365.25  # Kepler's 3rd law

A_TRANSFER_AU = (R_EARTH_AU + R_MARS_AU) / 2.0
E_TRANSFER = (R_MARS_AU - R_EARTH_AU) / (R_MARS_AU + R_EARTH_AU)
TRANSFER_DAYS = (A_TRANSFER_AU ** 1.5) * 365.25 / 2.0  # half the transfer ellipse

_OMEGA_EARTH = 360.0 / EARTH_PERIOD_DAYS   # deg/day
_OMEGA_MARS = 360.0 / MARS_PERIOD_DAYS     # deg/day
LAUNCH_PHASE_ANGLE_DEG = 180.0 - (_OMEGA_MARS * TRANSFER_DAYS)

# Synodic period: how often Earth and Mars return to the same relative
# geometry, i.e. how often a Hohmann-style launch window recurs.
SYNODIC_PERIOD_DAYS = 1.0 / (1.0 / EARTH_PERIOD_DAYS - 1.0 / MARS_PERIOD_DAYS)

STRAIGHT_LINE_DISTANCE_MIN_KM = (R_MARS_AU - R_EARTH_AU) * AU_KM   # closest approach
STRAIGHT_LINE_DISTANCE_MAX_KM = (R_MARS_AU + R_EARTH_AU) * AU_KM   # farthest apart


@dataclass
class JourneyFacts:
    transfer_days: float
    transfer_months: float
    earth_period_days: float
    mars_period_days: float
    mars_period_years: float
    launch_phase_angle_deg: float
    distance_closest_km: float
    distance_farthest_km: float
    earth_orbit_radius_km: float
    mars_orbit_radius_km: float
    synodic_period_days: float
    synodic_period_months: float


def get_journey_facts() -> JourneyFacts:
    """Return the real numbers behind the orbital mechanics, for display in the UI."""
    return JourneyFacts(
        transfer_days=TRANSFER_DAYS,
        transfer_months=TRANSFER_DAYS / 30.44,
        earth_period_days=EARTH_PERIOD_DAYS,
        mars_period_days=MARS_PERIOD_DAYS,
        mars_period_years=MARS_PERIOD_DAYS / 365.25,
        launch_phase_angle_deg=LAUNCH_PHASE_ANGLE_DEG,
        distance_closest_km=STRAIGHT_LINE_DISTANCE_MIN_KM,
        distance_farthest_km=STRAIGHT_LINE_DISTANCE_MAX_KM,
        earth_orbit_radius_km=R_EARTH_AU * AU_KM,
        mars_orbit_radius_km=R_MARS_AU * AU_KM,
        synodic_period_days=SYNODIC_PERIOD_DAYS,
        synodic_period_months=SYNODIC_PERIOD_DAYS / 30.44,
    )
