"""Durable issue-time archive and prospective verification of the deployed forecast.
Stores six lead times per issue (not every intermediate row) to bound repository growth.
Observation matching uses the gauge's actual timestamp, within three minutes of valid time.
"""
import csv
from pathlib import Path
from datetime import datetime,timezone,timedelta
from runtime_safety import parse_timestamp,finite_number,atomic_write_json

FIELDS=['issue_time_utc','guidance_issued_at_utc','valid_time_utc','lead_hours','actual_lead_hours','predicted_stage_mllw_ft','nwps_raw_stage_ft','fort_observation_time_utc','fort_elevation_navd88_ft','observed_stage_mllw_ft','verified_at_utc']

def archive_and_verify(status,ware_obs,path='issued_forecast_archive.csv',score_path='models/live_verification.json'):
    file=Path(path);rows=[]
    if file.exists():
        with file.open() as f:rows=list(csv.DictReader(f))
    issued=parse_timestamp(status.get('status_generated_at_utc'))
    timeline=status.get('forecast_hourly_timeline',[])
    fort=status.get('fort_monroe',{})
    existing={(r['issue_time_utc'],r['lead_hours']) for r in rows}
    if issued:
        for h in (1,3,6,12,24,48):
            # Select closest complete hour at least h hours after actual issue time.
            target=issued+timedelta(hours=h)
            eligible=[r for r in timeline if parse_timestamp(r.get('timestamp_utc')) and parse_timestamp(r['timestamp_utc'])>issued and finite_number(r.get('forecast_stage_mllw_ft'))]
            item=min(eligible,key=lambda r:abs((parse_timestamp(r['timestamp_utc'])-target).total_seconds()),default=None)
            if not item or (issued.isoformat(),str(h)) in existing:continue
            valid=parse_timestamp(item['timestamp_utc'])
            rows.append(dict(issue_time_utc=issued.isoformat(),guidance_issued_at_utc=status.get('forecast_issued_at_utc',''),valid_time_utc=valid.isoformat(),lead_hours=str(h),actual_lead_hours=round((valid-issued).total_seconds()/3600,3),predicted_stage_mllw_ft=item['forecast_stage_mllw_ft'],nwps_raw_stage_ft=item.get('nwps_raw_stage_ft',''),fort_observation_time_utc=fort.get('observation_time_utc',''),fort_elevation_navd88_ft=fort.get('elevation_navd88_ft'),observed_stage_mllw_ft='',verified_at_utc=''))
    measurements={r['datetime_utc']:r['stage_mllw_ft'] for r in ware_obs if finite_number(r.get('stage_mllw_ft'))}
    for row in rows:
        if row.get('observed_stage_mllw_ft') not in ('',None):continue
        valid=parse_timestamp(row['valid_time_utc'])
        nearby=[t for t in measurements if abs((t-valid).total_seconds())<=180]
        if nearby:
            best=min(nearby,key=lambda t:abs((t-valid).total_seconds()))
            row['observed_stage_mllw_ft']=measurements[best];row['verified_at_utc']=issued.isoformat()
    if rows:
        file.parent.mkdir(parents=True,exist_ok=True)
        import os,tempfile
        fd,tmp=tempfile.mkstemp(dir=file.parent,prefix='.issued-')
        try:
            with os.fdopen(fd,'w',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader();writer.writerows(rows)
            os.replace(tmp,file)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
    results=[]
    for h in (1,3,6,12,24,48):
        paired=[r for r in rows if r['lead_hours']==str(h) and r.get('observed_stage_mllw_ft') not in ('',None)]
        errors=[abs(float(r['predicted_stage_mllw_ft'])-float(r['observed_stage_mllw_ft'])) for r in paired]
        high=[r for r in paired if float(r['observed_stage_mllw_ft'])>=4]
        results.append(dict(lead_hours=h,n=len(paired),mae_ft=sum(errors)/len(errors) if errors else None,
            high_water_n=len(high),misses=sum(float(r['predicted_stage_mllw_ft'])<4 for r in high),
            false_alarms=sum(float(r['predicted_stage_mllw_ft'])>=4 and float(r['observed_stage_mllw_ft'])<4 for r in paired)))
    result=dict(updated_at_utc=issued.isoformat() if issued else None,issued_rows=len(rows),results=results,
        interpretation='Prospective deployed guidance verification against Ware River; Nominal lead bins use the nearest forecast hour; actual_lead_hours records exact lead. Repeated issues are correlated. No independent local-depth validation. Fort Monroe remains observational until a paired candidate passes promotion gates.')
    atomic_write_json(score_path,result)
    return result
