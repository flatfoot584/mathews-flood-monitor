#!/usr/bin/env python3
"""Build a clean GitHub Pages artifact from an explicit public file allowlist."""
from pathlib import Path
import shutil

PUBLIC_FILES = (
    'index.html', 'flood_dashboard.html', 'alerts.html', 'subscribe.html',
    'about.html', 'guide.html', 'data.html', 'science.html',
    'latest_status.json', 'forecast_48h.csv', 'realtime_recent_observations.csv',
    'archive_hourly_observations.csv', 'observer_yearly_summary.csv',
    'models/scientific_evidence.json', 'models/model_weights_and_thresholds.json',
    'assets/tailwind.css', 'assets/chart.umd.min.js', 'assets/leaflet.js',
    'assets/Chart.LICENSE.md', 'assets/Leaflet.LICENSE',
)


def build_site(root=Path('.'), destination=Path('_site')):
    root, destination = root.resolve(), destination.resolve()
    if destination != root / '_site':
        raise ValueError('Publication destination must be the dedicated _site directory.')
    for name in PUBLIC_FILES:
        source = root / name
        if not source.is_file() or source.is_symlink() or source.resolve() != source:
            raise ValueError(f'Missing or linked public file: {name}')
    if destination.is_symlink():
        raise ValueError('Publication destination cannot be a symlink.')
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir()
    for name in PUBLIC_FILES:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / name, target)
    return destination


if __name__ == '__main__':
    build_site()
