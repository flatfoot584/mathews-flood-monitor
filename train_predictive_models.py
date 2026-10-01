#!/usr/bin/env python3
"""
train_predictive_models.py — Machine Learning Training & Evaluation Pipeline
for Mathews County, Virginia Coastal Flood Prediction.

Implements the two-stage predictive architecture:
Stage 1: Predict Ware River water level (MLLW ft) from astronomical tides, wind stress, surge, and pressure.
         - Nowcasting Model (0-6 hr): Uses upstream surge + live winds + tides.
         - Forward Forecasting Model (6-48 hr): Uses forecast tides + forecast winds + pressure.
Stage 2: Predict hyper-local flood depth (inches) and inundation duration from Ware River stage.

Saves:
- models/model_weights_and_thresholds.json (lightweight, zero-dependency deployment config)
- models/stage1_lgbm_model.pkl (full LightGBM model)
- models/evaluation_report.json (detailed validation metrics and storm case studies)

Author: Antigravity Assistant for Mathews County Flood Prediction Project
"""

import os
import json
import math
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from lightgbm import LGBMRegressor

# Physical parameters & thresholds
FLOOD_STAGE_THRESHOLD = 3.99  # ft
DATUM_OFFSET_NAVD88 = -1.64

def engineer_features(df):
    """Derive physical coastal hydrodynamic features from raw hourly time series."""
    df = df.copy()
    df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
    df = df.sort_values('timestamp_utc').reset_index(drop=True)

    # 1. Quadratic wind stress (tau ~ |U| * U)
    df['along_bay_stress'] = np.sign(df['along_bay_wind_mph']) * (df['along_bay_wind_mph'] ** 2)
    df['cross_bay_stress'] = np.sign(df['cross_bay_wind_mph']) * (df['cross_bay_wind_mph'] ** 2)

    # 2. Multi-scale rolling wind set-up memory
    for w in [3, 6, 12, 24]:
        df[f'along_bay_{w}h'] = df['along_bay_wind_mph'].rolling(w, min_periods=1).mean()
        df[f'cross_bay_{w}h'] = df['cross_bay_wind_mph'].rolling(w, min_periods=1).mean()
        df[f'wind_speed_{w}h'] = df['yorktown_wind_speed_mph'].rolling(w, min_periods=1).mean()

    df['along_bay_stress_6h'] = df['along_bay_stress'].rolling(6, min_periods=1).mean()
    df['along_bay_stress_12h'] = df['along_bay_stress'].rolling(12, min_periods=1).mean()

    # 3. Barometric pressure changes (inverse barometer effect)
    df['baro_diff_3h'] = df['yorktown_baro_mb'] - df['yorktown_baro_mb'].shift(3)
    df['baro_diff_6h'] = df['yorktown_baro_mb'] - df['yorktown_baro_mb'].shift(6)
    df['baro_diff_12h'] = df['yorktown_baro_mb'] - df['yorktown_baro_mb'].shift(12)

    # 4. Tidal derivatives (rates of rise/fall)
    df['yt_tide_diff_1h'] = df['yorktown_pred_tide_ft'] - df['yorktown_pred_tide_ft'].shift(1)
    df['yt_tide_diff_2h'] = df['yorktown_pred_tide_ft'] - df['yorktown_pred_tide_ft'].shift(2)
    df['wm_tide_diff_1h'] = df['windmill_pred_tide_ft'] - df['windmill_pred_tide_ft'].shift(1)

    # 5. Upstream surge dynamics (Windmill Point)
    df['surge_lag_1h'] = df['windmill_surge_ft'].shift(1)
    df['surge_lag_3h'] = df['windmill_surge_ft'].shift(3)
    df['surge_lag_6h'] = df['windmill_surge_ft'].shift(6)
    df['surge_diff_3h'] = df['windmill_surge_ft'] - df['windmill_surge_ft'].shift(3)

    # 6. Cyclical temporal features
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)

    return df

