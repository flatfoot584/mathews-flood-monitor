"""Resident-facing components shared by the static portal (no external services)."""
import html, json
from pathlib import Path
from datetime import timezone
from runtime_safety import parse_timestamp, finite_number

def e(value): return html.escape(str(value if value is not None else 'Unavailable'),quote=True)
def number(value, unit='', precision=1):
    return f'{value:.{precision}f}{unit}' if finite_number(value) else 'Unknown'
def when(value):
    dt=parse_timestamp(str(value))
    if not dt:return 'Unavailable'
    from zoneinfo import ZoneInfo
    return dt.astimezone(ZoneInfo('America/New_York')).strftime('%a, %b %-d at %-I:%M %p %Z')

def navbar(active,status):
    curr=status.get('current_conditions',{});quality=status['data_quality']
    pages=[('live','Dashboard','index.html'),('map','Map','index.html#map-section'),('alerts','Alerts','alerts.html'),('guide','Guide','guide.html')]
    links=''.join(f'<a href="{url}" {"aria-current=page" if active==key else ""}>{label}</a>' for key,label,url in pages)
    extra=''.join(f'<a href="{key}.html" {"aria-current=page" if active==key else ""}>{label}</a>' for key,label in [('about','About'),('data','Data'),('science','Science')])
    fresh='Fresh data' if quality['state']=='healthy' else 'Data incomplete or stale: last available estimates shown'
    reasons=' '.join(quality.get('reasons',[]))
    detail='' if quality['state']=='healthy' else f'<p id="stale-detail">{e(reasons)} Last available values remain below for reference. They do not confirm current conditions or road safety.</p>'
    return f'''<link rel="stylesheet" href="assets/community.css">
<a class="skip-link" href="#main-content">Skip to content</a>
<header class="community-header"><div class="community-header-inner"><a class="community-brand" href="index.html">Mathews Flood Monitor<small>Blackwater &amp; Mobjack Bay Estates, Virginia</small></a>
<button id="mobile-menu-btn" aria-label="Toggle Navigation" aria-expanded="false" aria-controls="mobile-menu">Menu</button>
<nav id="mobile-menu" aria-label="Main navigation">{links}<details><summary>More</summary><div>{extra}</div></details></nav></div></header>
<aside id="data-freshness" role="status" class="freshness"><strong id="freshness-label">{fresh}</strong><span id="update-age">Updated {e(when(status.get('status_generated_at_utc')))}</span>
{detail}<details><summary>Data times &amp; alerts</summary><p>Ware River observation: {e(when(curr.get('observation_timestamp_local')))}<br>Forecast issued: {e(when(status.get('display_forecast_issued_at_utc') or status.get('forecast_issued_at_utc')))}<br>Forecast saved: {e(when(status.get('display_forecast_saved_at_utc') or status.get('status_generated_at_utc')))}<br>Website generated: {e(when(status.get('status_generated_at_utc')))}</p>
<p>{'Mobile push alerts are enabled for subscribers.' if status.get('alerting_enabled') else 'Mobile push alerts are not enabled.'} Dispatch status does not confirm reception on a phone.</p></details><button type="button" id="refresh-data">Check for an update</button><a href="https://github.com/flatfoot584/mathews-flood-monitor/actions/workflows/update_flood_monitor.yml">Pipeline status &amp; failure details</a></aside>'''

def footer(status):
    timeline=status.get('forecast_hourly_timeline',[])
    stamps=json.dumps({'generated':str(status.get('status_generated_at_utc','')),'observed':str(status.get('current_conditions',{}).get('observation_timestamp_local','')),'forecastSaved':str(status.get('display_forecast_saved_at_utc') or status.get('status_generated_at_utc','')),'forecastEnd':str(timeline[-1].get('timestamp_utc','')) if timeline else '', 'quality':status.get('data_quality',{})}).replace('<','\\u003c')
    return f'''<footer class="community-footer"><div><strong>Independent community research</strong><p>Maintained by Howard Hottinger using NOAA and USGS data. Estimates cover Blackwater and Mobjack Bay Estates, not all of Mathews County. No agency endorsement is implied.</p>
<a href="about.html">About this project</a> · <a href="https://github.com/flatfoot584/mathews-flood-monitor/issues/new">Report a problem or observed flooding</a> · <a href="science.html">Methods &amp; evidence</a></div><p>Scheduled updates every 30 minutes, with possible delays. Never enter flooded roads. Follow official warnings and local emergency instructions.</p></footer>
<script id="freshness-times" type="application/json">{stamps}</script><script src="assets/community.js"></script>'''

