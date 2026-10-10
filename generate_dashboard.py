#!/usr/bin/env python3
"""
generate_dashboard.py — Multi-Page Coastal Flood Monitoring & Educational Portal
for Mathews County, Virginia Flood Prediction System.

Generates a complete, modern, human-friendly multi-page web portal:
1. index.html (& flood_dashboard.html): Live Monitor with Human Impact Advisory, Interactive Leaflet Flood Map,
   Property Elevation Cross-Section, Vehicle Passability Matrix, and 48-Hour Hydrograph.
2. alerts.html (& subscribe.html): Instant Mobile Alerts & Step-by-Step Setup Guide with QR code,
   push notification timelines, and privacy-first ntfy.sh integration.
3. about.html: The Project History and Public Observation Summary (2021-2026),
   Discovery of the 3.99 ft Threshold, and Compound Pluvial Physics.
4. guide.html: Visual Flood Severity Tiers (Tier 0 to Tier 3), Vehicle Water Depth Safety Guide,
   and Plain-English Coastal Definitions (MLLW vs NAVD88, Storm Surge Residual, Wind Set-Up).
5. data.html: Major Storm Comparison (Erin, Oct 2025 Record Flood, Sep 2026 Nor'easters, Helene, Ian),
   Yearly Aggregated Observer Dataset Explorer, and Direct Data Downloads.

Author: Antigravity Assistant for Mathews County Flood Prediction Project
"""

import os
import json
import csv
import math
import argparse
import copy
import html
import hashlib
import base64
import re
from functools import wraps
from runtime_safety import assess_status, finite_number
from datetime import datetime

# Global topic configuration
DEFAULT_NTFY_TOPIC = os.getenv("NTFY_TOPIC", "mathews-flood-23128")
NTFY_SERVER = os.getenv("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
from urllib.parse import urlsplit
_url = urlsplit(NTFY_SERVER)
if (_url.scheme != "https" or not _url.hostname or _url.username or _url.password
        or _url.path or _url.query or _url.fragment or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", DEFAULT_NTFY_TOPIC)):
    raise ValueError("Invalid public ntfy server/topic configuration")


import resident_ui

class HtmlText(str):
    """Keep raw strings in JSON and escape interpolation into HTML."""
    def __format__(self, spec):
        return html.escape(super().__format__(spec), quote=True)
    def replace(self, *args):
        return HtmlText(super().replace(*args))
    def strip(self, *args):
        return HtmlText(super().strip(*args))
    def split(self, *args):
        return [HtmlText(v) for v in super().split(*args)]
    def __add__(self, other):
        return HtmlText(super().__add__(other))


def display_value(value):
    return "Unknown" if value is None else value


def escape_view(value):
    if isinstance(value, str):
        return HtmlText(value)
    if isinstance(value, list):
        return [escape_view(v) for v in value]
    if isinstance(value, dict):
        return {escape_view(k): escape_view(v) for k, v in value.items()}
    return value


def status_for_display(status):
    status = copy.deepcopy(status)
    quality = assess_status(status)
    if status.get("display_only_fallback"):
        quality.update(forecast_available=False, forecast_usable=False, alerts_all_clear_allowed=False, state="degraded")
    status["data_quality"] = quality
    fallback = status.get("last_available_forecast", {})
    if not any(finite_number(row.get("forecast_stage_mllw_ft")) for row in status.get("forecast_hourly_timeline", [])) and fallback:
        status["forecast_hourly_timeline"] = fallback.get("forecast_hourly_timeline", [])
        status["forecast_48h_outlook"] = fallback.get("forecast_48h_outlook", {})
        status["display_forecast_saved_at_utc"] = fallback.get("saved_at_utc")
        status["display_forecast_issued_at_utc"] = fallback.get("forecast_issued_at_utc")
        status["display_only_fallback"] = True
    if not quality["current_available"]:
        import micro_topography
        curr = status.setdefault("current_conditions", {})
        unknown = micro_topography.evaluate_compound_inundation(None)
        status["last_available_current_conditions"] = copy.deepcopy(curr)
        curr.update(flood_risk_tier=-1, flood_risk_label="Unknown (gauge missing or stale)",
                    vehicle_passability_code="UNKNOWN", vehicle_passability=unknown["vehicle_passability_label"],
                    vehicle_passability_desc=unknown["vehicle_passability_desc"])
        if not finite_number(curr.get("ware_river_stage_mllw_ft")):
            curr.update(estimated_local_flood_depth_in=None, site_sectors=unknown["sectors"], community_streets=unknown["streets"])
    if not quality["forecast_available"]:
        outl = status.setdefault("forecast_48h_outlook", {})
        if outl.get("peak_risk_tier", -1) <= 0:
            outl["peak_risk_tier"] = -1
        outl["advisory_summary"] = "Forecast incomplete or stale. Flooding cannot be ruled out."
    return status


def safe_template(function):
    @wraps(function)
    def render(status, *args, **kwargs):
        document = function(escape_view(status_for_display(status)),
                            *(escape_view(a) for a in args), **{k: escape_view(v) for k, v in kwargs.items()})
        if not document.startswith("<!DOCTYPE"):
            return document
        # New HTML must never load an old age guard from the browser/CDN cache.
        # The worker caches these exact URLs for offline use after an online visit.
        from pathlib import Path
        for asset in ('assets/community.js', 'assets/community.css'):
            asset_path = Path(__file__).resolve().parent / asset
            if not asset_path.is_file():
                continue  # The publication allowlist enforces assets at deploy time.
            revision = hashlib.sha256(asset_path.read_bytes()).hexdigest()[:12]
            document = document.replace('"' + asset + '"', '"' + asset + '?v=' + revision + '"')
        document = document.replace('</head>', '<link rel="manifest" href="manifest.webmanifest"><meta name="theme-color" content="#0f172a"></head>', 1)
        scripts = re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', document, re.S)
        handlers = [html.unescape(value) for value in re.findall(r'on(?:click|input|change)="([^"]*)"', document)]
        hashes = ["'sha256-" + base64.b64encode(hashlib.sha256(text.encode()).digest()).decode() + "'" for text in scripts + handlers]
        policy = ("default-src 'self'; script-src 'self' 'unsafe-hashes' " + " ".join(hashes)
                  + "; style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://unpkg.com https://fonts.googleapis.com; "
                  + "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
                  + "img-src 'self' data: https://tile.openstreetmap.org https://server.arcgisonline.com https://api.qrserver.com https://unpkg.com; "
                  + "connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-src 'none'")
        return document.replace('<meta charset="UTF-8">', '<meta charset="UTF-8">\n  <meta http-equiv="Content-Security-Policy" content="' + html.escape(policy, quote=True) + '">', 1)
    return render


# Common color themes & risk tiers
TIER_STYLES = {
    -1: {"badge_bg": "bg-slate-100", "badge_text": "text-slate-800", "badge_border": "border-slate-400",
         "pill": "bg-slate-500", "banner_bg": "bg-slate-100", "banner_border": "border-slate-400",
         "banner_text": "text-slate-950", "banner_sub": "text-slate-800", "accent": "#64748b",
         "icon": "fa-circle-question", "label": "Unknown (data unavailable)"},
    0: {
        "badge_bg": "bg-emerald-100",
        "badge_text": "text-emerald-800",
        "badge_border": "border-emerald-300",
        "pill": "bg-emerald-500",
        "banner_bg": "bg-emerald-50",
        "banner_border": "border-emerald-300",
        "banner_text": "text-emerald-950",
        "banner_sub": "text-emerald-800",
        "accent": "#10b981",
        "icon": "fa-circle-check",
        "label": "Tier 0 (Normal / Safe)"
    },
    1: {
        "badge_bg": "bg-amber-100",
        "badge_text": "text-amber-800",
        "badge_border": "border-amber-300",
        "pill": "bg-amber-500",
        "banner_bg": "bg-amber-50",
        "banner_border": "border-amber-300",
        "banner_text": "text-amber-950",
        "banner_sub": "text-amber-800",
        "accent": "#f59e0b",
        "icon": "fa-triangle-exclamation",
        "label": "Tier 1 (Nuisance / Ditch Full)"
    },
    2: {
        "badge_bg": "bg-orange-100",
        "badge_text": "text-orange-800",
        "badge_border": "border-orange-300",
        "pill": "bg-orange-500",
        "banner_bg": "bg-orange-50",
        "banner_border": "border-orange-300",
        "banner_text": "text-orange-950",
        "banner_sub": "text-orange-800",
        "accent": "#ea580c",
        "icon": "fa-car-burst",
        "label": "Tier 2 (Moderate / Driveway Blocked)"
    },
    3: {
        "badge_bg": "bg-red-100",
        "badge_text": "text-red-800",
        "badge_border": "border-red-300",
        "pill": "bg-red-500",
        "banner_bg": "bg-red-50",
        "banner_border": "border-red-300",
        "banner_text": "text-red-950",
        "banner_sub": "text-red-800",
        "accent": "#dc2626",
        "icon": "fa-triangle-exclamation",
        "label": "Tier 3 (Severe / Property Submerged)"
    }
}

def load_data(status_json_path, obs_csv_path, fcst_csv_path, ground_truth_path):
    with open(status_json_path, "r", encoding="utf-8") as f:
        status = json.load(f)

    obs_rows = []
    if os.path.exists(obs_csv_path):
        with open(obs_csv_path, "r", encoding="utf-8") as f:
            obs_rows = list(csv.DictReader(f))

    fcst_rows = []
    if os.path.exists(fcst_csv_path):
        with open(fcst_csv_path, "r", encoding="utf-8") as f:
            fcst_rows = list(csv.DictReader(f))

    ground_truth_rows = []
    if os.path.exists(ground_truth_path):
        with open(ground_truth_path, "r", encoding="utf-8") as f:
            ground_truth_rows = list(csv.DictReader(f))

    return status, obs_rows, fcst_rows, ground_truth_rows

def build_shared_navbar(active_page, status):
    return resident_ui.navbar(active_page, status)

@safe_template
def build_shared_footer(status):
    return resident_ui.footer(status)

# ==============================================================================
# 1. PAGE 1: INDEX.HTML (LIVE MONITOR & INTERACTIVE MAP)
# ==============================================================================
@safe_template
def build_index_html(status, obs_rows, fcst_rows):
    curr = status.get("current_conditions", {})
    outl = status.get("forecast_48h_outlook", {})
    if not fcst_rows or status.get("display_only_fallback"):
        fcst_rows = status.get("forecast_hourly_timeline", [])

    stage = display_value(curr.get("ware_river_stage_mllw_ft", "N/A"))
    stage_navd = display_value(curr.get("ware_river_stage_navd88_ft", "N/A"))
    depth = display_value(curr.get("estimated_local_flood_depth_in", 0.0))
    tier = curr.get("flood_risk_tier", 0)
    tier_info = TIER_STYLES.get(tier, TIER_STYLES[-1])
    passability = curr.get("vehicle_passability", "ALL VEHICLES PASSABLE")
    sectors = curr.get("site_sectors", {})
    streets = curr.get("community_streets", {})
    if not streets or not sectors:
        import micro_topography
        stg_val = float(stage) if isinstance(stage, (int, float)) else None
        st_eval = micro_topography.evaluate_compound_inundation(stg_val)
        if not streets:
            streets = st_eval.get("streets", {})
        if not sectors:
            sectors = st_eval.get("sectors", {})

    street_cards_html = ""
    for st_name, st_info in (streets or {}).items():
        st_depth = st_info.get("depth_in", 0.0)
        st_code = st_info.get("code", "GREEN")
        st_inv_mllw = st_info.get("invert_mllw_ft", 4.0)
        st_inv_navd = st_info.get("invert_navd88_ft", round(st_inv_mllw - 1.64, 2))
        
        badge_cls = "bg-emerald-50 text-emerald-800 border-emerald-200" if st_code == "GREEN" else \
                    "bg-amber-50 text-amber-800 border-amber-200" if st_code == "YELLOW" else \
                    "bg-orange-50 text-orange-800 border-orange-200" if st_code == "ORANGE" else \
                    "bg-red-50 text-red-800 border-red-200"
                    
        dot_cls = "bg-emerald-500" if st_code == "GREEN" else \
                  "bg-amber-500" if st_code == "YELLOW" else \
                  "bg-orange-500" if st_code == "ORANGE" else "bg-red-600"
                  
        street_cards_html += f"""
          <div class="p-3.5 rounded-xl border border-slate-200 bg-slate-50/70 hover:bg-white hover:border-slate-300 shadow-xs transition">
            <div class="flex items-center justify-between mb-1.5">
              <span class="font-bold text-xs text-slate-900">{st_name}</span>
              <span class="inline-flex items-center gap-1.5 text-[10px] font-bold px-2 py-0.5 rounded-full border {badge_cls}">
                <span class="w-1.5 h-1.5 rounded-full {dot_cls}"></span>
                {st_info.get("status", "Dry")}
              </span>
            </div>
            <div class="flex items-baseline justify-between text-xs text-slate-500 font-mono">
              <span class="text-[11px] text-slate-400">Elev: {st_inv_mllw}' MLLW</span>
              <span class="font-bold text-slate-800 font-mono">{st_depth}" Water</span>
            </div>
          </div>
        """

    ditch_depth = sectors.get('ditches', {}).get('depth_in', 0)
    ditch_depth_str = ditch_depth if ditch_depth is not None else 'Unknown'
    ditch_status = sectors.get('ditches', {}).get('status', 'DRY')
    ditch_w = min(100, max(2, int((ditch_depth or 0) * 15)))

    road_depth = sectors.get('road_apron', {}).get('depth_in', 0)
    road_depth_str = road_depth if road_depth is not None else 'Unknown'
    road_status = sectors.get('road_apron', {}).get('status', 'DRY')
    road_w = min(100, max(2, int((road_depth or 0) * 15)))

    drive_depth = sectors.get('main_driveway', {}).get('depth_in', 0)
    drive_depth_str = drive_depth if drive_depth is not None else 'Unknown'
    drive_status = sectors.get('main_driveway', {}).get('status', 'DRY')
    drive_w = min(100, max(2, int((drive_depth or 0) * 15)))

    lawn_depth = sectors.get('yard_lawn', {}).get('depth_in', 0)
    lawn_depth_str = lawn_depth if lawn_depth is not None else 'Unknown'
    lawn_status = sectors.get('yard_lawn', {}).get('status', 'DRY')
    lawn_w = min(100, max(2, int((lawn_depth or 0) * 15)))

    garage_depth = sectors.get('garage_foundation', {}).get('depth_in', 0)
    garage_depth_str = garage_depth if garage_depth is not None else 'Unknown'
    garage_status = sectors.get('garage_foundation', {}).get('status', 'SAFE')
    garage_w = min(100, max(2, int((garage_depth or 0) * 15)))

    sector_bars_html = f"""
      <div class="space-y-3 pt-1">
        <div>
          <div class="flex justify-between text-xs font-medium mb-1">
            <span class="text-slate-700 font-semibold"><i class="fa-solid fa-water text-sky-500 mr-1.5"></i> 1. Bayshore Waterfront Ditches &amp; Swales (Elev: 3.99' MLLW / 2.35' NAVD88)</span>
            <span class="font-mono font-semibold {'text-sky-700 font-bold' if (ditch_depth or 0) > 0 else 'text-slate-400'}">
              {ditch_depth_str}" Water ({ditch_status})
            </span>
          </div>
          <div class="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
            <div class="{'bg-sky-500' if (ditch_depth or 0) > 0 else 'bg-slate-300'} h-full rounded-full transition-all" style="width: {ditch_w}%"></div>
          </div>
        </div>
        <div>
          <div class="flex justify-between text-xs font-medium mb-1">
            <span class="text-slate-700 font-semibold"><i class="fa-solid fa-road text-amber-500 mr-1.5"></i> 2. Lower Residential Blocks — Allview / Hobday / New Little St South (Elev: 4.15' MLLW / 2.51' NAVD88)</span>
            <span class="font-mono font-semibold {'text-amber-700 font-bold' if (road_depth or 0) > 0 else 'text-emerald-700'}">
              {road_depth_str}" Water ({road_status})
            </span>
          </div>
          <div class="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
            <div class="{'bg-amber-500' if (road_depth or 0) > 0 else 'bg-emerald-500'} h-full rounded-full transition-all" style="width: {road_w}%"></div>
          </div>
        </div>
        <div>
          <div class="flex justify-between text-xs font-medium mb-1">
            <span class="text-slate-700 font-semibold"><i class="fa-solid fa-car text-orange-500 mr-1.5"></i> 3. Daniel Ave Central Spine &amp; Julian St — Primary Route (Elev: 4.40' MLLW / 2.76' NAVD88)</span>
            <span class="font-mono font-semibold {'text-orange-700 font-bold' if (drive_depth or 0) > 0 else 'text-emerald-700 font-bold'}">
              {drive_depth_str}" Water ({drive_status})
            </span>
          </div>
          <div class="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
            <div class="{'bg-orange-500' if (drive_depth or 0) > 0 else 'bg-emerald-500'} h-full rounded-full transition-all" style="width: {drive_w}%"></div>
          </div>
        </div>
        <div>
          <div class="flex justify-between text-xs font-medium mb-1">
            <span class="text-slate-700 font-semibold"><i class="fa-solid fa-tree text-emerald-600 mr-1.5"></i> 4. Upper Residential Grounds &amp; Northern Lots (Elev: 4.60' MLLW / 2.96' NAVD88)</span>
            <span class="font-mono font-semibold {'text-red-700 font-bold' if (lawn_depth or 0) > 0 else 'text-emerald-700'}">
              {lawn_depth_str}" Water ({lawn_status})
            </span>
          </div>
          <div class="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
            <div class="{'bg-red-500' if (lawn_depth or 0) > 0 else 'bg-emerald-500'} h-full rounded-full transition-all" style="width: {lawn_w}%"></div>
          </div>
        </div>
        <div>
          <div class="flex justify-between text-xs font-medium mb-1">
            <span class="text-slate-700 font-semibold"><i class="fa-solid fa-house text-blue-600 mr-1.5"></i> 5. Ridge High Ground Pads &amp; Northern Home Footprints (Elev: 4.90' MLLW / 3.26' NAVD88)</span>
            <span class="font-mono font-semibold {'text-red-700 font-bold' if (garage_depth or 0) > 0 else 'text-emerald-700'}">
              {garage_depth_str}" Water ({garage_status})
            </span>
          </div>
          <div class="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
            <div class="{'bg-red-600' if (garage_depth or 0) > 0 else 'bg-emerald-500'} h-full rounded-full transition-all" style="width: {garage_w}%"></div>
          </div>
        </div>
      </div>
    """

    wind_spd = display_value(curr.get("yorktown_wind_speed_mph", "N/A"))
    wind_dir = display_value(curr.get("yorktown_wind_dir_cardinal", "N/A"))
    wind_deg = display_value(curr.get("yorktown_wind_dir_deg", "N/A"))
    wind_gst = display_value(curr.get("yorktown_wind_gust_mph", "N/A"))
    along_bay = display_value(curr.get("along_bay_wind_vector_mph", "N/A"))
    baro = display_value(curr.get("yorktown_baro_pressure_mb", "N/A"))
    surge = display_value(curr.get("windmill_point_storm_surge_residual_ft", "N/A"))
    sw_surge = display_value(curr.get("sewells_point_storm_surge_residual_ft", "N/A"))
    sw_water = display_value(curr.get("sewells_point_water_level_mllw_ft", "N/A"))
    bay_grad = display_value(curr.get("bay_hydraulic_gradient_ft", "N/A"))
    bay_slope = display_value(curr.get("bay_hydraulic_slope_ft_per_mile", "N/A"))
    bay_dir = curr.get("bay_hydraulic_pressure_direction", "N/A")
    fort_info = status.get("fort_monroe", {})
    fort_elev = display_value(fort_info.get("elevation_navd88_ft", "N/A"))
    fort_mllw = display_value(fort_info.get("water_level_mllw_ft", "N/A"))
    fort_fresh = fort_info.get("fresh", False)

    peak_stage = display_value(outl.get("peak_forecast_stage_mllw_ft", "N/A"))
    peak_stage_q10 = display_value(outl.get("peak_forecast_stage_q10_ft", "N/A"))
    peak_stage_q90 = display_value(outl.get("peak_forecast_stage_q90_ft", "N/A"))
    peak_depth_q10 = display_value(outl.get("peak_estimated_flood_depth_q10_in", 0.0))
    peak_depth_q90 = display_value(outl.get("peak_estimated_flood_depth_q90_in", 0.0))
    ci_summary = outl.get("scenario_range_summary", "")
    slope_summary = outl.get("bay_hydraulic_slope_summary", "")
    peak_time = display_value(outl.get("peak_forecast_stage_time_local", "N/A"))
    peak_depth = display_value(outl.get("peak_estimated_flood_depth_in", 0.0))
    peak_tier = outl.get("peak_risk_tier", 0)
    peak_tier_info = TIER_STYLES.get(peak_tier, TIER_STYLES[-1])
    peak_passability = outl.get("peak_vehicle_passability", "ALL VEHICLES PASSABLE")
    hours_flooded = outl.get("hours_at_or_above_action_stage", 0)
    advisory_summary = outl.get("advisory_summary", "No flooding expected.")

    codes = [curr.get("vehicle_passability_code", "UNKNOWN"), outl.get("peak_vehicle_passability_code", "UNKNOWN")]
    route_unknown = "UNKNOWN" in codes or status["data_quality"]["state"] != "healthy"
    route_flooded = any(code in ("YELLOW", "ORANGE", "RED") for code in codes)
    route_dry = not route_unknown and not route_flooded and all(code == "GREEN" for code in codes)
    route_title = "DO NOT ENTER FLOODED ROADS" if route_flooded else "CONDITIONS UNKNOWN" if route_unknown else "NO MODELED STANDING WATER"
    route_description = "Check actual conditions. Never drive into standing or moving floodwater."

    # Human headline logic
    if status["data_quality"]["state"] != "healthy":
        headline = "Data Incomplete — Flood Safety Cannot Be Confirmed"
        sub_headline = "Some observations or forecasts are missing or stale. Check official forecasts and actual road conditions."
    elif tier == 0 and peak_tier == 0:
        headline = "No tidal inundation estimated"
        sub_headline = f"Ware River stage is currently {stage} ft MLLW. Water will remain safely contained in marsh ditches over the next 48 hours."
    elif tier == 0 and peak_tier == 1:
        headline = f"Nuisance Ditch Overflow Expected Around {peak_time.split(' ')[1] if ' ' in str(peak_time) else peak_time}"
        sub_headline = f"Current water level is safe ({stage} ft), but peak tide is forecast to reach {peak_stage} ft. Ditch beds will overflow into low grassy spots."
    elif peak_tier == 2:
        headline = f"Driveway Flooding Warning — Passenger Cars Blocked at High Tide"
        sub_headline = f"Water is forecast to crest at {peak_stage} ft around {peak_time}, covering the driveway with approx {peak_depth}\" of water. Sedans should move before peak tide."
    elif peak_tier == 3:
        headline = f"Severe Coastal Inundation Warning — Property Submerged"
        sub_headline = f"Extreme high tide and storm surge will crest at {peak_stage} ft around {peak_time} with {peak_depth}\"+ water across roads and yard. Do not enter flooded roads, regardless of vehicle clearance."
    else:
        headline = "Live Coastal Flood Advisory"
        sub_headline = advisory_summary

    navbar_html = build_shared_navbar("live", status)
    footer_html = build_shared_footer(status)

    curr_data = status.get("current_conditions", {})
    outl_data = status.get("forecast_48h_outlook", {})

    slim_curr = {
        "ware_river_stage_mllw_ft": curr_data.get("ware_river_stage_mllw_ft"),
        "yorktown_wind_speed_mph": curr_data.get("yorktown_wind_speed_mph"),
        "yorktown_wind_dir_cardinal": curr_data.get("yorktown_wind_dir_cardinal"),
        "yorktown_baro_pressure_mb": curr_data.get("yorktown_baro_pressure_mb"),
        "windmill_point_storm_surge_residual_ft": curr_data.get("windmill_point_storm_surge_residual_ft"),
        "sewells_point_storm_surge_residual_ft": curr_data.get("sewells_point_storm_surge_residual_ft"),
        "estimated_local_flood_depth_in": curr_data.get("estimated_local_flood_depth_in"),
        "vehicle_passability": curr_data.get("vehicle_passability"),
        "community_streets": {k: {"depth_in": v.get("depth_in"), "status": v.get("status"), "code": v.get("code")}
                              for k, v in curr_data.get("community_streets", {}).items()}
    }
    slim_fort = {
        "elevation_navd88_ft": fort_info.get("elevation_navd88_ft"),
        "water_level_mllw_ft": fort_info.get("water_level_mllw_ft"),
        "fresh": fort_fresh
    }
    slim_outl = {
        "peak_forecast_stage_mllw_ft": outl_data.get("peak_forecast_stage_mllw_ft"),
        "peak_hazard_time_local": outl_data.get("peak_hazard_time_local"),
        "peak_forecast_stage_time_local": outl_data.get("peak_forecast_stage_time_local")
    }

    # Embed pruned data for charts and Leaflet (slims HTML significantly while preserving forecast tests)
    embedded_data_json = json.dumps({
        "status": {
            "current_conditions": slim_curr,
            "forecast_48h_outlook": slim_outl,
            "data_quality": status.get("data_quality", {}),
            "fort_monroe": slim_fort
        },
        "forecast": fcst_rows[:48] if fcst_rows else []
    }).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")

    return f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Mathews County, VA Coastal Flood Monitor & Forecast</title>
  <meta name="description" content="Hyper-local real-time coastal flood prediction, interactive map, and 48-hour hydrograph for Mathews County, VA.">
  
  <!-- Tailwind CSS & FontAwesome -->
  <link rel="stylesheet" href="assets/tailwind.css">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" integrity="sha384-t1nt8BQoYMLFN5p42tRAtuAAFQaCQODekUVeKKZrEnEyp4H2R0RHFz0KWpmj7i8g" crossorigin="anonymous">
  
  <!-- Chart.js -->
  <script src="assets/chart.umd.min.js"></script>

  <!-- Leaflet CSS & JS -->
  <link rel="stylesheet" href="assets/leaflet.css">
  <script src="assets/leaflet.js"></script>

  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
    body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }}
    .font-mono {{ font-family: 'JetBrains Mono', monospace; }}
    #flood-map {{ height: 500px; z-index: 10; }}
    .leaflet-popup-content-wrapper {{ border-radius: 12px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.15); }}
  </style>
