#!/usr/bin/env python3
"""
check_alerts.py — Coastal Flood Alert Generator & Hazard Monitor
for Mathews County, Virginia Flood Prediction System.

Inspects latest_status.json (produced by ingest_realtime.py) and generates
standardized high-priority alert bulletins when flood thresholds are approached or exceeded.

Threshold Tiers:
- Tier 0: Normal / Safe (< 4.0 ft) -> 0" flooding
- Tier 1: Nuisance / Ditch Full (4.0 - 4.3 ft) -> 1" - 4" on property edges/ditches
- Tier 2: Moderate Inundation (4.4 - 4.7 ft) -> 5" - 8" on driveway/road (passenger cars impassable)
- Tier 3: Severe Inundation (>= 4.8 ft) -> 9" - 15"+ across property (trucks/SUVs only or stranded)

Author: Antigravity Assistant for Mathews County Flood Prediction Project
"""

import os
import sys
import json
import argparse
import subprocess
from datetime import datetime

def format_alert_message(status):
    curr = status.get("current_conditions", {})
    outl = status.get("forecast_48h_outlook", {})
    timeline = status.get("forecast_hourly_timeline", [])

    curr_stage = curr.get("ware_river_stage_mllw_ft")
    curr_depth = curr.get("estimated_local_flood_depth_in", 0.0)
    curr_tier = curr.get("flood_risk_tier", 0)
    curr_tier_lbl = curr.get("flood_risk_label", "Unknown")

    peak_stage = outl.get("peak_forecast_stage_mllw_ft")
    peak_depth = outl.get("peak_estimated_flood_depth_in", 0.0)
    peak_time = outl.get("peak_forecast_stage_time_local", "N/A")
    peak_tier = outl.get("peak_risk_tier", 0)
    peak_tier_lbl = outl.get("peak_risk_label", "Unknown")
    hours_above = outl.get("hours_at_or_above_action_stage", 0)

    # Determine flood window (onset and recession)
    flood_periods = [p for p in timeline if p.get("risk_tier", 0) > 0]
    onset_time = flood_periods[0]["timestamp_local"] if flood_periods else None
    end_time = flood_periods[-1]["timestamp_local"] if flood_periods else None

    # Header banner based on highest risk
    max_tier = max(curr_tier, peak_tier)
    if max_tier == 0:
        banner = "GREEN — NO FLOOD ADVISORY IN EFFECT"
    elif max_tier == 1:
        banner = "YELLOW — TIER 1: NUISANCE FLOOD ADVISORY (DITCHES FULL / MINOR OVERFLOW)"
    elif max_tier == 2:
        banner = "ORANGE — TIER 2: MODERATE COASTAL FLOOD WARNING (DRIVEWAY & ROADS BLOCKED)"
    else:
        banner = "RED — TIER 3: SEVERE COASTAL FLOOD WARNING (HAZARDOUS DEEP INUNDATION)"

    lines = []
    lines.append("=" * 72)
    lines.append(f"MATHEWS COUNTY, VA FLOOD ALERT BULLETIN")
    lines.append(f"Issued: {status.get('status_generated_at_local', 'N/A')}")
    lines.append("=" * 72)
    lines.append(f"ALERT LEVEL: {banner}")
    lines.append("-" * 72)
    lines.append(f"CURRENT CONDITIONS ({curr.get('observation_timestamp_local', 'Now')}):")
    lines.append(f"  • Ware River Stage    : {curr_stage} ft MLLW ({curr.get('ware_river_stage_navd88_ft')} ft NAVD88)")
    lines.append(f"  • Ground Inundation   : {curr_depth} inches ({curr_tier_lbl})")
    lines.append(f"  • Vehicle Access      : {curr.get('vehicle_passability', 'ALL VEHICLES PASSABLE')}")
    lines.append(f"  • Local Winds         : {curr.get('yorktown_wind_speed_mph')} mph from {curr.get('yorktown_wind_dir_cardinal')} (Gusts: {curr.get('yorktown_wind_gust_mph')} mph)")
    lines.append(f"  • Along-Bay Push      : {curr.get('along_bay_wind_vector_mph')} mph (toward Mobjack Bay)")
    lines.append(f"  • Bay Storm Surge     : +{curr.get('windmill_point_storm_surge_residual_ft')} ft at Windmill Point")
    lines.append("-" * 72)
    lines.append(f"48-HOUR HAZARD OUTLOOK:")
    lines.append(f"  • Peak Predicted Stage: {peak_stage} ft MLLW")
    lines.append(f"  • Expected Peak Time  : {peak_time}")
    lines.append(f"  • Max Expected Depth  : {peak_depth} inches ({peak_tier_lbl})")
    lines.append(f"  • Peak Travel Impact  : {outl.get('peak_vehicle_passability', 'ALL VEHICLES PASSABLE')}")
    lines.append(f"  • Inundation Duration : {hours_above} hours at or above action threshold (4.0 ft)")
    if onset_time and end_time:
        lines.append(f"  • Inundation Window   : From {onset_time} to {end_time}")

    sectors = curr.get("site_sectors", {})
    if sectors:
        lines.append("-" * 72)
        lines.append("PROPERTY SECTOR ELEVATION STATUS:")
        for k, s in sectors.items():
            lines.append(f"  • {s.get('name', k):<36}: {s.get('depth_in', 0.0):>4.1f}\" [{s.get('status', 'N/A')}]")
    lines.append("-" * 72)
    
    # Practical guidance
    lines.append("ACTIONABLE GUIDANCE:")
    lines.append(f"  • Vehicle Mobility: {curr.get('vehicle_passability_desc', 'All routes open.')}")
    if max_tier == 0:
        lines.append("  • Water levels will remain inside normal tidal ditches and marsh channels.")
        lines.append("  • All roads and driveways passable. Normal conditions.")
    elif max_tier == 1:
        lines.append("  • Expect 1 to 4 inches of water in roadside ditches and low spots.")
        lines.append("  • Driveway edges may be submerged near high tide.")
        lines.append("  • Passenger vehicle travel remains possible with caution.")
    elif max_tier == 2:
        lines.append("  • 5 to 8 inches of water expected across driveway and low-lying roadways.")
        lines.append("  • Low-clearance passenger cars will be blocked / risk stalling.")
        lines.append("  • Move vehicles to elevated high ground before high tide.")
    else:
        lines.append("  • CRITICAL: 9 to 15+ inches of deep saltwater inundation across property!")
        lines.append("  • Roads will be impassable except for high-clearance emergency vehicles.")
        lines.append("  • Relocate vehicles and outdoor equipment immediately.")
        lines.append("  • Expect prolonged tidal stacking; multiple consecutive high tides may flood.")
        
    lines.append("=" * 72)
    return max_tier, "\n".join(lines)

