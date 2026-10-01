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
    passability_desc = curr.get("vehicle_passability_desc", "Normal conditions for all passenger vehicles.")
    sectors = curr.get("site_sectors", {})

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

    <!-- 3. INTERACTIVE LEAFLET FLOOD MAP SECTION -->
    <section id="map-section" class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      <div class="p-5 sm:p-6 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-50/50">
        <div>
          <div class="flex items-center gap-2">
            <h2 class="text-lg sm:text-xl font-bold text-slate-900">Mathews County Real-Time Flood Map</h2>
            <span class="px-2.5 py-0.5 text-xs font-semibold bg-sky-100 text-sky-800 rounded-full">Interactive GIS</span>
          </div>
          <p class="text-xs sm:text-sm text-slate-500 mt-0.5">
            Visualizing tidal gauge networks, wind vectors, and property elevation flood zones (Green = Safe, Yellow = Swales Full, Orange = Driveway Inundated, Red = Severe).
          </p>
        </div>

        <!-- Map Layer Toggle Buttons -->
        <div class="flex items-center gap-2 bg-slate-200/80 p-1 rounded-xl self-start sm:self-auto text-xs font-medium">
          <button id="btn-map-current" class="px-3 py-1.5 rounded-lg bg-white shadow-sm text-slate-900 font-semibold transition">
            <i class="fa-solid fa-location-dot text-emerald-600 mr-1"></i> Current ({stage} ft)
          </button>
          <button id="btn-map-peak" class="px-3 py-1.5 rounded-lg text-slate-600 hover:text-slate-900 transition">
            <i class="fa-solid fa-bolt text-amber-500 mr-1"></i> Peak 48h ({peak_stage} ft)
          </button>
        </div>
      </div>

      <!-- The Leaflet Map Canvas -->
      <div class="relative">
        <div id="flood-map"></div>

        <!-- Floating Map Legend -->
        <div class="absolute bottom-5 right-5 z-[400] bg-white/95 backdrop-blur-md p-3.5 rounded-xl border border-slate-200 shadow-lg text-xs space-y-1.5 pointer-events-auto max-w-[210px]">
          <div class="font-bold text-slate-900 text-[11px] uppercase tracking-wider mb-1 flex items-center justify-between">
            <span>Risk Severity Legend</span>
            <i class="fa-solid fa-layer-group text-slate-400"></i>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-3.5 h-3.5 rounded bg-emerald-500 shrink-0"></span>
            <span class="text-slate-700 font-medium">Safe / Dry (&lt; 4.0')</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-3.5 h-3.5 rounded bg-amber-500 shrink-0"></span>
            <span class="text-slate-700 font-medium">Nuisance / Ditch Full (4.0-4.3')</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-3.5 h-3.5 rounded bg-orange-500 shrink-0"></span>
            <span class="text-slate-700 font-medium">Driveway Inundated (4.4-4.7')</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-3.5 h-3.5 rounded bg-red-600 shrink-0"></span>
            <span class="text-slate-700 font-medium">Property Submerged (&ge; 4.8')</span>
          </div>
        </div>
      </div>

      <div class="p-4 bg-slate-50 border-t border-slate-200 text-xs text-slate-600 flex flex-wrap items-center justify-between gap-3">
        <div class="flex items-center gap-4">
          <span class="flex items-center gap-1.5"><i class="fa-solid fa-circle text-[8px] text-sky-600"></i> Click any sensor pin or property polygon on the map to view detailed depths and sensor readings.</span>
        </div>
        <div class="text-slate-400 text-[11px]">Basemap &copy; OpenStreetMap & CartoDB Positron</div>
      </div>
    </section>

    <!-- 4. PROPERTY ELEVATION CROSS-SECTION (MICRO-TOPOGRAPHY PROFILE) -->
    <section class="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-5">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h2 class="text-lg font-bold text-slate-900 flex items-center gap-2">
            <i class="fa-solid fa-stairs text-sky-600"></i>
            Property Elevation Cross-Section Profile
          </h2>
          <p class="text-xs sm:text-sm text-slate-500">
            How water breaches our site as Ware River stage climbs (Threshold: 3.99 ft MLLW = 2.35 ft NAVD88).
          </p>
        </div>
        <div class="text-xs font-mono bg-slate-100 text-slate-700 px-3 py-1.5 rounded-lg self-start sm:self-auto font-medium">
          Ditch Tipping Point: 3.99' MLLW
        </div>
      </div>

      <!-- Sector Progress Bars -->
      <div class="space-y-3.5 pt-2">
        <!-- Sector 1: Ditches -->
        <div>
          <div class="flex justify-between text-xs font-medium mb-1">
            <span class="text-slate-700 font-semibold"><i class="fa-solid fa-water text-sky-500 mr-1.5"></i> 1. Tidal Ditches & Marsh Invert (Elev: 2.50' MLLW / 0.86' NAVD88)</span>
            <span class="font-mono font-semibold {'text-sky-700' if sectors.get('ditches', {}).get('depth_in', 0) > 0 else 'text-slate-400'}">
              {sectors.get('ditches', {}).get('depth_in', 0)}" Water ({sectors.get('ditches', {}).get('status', 'NORMAL')})
            </span>
          </div>
          <div class="w-full bg-slate-100 h-3 rounded-full overflow-hidden">
            <div class="bg-sky-500 h-full rounded-full transition-all" style="width: {min(100, max(5, int(sectors.get('ditches', {}).get('depth_in', 0) * 10)))}%"></div>
          </div>
        </div>

        <!-- Sector 2: Road Apron / Culvert -->
        <div>
          <div class="flex justify-between text-xs font-medium mb-1">
            <span class="text-slate-700 font-semibold"><i class="fa-solid fa-road text-amber-500 mr-1.5"></i> 2. Road Shoulder & Culvert Invert (Elev: 4.00' MLLW / 2.36' NAVD88)</span>
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
            <span class="text-slate-700 font-semibold"><i class="fa-solid fa-car text-orange-500 mr-1.5"></i> 3. Main Driveway — Vehicle Access Route (Elev: 4.40' MLLW / 2.76' NAVD88)</span>
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
            <span class="text-slate-700 font-semibold"><i class="fa-solid fa-tree text-emerald-600 mr-1.5"></i> 4. Residential Lawn & Grounds (Elev: 4.60' MLLW / 2.96' NAVD88)</span>
            <span class="font-mono font-semibold {'text-red-700 font-bold' if sectors.get('lawn_grounds', {}).get('depth_in', 0) > 0 else 'text-emerald-700'}">
              {sectors.get('lawn_grounds', {}).get('depth_in', 0)}" Water ({sectors.get('lawn_grounds', {}).get('status', 'DRY')})
            </span>
          </div>
          <div class="w-full bg-slate-100 h-3 rounded-full overflow-hidden">
            <div class="{'bg-red-500' if sectors.get('lawn_grounds', {}).get('depth_in', 0) > 0 else 'bg-emerald-500'} h-full rounded-full transition-all" style="width: {min(100, max(2, int(sectors.get('lawn_grounds', {}).get('depth_in', 0) * 15)))}%"></div>
          </div>
        </div>

        <!-- Sector 5: Garage High Ground -->
        <div>
          <div class="flex justify-between text-xs font-medium mb-1">
            <span class="text-slate-700 font-semibold"><i class="fa-solid fa-house text-blue-600 mr-1.5"></i> 5. Garage Apron & Residence High Ground (Elev: 4.90' MLLW / 3.26' NAVD88)</span>
            <span class="font-mono font-semibold {'text-red-700 font-bold' if sectors.get('garage_high_ground', {}).get('depth_in', 0) > 0 else 'text-emerald-700'}">
              {sectors.get('garage_high_ground', {}).get('depth_in', 0)}" Water ({sectors.get('garage_high_ground', {}).get('status', 'SAFE')})
            </span>
          </div>
          <div class="w-full bg-slate-100 h-3 rounded-full overflow-hidden">
            <div class="{'bg-red-600' if sectors.get('garage_high_ground', {}).get('depth_in', 0) > 0 else 'bg-emerald-500'} h-full rounded-full transition-all" style="width: {min(100, max(2, int(sectors.get('garage_high_ground', {}).get('depth_in', 0) * 15)))}%"></div>
          </div>
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

    <!-- 6. REAL-TIME SENSOR NETWORK CARDS -->
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

    // 1. LEAFLET INTERACTIVE MAP
    const map = L.map('flood-map', {{
      center: [37.385, -76.435],
      zoom: 11,
      scrollWheelZoom: false
    }});

    // Add CartoDB Positron / Voyager Neutral Basemap
    L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png', {{
      attribution: '&copy; OpenStreetMap contributors & CartoDB',
      maxZoom: 18
    }}).addTo(map);

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

    // Property Micro-Topography Zones (Near Ware River / Mobjack corridor)
    const propertyZones = [
      {{
        name: "Tidal Ditches & Marsh Inlets",
        elev: 2.50,
        coords: [
          [37.4010, -76.4420], [37.4035, -76.4405],
          [37.4045, -76.4430], [37.4020, -76.4450]
        ]
      }},
      {{
        name: "Road Shoulder & Culvert Swale",
        elev: 4.00,
        coords: [
          [37.4035, -76.4405], [37.4060, -76.4385],
          [37.4070, -76.4415], [37.4045, -76.4430]
        ]
      }},
      {{
        name: "Main Driveway Access Route",
        elev: 4.40,
        coords: [
          [37.4060, -76.4385], [37.4085, -76.4365],
          [37.4095, -76.4395], [37.4070, -76.4415]
        ]
      }},
      {{
        name: "Residential Lawn & Grounds",
        elev: 4.60,
        coords: [
          [37.4085, -76.4365], [37.4110, -76.4345],
          [37.4120, -76.4375], [37.4095, -76.4395]
        ]
      }},
      {{
        name: "Garage Apron & Residence High Ground",
        elev: 4.90,
        coords: [
          [37.4110, -76.4345], [37.4130, -76.4330],
          [37.4140, -76.4360], [37.4120, -76.4375]
        ]
      }}
    ];

    let zonePolygons = [];

    function renderPropertyZones(stageVal) {{
      zonePolygons.forEach(p => map.removeLayer(p));
      zonePolygons = [];

      propertyZones.forEach(z => {{
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
          statusTxt = 'Caution: Water within 3 inches of brim';
        }}

        const poly = L.polygon(z.coords, {{
          color: color,
          weight: 2,
          fillColor: color,
          fillOpacity: 0.55
        }}).addTo(map);

        poly.bindPopup(`
          <div class="p-1 space-y-1">
            <div class="font-bold text-sm text-slate-900">${{z.name}}</div>
            <div class="text-xs text-slate-500">Elevation: ${{z.elev}}' MLLW</div>
            <div class="text-xs font-semibold" style="color: ${{color}}">${{statusTxt}}</div>
          </div>
        `);

        zonePolygons.push(poly);
      }});
    }}

    // Initial render with current conditions
    renderPropertyZones(parseFloat(curr.ware_river_stage_mllw_ft || 3.1));

    // Toggle button handlers
    const btnCurrent = document.getElementById('btn-map-current');
    const btnPeak = document.getElementById('btn-map-peak');

    btnCurrent.addEventListener('click', () => {{
      btnCurrent.classList.add('bg-white', 'shadow-sm', 'font-semibold', 'text-slate-900');
      btnCurrent.classList.remove('text-slate-600');
      btnPeak.classList.remove('bg-white', 'shadow-sm', 'font-semibold', 'text-slate-900');
      btnPeak.classList.add('text-slate-600');
      renderPropertyZones(parseFloat(curr.ware_river_stage_mllw_ft || 3.1));
    }});

    btnPeak.addEventListener('click', () => {{
      btnPeak.classList.add('bg-white', 'shadow-sm', 'font-semibold', 'text-slate-900');
      btnPeak.classList.remove('text-slate-600');
      btnCurrent.classList.remove('bg-white', 'shadow-sm', 'font-semibold', 'text-slate-900');
      btnCurrent.classList.add('text-slate-600');
      renderPropertyZones(parseFloat(outl.peak_forecast_stage_mllw_ft || 3.5));
    }});

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
