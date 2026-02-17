#!/usr/bin/env python3

from __future__ import annotations

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.issue_snapshot import render_markdown


class IssueSnapshotTests(unittest.TestCase):
    def test_render_with_no_issues(self) -> None:
        md = render_markdown("owner/repo", [])
        self.assertIn("Open issues: 0", md)
        self.assertIn("No open issues", md)

    def test_render_with_issue(self) -> None:
        issues = [
            {
                "number": 12,
                "title": "Fix duplicate next items",
                "url": "https://example.com/12",
                "labels": [{"name": "qa"}, {"name": "bug"}],
                "updatedAt": "2026-02-17T21:00:00Z",
            }
        ]
        md = render_markdown("owner/repo", issues)
        self.assertIn("#12", md)
        self.assertIn("Fix duplicate next items", md)
        self.assertIn("qa, bug", md)


if __name__ == "__main__":
    unittest.main()