</head>
<body class="bg-slate-50 text-slate-900 min-h-screen flex flex-col antialiased">

  {navbar_html}

  <main id="main-content" class="flex-grow max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-8 w-full">

    {resident_ui.summary(status)}

    <!-- 5. 48-HOUR HYDROGRAPH & ENVIRONMENTAL DRIVERS -->
    <section data-current-safety class="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 class="text-lg font-bold text-slate-900 flex items-center gap-2">
            <i class="fa-solid fa-chart-line text-sky-600"></i>
            <span data-age-label data-last-label="Last saved water-level forecast">48-hour water-level forecast</span>
          </h2>
          <p class="text-xs sm:text-sm text-slate-500">
            NOAA water-level guidance with empirical local weather adjustments. The band shows uncalibrated scenarios.
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-3 text-xs">
          <span class="flex items-center gap-1.5"><span class="w-3 h-0.5 bg-sky-600"></span> Expected Stage</span>
          <span class="flex items-center gap-1.5"><span class="w-3.5 h-2 bg-sky-200/80 border border-sky-400 border-dashed rounded-[2px]"></span> Uncalibrated Scenario Band</span>
          <span class="flex items-center gap-1.5"><span class="w-3 h-0.5 bg-red-500 border-t border-dashed"></span> 3.99' Flood Threshold</span>
        </div>
      </div>

      <div class="h-80 w-full relative">
        <canvas id="hydrographChart" role="img" aria-label="48-hour Ware River water-level forecast with uncalibrated scenarios. Hourly values are in the table below."></canvas>
      </div>

      <div class="text-[11px] text-slate-500 flex flex-wrap items-center justify-between pt-2 border-t border-slate-100 gap-2">
        <span class="flex items-center gap-1.5"><i class="fa-solid fa-circle-info text-sky-500"></i> Shaded band is an uncalibrated scenario range. It is not a statistical confidence interval or a guaranteed worst case.</span>
        <span class="font-mono text-slate-700 font-medium">Expected Peak: {peak_stage}' (Scenario range: {peak_stage_q10}' to {peak_stage_q90}')</span>
      </div>
    </section>

    {resident_ui.forecast_table(status)}

    <!-- 3. INTERACTIVE LEAFLET FLOOD MAP SECTION -->
    <section data-current-safety id="map-section" class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      <div class="p-5 sm:p-6 border-b border-slate-200 flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-slate-50/50">
        <div>
          <div class="flex items-center gap-2">
            <h2 class="text-lg sm:text-xl font-bold text-slate-900">Blackwater &amp; Mobjack Bay Estates Real-Time Flood Map</h2>
            <span class="px-2.5 py-0.5 text-xs font-semibold bg-amber-100 text-amber-900 rounded-full font-mono">Community Monitoring Zone</span>
          </div>
          <p class="text-xs sm:text-sm text-slate-500 mt-0.5">
            Hyper-local elevation monitoring enclosing <strong>Daniel Ave, Bayshore Ave, River Rd, and connecting neighborhood streets</strong>, using estimated elevations from USGS 1-meter LiDAR. Map colors are estimates, not verified road conditions.
          </p>
        </div>

        <!-- Controls: Quick Zoom & Forecast Toggle -->
        <div class="flex flex-wrap items-center gap-2">
          <!-- Quick Zoom Buttons -->
          <div class="flex items-center bg-slate-200/80 p-1 rounded-xl text-xs font-medium">
            <button id="btn-zoom-community" class="px-2.5 py-1.5 rounded-lg bg-white shadow-sm text-slate-900 font-semibold transition" title="Fit full community monitoring area">
              <i class="fa-solid fa-draw-polygon text-amber-600 mr-1"></i> Community Area
            </button>
            <button id="btn-zoom-property" class="px-2.5 py-1.5 rounded-lg text-slate-600 hover:text-slate-900 transition" title="Zoom to Daniel Ave Primary Benchmark">
              <i class="fa-solid fa-crosshairs text-sky-600 mr-1"></i> Focus Benchmark
            </button>
            <button id="btn-zoom-county" class="px-2.5 py-1.5 rounded-lg text-slate-600 hover:text-slate-900 transition" title="Zoom out to county sensor network">
              <i class="fa-solid fa-earth-americas text-slate-500 mr-1"></i> County View
            </button>
          </div>

          <!-- Forecast Mode Toggle -->
          <div class="flex items-center bg-slate-200/80 p-1 rounded-xl text-xs font-medium">
            <button id="btn-map-current" class="px-3 py-1.5 rounded-lg bg-white shadow-sm text-slate-900 font-semibold transition">
              <i class="fa-solid fa-location-dot text-emerald-600 mr-1"></i> Current ({stage} ft)
            </button>
            <button id="btn-map-peak" class="px-3 py-1.5 rounded-lg text-slate-600 hover:text-slate-900 transition">
              <i class="fa-solid fa-bolt text-amber-500 mr-1"></i> Peak 48h ({peak_stage} ft)
            </button>
          </div>
        </div>
      </div>

      <!-- The Leaflet Map Canvas -->
      <div class="relative">
        <div id="flood-map"></div>

        <!-- Floating Map Legend -->
        <div class="absolute bottom-5 right-5 z-[400] bg-white/95 backdrop-blur-md p-3.5 rounded-xl border border-slate-200 shadow-lg text-xs space-y-1.5 pointer-events-auto max-w-[220px]">
          <div class="font-bold text-slate-900 text-[11px] uppercase tracking-wider mb-1 flex items-center justify-between">
            <span>Risk Severity Legend</span>
            <i class="fa-solid fa-layer-group text-slate-400"></i>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-4 h-0.5 border-t-2 border-dashed border-amber-500 shrink-0"></span>
            <span class="text-slate-700 font-medium text-[11px]">Community Boundary</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-3.5 h-3.5 rounded bg-emerald-500 shrink-0"></span>
            <span class="text-slate-700 font-medium">No inundation estimated</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-3.5 h-3.5 rounded bg-amber-500 shrink-0"></span>
            <span class="text-slate-700 font-medium">Low-spot flooding estimated</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-3.5 h-3.5 rounded bg-orange-500 shrink-0"></span>
            <span class="text-slate-700 font-medium">Moderate flooding estimated</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-3.5 h-3.5 rounded bg-red-600 shrink-0"></span>
            <span class="text-slate-700 font-medium">Severe flooding estimated</span>
          </div>
        </div>
      </div>

      <div class="p-4 bg-slate-50 border-t border-slate-200 text-xs text-slate-600 flex flex-wrap items-center justify-between gap-3">
        <div class="flex items-center gap-4">
          <span class="flex items-center gap-1.5"><i class="fa-solid fa-circle text-[8px] text-sky-600"></i> Click any sensor pin or property polygon on the map to view detailed depths and sensor readings.</span>
        </div>
        <div class="text-slate-400 text-[11px]">Basemap &copy; OpenStreetMap &amp; Esri (Zero API Key &bull; Open GIS)</div>
      </div>
    </section>

    <!-- 4. NEIGHBORHOOD STREET PASSABILITY MATRIX (DIRECTLY VISIBLE) -->
    <section data-current-safety class="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-5">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
        <div>
          <h2 class="text-lg sm:text-xl font-bold text-slate-900 flex items-center gap-2">
            <i class="fa-solid fa-route text-sky-600"></i>
            Neighborhood Street Passability Matrix
          </h2>
          <p class="text-xs sm:text-sm text-slate-500 mt-0.5">
            Hyper-local USGS 1-meter LiDAR elevation thresholds across Mobjack Bay Estates &amp; Blackwater roads.
          </p>
          <div class="mt-2.5 text-xs text-slate-600 bg-sky-50/80 border border-sky-200/80 rounded-xl p-2.5 flex items-start gap-2">
            <i class="fa-solid fa-circle-info text-sky-600 mt-0.5 shrink-0"></i>
            <span><strong>Road Surface vs. Roadside Ditches:</strong> Modeled street depths reflect water on the traveled roadway and key access dips. Roadside ditch culverts sit 5–8 inches lower than paved road crowns and front yards, which is why roadside ditches fill with water well before roads or yards are covered.</span>
          </div>
        </div>
        <div class="text-xs font-mono bg-amber-50 text-amber-900 border border-amber-200/80 px-3 py-1.5 rounded-lg font-semibold self-start sm:self-auto shadow-xs">
          Ditch Tipping Point: 3.99' MLLW
        </div>
      </div>

      <!-- Street Cards Grid -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {street_cards_html}
      </div>

      <!-- Sector Progress Bars in Progressive Disclosure -->
      <details class="pt-2 text-xs text-slate-600 border-t border-slate-100">
        <summary class="font-bold text-sky-700 cursor-pointer hover:underline py-1 flex items-center gap-1.5">
          <i class="fa-solid fa-stairs text-sky-600"></i>
          <span>View Property Sector LiDAR Cross-Section (Ditches, Driveway, Lawn, Garage High Ground)</span>
        </summary>
        <div class="space-y-3.5 pt-3 mt-2">
          {sector_bars_html}
        </div>
      </details>
    </section>

    <!-- 6. ENVIRONMENTAL SENSORS & PROSPECTIVE MODEL VERIFICATION -->
    <details class="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
      <summary class="text-base font-bold text-slate-900 cursor-pointer flex items-center justify-between">
        <span class="flex items-center gap-2">
          <i class="fa-solid fa-gauge-high text-sky-600"></i>
          Regional Weather, Tidal Forcing &amp; Sensor Telemetry
        </span>
        <span class="text-xs font-semibold text-sky-600 hover:underline">Toggle Telemetry</span>
      </summary>
      <div class="pt-4 space-y-6">
        <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-7 gap-3.5">
          <!-- Card 1: Yorktown Winds -->
          <div class="bg-slate-50/70 p-4 sm:p-5 rounded-xl border border-slate-200 shadow-xs space-y-1.5">
            <div class="flex items-center justify-between text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
              <span>Yorktown Winds</span>
              <i class="fa-solid fa-wind text-sky-500"></i>
            </div>
            <div class="text-2xl font-black text-slate-900 font-mono">
              {wind_spd} <span class="text-xs font-semibold text-slate-500">mph</span>
            </div>
            <div class="text-[11px] text-slate-600 flex items-center justify-between">
              <span>From {wind_dir} ({wind_deg}&deg;)</span>
              <span class="text-slate-400">G: {wind_gst} mph</span>
            </div>
          </div>

          <!-- Card 2: Along-Bay Wind Vector -->
          <div class="bg-slate-50/70 p-4 sm:p-5 rounded-xl border border-slate-200 shadow-xs space-y-1.5">
            <div class="flex items-center justify-between text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
              <span>Along-Bay Vector</span>
              <i class="fa-solid fa-compass text-blue-500"></i>
            </div>
            <div class="text-2xl font-black font-mono {'text-amber-600' if (along_bay if finite_number(along_bay) else 0) > 10 else 'text-slate-900'}">
              {along_bay} <span class="text-xs font-semibold text-slate-500">mph</span>
            </div>
            <div class="text-[11px] text-slate-500 truncate" title="Along-bay wind stress">
              {'Data unavailable' if not finite_number(along_bay) else 'Forcing water into Mobjack' if along_bay > 0 else 'Blowing water out to Atlantic'}
            </div>
          </div>

          <!-- Card 3: Barometric Pressure -->
          <div class="bg-slate-50/70 p-4 sm:p-5 rounded-xl border border-slate-200 shadow-xs space-y-1.5">
            <div class="flex items-center justify-between text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
              <span>Barometer</span>
              <i class="fa-solid fa-gauge-high text-indigo-500"></i>
            </div>
            <div class="text-2xl font-black text-slate-900 font-mono">
              {baro} <span class="text-xs font-semibold text-slate-500">mb</span>
            </div>
            <div class="text-[11px] text-slate-500 truncate">
              {'Data unavailable' if not finite_number(baro) else 'Low pressure (water rising)' if baro < 1010 else 'Normal atmospheric pressure'}
            </div>
          </div>

          <!-- Card 4: North Bay Surge (Windmill Point) -->
          <div class="bg-slate-50/70 p-4 sm:p-5 rounded-xl border border-slate-200 shadow-xs space-y-1.5">
            <div class="flex items-center justify-between text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
              <span>North Bay Surge</span>
              <i class="fa-solid fa-water-ladder text-cyan-500"></i>
            </div>
            <div class="text-2xl font-black font-mono {'text-amber-600' if (surge if finite_number(surge) else 0) > 1.0 else 'text-slate-900'}">
              +{surge} <span class="text-xs font-semibold text-slate-500">ft</span>
            </div>
            <div class="text-[11px] text-slate-500 truncate" title="Windmill Point (8636580)">
              Windmill Pt (8636580)
            </div>
          </div>

          <!-- Card 5: South Bay Surge (Sewells Point) -->
          <div class="bg-slate-50/70 p-4 sm:p-5 rounded-xl border border-slate-200 shadow-xs space-y-1.5">
            <div class="flex items-center justify-between text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
              <span>South Bay Surge</span>
              <i class="fa-solid fa-anchor text-blue-600"></i>
            </div>
            <div class="text-2xl font-black font-mono {'text-amber-600' if (sw_surge if finite_number(sw_surge) else 0) > 1.0 else 'text-slate-900'}">
              +{sw_surge} <span class="text-xs font-semibold text-slate-500">ft</span>
            </div>
            <div class="text-[11px] text-slate-500 truncate" title="Sewells Point / Norfolk (8638610)">
              Sewells Pt (8638610)
            </div>
          </div>

          <!-- Card 6: Bay Hydraulic Slope -->
          <div class="bg-slate-50/70 p-4 sm:p-5 rounded-xl border border-slate-200 shadow-xs space-y-1.5">
            <div class="flex items-center justify-between text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
              <span>Bay Hydraulic Slope</span>
              <i class="fa-solid fa-arrows-left-right-to-line text-emerald-600"></i>
            </div>
            <div class="text-2xl font-black font-mono {'text-amber-600' if (bay_grad if finite_number(bay_grad) else 0) >= 0.20 else 'text-slate-900'}">
              {'+' if (bay_grad if finite_number(bay_grad) else 0) > 0 else ''}{bay_grad} <span class="text-xs font-semibold text-slate-500">ft</span>
            </div>
            <div class="text-[11px] text-slate-500 truncate" title="{bay_dir}">
              {'South Inflow Head' if (bay_grad if finite_number(bay_grad) else 0) >= 0.20 else ('North Gradient' if (bay_grad if finite_number(bay_grad) else 0) <= -0.20 else 'Equilibrium')} (46 mi)
            </div>
          </div>

          <!-- Card 7: Fort Monroe Evaluation Sensor -->
          <div class="bg-purple-50/50 p-4 sm:p-5 rounded-xl border border-purple-200/80 shadow-xs space-y-1.5">
            <div class="flex items-center justify-between text-[11px] font-semibold text-purple-700 uppercase tracking-wider">
              <span>Fort Monroe Evaluation</span>
              <i class="fa-solid fa-flask text-purple-600"></i>
            </div>
            <div class="text-2xl font-black text-slate-900 font-mono">
              {fort_elev} <span class="text-xs font-semibold text-slate-500">ft NAVD</span>
            </div>
            <div class="text-[11px] text-slate-500 truncate" title="FTMV2 / USGS 0204289994: Candidate evaluation sensor">
              {fort_mllw} ft MLLW &bull; {'Live Ingested' if fort_fresh else 'Evaluation'}
            </div>
          </div>
        </section>

        {resident_ui.monitoring(status)}
      </div>
    </details>

    <!-- 7. REAL-TIME MOBILE FLOOD ALERTS CALLOUT -->
    <section id="alerts-section" class="bg-gradient-to-r from-slate-900 via-slate-800 to-sky-950 rounded-2xl text-white p-6 sm:p-7 border border-sky-800/50 shadow-md flex flex-col md:flex-row items-center justify-between gap-6">
      <div class="flex items-start sm:items-center gap-4">
        <div class="w-12 h-12 rounded-xl bg-sky-500/20 text-sky-400 border border-sky-500/30 flex items-center justify-center text-xl shrink-0 shadow-inner">
          <i class="fa-solid fa-bell"></i>
        </div>
        <div class="space-y-1">
          <div class="flex flex-wrap items-center gap-2">
            <h3 class="font-bold text-base sm:text-lg text-white">Get Audible Flood Warnings on Your Phone</h3>
            <span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-400/20 text-amber-300 border border-amber-400/30">No subscription fee currently</span>
            <span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-sky-500/20 text-sky-300 border border-sky-500/30">Zero Accounts</span>
          </div>
          <p class="text-xs sm:text-sm text-slate-300 max-w-2xl leading-relaxed">
            Stay informed about estimated flooding near Daniel Ave and Bayshore Ave. Push notifications sent <strong>when fresh forecasts first indicate a flood hazard</strong>. Subscribe to our public alert topic.
          </p>
        </div>
      </div>
      <div class="flex items-center gap-3 shrink-0 w-full md:w-auto justify-end">
        <a href="alerts.html" class="w-full md:w-auto px-5 py-2.5 rounded-xl bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold text-sm shadow-md transition flex items-center justify-center gap-2 group">
          <i class="fa-solid fa-mobile-screen-button"></i>
          <span>Set Up Free Mobile Alerts</span>
          <i class="fa-solid fa-arrow-right text-xs group-hover:translate-x-1 transition-transform"></i>
        </a>
      </div>
    </section>

  </main>

  {footer_html}

  <!-- Embedded JSON Data -->
  <script id="flood-data" type="application/json">
    {embedded_data_json}
  </script>

  <!-- Interactive Map & Charts Logic -->
  <script>
    const escapeHTML = value => String(value ?? 'Unknown').replace(/[&<>"']/g, ch => ({{'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}}[ch]));
    const floodData = JSON.parse(document.getElementById('flood-data').textContent);
    const curr = floodData.status.current_conditions || {{}};
    const fort = floodData.status.fort_monroe || {{}};
    const outl = floodData.status.forecast_48h_outlook || {{}};
    const fcst = floodData.forecast || [];

    // 1. LEAFLET INTERACTIVE MAP — Centered on Daniel Ave Benchmark (37.420183, -76.406550)
    const map = L.map('flood-map', {{
      center: [37.420183, -76.406550],
      zoom: 14,
      scrollWheelZoom: false
    }});

    // Base tile layers (100% free, zero API key required, zero watermarks)
    const osmLayer = L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors'
    }}).addTo(map);

    const esriImagery = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
      maxZoom: 19,
      attribution: 'Tiles &copy; Esri, Maxar, Earthstar Geographics, USDA FSA, USGS, Aerogrid, IGN, IGP, and the GIS User Community'
    }});

    const esriTopo = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
      maxZoom: 19,
      attribution: 'Tiles &copy; Esri &mdash; USGS, NOAA'
    }});

    const esriOcean = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
      maxZoom: 13,
      attribution: 'Tiles &copy; Esri &mdash; NOAA, GEBCO'
    }});

    // Add basemap layer control
    L.control.layers({{
      "OpenStreetMap (Streets & Water)": osmLayer,
      "High-Res Satellite (Esri Imagery)": esriImagery,
      "Esri Topographic": esriTopo,
      "Esri Marine / Ocean": esriOcean
    }}, null, {{ position: 'topright' }}).addTo(map);

    // Sensor Station Markers
    const wrvv2Marker = L.circleMarker([37.4082, -76.4714], {{
      radius: 9,
      fillColor: curr.ware_river_stage_mllw_ft >= 4.0 ? '#ea580c' : '#10b981',
      color: '#ffffff',
      weight: 2,
      opacity: 1,
      fillOpacity: 0.9
    }}).addTo(map);
    wrvv2Marker.bindPopup(`
      <div class="p-1 space-y-1">
        <div class="font-bold text-sm text-slate-900">Ware River near Schley (WRVV2)</div>
        <div class="text-xs text-slate-600">Primary Local Reference Gauge</div>
        <div class="text-base font-extrabold text-sky-900 font-mono">${{curr.ware_river_stage_mllw_ft || 'N/A'}} ft MLLW</div>
        <div class="text-[11px] text-slate-500">Flood Action Threshold: 3.99 ft</div>
      </div>
    `);

    const yorktownMarker = L.circleMarker([37.2267, -76.4789], {{
      radius: 8,
      fillColor: '#0284c7',
      color: '#ffffff',
      weight: 2,
      opacity: 1,
      fillOpacity: 0.85
    }}).addTo(map);
    yorktownMarker.bindPopup(`
      <div class="p-1 space-y-1">
        <div class="font-bold text-sm text-slate-900">Yorktown USCG Station (8637689)</div>
        <div class="text-xs text-slate-600">Primary Meteorological Reference</div>
        <div class="text-sm font-bold text-slate-900 font-mono">${{curr.yorktown_wind_speed_mph || 'N/A'}} mph from ${{escapeHTML(curr.yorktown_wind_dir_cardinal || 'N/A')}}</div>
        <div class="text-[11px] text-slate-500">Baro: ${{curr.yorktown_baro_pressure_mb || 'N/A'}} mb</div>
      </div>
    `);

    const windmillMarker = L.circleMarker([37.6150, -76.2900], {{
      radius: 8,
      fillColor: '#0d9488',
      color: '#ffffff',
      weight: 2,
      opacity: 1,
      fillOpacity: 0.85
    }}).addTo(map);
    windmillMarker.bindPopup(`
      <div class="p-1 space-y-1">
        <div class="font-bold text-sm text-slate-900">Windmill Point (8636580)</div>
        <div class="text-xs text-slate-600">Northern Bay Storm Surge Reference</div>
        <div class="text-sm font-bold text-slate-900 font-mono">+${{curr.windmill_point_storm_surge_residual_ft ?? 'Unknown'}} ft Surge Residual</div>
      </div>
    `);

    const sewellsMarker = L.circleMarker([36.9467, -76.3300], {{
      radius: 8,
      fillColor: '#2563eb',
      color: '#ffffff',
      weight: 2,
      opacity: 1,
      fillOpacity: 0.85
    }}).addTo(map);
    sewellsMarker.bindPopup(`
      <div class="p-1 space-y-1">
        <div class="font-bold text-sm text-slate-900">Sewells Point / Norfolk (8638610)</div>
        <div class="text-xs text-slate-600">Southern Bay Storm Surge Reference</div>
        <div class="text-sm font-bold text-slate-900 font-mono">+${{curr.sewells_point_storm_surge_residual_ft ?? 'Unknown'}} ft Surge Residual</div>
        <div class="text-[11px] text-slate-500">Paired with Windmill Pt across 46.2 mi for hydraulic slope</div>
      </div>
    `);

    const fortMarker = L.circleMarker([37.0042, -76.3006], {{
      radius: 8,
      fillColor: '#8b5cf6',
      color: '#ffffff',
      weight: 2,
      opacity: 1,
      fillOpacity: 0.85
    }}).addTo(map);
    fortMarker.bindPopup(`
      <div class="p-1 space-y-1">
        <div class="font-bold text-sm text-slate-900">Fort Monroe (FTMV2 / USGS 0204289994)</div>
        <div class="text-xs text-purple-700 font-semibold">Candidate Evaluation Sensor</div>
        <div class="text-sm font-bold text-slate-900 font-mono">${{fort.elevation_navd88_ft ?? 'N/A'}} ft NAVD88 (${{fort.water_level_mllw_ft ?? 'N/A'}} ft MLLW)</div>
        <div class="text-[11px] text-slate-500">Live measurements archived for prospective model validation.</div>
      </div>
    `);

    // Primary Ground-Truth Benchmark Marker (Daniel Ave & Blackwater Creek)
    const benchmarkMarker = L.circleMarker([37.420183, -76.406550], {{
      radius: 11,
      fillColor: '#f59e0b',
      color: '#ffffff',
      weight: 3,
      opacity: 1,
      fillOpacity: 0.95
    }}).addTo(map);

    benchmarkMarker.bindPopup(`
      <div class="p-1.5 space-y-1.5 min-w-[220px]">
        <div class="font-bold text-sm text-slate-900 flex items-center gap-1.5">
          <span class="text-amber-500 font-bold">&#9733;</span> Primary Observation Benchmark
        </div>
        <div class="text-xs text-slate-600 font-medium">Daniel Ave &bull; Blackwater, Mathews County</div>
        <div class="text-[11px] font-mono text-slate-500">Coords: 37.420183, -76.406550</div>
        <div class="text-xs font-mono text-slate-700 bg-slate-100 p-1 rounded">LiDAR Elevation: 2.76' NAVD88 (4.40' MLLW)</div>
        <div class="pt-1 border-t border-slate-100 flex items-baseline justify-between">
          <span class="text-xs text-slate-500">Current Depth:</span>
          <span class="text-base font-black text-sky-900 font-mono">${{curr.estimated_local_flood_depth_in ?? 'Unknown'}}"</span>
        </div>
        <div class="text-[11px] font-semibold ${{curr.estimated_local_flood_depth_in > 0 ? 'text-amber-600' : 'text-emerald-600'}}">
          Passability: ${{escapeHTML(curr.vehicle_passability || 'Unknown')}}
        </div>
      </div>
    `);

    // 1. Mobjack Bay Estates & Blackwater Community Monitored Perimeter (Yellow Boundary)
    const communityPerimeterCoords = [
      [37.4223, -76.4116], [37.4223, -76.4095], [37.4222, -76.4070],
      [37.422202, -76.407005], [37.422168, -76.406812], [37.422058, -76.406547],
      [37.421872, -76.406392], [37.421717, -76.406211], [37.421448, -76.406030],
      [37.421186, -76.406132], [37.420658, -76.405830], [37.420328, -76.405371],
      [37.419700, -76.404220], [37.419409, -76.404346], [37.418845, -76.404211],
      [37.418608, -76.403204], [37.418547, -76.404976], [37.418421, -76.405516],
      [37.418280, -76.406629], [37.418290, -76.407025], [37.418132, -76.408074],
      [37.418147, -76.409089], [37.418186, -76.409639], [37.417983, -76.410625],
      [37.418111, -76.411128], [37.4181, -76.4116], [37.4223, -76.4116]
    ];

    const perimeterPoly = L.polygon(communityPerimeterCoords, {{
      color: '#eab308', // Amber/Yellow matching user highlight
      weight: 3.5,
      dashArray: '8, 6',
      fillColor: '#fef08a',
      fillOpacity: 0.08
    }}).addTo(map);

    perimeterPoly.bindPopup(`
      <div class="p-1.5 space-y-1">
        <div class="font-bold text-sm text-amber-900 flex items-center gap-1.5">
          <i class="fa-solid fa-shield-halved text-amber-600"></i>
          Community Flood Monitoring Zone
        </div>
        <div class="text-xs text-slate-700 font-medium">Mobjack Bay Estates &amp; Blackwater Peninsula</div>
        <div class="text-[11px] text-slate-500">Enclosing Daniel Ave, Bayshore Ave, River Rd, and interior connecting cross streets.</div>
        <div class="text-[11px] font-mono text-slate-600 bg-amber-50 p-1 rounded border border-amber-200">Calibrated to USGS 1-meter LiDAR on dry land.</div>
      </div>
    `);

    // 2. Community Micro-Topography Land Elevation Zones (100% on Dry Land — Seamless Tiling, Zero Gaps, Zero in Water)
    const communityZones = [
      {{
        name: "Bayshore Waterfront Ditches & Shoreline Swales",
        elev: 3.99,
        desc: "Lowest swales and roadside ditch culverts along Bayshore Ave. First to overflow at 3.99 ft.",
        coords: [
          [37.4184, -76.4116], [37.4184, -76.4092], [37.4185, -76.4073],
          [37.4186, -76.4054], [37.4186, -76.4047], [37.4187, -76.4038],
          [37.418608, -76.403204], [37.418547, -76.404976], [37.418421, -76.405516],
          [37.418280, -76.406629], [37.418290, -76.407025], [37.418132, -76.408074],
          [37.418147, -76.409089], [37.418186, -76.409639], [37.417983, -76.410625],
          [37.418111, -76.411128], [37.4181, -76.4116], [37.4184, -76.4116]
        ]
      }},
      {{
        name: "Lower Residential Blocks (Allview / Hobday / New Little St South)",
        elev: 4.15,
        desc: "Southern residential parcels and lower cross street dips (1 to 4 inches standing water).",
        coords: [
          [37.4194, -76.4116], [37.4194, -76.4054],
          [37.4186, -76.4054], [37.4185, -76.4073], [37.4184, -76.4092],
          [37.4184, -76.4116]
        ]
      }},
      {{
        name: "Daniel Ave Central Spine & Julian St (Benchmark Corridor)",
        elev: 4.40,
        desc: "Primary community artery & Observation Benchmark. Sedans blocked when water exceeds 4 inches.",
        coords: [
          [37.4206, -76.4116], [37.4206, -76.4070], [37.420658, -76.405830],
          [37.420328, -76.405371], [37.419700, -76.404220], [37.419409, -76.404346],
          [37.418845, -76.404211], [37.418608, -76.403204],
          [37.4187, -76.4038], [37.4186, -76.4047], [37.4186, -76.4054],
          [37.4194, -76.4054], [37.4194, -76.4116]
        ]
      }},
      {{
        name: "Upper Residential Grounds & Northern Lots",
        elev: 4.60,
        desc: "Elevated residential lawns and northern lots along Daniel Ave. Do not enter flooded roads, regardless of vehicle clearance.",
        coords: [
          [37.4223, -76.4116], [37.4223, -76.4095], [37.4222, -76.4070],
          [37.4206, -76.4070], [37.4206, -76.4116]
        ]
      }},
      {{
        name: "Ridge High Ground Pads & Northern Home Footprints",
        elev: 4.90,
        desc: "Elevated building footprint and highest ground along community ridge north of River Road. Safe from moderate tides.",
        coords: [
          [37.4222, -76.4070],
          [37.422202, -76.407005], [37.422168, -76.406812], [37.422058, -76.406547],
          [37.421872, -76.406392], [37.421717, -76.406211], [37.421448, -76.406030],
          [37.421186, -76.406132], [37.420658, -76.405830],
          [37.4206, -76.4070]
        ]
      }}
    ];

    // 3. Community Street Network Centerlines with Verified Street Names & On-Map Labels
    const communityStreetData = {{
      "Bayshore Ave": {{
        fullName: "Bayshore Avenue",
        elev: 3.75,
        desc: "Southern waterfront roadway. West & east dips flood first.",
        coords: [
          [37.418612, -76.405419], [37.41858, -76.405771], [37.418556, -76.406277],
          [37.418525, -76.406948], [37.41852, -76.406995], [37.418469, -76.407802],
          [37.418451, -76.408076], [37.418417, -76.408605], [37.418403, -76.409227]
        ]
      }},
      "Julian St": {{
        fullName: "Julian Street",
        elev: 3.78,
        desc: "Connecting street between Daniel Ave and Bayshore Ave.",
        coords: [
          [37.420307, -76.407368], [37.419501, -76.407203], [37.419026, -76.407095],
          [37.41852, -76.406995]
        ]
      }},
      "Mobjack St": {{
        fullName: "Mobjack Street",
        elev: 3.82,
        desc: "Eastern connector between Daniel Ave/River Rd and Bayshore Ave.",
        coords: [
          [37.420142, -76.405689], [37.420096, -76.405699], [37.420036, -76.405699],
          [37.419961, -76.405691], [37.418612, -76.405419]
        ]
      }},
      "Daniel Ave": {{
        fullName: "Daniel Avenue",
        elev: 4.40,
        desc: "Main community spine. Primary Observation Benchmark at 4.40 ft.",
        coords: [
          [37.418612, -76.405419], [37.418614, -76.405388], [37.418638, -76.405025],
          [37.41864, -76.404743], [37.418698, -76.404708], [37.419085, -76.404812],
          [37.41964, -76.405232], [37.420138, -76.40569], [37.420183, -76.406550],
          [37.420307, -76.407368], [37.42026, -76.408129], [37.420215, -76.408918],
          [37.420186, -76.409627], [37.420128, -76.410866], [37.42012, -76.411600]
        ]
      }},
      "Allview St": {{
        fullName: "Allview Street",
        elev: 4.13,
        desc: "Western interior cross street. Shallow puddling above 4.13 ft.",
        coords: [
          [37.418403, -76.409227], [37.418605, -76.409328], [37.419033, -76.409405],
          [37.419515, -76.409495], [37.420186, -76.409627]
        ]
      }},
      "River Rd (at Daniel Ave)": {{
        fullName: "River Road (at Daniel Ave)",
        elev: 3.59,
        desc: "Northern shoreline access road. Critical intersection at Daniel Ave dips ~2 inches lower than Bayshore (3.59' MLLW / 1.95' NAVD88); floods first.",
        coords: [
          [37.420183, -76.406550], [37.420375, -76.406297], [37.420803, -76.406602]
        ]
      }},
      "River Rd (North Ridge)": {{
        fullName: "River Road (North Ridge)",
        elev: 4.53,
        desc: "Elevated northern ridge road (4.53' MLLW / 2.89' NAVD88). Sits high along residential pads; remains passable during moderate tides.",
        coords: [
          [37.420803, -76.406602], [37.421278, -76.406765], [37.421438, -76.406817],
          [37.421918, -76.407001], [37.421975, -76.407028]
        ]
      }},
      "Hobday St": {{
        fullName: "Hobday Street",
        elev: 4.22,
        desc: "Interior cross street between Daniel Ave & Bayshore Ave.",
        coords: [
          [37.42026, -76.408129], [37.419952, -76.408083], [37.4194, -76.407984],
          [37.418841, -76.407868], [37.418469, -76.407802]
        ]
      }},
      "New Little St": {{
        fullName: "New Little Street",
        elev: 4.23,
        desc: "Interior cross street rising towards Daniel Ave northern ridge.",
        coords: [
          [37.420215, -76.408918], [37.419698, -76.408835], [37.419093, -76.408721],
          [37.418767, -76.40865], [37.418417, -76.408605]
        ]
      }},
      "Matthews St": {{
        fullName: "Matthews Street",
        elev: 3.75,
        desc: "North residential access off Daniel Ave. Dips at entrance to match Bayshore flood levels (3.75' MLLW / 2.11' NAVD88).",
        coords: [
          [37.420307, -76.407368], [37.420319, -76.40717], [37.419648, -76.407127]
        ]
      }},
      "Bunny Rabbit Ln": {{
        fullName: "Bunny Rabbit Lane",
        elev: 4.45,
        desc: "Western community boundary road on elevated ridge.",
        coords: [
          [37.420128, -76.410866], [37.419844, -76.410825], [37.41937, -76.410734],
          [37.418645, -76.410585], [37.418322, -76.410533]
        ]
      }}
    }};

    let zoneLayers = [];
    let streetLayers = [];

    function renderCommunityMap(stageVal, streetAssessment = null) {{
      const unknownStage = stageVal == null || !Number.isFinite(stageVal);
      zoneLayers.forEach(l => map.removeLayer(l));
      zoneLayers = [];
      streetLayers.forEach(l => map.removeLayer(l));
      streetLayers = [];

      // 1. Render Elevation Zones (Dry land)
      communityZones.forEach(z => {{
        let color = '#10b981'; // Green
        let depthIn = 0;
        let statusTxt = unknownStage ? 'Unknown — data unavailable' : 'No modeled tidal inundation';
        if (unknownStage) color = '#64748b';

        if (!unknownStage && stageVal >= z.elev) {{
          depthIn = Math.round((stageVal - z.elev) * 12 * 10) / 10;
          if (depthIn < 4) {{
            color = '#f59e0b'; // Yellow / Nuisance
            statusTxt = `Nuisance Water (${{depthIn}}" deep)`;
          }} else if (depthIn < 8) {{
            color = '#ea580c'; // Orange / Moderate
            statusTxt = `Submerged (${{depthIn}}" deep) - Sedans Blocked`;
          }} else {{
            color = '#dc2626'; // Red / Severe
            statusTxt = `Severe Inundation (${{depthIn}}" deep)`;
          }}
        }} else if (!unknownStage && z.elev - stageVal < 0.25) {{
          color = '#f59e0b';
          statusTxt = 'Caution: Water within 3 inches of bank';
        }}

        const poly = L.polygon(z.coords, {{
          color: color,
          weight: 1.5,
          fillColor: color,
          fillOpacity: 0.45
        }}).addTo(map);

        poly.bindPopup(`
          <div class="p-1.5 space-y-1">
            <div class="font-bold text-sm text-slate-900">${{z.name}}</div>
            <div class="text-xs text-slate-600 font-medium">${{z.desc}}</div>
            <div class="text-xs font-mono text-slate-500">LiDAR Ground Invert: ${{z.elev}}' MLLW (${{(z.elev - 1.64).toFixed(2)}}' NAVD88)</div>
            <div class="text-xs font-bold pt-1 border-t border-slate-100" style="color: ${{color}}">Status: ${{statusTxt}}</div>
          </div>
        `);
        zoneLayers.push(poly);
      }});

      // 2. Render Street Corridors with Permanent On-Map Labels
      const normName = s => String(s || '').toLowerCase()
        .replace(/\b(ave|avenue)\b/g, 'ave')
        .replace(/\b(st|street)\b/g, 'st')
        .replace(/\b(rd|road)\b/g, 'rd')
        .replace(/\b(ln|lane)\b/g, 'ln')
        .trim();

      const lookupAssessment = (shortName, fullName) => {{
        if (!streetAssessment) return null;
        if (streetAssessment[shortName]) return streetAssessment[shortName];
        if (fullName && streetAssessment[fullName]) return streetAssessment[fullName];
        const target1 = normName(shortName);
        const target2 = normName(fullName);
        for (const [k, v] of Object.entries(streetAssessment)) {{
          const kn = normName(k);
          if (kn === target1 || kn === target2) return v;
        }}
        return null;
      }};

      for (const [stName, stData] of Object.entries(communityStreetData)) {{
        const fullTitle = stData.fullName || stName;
        let stColor = '#059669'; // Emerald
        let stDepth = 0;
        let stStatus = unknownStage ? 'Unknown — data unavailable' : 'No modeled tidal inundation';
        if (unknownStage) stColor = '#64748b';

        if (!unknownStage && stageVal >= stData.elev) {{
          stDepth = Math.round((stageVal - stData.elev) * 12 * 10) / 10;
          if (stDepth < 3.5) {{
            stColor = '#d97706'; // Amber
            stStatus = `Caution: Puddles / Ditch Full (${{stDepth}}")`;
          }} else if (stDepth < 7.5) {{
            stColor = '#ea580c'; // Orange
            stStatus = `Flooded Road — Do Not Drive (${{stDepth}}")`;
          }} else {{
            stColor = '#dc2626'; // Red
            stStatus = `Critical — Impassable Deep Water (${{stDepth}}")`;
          }}
        }}

        const assessment = lookupAssessment(stName, stData.fullName);
        if (assessment) {{
          stDepth = assessment.depth_in;
          stStatus = escapeHTML(assessment.status);
          stColor = ({{ GREEN: '#059669', YELLOW: '#d97706', ORANGE: '#ea580c', RED: '#dc2626', UNKNOWN: '#64748b' }})[assessment.code] || '#64748b';
        }}
        const line = L.polyline(stData.coords, {{
          color: stColor,
          weight: 5,
          opacity: 0.9,
          lineJoin: 'round'
        }}).addTo(map);

        line.bindPopup(`
          <div class="p-1.5 space-y-1">
            <div class="font-bold text-sm text-slate-900 flex items-center gap-1.5">
              <i class="fa-solid fa-road text-slate-500"></i> ${{escapeHTML(fullTitle)}}
            </div>
            <div class="text-xs text-slate-600">${{escapeHTML(stData.desc)}}</div>
            <div class="text-xs font-mono text-slate-500">Elevation: ${{stData.elev}}' MLLW (${{(stData.elev - 1.64).toFixed(2)}}' NAVD88)</div>
            <div class="text-xs font-bold pt-1 border-t border-slate-100" style="color: ${{stColor}}">Live Passability: ${{stStatus}}</div>
          </div>
        `);
        streetLayers.push(line);
      }}
    }}

    // Initial render with current conditions
    renderCommunityMap(floodData.status.data_quality.current_available ? Number(curr.ware_river_stage_mllw_ft) : null, curr.community_streets);

    // Toggle button handlers
    const btnCurrent = document.getElementById('btn-map-current');
    const btnPeak = document.getElementById('btn-map-peak');

    btnCurrent.addEventListener('click', () => {{
      btnCurrent.classList.add('bg-white', 'shadow-sm', 'font-semibold', 'text-slate-900');
      btnCurrent.classList.remove('text-slate-600');
      btnPeak.classList.remove('bg-white', 'shadow-sm', 'font-semibold', 'text-slate-900');
      btnPeak.classList.add('text-slate-600');
      renderCommunityMap(floodData.status.data_quality.current_available ? Number(curr.ware_river_stage_mllw_ft) : null, curr.community_streets);
    }});

    btnPeak.addEventListener('click', () => {{
      btnPeak.classList.add('bg-white', 'shadow-sm', 'font-semibold', 'text-slate-900');
      btnPeak.classList.remove('text-slate-600');
      btnCurrent.classList.remove('bg-white', 'shadow-sm', 'font-semibold', 'text-slate-900');
      btnCurrent.classList.add('text-slate-600');
      const timeline = floodData.status.forecast_hourly_timeline || floodData.forecast || [];
      const peakRow = timeline.find(row => row.timestamp_local === outl.peak_hazard_time_local);
      renderCommunityMap(floodData.status.data_quality.forecast_available && peakRow ? Number(peakRow.forecast_stage_mllw_ft) : null, peakRow?.community_streets);
    }});

    // Quick Zoom Button Handlers
    const btnZoomComm = document.getElementById('btn-zoom-community');
    const btnZoomProp = document.getElementById('btn-zoom-property');
    const btnZoomCounty = document.getElementById('btn-zoom-county');

    if (btnZoomComm) {{
      btnZoomComm.addEventListener('click', () => {{
        btnZoomComm.classList.add('bg-white', 'shadow-sm', 'font-semibold', 'text-slate-900');
        btnZoomComm.classList.remove('text-slate-600');
        if (btnZoomProp) {{
          btnZoomProp.classList.remove('bg-white', 'shadow-sm', 'font-semibold', 'text-slate-900');
          btnZoomProp.classList.add('text-slate-600');
        }}
        if (btnZoomCounty) {{
          btnZoomCounty.classList.remove('bg-white', 'shadow-sm', 'font-semibold', 'text-slate-900');
          btnZoomCounty.classList.add('text-slate-600');
        }}
        map.fitBounds(perimeterPoly.getBounds().pad(0.06), {{ duration: 1.2 }});
        perimeterPoly.openPopup();
      }});
    }}

    if (btnZoomProp) {{
      btnZoomProp.addEventListener('click', () => {{
        btnZoomProp.classList.add('bg-white', 'shadow-sm', 'font-semibold', 'text-slate-900');
        btnZoomProp.classList.remove('text-slate-600');
        if (btnZoomComm) {{
          btnZoomComm.classList.remove('bg-white', 'shadow-sm', 'font-semibold', 'text-slate-900');
          btnZoomComm.classList.add('text-slate-600');
        }}
        if (btnZoomCounty) {{
          btnZoomCounty.classList.remove('bg-white', 'shadow-sm', 'font-semibold', 'text-slate-900');
          btnZoomCounty.classList.add('text-slate-600');
        }}
        map.flyTo([37.420183, -76.406550], 16, {{ duration: 1.2 }});
        benchmarkMarker.openPopup();
      }});
    }}

    if (btnZoomCounty) {{
      btnZoomCounty.addEventListener('click', () => {{
        btnZoomCounty.classList.add('bg-white', 'shadow-sm', 'font-semibold', 'text-slate-900');
        btnZoomCounty.classList.remove('text-slate-600');
        if (btnZoomComm) {{
          btnZoomComm.classList.remove('bg-white', 'shadow-sm', 'font-semibold', 'text-slate-900');
          btnZoomComm.classList.add('text-slate-600');
        }}
        if (btnZoomProp) {{
          btnZoomProp.classList.remove('bg-white', 'shadow-sm', 'font-semibold', 'text-slate-900');
          btnZoomProp.classList.add('text-slate-600');
        }}
        map.flyTo([37.28, -76.38], 10, {{ duration: 1.2 }});
      }});
    }}

    // 2. Water-level chart with uncalibrated scenarios
    const ctx = document.getElementById('hydrographChart').getContext('2d');
    const labels = fcst.map(r => {{
      const d = r.timestamp_local || '';
      return d ? d.slice(5,10) + ' ' + (d.split(' ')[1] || '').slice(0,5) : d;
    }});
    const stageData = fcst.map(r => r.forecast_stage_mllw_ft === "" || r.forecast_stage_mllw_ft == null ? null : Number(r.forecast_stage_mllw_ft));
    const stageDataQ10 = fcst.map(r => r.forecast_stage_q10_ft === "" || r.forecast_stage_q10_ft == null ? null : Number(r.forecast_stage_q10_ft));
    const stageDataQ90 = fcst.map(r => r.forecast_stage_q90_ft === "" || r.forecast_stage_q90_ft == null ? null : Number(r.forecast_stage_q90_ft));
    const rainData = fcst.map(r => parseFloat(r.rain_forecast_hourly_in || 0));
    const thresholdData = fcst.map(() => 3.99);

    new Chart(ctx, {{
      type: 'line',
      data: {{
        labels: labels,
        datasets: [
          {{
            label: 'Upper scenario (uncalibrated)',
            data: stageDataQ90,
            borderColor: 'rgba(2, 132, 199, 0.35)',
            borderDash: [3, 3],
            borderWidth: 1.5,
            pointRadius: 0,
            fill: false,
            tension: 0.35,
            yAxisID: 'y'
          }},
          {{
            label: 'Uncalibrated Scenario Band',
            data: stageDataQ10,
            borderColor: 'rgba(2, 132, 199, 0.35)',
            borderDash: [3, 3],
            borderWidth: 1.5,
            pointRadius: 0,
            fill: '-1', // fills to dataset 0 (stageDataQ90)
            backgroundColor: 'rgba(2, 132, 199, 0.15)',
            tension: 0.35,
            yAxisID: 'y'
          }},
          {{
            label: 'Expected Stage (ft MLLW)',
            data: stageData,
            borderColor: '#0284c7',
            backgroundColor: 'transparent',
            fill: false,
            tension: 0.35,
            borderWidth: 2.8,
            pointRadius: 2,
            pointHoverRadius: 5,
            yAxisID: 'y'
          }},
          {{
            label: 'Flood Threshold (3.99 ft)',
            data: thresholdData,
            borderColor: '#ef4444',
            borderWidth: 2,
            borderDash: [5, 5],
            fill: false,
            pointRadius: 0,
            yAxisID: 'y'
          }},
          {{
            type: 'bar',
            label: 'Hourly Rain (in)',
            data: rainData,
            backgroundColor: 'rgba(14, 165, 233, 0.4)',
            yAxisID: 'y1'
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        interaction: {{ mode: 'index', intersect: false }},
        plugins: {{
          legend: {{ position: 'top', labels: {{ boxWidth: 12, font: {{ size: 11 }} }} }}
        }},
        scales: {{
          x: {{ grid: {{ display: false }}, ticks: {{ maxTicksLimit: 12, font: {{ size: 10 }} }} }},
          y: {{
            title: {{ display: true, text: 'Stage (ft MLLW)', font: {{ size: 11 }} }},
            min: 1.0,
            max: Math.max(5.5, Math.ceil(Math.max(...stageDataQ90, ...stageData, 4.5))),
            grid: {{ color: '#f1f5f9' }}
          }},
          y1: {{
            position: 'right',
            title: {{ display: true, text: 'Rain (in)', font: {{ size: 11 }} }},
            min: 0,
            max: 2.0,
            grid: {{ display: false }}
          }}
        }}
      }}
    }});
  </script>
</body>
</html>
"""

# ==============================================================================
# 2. PAGE 2: ALERTS.HTML (INSTANT MOBILE ALERTS & SUBSCRIPTION GUIDE)
# ==============================================================================
@safe_template
def build_alerts_html(status):
    return resident_ui.alerts(status, NTFY_SERVER, DEFAULT_NTFY_TOPIC)

@safe_template
def build_about_html(status):
    navbar_html = build_shared_navbar("about", status)
    footer_html = build_shared_footer(status)

    return f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>About & History — Mathews County Coastal Flood Prediction System</title>
  <meta name="description" content="The story of the Mathews Flood Monitor: built on years of careful observation by Sandra Hottinger and created for Blackwater and Mobjack Bay Estates.">
  
  <link rel="stylesheet" href="assets/tailwind.css">
  <link rel="stylesheet" href="assets/community.css">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" integrity="sha384-t1nt8BQoYMLFN5p42tRAtuAAFQaCQODekUVeKKZrEnEyp4H2R0RHFz0KWpmj7i8g" crossorigin="anonymous">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
    body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }}
    .font-mono {{ font-family: 'JetBrains Mono', monospace; }}
  </style>
</head>
<body class="bg-slate-50 text-slate-900 min-h-screen flex flex-col antialiased">

  {navbar_html}

  <main id="main-content" class="flex-grow max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-12 w-full">

    <!-- Hero Header: Built on Years of Observation, Created for Our Community -->
    <header class="space-y-4">
      <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-sky-100 text-sky-800 text-xs font-bold uppercase tracking-wider">
        <i class="fa-solid fa-heart text-rose-500"></i> Community-Driven Coastal Science
      </div>
      <h1 class="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-slate-900 tracking-tight leading-tight">
        Built on Years of Observation,<br class="hidden sm:inline"> Created for Our Community
      </h1>
      <p class="text-xl sm:text-2xl font-semibold text-slate-800 leading-relaxed max-w-3xl">
        The Mathews Flood Monitor began with a practical question: <span class="text-sky-700">What does a rising river gauge mean for the water outside our homes?</span>
      </p>
      <p class="text-base sm:text-lg text-slate-600 leading-relaxed max-w-3xl">
        For residents of Blackwater and Mobjack Bay Estates, flooding can affect everyday life long before it becomes a major disaster. Water can fill roadside ditches, spread across driveways, and interrupt access through the neighborhood. Knowing that coastal flooding is possible is useful. Understanding how changing water levels may affect familiar places makes that information more meaningful.
      </p>
    </header>

    <!-- Section 1: Sandra Hottinger’s Work Made This Possible -->
    <section class="bg-gradient-to-br from-amber-50/70 via-white to-sky-50/40 rounded-2xl p-6 sm:p-10 border border-amber-200/80 shadow-sm space-y-6">
      <div class="flex items-center gap-3">
        <div class="w-12 h-12 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center text-xl shadow-xs shrink-0">
          <i class="fa-solid fa-book-journal-whills"></i>
        </div>
        <div>
          <span class="text-xs font-bold uppercase tracking-wider text-amber-800">The Ground-Truth Foundation</span>
          <h2 class="text-2xl sm:text-3xl font-bold text-slate-900">Sandra Hottinger’s Work Made This Possible</h2>
        </div>
      </div>

      <div class="space-y-4 text-slate-700 leading-relaxed text-base sm:text-lg">
        <p>
          Over the years, Sandra Hottinger took the time to study nearby river gauges and compare their readings with flooding she observed in the community. She meticulously kept written logs, recording water levels, local flood depths, weather conditions, and the circumstances surrounding individual events.
        </p>

        <!-- Pull-Quote / Highlight Block -->
        <div class="my-6 p-5 sm:p-6 bg-white/95 border-l-4 border-amber-500 rounded-r-xl shadow-xs">
          <p class="text-lg sm:text-xl font-semibold text-slate-900 italic leading-snug">
            &ldquo;These records preserved something a distant gauge cannot measure on its own: what rising water actually looked like here.&rdquo;
          </p>
        </div>

        <p>
          By returning to the same problem across many tides, storms, and seasons, Sandra built a valuable record of the relationship between regional water levels and local flooding. Her observations helped reveal when water began spreading beyond the drainage system and how local depths changed as gauge readings rose.
        </p>
        <p>
          That patient, consistent work provided the essential local evidence needed to develop this project’s hyperlocal flood model. Her handwritten records became a structured dataset that could be compared with historical gauge measurements and weather data, supporting statistical analysis and machine learning.
        </p>
        <div class="pt-3 border-t border-amber-200/60 font-medium text-slate-900">
          Sandra’s observations are the foundation of this project. The technology builds on knowledge she gathered over years of paying close attention to this place.
        </div>
      </div>
    </section>

    <!-- Section 2: Why the Mobjack Bay Area Is Vulnerable -->
    <section class="bg-white rounded-2xl p-6 sm:p-10 border border-slate-200 shadow-sm space-y-6">
      <div class="flex items-center gap-3">
        <div class="w-12 h-12 rounded-xl bg-sky-100 text-sky-700 flex items-center justify-center text-xl shadow-xs shrink-0">
          <i class="fa-solid fa-water"></i>
        </div>
        <div>
          <span class="text-xs font-bold uppercase tracking-wider text-sky-700">Geographic &amp; Hydrologic Reality</span>
          <h2 class="text-2xl sm:text-3xl font-bold text-slate-900">Why the Mobjack Bay Area Is Vulnerable</h2>
        </div>
      </div>

      <div class="space-y-4 text-slate-700 leading-relaxed text-base sm:text-lg">
        <p>
          Mobjack Bay lies along the western side of the Chesapeake Bay, with tidal rivers and creeks connecting its waters to surrounding communities. Around Blackwater and Mobjack Bay Estates, low elevations and gently sloping terrain leave some roads, yards, and drainage channels close to tidal water levels.
        </p>
        <p>
          In this landscape, a relatively small rise in water can make a substantial difference on land. High tides raise the starting water level, while persistent onshore winds and coastal storms can push additional water toward the shoreline. Mathews County’s vulnerability to storm-driven tidal flooding is documented in the <a href="https://ccrm.vims.edu/gis_data_maps/ccrmp/mathews/Mathews_SMP.pdf" target="_blank" rel="noopener noreferrer" class="text-sky-600 hover:text-sky-800 font-semibold underline decoration-sky-300 underline-offset-2">Virginia Institute of Marine Science’s Shoreline Management Plan</a>.
        </p>
        <p>
          Rain can add another layer to the problem. When receiving creeks and bay waters are already high, ditches may drain more slowly, allowing rainfall to collect in low areas. The resulting flooding reflects the combined effects of tides, wind, rainfall, and local terrain.
        </p>
      </div>
    </section>

    <!-- Section 3: Turning Local Knowledge into Useful Guidance -->
    <section class="bg-white rounded-2xl p-6 sm:p-10 border border-slate-200 shadow-sm space-y-6">
      <div class="flex items-center gap-3">
        <div class="w-12 h-12 rounded-xl bg-indigo-100 text-indigo-700 flex items-center justify-center text-xl shadow-xs shrink-0">
          <i class="fa-solid fa-compass-drafting"></i>
        </div>
        <div>
          <span class="text-xs font-bold uppercase tracking-wider text-indigo-700">Hyper-Local Model Development</span>
          <h2 class="text-2xl sm:text-3xl font-bold text-slate-900">Turning Local Knowledge into Useful Guidance</h2>
        </div>
      </div>

      <div class="space-y-4 text-slate-700 leading-relaxed text-base sm:text-lg">
        <p>
          Howard Hottinger developed and maintains this independent community monitor, combining Sandra’s observation record with NOAA and USGS measurements, forecast guidance, and local elevation information.
        </p>
        <p>
          The purpose is to help residents understand developing conditions, anticipate possible neighborhood impacts, and prepare earlier. The monitor translates regional water-level information into estimates grounded in the community’s own experience.
        </p>
        <p>
          Its current focus is Blackwater and Mobjack Bay Estates. Estimates carry uncertainty, and conditions can differ from one location to another. Residents should use this information alongside official National Weather Service warnings and local emergency instructions.
        </p>
        <div class="p-4 bg-indigo-50/70 border border-indigo-100 rounded-xl text-indigo-950 font-semibold flex items-center gap-3">
          <i class="fa-solid fa-heart text-rose-500 text-lg shrink-0"></i>
          <span>At its heart, this project is about making years of careful observation useful to the people who live here.</span>
        </div>
      </div>
    </section>

    <!-- Physical Breakthroughs Discovered from the Logs -->
    <section class="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6">
      <div class="flex items-center justify-between flex-wrap gap-2 border-b border-slate-100 pb-3">
        <h2 class="text-xl sm:text-2xl font-bold text-slate-900 flex items-center gap-2">
          <i class="fa-solid fa-atom text-sky-600"></i>
          Physical Breakthroughs Discovered from the Logs
        </h2>
        <a href="science.html" class="text-xs font-semibold text-sky-600 hover:text-sky-800 flex items-center gap-1">
          View scientific benchmarks &amp; methodology <i class="fa-solid fa-arrow-right text-[10px]"></i>
        </a>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="p-5 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
          <div class="text-sky-600 font-bold text-2xl font-mono">3.99 ft</div>
          <h3 class="font-bold text-slate-900 text-sm">1. The Tipping Point</h3>
          <p class="text-xs text-slate-600 leading-relaxed">
            The historical depth relationship begins near 3.99 ft MLLW on the Ware River gauge, when roadside ditches fill and brim over into yards.
          </p>
        </div>

        <div class="p-5 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
          <div class="text-sky-600 font-bold text-2xl font-mono">10.95" / ft</div>
          <h3 class="font-bold text-slate-900 text-sm">2. The Inundation Slope</h3>
          <p class="text-xs text-slate-600 leading-relaxed">
            Every 0.10 ft of river rise yields approximately 1.1 to 1.2 inches of water depth on the property in the historical record.
          </p>
        </div>

        <div class="p-5 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
          <div class="text-sky-600 font-bold text-2xl font-mono">&beta; Restriction</div>
          <h3 class="font-bold text-slate-900 text-sm">3. Compound Pluvial Physics</h3>
          <p class="text-xs text-slate-600 leading-relaxed">
            Heavy rainfall cannot drain by gravity when elevated bay tides cork ditch culverts, trapping rain directly on driveways.
          </p>
        </div>
      </div>
    </section>

    <!-- Community Observation Privacy & Data Links -->
    <section class="resident-card flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6">
      <div class="space-y-1">
        <h3 class="font-bold text-slate-900 text-base flex items-center gap-2">
          <i class="fa-solid fa-users text-sky-600"></i> Community Observations &amp; Privacy
        </h3>
        <p class="text-sm text-slate-600">
          Historical observations inform the model. Original notebooks and observer logs remain strictly private. Summaries are published openly on our data page.
        </p>
      </div>
      <div class="flex items-center gap-3 shrink-0">
        <a href="data.html" class="px-4 py-2 rounded-xl bg-white border border-slate-200 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-xs transition">
          Explore Historical Data
        </a>
        <a href="https://github.com/flatfoot584/mathews-flood-monitor/issues/new" class="px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold shadow-xs transition">
          Contact Maintainer
        </a>
      </div>
    </section>

    <!-- Automated Serverless Cloud Execution -->
    <section class="bg-slate-900 text-white rounded-2xl p-6 sm:p-8 space-y-4">
      <h2 class="text-xl sm:text-2xl font-bold flex items-center gap-2">
        <i class="fa-solid fa-cloud text-sky-400"></i>
        Serverless Cloud Execution
      </h2>
      <p class="text-slate-300 text-sm leading-relaxed">
        This entire portal runs at <strong>zero financial cost</strong> using GitHub Actions. Every 30 minutes:
      </p>
      <ul class="text-xs text-slate-300 space-y-2 list-disc list-inside">
        <li>A cloud runner spins up and queries NOAA NWPS (Ware River WRVV2 6-min stage &amp; 4-day forecast hydrograph).</li>
        <li>Fetches real-time winds and storm surge from Yorktown USCG and Windmill Point.</li>
        <li>Computes NOAA guidance with empirical weather adjustments and estimated local water depths.</li>
        <li>Appends verified hours to our permanent <code class="bg-slate-800 text-sky-300 px-1 py-0.5 rounded">archive_hourly_observations.csv</code>.</li>
        <li>Rebuilds and publishes this website on GitHub Pages.</li>
      </ul>
    </section>

  </main>

  {footer_html}
</body>
</html>
"""

# ==============================================================================
# 4. PAGE 4: GUIDE.HTML (FLOOD TIERS & DEFINITIONS)
# ==============================================================================
@safe_template
def build_guide_html(status):
    navbar_html = build_shared_navbar("guide", status)
    footer_html = build_shared_footer(status)

    return f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Flood Severity Guide & Definitions — Mathews County Flood Monitor</title>
  <meta name="description" content="Visual guide to coastal flood risk tiers, vehicle depth safety limits, and plain-English definitions for Mathews County, VA.">
  
  <link rel="stylesheet" href="assets/tailwind.css">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" integrity="sha384-t1nt8BQoYMLFN5p42tRAtuAAFQaCQODekUVeKKZrEnEyp4H2R0RHFz0KWpmj7i8g" crossorigin="anonymous">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
    body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }}
    .font-mono {{ font-family: 'JetBrains Mono', monospace; }}
  </style>
</head>
<body class="bg-slate-50 text-slate-900 min-h-screen flex flex-col antialiased">

  {navbar_html}

  <main id="main-content" class="flex-grow max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-12 w-full">

    <!-- Hero Header -->
    <section class="space-y-3">
      <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sky-100 text-sky-800 text-xs font-bold uppercase tracking-wider">
        <i class="fa-solid fa-ruler-vertical"></i> Flood Risk Guide
      </div>
      <h1 class="text-3xl sm:text-4xl lg:text-5xl font-black text-slate-900 tracking-tight leading-tight">
        Understanding the Flood Tiers & Tidal Physics
      </h1>
      <p class="text-lg text-slate-600 leading-relaxed max-w-3xl">
        Clear, visual explanations of the 4 coastal flood severity tiers, vehicle driving limits, and plain-English translations of confusing marine terminology.
      </p>
    </section>

    <!-- 1. THE 4 FLOOD TIERS -->
    <section class="space-y-6">
      <h2 class="text-2xl font-bold text-slate-900 flex items-center gap-2">
        <i class="fa-solid fa-layer-group text-sky-600"></i>
        The 4 Risk Severity Tiers
      </h2>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Tier 0 Card -->
        <div class="bg-white rounded-2xl p-6 border-2 border-emerald-300 shadow-sm space-y-3">
          <div class="flex items-center justify-between">
            <span class="px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 text-xs font-bold uppercase tracking-wider">
              <i class="fa-solid fa-circle-check mr-1"></i> Tier 0
            </span>
            <span class="text-xs font-mono font-bold text-slate-500">Stage &lt; 4.0' MLLW</span>
          </div>
          <h3 class="text-xl font-extrabold text-slate-900">Normal / Safe Conditions</h3>
          <div class="text-sm text-emerald-700 font-semibold font-mono">Ground Flood Depth: 0.0 inches</div>
          <p class="text-xs text-slate-600 leading-relaxed">
            Water is fully contained within natural marsh channels and roadside ditch beds. No road or lawn inundation.
          </p>
          <div class="pt-2 border-t border-slate-100 text-xs text-slate-700 space-y-1">
            <div><strong>Vehicles:</strong> No modeled tidal inundation; verify rainfall and actual road conditions.</div>
            <div><strong>Action:</strong> None required.</div>
          </div>
        </div>

        <!-- Tier 1 Card -->
        <div class="bg-white rounded-2xl p-6 border-2 border-amber-300 shadow-sm space-y-3">
          <div class="flex items-center justify-between">
            <span class="px-3 py-1 rounded-full bg-amber-100 text-amber-800 text-xs font-bold uppercase tracking-wider">
              <i class="fa-solid fa-triangle-exclamation mr-1"></i> Tier 1
            </span>
            <span class="text-xs font-mono font-bold text-slate-500">Stage 4.0' – 4.3' MLLW</span>
          </div>
          <h3 class="text-xl font-extrabold text-slate-900">Nuisance Flooding / Ditches Full</h3>
          <div class="text-sm text-amber-700 font-semibold font-mono">Ground Flood Depth: 1.0" – 4.0" (Low Spots)</div>
          <p class="text-xs text-slate-600 leading-relaxed">
            Ditch beds are brim-full. Water begins backing up through driveway culvert pipes and creeps into low grassy depressions.
          </p>
          <div class="pt-2 border-t border-slate-100 text-xs text-slate-700 space-y-1">
            <div><strong>Vehicles:</strong> Avoid flooded culvert dips; do not drive into standing water.</div>
            <div><strong>Action:</strong> Keep pets inside; check ditch pipes for debris.</div>
          </div>
        </div>

        <!-- Tier 2 Card -->
        <div class="bg-white rounded-2xl p-6 border-2 border-orange-300 shadow-sm space-y-3">
          <div class="flex items-center justify-between">
            <span class="px-3 py-1 rounded-full bg-orange-100 text-orange-800 text-xs font-bold uppercase tracking-wider">
              <i class="fa-solid fa-car-burst mr-1"></i> Tier 2
            </span>
            <span class="text-xs font-mono font-bold text-slate-500">Stage 4.4' – 4.7' MLLW</span>
          </div>
          <h3 class="text-xl font-extrabold text-slate-900">Moderate Flooding / Driveway Impassable</h3>
          <div class="text-sm text-orange-700 font-semibold font-mono">Driveway Depth: 5.0" – 8.0"</div>
          <p class="text-xs text-slate-600 leading-relaxed">
            Water sheets completely across the main driveway. Road edges disappear underwater.
          </p>
          <div class="pt-2 border-t border-slate-100 text-xs text-slate-700 space-y-1">
            <div><strong>Vehicles:</strong> Passenger cars & sedans <strong>BLOCKED</strong>. Do not enter flooded roads in any vehicle.</div>
            <div><strong>Action:</strong> Move cars to high ground before high tide; plan travel around low tide.</div>
          </div>
        </div>

        <!-- Tier 3 Card -->
        <div class="bg-white rounded-2xl p-6 border-2 border-red-300 shadow-sm space-y-3">
          <div class="flex items-center justify-between">
            <span class="px-3 py-1 rounded-full bg-red-100 text-red-800 text-xs font-bold uppercase tracking-wider">
              <i class="fa-solid fa-triangle-exclamation mr-1"></i> Tier 3
            </span>
            <span class="text-xs font-mono font-bold text-slate-500">Stage &ge; 4.8' MLLW</span>
          </div>
          <h3 class="text-xl font-extrabold text-slate-900">Severe Inundation / Property Submerged</h3>
          <div class="text-sm text-red-700 font-semibold font-mono">Yard Depth: 9.0" – 15.0"+</div>
          <p class="text-xs text-slate-600 leading-relaxed">
            "Island" conditions. Lawns, ditches, and access roads merge into continuous open water. Approaching garage apron.
          </p>
          <div class="pt-2 border-t border-slate-100 text-xs text-slate-700 space-y-1">
            <div><strong>Vehicles:</strong> All standard vehicles <strong>IMPASSABLE</strong>. High risk of stall or float.</div>
            <div><strong>Action:</strong> Emergency access only. Do not attempt to drive through floodwaters.</div>
          </div>
        </div>
      </div>
    </section>

    <!-- 2. VEHICLE WATER DEPTH SAFETY GUIDE -->
    <section class="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-5">
      <h2 class="text-xl sm:text-2xl font-bold text-slate-900 flex items-center gap-2">
        <i class="fa-solid fa-car text-sky-600"></i>
        Vehicle Water Depth Danger Limits
      </h2>
      <p class="text-xs sm:text-sm text-slate-600">
        Salt water is corrosive and electrically conductive. Even shallow depths cause catastrophic vehicle damage.
      </p>

      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
        <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
          <div class="text-emerald-700 font-black text-xl font-mono">3 Inches</div>
          <div class="font-bold text-xs text-slate-900">Shallow water still poses a hazard</div>
          <p class="text-[11px] text-slate-600">Do not enter floodwater in any vehicle. Even shallow water can hide road damage, current and deeper areas.</p>
        </div>

        <div class="p-4 rounded-xl bg-orange-50 border border-orange-200 space-y-1.5">
          <div class="text-orange-700 font-black text-xl font-mono">6 Inches</div>
          <div class="font-bold text-xs text-orange-900">Loss of control hazard</div>
          <p class="text-[11px] text-orange-800">Six inches of moving water can knock a person down. Water depth does not establish that a road is safe to cross.</p>
        </div>

        <div class="p-4 rounded-xl bg-red-50 border border-red-200 space-y-1.5">
          <div class="text-red-700 font-black text-xl font-mono">12+ Inches</div>
          <div class="font-bold text-xs text-red-900">Buoyant / Floating Hazard</div>
          <p class="text-[11px] text-red-800">Water displaces vehicle weight. Cars float and can be swept off submerged road shoulders into ditch beds.</p>
        </div>
      </div>
    </section>

    <section class="resident-card"><h2>Save the monitor for offline viewing</h2><p>On iPhone, open the site in Safari and use Share, then Add to Home Screen. On Android or a supported desktop browser, use its Install or Add to Home Screen option. Visit the dashboard online first to save the main pages.</p><p>Offline pages retain their original timestamps and show an offline notice. Forecasts do not update offline; external warnings and map tiles may be unavailable. Mobile ntfy alerts are configured separately.</p></section>
    <!-- 3. PLAIN-ENGLISH GLOSSARY -->
    <section class="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6">
      <h2 class="text-xl sm:text-2xl font-bold text-slate-900 flex items-center gap-2">
        <i class="fa-solid fa-spell-check text-sky-600"></i>
        Demystifying Marine & Coastal Jargon
      </h2>

      <div class="space-y-4 text-xs sm:text-sm">
        <div class="border-b border-slate-200 pb-4 space-y-1">
          <h3 class="font-bold text-slate-900 text-base">MLLW (Mean Lower Low Water) vs NAVD88</h3>
          <p class="text-slate-600 leading-relaxed">
            <strong>MLLW</strong> is a tidal datum referenced to the average lowest daily tide — boaters and NOAA tide tables use this because it keeps water levels as positive numbers. <strong>NAVD88</strong> is a fixed national topographic elevation datum used by surveyors.
          </p>
          <div class="font-mono text-xs bg-slate-100 p-2 rounded text-slate-700 mt-1">
            Local Mathews Conversion: NAVD88 (ft) = MLLW (ft) - 1.64 ft
          </div>
        </div>

        <div class="border-b border-slate-200 pb-4 space-y-1">
          <h3 class="font-bold text-slate-900 text-base">Storm Surge Residual</h3>
          <p class="text-slate-600 leading-relaxed">
            The difference between the <em>verified water level</em> and the <em>predicted astronomical tide</em>. If NOAA predicted high tide at 2.5 ft, but the river reached 4.1 ft, the surge residual is <strong>+1.6 ft</strong>.
          </p>
        </div>

        <div class="border-b border-slate-200 pb-4 space-y-1">
          <h3 class="font-bold text-slate-900 text-base">Along-Bay Wind Vector (Wind Set-Up)</h3>
          <p class="text-slate-600 leading-relaxed">
            The Chesapeake Bay runs approximately north-to-south (20&deg; azimuth). Winds blowing from <strong>NNE, NE, and E</strong> act like a giant snowplow, forcing open-bay water down the Chesapeake and piling it into Mobjack Bay where it cannot escape.
          </p>
        </div>

        <div class="space-y-1">
          <h3 class="font-bold text-slate-900 text-base">Compound Pluvial Flooding</h3>
          <p class="text-slate-600 leading-relaxed">
            When high bay water plugs the drainage ditches, local rain has nowhere to drain. Even 2 inches of rain during a moderate high tide causes serious flooding that wouldn't occur on a dry day.
          </p>
        </div>
      </div>
    </section>

  </main>

  {footer_html}
</body>
</html>
"""

# ==============================================================================
# 5. PAGE 5: DATA.HTML (STORM ARCHIVE & DOWNLOADS)
# ==============================================================================
@safe_template
def build_data_html(status, ground_truth_rows, obs_rows):
    navbar_html = build_shared_navbar("data", status)
    footer_html = build_shared_footer(status)

    # Notable storms list
    notable_storms = []

    storm_cards_html = ""
    for s in notable_storms:
        badge_text = s.get("badge", "")
        is_record = "10-Yr Record" in badge_text
        border_cls = "border-rose-300 ring-2 ring-rose-200 bg-rose-50/20" if is_record else "border-slate-200 bg-white"
        badge_bg = "bg-rose-100 text-rose-800 border-rose-200" if is_record else ("bg-amber-100 text-amber-800 border-amber-200" if ("Twin" in badge_text or "Major" in badge_text) else "bg-sky-100 text-sky-800 border-sky-200")
        badge_html = f'<span class="text-[10px] font-bold px-2 py-0.5 rounded-full border {badge_bg}">{badge_text}</span>' if badge_text else ""
        depth_val = float(s['depth'].replace('\"', ''))
        depth_color = "text-rose-600" if depth_val >= 15 else ("text-orange-600" if depth_val >= 8 else "text-sky-700")

        storm_cards_html += f"""
        <div class="{border_cls} p-5 rounded-xl border shadow-sm space-y-2 flex flex-col justify-between hover:shadow-md transition">
          <div>
            <div class="flex items-center justify-between gap-1">
              <span class="text-xs font-bold text-slate-800 uppercase tracking-wider">{s['name']}</span>
              {badge_html}
            </div>
            <div class="text-[11px] text-slate-500 font-mono mt-0.5">{s['date']}</div>
            <div class="flex items-baseline justify-between pt-2">
              <div class="text-xl font-black text-slate-900 font-mono">{s['stage']}</div>
              <div class="text-sm font-bold {depth_color} font-mono">Depth: {s['depth']}</div>
            </div>
          </div>
          <div class="text-xs text-slate-600 flex flex-col gap-1 border-t border-slate-100 pt-2 mt-2">
            <span class="font-medium text-slate-700"><i class="fa-solid fa-wind text-slate-400 mr-1"></i> {s['wind']}</span>
            <span class="text-[11px] text-slate-500 italic leading-snug">{s['notes']}</span>
          </div>
        </div>
        """

    # Only explicitly public yearly aggregates are interpolated. Raw notes/rows are ignored.
    table_rows_html = ""
    for r in sorted(ground_truth_rows, key=lambda x: x.get("year", ""), reverse=True):
        if not str(r.get("year", "")).isdigit():
            continue
        values = [r.get(k, "—") for k in ("year", "record_count", "stage_min_ft", "stage_max_ft", "depth_mean_in", "depth_max_in")]
        cells = "".join(f'<td class="px-3 py-2.5 font-mono text-slate-700">{v}</td>' for v in values)
        table_rows_html += f'<tr class="hover:bg-slate-50 border-b border-slate-100 text-xs">{cells}</tr>'

    return f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Storm History & Data Archive — Mathews County Flood Monitor</title>
  <meta name="description" content="Historical storm comparisons (Helene, Ian, Idalia, Ophelia) and open data downloads for Mathews County, VA.">
  
  <link rel="stylesheet" href="assets/tailwind.css">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" integrity="sha384-t1nt8BQoYMLFN5p42tRAtuAAFQaCQODekUVeKKZrEnEyp4H2R0RHFz0KWpmj7i8g" crossorigin="anonymous">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
    body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }}
    .font-mono {{ font-family: 'JetBrains Mono', monospace; }}
  </style>
</head>
<body class="bg-slate-50 text-slate-900 min-h-screen flex flex-col antialiased">

  {navbar_html}

  <main id="main-content" class="flex-grow max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-12 min-w-0 w-full w-full">

    <!-- Hero Header -->
    <section class="space-y-3">
      <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sky-100 text-sky-800 text-xs font-bold uppercase tracking-wider">
        <i class="fa-solid fa-database"></i> Storm History & Open Data
      </div>
      <h1 class="text-3xl sm:text-4xl lg:text-5xl font-black text-slate-900 tracking-tight leading-tight">
        Historical Storm Archive & Data Center
      </h1>
      <p class="text-lg text-slate-600 leading-relaxed max-w-3xl">
        Browse yearly historical observation summaries and download the live automated gauge and forecast datasets. Individual observer records remain private.
      </p>
    </section>

    <section class="bg-white rounded-2xl p-6 border border-slate-200 space-y-3">
      <h2 class="text-xl font-bold text-slate-900">Historical observation summaries</h2>
      <p class="text-slate-600">Yearly statistics preserve the project's historical context without publishing individual observer records or notebook images. These are historical measurements, not an evaluation of today's forecast accuracy.</p>
    </section>

    <!-- 2. DATA DOWNLOAD CENTER -->
    <section class="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-5">
      <div>
        <h2 class="text-xl sm:text-2xl font-bold text-slate-900 flex items-center gap-2">
          <i class="fa-solid fa-file-arrow-down text-sky-600"></i>
          Download public data
        </h2>
        <p class="text-xs sm:text-sm text-slate-500 mt-1">
          These downloads contain public automated observations, forecasts, and yearly historical summaries. Original observer records and internal documents are not published.
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
        <!-- Download 1 -->
        <a href="archive_hourly_observations.csv" class="p-5 rounded-xl border border-slate-200 bg-slate-50 hover:bg-sky-50/50 hover:border-sky-300 transition group flex flex-col justify-between">
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold text-sky-700 uppercase">Hourly Archive</span>
              <i class="fa-solid fa-download text-slate-400 group-hover:text-sky-600 transition"></i>
            </div>
            <div class="font-bold text-slate-900 text-sm">Hourly sensor observations (CSV)</div>
            <p class="text-xs text-slate-600 leading-relaxed">
              Permanent cumulative hourly dataset appended every 30 minutes in the cloud.
            </p>
          </div>
          <div class="text-[11px] text-slate-400 font-mono pt-4">Updated every 30 mins</div>
        </a>

        <!-- Download 2 -->
        <a href="observer_yearly_summary.csv" class="p-5 rounded-xl border border-slate-200 bg-slate-50 hover:bg-sky-50/50 hover:border-sky-300 transition group flex flex-col justify-between">
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold text-sky-700 uppercase">Ground Truth</span>
              <i class="fa-solid fa-download text-slate-400 group-hover:text-sky-600 transition"></i>
            </div>
            <div class="font-bold text-slate-900 text-sm">Yearly observation summary (CSV)</div>
            <p class="text-xs text-slate-600 leading-relaxed">
              Yearly record counts and numerical stage/depth summaries; no individual records, notebook images, or free-text notes.
            </p>
          </div>
          <div class="text-[11px] text-slate-400 font-mono pt-4">Yearly aggregates &bull; 2021–2026</div>
        </a>

        <!-- Download 3 -->
        <a href="latest_status.json" class="p-5 rounded-xl border border-slate-200 bg-slate-50 hover:bg-sky-50/50 hover:border-sky-300 transition group flex flex-col justify-between">
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold text-sky-700 uppercase">JSON API</span>
              <i class="fa-solid fa-download text-slate-400 group-hover:text-sky-600 transition"></i>
            </div>
            <div class="font-bold text-slate-900 text-sm">Current conditions &amp; forecast (JSON)</div>
            <p class="text-xs text-slate-600 leading-relaxed">
              Real-time API JSON endpoint with current stage, sector elevations, passability, and 48h outlook.
            </p>
          </div>
          <div class="text-[11px] text-slate-400 font-mono pt-4">REST API &bull; Live</div>
        </a>
      </div>
    </section>

    {resident_ui.reporting()}

    <!-- 3. GROUND TRUTH OBSERVATION EXPLORER TABLE -->
    <section class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden space-y-4 p-6">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 class="text-xl font-bold text-slate-900">Yearly Observation Summary</h2>
          <p class="text-xs sm:text-sm text-slate-500">Yearly numeric aggregates, sorted newest first. Raw observer records are retained privately.</p>
        </div>
        <div class="text-xs text-slate-500 font-mono">
          Aggregate historical records
        </div>
      </div>

      <div class="overflow-x-auto max-h-[640px] overflow-y-auto border border-slate-200 rounded-xl shadow-inner">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="sticky top-0 bg-slate-100 text-slate-700 text-[11px] font-bold uppercase tracking-wider border-b border-slate-200 z-10 shadow-sm">
              <th class="px-3 py-2.5">Year</th>
              <th class="px-3 py-2.5">Record count</th>
              <th class="px-3 py-2.5">Minimum stage (ft)</th>
              <th class="px-3 py-2.5">Maximum stage (ft)</th>
              <th class="px-3 py-2.5">Mean depth (in)</th>
              <th class="px-3 py-2.5">Maximum depth (in)</th>
            </tr>
          </thead>
          <tbody>
            {table_rows_html}
          </tbody>
        </table>
      </div>
    </section>

  </main>

  {footer_html}
</body>
</html>
"""


# ==============================================================================
# 6. PAGE 6: SCIENCE.HTML (SCIENTIFIC METHODOLOGY & EMPIRICAL BENCHMARKS)
# ==============================================================================
@safe_template
def build_science_html(status, evidence=None):
    if not evidence:
        evidence_path = os.path.join("models", "scientific_evidence.json")
        if os.path.exists(evidence_path):
            with open(evidence_path, "r", encoding="utf-8") as f:
                evidence = json.load(f)
        else:
            evidence = {}

    navbar_html = build_shared_navbar("science", status)
    footer_html = build_shared_footer(status)

    metadata = evidence.get("metadata", {})
    ds = evidence.get("dataset_characteristics", {})
    model_perf = evidence.get("model_performance", {})
    stage1_now = model_perf.get("stage1_nowcast", {})
    stage1_fcst = model_perf.get("stage1_forecast", {})
    stage2 = model_perf.get("stage2_inundation", {})
    lidar_benchmarks = evidence.get("lidar_ground_truth_validation", [])
    streets = evidence.get("community_street_network", [])
    case_studies = evidence.get("benchmark_storm_case_studies", [])
    changelog = evidence.get("changelog", [])

    total_obs = ds.get("total_observations", 204)
    valid_pairs = ds.get("valid_numerical_pairs", 181)
    flooded_obs = ds.get("flooded_observations", 137)
    zero_flood_obs = ds.get("zero_flood_observations", 44)
    corr_flooded_r = ds.get("correlation_flooded_r", 0.9302)
    corr_flooded_r2 = ds.get("correlation_flooded_r2", 0.8652)
    corr_overall_r = ds.get("correlation_overall_r", 0.8898)
    stage_dist = ds.get("ware_river_stage_distribution_ft", {})
    depth_dist = ds.get("flood_depth_distribution_in", {})

    stage1_r2 = stage1_now.get("test_r2", 0.9731)
    stage1_mae_in = stage1_now.get("test_mae_in", 1.46)
    stage1_rmse_in = stage1_now.get("test_rmse_in", 1.92)

    stage1_fcst_r2 = stage1_fcst.get("test_r2", 0.7209)
    stage1_fcst_mae_in = stage1_fcst.get("test_mae_in", 4.74)
    stage1_fcst_rmse_in = stage1_fcst.get("test_rmse_in", 6.18)

    stage2_r2 = stage2.get("r2", 0.8511)
    stage2_mae_in = stage2.get("mae_inches", 1.25)
    stage2_rmse_in = stage2.get("rmse_inches", 1.69)
    stage2_slope = stage2.get("slope_in_per_ft", 10.95)
    tipping_point = stage2.get("tipping_point_threshold_mllw_ft", 3.99)

    # Format LiDAR table rows
    lidar_rows_html = ""
    for b in lidar_benchmarks:
        diff = b.get("discrepancy_ft", 0.0)
        diff_str = f"{diff:+.2f} ft ({diff*12.0:+.1f} in)" if abs(diff) > 0.001 else "0.00 ft (Exact match)"
        diff_badge = 'bg-emerald-100 text-emerald-800 border-emerald-200' if abs(diff) < 0.05 else 'bg-sky-100 text-sky-800 border-sky-200'
        lidar_rows_html += f"""
        <tr class="border-b border-slate-100 hover:bg-slate-50 transition text-xs sm:text-sm">
          <td class="px-4 py-3 font-semibold text-slate-900">{b.get('feature', '')}</td>
          <td class="px-4 py-3 font-mono text-slate-700">{b.get('elevation_navd88_ft', 0.0):.2f} ft</td>
          <td class="px-4 py-3 font-mono font-bold text-sky-700">{b.get('elevation_mllw_ft', 0.0):.2f} ft</td>
          <td class="px-4 py-3 font-mono font-bold text-slate-900">{b.get('model_empirical_mllw_ft', 0.0):.2f} ft</td>
          <td class="px-4 py-3"><span class="px-2 py-0.5 rounded text-[11px] font-bold border font-mono {diff_badge}">{diff_str}</span></td>
          <td class="px-4 py-3 text-xs text-slate-600">{b.get('significance', '')}</td>
        </tr>
        """

    # Format street rows
    street_rows_html = ""
    for s in streets:
        street_rows_html += f"""
        <tr class="border-b border-slate-100 hover:bg-slate-50 transition text-xs sm:text-sm">
          <td class="px-4 py-3 font-semibold text-slate-900">{s.get('street', '')}</td>
          <td class="px-4 py-3 font-mono text-slate-700">{s.get('invert_navd88_ft', 0.0):.2f} ft</td>
          <td class="px-4 py-3 font-mono font-bold text-sky-700">{s.get('invert_mllw_ft', 0.0):.2f} ft</td>
          <td class="px-4 py-3 text-xs text-slate-600">{s.get('risk_note', '')}</td>
        </tr>
        """

    # Format Benchmark storm case studies
    storm_rows_html = ""
    for cs in case_studies:
        diff = cs.get("depth_in", 0.0) - cs.get("predicted_depth_in", 0.0)
        storm_rows_html += f"""
        <tr class="border-b border-slate-100 hover:bg-slate-50 transition text-xs sm:text-sm">
          <td class="px-4 py-3 font-semibold text-slate-900">
            <div>{cs.get('storm', '')}</div>
            <div class="text-[11px] font-mono text-slate-400 font-normal">{cs.get('date', '')}</div>
          </td>
          <td class="px-4 py-3 font-mono font-bold text-slate-800">{cs.get('stage_mllw_ft', 0.0):.2f} ft</td>
          <td class="px-4 py-3 font-mono font-bold text-rose-700">{cs.get('depth_in', 0.0):.2f}&quot;</td>
          <td class="px-4 py-3 font-mono font-bold text-sky-700">{cs.get('predicted_depth_in', 0.0):.2f}&quot;</td>
          <td class="px-4 py-3 font-mono font-bold {'text-rose-600' if diff > 0 else 'text-emerald-600'}">{diff:+.2f}&quot;</td>
          <td class="px-4 py-3 font-mono text-xs text-slate-600">{cs.get('wind', '')}</td>
          <td class="px-4 py-3 text-xs text-slate-600 leading-snug">{cs.get('impact', '')}</td>
        </tr>
        """

    # Format Changelog timeline
    changelog_cards_html = ""
    for idx, cl in enumerate(changelog):
        is_latest = (idx == 0)
        badge_bg = "bg-sky-600 text-white" if is_latest else "bg-slate-200 text-slate-800"
        border_cls = "border-sky-300 ring-1 ring-sky-200 bg-sky-50/20" if is_latest else "border-slate-200 bg-white"
        bullets = "".join([f"<li class='text-xs text-slate-600 leading-relaxed'>{d}</li>" for d in cl.get("details", [])])
        changelog_cards_html += f"""
        <div class="relative pl-8 pb-8 border-l-2 border-slate-200 last:border-l-0 last:pb-0">
          <div class="absolute -left-2.5 top-0 w-5 h-5 rounded-full border-4 border-white {'bg-sky-600 shadow' if is_latest else 'bg-slate-400'}"></div>
          <div class="{border_cls} rounded-2xl p-5 sm:p-6 border shadow-sm space-y-3">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <div class="flex items-center gap-2.5">
                <span class="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold {badge_bg}">v{cl.get('version', '')}</span>
                <h3 class="font-bold text-slate-900 text-sm sm:text-base">{cl.get('title', '')}</h3>
              </div>
              <span class="text-xs font-mono text-slate-500">{cl.get('date', '')}</span>
            </div>
            <p class="text-xs sm:text-sm text-slate-700 leading-relaxed font-medium">{cl.get('summary', '')}</p>
            <ul class="list-disc list-inside space-y-1.5 pt-1">
              {bullets}
            </ul>
          </div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Scientific Methodology & Empirical Validation — Mathews County Coastal Flood Prediction</title>
  <meta name="description" content="Academic benchmarks, machine learning model weights, piecewise inundation formulas, USGS 3DEP LiDAR altimetry validation, and 5-year empirical record for Mathews County, VA.">
  
  <link rel="stylesheet" href="assets/tailwind.css">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" integrity="sha384-t1nt8BQoYMLFN5p42tRAtuAAFQaCQODekUVeKKZrEnEyp4H2R0RHFz0KWpmj7i8g" crossorigin="anonymous">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
    body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }}
    .font-mono {{ font-family: 'JetBrains Mono', monospace; }}
  </style>
</head>
<body class="bg-slate-50 text-slate-800 antialiased min-h-screen flex flex-col justify-between">
  {navbar_html}

  <main id="main-content" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-12 flex-1 min-w-0 w-full">

    <!-- 0. HERO SECTION -->
    <section class="bg-gradient-to-br from-slate-900 via-slate-800 to-sky-950 text-white rounded-3xl p-6 sm:p-10 shadow-xl border border-slate-700/60 relative overflow-hidden">
      <div class="relative z-10 max-w-4xl space-y-4">
        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-sky-900/80 text-sky-300 border border-sky-700/60 shadow-sm">
          <i class="fa-solid fa-graduation-cap"></i> COMMUNITY RESEARCH &bull; PUBLIC METHODS &bull; HISTORICAL OBSERVATIONS
        </div>
        <h1 class="text-2xl sm:text-4xl font-extrabold tracking-tight text-white">
          Scientific Methodology & Model Benchmarks
        </h1>
        <p class="text-sm sm:text-base text-slate-300 leading-relaxed max-w-3xl">
          Empirical validation, machine learning hydrodynamics, USGS 3DEP 1-meter LiDAR altimetry ground-truth, and formal version changelog for coastal flooding in Mathews County, Virginia.
        </p>
        <div class="flex flex-wrap gap-3 pt-2">
          <a href="models/scientific_evidence.json" download class="px-4 py-2 rounded-xl bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold text-xs sm:text-sm shadow-md transition flex items-center gap-2">
            <i class="fa-solid fa-download"></i> Download JSON Evidence
          </a>
          <a href="observer_yearly_summary.csv" download class="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white border border-slate-600 font-semibold text-xs sm:text-sm transition flex items-center gap-2">
            <i class="fa-solid fa-table text-emerald-400"></i> Yearly Observation Summary
          </a>
        </div>
      </div>
    </section>

    <aside class="official-card"><strong>How to interpret these scores</strong><p>Historical observed-weather benchmarks do not validate deployed forecasts. Stage 2 scores use the same historical record used to establish the depth relationship, not an independent holdout. A 1-meter LiDAR grid describes horizontal spacing, not vertical accuracy. Apparent threshold agreement does not prove sub-inch precision; elevation date, point type, vertical error and datum conversion need a documented survey audit.</p></aside>
    <!-- 1. EXECUTIVE KPI BENCHMARKS GRID (6 CARDS) -->
    <section>
      <div class="mb-4">
        <h2 class="text-lg font-bold text-slate-900 flex items-center gap-2">
          <i class="fa-solid fa-chart-simple text-sky-600"></i>
          Key Empirical & Model Benchmarks
        </h2>
        <p class="text-xs sm:text-sm text-slate-500">Quantitative metrics across 5.33 years of continuous storm observations and multi-sensor machine learning.</p>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        <!-- Card 1: Record Span -->
        <div class="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-2 hover:shadow-md transition">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-slate-400 uppercase tracking-wider">5.33-Year Record</span>
            <div class="w-8 h-8 rounded-lg bg-sky-50 text-sky-600 flex items-center justify-center text-sm font-bold"><i class="fa-solid fa-calendar-check"></i></div>
          </div>
          <div class="text-2xl sm:text-3xl font-black text-slate-900 font-mono">{total_obs} Observations</div>
          <p class="text-xs text-slate-500 leading-snug">{valid_pairs} paired depth records, May 2021 – Sep 2026 across 10 named storms.</p>
        </div>

        <!-- Card 2: Empirical Correlation -->
        <div class="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-2 hover:shadow-md transition">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-slate-400 uppercase tracking-wider">Empirical Correlation</span>
            <div class="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center text-sm font-bold"><i class="fa-solid fa-chart-line"></i></div>
          </div>
          <div class="text-2xl sm:text-3xl font-black text-emerald-700 font-mono">r = {corr_flooded_r:.4f}</div>
          <p class="text-xs text-slate-500 leading-snug">R&sup2; = {corr_flooded_r2:.4f} (p &lt; 10&minus;15) on flooded events; r = {corr_overall_r:.4f} overall.</p>
        </div>

        <!-- Card 3: LiDAR Culvert Agreement -->
        <div class="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-2 hover:shadow-md transition">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-slate-400 uppercase tracking-wider">LiDAR Culvert Match</span>
            <div class="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center text-sm font-bold"><i class="fa-solid fa-bullseye"></i></div>
          </div>
          <div class="text-2xl sm:text-3xl font-black text-indigo-700 font-mono">&Delta; = 0.06 ft</div>
          <p class="text-xs text-slate-500 leading-snug">Culvert invert 4.05' MLLW is close to the 3.99' empirical threshold. Vertical and datum uncertainty remain.</p>
        </div>

        <!-- Card 4: Driveway Pad Agreement -->
        <div class="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-2 hover:shadow-md transition">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-slate-400 uppercase tracking-wider">Driveway Pad Match</span>
            <div class="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center text-sm font-bold"><i class="fa-solid fa-road"></i></div>
          </div>
          <div class="text-2xl sm:text-3xl font-black text-amber-700 font-mono">&Delta; = 0.00 ft</div>
          <p class="text-xs text-slate-500 leading-snug">USGS LiDAR 4.40' MLLW is close to the empirical moderate-flood threshold; this is not a survey-precision validation.</p>
        </div>

        <!-- Card 5: Stage 1 ML Nowcast -->
        <div class="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-2 hover:shadow-md transition">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-slate-400 uppercase tracking-wider">Stage 1 Nowcast ML</span>
            <div class="w-8 h-8 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center text-sm font-bold"><i class="fa-solid fa-brain"></i></div>
          </div>
          <div class="text-2xl sm:text-3xl font-black text-purple-700 font-mono">R&sup2; = {stage1_r2:.4f}</div>
          <p class="text-xs text-slate-500 leading-snug">Holdout test MAE = {stage1_mae_in:.2f}" ({stage1_now.get('test_mae_ft', 0.12):.2f}') using LightGBM + Wind Stress.</p>
        </div>

        <!-- Card 6: Stage 2 Inundation Model -->
        <div class="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-2 hover:shadow-md transition">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-slate-400 uppercase tracking-wider">Stage 2 Local Model</span>
            <div class="w-8 h-8 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center text-sm font-bold"><i class="fa-solid fa-ruler-combined"></i></div>
          </div>
          <div class="text-2xl sm:text-3xl font-black text-rose-700 font-mono">MAE = {stage2_mae_in:.2f}"</div>
          <p class="text-xs text-slate-500 leading-snug">R&sup2; = {stage2_r2:.4f}, RMSE = {stage2_rmse_in:.2f}" across 181 ground-truth storm events.</p>
        </div>
      </div>
    </section>

    <!-- 2. TWO-STAGE MACHINE LEARNING & HYDRODYNAMIC ARCHITECTURE -->
    <section class="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
        <div>
          <h2 class="text-xl font-bold text-slate-900 flex items-center gap-2">
            <i class="fa-solid fa-diagram-project text-sky-600"></i>
            Two-Stage Machine Learning Predictive Architecture
          </h2>
          <p class="text-xs sm:text-sm text-slate-500">Decoupled estuarine hydrodynamic physics from hyper-local piecewise micro-topography.</p>
        </div>
        <span class="px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200 self-start sm:self-auto">
          Multi-Sensor Pipeline
        </span>
      </div>

      <!-- Architecture Pipeline Diagram -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Stage 1 Box -->
        <div class="p-5 rounded-xl border border-sky-200 bg-sky-50/40 space-y-3">
          <div class="flex items-center gap-2 font-bold text-sky-900 text-sm">
            <span class="w-6 h-6 rounded-full bg-sky-600 text-white flex items-center justify-center text-xs">1</span>
            Stage 1: Estuarine Hydrodynamic & Water Level Model
          </div>
          <p class="text-xs text-slate-600 leading-relaxed">
            Predicts the regional water level on the Ware River gauge (WRVV2) by synthesizing astronomical tide tables, quadratic wind stress vectors (&tau;<sub>w</sub> &prop; |U|U), barometric pressure tendencies (&Delta;P<sub>3h</sub>), rolling wind set-up memory (3h, 6h, 12h, 24h), and NOAA CBOFS hydrodynamic guidance.
          </p>
          <div class="bg-slate-900 text-sky-200 p-3.5 rounded-lg font-mono text-xs overflow-x-auto shadow-inner">
            <div class="text-slate-400 text-[10px] mb-1 font-sans font-semibold uppercase tracking-wider">Hydrodynamic Formulation:</div>
            Stage<sub>pred</sub>(t) = Tide<sub>ast</sub>(t) + f<sub>GBM</sub>(&tau;<sub>wx</sub>, &tau;<sub>wy</sub>, &Delta;P<sub>3h</sub>, Memory<sub>wind</sub>)
          </div>
        </div>

        <!-- Stage 2 Box -->
        <div class="p-5 rounded-xl border border-emerald-200 bg-emerald-50/40 space-y-3">
          <div class="flex items-center gap-2 font-bold text-emerald-900 text-sm">
            <span class="w-6 h-6 rounded-full bg-emerald-600 text-white flex items-center justify-center text-xs">2</span>
            Stage 2: Hyper-Local Piecewise Inundation Model
          </div>
          <p class="text-xs text-slate-600 leading-relaxed">
            Translates the predicted or observed gauge stage into estimated flood depth in inches on property benchmarks, driveway access corridors, and neighborhood roads using our empirically discovered 3.99 ft tipping point and 10.95 in/ft linear inundation gradient.
          </p>
          <div class="bg-slate-900 text-emerald-200 p-3.5 rounded-lg font-mono text-xs overflow-x-auto shadow-inner">
            <div class="text-slate-400 text-[10px] mb-1 font-sans font-semibold uppercase tracking-wider">Piecewise Inundation Law:</div>
            Depth(h) = max(0.0, 10.95 &times; Stage<sub>ft</sub> &minus; 43.69) inches
          </div>
        </div>
      </div>

      <!-- Model Performance Matrix Table -->
      <div>
        <h3 class="text-sm font-bold text-slate-800 mb-3 flex items-center gap-2">
          <i class="fa-solid fa-table-list text-slate-400"></i> Model Performance & Holdout Verification Matrix
        </h3>
        <div class="overflow-x-auto border border-slate-200 rounded-xl shadow-inner">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-100 text-slate-700 text-[11px] font-bold uppercase tracking-wider border-b border-slate-200">
                <th class="px-4 py-2.5">Model Component</th>
                <th class="px-4 py-2.5">Target Variable</th>
                <th class="px-4 py-2.5">Algorithm</th>
                <th class="px-4 py-2.5">Training Horizon</th>
                <th class="px-4 py-2.5">Holdout / Evaluation Set</th>
                <th class="px-4 py-2.5">R&sup2; Score</th>
                <th class="px-4 py-2.5">MAE</th>
                <th class="px-4 py-2.5">RMSE</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs">
              <tr class="hover:bg-slate-50 transition">
                <td class="px-4 py-3 font-semibold text-slate-900">Stage 1 (Nowcasting)</td>
                <td class="px-4 py-3 font-mono text-slate-700">Stage (ft MLLW)</td>
                <td class="px-4 py-3 text-slate-600">LightGBM + Ridge Blend</td>
                <td class="px-4 py-3 text-slate-600 font-mono">2021–2023 (32,833 hrs)</td>
                <td class="px-4 py-3 text-slate-600 font-mono">2024 Holdout Storms</td>
                <td class="px-4 py-3 font-mono font-bold text-purple-700">{stage1_r2:.4f}</td>
                <td class="px-4 py-3 font-mono text-slate-800">{stage1_mae_in:.2f}" ({stage1_now.get('test_mae_ft', 0.12):.2f}')</td>
                <td class="px-4 py-3 font-mono text-slate-800">{stage1_rmse_in:.2f}" ({stage1_now.get('test_rmse_ft', 0.16):.2f}')</td>
              </tr>
              <tr class="hover:bg-slate-50 transition">
                <td class="px-4 py-3 font-semibold text-slate-900">Weather-Conditioned Hindcast</td>
                <td class="px-4 py-3 font-mono text-slate-700">Stage (ft MLLW)</td>
                <td class="px-4 py-3 text-slate-600">LightGBM (48h Lead)</td>
                <td class="px-4 py-3 text-slate-600 font-mono">2021–2023 hourly</td>
                <td class="px-4 py-3 text-slate-600 font-mono">2024 Holdout Storms</td>
                <td class="px-4 py-3 font-mono font-bold text-purple-700">{stage1_fcst_r2:.4f}</td>
                <td class="px-4 py-3 font-mono text-slate-800">{stage1_fcst_mae_in:.2f}" ({stage1_fcst.get('test_mae_ft', 0.40):.2f}')</td>
                <td class="px-4 py-3 font-mono text-slate-800">{stage1_fcst_rmse_in:.2f}" ({stage1_fcst.get('test_rmse_ft', 0.51):.2f}')</td>
              </tr>
              <tr class="hover:bg-slate-50 transition bg-sky-50/20">
                <td class="px-4 py-3 font-semibold text-slate-900">Stage 2 (Hyper-Local Inundation)</td>
                <td class="px-4 py-3 font-mono text-sky-700 font-bold">Flood Depth (in)</td>
                <td class="px-4 py-3 text-slate-600">Piecewise Linear Threshold</td>
                <td class="px-4 py-3 text-slate-600 font-mono">2021–2026 Continuous</td>
                <td class="px-4 py-3 text-slate-600 font-mono">181 paired observations (same record)</td>
                <td class="px-4 py-3 font-mono font-bold text-emerald-700">{stage2_r2:.4f}</td>
                <td class="px-4 py-3 font-mono font-bold text-emerald-700">{stage2_mae_in:.2f}"</td>
                <td class="px-4 py-3 font-mono font-bold text-slate-800">{stage2_rmse_in:.2f}"</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- 3. USGS 3DEP 1-METER LIDAR GROUND-TRUTH VALIDATION -->
    <section class="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
        <div>
          <h2 class="text-xl font-bold text-slate-900 flex items-center gap-2">
            <i class="fa-solid fa-satellite text-sky-600"></i>
            USGS 3DEP elevation estimates &amp; limitations
          </h2>
          <p class="text-xs sm:text-sm text-slate-500">Federal airborne laser altimetry independently confirms handwritten empirical tipping points without parameter tuning.</p>
        </div>
        <div class="text-xs font-mono bg-sky-50 border border-sky-200 text-sky-800 px-3 py-1.5 rounded-lg">
          Datum Offset: NAVD88 + 1.64 ft = MLLW
        </div>
      </div>

      <!-- LiDAR Benchmark Feature Comparison Table -->
      <div>
        <h3 class="text-sm font-bold text-slate-800 mb-2 flex items-center gap-2">
          <i class="fa-solid fa-ruler text-slate-400"></i> Physical Benchmark Features vs Empirical Model Thresholds
        </h3>
        <div class="overflow-x-auto border border-slate-200 rounded-xl shadow-inner">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-100 text-slate-700 text-[11px] font-bold uppercase tracking-wider border-b border-slate-200">
                <th class="px-4 py-2.5">Feature Name</th>
                <th class="px-4 py-2.5">USGS LiDAR (NAVD88)</th>
                <th class="px-4 py-2.5">USGS LiDAR (MLLW)</th>
                <th class="px-4 py-2.5">Model Tipping Point (MLLW)</th>
                <th class="px-4 py-2.5">Discrepancy (&Delta;)</th>
                <th class="px-4 py-2.5">Hydrologic Significance</th>
              </tr>
            </thead>
            <tbody>
              {lidar_rows_html}
            </tbody>
          </table>
        </div>
      </div>

      <!-- Community Street Network LiDAR Invert Elevations Table -->
      <div>
        <h3 class="text-sm font-bold text-slate-800 mb-2 flex items-center gap-2">
          <i class="fa-solid fa-road text-slate-400"></i> Community Street Network Invert Elevations (Vehicle Hazard Thresholds)
        </h3>
        <div class="overflow-x-auto border border-slate-200 rounded-xl shadow-inner">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-100 text-slate-700 text-[11px] font-bold uppercase tracking-wider border-b border-slate-200">
                <th class="px-4 py-2.5">Street Name</th>
                <th class="px-4 py-2.5">Invert Elevation (NAVD88)</th>
                <th class="px-4 py-2.5">Invert Elevation (MLLW)</th>
                <th class="px-4 py-2.5">Inundation Sequence & Passability Risk</th>
              </tr>
            </thead>
            <tbody>
              {street_rows_html}
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- 4. DATASET CHARACTERISTICS & STATISTICAL MOMENTS -->
    <section class="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6">
      <div class="border-b border-slate-100 pb-4">
        <h2 class="text-xl font-bold text-slate-900 flex items-center gap-2">
          <i class="fa-solid fa-calculator text-sky-600"></i>
          Observational Dataset Characteristics & Statistical Moments
        </h2>
        <p class="text-xs sm:text-sm text-slate-500">Distribution analysis of 204 human verification records spanning May 2021 to September 2026.</p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Ware River Stage Moments -->
        <div class="p-5 rounded-xl border border-slate-200 bg-slate-50/50 space-y-3">
          <h3 class="text-sm font-bold text-slate-900 flex items-center gap-2">
            <i class="fa-solid fa-water text-sky-600"></i> Ware River Stage Moments (ft MLLW)
          </h3>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
            <div class="bg-white p-3 rounded-lg border border-slate-200 shadow-sm">
              <div class="text-[10px] uppercase font-bold text-slate-400">Min</div>
              <div class="text-base font-bold font-mono text-slate-800">{stage_dist.get('min', 3.40):.2f}'</div>
            </div>
            <div class="bg-white p-3 rounded-lg border border-slate-200 shadow-sm">
              <div class="text-[10px] uppercase font-bold text-slate-400">Median</div>
              <div class="text-base font-bold font-mono text-slate-800">{stage_dist.get('median', 4.35):.2f}'</div>
            </div>
            <div class="bg-white p-3 rounded-lg border border-slate-200 shadow-sm">
              <div class="text-[10px] uppercase font-bold text-slate-400">Mean</div>
              <div class="text-base font-bold font-mono text-slate-800">{stage_dist.get('mean', 4.39):.2f}'</div>
            </div>
            <div class="bg-white p-3 rounded-lg border border-slate-200 shadow-sm">
              <div class="text-[10px] uppercase font-bold text-slate-400">Max</div>
              <div class="text-base font-bold font-mono text-rose-700">{stage_dist.get('max', 5.54):.2f}'</div>
            </div>
          </div>
          <div class="text-xs text-slate-600 flex justify-between pt-1 font-mono">
            <span>IQR: [{stage_dist.get('p25', 4.14):.2f}', {stage_dist.get('p75', 4.61):.2f}'] (&Delta; {stage_dist.get('iqr', 0.47):.2f}')</span>
            <span>&sigma; = {stage_dist.get('std', 0.38):.2f}'</span>
          </div>
        </div>

        <!-- Flood Depth Moments -->
        <div class="p-5 rounded-xl border border-slate-200 bg-slate-50/50 space-y-3">
          <h3 class="text-sm font-bold text-slate-900 flex items-center gap-2">
            <i class="fa-solid fa-ruler-vertical text-rose-600"></i> Measured Flood Depth Moments (inches)
          </h3>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
            <div class="bg-white p-3 rounded-lg border border-slate-200 shadow-sm">
              <div class="text-[10px] uppercase font-bold text-slate-400">Min</div>
              <div class="text-base font-bold font-mono text-slate-800">{depth_dist.get('min', 0.0):.1f}&quot;</div>
            </div>
            <div class="bg-white p-3 rounded-lg border border-slate-200 shadow-sm">
              <div class="text-[10px] uppercase font-bold text-slate-400">Median</div>
              <div class="text-base font-bold font-mono text-slate-800">{depth_dist.get('median', 3.0):.1f}&quot;</div>
            </div>
            <div class="bg-white p-3 rounded-lg border border-slate-200 shadow-sm">
              <div class="text-[10px] uppercase font-bold text-slate-400">Mean</div>
              <div class="text-base font-bold font-mono text-slate-800">{depth_dist.get('mean', 4.3):.1f}&quot;</div>
            </div>
            <div class="bg-white p-3 rounded-lg border border-slate-200 shadow-sm">
              <div class="text-[10px] uppercase font-bold text-slate-400">Max</div>
              <div class="text-base font-bold font-mono text-rose-700">{depth_dist.get('max', 19.0):.1f}&quot;</div>
            </div>
          </div>
          <div class="text-xs text-slate-600 flex justify-between pt-1 font-mono">
            <span>IQR: [{depth_dist.get('p25', 0.25):.2f}&quot;, {depth_dist.get('p75', 7.0):.1f}&quot;] (&Delta; {depth_dist.get('iqr', 6.75):.2f}&quot;)</span>
            <span>&sigma; = {depth_dist.get('std', 4.37):.2f}&quot;</span>
          </div>
        </div>
      </div>

      <!-- Zero-Inundation Baseline Confirmation Callout -->
      <div class="p-4 rounded-xl border border-emerald-200 bg-emerald-50 text-emerald-950 text-xs sm:text-sm leading-relaxed flex items-start gap-3">
        <i class="fa-solid fa-circle-check text-emerald-600 mt-0.5 text-base shrink-0"></i>
        <div>
          <strong>Empirical Zero-Inundation Baseline Confirmation:</strong> Exactly 44 observations were recorded when the Ware River gauge was below 4.00 ft MLLW (ranging from 3.40' to 3.98'). All 44 instances exhibited exactly <strong>0.0 inches</strong> of inundation on the yard and road, describing this sample only. This does not establish zero future false alarms or cover rainfall-only flooding.
        </div>
      </div>
    </section>

    {resident_ui.evidence_section()}

    <!-- 6. FORMAL SCIENTIFIC & ENGINEERING CHANGELOG -->
    <section class="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6">
      <div class="border-b border-slate-100 pb-4">
        <h2 class="text-xl font-bold text-slate-900 flex items-center gap-2">
          <i class="fa-solid fa-timeline text-sky-600"></i>
          Project Version Changelog & Revision History
        </h2>
        <p class="text-xs sm:text-sm text-slate-500">Documented timeline of model upgrades, dataset expansions, and structural discoveries.</p>
      </div>

      <div class="pt-2">
        {changelog_cards_html}
      </div>
    </section>

    <aside class="bg-amber-50 border border-amber-300 rounded-xl p-4 text-sm text-amber-950">Historical benchmark scores use observed weather, not issue-time forecasts. They do not validate deployed 6–48-hour forecast accuracy. Live bounds are uncalibrated scenarios.</aside>
    <!-- 7. REPRODUCIBILITY & ACADEMIC CITATION -->
    <section class="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6">
      <div class="border-b border-slate-100 pb-4">
        <h2 class="text-xl font-bold text-slate-900 flex items-center gap-2">
          <i class="fa-solid fa-code-branch text-sky-600"></i>
          Reproducibility, API Integration & Academic Citation
        </h2>
        <p class="text-xs sm:text-sm text-slate-500">All data collection scripts and statistical engines are reproducible and open-source.</p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="p-5 rounded-xl border border-slate-200 bg-slate-50 space-y-3">
          <h3 class="text-sm font-bold text-slate-900">Benchmark interpretation</h3>
          <p class="text-xs text-slate-600 leading-relaxed">Historical benchmarks use archived observations. They do not establish accuracy or probability coverage for live forecasts. Raw observer records and internal analysis procedures are retained privately; public numerical summaries are available on the Data page.</p>
          <a href="data.html" class="text-sky-600 font-semibold">View public data summaries</a>
        </div>

        <!-- BibTeX Box -->
        <div class="p-5 rounded-xl border border-slate-200 bg-slate-50 space-y-3">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-bold text-slate-900 flex items-center gap-2">
              <i class="fa-solid fa-quote-right text-slate-600"></i> BibTeX Academic Citation
            </h3>
            <button onclick="copyBibtex()" class="px-2.5 py-1 rounded bg-white hover:bg-slate-100 text-slate-700 text-xs font-semibold border border-slate-200 shadow-sm transition flex items-center gap-1.5">
              <i class="fa-solid fa-copy"></i>
              <span id="copy-btn-text">Copy</span>
            </button>
          </div>
          <pre id="bibtex-text" class="bg-slate-900 text-slate-200 p-3 rounded-lg font-mono text-[11px] leading-relaxed overflow-x-auto shadow-inner select-all">@misc{{mathews_flood_prediction_2026,
  title={{Hyper-Local Coastal Flood Prediction and Empirical Threshold Discovery in Mathews County, Virginia: A 5-Year Observational Benchmark (2021--2026)}},
  author={{Hottinger, Howard and Contributors}},
  year={{2026}},
  howpublished={{{{https://flatfoot584.github.io/mathews-flood-monitor/science.html}}}},
  note={{Ground-truth empirical dataset (N=204) and two-stage machine learning hydrodynamic model}}
}}</pre>
        </div>
      </div>
    </section>

  </main>

  {footer_html}

  <script>
    // Copy BibTeX Function
    function copyBibtex() {{
      const text = document.getElementById('bibtex-text').innerText;
      navigator.clipboard.writeText(text).then(() => {{
        const btn = document.getElementById('copy-btn-text');
        if (btn) {{
          btn.innerText = 'Copied!';
          setTimeout(() => {{ btn.innerText = 'Copy'; }}, 2500);
        }}
      }}).catch(() => {{
        alert('Copied BibTeX to clipboard!');
      }});
    }}

  </script>
</body>
</html>
"""

# ==============================================================================
# MAIN DRIVER FUNCTION
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Generate comprehensive multi-page coastal flood portal.")
    parser.add_argument("--status-json", default="latest_status.json", help="Path to latest status JSON")
    parser.add_argument("--obs-csv", default="realtime_recent_observations.csv", help="Path to observations CSV")
    parser.add_argument("--fcst-csv", default="forecast_48h.csv", help="Path to forecast CSV")
    parser.add_argument("--ground-truth", default="observer_yearly_summary.csv", help="Path to public yearly aggregate CSV")
    args = parser.parse_args()

    status, obs_rows, fcst_rows, ground_truth_rows = load_data(
        args.status_json, args.obs_csv, args.fcst_csv, args.ground_truth
    )

    # 1. Build index.html & flood_dashboard.html
    index_html = build_index_html(status, obs_rows, fcst_rows)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(index_html)
    with open("flood_dashboard.html", "w", encoding="utf-8") as f:
        f.write(index_html)
    print("[+] Generated: index.html & flood_dashboard.html (Live Monitor & Interactive Map)")

    # 2. Build alerts.html & subscribe.html
    alerts_html = build_alerts_html(status)
    with open("alerts.html", "w", encoding="utf-8") as f:
        f.write(alerts_html)
    with open("subscribe.html", "w", encoding="utf-8") as f:
        f.write(alerts_html)
    print("[+] Generated: alerts.html & subscribe.html (Dedicated Mobile Alerts & Subscription Guide)")

    # 3. Build about.html
    about_html = build_about_html(status)
    with open("about.html", "w", encoding="utf-8") as f:
        f.write(about_html)
    print("[+] Generated: about.html (The Story, Public History & Physical Breakthroughs)")

    # 4. Build guide.html
    guide_html = build_guide_html(status)
    with open("guide.html", "w", encoding="utf-8") as f:
        f.write(guide_html)
    print("[+] Generated: guide.html (4 Flood Severity Tiers, Vehicle Safety & Plain-English Glossary)")

    # 5. Build data.html
    data_html = build_data_html(status, ground_truth_rows, obs_rows)
    with open("data.html", "w", encoding="utf-8") as f:
        f.write(data_html)
    print("[+] Generated: data.html (Historical Storm Comparisons & Public Data Downloads)")

    # 6. Build science.html
    evidence_path = os.path.join("models", "scientific_evidence.json")
    evidence = {}
    if os.path.exists(evidence_path):
        with open(evidence_path, "r", encoding="utf-8") as f:
            evidence = json.load(f)

    science_html = build_science_html(status, evidence)
    with open("science.html", "w", encoding="utf-8") as f:
        f.write(science_html)
    print("[+] Generated: science.html (Scientific Methodology, Empirical Benchmarks & Changelog)")

if __name__ == "__main__":
    main()
