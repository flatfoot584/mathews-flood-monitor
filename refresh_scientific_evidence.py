"""Refresh models/scientific_evidence.json in place.

Every pipeline run (no private data needed):
  * metadata.refreshed_at_utc and metadata.live_verification_updated_at_utc
  * prospective_verification: snapshot of models/live_verification.json summary

On demand, locally only (reads the private ground_truth_observations.csv):
  python3 refresh_scientific_evidence.py --from-ground-truth
  * dataset_characteristics counts/distributions
  * stage2_inundation r2/MAE/RMSE for the published formula, plus
    leave-one-year-out cross-validated MAE
Raw observer records are never published; only aggregates are written.
"""
import csv
import json
import math
import statistics as st
import sys
from datetime import datetime, timezone
from pathlib import Path

from runtime_safety import atomic_write_json

EVIDENCE = Path('models/scientific_evidence.json')
LIVE = Path('models/live_verification.json')
GROUND_TRUTH = Path('ground_truth_observations.csv')


def _load(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def _dist(values):
    v = sorted(values)
    q = lambda p: v[min(len(v) - 1, int(round(p * (len(v) - 1))))]
    return {'min': round(v[0], 2), 'max': round(v[-1], 2), 'mean': round(st.mean(v), 2),
            'std': round(st.pstdev(v), 2), 'p25': round(q(.25), 2), 'median': round(q(.5), 2),
            'p75': round(q(.75), 2), 'iqr': round(q(.75) - q(.25), 2)}


def _pearson(xs, ys):
    mx, my = st.mean(xs), st.mean(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def _fit_hinge(pts):
    best = None
    for i in range(80):
        t = 3.7 + 0.01 * i
        z = [(max(0.0, s - t), d) for s, d, _ in pts]
        den = sum(a * a for a, _ in z)
        if not den:
            continue
        m = sum(a * b for a, b in z) / den
        err = sum((m * a - b) ** 2 for a, b in z)
        if best is None or err < best[0]:
            best = (err, m, t)
    return best[1], best[2]


def refresh_ground_truth(evidence):
    rows = list(csv.DictReader(GROUND_TRUTH.open(encoding='utf-8')))
    pts = [(float(r['ware_river_stage_ft']), float(r['flood_depth_in']), r['date'])
           for r in rows if r.get('ware_river_stage_ft') and r.get('flood_depth_in')]
    stages = [p[0] for p in pts]
    depths = [p[1] for p in pts]
    flooded = [p for p in pts if p[1] > 0]
    ds = evidence.setdefault('dataset_characteristics', {})
    ds.update({
        'total_observations': len(rows),
        'valid_numerical_pairs': len(pts),
        'flooded_observations': len(flooded),
        'zero_flood_observations': len(pts) - len(flooded),
        'qualitative_notes_only': len(rows) - len(pts),
        'ware_river_stage_distribution_ft': _dist(stages),
        'flood_depth_distribution_in': _dist(depths),
        'correlation_overall_r': round(_pearson(stages, depths), 4),
        'correlation_flooded_r': round(_pearson([p[0] for p in flooded], [p[1] for p in flooded]), 4),
    })
    ds['correlation_flooded_r2'] = round(ds['correlation_flooded_r'] ** 2, 4)
    dates = sorted(p[2] for p in pts)
    ds['observation_date_range'] = [dates[0], dates[-1]]

    s2 = evidence.setdefault('model_performance', {}).setdefault('stage2_inundation', {})
    slope = s2.get('slope_in_per_ft', 10.95)
    # Published formula: depth = max(0, slope * stage - intercept); intercept from tipping point.
    thr = s2.get('tipping_point_threshold_mllw_ft', 3.99)
    pred = [max(0.0, slope * (s - thr)) for s in stages]
    resid = [p - d for p, d in zip(pred, depths)]
    mean_d = st.mean(depths)
    s2.update({
        'evaluation_samples': len(pts),
        'mae_inches': round(st.mean(abs(r) for r in resid), 2),
        'rmse_inches': round(math.sqrt(st.mean(r * r for r in resid)), 2),
        'r2_in_sample': round(1 - sum(r * r for r in resid) / sum((d - mean_d) ** 2 for d in depths), 4),
    })
    cv = []
    for year in sorted({p[2][:4] for p in pts}):
        train = [p for p in pts if p[2][:4] != year]
        test = [p for p in pts if p[2][:4] == year]
        if not train or not test:
            continue
        m, t = _fit_hinge(train)
        cv.append({'held_out_year': year, 'n': len(test),
                   'mae_in': round(st.mean(abs(max(0.0, m * (s - t)) - d) for s, d, _ in test), 2),
                   'fitted_slope_in_per_ft': round(m, 2), 'fitted_threshold_ft': round(t, 2)})
    s2['leave_one_year_out_cv'] = cv
    s2['note'] = ('Published formula scored in-sample. Cross-validation refits a through-threshold '
                  'hinge model with one year held out. Observations cover flood-likely periods only.')


def refresh(from_ground_truth=False, now=None):
    evidence = _load(EVIDENCE) or {}
    now = now or datetime.now(timezone.utc)
    meta = evidence.setdefault('metadata', {})
    stamp = now.strftime('%Y-%m-%d %H:%M:%S UTC')
    meta['refreshed_at_utc'] = stamp
    if from_ground_truth:
        refresh_ground_truth(evidence)
        meta['generated_at_utc'] = stamp
        meta['observation_statistics_as_of_utc'] = stamp
        dr = evidence['dataset_characteristics'].get('observation_date_range')
        if dr:
            meta['study_period'] = f'{dr[0]} to {dr[1]}'
    else:
        meta.setdefault('observation_statistics_as_of_utc', meta.get('generated_at_utc'))
    live = _load(LIVE)
    if live and live.get('summary'):
        meta['live_verification_updated_at_utc'] = live.get('updated_at_utc')
        evidence['prospective_verification'] = {
            'source': 'models/live_verification.json',
            'updated_at_utc': live.get('updated_at_utc'),
            'issued_rows': live.get('issued_rows'),
            'summary': live['summary'],
        }
    atomic_write_json(EVIDENCE, evidence)
    return evidence


if __name__ == '__main__':
    refresh(from_ground_truth='--from-ground-truth' in sys.argv)
    print('[+] Refreshed models/scientific_evidence.json')
