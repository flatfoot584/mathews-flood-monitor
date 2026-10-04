"""Offline regression cases for flood guidance and authenticated alerting."""
import contextlib
import copy
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import check_alerts as alerts
import generate_dashboard as dashboard
import ingest_realtime as ingest
import micro_topography as topography
from runtime_safety import assess_status, atomic_write_json, parse_timestamp


def fixture(stage=1.0, forecast_stage=None, rain=0.0):
    now = datetime.now(timezone.utc)
    hour = now.replace(minute=0, second=0, microsecond=0)
    hours = [hour + timedelta(hours=i) for i in range(49)]
    forecast_stage = stage if forecast_stage is None else forecast_stage
    ingest.SOURCE_HEALTH.clear()
    timeline = ingest.build_forecast_timeline(
        [{'datetime_utc':h, 'forecast_stage_mllw_ft':forecast_stage} for h in hours],
        [{'datetime_utc':h, 'wind_speed_mph':0.0, 'wind_dir_deg':0.0} for h in hours],
        [], [], {h:rain for h in hours})
    return ingest.generate_latest_status(
        ware_obs=[{'datetime_utc':now, 'stage_mllw_ft':stage}], fcst_timeline=timeline)


class FloodSafetyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.state_file = str(Path(self.directory.name) / 'state.json')
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)

    def test_healthy_fixture_and_fresh_all_clear(self):
        status = fixture()
        self.assertEqual(assess_status(status)['state'], 'healthy')
        atomic_write_json(self.state_file, {'active_event':True})
        with patch.object(alerts, 'send_ntfy_push', return_value=True) as send:
            alerts.evaluate_and_dispatch_alerts(status, self.state_file)
        self.assertIn('Modeled hazard ended', send.call_args.kwargs['title'])
        self.assertFalse(json.loads(Path(self.state_file).read_text())['active_event'])

    def test_missing_sources_never_clear_active_event(self):
        status = ingest.generate_latest_status(fcst_timeline=ingest.build_forecast_timeline([],[],[],[],{}))
        atomic_write_json(self.state_file, {'active_event':True})
        with patch.object(alerts, 'send_ntfy_push') as send:
            alerts.evaluate_and_dispatch_alerts(status, self.state_file)
        send.assert_not_called()
        self.assertTrue(json.loads(Path(self.state_file).read_text())['active_event'])
        self.assertEqual(status['current_conditions']['flood_risk_tier'], -1)
        self.assertEqual(status['current_conditions']['vehicle_passability_code'], 'UNKNOWN')
        self.assertIsNone(status['current_conditions']['estimated_local_flood_depth_in'])

    def test_stale_observations_and_pipeline_never_clear(self):
        for field in ('observation_timestamp_local', 'status_generated_at_utc'):
            status = fixture()
            stamp = (datetime.now(timezone.utc)-timedelta(days=3)).isoformat()
            if field.startswith('observation'):
                status['current_conditions'][field] = stamp
            else:
                status[field] = stamp
            atomic_write_json(self.state_file, {'active_event':True})
            with patch.object(alerts, 'send_ntfy_push') as send:
                alerts.evaluate_and_dispatch_alerts(status, self.state_file)
            send.assert_not_called()

    def test_incomplete_weather_or_rain_never_clear(self):
        for flag in ('weather_available', 'precipitation_available'):
            status = fixture()
            status['forecast_hourly_timeline'][10][flag] = False
            atomic_write_json(self.state_file, {'active_event':True})
            with patch.object(alerts, 'send_ntfy_push') as send:
                alerts.evaluate_and_dispatch_alerts(status, self.state_file)
            send.assert_not_called()

    def test_missing_forecast_hour_never_clear(self):
        status = fixture()
        status['forecast_hourly_timeline'].pop(8)
        self.assertFalse(assess_status(status)['alerts_all_clear_allowed'])

    def test_severe_page_cannot_call_impassable_safe(self):
        status = fixture(5.2)
        self.assertEqual(status['current_conditions']['vehicle_passability_code'], 'RED')
        page = dashboard.build_index_html(status, [], [])
        self.assertNotIn('PASSABLE & SAFE', page)
        self.assertNotIn('All access routes dry. Safe for low clearance sedans.', page)
        self.assertIn('never enter floodwater', page)

    def test_forecast_hazard_controls_vehicle_cards(self):
        page = dashboard.build_index_html(fixture(1.0, 5.2), [], [])
        self.assertIn('never enter floodwater', page)
        self.assertNotIn('Ground clearance adequate for current and peak tides.', page)

    def test_rain_flooded_road_blocks_sedans_and_escalates(self):
        status = fixture(4.3, rain=3.0)
        row = status['forecast_hourly_timeline'][0]
        self.assertGreater(row['sector_road_depth_in'], 3.5)
        self.assertIn(row['vehicle_passability_code'], ('ORANGE', 'RED'))
        self.assertGreaterEqual(row['risk_tier'], 2)

    def test_low_stage_rain_hazard_is_not_tier_zero(self):
        status = fixture(3.95, rain=6.0)
        self.assertGreater(status['forecast_48h_outlook']['peak_risk_tier'], 0)

    def test_nws_explicit_calm_without_direction_has_complete_coverage(self):
        now = datetime.now(timezone.utc)
        hour = now.replace(minute=0, second=0, microsecond=0)
        hours = [hour + timedelta(hours=i) for i in range(49)]
        raw = {'properties': {'periods': [
            {'startTime': h.isoformat(), 'windSpeed': '0 mph', 'windDirection': ''}
            for h in hours]}}
        with patch.object(ingest, 'fetch_json', return_value=raw):
            wind = ingest.fetch_nws_hourly_forecast()
        self.assertIsNone(wind[0]['wind_dir_deg'])
        ingest.SOURCE_HEALTH.clear()
        timeline = ingest.build_forecast_timeline(
            [{'datetime_utc': h, 'forecast_stage_mllw_ft': 1.0} for h in hours],
            wind, [], [], {h: 0.0 for h in hours})
        for row in timeline:
            self.assertTrue(row['weather_available'])
            self.assertEqual(row['along_bay_wind_mph'], 0.0)
            self.assertEqual(row['cross_bay_wind_mph'], 0.0)
            self.assertEqual(row['nws_wind_cardinal'], 'Calm')
            self.assertEqual(row['nws_wind_dir_deg'], '')
        status = ingest.generate_latest_status(
            ware_obs=[{'datetime_utc': now, 'stage_mllw_ft': 1.0}], fcst_timeline=timeline)
        quality = assess_status(status)
        self.assertEqual(quality['forecast_hours_available'], 48)
        self.assertTrue(quality['alerts_all_clear_allowed'])

    def test_nonzero_or_missing_speed_without_direction_stays_unknown(self):
        hour = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        for speed in (5.0, None, -1.0, float('nan')):
            wind = [{'datetime_utc': hour, 'wind_speed_mph': speed, 'wind_dir_deg': None}]
            timeline = ingest.build_forecast_timeline(
                [{'datetime_utc': hour, 'forecast_stage_mllw_ft': 1.0}], wind, [], [], {hour: 0.0})
            self.assertFalse(timeline[0]['weather_available'])
            self.assertEqual(timeline[0]['along_bay_wind_mph'], '')

    def test_missing_wind_period_is_not_inferred_calm(self):
        hour = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        timeline = ingest.build_forecast_timeline(
            [{'datetime_utc': hour, 'forecast_stage_mllw_ft': 1.0}], [], [], [], {hour: 0.0})
        self.assertFalse(timeline[0]['weather_available'])
        self.assertEqual(timeline[0]['nws_wind_speed_mph'], '')

    def test_compound_scenario_bounds_enclose_central_estimate(self):
        status = fixture(4.3, rain=3.0)
        for row in status['forecast_hourly_timeline']:
            self.assertLessEqual(row['compound_flood_depth_q10_in'], row['compound_flood_depth_in'])
            self.assertGreaterEqual(row['compound_flood_depth_q90_in'], row['compound_flood_depth_in'])
        page = dashboard.build_index_html(status, [], [])
        self.assertNotIn('80% confidence interval', page)
        self.assertIn('uncalibrated scenario range', page.lower())

    def test_peak_stage_and_depth_times_are_independent(self):
        status = fixture(1, 4.4)
        rows = status['forecast_hourly_timeline']
        rows[1]['forecast_stage_mllw_ft'] = 4.8
        rows[2]['compound_flood_depth_in'] = 20
        result = ingest.generate_latest_status(fcst_timeline=rows)['forecast_48h_outlook']
        self.assertEqual(result['peak_forecast_stage_time_local'], rows[1]['timestamp_local'])
        self.assertEqual(result['peak_depth_time_local'], rows[2]['timestamp_local'])
        self.assertEqual(result['peak_estimated_flood_depth_in'], 20)

    def test_missing_page_renders_unknown_and_has_age_guard(self):
        status = ingest.generate_latest_status(fcst_timeline=[])
        for build, args in [(dashboard.build_index_html,([],[])), (dashboard.build_alerts_html,()),
                            (dashboard.build_about_html,()), (dashboard.build_guide_html,()),
                            (dashboard.build_data_html,([],[])), (dashboard.build_science_html,())]:
            page = build(status, *args)
            self.assertIn('data-freshness', page)
            self.assertIn('assets/community.js', page)
            self.assertIn('age>90*60000', Path('assets/community.js').read_text())
            self.assertNotIn('Normal Conditions — Driveways & Roads Clear', page)

    def test_script_breakout_and_attribute_injection_are_escaped(self):
        status = fixture()
        attack = '</script><script>alert(1)</script>'
        status['forecast_hourly_timeline'][0]['nws_short_forecast'] = attack
        page = dashboard.build_index_html(status, [], [])
        self.assertNotIn(attack, page)
        self.assertIn('\\u003c/script', page)
        notes = '" onmouseover="alert(1)'
        table = dashboard.build_data_html(status, [{'year':'2026','record_count':notes,'raw_notes':'PRIVATE_NOTE_SENTINEL'}], [])
        self.assertNotIn('title="'+notes+'"', table)
        self.assertIn('&quot; onmouseover=&quot;', table)
        self.assertNotIn('PRIVATE_NOTE_SENTINEL',table)

    def test_csp_and_local_runtime_scripts(self):
        page = dashboard.build_index_html(fixture(), [], [])
        self.assertIn('Content-Security-Policy', page)
        self.assertIn('sha256-', page)
        self.assertNotIn('cdn.tailwindcss.com', page)
        self.assertIn('assets/chart.umd.min.js', page)
        self.assertIn('integrity="sha384-', page)

    def test_same_event_one_hour_revision_does_not_duplicate(self):
        status = fixture(1, 4.1)
        peak = datetime.now(timezone.utc)+timedelta(hours=10)
        out = status['forecast_48h_outlook']
        out['peak_hazard_time_local'] = peak.isoformat()
        with patch.object(alerts,'send_ntfy_push',return_value=True) as send:
            alerts.evaluate_and_dispatch_alerts(status,self.state_file)
            out['peak_hazard_time_local'] = (peak+timedelta(hours=1)).isoformat()
            alerts.evaluate_and_dispatch_alerts(status,self.state_file)
        self.assertEqual(send.call_count,1)

    def test_escalation_survives_timestamp_tolerance(self):
        status = fixture(1,4.1)
        with patch.object(alerts,'send_ntfy_push',return_value=True) as send:
            alerts.evaluate_and_dispatch_alerts(status,self.state_file)
            status['forecast_48h_outlook']['peak_risk_tier'] = 3
            alerts.evaluate_and_dispatch_alerts(status,self.state_file)
        self.assertEqual(send.call_count,2)

    def test_failed_delivery_does_not_advance_state(self):
        atomic_write_json(self.state_file, {'active_event':False})
        original = Path(self.state_file).read_text()
        with patch.object(alerts,'send_ntfy_push',return_value=False):
            with self.assertRaises(alerts.DeliveryError):
                alerts.evaluate_and_dispatch_alerts(fixture(1,4.5),self.state_file)
        self.assertEqual(Path(self.state_file).read_text(),original)

    def test_state_write_failure_is_propagated(self):
        with patch.object(alerts,'send_ntfy_push',return_value=True), patch.object(alerts,'atomic_write_json',side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):
                alerts.evaluate_and_dispatch_alerts(fixture(1,4.5),self.state_file)

    def test_corrupt_state_is_not_silently_reset(self):
        Path(self.state_file).write_text('{')
        with self.assertRaises(alerts.DeliveryError):
            alerts.load_alert_state(self.state_file)

    def test_qpf_iso_durations_preserve_volume(self):
        for duration, expected_hours in [('P1D',24),('P1DT6H',30),('PT90M',2)]:
            start = datetime.now(timezone.utc).replace(minute=0,second=0,microsecond=0)
            payload={'properties':{'quantitativePrecipitation':{'values':[{'validTime':start.isoformat()+'/'+duration,'value':25.4}]}}}
            with patch.object(ingest,'fetch_json',return_value=payload):
                result = ingest.fetch_nws_qpf_map()
            self.assertEqual(len(result),expected_hours)
            self.assertAlmostEqual(sum(result.values()),1.0)

    def test_unknown_qpf_is_not_zero(self):
        with patch.object(ingest,'fetch_json',return_value={'properties':{'quantitativePrecipitation':{'values':[{'validTime':'2026-10-03T00:00:00Z/PT1H','value':None}]}}}):
            self.assertEqual(ingest.fetch_nws_qpf_map(),{})

    def test_archive_repairs_missing_data_without_erasing_good_values(self):
        path=Path(self.directory.name)/'archive.csv'
        stamp=(datetime.now(timezone.utc)-timedelta(hours=2)).strftime('%Y-%m-%d %H:00:00 UTC')
        ingest.update_archive_observations(path,[{'timestamp_utc':stamp,'stage':'','wind':5}])
        ingest.update_archive_observations(path,[{'timestamp_utc':stamp,'stage':4.2,'wind':''}])
        with path.open() as stream:rows=list(csv.DictReader(stream))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['stage'],'4.2')
        self.assertEqual(rows[0]['wind'],'5')

    def test_surge_uses_matching_timestamp(self):
        now=datetime.now(timezone.utc)
        observed=[{'datetime_utc':now,'water_level_ft':4.0}]
        preds=[{'datetime_utc':now,'water_level_ft':3.0},{'datetime_utc':now+timedelta(hours=1),'water_level_ft':2.0}]
        self.assertEqual(ingest.matched_surge(observed,preds),1.0)

    def test_dst_fall_back_offsets_are_distinct(self):
        first=parse_timestamp('2026-11-01 01:30:00 EDT')
        second=parse_timestamp('2026-11-01 01:30:00 EST')
        self.assertEqual((second-first).total_seconds(),3600)

    def test_cli_bulletin_does_not_call_stale_data_normal(self):
        status = fixture()
        status['current_conditions']['observation_timestamp_local'] = '2020-01-01T00:00:00Z'
        tier, bulletin = alerts.format_alert_message(status)
        self.assertEqual(tier, -1)
        self.assertNotIn('GREEN — NO FLOOD', bulletin)
        self.assertIn('UNKNOWN', bulletin)

    def test_api_cache_reuses_last_response_across_query_windows(self):
        base='https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?station=1&product=wind'
        response=MagicMock();response.__enter__.return_value=response
        response.read.return_value=b'{"data": []}'
        with patch.dict(os.environ,{'FLOOD_CACHE_DIR':self.directory.name}):
            with patch.object(ingest.urllib.request,'urlopen',return_value=response):
                ingest.fetch_json(base+'&begin_date=20261001%2000:00&end_date=20261001%2001:00')
            with patch.object(ingest.urllib.request,'urlopen',side_effect=urllib.error.URLError('offline')):
                url=base+'&begin_date=20261002%2000:00&end_date=20261002%2001:00'
                self.assertEqual(ingest.fetch_json(url,max_retries=1),{'data':[]})
                self.assertTrue(ingest.SOURCE_HEALTH[url]['cached'])

    def test_circular_wind_mean_wraps_at_north(self):
        hour=datetime.now(timezone.utc).replace(minute=0,second=0,microsecond=0)-timedelta(hours=1)
        wind=[{'datetime_utc':hour,'wind_speed_mph':5.0,'wind_dir_deg':d,'wind_gust_mph':5.0} for d in (359,1)]
        rows=ingest.aggregate_hourly_observations([],wind,[],[],[],[],[],[],lookback_hours=2)
        directions=[r['yorktown_wind_dir_deg'] for r in rows if r['yorktown_wind_dir_deg']!='']
        self.assertTrue(directions)
        self.assertTrue(directions[0]<2 or directions[0]>358)

    def test_operational_pipeline_end_to_end_without_network_or_push(self):
        now=datetime.now(timezone.utc)
        hour=now.replace(minute=0,second=0,microsecond=0)
        hours=[hour+timedelta(hours=n) for n in range(49)]
        wind=[{'datetime_utc':h,'wind_speed_mph':0.0,'wind_dir_deg':0.0,'wind_gust_mph':0.0} for h in hours]
        def coops(station,product,*args,**kwargs):
            if product=='wind':return wind
            if product=='air_pressure':return [{'datetime_utc':now,'baro_mb':1013.0}]
            if product=='air_temperature':return [{'datetime_utc':now,'air_temp_f':60.0}]
            return [{'datetime_utc':h,'water_level_ft':1.0} for h in hours]
        original=os.getcwd()
        try:
            os.chdir(self.directory.name)
            with patch.object(sys,'argv',['ingest_realtime.py','--quiet']),patch.object(ingest,'fetch_nwps_wrvv2_observed',return_value=[{'datetime_utc':now,'stage_mllw_ft':1.0}]),patch.object(ingest,'fetch_nwps_wrvv2_forecast',return_value=[{'datetime_utc':h,'forecast_stage_mllw_ft':1.0} for h in hours]),patch.object(ingest,'fetch_coops_product',side_effect=coops),patch.object(ingest,'fetch_nws_hourly_forecast',return_value=wind),patch.object(ingest,'fetch_nws_qpf_map',return_value={h:0.0 for h in hours}),patch.object(ingest,'fetch_fort_monroe_observed',return_value=[]),patch.object(ingest,'fetch_official_alerts',return_value={'available':False,'alerts':[]}):
                ingest.SOURCE_HEALTH.clear()
                ingest.main()
            status=json.loads(Path('latest_status.json').read_text())
            self.assertEqual(status['data_quality']['state'],'healthy')
            with patch.object(sys,'argv',['generate_dashboard.py']):dashboard.main()
            self.assertTrue(Path('science.html').is_file())
            self.assertIn('Content-Security-Policy',Path('index.html').read_text())
            with patch.object(sys,'argv',['check_alerts.py','--no-ntfy']),patch.object(alerts,'send_ntfy_push') as send:
                alerts.main()
                send.assert_not_called()
        finally:
            os.chdir(original)


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{'NTFY_TOKEN':'secret-test-token','NTFY_SERVER':'https://ntfy.sh'},clear=False)
        self.env.start();self.addCleanup(self.env.stop)

    def test_redirects_are_refused(self):
        with self.assertRaises(alerts.DeliveryError):
            alerts.NoRedirect().redirect_request(None,None,302,'',{},'https://other.test')

    def test_topic_and_https_origin_are_validated(self):
        with self.assertRaises(alerts.DeliveryError): alerts.publisher_config('../evil')
        with patch.dict(os.environ,{'NTFY_SERVER':'http://ntfy.test'}):
            with self.assertRaises(alerts.DeliveryError): alerts.publisher_config('test-topic')

    def test_json_publishing_handles_unicode_without_header_errors(self):
        response=MagicMock();response.status=200;response.__enter__.return_value=response
        with patch.object(alerts.urllib.request,'build_opener') as opener:
            opener.return_value.open.return_value=response
            alerts.send_ntfy_push('test-topic','Flood — warning','Body ☔')
            request=opener.return_value.open.call_args.args[0]
            self.assertEqual(json.loads(request.data)['title'],'Flood — warning')
            self.assertIsNone(request.get_header('Authorization'))
            self.assertEqual(opener.return_value.open.call_count,1)
            self.assertEqual(request.full_url,'https://ntfy.sh/')

    def test_transient_delivery_retries(self):
        response=MagicMock();response.status=200;response.__enter__.return_value=response
        with patch.object(alerts.time,'sleep'),patch.object(alerts.urllib.request,'build_opener') as opener:
            opener.return_value.open.side_effect=[urllib.error.URLError('offline'),response]
            self.assertTrue(alerts.send_ntfy_push('test-topic','Title','Body'))
            self.assertEqual(opener.return_value.open.call_count,2)

    def test_dry_run_never_logs_token_or_sends(self):
        output=io.StringIO()
        with contextlib.redirect_stdout(output),patch.object(alerts.urllib.request,'build_opener') as opener:
            alerts.send_ntfy_push('test-topic','Title','Body',dry_run=True)
        opener.assert_not_called()
        self.assertNotIn('secret-test-token',output.getvalue())


if __name__=='__main__':
    unittest.main()
