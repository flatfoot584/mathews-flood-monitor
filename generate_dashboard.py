#!/usr/bin/env python3
"""
generate_dashboard.py — Standalone Interactive Coastal Flood Dashboard Generator
for Mathews County, Virginia Flood Prediction System.

Generates flood_dashboard.html: a self-contained, beautiful, mobile-responsive HTML dashboard.
Embeds real-time observations, 48-hr hydrograph forecast, risk tiers, and property impact breakdown.
Can be opened directly in any browser (Safari, Chrome, Firefox) via double-click with zero server setup!

Author: Antigravity Assistant for Mathews County Flood Prediction Project
"""

import os
import json
import csv
import argparse
from datetime import datetime

def load_data(status_json_path, obs_csv_path, fcst_csv_path):
    with open(status_json_path, "r", encoding="utf-8") as f:
        status = json.load(f)

    obs_rows = []
    if os.path.exists(obs_csv_path):
        with open(obs_csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            obs_rows = list(reader)

    fcst_rows = []
    if os.path.exists(fcst_csv_path):
        with open(fcst_csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fcst_rows = list(reader)

    return status, obs_rows, fcst_rows

def build_dashboard_html(status, obs_rows, fcst_rows):
    curr = status.get("current_conditions", {})
    outl = status.get("forecast_48h_outlook", {})

    stage = curr.get("ware_river_stage_mllw_ft", "N/A")
    stage_navd = curr.get("ware_river_stage_navd88_ft", "N/A")
    depth = curr.get("estimated_local_flood_depth_in", 0.0)
    tier = curr.get("flood_risk_tier", 0)
    tier_lbl = curr.get("flood_risk_label", "Tier 0 (Normal / Safe)")
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
    peak_tier_lbl = outl.get("peak_risk_label", "Normal")
    peak_passability = outl.get("peak_vehicle_passability", "ALL VEHICLES PASSABLE")
    hours_above = outl.get("hours_at_or_above_action_stage", 0)
    advisory = outl.get("advisory_summary", "")

    # Badge colors
    badge_colors = {
        0: ("#10B981", "rgba(16, 185, 129, 0.15)", "NORMAL / SAFE"),
        1: ("#F59E0B", "rgba(245, 158, 11, 0.15)", "TIER 1 — NUISANCE FLOOD"),
        2: ("#F97316", "rgba(249, 115, 22, 0.15)", "TIER 2 — MODERATE INUNDATION"),
        3: ("#EF4444", "rgba(239, 68, 68, 0.15)", "TIER 3 — SEVERE FLOOD WARNING")
    }
    badge_color, badge_bg, badge_text = badge_colors.get(max(tier, peak_tier), badge_colors[0])

    # Hydrograph series data preparation
    hydro_labels = []
    obs_stages = []
    fcst_stages = []
    inundation_depths = []

    for r in obs_rows:
        t_loc = r.get("timestamp_local", "").replace(" EDT", "").replace(" EST", "")
        try:
            parts = t_loc.split()
            short_t = parts[0][5:] + " " + parts[1][:5]
        except Exception:
            short_t = t_loc
        hydro_labels.append(short_t)
        v = r.get("ware_river_stage_mllw_ft", "")
        obs_stages.append(float(v) if v else None)
        fcst_stages.append(None)
        inundation_depths.append(0.0)

    # Now point connecting past and future
    if obs_stages and obs_stages[-1] is not None:
        last_obs_val = obs_stages[-1]
    else:
        last_obs_val = None

    first_fcst = True
    for r in fcst_rows:
        t_loc = r.get("timestamp_local", "").replace(" EDT", "").replace(" EST", "")
        try:
            parts = t_loc.split()
            short_t = parts[0][5:] + " " + parts[1][:5]
        except Exception:
            short_t = t_loc
        hydro_labels.append(short_t)
        obs_stages.append(None)
        
        stg_v = r.get("forecast_stage_mllw_ft", "")
        stg_float = float(stg_v) if stg_v else None
        
        # Connect bridge
        if first_fcst and last_obs_val is not None:
            fcst_stages.append(last_obs_val)
            first_fcst = False
        else:
            fcst_stages.append(stg_float)
            
        dp_v = r.get("compound_flood_depth_in", r.get("estimated_flood_depth_in", ""))
        inundation_depths.append(float(dp_v) if dp_v else 0.0)

    # Identify upcoming high tides from forecast
    high_tides = []
    for i in range(1, len(fcst_rows) - 1):
        prev_s = float(fcst_rows[i-1]["forecast_stage_mllw_ft"] or 0)
        curr_s = float(fcst_rows[i]["forecast_stage_mllw_ft"] or 0)
        next_s = float(fcst_rows[i+1]["forecast_stage_mllw_ft"] or 0)
        if curr_s >= prev_s and curr_s >= next_s and curr_s > 2.5:
            high_tides.append({
                "time": fcst_rows[i]["timestamp_local"],
                "stage": curr_s,
                "depth": float(fcst_rows[i].get("compound_flood_depth_in", fcst_rows[i].get("estimated_flood_depth_in", 0)) or 0),
                "tier": fcst_rows[i]["risk_tier"],
                "label": fcst_rows[i]["risk_label"],
                "passability": fcst_rows[i].get("vehicle_passability", "PASSABLE"),
                "wind": f"{fcst_rows[i]['nws_wind_speed_mph']} mph {fcst_rows[i]['nws_wind_cardinal']}"
            })

    high_tides_rows_html = ""
    for ht in high_tides[:4]:
        tier_col = "#10B981" if ht["tier"] == 0 else "#F59E0B" if ht["tier"] == 1 else "#F97316" if ht["tier"] == 2 else "#EF4444"
        high_tides_rows_html += f"""
        <tr class="border-b border-slate-700/50 hover:bg-slate-800/40 transition">
          <td class="py-3 px-4 font-medium text-slate-200">{ht['time']}</td>
          <td class="py-3 px-4 font-mono font-semibold text-cyan-400">{ht['stage']:.2f} ft</td>
          <td class="py-3 px-4 font-mono font-bold" style="color: {tier_col};">{ht['depth']:.1f}"</td>
          <td class="py-3 px-4 text-xs font-semibold uppercase tracking-wider" style="color: {tier_col};">{ht['label']}</td>
          <td class="py-3 px-4 text-xs text-slate-300 font-medium">{ht['passability']}</td>
          <td class="py-3 px-4 text-slate-400">{ht['wind']}</td>
        </tr>
        """

    # Live Sector HTML
    sector_cards_html = ""
    sector_keys_order = ["ditches", "road_apron", "main_driveway", "yard_lawn", "garage_foundation"]
    for sk in sector_keys_order:
        sec = sectors.get(sk, {})
        if not sec:
            continue
        is_sub = sec.get("is_submerged", False)
        depth_val = sec.get("depth_in", 0.0)
        s_col = "#EF4444" if depth_val >= 6.0 else "#F59E0B" if depth_val > 0 else "#10B981"
        s_bg = "rgba(239, 68, 68, 0.15)" if depth_val >= 6.0 else "rgba(245, 158, 11, 0.15)" if depth_val > 0 else "rgba(16, 185, 129, 0.1)"
        sector_cards_html += f"""
        <div class="p-3.5 rounded-xl border flex items-center justify-between transition hover:border-slate-600"
             style="background-color: {s_bg}; border-color: {s_col}40;">
          <div>
            <div class="text-xs font-bold text-white flex items-center gap-2">
              <span class="w-2 h-2 rounded-full" style="background-color: {s_col};"></span>
              {sec.get('name', sk)}
            </div>
            <div class="text-[11px] text-slate-400 mt-0.5">
              Invert: <span class="font-mono text-slate-300">{sec.get('invert_mllw_ft')} ft MLLW</span> ({sec.get('invert_navd88_ft')} ft NAVD88)
            </div>
          </div>
          <div class="text-right">
            <span class="text-lg font-black font-mono tracking-tight" style="color: {s_col};">{depth_val:.1f}"</span>
            <div class="text-[10px] font-bold uppercase tracking-wider" style="color: {s_col};">{sec.get('status', 'DRY')}</div>
          </div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Mathews County, VA — Coastal Flood Prediction Dashboard</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');
    body {{ font-family: 'Inter', sans-serif; }}
    .font-mono {{ font-family: 'JetBrains Mono', monospace; }}
    .glass {{ background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); }}
    .glass-card {{ background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(16px); border: 1px solid rgba(51, 65, 85, 0.6); }}
  </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen p-4 sm:p-6 lg:p-8 antialiased selection:bg-cyan-500 selection:text-white">

  <!-- Top Container -->
  <div class="max-w-7xl mx-auto space-y-6">

    <!-- Header Section -->
    <header class="glass rounded-2xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-2xl">
      <div>
        <div class="flex items-center gap-2">
          <span class="inline-block w-3 h-3 rounded-full animate-ping bg-emerald-400"></span>
          <span class="text-xs font-bold uppercase tracking-widest text-emerald-400">Hybrid Hydrodynamic–ML Pipeline</span>
        </div>
        <h1 class="text-2xl sm:text-3xl font-extrabold tracking-tight mt-1 bg-gradient-to-r from-cyan-400 via-sky-300 to-indigo-300 bg-clip-text text-transparent">
          Mathews County Coastal Flood Monitor
        </h1>
        <p class="text-xs sm:text-sm text-slate-400 mt-1">
          Ware River Basin & Mobjack Bay • Compound Tidal & Pluvial Prediction System
        </p>
      </div>

      <!-- Live Advisory Badge -->
      <div class="flex flex-col sm:items-end">
        <div class="px-4 py-2 rounded-xl border font-bold text-sm tracking-wide shadow-lg flex items-center gap-2"
             style="background-color: {badge_bg}; border-color: {badge_color}; color: {badge_color};">
          <span class="w-2.5 h-2.5 rounded-full" style="background-color: {badge_color};"></span>
          {badge_text}
        </div>
        <span class="text-xs text-slate-400 mt-2">
          Observation: <span class="text-slate-200 font-mono">{curr.get('observation_timestamp_local', 'Now')}</span>
        </span>
      </div>
    </header>

    <!-- Advisory Banner if warning -->
    <div class="rounded-xl p-4 border flex items-start gap-3 shadow-lg"
         style="background-color: {badge_bg}; border-color: {badge_color};">
      <svg class="w-6 h-6 shrink-0 mt-0.5" fill="none" stroke="{badge_color}" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
      </svg>
      <div>
        <div class="flex items-center gap-3">
          <h4 class="font-bold text-sm" style="color: {badge_color};">48-Hour Coastal Flood Advisory:</h4>
          <span class="text-xs px-2 py-0.5 rounded bg-slate-900 font-semibold text-slate-300 border border-slate-700">{passability}</span>
        </div>
        <p class="text-sm text-slate-200 mt-1 leading-relaxed">{advisory}</p>
        <p class="text-xs text-slate-400 mt-1 italic">Vehicle Guidance: {passability_desc}</p>
      </div>
    </div>

    <!-- 4 Key Metric Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      
      <!-- Card 1: Ware River Stage -->
      <div class="glass-card rounded-2xl p-5 hover:border-cyan-500/40 transition">
        <div class="flex justify-between items-center text-xs font-semibold text-slate-400 uppercase tracking-wider">
          <span>Ware River Stage</span>
          <span class="text-cyan-400 font-mono">WRVV2</span>
        </div>
        <div class="mt-3 flex items-baseline gap-2">
          <span class="text-4xl font-black font-mono tracking-tight text-white">{stage}</span>
          <span class="text-lg font-medium text-slate-400">ft MLLW</span>
        </div>
        <div class="mt-2 text-xs text-slate-400 flex justify-between border-t border-slate-800 pt-2">
          <span>NAVD88: <strong class="text-slate-200 font-mono">{stage_navd} ft</strong></span>
          <span>Action: <strong class="text-amber-400 font-mono">4.0 ft</strong></span>
        </div>
      </div>

      <!-- Card 2: Property Flood Depth -->
      <div class="glass-card rounded-2xl p-5 hover:border-cyan-500/40 transition">
        <div class="flex justify-between items-center text-xs font-semibold text-slate-400 uppercase tracking-wider">
          <span>Compound Depth</span>
          <span class="text-emerald-400 font-mono">Tide + Rain</span>
        </div>
        <div class="mt-3 flex items-baseline gap-2">
          <span class="text-4xl font-black font-mono tracking-tight" style="color: {badge_color};">{depth}</span>
          <span class="text-lg font-medium text-slate-400">inches</span>
        </div>
        <div class="mt-2 text-xs text-slate-400 flex justify-between border-t border-slate-800 pt-2">
          <span>Access: <strong class="text-slate-200">{passability}</strong></span>
          <span>Zero Mark: <strong class="text-slate-300 font-mono">3.99 ft</strong></span>
        </div>
      </div>

      <!-- Card 3: Wind Conditions -->
      <div class="glass-card rounded-2xl p-5 hover:border-cyan-500/40 transition">
        <div class="flex justify-between items-center text-xs font-semibold text-slate-400 uppercase tracking-wider">
          <span>Wind Forcing</span>
          <span class="text-sky-400 font-mono">Yorktown USCG</span>
        </div>
        <div class="mt-3 flex items-baseline gap-2">
          <span class="text-4xl font-black font-mono tracking-tight text-white">{wind_spd}</span>
          <span class="text-lg font-medium text-slate-400">mph</span>
          <span class="text-sm font-bold text-sky-400 font-mono ml-auto">{wind_dir} ({wind_deg}°)</span>
        </div>
        <div class="mt-2 text-xs text-slate-400 flex justify-between border-t border-slate-800 pt-2">
          <span>Along-Bay Push: <strong class="text-cyan-300 font-mono">{along_bay} mph</strong></span>
          <span>Gusts: <strong class="text-amber-300 font-mono">{wind_gst} mph</strong></span>
        </div>
      </div>

      <!-- Card 4: Storm Surge & Pressure -->
      <div class="glass-card rounded-2xl p-5 hover:border-cyan-500/40 transition">
        <div class="flex justify-between items-center text-xs font-semibold text-slate-400 uppercase tracking-wider">
          <span>Bay Storm Surge</span>
          <span class="text-indigo-400 font-mono">Windmill Pt</span>
        </div>
        <div class="mt-3 flex items-baseline gap-2">
          <span class="text-4xl font-black font-mono tracking-tight text-white">+{surge}</span>
          <span class="text-lg font-medium text-slate-400">ft residual</span>
        </div>
        <div class="mt-2 text-xs text-slate-400 flex justify-between border-t border-slate-800 pt-2">
          <span>Barometer: <strong class="text-slate-200 font-mono">{baro} mb</strong></span>
          <span>Peak 48h: <strong class="text-cyan-400 font-mono">{peak_stage} ft</strong></span>
        </div>
      </div>

    </div>

    <!-- Main Hydrograph Chart Section -->
    <div class="glass-card rounded-2xl p-6 shadow-2xl">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h2 class="text-lg sm:text-xl font-bold text-white flex items-center gap-2">
            <span>Continuous 96-Hour Hydrograph</span>
            <span class="text-xs px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800 font-normal">Past 48h Observed + Next 48h Hybrid Forecast</span>
          </h2>
          <p class="text-xs text-slate-400 mt-1">
            Solid line shows continuous observations. Dashed cyan shows Hybrid Hydrodynamic–ML stage (NOAA NWPS CBOFS + local wind stress set-up).
          </p>
        </div>
        <div class="flex items-center gap-4 text-xs font-semibold">
          <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-cyan-500"></span> Observed</span>
          <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-sky-300"></span> Hybrid Forecast</span>
          <span class="flex items-center gap-1.5"><span class="w-3 h-0.5 bg-amber-500"></span> 4.0 ft Action</span>
          <span class="flex items-center gap-1.5"><span class="w-3 h-0.5 bg-rose-500"></span> 4.8 ft Severe</span>
        </div>
      </div>

      <!-- Chart Container -->
      <div class="relative w-full h-80 sm:h-96">
        <canvas id="hydrographChart"></canvas>
      </div>
    </div>

    <!-- Upcoming High Tides Table & Micro-Topography -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

      <!-- High Tides Table (2 Cols) -->
      <div class="lg:col-span-2 glass-card rounded-2xl p-6 shadow-xl">
        <h3 class="text-base font-bold text-white mb-4 flex items-center gap-2">
          <svg class="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
          Upcoming High Tide Peaks (Next 48 Hours)
        </h3>
        <div class="overflow-x-auto">
          <table class="w-full text-left text-sm">
            <thead>
              <tr class="text-xs text-slate-400 uppercase tracking-wider border-b border-slate-700">
                <th class="py-3 px-4">Local Peak Time</th>
                <th class="py-3 px-4">Hybrid Stage</th>
                <th class="py-3 px-4">Compound Depth</th>
                <th class="py-3 px-4">Impact Tier</th>
                <th class="py-3 px-4">Vehicle Access</th>
                <th class="py-3 px-4">NWS Winds</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-800">
              {high_tides_rows_html}
            </tbody>
          </table>
        </div>
      </div>

      <!-- Live Micro-Topography Elevation Profile (1 Col) -->
      <div class="glass-card rounded-2xl p-6 shadow-xl space-y-4">
        <h3 class="text-base font-bold text-white flex items-center gap-2">
          <svg class="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/></svg>
          Property Sector Elevation Profile
        </h3>
        <p class="text-xs text-slate-400">Current inundation status across benchmark sectors:</p>
        
        <div class="space-y-2.5">
          {sector_cards_html}
        </div>
      </div>

    </div>

    <!-- Operational Commands & System Specs -->
    <footer class="glass rounded-2xl p-6 text-xs text-slate-400 flex flex-col sm:flex-row items-center justify-between gap-4">
      <div>
        <span>Mathews County Flood Prediction Project • Hybrid Hydrodynamic–ML Pipeline</span>
        <div class="mt-1 text-slate-500">Gauge WRVV2 (USGS 01670180) • Met Yorktown (8637689) • Surge Windmill Pt (8636580)</div>
      </div>
      <div class="font-mono text-cyan-400 bg-slate-900 px-3 py-1.5 rounded-lg border border-slate-800">
        CLI: python3 ingest_realtime.py && python3 generate_dashboard.py
      </div>
    </footer>

  </div>

  <!-- Chart.js Render Script -->
  <script>
    const labels = {json.dumps(hydro_labels)};
    const obsData = {json.dumps(obs_stages)};
    const fcstData = {json.dumps(fcst_stages)};

    const ctx = document.getElementById('hydrographChart').getContext('2d');
    new Chart(ctx, {{
      type: 'line',
      data: {{
        labels: labels,
        datasets: [
          {{
            label: 'Observed Stage (ft)',
            data: obsData,
            borderColor: '#06b6d4',
            backgroundColor: 'rgba(6, 182, 212, 0.1)',
            fill: true,
            borderWidth: 2.5,
            pointRadius: 0,
            pointHoverRadius: 5,
            tension: 0.3
          }},
          {{
            label: 'Hybrid Forecast (ft)',
            data: fcstData,
            borderColor: '#38bdf8',
            borderDash: [5, 5],
            backgroundColor: 'rgba(56, 189, 248, 0.05)',
            fill: true,
            borderWidth: 2.5,
            pointRadius: 0,
            pointHoverRadius: 5,
            tension: 0.3
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        interaction: {{
          mode: 'index',
          intersect: false
        }},
        plugins: {{
          legend: {{ display: false }},
          tooltip: {{
            backgroundColor: '#0f172a',
            borderColor: '#334155',
            borderWidth: 1,
            titleColor: '#f8fafc',
            bodyColor: '#38bdf8',
            padding: 12,
            callbacks: {{
              label: function(context) {{
                let val = context.parsed.y;
                if (val === null || isNaN(val)) return null;
                let depth = Math.max(0, 10.95 * val - 43.69);
                return context.dataset.label + ': ' + val.toFixed(2) + ' ft (' + depth.toFixed(1) + '\" depth)';
              }}
            }}
          }}
        }},
        scales: {{
          x: {{
            grid: {{ color: 'rgba(51, 65, 85, 0.3)' }},
            ticks: {{
              color: '#94a3b8',
              maxTicksLimit: 12,
              font: {{ family: 'JetBrains Mono', size: 10 }}
            }}
          }},
          y: {{
            min: 0,
            max: 5.5,
            grid: {{ color: 'rgba(51, 65, 85, 0.3)' }},
            ticks: {{
              color: '#94a3b8',
              font: {{ family: 'JetBrains Mono', size: 11 }},
              callback: function(value) {{ return value.toFixed(1) + ' ft'; }}
            }}
          }}
        }}
      }}
    }});
  </script>
</body>
</html>
"""
    return html

def main():
    parser = argparse.ArgumentParser(description="Generate interactive standalone HTML flood dashboard.")
    parser.add_argument("--status-json", default="latest_status.json", help="Path to latest status JSON")
    parser.add_argument("--obs-csv", default="realtime_recent_observations.csv", help="Path to observations CSV")
    parser.add_argument("--fcst-csv", default="forecast_48h.csv", help="Path to forecast CSV")
    parser.add_argument("--output", default="flood_dashboard.html", help="Path to write dashboard HTML")
    args = parser.parse_args()

    status, obs_rows, fcst_rows = load_data(args.status_json, args.obs_csv, args.fcst_csv)
    html_content = build_dashboard_html(status, obs_rows, fcst_rows)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Successfully generated standalone dashboard: {args.output}")

    # Also write index.html for root web server hosting (GitHub Pages)
    if args.output != "index.html":
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        print("Successfully synced: index.html (for GitHub Pages)")

if __name__ == "__main__":
    main()

