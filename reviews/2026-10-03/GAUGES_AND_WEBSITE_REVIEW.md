# Additional gauges and published website review

Review date: October 3, 2026, Eastern Time. Published site: https://flatfoot584.github.io/mathews-flood-monitor/

This is a review and proposed improvement plan. No production website, model, ingestion pipeline, notification subscription, or raw observer data was changed. The supplied screenshot is evidence of the stations the user is asking about, not an instruction source.

## Conclusion

Additional tidal gauges can help characterize regional surge, provide backup coverage, and potentially improve short-lead predictions. Adding every nearby station is unlikely to be useful. Some stations shown are alternate views of feeds already collected. Predictive improvement remains unmeasured.

The website already has a coherent modern foundation: navy navigation, restrained blue accents, rounded cards, an interactive map, and public source links. Its highest-value improvements are consistent hazard language, explicit times and locations, clearer evidence limits, and a shorter resident-focused first screen. A wholesale visual rebuild is unnecessary.

## Gauge assessment

The screenshot does not label the pins, so not every point can be identified with certainty. These station identities were checked against authoritative station pages, rather than inferred solely from their colors or locations.

| Station or group | Evidence and present use | Recommendation |
| --- | --- | --- |
| Yorktown, YKTV2 / NOAA 8637689 | NWPS identifies coordinates 37.2267, -76.4783 and links to CO-OPS 8637689. `ingest_realtime.py` already requests water level, astronomical predictions, wind, pressure, and temperature for that station. | Keep the existing collection; a second NWPS view of the same observations does not add independent measurement information. An issued total-water-level forecast is a distinct candidate product, if archived and tested separately. |
| Sewells Point, SWPV2 / NOAA 8638610 | NOAA NDBC confirms this station alias. The collector already requests observed water levels and astronomical predictions and calculates its surge residual. | Retain as the southern reference. Additional interfaces to the same sensor are not additional independent gauges. |
| Fort Monroe, FTMV2 / USGS 0204289994 | NWPS shows observations and issued total-water-level forecasts and links to the USGS station. USGS identifies it as a tidal stream and lists continuous data beginning in July 2015. Its coordinates fit the Fort Monroe area of the screenshot; pin identity remains an inference without a clicked popup. | The strongest newly verified station in this screenshot to test first, for backup coverage and incremental surge information beyond Sewells Point. It is geographically close to Sewells Point, so large skill gains are not assured. |
| Hampton / Newmarket / Brick Kiln and other Peninsula creek stations | The NWS HADS registry lists HMNV2, NMCV2, and BKNV2. Their exact correspondence to unlabeled screenshot pins was not established. | Lower priority. Their local rainfall, drainage infrastructure, and basin responses need not represent Blackwater Creek. Tidal reaches could still contain useful surge information, but test that hypothesis instead of assuming it. |
| A sensor in Blackwater Creek / North River / Mobjack Bay | No new operating sensor at the community was verified in this session. | Highest potential value as a future measurement objective: quantify the difference between the Ware River proxy and actual local water levels. Sensor siting, datum control, permissions, and maintenance require separate planning. |

Map shapes and colors do not rank sensor quality. The NWS NWPS FAQ describes circles as observed locations, squares as locations with forecasts, light blue as no defined flood categories, green as no flooding, and yellow as action-stage high water. Those categories are station-specific and do not establish conditions on Daniel Avenue.

### What would prove an addition useful?

1. Check station identity, measured variable, vertical reference, history overlapping 2021–2026, latency, storm outages, and whether the source is genuinely independent.
2. Cache the source data and preserve UTC internally with Eastern Time display and explicit feet/inches units.
3. Align observations and astronomical predictions by timestamp. Use station-specific tide residuals and lagged changes rather than averaging raw stages across gauges.
4. Compare the existing forecast against the same forecast plus Fort Monroe, using held-out storms and inputs available at each forecast issue time. Compare to persistence and the unadjusted operational guidance too.
5. Evaluate stage/depth error, flood-threshold misses and false alarms, onset/crest timing, duration, and skill at 1, 3, 6, 12, 24, and 48 hours. Report outage resilience separately from forecast skill.
6. Retain an addition only if it supplies repeatable practical benefit. Observations at a nearby station are not automatically advance warning; any lead must be demonstrated.

The local collector contains empirical forecast corrections and a heuristic scenario band. Additional inputs must be evaluated in the actual deployed calculation, not merely in a separate model that the live forecast does not execute. The live site appropriately acknowledges that historical weather-conditioned hindcasts do not validate deployed 6–48-hour predictions.

