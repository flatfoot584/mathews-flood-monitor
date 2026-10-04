#!/usr/bin/env python3
"""Read-only freshness monitor for an independent scheduler; exits 1 when degraded."""
import argparse
import json
import sys
import urllib.request
from runtime_safety import assess_status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='https://flatfoot584.github.io/mathews-flood-monitor/latest_status.json')
    args = parser.parse_args()
    try:
        request = urllib.request.Request(args.url, headers={'Cache-Control': 'no-cache'})
        with urllib.request.urlopen(request, timeout=15) as response:
            quality = assess_status(json.load(response))
        print(json.dumps(quality, indent=2))
        return 0 if quality['state'] == 'healthy' else 1
    except (OSError, ValueError):
        print('Pipeline health unavailable.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
