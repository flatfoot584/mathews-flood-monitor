# BACKLOG.md — Mathews County Coastal Flood Prediction Project

This document tracks future features, architectural improvements, and backlog tasks to be implemented over time.

---

## 1. Active High Priority Tasks

### 1.1 Multi-Channel Phone & Webhook Alerting (Mobile Push Notifications)
- **Task**: Extend `check_alerts.py` (and the GitHub Actions pipeline) to dispatch alerts automatically when peak forecast stage $\ge 4.4\text{ ft}$ (Tier 2/3):
  - **Discord / Slack Webhook**: Post real-time flood warning cards with vehicle passability to a private family or community channel (Free, zero setup).
  - **Ntfy.sh / Pushover API**: High-priority push notification banners with audible alarms directly to iOS and Android smartphones (Zero app build required).
  - **Twilio SMS / Email**: Automated text or email alerts to designated family phone numbers.

### 1.2 Shaded Confidence Interval Forecasting (Uncertainty Envelope)
- **Task**: Implement quantile regression (or conformal prediction) in `train_predictive_models.py` and display on dashboard.
- **Output**:
  - 10th percentile (best case), 50th percentile (expected), and 90th percentile (worst case) stage and depth.
  - Renders a semi-transparent shaded uncertainty band around the 48-hour hydrograph curve on `index.html`.

### 1.3 Multi-Station Hydraulic Slope Modeling (Norfolk vs. Rappahannock)
- **Task**: Incorporate Sewells Point (8638610) at the Chesapeake Bay mouth to calculate the bay hydraulic gradient ($\Delta \text{Surge} = \text{Surge}_{\text{Windmill}} - \text{Surge}_{\text{Sewells}}$).
- **Physical Rationale**: When northern bay surge exceeds southern bay surge, a hydraulic pressure head pushes water directly into Mobjack Bay and the Ware River.

---

## 2. Medium Priority (Observation & Visual Enhancements)

### 2.1 Mobile Ground-Truth Observation Submission Tool
- **Task**: A simple, mobile-friendly web form where family or neighbors can submit ground observations (timestamp + depth in inches + optional photo) directly from their smartphone.
- **Functionality**: Automatically appends new records into `ground_truth_observations.csv` for continuous ML model training.

### 2.2 Interactive Micro-Topography Property Map (LiDAR Footprint)
- **Task**: An interactive site plan graphic or map on `index.html` illustrating water progression across the 5 property sectors (Ditches $\to$ Culvert Apron $\to$ Main Driveway $\to$ Yard $\to$ Residence) dynamically shaded based on the predicted hour.

### 2.3 Automated Monthly Model Retraining Workflow
- **Task**: A scheduled GitHub Actions workflow that periodically runs `train_predictive_models.py` using `archive_hourly_observations.csv` to continually calibrate model weights as new seasons pass.

---

## 3. Completed Milestones

- [x] **Task 1**: Formalize 141 ground-truth observations into machine-readable CSV (`ground_truth_observations.csv`).
- [x] **Task 2**: Backfill full 2021–2024 Ware River hourly hydrograph (31k rows) and construct unified training dataset (`merged_hourly_training_dataset.csv`, 32,833 records).
- [x] **Task 3**: Build automated multi-network real-time ingestion pipeline (`ingest_realtime.py`).
- [x] **Task 4**: Train and evaluate predictive ML models (Stage 1 Nowcast $R^2=0.973$, Stage 1 Forecast $R^2=0.721$, Stage 2 Inundation $R^2=0.800$).
- [x] **Task 5**: Build coastal flood alert generator (`check_alerts.py`), micro-topography engine (`micro_topography.py`), and standalone interactive web dashboard (`generate_dashboard.py` & `flood_dashboard.html`).
- [x] **Task 6**: Serverless Cloud Execution & Public Web Hosting (GitHub Actions 30-min cron + GitHub Pages deployment at `https://flatfoot584.github.io/mathews-flood-monitor/`).
- [x] **Task 7**: Continuous Automated Data Archiving (`archive_hourly_observations.csv` with automatic hourly deduplication and git commits).

