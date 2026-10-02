#!/usr/bin/env python3
"""
generate_dashboard.py — Multi-Page Coastal Flood Monitoring & Educational Portal
for Mathews County, Virginia Flood Prediction System.

Generates a complete, modern, human-friendly multi-page web portal:
1. index.html (& flood_dashboard.html): Live Monitor with Human Impact Advisory, Interactive Leaflet Flood Map,
   Property Elevation Cross-Section, Vehicle Passability Matrix, and 48-Hour Hydrograph.
2. about.html: The Origin Story, Mom's Handwritten Observer Notebook Gallery (2021-2024),
   Discovery of the 3.99 ft Threshold, and Compound Pluvial Physics.
3. guide.html: Visual Flood Severity Tiers (Tier 0 to Tier 3), Vehicle Water Depth Safety Guide,
   and Plain-English Coastal Definitions (MLLW vs NAVD88, Storm Surge Residual, Wind Set-Up).
4. data.html: Major Storm Comparison (Helene, Ian, Idalia, Ophelia, Earl, Nor'easters),
   Searchable 141-Event Observer Dataset Explorer, and Direct Data Downloads.

Author: Antigravity Assistant for Mathews County Flood Prediction Project
"""

import os
import json
import csv
import math
import argparse
from datetime import datetime

# Global topic configuration
DEFAULT_NTFY_TOPIC = os.getenv("NTFY_TOPIC", "mathews-flood-23128")

