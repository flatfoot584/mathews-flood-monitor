# Fort Monroe causal forecasting experiment

Completed October 4, 2026. Fort Monroe FTMV2 / USGS 0204289994, parameter 62620 (NAVD88 feet), is a newly collected optional evaluation sensor.

The 2024 holdout compares paired complete-case rows against a Ridge baseline containing Ware River history, Windmill surge, Yorktown weather and known tide, Sewells Point water levels, and known calendar/tidal phase features. Train 2021–22, validation 2023, test 2024, 48-hour split gaps, fixed Ridge alpha 10 and a one-hour simulated observation latency. No future observed weather is supplied.

| Lead (hours) | Baseline MAE (ft) | With Fort Monroe MAE (ft) | Improvement |
| --- | --- | --- | --- |
| 1 | 0.1262 | 0.1002 | 20.65% |
| 3 | 0.1647 | 0.1568 | 4.81% |
| 6 | 0.1856 | 0.1817 | 2.08% |
| 12 | 0.2181 | 0.2145 | 1.62% |
| 24 | 0.2956 | 0.2927 | 0.96% |
| 48 | 0.4366 | 0.4347 | 0.43% |

Fort Monroe supplies a useful historical short-lead signal, especially at one hour. It does not meet the predeclared 5% improvement gate across 1, 3 and 6 hours. More importantly, this is not a comparison against historical issued NWPS forecasts, which were not archived in the previous system. The current operational forecast remains unchanged; no claim of live forecast improvement is supported. No production retraining or model replacement was performed.

The live collector now records Fort Monroe hourly elevations and source timestamps, using the station-specific conversion NAVD88 = NWPS MLLW minus 1.70 ft. A coincident USGS value of 0.13 ft NAVD88 matched NWPS 1.83 ft MLLW, verifying the difference on October 4. Ware River's 1.64 ft offset is kept separate. Fort Monroe failure is optional and cannot disable existing alerts or guidance.

Six nominal lead bins per issue, exact issue/valid/lead times, unadjusted NWPS stage, the Fort Monroe reading available at issue, and subsequent Ware observations are now archived. A public prospective scorecard starts with zero verified forecasts instead of invented scores. Repeated issues are correlated; depth errors are derived from the existing equation and not independent field verification.

The JSON report includes sample sizes, high-water errors, threshold misses/false alarms, storm-window peak errors, limits, software versions, and data checksums. The cached USGS response and private analysis dataset remain local. Original observer records were not altered or republished. A first exploratory comparator omitted Sewells; only the final comparator including Sewells is reported here. A timestamp-resolution compatibility error was corrected before accepting the results.

Next experiment: build a causal short-lead candidate in shadow mode and compare paired prospective results against the actual deployed NWPS-based calculation, with storm-block uncertainty, threshold/onset/crest/duration errors and outage analysis. Promote only after useful gains repeat and high-water errors/misses do not worsen.
