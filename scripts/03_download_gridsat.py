"""
03_download_gridsat.py
Download GridSat-B1 brightness-temperature subsets for each study storm via
NCEI THREDDS OPeNDAP.

For each storm, downloads all 3-hourly files in the 96 h window before
t_closest (used by 05_coldcloud_metrics.py), plus the 4 film-strip timestamps
(used by fig4_ir_filmstrip.py).

GridSat-B1 URL pattern:
  https://www.ncei.noaa.gov/thredds/dodsC/cdr/gridsat/
  YYYY/GRIDSAT-B1.YYYY.MM.DD.HH.v02r01.nc

Variable: irwin_cdr  (11 µm window IR, K, decoded automatically by xarray)
Resolution: 0.07° global grid, 3-hourly.

Outputs
-------
  data/gridsat/{storm}/GRIDSAT-B1.YYYY.MM.DD.HH.nc  — per-timestep subsets

Run after 01_track_analysis.py.
"""

import os
import sys
import math
import pandas as pd
from datetime import timedelta

sys.path.insert(0, os.path.dirname(__file__))
from utils import (
    GRIDSAT_DIR, IBTRACS_DIR, GRIDSAT_BASE_URL,
    STORM_ORDER, STORMS, ensure_dirs
)

try:
    import xarray as xr
    import numpy as np
except ImportError as e:
    sys.exit(f"[ERROR] Missing dependency: {e}\n  pip install xarray netCDF4")

# Spatial padding around storm center for subset (degrees)
DELTA = 10.0
# Hours before t_closest to download (for metrics)
PRE_IMPACT_HRS = 96
# GridSat available hours (UTC)
GRIDSAT_HOURS = [0, 3, 6, 9, 12, 15, 18, 21]


def round_to_gridsat_hour(dt: pd.Timestamp) -> pd.Timestamp:
    """Round a timestamp to the nearest 3-hour GridSat slot."""
    hour = round(dt.hour / 3) * 3
    if hour == 24:
        dt = dt + timedelta(days=1)
        hour = 0
    return dt.replace(hour=hour, minute=0, second=0, microsecond=0)


def gridsat_url(dt: pd.Timestamp) -> str:
    return (
        f"{GRIDSAT_BASE_URL}/{dt.year}/"
        f"GRIDSAT-B1.{dt.year}.{dt.month:02d}.{dt.day:02d}.{dt.hour:02d}.v02r01.nc"
    )


def storm_center_at(track_df: pd.DataFrame, dt: pd.Timestamp):
    """
    Return (lat, lon) of the storm center nearest to dt.
    Interpolates linearly between flanking 6-hour track points.
    """
    track_df = track_df.sort_values("ISO_TIME")
    diffs = (track_df["ISO_TIME"] - dt).abs()
    idx = diffs.idxmin()
    return float(track_df.loc[idx, "LAT"]), float(track_df.loc[idx, "LON"])


def download_one(dt: pd.Timestamp, lat_c: float, lon_c: float,
                 outpath: str) -> bool:
    """
    Download one GridSat-B1 subset via OPeNDAP and save as NetCDF.
    Returns True on success, False on failure.
    """
    if os.path.exists(outpath):
        return True  # already cached

    url = gridsat_url(dt)
    lat_min = max(lat_c - DELTA, -70.0)
    lat_max = min(lat_c + DELTA,  70.0)
    lon_min = lon_c - DELTA
    lon_max = lon_c + DELTA

    try:
        ds = xr.open_dataset(url, engine="pydap")
    except Exception as exc:
        print(f"  [WARN] Cannot open {url}: {exc}")
        return False

    try:
        subset = ds.sel(lat=slice(lat_min, lat_max),
                        lon=slice(lon_min, lon_max))
        # Load irwin_cdr only to minimise transfer
        bt = subset["irwin_cdr"].load()
        ds_out = bt.to_dataset(name="irwin_cdr")
        ds_out.to_netcdf(outpath)
        return True
    except Exception as exc:
        print(f"  [WARN] Subset/save failed for {url}: {exc}")
        return False
    finally:
        ds.close()


def download_storm(key: str, track_df: pd.DataFrame) -> None:
    out_dir = os.path.join(GRIDSAT_DIR, key)
    os.makedirs(out_dir, exist_ok=True)

    meta = STORMS[key]

    # Identify t_closest from track
    idx_min = track_df["dist_km"].idxmin()
    t_closest = track_df.loc[idx_min, "ISO_TIME"]
    print(f"\n[{key}] t_closest = {t_closest}")

    # ── Build list of timesteps to download ───────────────────────────────
    timestamps = set()

    # 96 h pre-impact window (inclusive of t_closest)
    t0 = t_closest - timedelta(hours=PRE_IMPACT_HRS)
    cur = round_to_gridsat_hour(t0)
    while cur <= t_closest + timedelta(hours=3):   # +3 h buffer
        timestamps.add(cur)
        cur += timedelta(hours=3)

    # Film-strip timestamps
    for date_key in ("t_minus48_date", "t_peak_date", "t_closest_date", "t_plus24_date"):
        date_str = meta[date_key]
        # Try all 8 hours for the day to capture best option
        base = pd.Timestamp(date_str)
        for h in GRIDSAT_HOURS:
            timestamps.add(base.replace(hour=h))

    timestamps = sorted(timestamps)
    print(f"[{key}] Downloading {len(timestamps)} GridSat-B1 files …")

    ok, fail = 0, 0
    for dt in timestamps:
        lat_c, lon_c = storm_center_at(track_df, dt)
        fname = f"GRIDSAT-B1.{dt.year}.{dt.month:02d}.{dt.day:02d}.{dt.hour:02d}.nc"
        outpath = os.path.join(out_dir, fname)
        success = download_one(dt, lat_c, lon_c, outpath)
        if success:
            ok += 1
        else:
            fail += 1

    print(f"[{key}] Done: {ok} OK, {fail} failed.")


def main():
    ensure_dirs()
    for key in STORM_ORDER:
        track_csv = os.path.join(IBTRACS_DIR, f"{key}_track.csv")
        if not os.path.exists(track_csv):
            print(f"[{key}] Track CSV not found — skipping ({track_csv})")
            continue
        track_df = pd.read_csv(track_csv, parse_dates=["ISO_TIME"])
        download_storm(key, track_df)


if __name__ == "__main__":
    main()
