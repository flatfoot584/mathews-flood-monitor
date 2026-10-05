# Mathews coastline and Mobjack vicinity expansion assessment

Assessment completed October 4, 2026, Eastern Time. Scope: inspect the existing prediction pipeline and available data, assess geographic transfer, and recommend a bounded expansion. This is research, not approval or implementation of countywide operational coverage.

## Assessment

**Yes, the project can reasonably expand into a zoned coastal flood and access-risk system. The present evidence does not support applying the existing neighborhood depth equation unchanged to the entire Mathews coastline.**

The useful assets are the ingestion, weather and water-level history, forecast/display/alert infrastructure, and the local observer record. Public terrain and county asset geometry are also available. The main constraint is establishing local water levels, drainage connections, and observed impacts outside the existing benchmark area.

Regional screening for potentially affected roads, driveways, parcels, and building surroundings is feasible. Calibrated road-depth predictions require additional local evidence. Predicting water entering a house requires finished-floor or lowest-entry elevations, which the inspected county geometry does not supply. Raised homes can remain above water while their yards and access roads flood.

## What is actually in the workspace

| Asset | Verified content | Expansion value and limitation |
| --- | --- | --- |
| Human observations | 204 records, May 29, 2021 through September 28, 2026; 181 numeric gauge-stage/depth pairs; 143 distinct dates across all records | Valuable local impact evidence. The schema has no site ID, coordinates, road segment, or measured-object field. These are observations, not 204 independent storms or a spatially distributed county survey. |
| Ware River history | 285,097 short-interval rows and 31,340 hourly rows | Useful tidal reference history; one gauge cannot establish spatial differences everywhere. |
| Merged training table | 32,833 hourly rows, January 2021 through September 30, 2024; 31,340 populated stage rows; 100 populated local-depth rows | Rich temporal data, limited impact labels. The five-year observer record does not mean the hourly training table extends through 2026. |
| Live collection | WRVV2; NOAA Yorktown, Windmill Point, Sewells Point; NWS hourly wind and precipitation guidance | Reusable infrastructure. Weather guidance is selected from one fixed NWS grid location. County expansion requires appropriate local weather coverage. |
| Live archive | 118 hourly observation rows at inspection | A short continuous archive, not a multi-year issued-forecast validation dataset. Estimated-depth columns are model outputs, not independent field truth. |
| Impact engine | Eight hard-coded streets and five elevation sectors in `micro_topography.py` | Covers Mobjack Bay Estates and Blackwater. A constant datum offset, one gauge-stage/depth equation, common rain multiplier, and single street low-point summaries are embedded in the implementation. |
| Spatial files | No local GeoTIFF, LAS/LAZ, GeoPackage, shapefile, GeoJSON, or NetCDF files found outside the environment/repository internals | Existing sampled elevation values and drawn neighborhood geometry are not a county terrain model. Wider layers must be obtained and processed. |

Files inspected include `README.md`, `AGENTS.md`, `FINDINGS_AND_DECISIONS.md`, `BACKLOG.md`, `ingest_realtime.py`, `micro_topography.py`, `train_predictive_models.py`, the model/evaluation JSON, actual CSV files, and publication/workflow configuration. Raw observer records were read only for aggregate audit and were not copied into the report or external project state.

## Public data verified for expansion

### Terrain

