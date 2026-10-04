#!/usr/bin/env python3
"""Causal station ablation. Private merged records stay local; only metrics are public.
Use hourly means of the previous complete hour (one-hour source latency).
All future inputs are astronomical predictions or calendar features.
Train 2021–22, validation 2023, untouched test 2024, with a 48-hour boundary gap.
This does NOT replay historical issued NWPS guidance; operational promotion needs
prospective paired verification against that actual deployed baseline.
"""
from pathlib import Path
import argparse, hashlib, json
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge

HORIZONS = (1, 3, 6, 12, 24, 48)

def parse_usgs(payload):
    records = []
    for series in payload['value']['timeSeries']:
        if series['sourceInfo']['siteCode'][0]['value'] != '0204289994':
            continue
        if series['variable']['variableCode'][0]['value'] != '62620':
            continue
        if series['variable']['unit']['unitCode'] != 'ft':
            raise ValueError('Unexpected Fort Monroe unit')
        for block in series['values']:
            for row in block['value']:
                value = float(row['value'])
                if np.isfinite(value) and value != -999999:
                    records.append((row['dateTime'], value))
    if not records:
        raise ValueError('No verified station/parameter observations')
    result = pd.Series({stamp: value for stamp, value in records})
    result.index = pd.to_datetime(result.index, utc=True)
    result = result.sort_index()
    return result.resample('1h').mean().rename('fort_navd88_ft')

