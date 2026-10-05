# Fort Monroe and resident portal release closeout

Published October 4, 2026. Implementation commit `70a72490718d8712507de6cf5194c1ce7459dfbe`; first production data update `cc4755f`.

Live site: https://flatfoot584.github.io/mathews-flood-monitor/
Successful production collection, alert evaluation and Pages deployment: https://github.com/flatfoot584/mathews-flood-monitor/actions/runs/37177030993

## Model decision

The final causal historical ablation includes the existing Sewells Point sensor. Train 2021–2022, validation 2023, test 2024, chronological gaps and only past observations plus known tides. Test MAE improvements: 1h 20.65%, 3h 4.81%, 6h 2.08%, 12h 1.62%, 24h 0.96%, 48h 0.43%. The predeclared multi-lead promotion gate failed. This is not a demonstrated improvement over actual historically issued operational NWPS guidance. Production formula and weights were retained.

Fort Monroe FTMV2 / USGS 0204289994 is now collected as an optional evaluation sensor. Its own MLLW-to-NAVD88 offset is 1.70 ft. Production reported 6,942 archived observations. Six issued forecast lead bins and subsequent Ware observations are archived for prospective scoring. No live accuracy score is claimed before verified pairs accumulate.

## Published user experience

Resident summaries, current versus future distinctions, full Eastern dates, affected streets, official NWS alerts and links, compact navigation, accessible hourly data and map states, qualified scientific and elevation claims, consistent road-safety wording, device-specific mobile alert setup, local observation drafts for manual review, and install/offline age warnings are published. Raw private observer records were preserved and excluded.

## Verification

- 48 regression tests passed locally and in production CI; separate regression workflow succeeded.
- All six pages inspected at desktop and 390px mobile widths; no horizontal overflow or JavaScript errors in the inspected views.
- Live desktop and mobile dashboard verified after deployment. Screenshots: `/tmp/mathews-flood-release-desktop.jpg` and `/tmp/mathews-flood-release-mobile.jpg`.
- Production mobile alerting remains enabled with `NTFY_ALERTS_ENABLED=true` and unconditional `check_alerts.py --ntfy`. The actual production check suppressed a duplicate alert for an already-notified crest. No public test push was sent, and physical phone reception was not verified.
- Physical iPhone installation and offline behavior were not verified; browser offline shell and stale-data guards were implemented and structurally checked.
- Howard HQ project, completed review task, experiment, next shadow-forecast task and session closeout were synchronized successfully.

Next action: build a causal short-lead shadow candidate and compare paired issued candidate/deployed predictions over independent storm windows. Retain production until practical high-water gains repeat.
