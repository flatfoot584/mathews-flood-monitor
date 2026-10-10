#!/usr/bin/env python3
"""
ingest_realtime.py — Real-Time Hydrological & Meteorological Ingestion Pipeline
for Mathews County, Virginia Flood Prediction System.

Incorporates:
1. Real-time multi-network sensor ingestion (NOAA NWPS, NOAA CO-OPS, NWS AKQ)
2. Hybrid Hydrodynamic–ML Residual Modeling (blends NOAA NWPS CBOFS stage with local wind stress ML correction)
3. Compound Pluvial + Tidal Inundation Physics (precipitation backwater entrapment)
4. Multi-Sector Micro-Topographical Elevation Mapping (Ditches, Driveway Apron, Main Driveway, Yard, Garage)
5. Vehicle Passability Evaluation Matrix (Sedans vs. SUVs vs. Impassable)

Outputs:
- latest_status.json: Complete real-time status summary and multi-sector risk evaluation
- realtime_recent_observations.csv: Hourly-aligned recent observations (same schema as merged training dataset)
- forecast_48h.csv: Hourly forward forecast table (48 hours ahead)

Author: Antigravity Assistant for Mathews County Flood Prediction Project
"""

import os
import sys
import csv
import json
import math
import time
import argparse
import hashlib
import re
from pathlib import Path
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import threading
import concurrent.futures

import micro_topography
from runtime_safety import (assess_status, atomic_write_csv, atomic_write_json, compound_risk_tier,
                            finite_number, is_recent, UNKNOWN_TIER)
from forecast_verification import archive_and_verify

SOURCE_HEALTH = {}
_HEALTH_LOCK = threading.Lock()
FORECAST_ISSUED_AT = None

# Timezone standard
EASTERN_TZ = ZoneInfo("America/New_York")

# Physical thresholds & empirical models
FLOOD_STAGE_THRESHOLD = 3.99  # ft (approx 4.0 ft)
STAGE_TO_DEPTH_SLOPE = 10.95  # inches per foot rise
STAGE_TO_DEPTH_INTERCEPT = -43.69
DATUM_OFFSET_NAVD88_MLLW = -1.64  # NAVD88 = MLLW - 1.64 ft

COMPASS_DIRS = {
    'N': 0.0, 'NNE': 22.5, 'NE': 45.0, 'ENE': 67.5,
    'E': 90.0, 'ESE': 112.5, 'SE': 135.0, 'SSE': 157.5,
    'S': 180.0, 'SSW': 202.5, 'SW': 225.0, 'WSW': 247.5,
    'W': 270.0, 'WNW': 292.5, 'NW': 315.0, 'NNW': 337.5
}

def degrees_to_compass(deg):
    if deg is None:
        return "N/A"
    deg = deg % 360
    val = int((deg / 22.5) + 0.5)
    arr = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
           "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return arr[val % 16]

def get_risk_tier(stage_mllw_ft):
    if not finite_number(stage_mllw_ft):
        return UNKNOWN_TIER, "Unknown (water-level data unavailable)"
    if stage_mllw_ft < 4.0:
        return 0, "Tier 0 (Normal / Safe)"
    elif stage_mllw_ft < 4.4:
        return 1, "Tier 1 (Nuisance / Ditch Full)"
    elif stage_mllw_ft < 4.8:
        return 2, "Tier 2 (Moderate Inundation)"
    else:
        return 3, "Tier 3 (Severe Inundation)"

def estimate_flood_depth_in(stage_mllw_ft):
    if not finite_number(stage_mllw_ft):
        return None
    if stage_mllw_ft < FLOOD_STAGE_THRESHOLD:
        return 0.0
    depth = STAGE_TO_DEPTH_SLOPE * stage_mllw_ft + STAGE_TO_DEPTH_INTERCEPT
    return max(0.0, round(depth, 2))

def fetch_json(url, max_retries=3, backoff=2.0, timeout=15):
    """Cache successful public API responses; expose cached data age explicitly."""
    cache_dir = Path(os.getenv("FLOOD_CACHE_DIR", ".cache/api"))
    parsed = urllib.parse.urlsplit(url)
    parameters = urllib.parse.parse_qs(parsed.query)
    window = ""
    if "begin_date" in parameters:
        try:
            begin = datetime.strptime(parameters["begin_date"][0], "%Y%m%d %H:%M").replace(tzinfo=timezone.utc)
            window = "future" if begin >= datetime.now(timezone.utc) - timedelta(hours=1) else "past"
        except ValueError:
            window = "unknown"
    stable_query = urllib.parse.urlencode(sorted((key, values[0]) for key, values in parameters.items()
                                              if key not in ("begin_date", "end_date")))
    cache_key = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, stable_query, "")) + window
    cache_file = cache_dir / (hashlib.sha256(cache_key.encode()).hexdigest() + ".json")
    request = urllib.request.Request(url, headers={"User-Agent": "MathewsCountyFloodStudy/1.1"})
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
                if not isinstance(payload, dict) or "error" in payload or payload.get("status", 200) in (400, 404, 500):
                    raise ValueError("API returned an error payload")
            stamp = datetime.now(timezone.utc).isoformat()
            with _HEALTH_LOCK:
                SOURCE_HEALTH[url] = {"available": True, "cached": False, "retrieved_at_utc": stamp}
            try:
                atomic_write_json(cache_file, {"retrieved_at_utc": stamp, "payload": payload})
            except OSError:
                print("[WARN] Could not persist API cache.", file=sys.stderr)
            return payload
        except (urllib.error.URLError, OSError, ValueError, TimeoutError):
            if attempt + 1 < max_retries:
                time.sleep(backoff * (attempt + 1))
    try:
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        fresh = is_recent(cached.get("retrieved_at_utc"))
        with _HEALTH_LOCK:
            SOURCE_HEALTH[url] = {"available": fresh, "cached": True,
                                  "retrieved_at_utc": cached.get("retrieved_at_utc")}
        if not fresh:
            # Never serve a stale cached response as live data. Outages are
            # handled explicitly (preserve_last_forecast) with clear labeling.
            print("[WARN] API unavailable and cached response is stale; treating as unavailable.", file=sys.stderr)
            return None
        print("[WARN] API unavailable; using a timestamped cached response.", file=sys.stderr)
        return cached["payload"]
    except (OSError, ValueError, KeyError):
        with _HEALTH_LOCK:
            SOURCE_HEALTH[url] = {"available": False, "cached": False}
        print("[WARN] API unavailable and no valid cached response exists.", file=sys.stderr)
        return None


def matched_surge(observed, predictions):
    """Subtract values at a common time, rather than unrelated latest readings."""
    predicted = {r["datetime_utc"]: r.get("water_level_ft") for r in predictions or []}
    for row in reversed(observed or []):
        actual = row.get("water_level_ft")
        tide = predicted.get(row["datetime_utc"])
        if finite_number(actual) and finite_number(tide):
            return round(actual - tide, 2)
    return None