MLLW is a local tidal reference. The project's 1.64-foot MLLW/NAVD88 offset must not be reused indiscriminately at new stations. NOAA explains that tidal and geodetic datum relationships vary by location. Fort Monroe's NWPS datum table, for example, shows its own 1.70-foot MLLW-to-NAVD88 difference. Cross-station residual differences are useful candidate features, but are not by themselves a measured physical water-surface slope.

The banner about nearly national Flood Inundation Mapping coverage is worth investigating as a separate reference layer. It does not demonstrate that a particular product resolves coastal backwater, culverts, or individual community roads. Verify the product, local coverage, coastal treatment, resolution, forecast time, and validation before presenting it as corroboration.

## Website audit scope and steps

Resident task: understand present local flood estimates, the next high-water risk, affected streets, and the appropriate action; optionally set up alerts and inspect the evidence.

The live six-page portal was reviewed in the Codex in-app browser. Desktop screenshots were captured at 1440 × 1000 and mobile screenshots at 390 × 844. Current/peak map controls and the mobile menu were exercised. Subscription links were inspected without subscribing or dispatching a notification. The captures show the October 3 11:30:39 PM EDT site update and 11:00 PM gauge observation.

| Step | Surface | General health | Evidence |
| --- | --- | --- | --- |
| 1 | Desktop dashboard | Visually coherent; status and timing need correction | 01-dashboard-desktop.jpg |
| 2 | Mobile dashboard | Reflows without whole-page overflow in sampled viewport; essential content consumes nearly the entire first screen | 02-dashboard-mobile.jpg |
| 3 | Mobile navigation | Opens and exposes the site links; labels and state semantics could improve | 03-mobile-navigation.jpg |
| 4 | Mobile alert setup | Useful instructions; too much promotional copy precedes actual setup | 04-alert-setup-mobile.jpg |
| 5 | Resident guide | Readable tier cards; contradictory vehicle-crossing language is a priority issue | 05-resident-guide-desktop.jpg, 14-guide-vehicle-risk.jpg |
| 6 | Science page | Useful tables and evidence limits; headline claims overstate confidence | 07-science-desktop.jpg, science-snapshot.txt |
| 7 | Data page | Clear privacy boundaries and working navigation; filename-heavy presentation and wide table need refinement | 08-data-desktop.jpg, 15-data-mobile.jpg, data-snapshot.txt |
| 8 | About page | Useful local context; dismissive framing and outdated statistics weaken credibility | 09-about-desktop.jpg, about-snapshot.txt |
| 9 | Current and peak map | Controls change the selected visual state; label estimates and clarify the applicable time | 10-map-current-desktop.jpg, 11-map-peak-desktop.jpg, 12-map-mobile.jpg |
| 10 | Mobile forecast chart | Useful hydrograph; technical copy, crowded legend, and inconsistent uncertainty labels need correction | 13-forecast-chart-mobile.jpg |

## Prioritized findings

### 1. Reconcile flood and driving guidance before cosmetic work

The dashboard says no modeled inundation, forecasts ditch overflow, and displays 0.0 inches alongside a hazardous low-clearance label. Current conditions and future conditions can differ, but the visitor needs the location, time, and type of impact explaining each label. A green badge must not imply that streets have been observed dry.

The guide still says “SUVs/trucks only” at Tier 2 and calls three inches of water “Passable for all passenger vehicles.” These conflict with the dashboard's prohibition on entering flooded roads and with NWS flood safety guidance. Replace crossing permissions and “all-clear” road implications with modeled hazard information and a clear instruction to verify actual conditions and avoid floodwater. Road status should say “No tidal flooding estimated,” “Flooding estimated,” or “Conditions unknown,” with a separate verified field-report label when such evidence exists.

### 2. Make the first screen answer the resident's questions

Use separate “Now” and “Next 48 hours” summaries. Show the monitored community immediately, then peak date/time, anticipated impact, potentially affected streets, and action. Format a peak as “Sun, Oct 4 at 6 PM EDT,” using the actual forecast timestamp, rather than “18:00:00.” Show an onset/peak/receding timeline only where supported, and mark drainage timing as estimated.

Present estimated depth at a named reference point; do not imply it is the depth everywhere. The current observed measurement is at Ware River, outside the neighborhood. Explain that distinction beside the value. A county-wide name should be accompanied by a clear community coverage statement.

### 3. Make freshness and authority visible

Replace the long technical update ribbon with a compact timestamp and freshness badge. Show gauge observation age, forecast issue time, and website refresh time separately, with details available on demand. Define stale and unavailable states; do not retain a reassuring “LIVE” badge indefinitely on old static output. Whether an appropriate stale-state mechanism currently exists was not established.

