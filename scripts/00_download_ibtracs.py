"""
00_download_ibtracs.py
Download (or use cached) IBTrACS since-1980 CSV, filter to the four study storms,
and print a verification table of peak USA_WIND per storm.

Run once before any other script.
"""

import os
import sys
import pandas as pd

# Allow running from any directory
sys.path.insert(0, os.path.dirname(__file__))
from utils import (
    IBTRACS_URL, IBTRACS_DIR, STORM_ORDER, STORMS, ensure_dirs
)

RAW_CSV     = os.path.join(IBTRACS_DIR, "ibtracs.since1980.csv")
FILTERED_CSV = os.path.join(IBTRACS_DIR, "storms_filtered.csv")


def load_ibtracs() -> pd.DataFrame:
    """Download IBTrACS CSV if not cached; return full DataFrame."""
    ensure_dirs()
    if os.path.exists(RAW_CSV):
        print(f"[IBTrACS] Using cached file: {RAW_CSV}")
    else:
        print(f"[IBTrACS] Downloading (~250 MB) from:\n  {IBTRACS_URL}")
        # skiprows=[1] drops the units row; low_memory=False avoids dtype warnings
        df = pd.read_csv(IBTRACS_URL, skiprows=[1], low_memory=False)
        df.to_csv(RAW_CSV, index=False)
        print(f"[IBTrACS] Saved to {RAW_CSV}")
        return df

    return pd.read_csv(RAW_CSV, low_memory=False)


def filter_storms(df: pd.DataFrame) -> pd.DataFrame:
    """Return rows for the four study storms; warn if any are missing."""
    df["ISO_TIME"] = pd.to_datetime(df["ISO_TIME"], errors="coerce")
    df["USA_WIND"] = pd.to_numeric(df["USA_WIND"], errors="coerce")
    df["WMO_WIND"] = pd.to_numeric(df["WMO_WIND"], errors="coerce")
    df["LAT"]      = pd.to_numeric(df["LAT"],      errors="coerce")
    df["LON"]      = pd.to_numeric(df["LON"],      errors="coerce")

    pieces = []
    for key in STORM_ORDER:
        meta = STORMS[key]
        name = meta["ibtracs_name"]
        year = meta["year"]

        # Match by NAME and year of ISO_TIME
        mask = (df["NAME"] == name) & (df["ISO_TIME"].dt.year == year)
        subset = df[mask].copy()
        subset["storm_key"] = key

        if subset.empty:
            # Ragasa 2025 may not be in IBTrACS yet
            print(
                f"[WARNING] {name} ({year}) not found in IBTrACS.\n"
                f"          If this is Ragasa 2025, the storm may not yet be "
                f"in the archive (IBTrACS has a publication lag).\n"
                f"          Skipping this storm for now."
            )
        else:
            print(f"[IBTrACS] Found {name} ({year}): {len(subset)} rows, "
                  f"SID = {subset['SID'].iloc[0]}")
            pieces.append(subset)

    if not pieces:
        raise RuntimeError("No study storms found in IBTrACS.")

    return pd.concat(pieces, ignore_index=True)


def print_verification(df: pd.DataFrame) -> None:
    """Print peak USA_WIND per storm for Q1 verification."""
    print("\n" + "=" * 60)
    print("Q1 Verification — Peak intensity (USA_WIND, 1-min kt)")
    print("=" * 60)
    rows = []
    for key in STORM_ORDER:
        sub = df[df["storm_key"] == key]
        if sub.empty:
            rows.append({"storm": key, "peak_USA_WIND_kt": "N/A", "peak_date": "N/A"})
            continue
        idx = sub["USA_WIND"].idxmax()
        rows.append({
            "storm": f"{STORMS[key]['name']} ({STORMS[key]['year']})",
            "basin": STORMS[key]["basin"],
            "peak_USA_WIND_kt": sub.loc[idx, "USA_WIND"],
            "peak_date": sub.loc[idx, "ISO_TIME"].strftime("%Y-%m-%d %HZ"),
        })
    tbl = pd.DataFrame(rows)
    print(tbl.to_string(index=False))

    # Pairwise peak-wind differences (WNP vs ATL)
    peaks = {}
    for _, r in tbl.iterrows():
        if r["peak_USA_WIND_kt"] != "N/A":
            peaks[r["storm"]] = float(r["peak_USA_WIND_kt"])
    if len(peaks) > 1:
        names = list(peaks.keys())
        print("\nPairwise |ΔVmax| (kt):")
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                diff = abs(peaks[names[i]] - peaks[names[j]])
                print(f"  {names[i]} vs {names[j]}: {diff:.0f} kt")
    print("=" * 60 + "\n")


def main():
    df_full = load_ibtracs()
    df = filter_storms(df_full)
    print_verification(df)
    df.to_csv(FILTERED_CSV, index=False)
    print(f"[IBTrACS] Filtered data saved → {FILTERED_CSV}")
    print(f"[IBTrACS] Total rows saved: {len(df)}")


if __name__ == "__main__":
    main()
