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
    status["data_quality"] = quality
    if not quality["current_available"]:
        import micro_topography
        curr = status.setdefault("current_conditions", {})
        unknown = micro_topography.evaluate_compound_inundation(None)
        curr.update(flood_risk_tier=-1, flood_risk_label="Unknown (gauge missing or stale)",
                    vehicle_passability_code="UNKNOWN", vehicle_passability=unknown["vehicle_passability_label"],
                    vehicle_passability_desc=unknown["vehicle_passability_desc"],
                    estimated_local_flood_depth_in=None, site_sectors=unknown["sectors"],
                    community_streets=unknown["streets"])
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
    status = escape_view(status_for_display(status))
    curr = status.get("current_conditions", {})
    tier = curr.get("flood_risk_tier", 0)
    tier_info = TIER_STYLES.get(tier, TIER_STYLES[-1])
    tier_lbl = curr.get("flood_risk_label", "Tier 0 (Normal / Safe)").split("(")[-1].replace(")", "")
    
    pages = [
        {"id": "live", "title": "Live Monitor", "href": "index.html", "icon": "fa-water"},
        {"id": "alerts", "title": "Mobile Alerts", "href": "alerts.html", "icon": "fa-bell"},
        {"id": "map", "title": "Flood Map", "href": "index.html#map-section", "icon": "fa-map-location-dot"},
        {"id": "about", "title": "About & History", "href": "about.html", "icon": "fa-book-open"},
        {"id": "guide", "title": "Flood Guide & Tiers", "href": "guide.html", "icon": "fa-ruler-vertical"},
        {"id": "data", "title": "Storm Archive & Data", "href": "data.html", "icon": "fa-database"},
        {"id": "science", "title": "Science & Methodology", "href": "science.html", "icon": "fa-microscope"}
    ]

    nav_links_html = ""
    mobile_links_html = ""
    for p in pages:
        is_active = (active_page == p["id"])
        active_class = "bg-sky-900/60 text-sky-200 border-b-2 border-sky-400 font-semibold" if is_active else "text-slate-300 hover:text-white hover:bg-slate-800/60"
        mobile_active = "bg-sky-900/50 text-sky-200 font-semibold" if is_active else "text-slate-300 hover:text-white hover:bg-slate-800"
        
        nav_links_html += f"""
        <a href="{p['href']}" class="px-2.5 xl:px-3.5 py-1.5 xl:py-2 text-xs xl:text-sm rounded-lg transition-all flex items-center gap-1.5 {active_class}">
          <i class="fa-solid {p['icon']} text-xs"></i>
          <span>{p['title']}</span>
        </a>
        """
        mobile_links_html += f"""
        <a href="{p['href']}" class="block px-4 py-2.5 rounded-lg text-sm transition {mobile_active}">
          <i class="fa-solid {p['icon']} w-5 text-center mr-2"></i> {p['title']}
        </a>
        """

    last_ts = curr.get("observation_timestamp_local", "Just now")

    return f"""
    <header class="bg-slate-900 text-white border-b border-slate-800 sticky top-0 z-50 shadow-md">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-16">
          <!-- Logo & Brand -->
          <div class="flex items-center gap-3">
            <a href="index.html" class="flex items-center gap-3 group">
              <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-sky-500 to-blue-700 flex items-center justify-center shadow-inner group-hover:scale-105 transition-transform">
                <i class="fa-solid fa-water text-lg text-white"></i>
              </div>
              <div>
                <div class="font-bold text-base sm:text-lg tracking-tight flex items-center gap-2 text-white">
                  Mathews County Flood Monitor
                </div>
                <div class="text-[11px] text-slate-400 font-medium">Middle Peninsula &bull; Mobjack Bay, VA</div>
              </div>
            </a>
          </div>

          <!-- Desktop Navigation -->
          <nav class="hidden lg:flex items-center gap-1">
            {nav_links_html}
          </nav>

          <!-- Status Pill & Mobile Menu Button -->
          <div class="flex items-center gap-3">
            <div class="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full {tier_info['badge_bg']} {tier_info['badge_border']} border text-xs font-semibold {tier_info['badge_text']}">
              <span class="w-2.5 h-2.5 rounded-full {tier_info['pill']} animate-pulse"></span>
              <span>LIVE: {tier_lbl.strip()}</span>
            </div>

            <button id="mobile-menu-btn" class="lg:hidden p-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 focus:outline-none" aria-label="Toggle Navigation">
              <i class="fa-solid fa-bars text-lg"></i>
            </button>
          </div>
        </div>

        <!-- Mobile Menu Dropdown -->
        <div id="mobile-menu" class="hidden lg:hidden border-t border-slate-800 py-3 space-y-1">
          <div class="px-4 py-2 sm:hidden mb-2">
            <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full {tier_info['badge_bg']} {tier_info['badge_border']} border text-xs font-semibold {tier_info['badge_text']}">
              <span class="w-2.5 h-2.5 rounded-full {tier_info['pill']} animate-pulse"></span>
              <span>LIVE STATUS: {tier_lbl.strip()}</span>
            </div>
          </div>
          {mobile_links_html}
        </div>
      </div>
    </header>
    <aside id="data-freshness" role="status" class="bg-amber-50 text-amber-950 border-b border-amber-300 px-4 py-3 text-sm">
      Last update: {status.get('status_generated_at_local', 'Unavailable')}.
      Gauge observation: {curr.get('observation_timestamp_local') or 'Unavailable'}.
      {"Data incomplete or stale. Do not assume roads are clear." if status['data_quality']['state'] != 'healthy' else "Check actual road conditions before travel."}
      {"Mobile push alerts are not enabled." if not status.get('alerting_enabled', False) else ""}
    </aside>
    """

@safe_template
def build_shared_footer(status):
    curr = status.get("current_conditions", {})
    last_ts = status.get("status_generated_at_local", "Unavailable")
    generated_iso = json.dumps(status.get("status_generated_at_utc", "")).replace("<", "\\u003c")
    observed_iso = json.dumps(curr.get("observation_timestamp_local", "")).replace("<", "\\u003c")
    return f"""
    <footer class="bg-slate-900 text-slate-400 text-sm border-t border-slate-800 mt-16 py-12">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid grid-cols-1 md:grid-cols-4 gap-8">
        <!-- Col 1: Project Info -->
        <div class="md:col-span-2 space-y-3">
          <div class="flex items-center gap-2 text-white font-bold text-base">
            <i class="fa-solid fa-water text-sky-400"></i>
            <span>Mathews County Coastal Flood Prediction System</span>
          </div>
          <p class="text-xs text-slate-400 leading-relaxed max-w-lg">
            An open science, hyper-local flood prediction pipeline and machine learning model built from 204 ground-truth storm observations (2021–2026), NOAA NWPS hydrodynamic water level guidance, and NOAA CO-OPS sensor networks across the Middle Peninsula of Virginia.
          </p>
          <div class="text-xs text-slate-500 pt-1">
            Last Automated Cloud Sync: <span class="text-slate-300 font-mono font-medium">{last_ts}</span> (Scheduled every 30 minutes; delays are possible)
          </div>
        </div>

        <!-- Col 2: Navigation Links -->
        <div>
          <h4 class="text-xs font-semibold uppercase tracking-wider text-slate-200 mb-3">Portal Navigation</h4>
          <ul class="space-y-2 text-xs">
            <li><a href="index.html" class="hover:text-sky-400 transition">Live Dashboard & Forecast</a></li>
            <li><a href="alerts.html" class="hover:text-sky-400 transition">Free Mobile Flood Alerts</a></li>
            <li><a href="index.html#map-section" class="hover:text-sky-400 transition">Interactive Coastal Map</a></li>
            <li><a href="about.html" class="hover:text-sky-400 transition">The Story & Handwritten Notes</a></li>
            <li><a href="guide.html" class="hover:text-sky-400 transition">Flood Tiers & Plain-English Guide</a></li>
            <li><a href="data.html" class="hover:text-sky-400 transition">Storm History & Data Archive</a></li>
            <li><a href="science.html" class="hover:text-sky-400 transition">Science, Models & Changelog</a></li>
          </ul>
        </div>

        <!-- Col 3: Sensor Networks & Code -->
        <div>
          <h4 class="text-xs font-semibold uppercase tracking-wider text-slate-200 mb-3">Data & Source Code</h4>
          <ul class="space-y-2 text-xs">
            <li><a href="https://water.noaa.gov/gauges/WRVV2" target="_blank" rel="noopener" class="hover:text-sky-400 transition flex items-center gap-1.5"><i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i> NOAA NWPS Ware River (WRVV2)</a></li>
            <li><a href="https://tidesandcurrents.noaa.gov/stationhome.html?id=8637689" target="_blank" rel="noopener" class="hover:text-sky-400 transition flex items-center gap-1.5"><i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i> NOAA Yorktown USCG (8637689)</a></li>
            <li><a href="https://tidesandcurrents.noaa.gov/stationhome.html?id=8636580" target="_blank" rel="noopener" class="hover:text-sky-400 transition flex items-center gap-1.5"><i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i> NOAA Windmill Point (8636580)</a></li>
            <li><a href="models/scientific_evidence.json" target="_blank" class="hover:text-sky-400 transition flex items-center gap-1.5"><i class="fa-solid fa-code text-[10px]"></i> Scientific Evidence (JSON)</a></li>
            <li><a href="science.html" class="hover:text-sky-400 transition flex items-center gap-1.5"><i class="fa-solid fa-file-lines text-[10px]"></i> Public Methodology</a></li>
            <li><a href="https://github.com/flatfoot584/mathews-flood-monitor" target="_blank" rel="noopener" class="hover:text-sky-400 transition flex items-center gap-1.5"><i class="fa-brands fa-github text-[11px]"></i> GitHub Repository</a></li>
          </ul>
        </div>
      </div>

      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-8 pt-6 border-t border-slate-800/80 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-4">
        <div>&copy; 2021–2026 Mathews County Flood Prediction Project &bull; Public Community Resource</div>
        <div class="italic text-[11px]">Empirical model calibrated to 3.99 ft MLLW flood tipping point. Not an official NWS evacuation order.</div>
      </div>
    </footer>

    <script>
      const generatedText = {generated_iso};
      const observedText = {observed_iso};
      function utcMillis(text) {{
        if (!text) return NaN;
        return Date.parse(text.replace(' UTC', 'Z').replace(' EDT', '-04:00').replace(' EST', '-05:00').replace(' ', 'T'));
      }}
      function updateFreshness() {{
        const stamp = utcMillis(generatedText);
        const observation = utcMillis(observedText);
        const old = !Number.isFinite(stamp) || !Number.isFinite(observation) || Date.now() - stamp > 90*60000 || Date.now() - observation > 90*60000;
        if (old) {{
          const notice = document.getElementById('data-freshness');
          if (notice) notice.textContent = 'DATA STALE OR UNAVAILABLE — Flood safety cannot be confirmed. Last update: ' + generatedText;
          document.querySelectorAll('[data-current-safety]').forEach(el => el.hidden = true);
        }}
      }}
      updateFreshness();
      setInterval(updateFreshness, 60000);
      // Mobile menu toggle
      const menuBtn = document.getElementById('mobile-menu-btn');
      const mobileMenu = document.getElementById('mobile-menu');
      if (menuBtn && mobileMenu) {{
        menuBtn.addEventListener('click', () => {{
          mobileMenu.classList.toggle('hidden');
        }});
      }}
    </script>
    """