# Common color themes & risk tiers
TIER_STYLES = {
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
    curr = status.get("current_conditions", {})
    tier = curr.get("flood_risk_tier", 0)
    tier_info = TIER_STYLES.get(tier, TIER_STYLES[0])
    tier_lbl = curr.get("flood_risk_label", "Tier 0 (Normal / Safe)").split("(")[-1].replace(")", "")
    
    pages = [
        {"id": "live", "title": "Live Monitor", "href": "index.html", "icon": "fa-water"},
        {"id": "alerts", "title": "Mobile Alerts", "href": "index.html#alerts-section", "icon": "fa-bell"},
        {"id": "map", "title": "Flood Map", "href": "index.html#map-section", "icon": "fa-map-location-dot"},
        {"id": "about", "title": "About & History", "href": "about.html", "icon": "fa-book-open"},
        {"id": "guide", "title": "Flood Guide & Tiers", "href": "guide.html", "icon": "fa-ruler-vertical"},
        {"id": "data", "title": "Storm Archive & Data", "href": "data.html", "icon": "fa-database"}
    ]

    nav_links_html = ""
    mobile_links_html = ""
    for p in pages:
        is_active = (active_page == p["id"])
        active_class = "bg-sky-900/60 text-sky-200 border-b-2 border-sky-400 font-semibold" if is_active else "text-slate-300 hover:text-white hover:bg-slate-800/60"
        mobile_active = "bg-sky-900/50 text-sky-200 font-semibold" if is_active else "text-slate-300 hover:text-white hover:bg-slate-800"
        
        nav_links_html += f"""
        <a href="{p['href']}" class="px-3.5 py-2 text-sm rounded-lg transition-all flex items-center gap-2 {active_class}">
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
    """

def build_shared_footer(status):
    curr = status.get("current_conditions", {})
    last_ts = curr.get("observation_timestamp_local", "Just now")
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
            An open science, hyper-local flood prediction pipeline and machine learning model built from 141 ground-truth storm observations (2021–2024), NOAA NWPS hydrodynamic water level guidance, and NOAA CO-OPS sensor networks across the Middle Peninsula of Virginia.
          </p>
          <div class="text-xs text-slate-500 pt-1">
            Last Automated Cloud Sync: <span class="text-slate-300 font-mono font-medium">{last_ts}</span> (Runs every 30 mins)
          </div>
        </div>

        <!-- Col 2: Navigation Links -->
        <div>
          <h4 class="text-xs font-semibold uppercase tracking-wider text-slate-200 mb-3">Portal Navigation</h4>
          <ul class="space-y-2 text-xs">
            <li><a href="index.html" class="hover:text-sky-400 transition">Live Dashboard & Forecast</a></li>
            <li><a href="index.html#map-section" class="hover:text-sky-400 transition">Interactive Coastal Map</a></li>
            <li><a href="about.html" class="hover:text-sky-400 transition">The Story & Handwritten Notes</a></li>
            <li><a href="guide.html" class="hover:text-sky-400 transition">Flood Tiers & Plain-English Guide</a></li>
            <li><a href="data.html" class="hover:text-sky-400 transition">Storm History & Data Archive</a></li>
          </ul>
        </div>

        <!-- Col 3: Sensor Networks & Code -->
        <div>
          <h4 class="text-xs font-semibold uppercase tracking-wider text-slate-200 mb-3">Data & Source Code</h4>
          <ul class="space-y-2 text-xs">
            <li><a href="https://water.noaa.gov/gauges/WRVV2" target="_blank" rel="noopener" class="hover:text-sky-400 transition flex items-center gap-1.5"><i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i> NOAA NWPS Ware River (WRVV2)</a></li>
            <li><a href="https://tidesandcurrents.noaa.gov/stationhome.html?id=8637689" target="_blank" rel="noopener" class="hover:text-sky-400 transition flex items-center gap-1.5"><i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i> NOAA Yorktown USCG (8637689)</a></li>
            <li><a href="https://tidesandcurrents.noaa.gov/stationhome.html?id=8636580" target="_blank" rel="noopener" class="hover:text-sky-400 transition flex items-center gap-1.5"><i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i> NOAA Windmill Point (8636580)</a></li>
            <li><a href="archive_hourly_observations.csv" class="hover:text-sky-400 transition flex items-center gap-1.5"><i class="fa-solid fa-download text-[10px]"></i> Download Hourly Archive (CSV)</a></li>
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
def build_index_html(status, obs_rows, fcst_rows):
    curr = status.get("current_conditions", {})
    outl = status.get("forecast_48h_outlook", {})

    stage = curr.get("ware_river_stage_mllw_ft", "N/A")
    stage_navd = curr.get("ware_river_stage_navd88_ft", "N/A")
    depth = curr.get("estimated_local_flood_depth_in", 0.0)
    tier = curr.get("flood_risk_tier", 0)
    tier_info = TIER_STYLES.get(tier, TIER_STYLES[0])
    passability = curr.get("vehicle_passability", "ALL VEHICLES PASSABLE")
    sectors = curr.get("site_sectors", {})
    streets = curr.get("community_streets", {})
    if not streets or not sectors:
        import micro_topography
        stg_val = float(stage) if isinstance(stage, (int, float)) else 3.34
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

    wind_spd = curr.get("yorktown_wind_speed_mph", "N/A")
    wind_dir = curr.get("yorktown_wind_dir_cardinal", "N/A")
    wind_deg = curr.get("yorktown_wind_dir_deg", "N/A")
    wind_gst = curr.get("yorktown_wind_gust_mph", "N/A")
    along_bay = curr.get("along_bay_wind_vector_mph", "N/A")
    baro = curr.get("yorktown_baro_pressure_mb", "N/A")
    surge = curr.get("windmill_point_storm_surge_residual_ft", "N/A")

    peak_stage = outl.get("peak_forecast_stage_mllw_ft", "N/A")
    peak_time = outl.get("peak_forecast_stage_time_local", "N/A")
    peak_depth = outl.get("peak_estimated_flood_depth_in", 0.0)
    peak_tier = outl.get("peak_risk_tier", 0)
    peak_tier_info = TIER_STYLES.get(peak_tier, TIER_STYLES[0])
    peak_passability = outl.get("peak_vehicle_passability", "ALL VEHICLES PASSABLE")
    hours_flooded = outl.get("hours_at_or_above_action_stage", 0)
    advisory_summary = outl.get("advisory_summary", "No flooding expected.")

    # Human headline logic
    if tier == 0 and peak_tier == 0:
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
        sub_headline = f"Extreme high tide and storm surge will crest at {peak_stage} ft around {peak_time} with {peak_depth}\"+ water across roads and yard. High clearance trucks only or impassable."
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
    })

    return f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Mathews County, VA Coastal Flood Monitor & Forecast</title>
  <meta name="description" content="Hyper-local real-time coastal flood prediction, interactive map, and 48-hour hydrograph for Mathews County, VA.">
  
  <!-- Tailwind CSS & FontAwesome -->
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  
  <!-- Chart.js -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>

  <!-- Leaflet CSS & JS -->
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

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
    <section class="rounded-2xl {peak_tier_info['banner_bg']} border-2 {peak_tier_info['banner_border']} p-6 sm:p-8 shadow-sm transition-all">
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
        <div class="flex flex-wrap lg:flex-col gap-3 bg-white/80 backdrop-blur-sm p-4 rounded-xl border border-slate-200/80 shadow-sm min-w-[240px]">
          <div>
            <div class="text-[11px] font-semibold text-slate-500 uppercase">Current Ware River Stage</div>
            <div class="text-2xl font-black text-slate-900 font-mono">{stage} <span class="text-sm font-semibold text-slate-500">ft MLLW</span></div>
            <div class="text-[11px] text-slate-500 font-medium">({stage_navd} ft NAVD88)</div>
          </div>
          <div class="pt-2 border-t border-slate-200">
            <div class="text-[11px] font-semibold text-slate-500 uppercase">48-Hour Peak Forecast</div>
            <div class="text-lg font-extrabold text-sky-900 font-mono">{peak_stage} ft <span class="text-xs font-normal text-slate-500">at {peak_time.split(' ')[1] if ' ' in str(peak_time) else peak_time}</span></div>
            <div class="text-xs font-semibold {peak_tier_info['badge_text']}">Inundation: {peak_depth}" ({peak_passability})</div>
          </div>
        </div>
      </div>
    </section>

    <!-- 2. VEHICLE PASSABILITY & HUMAN ACTION STRIP -->
    <section class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <!-- Card 1: Sedans -->
      <div class="bg-white rounded-xl p-5 border border-slate-200 shadow-sm flex items-start gap-4">
        <div class="w-12 h-12 rounded-xl {'bg-emerald-100 text-emerald-700' if 'PASSABLE' in passability else 'bg-red-100 text-red-700'} flex items-center justify-center text-xl shrink-0">
          <i class="fa-solid fa-car-side"></i>
        </div>
        <div>
          <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Passenger Cars / Sedans</div>
          <div class="text-base font-bold text-slate-900 mt-0.5">
            {'PASSABLE & SAFE' if 'PASSABLE' in passability else 'DO NOT DRIVE (BLOCKED)'}
          </div>
          <p class="text-xs text-slate-600 mt-1">
            {'All access routes dry. Safe for low clearance sedans.' if 'PASSABLE' in passability else 'Water over road exceeds 4 inches. Risk of engine stall and brake failure.'}
          </p>
        </div>
      </div>

      <!-- Card 2: SUVs & Trucks -->
      <div class="bg-white rounded-xl p-5 border border-slate-200 shadow-sm flex items-start gap-4">
        <div class="w-12 h-12 rounded-xl {'bg-emerald-100 text-emerald-700' if tier < 3 else 'bg-amber-100 text-amber-700'} flex items-center justify-center text-xl shrink-0">
          <i class="fa-solid fa-truck-pickup"></i>
        </div>
        <div>
          <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider">SUVs & High-Clearance Trucks</div>
          <div class="text-base font-bold text-slate-900 mt-0.5">
            {'PASSABLE' if tier < 3 else 'PROCEED WITH EXTREME CAUTION'}
          </div>
          <p class="text-xs text-slate-600 mt-1">
            {'Ground clearance adequate for current and peak tides.' if tier < 3 else 'Water depth approaching 9-12 inches. Do not drive through moving water.'}
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
            {'No Action Required' if peak_tier < 2 else 'Plan Around High Tide'}
          </div>
          <p class="text-xs text-slate-600 mt-1">
            {'Normal routines. Ditches flowing freely.' if peak_tier < 2 else f'Move low vehicles to higher ground before {peak_time.split(" ")[1] if " " in str(peak_time) else peak_time}.'}
          </p>
        </div>
      </div>
    </section>

    <!-- 3. REAL-TIME MOBILE FLOOD ALERTS (NTFY.SH) BANNER -->
    <section id="alerts-section" class="bg-gradient-to-br from-slate-900 via-slate-800 to-sky-950 rounded-2xl text-white p-6 sm:p-8 border border-sky-800/50 shadow-lg relative overflow-hidden">
      <div class="absolute -right-12 -bottom-12 w-64 h-64 bg-sky-500/10 rounded-full blur-3xl pointer-events-none"></div>

      <div class="relative z-10 grid grid-cols-1 lg:grid-cols-3 gap-8 items-center">
        <!-- Explainer & Action Buttons -->
        <div class="lg:col-span-2 space-y-4">
          <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-400/20 text-amber-300 border border-amber-400/30 text-xs font-bold uppercase tracking-wider">
            <i class="fa-solid fa-bell animate-bounce"></i>
            <span>Instant Mobile Alerts &bull; 100% Free &bull; Zero Accounts</span>
          </div>

          <h2 class="text-2xl sm:text-3xl font-extrabold tracking-tight text-white leading-tight">
            Get Audible Flood Warnings on Your Phone Before High Tide
          </h2>

          <p class="text-sm sm:text-base text-slate-300 leading-relaxed">
            Never get caught off guard by saltwater over Daniel Ave or Bayshore Ave. Receive high-priority push notifications directly to your smartphone <strong>6 to 12 hours before peak high tide</strong>. 
            <span class="text-sky-300 font-medium">Free forever, no email or password needed, and zero notification spam</span> (only alerts when ditch overflow or road flooding is predicted).
          </p>

          <!-- 3-Step Setup Guide -->
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
            <div class="bg-slate-800/80 border border-slate-700/80 rounded-xl p-3">
              <div class="flex items-center gap-2 text-sky-400 font-bold text-xs uppercase mb-1">
                <span class="w-5 h-5 rounded-full bg-sky-900 text-sky-200 flex items-center justify-center text-[11px]">1</span>
                <span>Install Free App</span>
              </div>
              <p class="text-xs text-slate-300">
                Install <strong>ntfy</strong> from App Store or Google Play (or subscribe in web browser).
              </p>
            </div>

            <div class="bg-slate-800/80 border border-slate-700/80 rounded-xl p-3">
              <div class="flex items-center gap-2 text-sky-400 font-bold text-xs uppercase mb-1">
                <span class="w-5 h-5 rounded-full bg-sky-900 text-sky-200 flex items-center justify-center text-[11px]">2</span>
                <span>Subscribe</span>
              </div>
              <p class="text-xs text-slate-300">
                Tap <strong>+</strong> and enter topic <code class="bg-slate-950 px-1.5 py-0.5 rounded text-amber-300 font-mono text-[11px]">{DEFAULT_NTFY_TOPIC}</code>.
              </p>
            </div>

            <div class="bg-slate-800/80 border border-slate-700/80 rounded-xl p-3">
              <div class="flex items-center gap-2 text-sky-400 font-bold text-xs uppercase mb-1">
                <span class="w-5 h-5 rounded-full bg-sky-900 text-sky-200 flex items-center justify-center text-[11px]">3</span>
                <span>Stay Protected</span>
              </div>
              <p class="text-xs text-slate-300">
                Audible chimes warn you in advance with crest timing &amp; inches on the driveway.
              </p>
            </div>
          </div>

          <!-- Action Buttons -->
          <div class="flex flex-wrap items-center gap-3 pt-2">
            <a href="https://ntfy.sh/{DEFAULT_NTFY_TOPIC}" target="_blank" rel="noopener noreferrer" 
               class="px-5 py-2.5 rounded-xl bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold text-sm shadow-md transition flex items-center gap-2">
              <i class="fa-solid fa-mobile-screen-button"></i>
              <span>Subscribe on Phone / Browser</span>
            </a>

            <button onclick="navigator.clipboard.writeText('{DEFAULT_NTFY_TOPIC}'); alert(&quot;Topic copied to clipboard: {DEFAULT_NTFY_TOPIC}&quot;);" 
                    class="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold text-sm transition flex items-center gap-2">
              <i class="fa-solid fa-copy text-amber-400"></i>
              <span>Copy Topic: <span class="font-mono text-amber-300">{DEFAULT_NTFY_TOPIC}</span></span>
            </button>
          </div>
        </div>

        <!-- QR Code Card -->
        <div class="bg-slate-800/90 border border-slate-700 rounded-2xl p-5 flex flex-col items-center text-center shadow-inner">
          <div class="text-xs font-bold uppercase tracking-wider text-slate-300 mb-3 flex items-center gap-2">
            <i class="fa-solid fa-qrcode text-sky-400"></i>
            <span>Scan with Phone Camera</span>
          </div>

          <div class="p-2.5 bg-white rounded-xl shadow-md inline-block">
            <img src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&amp;data=https://ntfy.sh/{DEFAULT_NTFY_TOPIC}" 
                 alt="Scan to Subscribe to Mathews Flood Alerts" 
                 class="w-36 h-36 block" 
                 loading="lazy" />
          </div>

          <div class="text-[11px] text-slate-400 mt-3 max-w-[200px]">
            Direct link to <span class="font-mono text-sky-300 font-semibold">ntfy.sh/{DEFAULT_NTFY_TOPIC}</span>
          </div>

          <div class="mt-4 pt-3 border-t border-slate-700/80 w-full flex items-center justify-center gap-4 text-xs text-slate-400">
            <a href="https://apps.apple.com/app/ntfy/id1625396347" target="_blank" rel="noopener noreferrer" class="hover:text-white transition flex items-center gap-1">
              <i class="fa-brands fa-apple text-sm"></i> iPhone
            </a>
            <span class="text-slate-600">&bull;</span>
            <a href="https://play.google.com/store/apps/details?id=io.heckel.ntfy" target="_blank" rel="noopener noreferrer" class="hover:text-white transition flex items-center gap-1">
              <i class="fa-brands fa-google-play text-sm"></i> Android
            </a>
            <span class="text-slate-600">&bull;</span>
            <a href="https://ntfy.sh/{DEFAULT_NTFY_TOPIC}" target="_blank" rel="noopener noreferrer" class="hover:text-white transition flex items-center gap-1">
              <i class="fa-solid fa-globe text-sm"></i> Web
            </a>
          </div>
        </div>
      </div>
    </section>

    <!-- 4. INTERACTIVE LEAFLET FLOOD MAP SECTION -->
    <section id="map-section" class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
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

    <!-- 5. COMMUNITY ELEVATION PROFILE & STREET PASSABILITY -->
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
            <span class="font-mono font-semibold {'text-sky-700' if sectors.get('ditches', {}).get('depth_in', 0) > 0 else 'text-slate-400'}">
              {sectors.get('ditches', {}).get('depth_in', 0)}" Water ({sectors.get('ditches', {}).get('status', 'DRY')})
            </span>
          </div>
          <div class="w-full bg-slate-100 h-3 rounded-full overflow-hidden">
            <div class="bg-sky-500 h-full rounded-full transition-all" style="width: {min(100, max(2, int(sectors.get('ditches', {}).get('depth_in', 0) * 15)))}%"></div>
          </div>
        </div>

        <!-- Sector 2: Road Apron / Culvert -->
        <div>
          <div class="flex justify-between text-xs font-medium mb-1">
            <span class="text-slate-700 font-semibold"><i class="fa-solid fa-road text-amber-500 mr-1.5"></i> 2. Lower Residential Blocks — Allview / Hobday / Little Ave South (Elev: 4.15' MLLW / 2.51' NAVD88)</span>
            <span class="font-mono font-semibold {'text-amber-700' if sectors.get('road_apron', {}).get('depth_in', 0) > 0 else 'text-emerald-700'}">
              {sectors.get('road_apron', {}).get('depth_in', 0)}" Water ({sectors.get('road_apron', {}).get('status', 'DRY')})
            </span>
          </div>
          <div class="w-full bg-slate-100 h-3 rounded-full overflow-hidden">
            <div class="{'bg-amber-500' if sectors.get('road_apron', {}).get('depth_in', 0) > 0 else 'bg-emerald-500'} h-full rounded-full transition-all" style="width: {min(100, max(2, int(sectors.get('road_apron', {}).get('depth_in', 0) * 15)))}%"></div>
          </div>
        </div>

        <!-- Sector 3: Main Driveway -->
        <div>
          <div class="flex justify-between text-xs font-medium mb-1">
            <span class="text-slate-700 font-semibold"><i class="fa-solid fa-car text-orange-500 mr-1.5"></i> 3. Daniel Ave Central Spine &amp; Julian St — Primary Route (Elev: 4.40' MLLW / 2.76' NAVD88)</span>
            <span class="font-mono font-semibold {'text-orange-700 font-bold' if sectors.get('main_driveway', {}).get('depth_in', 0) > 0 else 'text-emerald-700 font-bold'}">
              {sectors.get('main_driveway', {}).get('depth_in', 0)}" Water ({sectors.get('main_driveway', {}).get('status', 'DRY')})
            </span>
          </div>
          <div class="w-full bg-slate-100 h-3 rounded-full overflow-hidden">
            <div class="{'bg-orange-500' if sectors.get('main_driveway', {}).get('depth_in', 0) > 0 else 'bg-emerald-500'} h-full rounded-full transition-all" style="width: {min(100, max(2, int(sectors.get('main_driveway', {}).get('depth_in', 0) * 15)))}%"></div>
          </div>
        </div>

        <!-- Sector 4: Residential Lawn -->
        <div>
          <div class="flex justify-between text-xs font-medium mb-1">
            <span class="text-slate-700 font-semibold"><i class="fa-solid fa-tree text-emerald-600 mr-1.5"></i> 4. Upper Residential Grounds &amp; Northern Lots (Elev: 4.60' MLLW / 2.96' NAVD88)</span>
            <span class="font-mono font-semibold {'text-red-700 font-bold' if sectors.get('yard_lawn', {}).get('depth_in', 0) > 0 else 'text-emerald-700'}">
              {sectors.get('yard_lawn', {}).get('depth_in', 0)}" Water ({sectors.get('yard_lawn', {}).get('status', 'DRY')})
            </span>
          </div>
          <div class="w-full bg-slate-100 h-3 rounded-full overflow-hidden">
            <div class="{'bg-red-500' if sectors.get('yard_lawn', {}).get('depth_in', 0) > 0 else 'bg-emerald-500'} h-full rounded-full transition-all" style="width: {min(100, max(2, int(sectors.get('yard_lawn', {}).get('depth_in', 0) * 15)))}%"></div>
          </div>
        </div>

        <!-- Sector 5: Garage High Ground -->
        <div>
          <div class="flex justify-between text-xs font-medium mb-1">
            <span class="text-slate-700 font-semibold"><i class="fa-solid fa-house text-blue-600 mr-1.5"></i> 5. River Road North &amp; Ridge High Ground Pads (Elev: 4.90' MLLW / 3.26' NAVD88)</span>
            <span class="font-mono font-semibold {'text-red-700 font-bold' if sectors.get('garage_foundation', {}).get('depth_in', 0) > 0 else 'text-emerald-700'}">
              {sectors.get('garage_foundation', {}).get('depth_in', 0)}" Water ({sectors.get('garage_foundation', {}).get('status', 'SAFE')})
            </span>
          </div>
          <div class="w-full bg-slate-100 h-3 rounded-full overflow-hidden">
            <div class="{'bg-red-600' if sectors.get('garage_foundation', {}).get('depth_in', 0) > 0 else 'bg-emerald-500'} h-full rounded-full transition-all" style="width: {min(100, max(2, int(sectors.get('garage_foundation', {}).get('depth_in', 0) * 15)))}%"></div>
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

    <!-- 6. 48-HOUR HYDROGRAPH & ENVIRONMENTAL DRIVERS -->
    <section class="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 class="text-lg font-bold text-slate-900 flex items-center gap-2">
            <i class="fa-solid fa-chart-line text-sky-600"></i>
            48-Hour Hybrid Forecast Hydrograph
          </h2>
          <p class="text-xs sm:text-sm text-slate-500">
            NOAA NWPS CBOFS hydrodynamic water model blended with local wind stress ML bias correction and NWS rainfall.
          </p>
        </div>
        <div class="flex items-center gap-3 text-xs">
          <span class="flex items-center gap-1.5"><span class="w-3 h-0.5 bg-sky-600"></span> Predicted Stage</span>
          <span class="flex items-center gap-1.5"><span class="w-3 h-0.5 bg-red-500 border-t border-dashed"></span> 3.99' Flood Threshold</span>
        </div>
      </div>

      <div class="h-80 w-full relative">
        <canvas id="hydrographChart"></canvas>
      </div>
    </section>

    <!-- 7. REAL-TIME SENSOR NETWORK CARDS -->
    <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- Card: Yorktown Winds -->
      <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
        <div class="flex items-center justify-between text-xs font-semibold text-slate-500 uppercase">
          <span>Yorktown Winds</span>
          <i class="fa-solid fa-wind text-sky-500"></i>
        </div>
        <div class="text-2xl font-black text-slate-900 font-mono">
          {wind_spd} <span class="text-sm font-semibold text-slate-500">mph</span>
        </div>
        <div class="text-xs text-slate-600 flex items-center justify-between">
          <span>From {wind_dir} ({wind_deg}&deg;)</span>
          <span>Gusts: {wind_gst} mph</span>
        </div>
      </div>

      <!-- Card: Along-Bay Wind Vector -->
      <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
        <div class="flex items-center justify-between text-xs font-semibold text-slate-500 uppercase">
          <span>Along-Bay Vector</span>
          <i class="fa-solid fa-compass text-blue-500"></i>
        </div>
        <div class="text-2xl font-black font-mono {'text-amber-600' if float(along_bay or 0) > 10 else 'text-slate-900'}">
          {along_bay} <span class="text-sm font-semibold text-slate-500">mph</span>
        </div>
        <div class="text-xs text-slate-500">
          {'Forcing water into Mobjack Bay' if float(along_bay or 0) > 0 else 'Blowing water out to Atlantic'}
        </div>
      </div>

      <!-- Card: Barometric Pressure -->
      <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
        <div class="flex items-center justify-between text-xs font-semibold text-slate-500 uppercase">
          <span>Barometer</span>
          <i class="fa-solid fa-gauge-high text-indigo-500"></i>
        </div>
        <div class="text-2xl font-black text-slate-900 font-mono">
          {baro} <span class="text-sm font-semibold text-slate-500">mb</span>
        </div>
        <div class="text-xs text-slate-500">
          {'Low pressure (water rising)' if float(baro or 1013) < 1010 else 'Normal atmospheric pressure'}
        </div>
      </div>

      <!-- Card: Mouth of Bay Surge -->
      <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
        <div class="flex items-center justify-between text-xs font-semibold text-slate-500 uppercase">
          <span>Mouth-of-Bay Surge</span>
          <i class="fa-solid fa-water-ladder text-cyan-500"></i>
        </div>
        <div class="text-2xl font-black font-mono {'text-amber-600' if float(surge or 0) > 1.0 else 'text-slate-900'}">
          +{surge} <span class="text-sm font-semibold text-slate-500">ft</span>
        </div>
        <div class="text-xs text-slate-500">
          Windmill Point storm surge residual
        </div>
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
        <div class="text-sm font-bold text-slate-900 font-mono">${{curr.yorktown_wind_speed_mph || 'N/A'}} mph from ${{curr.yorktown_wind_dir_cardinal || 'N/A'}}</div>
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
        <div class="text-sm font-bold text-slate-900 font-mono">+${{curr.windmill_point_storm_surge_residual_ft || '0.0'}} ft Surge Residual</div>
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
          <span class="text-base font-black text-sky-900 font-mono">${{curr.estimated_local_flood_depth_in || '0.0'}}"</span>
        </div>
        <div class="text-[11px] font-semibold ${{curr.estimated_local_flood_depth_in > 0 ? 'text-amber-600' : 'text-emerald-600'}}">
          Passability: ${{curr.vehicle_passability || 'ALL VEHICLES PASSABLE'}}
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

    function renderCommunityMap(stageVal) {{
      zoneLayers.forEach(l => map.removeLayer(l));
      zoneLayers = [];
      streetLayers.forEach(l => map.removeLayer(l));
      streetLayers = [];

      // 1. Render Elevation Zones (Dry land)
      communityZones.forEach(z => {{
        let color = '#10b981'; // Green
        let depthIn = 0;
        let statusTxt = 'Dry & Clear';

        if (stageVal >= z.elev) {{
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
        }} else if (z.elev - stageVal < 0.25) {{
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
        let stStatus = 'All Vehicles Passable (Dry)';

        if (stageVal >= stData.elev) {{
          stDepth = Math.round((stageVal - stData.elev) * 12 * 10) / 10;
          if (stDepth < 3.5) {{
            stColor = '#d97706'; // Amber
            stStatus = `Caution: Puddles / Ditch Full (${{stDepth}}")`;
          }} else if (stDepth < 7.5) {{
            stColor = '#ea580c'; // Orange
            stStatus = `Sedans Blocked — Trucks/SUVs Only (${{stDepth}}")`;
          }} else {{
            stColor = '#dc2626'; // Red
            stStatus = `Critical — Impassable Deep Water (${{stDepth}}")`;
          }}
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
    renderCommunityMap(parseFloat(curr.ware_river_stage_mllw_ft || 3.1));

    // Toggle button handlers
    const btnCurrent = document.getElementById('btn-map-current');
    const btnPeak = document.getElementById('btn-map-peak');

    btnCurrent.addEventListener('click', () => {{
      btnCurrent.classList.add('bg-white', 'shadow-sm', 'font-semibold', 'text-slate-900');
      btnCurrent.classList.remove('text-slate-600');
      btnPeak.classList.remove('bg-white', 'shadow-sm', 'font-semibold', 'text-slate-900');
      btnPeak.classList.add('text-slate-600');
      renderCommunityMap(parseFloat(curr.ware_river_stage_mllw_ft || 3.1));
    }});

    btnPeak.addEventListener('click', () => {{
      btnPeak.classList.add('bg-white', 'shadow-sm', 'font-semibold', 'text-slate-900');
      btnPeak.classList.remove('text-slate-600');
      btnCurrent.classList.remove('bg-white', 'shadow-sm', 'font-semibold', 'text-slate-900');
      btnCurrent.classList.add('text-slate-600');
      renderCommunityMap(parseFloat(outl.peak_forecast_stage_mllw_ft || 3.5));
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

    // 2. CHART.JS 48-HOUR HYDROGRAPH
    const ctx = document.getElementById('hydrographChart').getContext('2d');
    const labels = fcst.map(r => {{
      const d = r.timestamp_local || '';
      return d.split(' ')[1] ? d.split(' ')[1].slice(0,5) : d;
    }});
    const stageData = fcst.map(r => parseFloat(r.forecast_stage_mllw_ft || 0));
    const rainData = fcst.map(r => parseFloat(r.rain_forecast_hourly_in || 0));
    const thresholdData = fcst.map(() => 3.99);

    new Chart(ctx, {{
      type: 'line',
      data: {{
        labels: labels,
        datasets: [
          {{
            label: 'Predicted Stage (ft MLLW)',
            data: stageData,
            borderColor: '#0284c7',
            backgroundColor: 'rgba(2, 132, 199, 0.1)',
            fill: true,
            tension: 0.35,
            borderWidth: 2.5,
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
            max: Math.max(5.5, Math.ceil(Math.max(...stageData, 4.5))),
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
# 2. PAGE 2: ABOUT.HTML (THE STORY, NOTEBOOKS, AND SCIENCE)
# ==============================================================================
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
  
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
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
        How 141 storm observations recorded with measuring tapes across 4 years in Mathews County, Virginia uncovered the mathematical tipping points of coastal compound flooding.
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

    <!-- 2. Mom's Notebooks Gallery -->
    <section class="space-y-6">
      <div class="space-y-1">
        <h2 class="text-2xl font-bold text-slate-900 flex items-center gap-2">
          <i class="fa-solid fa-camera text-sky-600"></i>
          The Ground-Truth Observations (2021–2024)
        </h2>
        <p class="text-slate-600 text-sm">
          Between May 2021 and September 2024, our family logged 141 individual storm events by hand, measuring water depths in inches and noting Ware River gauge stages and wind directions.
        </p>
      </div>

      <!-- Photo Cards Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Photo Card 1: IMG_8049 (The Formula) -->
        <div class="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm hover:shadow-md transition">
          <div class="h-64 bg-slate-100 overflow-hidden relative">
            <img src="photos/IMG_8049.jpeg" alt="Observer Handwritten Formula" class="w-full h-full object-cover object-top hover:scale-105 transition-transform duration-300">
            <div class="absolute bottom-2 left-2 bg-slate-900/80 text-white text-[11px] font-mono px-2 py-0.5 rounded backdrop-blur">IMG_8049.jpeg</div>
          </div>
          <div class="p-5 space-y-2">
            <h3 class="font-bold text-slate-900 text-base">The Discovery Note: ".10 = 1 3/16th IN"</h3>
            <p class="text-xs text-slate-600 leading-relaxed">
              On this sticky note, mom recorded her empirical conversion: <strong>0.10 ft of river rise equals almost 1.25 inches of ground flood</strong>. Three years later, our rigorous linear regression proved her exact ratio: <strong>10.95 inches per foot (1.10" per 0.10')</strong>!
            </p>
          </div>
        </div>

        <!-- Photo Card 2: IMG_8050 (Notebook Page 1) -->
        <div class="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm hover:shadow-md transition">
          <div class="h-64 bg-slate-100 overflow-hidden relative">
            <img src="photos/IMG_8050.jpeg" alt="Notebook Page 1" class="w-full h-full object-cover object-top hover:scale-105 transition-transform duration-300">
            <div class="absolute bottom-2 left-2 bg-slate-900/80 text-white text-[11px] font-mono px-2 py-0.5 rounded backdrop-blur">IMG_8050.jpeg</div>
          </div>
          <div class="p-5 space-y-2">
            <h3 class="font-bold text-slate-900 text-base">Notebook Page 1: May 2021 to Jan 2022</h3>
            <p class="text-xs text-slate-600 leading-relaxed">
              Tracking early nor'easters, winter storms, and the May 2021 high water event (5.10 ft stage yielding 14.0" flood depth). Clear records of wind directions and speeds.
            </p>
          </div>
        </div>

        <!-- Photo Card 3: IMG_8051 (Hurricanes Ian & Earl) -->
        <div class="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm hover:shadow-md transition">
          <div class="h-64 bg-slate-100 overflow-hidden relative">
            <img src="photos/IMG_8051.jpeg" alt="Notebook Page 2 - Hurricanes" class="w-full h-full object-cover object-top hover:scale-105 transition-transform duration-300">
            <div class="absolute bottom-2 left-2 bg-slate-900/80 text-white text-[11px] font-mono px-2 py-0.5 rounded backdrop-blur">IMG_8051.jpeg</div>
          </div>
          <div class="p-5 space-y-2">
            <h3 class="font-bold text-slate-900 text-base">Page 2: Hurricane Earl & Hurricane Ian</h3>
            <p class="text-xs text-slate-600 leading-relaxed">
              Documenting Hurricane Earl (Sep 2022, 10" depth) and Hurricane Ian (Oct 2022, 7" depth). Demonstrates how wind direction dictated flood depth even when river stages were identical.
            </p>
          </div>
        </div>

        <!-- Photo Card 4: IMG_8054 (Tape Measure Verification) -->
        <div class="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm hover:shadow-md transition">
          <div class="h-64 bg-slate-100 overflow-hidden relative">
            <img src="photos/IMG_8054.jpeg" alt="Physical Water Depth Measurement" class="w-full h-full object-cover object-top hover:scale-105 transition-transform duration-300">
            <div class="absolute bottom-2 left-2 bg-slate-900/80 text-white text-[11px] font-mono px-2 py-0.5 rounded backdrop-blur">IMG_8054.jpeg</div>
          </div>
          <div class="p-5 space-y-2">
            <h3 class="font-bold text-slate-900 text-base">Direct Physical Verification</h3>
            <p class="text-xs text-slate-600 leading-relaxed">
              Every point in our training dataset was physically verified with yardsticks and tape measures at key reference spots on the driveway and yard.
            </p>
          </div>
        </div>
      </div>
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
# 3. PAGE 3: GUIDE.HTML (FLOOD TIERS & DEFINITIONS)
# ==============================================================================
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
  
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
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
            <div><strong>Vehicles:</strong> All passenger cars, sedans, and delivery vans 100% passable.</div>
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
            <div><strong>Vehicles:</strong> Main driveway passable; drive slowly through culvert dip.</div>
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
# 4. PAGE 4: DATA.HTML (STORM ARCHIVE & DOWNLOADS)
# ==============================================================================
def build_data_html(status, ground_truth_rows, obs_rows):
    navbar_html = build_shared_navbar("data", status)
    footer_html = build_shared_footer(status)

    # Notable storms list
    notable_storms = [
        {"name": "Hurricane Helene", "date": "Sep 27, 2024", "stage": "4.70 ft", "depth": "9.75\"", "wind": "SE 25.3 mph", "notes": "Rapid tropical surge backing up ditches"},
        {"name": "Hurricane Ophelia", "date": "Sep 23, 2023", "stage": "4.87 ft", "depth": "14.50\"", "wind": "SE 30+ mph", "notes": "Highest flood depth in recent observer records"},
        {"name": "Hurricane Ian", "date": "Sep 30 – Oct 3, 2022", "stage": "4.66 ft", "depth": "7.00\"", "wind": "N 12–24 mph", "notes": "Multi-day prolonged northerly wind set-up"},
        {"name": "Hurricane Idalia", "date": "Aug 28–29, 2023", "stage": "4.61 ft", "depth": "7.50\"", "wind": "E 15–20 mph", "notes": "King Tide alignment plus tropical swell"},
        {"name": "Hurricane Earl", "date": "Sep 7–10, 2022", "stage": "4.82 ft", "depth": "10.00\"", "wind": "NNE 17 mph", "notes": "Driveway submerged for multiple tidal cycles"},
        {"name": "Winter Storm (Snow/Nor'easter)", "date": "Jan 3, 2022", "stage": "5.22 ft", "depth": "11.00\"", "wind": "N gale", "notes": "Highest Ware River stage recorded (5.22 ft)"}
    ]

    storm_cards_html = ""
    for s in notable_storms:
        storm_cards_html += f"""
        <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-sky-700 uppercase tracking-wider">{s['name']}</span>
            <span class="text-xs text-slate-500 font-mono">{s['date']}</span>
          </div>
          <div class="flex items-baseline justify-between pt-1">
            <div class="text-xl font-black text-slate-900 font-mono">{s['stage']}</div>
            <div class="text-sm font-bold text-orange-600 font-mono">Depth: {s['depth']}</div>
          </div>
          <div class="text-xs text-slate-600 flex items-center justify-between border-t border-slate-100 pt-2">
            <span>Wind: {s['wind']}</span>
            <span class="text-[11px] text-slate-500 italic">{s['notes']}</span>
          </div>
        </div>
        """

    # Ground truth table rows
    table_rows_html = ""
    for r in ground_truth_rows[:60]: # Show recent 60
        date_str = r.get("date", "")
        stage_str = r.get("ware_river_stage_ft", "")
        depth_str = r.get("flood_depth_in", "")
        wind_dir = r.get("wind_direction", "")
        wind_spd = r.get("wind_speed_mph", "")
        system = r.get("weather_system", "") or r.get("astronomical_event", "")
        notes = r.get("raw_notes", "")

        table_rows_html += f"""
        <tr class="hover:bg-slate-50 border-b border-slate-100 text-xs">
          <td class="px-3 py-2.5 font-mono text-slate-700">{date_str}</td>
          <td class="px-3 py-2.5 font-mono font-bold text-sky-900">{stage_str} ft</td>
          <td class="px-3 py-2.5 font-mono font-bold {'text-orange-600' if float(depth_str or 0) > 4 else 'text-slate-700'}">{depth_str}"</td>
          <td class="px-3 py-2.5 text-slate-600">{wind_dir} {wind_spd}</td>
          <td class="px-3 py-2.5 text-slate-600 font-medium">{system}</td>
          <td class="px-3 py-2.5 text-slate-500 truncate max-w-xs">{notes}</td>
        </tr>
        """

    return f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Storm History & Data Archive — Mathews County Flood Monitor</title>
  <meta name="description" content="Historical storm comparisons (Helene, Ian, Idalia, Ophelia) and open data downloads for Mathews County, VA.">
  
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
    body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }}
    .font-mono {{ font-family: 'JetBrains Mono', monospace; }}
  </style>
</head>
<body class="bg-slate-50 text-slate-900 min-h-screen flex flex-col antialiased">

  {navbar_html}

  <main class="flex-grow max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-12 w-full">

    <!-- Hero Header -->
    <section class="space-y-3">
      <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sky-100 text-sky-800 text-xs font-bold uppercase tracking-wider">
        <i class="fa-solid fa-database"></i> Storm History & Open Data
      </div>
      <h1 class="text-3xl sm:text-4xl lg:text-5xl font-black text-slate-900 tracking-tight leading-tight">
        Historical Storm Archive & Data Center
      </h1>
      <p class="text-lg text-slate-600 leading-relaxed max-w-3xl">
        Transparent open data access: browse 141 ground-truth observer measurements from 2021 to 2024 and download our live automated datasets.
      </p>
    </section>

    <!-- 1. NOTABLE STORMS COMPARISON -->
    <section class="space-y-4">
      <div class="flex items-center justify-between">
        <h2 class="text-xl sm:text-2xl font-bold text-slate-900 flex items-center gap-2">
          <i class="fa-solid fa-hurricane text-sky-600"></i>
          Major Storm Benchmark Events
        </h2>
        <span class="text-xs text-slate-500">2021–2024 Observed</span>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {storm_cards_html}
      </div>
    </section>

    <!-- 2. DATA DOWNLOAD CENTER -->
    <section class="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-5">
      <div>
        <h2 class="text-xl sm:text-2xl font-bold text-slate-900 flex items-center gap-2">
          <i class="fa-solid fa-file-arrow-down text-sky-600"></i>
          Download Raw Datasets
        </h2>
        <p class="text-xs sm:text-sm text-slate-500 mt-1">
          All data generated by this project is public and freely accessible for researchers, neighbors, and planners.
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
        <a href="ground_truth_observations.csv" class="p-5 rounded-xl border border-slate-200 bg-slate-50 hover:bg-sky-50/50 hover:border-sky-300 transition group flex flex-col justify-between">
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold text-sky-700 uppercase">Ground Truth</span>
              <i class="fa-solid fa-download text-slate-400 group-hover:text-sky-600 transition"></i>
            </div>
            <div class="font-bold text-slate-900 text-sm">ground_truth_observations.csv</div>
            <p class="text-xs text-slate-600 leading-relaxed">
              The original 141 observer measurements transcribed from handwritten notes (2021–2024).
            </p>
          </div>
          <div class="text-[11px] text-slate-400 font-mono pt-4">141 records &bull; Verified</div>
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
          <h2 class="text-xl font-bold text-slate-900">Ground-Truth Observation Explorer</h2>
          <p class="text-xs sm:text-sm text-slate-500">Showing 141 human verification records across 4 years of storm seasons.</p>
        </div>
        <div class="text-xs text-slate-500">
          Showing 60 most recent events
        </div>
      </div>

      <div class="overflow-x-auto border border-slate-200 rounded-xl">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-slate-100 text-slate-700 text-[11px] font-bold uppercase tracking-wider border-b border-slate-200">
              <th class="px-3 py-2.5">Date</th>
              <th class="px-3 py-2.5">Ware River Stage</th>
              <th class="px-3 py-2.5">Flood Depth</th>
              <th class="px-3 py-2.5">Winds</th>
              <th class="px-3 py-2.5">System / Event</th>
              <th class="px-3 py-2.5">Observer Notes</th>
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
# MAIN DRIVER FUNCTION
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Generate comprehensive multi-page coastal flood portal.")
    parser.add_argument("--status-json", default="latest_status.json", help="Path to latest status JSON")
    parser.add_argument("--obs-csv", default="realtime_recent_observations.csv", help="Path to observations CSV")
    parser.add_argument("--fcst-csv", default="forecast_48h.csv", help="Path to forecast CSV")
    parser.add_argument("--ground-truth", default="ground_truth_observations.csv", help="Path to ground truth CSV")
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

    # 2. Build about.html
    about_html = build_about_html(status)
    with open("about.html", "w", encoding="utf-8") as f:
        f.write(about_html)
    print("[+] Generated: about.html (The Story, Handwritten Notebooks & Physical Breakthroughs)")

    # 3. Build guide.html
    guide_html = build_guide_html(status)
    with open("guide.html", "w", encoding="utf-8") as f:
        f.write(guide_html)
    print("[+] Generated: guide.html (4 Flood Severity Tiers, Vehicle Safety & Plain-English Glossary)")

    # 4. Build data.html
    data_html = build_data_html(status, ground_truth_rows, obs_rows)
    with open("data.html", "w", encoding="utf-8") as f:
        f.write(data_html)
    print("[+] Generated: data.html (Historical Storm Comparisons & Raw Data Downloads)")

if __name__ == "__main__":
    main()
