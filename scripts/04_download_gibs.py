"""
04_download_gibs.py
Fetch 4×4 = 16 GIBS PNG tiles per layer (true-color + IR) for all four storms.

Film-strip timestamps per storm: T−48h, T_peak, T_closest, T+24h
GIBS layers:
  True-color : MODIS_Terra_CorrectedReflectance_TrueColor  (date only)
  IR BT/WNP  : Himawari_AHI_Band13_Clean_Longwave_Window   (datetime)
  IR BT/ATL  : GOES-East_ABI_Band13_Clean_Longwave_Window  (datetime)

Outputs
-------
  data/gibs/{storm}/{layer_type}_{timestamp_label}.png

Warnings are printed for black/night tiles; a placeholder tile is saved.
"""

import os
import sys
import time
import pandas as pd
from io import BytesIO

sys.path.insert(0, os.path.dirname(__file__))
from utils import (
    GIBS_BASE_URL, GIBS_DIR, IBTRACS_DIR,
    STORM_ORDER, STORMS, ensure_dirs
)

try:
    import requests
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
except ImportError as e:
    sys.exit(f"[ERROR] Missing dependency: {e}\n  pip install requests Pillow numpy")

TILE_PX = 1024
RETRY_DELAY_S = 2


def fetch_gibs(layer: str, time_str: str, bbox: tuple,
               width: int = TILE_PX, height: int = TILE_PX) -> Image.Image | None:
    """
    Fetch one GIBS WMS tile.
    bbox = (min_lat, min_lon, max_lat, max_lon)
    time_str = 'YYYY-MM-DD' for daily layers or 'YYYY-MM-DDTHH:MM:SSZ' for hourly.
    Returns PIL Image or None on HTTP error.
    """
    params = {
        "SERVICE": "WMS",
        "VERSION": "1.3.0",
        "REQUEST": "GetMap",
        "LAYERS": layer,
        "CRS": "EPSG:4326",
        "BBOX": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
        "WIDTH": width,
        "HEIGHT": height,
        "FORMAT": "image/png",
        "TIME": time_str,
    }
    for attempt in range(3):
        try:
            r = requests.get(GIBS_BASE_URL, params=params, timeout=60)
            r.raise_for_status()
            # Check Content-Type; WMS errors come back as text/xml
            if "image" not in r.headers.get("Content-Type", ""):
                print(f"  [WARN] WMS returned non-image response (layer may not exist for this time).")
                return None
            return Image.open(BytesIO(r.content)).convert("RGB")
        except requests.HTTPError as e:
            print(f"  [WARN] HTTP {e.response.status_code} — {layer} @ {time_str}")
            return None
        except Exception as exc:
            print(f"  [WARN] Attempt {attempt+1}/3 failed: {exc}")
            time.sleep(RETRY_DELAY_S)
    return None


def is_mostly_black(img: Image.Image, threshold: float = 0.95) -> bool:
    """Return True if >threshold fraction of pixels are near-black (night tile)."""
    arr = np.array(img)
    dark = (arr < 20).all(axis=-1)
    return dark.mean() > threshold


def make_placeholder(width: int, height: int, label: str) -> Image.Image:
    """Create a grey placeholder tile with a text label."""
    img = Image.new("RGB", (width, height), color=(80, 80, 80))
    draw = ImageDraw.Draw(img)
    draw.text((width // 2 - 80, height // 2), label, fill=(200, 200, 200))
    return img


def storm_center_at_date(track_df: pd.DataFrame, date_str: str):
    """Return (lat, lon) nearest to the given date string (date only)."""
    target = pd.Timestamp(date_str)
    track_df = track_df.sort_values("ISO_TIME")
    diffs = (track_df["ISO_TIME"] - target).abs()
    idx = diffs.idxmin()
    return float(track_df.loc[idx, "LAT"]), float(track_df.loc[idx, "LON"])


def download_storm_tiles(key: str, track_df: pd.DataFrame) -> None:
    meta = STORMS[key]
    out_dir = os.path.join(GIBS_DIR, key)
    os.makedirs(out_dir, exist_ok=True)

    filmstrip = [
        ("T-48h",    meta["t_minus48_date"]),
        ("T_peak",   meta["t_peak_date"]),
        ("T_closest",meta["t_closest_date"]),
        ("T+24h",    meta["t_plus24_date"]),
    ]

    for label, date_str in filmstrip:
        lat_c, lon_c = storm_center_at_date(track_df, date_str)
        half = 8.0  # ± 8° around storm center
        bbox = (lat_c - half, lon_c - half, lat_c + half, lon_c + half)

        # ── True-color (MODIS, daily) ─────────────────────────────────────
        tc_path = os.path.join(out_dir, f"tc_{label}_{date_str}.png")
        if not os.path.exists(tc_path):
            print(f"  [{key}] TC  {label} {date_str} …")
            img = fetch_gibs(meta["gibs_tc_layer"], date_str, bbox)
            if img is None:
                img = make_placeholder(TILE_PX, TILE_PX, f"TC unavailable\n{date_str}")
            elif is_mostly_black(img):
                img = make_placeholder(TILE_PX, TILE_PX, f"Night — TC unavailable\n{date_str}")
                print(f"  [{key}] TC  {label}: nighttime (black) tile — saved placeholder")
            img.save(tc_path)

        # ── IR brightness temperature ──────────────────────────────────────
        # Try sub-daily (noon UTC) for Himawari/GOES; fall back to daily
        noon_str = f"{date_str}T12:00:00Z"
        ir_path = os.path.join(out_dir, f"ir_{label}_{date_str}.png")
        if not os.path.exists(ir_path):
            print(f"  [{key}] IR  {label} {date_str} …")
            img = fetch_gibs(meta["gibs_ir_layer"], noon_str, bbox)
            if img is None:
                # Fallback: try daily time string
                img = fetch_gibs(meta["gibs_ir_layer"], date_str, bbox)
            if img is None:
                img = make_placeholder(TILE_PX, TILE_PX, f"IR unavailable\n{date_str}")
                print(f"  [{key}] IR  {label}: layer not available — saved placeholder")
            img.save(ir_path)


def main():
    ensure_dirs()
    for key in STORM_ORDER:
        track_csv = os.path.join(IBTRACS_DIR, f"{key}_track.csv")
        if not os.path.exists(track_csv):
            print(f"[{key}] Track CSV not found — skipping")
            continue
        track_df = pd.read_csv(track_csv, parse_dates=["ISO_TIME"])
        print(f"\n[{key}] Fetching GIBS tiles …")
        download_storm_tiles(key, track_df)
        print(f"[{key}] Done.")


if __name__ == "__main__":
    main()
