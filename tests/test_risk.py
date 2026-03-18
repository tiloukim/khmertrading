"""Tests for risk.py — pure logic functions only (no API calls)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from risk import check_drawdown


class TestCheckDrawdown(unittest.TestCase):

    def test_check_drawdown_safe(self):
        # 5% drawdown is below the 10% limit -> False (no breach)
        result = check_drawdown(equity=95000, initial_capital=100000)
        self.assertFalse(result)

    def test_check_drawdown_exceeded(self):
        # 11% drawdown exceeds the 10% limit -> True
        result = check_drawdown(equity=89000, initial_capital=100000)
        self.assertTrue(result)

    def test_check_drawdown_edge(self):
        # Exactly 10% drawdown — function uses >, so exactly 10% is NOT exceeded
        result = check_drawdown(equity=90000, initial_capital=100000)
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