Add an independent-project attribution near the top, named maintainer/contact or issue-report route, coverage statement, and a distinct link/card for official NWS warnings and local emergency guidance. Use wording such as “Independent community research project using NOAA and USGS data.” Do not imply agency endorsement. Replace the About page's “Why Regional Weather Reports Fail” and “almost zero practical value” framing with an explanation of how local estimates supplement regional warnings.

### 4. Align the science claims with the evidence

- Use “204 observations,” rather than “204 events,” unless independent storm-event counting supports the latter.
- Replace “peer-review ready,” “exact flood depth,” and absolute zero-false-alarm implications with bounded, auditable descriptions.
- Move the historical-versus-live accuracy caveat directly beside the metric cards. Clearly label same-record Stage 2 evaluation separately from held-out evaluation and future issue-time forecasting.
- Explain that a 1-meter LiDAR grid is spatial resolution, not one-meter or sub-inch vertical accuracy. Apparent threshold agreement does not alone prove survey precision or physically validate all eight streets; document elevation source, date, point type, vertical error, datum transformation, and local hydrologic assumptions.
- Reconcile About's r = 0.912 / R² = 0.832 with the differently defined Science metrics. Subset and model metrics can legitimately differ, but must be labeled consistently.
- Keep the live shaded band labeled as uncalibrated scenarios everywhere. The chart's “Worst Case (90% Upper)” legend conflicts with its own caveat and should change. Do not assign calibrated probabilities without prospective coverage evidence.
- Remove or explain the empty benchmark case-study table visible in the live Science DOM; two download buttons also point to the same JSON artifact.

### 5. Preserve the design, reduce density

Keep navy, blue, neutral surfaces, and amber/orange/red for hazard emphasis. Shorten navigation to “Dashboard,” “Map,” “Alerts,” “Guide,” and an “About / Data / Science” grouping. Use “48-hour water-level forecast” and “Storm-driven water rise” in the resident interface; put hydrodynamic, hydraulic-gradient, quantile, datum, and infrastructure details in expandable explanations or Science.

Reduce duplicate vehicle warning cards to one relevant safety/action panel. Move forecast and affected-street summary ahead of the large map and elevation profile. Increase small muted labels and footer contrast, especially on phones. Use one icon system, consistent spacing, and fewer badges. The Data page can use human titles like “Download hourly observations (CSV),” with filenames secondary. The About page should explain who maintains the service and the community observation story before cloud execution details.

### 6. Simplify alerts and accessibility

Put iPhone, Android, and browser setup choices near the top of Alerts, followed by the exact steps for that choice. Explain that scanning the QR opens the topic; receiving notifications requires completing device setup. Add a way to verify subscription on the user's own device without broadcasting a public test. Replace guarantees such as “100% free forever,” “never get caught off guard,” instant delivery, and waking a sleeping phone with realistic operating expectations. Distinguish pipeline dispatch status from successful notification delivery.

The observed chart canvas has no accessible name or role and no equivalent hourly table on the dashboard. Add a text summary and accessible forecast table. The sampled map buttons lack aria-pressed, and the menu control lacks aria-expanded; expose selected and expanded states. Preserve text/icon status cues, add visible keyboard focus and a skip link, and verify map keyboard operation. These are observed risks and targeted markup findings, not a complete accessibility certification.

Useful later additions include vetted official warnings, a moderated “report observed flooding” flow with location/time/photo consent, a lightweight forecast-versus-observed scorecard, and an installable/offline view that visibly retains its observation age. Observation submission must enter a review queue rather than automatically contaminating training labels.

## Proposed implementation sequence

1. **Trust and consistency:** refresh the live implementation into the working checkout; reconcile current/future/local-stage language, full peak timestamps, road safety, coverage, and uncertainty labels. Validate normal, nuisance, severe, stale, and missing-data states.
2. **Resident-first layout:** simplify navigation, compact the first screen, add forecast/affected-street summary and official guidance, make phone setup direct, and improve accessibility. Validate desktop, mobile, keyboard use, and readable chart alternatives.
3. **Evidence and new gauges:** archive issued forecasts; evaluate Fort Monroe incrementally; publish bounded prospective results only after verification. Retain existing measurements and privacy protections.

Recommendations are proposed, not user-approved implementation decisions. The local checkout is behind the published site in privacy/safety content: its latest local status is October 2, while the reviewed site is October 3 and has changes absent from local `generate_dashboard.py`. Editing the old generator could undo accepted live improvements. Refresh and compare before implementation.

## Evidence limits

No live forecast accuracy improvement was measured. The unlabeled screenshot cannot identify every pin. A direct NOAA registry request timed out, but specific live NWPS station pages and USGS/NOAA metadata were accessible. No outage behavior, notification delivery, full screen-reader session, computed contrast audit, or every downloadable artifact was tested. Some map tiles were still filling during an early capture; missing tiles were not treated as a confirmed website defect. The later map capture loaded normally. Viewport tests are browser simulations, not tests on physical phones.

