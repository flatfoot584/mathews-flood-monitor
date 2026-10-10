# models/ — artifact provenance

This directory holds model artifacts and evaluation outputs for the Mathews County
flood monitor. Provenance matters: an unversioned model file is a reproducibility
trap. This file records what each artifact is and whether anything still uses it.

## Live / in use

| File | Status | Notes |
|---|---|---|
| `model_weights_and_thresholds.json` | **Live** | Thresholds and weights consumed by the pipeline. Versioned in git; changes are reviewed. |
| `scientific_evidence.json` | **Live** | Evidence summary rendered on science.html. |
| `live_verification.json` | **Live, regenerated** | Rewritten by every `ingest_realtime.py` run via `forecast_verification.archive_and_verify`. Do not hand-edit; it is a pipeline output. |
| `fort_monroe_evaluation.json` | **Live, evaluation only** | Fort Monroe is an evaluation sensor, not an operational input. |
| `evaluation_report.json` | Reference | Historical evaluation snapshot. |

## Archived / unused

| File | Status | Notes |
|---|---|---|
| `stage1_forecast_lgbm.pkl` | **Unused legacy** | No code in this repo loads it (verified 2026-10-10). |
| `stage1_forecast_q10_lgbm.pkl` | **Unused legacy** | No code in this repo loads it. |
| `stage1_forecast_q90_lgbm.pkl` | **Unused legacy** | No code in this repo loads it. |
| `stage1_nowcast_lgbm.pkl` | **Unused legacy** | No code in this repo loads it. |

The `stage1_*.pkl` files are LightGBM binaries from an earlier modeling stage. They have
no recorded training configuration, training data snapshot, or version — they cannot be
reproduced or safely promoted. They are kept only as historical reference. If a model is
ever promoted to operational use, it must be re-trained through a versioned pipeline with
its config, data hash, and metrics recorded alongside the artifact (see
`forecast_verification.py` for the prospective-verification pattern to follow).
