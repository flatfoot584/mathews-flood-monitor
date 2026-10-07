#!/usr/bin/env python3
"""Independent published-site watchdog; never modifies flood-event alert state.

Uses only the standard library and runs even when collection/regression/deployment
fails. Notification state lives on a separate branch, outside the Pages allowlist.
"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from check_alerts import DEFAULT_NTFY_TOPIC, PUBLIC_PORTAL_URL, DeliveryError, send_ntfy_push
from runtime_safety import assess_status, atomic_write_json, parse_timestamp

WORKFLOW = 'update_flood_monitor.yml'
STATE_BRANCH = 'monitor-health-state'
STATE_FILE = 'pipeline_health_state.json'
REMINDER_HOURS = 6
DEFAULT_HEALTH_TOPIC = 'mathews-flood-ops-23128'


def read_json(url, token=None, method='GET', payload=None):
    headers = {'User-Agent': 'MathewsFloodMonitor-health', 'Cache-Control': 'no-cache'}
    if token:
        if urllib.parse.urlsplit(url).hostname != 'api.github.com':
            raise ValueError('GitHub credential may only be sent to api.github.com')
        headers['Authorization'] = 'Bearer ' + token
        headers['Accept'] = 'application/vnd.github+json'
    body = json.dumps(payload).encode() if payload is not None else None
    if body is not None:
        headers['Content-Type'] = 'application/json'
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        content = response.read()
        return json.loads(content) if content else {}


def classify(status, latest_run=None, failed_steps=(), now=None):
    """Return diagnostic categories plus concrete, bounded next actions."""
    now = now or datetime.now(timezone.utc)
    run = latest_run or {}
    link = run.get('html_url') or 'https://github.com/flatfoot584/mathews-flood-monitor/actions'
    if run.get('status') == 'completed' and run.get('conclusion') in ('failure', 'timed_out', 'cancelled', 'action_required'):
        steps = ', '.join(failed_steps) or run['conclusion']
        action = ('Fix the failing regression, then rerun the pipeline.' if 'Regression checks' in failed_steps else
                  'Check upstream NOAA/NWS responses and retry collection.' if 'Fetch timestamped observations and forecasts' in failed_steps else
                  'Check ntfy delivery/service configuration; hazard messages may be delayed.' if 'Dispatch existing community alerts' in failed_steps or 'Surface notification failure' in failed_steps else
                  'Open the failed run, correct the failing step, and rerun the pipeline.')
        return {'kind': 'pipeline_failed', 'key': 'pipeline_failed:' + steps,
                'detail': 'Pipeline failed at: ' + steps + '. ' + action, 'url': link}
    if status is None:
        return {'kind': 'site_unreachable', 'key': 'site_unreachable',
                'detail': 'Published status could not be read. Check GitHub Pages deployment and availability.', 'url': link}
    quality = assess_status(status, now)
    if quality['state'] == 'healthy':
        return {'kind': 'healthy', 'key': 'healthy', 'detail': 'Published observations and forecast coverage are fresh.', 'url': PUBLIC_PORTAL_URL}
    generated = parse_timestamp(status.get('status_generated_at_utc'))
    age = (now - generated).total_seconds() / 60 if generated else None
    if age is None or age > 90 or age < -5:
        detail = ('Website update age: %.0f minutes. ' % age) if age is not None else 'Website update timestamp missing. '
        detail += ('A pipeline run is queued or running; wait for its result. ' if run.get('status') in ('queued', 'in_progress', 'waiting', 'pending', 'requested') else
                   'Scheduled updates are overdue. GitHub schedules can be delayed; manually run the update workflow if needed. ')
        return {'kind': 'overdue', 'key': 'overdue', 'detail': detail + 'Last saved forecasts remain available with age warnings.', 'url': link}
    kind = 'gauge_stale' if not quality['current_available'] else 'forecast_incomplete'
    return {'kind': kind, 'key': kind, 'detail': ' '.join(quality['reasons']) +
            ' Check the collection run and upstream NOAA/NWS services. Optional Fort Monroe or warning-feed failures do not stop the existing flood channel.', 'url': link}


def notify_transition(health, state, save, topic, now=None, dry_run=False):
    now = now or datetime.now(timezone.utc)
    previous = state.get('key', 'healthy')
    last_sent = parse_timestamp(state.get('notified_at_utc'))
    reminder = last_sent is None or (now - last_sent).total_seconds() >= REMINDER_HOURS * 3600
    if health['key'] == 'healthy' and previous == 'healthy':
        return False
    if health['key'] != 'healthy' and health['key'] == previous and not reminder:
        return False
    recovery = health['key'] == 'healthy'
    title = 'Mathews Flood Monitor: updates restored' if recovery else 'Mathews Flood Monitor: data/pipeline problem'
    message = health['detail']
    if recovery:
        message += ' This is a data-service recovery notice, not confirmation that roads are clear.'
    else:
        message += ' Check official forecasts and actual conditions. Details: ' + health['url']
    delivered = send_ntfy_push(topic, title, message, priority='default' if recovery else 'high',
                              tags='white_check_mark' if recovery else 'warning', click_url=health['url'], dry_run=dry_run)
    if not delivered:
        raise DeliveryError('Health notification delivery failed; notification state was not advanced.')
    if delivered and not dry_run:
        save({'key': health['key'], 'notified_at_utc': now.isoformat()})
    return bool(delivered)


class GitHubState:
    def __init__(self, repository, token):
        self.base = 'https://api.github.com/repos/' + repository
        self.token = token
        self.sha = None

    def api(self, path, method='GET', payload=None):
        return read_json(self.base + path, self.token, method, payload)

    def load(self):
        try:
            item = self.api('/contents/' + STATE_FILE + '?ref=' + STATE_BRANCH)
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
            return {}
        self.sha = item['sha']
        state = json.loads(base64.b64decode(item['content']))
        if not isinstance(state, dict):
            raise ValueError('Invalid watchdog state')
        return state

    def save(self, state):
        try:
            self.api('/git/ref/heads/' + STATE_BRANCH)
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
            main = self.api('/git/ref/heads/main')
            self.api('/git/refs', 'POST', {'ref': 'refs/heads/' + STATE_BRANCH, 'sha': main['object']['sha']})
        payload = {'message': 'Record delivered pipeline-health notification', 'branch': STATE_BRANCH,
                   'content': base64.b64encode((json.dumps(state, indent=2) + '\n').encode()).decode()}
        if self.sha:
            payload['sha'] = self.sha
        result = self.api('/contents/' + STATE_FILE, 'PUT', payload)
        self.sha = result['content']['sha']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--github-state', action='store_true')
    parser.add_argument('--state-file', default=STATE_FILE)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--retry-overdue', action='store_true')
    args = parser.parse_args()
    repository = os.getenv('GITHUB_REPOSITORY', 'flatfoot584/mathews-flood-monitor')
    token = os.getenv('GH_TOKEN') or os.getenv('GITHUB_TOKEN')
    store = GitHubState(repository, token)
    runs = store.api('/actions/workflows/' + WORKFLOW + '/runs?branch=main&per_page=1')['workflow_runs']
    latest = runs[0] if runs else {}
    failed_steps = []
    if latest.get('conclusion') in ('failure', 'timed_out', 'cancelled', 'action_required'):
        jobs = store.api('/actions/runs/' + str(latest['id']) + '/jobs')['jobs']
        for job in jobs:
            steps = [s['name'] for s in job.get('steps', []) if s.get('conclusion') in ('failure', 'timed_out', 'cancelled')]
            failed_steps.extend(steps or ([job['name']] if job.get('conclusion') == 'failure' else []))
    try:
        stamp = int(datetime.now(timezone.utc).timestamp())
        status = read_json(PUBLIC_PORTAL_URL + 'latest_status.json?health=' + str(stamp))
    except (OSError, ValueError):
        status = None
    health = classify(status, latest, failed_steps)
    print(json.dumps(health, indent=2))
    if args.github_state:
        if not token:
            raise ValueError('GitHub notification state requires a token')
        state, save = store.load(), store.save
    else:
        path = Path(args.state_file)
        state = json.loads(path.read_text()) if path.exists() else {}
        save = lambda value: atomic_write_json(path, value)
    topic = os.getenv('NTFY_HEALTH_TOPIC') or DEFAULT_HEALTH_TOPIC
    notify_transition(health, state, save, topic, dry_run=args.dry_run)
    # Attempt a refresh only for scheduler gaps, never loop on failing code or
    # create parallel updates. The run-history timestamp supplies a cooldown.
    created = parse_timestamp(latest.get('created_at'))
    minutes = (datetime.now(timezone.utc) - created).total_seconds() / 60 if created else 1e6
    if (args.retry_overdue and health['kind'] == 'overdue' and minutes > 90
            and latest.get('status') not in ('queued', 'in_progress', 'waiting', 'pending', 'requested')):
        if args.dry_run:
            print('DRY-RUN: would request an overdue pipeline refresh.')
        else:
            store.api('/actions/workflows/' + WORKFLOW + '/dispatches', 'POST', {'ref': 'main'})
            print('Requested an overdue pipeline refresh.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Do not log response bodies, credentials, or arbitrary remote errors.
        print('Pipeline health check failed (' + type(error).__name__ + '). State not advanced unless notification delivery succeeded.', file=sys.stderr)
        sys.exit(1)
