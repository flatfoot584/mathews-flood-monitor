# Empirical Validation and Compound Machine Learning Modeling of Hyper-Local Coastal Plain Inundation: A 5-Year Benchmark in Mathews County, Virginia

> **Author**: Mathews County Flood Prediction Project  
> **Location**: Middle Peninsula, Mathews County, Virginia (`37.420183, -76.40655`)  
> **Study Period**: 2021-05-29 to 2026-09-28 (5.33 Years)  
> **Dataset Status**: Fully Verified Ground-Truth Human Observations ($N = 204$)  
> **Generated / Last Evaluated**: `2026-10-02 03:48:53 UTC`  

---

## Abstract

Coastal plain compound flooding poses a critical threat to low-lying rural estuaries along the Chesapeake Bay. Standard regional weather advisories issued by national weather centers provide broad warning polygons but fail to predict parcel-level water depth, road passability, or inundation duration. 

This paper presents the empirical findings and predictive architecture of an open-science flood monitoring system in **Mathews County, Virginia**. Grounded in a continuous 5-year observational record ($N = 204$ human-logged flood measurements, 2021–2026) paired with 285,000 USGS 6-minute river gauge records, NOAA sensor networks, and USGS 3DEP 1-meter LiDAR elevation ground-truth, this study demonstrates that:

1. **Empirical Zero-Flood Tipping Point**: Surface water inundation begins at exactly **$3.99\text{ ft MLLW}$** ($2.35\text{ ft NAVD88}$) on the local Ware River gauge (USGS 01670180). This threshold is independently validated by USGS 1-meter LiDAR elevation data, which places the roadside ditch culvert invert at **$4.05\text{ ft MLLW}$** (a $0.06\text{ ft}$ / $0.7\text{"}$ physical match).
2. **Linear Inundation Dynamics**: Above $3.99\text{ ft MLLW}$, flood depth scales at **$10.95\text{ inches per foot of gauge rise}$** ($pprox 1.10\text{"}$ per $0.10\text{ ft}$ rise), confirming the observer's handwritten conversion ($0.10\text{ ft} \approx 1\ 3/16\text{"}$). Across 181 verified storm observations spanning minor tides to a 10-year record flood, the model achieves **$R^2 = 0.8511$** and a Mean Absolute Error (**MAE**) of **$1.25\text{ inches}$**.
3. **Two-Stage Machine Learning Pipeline**: 
   - **Stage 1 (Hydrodynamic Gauge Modeling)**: LightGBM and multilinear models predict river stage from upstream surge (Windmill Point 8636580), astronomical tides, quadratic along-bay wind stress (Yorktown USCG 8637689), and barometric pressure, achieving **$R^2 = 0.9731$** (MAE = $1.46\text{"}$) for 0–6h nowcasts and **$R^2 = 0.7209$** (MAE = $4.74\text{"}$) for 48h forward forecasts.
   - **Stage 2 (Hyper-Local Inundation Depth)**: Translates predicted gauge height into neighborhood ground depth and evaluates vehicle passability across an 8-street LiDAR road invert network.

---

## 1. Geographic, Hydrologic & Topographic Context

Mathews County lies on the Middle Peninsula of Virginia, bounded by the Piankatank River to the north, the Chesapeake Bay to the east, and Mobjack Bay to the south (fed by the East, North, Ware, and Severn Rivers). 

The primary study transect is located in the **Mobjack Bay Estates & Blackwater Community** (`37.420183, -76.406550`), draining into Blackwater Creek, the North River, and Mobjack Bay ($pprox 3.6\text{ miles}$ east of the Ware River WRVV2 reference gauge).

### 1.1 USGS 3DEP 1-Meter LiDAR Elevation Ground-Truth

Ground-truth elevations were obtained via the USGS 3D Elevation Program (3DEP) 1-meter digital elevation model. Elevations are tied to NAVD88 and converted to local tidal Mean Lower Low Water (**MLLW**) using the verified tidal datum offset of $+1.64\text{ ft}$ ($	ext{Datum Offset: } \text{MLLW} = \text{NAVD88} + 1.64\text{ ft}$):

| Physiographic Feature | LiDAR Elevation (NAVD88) | Tidal Elevation (MLLW) | Empirical Regression Benchmark | Discrepancy | Physical Hydrologic Role |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Blackwater Creek Marsh Margin** | $-1.09\text{ ft}$ | $0.55\text{ ft}$ | $0.55\text{ ft}$ | $0.00\text{ ft}$ | Wet during twice-daily astronomical high tides |
| **Roadside Ditch Culvert Invert** | $2.41\text{ ft}$ | $4.05\text{ ft}$ | **$3.99\text{ ft}$** | $+0.06\text{ ft}$ ($0.7\"$) | Brim of culvert; water overflows ditches into yard |
| **Driveway Benchmark Pad** | $2.76\text{ ft}$ | $4.40\text{ ft}$ | **$4.40\text{ ft}$** | **$0.00\text{ ft}$ ($0.0\"$)** | Driveway submerged; sedans blocked (Tier 2) |
| **Residence / Garage Slab Elevation** | $3.26\text{ ft}$ | $4.90\text{ ft}$ | **$4.80\text{ ft}$** | $+0.10\text{ ft}$ ($1.2\"$) | Severe property hazard; trucks only (Tier 3) |

### 1.2 Community Street LiDAR Inverts

LiDAR elevation profiles across the 8 community streets establish the dry-land street passability thresholds:

| Street Name | LiDAR Invert (NAVD88) | Tidal Invert (MLLW) | Flooding Mechanism & Vulnerability |
| :--- | :---: | :---: | :--- |
| **Bayshore Avenue** | $2.11\text{ ft}$ | **$3.75\text{ ft}$** | Waterfront dips flood first during astronomical spring tides |
| **Julian Street** | $2.14\text{ ft}$ | **$3.78\text{ ft}$** | Southern culvert dip; water backs up from Blackwater swale |
| **Daniel Avenue** | $2.24\text{ ft}$ | **$3.88\text{ ft}$** | Road dip floods prior to driveway pad benchmark ($4.40\text{ ft}$) |
| **Allview Street** | $2.49\text{ ft}$ | **$4.13\text{ ft}$** | Shallow standing water covers mid-block above $4.13\text{ ft}$ |
| **River Road** | $2.50\text{ ft}$ | **$4.14\text{ ft}$** | Critical community access road; dip blocks passenger sedans |
| **Hobday Street** | $2.58\text{ ft}$ | **$4.22\text{ ft}$** | Roadside ditches breach into travel lanes above $4.22\text{ ft}$ |
| **Little Avenue** | $2.59\text{ ft}$ | **$4.23\text{ ft}$** | Drainage culvert backwater during compound rainfall |
| **Bunny Rabbit Lane** | $2.81\text{ ft}$ | **$4.45\text{ ft}$** | Elevated western ridge; remains passable during nuisance floods |

---

## 2. Sensor Registry & Multi-Station Architecture

| Station ID | Managing Agency | Location | Coordinates | Role in Predictive Architecture |
| :--- | :--- | :--- | :--- | :--- |
| **USGS 01670180 / WRVV2** | USGS / NOAA NWS | Ware River near Schley, VA | `37.3888, -76.4744` | **Primary local hydrological reference gauge** (6-min stage) |
| **NOAA 8637689** | NOAA CO-OPS | Yorktown USCG Training Center, VA | `37.2267, -76.4783` | **Primary meteorological forcing station** (winds, gusts, pressure, tides) |
| **NOAA 8636580** | NOAA CO-OPS | Windmill Point, VA | `37.6150, -76.2817` | **Northern Rappahannock / Chesapeake storm surge reference** |
| **NOAA CBOFS** | NOAA / NOS | Chesapeake Bay Operational Forecast | Bay-wide grid | 48-hr hydrodynamic water level guidance |
| **NWS AKQ** | NOAA NWS | Wakefield Weather Forecast Office, VA | Regional grid | 156-hr hourly meteorological forecast (wind, sky, precip) |

---

## 3. Observational Ground-Truth Dataset: `ground_truth_observations.csv`

The foundational asset of this research is a continuous 5-year observation log recorded by local resident observers between **May 29, 2021 and September 28, 2026**:

### 3.1 Dataset Metrics & Summary Statistics

- **Total Recorded Events**: **204** observations.
- **Valid Stage–Depth Numerical Pairs**: **181** observations.
  - Flooded Observations ($> 0\text{"}$): **137** events ($75.7\%$ of numerical observations).
  - Non-Flooded Baseline Observations ($= 0\text{"}$): **44** events ($24.3\%$ of numerical observations).
  - Qualitative Observations & Notes: **23** events.
- **Temporal Span**: **5.33 years** (2021-05-29 to 2026-09-28).
- **Ware River Gauge Distribution ($MLLW\text{ ft}$)**:
  - $\text{Minimum}: 3.4\text{ ft}$
  - $\text{25th Percentile}: 4.14\text{ ft}$
  - $\text{Median}: 4.35\text{ ft}$
  - $\text{Mean}: 4.39\text{ ft}$
  - $\text{75th Percentile}: 4.61\text{ ft}$
  - $\text{Maximum}: 5.54\text{ ft}$
  - $\text{Interquartile Range (IQR)}: 0.47\text{ ft}$
- **Observed Flood Depth Distribution (inches)**:
  - $\text{Minimum}: 0.0\text{"}$
  - $\text{25th Percentile}: 0.25\text{"}$
  - $\text{Median}: 3.0\text{"}$
  - $\text{Mean}: 4.3\text{"}$
  - $\text{75th Percentile}: 7.0\text{"}$
  - $\text{Maximum}: 19.0\text{"}$
  - $\text{Interquartile Range (IQR)}: 6.75\text{"}$
- **Linear Correlation**:
  - Overall Sample: **$r = 0.8898$** ($N = 181$)
  - Flooded Sample ($> 0\text{"}$): **$r = 0.9302$** ($R^2 = 0.8652$, $N = 137$, $p < 10^{-15}$)

---

## 4. Mathematical Formulations & Model Architectures

### 4.1 Stage 1: Hydrodynamic Water Level Modeling

Stage 1 predicts the Ware River water level ($H_\text{WR}$, in $\text{ft MLLW}$) driven by astronomical tides, upstream surge residuals, quadratic wind stress, and barometric inverse-barometer effects.

#### Quadratic Wind Stress & Roll Setup Memory
Wind stress $\tau$ is computed quadratically from orthogonal wind components:
$$\tau_\text{along} = \text{sign}(U_\text{along}) \cdot |U_\text{along}|^2$$
$$\tau_\text{cross} = \text{sign}(U_\text{cross}) \cdot |U_\text{cross}|^2$$

Rolling wind memory is evaluated over windows $w \in \{3, 6, 12, 24\}\,\text{hours}$:
$$\overline{\tau}_{w}(t) = \frac{1}{w} \int_{t-w}^{t} \tau(t')\, dt'$$

#### Stage 1 Model Results (2024 Holdout Test Set: 6,127 Hours)

| Model Architecture | Lead Time | $R^2$ | RMSE (ft) | MAE (ft) | MAE (inches) | High-Water MAE (>= 4.0') |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Nowcast Linear Baseline** | 0–6 hr | **0.9731** | **0.1599** | **0.1215** | **1.46\"** | **1.7\"** |
| **Nowcast LightGBM** | 0–6 hr | 0.9722 | 0.1625 | 0.1214 | 1.46\" | 2.6\" |
| **Forecast Linear Baseline** | 6–48 hr | **0.7209** | **0.5148** | **0.3954** | **4.74\"** | **9.6\"** |
| **Forecast LightGBM** | 6–48 hr | 0.7067 | 0.5276 | 0.4022 | 4.83\" | 10.9\" |

### 4.2 Stage 2: Hyper-Local Ground Inundation Model

Stage 2 converts Ware River stage ($H_\text{WR}$) to parcel water depth ($D_\text{flood}$, in inches):

$$D_\text{flood} = \max\left(0.0,\, 10.95 \times H_\text{WR} - 43.69\right)$$

Equivalently expressed relative to the zero-flood tipping point threshold ($H_0 = 3.99\text{ ft}$):

$$D_\text{flood} = \begin{cases} 
0.0 & \text{if } H_\text{WR} < 3.99\text{ ft} \\
10.95 \times (H_\text{WR} - 3.99) & \text{if } H_\text{WR} >= 3.99\text{ ft}
\end{cases}$$

#### Empirical Validation (2021–2026, $N = 181$)
- **Coefficient of Determination ($R^2$)**: **$0.8511$**
- **Mean Absolute Error (MAE)**: **$1.25\text{ inches}$** ($1.3\text{"}$ on flooded events)
- **Root Mean Squared Error (RMSE)**: **$1.69\text{ inches}$** ($1.58\text{"}$ on flooded events)
- **Zero-Crossing Intercept**: $-43.69 / 10.95 = 3.990\text{ ft MLLW}$, matching culvert invert ($4.05\text{ ft MLLW}$) within $0.06\text{ ft}$.

### 4.3 Compound Ditch Drainage & Backwater Physics

When high tides elevate water in Blackwater Creek above the ditch culvert invert, gravity drainage from precipitation is physically obstructed:

$$\beta(H_\text{WR}) = \text{clip}\left(\frac{H_\text{WR} - 3.80}{0.40},\, 0,\, 1\right)$$

Where $\beta = 0$ denotes unimpeded gravity ditch discharge ($H_\text{WR} \le 3.80\text{ ft}$) and $\beta = 1$ denotes complete tailwater submergence and zero gravity drainage ($H_\text{WR} \ge 4.20\text{ ft}$). Rainfall accumulated during periods where $\beta > 0.5$ compounds flood depth above purely tidal predictions.

---

## 5. Major Benchmark Storm Case Studies

The 5-year empirical record captures 10 major tropical cyclones, nor'easters, and astronomical events that benchmark system performance:

| Storm Event | Date | Ware River Stage ($MLLW$) | Stage ($NAVD88$) | Measured Depth (in) | Predicted Depth (in) | Peak Wind Conditions | Observed Hydrologic Impact |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- | :--- |
| **10-Year Record Nor'easter** | Oct 12, 2025 | **$5.54\text{ ft}$** | $3.90\text{ ft}$ | **$19.00\text{"}$** | $16.97\text{"}$ | NNE 24 mph (35 gusts) | All-time 10-year property record. Complete yard and driveway submergence. |
| **Twin Nor'easters (Storm 1 & 2)** | Sep 22–26, 2026 | **$5.38\text{ ft}$** | $3.74\text{ ft}$ | **$17.50\text{"}$** | $15.22\text{"}$ | NE 21.9 mph / NNW 23 | Multi-day surge stacking prevented drainage between tides; NJ state of emergency. |
| **Late Autumn Nor'easter** | Nov 15, 2024 | **$5.27\text{ ft}$** | $3.63\text{ ft}$ | **$15.00\text{"}$** | $14.02\text{"}$ | NNE 12.8 mph | 15 inches of water over yard and access road. |
| **September King Tide** | Sep 22, 2024 | **$5.20\text{ ft}$** | $3.56\text{ ft}$ | **$14.50\text{"}$** | $13.25\text{"}$ | SE 5–10 mph | Astronomical perigean high tide; extensive property submergence. |
| **Winter Blizzard Gale** | Jan 3, 2022 | **$5.22\text{ ft}$** | $3.58\text{ ft}$ | **$11.00\text{"}$** | $13.47\text{"}$ | N gale + snow | Blizzard winds stacked water down Chesapeake Bay into Mobjack Bay. |
| **Hurricane Erin** | Aug 21–22, 2025 | **$5.12\text{ ft}$** | $3.48\text{ ft}$ | **$13.00\text{"}$** | $12.37\text{"}$ | NNE 18.3 (24.6 gusts) | Severe tropical surge; documented rapid 13\" to 10.75\" drop in 30 min post-tide. |
| **Hurricane Ophelia** | Sep 23, 2023 | **$5.00\text{ ft}$** | $3.36\text{ ft}$ | **$12.00\text{"}$** | $11.06\text{"}$ | SE 20–30 mph | Tropical surge aligned with lunar perigee; road network impassable. |
| **Hurricane Helene** | Sep 27, 2024 | **$4.70\text{ ft}$** | $3.06\text{ ft}$ | **$9.75\text{"}$** | $7.78\text{"}$ | SE 25.3 mph | Rapid tropical surge into ditches; peaked at 9.75 inches at 7:30 PM. |
| **Hurricane Earl** | Sep 8, 2022 | **$4.82\text{ ft}$** | $3.18\text{ ft}$ | **$10.00\text{"}$** | $9.09\text{"}$ | NNE 17 mph | Sustained driveway submergence across 3 consecutive tidal cycles. |
| **Hurricane Ian** | Sep 30–Oct 1, 2022 | **$4.66\text{ ft}$** | $3.02\text{ ft}$ | **$7.00\text{"}$** | $7.34\text{"}$ | N 12–25 mph | Prolonged northerly wind set-up forcing persistent water into Mobjack Bay. |

---

## 6. Scientific Versioning & Model Calibration Changelog

```
[
  {
    "version": "2.1.0",
    "date": "2026-10-02",
    "title": "Multi-Station Hydraulic Gradient & Quantile Uncertainty Envelope",
    "summary": "Integrated NOAA Sewells Point (8638610) southern Chesapeake Bay reference station and LightGBM quantile regression uncertainty bounds (Q10/Q90) for probabilistic forecasting.",
    "details": [
      "Incorporated NOAA Sewells Point (8638610) to calculate Chesapeake Bay hydraulic gradient across the 46.2-mile north-south transect (Delta Surge = Surge_Windmill - Surge_Sewells).",
      "Identified southward pressure head regime (Delta Surge >= +0.20 ft) actively pushing water into Mobjack Bay and the Ware River basin.",
      "Trained LightGBM quantile regression models for alpha = 0.10 (best case) and alpha = 0.90 (worst case) with empirical conformal residual adjustments.",
      "Visualized semi-transparent shaded 80% confidence interval band around the 48-hour hydrograph curve on index.html.",
      "Expanded regional station grid to 6 cards on index.html featuring Yorktown winds, wind vectors, barometer, Windmill Pt surge, Sewells Pt surge, and bay hydraulic slope."
    ]
  },
  {
    "version": "2.0.0",
    "date": "2026-10-01",
    "title": "5-Year Full Empirical Expansion (2021\u20132026) & Science Portal Launch",
    "summary": "Incorporated 63 newly verified storm records from continuous observer logs, expanding ground-truth archive from 141 to 204 events (181 depth pairs).",
    "details": [
      "Ingested 63 new storm records from 2024-10-16 to 2026-09-28 from RAW Observer data - Mom.gsheet.",
      "Captured all-time 10-year record nor'easter (2025-10-12: 5.54 ft stage, 19.0\" flood depth, 35 mph gusts).",
      "Captured September 2026 twin nor'easters (2026-09-22 to 09-26: 5.38 ft stage, 17.5\" depth, multi-day surge stacking).",
      "Captured Hurricane Erin (2025-08-21 to 08-22: 5.12 ft stage, 13.0\" depth, rapid drainage documented).",
      "Applied observer depth corrections: Obs 42 (2.50\"), Obs 62 (8.00\"), Obs 136 (2.00\").",
      "Re-calibrated Stage 2 inundation model: R\u00b2 improved from 0.800 to 0.8511, MAE = 1.25\", RMSE = 1.69\" across 181 observations.",
      "Launched dedicated scientific documentation (SCIENTIFIC_FINDINGS.md, science.html, generate_scientific_report.py)."
    ]
  },
  {
    "version": "1.2.0",
    "date": "2025-10-15",
    "title": "Automated Cloud Ingestion & Micro-Topography GIS Engine",
    "summary": "Deployed automated 30-minute cloud pipeline with GitHub Actions, ntfy.sh mobile alerts, and USGS 3DEP LiDAR street network integration.",
    "details": [
      "Implemented 30-minute automated cron ingestion via .github/workflows/update_flood_monitor.yml.",
      "Created check_alerts.py stateful alerting engine with instant push dispatcher via ntfy.sh topic mathews-flood-alerts.",
      "Extracted 8-street LiDAR road invert elevations (3.75' to 4.45' MLLW) for vehicle passability matrix.",
      "Integrated OpenStreetMap coastline boundary ensuring zero warning polygons fall into open water.",
      "Created multi-page web portal (index.html, alerts.html, about.html, guide.html, data.html)."
    ]
  },
  {
    "version": "1.1.0",
    "date": "2024-10-01",
    "title": "Historical Backfill & Stage 1 Hydrodynamic ML Modeling",
    "summary": "Constructed 32,833-hour training dataset and developed two-stage machine learning predictive architecture.",
    "details": [
      "Scraped 4 years of 6-minute Ware River hydrograph (USGS 01670180 / WRVV2) via IEM HML API (2021\u20132024).",
      "Aligned hourly NOAA CO-OPS Yorktown USCG (8637689) meteorological and Windmill Point (8636580) surge data.",
      "Engineered physical hydrodynamic features: quadratic wind stress (tau ~ |U|*U), rolling set-up memory (3h, 6h, 12h, 24h), barometric pressure derivatives, and tidal rise rates.",
      "Trained Stage 1 Nowcasting LightGBM (R\u00b2 = 0.973, MAE = 1.5 in) and Forward Forecasting LightGBM (R\u00b2 = 0.721, MAE = 4.8 in).",
      "Validated against Hurricane Helene (Sep 2024) and September 2024 King Tide holdout test sets."
    ]
  },
  {
    "version": "1.0.0",
    "date": "2024-09-30",
    "title": "Initial Ground-Truth Extraction & Mathematical Threshold Discovery",
    "summary": "Digitized 141 handwritten observer measurements (2021\u20132024) and established the empirical 3.99 ft flood tipping point.",
    "details": [
      "Digitized notebook photos (IMG_8049.jpeg\u2013IMG_8058.jpeg) into ground_truth_observations.csv.",
      "Discovered empirical flooding threshold at 3.99 ft MLLW on the Ware River gauge.",
      "Discovered linear inundation slope: 10.95 inches per foot rise (~1.1\u20131.2\" per 0.1 ft).",
      "Mathematically verified observer's handwritten conversion: 0.10 ft ~= 1 3/16\" to 1.25\".",
      "Established Risk Severity Tiers 0\u20133 based on physical elevation thresholds."
    ]
  }
]
```

---

## 7. Data Availability & Reproducibility Statement

All code, trained model weights, and ground-truth datasets supporting this research are open science:

1. **Ground-Truth Dataset**: [`ground_truth_observations.csv`](file:///Users/howard_hottinger/Library/CloudStorage/GoogleDrive-flatfoot584@gmail.com/My%20Drive/Weather%20data/ground_truth_observations.csv)
2. **Model Weights & Thresholds Configuration**: [`models/model_weights_and_thresholds.json`](file:///Users/howard_hottinger/Library/CloudStorage/GoogleDrive-flatfoot584@gmail.com/My%20Drive/Weather%20data/models/model_weights_and_thresholds.json)
3. **Machine-Readable Scientific Evidence**: [`models/scientific_evidence.json`](file:///Users/howard_hottinger/Library/CloudStorage/GoogleDrive-flatfoot584@gmail.com/My%20Drive/Weather%20data/models/scientific_evidence.json)
4. **Automated Evaluation Pipeline**: Run `.venv/bin/python generate_scientific_report.py` to regenerate all metrics upon receiving new data.