# ==============================================================================
# 1. PAGE 1: INDEX.HTML (LIVE MONITOR & INTERACTIVE MAP)
# ==============================================================================
@safe_template
def build_index_html(status, obs_rows, fcst_rows):
    curr = status.get("current_conditions", {})
    outl = status.get("forecast_48h_outlook", {})

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
          <div class="p-3 rounded-xl border border-slate-200 bg-slate-50/60 hover:bg-slate-50 transition">
            <div class="flex items-center justify-between mb-1.5">
              <span class="font-bold text-xs text-slate-900">{st_name}</span>
              <span class="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full border {badge_cls}">
                <span class="w-1.5 h-1.5 rounded-full {dot_cls}"></span>
                {st_info.get("status", "Dry")}
              </span>
            </div>
            <div class="flex items-baseline justify-between text-xs text-slate-500 font-mono">
              <span class="text-[11px]">Invert: {st_inv_mllw}' MLLW ({st_inv_navd}' NAVD)</span>
              <span class="font-bold text-slate-800 font-mono">{st_depth}" Water</span>
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
        headline = "Normal Conditions — Driveways & Roads Clear"
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

    # Embed data for charts and Leaflet
    embedded_data_json = json.dumps({
        "status": status,
        "observations": obs_rows[-36:] if obs_rows else [],
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
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha384-sHL9NAb7lN7rfvG5lfHpm643Xkcjzp4jFvuavGOndn6pjVqS6ny56CAt3nsEVT4H" crossorigin="anonymous" />
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

  <main class="flex-grow max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-8 w-full">

    <!-- 1. HUMAN-FIRST ADVISORY HERO BANNER -->
    <section data-current-safety class="rounded-2xl {peak_tier_info['banner_bg']} border-2 {peak_tier_info['banner_border']} p-6 sm:p-8 shadow-sm transition-all">
      <div class="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
        <div class="space-y-2 max-w-3xl">
          <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full {peak_tier_info['badge_bg']} text-xs font-bold {peak_tier_info['badge_text']} uppercase tracking-wider">
            <i class="fa-solid {peak_tier_info['icon']}"></i>
            <span>Current Status &bull; {curr.get('flood_risk_label', 'Normal')}</span>
          </div>
          <h1 class="text-2xl sm:text-3xl lg:text-4xl font-extrabold {peak_tier_info['banner_text']} tracking-tight leading-tight">
            {headline}
          </h1>
          <p class="text-base {peak_tier_info['banner_sub']} leading-relaxed">
            {sub_headline}
          </p>
        </div>

        <!-- Quick Metrics Box -->
        <div class="flex flex-wrap lg:flex-col gap-3 bg-white/80 backdrop-blur-sm p-4 rounded-xl border border-slate-200/80 shadow-sm min-w-[250px]">
          <div>
            <div class="text-[11px] font-semibold text-slate-500 uppercase">Current Ware River Stage</div>
            <div class="text-2xl font-black text-slate-900 font-mono">{stage} <span class="text-sm font-semibold text-slate-500">ft MLLW</span></div>
            <div class="text-[11px] text-slate-500 font-medium">({stage_navd} ft NAVD88)</div>
          </div>
          <div class="pt-2 border-t border-slate-200">
            <div class="text-[11px] font-semibold text-slate-500 uppercase">48-Hour Peak Forecast</div>
            <div class="text-lg font-extrabold text-sky-900 font-mono">{peak_stage} ft <span class="text-xs font-normal text-slate-500">at {peak_time.split(' ')[1] if ' ' in str(peak_time) else peak_time}</span></div>
            <div class="text-xs font-semibold {peak_tier_info['badge_text']}">Inundation: {peak_depth}" ({peak_passability})</div>
            <div class="text-[11px] font-mono text-slate-500 mt-1 flex items-center justify-between">
              <span>Scenario range:</span>
              <span class="font-bold text-slate-700">{peak_stage_q10}' – {peak_stage_q90}'</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 2. VEHICLE PASSABILITY & HUMAN ACTION STRIP -->
    <section data-current-safety class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <!-- Card 1: Sedans -->
      <div class="bg-white rounded-xl p-5 border border-slate-200 shadow-sm flex items-start gap-4">
        <div class="w-12 h-12 rounded-xl {'bg-emerald-100 text-emerald-700' if route_dry else 'bg-red-100 text-red-700'} flex items-center justify-center text-xl shrink-0">
          <i class="fa-solid fa-car-side"></i>
        </div>
        <div>
          <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Passenger Cars / Sedans</div>
          <div class="text-base font-bold text-slate-900 mt-0.5">
            {route_title}
          </div>
          <p class="text-xs text-slate-600 mt-1">
            {route_description}
          </p>
        </div>
      </div>

      <!-- Card 2: SUVs & Trucks -->
      <div class="bg-white rounded-xl p-5 border border-slate-200 shadow-sm flex items-start gap-4">
        <div class="w-12 h-12 rounded-xl {'bg-emerald-100 text-emerald-700' if route_dry else 'bg-amber-100 text-amber-700'} flex items-center justify-center text-xl shrink-0">
          <i class="fa-solid fa-truck-pickup"></i>
        </div>
        <div>
          <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider">SUVs & High-Clearance Trucks</div>
          <div class="text-base font-bold text-slate-900 mt-0.5">
            {route_title}
          </div>
          <p class="text-xs text-slate-600 mt-1">
            {route_description}
          </p>
        </div>
      </div>

      <!-- Card 3: Action Checklist -->
      <div class="bg-white rounded-xl p-5 border border-slate-200 shadow-sm flex items-start gap-4">
        <div class="w-12 h-12 rounded-xl bg-sky-100 text-sky-700 flex items-center justify-center text-xl shrink-0">
          <i class="fa-solid fa-clipboard-check"></i>
        </div>
        <div>
          <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Recommended Action</div>
          <div class="text-base font-bold text-slate-900 mt-0.5">
            {'Check Actual Conditions' if route_unknown else 'Plan Around Flood Hazards' if route_flooded else 'Monitor Updates'}
          </div>
          <p class="text-xs text-slate-600 mt-1">
            {'Do not assume roads are clear when data is missing.' if route_unknown else 'Move vehicles before flooding starts; do not enter floodwater.'}
          </p>
        </div>
      </div>
    </section>

    <!-- 3. INTERACTIVE LEAFLET FLOOD MAP SECTION -->
    <section data-current-safety id="map-section" class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      <div class="p-5 sm:p-6 border-b border-slate-200 flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-slate-50/50">
        <div>
          <div class="flex items-center gap-2">
            <h2 class="text-lg sm:text-xl font-bold text-slate-900">Blackwater &amp; Mobjack Bay Estates Real-Time Flood Map</h2>
            <span class="px-2.5 py-0.5 text-xs font-semibold bg-amber-100 text-amber-900 rounded-full font-mono">Community Monitoring Zone</span>
          </div>
          <p class="text-xs sm:text-sm text-slate-500 mt-0.5">
            Hyper-local elevation monitoring enclosing <strong>Daniel Ave, Bayshore Ave, River Rd, and connecting neighborhood streets</strong>, calibrated to USGS 1-meter LiDAR on dry land.
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
            <span class="text-slate-700 font-medium">Safe / Dry (&lt; 4.0')</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-3.5 h-3.5 rounded bg-amber-500 shrink-0"></span>
            <span class="text-slate-700 font-medium">Nuisance / Puddles (4.0-4.3')</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-3.5 h-3.5 rounded bg-orange-500 shrink-0"></span>
            <span class="text-slate-700 font-medium">Roads Flooded (4.4-4.7')</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-3.5 h-3.5 rounded bg-red-600 shrink-0"></span>
            <span class="text-slate-700 font-medium">Severe / Impassable (&ge; 4.8')</span>
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

    <!-- 4. COMMUNITY ELEVATION PROFILE & STREET PASSABILITY -->
    <section class="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-6">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h2 class="text-lg font-bold text-slate-900 flex items-center gap-2">
            <i class="fa-solid fa-stairs text-sky-600"></i>
            Community Elevation Profile &amp; Street Passability
          </h2>
          <p class="text-xs sm:text-sm text-slate-500">
            Micro-topographical water encroachment across Mobjack Bay Estates &amp; Blackwater Peninsula (Threshold: 3.99 ft MLLW = 2.35 ft NAVD88).
          </p>
        </div>
        <div class="text-xs font-mono bg-slate-100 text-slate-700 px-3 py-1.5 rounded-lg self-start sm:self-auto font-medium">
          Ditch Tipping Point: 3.99' MLLW
        </div>
      </div>

      <!-- Sector Progress Bars -->
      <div class="space-y-3.5 pt-1">
        <!-- Sector 1: Ditches -->
        <div>
          <div class="flex justify-between text-xs font-medium mb-1">
            <span class="text-slate-700 font-semibold"><i class="fa-solid fa-water text-sky-500 mr-1.5"></i> 1. Bayshore Waterfront Ditches &amp; Swales (Elev: 3.99' MLLW / 2.35' NAVD88)</span>
            <span class="font-mono font-semibold {'text-sky-700' if (sectors.get('ditches', {}).get('depth_in', 0) or 0) > 0 else 'text-slate-400'}">
              {sectors.get('ditches', {}).get('depth_in', 0) if sectors.get('ditches', {}).get('depth_in', 0) is not None else 'Unknown'}" Water ({sectors.get('ditches', {}).get('status', 'DRY')})
            </span>
          </div>
          <div class="w-full bg-slate-100 h-3 rounded-full overflow-hidden">
            <div class="bg-sky-500 h-full rounded-full transition-all" style="width: {min(100, max(2, int((sectors.get('ditches', {}).get('depth_in', 0) or 0) * 15)))}%"></div>
          </div>
        </div>

        <!-- Sector 2: Road Apron / Culvert -->
        <div>
          <div class="flex justify-between text-xs font-medium mb-1">
            <span class="text-slate-700 font-semibold"><i class="fa-solid fa-road text-amber-500 mr-1.5"></i> 2. Lower Residential Blocks — Allview / Hobday / Little Ave South (Elev: 4.15' MLLW / 2.51' NAVD88)</span>
            <span class="font-mono font-semibold {'text-amber-700' if (sectors.get('road_apron', {}).get('depth_in', 0) or 0) > 0 else 'text-emerald-700'}">
              {sectors.get('road_apron', {}).get('depth_in', 0) if sectors.get('road_apron', {}).get('depth_in', 0) is not None else 'Unknown'}" Water ({sectors.get('road_apron', {}).get('status', 'DRY')})
            </span>
          </div>
          <div class="w-full bg-slate-100 h-3 rounded-full overflow-hidden">
            <div class="{'bg-amber-500' if (sectors.get('road_apron', {}).get('depth_in', 0) or 0) > 0 else 'bg-emerald-500'} h-full rounded-full transition-all" style="width: {min(100, max(2, int((sectors.get('road_apron', {}).get('depth_in', 0) or 0) * 15)))}%"></div>
          </div>
        </div>

        <!-- Sector 3: Main Driveway -->
        <div>
          <div class="flex justify-between text-xs font-medium mb-1">
            <span class="text-slate-700 font-semibold"><i class="fa-solid fa-car text-orange-500 mr-1.5"></i> 3. Daniel Ave Central Spine &amp; Julian St — Primary Route (Elev: 4.40' MLLW / 2.76' NAVD88)</span>
            <span class="font-mono font-semibold {'text-orange-700 font-bold' if (sectors.get('main_driveway', {}).get('depth_in', 0) or 0) > 0 else 'text-emerald-700 font-bold'}">
              {sectors.get('main_driveway', {}).get('depth_in', 0) if sectors.get('main_driveway', {}).get('depth_in', 0) is not None else 'Unknown'}" Water ({sectors.get('main_driveway', {}).get('status', 'DRY')})
            </span>
          </div>
          <div class="w-full bg-slate-100 h-3 rounded-full overflow-hidden">
            <div class="{'bg-orange-500' if (sectors.get('main_driveway', {}).get('depth_in', 0) or 0) > 0 else 'bg-emerald-500'} h-full rounded-full transition-all" style="width: {min(100, max(2, int((sectors.get('main_driveway', {}).get('depth_in', 0) or 0) * 15)))}%"></div>
          </div>
        </div>

        <!-- Sector 4: Residential Lawn -->
        <div>
          <div class="flex justify-between text-xs font-medium mb-1">
            <span class="text-slate-700 font-semibold"><i class="fa-solid fa-tree text-emerald-600 mr-1.5"></i> 4. Upper Residential Grounds &amp; Northern Lots (Elev: 4.60' MLLW / 2.96' NAVD88)</span>
            <span class="font-mono font-semibold {'text-red-700 font-bold' if (sectors.get('yard_lawn', {}).get('depth_in', 0) or 0) > 0 else 'text-emerald-700'}">
              {sectors.get('yard_lawn', {}).get('depth_in', 0) if sectors.get('yard_lawn', {}).get('depth_in', 0) is not None else 'Unknown'}" Water ({sectors.get('yard_lawn', {}).get('status', 'DRY')})
            </span>
          </div>
          <div class="w-full bg-slate-100 h-3 rounded-full overflow-hidden">
            <div class="{'bg-red-500' if (sectors.get('yard_lawn', {}).get('depth_in', 0) or 0) > 0 else 'bg-emerald-500'} h-full rounded-full transition-all" style="width: {min(100, max(2, int((sectors.get('yard_lawn', {}).get('depth_in', 0) or 0) * 15)))}%"></div>
          </div>
        </div>

        <!-- Sector 5: Garage High Ground -->
        <div>
          <div class="flex justify-between text-xs font-medium mb-1">
            <span class="text-slate-700 font-semibold"><i class="fa-solid fa-house text-blue-600 mr-1.5"></i> 5. River Road North &amp; Ridge High Ground Pads (Elev: 4.90' MLLW / 3.26' NAVD88)</span>
            <span class="font-mono font-semibold {'text-red-700 font-bold' if (sectors.get('garage_foundation', {}).get('depth_in', 0) or 0) > 0 else 'text-emerald-700'}">
              {sectors.get('garage_foundation', {}).get('depth_in', 0) if sectors.get('garage_foundation', {}).get('depth_in', 0) is not None else 'Unknown'}" Water ({sectors.get('garage_foundation', {}).get('status', 'SAFE')})
            </span>
          </div>
          <div class="w-full bg-slate-100 h-3 rounded-full overflow-hidden">
            <div class="{'bg-red-600' if (sectors.get('garage_foundation', {}).get('depth_in', 0) or 0) > 0 else 'bg-emerald-500'} h-full rounded-full transition-all" style="width: {min(100, max(2, int((sectors.get('garage_foundation', {}).get('depth_in', 0) or 0) * 15)))}%"></div>
          </div>
        </div>
      </div>

      <!-- Community Street Passability Board -->
      <div class="pt-5 border-t border-slate-200">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-sm font-bold text-slate-900 flex items-center gap-1.5">
            <i class="fa-solid fa-route text-sky-600"></i>
            Community Street Passability &amp; LiDAR Invert Elevations
          </h3>
          <span class="text-xs text-slate-500">Mobjack Bay Estates &amp; Blackwater Road Network</span>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {street_cards_html}
        </div>
      </div>
    </section>

    <!-- 5. 48-HOUR HYDROGRAPH & ENVIRONMENTAL DRIVERS -->
    <section class="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 class="text-lg font-bold text-slate-900 flex items-center gap-2">
            <i class="fa-solid fa-chart-line text-sky-600"></i>
            48-Hour Hybrid Forecast Hydrograph
          </h2>
          <p class="text-xs sm:text-sm text-slate-500">
            NOAA NWPS CBOFS hydrodynamic water model blended with local wind stress ML bias correction, bay hydraulic slope, and quantile regression uncertainty.
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-3 text-xs">
          <span class="flex items-center gap-1.5"><span class="w-3 h-0.5 bg-sky-600"></span> Expected Stage</span>
          <span class="flex items-center gap-1.5"><span class="w-3.5 h-2 bg-sky-200/80 border border-sky-400 border-dashed rounded-[2px]"></span> Uncalibrated Scenario Band</span>
          <span class="flex items-center gap-1.5"><span class="w-3 h-0.5 bg-red-500 border-t border-dashed"></span> 3.99' Flood Threshold</span>
        </div>
      </div>

      <div class="h-80 w-full relative">
        <canvas id="hydrographChart"></canvas>
      </div>

      <div class="text-[11px] text-slate-500 flex flex-wrap items-center justify-between pt-2 border-t border-slate-100 gap-2">
        <span class="flex items-center gap-1.5"><i class="fa-solid fa-circle-info text-sky-500"></i> Shaded band is an uncalibrated scenario range. It is not a statistical confidence interval or a guaranteed worst case.</span>
        <span class="font-mono text-slate-700 font-medium">Expected Peak: {peak_stage}' (Scenario range: {peak_stage_q10}' to {peak_stage_q90}')</span>
      </div>
    </section>

    <!-- 6. REAL-TIME SENSOR NETWORK & BAY HYDRAULIC GRADIENT -->
    <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3.5">
      <!-- Card 1: Yorktown Winds -->
      <div class="bg-white p-4 sm:p-5 rounded-xl border border-slate-200 shadow-sm space-y-1.5">
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
      <div class="bg-white p-4 sm:p-5 rounded-xl border border-slate-200 shadow-sm space-y-1.5">
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
      <div class="bg-white p-4 sm:p-5 rounded-xl border border-slate-200 shadow-sm space-y-1.5">
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
      <div class="bg-white p-4 sm:p-5 rounded-xl border border-slate-200 shadow-sm space-y-1.5">
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
      <div class="bg-white p-4 sm:p-5 rounded-xl border border-slate-200 shadow-sm space-y-1.5">
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
      <div class="bg-white p-4 sm:p-5 rounded-xl border border-slate-200 shadow-sm space-y-1.5">
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
    </section>

    <!-- 7. REAL-TIME MOBILE FLOOD ALERTS CALLOUT -->
    <section id="alerts-section" class="bg-gradient-to-r from-slate-900 via-slate-800 to-sky-950 rounded-2xl text-white p-6 sm:p-7 border border-sky-800/50 shadow-md flex flex-col md:flex-row items-center justify-between gap-6">
      <div class="flex items-start sm:items-center gap-4">
        <div class="w-12 h-12 rounded-xl bg-sky-500/20 text-sky-400 border border-sky-500/30 flex items-center justify-center text-xl shrink-0 shadow-inner">
          <i class="fa-solid fa-bell"></i>
        </div>
        <div class="space-y-1">
          <div class="flex flex-wrap items-center gap-2">
            <h3 class="font-bold text-base sm:text-lg text-white">Get Audible Flood Warnings on Your Phone</h3>
            <span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-400/20 text-amber-300 border border-amber-400/30">100% Free Forever</span>
            <span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-sky-500/20 text-sky-300 border border-sky-500/30">Zero Accounts</span>
          </div>
          <p class="text-xs sm:text-sm text-slate-300 max-w-2xl leading-relaxed">
            Never get caught off guard by saltwater over Daniel Ave or Bayshore Ave. Push notifications sent <strong>when fresh forecasts first indicate a flood hazard</strong>. Public subscriptions; authenticated publishing.
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

    // 2. Community Micro-Topography Land Elevation Zones (100% on Dry Land — Zero in Water)
    const communityZones = [
      {{
        name: "Bayshore Waterfront Ditches & Shoreline Swales",
        elev: 3.99,
        desc: "Lowest swales and roadside ditch culverts along Bayshore Ave. First to overflow at 3.99 ft.",
        coords: [
          [37.4184, -76.4111], [37.4184, -76.4092], [37.4185, -76.4073],
          [37.4186, -76.4054], [37.4186, -76.4047], [37.4187, -76.4038],
          [37.418608, -76.403204], [37.418547, -76.404976], [37.418421, -76.405516],
          [37.418280, -76.406629], [37.418290, -76.407025], [37.418132, -76.408074],
          [37.418147, -76.409089], [37.418186, -76.409639], [37.417983, -76.410625],
          [37.418111, -76.411128]
        ]
      }},
      {{
        name: "Lower Residential Blocks (Allview / Hobday / Little Ave South)",
        elev: 4.15,
        desc: "Southern residential parcels and lower cross street dips (1 to 4 inches standing water).",
        coords: [
          [37.4194, -76.4111], [37.4194, -76.4068], [37.4186, -76.4054],
          [37.4185, -76.4073], [37.4184, -76.4092], [37.4184, -76.4111]
        ]
      }},
      {{
        name: "Daniel Ave Central Spine & Julian St (Benchmark Corridor)",
        elev: 4.40,
        desc: "Primary community artery & Observation Benchmark. Sedans blocked when water exceeds 4 inches.",
        coords: [
          [37.4206, -76.4116], [37.4206, -76.4068], [37.4201, -76.4050],
          [37.4194, -76.4045], [37.4194, -76.4068], [37.4194, -76.4116]
        ]
      }},
      {{
        name: "Upper Residential Grounds & Northern Lots",
        elev: 4.60,
        desc: "Elevated residential lawns and northern lots along Daniel Ave. Trucks and SUVs required.",
        coords: [
          [37.4223, -76.4116], [37.4223, -76.4075], [37.4206, -76.4075],
          [37.4206, -76.4116]
        ]
      }},
      {{
        name: "River Road North & Ridge High Ground Pads",
        elev: 4.90,
        desc: "Elevated building footprint and highest ground along River Road. Impassable only in severe storms.",
        coords: [
          [37.4222, -76.4075], [37.4222, -76.4070], [37.422058, -76.406547],
          [37.421872, -76.406392], [37.421717, -76.406211], [37.421448, -76.406030],
          [37.421186, -76.406132], [37.420658, -76.405830], [37.4206, -76.4068],
          [37.4206, -76.4075]
        ]
      }}
    ];

    // 3. Community Street Network Centerlines (Loaded directly from OSM)
    const communityStreetData = {{
      "Bayshore Avenue": {{
        elev: 3.75,
        desc: "Waterfront road. West & east dips flood first.",
        coords: [
          [37.418612, -76.405419], [37.41858, -76.405771], [37.418556, -76.406277],
          [37.418525, -76.406948], [37.41852, -76.406995], [37.418469, -76.407802],
          [37.418451, -76.408076], [37.418417, -76.408605], [37.418403, -76.409227]
        ]
      }},
      "Daniel Avenue": {{
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
      "Julian Street": {{
        elev: 3.78,
        desc: "Connecting street between Daniel Ave and Bayshore Ave.",
        coords: [
          [37.420307, -76.407368], [37.419501, -76.407203], [37.419026, -76.407095],
          [37.41852, -76.406995]
        ]
      }},
      "Allview Street": {{
        elev: 4.13,
        desc: "Western interior cross street.",
        coords: [
          [37.418403, -76.409227], [37.418605, -76.409328], [37.419033, -76.409405],
          [37.419515, -76.409495], [37.420186, -76.409627]
        ]
      }},
      "River Road": {{
        elev: 4.14,
        desc: "Northern shoreline access road.",
        coords: [
          [37.420375, -76.406297], [37.420803, -76.406602], [37.421278, -76.406765],
          [37.421438, -76.406817], [37.421918, -76.407001], [37.421975, -76.407028]
        ]
      }},
      "Hobday Street": {{
        elev: 4.22,
        desc: "Interior cross street between Daniel Ave & Bayshore Ave.",
        coords: [
          [37.42026, -76.408129], [37.419952, -76.408083], [37.4194, -76.407984],
          [37.418841, -76.407868], [37.418469, -76.407802]
        ]
      }},
      "Little Avenue": {{
        elev: 4.23,
        desc: "Interior cross street rising towards Daniel Ave.",
        coords: [
          [37.420215, -76.408918], [37.419698, -76.408835], [37.419093, -76.408721],
          [37.418767, -76.40865], [37.418417, -76.408605]
        ]
      }},
      "Bunny Rabbit Lane": {{
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

      // 2. Render Street Corridors
      for (const [stName, stData] of Object.entries(communityStreetData)) {{
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

        if (streetAssessment && streetAssessment[stName]) {{
          const assessment = streetAssessment[stName];
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
              <i class="fa-solid fa-road text-slate-500"></i> ${{stName}}
            </div>
            <div class="text-xs text-slate-600">${{stData.desc}}</div>
            <div class="text-xs font-mono text-slate-500">Street Invert: ${{stData.elev}}' MLLW (${{(stData.elev - 1.64).toFixed(2)}}' NAVD88)</div>
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
      const peakRow = (floodData.status.forecast_hourly_timeline || []).find(row => row.timestamp_local === outl.peak_hazard_time_local);
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
        map.flyTo([37.385, -76.435], 11, {{ duration: 1.2 }});
      }});
    }}

    // 2. CHART.JS 48-HOUR HYDROGRAPH WITH QUANTILE CONFIDENCE ENVELOPE
    const ctx = document.getElementById('hydrographChart').getContext('2d');
    const labels = fcst.map(r => {{
      const d = r.timestamp_local || '';
      return d.split(' ')[1] ? d.split(' ')[1].slice(0,5) : d;
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
            label: 'Worst Case (90% Upper)',
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
    curr = status.get("current_conditions", {})
    outl = status.get("forecast_48h_outlook", {})

    stage = display_value(curr.get("ware_river_stage_mllw_ft", "N/A"))
    stage_navd = display_value(curr.get("ware_river_stage_navd88_ft", "N/A"))
    tier = curr.get("flood_risk_tier", 0)
    tier_info = TIER_STYLES.get(tier, TIER_STYLES[-1])
    tier_lbl = curr.get("flood_risk_label", "Tier 0 (Normal / Safe)")

    peak_stage = display_value(outl.get("peak_forecast_stage_mllw_ft", "N/A"))
    peak_time = display_value(outl.get("peak_forecast_stage_time_local", "N/A"))
    peak_depth = display_value(outl.get("peak_estimated_flood_depth_in", 0.0))
    peak_tier = outl.get("peak_risk_tier", 0)
    peak_tier_info = TIER_STYLES.get(peak_tier, TIER_STYLES[-1])
    peak_tier_lbl = outl.get("peak_risk_label", "Tier 0 (Normal / Safe)")
    passability = curr.get("vehicle_passability", "ALL VEHICLES PASSABLE")

    navbar_html = build_shared_navbar("alerts", status)
    footer_html = build_shared_footer(status)

    return f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Free Mobile Flood Alerts — Mathews County, VA</title>
  <meta name="description" content="Subscribe to instant audible flood alerts and push notifications for Mathews County, VA when fresh data indicates flood risk. Delivery timing depends on updates and mobile connectivity.">

  <!-- Tailwind CSS & FontAwesome -->
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

  <main class="flex-grow max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-12 w-full">

    <!-- HERO HEADER -->
    <section class="space-y-4 text-center sm:text-left">
      <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-400/20 text-amber-800 border border-amber-400/30 text-xs font-bold uppercase tracking-wider">
        <i class="fa-solid fa-bell animate-bounce text-amber-600"></i>
        <span>Instant Mobile Alerts &bull; 100% Free Forever &bull; Zero Accounts</span>
      </div>

      <h1 class="text-3xl sm:text-4xl lg:text-5xl font-black text-slate-900 tracking-tight leading-tight">
        Get Audible Flood Warnings on Your Phone Before High Tide
      </h1>

      <p class="text-base sm:text-lg text-slate-600 leading-relaxed max-w-3xl">
        Never get caught off guard by saltwater over Daniel Ave, Bayshore Ave, or neighborhood access roads. Receive loud, high-priority push notifications directly to your smartphone <strong>when fresh forecasts first indicate a flood hazard</strong>.
      </p>

      <!-- Key Guarantees Badges -->
      <div class="flex flex-wrap items-center justify-center sm:justify-start gap-3 pt-2">
        <div class="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-white border border-slate-200 text-xs font-semibold text-slate-700 shadow-sm">
          <i class="fa-solid fa-shield-halved text-emerald-600"></i>
          <span>100% Free &amp; Open Source</span>
        </div>
        <div class="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-white border border-slate-200 text-xs font-semibold text-slate-700 shadow-sm">
          <i class="fa-solid fa-user-shield text-sky-600"></i>
          <span>No Email, Password, or Sign-Up</span>
        </div>
        <div class="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-white border border-slate-200 text-xs font-semibold text-slate-700 shadow-sm">
          <i class="fa-solid fa-bell-slash text-indigo-600"></i>
          <span>Flood alerts with duplicate suppression</span>
        </div>
      </div>
    </section>

    <!-- 1. PRIMARY SUBSCRIPTION HERO BLOCK (ACTION + QR CODE) -->
    <section class="bg-gradient-to-br from-slate-900 via-slate-800 to-sky-950 rounded-3xl text-white p-6 sm:p-10 border border-sky-800/50 shadow-2xl relative overflow-hidden">
      <div class="absolute -right-16 -bottom-16 w-80 h-80 bg-sky-500/10 rounded-full blur-3xl pointer-events-none"></div>

      <div class="relative z-10 grid grid-cols-1 lg:grid-cols-3 gap-8 items-center">
        <!-- Left 2 Cols: Setup Buttons & Live State -->
        <div class="lg:col-span-2 space-y-6">
          <div class="space-y-2">
            <div class="text-xs font-bold uppercase tracking-wider text-sky-400 flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>1-Click Subscription Channel</span>
            </div>
            <h2 class="text-2xl sm:text-3xl font-extrabold text-white leading-tight">
              Subscribe to Channel: <span class="font-mono text-amber-300">{DEFAULT_NTFY_TOPIC}</span>
            </h2>
            <p class="text-sm sm:text-base text-slate-300 leading-relaxed">
              Powered by <strong>ntfy.sh</strong>, a lightweight open-source push notification system. You can subscribe with a single tap in your web browser, or via the free mobile app for iPhone and Android.
            </p>
          </div>

          <!-- Action Buttons -->
          <div class="flex flex-wrap items-center gap-3">
            <a href="{NTFY_SERVER}/{DEFAULT_NTFY_TOPIC}" target="_blank" rel="noopener noreferrer"
               class="px-6 py-3 rounded-xl bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold text-sm sm:text-base shadow-lg transition flex items-center gap-2.5 group">
              <i class="fa-solid fa-mobile-screen-button"></i>
              <span>Subscribe on Phone / Browser</span>
              <i class="fa-solid fa-arrow-up-right-from-square text-xs opacity-75 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform"></i>
            </a>

            <button onclick="copyTopic()" 
                    class="px-5 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold text-sm transition flex items-center gap-2">
              <i class="fa-solid fa-copy text-amber-400"></i>
              <span>Copy Topic: <span class="font-mono text-amber-300">{DEFAULT_NTFY_TOPIC}</span></span>
            </button>
          </div>

          <!-- Copy Toast Feedback -->
          <div id="copy-feedback" class="hidden text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
            <i class="fa-solid fa-circle-check"></i>
            <span>Topic name copied to clipboard! Paste it into the ntfy app.</span>
          </div>

          <!-- App Store Quick Links -->
          <div class="pt-2 flex flex-wrap items-center gap-4 text-xs text-slate-300">
            <span class="text-slate-400 font-medium">Free app downloads:</span>
            <a href="https://apps.apple.com/app/ntfy/id1625396347" target="_blank" rel="noopener noreferrer" class="hover:text-white transition flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700">
              <i class="fa-brands fa-apple text-sm text-slate-200"></i> Apple App Store
            </a>
            <a href="https://play.google.com/store/apps/details?id=io.heckel.ntfy" target="_blank" rel="noopener noreferrer" class="hover:text-white transition flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700">
              <i class="fa-brands fa-google-play text-sm text-emerald-400"></i> Google Play
            </a>
            <a href="{NTFY_SERVER}/{DEFAULT_NTFY_TOPIC}" target="_blank" rel="noopener noreferrer" class="hover:text-white transition flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700">
              <i class="fa-solid fa-globe text-sm text-sky-400"></i> Web Browser
            </a>
          </div>

          <!-- Live Alert Engine Status Pill -->
          <div class="bg-slate-800/60 border border-slate-700/80 rounded-2xl p-4 grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
            <div>
              <div class="text-slate-400 text-[11px] uppercase">Current River Stage</div>
              <div class="text-base font-extrabold text-white font-mono mt-0.5">{stage} ft MLLW</div>
            </div>
            <div>
              <div class="text-slate-400 text-[11px] uppercase">Peak 48h Forecast</div>
              <div class="text-base font-extrabold text-sky-300 font-mono mt-0.5">{peak_stage} ft</div>
            </div>
            <div class="col-span-2 sm:col-span-1">
              <div class="text-slate-400 text-[11px] uppercase">Alert Dispatch Status</div>
              <div class="text-base font-extrabold text-emerald-400 mt-0.5">{tier_lbl.split('(')[-1].replace(')', '')}</div>
            </div>
          </div>
        </div>

        <!-- Right Col: Big Scannable QR Code -->
        <div class="bg-slate-800/90 border border-slate-700 rounded-3xl p-6 flex flex-col items-center text-center shadow-inner">
          <div class="text-xs font-bold uppercase tracking-wider text-slate-300 mb-4 flex items-center gap-2">
            <i class="fa-solid fa-qrcode text-sky-400 text-base"></i>
            <span>Scan with Phone Camera</span>
          </div>

          <div class="p-3 bg-white rounded-2xl shadow-xl inline-block">
            <img src="https://api.qrserver.com/v1/create-qr-code/?size=200x200&amp;data={NTFY_SERVER}/{DEFAULT_NTFY_TOPIC}"
                 alt="Scan to Subscribe to Mathews Flood Alerts" 
                 class="w-44 h-44 block" 
                 loading="lazy" />
          </div>

          <div class="text-xs text-slate-300 mt-4 leading-snug">
            Point your iPhone or Android camera to open:
            <div class="font-mono text-sky-300 font-bold mt-1 text-sm">ntfy.sh/{DEFAULT_NTFY_TOPIC}</div>
          </div>

          <div class="mt-4 pt-3 border-t border-slate-700/80 w-full text-[11px] text-slate-400">
            Works instantly in camera app &bull; Zero configuration
          </div>
        </div>
      </div>
    </section>

    <!-- 2. DEVICE-BY-DEVICE STEP-BY-STEP SETUP GUIDE -->
    <section class="space-y-6">
      <div class="space-y-1">
        <h2 class="text-2xl font-bold text-slate-900 flex items-center gap-2">
          <i class="fa-solid fa-screwdriver-wrench text-sky-600"></i>
          Step-by-Step Setup Guide
        </h2>
        <p class="text-slate-600 text-sm">
          Setup takes less than 60 seconds on any smartphone, tablet, or laptop.
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- Card 1: iPhone & iPad (iOS) -->
        <div class="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4 flex flex-col justify-between">
          <div class="space-y-3">
            <div class="w-10 h-10 rounded-xl bg-slate-100 text-slate-900 flex items-center justify-center text-xl">
              <i class="fa-brands fa-apple"></i>
            </div>
            <h3 class="font-bold text-slate-900 text-lg">Apple iPhone &amp; iPad</h3>
            <ol class="space-y-3 text-xs text-slate-600 leading-relaxed list-decimal list-inside">
              <li>
                Install the free <a href="https://apps.apple.com/app/ntfy/id1625396347" target="_blank" rel="noopener" class="text-sky-600 font-bold hover:underline">ntfy app</a> from the App Store.
              </li>
              <li>
                Open the app, tap the <strong class="text-slate-900">+</strong> icon in the top-right corner, and type topic name:
                <div class="mt-1 font-mono bg-slate-100 text-slate-900 px-2 py-1 rounded text-[11px] font-bold border border-slate-200 inline-block">{DEFAULT_NTFY_TOPIC}</div>
              </li>
              <li>
                Tap <strong>Subscribe</strong>. In iOS Settings &gt; Notifications &gt; ntfy, make sure <em>Sounds &amp; Banners</em> are enabled so you receive audible warnings before high tide crests.
              </li>
            </ol>
          </div>
          <div class="pt-3 border-t border-slate-100">
            <a href="https://apps.apple.com/app/ntfy/id1625396347" target="_blank" rel="noopener" class="text-xs font-bold text-sky-600 hover:text-sky-700 flex items-center gap-1">
              <span>View in App Store</span> <i class="fa-solid fa-arrow-right text-[10px]"></i>
            </a>
          </div>
        </div>

        <!-- Card 2: Android -->
        <div class="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4 flex flex-col justify-between">
          <div class="space-y-3">
            <div class="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center text-xl">
              <i class="fa-brands fa-google-play"></i>
            </div>
            <h3 class="font-bold text-slate-900 text-lg">Android Devices</h3>
            <ol class="space-y-3 text-xs text-slate-600 leading-relaxed list-decimal list-inside">
              <li>
                Install the free <a href="https://play.google.com/store/apps/details?id=io.heckel.ntfy" target="_blank" rel="noopener" class="text-emerald-700 font-bold hover:underline">ntfy app</a> from the Google Play Store.
              </li>
              <li>
                Open the app, tap the <strong class="text-slate-900">+</strong> button in the bottom right, enter topic:
                <div class="mt-1 font-mono bg-slate-100 text-slate-900 px-2 py-1 rounded text-[11px] font-bold border border-slate-200 inline-block">{DEFAULT_NTFY_TOPIC}</div>
              </li>
              <li>
                Tap <strong>Subscribe</strong>. In your device settings, disable battery optimization for ntfy to ensure notifications arrive in real time without sleep delays.
              </li>
            </ol>
          </div>
          <div class="pt-3 border-t border-slate-100">
            <a href="https://play.google.com/store/apps/details?id=io.heckel.ntfy" target="_blank" rel="noopener" class="text-xs font-bold text-emerald-700 hover:text-emerald-800 flex items-center gap-1">
              <span>View in Google Play</span> <i class="fa-solid fa-arrow-right text-[10px]"></i>
            </a>
          </div>
        </div>

        <!-- Card 3: Web Browser (No App) -->
        <div class="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4 flex flex-col justify-between">
          <div class="space-y-3">
            <div class="w-10 h-10 rounded-xl bg-sky-50 text-sky-600 flex items-center justify-center text-xl">
              <i class="fa-solid fa-globe"></i>
            </div>
            <h3 class="font-bold text-slate-900 text-lg">Web Browser (Zero App)</h3>
            <ol class="space-y-3 text-xs text-slate-600 leading-relaxed list-decimal list-inside">
              <li>
                Navigate to <a href="{NTFY_SERVER}/{DEFAULT_NTFY_TOPIC}" target="_blank" rel="noopener" class="text-sky-600 font-bold hover:underline">ntfy.sh/{DEFAULT_NTFY_TOPIC}</a> in Chrome, Safari, Edge, or Firefox.
              </li>
              <li>
                Click the <strong>Subscribe</strong> button in the top menu bar.
              </li>
              <li>
                When your browser prompts: <em>"Allow ntfy.sh to send notifications?"</em>, click <strong>Allow</strong>. That's it! You will now receive push notifications directly in your browser.
              </li>
            </ol>
          </div>
          <div class="pt-3 border-t border-slate-100">
            <a href="{NTFY_SERVER}/{DEFAULT_NTFY_TOPIC}" target="_blank" rel="noopener" class="text-xs font-bold text-sky-600 hover:text-sky-700 flex items-center gap-1">
              <span>Open Web Feed</span> <i class="fa-solid fa-arrow-right text-[10px]"></i>
            </a>
          </div>
        </div>
      </div>
    </section>

    <!-- 3. HOW THE ALERT SYSTEM WORKS (THE 4-STAGE PIPELINE) -->
    <section class="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6">
      <div class="space-y-1">
        <h2 class="text-2xl font-bold text-slate-900 flex items-center gap-2">
          <i class="fa-solid fa-clock-rotate-left text-sky-600"></i>
          How &amp; When You Receive Flood Warnings
        </h2>
        <p class="text-slate-600 text-sm">
          Our system is completely automated and runs every 30 minutes. It evaluates hydrological water levels and dispatches alerts along four distinct warning stages:
        </p>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <!-- Stage 1: Advance Warning -->
        <div class="p-5 rounded-xl border border-amber-200 bg-amber-50/50 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold uppercase tracking-wider text-amber-800 flex items-center gap-1.5">
              <i class="fa-solid fa-hourglass-start"></i> Stage 1: Advance Notice
            </span>
            <span class="text-[11px] font-mono font-semibold bg-amber-200 text-amber-900 px-2 py-0.5 rounded-full">When Risk Is Detected</span>
          </div>
          <h3 class="font-bold text-slate-900 text-base">Early Crest Warning</h3>
          <p class="text-xs text-slate-700 leading-relaxed">
            Dispatched as soon as the NOAA NWPS / CBOFS forecast first indicates that an upcoming high tide will breach the <strong>3.99 ft flood tipping point</strong>. Gives you plenty of time to plan travel, move vehicles, or secure items before water rises.
          </p>
        </div>

        <!-- Stage 2: Imminent Warning -->
        <div class="p-5 rounded-xl border border-orange-200 bg-orange-50/50 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold uppercase tracking-wider text-orange-800 flex items-center gap-1.5">
              <i class="fa-solid fa-triangle-exclamation"></i> Stage 2: Imminent Warning
            </span>
            <span class="text-[11px] font-mono font-semibold bg-orange-200 text-orange-900 px-2 py-0.5 rounded-full">1–2 Hours Ahead</span>
          </div>
          <h3 class="font-bold text-slate-900 text-base">Pre-Crest Hazard Alert</h3>
          <p class="text-xs text-slate-700 leading-relaxed">
            Attempted near the crest when fresh forecast data and scheduled updates are available. Provides specific estimated flood depths in inches (e.g., <em>"5 to 7 inches over Daniel Ave"</em>) and describes modeled road hazards.
          </p>
        </div>

        <!-- Stage 3: Escalation Alert -->
        <div class="p-5 rounded-xl border border-red-200 bg-red-50/50 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold uppercase tracking-wider text-red-800 flex items-center gap-1.5">
              <i class="fa-solid fa-bolt text-red-600"></i> Stage 3: Surge Escalation
            </span>
            <span class="text-[11px] font-mono font-semibold bg-red-200 text-red-900 px-2 py-0.5 rounded-full">Immediate</span>
          </div>
          <h3 class="font-bold text-slate-900 text-base">Sudden Surge Increase</h3>
          <p class="text-xs text-slate-700 leading-relaxed">
            If persistent easterly or along-bay winds drive storm surge <strong>&ge; 0.25 ft (3+ inches) higher</strong> than the previous forecast, or if the risk tier escalates to Tier 3, an immediate update is dispatched.
          </p>
        </div>

        <!-- Stage 4: All Clear -->
        <div class="p-5 rounded-xl border border-emerald-200 bg-emerald-50/50 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold uppercase tracking-wider text-emerald-800 flex items-center gap-1.5">
              <i class="fa-solid fa-circle-check text-emerald-600"></i> Stage 4: Water Receding
            </span>
            <span class="text-[11px] font-mono font-semibold bg-emerald-200 text-emerald-900 px-2 py-0.5 rounded-full">Post-Crest</span>
          </div>
          <h3 class="font-bold text-slate-900 text-base">All-Clear Bulletin</h3>
          <p class="text-xs text-slate-700 leading-relaxed">
            Dispatched when the Ware River gauge safely drops back below 3.99 ft, water recedes into drainage ditches, and no further high water is predicted within the next 48-hour forecast window.
          </p>
        </div>
      </div>
    </section>

    <!-- 4. REALISTIC LOCK-SCREEN NOTIFICATION SIMULATOR -->
    <section class="space-y-6">
      <div class="space-y-1">
        <h2 class="text-2xl font-bold text-slate-900 flex items-center gap-2">
          <i class="fa-solid fa-mobile text-sky-600"></i>
          Sample Phone Push Notifications
        </h2>
        <p class="text-slate-600 text-sm">
          Here is what alerts look like when they appear on your smartphone lock screen:
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Sample 1: Tier 1 Nuisance -->
        <div class="bg-slate-900 text-white rounded-2xl p-4 sm:p-5 border border-slate-800 shadow-md flex items-start gap-3.5">
          <div class="w-10 h-10 rounded-xl bg-amber-500/20 text-amber-400 border border-amber-500/30 flex items-center justify-center text-lg shrink-0">
            <i class="fa-solid fa-triangle-exclamation"></i>
          </div>
          <div class="space-y-1 w-full">
            <div class="flex items-center justify-between text-[11px] text-slate-400">
              <span class="font-semibold text-slate-300">ntfy &bull; mathews-flood-23128</span>
              <span>2h ago</span>
            </div>
            <div class="font-bold text-sm text-amber-300">
              ⚠️ Tier 1 Flood Advisory: Ware River Crest at 4.15 ft MLLW
            </div>
            <p class="text-xs text-slate-300 leading-relaxed">
              Minor ditch overflow expected at 1:30 PM EDT (1-2" in roadside swales). Check actual conditions on Daniel Ave &amp; Bayshore Ave before travel.
            </p>
          </div>
        </div>

        <!-- Sample 2: Tier 2 Moderate -->
        <div class="bg-slate-900 text-white rounded-2xl p-4 sm:p-5 border border-slate-800 shadow-md flex items-start gap-3.5">
          <div class="w-10 h-10 rounded-xl bg-orange-500/20 text-orange-400 border border-orange-500/30 flex items-center justify-center text-lg shrink-0">
            <i class="fa-solid fa-car-burst"></i>
          </div>
          <div class="space-y-1 w-full">
            <div class="flex items-center justify-between text-[11px] text-slate-400">
              <span class="font-semibold text-slate-300">ntfy &bull; mathews-flood-23128</span>
              <span>1h ago</span>
            </div>
            <div class="font-bold text-sm text-orange-300">
              🚨 Coastal Flood Warning: Road Flooding Expected at 2:00 PM
            </div>
            <p class="text-xs text-slate-300 leading-relaxed">
              Peak stage 4.52 ft MLLW. 5 to 7 inches water across Daniel Ave &amp; Bayshore Ave. Passenger cars blocked. Move vehicles to high ground now.
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- 5. FREQUENTLY ASKED QUESTIONS (FAQ) -->
    <section class="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6">
      <div class="space-y-1">
        <h2 class="text-2xl font-bold text-slate-900 flex items-center gap-2">
          <i class="fa-solid fa-circle-question text-sky-600"></i>
          Frequently Asked Questions
        </h2>
        <p class="text-slate-600 text-sm">
          Everything you need to know about our privacy-first community notification system.
        </p>
      </div>

      <div class="divide-y divide-slate-100 text-sm space-y-4 pt-2">
        <div class="pt-4 space-y-1.5">
          <h3 class="font-bold text-slate-900 text-base flex items-center gap-2">
            <i class="fa-solid fa-comment-dots text-sky-600"></i>
            Why ntfy.sh instead of standard SMS text messages?
          </h3>
          <p class="text-slate-600 leading-relaxed text-xs sm:text-sm">
            Standard SMS text messaging requires collecting and storing community members' personal phone numbers, paying telecom gateway fees, and navigating complex carrier spam filters. <strong>ntfy.sh</strong> is 100% free, decentralized, open-source, and does not require you to share any personal information whatsoever.
          </p>
        </div>

        <div class="pt-4 space-y-1.5">
          <h3 class="font-bold text-slate-900 text-base flex items-center gap-2">
            <i class="fa-solid fa-lock text-sky-600"></i>
            Do I have to create an account or give my email?
          </h3>
          <p class="text-slate-600 leading-relaxed text-xs sm:text-sm">
            No. There are <strong>zero accounts, zero passwords, and zero email registrations</strong>. Subscribing to an ntfy topic is just like tuning a radio to a broadcast channel.
          </p>
        </div>

        <div class="pt-4 space-y-1.5">
          <h3 class="font-bold text-slate-900 text-base flex items-center gap-2">
            <i class="fa-solid fa-volume-high text-sky-600"></i>
            Will this wake me up at 3:00 AM?
          </h3>
          <p class="text-slate-600 leading-relaxed text-xs sm:text-sm">
            If an extreme high tide is predicted to breach roads in the middle of the night, you will receive an Advance Warning <strong>when a hazard is detected in fresh forecast data</strong>, giving you time to park safely before bed. Imminent crest warnings also chime so you are not trapped unexpectedly by rising water.
          </p>
        </div>

        <div class="pt-4 space-y-1.5">
          <h3 class="font-bold text-slate-900 text-base flex items-center gap-2">
            <i class="fa-solid fa-battery-full text-sky-600"></i>
            Will this drain my phone's battery?
          </h3>
          <p class="text-slate-600 leading-relaxed text-xs sm:text-sm">
            No. ntfy uses standard Apple Push Notification service (APNs) on iOS and Google Firebase Cloud Messaging on Android, using virtually 0% additional battery.
          </p>
        </div>

        <div class="pt-4 space-y-1.5">
          <h3 class="font-bold text-slate-900 text-base flex items-center gap-2">
            <i class="fa-solid fa-trash-can text-sky-600"></i>
            How do I unsubscribe?
          </h3>
          <p class="text-slate-600 leading-relaxed text-xs sm:text-sm">
            In the ntfy app, swipe left or long-press on <code class="bg-slate-100 px-1 py-0.5 rounded font-mono text-xs">{DEFAULT_NTFY_TOPIC}</code> and tap <strong>Delete</strong>. In a web browser, tap Unsubscribe in the top corner. You are instantly removed.
          </p>
        </div>
      </div>
    </section>

    <!-- 6. BACK TO LIVE MONITOR CTA -->
    <section class="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-6">
      <div class="space-y-1 text-center sm:text-left">
        <h3 class="text-lg font-bold text-slate-900">Want to see real-time water levels right now?</h3>
        <p class="text-xs sm:text-sm text-slate-600">
          Check the live Ware River stage, interactive coastal flood map, and 48-hour hydrograph.
        </p>
      </div>
      <a href="index.html" class="px-6 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-sm shadow-md transition flex items-center gap-2 shrink-0">
        <i class="fa-solid fa-water text-sky-400"></i>
        <span>View Live Monitor</span>
        <i class="fa-solid fa-arrow-right text-xs ml-1"></i>
      </a>
    </section>

  </main>

  {footer_html}

  <script>
    function copyTopic() {{
      const topic = '{DEFAULT_NTFY_TOPIC}';
      navigator.clipboard.writeText(topic).then(() => {{
        const feedback = document.getElementById('copy-feedback');
        if (feedback) {{
          feedback.classList.remove('hidden');
          setTimeout(() => {{
            feedback.classList.add('hidden');
          }}, 4000);
        }} else {{
          alert('Topic copied to clipboard: ' + topic);
        }}
      }}).catch(() => {{
        prompt('Copy topic name:', topic);
      }});
    }}
  </script>
</body>
</html>
"""

# ==============================================================================
# 3. PAGE 3: ABOUT.HTML (THE STORY, NOTEBOOKS, AND SCIENCE)
# ==============================================================================
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
  <meta name="description" content="The story of how handwritten storm logs from 2021 to 2024 uncovered the 3.99 ft flood threshold in Mathews County, VA.">
  
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

  <main class="flex-grow max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-12 w-full">

    <!-- Hero Header -->
    <section class="space-y-3">
      <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sky-100 text-sky-800 text-xs font-bold uppercase tracking-wider">
        <i class="fa-solid fa-book-open"></i> Project History & Science
      </div>
      <h1 class="text-3xl sm:text-4xl lg:text-5xl font-black text-slate-900 tracking-tight leading-tight">
        From Handwritten Notebooks to a Predictive Flood Model
      </h1>
      <p class="text-lg text-slate-600 leading-relaxed max-w-3xl">
        How 204 storm observations recorded with measuring tapes across 5 years in Mathews County, Virginia uncovered the mathematical tipping points of coastal compound flooding.
      </p>
    </section>

    <!-- 1. The Real-World Problem -->
    <section class="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-4">
      <div class="flex items-center gap-3 text-sky-600">
        <i class="fa-solid fa-compass text-2xl"></i>
        <h2 class="text-xl sm:text-2xl font-bold text-slate-900">Why Regional Weather Reports Fail Mathews County</h2>
      </div>
      <p class="text-slate-700 leading-relaxed">
        Mathews County is an almost sea-level peninsula surrounded by the Chesapeake Bay, Mobjack Bay, and the Piankatank River. Much of the land sits less than 5 to 10 feet above sea level.
      </p>
      <p class="text-slate-700 leading-relaxed">
        When TV forecasts in Richmond or Norfolk announce a "Coastal Flood Warning," it offers almost zero practical value to a local homeowner. It doesn’t tell you whether the water will stay in the ditch or flood the driveway, what time high tide will block your car, or whether an SUV can get through.
      </p>
      <div class="bg-sky-50 border-l-4 border-sky-500 p-4 rounded-r-xl text-sky-950 text-sm">
        <strong>The Core Question:</strong> "At exactly what river stage does the water breach our ditches, and how many inches of water does every additional tenth of a foot create?"
      </div>
    </section>

    <section class="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-4">
      <h2 class="text-2xl font-bold text-slate-900">Community observation archive</h2>
      <p class="text-slate-600 leading-relaxed">Historical community observations inform the model. Original notebooks and individual observer records are retained privately. The Data page provides yearly numerical summaries, while the Science page explains aggregate benchmarks and their limitations.</p>
      <a href="data.html" class="font-semibold text-sky-600">Explore the public historical summaries</a>
    </section>

    <!-- 3. Key Physical Breakthroughs -->
    <section class="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6">
      <h2 class="text-xl sm:text-2xl font-bold text-slate-900 flex items-center gap-2">
        <i class="fa-solid fa-atom text-sky-600"></i>
        The Three Physical Breakthroughs
      </h2>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="p-5 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
          <div class="text-sky-600 font-bold text-2xl font-mono">3.99 ft</div>
          <h3 class="font-bold text-slate-900 text-sm">1. The Tipping Point</h3>
          <p class="text-xs text-slate-600 leading-relaxed">
            Below 3.99 ft MLLW, water remains in ditches (0" flooding). Above 4.00 ft, ditch banks breach and water spreads across the driveway.
          </p>
        </div>

        <div class="p-5 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
          <div class="text-sky-600 font-bold text-2xl font-mono">10.95" / ft</div>
          <h3 class="font-bold text-slate-900 text-sm">2. The Inundation Slope</h3>
          <p class="text-xs text-slate-600 leading-relaxed">
            Every 0.10 ft of river rise yields 1.1 to 1.2 inches of water depth on the property ($r = 0.912$, $R^2 = 0.832$).
          </p>
        </div>

        <div class="p-5 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
          <div class="text-sky-600 font-bold text-2xl font-mono">&beta; Restriction</div>
          <h3 class="font-bold text-slate-900 text-sm">3. Compound Pluvial Physics</h3>
          <p class="text-xs text-slate-600 leading-relaxed">
            Heavy rainfall cannot drain by gravity when high bay water acts as a "cork in the ditch," trapping rain directly onto driveways.
          </p>
        </div>
      </div>
    </section>

    <!-- 4. How the Cloud Pipeline Works -->
    <section class="bg-slate-900 text-white rounded-2xl p-6 sm:p-8 space-y-4">
      <h2 class="text-xl sm:text-2xl font-bold flex items-center gap-2">
        <i class="fa-solid fa-cloud text-sky-400"></i>
        Serverless Cloud Execution
      </h2>
      <p class="text-slate-300 text-sm leading-relaxed">
        This entire portal runs at <strong>zero financial cost</strong> using GitHub Actions. Every 30 minutes:
      </p>
      <ul class="text-xs text-slate-300 space-y-2 list-disc list-inside">
        <li>A cloud runner spins up and queries NOAA NWPS (Ware River WRVV2 6-min stage & 4-day forecast hydrograph).</li>
        <li>Fetches real-time winds and storm surge from Yorktown USCG and Windmill Point.</li>
        <li>Computes the Hybrid Hydrodynamic–ML stage forecast and micro-topography water depths.</li>
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

  <main class="flex-grow max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-12 w-full">

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
            <div><strong>Vehicles:</strong> Passenger cars & sedans <strong>BLOCKED</strong>. SUVs/trucks only.</div>
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
          <div class="font-bold text-xs text-slate-900">Tire Splash Zone</div>
          <p class="text-[11px] text-slate-600">Passable for all passenger vehicles. Slow down to avoid throwing salt spray into engine compartments.</p>
        </div>

        <div class="p-4 rounded-xl bg-orange-50 border border-orange-200 space-y-1.5">
          <div class="text-orange-700 font-black text-xl font-mono">6 Inches</div>
          <div class="font-bold text-xs text-orange-900">Sedan Danger Threshold</div>
          <p class="text-[11px] text-orange-800">Reaches floorboards and exhaust pipes of passenger sedans. Stalls engines and ruins electronic modules.</p>
        </div>

        <div class="p-4 rounded-xl bg-red-50 border border-red-200 space-y-1.5">
          <div class="text-red-700 font-black text-xl font-mono">12+ Inches</div>
          <div class="font-bold text-xs text-red-900">Buoyant / Floating Hazard</div>
          <p class="text-[11px] text-red-800">Water displaces vehicle weight. Cars float and can be swept off submerged road shoulders into ditch beds.</p>
        </div>
      </div>
    </section>

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

  <main class="flex-grow max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-12 min-w-0 w-full w-full">

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
          Download Raw Datasets
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
            <div class="font-bold text-slate-900 text-sm">archive_hourly_observations.csv</div>
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
            <div class="font-bold text-slate-900 text-sm">observer_yearly_summary.csv</div>
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
            <div class="font-bold text-slate-900 text-sm">latest_status.json</div>
            <p class="text-xs text-slate-600 leading-relaxed">
              Real-time API JSON endpoint with current stage, sector elevations, passability, and 48h outlook.
            </p>
          </div>
          <div class="text-[11px] text-slate-400 font-mono pt-4">REST API &bull; Live</div>
        </a>
      </div>
    </section>

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

  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-12 flex-1 min-w-0 w-full">

    <!-- 0. HERO SECTION -->
    <section class="bg-gradient-to-br from-slate-900 via-slate-800 to-sky-950 text-white rounded-3xl p-6 sm:p-10 shadow-xl border border-slate-700/60 relative overflow-hidden">
      <div class="relative z-10 max-w-4xl space-y-4">
        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-sky-900/80 text-sky-300 border border-sky-700/60 shadow-sm">
          <i class="fa-solid fa-graduation-cap"></i> PEER-REVIEW READY &bull; OPEN SCIENCE &bull; 5-YEAR EMPIRICAL RECORD
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
          <a href="models/scientific_evidence.json" target="_blank" class="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white border border-slate-600 font-semibold text-xs sm:text-sm transition flex items-center gap-2">
            <i class="fa-solid fa-file-lines text-sky-400"></i> Download Aggregate Benchmarks
          </a>
          <a href="observer_yearly_summary.csv" download class="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white border border-slate-600 font-semibold text-xs sm:text-sm transition flex items-center gap-2">
            <i class="fa-solid fa-table text-emerald-400"></i> Yearly Observation Summary
          </a>
        </div>
      </div>
    </section>

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
          <div class="text-2xl sm:text-3xl font-black text-slate-900 font-mono">{total_obs} Events</div>
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
          <p class="text-xs text-slate-500 leading-snug">Culvert invert 4.05' MLLW independently verifies 3.99' tipping point within 0.7".</p>
        </div>

        <!-- Card 4: Driveway Pad Agreement -->
        <div class="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-2 hover:shadow-md transition">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-slate-400 uppercase tracking-wider">Driveway Pad Match</span>
            <div class="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center text-sm font-bold"><i class="fa-solid fa-road"></i></div>
          </div>
          <div class="text-2xl sm:text-3xl font-black text-amber-700 font-mono">&Delta; = 0.00 ft</div>
          <p class="text-xs text-slate-500 leading-snug">USGS LiDAR 4.40' MLLW exactly matches Tier 2 moderate flood threshold.</p>
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
            Translates the predicted or observed gauge stage into exact flood depth in inches on property benchmarks, driveway access corridors, and neighborhood roads using our empirically discovered 3.99 ft tipping point and 10.95 in/ft linear inundation gradient.
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
                <td class="px-4 py-3 text-slate-600 font-mono">181 Ground-Truth Events</td>
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
            USGS 3DEP 1-Meter LiDAR Altimetry Ground-Truth Validation
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
          <strong>Empirical Zero-Inundation Baseline Confirmation:</strong> Exactly 44 observations were recorded when the Ware River gauge was below 4.00 ft MLLW (ranging from 3.40' to 3.98'). All 44 instances exhibited exactly <strong>0.0 inches</strong> of inundation on the yard and road, verifying zero false positive flood alerts below our physical 3.99 ft threshold.
        </div>
      </div>
    </section>

    <!-- 5. BENCHMARK STORM CASE STUDIES -->
    <section class="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
        <div>
          <h2 class="text-xl font-bold text-slate-900 flex items-center gap-2">
            <i class="fa-solid fa-cloud-bolt text-rose-600"></i>
            Benchmark Storm Case Studies (Observed vs Model Predicted)
          </h2>
          <p class="text-xs sm:text-sm text-slate-500">Evaluation against 10 notable tropical cyclones, coastal lows, and king tide events across the 5-year record.</p>
        </div>
        <div class="text-xs font-mono text-slate-500">
          Evaluated via Piecewise Stage 2 Formula
        </div>
      </div>

      <div class="overflow-x-auto border border-slate-200 rounded-xl shadow-inner">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-slate-100 text-slate-700 text-[11px] font-bold uppercase tracking-wider border-b border-slate-200">
              <th class="px-4 py-2.5">Storm / Event</th>
              <th class="px-4 py-2.5">Stage (MLLW)</th>
              <th class="px-4 py-2.5">Observed Depth</th>
              <th class="px-4 py-2.5">Predicted Depth</th>
              <th class="px-4 py-2.5">Residual Error</th>
              <th class="px-4 py-2.5">Wind Forcing</th>
              <th class="px-4 py-2.5">Hydrologic & Inundation Impact</th>
            </tr>
          </thead>
          <tbody>
            {storm_rows_html}
          </tbody>
        </table>
      </div>
    </section>

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
