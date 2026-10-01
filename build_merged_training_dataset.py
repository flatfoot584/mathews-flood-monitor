import os
import glob
import csv
import math
from datetime import datetime, timezone, timedelta
import zoneinfo

EASTERN_TZ = zoneinfo.ZoneInfo("America/New_York")

print("1. Loading Ware River hourly data...")
ware_data = {}
with open("ware_river_hourly_2021_2024.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        # valid_time_utc: '2021-01-01 00:00:00 UTC'
        t_str = row["valid_time_utc"].replace(" UTC", "")
        dt_utc = datetime.strptime(t_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        ware_data[dt_utc] = {
            "stage_mllw_mean_ft": float(row["stage_mllw_mean_ft"]),
            "stage_mllw_max_ft": float(row["stage_mllw_max_ft"]),
            "stage_navd88_mean_ft": float(row["stage_navd88_mean_ft"])
        }
print(f"Loaded {len(ware_data)} Ware River hourly records.")

print("2. Loading Yorktown hourly meteorological data...")
yorktown_met = {}
for path in sorted(glob.glob("8637689-Yorktown-USCG-Training-Center-data/*-hrly-Yorktown-met-data.csv")):
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            d_str = row["Date"].replace("-", "/").strip()
            t_str = row["Time (GMT)"].strip()
            if not d_str or not t_str: continue
            try:
                dt_utc = datetime.strptime(f"{d_str} {t_str}", "%Y/%m/%d %H:%M").replace(tzinfo=timezone.utc)
            except ValueError:
                continue

            def parse_flt(val):
                v = val.strip()
                if v in ("-", "", "nan", "None"): return None
                try: return float(v)
                except ValueError: return None

            w_spd_kn = parse_flt(row.get("Wind Speed (kn)", "-"))
            w_dir_deg = parse_flt(row.get("Wind Dir (deg)", "-"))
            w_gst_kn = parse_flt(row.get("Wind Gust (kn)", "-"))
            air_temp_f = parse_flt(row.get("Air Temp (°F)", "-"))
            baro_mb = parse_flt(row.get("Baro (mb)", "-"))

            w_spd_mph = round(w_spd_kn * 1.15078, 2) if w_spd_kn is not None else None
            w_gst_mph = round(w_gst_kn * 1.15078, 2) if w_gst_kn is not None else None

            yorktown_met[dt_utc] = {
                "wind_speed_mph": w_spd_mph,
                "wind_dir_deg": w_dir_deg,
                "wind_gust_mph": w_gst_mph,
                "air_temp_f": air_temp_f,
                "baro_mb": baro_mb
            }
print(f"Loaded {len(yorktown_met)} Yorktown met records.")

print("3. Loading Yorktown predicted tides...")
yorktown_tides = {}
for path in sorted(glob.glob("8637689-Yorktown-USCG-Training-Center-data/*[Yy]orktown-tides.csv")):
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            d_str = row["Date"].replace("-", "/").strip()
            t_str = row["Time (GMT)"].strip()
            pred_str = row["Predicted (ft)"].strip()
            if not d_str or not t_str or pred_str in ("-", ""): continue
            try:
                dt_utc = datetime.strptime(f"{d_str} {t_str}", "%Y/%m/%d %H:%M").replace(tzinfo=timezone.utc)
                if dt_utc.minute == 0:
                    yorktown_tides[dt_utc] = float(pred_str)
            except ValueError:
                continue
print(f"Loaded {len(yorktown_tides)} Yorktown hourly tide predictions.")

print("4. Loading Windmill Point tidal data (LST = UTC-5)...")
windmill_tides = {}
for path in sorted(glob.glob("Windmill-point-data/*-8636580-Windmill-point-tidal.csv")):
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            d_str = row["Date"].replace("-", "/").strip()
            t_str = row["Time (LST)"].strip()
            if not d_str or not t_str: continue
            try:
                dt_lst = datetime.strptime(f"{d_str} {t_str}", "%Y/%m/%d %H:%M")
                # LST is UTC-5 year round: UTC = LST + 5 hours
                dt_utc = dt_lst.replace(tzinfo=timezone.utc) + timedelta(hours=5)
            except ValueError:
                continue

            def parse_flt(val):
                v = val.strip()
                if v in ("-", "", "nan", "None"): return None
                try: return float(v)
                except ValueError: return None

            pred_ft = parse_flt(row.get("Predicted (ft)", "-"))
            ver_ft = parse_flt(row.get("Verified (ft)", "-"))
            surge_ft = round(ver_ft - pred_ft, 3) if (ver_ft is not None and pred_ft is not None) else None

            windmill_tides[dt_utc] = {
                "wm_pred_ft": pred_ft,
                "wm_ver_ft": ver_ft,
                "wm_surge_ft": surge_ft
            }
print(f"Loaded {len(windmill_tides)} Windmill Point tidal records.")

print("5. Loading Ground-Truth Observations...")
ground_truth = {}
with open("ground_truth_observations.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        date_str = row["date"].strip()
        time_str = row["time_local"].strip()
        time_qual = row["time_qualifier"].strip()
        depth_str = row["flood_depth_in"].strip()
        is_flood = row["is_flooded"].strip()
        weather = row["weather_system"].strip()

        # Parse local time or approximate if only date or AM/PM
        hour_local = 12 # default to noon if unknown
        if time_str and ":" in time_str:
            parts = time_str.split(":")
            hour_local = int(parts[0])
            if time_qual == "PM" and hour_local < 12: hour_local += 12
            if time_qual == "AM" and hour_local == 12: hour_local = 0
        elif time_qual == "AM":
            hour_local = 9
        elif time_qual == "PM":
            hour_local = 18

        try:
            dt_loc = datetime.strptime(f"{date_str} {hour_local:02d}:00", "%Y-%m-%d %H:%M").replace(tzinfo=EASTERN_TZ)
            dt_utc = dt_loc.astimezone(timezone.utc)
            # Round to nearest hour
            dt_utc_hour = dt_utc.replace(minute=0, second=0, microsecond=0)
            ground_truth[dt_utc_hour] = {
                "flood_depth_in": float(depth_str) if depth_str else None,
                "is_flooded": is_flood if is_flood else None,
                "weather_system": weather if weather else None,
                "obs_id": row["observation_id"]
            }
        except ValueError:
            continue
print(f"Matched {len(ground_truth)} ground-truth observations to hourly timestamps.")

print("6. Merging all streams on common hourly timeline (2021-01-01 to 2024-09-29)...")
all_hours = sorted(set(ware_data.keys()) | set(yorktown_met.keys()) | set(windmill_tides.keys()))
print(f"Total union hourly timestamps: {len(all_hours)}")

merged_rows = []
for dt_utc in all_hours:
    # Filter to 2021-01-01 to 2024-09-30
    if dt_utc < datetime(2021, 1, 1, tzinfo=timezone.utc) or dt_utc > datetime(2024, 9, 30, tzinfo=timezone.utc):
        continue

    dt_local = dt_utc.astimezone(EASTERN_TZ)
    ware = ware_data.get(dt_utc, {})
    met = yorktown_met.get(dt_utc, {})
    yt_tide = yorktown_tides.get(dt_utc)
    wm = windmill_tides.get(dt_utc, {})
    gt = ground_truth.get(dt_utc, {})

    w_spd = met.get("wind_speed_mph")
    w_dir = met.get("wind_dir_deg")

    # Decompose wind vectors:
    # Meteorological direction: 0 = from North (blowing south), 90 = from East (blowing west)
    # Wind vector (u, v) direction water is pushed:
    # u = -spd * sin(rad), v = -spd * cos(rad)
    u_wind = None
    v_wind = None
    along_bay_wind = None # Bay orientation ~20 deg NNE to SSW
    cross_bay_wind = None

    if w_spd is not None and w_dir is not None:
        rad = math.radians(w_dir)
        u_wind = round(-w_spd * math.sin(rad), 2)
        v_wind = round(-w_spd * math.cos(rad), 2)
        # Along Chesapeake Bay: 20 degrees North-Northeast.
        # Wind blowing toward 200 degrees (from 20 deg) pushes water DOWN the bay into Mobjack Bay
        bay_rad = math.radians(w_dir - 20)
        along_bay_wind = round(w_spd * math.cos(bay_rad), 2)
        cross_bay_wind = round(w_spd * math.sin(bay_rad), 2)

    merged_rows.append({
        "timestamp_utc": dt_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "timestamp_local": dt_local.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "year": dt_local.year,
        "month": dt_local.month,
        "day": dt_local.day,
        "hour": dt_local.hour,
        # Ware River stage targets
        "ware_river_stage_mllw_ft": ware.get("stage_mllw_mean_ft", ""),
        "ware_river_stage_max_ft": ware.get("stage_mllw_max_ft", ""),
        "ware_river_stage_navd88_ft": ware.get("stage_navd88_mean_ft", ""),
        # Yorktown Meteorological Forcing
        "yorktown_wind_speed_mph": w_spd if w_spd is not None else "",
        "yorktown_wind_dir_deg": w_dir if w_dir is not None else "",
        "yorktown_wind_gust_mph": met.get("wind_gust_mph", ""),
        "yorktown_baro_mb": met.get("baro_mb", ""),
        "yorktown_air_temp_f": met.get("air_temp_f", ""),
        "wind_u_mph": u_wind if u_wind is not None else "",
        "wind_v_mph": v_wind if v_wind is not None else "",
        "along_bay_wind_mph": along_bay_wind if along_bay_wind is not None else "",
        "cross_bay_wind_mph": cross_bay_wind if cross_bay_wind is not None else "",
        # Tidal Forcing
        "yorktown_pred_tide_ft": f"{yt_tide:.3f}" if yt_tide is not None else "",
        "windmill_pred_tide_ft": f"{wm['wm_pred_ft']:.3f}" if wm.get("wm_pred_ft") is not None else "",
        "windmill_ver_water_ft": f"{wm['wm_ver_ft']:.3f}" if wm.get("wm_ver_ft") is not None else "",
        "windmill_surge_ft": f"{wm['wm_surge_ft']:.3f}" if wm.get("wm_surge_ft") is not None else "",
        # Ground Truth Flood Depth (Inches)
        "local_flood_depth_in": gt.get("flood_depth_in", ""),
        "is_flooded": gt.get("is_flooded", ""),
        "weather_system": gt.get("weather_system", ""),
        "ground_truth_obs_id": gt.get("obs_id", "")
    })

output_path = "merged_hourly_training_dataset.csv"
fieldnames = list(merged_rows[0].keys())
with open(output_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(merged_rows)

print(f"Successfully generated {output_path} with {len(merged_rows)} hourly records.")
