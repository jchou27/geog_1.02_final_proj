# Storm Structure as Radiative Signature: Typhoon Ragasa and a Cross-Basin Comparison with Atlantic Hurricanes

**GEOG 1.02 Final Project** | Due: March 14, 2026

## Overview

This project analyzes cross-basin differences in tropical cyclone intensity change near land and cloud radiative signatures (shortwave dimming / longwave emission) across four study storms:

| Storm | Basin | Year | Notes |
|---|---|---|---|
| Typhoon Ragasa | Western North Pacific | 2025 | Made landfall near Hong Kong |
| Typhoon Mangkhut | Western North Pacific | 2018 | Super typhoon, WNP benchmark |
| Hurricane Maria | Atlantic | 2017 | Category 5, Puerto Rico landfall |
| Hurricane Dorian | Atlantic | 2019 | Category 5, stalled over Bahamas |

**Research question:** For storms of similar peak intensity, do typhoons and hurricanes differ in intensity change near land and in the cloud structures shaping shortwave dimming and longwave emission?

## Setup

```bash
pip install -r requirements.txt
```

**Dependencies:** pandas, numpy, xarray, netCDF4, pydap, cartopy, matplotlib, Pillow, scipy, requests

## Running the Pipeline

Scripts must be run in order. Download scripts are `.py`; analysis and figure scripts are Jupyter notebooks.

### Phase 1 — Track data
```bash
python scripts/00_download_ibtracs.py
jupyter nbconvert --to notebook --execute scripts/01_track_analysis.ipynb
```

### Phase 2 — Satellite and ocean data
```bash
python scripts/02_download_oisst.py
python scripts/03_download_gridsat.py
python scripts/04_download_gibs.py
```

### Phase 3 — Metrics and figures
```bash
jupyter nbconvert --to notebook --execute scripts/05_coldcloud_metrics.ipynb
jupyter nbconvert --to notebook --execute scripts/fig1_track_vmax.ipynb
jupyter nbconvert --to notebook --execute scripts/fig2_sst_maps.ipynb
jupyter nbconvert --to notebook --execute scripts/fig3_truecolor_filmstrip.ipynb
jupyter nbconvert --to notebook --execute scripts/fig4_ir_filmstrip.ipynb
jupyter nbconvert --to notebook --execute scripts/fig5_coldcloud_timeseries.ipynb
```

Figures are saved to `figures/`.

## Project Structure

```
scripts/
  utils.py                    # Central config — STORMS dict, paths, constants
  00_download_ibtracs.py      # Download IBTrACS CSV (~250 MB, cached)
  01_track_analysis.ipynb     # Storm track filtering and intensity analysis
  02_download_oisst.py        # OISST v2.1 SST fields via ERDDAP
  03_download_gridsat.py      # GridSat-B1 IR grids via NCEI THREDDS OPeNDAP
  04_download_gibs.py         # GIBS WMS satellite imagery (true-color + IR)
  05_coldcloud_metrics.ipynb  # Compute cold-cloud-top area and min BT
  track_vmax.ipynb       # Track + Vmax vs. distance-to-coast
  sst_maps.ipynb         # SST context maps with storm tracks
  truecolor_filmstrip.ipynb  # True-color film strips (4 timestamps x 4 storms)
  ir_filmstrip.ipynb     # IR brightness temperature film strips
  coldcloud_timeseries.ipynb # Cold-cloud area & min BT vs. time-to-landfall
data/
  ibtracs/    # IBTrACS CSV (downloaded by 00_)
  oisst/      # OISST NetCDF per storm
  gridsat/    # GridSat-B1 NetCDF per storm
  gibs/       # GIBS PNG tiles per storm
figures/      # Output figures
```

## Data Sources

| Dataset | Purpose | Access |
|---|---|---|
| IBTrACS v04r01 | 6-hourly storm tracks and intensity | NCEI CSV download |
| OISST v2.1 | Daily SST at 0.25° resolution | NOAA ERDDAP |
| GridSat-B1 | 3-hourly IR brightness temperature | NCEI THREDDS OPeNDAP |
| GIBS / NASA Worldview | True-color and IR satellite imagery | WMS API |

**Intensity data:** `USA_WIND` (JTWC 1-minute kt) is used for cross-basin comparison rather than `WMO_WIND`.

**Key thresholds:**
- `BT < 208 K` — deep convection (cold cloud-top area)
- `BT < 235 K` — cloud shield / SW-dimming footprint (CDO radius)

## Known Issues

- **Ragasa 2025** may not be in IBTrACS yet due to publication lag. The download script warns and skips rather than crashing.
- **Maria 2017**: GOES-East ABI IR layer may be unavailable (GOES-16 was in beta testing Sept 2017). A fallback layer is noted in `utils.py`.
- **Dorian**: stalled ~30h over the Bahamas so `T_peak == T_closest` (both `2019-09-01`). This is scientifically meaningful.
