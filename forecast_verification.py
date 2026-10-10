"""Durable issue-time archive and prospective verification of the deployed forecast.
Stores six lead times per issue (not every intermediate row) to bound repository growth.
Observation matching uses gauge readings within 6 minutes of valid time, falling back
to verified hourly archive records when 6-minute pings are missed or buffer rolled over.
Evaluates live operational MAE vs raw NOAA NWPS guidance across all leads and storm events.
"""
import csv
from pathlib import Path
from datetime import datetime, timezone, timedelta
from runtime_safety import parse_timestamp, finite_number, atomic_write_json

FIELDS = [
    'issue_time_utc', 'guidance_issued_at_utc', 'valid_time_utc', 'lead_hours',
    'actual_lead_hours', 'predicted_stage_mllw_ft', 'nwps_raw_stage_ft',
    'fort_observation_time_utc', 'fort_elevation_navd88_ft',
    'observed_stage_mllw_ft', 'verified_at_utc'
]

HIGH_WATER_THRESHOLD_FT = 4.00


def _parse_float(val):
    if val in ('', None):
        return None
    try:
        f = float(val)
        return f if finite_number(f) else None
    except (ValueError, TypeError):
        return None


def archive_and_verify(status, ware_obs, path='issued_forecast_archive.csv', score_path='models/live_verification.json', hourly_archive_path='archive_hourly_observations.csv'):
    file = Path(path)
    rows = []
    if file.exists():
        with file.open() as f:
            rows = list(csv.DictReader(f))
    issued = parse_timestamp(status.get('status_generated_at_utc'))
    timeline = status.get('forecast_hourly_timeline', [])
    fort = status.get('fort_monroe', {})
    existing = {(r['issue_time_utc'], r['lead_hours']) for r in rows}

    # 1. Archive newly issued forecast leads (1, 3, 6, 12, 24, 48 hours)
    if issued:
        for h in (1, 3, 6, 12, 24, 48):
            target = issued + timedelta(hours=h)
            eligible = [
                r for r in timeline
                if parse_timestamp(r.get('timestamp_utc'))
                and parse_timestamp(r['timestamp_utc']) > issued
                and finite_number(r.get('forecast_stage_mllw_ft'))
            ]
            item = min(eligible, key=lambda r: abs((parse_timestamp(r['timestamp_utc']) - target).total_seconds()), default=None)
            if not item or (issued.isoformat(), str(h)) in existing:
                continue
            valid = parse_timestamp(item['timestamp_utc'])
            rows.append(dict(
                issue_time_utc=issued.isoformat(),
                guidance_issued_at_utc=status.get('forecast_issued_at_utc', ''),
                valid_time_utc=valid.isoformat(),
                lead_hours=str(h),
                actual_lead_hours=round((valid - issued).total_seconds() / 3600, 3),
                predicted_stage_mllw_ft=item['forecast_stage_mllw_ft'],
                nwps_raw_stage_ft=item.get('nwps_raw_stage_ft', ''),
                fort_observation_time_utc=fort.get('observation_time_utc', ''),
                fort_elevation_navd88_ft=fort.get('elevation_navd88_ft', ''),
                observed_stage_mllw_ft='',
                verified_at_utc=''
            ))

    # 2. Build dictionary of verified observations: 6-minute readings + hourly archive fallback
    measurements = {r['datetime_utc']: r['stage_mllw_ft'] for r in ware_obs if finite_number(r.get('stage_mllw_ft'))}
    h_file = Path(hourly_archive_path) if hourly_archive_path else None
    if h_file and h_file.exists():
        try:
            with h_file.open() as f:
                for r in csv.DictReader(f):
                    dt = parse_timestamp(r.get('timestamp_utc'))
                    stg = _parse_float(r.get('ware_river_stage_mllw_ft'))
                    if dt and stg is not None and dt not in measurements:
                        measurements[dt] = stg
        except Exception:
            pass

    # 3. Match observations with issued forecasts (within 360 seconds / 6 minutes)
    for row in rows:
        if row.get('observed_stage_mllw_ft') not in ('', None):
            continue
        valid = parse_timestamp(row['valid_time_utc'])
        if not valid:
            continue
        nearby = [t for t in measurements if abs((t - valid).total_seconds()) <= 360]
        if nearby:
            best = min(nearby, key=lambda t: abs((t - valid).total_seconds()))
            row['observed_stage_mllw_ft'] = measurements[best]
            row['verified_at_utc'] = issued.isoformat() if issued else datetime.now(timezone.utc).isoformat()

    # 4. Atomically persist updated archive CSV
    if rows:
        file.parent.mkdir(parents=True, exist_ok=True)
        import os, tempfile
        fd, tmp = tempfile.mkstemp(dir=file.parent, prefix='.issued-')
        try:
            with os.fdopen(fd, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(rows)
            os.replace(tmp, file)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    # 5. Evaluate prospective performance per lead time (Operational ML/Hybrid vs Raw NWPS)
    results = []
    for h in (1, 3, 6, 12, 24, 48):
        paired = [
            r for r in rows
            if r['lead_hours'] == str(h)
            and r.get('observed_stage_mllw_ft') not in ('', None)
            and _parse_float(r.get('observed_stage_mllw_ft')) is not None
        ]
        
        op_errors = [
            abs(_parse_float(r['predicted_stage_mllw_ft']) - _parse_float(r['observed_stage_mllw_ft']))
            for r in paired
            if _parse_float(r.get('predicted_stage_mllw_ft')) is not None
        ]
        mae_ft = (sum(op_errors) / len(op_errors)) if op_errors else None

        # NWPS raw evaluation
        nwps_paired = [
            r for r in paired
            if _parse_float(r.get('nwps_raw_stage_ft')) is not None
        ]
        nwps_errors = [
            abs(_parse_float(r['nwps_raw_stage_ft']) - _parse_float(r['observed_stage_mllw_ft']))
            for r in nwps_paired
        ]
        nwps_mae_ft = (sum(nwps_errors) / len(nwps_errors)) if nwps_errors else None

        # Direct common subset comparison
        common_paired = [
            r for r in paired
            if _parse_float(r.get('predicted_stage_mllw_ft')) is not None
            and _parse_float(r.get('nwps_raw_stage_ft')) is not None
        ]
        common_op_errors = [
            abs(_parse_float(r['predicted_stage_mllw_ft']) - _parse_float(r['observed_stage_mllw_ft']))
            for r in common_paired
        ]
        common_op_mae = (sum(common_op_errors) / len(common_op_errors)) if common_op_errors else None

        skill_delta_ft = None
        skill_improvement_pct = None
        if nwps_mae_ft is not None and common_op_mae is not None:
            skill_delta_ft = round(nwps_mae_ft - common_op_mae, 4)
            if nwps_mae_ft > 0:
                skill_improvement_pct = round((nwps_mae_ft - common_op_mae) / nwps_mae_ft * 100, 1)
            else:
                skill_improvement_pct = 0.0

        # Storm event / high-water metrics (stage >= 4.0 ft)
        high = [r for r in paired if _parse_float(r['observed_stage_mllw_ft']) >= HIGH_WATER_THRESHOLD_FT]
        high_op_errors = [
            abs(_parse_float(r['predicted_stage_mllw_ft']) - _parse_float(r['observed_stage_mllw_ft']))
            for r in high
            if _parse_float(r.get('predicted_stage_mllw_ft')) is not None
        ]
        high_water_mae_ft = (sum(high_op_errors) / len(high_op_errors)) if high_op_errors else None
        misses = sum(_parse_float(r['predicted_stage_mllw_ft']) < HIGH_WATER_THRESHOLD_FT for r in high if _parse_float(r.get('predicted_stage_mllw_ft')) is not None)
        false_alarms = sum(
            _parse_float(r['predicted_stage_mllw_ft']) >= HIGH_WATER_THRESHOLD_FT
            and _parse_float(r['observed_stage_mllw_ft']) < HIGH_WATER_THRESHOLD_FT
            for r in paired
            if _parse_float(r.get('predicted_stage_mllw_ft')) is not None
        )

        high_nwps = [r for r in nwps_paired if _parse_float(r['observed_stage_mllw_ft']) >= HIGH_WATER_THRESHOLD_FT]
        high_nwps_errors = [
            abs(_parse_float(r['nwps_raw_stage_ft']) - _parse_float(r['observed_stage_mllw_ft']))
            for r in high_nwps
        ]
        nwps_high_water_mae_ft = (sum(high_nwps_errors) / len(high_nwps_errors)) if high_nwps_errors else None
        nwps_misses = sum(_parse_float(r['nwps_raw_stage_ft']) < HIGH_WATER_THRESHOLD_FT for r in high_nwps)
        nwps_false_alarms = sum(
            _parse_float(r['nwps_raw_stage_ft']) >= HIGH_WATER_THRESHOLD_FT
            and _parse_float(r['observed_stage_mllw_ft']) < HIGH_WATER_THRESHOLD_FT
            for r in nwps_paired
        )

        results.append(dict(
            lead_hours=h,
            n=len(paired),
            mae_ft=mae_ft,
            nwps_n=len(nwps_paired),
            nwps_mae_ft=nwps_mae_ft,
            skill_delta_ft=skill_delta_ft,
            skill_improvement_pct=skill_improvement_pct,
            high_water_n=len(high),
            high_water_mae_ft=high_water_mae_ft,
            nwps_high_water_mae_ft=nwps_high_water_mae_ft,
            misses=misses,
            nwps_misses=nwps_misses,
            false_alarms=false_alarms,
            nwps_false_alarms=nwps_false_alarms
        ))

    # 6. Overall summary across all verified issue rows
    all_paired = [
        r for r in rows
        if r.get('observed_stage_mllw_ft') not in ('', None)
        and _parse_float(r.get('observed_stage_mllw_ft')) is not None
    ]
    all_op_errors = [
        abs(_parse_float(r['predicted_stage_mllw_ft']) - _parse_float(r['observed_stage_mllw_ft']))
        for r in all_paired
        if _parse_float(r.get('predicted_stage_mllw_ft')) is not None
    ]
    all_nwps_paired = [
        r for r in all_paired
        if _parse_float(r.get('nwps_raw_stage_ft')) is not None
    ]
    all_nwps_errors = [
        abs(_parse_float(r['nwps_raw_stage_ft']) - _parse_float(r['observed_stage_mllw_ft']))
        for r in all_nwps_paired
    ]
    all_high = [r for r in all_paired if _parse_float(r['observed_stage_mllw_ft']) >= HIGH_WATER_THRESHOLD_FT]
    all_high_nwps = [r for r in all_nwps_paired if _parse_float(r['observed_stage_mllw_ft']) >= HIGH_WATER_THRESHOLD_FT]

    overall_mae = (sum(all_op_errors) / len(all_op_errors)) if all_op_errors else None
    overall_nwps_mae = (sum(all_nwps_errors) / len(all_nwps_errors)) if all_nwps_errors else None
    overall_skill_delta = (round(overall_nwps_mae - overall_mae, 4)) if (overall_nwps_mae is not None and overall_mae is not None) else None
    overall_improvement_pct = (round((overall_nwps_mae - overall_mae) / overall_nwps_mae * 100, 1)) if (overall_nwps_mae and overall_mae is not None and overall_nwps_mae > 0) else None

    summary = {
        "verified_rows": len(all_paired),
        "nwps_verified_rows": len(all_nwps_paired),
        "overall_operational_mae_ft": round(overall_mae, 4) if overall_mae is not None else None,
        "overall_nwps_mae_ft": round(overall_nwps_mae, 4) if overall_nwps_mae is not None else None,
        "overall_skill_delta_ft": overall_skill_delta,
        "overall_skill_improvement_pct": overall_improvement_pct,
        "high_water_observations": len(all_high),
        "high_water_operational_misses": sum(_parse_float(r['predicted_stage_mllw_ft']) < HIGH_WATER_THRESHOLD_FT for r in all_high if _parse_float(r.get('predicted_stage_mllw_ft')) is not None),
        "high_water_nwps_misses": sum(_parse_float(r['nwps_raw_stage_ft']) < HIGH_WATER_THRESHOLD_FT for r in all_high_nwps),
        "high_water_operational_false_alarms": sum(
            _parse_float(r['predicted_stage_mllw_ft']) >= HIGH_WATER_THRESHOLD_FT
            and _parse_float(r['observed_stage_mllw_ft']) < HIGH_WATER_THRESHOLD_FT
            for r in all_paired
            if _parse_float(r.get('predicted_stage_mllw_ft')) is not None
        ),
        "high_water_nwps_false_alarms": sum(
            _parse_float(r['nwps_raw_stage_ft']) >= HIGH_WATER_THRESHOLD_FT
            and _parse_float(r['observed_stage_mllw_ft']) < HIGH_WATER_THRESHOLD_FT
            for r in all_nwps_paired
        ),
    }
    if summary["high_water_observations"] == 0:
        # Say it plainly: with zero verified high-water samples, the high-water
        # skill columns are unvalidated and storm performance is unknown.
        summary["high_water_caveat"] = (
            "No high-water observations (stage >= 4.00 ft MLLW) have been verified yet; "
            "high-water skill metrics are unvalidated and storm performance is unknown.")
    else:
        summary["high_water_caveat"] = None

    result = dict(
        updated_at_utc=issued.isoformat() if issued else None,
        issued_rows=len(rows),
        summary=summary,
        results=results,
        interpretation='Prospective deployed guidance verification against Ware River comparing operational model with raw NOAA NWPS guidance. Nominal lead bins use the nearest forecast hour; actual_lead_hours records exact lead. Repeated issues are correlated across forecast horizons. High-water threshold is 4.00 ft MLLW. Fort Monroe remains observational until a paired candidate passes promotion gates.'
    )
    atomic_write_json(score_path, result)
    return result

