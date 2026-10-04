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