def official(status=None):
    feed=(status or {}).get('official_nws_alerts',{})
    from runtime_safety import is_recent
    fresh=feed.get('available') and is_recent(feed.get('retrieved_at_utc'))
    items=''.join(f'<li><strong>{e(item.get("event"))}</strong>: {e(item.get("headline"))} (expires {e(when(item.get("expires")))})</li>' for item in feed.get('alerts',[]) if parse_timestamp(item.get('expires')) and parse_timestamp(item['expires'])>__import__('datetime').datetime.now(timezone.utc)) if fresh else ''
    state=('Official feed reports active alerts:' if items else 'No active NWS alerts returned for this point at the displayed check time; this does not verify road safety.') if fresh else 'Official alert feed unavailable or stale. Check NWS directly.'
    checked=when(feed.get('retrieved_at_utc'))
    warning=f'<div data-official-feed><p>{e(state)} Checked {e(checked)}.</p><ul>{items}</ul></div>'
    return warning+'''<aside class="official-card"><strong>Official warnings &amp; emergency guidance</strong><p>This monitor provides local estimates. Check <a href="https://www.weather.gov/akq/">NWS Wakefield warnings</a> and <a href="https://www.mathewscountyva.gov/">Mathews County emergency information</a>. Call 911 for an immediate emergency. <a href="https://www.weather.gov/safety/flood-turn-around-dont-drown">Never drive into floodwater.</a></p></aside>'''

def stoplight_meta(tier, is_available=True):
    if not is_available or tier is None or tier < 0:
        return {
            'class': 'stoplight-unknown',
            'badge': '<div class="stoplight-badge badge-unknown"><span class="stoplight-dot"></span> Status Unknown</div>',
            'color': 'unknown'
        }
    if tier == 0:
        return {
            'class': 'stoplight-green',
            'badge': '<div class="stoplight-badge badge-green"><span class="stoplight-dot"></span> Good · No Flooding</div>',
            'color': 'green'
        }
    if tier in (1, 2):
        text = 'Caution · Some Flooding' if tier == 1 else 'Caution · Moderate Flooding'
        return {
            'class': 'stoplight-yellow',
            'badge': f'<div class="stoplight-badge badge-yellow"><span class="stoplight-dot"></span> {text}</div>',
            'color': 'yellow'
        }
    return {
        'class': 'stoplight-red',
        'badge': '<div class="stoplight-badge badge-red"><span class="stoplight-dot"></span> Danger · Severe Flooding — Extreme Caution</div>',
        'color': 'red'
    }

