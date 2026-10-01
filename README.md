# Mathews County, Virginia Coastal Flood Prediction System 🌊

[![Update Mathews County Flood Monitor](https://github.com/flatfoot584/mathews-flood-monitor/actions/workflows/update_flood_monitor.yml/badge.svg)](https://github.com/flatfoot584/mathews-flood-monitor/actions/workflows/update_flood_monitor.yml)

A hyper-local, automated data collection pipeline, hybrid hydrodynamic–machine learning model, and real-time dashboard predicting coastal, tidal, and compound pluvial flooding for Mathews County, Virginia (Middle Peninsula, Mobjack Bay & Chesapeake Bay).

---

## 📍 Geographic & Physical Context

Mathews County lies on Virginia’s Middle Peninsula, surrounded by the **Chesapeake Bay**, **Mobjack Bay** (fed by the East, North, Ware, and Severn Rivers), and the **Piankatank River**. With much of the populated topography below $5\text{ to }10\text{ ft}$ NAVD88, flooding occurs via **compound drivers**:

* **Primary Ground-Truth Benchmark**: `37.420183, -76.406550` (Daniel Ave, Blackwater, Mathews County, VA) draining into Blackwater Creek and North River / Mobjack Bay.
* **USGS 1-Meter LiDAR Elevation Validation**:
  * Driveway Benchmark: **`2.761 ft NAVD88`** $\equiv$ **`4.401 ft MLLW`** (independently validates our empirical $4.40\text{ ft}$ regression threshold to within $0.01\text{ ft}$).
  * Roadside Ditch Culvert: **`2.41 ft NAVD88`** $\equiv$ **`4.05 ft MLLW`** (matches the $3.99\text{ ft}$ ditch brim tipping point).
  * Residence / Garage Pad: **`3.26 ft NAVD88`** $\equiv$ **`4.90 ft MLLW`** (matches the Tier 3 severe inundation mark).

1. **Astronomical Tides**: Semi-diurnal cycles amplified by Spring Tides, King Tides, and Perigee.
2. **Meteorological Surge (Wind Set-Up)**: Persistent winds from NNE, NE, E, and SE force water down Chesapeake Bay and pile it directly into Mobjack Bay.
3. **Pluvial Backwater Entrapment**: Heavy rainfall cannot drain by gravity when tidal ditches are backed up by elevated bay stages.
4. **Offshore Drain (W/SW Winds)**: Westerly winds blow water out of Mobjack Bay, acting as a mitigating force.

---

## 📊 Core Ground-Truth & Empirical Findings

Trained on a continuous human observation log recorded between **May 2021 and September 2024** (141 entries, 121 depth measurements across storms like Ian, Idalia, Ophelia, Helene, and Nor'easters) paired with 285,000 6-minute USGS/NOAA Ware River gauge readings (`ground_truth_observations.csv`):

* **Flooding Threshold**: **$3.99\text{ ft MLLW}$** ($\approx 2.35\text{ ft NAVD88}$) on the Ware River gauge (WRVV2 / USGS 01670180).
  * Stage $< 4.0\text{ ft} \implies$ Water remains in marsh channels and drainage ditches ($0"$ depth).
  * Stage $\ge 4.0\text{ ft} \implies$ Water breaches ditch banks and covers the property.
* **Inundation Rate**: **$10.95\text{ inches of water per foot of river rise}$** ($\approx 1.1\text{ to }1.2\text{ in}$ per $0.10\text{ ft}$).
* **Correlation**: $r = 0.912$ ($R^2 = 0.832$). Residual variance is explained by wind direction, wind duration, and barometric pressure drops.

### Risk Severity Tiers
* **Tier 0 (Safe / Normal)**: Stage $< 4.0\text{ ft} \to 0"$ flooding.
* **Tier 1 (Nuisance / Ditch Full)**: Stage $4.0 - 4.3\text{ ft} \to 1" - 4"$ in low spots and culverts.
* **Tier 2 (Moderate / Driveway Blocked)**: Stage $4.4 - 4.7\text{ ft} \to 5" - 8"$ on driveway (sedans blocked).
* **Tier 3 (Severe / Property Submerged)**: Stage $\ge 4.8\text{ ft} \to 9" - 15"+$ across yard (SUVs only or impassable).

---

## 🤖 Model Architecture & Performance

```
Stage 1: Ware River Stage Nowcast & 48-Hour Forecast
  ├── Stage 1 Nowcast (0-6h): R² = 0.973, MAE = 1.5 in
  │     └─ Features: Ware River stage + Yorktown winds + Windmill Point storm surge
  └── Stage 1 Forecast (6-48h): R² = 0.721, MAE = 4.8 in
        └─ Features: Astronomical predicted tide + Quadratic wind stress (NNE/NE/ENE/E)

Stage 2: Hyper-Local Ground Inundation Model
  ├── R² = 0.800, MAE = 1.22 in on ground-truth observations
  └── Piecewise threshold linear model: Depth = 10.95 × (Stage - 3.99 ft)

Compound Pluvial & Micro-Topography Engine (micro_topography.py)
  ├── Models ditch backwater restriction: β = clip((Stage - 3.8) / 0.4, 0, 1)
  ├── 5 Micro-elevation sectors: Ditches (2.5'), Apron (4.0'), Driveway (4.4'), Yard (4.6'), Garage (4.9')
  └── Vehicle Passability Matrix: Evaluates passenger cars vs. high-clearance trucks
```

---

## ☁️ Automated Cloud Architecture (GitHub Actions + Pages)

This repository runs completely autonomously in the cloud at **zero cost**:

* **GitHub Actions (`.github/workflows/update_flood_monitor.yml`)**:
  * Runs every **30 minutes** via cron (and manual dispatch).
  * Executes `ingest_realtime.py` (queries NOAA NWPS WRVV2, NOAA CO-OPS 8637689/8636580, NWS AKQ Wakefield).
  * Executes `generate_dashboard.py` to create a standalone, mobile-responsive dashboard.
  * Commits the latest JSON/CSV data files to git history.
  * Deploys `index.html` to **GitHub Pages**.

---

## 📁 Repository Structure

```
├── .github/workflows/
│   └── update_flood_monitor.yml      # 30-minute automated ingestion & deployment workflow
├── models/
│   ├── model_weights_and_thresholds.json # Deployable zero-dependency model parameters
│   └── *.pkl                             # Scikit-learn serialized models
├── ingest_realtime.py                # Multi-sensor real-time ingestion & forecast pipeline
├── micro_topography.py               # Compound pluvial & property elevation engine
├── generate_dashboard.py             # Standalone interactive dashboard HTML generator
├── check_alerts.py                   # CLI hazard bulletin & macOS desktop notification script
├── train_predictive_models.py        # Model training & validation pipeline
├── build_merged_training_dataset.py  # Historical multi-station dataset merger
├── backfill_ware_river_history.py    # IEM HML API scraper for 2021-2024 Ware River stage
├── ground_truth_observations.csv     # 141 ground-truth observer measurements (2021-2024)
├── merged_hourly_training_dataset.csv # 32,833 continuous hourly aligned training rows
├── latest_status.json                # Latest real-time status summary
├── realtime_recent_observations.csv  # Rolling recent observations
├── forecast_48h.csv                  # 48-hour forward hourly forecast
├── flood_dashboard.html              # Standalone interactive dashboard
├── index.html                        # GitHub Pages entrypoint
├── AGENTS.md                         # Architecture guide & system prompt context
├── FINDINGS_AND_DECISIONS.md         # Engineering logbook and physical discoveries
└── BACKLOG.md                        # Long-term feature roadmap
```

---

## 🚀 Local Quickstart

The entire operational pipeline uses the **Python Standard Library** with zero external pip dependencies:

```bash
# 1. Fetch real-time data & compute forecast
python3 ingest_realtime.py

# 2. Check flood status and trigger desktop notification (macOS)
python3 check_alerts.py --notify

# 3. Generate and view interactive dashboard
python3 generate_dashboard.py
open flood_dashboard.html
```