An actual query of the [USGS National Map product catalog](https://tnmaccess.nationalmap.gov/api/v1/products?datasets=Digital%20Elevation%20Model%20%28DEM%29%201%20meter&bbox=-76.52%2C37.26%2C-76.18%2C37.60&max=100&outputFormat=JSON) returned **21 one-meter DEM product records** intersecting the regional bounding box. Seventeen belong to `VA_UpperMiddleNeck_2018_D18`; the remaining records include overlapping products near the southwestern query edge. Product count is not a count of nonoverlapping tiles or proof of every land pixel's completeness.

Bounding-box checks found coverage at the existing Blackwater benchmark and representative coordinates in the East River, southern/eastern Mathews, Gwynn's Island vicinity, and Piankatank vicinity. This is strong evidence that terrain acquisition is practical. Full county clipping, raster nodata, shoreline accuracy, and hydraulic-connectivity checks remain unperformed.

The [Blackwater tile metadata](https://www.sciencebase.gov/catalog/item/61c2bf33d34e2ca389d9ea0e?format=json) identifies bare-earth heights in meters NAVD88, UTM/NAD83 horizontal coordinates, publication in December 2021, and collection date fields spanning December 2018 to January 2020. Publication date is not collection date. Terrain can predate road raising, culvert work, shoreline erosion, and building changes. One-meter pixel size does not establish inch-level vertical accuracy.

### Roads and buildings

Following the GIS link on the [official county website](https://mathewscountyva.gov/) led to its [county GIS viewer](https://experience.arcgis.com/experience/fec71d0cfd1841ee9a2be41ebb5ba525/page/Map). The actual web-map configuration references a public [county feature service](https://services5.arcgis.com/DvUHhhcJDK6FHDIv/arcgis/rest/services/Mathews_WL_P/FeatureServer).

Public metadata and count queries succeeded for:

| Layer | Feature records | Important qualification |
| --- | ---: | --- |
| Road Centerlines, layer 1 | 3,272 | Features/segments, not necessarily 3,272 distinct named roads; lines do not supply road-crown elevations. |
| Bridges, layer 2 | 12 | Geometry is available; inspected fields do not provide deck elevations. |
| Driveways, layer 4 | 3,269 | Access geometry is useful; no elevation field was found. |
| Building Footprints, layer 5 | 11,987 | The service represents these as polylines. Records are not necessarily unique houses, and do not provide finished-floor elevations. |

The map also references parcels, water bodies, flood zones, and a Limit of Moderate Wave Action layer. Their presence was verified in configuration; completeness, accuracy, export behavior, and detailed attributes were not audited. The four counted layers advertise Query and Extract. No owner names or addresses were downloaded.

These layers make a county exposure inventory possible. FEMA flood zones can help prioritize assets but do not predict the timing or depth of the next tide.

### Regional water guidance and comparison products

[NOAA's OFS documentation](https://www.tidesandcurrents.noaa.gov/ofs/ofs_faq.html) provides a path beyond the single Ware River hydrograph: CBOFS has hourly spatial fields and 48-hour guidance, four cycles daily. Its documented horizontal grid spacing varies from 50 meters to 5 kilometers. Actual usable wet cells at each proposed zone and their vertical references still need inspection; this is not a road or drainage model.

[VIMS Tidewatch Map](https://cmap22.vims.edu/SCHISM/TidewatchViewer.html) describes regional inundation guidance and a location-specific chart comparing water and land elevations over 36 hours. It should be evaluated as an existing comparison and potential source before duplicating regional flood modeling. Current Mathews pixel availability, feed access, archives, and reuse terms have not been tested.

The [regional hazard mitigation plan](https://www.mppdc.com/articles/service_centers/mandates/All%20Hazards%20Mitigation%20Plan%20Update/FINAL_2021_Amended%20MPPDC%20Plan_05022022_RED.pdf) identifies historically flood-prone roads, including Bethel Beach, Haven Beach, Old Ferry, Potato Neck, Tabernacle, and Light House/Point roads. This older planning inventory is a useful candidate list, not current road-condition evidence or a calibrated stage threshold. Search-index excerpts were available; direct PDF retrieval failed, so the complete plan was not independently rechecked.

## Why the existing coefficients cannot simply be copied

1. **Different water surfaces.** Blackwater Creek/North River, East River, open Chesapeake shore, and Piankatank have different exposure, tide timing, channels, wind setup, and drainage. Proximity is a useful hypothesis, not validation that Ware River represents every zone.
2. **Different vertical references.** The implementation applies `NAVD88 = MLLW - 1.64 ft` throughout. The same offset must not be assumed valid countywide. Convert all water and terrain heights to a common vertical datum using documented local transformations and uncertainty. [NOAA VDatum](https://vdatum.noaa.gov/docs/faqs.html) describes the role of spatially varying coastal datum patterns.
3. **Water needs a route.** Land below the forecast water surface is not automatically flooded. Berms, road embankments, ditches, culverts, bridges, and disconnected depressions control connectivity. Shoreline clipping alone does not resolve these pathways. Bridge-deck heights must be distinguished from bare-earth terrain below them.
4. **Rainfall response is local.** The current backwater function and 1.4 rainfall multiplier are heuristic rules. They are not a calibrated county drainage model. Rain-only flooding and overtopping/waves are outside what the current depth relation validates.
5. **House interior and property exposure are different targets.** Bare-earth terrain and building outlines support surrounding-ground exposure. Water entering a structure requires surveyed or documented floor/entry heights and relevant flood pathways.

For a connected coastal ground point, a useful baseline is `depth_in = max(0, water_NAVD88_ft - ground_NAVD88_ft) * 12`. Local bias and connectivity must be established first. The existing 10.95 inches-per-foot regression is an empirical relation at its observation reference, not a universal geometric conversion.

## Accuracy findings that limit expansion claims

- The saved linear nowcast reports water-level MAE **1.46 inches overall**, using contemporaneous measured regional conditions to estimate Ware River. This is not a 48-hour warning score.
- The saved linear forecast-style benchmark reports **4.75 inches overall** and **9.58 inches at high-water hours**, across 126 high-water hourly samples. Samples are not necessarily independent storms. The features include observed wind and pressure at the target times, so this is a retrospective observed-weather benchmark, not an issue-time operational forecast backtest.
- The ground-depth equation reports **1.25-inch MAE on 181 local numeric pairs**. That score evaluates the existing relation on the observer record without an independent location or storm holdout. It does not validate eight streets individually, countywide predictions, compound rainfall additions, or the combined 48-hour forecast chain.
- Saved uncertainty metadata reports **55.8% empirical coverage for a nominal 80% interval**. The live code instead uses fixed heuristic offsets growing with lead time and wind; its bands have no demonstrated coverage probability.
- Production uses NWPS guidance plus fixed wind/hydraulic adjustments and a separate fallback formula, rather than loading the saved forecast coefficients or quantile models. The saved statistical model scores therefore are not scores for the current production calculation. NOAA guidance already contains meteorological forcing; extra wind terms need evaluation to establish benefit and avoid counting the same effect twice.
- The single latest forecast file is overwritten. A dedicated archive by model cycle, issue time, valid time, lead time, zone, and model version is needed. Git snapshots alone should not be assumed to be a complete issued-forecast archive.
- A final workspace refresh also found `experiments/evaluate_fort_monroe.py`, a causal station-ablation script. Its own documented limitations say it does not replay historical issued NWPS guidance. No completed experiment results were available in that directory at inspection, so it does not change the geographic-transfer assessment.

For perspective, a 0.2-foot water-surface or ground-height error corresponds to 2.4 inches of geometric depth error. Apparent sub-inch agreement between a sampled DEM elevation and an empirical threshold does not establish survey precision.

## Where expansion is most defensible

| Area | Recommendation | What must be established |
| --- | --- | --- |
| Nearby Blackwater and North River shoreline communities | First operational pilot candidate | Local road/driveway elevations, connectivity, and concurrent gauge/impact observations. Highest transfer plausibility, still unvalidated. |
| East River and Mobjack-facing Mathews, including the Bohannon vicinity | Second contrasting pilot | Zone water-level bias, tide timing, wind sensitivity, and local observations. |
| Ware/Severn and adjoining Gloucester shores around Mobjack Bay | Feasible subsequent zones | Separate asset inventory and basin-specific transfer validation. Ware River proximity alone does not prove local depths. |
| New Point, Bethel Beach, Haven Beach, eastern Chesapeake-facing shore | Valuable screening targets, later operational predictions | Spatial water guidance and explicit treatment of wave exposure, overtopping, erosion, barriers, and access constraints. |
| Gwynn's Island and Piankatank-facing Mathews; adjoining lower Middlesex | Separate northern zones | Northern-basin water-level behavior and access bottlenecks; do not reuse the Mobjack relation unchanged. |

This ranking is an inference about transfer difficulty, not a measured comparison of predictive skill.

## Recommended next action and gates

**Build a bounded feasibility study for 10–20 road/driveway low points across two pilot zones: nearby North River/Blackwater and one East River community.** Exact points should be selected using the county layers and documented access problems. This is the recommended follow-up, not a started implementation.

1. Establish asset coordinates and measured object, DEM source/date/error, local vertical conversion, ground or deck elevation, and coastal/drainage connectivity. Keep uncertain assets marked unknown.
2. Compare unmodified NOAA/VIMS guidance, a simple zonal bias-corrected baseline, and the existing adjustment approach. Archive forecasts as issued; use 6-, 12-, 24-, and 48-hour lead bins.
3. Collect geolocated depth and wet/dry observations, including verified dry conditions at forecast hazard times. Useful sources could include participating residents, a surveyed temporary local sensor, and county/VDOT reports. Availability of timestamped closure archives is unverified.
4. Hold out entire storms and at least one location. Measure missed floods, false alarms, depth error, onset/crest/receding error, coverage, and missing-data performance. Define acceptance tolerances against the intended use before fitting. As a provisional design gate, total uncertainty should be smaller than the impact categories we intend to distinguish.
5. Publish broader coverage in stages: experimental regional screening, locally checked access-risk estimates, then calibrated depth guidance where supported. Avoid precise inch values where the uncertainty exceeds the useful distinctions. Emergency road closures and safe routing are separate claims requiring stronger evidence.

Several different events are needed, including high tide with little rain, prolonged wind-driven surge, and rainfall with blocked drainage. A few storms can expose obvious failures but cannot establish rare-extreme reliability.

The lightweight zonal/asset approach can use public data and existing hosting without running a new hydrodynamic model. Terrain processing is a batch GIS workload; serving precomputed asset thresholds should be modest. Initial sensor/survey effort and validation are more likely to govern cost and readiness than ML compute. No cost, deployment date, or expected accuracy gain is claimed.

## Closeout

The pipeline, website, notifications, model weights, and observer records were not changed. Public metadata responses and failed-access records are saved in `EXPANSION_PUBLIC_DATA_INVENTORY.json`. No multi-gigabyte terrain tiles were downloaded. The project is technically expandable; locally calibrated operational accuracy remains the gate.