def summary(status):
    curr=status.get('last_available_current_conditions') or status.get('current_conditions',{});out=status.get('forecast_48h_outlook',{});q=status['data_quality']
    timeline=status.get('forecast_hourly_timeline',[])
    current_streets=curr.get('community_streets',{})
    affected=set()
    flooding=[]
    for row in timeline:
        wet=[name for name,item in row.get('community_streets',{}).items() if finite_number(item.get('depth_in')) and item['depth_in']>0]
        affected.update(wet)
        if wet: flooding.append(row)
    peak=out.get('peak_forecast_stage_mllw_ft')

    stage_val = curr.get('ware_river_stage_mllw_ft')
    has_curr = finite_number(stage_val)
    now_tier = curr.get('flood_risk_tier', 0) if has_curr else -1

    has_forecast = finite_number(peak)
    next_tier = out.get('peak_risk_tier', 0) if has_forecast else -1

    now_sl = stoplight_meta(now_tier, has_curr)
    next_sl = stoplight_meta(next_tier, has_forecast)
    valid_tiers = [t for t in (now_tier, next_tier) if t >= 0]
    worst_tier = max(valid_tiers) if valid_tiers else -1
    streets_sl = stoplight_meta(worst_tier, bool(valid_tiers))

    now_meter = ''
    if has_curr:
        now_pct = max(3, min(100, int((stage_val / 5.0) * 100)))
        diff = 3.99 - stage_val
        diff_txt = f"{diff:.2f}' below ditch threshold" if diff > 0 else f"{abs(diff):.2f}' above ditch threshold"
        now_meter = f'''<div class="stage-meter" aria-hidden="true" title="{diff_txt}"><div class="stage-meter-fill fill-{now_sl['color']}" style="width: {now_pct}%"></div><div class="stage-meter-threshold" style="left: 79.8%"></div></div><div class="stage-meter-labels"><span>0' Safe</span><span title="Ditch overflow threshold">3.99' Ditch Brim</span><span>5.0'+ Severe</span></div>'''

    next_meter = ''
    if has_forecast:
        next_pct = max(3, min(100, int((peak / 5.0) * 100)))
        pdiff = 3.99 - peak
        pdiff_txt = f"{pdiff:.2f}' below ditch threshold" if pdiff > 0 else f"{abs(pdiff):.2f}' above ditch threshold"
        next_meter = f'''<div class="stage-meter" aria-hidden="true" title="{pdiff_txt}"><div class="stage-meter-fill fill-{next_sl['color']}" style="width: {next_pct}%"></div><div class="stage-meter-threshold" style="left: 79.8%"></div></div><div class="stage-meter-labels"><span>0' Safe</span><span title="Ditch overflow threshold">3.99' Ditch Brim</span><span>5.0'+ Severe</span></div>'''

    if not q['current_available']:
        now_label = 'Last observation; current conditions unknown'
    elif now_tier >= 3:
        now_label = 'Severe property flooding estimated'
    elif now_tier == 2:
        now_label = 'Moderate road flooding estimated'
    elif now_tier == 1:
        now_label = 'Flooding estimated in low spots'
    else:
        now_label = 'No tidal inundation estimated'

    if not q['forecast_available']:
        next_label = 'Last available forecast; check its dates'
    elif next_tier >= 3:
        next_label = 'Severe flooding estimated · Extreme caution'
    elif next_tier == 2:
        next_label = 'Moderate road flooding estimated'
    elif next_tier == 1:
        next_label = 'Flooding estimated in low spots'
    else:
        next_label = 'No inundation estimated'

    streets=', '.join(sorted(affected)) if affected else 'No street inundation estimated in the saved timeline' if timeline else 'Street conditions unknown'
    nowwet=', '.join(name for name,item in current_streets.items() if finite_number(item.get('depth_in')) and item['depth_in']>0) or 'No street inundation estimated'
    timing='No modeled street flooding in the available timeline.'
    if flooding:
        timing=f'First modeled street flooding: {when(flooding[0]["timestamp_local"])}. Last modeled flooded hour: {when(flooding[-1]["timestamp_local"])}. {len(flooding)} flooded hourly intervals, which may be separated.'
        if timeline and flooding[-1]==timeline[-1]:timing+=' Flooding continues beyond this forecast window; drainage time is unknown.'
        else:timing+=' Receding estimates do not establish when roads will be safe.'
    if not q['forecast_available']:timing+=' Forecast coverage is incomplete.'
    action='Plan before flooding starts; never enter floodwater.' if affected else 'Check actual conditions before travel; keep watching updates.'
    depth_description = f"Peak local reference depth: {number(out.get('peak_estimated_flood_depth_in'),' in')}, at {when(out.get('peak_depth_time_local'))}. Street depths vary." if finite_number(out.get('peak_estimated_flood_depth_in')) and out['peak_estimated_flood_depth_in']>0 else 'No inundation modeled at the local reference point. Low streets may still flood; see affected streets below.' if out.get('peak_estimated_flood_depth_in')==0 else 'Local depth estimate unavailable.'
    chips = ''.join(f'<span class="street-chip chip-yellow"><span class="stoplight-dot" style="background:#ca8a04"></span>{e(st)}</span>' for st in sorted(affected))
    chips_html = f'<div class="street-chips">{chips}</div>' if affected else ''
    return f'''<section class="resident-intro"><p class="eyebrow">Blackwater &amp; Mobjack Bay Estates</p><h1>Your local flood outlook</h1><p>Independent community research using NOAA and USGS data.</p></section>
<section data-current-safety class="resident-grid" aria-label="Current conditions and forecast"><article class="resident-card {now_sl['class']}">{now_sl['badge']}<p class="eyebrow" data-age-label data-last-label="Last Ware River observation">Now · Ware River observation</p><h2 data-age-label data-last-label="Last observation; current conditions unknown">{e(now_label)}</h2><p class="resident-value">{number(curr.get('ware_river_stage_mllw_ft'),' ft',2)} <small>MLLW at the gauge</small></p>{now_meter}<p>Observed {e(when(curr.get('observation_timestamp_local')))}</p><p>Local reference estimate: <strong>{number(curr.get('estimated_local_flood_depth_in'),' in')}</strong></p><details><summary>Where &amp; what this measures</summary><p class="muted">Empirical low-point reference near Daniel Ave &amp; Julian St. {e(nowwet)}. Estimates use tidal water levels; recent rainfall is not measured here.</p></details></article>
<article class="resident-card {next_sl['class']}">{next_sl['badge']}<p class="eyebrow" data-age-label data-last-label="Last saved forecast · Model estimate">Next 48 hours · Model estimate</p><h2 data-age-label data-last-label="Last available forecast; check its dates">{e(next_label)}</h2><p class="resident-value">{number(peak,' ft',2)} <small>peak Ware River stage</small></p>{next_meter}<p><strong>{e(when(out.get('peak_forecast_stage_time_local')))}</strong></p><details><summary>Depth &amp; uncertainty</summary><p>{e(depth_description)}</p><p class="muted">Scenario range {number(out.get('peak_forecast_stage_q10_ft'))} to {number(out.get('peak_forecast_stage_q90_ft'))} ft. Uncalibrated; not a guaranteed upper bound.</p></details></article></section>
<section data-current-safety class="resident-card {streets_sl['class']}">{streets_sl['badge']}<h2>Potentially affected streets</h2><p>{e(streets)}</p>{chips_html}<details><summary>Estimated timing &amp; duration</summary><p>{e(timing)}</p></details><h3>What to do</h3><p><strong>{e(action)}</strong> Map colors and model estimates do not verify road safety for any vehicle.</p><a class="resident-button" href="alerts.html">Set up mobile alerts</a> <a href="guide.html">Understand flood estimates</a></section>{official(status)}'''

