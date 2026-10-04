# Mathews County Flood Monitor

[Live dashboard](https://flatfoot584.github.io/mathews-flood-monitor/)

The monitor combines Ware River gauge readings, NOAA tides/weather, NWS guidance,
and modeled tidal/rainfall impacts to describe potential community flooding.
The public portal includes live conditions, a forecast map/hydrograph, mobile
subscription instructions, safety guidance, public data downloads, and methodology.

Unknown or stale data must not imply dry roads. A fresh gauge and complete 48-hour
water/wind/rain coverage are required before an ALL CLEAR. Never drive into floodwater.
Live uncertainty bands are heuristic scenario ranges, not calibrated probabilities.
Historical observed-weather benchmarks do not establish live forecast accuracy.

Existing community notifications remain on the current public ntfy.sh topic.
The authenticated-topic migration is deferred; no account, reservation, or publishing
token is required by this release. The public channel remains writable by others.

## Public and private files

This repository contains runtime code, public automated gauge/forecast outputs,
yearly numeric observer summaries, aggregate benchmark statistics, and website assets.
Original observer logs, notebook images, internal notes/setup guides and private
analysis material are retained outside this repository. Their names are ignored to
prevent accidental re-addition. Deleting current files does not erase Git history.

GitHub Pages is built by `publish_site.py`, which copies only explicitly approved
public files into a clean artifact. It excludes alert state, private data, internal
documents, and arbitrary HTML files. Public help/about/science pages remain available.

## Runtime

Python 3.11+ with timezone data is sufficient for collection and page generation.

```bash
python3 -m unittest discover -s tests -v
python3 ingest_realtime.py
python3 generate_dashboard.py
python3 publish_site.py
```

The GitHub workflow separately dispatches eligible community alerts. Use
`check_alerts.py --dry-run --ntfy` for local evaluation without sending messages.
GitHub's requested 30-minute schedule remains best effort; timestamp-based freshness
checks detect stale output. `check_pipeline_health.py` supports independent monitoring.

Node is needed only to rebuild the committed stylesheet after template changes:
`npm ci --ignore-scripts` followed by `npm run build:css`.

## Fort Monroe evaluation and resident portal

Fort Monroe FTMV2 (USGS 0204289994) is collected as an optional evaluation
sensor. NWPS MLLW readings are converted with that station's 1.70 ft offset to
NAVD88, checked against coincident USGS parameter 62620 observations.
Its hourly NAVD88 elevations are stored in the public observation archive.

The historical causal ablation uses past readings from all existing station
groups, known future astronomical tides, chronological 2021–22 training, 2023
validation and 2024 testing, with boundary gaps. Fort Monroe improves the
1-hour Ridge baseline but does not pass the multi-lead promotion gate. This
experiment does not establish incremental accuracy over issued NWPS guidance.
The operational forecast is retained; see `models/fort_monroe_evaluation.json`.
The private hourly analysis dataset remains local and excluded from publication.
Run `experiments/evaluate_fort_monroe.py` in the local numerical environment
with cached public Fort Monroe and Sewells data to reproduce the ablation.

`forecast_verification.py` archives six lead bins per issue, retaining exact
lead times and matching predictions to subsequent Ware River readings.
`models/live_verification.json` reports prospective stage scores, with sample
counts and limitations. Repeated issues are correlated and local depth remains
unverified. Fort Monroe outages do not disable the existing forecast or alerts.

The resident portal separates present observations, modeled future impacts,
official NWS warnings, source times and evidence limits. Device-specific ntfy
setup retains the existing community topic. Offline pages visibly retain data
age. The Data page prepares an observation draft locally for manual submission
to the existing GitHub issue review queue; it never writes training labels.
