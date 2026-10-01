#!/usr/bin/env python3
"""
micro_topography.py — Property Elevation Profile & Compound Pluvial Inundation Engine
for Mathews County, Virginia Coastal Flood Prediction System.

Implements:
1. Multi-sector micro-topographical elevation mapping (MLLW and NAVD88)
2. Compound pluvial (rainfall) + tidal backwater physics
3. Sector-by-sector inundation status (Ditches, Driveway Apron, Main Driveway, Yard, Garage)
4. Granular vehicle passability assessment (Sedans vs. SUVs/Trucks vs. Emergency)

Author: Antigravity Assistant for Mathews County Flood Prediction Project
"""

import math

# Primary ground-truth observation benchmark coordinates (Daniel Ave, Blackwater, Mathews County, VA)
BENCHMARK_LAT = 37.420183
BENCHMARK_LON = -76.406550
BENCHMARK_LOCATION = "Daniel Ave, Blackwater, Mathews County, VA"

DATUM_OFFSET_NAVD88_MLLW = -1.64  # NAVD88 = MLLW - 1.64 ft
FLOOD_STAGE_THRESHOLD = 3.99       # ft MLLW (ditch bank full)

# Property elevation sectors anchored to USGS 3DEP 1-meter LiDAR at 37.420183, -76.406550:
# - Ditch culvert invert: 2.41' NAVD88 (4.05' MLLW)
# - Main driveway benchmark: 2.76' NAVD88 (4.40' MLLW)
# - Residence / garage pad: 3.26' NAVD88 (4.90' MLLW)
SECTOR_PROFILES = {
    "ditches": {
        "name": "Tidal Ditches & Marsh Channels",
        "invert_mllw_ft": 2.50,
        "bank_mllw_ft": 3.99,
        "description": "Intertidal marsh creeks and drainage swales. Gravity drainage to Ware River."
    },
    "road_apron": {
        "name": "Road Shoulder & Culvert Invert",
        "invert_mllw_ft": 4.00,
        "bank_mllw_ft": 4.39,
        "description": "Lowest driveway entrance dip and road culvert apron."
    },
    "main_driveway": {
        "name": "Main Driveway (Vehicle Route)",
        "invert_mllw_ft": 4.40,
        "bank_mllw_ft": 4.79,
        "description": "Critical travel route. Passenger cars blocked when water exceeds 4 inches."
    },
    "yard_lawn": {
        "name": "Residential Lawn & Grounds",
        "invert_mllw_ft": 4.60,
        "bank_mllw_ft": 4.89,
        "description": "Open yard and property interior. Trucks and SUVs required."
    },
    "garage_foundation": {
        "name": "Garage Apron & Residence High Ground",
        "invert_mllw_ft": 4.90,
        "bank_mllw_ft": 99.0,
        "description": "Elevated building footprint and high ground foundation."
    }
}

def calculate_backwater_restriction(stage_mllw_ft):
    """
    Calculate drainage ditch backwater blockage factor (0.0 = full gravity drain, 1.0 = completely blocked).
    Gravity flow slows as stage passes 3.80 ft, reaching complete restriction at 4.20 ft.
    """
    if stage_mllw_ft is None:
        return 0.0
    if stage_mllw_ft <= 3.80:
        return 0.0
    elif stage_mllw_ft >= 4.20:
        return 1.0
    else:
        return (stage_mllw_ft - 3.80) / (4.20 - 3.80)