def forecast_table(status):
    rows=[]
    for r in status.get('forecast_hourly_timeline',[])[:48]:
        rows.append(f'<tr><th scope="row">{e(when(r.get("timestamp_local")))}</th><td>{number(r.get("forecast_stage_mllw_ft"))}</td><td>{number(r.get("compound_flood_depth_in"))}</td><td>{number(r.get("rain_forecast_hourly_in"))}</td><td>{"Complete" if r.get("weather_available") and r.get("precipitation_available") else "Incomplete"}</td></tr>')
    return '<details data-current-safety class="forecast-table"><summary data-age-label data-last-label="View last saved hourly forecast table">View accessible hourly forecast table</summary><div class="table-scroll"><table><caption>Local reference depth is an estimate, not a road measurement. All times Eastern.</caption><thead><tr><th scope="col">Time</th><th scope="col">Ware stage (ft MLLW)</th><th scope="col">Local depth (in)</th><th scope="col">Rain (in)</th><th scope="col">Weather coverage</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div></details>'

def evidence_section():
    path = Path('models/fort_monroe_evaluation.json')
    vpath = Path('models/live_verification.json')
    card1 = ''
    if path.exists():
        report = json.loads(path.read_text())
        rows = []
        for r in report.get('results', []):
            rows.append(f'<tr><th scope="row">{r["horizon_hours"]} hours</th><td>{r["baseline"]["test"]["mae_ft"]:.3f}</td><td>{r["fort_monroe"]["test"]["mae_ft"]:.3f}</td><td>{r["improvement_pct"]:+.1f}%</td></tr>')
        card1 = '''<section class="resident-card"><h2>Fort Monroe: measured historical contribution</h2><p>2024 held-out causal forecasts use past observations and known astronomical tides. This comparison uses a Ridge baseline, not archived issued NOAA guidance. A historical gain cannot establish improvement to the deployed forecast.</p><div class="table-scroll"><table><thead><tr><th>Lead time</th><th>Baseline MAE (ft)</th><th>With Fort Monroe MAE (ft)</th><th>Change in skill</th></tr></thead><tbody>''' + ''.join(rows) + '''</tbody></table></div><p>Fort Monroe is collected for evaluation. The current operational forecast remains in use pending paired prospective evidence.</p><a href="models/fort_monroe_evaluation.json">Download experiment metrics and limitations</a></section>'''

    card2 = ''
    if vpath.exists():
        vdata = json.loads(vpath.read_text())
        vrows = []
        for r in vdata.get('results', []):
            op_mae = f"{r['mae_ft']:.3f} ft" if r.get('mae_ft') is not None else "—"
            nw_mae = f"{r['nwps_mae_ft']:.3f} ft" if r.get('nwps_mae_ft') is not None else "—"
            diff = r.get('skill_delta_ft')
            diff_str = f"{diff:+.3f} ft ({r.get('skill_improvement_pct'):+.1f}%)" if diff is not None and r.get('skill_improvement_pct') is not None else (f"{diff:+.3f} ft" if diff is not None else "—")
            hw_n = r.get('high_water_n', 0)
            hw_str = f"{hw_n} (miss: {r.get('misses', 0)} op / {r.get('nwps_misses', 0)} nwps)" if hw_n > 0 else "0"
            vrows.append(f'<tr><th scope="row">{r["lead_hours"]} hours</th><td>{r.get("n", 0)}</td><td>{op_mae}</td><td>{nw_mae}</td><td>{diff_str}</td><td>{hw_str}</td></tr>')
        sumry = vdata.get('summary', {})
        summary_note = ''
        if sumry.get('overall_operational_mae_ft') is not None and sumry.get('overall_nwps_mae_ft') is not None:
            summary_note = f'<p><strong>Overall Autumn 2026 Verification:</strong> Operational Model MAE = {sumry["overall_operational_mae_ft"]:.3f} ft vs Raw NOAA NWPS MAE = {sumry["overall_nwps_mae_ft"]:.3f} ft (Operational skill improvement: {sumry.get("overall_skill_improvement_pct", 0):+.1f}% across {sumry.get("verified_rows", 0)} verified issues).</p>'
        card2 = f'''<section class="resident-card"><h2>Prospective Verification: Operational Model vs. Raw NOAA NWPS</h2><p>Durable issue-time validation archived in <code>issued_forecast_archive.csv</code> across autumn 2026. Gauges paired against verified Ware River stage (WRVV2). High-water events track threshold breaches (&ge; 4.00 ft MLLW).</p>{summary_note}<div class="table-scroll"><table><thead><tr><th>Lead time</th><th>Verified (N)</th><th>Operational MAE</th><th>Raw NWPS MAE</th><th>Skill Δ (Improvement)</th><th>High-water (&ge; 4.0 ft)</th></tr></thead><tbody>{''.join(vrows)}</tbody></table></div><p><a href="models/live_verification.json">Download live verification JSON</a> · <a href="issued_forecast_archive.csv">Download complete issued forecast archive CSV</a></p></section>'''

    return card1 + card2