def send_macos_notification(title, message, subtitle=""):
    """Send native macOS notification banner with alert sound via osascript."""
    try:
        sub_clause = f'subtitle "{subtitle}"' if subtitle else ''
        cmd = f'display notification "{message}" with title "{title}" {sub_clause} sound name "Submarine"'
        subprocess.run(["osascript", "-e", cmd], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def main():
    parser = argparse.ArgumentParser(description="Check flood status and generate alert bulletins.")
    parser.add_argument("--status-json", type=str, default="latest_status.json", help="Path to latest status JSON file")
    parser.add_argument("--min-tier", type=int, default=1, help="Minimum tier required to trigger alert output (default: 1)")
    parser.add_argument("--always-print", action="store_true", help="Always print bulletin even if Tier 0 (Normal)")
    parser.add_argument("--notify", action="store_true", help="Send native macOS desktop notification when alert triggered")
    args = parser.parse_args()

    if not os.path.exists(args.status_json):
        print(f"[ERROR] Status file {args.status_json} not found. Run ingest_realtime.py first.", file=sys.stderr)
        sys.exit(1)

    with open(args.status_json, "r", encoding="utf-8") as f:
        status = json.load(f)

    tier, bulletin = format_alert_message(status)

    if args.always_print or tier >= args.min_tier:
        print(bulletin)
        if args.notify:
            outl = status.get("forecast_48h_outlook", {})
            peak_depth = outl.get("peak_estimated_flood_depth_in", 0.0)
            peak_time = outl.get("peak_forecast_stage_time_local", "N/A")
            lbl = outl.get("peak_risk_label", f"Tier {tier}")
            send_macos_notification(
                title=f"Mathews Flood Alert: {lbl}",
                subtitle=f"Peak: {peak_depth}\" water at {peak_time}",
                message=outl.get("advisory_summary", "")
            )
    else:
        print(f"Status is normal (Tier {tier}). No alert needed.")

if __name__ == "__main__":
    main()

