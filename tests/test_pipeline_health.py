"""Outage, recovery and retained-forecast regressions without live API or push."""
import copy
import csv
import json
import re
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import generate_dashboard as dashboard
import ingest_realtime as ingest
import pipeline_health as health
from runtime_safety import assess_status, atomic_write_json, parse_timestamp
from test_flood_safety import fixture


class HealthTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.failed = {'status': 'completed', 'conclusion': 'failure', 'html_url': 'https://github.com/flatfoot584/mathews-flood-monitor/actions/runs/1'}

    def test_failed_regression_identifies_step_and_fix_even_when_site_fresh(self):
        result = health.classify(fixture(), self.failed, ['Regression checks'], self.now)
        self.assertEqual(result['kind'], 'pipeline_failed')
        self.assertIn('Fix the failing regression', result['detail'])
        self.assertIn('/runs/1', result['url'])

    def test_scheduler_gap_is_distinct_from_upstream_gauge_outage(self):
        status = fixture()
        status['status_generated_at_utc'] = (self.now-timedelta(hours=3)).isoformat()
        self.assertEqual(health.classify(status, now=self.now)['kind'], 'overdue')
        status['status_generated_at_utc'] = self.now.isoformat()
        status['current_conditions']['observation_timestamp_local'] = (self.now-timedelta(hours=3)).isoformat()
        self.assertEqual(health.classify(status, now=self.now)['kind'], 'gauge_stale')
        self.assertEqual(health.classify(None, now=self.now)['kind'], 'site_unreachable')

    def test_initial_outage_duplicate_reminder_and_recovery(self):
        state = {}
        def save(value):
            state.clear(); state.update(value)
        problem = health.classify(None, self.failed, ['Regression checks'])
        with patch.object(health, 'send_ntfy_push', return_value=True) as send:
            self.assertTrue(health.notify_transition(problem, state, save, 'test', self.now))
            self.assertFalse(health.notify_transition(problem, state, save, 'test', self.now+timedelta(minutes=30)))
            self.assertTrue(health.notify_transition(problem, state, save, 'test', self.now+timedelta(hours=6)))
            recovery = health.classify(fixture(), now=self.now)
            self.assertTrue(health.notify_transition(recovery, state, save, 'test', self.now+timedelta(hours=7)))
            self.assertIn('not confirmation that roads are clear', send.call_args.args[2])
            self.assertFalse(health.notify_transition(recovery, state, save, 'test', self.now+timedelta(hours=8)))
            self.assertEqual(send.call_count, 3)

    def test_notification_failure_and_dry_run_do_not_advance_state(self):
        problem = health.classify(None)
        state = {}
        with patch.object(health, 'send_ntfy_push', side_effect=RuntimeError('delivery failure')), patch.object(health, 'atomic_write_json') as save:
            with self.assertRaises(RuntimeError):
                health.notify_transition(problem, state, save, 'test', self.now)
            save.assert_not_called()
        with patch.object(health, 'send_ntfy_push', return_value=True), patch.object(health, 'atomic_write_json') as save:
            health.notify_transition(problem, state, save, 'test', self.now, dry_run=True)
            save.assert_not_called()

    def test_optional_sensor_failure_does_not_raise_health_incident(self):
        status = fixture()
        status['fort_monroe'] = {'fresh': False}
        status['official_nws_alerts'] = {'available': False}
        self.assertEqual(health.classify(status, now=self.now)['kind'], 'healthy')

    def test_stale_display_keeps_original_values_and_forecast_dates(self):
        status = fixture(4.6)
        status['status_generated_at_utc'] = (self.now-timedelta(days=3)).isoformat()
        status['current_conditions']['observation_timestamp_local'] = status['status_generated_at_utc']
        view = dashboard.status_for_display(status)
        self.assertFalse(view['data_quality']['alerts_all_clear_allowed'])
        self.assertEqual(view['last_available_current_conditions']['estimated_local_flood_depth_in'], status['current_conditions']['estimated_local_flood_depth_in'])
        page = dashboard.build_index_html(status, [], [])
        self.assertIn('Last observation; current conditions unknown', page)
        self.assertIn('Last available forecast; check its dates', page)
        self.assertIn('4.60 ft', page)
        self.assertIn('Pipeline status &amp; failure details', page)
        self.assertEqual(view['forecast_hourly_timeline'], status['forecast_hourly_timeline'])

    def test_total_outage_retains_forecast_without_promoting_it_to_live_data(self):
        old = fixture(4.6)
        missing = ingest.generate_latest_status(fcst_timeline=[])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'status.json'
            atomic_write_json(path, old)
            ingest.preserve_last_forecast(missing, path)
            self.assertFalse(assess_status(missing)['forecast_usable'])
            self.assertEqual(missing['last_available_forecast']['saved_at_utc'], old['status_generated_at_utc'])
            view = dashboard.status_for_display(missing)
            self.assertEqual(view['forecast_hourly_timeline'], old['forecast_hourly_timeline'])
            self.assertFalse(view['data_quality']['alerts_all_clear_allowed'])
            repeated = dashboard.status_for_display(view)
            self.assertFalse(repeated['data_quality']['forecast_available'])
            page = dashboard.build_index_html(missing, [], [])
            embedded = json.loads(re.search(r'<script id="flood-data" type="application/json">(.*?)</script>', page, re.S).group(1))
            self.assertEqual(embedded['forecast'], old['forecast_hourly_timeline'][:48])
            atomic_write_json(path, missing)
            again = ingest.generate_latest_status(fcst_timeline=[])
            ingest.preserve_last_forecast(again, path)
            self.assertEqual(again['last_available_forecast'], missing['last_available_forecast'])

    def test_watchdog_runs_independently_and_keeps_health_state_off_main(self):
        workflow = Path('.github/workflows/pipeline_health.yml').read_text()
        self.assertIn('workflow_run:', workflow)
        self.assertIn('schedule:', workflow)
        self.assertNotIn('unittest', workflow)
        self.assertNotIn('needs:', workflow)
        self.assertEqual(health.STATE_BRANCH, 'monitor-health-state')
        self.assertNotIn('el.hidden=true', Path('assets/community.js').read_text())
        self.assertIn('el.hidden=false', Path('assets/community.js').read_text())

    def test_new_page_uses_content_versioned_age_guard_and_styles(self):
        page = dashboard.build_index_html(fixture(), [], [])
        self.assertRegex(page, r'assets/community\.js\?v=[a-f0-9]{12}')
        self.assertRegex(page, r'assets/community\.css\?v=[a-f0-9]{12}')
        worker = Path('service-worker.js').read_text()
        self.assertIn("cache:'no-cache'", worker)
        self.assertIn("ignoreSearch:event.request.mode==='navigate'", worker)

    def test_health_topic_is_separate_from_weather_alert_channel(self):
        workflow = Path('.github/workflows/pipeline_health.yml').read_text()
        self.assertEqual(health.DEFAULT_HEALTH_TOPIC, 'mathews-flood-ops-23128')
        self.assertNotEqual(health.DEFAULT_HEALTH_TOPIC, health.DEFAULT_NTFY_TOPIC)
        self.assertIn("NTFY_HEALTH_TOPIC: ${{ vars.NTFY_HEALTH_TOPIC || 'mathews-flood-ops-23128' }}", workflow)
        # Verify resolution with and without env override
        with patch.dict('os.environ', {}, clear=True):
            resolved = health.os.getenv('NTFY_HEALTH_TOPIC') or health.DEFAULT_HEALTH_TOPIC
            self.assertEqual(resolved, 'mathews-flood-ops-23128')
        with patch.dict('os.environ', {'NTFY_HEALTH_TOPIC': 'custom-ops-channel'}, clear=True):
            resolved = health.os.getenv('NTFY_HEALTH_TOPIC') or health.DEFAULT_HEALTH_TOPIC
            self.assertEqual(resolved, 'custom-ops-channel')

    def test_classify_identifies_stalled_run_with_id_and_age(self):
        status = fixture()
        status['status_generated_at_utc'] = (self.now - timedelta(hours=3)).isoformat()
        stalled = {
            'id': 123456789,
            'status': 'waiting',
            'created_at': (self.now - timedelta(minutes=75)).isoformat(),
            'html_url': 'https://github.com/flatfoot584/mathews-flood-monitor/actions/runs/123456789'
        }
        res = health.classify(status, latest_run=stalled, now=self.now, stalled_run=stalled)
        self.assertEqual(res['kind'], 'overdue')
        self.assertEqual(res['key'], 'pipeline_stalled')
        self.assertIn('123456789', res['detail'])
        self.assertIn('75 minutes', res['detail'])
        self.assertEqual(res['url'], 'https://github.com/flatfoot584/mathews-flood-monitor/actions/runs/123456789')

    def test_cancel_stalled_run_attempts_force_cancel_then_cancel(self):
        class MockStore:
            def __init__(self, fail_first=False):
                self.calls = []
                self.fail_first = fail_first
            def api(self, path, method='GET', payload=None):
                self.calls.append((path, method))
                if self.fail_first and 'force-cancel' in path:
                    raise RuntimeError('force-cancel not supported')
                return {}

        store1 = MockStore(fail_first=False)
        self.assertTrue(health.cancel_stalled_run(store1, 999))
        self.assertEqual(store1.calls, [('/actions/runs/999/force-cancel', 'POST')])

        store2 = MockStore(fail_first=True)
        self.assertTrue(health.cancel_stalled_run(store2, 888))
        self.assertEqual(store2.calls, [
            ('/actions/runs/888/force-cancel', 'POST'),
            ('/actions/runs/888/cancel', 'POST')
        ])

        self.assertFalse(health.cancel_stalled_run(store1, None))

    def test_update_workflow_concurrency_and_deploy_guard(self):
        wf = Path('.github/workflows/update_flood_monitor.yml').read_text()
        self.assertIn('cancel-in-progress: true', wf)
        self.assertIn("if: !cancelled() && needs.update.outputs.artifact_ready == 'true'", wf)


if __name__ == '__main__':
    unittest.main()