def alerts(status,server,topic):
    url=e(server+'/'+topic); t=e(topic)
    devices = [
        ('iPhone & iPad', 'fa-brands fa-apple', 'https://apps.apple.com/app/ntfy/id1625396347', 'In Settings, allow ntfy notifications, sounds and banners. Focus and silent settings can suppress sound.'),
        ('Android', 'fa-brands fa-android', 'https://play.google.com/store/apps/details?id=io.heckel.ntfy', 'Allow ntfy notifications. If delivery is delayed, review battery restrictions for the app.'),
        ('Browser & Desktop', 'fa-solid fa-desktop', server+'/'+topic, 'Open the channel, choose Subscribe, and allow notifications. Browser and operating-system support vary; use the mobile app for your phone.')
    ]
    cards=[]
    for name,icon,link,description in devices:
        mobile = name != 'Browser & Desktop'
        steps = f'<li><a href="{e(link)}" target="_blank" rel="noopener">Install the ntfy app</a>.</li><li>Open ntfy, add a subscription on {e(server)}, and enter topic <code>{t}</code>.</li><li>Tap Subscribe. {e(description)}</li>' if mobile else f'<li><a href="{url}" target="_blank" rel="noopener">Open the web channel</a>.</li><li>{e(description)}</li>'
        cards.append(f'<details class="resident-card device" open><summary><i class="{icon} mr-2"></i>{name}</summary><ol>{steps}</ol></details>')
    return f'''<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Mobile alerts | Mathews Flood Monitor</title><link rel="stylesheet" href="assets/tailwind.css"><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" integrity="sha384-t1nt8BQoYMLFN5p42tRAtuAAFQaCQODekUVeKKZrEnEyp4H2R0RHFz0KWpmj7i8g" crossorigin="anonymous"><link rel="stylesheet" href="assets/community.css"></head><body>{navbar('alerts',status)}<main id="main-content" class="resident-main"><section class="resident-intro"><p class="eyebrow">Community flood alerts</p><h1>Set up alerts on your device</h1><p>Choose your device, subscribe to the existing channel, then check notification settings.</p></section><div class="device-grid">{''.join(cards)}</div>
<section class="resident-card"><h2>Your community channel</h2><p>Server: <code>{e(server)}</code><br>Topic: <code>{t}</code></p><button class="resident-button" id="copy-topic" data-topic="{t}"><i class="fa-regular fa-copy mr-1"></i>Copy topic</button> <a href="{url}" target="_blank" rel="noopener" class="resident-button" style="background:#0f172a"><i class="fa-solid fa-arrow-up-right-from-square mr-1"></i>Open channel</a><p id="copy-feedback" role="status"></p><details><summary>Open with a QR code</summary><div style="padding:16px 0"><img width="180" height="180" alt="QR code opening the community ntfy channel" src="https://api.qrserver.com/v1/create-qr-code/?size=180x180&amp;data={url}" style="border-radius:12px;border:1px solid #e2e8f0;box-shadow:0 4px 12px rgba(0,0,0,0.06)"></div><p>Scan with your phone camera to open the topic in ntfy. Complete subscription and notification setup to receive alerts.</p></details></section>
<section class="resident-card"><h2>Verify setup on your own device</h2><ol><li>Confirm the topic appears in your subscription list.</li><li>Check your operating system's ntfy notification permissions and sound settings.</li><li>Use a separate personal test topic to verify delivery to your device. Do not publish tests to the community channel.</li></ol><p>Seeing messages in a feed does not confirm background push delivery. No test is broadcast by this page.</p></section>
<section class="resident-card"><h2>What to expect</h2><p>The pipeline is scheduled about every 30 minutes and sends initial hazard, escalation, crest reminder, and modeled hazard-ended notifications with duplicate suppression. Independent monitoring sends a data-service warning when a run fails or published data becomes stale, identifies the failing step when known, and sends one recovery notice. An unchanged outage is repeated at most every six hours. Health notices use this channel unless the maintainer configures a separate channel.</p><p>GitHub schedules and notification delivery may be delayed. Old forecasts remain visible with dates and age warnings. A recovery notice does not confirm that roads are clear. Do not rely on an alert as your sole warning source.</p><p>The project currently charges no subscription fee. ntfy is open-source; service terms and availability can change. The existing public topic requires no account and is writable by others, so verify unusual messages against the dashboard and official warnings.</p><p>Sound, overnight delivery, battery use and wake behavior depend on your device, connection, app and settings. Remove the topic from ntfy to unsubscribe.</p></section>{official(status)}</main>{footer(status)}</body></html>'''

