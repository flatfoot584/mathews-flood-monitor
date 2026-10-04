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
    fresh='Fresh data' if quality['state']=='healthy' else 'Data incomplete or stale'
    return f'''<link rel="stylesheet" href="assets/community.css">
<a class="skip-link" href="#main-content">Skip to content</a>
<header class="community-header"><div class="community-header-inner"><a class="community-brand" href="index.html">Mathews Flood Monitor<small>Blackwater &amp; Mobjack Bay Estates, Virginia</small></a>
<button id="mobile-menu-btn" aria-label="Toggle Navigation" aria-expanded="false" aria-controls="mobile-menu">Menu</button>
<nav id="mobile-menu" aria-label="Main navigation">{links}<details><summary>More</summary><div>{extra}</div></details></nav></div></header>
<aside id="data-freshness" role="status" class="freshness"><strong id="freshness-label">{fresh}</strong><span>Updated {e(when(status.get('status_generated_at_utc')))}</span>
<details><summary>Data times &amp; alerts</summary><p>Ware River observation: {e(when(curr.get('observation_timestamp_local')))}<br>Forecast issued: {e(when(status.get('forecast_issued_at_utc')))}<br>Website generated: {e(when(status.get('status_generated_at_utc')))}</p>
<p>{'Mobile push alerts are enabled for subscribers.' if status.get('alerting_enabled') else 'Mobile push alerts are not enabled.'} Dispatch status does not confirm reception on a phone.</p></details></aside>'''

def footer(status):
    stamps=json.dumps({'generated':str(status.get('status_generated_at_utc','')),'observed':str(status.get('current_conditions',{}).get('observation_timestamp_local',''))}).replace('<','\\u003c')
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

def summary(status):
    curr=status.get('current_conditions',{});out=status.get('forecast_48h_outlook',{});q=status['data_quality']
    timeline=status.get('forecast_hourly_timeline',[])
    current_streets=curr.get('community_streets',{})
    affected=set()
    flooding=[]
    for row in timeline:
        wet=[name for name,item in row.get('community_streets',{}).items() if finite_number(item.get('depth_in')) and item['depth_in']>0]
        affected.update(wet)
        if wet: flooding.append(row)
    peak=out.get('peak_forecast_stage_mllw_ft')
    now_label='Conditions unknown' if not q['current_available'] else 'Flooding estimated in low spots' if curr.get('flood_risk_tier',0)>0 else 'No tidal inundation estimated'
    next_label='Forecast incomplete' if not q['forecast_available'] else 'Flooding estimated in low spots' if out.get('peak_risk_tier',0)>0 else 'No inundation estimated'
    streets=', '.join(sorted(affected)) if affected else 'No street inundation estimated' if q['forecast_available'] else 'Street conditions unknown'
    nowwet=', '.join(name for name,item in current_streets.items() if finite_number(item.get('depth_in')) and item['depth_in']>0) or 'No street inundation estimated'
    timing='No modeled street flooding in the available timeline.'
    if flooding:
        timing=f'First modeled street flooding: {when(flooding[0]["timestamp_local"])}. Last modeled flooded hour: {when(flooding[-1]["timestamp_local"])}. {len(flooding)} flooded hourly intervals, which may be separated.'
        if timeline and flooding[-1]==timeline[-1]:timing+=' Flooding continues beyond this forecast window; drainage time is unknown.'
        else:timing+=' Receding estimates do not establish when roads will be safe.'
    if not q['forecast_available']:timing+=' Forecast coverage is incomplete.'
    action='Plan before flooding starts; never enter floodwater.' if affected else 'Check actual conditions before travel; keep watching updates.'
    depth_description = f"Peak local reference depth: {number(out.get('peak_estimated_flood_depth_in'),' in')}, at {when(out.get('peak_depth_time_local'))}. Street depths vary." if finite_number(out.get('peak_estimated_flood_depth_in')) and out['peak_estimated_flood_depth_in']>0 else 'No inundation modeled at the local reference point. Low streets may still flood; see affected streets below.' if out.get('peak_estimated_flood_depth_in')==0 else 'Local depth estimate unavailable.'
    return f'''<section class="resident-intro"><p class="eyebrow">Blackwater &amp; Mobjack Bay Estates</p><h1>Your local flood outlook</h1><p>Independent community research using NOAA and USGS data.</p></section>
<section data-current-safety class="resident-grid" aria-label="Current conditions and forecast"><article class="resident-card"><p class="eyebrow">Now · Ware River observation</p><h2>{e(now_label)}</h2><p class="resident-value">{number(curr.get('ware_river_stage_mllw_ft'),' ft',2)} <small>MLLW at the gauge</small></p><p>Local reference estimate: <strong>{number(curr.get('estimated_local_flood_depth_in'),' in')}</strong></p><details><summary>Where &amp; what this measures</summary><p class="muted">Empirical low-point reference near Daniel Ave &amp; Julian St. {e(nowwet)}. Current estimates use tidal water levels; recent rainfall is not measured here.</p></details></article>
<article class="resident-card"><p class="eyebrow">Next 48 hours · Model estimate</p><h2>{e(next_label)}</h2><p class="resident-value">{number(peak,' ft',2)} <small>peak Ware River stage</small></p><p><strong>{e(when(out.get('peak_forecast_stage_time_local')))}</strong></p><details><summary>Depth &amp; uncertainty</summary><p>{e(depth_description)}</p><p class="muted">Scenario range {number(out.get('peak_forecast_stage_q10_ft'))} to {number(out.get('peak_forecast_stage_q90_ft'))} ft. Uncalibrated; not a guaranteed upper bound.</p></details></article></section>
<section data-current-safety class="resident-card"><h2>Potentially affected streets</h2><p>{e(streets)}</p><details><summary>Estimated timing &amp; duration</summary><p>{e(timing)}</p></details><h3>What to do</h3><p><strong>{e(action)}</strong> Map colors and model estimates do not verify road safety for any vehicle.</p><a class="resident-button" href="alerts.html">Set up mobile alerts</a> <a href="guide.html">Understand flood estimates</a></section>{official(status)}'''

