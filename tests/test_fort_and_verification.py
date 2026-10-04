import json,tempfile,unittest
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
        status=fixture();stamp=ingest.datetime.now(timezone.utc).replace(minute=0,second=0,microsecond=0)+timedelta(hours=1)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'archive.csv';score=Path(folder)/'score.json'
            first=verify.archive_and_verify(status,[],path,score)
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

if __name__=='__main__':unittest.main()
