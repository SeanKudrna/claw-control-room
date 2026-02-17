#!/usr/bin/env python3
"""Contract tests for compact heading mode inside collapsible sections."""

from pathlib import Path
import unittest


class CollapsibleHeadingCompactTests(unittest.TestCase):
    def test_app_passes_hide_heading_for_collapsible_panel_bodies(self) -> None:
        app = Path('src/App.tsx').read_text(encoding='utf-8')

        expected_snippets = [
            '<Timeline items={data.timeline} hideHeading={true} />',
            '<JobsTable jobs={data.nextJobs} hideHeading={true} />',
            '<ActivityFeed activity={data.activity ?? []} hideHeading={true} />',
            '<Findings findings={data.findings} hideHeading={true} />',
            'hideHeading={true}',
        ]

        for snippet in expected_snippets:
            self.assertIn(snippet, app)


if __name__ == '__main__':
    unittest.main()