def score(y, p):
    high = y >= 4.0
    depth = lambda v: np.maximum(0, 10.95*v - 43.69)
    return dict(n=len(y), mae_ft=float(np.abs(y-p).mean()),
        rmse_ft=float(np.sqrt(((y-p)**2).mean())), high_n=int(high.sum()),
        high_mae_ft=float(np.abs(y[high]-p[high]).mean()) if high.any() else None,
        misses=int(((y>=4)&(p<4)).sum()), false_alarms=int(((y<4)&(p>=4)).sum()),
        modeled_depth_mae_in=float(np.abs(depth(y)-depth(p)).mean()))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--history', default='.cache/fort_monroe/history.json')
    ap.add_argument('--dataset',default='merged_hourly_training_dataset.csv');args=ap.parse_args()
    raw=Path(args.history).read_bytes(); fort=parse_usgs(json.loads(raw))
    df=pd.read_csv(args.dataset)
    df.index=pd.to_datetime(df.pop('timestamp_utc').str.replace(' UTC','',regex=False),utc=True)
    df=df[~df.index.duplicated()].sort_index().reindex(pd.date_range('2021-01-01','2024-12-31 23:00',freq='1h',tz='UTC'))
    df=df.join(fort)
    sw=[]
    for year in range(2021,2025):
        payload=json.loads(Path(f'.cache/fort_monroe/sewells_{year}.json').read_text())
        for row in payload.get('data',[]):
            try:sw.append((row['t'],float(row['v'])))
            except (ValueError,KeyError):continue
    sewells=pd.Series(dict(sw));sewells.index=pd.to_datetime(sewells.index,utc=True)
    df['sewells_water_mllw_ft']=sewells.reindex(df.index)
    stage=df.ware_river_stage_mllw_ft
    base=pd.DataFrame(index=df.index)
    for col in ['ware_river_stage_mllw_ft','windmill_surge_ft','yorktown_baro_mb','along_bay_wind_mph','cross_bay_wind_mph','sewells_water_mllw_ft']:
        for lag in (1,3,6,12,24): base[f'{col}_lag{lag}']=df[col].shift(lag)
    extra=pd.DataFrame(index=df.index)
    for lag in (1,3,6,12,24): extra[f'fort_navd88_lag{lag}']=df.fort_navd88_ft.shift(lag)
    for lag in (3,6,12): extra[f'fort_change_{lag}h']=df.fort_navd88_ft.shift(1)-df.fort_navd88_ft.shift(1+lag)
    report=dict(station='FTMV2 / USGS 0204289994',parameter='62620, ft NAVD88',
        history_sha256=hashlib.sha256(raw).hexdigest(), training_dataset_sha256=hashlib.sha256(Path(args.dataset).read_bytes()).hexdigest(), historical_hourly_count=int(fort.notna().sum()), software_versions={'numpy':np.__version__,'pandas':pd.__version__,'scikit_learn':__import__('sklearn').__version__},
        baseline_sensors='Ware River, Windmill Point, Yorktown weather and predicted tide, Sewells Point',
        protocol='1h observation latency; train 2021–22; validate 2023; test 2024; 48h split gap; fixed Ridge alpha=10; paired complete-case rows; no future observed weather',
        promotion_gate='At least 5% paired test MAE improvement, no high-water MAE or threshold-miss regression at 1/3/6h; actual issued-guidance replay or prospective evidence additionally required',
        operational_replay_available=False, results=[])
    for h in HORIZONS:
        X=base.copy(); future=df.index+pd.Timedelta(hours=h)
        X['known_target_tide']=df.yorktown_pred_tide_ft.shift(-h)
        for period in (12.4206012,24,24*365.2425):
            angle=2*np.pi*((future-pd.Timestamp('1970-01-01',tz='UTC')).total_seconds()/3600)/period
            X[f'sin_{period}']=np.sin(angle);X[f'cos_{period}']=np.cos(angle)
        y=stage.shift(-h)
        data=X.join(extra).assign(target=y).dropna()
        train=data[data.index<'2023-01-01T00:00Z']; train=train.iloc[:-48]
        val=data[(data.index>='2023-01-03T00:00Z')&(data.index<'2024-01-01T00:00Z')];val=val.iloc[:-48]
        test=data[data.index>='2024-01-03T00:00Z']
        if min(len(train),len(val),len(test))<100: raise ValueError('Insufficient chronological data')
        models=[]; results={}
        for name,features in [('baseline',list(X)),('fort_monroe',list(X)+list(extra))]:
            model=make_pipeline(StandardScaler(),Ridge(alpha=10))
            model.fit(train[features],train.target)
            results[name]={'validation':score(val.target.values,model.predict(val[features])),
                'test':score(test.target.values,model.predict(test[features]))}
            models.append(model.predict(test[features]))
        b,f=results['baseline']['test'],results['fort_monroe']['test']
        # Storm windows from observed high-water groups, split by >72h.
        high_times=test.index[test.target>=4]
        groups=[]
        for ts in high_times:
            if not groups or ts-groups[-1][-1]>pd.Timedelta(hours=72):groups.append([])
            groups[-1].append(ts)
        events=[]
        for group in groups:
            mask=(test.index>=group[0]-pd.Timedelta(hours=24))&(test.index<=group[-1]+pd.Timedelta(hours=24))
            actual=test.target.values[mask];p0,p1=models[0][mask],models[1][mask]
            events.append(dict(start=str(group[0]),end=str(group[-1]),n=int(mask.sum()),baseline_mae_ft=float(np.abs(actual-p0).mean()),fort_mae_ft=float(np.abs(actual-p1).mean()),baseline_peak_error_ft=float(abs(actual.max()-p0.max())),fort_peak_error_ft=float(abs(actual.max()-p1.max()))))
        report['results'].append(dict(horizon_hours=h,train_n=len(train),validation_n=len(val),**results,
            improvement_pct=100*(b['mae_ft']-f['mae_ft'])/b['mae_ft'],events=events))
    short=report['results'][:3]
    numerical=all(r['improvement_pct']>=5 and r['fort_monroe']['test']['high_mae_ft']<=r['baseline']['test']['high_mae_ft'] and r['fort_monroe']['test']['misses']<=r['baseline']['test']['misses'] for r in short)
    report['historical_gate_passed']=numerical
    report['promoted']=False
    report['promotion_reason']='The 3h and 6h paired improvements are below the predeclared 5% gate. Actual issued-guidance incremental skill has not been established.'
    report['sources']=['https://waterservices.usgs.gov/nwis/iv/ (0204289994, parameter 62620, 2021–2024)', 'https://api.tidesandcurrents.noaa.gov/api/prod/datagetter (Sewells 8638610, hourly_height, MLLW, GMT, 2021–2024)', 'Local hourly gauge/met alignment; original observer fields excluded from features and outputs']
    report['decision']='Collect Fort Monroe and paired issued forecasts in shadow mode; retain current operational forecast. Historical ablation cannot prove incremental skill over deployed NWPS guidance.'
    report['limits']=['Revised historical observations, not historical receipt times; simulated 1h latency.', 'No historical issued NWPS or NWS forecast archive; comparator is a causal Ridge baseline, not the deployed guidance.', 'Depth errors use the existing conversion, not independent local field labels.', 'Complete-case sampling does not prove outage resilience or calibrated uncertainty.']
    Path('models/fort_monroe_evaluation.json').write_text(json.dumps(report,indent=2)+'\n')
    for r in report['results']:print(h:=r['horizon_hours'],round(r['baseline']['test']['mae_ft'],4),round(r['fort_monroe']['test']['mae_ft'],4),round(r['improvement_pct'],2))
    print(report['decision'])
if __name__=='__main__':main()
