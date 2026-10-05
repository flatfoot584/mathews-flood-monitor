import csv,json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
import ingest_realtime as ingest
import forecast_verification as verify
import generate_dashboard as dashboard
from test_flood_safety import fixture

class FortTests(unittest.TestCase):
    def test_station_specific_datum_and_sentinels(self):
        payload={'primaryUnits':'ft','data':[{'validTime':'2026-10-04T03:18:00Z','primary':1.83},{'validTime':'2026-10-04T03:24:00Z','primary':-999},{'validTime':'invalid','primary':2}]}
        with patch.object(ingest,'fetch_json',return_value=payload):rows=ingest.fetch_fort_monroe_observed()
        self.assertEqual(len(rows),1);self.assertAlmostEqual(rows[0]['elevation_navd88_ft'],0.13)
        payload['primaryUnits']='m'
        with patch.object(ingest,'fetch_json',return_value=payload):self.assertEqual(ingest.fetch_fort_monroe_observed(),[])

    def test_hourly_alignment_never_fills_missing_with_zero(self):
        rows=[{'timestamp_utc':'2026-10-04 03:00:00 UTC'},{'timestamp_utc':'2026-10-04 04:00:00 UTC'}]
        obs=[{'datetime_utc':datetime(2026,10,4,3,18,tzinfo=timezone.utc),'elevation_navd88_ft':0.13}]
        ingest.add_fort_hourly(rows,obs)
        self.assertEqual(rows[0]['fort_monroe_elevation_navd88_ft'],.13)
        self.assertEqual(rows[1]['fort_monroe_elevation_navd88_ft'],'')

    def test_optional_sensor_failure_does_not_change_safety(self):
        status=fixture();status['fort_monroe']={'fresh':False}
        self.assertEqual(ingest.assess_status(status)['state'],'healthy')

    def test_archive_has_all_leads_and_is_idempotent(self):
        status=fixture();now=datetime.now(timezone.utc)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'archive.csv';score=Path(folder)/'score.json'
            first=verify.archive_and_verify(status,[],path,score)
            second=verify.archive_and_verify(status,[],path,score)
            self.assertEqual(first['issued_rows'],6);self.assertEqual(first['issued_rows'],second['issued_rows'])
            self.assertTrue(all(r['n']==0 and r['mae_ft'] is None for r in first['results']))

    def test_matching_observation_is_verified_and_old_rows_preserved(self):
        for minute in (7, 30, 37, 59):
            with self.subTest(issue_minute=minute):
                status=fixture()
                issued=verify.parse_timestamp(status['status_generated_at_utc']).replace(minute=minute,second=0,microsecond=0)
                status['status_generated_at_utc']=issued.isoformat()
                with tempfile.TemporaryDirectory() as folder:
                    path=Path(folder)/'archive.csv';score=Path(folder)/'score.json'
                    verify.archive_and_verify(status,[],path,score)
                    # Nearest nominal 1h valid time changes after :30.
                    # Match the archived time rather than assuming the next hour.
                    with path.open() as stream:
                        row=next(r for r in csv.DictReader(stream) if r['lead_hours']=='1')
                    stamp=verify.parse_timestamp(row['valid_time_utc'])
                    result=verify.archive_and_verify(status,[{'datetime_utc':stamp,'stage_mllw_ft':1.25}],path,score)
                    self.assertEqual(result['results'][0]['n'],1)
                    self.assertAlmostEqual(result['results'][0]['mae_ft'],.25)
                    no_match=verify.archive_and_verify(status,[{'datetime_utc':stamp+timedelta(minutes=30),'stage_mllw_ft':9}],path,score)
                    self.assertEqual(no_match['results'][0]['mae_ft'],result['results'][0]['mae_ft'])

    def test_resident_forecast_has_no_vehicle_crossing_permission(self):
        for stage in (1,4.1,4.5,5.2):
            status=fixture(stage);page=dashboard.build_index_html(status,[],[])
            self.assertNotIn('SUVs/trucks only',page)
            self.assertIn('Hourly values are in the table below',page)
            self.assertIn('Independent community research',page)
            self.assertIn('Official warnings',page)
        self.assertNotIn('100% Free Forever',dashboard.build_alerts_html(fixture()))

    def test_operational_vs_nwps_evaluation_and_high_water(self):
        status = fixture()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'archive.csv'
            score = Path(folder) / 'score.json'
            verify.archive_and_verify(status, [], path, score)
            with path.open() as stream:
                rows = list(csv.DictReader(stream))
            row1 = next(r for r in rows if r['lead_hours'] == '1')
            valid_dt = verify.parse_timestamp(row1['valid_time_utc'])

            # High-water storm event: observed stage 4.50 ft MLLW (>= 4.0 ft)
            obs = [{'datetime_utc': valid_dt, 'stage_mllw_ft': 4.50}]
            res = verify.archive_and_verify(status, obs, path, score)
            r1 = res['results'][0]
            self.assertEqual(r1['n'], 1)
            self.assertEqual(r1['nwps_n'], 1)
            self.assertAlmostEqual(r1['mae_ft'], 3.50)
            self.assertAlmostEqual(r1['nwps_mae_ft'], 3.50)
            self.assertEqual(r1['high_water_n'], 1)
            self.assertEqual(r1['misses'], 1)
            self.assertEqual(r1['nwps_misses'], 1)
            self.assertEqual(r1['false_alarms'], 0)
            self.assertIn('summary', res)
            self.assertEqual(res['summary']['high_water_observations'], 1)

            # Check resident UI rendering
            status['live_verification'] = res
            html = dashboard.resident_ui.monitoring(status)
            self.assertIn('Raw NWPS MAE', html)
            self.assertIn('Skill Δ', html)

    def test_stoplight_panel_colors(self):
        # Green: stage 2.30 ft (Tier 0 - good, no flooding)
        s_green = fixture(2.30, 2.30)
        html_green = dashboard.resident_ui.summary(s_green)
        self.assertIn('stoplight-green', html_green)
        self.assertIn('badge-green', html_green)
        self.assertIn('Good · No Flooding', html_green)

        # Yellow: stage 3.89 ft (Tier 1 - caution, some flooding)
        s_yellow = fixture(3.89, 3.89)
        html_yellow = dashboard.resident_ui.summary(s_yellow)
        self.assertIn('stoplight-yellow', html_yellow)
        self.assertIn('badge-yellow', html_yellow)
        self.assertIn('Caution · Some Flooding', html_yellow)

        # Red: stage 5.20 ft (Tier 3 - danger, severe flooding)
        s_red = fixture(5.20, 5.20)
        html_red = dashboard.resident_ui.summary(s_red)
        self.assertIn('stoplight-red', html_red)
        self.assertIn('badge-red', html_red)
        self.assertIn('Danger · Severe Flooding', html_red)

if __name__=='__main__':unittest.main()