def evaluate_compound_inundation(stage_mllw_ft, rain_rolling_6h_in=0.0):
    """
    Compute compound tidal + pluvial inundation and evaluate each property sector.
    
    Args:
        stage_mllw_ft: Ware River gauge stage in feet MLLW
        rain_rolling_6h_in: Cumulative 6-hour rainfall in inches
        
    Returns:
        Structured dict with total flood depth, compound pluvial addition,
        sector-specific status, and vehicular accessibility matrix.
    """
    if stage_mllw_ft is None:
        stage_mllw_ft = 0.0

    # 1. Base tidal flood depth on property reference marker
    # Regression: depth = 10.95 * stage - 43.69
    if stage_mllw_ft >= FLOOD_STAGE_THRESHOLD:
        tidal_depth_in = round(10.95 * stage_mllw_ft - 43.69, 2)
    else:
        tidal_depth_in = 0.0

    # 2. Compound pluvial backwater trapped depth
    backwater_factor = calculate_backwater_restriction(stage_mllw_ft)
    # Rainfall trapped on flat ground with 1.4x micro-swale concentration
    pluvial_trapped_in = round(float(rain_rolling_6h_in or 0.0) * backwater_factor * 1.4, 2)
    total_depth_in = round(max(0.0, tidal_depth_in + pluvial_trapped_in), 2)

    # 3. Micro-topography sectors
    sector_results = {}
    for key, sec in SECTOR_PROFILES.items():
        inv = sec["invert_mllw_ft"]
        inv_navd = round(inv + DATUM_OFFSET_NAVD88_MLLW, 2)
        
        if stage_mllw_ft < inv:
            if pluvial_trapped_in > 0 and key in ("ditches", "road_apron"):
                sec_depth = pluvial_trapped_in
                status = "DITCH FULL (RAIN BACKED UP)" if key == "ditches" else "PUDDLING"
            else:
                sec_depth = 0.0
                status = "DRY"
        else:
            rise_ft = stage_mllw_ft - inv
            # Stage rise converted to ground depth inches (~11.0 to 11.5 in per ft rise)
            base_in = rise_ft * 11.2
            sec_depth = round(base_in + pluvial_trapped_in, 1)
            status = "SUBMERGED"

        sector_results[key] = {
            "name": sec["name"],
            "invert_mllw_ft": inv,
            "invert_navd88_ft": inv_navd,
            "depth_in": sec_depth,
            "status": status,
            "is_submerged": sec_depth > 0.0
        }

    # 4. Vehicle passability assessment
    driveway_depth = sector_results["main_driveway"]["depth_in"]
    road_depth = sector_results["road_apron"]["depth_in"]
    
    if driveway_depth == 0.0 and road_depth < 1.0:
        passability_code = "GREEN"
        passability_label = "ALL VEHICLES PASSABLE"
        passability_desc = "Driveway and road dry. Normal conditions for all passenger vehicles."
    elif driveway_depth < 3.5:
        passability_code = "YELLOW"
        passability_label = "CAUTION — LOW-CLEARANCE HAZARDOUS"
        passability_desc = "1 to 3 inches on driveway apron. Sedans can pass with caution; avoid sudden braking."
    elif driveway_depth < 7.5:
        passability_code = "ORANGE"
        passability_label = "SEDANS BLOCKED — TRUCKS / SUVS ONLY"
        passability_desc = "4 to 7 inches on main driveway. Passenger cars will stall or float. Move cars to high ground."
    else:
        passability_code = "RED"
        passability_label = "CRITICAL — IMPASSABLE TO CIVILIAN TRAFFIC"
        passability_desc = "8 to 15+ inches of deep saltwater. Road & driveway impassable. High-clearance emergency only."

    return {
        "stage_mllw_ft": round(stage_mllw_ft, 2),
        "stage_navd88_ft": round(stage_mllw_ft + DATUM_OFFSET_NAVD88_MLLW, 2),
        "rainfall_6h_in": round(float(rain_rolling_6h_in or 0.0), 2),
        "backwater_restriction_pct": round(backwater_factor * 100, 1),
        "tidal_depth_in": tidal_depth_in,
        "pluvial_trapped_depth_in": pluvial_trapped_in,
        "total_compound_depth_in": total_depth_in,
        "vehicle_passability_code": passability_code,
        "vehicle_passability_label": passability_label,
        "vehicle_passability_desc": passability_desc,
        "sectors": sector_results
    }

if __name__ == "__main__":
    import sys
    test_stage = float(sys.argv[1]) if len(sys.argv) > 1 else 4.45
    test_rain = float(sys.argv[2]) if len(sys.argv) > 2 else 1.5
    res = evaluate_compound_inundation(test_stage, test_rain)
    print("=" * 60)
    print(f"STAGE: {res['stage_mllw_ft']} ft MLLW | RAIN (6h): {res['rainfall_6h_in']} in")
    print(f"Total Depth: {res['total_compound_depth_in']}\" (Tidal: {res['tidal_depth_in']}\", Rain trapped: {res['pluvial_trapped_depth_in']}\")")
    print(f"Passability: {res['vehicle_passability_label']} ({res['vehicle_passability_desc']})")
    print("-" * 60)
    for k, v in res['sectors'].items():
        print(f"  • {v['name']:<38}: {v['depth_in']:>4.1f}\" [{v['status']}]")
    print("=" * 60)
