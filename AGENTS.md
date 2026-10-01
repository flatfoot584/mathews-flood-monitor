# AGENTS.md — Assistant Guide for Mathews County Flood Prediction Project

> **Project Goal**: Build an automated data collection pipeline and machine learning model to predict hyper-local coastal and tidal flooding (water depth in inches and inundation duration) in Mathews County, Virginia.

---

## 1. Geographic & Hydrologic Context

* **Location**: Mathews County, Virginia (Middle Peninsula).
* **Surrounding Water Bodies**:
  * **Chesapeake Bay** to the East.
  * **Mobjack Bay** to the South (fed by the East, North, Ware, and Severn Rivers).
  * **Piankatank River** to the North.
* **Topography**: Extremely low-lying coastal plain (much of the populated land is $< 5\text{ to }10\text{ ft}$ above NAVD88 elevation).
* **Flood Mechanism**: **Compound flooding** driven by:
  1. **Astronomical Tides**: Semi-diurnal tides with high sensitivity to spring tides, lunar perigee, and King Tides.
  2. **Meteorological Surge (Wind Set-Up)**: Persistent winds from **NNE, NE, E, and SE** force water down the Chesapeake Bay and drive water into Mobjack Bay, creating surge that cannot drain during low tide.
  3. **Pluvial / Precipitation Inundation**: Heavy rain creates ditch flooding when elevated bay water blocks gravity drainage.
  4. **Offshore Westerly Winds**: Winds from the W/SW push water out of Mobjack Bay, mitigating high tides.

---

## 2. Sensor & Gauge Registry

| Station Identifier | Agency / Network | Location | Measured Parameters | Role in Model |
| :--- | :--- | :--- | :--- | :--- |
| **WRVV2 / USGS 01670180** | NOAA NWS / USGS | Ware River near Schley, VA | River stage (ft), 6-min intervals | **Primary local hydrological reference gauge** |
| **8637689** | NOAA CO-OPS | Yorktown USCG Training Center, VA | Hourly wind speed, direction, gusts, pressure, air temp; predicted tides | **Primary meteorological forcing station** |
| **8636580** | NOAA CO-OPS | Windmill Point, VA | Hourly predicted & verified water levels | **Northern mouth of Rappahannock / Chesapeake reference** |
| **8638610** | NOAA CO-OPS | Sewells Point (Norfolk), VA | Water level, surge, winds | **Southern Chesapeake Bay storm surge reference** |
| **CBOFS** | NOAA / NOS | Chesapeake Bay Operational Forecast System | 48-hr hydrodynamic water level and current forecasts | **Primary forward-looking surge model guidance** |

---

## 3. Ground-Truth Dataset: `ground_truth_observations.csv`

The core asset of this project is a continuous human observation log recorded between **May 2021 and September 2024** (141 entries, 121 depth records):
* **Source**: Handwritten logs in `Photos of observations/` (Pages 1–8 + sticky notes) and `RAW Observer data - Mom.gsheet`.
* **Columns**:
  * `observation_id`: Unique integer.
  * `date`: YYYY-MM-DD.
  * `time_local`: Local time (EST/EDT) when recorded.
  * `time_qualifier`: AM, PM, or exact timestamp.
  * `page_source`: Originating notebook page or sticky note.
  * `ware_river_stage_ft`: Reading from the Ware River gauge (WRVV2) at time of observation.
  * `flood_depth_in`: Measured water depth in inches at the observation point.
  * `is_flooded`: `TRUE` if depth $> 0$, `FALSE` if depth $= 0$.
  * `wind_direction`, `wind_speed_mph`, `wind_gust_mph`: Wind conditions.
  * `weather_system`: Named storm or event (Helene, Ian, Idalia, Ophelia, Earl, SC Low, Snow).
  * `astronomical_event`: King Tide, Full Moon, Lunar Perigee, Eclipse.
  * `raw_notes`: Raw text transcription.

---

## 4. Discovered Physical Rules & Thresholds

From linear and exploratory analysis on the ground-truth observations:

1. **Flooding Threshold**: **$3.99\text{ ft}$** on the Ware River gauge.
   * $\text{Stage} < 4.0\text{ ft} \implies$ Water remains in ditches/marshes ($0"$ flood depth).
   * $\text{Stage} \ge 4.0\text{ ft} \implies$ Water breaches banks and begins covering the yard/road.
2. **Inundation Slope**: **$10.95\text{ inches of water per foot of gauge rise}$** ($\approx 1.1\text{ to }1.2\text{ in}$ per $0.10\text{ ft}$ rise).
   * Confirms the observer's handwritten conversion: $0.10\text{ ft} \approx 1\ 3/16\text{"}$ to $1.25\text{"}$.
3. **Correlation**: $r = 0.912$ ($R^2 = 0.832$). Residual variance is explained by wind direction, wind duration, and barometric pressure drops.
4. **Risk Severity Tiers**:
   * **Tier 0 (Normal / Safe)**: Ware River $< 4.0\text{ ft} \to 0"$ flooding.
   * **Tier 1 (Nuisance / Ditch Full)**: Ware River $4.0 - 4.3\text{ ft} \to 1" - 4"$ in low spots and ditches.
   * **Tier 2 (Moderate Inundation)**: Ware River $4.4 - 4.7\text{ ft} \to 5" - 8"$ on driveway/road (passenger cars blocked).
   * **Tier 3 (Severe Inundation)**: Ware River $\ge 4.8\text{ ft} \to 9" - 15"+$ across the property (trucks/SUVs only or impassable).

---

## 5. System Architecture Roadmap

```
Phase 1 (Complete): Ground-Truth Extraction & Baseline Statistics
  └─ Transcribe notebook photos to ground_truth_observations.csv
  └─ Establish documentation (AGENTS.md, FINDINGS_AND_DECISIONS.md)

Phase 2 (Complete): Historical Data Backfill & Alignment
  └─ Batch queried IEM HML API for full 2021-2024 Ware River hydrograph (01670180/WRVV2)
  └─ Aligned NOAA CO-OPS Yorktown & Windmill Point hourly data
  └─ Constructed unified hourly ML dataset: merged_hourly_training_dataset.csv (32,833 records)

Phase 3 (Complete): Automated Real-Time Ingestion Pipeline
  └─ Python collector script: ingest_realtime.py
  └─ Fetches live 6-min Ware River stage (NWPS API) + 4-day forecast hydrograph
  └─ Fetches live Yorktown USCG met/water & Windmill Point storm surge residual
  └─ Fetches NWS AKQ 156-hr hourly wind forecast
  └─ Outputs latest_status.json, realtime_recent_observations.csv, forecast_48h.csv

Phase 4 (Complete): Predictive Machine Learning Models
  └─ Training pipeline: train_predictive_models.py
  └─ Stage 1 Nowcasting: R² = 0.973, MAE = 1.5 inches (tested on 2024 holdout storms)
  └─ Stage 1 Forecasting: R² = 0.721, MAE = 4.8 inches (astronomical tide + quadratic wind stress)
  └─ Stage 2 Local Inundation: R² = 0.800, MAE = 1.22 inches on ground truth
  └─ Saved deployable model config: models/model_weights_and_thresholds.json & models/*.pkl

Phase 5 (Complete): Notification, Alerting & Hazard Monitoring
  └─ Alert generation script: check_alerts.py (with macOS desktop --notify banner)
  └─ Compound pluvial & micro-topography engine: micro_topography.py
  └─ Standalone interactive web dashboard: generate_dashboard.py & flood_dashboard.html
  └─ Long-term project roadmap: BACKLOG.md
```

---

## 6. Agent Working Guidelines

1. **Maintain Documentation**:
   * Always log major decisions, code additions, and findings in `FINDINGS_AND_DECISIONS.md`.
   * Update this `AGENTS.md` file whenever pipeline architecture or schemas evolve.
2. **Preserve Ground-Truth Integrity**:
   * Never overwrite or alter original raw data in `ground_truth_observations.csv` without documenting the exact change.
3. **Timezone & Unit Consistency**:
   * Timestamps: Convert all external APIs (which often default to UTC/GMT) to local Eastern Time (`America/New_York`), explicitly labeling EST or EDT.
   * Units: Water levels and gauge stages in **feet (ft)**; ground inundation in **inches (in)**; wind speeds in **mph** (convert knots $\times 1.15078$).
4. **Offline Resilience**:
   * Cache all downloaded API data locally in CSV or Parquet files so future runs or disconnected environments do not break.