def evaluate_predictions(y_true, y_pred, label=""):
    """Calculate core performance metrics."""
    r2 = r2_score(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae = mean_absolute_error(y_true, y_pred)
    
    # High water subset (>= 4.0 ft Action Stage)
    mask_high = y_true >= 4.0
    if mask_high.sum() > 0:
        high_rmse = np.sqrt(mean_squared_error(y_true[mask_high], y_pred[mask_high]))
        high_mae = mean_absolute_error(y_true[mask_high], y_pred[mask_high])
    else:
        high_rmse, high_mae = 0.0, 0.0

    return {
        "label": label,
        "n_samples": int(len(y_true)),
        "r2": round(float(r2), 4),
        "rmse_ft": round(float(rmse), 4),
        "mae_ft": round(float(mae), 4),
        "rmse_in": round(float(rmse * 12.0), 2),
        "mae_in": round(float(mae * 12.0), 2),
        "high_water_n": int(mask_high.sum()),
        "high_water_rmse_ft": round(float(high_rmse), 4),
        "high_water_mae_ft": round(float(high_mae), 4),
        "high_water_mae_in": round(float(high_mae * 12.0), 2)
    }

def main():
    os.makedirs("models", exist_ok=True)
    print("=" * 70)
    print("MATHEWS COUNTY FLOOD PREDICTION MODEL TRAINING PIPELINE")
    print("=" * 70)

    # 1. Load data
    print("[1/5] Loading merged training dataset...")
    df_raw = pd.read_csv("merged_hourly_training_dataset.csv")
    print(f"      Loaded {len(df_raw)} raw hourly rows.")

    # 2. Feature engineering
    print("[2/5] Engineering physical hydrodynamic features...")
    df = engineer_features(df_raw)

    # 3. Define feature sets
    nowcast_features = [
        'yorktown_pred_tide_ft', 'yt_tide_diff_1h', 'yt_tide_diff_2h',
        'windmill_surge_ft', 'surge_lag_1h', 'surge_lag_3h', 'surge_diff_3h',
        'along_bay_wind_mph', 'along_bay_3h', 'along_bay_6h', 'along_bay_12h', 'along_bay_24h',
        'along_bay_stress', 'along_bay_stress_6h', 'along_bay_stress_12h',
        'cross_bay_wind_mph', 'cross_bay_6h', 'yorktown_wind_speed_mph',
        'yorktown_baro_mb', 'baro_diff_6h', 'baro_diff_12h',
        'hour_sin', 'hour_cos', 'month_sin', 'month_cos'
    ]

    forecast_features = [
        'yorktown_pred_tide_ft', 'yt_tide_diff_1h', 'yt_tide_diff_2h',
        'windmill_pred_tide_ft', 'wm_tide_diff_1h',
        'along_bay_wind_mph', 'along_bay_3h', 'along_bay_6h', 'along_bay_12h', 'along_bay_24h',
        'along_bay_stress', 'along_bay_stress_6h', 'along_bay_stress_12h',
        'cross_bay_wind_mph', 'cross_bay_6h', 'yorktown_wind_speed_mph',
        'yorktown_baro_mb', 'baro_diff_6h', 'baro_diff_12h',
        'hour_sin', 'hour_cos', 'month_sin', 'month_cos'
    ]

    target = 'ware_river_stage_mllw_ft'

    # Filter valid rows
    data_nowcast = df.dropna(subset=nowcast_features + [target]).copy()
    data_forecast = df.dropna(subset=forecast_features + [target]).copy()

    # Train / Test split: Train on 2021-2023, Test on 2024 holdout
    train_nc = data_nowcast[data_nowcast['timestamp_utc'] < '2024-01-01']
    test_nc = data_nowcast[data_nowcast['timestamp_utc'] >= '2024-01-01']

    train_fc = data_forecast[data_forecast['timestamp_utc'] < '2024-01-01']
    test_fc = data_forecast[data_forecast['timestamp_utc'] >= '2024-01-01']

    print(f"\n[3/5] Training Stage 1 Models:")
    print(f"      Nowcast Split  -> Train: {len(train_nc)} rows, Test: {len(test_nc)} rows (2024 holdout)")
    print(f"      Forecast Split -> Train: {len(train_fc)} rows, Test: {len(test_fc)} rows (2024 holdout)")

    # Model 1A: Nowcast Linear Baseline
    lr_nc = LinearRegression()
    lr_nc.fit(train_nc[nowcast_features], train_nc[target])
    pred_lr_nc = lr_nc.predict(test_nc[nowcast_features])
    res_lr_nc = evaluate_predictions(test_nc[target].values, pred_lr_nc, "Nowcast Linear Baseline")

    # Model 1B: Nowcast LightGBM
    lgb_nc = LGBMRegressor(n_estimators=250, learning_rate=0.04, num_leaves=31, random_state=42, verbose=-1)
    lgb_nc.fit(train_nc[nowcast_features], train_nc[target])
    pred_lgb_nc = lgb_nc.predict(test_nc[nowcast_features])
    res_lgb_nc = evaluate_predictions(test_nc[target].values, pred_lgb_nc, "Nowcast LightGBM")

    # Model 2A: Forward Forecast Linear Baseline
    lr_fc = LinearRegression()
    lr_fc.fit(train_fc[forecast_features], train_fc[target])
    pred_lr_fc = lr_fc.predict(test_fc[forecast_features])
    res_lr_fc = evaluate_predictions(test_fc[target].values, pred_lr_fc, "Forecast Linear Baseline")

    # Model 2B: Forward Forecast LightGBM
    lgb_fc = LGBMRegressor(n_estimators=300, learning_rate=0.03, num_leaves=31, random_state=42, verbose=-1)
    lgb_fc.fit(train_fc[forecast_features], train_fc[target])
    pred_lgb_fc = lgb_fc.predict(test_fc[forecast_features])
    res_lgb_fc = evaluate_predictions(test_fc[target].values, pred_lgb_fc, "Forecast LightGBM")

    # Display Stage 1 Results
    print("\nSTAGE 1 MODEL COMPARISON (2024 Holdout Test Set):")
    print(f"{'Model':<28} | {'R2':<6} | {'RMSE (ft)':<9} | {'MAE (ft)':<8} | {'MAE (in)':<8} | {'High-Water MAE':<14}")
    print("-" * 85)
    for r in [res_lr_nc, res_lgb_nc, res_lr_fc, res_lgb_fc]:
        print(f"{r['label']:<28} | {r['r2']:<6.4f} | {r['rmse_ft']:<9.3f} | {r['mae_ft']:<8.3f} | {r['mae_in']:<6.1f}\" | {r['high_water_mae_in']:<6.1f}\"")

    # 4. Stage 2: Local Flood Depth Modeling & Evaluation on Ground Truth
    print("\n[4/5] Training & Evaluating Stage 2 Local Inundation Model:")
    gt_df = pd.read_csv("ground_truth_observations.csv")
    gt_valid = gt_df[gt_df['ware_river_stage_ft'].notna() & gt_df['flood_depth_in'].notna()].copy()
    
    stages_gt = gt_valid['ware_river_stage_ft'].values
    actual_depths = gt_valid['flood_depth_in'].values
    
    # Piecewise empirical model
    pred_depths_emp = np.maximum(0.0, 10.95 * stages_gt - 43.69)
    r2_gt = r2_score(actual_depths, pred_depths_emp)
    mae_gt = mean_absolute_error(actual_depths, pred_depths_emp)
    rmse_gt = np.sqrt(mean_squared_error(actual_depths, pred_depths_emp))
    
    print(f"      Evaluated on {len(gt_valid)} ground-truth observations.")
    print(f"      Stage 2 Inundation Model -> R2 = {r2_gt:.4f}, MAE = {mae_gt:.2f}\", RMSE = {rmse_gt:.2f}\"")

    # 5. Historical Storm Case Studies
    print("\n[5/5] Backtesting on Major Storm Events in 2024 Test Set:")
    
    # Case 1: Hurricane Helene (Sep 26-28, 2024) - In Holdout Test Set
    helene_mask = (test_nc['timestamp_utc'] >= pd.to_datetime('2024-09-26', utc=True)) & (test_nc['timestamp_utc'] <= pd.to_datetime('2024-09-28 23:59:59', utc=True))
    helene_data = test_nc[helene_mask]
    helene_obs_peak = helene_data[target].max()
    helene_lgb_peak = lgb_nc.predict(helene_data[nowcast_features]).max()
    helene_lr_peak = lr_nc.predict(helene_data[nowcast_features]).max()
    
    print(f"      Hurricane Helene (Sep 27, 2024) [Test Set]:")
    print(f"        Observed Peak Stage : {helene_obs_peak:.2f} ft (Ground Truth: 9.75\" flood)")
    print(f"        Nowcast LGB Peak    : {helene_lgb_peak:.2f} ft (Error: {abs(helene_lgb_peak - helene_obs_peak):.2f} ft / {abs(helene_lgb_peak - helene_obs_peak)*12:.1f}\")")
    print(f"        Nowcast Linear Peak : {helene_lr_peak:.2f} ft (Error: {abs(helene_lr_peak - helene_obs_peak):.2f} ft / {abs(helene_lr_peak - helene_obs_peak)*12:.1f}\")")

    # Case 2: September King Tide (Sep 21-23, 2024) - In Holdout Test Set
    king_mask = (test_nc['timestamp_utc'] >= pd.to_datetime('2024-09-21', utc=True)) & (test_nc['timestamp_utc'] <= pd.to_datetime('2024-09-23 23:59:59', utc=True))
    king_data = test_nc[king_mask]
    king_obs_peak = king_data[target].max()
    king_lgb_peak = lgb_nc.predict(king_data[nowcast_features]).max()
    king_lr_peak = lr_nc.predict(king_data[nowcast_features]).max()

    print(f"      September King Tide (Sep 22, 2024) [Test Set]:")
    print(f"        Observed Peak Stage : {king_obs_peak:.2f} ft (Ground Truth: 14.5\" flood)")
    print(f"        Nowcast LGB Peak    : {king_lgb_peak:.2f} ft (Error: {abs(king_lgb_peak - king_obs_peak):.2f} ft / {abs(king_lgb_peak - king_obs_peak)*12:.1f}\")")
    print(f"        Nowcast Linear Peak : {king_lr_peak:.2f} ft (Error: {abs(king_lr_peak - king_obs_peak):.2f} ft / {abs(king_lr_peak - king_obs_peak)*12:.1f}\")")

    # Case 3: TS Ophelia (Sep 22-24, 2023)
    oph_mask = (train_nc['timestamp_utc'] >= pd.to_datetime('2023-09-22', utc=True)) & (train_nc['timestamp_utc'] <= pd.to_datetime('2023-09-24 23:59:59', utc=True))
    oph_data = train_nc[oph_mask]
    oph_obs_peak = oph_data[target].max()
    oph_lgb_peak = lgb_nc.predict(oph_data[nowcast_features]).max()
    print(f"      TS Ophelia (Sep 22-23, 2023):")
    print(f"        Observed Peak Stage : {oph_obs_peak:.2f} ft (Ground Truth: 12.0\" flood)")
    print(f"        Nowcast LGB Peak    : {oph_lgb_peak:.2f} ft (Error: {abs(oph_lgb_peak - oph_obs_peak):.2f} ft / {abs(oph_lgb_peak - oph_obs_peak)*12:.1f}\")")

    # Save lightweight JSON model configuration
    model_config = {
        "model_metadata": {
            "trained_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "training_period": "2021-01-01 to 2023-12-31",
            "test_period": "2024-01-01 to 2024-09-30 (holdout)",
            "training_samples": len(train_nc),
            "test_samples": len(test_nc)
        },
        "stage1_nowcast_linear": {
            "intercept": float(lr_nc.intercept_),
            "coefficients": {feat: float(coef) for feat, coef in zip(nowcast_features, lr_nc.coef_)},
            "test_r2": res_lr_nc['r2'],
            "test_mae_ft": res_lr_nc['mae_ft'],
            "test_mae_in": res_lr_nc['mae_in']
        },
        "stage1_forecast_linear": {
            "intercept": float(lr_fc.intercept_),
            "coefficients": {feat: float(coef) for feat, coef in zip(forecast_features, lr_fc.coef_)},
            "test_r2": res_lr_fc['r2'],
            "test_mae_ft": res_lr_fc['mae_ft']
        },
        "stage2_inundation_model": {
            "flood_stage_threshold_ft": FLOOD_STAGE_THRESHOLD,
            "slope_in_per_ft": 10.95,
            "intercept_in": -43.69,
            "formula": "flood_depth_in = max(0.0, 10.95 * stage_ft - 43.69)",
            "ground_truth_r2": round(float(r2_gt), 4),
            "ground_truth_mae_in": round(float(mae_gt), 2)
        },
        "risk_severity_tiers": {
            "Tier 0": {"range_ft": "< 4.0 ft", "depth_range_in": "0\"", "desc": "Normal / Safe"},
            "Tier 1": {"range_ft": "4.0 - 4.3 ft", "depth_range_in": "1\" - 4\"", "desc": "Nuisance / Ditch Full"},
            "Tier 2": {"range_ft": "4.4 - 4.7 ft", "depth_range_in": "5\" - 8\"", "desc": "Moderate Inundation (Driveway / Road blocked)"},
            "Tier 3": {"range_ft": ">= 4.8 ft", "depth_range_in": "9\" - 15\"+", "desc": "Severe Inundation (Impassable)"}
        }
    }

    with open("models/model_weights_and_thresholds.json", "w", encoding="utf-8") as f:
        json.dump(model_config, f, indent=2)
    print("\n[*] Saved lightweight deployable config: models/model_weights_and_thresholds.json")

    # Save pickled LGBM models
    with open("models/stage1_nowcast_lgbm.pkl", "wb") as f:
        pickle.dump(lgb_nc, f)
    with open("models/stage1_forecast_lgbm.pkl", "wb") as f:
        pickle.dump(lgb_fc, f)
    print("[*] Saved full LightGBM models: models/stage1_nowcast_lgbm.pkl & stage1_forecast_lgbm.pkl")

    # Save detailed evaluation report
    eval_report = {
        "evaluation_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "metrics": {
            "nowcast_linear": res_lr_nc,
            "nowcast_lgbm": res_lgb_nc,
            "forecast_linear": res_lr_fc,
            "forecast_lgbm": res_lgb_fc,
            "stage2_ground_truth": {
                "n_observations": len(gt_valid),
                "r2": round(float(r2_gt), 4),
                "mae_inches": round(float(mae_gt), 2),
                "rmse_inches": round(float(rmse_gt), 2)
            }
        },
        "storm_case_studies": {
            "hurricane_helene": {
                "observed_peak_stage_ft": float(helene_obs_peak),
                "observed_flood_depth_in": 9.75,
                "nowcast_lgbm_predicted_stage_ft": round(float(helene_lgb_peak), 2),
                "nowcast_linear_predicted_stage_ft": round(float(helene_lr_peak), 2),
                "predicted_flood_depth_in": round(float(max(0.0, 10.95 * helene_lgb_peak - 43.69)), 2)
            },
            "september_king_tide": {
                "observed_peak_stage_ft": float(king_obs_peak),
                "observed_flood_depth_in": 14.5,
                "nowcast_lgbm_predicted_stage_ft": round(float(king_lgb_peak), 2),
                "nowcast_linear_predicted_stage_ft": round(float(king_lr_peak), 2),
                "predicted_flood_depth_in": round(float(max(0.0, 10.95 * king_lgb_peak - 43.69)), 2)
            }
        }
    }

    with open("models/evaluation_report.json", "w", encoding="utf-8") as f:
        json.dump(eval_report, f, indent=2)
    print("[*] Saved full evaluation report: models/evaluation_report.json")
    print("=" * 70)

if __name__ == "__main__":
    main()