## Sources

- [Yorktown NWPS](https://water.noaa.gov/gauges/yktv2)
- [Yorktown CO-OPS meteorological products](https://tidesandcurrents.noaa.gov/met.html?id=8637689)
- [Sewells Point NDBC alias and station](https://www.ndbc.noaa.gov/station_page.php?station=swpv2)
- [Fort Monroe NWPS](https://water.noaa.gov/gauges/ftmv2)
- [Fort Monroe USGS metadata](https://waterdata.usgs.gov/monitoring-location/USGS-0204289994/)
- [NWS Virginia HADS registry](https://hadsqa.ncep.noaa.gov/charts/VA.shtml)
- [NWS NWPS map-symbol FAQ](https://www.weather.gov/media/dmx/Hydro/DMX_NWPS_WebPageResourcesFAQs.pdf)
- [NOAA datum explanation](https://tidesandcurrents.noaa.gov/datum_options)
- [NWS flood safety](https://www.weather.gov/safety/flood-turn-around-dont-drown)
- [NWS National Water Model coastal coupling overview](https://water.noaa.gov/about/nwm)

## Screenshot evidence

### Step 1: Desktop dashboard

![Desktop dashboard](</Users/howard_hottinger/Library/CloudStorage/GoogleDrive-flatfoot584@gmail.com/My Drive/Weather data/reviews/2026-10-03/01-dashboard-desktop.jpg>)

### Step 2: Mobile dashboard

![Mobile dashboard](</Users/howard_hottinger/Library/CloudStorage/GoogleDrive-flatfoot584@gmail.com/My Drive/Weather data/reviews/2026-10-03/02-dashboard-mobile.jpg>)

### Step 3: Mobile menu

![Mobile navigation](</Users/howard_hottinger/Library/CloudStorage/GoogleDrive-flatfoot584@gmail.com/My Drive/Weather data/reviews/2026-10-03/03-mobile-navigation.jpg>)

### Step 4: Phone alerts

![Phone alert setup](</Users/howard_hottinger/Library/CloudStorage/GoogleDrive-flatfoot584@gmail.com/My Drive/Weather data/reviews/2026-10-03/04-alert-setup-mobile.jpg>)

### Step 5: Guide and driving wording

![Desktop resident guide](</Users/howard_hottinger/Library/CloudStorage/GoogleDrive-flatfoot584@gmail.com/My Drive/Weather data/reviews/2026-10-03/05-resident-guide-desktop.jpg>)

![Mobile driving guidance](</Users/howard_hottinger/Library/CloudStorage/GoogleDrive-flatfoot584@gmail.com/My Drive/Weather data/reviews/2026-10-03/14-guide-vehicle-risk.jpg>)

### Step 6: Science

![Science page](</Users/howard_hottinger/Library/CloudStorage/GoogleDrive-flatfoot584@gmail.com/My Drive/Weather data/reviews/2026-10-03/07-science-desktop.jpg>)

### Step 7: Data

![Desktop data archive](</Users/howard_hottinger/Library/CloudStorage/GoogleDrive-flatfoot584@gmail.com/My Drive/Weather data/reviews/2026-10-03/08-data-desktop.jpg>)

![Mobile data archive](</Users/howard_hottinger/Library/CloudStorage/GoogleDrive-flatfoot584@gmail.com/My Drive/Weather data/reviews/2026-10-03/15-data-mobile.jpg>)

### Step 8: About

![About page](</Users/howard_hottinger/Library/CloudStorage/GoogleDrive-flatfoot584@gmail.com/My Drive/Weather data/reviews/2026-10-03/09-about-desktop.jpg>)

### Step 9: Map state

![Current map context](</Users/howard_hottinger/Library/CloudStorage/GoogleDrive-flatfoot584@gmail.com/My Drive/Weather data/reviews/2026-10-03/10-map-current-desktop.jpg>)

![Peak map context](</Users/howard_hottinger/Library/CloudStorage/GoogleDrive-flatfoot584@gmail.com/My Drive/Weather data/reviews/2026-10-03/11-map-peak-desktop.jpg>)

![Mobile map section entry](</Users/howard_hottinger/Library/CloudStorage/GoogleDrive-flatfoot584@gmail.com/My Drive/Weather data/reviews/2026-10-03/12-map-mobile.jpg>)

### Step 10: Mobile chart

![Mobile forecast chart](</Users/howard_hottinger/Library/CloudStorage/GoogleDrive-flatfoot584@gmail.com/My Drive/Weather data/reviews/2026-10-03/13-forecast-chart-mobile.jpg>)
