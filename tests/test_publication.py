import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import generate_dashboard as dashboard
import publish_site


class PublicationTests(unittest.TestCase):
    def test_only_allowlisted_files_enter_clean_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in publish_site.PUBLIC_FILES:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('public fixture')
            (root / 'ground_truth_observations.csv').write_text('PRIVATE RAW SENTINEL')
            (root / 'notes.html').write_text('PRIVATE NOTES SENTINEL')
            site = root / '_site'
            site.mkdir()
            (site / 'AGENTS.md').write_text('STALE PRIVATE DOCUMENT')
            publish_site.build_site(root, site)
            files = {str(p.relative_to(site)) for p in site.rglob('*') if p.is_file()}
            self.assertEqual(files, set(publish_site.PUBLIC_FILES))
            self.assertNotIn('alert_state.json', files)

    def test_symlink_cannot_smuggle_private_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            private = root / 'private.txt'
            private.write_text('private')
            (root / 'index.html').symlink_to(private)
            with self.assertRaises(ValueError):
                publish_site.build_site(root, root / '_site')

    def test_data_page_never_renders_raw_observer_fields(self):
        page = dashboard.build_data_html({}, [{'year': '2026', 'record_count': '12',
            'raw_notes': 'PRIVATE RAW SENTINEL', 'page_source': 'PRIVATE SOURCE SENTINEL'}], [])
        self.assertNotIn('PRIVATE RAW SENTINEL', page)
        self.assertNotIn('PRIVATE SOURCE SENTINEL', page)
        self.assertNotIn('ground_truth_observations.csv', page)
        self.assertIn('observer_yearly_summary.csv', page)

    def test_public_pages_have_no_private_images_or_documents(self):
        for page in [dashboard.build_about_html({}), dashboard.build_science_html({})]:
            for private in ('photos/IMG_', 'SCIENTIFIC_FINDINGS.md', 'ground_truth_observations.csv', 'file:///'):
                self.assertNotIn(private, page)

    def test_workflow_keeps_live_channel_enabled_without_authentication_gate(self):
        workflow = Path('.github/workflows/update_flood_monitor.yml').read_text()
        self.assertIn('run: python3 check_alerts.py --ntfy', workflow)
        self.assertIn('run: python3 publish_site.py', workflow)
        self.assertNotIn('NTFY_ALERTS_ENABLED', workflow)
        self.assertNotIn('NTFY_TOKEN', workflow)


if __name__ == '__main__':
    unittest.main()