def forecast_table(status):
    rows=[]
    for r in status.get('forecast_hourly_timeline',[])[:48]:
        rows.append(f'<tr><th scope="row">{e(when(r.get("timestamp_local")))}</th><td>{number(r.get("forecast_stage_mllw_ft"))}</td><td>{number(r.get("compound_flood_depth_in"))}</td><td>{number(r.get("rain_forecast_hourly_in"))}</td><td>{"Complete" if r.get("weather_available") and r.get("precipitation_available") else "Incomplete"}</td></tr>')
    return '<details data-current-safety class="forecast-table"><summary>View accessible hourly forecast table</summary><div class="table-scroll"><table><caption>Local reference depth is an estimate, not a road measurement. All times Eastern.</caption><thead><tr><th scope="col">Time</th><th scope="col">Ware stage (ft MLLW)</th><th scope="col">Local depth (in)</th><th scope="col">Rain (in)</th><th scope="col">Weather coverage</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div></details>'

def evidence_section():
    path=Path('models/fort_monroe_evaluation.json')
    if not path.exists():return '<section class="resident-card"><h2>Fort Monroe evaluation</h2><p>Historical comparison pending. No live improvement has been established.</p></section>'
    report=json.loads(path.read_text());rows=[]
    for r in report.get('results',[]):
        rows.append(f'<tr><th scope="row">{r["horizon_hours"]} hours</th><td>{r["baseline"]["test"]["mae_ft"]:.3f}</td><td>{r["fort_monroe"]["test"]["mae_ft"]:.3f}</td><td>{r["improvement_pct"]:+.1f}%</td></tr>')
    return '''<section class="resident-card"><h2>Fort Monroe: measured historical contribution</h2><p>2024 held-out causal forecasts use past observations and known astronomical tides. This comparison uses a Ridge baseline, not archived issued NOAA guidance. A historical gain cannot establish improvement to the deployed forecast.</p><div class="table-scroll"><table><thead><tr><th>Lead time</th><th>Baseline MAE (ft)</th><th>With Fort Monroe MAE (ft)</th><th>Change in skill</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table></div><p>Fort Monroe is collected for evaluation. The current operational forecast remains in use pending paired prospective evidence.</p><a href="models/fort_monroe_evaluation.json">Download experiment metrics and limitations</a></section>'''

