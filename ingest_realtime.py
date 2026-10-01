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
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import micro_topography

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
    if stage_mllw_ft is None:
        return 0, "Unknown"
    if stage_mllw_ft < 4.0:
        return 0, "Tier 0 (Normal / Safe)"
    elif stage_mllw_ft < 4.4:
        return 1, "Tier 1 (Nuisance / Ditch Full)"
    elif stage_mllw_ft < 4.8:
        return 2, "Tier 2 (Moderate Inundation)"
    else:
        return 3, "Tier 3 (Severe Inundation)"

def estimate_flood_depth_in(stage_mllw_ft):
    if stage_mllw_ft is None or stage_mllw_ft < FLOOD_STAGE_THRESHOLD:
        return 0.0
    depth = STAGE_TO_DEPTH_SLOPE * stage_mllw_ft + STAGE_TO_DEPTH_INTERCEPT
    return max(0.0, round(depth, 2))

def fetch_json(url, max_retries=3, backoff=2.0, timeout=15):
    """Fetch JSON with retry logic and descriptive user agent."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "MathewsCountyFloodStudy/1.0 (contact@mathewsflood.org)"}
    )
    for attempt in range(1, max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            if attempt == max_retries:
                print(f"[WARN] Failed fetching {url} after {max_retries} attempts: {e}", file=sys.stderr)
                return None
            time.sleep(backoff * attempt)
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
        dt_utc = datetime.fromisoformat(valid_time_str.replace("Z", "+00:00"))
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
    data = fetch_json(url)
    if not data or "data" not in data:
        return []
    records = []
    for item in data.get("data", []):
        valid_time_str = item.get("validTime")
        stage = item.get("primary")
        if not valid_time_str or stage is None or stage == -999:
            continue
        dt_utc = datetime.fromisoformat(valid_time_str.replace("Z", "+00:00"))
        records.append({
            "datetime_utc": dt_utc,
            "forecast_stage_mllw_ft": float(stage),
            "forecast_stage_navd88_ft": round(float(stage) + DATUM_OFFSET_NAVD88_MLLW, 2)
        })
    records.sort(key=lambda x: x["datetime_utc"])
    return records

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
        dt_utc = datetime.strptime(t_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        rec = {"datetime_utc": dt_utc}
        
        if product == "wind":
            try:
                rec["wind_speed_mph"] = round(float(item.get("s", 0)) * 1.15078, 2)
                rec["wind_dir_deg"] = round(float(item.get("d", 0)), 1)
                gust_str = item.get("g")
                rec["wind_gust_mph"] = round(float(gust_str) * 1.15078, 2) if gust_str else rec["wind_speed_mph"]
            except ValueError:
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
        dt = datetime.fromisoformat(start_str)
        dt_utc = dt.astimezone(timezone.utc)
        
        # Parse wind speed
        spd_str = p.get("windSpeed", "0 mph")
        digits = [float(x) for x in "".join([c if c.isdigit() or c == "." else " " for c in spd_str]).split()]
        wind_spd = sum(digits) / len(digits) if digits else 0.0
        
        wind_dir_cardinal = p.get("windDirection", "N")
        wind_dir_deg = COMPASS_DIRS.get(wind_dir_cardinal.upper(), 0.0)
        temp_f = p.get("temperature")
        pop = p.get("probabilityOfPrecipitation", {}).get("value", 0) or 0
        short_fcst = p.get("shortForecast", "")
        
        records.append({
            "datetime_utc": dt_utc,
            "wind_speed_mph": round(wind_spd, 1),
            "wind_dir_deg": wind_dir_deg,
            "wind_dir_cardinal": wind_dir_cardinal,
            "temp_f": temp_f,
            "pop_percent": pop,
            "short_forecast": short_fcst
        })
    records.sort(key=lambda x: x["datetime_utc"])
    return records

def fetch_nws_qpf_map():
    """Fetch quantitative precipitation forecast from NWS gridpoints and map to hourly rain inches."""
    url = "https://api.weather.gov/gridpoints/AKQ/80,76"
    data = fetch_json(url)
    if not data or "properties" not in data or "quantitativePrecipitation" not in data["properties"]:
        return {}
    qpf_values = data["properties"]["quantitativePrecipitation"].get("values", [])
    rain_by_hour = {}
    for item in qpf_values:
        vt = item.get("validTime", "")
        val_mm = item.get("value") or 0.0
        val_in = val_mm / 25.4
        if "/" in vt:
            start_str, dur_str = vt.split("/")
            try:
                start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                dur_hours = int("".join([c for c in dur_str if c.isdigit()]) or 1)
                hourly_rain = round(val_in / dur_hours, 3)
                for h in range(dur_hours):
                    hr_dt = (start_dt + timedelta(hours=h)).replace(minute=0, second=0, microsecond=0)
                    rain_by_hour[hr_dt] = hourly_rain
            except Exception:
                continue
    return rain_by_hour

def aggregate_hourly_observations(ware_obs, yt_winds, yt_press, yt_temps, yt_water, yt_preds, wm_water, wm_preds, lookback_hours=48):
    """Aggregate 6-min observations into hourly rows matching the training schema."""
    now_utc = datetime.now(timezone.utc)
    start_utc = (now_utc - timedelta(hours=lookback_hours)).replace(minute=0, second=0, microsecond=0)
    
    def group_by_hour(records, val_key):
        grouped = {}
        for r in records:
            hr_dt = r["datetime_utc"].replace(minute=0, second=0, microsecond=0)
            if hr_dt not in grouped:
                grouped[hr_dt] = []
            grouped[hr_dt].append(r[val_key])
        return grouped
    
    ware_grouped = group_by_hour(ware_obs, "stage_mllw_ft")
    
    yt_wind_grouped = {}
    for r in yt_winds:
        hr_dt = r["datetime_utc"].replace(minute=0, second=0, microsecond=0)
        if hr_dt not in yt_wind_grouped:
            yt_wind_grouped[hr_dt] = {"speeds": [], "dirs": [], "gusts": []}
        yt_wind_grouped[hr_dt]["speeds"].append(r["wind_speed_mph"])
        yt_wind_grouped[hr_dt]["dirs"].append(r["wind_dir_deg"])
        yt_wind_grouped[hr_dt]["gusts"].append(r["wind_gust_mph"])
        
    yt_press_grouped = group_by_hour(yt_press, "baro_mb")
    yt_temps_grouped = group_by_hour(yt_temps, "air_temp_f")
    yt_water_grouped = group_by_hour(yt_water, "water_level_ft")
    yt_preds_grouped = group_by_hour(yt_preds, "water_level_ft")
    wm_water_grouped = group_by_hour(wm_water, "water_level_ft")
    wm_preds_grouped = group_by_hour(wm_preds, "water_level_ft")
    
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
        w_dir = round(sum(w_info["dirs"]) / len(w_info["dirs"]), 1) if (w_info and w_info["dirs"]) else None
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
        
        # Micro-topographical evaluation
        eval_res = micro_topography.evaluate_compound_inundation(ware_mean, rain_rolling_6h_in=0.0)
        tier_num, tier_lbl = get_risk_tier(ware_mean)
        
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
            "estimated_flood_depth_in": eval_res["total_compound_depth_in"],
            "is_flooded": "TRUE" if eval_res["total_compound_depth_in"] > 0 else "FALSE",
            "flood_risk_tier": tier_num,
            "flood_risk_label": tier_lbl,
            "vehicle_passability": eval_res["vehicle_passability_label"],
            "driveway_depth_in": eval_res["sectors"]["main_driveway"]["depth_in"]
        }
        hourly_rows.append(row)
        curr += timedelta(hours=1)
        
    return hourly_rows

def build_forecast_timeline(nwps_fcst, nws_fcst, yt_pred_fcst, wm_pred_fcst, qpf_map, max_hours=48):
    """
    Build multi-model forward 48-hour timeline with:
    1. Hybrid Hydrodynamic–ML Residual Modeling
    2. Compound Pluvial + Tidal Inundation
    3. Multi-Sector Micro-Topographical Elevation Depths
    """
    now_utc = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    end_utc = now_utc + timedelta(hours=max_hours)
    
    nwps_map = {r["datetime_utc"].replace(minute=0, second=0, microsecond=0): r["forecast_stage_mllw_ft"] for r in nwps_fcst}
    nws_map = {r["datetime_utc"].replace(minute=0, second=0, microsecond=0): r for r in nws_fcst}
    yt_pred_map = {r["datetime_utc"].replace(minute=0, second=0, microsecond=0): r["water_level_ft"] for r in yt_pred_fcst}
    wm_pred_map = {r["datetime_utc"].replace(minute=0, second=0, microsecond=0): r["water_level_ft"] for r in wm_pred_fcst}
    
    timeline = []
    curr = now_utc
    hourly_rain_history = []
    
    while curr <= end_utc:
        dt_local = curr.astimezone(EASTERN_TZ)
        nwps_stage = nwps_map.get(curr)
        nws_item = nws_map.get(curr, {})
        yt_pred = yt_pred_map.get(curr)
        wm_pred = wm_pred_map.get(curr)
        
        wind_spd = nws_item.get("wind_speed_mph", 0.0)
        wind_dir = nws_item.get("wind_dir_deg", 0.0)
        along_bay = None
        cross_bay = None
        along_stress = 0.0
        if wind_spd is not None and wind_dir is not None:
            bay_rad = math.radians(wind_dir - 20)
            along_bay = round(wind_spd * math.cos(bay_rad), 2)
            cross_bay = round(wind_spd * math.sin(bay_rad), 2)
            along_stress = math.copysign(along_bay ** 2, along_bay)
            
        # Rainfall tracking (QPF in inches)
        rain_in = qpf_map.get(curr, 0.0)
        hourly_rain_history.append(rain_in)
        # 6-hour rolling accumulation
        rolling_rain_6h = round(sum(hourly_rain_history[-6:]), 2)

        # Recommendation 2: Hybrid Hydrodynamic–ML Residual Modeling
        # When NOAA NWPS hydrodynamic forecast is available, calculate local wind stress set-up adjustment:
        # Bias adjustment captures shallow-water stacking into Mobjack Bay that coarse ocean grid underpredicts
        if nwps_stage is not None:
            local_wind_adj = round((0.012 * (along_bay or 0.0)) + (0.0006 * along_stress), 3)
            hybrid_stage = round(max(0.5, nwps_stage + local_wind_adj), 2)
        elif yt_pred is not None:
            # Fallback to statistical ML forecast model
            hybrid_stage = round(0.735 * yt_pred + 0.02 * (along_bay or 0.0) + 1.1, 2)
        else:
            hybrid_stage = None

        # Recommendation 1 & 3: Compound Inundation & Micro-Topography
        eval_res = micro_topography.evaluate_compound_inundation(hybrid_stage, rolling_rain_6h)
        tier_num, tier_lbl = get_risk_tier(hybrid_stage)
        
        timeline.append({
            "timestamp_utc": curr.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "timestamp_local": dt_local.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "forecast_stage_mllw_ft": hybrid_stage if hybrid_stage is not None else "",
            "nwps_raw_stage_ft": nwps_stage if nwps_stage is not None else "",
            "compound_flood_depth_in": eval_res["total_compound_depth_in"],
            "tidal_depth_in": eval_res["tidal_depth_in"],
            "pluvial_trapped_depth_in": eval_res["pluvial_trapped_depth_in"],
            "rain_forecast_hourly_in": rain_in,
            "rain_rolling_6h_in": rolling_rain_6h,
            "risk_tier": tier_num,
            "risk_label": tier_lbl,
            "vehicle_passability": eval_res["vehicle_passability_label"],
            "vehicle_passability_desc": eval_res["vehicle_passability_desc"],
            "sector_ditches_depth_in": eval_res["sectors"]["ditches"]["depth_in"],
            "sector_road_depth_in": eval_res["sectors"]["road_apron"]["depth_in"],
            "sector_driveway_depth_in": eval_res["sectors"]["main_driveway"]["depth_in"],
            "sector_yard_depth_in": eval_res["sectors"]["yard_lawn"]["depth_in"],
            "sector_garage_depth_in": eval_res["sectors"]["garage_foundation"]["depth_in"],
            "nws_wind_speed_mph": wind_spd if wind_spd is not None else "",
            "nws_wind_dir_deg": wind_dir if wind_dir is not None else "",
            "nws_wind_cardinal": nws_item.get("wind_dir_cardinal", ""),
            "along_bay_wind_mph": along_bay if along_bay is not None else "",
            "cross_bay_wind_mph": cross_bay if cross_bay is not None else "",
            "nws_short_forecast": nws_item.get("short_forecast", ""),
            "nws_temp_f": nws_item.get("temp_f", ""),
            "nws_pop_pct": nws_item.get("pop_percent", 0),
            "yorktown_pred_tide_ft": yt_pred if yt_pred is not None else "",
            "windmill_pred_tide_ft": wm_pred if wm_pred is not None else ""
        })
        curr += timedelta(hours=1)
        
    return timeline

def generate_latest_status(ware_obs, yt_winds, yt_press, yt_temps, yt_water, yt_preds, wm_water, wm_preds, nwps_fcst, fcst_timeline):
    """Construct structured JSON payload describing current status, micro-topography, and upcoming hazards."""
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(EASTERN_TZ)
    
    latest_ware = ware_obs[-1] if ware_obs else None
    current_stage = latest_ware["stage_mllw_ft"] if latest_ware else None
    current_stage_time = latest_ware["datetime_utc"].astimezone(EASTERN_TZ).strftime("%Y-%m-%d %H:%M:%S %Z") if latest_ware else None
    
    latest_wind = yt_winds[-1] if yt_winds else None
    latest_press = yt_press[-1] if yt_press else None
    latest_temp = yt_temps[-1] if yt_temps else None
    latest_yt_water = yt_water[-1] if yt_water else None
    latest_yt_pred = yt_preds[-1] if yt_preds else None
    
    latest_wm_water = wm_water[-1] if wm_water else None
    latest_wm_pred = wm_preds[-1] if wm_preds else None
    wm_surge = None
    if latest_wm_water and latest_wm_pred:
        wm_surge = round(latest_wm_water["water_level_ft"] - latest_wm_pred["water_level_ft"], 2)
        
    yt_surge = None
    if latest_yt_water and latest_yt_pred:
        yt_surge = round(latest_yt_water["water_level_ft"] - latest_yt_pred["water_level_ft"], 2)
        
    w_spd = latest_wind["wind_speed_mph"] if latest_wind else None
    w_dir = latest_wind["wind_dir_deg"] if latest_wind else None
    along_bay = None
    cross_bay = None
    if w_spd is not None and w_dir is not None:
        bay_rad = math.radians(w_dir - 20)
        along_bay = round(w_spd * math.cos(bay_rad), 2)
        cross_bay = round(w_spd * math.sin(bay_rad), 2)
        
    current_eval = micro_topography.evaluate_compound_inundation(current_stage, rain_rolling_6h_in=0.0)
    current_tier, current_tier_label = get_risk_tier(current_stage)
    
    # 48h outlook analysis
    stages_fcst = [r["forecast_stage_mllw_ft"] for r in fcst_timeline if isinstance(r["forecast_stage_mllw_ft"], (int, float))]
    peak_stage = max(stages_fcst) if stages_fcst else None
    peak_stage_time = None
    peak_timeline_item = None
    if peak_stage is not None:
        for r in fcst_timeline:
            if r["forecast_stage_mllw_ft"] == peak_stage:
                peak_stage_time = r["timestamp_local"]
                peak_timeline_item = r
                break
                
    peak_compound_depth = peak_timeline_item["compound_flood_depth_in"] if peak_timeline_item else 0.0
    peak_tier, peak_tier_label = get_risk_tier(peak_stage) if peak_stage is not None else (0, "Unknown")
    hours_above_action = sum(1 for s in stages_fcst if s >= 4.0)
    
    status = {
        "status_generated_at_local": now_local.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "status_generated_at_utc": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "system_location": "Mathews County, Virginia (Ware River / Mobjack Bay Basin)",
        "current_conditions": {
            "observation_timestamp_local": current_stage_time,
            "ware_river_stage_mllw_ft": current_stage,
            "ware_river_stage_navd88_ft": round(current_stage + DATUM_OFFSET_NAVD88_MLLW, 2) if current_stage is not None else None,
            "action_stage_threshold_ft": 4.00,
            "flood_inundation_threshold_ft": FLOOD_STAGE_THRESHOLD,
            "estimated_local_flood_depth_in": current_eval["total_compound_depth_in"],
            "tidal_depth_in": current_eval["tidal_depth_in"],
            "pluvial_trapped_depth_in": current_eval["pluvial_trapped_depth_in"],
            "flood_risk_tier": current_tier,
            "flood_risk_label": current_tier_label,
            "vehicle_passability": current_eval["vehicle_passability_label"],
            "vehicle_passability_desc": current_eval["vehicle_passability_desc"],
            "site_sectors": current_eval["sectors"],
            "yorktown_wind_speed_mph": w_spd,
            "yorktown_wind_dir_deg": w_dir,
            "yorktown_wind_dir_cardinal": degrees_to_compass(w_dir),
            "yorktown_wind_gust_mph": latest_wind["wind_gust_mph"] if latest_wind else None,
            "along_bay_wind_vector_mph": along_bay,
            "cross_bay_wind_vector_mph": cross_bay,
            "yorktown_baro_pressure_mb": latest_press["baro_mb"] if latest_press else None,
            "yorktown_air_temp_f": latest_temp["air_temp_f"] if latest_temp else None,
            "yorktown_water_level_mllw_ft": latest_yt_water["water_level_ft"] if latest_yt_water else None,
            "yorktown_storm_surge_residual_ft": yt_surge,
            "windmill_point_water_level_mllw_ft": latest_wm_water["water_level_ft"] if latest_wm_water else None,
            "windmill_point_storm_surge_residual_ft": wm_surge
        },
        "forecast_48h_outlook": {
            "peak_forecast_stage_mllw_ft": peak_stage,
            "peak_forecast_stage_time_local": peak_stage_time,
            "peak_estimated_flood_depth_in": peak_compound_depth,
            "peak_risk_tier": peak_tier,
            "peak_risk_label": peak_tier_label,
            "peak_vehicle_passability": peak_timeline_item["vehicle_passability"] if peak_timeline_item else "ALL VEHICLES PASSABLE",
            "hours_at_or_above_action_stage": hours_above_action,
            "advisory_summary": (
                "NO FLOODING EXPECTED: Water levels will remain inside normal tidal ditches and marsh channels."
                if peak_tier == 0 else
                f"FLOODING ADVISORY: Potential {peak_tier_label} with up to {peak_compound_depth} inches of water expected around {peak_stage_time}."
            )
        },
        "forecast_hourly_timeline": fcst_timeline
    }
    return status

def update_archive_observations(archive_path, hourly_obs):
    """
    Appends new completed hourly observations to a permanent cumulative archive CSV.
    Deduplicates by timestamp_utc so reruns never duplicate data.
    """
    now_utc = datetime.now(timezone.utc)
    current_hour_utc = now_utc.replace(minute=0, second=0, microsecond=0)
    
    existing_timestamps = set()
    existing_rows = []
    headers = None
    
    if os.path.exists(archive_path):
        with open(archive_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            for row in reader:
                existing_timestamps.add(row["timestamp_utc"])
                existing_rows.append(row)
                
    if not headers and hourly_obs:
        headers = list(hourly_obs[0].keys())
        
    added = 0
    for obs in hourly_obs:
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
            
        if ts_str not in existing_timestamps:
            existing_rows.append(obs)
            existing_timestamps.add(ts_str)
            added += 1
            
    if added > 0 or not os.path.exists(archive_path):
        existing_rows.sort(key=lambda r: r.get("timestamp_utc", ""))
        with open(archive_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(existing_rows)
            
    return added, len(existing_rows)

def write_csv(filepath, rows, fieldnames):
    """Write list of dictionaries to CSV."""
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

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

    log(f"[*] Querying real-time sensor networks for window: {begin_dt_utc.strftime('%Y-%m-%d %H:%M')} to {end_dt_utc.strftime('%Y-%m-%d %H:%M')} UTC")

    # 1. Ware River WRVV2
    log("[1/6] Fetching Ware River (WRVV2) observed stage...")
    ware_obs = fetch_nwps_wrvv2_observed()
    log(f"      -> Retrieved {len(ware_obs)} 6-min stage readings from NWPS.")

    log("[2/6] Fetching Ware River (WRVV2) stage forecast hydrograph...")
    ware_fcst = fetch_nwps_wrvv2_forecast()
    log(f"      -> Retrieved {len(ware_fcst)} forecast stage points.")

    # 2. Yorktown USCG (8637689)
    log("[3/6] Fetching Yorktown USCG (8637689) wind, pressure, water level & tides...")
    yt_winds = fetch_coops_product("8637689", "wind", begin_dt_utc, end_dt_utc)
    yt_press = fetch_coops_product("8637689", "air_pressure", begin_dt_utc, end_dt_utc)
    yt_temps = fetch_coops_product("8637689", "air_temperature", begin_dt_utc, end_dt_utc)
    yt_water = fetch_coops_product("8637689", "water_level", begin_dt_utc, end_dt_utc)
    yt_preds_past = fetch_coops_product("8637689", "predictions", begin_dt_utc, end_dt_utc)
    yt_preds_future = fetch_coops_product("8637689", "predictions", now_utc, forward_end_utc)
    log(f"      -> Yorktown winds: {len(yt_winds)}, baro: {len(yt_press)}, water: {len(yt_water)}, fwd tides: {len(yt_preds_future)}")

    # 3. Windmill Point (8636580)
    log("[4/6] Fetching Windmill Point (8636580) water level & tide predictions...")
    wm_water = fetch_coops_product("8636580", "water_level", begin_dt_utc, end_dt_utc)
    wm_preds_past = fetch_coops_product("8636580", "predictions", begin_dt_utc, end_dt_utc)
    wm_preds_future = fetch_coops_product("8636580", "predictions", now_utc, forward_end_utc)
    log(f"      -> Windmill Pt water: {len(wm_water)}, verified: {len(wm_preds_past)}, fwd tides: {len(wm_preds_future)}")

    # 4. NWS Grid Forecast & QPF Rain
    log("[5/6] Fetching NWS AKQ hourly wind & weather forecast...")
    nws_fcst = fetch_nws_hourly_forecast()
    log(f"      -> Retrieved {len(nws_fcst)} hourly forecast intervals.")

    log("[6/6] Fetching NWS AKQ quantitative precipitation forecast (QPF)...")
    qpf_map = fetch_nws_qpf_map()
    log(f"      -> Retrieved {len(qpf_map)} hourly QPF intervals.")

    # Data processing & alignment
    log("\n[*] Resampling & aligning recent observations on hourly timestamps...")
    hourly_obs = aggregate_hourly_observations(
        ware_obs, yt_winds, yt_press, yt_temps, yt_water, yt_preds_past,
        wm_water, wm_preds_past, lookback_hours=args.hours
    )
    log(f"    -> Aligned {len(hourly_obs)} hourly observation rows.")

    log("[*] Building forward 48-hour Hybrid Hydrodynamic–ML forecast timeline...")
    fcst_timeline = build_forecast_timeline(ware_fcst, nws_fcst, yt_preds_future, wm_preds_future, qpf_map, max_hours=48)
    log(f"    -> Built {len(fcst_timeline)} hourly forecast periods.")

    # Status summary
    status_summary = generate_latest_status(
        ware_obs, yt_winds, yt_press, yt_temps, yt_water, yt_preds_past,
        wm_water, wm_preds_past, ware_fcst, fcst_timeline
    )

    # Write files
    log(f"\n[*] Writing outputs:")
    
    with open(args.json_out, "w", encoding="utf-8") as f:
        json.dump(status_summary, f, indent=2)
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
    log(f"  Baro Pressure    : {curr['yorktown_baro_pressure_mb']} mb | Windmill Surge: +{curr['windmill_point_storm_surge_residual_ft']} ft")
    log("-" * 72)
    log("MICRO-TOPOGRAPHY SECTOR STATUS:")
    for k, v in curr["site_sectors"].items():
        log(f"  • {v['name']:<36}: {v['depth_in']:>4.1f}\" [{v['status']}]")
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
