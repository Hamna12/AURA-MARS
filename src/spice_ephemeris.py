"""
AURA Mars — Optional SPICE Ephemeris Layer

Real NASA/JPL planetary ephemeris positions via spiceypy, when the
kernel files are present (see scripts/download_spice_kernels.py).
Entirely optional: every function here degrades gracefully to None /
False when spiceypy isn't installed or the kernels haven't been
downloaded — nothing else in the app depends on this being available.

This exists to let the Journey to Mars tab optionally show "using real
NASA ephemeris data" instead of the analytical Kepler-orbit
approximation (src/orbital_mechanics.py) that the rest of the app uses
by default. The analytical math is already independently validated
(see journey_scene.py) — this is a precision upgrade, not a
correctness fix.
"""

from datetime import date, datetime
from pathlib import Path
from typing import Optional, Tuple

from src.config import PROJECT_ROOT

KERNEL_DIR = PROJECT_ROOT / "data" / "spice_kernels"
REQUIRED_KERNELS = ["naif0012.tls", "de440s.bsp"]

_kernels_loaded = False
_spice_import_failed = False


def _try_import_spiceypy():
    global _spice_import_failed
    if _spice_import_failed:
        return None
    try:
        import spiceypy
        return spiceypy
    except ImportError:
        _spice_import_failed = True
        return None


def kernels_present() -> bool:
    """True if all required SPICE kernel files have been downloaded."""
    return all((KERNEL_DIR / name).exists() for name in REQUIRED_KERNELS)


def spice_available() -> bool:
    """True if spiceypy is installed AND the required kernels are present."""
    return _try_import_spiceypy() is not None and kernels_present()


def _ensure_kernels_loaded() -> bool:
    """Load the SPICE kernels once (idempotent). Returns True if ready."""
    global _kernels_loaded
    spiceypy = _try_import_spiceypy()
    if spiceypy is None or not kernels_present():
        return False
    if not _kernels_loaded:
        for name in REQUIRED_KERNELS:
            spiceypy.furnsh(str(KERNEL_DIR / name))
        _kernels_loaded = True
    return True


# NAIF body names for the ecliptic-J2000, Sun-centered frame.
_BODY_NAMES = {"earth": "EARTH BARYCENTER", "mars": "MARS BARYCENTER"}


def get_planet_position_au(planet: str, when: Optional[date] = None) -> Optional[Tuple[float, float, float]]:
    """
    Real heliocentric (x, y, z) position of a planet in AU, in the
    ecliptic J2000 frame, from NASA's own DE440s ephemeris.

    Parameters
    ----------
    planet : str
        "earth" or "mars".
    when : date, optional
        Defaults to today.

    Returns
    -------
    (x, y, z) in AU, or None if SPICE/kernels are unavailable or the
    planet name isn't recognised.
    """
    if planet.lower() not in _BODY_NAMES:
        return None
    spiceypy = _try_import_spiceypy()
    if spiceypy is None or not _ensure_kernels_loaded():
        return None

    when = when or date.today()
    utc_str = datetime(when.year, when.month, when.day, 12, 0, 0).strftime("%Y-%m-%dT%H:%M:%S")
    et = spiceypy.str2et(utc_str)

    position_km, _light_time = spiceypy.spkpos(
        _BODY_NAMES[planet.lower()], et, "ECLIPJ2000", "NONE", "SUN"
    )
    au_km = 149_597_870.7
    return (position_km[0] / au_km, position_km[1] / au_km, position_km[2] / au_km)


def get_data_source_label() -> str:
    """Human-readable label for which position data source is active."""
    return "NASA SPICE ephemeris (DE440s)" if spice_available() else "Analytical Kepler-orbit approximation"