def monitoring(status):
    fort=status.get('fort_monroe',{})
    verification=status.get('live_verification',{})
    verified=sum(r.get('n',0) for r in verification.get('results',[]))
    summary=verification.get('summary',{})
    rows=[]
    for r in verification.get('results',[]):
        lead=f'{r["lead_hours"]} hours'
        n_cnt=r.get('n',0)
        op_mae=number(r.get('mae_ft'),' ft',2) if r.get('mae_ft') is not None else '—'
        nwps_mae=number(r.get('nwps_mae_ft'),' ft',2) if r.get('nwps_mae_ft') is not None else '—'
        diff=r.get('skill_delta_ft')
        diff_str=f"{diff:+.2f} ft" if diff is not None else '—'
        hw_n=r.get('high_water_n',0)
        hw_desc=f"{hw_n} (miss: {r.get('misses',0)} op / {r.get('nwps_misses',0)} nwps)" if hw_n>0 else "0"
        rows.append(f'<tr><th scope="row">{lead}</th><td>{n_cnt}</td><td>{op_mae}</td><td>{nwps_mae}</td><td>{diff_str}</td><td>{hw_desc}</td></tr>')
    rows_html=''.join(rows)
    overall_comp=''
    if summary.get('overall_operational_mae_ft') is not None and summary.get('overall_nwps_mae_ft') is not None:
        op_all=number(summary['overall_operational_mae_ft'],' ft',2)
        nwps_all=number(summary['overall_nwps_mae_ft'],' ft',2)
        overall_comp=f'<p class="muted">Overall verified accuracy: Operational model MAE = <strong>{op_all}</strong> vs Raw NOAA NWPS MAE = <strong>{nwps_all}</strong> across autumn 2026 events.</p>'
    return f'''<section data-current-safety class="resident-card"><h2>Fort Monroe sensor &amp; forecast verification</h2><p><a href="https://waterdata.usgs.gov/monitoring-location/USGS-0204289994/">Fort Monroe USGS 0204289994 / FTMV2</a>: {number(fort.get('elevation_navd88_ft'),' ft NAVD88')}, observed {e(when(fort.get('observation_time_utc')))}. {'Fresh observation' if fort.get('fresh') else 'Missing or stale observation'}.</p><p>Evaluation sensor: its measurements are being archived. It has not been promoted into the operational forecast. <a href="science.html">See the historical comparison and promotion criteria</a>.</p><details><summary>Prospective forecast-versus-observed scorecard (Operational vs. Raw NWPS)</summary><p>{verified} matched issued predictions. Scores compare the deployed water-level forecast and raw NOAA NWPS guidance with the Ware River gauge, not measurements of local road depth. Repeated forecast issues are correlated; storm skill continues accumulating across autumn 2026.</p>{overall_comp}<div class="table-scroll"><table><thead><tr><th scope="col">Lead</th><th scope="col">Verified</th><th scope="col">Model MAE</th><th scope="col">Raw NWPS MAE</th><th scope="col">Skill Δ</th><th scope="col">High-water (&ge; 4.0 ft)</th></tr></thead><tbody>{rows_html}</tbody></table></div><a href="models/live_verification.json">Download prospective scores</a> · <a href="issued_forecast_archive.csv">Download issued forecast archive CSV</a></details></section>'''

