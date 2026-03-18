"""Tests for earnings.py — keyword detection logic (no API calls)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from earnings import EARNINGS_KEYWORDS, _clean_symbol


class TestEarningsKeywords(unittest.TestCase):

    def test_earnings_headline_detected(self):
        headline = "NVDA quarterly earnings beat expectations"
        lower = headline.lower()
        self.assertTrue(any(kw in lower for kw in EARNINGS_KEYWORDS))

    def test_non_earnings_headline(self):
        headline = "Company launches new product line"
        lower = headline.lower()
        self.assertFalse(any(kw in lower for kw in EARNINGS_KEYWORDS))

    def test_q_keywords(self):
        for q in ["q1", "q2", "q3", "q4"]:
            headline = "Company reports %s results" % q
            lower = headline.lower()
            self.assertTrue(
                any(kw in lower for kw in EARNINGS_KEYWORDS),
                "Expected '%s' to match an earnings keyword" % q,
            )

    def test_revenue_report(self):
        headline = "AAPL revenue report exceeds forecast"
        lower = headline.lower()
        self.assertTrue(any(kw in lower for kw in EARNINGS_KEYWORDS))


class TestCleanSymbol(unittest.TestCase):

    def test_crypto_symbol(self):
        self.assertEqual(_clean_symbol("BTC/USD"), "BTC")

    def test_stock_symbol(self):
        self.assertEqual(_clean_symbol("NVDA"), "NVDA")


if __name__ == '__main__':
    unittest.main()
