"""Tests for sentiment.py — keyword scoring logic (no API calls)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sentiment import _score_text


class TestScoreText(unittest.TestCase):

    def test_bullish_headline(self):
        text = "Stock surges to record high on strong growth"
        score = _score_text(text)
        self.assertGreater(score, 0)

    def test_bearish_headline(self):
        text = "Stock crashes amid loss and decline warning"
        score = _score_text(text)
        self.assertLess(score, 0)

    def test_neutral_headline(self):
        text = "Company announces new product"
        score = _score_text(text)
        self.assertEqual(score, 0)


if __name__ == '__main__':
    unittest.main()
