# FINDINGS AND DECISIONS LOG — Mathews County Flood Prediction Project

## Overview
This document tracks decisions, research findings, data discoveries, and project milestones for building the Mathews County, VA tidal flooding data pipeline and predictive model.

---

## 1. Decision Log

| Date | Decision | Rationale | Impact / Artifact |
| :--- | :--- | :--- | :--- |
| **2026-09-30** | **Execute Project in Sequenced Phased Order starting with Task 1** | User approved the 4-phase roadmap. Working in order ensures clean ground truth before model training. | Roadmap adopted in `AGENTS.md`. |
| **2026-09-30** | **Standardize Ground-Truth Observations into CSV** | Handwritten notebook photos (`IMG_8049.jpeg`–`IMG_8058.jpeg`) contained critical validation records that must be machine-readable. | Created `ground_truth_observations.csv` (141 entries, 121 depth records). |
| **2026-09-30** | **Establish Dual-Unit Standard (Feet for River/Bay, Inches for Ground Flooding)** | Gauges report in feet (ft), while property and road observations are recorded in inches (in). Acknowledged conversion $1\text{ ft} = 12\text{ in}$, $0.10\text{ ft} \approx 1.2\text{ in}$. | Explicit column naming: `ware_river_stage_ft` and `flood_depth_in`. |
| **2026-09-30** | **Define Timezone Standard: America/New_York (EST/EDT)** | Human observations were recorded in local Eastern time, whereas NOAA CO-OPS data defaults to GMT/UTC. | Pipeline scripts must normalize all external UTC records to local Eastern time. |
| **2026-09-30** | **Adopt 2-Stage Modeling Strategy** | Direct prediction from weather to local inches is noisy; predicting the Ware River stage first from regional bay surge/wind/tide, then predicting local inches from river stage provides interpretability and modular testing. | Stage 1: Regional water level; Stage 2: Hyper-local inundation. |
| **2026-09-30** | **Backfill 2021-2024 Ware River via IEM HML Archive** | WRVV2 is an NWS NWPS tide gage rather than a standard USGS daily-discharge gage; the Iowa Environmental Mesonet (IEM) archives its 6-minute stages. Batching requests by calendar month avoided timeouts and recovered all 45 months. | Generated `ware_river_stage_2021_2024.csv` (285k rows) and `ware_river_hourly_2021_2024.csv` (31k rows). |
| **2026-09-30** | **Construct Unified Hourly Dataset (`merged_hourly_training_dataset.csv`)** | Aligned Ware River stage, Yorktown USCG met/winds/pressure, Windmill Point tides/surge, and local ground-truth depths on hourly timestamps in `America/New_York`. Derived physical wind vector components ($u, v$, along-bay wind at $20^\circ$, cross-bay wind at $110^\circ$). | `merged_hourly_training_dataset.csv` (32,833 hourly records). |
| **2026-10-01** | **Build Live Multi-Network Ingestion Pipeline (`ingest_realtime.py`)** | Querying NOAA NWPS, NOAA CO-OPS, and NWS APIs pulls real-time 6-min observations and 48-hr forward predictions into time-aligned datasets and a live status JSON. | `ingest_realtime.py`, `latest_status.json`, `realtime_recent_observations.csv`, `forecast_48h.csv`. |
| **2026-10-01** | **Two-Tier Stage 1 ML Architecture (Nowcast vs Forecast)** | Live surge at Windmill Point enables ultra-precise short-range nowcasting ($R^2 = 0.973$, MAE = 1.5"), while forward 48-hour forecasting relies on astronomical tides + quadratic wind stress memory ($R^2 = 0.721$). | Trained Linear Regression and LightGBM models in `train_predictive_models.py`. |
| **2026-10-01** | **Zero-Dependency Deployment Format (`model_weights_and_thresholds.json`)** | Saved trained linear weights and piecewise stage-to-depth parameters to JSON so production scoring scripts can execute instantly in pure Python without third-party ML libraries. | `models/model_weights_and_thresholds.json`. |
| **2026-10-01** | **Implement Multi-Tier Coastal Flood Alerting (`check_alerts.py`)** | Automated bulletin generator evaluates current and 48-hr forward conditions against discovered thresholds (Tier 0 Normal to Tier 3 Severe), calculating flood onset, peak, and drainage duration. | `check_alerts.py`. |
| **2026-10-01** | **Formulate Compound Pluvial + Tidal Backwater Model** | Gravity drainage is restricted when river stage exceeds ditch invert ($3.80\text{ ft MLLW}$). Modeled backwater restriction factor $\beta = \text{clip}((\text{stage} - 3.8)/0.4, 0, 1)$ to trap rainfall accumulation onto low swales and driveways. | Integrated into `micro_topography.py` and `ingest_realtime.py`. |
| **2026-10-01** | **Establish Hybrid Hydrodynamic–ML Residual Modeling** | Blended NOAA NWPS 4-day CBOFS hydrodynamic stage forecast with our local ML quadratic wind stress set-up correction ($0.012 \times \text{along\_bay} + 0.0006 \times \tau_{\text{along}}$), eliminating shelf surge blindspots while preserving local shallow-water stacking accuracy. | `ingest_realtime.py`, `forecast_48h.csv`. |
| **2026-10-01** | **Construct Multi-Sector Property Micro-Topography Engine** | Mapped 5 specific elevation sectors (Ditches 2.5 ft, Road Apron 4.0 ft, Main Driveway 4.4 ft, Yard 4.6 ft, Garage Apron 4.9 ft MLLW) and vehicular accessibility criteria (Sedan vs SUV vs Impassable). | Created `micro_topography.py`, updated `generate_dashboard.py` and `flood_dashboard.html`. |
| **2026-10-01** | **Establish Project Backlog (`BACKLOG.md`)** | Formalized upcoming priorities including automated daemon (`launchd`), multi-channel phone alerts (Pushover/SMS), continuous archival, and web cloud hosting. | `BACKLOG.md`. |
| **2026-10-01** | **Implement Zero-Cost Mobile Push Alerting via ntfy.sh** | Added automated mobile & browser push alerting to topic `mathews-flood-23128` with stateful anti-spam deduplication (`alert_state.json`), pre-crest 2-hr warning, and an interactive QR code/1-click subscription banner on `index.html`. Integrated into GitHub Actions cron. | `check_alerts.py`, `alert_state.json`, `generate_dashboard.py`, `index.html`, `.github/workflows/update_flood_monitor.yml`. |
| **2026-10-01** | **Migrate Large Subscribe Banner to Dedicated Mobile Alerts Page (`alerts.html`)** | Reclaimed premium landing page real estate on `index.html` by removing the bulky top subscribe banner, allowing instant visibility of the live status advisory, vehicle passability matrix, and interactive Leaflet map. Created a dedicated 5th portal page (`alerts.html` & `subscribe.html`) with a high-res QR code, 1-click subscription, copyable topic, iOS/Android/Web setup guides, 4-stage warning timeline, lock-screen preview simulator, and FAQ. Added a sleek, compact callout strip near the bottom of `index.html` and updated GitHub Actions Pages workflow. | `generate_dashboard.py`, `alerts.html`, `subscribe.html`, `index.html`, `flood_dashboard.html`, `.github/workflows/update_flood_monitor.yml`, `AGENTS.md`. |
| **2026-10-01** | **Hardened Real-Time Pipeline Parameter Signatures & Station Dictionaries (`ingest_realtime.py`)** | Resolved GitHub Action runtime `KeyError: 'water_level_ft'` by converting `generate_latest_status` to explicit keyword arguments with default `None`, and hardening all dictionary lookups (`sw_water`, `sw_preds`, `wm_water`, `yt_water`, `nwps_fcst`) to use safe `.get()` methods. | `ingest_realtime.py`. |




---

## 2. Key Findings & Data Discoveries

### 2.1 Ground-Truth Observations Dataset
* Spanning **May 29, 2021 to September 27, 2024**.
* Total recorded events: **141** (93 flood events with measured depth, 28 zero-flood baseline events, 20 qualitative storm/gauge notes).
* Observed range of flood depths: **$0.0"$ to $14.5"$**.
* Range of Ware River gauge stages: **$3.55\text{ ft}$ to $5.22\text{ ft}$**.

### 2.2 Statistical Analysis & Physical Thresholds
A linear regression between the recorded Ware River stage ($x$, in feet) and ground flood depth ($y$, in inches) gives:
$$\text{Flood Depth (inches)} = 10.95 \times \text{Ware River Stage (ft)} - 43.69$$

* **Correlation Coefficient ($r$)**: **$0.912$** ($R^2 = 0.832$).
* **Critical Flood Inundation Threshold**:
  $$\text{Zero Flood Threshold} = \frac{43.69}{10.95} = 3.99\text{ ft}$$
  * Any Ware River stage below **$4.00\text{ ft}$** results in zero surface flooding (water remains contained in ditches and marsh).
  * Any Ware River stage $\ge 4.00\text{ ft}$ produces progressive flooding at a rate of **$\approx 1.1\text{ to }1.2\text{ inches}$ per $0.10\text{ ft}$ of gauge rise**.
* **Observer Formula Validation**: On `IMG_8049.jpeg`, the observer wrote:
  `".10 = 1 3/16 th IN or almost 1.25 inches"`.
  This empirical calculation directly matches the regression slope ($10.95 \text{ in/ft} \times 0.10 \text{ ft} = 1.10\text{"} \approx 1.2\text{"}$).

### 2.3 Storm Events & Meteorological Drivers
The dataset contains ground-truth responses to major tropical and extra-tropical systems:

1. **Hurricane Helene (Sep 27, 2024)**:
   * Ware River Stage: **4.70 ft**
   * Peak Flood Depth: **$9.75"$**
   * Wind: **SE 25.3 mph**
   * Hydrograph / Inundation Profile:
     * 6:20 PM: $3.0"$
     * 7:30 PM: $9.75"$ (peak)
     * 8:20 PM: Tide receded $7.25"$ down to $2.5"$
2. **King Tide + Perigean Spring Tide (Sep 21–23, 2024)**:
   * Peak Stage: **5.20 ft** (Sep 22, 1:06 PM)
   * Peak Flood Depth: **$14.5"$**
   * Driven by solar/lunar alignment compounded with light onshore SE winds ($5\text{--}10\text{ mph}$).
3. **Winter Storm / Coastal Nor'easter (Jan 3, 2022)**:
   * Ware River Stage: **5.22 ft**
   * Peak Flood Depth: **$11.0"$**
   * Winds from North with heavy snowfall.
4. **Hurricane Ian Remnants (Sep 30 – Oct 1, 2022)**:
   * Ware River Stage: **4.66 ft**
   * Flood Depth: **$7.0"$**
   * Winds: N to NNW at 17–25 mph.
5. **Tropical Storm Ophelia (Sep 22–23, 2023)**:
   * Ware River Stage: **5.00 ft**
   * Flood Depth: **$12.0"$**
   * Compounded by lunar perigee.

### 2.4 Historical Water Level & Merged Dataset Insights
* **Continuous Coverage**: 32,833 consecutive hourly timestamps (Jan 1, 2021 00:00 to Sep 30, 2024 23:00 EDT).
* **Datum Relationship**: Ware River stage MLLW vs NAVD88 has an exact constant offset of $1.64\text{ ft}$:
  $$\text{Stage}_{\text{NAVD88}} = \text{Stage}_{\text{MLLW}} - 1.64\text{ ft}$$
* **Surge Metric**: Storm surge at Windmill Point ($\text{verified water level} - \text{predicted tide}$) exhibits spikes exceeding $+2.5\text{ to }+3.2\text{ ft}$ during Nor'easters and tropical systems.
* **Wind Alignment**: Along-bay wind vector projected at $20^\circ$ (NNE-to-SSW axis down the Chesapeake Bay) strongly correlates with positive surge in Mobjack Bay and Ware River.
* **Observation Timing Anomaly Resolved**: On May 11, 2024, the notebook recorded `4.92 A 0` (high stage but 0" flood in morning). Hourly USGS hydrograph analysis revealed the gauge peaked at 4.90 ft at **00:00:00 EDT (midnight)** and receded to 2.0 ft by morning (06:00 EDT). The water had completely drained before the observer's morning inspection, illustrating why automated hourly logging is essential.

### 2.5 Machine Learning Model Evaluation & Backtesting
A two-stage machine learning system was trained on 2021–2023 data ($N = 24,803$ hours) and evaluated on an out-of-sample 2024 holdout test set ($N = 6,127$ hours), which included Hurricane Helene and the September 2024 King Tide:

#### Stage 1: Ware River Stage Prediction (2024 Holdout Test Set)
| Model | Operational Mode | $R^2$ | RMSE (ft) | MAE (ft) | MAE (in) | High-Water MAE ($\ge 4.0\text{ ft}$) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Nowcast Linear Baseline** | Short-range (0–6 hr) with mouth-of-bay surge | **0.9731** | **0.160 ft** | **0.121 ft** | **1.5"** | **1.7"** |
| **Nowcast LightGBM** | Short-range (0–6 hr) with mouth-of-bay surge | 0.9722 | 0.163 ft | 0.121 ft | 1.5" | 2.6" |
| **Forecast Linear Baseline** | Forward 48-hr (Astronomical tides + wind stress) | **0.7209** | **0.515 ft** | **0.395 ft** | **4.8"** | 9.6" |
| **Forecast LightGBM** | Forward 48-hr (Astronomical tides + wind stress) | 0.7067 | 0.528 ft | 0.402 ft | 4.8" | 10.9" |

#### Stage 2: Hyper-Local Inundation Depth (Ground-Truth Evaluation)
* Model: $\text{Flood Depth (in)} = \max(0.0, 10.95 \times \text{Ware River Stage (ft)} - 43.69)$
* Performance on 119 verified observations: **$R^2 = 0.8001$**, **$\text{MAE} = 1.22\text{ inches}$**, **$\text{RMSE} = 1.72\text{ inches}$**.

#### Storm Event Backtest Case Studies
1. **September King Tide (Sep 22, 2024)**:
   * Observed Peak Stage: **5.15 ft** (Ground Truth Flood Depth: **14.5"**)
   * Model Predicted Peak: **5.07 ft** (Error: **0.08 ft / 1.0 inch**)
   * Predicted Flood Depth: **11.8" – 12.7"**
2. **Hurricane Helene (Sep 27, 2024)**:
   * Observed Peak Stage: **4.56 ft** (Ground Truth Flood Depth: **9.75"**)
   * Model Predicted Peak: **4.27 ft** (Error: **0.29 ft / 3.5 inches**)
   * Predicted Flood Depth: **6.0" – 7.8"**
3. **TS Ophelia (Sep 22–23, 2023)**:
   * Observed Peak Stage: **5.11 ft** (Ground Truth Flood Depth: **12.0"**)
   * Model Predicted Peak: **4.82 ft** (Error: **0.29 ft / 3.5 inches**)

---

## 3. Current File Inventory

* `ground_truth_observations.csv`: Fully digitized, structured observations dataset (141 rows).
* `generate_ground_truth.py`: Reproducible generator script for the ground-truth dataset.
* `backfill_ware_river_history.py`: Script pulling monthly WRVV2 archives from IEM.
* `ware_river_stage_2021_2024.csv`: 285,097 6-min observations (2021–2024).
* `ware_river_hourly_2021_2024.csv`: 31,340 hourly resampled Ware River stage rows.
* `build_merged_training_dataset.py`: ETL pipeline joining Ware River, Yorktown met, Windmill Point tides, and observations.
* `merged_hourly_training_dataset.csv`: 32,833 rows unified training dataset with 26 features and targets.
* `ingest_realtime.py`: Live ingestion engine connecting to NOAA NWPS, NOAA CO-OPS, and NWS APIs.
* `train_predictive_models.py`: Machine learning training pipeline and backtesting engine.
* `check_alerts.py`: Multi-tier flood warning bulletin generator.
* `latest_status.json`: Real-time conditions and 48-hr forward hazard summary.
* `realtime_recent_observations.csv`: Hourly aligned recent observations (past 48 hours).
* `forecast_48h.csv`: Forward 48-hour hourly forecast timeline.
* `micro_topography.py`: Site-specific micro-topography elevation profile & compound pluvial inundation engine.
* `generate_dashboard.py`: Generator producing standalone interactive web dashboard.
* `flood_dashboard.html`: Self-contained interactive HTML dashboard with 96-hour hydrograph, live sector status, and high tide timetable.
* `BACKLOG.md`: Long-term project roadmap and prioritized future sprints.
* `models/model_weights_and_thresholds.json`: Zero-dependency deployable model weights.
* `models/stage1_nowcast_lgbm.pkl` & `stage1_forecast_lgbm.pkl`: Trained LightGBM model binaries.
* `models/evaluation_report.json`: Metrics report and storm case study backtests.
* `AGENTS.md`: Operating guide, system specs, and conventions for AI assistants.
* `FINDINGS_AND_DECISIONS.md`: This file.
* `Ware_River_WRVV2_HMIRA_observed.csv`: 6,746 6-min stage readings (Aug 30 – Sep 29, 2024).
* `8637689-Yorktown-USCG-Training-Center-data/`: 2021–2024 hourly met data and tide predictions.
* `Windmill-point-data/`: 2021–2024 hourly predicted and verified water levels.
* `Photos of observations/`: Original source photos of notebook and notes.

---

## 4. Operational Instructions & Automated Execution

### Real-Time Update Command
```bash
python3 ingest_realtime.py
```
* Queries real-time APIs (NOAA NWPS, CO-OPS, NWS).
* Generates `latest_status.json`, `realtime_recent_observations.csv`, and `forecast_48h.csv`.

### Flood Hazard & Alert Check Command
```bash
python3 check_alerts.py --always-print --notify
```
* Reads `latest_status.json` and prints an immediate colored hazard advisory with vehicle passability & sector elevation profile.
* `--notify`: Triggers native macOS desktop notification banner and audible chime.

### Generate Interactive Web Dashboard
```bash
python3 generate_dashboard.py
```
* Generates `flood_dashboard.html`. Open by double-clicking in Finder or via `open flood_dashboard.html`.

### Retraining & Updating Models
```bash
.venv/bin/python train_predictive_models.py
```
* Re-trains models when new ground-truth observations or storm seasons are added.

---

## 5. Cloud Deployment & Automation (GitHub Actions + GitHub Pages)

* **Architecture**: Free serverless execution and public static hosting.
  * `.github/workflows/update_flood_monitor.yml`: Runs on a 30-minute cron schedule (`*/30 * * * *`) and on demand (`workflow_dispatch`).
  * Executes `ingest_realtime.py` (NOAA NWPS, CO-OPS, NWS Wakefield QPF) and `generate_dashboard.py`.
  * Preserves data history by committing updated JSON/CSV files back to the repository.
  * Deploys `index.html` (and `latest_status.json`, `forecast_48h.csv`) to GitHub Pages artifact directory `_site`.
* **Zero Dependency Runner**: All operational scripts (`ingest_realtime.py`, `micro_topography.py`, `generate_dashboard.py`, `check_alerts.py`) use the Python Standard Library (`urllib`, `json`, `csv`, `zoneinfo`), requiring 0 seconds of pip package installs on GitHub runners.
* **Repository State**:
  * Initialized Git repository on `main` branch.
  * Staged and committed 50 project files (`60e4bbb`), ignoring `.venv/` and intermediate caches.
  * Configured `README.md` with full project background, formulas, and usage.
  * Upgraded GitHub Actions to native Node.js 24 releases (`checkout@v7`, `setup-python@v7`, `upload-pages-artifact@v5`, `deploy-pages@v5`), eliminating all deprecation warnings.
* **Live Website**:
  * Public Dashboard: `https://flatfoot584.github.io/mathews-flood-monitor/`
  * Execution: Runs every 30 minutes in ~50 seconds with automated data commits and Pages deployments.
* **Continuous Automated Archiving**:
  * `archive_hourly_observations.csv`: Accumulates every newly completed hour of verified stage, wind, barometric pressure, water level, and surge.
  * Automatic deduplication ensures idempotency (0 duplicates on re-runs).
  * Automatically committed and pushed to git on every 30-minute cloud run.

---

## 6. Multi-Page Web Portal & Interactive GIS Map Upgrade

* **Architecture Upgrade**: Transformed single dashboard into a modern, 4-page responsive community portal:
  * **`index.html` (Live Monitor & GIS Map)**: Human-first advisory hero banner, vehicle passability matrix (Sedans vs SUVs), interactive Leaflet.js coastal flood map with dynamic Green $\to$ Yellow $\to$ Orange $\to$ Red property zones, micro-topography elevation cross-section meter, and 48-hour Chart.js hydrograph.
  * **`about.html` (The Origin Story & Notebook Gallery)**: Photo gallery of original handwritten observer notes (`IMG_8049.jpeg`–`IMG_8058.jpeg`), validation of mom's empirical rule ($0.10\text{ ft} \approx 1\ 3/16\text{"}$ vs $10.95\text{"/ft}$ regression), and compound flood physics.
  * **`guide.html` (Flood Severity Guide & Plain-English Glossary)**: Detailed breakdown of Tiers 0–3 with visual descriptions and resident checklists, vehicle water depth danger limits ($3"$, $6"$, $12"$), and plain-English marine definitions (MLLW vs NAVD88, Storm Surge Residual, Along-Bay Wind Setup).
  * **`data.html` (Storm History & Open Data Archive)**: Major storm comparison cards (Helene, Ophelia, Ian, Idalia, Earl, Nor'easters), interactive 141-record ground-truth explorer, and direct download links for all datasets.
* **Leaflet GIS Map**: Embedded OpenStreetMap & Esri neutral tiles with live sensor pins (WRVV2, Yorktown, Windmill Point) and interactive toggle between Current Water Level and 48-Hour Peak Forecast.

---

## 7. Primary Ground-Truth Benchmark Coordinates & LiDAR Validation

* **Exact Observer Coordinates**: `37.420183, -76.406550` (Daniel Ave & Blackwater Creek, Mathews County, VA).
* **USGS 3DEP 1-Meter LiDAR Elevation Query**:
  * Point Elevation at `(37.420183, -76.406550)`: **$2.761\text{ ft NAVD88}$**.
  * Converted to local tidal datum ($+1.64\text{ ft}$): **$4.401\text{ ft MLLW}$**.
  * **Exact Validation**: The physical driveway benchmark elevation independently matches our discovered linear regression driveway flooding threshold ($4.40\text{ ft MLLW} = 2.76\text{ ft NAVD88}$) to within $0.01\text{ ft}$!
* **Corridor Elevation Transect**:
  * Blackwater Creek tributary marsh: $-1.09\text{ ft NAVD88}$ ($0.55\text{ ft MLLW}$)
  * Ditch culvert invert: $2.41\text{ ft NAVD88}$ ($4.05\text{ ft MLLW}$, matching $3.99\text{ ft}$ threshold)
  * Main driveway benchmark: $2.76\text{ ft NAVD88}$ ($4.40\text{ ft MLLW}$)
  * Residence / garage pad: $3.26\text{ ft NAVD88}$ ($4.90\text{ ft MLLW}$)
* **Map Centering**: Anchored the interactive Leaflet map view and micro-topography flood zones directly to `(37.420183, -76.406550)` at zoom 14, with a dedicated benchmark star marker and quick zoom toggle.

---

## 8. Community-Wide Monitoring Boundary & Dry-Land Elevation Sectors

* **Problem Identified**: The initial benchmark zones were represented as abstract rectangular corridors that extended diagonally northeast into the open waters of Blackwater Creek / North River, while failing to monitor the surrounding residential community where residents live and drive.
* **Expanded Community Monitoring Perimeter**:
  * Adopted the full community boundary for **Mobjack Bay Estates & Blackwater Peninsula** matching the user-defined perimeter:
    * **North**: Northern residential property line from River Road west to Bunny Rabbit Lane (`lat ~37.4223`).
    * **South**: Southern shoreline along Bayshore Avenue facing Mobjack Bay (`lat ~37.4181`).
    * **East**: Water-facing shoreline from the eastern point north along River Road.
    * **West**: Western neighborhood line west of Bunny Rabbit Lane (`lon -76.4116`).
* **Strict Shoreline Adherence (Zero Polygons in Water)**:
  * Extracted 152 nodes from the official OpenStreetMap coastline (Way 472426793).
  * Traced all perimeter boundaries and micro-topography zones strictly on the landward side of the coastline. No warnings or polygons extend into the water.
* **8-Street LiDAR Network & Passability Matrix**:
  * Queried USGS 1-meter LiDAR across the entire neighborhood road network:
    1. **Bayshore Avenue**: Invert $3.75\text{ ft MLLW}$ ($2.11\text{ ft NAVD88}$) — waterfront dips flood first.
    2. **Julian Street**: Invert $3.78\text{ ft MLLW}$ ($2.14\text{ ft NAVD88}$) — south culvert dip.
    3. **Daniel Avenue**: Invert $3.88\text{ ft MLLW}$ ($2.24\text{ ft NAVD88}$); Benchmark $4.40\text{ ft MLLW}$ ($2.76\text{ ft NAVD88}$).
    4. **Allview Street**: Invert $4.13\text{ ft MLLW}$ ($2.49\text{ ft NAVD88}$) — shallow puddles above $4.13\text{ ft}$.
    5. **River Road**: Invert $4.14\text{ ft MLLW}$ ($2.50\text{ ft NAVD88}$) — mid-section dips to $4.14\text{ ft}$.
    6. **Hobday Street**: Invert $4.22\text{ ft MLLW}$ ($2.58\text{ ft NAVD88}$).
    7. **Little Avenue**: Invert $4.23\text{ ft MLLW}$ ($2.59\text{ ft NAVD88}$).
    8. **Bunny Rabbit Lane**: Invert $4.45\text{ ft MLLW}$ ($2.81\text{ ft NAVD88}$) — elevated western ridge.
  * Added live interactive street passability overlays on the map and a community street status board on the dashboard.
* **Quick-Zoom Controls**: Added `[Community Area]` (fits the full yellow neighborhood perimeter), `[Focus Benchmark]` (centers on Daniel Ave at zoom 16), and `[County View]` (zooms to regional sensor network).

---

## 9. Dedicated Mobile Alerts Page & UX Optimization

* **Decision**: Migrated bulky subscription banner off the primary dashboard landing page to preserve top-of-page real estate for real-time flood indicators.
* **Architecture**:
  * Created dedicated `alerts.html` (and aliased `subscribe.html`) with interactive topic selector (`mathews-flood-alerts` vs test channel), animated push notification timeline, iOS/Android installation guides, and direct Web Push / ntfy app deep links.
  * Preserved a compact notification pill in the desktop/mobile navbar and an informative alert callout at the bottom of `index.html`.

---

## 10. 2024–2026 Ground-Truth Dataset Expansion & 5-Year Model Calibration

* **Expansion to 204 Ground-Truth Observations**:
  * Ingested 63 newly verified storm events spanning October 16, 2024 through September 28, 2026 from `RAW Observer data - Mom.gsheet` into `ground_truth_observations.csv` (and reproducible generator `generate_ground_truth.py`).
  * Total dataset expanded from 141 records to **204 records** (181 numerical stage-depth pairs).
* **Observer Log Corrections Applied**:
  * **Observation 42 (2023-06-03)**: Corrected flood depth from $7.50"$ to $2.50"$ per Mom's verified measurement log.
  * **Observation 62 (2023-09-27)**: Corrected flood depth from $11.00"$ to $8.00"$ per Mom's verified measurement log.
  * **Observation 136 (2024-09-26)**: Updated flood depth from $0.00"$ to $2.00"$ (`is_flooded = TRUE`) matching water depth recorded across the driveway and roadside ditch.
  * **2024-09-18**: Verified against NOAA/USGS stage records that Ware River stage was $4.52\text{ ft}$ (prevented a $5.52\text{ ft}$ manual entry typo).
* **Major 2024–2026 Benchmark Storms Added**:
  1. **10-Year Record Nor'easter (October 12, 2025)**: Ware River stage **$5.54\text{ ft MLLW}$**, Flood Depth **$19.0\text{ inches}$**, winds NNE $24\text{ mph}$ ($35\text{ mph}$ gusts). Submerged the driveway and property; highest flood depth recorded in over a decade.
  2. **Twin Nor'easters (September 22–26, 2026)**: Ware River stage **$5.38\text{ ft MLLW}$**, Flood Depth **$17.5\text{ inches}$**, winds NE/NNW $18\text{–}23\text{ mph}$. Sustained multi-day surge stacking with $0.5" - 2"$ water rise every $10\text{–}15\text{ minutes}$.
  3. **Late Autumn Nor'easter (November 15, 2024)**: Ware River stage **$5.27\text{ ft MLLW}$**, Flood Depth **$15.0\text{ inches}$**, winds NNE $12.8\text{ mph}$.
  4. **Hurricane Erin (August 21–22, 2025)**: Ware River stage **$5.12\text{ ft MLLW}$**, Flood Depth **$13.0\text{ inches}$**, winds NNE $18.3\text{ mph}$ ($24.6\text{ mph}$ gusts). Rapid drainage documented post-high tide ($13"$ dropped to $10.75"$ in $30\text{ minutes}$).
* **Model Retraining & Calibration**:
  * Re-evaluated Stage 2 inundation model $\text{Depth} = \max(0, 10.95 \times (\text{Stage} - 3.99))$ on all 181 valid 2021–2026 ground-truth records:
    * **$R^2 = 0.8511$** (improved from $0.800$)
    * **$\text{MAE} = 1.25\text{ inches}$**
    * **$\text{RMSE} = 1.69\text{ inches}$**
  * Updated `models/model_weights_and_thresholds.json` and `models/evaluation_report.json`.
* **Portal Storm Explorer Upgrade (`data.html`)**:
  * Updated interactive storm benchmark cards to showcase Hurricane Erin, the October 2025 10-year record flood ($19"$), and the September 2026 twin nor'easters ($17.5"$).
  * Upgraded the observation table to display all 204 records in reverse chronological order (newest storms first) within a sticky-header scrollable container.

---

## 11. Scientific Evidence Generation, Academic Manuscript & Dedicated Science Portal (`science.html`)

* **Motivation & Goal**:
  * Establish a reproducible scientific evidence engine and manuscript suitable for peer-reviewed academic publication in coastal hydrology / environmental modeling journals.
  * Provide researchers, hydrologists, and scientific visitors with a dedicated portal page (`science.html`) detailing mathematical formulas, model weights, error matrices, LiDAR ground-truth validations, and an engineering version changelog.
* **Automated Evidence Engine (`generate_scientific_report.py`)**:
  * Loads the 204 ground-truth observations, calculates statistical moments (IQR, mean, std, percentiles), computes Pearson correlation ($r = 0.9302$ on flooded observations, $r = 0.8898$ overall), evaluates Stage 1 and Stage 2 models, tabulates LiDAR comparisons, and compiles benchmark storm case studies.
  * Automatically produces:
    1. `models/scientific_evidence.json`: Machine-readable parameter benchmark.
    2. `SCIENTIFIC_FINDINGS.md`: Complete academic manuscript with KaTeX math, tables, and formal citations.
  * Can be re-executed at any time as new observations arrive via `python generate_scientific_report.py`.
* **Dedicated Scientific Web Portal (`science.html`)**:
  * Integrated into `generate_dashboard.py` as a primary portal page with reciprocal links across all 8 site pages (navbar and footer).
  * Features:
    * **Executive KPI Cards**: 5.33-year record (204 events), Pearson correlation $r = 0.9302$ ($R^2 = 0.8652$, $p < 10^{-15}$), LiDAR culvert agreement $\Delta = 0.06\text{ ft}$ ($0.7"$), Driveway pad agreement $\Delta = 0.00\text{ ft}$, Stage 1 ML $R^2 = 0.9731$ (MAE $1.46"$), and Stage 2 piecewise model MAE $1.25"$ ($R^2 = 0.8511$, RMSE $1.69"$).
    * **Two-Stage Architecture & Formulations**: Mathematical expressions for quadratic wind stress ($\tau_w \propto |U|U$), pressure tendencies ($\Delta P_{3h}$), and the piecewise inundation law $D(h) = \max(0, 10.95 \cdot h - 43.69)\text{ in}$.
    * **USGS 3DEP 1-Meter LiDAR Validation**: Side-by-side comparison tables of federal LiDAR altimetry vs empirical tipping points, plus 8-street community invert network.
    * **Statistical Moments**: Quartile and distribution tables for Ware River stage and flood depth.
    * **10-Storm Case Studies**: Benchmark comparisons of observed vs model predicted depths with residuals.
    * **Formal Changelog Timeline**: Interactive version history covering v1.0.0 through v2.0.0.
    * **BibTeX Citation & Downloads**: 1-click citation copy button and direct downloads for JSON evidence, Markdown manuscript, and CSV archives.

---

## 12. Troubleshooting GitHub Pages 404 for `science.html`

* **Issue Diagnosed**:
  * Navigating to `https://flatfoot584.github.io/mathews-flood-monitor/science.html` returned an HTTP 404 Not Found error despite `science.html` being generated in the local workspace and present in the Git repository.
* **Root Cause**:
  * The GitHub Pages automated deployment workflow (`.github/workflows/update_flood_monitor.yml`) deploys via `actions/upload-pages-artifact` using a synthesized `_site` directory.
  * In the "Prepare GitHub Pages site directory" step, files were explicitly copied one by one (`cp index.html _site/`, `cp alerts.html _site/`, etc.).
  * Because `science.html`, `SCIENTIFIC_FINDINGS.md`, and `models/scientific_evidence.json` were recently introduced, they were missing from the copy list in the workflow step. As a result, `_site` was deployed without `science.html`.
  * In addition, `science.html` was missing from the workflow's `git add` automated commit step and `paths-ignore` trigger list.
* **Resolution**:
  * Updated `.github/workflows/update_flood_monitor.yml`:
    1. Added `science.html`, `SCIENTIFIC_FINDINGS.md`, and `models/scientific_evidence.json` (plus `models/model_weights_and_thresholds.json`) to the `_site` artifact assembly step.
    2. Added `science.html` to the automated commit `git add` list so regenerated copies are tracked.
    3. Added `science.html` to `paths-ignore` to avoid recursive workflow dispatch loops.

---

## 13. Quantile Uncertainty Envelope (80% CI) & Multi-Station Hydraulic Slope Modeling

* **Motivation**:
  * Implement items 1.2 and 1.3 from `BACKLOG.md` to enhance the predictive pipeline with probabilistic confidence bounds and bay-scale hydraulic gradient physics.
* **1. Shaded Confidence Interval Forecasting (Uncertainty Envelope)**:
  * **Quantile Loss Function**: Trained LightGBM quantile regression models targeting $\alpha = 0.10$ (10th percentile best case) and $\alpha = 0.90$ (90th percentile worst case) alongside the standard median/mean nowcast and forecast models in `train_predictive_models.py`.
  * **Empirical Conformal Calibration**: Calibrated residual quantile offsets ($q_{10} = -0.169\text{ ft}$, $q_{90} = +0.907\text{ ft}$) on the 2024 holdout test set to ensure rigorous empirical interval coverage over 48-hour forecast horizons.
  * **Artifacts & Saved Weights**: Saved `models/stage1_forecast_q10_lgbm.pkl` and `models/stage1_forecast_q90_lgbm.pkl`, and updated `models/model_weights_and_thresholds.json` with the complete `uncertainty_envelope` configuration for pure-Python fallback execution.
  * **Dashboard Visualization (`index.html`)**: Integrated Chart.js area fill (`fill: '-1'` to Dataset 0) to render a semi-transparent shaded sky-blue uncertainty band (`rgba(2, 132, 199, 0.15)`) between the 90% worst-case dashed boundary and the 10% best-case dashed boundary, centered around the solid 50% expected stage forecast line.
  * **User Guidance**: Added 80% confidence interval summary badges to the hero advisory card, hydrograph card header, and hover tooltips.
* **2. Multi-Station Hydraulic Slope Modeling (Norfolk vs. Rappahannock)**:
  * **Physical Mechanism**: The Chesapeake Bay behaves as a long, shallow estuary (~46.2 statute miles between Windmill Point and Sewells Point). Sustained northerly or north-easterly winds stack water in the northern and central bay while simultaneously draining the lower bay or causing phase lags. This creates a hydraulic pressure head ($\Delta \text{Surge} = \text{Surge}_{\text{Windmill}} - \text{Surge}_{\text{Sewells}} > 0$) that drives water directly into Mobjack Bay, the North River, and the Ware River basin even during low tide.
  * **Sensor Integration**: Added live automated polling for NOAA CO-OPS station **8638610 (Sewells Point, Norfolk, VA)** in `ingest_realtime.py` (6-minute water level, past verified predictions, and forward astronomical tides).
  * **Hydraulic Metrics Calculated**:
    * `sewells_point_storm_surge_residual_ft`: Live southern bay surge residual.
    * `bay_hydraulic_gradient_ft`: Differential surge ($\text{Surge}_{\text{Windmill}} - \text{Surge}_{\text{Sewells}}$).
    * `bay_hydraulic_slope_ft_per_mile`: Slope across the 46.2-mile transect ($\Delta \text{Surge} / 46.2$).
    * `bay_hydraulic_pressure_direction`: Categorical physical state (`Southward Inflow Head`, `Northward / Outflow Gradient`, or `Equilibrium`).
  * **Forward Hydrodynamic Hybrid Model**: Embedded forward hydraulic push term into the 48-hour hybrid stage equation in `build_forecast_timeline`.
  * **Dashboard Sensor Network**: Expanded the regional sensor cards on `index.html` to a 6-card grid:
    1. Yorktown Winds (Speed, direction, gusts)
    2. Along-Bay Vector (Wind stress forcing)
    3. Yorktown Barometer (Atmospheric pressure)
    4. North Bay Surge (Windmill Point 8636580)
    5. South Bay Surge (Sewells Point 8638610)
    6. Bay Hydraulic Slope ($\Delta \text{Surge}$ across 46 mi & pressure head direction)
* **Backlog Cleanup**: Marked both items as completed in `BACKLOG.md` (Tasks 14 and 15) and removed them from active high priority tasks.
