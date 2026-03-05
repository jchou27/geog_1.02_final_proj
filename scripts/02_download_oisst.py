"""
02_download_oisst.py
Download OISST v2.1 SST fields from ERDDAP for each study storm and extract
along-track SST values (Q5).

For each storm:
  1. Download one daily SST NetCDF covering the storm bounding box
     at the storm's peak-intensity date.
  2. Append sst_C column to the per-storm track CSV.

Outputs
-------
  data/oisst/{storm}_sst.nc      — SST field for Fig 2
  data/ibtracs/{storm}_track.csv — updated with sst_C column

Run after 01_track_analysis.py.
"""

import os
import sys
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from utils import (
    OISST_DIR, IBTRACS_DIR, OISST_ERDDAP,
    STORM_ORDER, STORMS, ensure_dirs
)

try:
    import xarray as xr
    import requests
except ImportError as e:
    sys.exit(f"[ERROR] Missing dependency: {e}\n  pip install xarray requests netCDF4")


def peak_date(track_df: pd.DataFrame) -> str:
    """Return ISO date string of the row with maximum USA_WIND."""
    idx = track_df["USA_WIND"].idxmax()
    return track_df.loc[idx, "ISO_TIME"].strftime("%Y-%m-%d")


def build_erddap_url(date_str: str, lat_min: float, lat_max: float,
                     lon_min: float, lon_max: float) -> str:
    """
    Build ERDDAP griddap URL for a single-day OISST subset.
    ncdcOisst21Agg_LonPM180 uses longitude range -180..180.
    """
    t = f"{date_str}T12:00:00Z"
    url = (
        f"{OISST_ERDDAP}.nc"
        f"?sst[({t}):1:({t})]"
        f"[(0.0):1:(0.0)]"
        f"[({lat_min:.2f}):1:({lat_max:.2f})]"
        f"[({lon_min:.2f}):1:({lon_max:.2f})]"
    )
    return url


def download_sst(key: str, track_df: pd.DataFrame) -> None:
    """Download SST NetCDF for one storm and append sst_C to track CSV."""
    meta = STORMS[key]
    s, w, n, e = meta["oisst_bbox"]

    # Use peak-intensity date; fall back to first track date
    try:
        date_str = peak_date(track_df)
    except Exception:
        date_str = track_df["ISO_TIME"].iloc[0].strftime("%Y-%m-%d")

    outpath = os.path.join(OISST_DIR, f"{key}_sst.nc")
    if os.path.exists(outpath):
        print(f"[{key}] SST already cached: {outpath}")
    else:
        url = build_erddap_url(date_str, s, n, w, e)
        print(f"[{key}] Downloading SST ({date_str}) …\n  {url}")
        try:
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            with open(outpath, "wb") as f:
                f.write(r.content)
            print(f"[{key}] SST saved → {outpath}")
        except Exception as exc:
            # OISST "final" product has ~2-week lag; suggest "preliminary"
            print(f"[{key}] ERDDAP download failed: {exc}")
            print(
                f"[{key}] If Ragasa 2025, the final OISST product may not be "
                f"available yet.  Try the preliminary dataset:\n"
                f"  ncdcOisst21Agg instead of ncdcOisst21Agg_LonPM180,\n"
                f"  or download manually from https://www.ncei.noaa.gov/products/optimum-interpolation-sst"
            )
            return

    # ── Extract along-track SST ──────────────────────────────────────────────
    try:
        ds = xr.open_dataset(outpath)
        sst_da = ds["sst"].squeeze()   # drop time / altitude dims
    except Exception as exc:
        print(f"[{key}] Could not open SST file: {exc}")
        return

    sst_vals = []
    for _, row in track_df.iterrows():
        try:
            val = float(
                sst_da.sel(lat=row["LAT"], lon=row["LON"], method="nearest").values
            )
        except Exception:
            val = float("nan")
        sst_vals.append(val)

    track_df = track_df.copy()
    track_df["sst_C"] = sst_vals

    # Overwrite the track CSV with the new column
    track_csv = os.path.join(IBTRACS_DIR, f"{key}_track.csv")
    track_df.to_csv(track_csv, index=False)
    print(f"[{key}] sst_C appended → {track_csv}")
    print(
        f"[{key}] Along-track SST range: "
        f"{np.nanmin(sst_vals):.1f}–{np.nanmax(sst_vals):.1f} °C"
    )


def main():
    ensure_dirs()
    for key in STORM_ORDER:
        track_csv = os.path.join(IBTRACS_DIR, f"{key}_track.csv")
        if not os.path.exists(track_csv):
            print(f"[{key}] Track CSV not found — skipping ({track_csv})")
            continue
        track_df = pd.read_csv(track_csv, parse_dates=["ISO_TIME"])
        download_sst(key, track_df)


if __name__ == "__main__":
    main()
