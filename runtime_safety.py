"""Shared data validity, risk, and atomic persistence helpers (standard library only)."""
import csv
import json
import math
import os
import tempfile
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

UNKNOWN_TIER = -1
MAX_DATA_AGE_MINUTES = 90
EASTERN = ZoneInfo("America/New_York")

# Forecast completeness policy: a 48-hour outlook is usable when at least this
# many hours carry water, wind, and rainfall guidance, and no missing hour sits
# near high water where it could hide a flood peak.
FORECAST_WINDOW_HOURS = 48
MIN_FORECAST_COMPLETE_HOURS = 44
ACTION_STAGE_FT = 4.0
GAP_HAZARD_MARGIN_FT = 0.3
GAP_NEIGHBORHOOD_HOURS = 3


def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def parse_timestamp(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        for suffix in (" UTC", " EDT", " EST"):
            if value.endswith(suffix):
                naive = datetime.fromisoformat(value[:-4])
                if suffix == " UTC":
                    return naive.replace(tzinfo=timezone.utc)
                # Retain the explicit offset even during the repeated DST hour.
                from datetime import timezone as fixed_timezone
                offset = -4 if suffix == " EDT" else -5
                return naive.replace(tzinfo=fixed_timezone(timedelta(hours=offset)))
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result if result.tzinfo else result.replace(tzinfo=EASTERN)
    except (ValueError, TypeError):
        return None


def is_recent(value, now=None, max_minutes=MAX_DATA_AGE_MINUTES):
    now = now or datetime.now(timezone.utc)
    parsed = parse_timestamp(value)
    return parsed is not None and -5 <= (now - parsed).total_seconds() / 60 <= max_minutes


def _gaps_hide_hazard(timeline, start):
    """True when a missing forecast hour sits near high water and could hide a flood peak.

    A handful of missing hours is tolerable only when the surrounding guidance is
    safely below the action stage. If any hour within GAP_NEIGHBORHOOD_HOURS of a
    gap shows stage within GAP_HAZARD_MARGIN_FT of the action stage, the gap is
    treated as potentially hiding a flood crest.
    """
    stage_by_hour = {}
    for row in timeline:
        stamp = parse_timestamp(row.get("timestamp_utc"))
        stage = row.get("forecast_stage_mllw_ft")
        if stamp is None or not finite_number(stage):
            continue
        hour = stamp.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
        if start <= hour < start + timedelta(hours=FORECAST_WINDOW_HOURS):
            stage_by_hour[hour] = stage
    for offset in range(FORECAST_WINDOW_HOURS):
        hour = start + timedelta(hours=offset)
        if hour in stage_by_hour:
            continue
        nearby = [s for h, s in stage_by_hour.items()
                  if abs((h - hour).total_seconds()) <= GAP_NEIGHBORHOOD_HOURS * 3600]
        if nearby and max(nearby) >= ACTION_STAGE_FT - GAP_HAZARD_MARGIN_FT:
            return True
    return False


def assess_status(status, now=None):
    """Recheck timestamps at use time; never infer healthy data from tier zero."""
    now = now or datetime.now(timezone.utc)
    current = status.get("current_conditions", {})
    generated = status.get("status_generated_at_utc")
    current_ok = (finite_number(current.get("ware_river_stage_mllw_ft"))
                  and is_recent(current.get("observation_timestamp_local"), now))
    timeline = status.get("forecast_hourly_timeline", [])
    start = now.replace(minute=0, second=0, microsecond=0)
    valid_hours = set()
    known_hours = set()
    for row in timeline:
        stamp = parse_timestamp(row.get("timestamp_utc"))
        if stamp is None or not finite_number(row.get("forecast_stage_mllw_ft")):
            continue
        hour = stamp.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
        if start <= hour < start + timedelta(hours=48):
            known_hours.add(hour)
            if row.get("weather_available") is True and row.get("precipitation_available") is True:
                valid_hours.add(hour)
    recent_generation = is_recent(generated, now)
    complete_enough = len(valid_hours) >= MIN_FORECAST_COMPLETE_HOURS
    gaps_hide_hazard = _gaps_hide_hazard(timeline, start)
    forecast_ok = recent_generation and complete_enough and not gaps_hide_hazard
    source_health = status.get("source_health", {})
    if any(v.get("required") and not v.get("available") for v in source_health.values()):
        forecast_ok = False
    reasons = []
    if not current_ok:
        reasons.append("Current gauge observation is missing or older than 90 minutes.")
    if not recent_generation:
        reasons.append("Pipeline update is missing or older than 90 minutes.")
    if not complete_enough:
        reasons.append(
            f"Only {len(valid_hours)} of {FORECAST_WINDOW_HOURS} forecast hours carry complete "
            f"water, wind, and rainfall guidance (need {MIN_FORECAST_COMPLETE_HOURS}).")
    elif gaps_hide_hazard:
        reasons.append("Missing forecast hours sit near high water; a flood peak could be hidden.")
    if not forecast_ok and complete_enough and not gaps_hide_hazard:
        reasons.append("A complete fresh 48-hour water, wind, and rainfall forecast is unavailable.")
    return {
        "current_available": current_ok,
        "forecast_available": forecast_ok,
        "forecast_usable": recent_generation and bool(known_hours),
        "forecast_hours_available": len(valid_hours),
        "alerts_all_clear_allowed": current_ok and forecast_ok,
        "state": "healthy" if current_ok and forecast_ok else "degraded",
        "reasons": reasons,
        "max_age_minutes": MAX_DATA_AGE_MINUTES,
    }


def compound_risk_tier(stage, evaluation):
    if not finite_number(stage):
        return UNKNOWN_TIER, "Unknown (water-level data unavailable)"
    stage_tier = 0 if stage < 4 else 1 if stage < 4.4 else 2 if stage < 4.8 else 3
    depths = [evaluation.get("total_compound_depth_in")]
    depths.extend(s.get("depth_in") for key, s in evaluation.get("sectors", {}).items() if key != "ditches")
    depths.extend(s.get("depth_in") for s in evaluation.get("streets", {}).values())
    worst = max((v for v in depths if finite_number(v)), default=0)
    impact_tier = 3 if worst >= 7.5 else 2 if worst >= 3.5 else 1 if worst > 0 else 0
    tier = max(stage_tier, impact_tier)
    labels = ["Tier 0 (No modeled inundation)", "Tier 1 (Nuisance / Low spots wet)",
              "Tier 2 (Moderate / Roads flooded)", "Tier 3 (Severe / Travel hazardous)"]
    return tier, labels[tier]


def atomic_write_json(path, payload):
    """Replace complete JSON atomically; propagate errors to the caller."""
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_write_csv(path, rows, fieldnames):
    """Replace a CSV file atomically via temp file + rename.

    A crash mid-write can never leave a truncated archive behind; readers
    always see either the old or the new complete file.
    """
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".pending-", suffix=".csv", dir=parent)
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames, restval="", extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
