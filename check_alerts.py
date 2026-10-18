#!/usr/bin/env python3
"""
check_alerts.py — Coastal Flood Alert Generator, Hazard Monitor & Mobile Push Dispatcher
for Mathews County, Virginia Flood Prediction System.

Inspects latest_status.json (produced by ingest_realtime.py), tracks persistent alert
state in alert_state.json to prevent duplicate/spam notifications, and dispatches
audible mobile push notifications via ntfy.sh (topic: mathews-flood-23128).

Notification Strategy:
- Tier 0: Absolute silence (normal conditions, no notifications).
- Advance Warning (Tier 1+): Dispatched when fresh guidance first indicates a compound flood hazard.
- Escalation Warning: Dispatched if peak stage increases by >= 0.25 ft (3"+) or risk tier escalates.
- Imminent Crest (2h Warning): Dispatched 1.0 to 2.5 hours before crest peak.
- All Clear: Dispatched when water recedes below 4.0 ft and no further flooding is expected in 48h.

Author: Antigravity Assistant for Mathews County Flood Prediction Project
"""

import os
import sys
import json
import argparse
import subprocess
import urllib.request
import urllib.error
import urllib.parse
import re
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from runtime_safety import assess_status, atomic_write_json, parse_timestamp, finite_number

EASTERN_TZ = ZoneInfo("America/New_York")
DEFAULT_NTFY_TOPIC = "mathews-flood-23128"
PUBLIC_PORTAL_URL = "https://flatfoot584.github.io/mathews-flood-monitor/"

# Alert state-machine tuning.
TIER_QUIET_MINUTES = 90       # suppress repeat tier-change alerts inside this window (tier 3 always alerts)
STAGE_ESCALATION_FT = 0.25     # forecast peak rising this much re-alerts
STAGE_MAJOR_JUMP_FT = 0.5      # ...a jump this big bypasses the quiet period
RISE_ALERT_FT_PER_HR = 0.5     # 3-hour rise rate that triggers an early warning
RISE_ALERT_MIN_STAGE_FT = 3.0  # ...once water is already meaningfully elevated (below Tier 1)
RISE_ALERT_RESET_FT_PER_HR = 0.25
CREST_WARN_MIN_HOURS = -0.25   # still warn if a run lands just past the crest
CREST_WARN_MAX_HOURS = 2.5

def parse_local_time(ts_str):
    """Parse explicit EST/EDT offsets without ambiguity during DST changes."""
    return parse_timestamp(ts_str)