def alerts(status,server,topic):
    url=e(server+'/'+topic); t=e(topic)
    cards=[]
    for name,link,description in [('iPhone & iPad','https://apps.apple.com/app/ntfy/id1625396347','In Settings, allow ntfy notifications, sounds and banners. Focus and silent settings can suppress sound.'),('Android','https://play.google.com/store/apps/details?id=io.heckel.ntfy','Allow ntfy notifications. If delivery is delayed, review battery restrictions for the app.'),('Browser',server+'/'+topic,'Open the channel, choose Subscribe, and allow notifications. Browser and operating-system support vary; use the mobile app for your phone.')]:
        mobile=name!='Browser'
        steps=f'<li><a href="{e(link)}" target="_blank" rel="noopener">Install the ntfy app</a>.</li><li>Open ntfy, add a subscription on {e(server)}, and enter topic <code>{t}</code>.</li><li>Tap Subscribe. {e(description)}</li>' if mobile else f'<li><a href="{url}" target="_blank" rel="noopener">Open the web channel</a>.</li><li>{e(description)}</li>'
        cards.append(f'<details class="resident-card device"><summary>{name}</summary><ol>{steps}</ol></details>')
    return f'''<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Mobile alerts | Mathews Flood Monitor</title><link rel="stylesheet" href="assets/community.css"></head><body>{navbar('alerts',status)}<main id="main-content" class="resident-main"><section class="resident-intro"><p class="eyebrow">Community flood alerts</p><h1>Set up alerts on your device</h1><p>Choose your device, subscribe to the existing channel, then check notification settings.</p></section><div class="device-grid">{''.join(cards)}</div>
<section class="resident-card"><h2>Your community channel</h2><p>Server: <code>{e(server)}</code><br>Topic: <code>{t}</code></p><button class="resident-button" id="copy-topic" data-topic="{t}">Copy topic</button> <a href="{url}" target="_blank" rel="noopener">Open channel</a><p id="copy-feedback" role="status"></p><details><summary>Open with a QR code</summary><img width="180" height="180" alt="QR code opening the community ntfy channel" src="https://api.qrserver.com/v1/create-qr-code/?size=180x180&amp;data={url}"><p>The QR code opens the topic. Complete subscription and notification setup to receive alerts.</p></details></section>
<section class="resident-card"><h2>Verify setup on your own device</h2><ol><li>Confirm the topic appears in your subscription list.</li><li>Check your operating system's ntfy notification permissions and sound settings.</li><li>Use a separate personal test topic to verify delivery to your device. Do not publish tests to the community channel.</li></ol><p>Seeing messages in a feed does not confirm background push delivery. No test is broadcast by this page.</p></section>
<section class="resident-card"><h2>What to expect</h2><p>The pipeline checks fresh data about every 30 minutes and sends initial hazard, escalation, crest reminder, and modeled hazard-ended notifications with duplicate suppression. Updates and delivery may be delayed. Do not rely on an alert as your sole warning source.</p><p>The project currently charges no subscription fee. ntfy is open-source; service terms and availability can change. The existing public topic requires no account and is writable by others, so verify unusual messages against the dashboard and official warnings.</p><p>Sound, overnight delivery, battery use and wake behavior depend on your device, connection, app and settings. Remove the topic from ntfy to unsubscribe.</p></section>{official(status)}</main>{footer(status)}</body></html>'''

def monitoring(status):
    fort=status.get('fort_monroe',{})
    verification=status.get('live_verification',{})
    verified=sum(r.get('n',0) for r in verification.get('results',[]))
    rows=''.join(f'<tr><th scope="row">{r["lead_hours"]} hours</th><td>{r.get("n",0)}</td><td>{number(r.get("mae_ft"))}</td><td>{r.get("high_water_n",0)}</td></tr>' for r in verification.get('results',[]))
    return f'''<section data-current-safety class="resident-card"><h2>Fort Monroe sensor &amp; forecast verification</h2><p><a href="https://waterdata.usgs.gov/monitoring-location/USGS-0204289994/">Fort Monroe USGS 0204289994 / FTMV2</a>: {number(fort.get('elevation_navd88_ft'),' ft NAVD88')}, observed {e(when(fort.get('observation_time_utc')))}. {'Fresh observation' if fort.get('fresh') else 'Missing or stale observation'}.</p><p>Evaluation sensor: its measurements are being archived. It has not been promoted into the operational forecast. <a href="science.html">See the historical comparison and promotion criteria</a>.</p><details><summary>Prospective forecast-versus-observed scorecard</summary><p>{verified} matched issued predictions. Scores compare the deployed water-level forecast with the Ware River gauge, not measurements of local road depth. Repeated forecast issues are correlated; storm skill needs more events.</p><div class="table-scroll"><table><thead><tr><th>Lead</th><th>Verified predictions</th><th>MAE (ft)</th><th>High-water predictions</th></tr></thead><tbody>{rows}</tbody></table></div><a href="models/live_verification.json">Download prospective scores</a></details></section>'''

def reporting():
    return '''<section class="resident-card"><h2>Report observed flooding for review</h2><p>Prepare a report below, then submit it through the maintainer's <a href="https://github.com/flatfoot584/mathews-flood-monitor/issues/new">GitHub issue review queue</a> (account required). This page creates a draft on your device; it does not send or upload anything. Reports are unverified until reviewed and never enter training automatically.</p>
<form id="report-form"><label>Street or public landmark<input name="location" required maxlength="120" placeholder="For example, Daniel Ave at Julian St"></label><label>Observation date and time (Eastern)<input name="time" type="datetime-local" required></label><label>Measured depth in inches, if known<input name="depth" type="number" min="0" max="120" step="0.25"></label><label>What did you observe?<textarea name="notes" required maxlength="2000" rows="3"></textarea></label><label class="consent"><input type="checkbox" required> I consent to maintainer review and understand that submitted issue text is public. I will omit private addresses and identifying details. If I attach a photo in the issue, I have permission to share it and will remove faces and license plates.</label><button class="resident-button" type="submit">Prepare report draft</button></form>
<div id="report-result" hidden><p><strong>Draft ready, not submitted.</strong> Review it before copying it into a GitHub issue. Avoid approaching floodwater to collect a measurement.</p><pre id="report-draft"></pre><button id="download-report" class="resident-button" type="button">Download draft</button><a href="https://github.com/flatfoot584/mathews-flood-monitor/issues/new">Open review queue</a></div></section>'''
