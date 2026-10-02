# BACKLOG.md — Mathews County Coastal Flood Prediction Project

This document tracks future features, architectural improvements, and backlog tasks to be implemented over time.

---

## 1. Active High Priority Tasks

### 1.1 Auxiliary Notification Channels (Discord / Slack Webhooks & Twilio SMS)
- **Status**: Mobile push notifications via **ntfy.sh** are fully operational (see [Task 8](#3-completed-milestones) & [Task 12](#3-completed-milestones)). This item tracks optional supplementary delivery channels:
  - **Discord / Slack Webhook**: Post real-time flood warning cards with vehicle passability to a private family or community channel (Free, zero setup).
  - **Twilio SMS / Email**: Automated emergency text messages or email alerts to designated family phone numbers.

---

## 2. Medium Priority Tasks

### 2.1 Mobile Ground-Truth Observation Submission Tool
- **Task**: A simple, mobile-friendly web form where family or neighbors can submit ground observations (timestamp + depth in inches + optional photo) directly from their smartphone.
- **Functionality**: Automatically appends new records into `ground_truth_observations.csv` for continuous ML model training.

### 2.2 Automated Periodic Model Retraining Workflow
- **Task**: A scheduled GitHub Actions workflow that periodically runs `train_predictive_models.py` using `archive_hourly_observations.csv` and updated ground truth records to continually re-calibrate model weights as new seasons pass.

---

## 3. Completed Milestones

- [x] **Task 1: Ground-Truth Dataset Digitization & Baseline Statistics**
  - Digitized handwritten notebook logs and photos into structured, machine-readable format (`ground_truth_observations.csv`).
  - Derived empirical physical rules: $3.99\text{ ft}$ zero-flood threshold, $10.95\text{"/ft}$ inundation slope, validating the observer's handwritten conversion ($0.10\text{ ft} \approx 1\ 3/16\text{"}$ to $1.25\text{"}$).

- [x] **Task 2: Historical Data Backfill & Alignment (2021–2024)**
  - Batch queried the IEM HML archive to recover the full 2021–2024 6-minute Ware River hydrograph (01670180 / WRVV2, 285k rows).
  - Aligned NOAA CO-OPS Yorktown met/wind and Windmill Point tide/surge data to create a unified 32,833-row hourly training dataset (`merged_hourly_training_dataset.csv`).

- [x] **Task 3: Automated Real-Time Ingestion Pipeline**
  - Built `ingest_realtime.py` querying NOAA NWPS (6-min stage & 4-day CBOFS hydrograph), NOAA CO-OPS (live met/winds/surge), and NWS Wakefield QPF rainfall.
  - Outputs `latest_status.json`, `realtime_recent_observations.csv`, and `forecast_48h.csv`.

- [x] **Task 4: Predictive Machine Learning Models**
  - Built two-stage predictive architecture (`train_predictive_models.py`): Stage 1 Nowcasting ($R^2 = 0.973$, MAE $1.5"$) and Stage 1 Forecasting ($R^2 = 0.721$, MAE $4.8"$).
  - Exported zero-dependency model configuration (`models/model_weights_and_thresholds.json`) for pure-Python execution.

- [x] **Task 5: Alert Generation & Micro-Topography Engine**
  - Created multi-tier coastal flood bulletin generator (`check_alerts.py`) evaluating Tiers 0–3, onset, crest, and drainage duration.
  - Modeled compound pluvial backwater and site elevation profile in `micro_topography.py`.

- [x] **Task 6: Serverless Cloud Execution & Public Web Hosting**
  - Deployed GitHub Actions workflow (`.github/workflows/update_flood_monitor.yml`) running on a 30-minute cron schedule.
  - Hosted public live dashboard on GitHub Pages: `https://flatfoot584.github.io/mathews-flood-monitor/`.

- [x] **Task 7: Continuous Automated Data Archiving**
  - Implemented automated accumulation of verified hourly stage, met, and surge data (`archive_hourly_observations.csv`) with automatic deduplication committed back to Git on every 30-minute run.

- [x] **Task 8: Automated Mobile Push Alerting (ntfy.sh Integration)**
  - Integrated zero-cost, zero-account mobile push notification system via `ntfy.sh` (topic `mathews-flood-23128`).
  - Added stateful anti-spam deduplication (`alert_state.json`), pre-crest 2-hour warnings, and GitHub Actions cron execution.

- [x] **Task 9: Multi-Page Community Portal & Interactive GIS Leaflet Map**
  - Upgraded standalone dashboard to a comprehensive 5-page portal (`index.html`, `alerts.html`, `about.html`, `guide.html`, `data.html`).
  - Embedded Leaflet.js GIS map with OpenStreetMap & Esri neutral tiles, live sensor pins (WRVV2, Yorktown, Windmill Point), and Current vs 48-Hour Peak toggles.
  - Added plain-English resident guides, vehicle danger limits, photo gallery of original observer notes, and storm comparison charts.

- [x] **Task 10: USGS 3DEP 1-Meter LiDAR Elevation Ground-Truth Validation**
  - Queried official USGS 3DEP 1-meter LiDAR for primary observation benchmark at Daniel Ave & Blackwater Creek (`37.420183, -76.406550`).
  - Discovered physical driveway elevation is exactly $2.761\text{ ft NAVD88} \equiv 4.401\text{ ft MLLW}$, independently confirming our linear regression driveway flooding threshold ($4.40\text{ ft MLLW}$) to within $0.01\text{ ft}$.

- [x] **Task 11: Community-Wide Monitoring Boundary & 8-Street LiDAR Network**
  - Expanded monitored area to encompass the full Mobjack Bay Estates & Blackwater Peninsula residential community (River Rd to Bunny Rabbit Ln, Bayshore Ave north to property lines).
  - Traced strict landward boundary along 152 OpenStreetMap coastline nodes to ensure zero flood warnings or polygons extend into open water.
  - Queried LiDAR for 8 community streets (Bayshore, Julian, Daniel, Allview, River, Hobday, Little, Bunny Rabbit) and built an interactive street passability status board and map overlays.

- [x] **Task 12: Dedicated Mobile Alerts Page & UX Optimization (`alerts.html`)**
  - Streamlined `index.html` by migrating large subscribe banner to dedicated `alerts.html` (and aliased `subscribe.html`).
  - Added high-res QR code, topic selector, interactive lock-screen alert simulator, and step-by-step iOS, Android, and Web setup guides.

- [x] **Task 13: 2024–2026 Ground-Truth Dataset Expansion (204 Records) & 5-Year Model Recalibration**
  - Ingested 63 newly verified storm events from `RAW Observer data - Mom.gsheet` through September 2026, expanding the dataset from 141 to 204 records (181 numerical stage-depth pairs).
  - Documented major historical storms: Hurricane Erin ($13"$), October 2025 10-year record nor'easter ($19"$, $5.54\text{ ft}$), and September 2026 twin nor'easters ($17.5"$, $5.38\text{ ft}$).
  - Recalibrated Stage 2 inundation model on all 5 years of observations, boosting $R^2$ from $0.800$ to **$0.851$** (MAE $1.25"$, RMSE $1.69"$).
  - Upgraded `data.html` with new storm showcase cards and a 204-record scrollable sticky-header table.

- [x] **Task 14: Shaded Confidence Interval Forecasting (Uncertainty Envelope)**
  - Implemented LightGBM quantile regression models ($\alpha = 0.10$ and $\alpha = 0.90$) with empirical conformal residual adjustments in `train_predictive_models.py`.
  - Added 10th percentile (best case), 50th percentile (expected), and 90th percentile (worst case) stage and depth to `latest_status.json` and `forecast_48h.csv`.
  - Rendered a semi-transparent shaded uncertainty band around the 48-hour hydrograph curve on `index.html` using Chart.js area fill.

- [x] **Task 15: Multi-Station Hydraulic Slope Modeling (Norfolk vs. Rappahannock)**
  - Integrated NOAA Sewells Point (`8638610`) at the southern Chesapeake Bay mouth into `ingest_realtime.py`.
  - Calculated real-time bay hydraulic gradient ($\Delta \text{Surge} = \text{Surge}_{\text{Windmill}} - \text{Surge}_{\text{Sewells}}$) and hydraulic slope across the 46.2-mile transect.
  - Modeled downward hydraulic pressure head forcing water into Mobjack Bay and the Ware River basin during north-bay surge stacking events.
  - Added Sewells Point and Bay Hydraulic Slope metric cards to the regional station grid on `index.html`.
