#!/usr/bin/env python3
"""Contract tests for Activity Feed category normalization."""

from pathlib import Path
import unittest


class ActivityFeedCategoryNormalizationTests(unittest.TestCase):
    def test_activity_feed_normalizes_unknown_categories_to_ops(self) -> None:
        source = Path('src/components/ActivityFeed.tsx').read_text(encoding='utf-8')

        self.assertIn('function normalizeActivityCategory(category: string): ActivityCategory', source)
        self.assertIn("const normalized = category.trim().toLowerCase();", source)
        self.assertIn("return 'ops';", source)
        self.assertIn('normalizeActivityCategory(item.category)', source)

    def test_activity_feed_uses_normalized_category_for_badges(self) -> None:
        source = Path('src/components/ActivityFeed.tsx').read_text(encoding='utf-8')

        self.assertIn('const normalizedCategory = normalizeActivityCategory(item.category);', source)
        self.assertIn('{normalizedCategory.toUpperCase()}', source)
        self.assertIn('tiny-pill ${normalizedCategory}', source)


if __name__ == '__main__':
    unittest.main()