def format_alert_message(status):
    """Format human-readable CLI bulletin."""
    curr = dict(status.get("current_conditions", {}))
    outl = dict(status.get("forecast_48h_outlook", {}))
    quality = assess_status(status)
    if not quality["current_available"]:
        curr.update(flood_risk_tier=-1, vehicle_passability="UNKNOWN — DATA UNAVAILABLE",
                    vehicle_passability_desc="Do not infer that roads are clear.")
    if not quality["forecast_available"] and outl.get("peak_risk_tier", -1) <= 0:
        outl["peak_risk_tier"] = -1
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
    if max_tier == 0 and quality["state"] != "healthy":
        max_tier = -1
    if max_tier < 0:
        banner = "DATA UNAVAILABLE — FLOOD STATUS UNKNOWN"
    elif max_tier == 0:
        banner = "GREEN — NO FLOOD ADVISORY IN EFFECT"
    elif max_tier == 1:
        banner = "YELLOW — TIER 1: NUISANCE FLOOD ADVISORY (DITCHES FULL / MINOR OVERFLOW)"
    elif max_tier == 2:
        banner = "ORANGE — TIER 2: MODERATE COASTAL FLOOD WARNING (DRIVEWAY & ROADS BLOCKED)"
    else:
        banner = "RED — TIER 3: SEVERE COASTAL FLOOD WARNING (HAZARDOUS DEEP INUNDATION)"

    lines = []
    lines.append("=" * 72)
    lines.append("MATHEWS COUNTY, VA FLOOD ALERT BULLETIN")
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
    lines.append("48-HOUR HAZARD OUTLOOK:")
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
            lines.append(f"  • {s.get('name', k):<36}: {str(s.get('depth_in') if s.get('depth_in') is not None else 'Unknown'):>4}\" [{s.get('status', 'N/A')}]")
    flags = status.get("data_quality_flags", [])
    if flags:
        lines.append("-" * 72)
        lines.append("DATA QUALITY NOTES:")
        for flag in flags:
            lines.append(f"  • {flag}")
    lines.append("-" * 72)
    
    # Practical guidance
    lines.append("ACTIONABLE GUIDANCE:")
    lines.append(f"  • Vehicle Mobility: {curr.get('vehicle_passability_desc', 'All routes open.')}")
    if max_tier < 0:
        lines.append("  • Data unavailable. Do not infer that roads are clear.")
    elif max_tier == 0:
        lines.append("  • Water levels will remain inside normal tidal ditches and marsh channels.")
        lines.append("  • No modeled inundation. Check actual road conditions before travel.")
    elif max_tier == 1:
        lines.append("  • Expect 1 to 4 inches of water in roadside ditches and low spots.")
        lines.append("  • Driveway edges may be submerged near high tide.")
        lines.append("  • Do not enter flooded roads, even when modeled depths are shallow.")
    elif max_tier == 2:
        lines.append("  • 5 to 8 inches of water expected across driveway and low-lying roadways.")
        lines.append("  • Low-clearance passenger cars will be blocked / risk stalling.")
        lines.append("  • Move vehicles to elevated high ground before high tide.")
    else:
        lines.append("  • CRITICAL: 9 to 15+ inches of deep saltwater inundation across property!")
        lines.append("  • Do not enter flooded roads, regardless of vehicle clearance.")
        lines.append("  • Relocate vehicles and outdoor equipment immediately.")
        lines.append("  • Expect prolonged tidal stacking; multiple consecutive high tides may flood.")
        
    lines.append("=" * 72)
    return max_tier, "\n".join(lines)

