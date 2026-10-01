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


