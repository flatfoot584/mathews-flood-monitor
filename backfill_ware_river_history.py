import os
import time
import calendar
import urllib.request
import csv
from datetime import datetime, timezone
import zoneinfo

CACHE_DIR = "ware_river_historical_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

EASTERN_TZ = zoneinfo.ZoneInfo("America/New_York")

def fetch_month(year, month):
    cache_file = os.path.join(CACHE_DIR, f"wrvv2_{year}_{month:02d}.csv")
    if os.path.exists(cache_file) and os.path.getsize(cache_file) > 500:
        print(f"[{year}-{month:02d}] Loaded from cache.")
        return cache_file

    last_day = calendar.monthrange(year, month)[1]
    url = (
        f"https://mesonet.agron.iastate.edu/cgi-bin/request/hml.py"
        f"?station=WRVV2&kind=obs&tz=UTC"
        f"&year1={year}&month1={month}&day1=1"
        f"&year2={year}&month2={month}&day2={last_day}"
        f"&fmt=csv"
    )

    req = urllib.request.Request(url, headers={"User-Agent": "MathewsFloodResearch/1.0"})
    for attempt in range(1, 4):
        try:
            print(f"[{year}-{month:02d}] Fetching from IEM (attempt {attempt})...")
            with urllib.request.urlopen(req, timeout=30) as resp:
                content = resp.read().decode("utf-8", errors="ignore")
                if "station,valid[UTC]" in content and len(content.splitlines()) > 5:
                    with open(cache_file, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"[{year}-{month:02d}] Successfully downloaded ({len(content.splitlines())} lines).")
                    return cache_file
                else:
                    print(f"[{year}-{month:02d}] Warning: short or empty response.")
        except Exception as e:
            print(f"[{year}-{month:02d}] Error on attempt {attempt}: {e}")
            time.sleep(2)

    return None

def consolidate_data():
    all_records = []
    # Date range: 2021-01 to 2024-09
    for year in range(2021, 2025):
        max_month = 9 if year == 2024 else 12
        for month in range(1, max_month + 1):
            cache_file = fetch_month(year, month)
            if not cache_file or not os.path.exists(cache_file):
                continue
            with open(cache_file, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                for row in reader:
                    if len(row) >= 3 and row[0].strip() == "WRVV2":
                        valid_utc_str = row[1].strip()
                        stage_str = row[2].strip()
                        try:
                            stage = float(stage_str)
                            dt_utc = datetime.strptime(valid_utc_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                            all_records.append((dt_utc, stage))
                        except ValueError:
                            continue
            time.sleep(0.3)

    print(f"\nTotal raw observations collected: {len(all_records)}")
    if not all_records:
        return

    # Deduplicate and sort by UTC timestamp
    unique_records = {}
    for dt, stage in all_records:
        unique_records[dt] = stage
    sorted_dts = sorted(unique_records.keys())
    print(f"Unique observations after deduplication: {len(sorted_dts)}")

    # Write full 6-minute CSV
    full_csv_path = "ware_river_stage_2021_2024.csv"
    with open(full_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["valid_time_utc", "valid_time_local", "stage_mllw_ft", "stage_navd88_ft"])
        for dt in sorted_dts:
            dt_local = dt.astimezone(EASTERN_TZ)
            stage_mllw = unique_records[dt]
            stage_navd88 = round(stage_mllw - 1.64, 3) # NAVD88 = MLLW - 1.64 ft
            writer.writerow([
                dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                dt_local.strftime("%Y-%m-%d %H:%M:%S %Z"),
                f"{stage_mllw:.2f}",
                f"{stage_navd88:.2f}"
            ])
    print(f"Written continuous 6-minute dataset: {full_csv_path}")

    # Build Hourly Aggregated Dataset
    hourly_buckets = {}
    for dt in sorted_dts:
        hour_key = dt.replace(minute=0, second=0, microsecond=0)
        hourly_buckets.setdefault(hour_key, []).append(unique_records[dt])

    hourly_csv_path = "ware_river_hourly_2021_2024.csv"
    with open(hourly_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "valid_time_utc",
            "valid_time_local",
            "stage_mllw_mean_ft",
            "stage_mllw_min_ft",
            "stage_mllw_max_ft",
            "stage_navd88_mean_ft",
            "num_obs"
        ])
        for hour_dt in sorted(hourly_buckets.keys()):
            vals = hourly_buckets[hour_dt]
            hour_local = hour_dt.astimezone(EASTERN_TZ)
            mean_mllw = sum(vals) / len(vals)
            min_mllw = min(vals)
            max_mllw = max(vals)
            mean_navd88 = mean_mllw - 1.64
            writer.writerow([
                hour_dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                hour_local.strftime("%Y-%m-%d %H:%M:%S %Z"),
                f"{mean_mllw:.2f}",
                f"{min_mllw:.2f}",
                f"{max_mllw:.2f}",
                f"{mean_navd88:.2f}",
                len(vals)
            ])
    print(f"Written hourly aggregated dataset: {hourly_csv_path} ({len(hourly_buckets)} hours)")

if __name__ == "__main__":
    consolidate_data()