def fetch_nwps_wrvv2_observed():
    """Fetch observed 6-min stage from NOAA NWPS API for WRVV2."""
    url = "https://api.water.noaa.gov/nwps/v1/gauges/WRVV2/stageflow/observed"
    data = fetch_json(url)
    if not data or "data" not in data:
        return []
    records = []
    for item in data.get("data", []):
        valid_time_str = item.get("validTime")
        stage = item.get("primary")
        if not valid_time_str or stage is None or stage == -999:
            continue
        try:
            stage = float(stage)
            if not finite_number(stage):
                continue
            dt_utc = datetime.fromisoformat(valid_time_str.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            continue
        records.append({
            "datetime_utc": dt_utc,
            "stage_mllw_ft": float(stage),
            "stage_navd88_ft": round(float(stage) + DATUM_OFFSET_NAVD88_MLLW, 2)
        })
    records.sort(key=lambda x: x["datetime_utc"])
    return records

def fetch_nwps_wrvv2_forecast():
    """Fetch forecast stage hydrograph from NOAA NWPS API for WRVV2."""
    url = "https://api.water.noaa.gov/nwps/v1/gauges/WRVV2/stageflow/forecast"
    global FORECAST_ISSUED_AT
    data = fetch_json(url)
    FORECAST_ISSUED_AT = data.get("issuedTime") if data else None
    if not data or "data" not in data:
        return []
    records = []
    for item in data.get("data", []):
        valid_time_str = item.get("validTime")
        stage = item.get("primary")
        if not valid_time_str or stage is None or stage == -999:
            continue
        try:
            stage = float(stage)
            if not finite_number(stage):
                continue
            dt_utc = datetime.fromisoformat(valid_time_str.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            continue
        records.append({
            "datetime_utc": dt_utc,
            "forecast_stage_mllw_ft": float(stage),
            "forecast_stage_navd88_ft": round(float(stage) + DATUM_OFFSET_NAVD88_MLLW, 2)
        })
    records.sort(key=lambda x: x["datetime_utc"])
    return records

def fetch_fort_monroe_observed():
    """FTMV2 primary values are MLLW; metadata specifies NAVD88 = MLLW - 1.70.
    Keep this station conversion separate from Ware River's 1.64 ft offset.
    This is an optional evaluation sensor, never a required safety input.
    """
    url = "https://api.water.noaa.gov/nwps/v1/gauges/FTMV2/stageflow/observed"
    payload = fetch_json(url)
    if not payload or payload.get("primaryUnits") != "ft":
        return []
    records = []
    for row in payload.get("data", []):
        value = row.get("primary")
        if not finite_number(value) or value == -999:
            continue
        try:
            dt = datetime.fromisoformat(row["validTime"].replace("Z", "+00:00"))
        except (KeyError, ValueError, TypeError):
            continue
        records.append({"datetime_utc": dt, "elevation_navd88_ft": round(value - 1.70, 3),
                        "water_level_mllw_ft": value,
                        "received_at_utc": row.get("generatedTime")})
    return sorted(records, key=lambda r: r["datetime_utc"])


def add_fort_hourly(hourly, observations):
    grouped = {}
    for row in observations:
        hour = row["datetime_utc"].replace(minute=0, second=0, microsecond=0)
        grouped.setdefault(hour, []).append(row["elevation_navd88_ft"])
    for row in hourly:
        stamp = datetime.strptime(row["timestamp_utc"], "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=timezone.utc)
        values = grouped.get(stamp, [])
        row["fort_monroe_elevation_navd88_ft"] = round(sum(values) / len(values), 3) if values else ""
    return hourly


def fetch_official_alerts():
    url = "https://api.weather.gov/alerts/active?point=37.420183,-76.406550"
    payload = fetch_json(url, max_retries=2)
    health = SOURCE_HEALTH.get(url, {})
    items = []
    for feature in (payload or {}).get("features", []):
        props = feature.get("properties", {})
        items.append({"event": props.get("event"), "headline": props.get("headline"),
                      "effective": props.get("effective"), "expires": props.get("expires"),
                      "severity": props.get("severity")})
    return {"available": bool(payload and health.get("available")),
            "retrieved_at_utc": health.get("retrieved_at_utc"), "alerts": items,
            "source": "https://www.weather.gov/akq/"}


def fetch_coops_product(station, product, begin_dt_utc, end_dt_utc, datum="mllw"):
    """Fetch NOAA CO-OPS data product for a given station and time window."""
    base_url = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
    begin_str = begin_dt_utc.strftime("%Y%m%d %H:%M").replace(" ", "%20")
    end_str = end_dt_utc.strftime("%Y%m%d %H:%M").replace(" ", "%20")
    url = (f"{base_url}?begin_date={begin_str}&end_date={end_str}&station={station}"
           f"&product={product}&datum={datum}&units=english&time_zone=gmt"
           f"&application=MathewsFloodStudy&format=json")
    
    data = fetch_json(url)
    if not data:
        return []
    
    key = "predictions" if product == "predictions" else "data"
    raw_list = data.get(key, [])
    records = []
    for item in raw_list:
        t_str = item.get("t")
        if not t_str:
            continue
        try:
            dt_utc = datetime.strptime(t_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            # One malformed record must never kill the whole feed.
            continue
        rec = {"datetime_utc": dt_utc}

        if product == "wind":
            try:
                speed_raw = item.get("s")
                if speed_raw in (None, ""):
                    continue  # never fabricate calm from a missing reading
                rec["wind_speed_mph"] = round(float(speed_raw) * 1.15078, 2)
                dir_raw = item.get("d")
                rec["wind_dir_deg"] = round(float(dir_raw), 1) if dir_raw not in (None, "") else None
                gust_str = item.get("g")
                rec["wind_gust_mph"] = round(float(gust_str) * 1.15078, 2) if gust_str not in (None, "") else rec["wind_speed_mph"]
            except (ValueError, TypeError):
                continue
        elif product == "air_pressure":
            try:
                rec["baro_mb"] = round(float(item.get("v")), 1)
            except (ValueError, TypeError):
                continue
        elif product == "air_temperature":
            try:
                rec["air_temp_f"] = round(float(item.get("v")), 1)
            except (ValueError, TypeError):
                continue
        elif product in ("water_level", "predictions"):
            try:
                rec["water_level_ft"] = round(float(item.get("v")), 3)
            except (ValueError, TypeError):
                continue
                
        if any(not finite_number(value) for key, value in rec.items() if key != "datetime_utc"):
            continue
        records.append(rec)
    records.sort(key=lambda x: x["datetime_utc"])
    return records

def fetch_nws_hourly_forecast():
    """Fetch NWS hourly forecast for grid AKQ 80,76 (Ware River / Mathews County)."""
    url = "https://api.weather.gov/gridpoints/AKQ/80,76/forecast/hourly"
    data = fetch_json(url)
    if not data or "properties" not in data or "periods" not in data["properties"]:
        return []
    
    periods = data["properties"]["periods"]
    records = []
    for p in periods:
        start_str = p.get("startTime")
        if not start_str:
            continue
        try:
            dt = datetime.fromisoformat(start_str)
        except (ValueError, TypeError):
            # One malformed period must never kill the whole forecast.
            continue
        dt_utc = dt.astimezone(timezone.utc)
        
        # Parse wind speed
        spd_str = p.get("windSpeed", "") or ""
        digits = [float(x) for x in "".join([c if c.isdigit() or c == "." else " " for c in spd_str]).split()]
        wind_spd = sum(digits) / len(digits) if digits else None
        
        wind_dir_cardinal = p.get("windDirection", "") or ""
        wind_dir_deg = COMPASS_DIRS.get(wind_dir_cardinal.upper())
        temp_f = p.get("temperature")
        pop = p.get("probabilityOfPrecipitation", {}).get("value", 0) or 0
        short_fcst = p.get("shortForecast", "")
        
        records.append({
            "datetime_utc": dt_utc,
            "wind_speed_mph": round(wind_spd, 1) if wind_spd is not None else None,
            "wind_dir_deg": wind_dir_deg,
            "wind_dir_cardinal": wind_dir_cardinal,
            "temp_f": temp_f,
            "pop_percent": pop,
            "short_forecast": short_fcst
        })
    records.sort(key=lambda x: x["datetime_utc"])
    return records

def parse_duration(text):
    """Parse fixed ISO 8601 day/hour/minute/second durations, rejecting months."""
    match = re.fullmatch(r"P(?:(\d+(?:\.\d+)?)D)?(?:T(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)S)?)?", text)
    if not match or not any(match.groups()):
        raise ValueError("Unsupported duration")
    days, hours, minutes, seconds = (float(v or 0) for v in match.groups())
    result = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
    if result.total_seconds() <= 0 or result > timedelta(days=14):
        raise ValueError("Invalid forecast duration")
    return result


def fetch_nws_qpf_map():
    """Distribute interval rainfall by hourly overlap, preserving total volume."""
    data = fetch_json("https://api.weather.gov/gridpoints/AKQ/80,76")
    values = (data or {}).get("properties", {}).get("quantitativePrecipitation", {}).get("values", [])
    rain_by_hour = {}
    for item in values:
        try:
            value = item.get("value")
            if not finite_number(value) or value < 0:
                continue
            start_text, duration_text = item["validTime"].split("/")
            start = datetime.fromisoformat(start_text.replace("Z", "+00:00")).astimezone(timezone.utc)
            duration = parse_duration(duration_text)
            end = start + duration
            hour = start.replace(minute=0, second=0, microsecond=0)
            while hour < end:
                overlap = (min(end, hour + timedelta(hours=1)) - max(start, hour)).total_seconds()
                if overlap > 0:
                    rain_by_hour[hour] = rain_by_hour.get(hour, 0.0) + value / 25.4 * overlap / duration.total_seconds()
                hour += timedelta(hours=1)
        except (KeyError, TypeError, ValueError):
            continue
    return rain_by_hour

def aggregate_hourly_observations(ware_obs, yt_winds, yt_press, yt_temps, yt_water, yt_preds, wm_water, wm_preds, sw_water=None, sw_preds=None, lookback_hours=48):
    """Aggregate 6-min observations into hourly rows matching the training schema, including bay hydraulic slope."""
    now_utc = datetime.now(timezone.utc)
    start_utc = (now_utc - timedelta(hours=lookback_hours)).replace(minute=0, second=0, microsecond=0)
    
    def group_by_hour(records, val_key):
        grouped = {}
        for r in (records or []):
            hr_dt = r["datetime_utc"].replace(minute=0, second=0, microsecond=0)
            if hr_dt not in grouped:
                grouped[hr_dt] = []
            if isinstance(r, dict) and r.get(val_key) is not None:
                grouped[hr_dt].append(r[val_key])
        return grouped
    
    ware_grouped = group_by_hour(ware_obs, "stage_mllw_ft")
    
    yt_wind_grouped = {}
    for r in yt_winds:
        hr_dt = r["datetime_utc"].replace(minute=0, second=0, microsecond=0)
        if hr_dt not in yt_wind_grouped:
            yt_wind_grouped[hr_dt] = {"speeds": [], "dirs": [], "gusts": []}
        yt_wind_grouped[hr_dt]["speeds"].append(r["wind_speed_mph"])
        if r.get("wind_dir_deg") is not None:
            yt_wind_grouped[hr_dt]["dirs"].append(r["wind_dir_deg"])
        yt_wind_grouped[hr_dt]["gusts"].append(r["wind_gust_mph"])
        
    yt_press_grouped = group_by_hour(yt_press, "baro_mb")
    yt_temps_grouped = group_by_hour(yt_temps, "air_temp_f")
    yt_water_grouped = group_by_hour(yt_water, "water_level_ft")
    yt_preds_grouped = group_by_hour(yt_preds, "water_level_ft")
    wm_water_grouped = group_by_hour(wm_water, "water_level_ft")
    wm_preds_grouped = group_by_hour(wm_preds, "water_level_ft")
    sw_water_grouped = group_by_hour(sw_water, "water_level_ft")
    sw_preds_grouped = group_by_hour(sw_preds, "water_level_ft")
    
    curr = start_utc
    hourly_rows = []
    
    while curr <= now_utc:
        dt_local = curr.astimezone(EASTERN_TZ)
        
        # Ware river
        w_stages = ware_grouped.get(curr, [])
        ware_mean = round(sum(w_stages) / len(w_stages), 2) if w_stages else None
        ware_max = round(max(w_stages), 2) if w_stages else None
        ware_navd88 = round(ware_mean + DATUM_OFFSET_NAVD88_MLLW, 2) if ware_mean is not None else None
        
        # Yorktown wind
        w_info = yt_wind_grouped.get(curr)
        w_spd = round(sum(w_info["speeds"]) / len(w_info["speeds"]), 2) if (w_info and w_info["speeds"]) else None
        w_dir = round(math.degrees(math.atan2(
            sum(math.sin(math.radians(d)) for d in w_info["dirs"]),
            sum(math.cos(math.radians(d)) for d in w_info["dirs"]))) % 360, 1) if (w_info and w_info["dirs"]) else None
        w_gst = round(max(w_info["gusts"]), 2) if (w_info and w_info["gusts"]) else None
        
        # Physical wind vectors
        u_wind = None
        v_wind = None
        along_bay_wind = None
        cross_bay_wind = None
        if w_spd is not None and w_dir is not None:
            rad = math.radians(w_dir)
            u_wind = round(-w_spd * math.sin(rad), 2)
            v_wind = round(-w_spd * math.cos(rad), 2)
            bay_rad = math.radians(w_dir - 20)
            along_bay_wind = round(w_spd * math.cos(bay_rad), 2)
            cross_bay_wind = round(w_spd * math.sin(bay_rad), 2)
            
        press_list = yt_press_grouped.get(curr, [])
        baro = round(sum(press_list) / len(press_list), 1) if press_list else None
        
        temp_list = yt_temps_grouped.get(curr, [])
        temp_f = round(sum(temp_list) / len(temp_list), 1) if temp_list else None
        
        yt_pred_list = yt_preds_grouped.get(curr, [])
        yt_pred = round(sum(yt_pred_list) / len(yt_pred_list), 3) if yt_pred_list else None
        
        wm_ver_list = wm_water_grouped.get(curr, [])
        wm_ver = round(sum(wm_ver_list) / len(wm_ver_list), 3) if wm_ver_list else None
        
        wm_pred_list = wm_preds_grouped.get(curr, [])
        wm_pred = round(sum(wm_pred_list) / len(wm_pred_list), 3) if wm_pred_list else None
        
        wm_surge = round(wm_ver - wm_pred, 3) if (wm_ver is not None and wm_pred is not None) else None

        # Sewells Point (8638610) & Bay Hydraulic Slope
        sw_ver_list = sw_water_grouped.get(curr, [])
        sw_ver = round(sum(sw_ver_list) / len(sw_ver_list), 3) if sw_ver_list else None

        sw_pred_list = sw_preds_grouped.get(curr, [])
        sw_pred = round(sum(sw_pred_list) / len(sw_pred_list), 3) if sw_pred_list else None

        sw_surge = round(sw_ver - sw_pred, 3) if (sw_ver is not None and sw_pred is not None) else None
        bay_grad = round(wm_surge - sw_surge, 3) if (wm_surge is not None and sw_surge is not None) else None
        bay_slope = round(bay_grad / 46.2, 5) if bay_grad is not None else None
        
        # Micro-topographical evaluation
        eval_res = micro_topography.evaluate_compound_inundation(ware_mean, rain_rolling_6h_in=0.0)
        tier_num, tier_lbl = compound_risk_tier(ware_mean, eval_res)
        
        row = {
            "timestamp_utc": curr.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "timestamp_local": dt_local.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "year": dt_local.year,
            "month": dt_local.month,
            "day": dt_local.day,
            "hour": dt_local.hour,
            "ware_river_stage_mllw_ft": ware_mean if ware_mean is not None else "",
            "ware_river_stage_max_ft": ware_max if ware_max is not None else "",
            "ware_river_stage_navd88_ft": ware_navd88 if ware_navd88 is not None else "",
            "yorktown_wind_speed_mph": w_spd if w_spd is not None else "",
            "yorktown_wind_dir_deg": w_dir if w_dir is not None else "",
            "yorktown_wind_gust_mph": w_gst if w_gst is not None else "",
            "yorktown_baro_mb": baro if baro is not None else "",
            "yorktown_air_temp_f": temp_f if temp_f is not None else "",
            "wind_u_mph": u_wind if u_wind is not None else "",
            "wind_v_mph": v_wind if v_wind is not None else "",
            "along_bay_wind_mph": along_bay_wind if along_bay_wind is not None else "",
            "cross_bay_wind_mph": cross_bay_wind if cross_bay_wind is not None else "",
            "yorktown_pred_tide_ft": yt_pred if yt_pred is not None else "",
            "windmill_pred_tide_ft": wm_pred if wm_pred is not None else "",
            "windmill_ver_water_ft": wm_ver if wm_ver is not None else "",
            "windmill_surge_ft": wm_surge if wm_surge is not None else "",
            "sewells_point_water_level_mllw_ft": sw_ver if sw_ver is not None else "",
            "sewells_point_pred_tide_ft": sw_pred if sw_pred is not None else "",
            "sewells_point_surge_ft": sw_surge if sw_surge is not None else "",
            "bay_hydraulic_gradient_ft": bay_grad if bay_grad is not None else "",
            "bay_hydraulic_slope_ft_per_mile": bay_slope if bay_slope is not None else "",
            "estimated_flood_depth_in": eval_res["total_compound_depth_in"],
            "is_flooded": ("" if eval_res["total_compound_depth_in"] is None else "TRUE" if eval_res["total_compound_depth_in"] > 0 else "FALSE"),
            "flood_risk_tier": tier_num,
            "flood_risk_label": tier_lbl,
            "community_streets": eval_res["streets"],
            "vehicle_passability_code": eval_res["vehicle_passability_code"],
            "vehicle_passability": eval_res["vehicle_passability_label"],
            "driveway_depth_in": eval_res["sectors"]["main_driveway"]["depth_in"]
        }
        hourly_rows.append(row)
        curr += timedelta(hours=1)
        
    return hourly_rows

def build_forecast_timeline(nwps_fcst, nws_fcst, yt_pred_fcst, wm_pred_fcst, qpf_map, sewells_pred_fcst=None, max_hours=48):
    """
    Build multi-model forward 48-hour timeline with:
    1. Hybrid Hydrodynamic–ML Residual Modeling with Bay Hydraulic Push
    2. Quantile Regression Uncertainty Envelope (10th, 50th, 90th percentiles)
    3. Compound Pluvial + Tidal Inundation
    4. Multi-Sector Micro-Topographical Elevation Depths
    """
    now_utc = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    end_utc = now_utc + timedelta(hours=max_hours)
    
    nwps_map = {r["datetime_utc"].replace(minute=0, second=0, microsecond=0): r["forecast_stage_mllw_ft"] for r in nwps_fcst}
    nws_map = {r["datetime_utc"].replace(minute=0, second=0, microsecond=0): r for r in nws_fcst}
    yt_pred_map = {r["datetime_utc"].replace(minute=0, second=0, microsecond=0): r["water_level_ft"] for r in (yt_pred_fcst or []) if r.get("water_level_ft") is not None}
    wm_pred_map = {r["datetime_utc"].replace(minute=0, second=0, microsecond=0): r["water_level_ft"] for r in (wm_pred_fcst or []) if r.get("water_level_ft") is not None}
    sw_pred_map = {r["datetime_utc"].replace(minute=0, second=0, microsecond=0): r["water_level_ft"] for r in (sewells_pred_fcst or []) if r.get("water_level_ft") is not None}
    
    timeline = []
    curr = now_utc
    hourly_rain_history = [qpf_map.get(now_utc - timedelta(hours=h), 0.0) for h in range(5, 0, -1)]
    
    while curr <= end_utc:
        dt_local = curr.astimezone(EASTERN_TZ)
        nwps_stage = nwps_map.get(curr)
        nws_item = nws_map.get(curr, {})
        yt_pred = yt_pred_map.get(curr)
        wm_pred = wm_pred_map.get(curr)
        sw_pred = sw_pred_map.get(curr)
        
        lead_hours = max(0.0, (curr - now_utc).total_seconds() / 3600.0)
        
        wind_spd = nws_item.get("wind_speed_mph")
        wind_dir = nws_item.get("wind_dir_deg")
        # NWS legitimately omits direction for explicit 0 mph forecasts.
        # Calm wind has a known zero vector, without inventing a bearing.
        calm_wind = finite_number(wind_spd) and wind_spd == 0
        weather_available = (bool(nws_item) and finite_number(wind_spd) and wind_spd >= 0
                             and (calm_wind or finite_number(wind_dir)))
        along_bay = None
        cross_bay = None
        along_stress = 0.0
        if calm_wind:
            along_bay = cross_bay = 0.0
        elif weather_available:
            bay_rad = math.radians(wind_dir - 20)
            along_bay = round(wind_spd * math.cos(bay_rad), 2)
            cross_bay = round(wind_spd * math.sin(bay_rad), 2)
            along_stress = math.copysign(along_bay ** 2, along_bay)
            
        # Rainfall tracking (QPF in inches)
        rain_in = qpf_map.get(curr, 0.0)
        hourly_rain_history.append(rain_in)
        # 6-hour rolling accumulation
        rolling_rain_6h = round(sum(hourly_rain_history[-6:]), 2)

        # Multi-Station Hydraulic Slope Estimation:
        # Northerly winds stack water in northern bay, creating downward hydraulic pressure head into Mobjack Bay
        along_bay_val = along_bay or 0.0
        forward_bay_gradient = round((0.015 * along_bay_val) + (0.0004 * along_stress), 3) if along_bay is not None else 0.0
        if wm_pred is not None and sw_pred is not None:
            forward_hydraulic_gradient = round(forward_bay_gradient + 0.08 * (wm_pred - sw_pred), 2)
        else:
            forward_hydraulic_gradient = round(forward_bay_gradient, 2)
            
        hydraulic_push = round(max(0.0, forward_hydraulic_gradient) * 0.12, 3)

        # Hybrid Hydrodynamic–ML Residual Modeling
        if nwps_stage is not None:
            local_wind_adj = round((0.012 * (along_bay or 0.0)) + (0.0006 * along_stress), 3)
            hybrid_stage = round(max(0.5, nwps_stage + local_wind_adj + hydraulic_push), 2)
        elif yt_pred is not None:
            # Fallback to statistical ML forecast model
            hybrid_stage = round(0.735 * yt_pred + 0.02 * (along_bay or 0.0) + 1.1 + hydraulic_push, 2)
        else:
            hybrid_stage = None

        # Heuristic scenario envelope (legacy Q10/Q90 field names retained for compatibility)
        # Lead time growth factor: meteorological uncertainty widens over 48 hours
        lead_growth = 0.08 * math.sqrt(lead_hours / 24.0)
        wind_expansion = 0.02 * max(0.0, ((wind_spd or 0.0) - 15.0) / 10.0)
        
        q10_offset = -0.18 - lead_growth - wind_expansion
        q90_offset = 0.22 + lead_growth + wind_expansion

        if hybrid_stage is not None:
            stage_q10 = round(max(0.2, hybrid_stage + q10_offset), 2)
            stage_q90 = round(hybrid_stage + q90_offset, 2)
        else:
            stage_q10 = None
            stage_q90 = None

        # Compound Inundation & Micro-Topography
        eval_res = micro_topography.evaluate_compound_inundation(hybrid_stage, rolling_rain_6h)
        tier_num, tier_lbl = compound_risk_tier(hybrid_stage, eval_res)

        # Scenario bounds use the same rainfall contribution as the central estimate.
        depth_q10 = micro_topography.evaluate_compound_inundation(stage_q10, rolling_rain_6h)["total_compound_depth_in"]
        depth_q90 = micro_topography.evaluate_compound_inundation(stage_q90, rolling_rain_6h)["total_compound_depth_in"]
        
        timeline.append({
            "weather_available": weather_available,
            "precipitation_available": curr in qpf_map,
            "forecast_source": "nwps" if nwps_stage is not None else "tide_fallback" if yt_pred is not None else "unavailable",
            "timestamp_utc": curr.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "timestamp_local": dt_local.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "forecast_stage_q10_ft": stage_q10 if stage_q10 is not None else "",
            "forecast_stage_mllw_ft": hybrid_stage if hybrid_stage is not None else "",
            "forecast_stage_q90_ft": stage_q90 if stage_q90 is not None else "",
            "nwps_raw_stage_ft": nwps_stage if nwps_stage is not None else "",
            "compound_flood_depth_q10_in": depth_q10,
            "compound_flood_depth_in": eval_res["total_compound_depth_in"],
            "compound_flood_depth_q90_in": depth_q90,
            "tidal_depth_in": eval_res["tidal_depth_in"],
            "pluvial_trapped_depth_in": eval_res["pluvial_trapped_depth_in"],
            "rain_forecast_hourly_in": rain_in,
            "rain_rolling_6h_in": rolling_rain_6h,
            "bay_hydraulic_gradient_ft": forward_hydraulic_gradient,
            "risk_tier": tier_num,
            "risk_label": tier_lbl,
            "community_streets": eval_res["streets"],
            "vehicle_passability_code": eval_res["vehicle_passability_code"],
            "vehicle_passability": eval_res["vehicle_passability_label"],
            "vehicle_passability_desc": eval_res["vehicle_passability_desc"],
            "sector_ditches_depth_in": eval_res["sectors"]["ditches"]["depth_in"],
            "sector_road_depth_in": eval_res["sectors"]["road_apron"]["depth_in"],
            "sector_driveway_depth_in": eval_res["sectors"]["main_driveway"]["depth_in"],
            "sector_yard_depth_in": eval_res["sectors"]["yard_lawn"]["depth_in"],
            "sector_garage_depth_in": eval_res["sectors"]["garage_foundation"]["depth_in"],
            "nws_wind_speed_mph": wind_spd if wind_spd is not None else "",
            "nws_wind_dir_deg": wind_dir if wind_dir is not None else "",
            "nws_wind_cardinal": "Calm" if calm_wind else nws_item.get("wind_dir_cardinal", ""),
            "along_bay_wind_mph": along_bay if along_bay is not None else "",
            "cross_bay_wind_mph": cross_bay if cross_bay is not None else "",
            "nws_short_forecast": nws_item.get("short_forecast", ""),
            "nws_temp_f": nws_item.get("temp_f", ""),
            "nws_pop_pct": nws_item.get("pop_percent", 0),
            "yorktown_pred_tide_ft": yt_pred if yt_pred is not None else "",
            "windmill_pred_tide_ft": wm_pred if wm_pred is not None else "",
            "sewells_pred_tide_ft": sw_pred if sw_pred is not None else ""
        })
        curr += timedelta(hours=1)
        
    return timeline

def stage_trend_ft_per_hr(ware_obs, now_utc, window_hours=3):
    """Robust water-level rise rate over the trailing window.

    Compares the mean of the second half of the window against the first half,
    which is stabler than endpoints on noisy 6-minute gauge data. Returns None
    when there are too few readings to trust.
    """
    if not ware_obs:
        return None
    cutoff = now_utc - timedelta(hours=window_hours)
    pts = [(r["datetime_utc"], r["stage_mllw_ft"]) for r in ware_obs
           if isinstance(r.get("datetime_utc"), datetime) and finite_number(r.get("stage_mllw_ft"))
           and r["datetime_utc"] >= cutoff]
    if len(pts) < 4:
        return None
    pts.sort()
    mid = cutoff + timedelta(hours=window_hours / 2)
    early = [s for t, s in pts if t <= mid]
    late = [s for t, s in pts if t > mid]
    if not early or not late:
        return None
    return round((sum(late) / len(late) - sum(early) / len(early)) / (window_hours / 2), 3)


def generate_latest_status(
    ware_obs=None,
    yt_winds=None,
    yt_press=None,
    yt_temps=None,
    yt_water=None,
    yt_preds=None,
    wm_water=None,
    wm_preds=None,
    sw_water=None,
    sw_preds=None,
    nwps_fcst=None,
    fcst_timeline=None,
):
    """Construct structured JSON payload describing current status, micro-topography, bay hydraulic slope, and uncertainty outlook."""
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(EASTERN_TZ)
    
    latest_ware = ware_obs[-1] if ware_obs else None
    current_stage = latest_ware.get("stage_mllw_ft") if latest_ware else None
    current_stage_time = (
        latest_ware["datetime_utc"].astimezone(EASTERN_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")
        if (latest_ware and "datetime_utc" in latest_ware)
        else None
    )
    
    latest_wind = yt_winds[-1] if yt_winds else None
    latest_press = yt_press[-1] if yt_press else None
    latest_temp = yt_temps[-1] if yt_temps else None
    latest_yt_water = yt_water[-1] if yt_water else None
    latest_yt_pred = yt_preds[-1] if yt_preds else None
    
    latest_wm_water = wm_water[-1] if wm_water else None
    latest_wm_pred = wm_preds[-1] if wm_preds else None
    wm_surge = matched_surge(wm_water, wm_preds)
    latest_sw_water = sw_water[-1] if sw_water else None
    latest_sw_pred = sw_preds[-1] if sw_preds else None
    sw_surge = matched_surge(sw_water, sw_preds)

    bay_gradient = round(wm_surge - sw_surge, 2) if (wm_surge is not None and sw_surge is not None) else None
    bay_slope = round(bay_gradient / 46.2, 5) if bay_gradient is not None else None
    if bay_gradient is not None:
        if bay_gradient >= 0.20:
            bay_pressure_direction = "Southward Inflow Head (North Bay surge forcing water into Mobjack Bay)"
        elif bay_gradient <= -0.20:
            bay_pressure_direction = "Northward / Outflow Gradient"
        else:
            bay_pressure_direction = "Equilibrium (Near-zero gradient across bay)"
    else:
        bay_pressure_direction = "N/A"
        
    yt_surge = matched_surge(yt_water, yt_preds)

    data_quality_flags = []
    if (yt_surge is not None and wm_surge is not None
            and abs(yt_surge - wm_surge) > 0.75):
        # Nearby gauges disagreeing on surge is a data-quality signal, not a
        # forecast input: flag it for the bulletin instead of silently trusting one.
        data_quality_flags.append(
            f"Yorktown and Windmill Point surge residuals disagree by "
            f"{abs(yt_surge - wm_surge):.2f} ft; treat water-level readings cautiously.")

    w_spd = latest_wind.get("wind_speed_mph") if latest_wind else None
    w_dir = latest_wind.get("wind_dir_deg") if latest_wind else None
    along_bay = None
    cross_bay = None
    if w_spd is not None and w_dir is not None:
        bay_rad = math.radians(w_dir - 20)
        along_bay = round(w_spd * math.cos(bay_rad), 2)
        cross_bay = round(w_spd * math.sin(bay_rad), 2)
        
    current_eval = micro_topography.evaluate_compound_inundation(current_stage, rain_rolling_6h_in=0.0)
    current_tier, current_tier_label = compound_risk_tier(current_stage, current_eval)
    if not is_recent(current_stage_time, now_utc):
        current_tier, current_tier_label = UNKNOWN_TIER, "Unknown (gauge missing or stale)"
        current_eval = micro_topography.evaluate_compound_inundation(None)
    
    # 48h outlook analysis
    fcst_timeline = fcst_timeline or []
    stages_fcst = [r["forecast_stage_mllw_ft"] for r in fcst_timeline if isinstance(r.get("forecast_stage_mllw_ft"), (int, float))]
    peak_stage = max(stages_fcst) if stages_fcst else None
    peak_stage_time = None
    peak_timeline_item = None
    if peak_stage is not None:
        for r in fcst_timeline:
            if r.get("forecast_stage_mllw_ft") == peak_stage:
                peak_stage_time = r["timestamp_local"]
                peak_timeline_item = r
                break
                
    valid_rows = [r for r in fcst_timeline if finite_number(r.get("compound_flood_depth_in"))]
    depth_item = max(valid_rows, key=lambda r: r["compound_flood_depth_in"], default=None)
    hazard_item = max(valid_rows, key=lambda r: (r.get("risk_tier", -1),
                      max((v for k, v in r.items() if k.startswith("sector_") and k.endswith("depth_in") and finite_number(v)), default=0)), default=None)
    peak_compound_depth = depth_item["compound_flood_depth_in"] if depth_item else None
    peak_tier = hazard_item["risk_tier"] if hazard_item else UNKNOWN_TIER
    peak_tier_label = hazard_item["risk_label"] if hazard_item else "Unknown"
    hours_above_action = sum(1 for s in stages_fcst if s >= 4.0)

    stages_q10 = [r["forecast_stage_q10_ft"] for r in fcst_timeline if isinstance(r.get("forecast_stage_q10_ft"), (int, float))]
    stages_q90 = [r["forecast_stage_q90_ft"] for r in fcst_timeline if isinstance(r.get("forecast_stage_q90_ft"), (int, float))]
    peak_stage_q10 = max(stages_q10) if stages_q10 else None
    peak_stage_q90 = max(stages_q90) if stages_q90 else None
    peak_depth_q10 = max((r["compound_flood_depth_q10_in"] for r in fcst_timeline if finite_number(r.get("compound_flood_depth_q10_in"))), default=None)
    peak_depth_q90 = max((r["compound_flood_depth_q90_in"] for r in fcst_timeline if finite_number(r.get("compound_flood_depth_q90_in"))), default=None)
    
    status = {
        "status_generated_at_local": now_local.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "status_generated_at_utc": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "source_health": SOURCE_HEALTH.copy(),
        "alerting_enabled": os.getenv("NTFY_ALERTS_ENABLED", "false").lower() == "true",
        "forecast_method": "NWPS guidance with heuristic local adjustments; scenario bounds are not calibrated confidence intervals",
        "system_location": "Mathews County, Virginia (Ware River / Mobjack Bay Basin)",
        "data_quality_flags": data_quality_flags,
        "current_conditions": {
            "observation_timestamp_local": current_stage_time,
            "ware_river_stage_mllw_ft": current_stage,
            "ware_river_stage_navd88_ft": round(current_stage + DATUM_OFFSET_NAVD88_MLLW, 2) if current_stage is not None else None,
            "stage_trend_3h_ft_per_hr": stage_trend_ft_per_hr(ware_obs, now_utc),
            "action_stage_threshold_ft": 4.00,
            "flood_inundation_threshold_ft": FLOOD_STAGE_THRESHOLD,
            "estimated_local_flood_depth_in": current_eval["total_compound_depth_in"],
            "tidal_depth_in": current_eval["tidal_depth_in"],
            "pluvial_trapped_depth_in": current_eval["pluvial_trapped_depth_in"],
            "flood_risk_tier": current_tier,
            "flood_risk_label": current_tier_label,
            "vehicle_passability_code": current_eval["vehicle_passability_code"],
            "vehicle_passability": current_eval["vehicle_passability_label"],
            "vehicle_passability_desc": current_eval["vehicle_passability_desc"],
            "community_name": current_eval.get("community_name", "Mobjack Bay Estates & Blackwater Community"),
            "site_sectors": current_eval["sectors"],
            "community_streets": current_eval.get("streets", {}),
            "yorktown_wind_speed_mph": w_spd,
            "yorktown_wind_dir_deg": w_dir,
            "yorktown_wind_dir_cardinal": degrees_to_compass(w_dir) if w_dir is not None else "N/A",
            "yorktown_wind_gust_mph": latest_wind.get("wind_gust_mph") if latest_wind else None,
            "along_bay_wind_vector_mph": along_bay,
            "cross_bay_wind_vector_mph": cross_bay,
            "yorktown_baro_pressure_mb": latest_press.get("baro_mb") if latest_press else None,
            "yorktown_air_temp_f": latest_temp.get("air_temp_f") if latest_temp else None,
            "yorktown_water_level_mllw_ft": latest_yt_water.get("water_level_ft") if latest_yt_water else None,
            "yorktown_storm_surge_residual_ft": yt_surge,
            "windmill_point_water_level_mllw_ft": latest_wm_water.get("water_level_ft") if latest_wm_water else None,
            "windmill_point_storm_surge_residual_ft": wm_surge,
            "sewells_point_water_level_mllw_ft": latest_sw_water.get("water_level_ft") if latest_sw_water else None,
            "sewells_point_pred_tide_ft": latest_sw_pred.get("water_level_ft") if latest_sw_pred else None,
            "sewells_point_storm_surge_residual_ft": sw_surge,
            "bay_hydraulic_gradient_ft": bay_gradient,
            "bay_hydraulic_slope_ft_per_mile": bay_slope,
            "bay_hydraulic_pressure_direction": bay_pressure_direction
        },
        "forecast_48h_outlook": {
            "peak_forecast_stage_q10_ft": peak_stage_q10,
            "peak_forecast_stage_mllw_ft": peak_stage,
            "peak_forecast_stage_q90_ft": peak_stage_q90,
            "peak_forecast_stage_time_local": peak_stage_time,
            "peak_estimated_flood_depth_q10_in": peak_depth_q10,
            "peak_estimated_flood_depth_in": peak_compound_depth,
            "peak_estimated_flood_depth_q90_in": peak_depth_q90,
            "peak_risk_tier": peak_tier,
            "peak_risk_label": peak_tier_label,
            "peak_depth_time_local": depth_item["timestamp_local"] if depth_item else None,
            "peak_hazard_time_local": hazard_item["timestamp_local"] if hazard_item else None,
            "peak_vehicle_passability_code": hazard_item.get("vehicle_passability_code", "UNKNOWN") if hazard_item else "UNKNOWN",
            "peak_vehicle_passability": hazard_item["vehicle_passability"] if hazard_item else "UNKNOWN — DATA UNAVAILABLE",
            "hours_at_or_above_action_stage": hours_above_action,
            "scenario_range_summary": (
                f"Expected peak {peak_stage:.2f} ft (uncalibrated scenario range: {peak_stage_q10:.2f} ft [lower scenario] to {peak_stage_q90:.2f} ft [upper scenario]; depth {peak_depth_q10:.1f}\" to {peak_depth_q90:.1f}\")"
                if peak_stage is not None and peak_stage_q10 is not None else "N/A"
            ),
            "bay_hydraulic_slope_summary": (
                f"Current Bay Gradient: {bay_gradient:+.2f} ft ({bay_pressure_direction})"
                if bay_gradient is not None else "N/A"
            ),
            "advisory_summary": (
                "NO FLOODING EXPECTED: Water levels will remain inside normal tidal ditches and marsh channels."
                if peak_tier == 0 else
                f"FLOODING ADVISORY: Potential {peak_tier_label} with up to {peak_compound_depth} inches of water expected around {peak_stage_time}."
            )
        },
        "forecast_hourly_timeline": fcst_timeline
    }
    for url, health in status["source_health"].items():
        health["required"] = ("forecast/hourly" in url or url.endswith("/80,76")
                              or ("stageflow/forecast" in url and any(r.get("forecast_source") == "nwps" for r in fcst_timeline)))
    status["data_quality"] = assess_status(status, now_utc)
    if not status["data_quality"]["forecast_available"]:
        status["forecast_48h_outlook"]["advisory_summary"] = "Forecast incomplete or stale. Flooding cannot be ruled out; consult official forecasts and actual conditions."
    return status

def update_archive_observations(archive_path, hourly_obs):
    """
    Appends new completed hourly observations to a permanent cumulative archive CSV.
    Deduplicates by timestamp_utc so reruns never duplicate data.
    Dynamically expands header fields if new sensor products are added over time.
    """
    now_utc = datetime.now(timezone.utc)
    current_hour_utc = now_utc.replace(minute=0, second=0, microsecond=0)
    
    existing_timestamps = set()
    updated = 0
    rows_by_timestamp = {}
    existing_rows = []
    headers = []
    
    if os.path.exists(archive_path):
        with open(archive_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames:
                headers = list(reader.fieldnames)
            for row in reader:
                existing_timestamps.add(row.get("timestamp_utc", ""))
                existing_rows.append(row)
                rows_by_timestamp[row.get("timestamp_utc", "")] = row
                
    # Dynamically expand headers to include any newly introduced columns from hourly_obs
    for obs in (hourly_obs or []):
        for k in obs.keys():
            if k not in headers:
                headers.append(k)
        
    added = 0
    for obs in (hourly_obs or []):
        ts_str = obs.get("timestamp_utc", "")
        if not ts_str:
            continue
        try:
            ts_dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=timezone.utc)
            # Only archive completed past hours so readings are final
            if ts_dt >= current_hour_utc:
                continue
        except Exception:
            pass
            
        if ts_str in existing_timestamps:
            previous = rows_by_timestamp.get(ts_str, {})
            # Repair previously missing fields; never replace a good measurement with missing data.
            for key, value in obs.items():
                if value not in (None, "") and previous.get(key) in (None, ""):
                    previous[key] = value
                    updated += 1
        else:
            existing_rows.append(obs)
            rows_by_timestamp[ts_str] = obs
            existing_timestamps.add(ts_str)
            added += 1
            
    if (added > 0 or updated > 0 or not os.path.exists(archive_path)) and headers:
        existing_rows.sort(key=lambda r: r.get("timestamp_utc", ""))
        # Atomic replace: a crash mid-write can never leave a truncated archive.
        atomic_write_csv(archive_path, existing_rows, headers)

    return added, len(existing_rows)

def write_csv(filepath, rows, fieldnames):
    """Write list of dictionaries to CSV atomically."""
    atomic_write_csv(filepath, rows, fieldnames)

def preserve_last_forecast(status, path):
    """Keep original forecast dates on total outages; never use fallback for alerts."""
    if any(finite_number(r.get('forecast_stage_mllw_ft')) for r in status.get('forecast_hourly_timeline', [])):
        return
    try:
        with open(path, encoding='utf-8') as stream:
            previous = json.load(stream)
    except (OSError, ValueError):
        return
    if any(finite_number(r.get('forecast_stage_mllw_ft')) for r in previous.get('forecast_hourly_timeline', [])):
        status['last_available_forecast'] = {
            'saved_at_utc': previous.get('status_generated_at_utc'),
            'forecast_issued_at_utc': previous.get('forecast_issued_at_utc'),
            'forecast_hourly_timeline': previous['forecast_hourly_timeline'],
            'forecast_48h_outlook': previous.get('forecast_48h_outlook', {}),
        }
    elif previous.get('last_available_forecast'):
        status['last_available_forecast'] = previous['last_available_forecast']


def main():
    parser = argparse.ArgumentParser(description="Fetch real-time hydrological & meteorological data for Mathews County flood prediction.")
    parser.add_argument("--hours", type=int, default=48, help="Number of past observation hours to aggregate (default: 48)")
    parser.add_argument("--json-out", type=str, default="latest_status.json", help="Path to write latest status JSON")
    parser.add_argument("--obs-csv-out", type=str, default="realtime_recent_observations.csv", help="Path to write hourly recent observations CSV")
    parser.add_argument("--archive-csv-out", type=str, default="archive_hourly_observations.csv", help="Path to cumulative continuous archive CSV")
    parser.add_argument("--fcst-csv-out", type=str, default="forecast_48h.csv", help="Path to write 48h forecast CSV")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose stdout output")
    args = parser.parse_args()

    def log(msg):
        if not args.quiet:
            print(msg)

    log("=" * 72)
    log("MATHEWS COUNTY, VA — ADVANCED REAL-TIME FLOOD INGESTION PIPELINE")
    log("=" * 72)

    now_utc = datetime.now(timezone.utc)
    begin_dt_utc = now_utc - timedelta(hours=args.hours + 2)
    end_dt_utc = now_utc
    forward_end_utc = now_utc + timedelta(days=3)

    log(f"[*] Querying real-time sensor networks (concurrent) for window: {begin_dt_utc.strftime('%Y-%m-%d %H:%M')} to {end_dt_utc.strftime('%Y-%m-%d %H:%M')} UTC")

    tasks = {
        'ware_obs': lambda: fetch_nwps_wrvv2_observed(),
        'ware_fcst': lambda: fetch_nwps_wrvv2_forecast(),
        'yt_winds': lambda: fetch_coops_product("8637689", "wind", begin_dt_utc, end_dt_utc),
        'yt_press': lambda: fetch_coops_product("8637689", "air_pressure", begin_dt_utc, end_dt_utc),
        'yt_temps': lambda: fetch_coops_product("8637689", "air_temperature", begin_dt_utc, end_dt_utc),
        'yt_water': lambda: fetch_coops_product("8637689", "water_level", begin_dt_utc, end_dt_utc),
        'yt_preds_past': lambda: fetch_coops_product("8637689", "predictions", begin_dt_utc, end_dt_utc),
        'yt_preds_future': lambda: fetch_coops_product("8637689", "predictions", now_utc, forward_end_utc),
        'wm_water': lambda: fetch_coops_product("8636580", "water_level", begin_dt_utc, end_dt_utc),
        'wm_preds_past': lambda: fetch_coops_product("8636580", "predictions", begin_dt_utc, end_dt_utc),
        'wm_preds_future': lambda: fetch_coops_product("8636580", "predictions", now_utc, forward_end_utc),
        'sw_water': lambda: fetch_coops_product("8638610", "water_level", begin_dt_utc, end_dt_utc),
        'sw_preds_past': lambda: fetch_coops_product("8638610", "predictions", begin_dt_utc, end_dt_utc),
        'sw_preds_future': lambda: fetch_coops_product("8638610", "predictions", now_utc, forward_end_utc),
        'fort_obs': lambda: fetch_fort_monroe_observed(),
        'nws_fcst': lambda: fetch_nws_hourly_forecast(),
        'qpf_map': lambda: fetch_nws_qpf_map(),
    }

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        future_to_key = {executor.submit(func): key for key, func in tasks.items()}
        for future in concurrent.futures.as_completed(future_to_key):
            key = future_to_key[future]
            try:
                results[key] = future.result()
            except Exception as ex:
                log(f"[WARN] Error fetching {key}: {ex}")
                results[key] = [] if key != 'qpf_map' else {}

    ware_obs = results.get('ware_obs', [])
    ware_fcst = results.get('ware_fcst', [])
    yt_winds = results.get('yt_winds', [])
    yt_press = results.get('yt_press', [])
    yt_temps = results.get('yt_temps', [])
    yt_water = results.get('yt_water', [])
    yt_preds_past = results.get('yt_preds_past', [])
    yt_preds_future = results.get('yt_preds_future', [])
    wm_water = results.get('wm_water', [])
    wm_preds_past = results.get('wm_preds_past', [])
    wm_preds_future = results.get('wm_preds_future', [])
    sw_water = results.get('sw_water', [])
    sw_preds_past = results.get('sw_preds_past', [])
    sw_preds_future = results.get('sw_preds_future', [])
    fort_obs = results.get('fort_obs', [])
    nws_fcst = results.get('nws_fcst', [])
    qpf_map = results.get('qpf_map', {})

    log(f"      -> Ware River obs: {len(ware_obs)}, fcst: {len(ware_fcst)}")
    log(f"      -> Yorktown winds: {len(yt_winds)}, baro: {len(yt_press)}, water: {len(yt_water)}, fwd tides: {len(yt_preds_future)}")
    log(f"      -> Windmill Pt water: {len(wm_water)}, verified: {len(wm_preds_past)}, fwd tides: {len(wm_preds_future)}")
    log(f"      -> Sewells Pt water: {len(sw_water)}, verified: {len(sw_preds_past)}, fwd tides: {len(sw_preds_future)}")
    log(f"      -> Fort Monroe sensor: {len(fort_obs)} observations")
    log(f"      -> NWS AKQ forecast: {len(nws_fcst)} intervals, QPF: {len(qpf_map)} intervals")

    # Data processing & alignment
    log("\n[*] Resampling & aligning recent observations on hourly timestamps...")
    hourly_obs = aggregate_hourly_observations(
        ware_obs, yt_winds, yt_press, yt_temps, yt_water, yt_preds_past,
        wm_water, wm_preds_past, sw_water, sw_preds_past, lookback_hours=args.hours
    )
    add_fort_hourly(hourly_obs, fort_obs)
    log(f"    -> Aligned {len(hourly_obs)} hourly observation rows.")

    log("[*] Building forward 48-hour Hybrid Hydrodynamic–ML forecast timeline...")
    fcst_timeline = build_forecast_timeline(
        ware_fcst, nws_fcst, yt_preds_future, wm_preds_future, qpf_map,
        sewells_pred_fcst=sw_preds_future, max_hours=48
    )
    log(f"    -> Built {len(fcst_timeline)} hourly forecast periods.")

    # Status summary
    status_summary = generate_latest_status(
        ware_obs=ware_obs,
        yt_winds=yt_winds,
        yt_press=yt_press,
        yt_temps=yt_temps,
        yt_water=yt_water,
        yt_preds=yt_preds_past,
        wm_water=wm_water,
        wm_preds=wm_preds_past,
        sw_water=sw_water,
        sw_preds=sw_preds_past,
        nwps_fcst=ware_fcst,
        fcst_timeline=fcst_timeline,
    )

    status_summary["official_nws_alerts"] = fetch_official_alerts()
    status_summary["source_health"] = SOURCE_HEALTH.copy()
    latest_fort = fort_obs[-1] if fort_obs else {}
    ft = latest_fort.get("datetime_utc")
    status_summary["forecast_issued_at_utc"] = FORECAST_ISSUED_AT
    status_summary["fort_monroe"] = {
        "station": "FTMV2 / USGS 0204289994", "role": "evaluation_only",
        "observation_time_utc": ft.isoformat() if ft else None,
        "received_at_utc": latest_fort.get("received_at_utc"),
        "elevation_navd88_ft": latest_fort.get("elevation_navd88_ft"),
        "water_level_mllw_ft": latest_fort.get("water_level_mllw_ft"),
        "datum_offset_ft": -1.70, "fresh": is_recent(ft.isoformat()) if ft else False,
        "model_promoted": False,
    }
    try:
        status_summary["live_verification"] = archive_and_verify(status_summary, ware_obs)
    except Exception as ex:
        # Verification is advisory: it must never abort ingest, dashboard, or alerts.
        log(f"[WARN] Forecast verification failed ({ex}); continuing without updated scores.")
        status_summary["live_verification"] = {"error": str(ex)[:200], "degraded": True}

    # Write files
    log(f"\n[*] Writing outputs:")
    
    preserve_last_forecast(status_summary, args.json_out)
    atomic_write_json(args.json_out, status_summary)
    log(f"    -> Status JSON: {args.json_out}")

    if hourly_obs:
        write_csv(args.obs_csv_out, hourly_obs, list(hourly_obs[0].keys()))
        log(f"    -> Recent Observations CSV: {args.obs_csv_out} ({len(hourly_obs)} rows)")
        
        if args.archive_csv_out:
            added_cnt, total_archived = update_archive_observations(args.archive_csv_out, hourly_obs)
            log(f"    -> Cumulative Archive CSV  : {args.archive_csv_out} (+{added_cnt} new hours, total: {total_archived} rows)")

    if fcst_timeline:
        write_csv(args.fcst_csv_out, fcst_timeline, list(fcst_timeline[0].keys()))
        log(f"    -> Forecast CSV: {args.fcst_csv_out} ({len(fcst_timeline)} rows)")

    # Terminal summary display
    curr = status_summary["current_conditions"]
    outl = status_summary["forecast_48h_outlook"]
    log("\n" + "=" * 72)
    log(f"CURRENT STATUS ({curr['observation_timestamp_local']}):")
    log(f"  Ware River Stage : {curr['ware_river_stage_mllw_ft']} ft MLLW ({curr['ware_river_stage_navd88_ft']} ft NAVD88)")
    log(f"  Ground Inundation: {curr['estimated_local_flood_depth_in']} inches ({curr['flood_risk_label']})")
    log(f"  Vehicle Access   : {curr['vehicle_passability']}")
    log(f"  Yorktown Wind    : {curr['yorktown_wind_speed_mph']} mph from {curr['yorktown_wind_dir_cardinal']} ({curr['yorktown_wind_dir_deg']}°)")
    log(f"  Wind Vectors     : Along-Bay={curr['along_bay_wind_vector_mph']} mph, Cross-Bay={curr['cross_bay_wind_vector_mph']} mph")
    wm_surge_val = curr.get("windmill_point_storm_surge_residual_ft")
    wm_surge_str = f"{wm_surge_val:+.2f}" if wm_surge_val is not None else "N/A"
    sw_surge_val = curr.get("sewells_point_storm_surge_residual_ft")
    sw_surge_str = f"{sw_surge_val:+.2f}" if sw_surge_val is not None else "N/A"
    log(f"  Baro Pressure    : {curr.get('yorktown_baro_pressure_mb', 'N/A')} mb | Windmill Surge: {wm_surge_str} ft | Sewells Surge: {sw_surge_str} ft")
    grad_val = curr.get("bay_hydraulic_gradient_ft")
    grad_str = f"{grad_val:+.2f}" if grad_val is not None else "N/A"
    slope_val = curr.get("bay_hydraulic_slope_ft_per_mile")
    slope_str = f"{slope_val}" if slope_val is not None else "N/A"
    log(f"  Bay Hydraulic Grad: {grad_str} ft ({slope_str} ft/mi) -> {curr.get('bay_hydraulic_pressure_direction', 'N/A')}")
    log("-" * 72)
    log("MICRO-TOPOGRAPHY SECTOR STATUS:")
    for k, v in curr["site_sectors"].items():
        depth_val = v.get("depth_in")
        depth_str = f"{depth_val:>4.1f}\"" if depth_val is not None else " N/A "
        log(f"  • {v['name']:<36}: {depth_str} [{v['status']}]")
    log("-" * 72)
    log("48-HOUR HAZARD OUTLOOK:")
    log(f"  Peak Hybrid Stage: {outl['peak_forecast_stage_mllw_ft']} ft at {outl['peak_forecast_stage_time_local']}")
    log(f"  Peak Flood Depth : {outl['peak_estimated_flood_depth_in']} inches ({outl['peak_risk_label']})")
    log(f"  Peak Passability : {outl['peak_vehicle_passability']}")
    log(f"  Hours >= 4.0 ft  : {outl['hours_at_or_above_action_stage']} hours")
    log(f"  Advisory         : {outl['advisory_summary']}")
    log("=" * 72)

if __name__ == "__main__":
    main()
