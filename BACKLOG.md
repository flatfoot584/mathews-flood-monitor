# BACKLOG.md — Mathews County Coastal Flood Prediction Project

This document tracks future features, architectural improvements, and backlog tasks to be implemented over time.

---

## 1. High Priority (Upcoming Sprints)

### 1.1 Automated Background Daemon & Continuous Execution
- **Task**: Create `run_daemon.py` and a macOS `launchd` plist service (`com.mathews.floodprediction.plist`).
- **Functionality**:
  - Automatically runs `ingest_realtime.py` and `generate_dashboard.py` every **15 to 30 minutes** in the background.
  - Keeps `latest_status.json` continuously fresh without requiring manual terminal execution.
  - Evaluates risk tier changes (e.g., transition from Tier 0 to Tier 1/2/3) and fires alerts.

### 1.2 Multi-Channel Phone & Webhook Alerting
- **Task**: Extend `check_alerts.py` to dispatch notifications to mobile devices.
- **Channels**:
  - **Pushover API**: Direct push notifications with priority tones to iOS/Android phones.
  - **Discord / Slack Webhook**: Post real-time flood warning cards to a community or family channel.
  - **Twilio SMS**: Send SMS text alerts for critical Tier 2 and Tier 3 flood thresholds.

### 1.3 Continuous Rolling Data Archiving
- **Task**: Automated append mechanism in `ingest_realtime.py`.
- **Why**: NOAA NWPS only maintains a rolling 30-day window of 6-minute stage readings.
- **Functionality**:
  - Append verified hourly records to a persistent `live_archive_2024_present.csv` without duplicate rows.
  - Ensures every upcoming storm and King Tide is permanently archived for future ML retraining.

---

## 2. Medium Priority (Data Science & Modeling)

### 2.1 Multi-Station Surge Gradient Modeling
- **Task**: Incorporate Sewells Point (8638610) and Lewisetta (8635750) into Stage 1 ML.
- **Rationale**:
  - Windmill Point (8636580) sits north at the Rappahannock mouth.
  - Sewells Point (8638610) sits south at the Chesapeake Bay mouth / Norfolk.
  - The surge difference ($\Delta \text{Surge} = \text{Surge}_{\text{Windmill}} - \text{Surge}_{\text{Sewells}}$) measures the hydraulic water slope forcing water into Mobjack Bay.

### 2.2 Probabilistic / Confidence Interval Forecasting
- **Task**: Implement quantile regression (or conformal prediction) in `train_predictive_models.py`.
- **Output**: 
  - 10th percentile (optimistic), 50th percentile (median), and 90th percentile (pessimistic) predicted stage and flood depth.
  - Displays a shaded uncertainty envelope on `flood_dashboard.html`.

### 2.3 Local Groundwater & Soil Saturation Integration
- **Task**: Incorporate USGS Middle Peninsula groundwater well observations or NASA SPoRT soil moisture.
- **Rationale**: Prolonged rainy periods saturate the shallow sandy water table, accelerating runoff into ditches.

---

## 3. Web & Community Features

### 3.1 GitHub Pages / Cloud Dashboard Hosting
- **Task**: Deploy `flood_dashboard.html` to a public or private GitHub Pages URL or Cloudflare Pages site.
- **Functionality**: Allows family members, neighbors, and emergency responders to view live conditions from any smartphone browser without needing local access to the Mac.

### 3.2 Crowd-Sourced / Mobile Observation Submission Portal
- **Task**: A lightweight web form where the observer or family members can submit a timestamp and measured depth in inches directly from their phone.
- **Functionality**: Automatically appends new records to `ground_truth_observations.csv`.

---

## 4. Completed Milestones (Archived)
- [x] **Task 1**: Formalize 141 ground-truth observations into machine-readable CSV (`ground_truth_observations.csv`).
- [x] **Task 2**: Backfill full 2021–2024 Ware River hourly hydrograph (31k rows) and construct unified training dataset (`merged_hourly_training_dataset.csv`, 32,833 records).
- [x] **Task 3**: Build automated multi-network real-time ingestion pipeline (`ingest_realtime.py`).
- [x] **Task 4**: Train and evaluate predictive ML models (Stage 1 Nowcast $R^2=0.973$, Stage 1 Forecast $R^2=0.721$, Stage 2 Inundation $R^2=0.800$).
- [x] **Task 5**: Build coastal flood alert generator (`check_alerts.py`) and standalone interactive web dashboard (`flood_dashboard.html`).
