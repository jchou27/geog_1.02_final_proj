"""
utils.py — shared constants, storm metadata, and helper functions.
No I/O, no network access.
"""

from math import radians, sin, cos, sqrt, atan2
import os

# ── Storm metadata ────────────────────────────────────────────────────────────
STORMS = {
    "ragasa": {
        "name": "Ragasa",
        "year": 2025,
        "basin": "WNP",
        "ibtracs_name": "RAGASA",
        "ibtracs_sid": None,            # 2025 storm; may not be in IBTrACS yet
        "impact_lat": 22.28,
        "impact_lon": 114.18,
        "impact_label": "Victoria Harbour, HK",
        "gibs_ir_layer": "Himawari_AHI_Band13_Clean_Infrared",
        "gibs_tc_layer": "MODIS_Terra_CorrectedReflectance_TrueColor",
        "color": "#d62728",
        "linestyle": "-",      # WNP = solid
        "oisst_bbox": (10, 100, 35, 145),    # S, W, N, E
        "gridsat_bbox": (5, 95, 40, 150),
        # Approximate film-strip dates (confirmed by 01_track_analysis.py output)
        "t_minus48_date": "2025-09-22",
        "t_peak_date":    "2025-09-22",
        "t_closest_date": "2025-09-24",
        "t_plus24_date":  "2025-09-25",
    },
    "mangkhut": {
        "name": "Mangkhut",
        "year": 2018,
        "basin": "WNP",
        "ibtracs_name": "MANGKHUT",
        "ibtracs_sid": "WP252018",          # JTWC 25W-2018; verify after download
        "impact_lat": 22.28,
        "impact_lon": 114.18,
        "impact_label": "Victoria Harbour, HK",
        "gibs_ir_layer": "Himawari_AHI_Band13_Clean_Infrared",
        "gibs_tc_layer": "MODIS_Terra_CorrectedReflectance_TrueColor",
        "color": "#ff7f0e",
        "linestyle": "-",      # WNP = solid
        "oisst_bbox": (10, 100, 35, 145),
        "gridsat_bbox": (5, 95, 40, 150),
        "t_minus48_date": "2018-09-14",
        "t_peak_date":    "2018-09-15",
        "t_closest_date": "2018-09-16",
        "t_plus24_date":  "2018-09-17",
    },
    "maria": {
        "name": "Maria",
        "year": 2017,
        "basin": "ATL",
        "ibtracs_name": "MARIA",
        "ibtracs_sid": "AL152017",
        "impact_lat": 18.05,
        "impact_lon": -65.77,
        "impact_label": "Yabucoa, Puerto Rico",
        # GOES-16 ABI was in beta testing Sept 2017; layer may be available.
        # Fallback: MODIS_Terra_Brightness_Temp_Band31_Night
        "gibs_ir_layer": "GOES-East_ABI_Band13_Clean_Infrared",
        "gibs_tc_layer": "MODIS_Terra_CorrectedReflectance_TrueColor",
        "color": "#1f77b4",
        "linestyle": "--",     # ATL = dashed
        "oisst_bbox": (5, -100, 40, -50),
        "gridsat_bbox": (0, -105, 45, -45),
        "t_minus48_date": "2017-09-18",
        "t_peak_date":    "2017-09-19",
        "t_closest_date": "2017-09-20",
        "t_plus24_date":  "2017-09-21",
    },
    "dorian": {
        "name": "Dorian",
        "year": 2019,
        "basin": "ATL",
        "ibtracs_name": "DORIAN",
        "ibtracs_sid": "AL052019",
        "impact_lat": 26.50,
        "impact_lon": -76.98,
        "impact_label": "Elbow Cay, Great Abaco, Bahamas",
        "gibs_ir_layer": "GOES-East_ABI_Band13_Clean_Infrared",
        "gibs_tc_layer": "MODIS_Terra_CorrectedReflectance_TrueColor",
        "color": "#2ca02c",
        "linestyle": "--",     # ATL = dashed
        "oisst_bbox": (10, -100, 40, -60),
        "gridsat_bbox": (5, -105, 45, -55),
        # Dorian stalled ~30 h over Bahamas: T_peak ≈ T_closest
        "t_minus48_date": "2019-08-30",
        "t_peak_date":    "2019-09-01",
        "t_closest_date": "2019-09-01",
        "t_plus24_date":  "2019-09-02",
    },
}

# Canonical iteration order (WNP first, then ATL)
STORM_ORDER = ["ragasa", "mangkhut", "maria", "dorian"]

# ── URLs ──────────────────────────────────────────────────────────────────────
GIBS_BASE_URL = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
GRIDSAT_BASE_URL = "https://www.ncei.noaa.gov/thredds/dodsC/cdr/gridsat"
IBTRACS_URL = (
    "https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs"
    "/v04r01/access/csv/ibtracs.since1980.list.v04r01.csv"
)
OISST_ERDDAP = "https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21Agg_LonPM180"

# ── File-system paths (resolved relative to this file's parent) ───────────────
PROJ_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR    = os.path.join(PROJ_ROOT, "data")
FIG_DIR     = os.path.join(PROJ_ROOT, "figures")
IBTRACS_DIR = os.path.join(DATA_DIR, "ibtracs")
OISST_DIR   = os.path.join(DATA_DIR, "oisst")
GRIDSAT_DIR = os.path.join(DATA_DIR, "gridsat")
GIBS_DIR    = os.path.join(DATA_DIR, "gibs")

# ── Physical / threshold constants ───────────────────────────────────────────
BT_COLD    = 208    # K — deep convection / OLR-suppression threshold
BT_CDO     = 235    # K — cirrus cloud shield / SW-dimming footprint
GRIDSAT_DX = 0.07   # degrees — GridSat-B1 native grid spacing
R_EARTH    = 6371   # km


def haversine(lat1, lon1, lat2, lon2):
    """Return great-circle distance in km between two lat/lon points."""
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return R_EARTH * 2 * atan2(sqrt(a), sqrt(1 - a))


def ensure_dirs():
    """Create all required data/figure directories."""
    for d in (IBTRACS_DIR, OISST_DIR, GRIDSAT_DIR, GIBS_DIR, FIG_DIR):
        os.makedirs(d, exist_ok=True)