def send_macos_notification(title, message, subtitle=""):
    """Send native macOS notification banner with alert sound via osascript."""
    try:
        def quote(value):
            return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ') + '"'
        sub_clause = f'subtitle {quote(subtitle)}' if subtitle else ''
        cmd = f'display notification {quote(message)} with title {quote(title)} {sub_clause} sound name "Submarine"'
        subprocess.run(["osascript", "-e", cmd], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

class DeliveryError(RuntimeError):
    """A required notification or publisher configuration failed."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise DeliveryError("Unexpected notification redirect refused.")


def publisher_config(topic):
    server = os.getenv("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
    parsed = urllib.parse.urlsplit(server)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.path or parsed.query or parsed.fragment):
        raise DeliveryError("NTFY_SERVER must be an HTTPS origin without credentials or a path.")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", topic):
        raise DeliveryError("Invalid ntfy topic; use 1–64 letters, digits, underscores or hyphens.")
    return server


def send_ntfy_push(topic, title, message, priority="default", tags="warning", click_url=PUBLIC_PORTAL_URL, dry_run=False):
    """Legacy public-topic JSON publishing; authenticated migration is on hold."""
    if dry_run:
        print(f"[ntfy DRY-RUN] Topic: {topic}; Title: {title}\n{message}")
        return True
    server = publisher_config(topic)
    priorities = {"low": 2, "default": 3, "high": 4, "urgent": 5}
    body = json.dumps({"topic": topic, "title": title, "message": message,
                       "priority": priorities.get(priority, 3), "tags": tags.split(","),
                       "click": click_url}, ensure_ascii=False).encode("utf-8")
    opener = urllib.request.build_opener(NoRedirect())
    for attempt in range(3):
        request = urllib.request.Request(server + "/", data=body, method="POST", headers={
            "Content-Type": "application/json"})
        try:
            with opener.open(request, timeout=12) as response:
                if response.status == 200:
                    print(f"[ntfy] Alert dispatched to '{topic}'.")
                    return True
                raise DeliveryError("Unexpected ntfy response.")
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504):
                raise DeliveryError(f"ntfy rejected delivery (HTTP {error.code}).") from None
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        if attempt < 2:
            time.sleep(2 ** attempt)
    raise DeliveryError("ntfy delivery failed after three attempts; alert state was not advanced.")

def load_alert_state(state_file):
    """Load persistent alert state to prevent duplicate notifications."""
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise DeliveryError("Alert state is unreadable; restore it before dispatching.") from None
    return {
        "active_event": False,
        "last_notified_tier": 0,
        "last_notified_peak_stage": 0.0,
        "last_notified_peak_time": "",
        "two_hour_warning_sent_for": "",
        "last_alert_type": "none",
        "last_alert_timestamp_utc": "",
        "last_alert_timestamp_local": "",
        "last_tier_change_utc": "",
        "pending_tier": None,
        "pending_escalation_tier": None,
        "rise_alert_active": False
    }

def save_alert_state(state_file, state):
    atomic_write_json(state_file, state)

def evaluate_and_dispatch_alerts(status, state_file, topic=DEFAULT_NTFY_TOPIC, force=False, dry_run=False):
    """
    State machine that decides whether to send a push notification.
    Prevents spamming every 30 minutes while ensuring critical warnings arrive on time.
    """
    curr = status.get("current_conditions", {})
    outl = status.get("forecast_48h_outlook", {})

    quality = assess_status(status)
    curr_tier = curr.get("flood_risk_tier", -1) if quality["current_available"] else -1
    peak_tier = outl.get("peak_risk_tier", -1) if quality["forecast_usable"] else -1
    max_tier = max(curr_tier, peak_tier)
    if max_tier < 1 and not quality["alerts_all_clear_allowed"]:
        print("[ntfy] Data degraded. Holding event state; no ALL CLEAR or normal-condition notification.")
        return False

    peak_stage = outl.get("peak_forecast_stage_mllw_ft")
    if not finite_number(peak_stage):
        peak_stage = curr.get("ware_river_stage_mllw_ft") if quality["current_available"] else 0.0
    peak_stage = peak_stage if finite_number(peak_stage) else 0.0
    peak_depth = outl.get("peak_estimated_flood_depth_in", 0.0)
    peak_time_str = outl.get("peak_hazard_time_local") or outl.get("peak_forecast_stage_time_local") or "N/A"
    peak_pass = outl.get("peak_vehicle_passability", "Unknown")
    if curr_tier > peak_tier:
        peak_depth = curr.get("estimated_local_flood_depth_in")
        peak_time_str = "Now"
        peak_pass = curr.get("vehicle_passability", "Unknown")

    state = load_alert_state(state_file)
    now_dt = datetime.now(EASTERN_TZ)
    peak_dt = parse_local_time(peak_time_str)

    # Rapid water-level rise is an early warning even before Tier 1. It never
    # consumes the tier state machine.
    trend = curr.get("stage_trend_3h_ft_per_hr")
    stage_now = curr.get("ware_river_stage_mllw_ft")
    if state.get("rise_alert_active") and (not finite_number(trend) or trend < RISE_ALERT_RESET_FT_PER_HR):
        state["rise_alert_active"] = False
    rise_fire = (quality["current_available"]
                 and finite_number(trend) and trend >= RISE_ALERT_FT_PER_HR
                 and finite_number(stage_now) and stage_now >= RISE_ALERT_MIN_STAGE_FT
                 and not state.get("rise_alert_active"))

    hours_to_peak = None
    if peak_dt:
        hours_to_peak = (peak_dt - now_dt).total_seconds() / 3600.0

    send_alert = False
    alert_type = None
    priority = "default"
    tags = "warning"
    title = ""
    body_lines = []

    # Case 1: Normal Conditions (Tier 0)
    if max_tier == 0:
        if state.get("active_event"):
            # We had an active warning, but water has receded! Send ALL CLEAR.
            send_alert = True
            alert_type = "all_clear"
            priority = "low"
            tags = "white_check_mark,sunny"
            title = "Mathews Flood Monitor: Modeled hazard ended"
            body_lines = [
                "The current model no longer estimates inundation from tidal water levels or forecast rainfall.",
                "No modeled coastal or forecast rainfall hazard remains. Check actual road conditions before travel.",
                f"Ware River Stage: {curr.get('ware_river_stage_mllw_ft')} ft MLLW."
            ]
            state["active_event"] = False
            state["last_notified_tier"] = 0
            state["last_notified_peak_stage"] = 0.0
            state["last_notified_peak_time"] = ""
            state["event_peak_time"] = ""
            state["two_hour_warning_sent_for"] = ""
            state["rise_alert_active"] = False
        elif rise_fire:
            # Early warning at Tier 0: water climbing fast toward the action stage.
            send_alert = True
            alert_type = "rapid_rise_warning"
            priority = "high"
            tags = "warning,chart_with_upwards_trend"
            title = "Mathews Flood Alert: water rising fast"
            body_lines.append(f"Ware River rising {trend:.2f} ft/hr; now {stage_now} ft MLLW.")
            body_lines.append("Action: prepare to move vehicles; flooding may develop before the next high tide.")
            state["rise_alert_active"] = True
        else:
            print(f"[ntfy] Normal conditions (Tier 0). No notification sent.")
            save_alert_state(state_file, state)
            return False

    # Case 2: Active or Upcoming Flood Event (Tier 1+)
    else:
        # Determine priority and tags based on severity
        if max_tier == 1:
            priority = "default"
            tags = "warning,droplet"
            tier_name = "Tier 1 (Nuisance / Ditches Full)"
        elif max_tier == 2:
            priority = "high"
            tags = "warning,ocean,car"
            tier_name = "Tier 2 (Moderate Inundation - Driveway Blocked)"
        else:
            priority = "urgent"
            tags = "rotating_light,sos,car"
            tier_name = "Tier 3 (SEVERE INUNDATION HAZARD)"

        last_change = parse_timestamp(state.get("last_tier_change_utc"))
        quiet = (last_change is not None
                 and (now_dt - last_change).total_seconds() < TIER_QUIET_MINUTES * 60)
        notified_peak_dt = parse_local_time(state.get("event_peak_time") or state.get("last_notified_peak_time"))
        new_crest = (peak_dt and notified_peak_dt
                     and abs((peak_dt - notified_peak_dt).total_seconds()) > 4 * 3600)

        # Check conditions for triggering
        if force:
            send_alert = True
            alert_type = "forced_manual"
        elif not state.get("active_event"):
            # New flood event detected; lead time depends on fresh guidance
            send_alert = True
            alert_type = "advance_warning"
        elif new_crest:
            # A different tidal crest; tolerate revisions to this event's peak.
            send_alert = True
            alert_type = "new_crest_event"
        elif max_tier > state.get("last_notified_tier", 0):
            # Tier escalated. Tier 3 always alerts immediately; smaller moves
            # inside the quiet period are deferred to avoid flapping on boundary
            # oscillations, then sent once the window expires if still elevated.
            if max_tier >= 3 or not quiet:
                send_alert = True
                alert_type = "tier_escalation"
            else:
                state["pending_escalation_tier"] = max_tier
                print(f"[ntfy] Tier escalation to Tier {max_tier} inside quiet period; deferred.")
        elif max_tier < state.get("last_notified_tier", 0):
            # Tier de-escalated: announce only after the lower tier is confirmed
            # on a second consecutive evaluation, so boundary wobble doesn't spam.
            if state.get("pending_tier") == max_tier:
                send_alert = True
                alert_type = "tier_deescalation"
                priority = "low"
                tags = "white_check_mark"
            else:
                state["pending_tier"] = max_tier
                print(f"[ntfy] Tier de-escalation to Tier {max_tier} awaiting confirmation.")
        elif peak_stage >= state.get("last_notified_peak_stage", 0.0) + STAGE_ESCALATION_FT:
            # Stage forecast jumped by 0.25+ ft (3+ inches)
            jump = peak_stage - state.get("last_notified_peak_stage", 0.0)
            if max_tier >= 3 or jump >= STAGE_MAJOR_JUMP_FT or not quiet:
                send_alert = True
                alert_type = "forecast_escalation"
            else:
                print("[ntfy] Forecast escalation inside quiet period; deferred.")
        elif (hours_to_peak is not None and CREST_WARN_MIN_HOURS <= hours_to_peak <= CREST_WARN_MAX_HOURS
              and not state.get("two_hour_warning_sent_for")):
            # 2-hour pre-crest immediate window reminder. Fires even just past
            # the crest in case a pipeline cycle was missed.
            send_alert = True
            alert_type = "imminent_crest_warning"
            state["two_hour_warning_sent_for"] = peak_time_str
        elif (not quiet and state.get("pending_escalation_tier")
              and max_tier >= state["pending_escalation_tier"]):
            # Deferred escalation from inside the quiet period; still elevated.
            send_alert = True
            alert_type = "tier_escalation"

        # Rapid rise during an active event (Tier 0 is handled in Case 1).
        if not send_alert and rise_fire:
            send_alert = True
            alert_type = "rapid_rise_warning"
            priority = "high"
            tags = "warning,chart_with_upwards_trend"

        if send_alert:
            if alert_type == "imminent_crest_warning":
                title = f"Mathews Flood Alert: High Tide in ~2 Hours ({peak_depth} in)"
            elif alert_type == "tier_deescalation":
                title = f"Mathews Flood Monitor: advisory downgraded to {tier_name}"
            elif alert_type == "rapid_rise_warning":
                title = "Mathews Flood Alert: water rising fast"
            elif alert_type in ("tier_escalation", "forecast_escalation"):
                title = f"Mathews Flood WARNING ESCALATED: {tier_name}"
            else:
                title = f"Mathews Coastal Flood Advisory: {tier_name}"

            # Compose concise lockscreen-friendly body
            if alert_type == "tier_deescalation":
                body_lines.append(f"Hazard reduced to {tier_name}.")
                body_lines.append(f"Ware River Stage: {curr.get('ware_river_stage_mllw_ft')} ft MLLW.")
                body_lines.append("Action: conditions improving, but do not enter standing water.")
            elif alert_type == "rapid_rise_warning":
                body_lines.append(f"Ware River rising {trend:.2f} ft/hr; now {stage_now} ft MLLW.")
                body_lines.append("Action: prepare to move vehicles; flooding may develop before the next high tide.")
            else:
                body_lines.append(f"Predicted Crest: {peak_depth}\" water at {peak_time_str}")
                body_lines.append(f"Ware River Stage: {peak_stage} ft MLLW (Threshold: 4.0 ft)")
                body_lines.append(f"Travel Impact: {peak_pass}")
                if max_tier >= 2:
                    body_lines.append("Action: Move vehicles to verified dry high ground before flooding starts. Never enter floodwater.")
                else:
                    body_lines.append("Action: Water ponding in low spots. Do not drive into flooded roads.")

            if alert_type == "rapid_rise_warning":
                # Early warning only; it must not consume the tier state machine.
                state["rise_alert_active"] = True
            else:
                if not state.get("active_event") or alert_type == "new_crest_event":
                    state["event_peak_time"] = peak_time_str
                    state["two_hour_warning_sent_for"] = ""
                state["active_event"] = True
                state["last_notified_tier"] = max_tier
                state["last_notified_peak_stage"] = peak_stage
                state["last_notified_peak_time"] = peak_time_str
                if alert_type in ("advance_warning", "new_crest_event",
                                  "tier_escalation", "tier_deescalation"):
                    state["last_tier_change_utc"] = now_dt.isoformat()
                state["pending_tier"] = None
                state["pending_escalation_tier"] = None
        else:
            print(f"[ntfy] Flood event active ({tier_name}), no new alert conditions; state saved.")
            save_alert_state(state_file, state)
            return False

    # Dispatch notification
    body_text = "\n".join(body_lines)
    success = send_ntfy_push(
        topic=topic,
        title=title,
        message=body_text,
        priority=priority,
        tags=tags,
        click_url=PUBLIC_PORTAL_URL,
        dry_run=dry_run
    )

    if not success:
        raise DeliveryError("Notification delivery failed; state was not advanced.")
    if success and not dry_run:
        state["last_alert_type"] = alert_type
        state["last_alert_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
        state["last_alert_timestamp_local"] = now_dt.strftime("%Y-%m-%d %H:%M:%S %Z")
        save_alert_state(state_file, state)

    return success

def send_test_alert(topic=DEFAULT_NTFY_TOPIC, dry_run=False):
    """Send an immediate test alert to verify phone notification reception."""
    title = "Mathews Flood Monitor: Test Notification"
    message = (
        "Mobile push notifications are working!\n\n"
        "You are subscribed to Mathews County coastal flood alerts. "
        "You will receive audible warnings with water depth predictions before high-tide flood events.\n"
        "Portal: " + PUBLIC_PORTAL_URL
    )
    print(f"[ntfy] Sending test notification to topic '{topic}'...")
    return send_ntfy_push(
        topic=topic,
        title=title,
        message=message,
        priority="default",
        tags="bell,white_check_mark",
        click_url=PUBLIC_PORTAL_URL,
        dry_run=dry_run
    )

def main():
    parser = argparse.ArgumentParser(description="Check flood status, generate bulletins, and dispatch ntfy alerts.")
    parser.add_argument("--status-json", type=str, default="latest_status.json", help="Path to latest status JSON file")
    parser.add_argument("--state-file", type=str, default="alert_state.json", help="Path to alert state file for spam prevention")
    parser.add_argument("--ntfy-topic", type=str, default=os.getenv("NTFY_TOPIC", DEFAULT_NTFY_TOPIC), help="ntfy topic name (default: mathews-flood-23128)")
    parser.add_argument("--ntfy", action="store_true", default=False, help="Enable existing public-topic ntfy publishing")
    parser.add_argument("--no-ntfy", action="store_false", dest="ntfy", help="Disable ntfy.sh push notifications")
    parser.add_argument("--test-ntfy", action="store_true", help="Send a test notification to verify phone reception")
    parser.add_argument("--force-ntfy", action="store_true", help="Force send notification regardless of prior state")
    parser.add_argument("--dry-run", action="store_true", help="Evaluate conditions without sending HTTP request")
    parser.add_argument("--min-tier", type=int, default=1, help="Minimum tier required to print the bulletin to stdout (display only; does not affect ntfy dispatch)")
    parser.add_argument("--always-print", action="store_true", help="Always print bulletin even if Tier 0 (Normal)")
    parser.add_argument("--notify", action="store_true", help="Send native macOS desktop notification when alert triggered")
    args = parser.parse_args()

    if args.test_ntfy:
        if not send_test_alert(topic=args.ntfy_topic, dry_run=args.dry_run):
            raise DeliveryError("Test notification failed.")
        return

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
        print(f"Status is normal (Tier {tier}). Bulletin output suppressed (use --always-print to view).")

    # Evaluate and dispatch ntfy push notification
    if args.ntfy:
        evaluate_and_dispatch_alerts(
            status=status,
            state_file=args.state_file,
            topic=args.ntfy_topic,
            force=args.force_ntfy,
            dry_run=args.dry_run
        )

if __name__ == "__main__":
    try:
        main()
    except (DeliveryError, OSError, ValueError) as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        sys.exit(1)