def reporting():
    return '''<section class="resident-card"><h2>Report observed flooding for review</h2><p>Prepare a report below, then submit it through the maintainer's <a href="https://github.com/flatfoot584/mathews-flood-monitor/issues/new">GitHub issue review queue</a> (account required). This page creates a draft on your device; it does not send or upload anything. Reports are unverified until reviewed and never enter training automatically.</p>
<form id="report-form"><label>Street or public landmark<input name="location" required maxlength="120" placeholder="For example, Daniel Ave at Julian St"></label><label>Observation date and time (Eastern)<input name="time" type="datetime-local" required></label><label>Measured depth in inches, if known<input name="depth" type="number" min="0" max="120" step="0.25"></label><label>What did you observe?<textarea name="notes" required maxlength="2000" rows="3"></textarea></label><label class="consent"><input type="checkbox" required> I consent to maintainer review and understand that submitted issue text is public. I will omit private addresses and identifying details. If I attach a photo in the issue, I have permission to share it and will remove faces and license plates.</label><button class="resident-button" type="submit">Prepare report draft</button></form>
<div id="report-result" hidden><p><strong>Draft ready, not submitted.</strong> Review it before copying it into a GitHub issue. Avoid approaching floodwater to collect a measurement.</p><pre id="report-draft"></pre><button id="download-report" class="resident-button" type="button">Download draft</button><a href="https://github.com/flatfoot584/mathews-flood-monitor/issues/new">Open review queue</a></div></section>'''
