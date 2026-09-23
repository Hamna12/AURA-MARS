"""
AURA Mars — SPICE Kernel Downloader (optional)

Downloads the small set of NASA/NAIF SPICE kernel files needed for
real-ephemeris planet positions (src/spice_ephemeris.py). This is
entirely optional — the Journey to Mars and Mission Planner tabs work
fine without it, using validated analytical Kepler orbit math instead.
Run this once if you want Journey to Mars to additionally show
"using real NASA ephemeris data" for its planet positions.

Kernels (all free, public, no API key — from NASA's NAIF archive):
    - naif0012.tls   Leap-seconds kernel (~5 KB)
    - de440s.bsp     Planetary ephemeris, 1849-2150 (~31 MB)

Usage:
    python scripts/download_spice_kernels.py
"""

import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import PROJECT_ROOT

KERNEL_DIR = PROJECT_ROOT / "data" / "spice_kernels"

KERNELS = {
    "naif0012.tls": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/naif0012.tls",
    "de440s.bsp": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440s.bsp",
}


def download_kernel(filename: str, url: str) -> bool:
    dest = KERNEL_DIR / filename
    if dest.exists():
        print(f"  [SKIP] {filename} already present ({dest.stat().st_size / 1e6:.1f} MB)")
        return True

    print(f"  Downloading {filename} from {url} ...")
    try:
        with requests.get(url, stream=True, timeout=60) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0))
            downloaded = 0
            with open(dest, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded / total * 100
                        print(f"\r    {downloaded / 1e6:.1f} / {total / 1e6:.1f} MB ({pct:.0f}%)", end="")
        print()
        print(f"  [OK] {filename}")
        return True
    except Exception as e:
        print(f"\n  [ERR] Failed to download {filename}: {e}")
        if dest.exists():
            dest.unlink()
        return False


def main():
    print("AURA Mars — SPICE Kernel Downloader")
    print("=" * 50)
    print(f"Destination: {KERNEL_DIR}")
    print("This is optional — the app works fine without it.")
    print("=" * 50)
    print()

    KERNEL_DIR.mkdir(parents=True, exist_ok=True)

    results = [download_kernel(name, url) for name, url in KERNELS.items()]

    print()
    if all(results):
        print("[SUCCESS] All SPICE kernels downloaded. Real NASA ephemeris data is now available.")
    else:
        print("[WARNING] Some kernels failed to download. The app will keep using analytical orbit math.")


if __name__ == "__main__":
    main()
