#!/usr/bin/env python3

from __future__ import annotations

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.extract_release_notes import extract_release_notes


class ExtractReleaseNotesTests(unittest.TestCase):
    def test_extract_section(self) -> None:
        changelog = """
# Changelog

## v1.0.0 - 2026-02-17
### Added
- One

## v0.9.0 - 2026-02-10
- Old
"""
        notes = extract_release_notes(changelog, "1.0.0")
        self.assertIn("v1.0.0", notes)
        self.assertIn("- One", notes)
        self.assertNotIn("v0.9.0", notes)

    def test_missing_version_raises(self) -> None:
        with self.assertRaises(ValueError):
            extract_release_notes("# Changelog\n", "9.9.9")


if __name__ == "__main__":
    unittest.main()
