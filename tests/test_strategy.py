"""Tests for strategy.py — pure computation functions only (no API calls)."""

import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from strategy import (
    calculate_rsi,
    calculate_ma,
    calculate_macd,
    calculate_bollinger,
    calculate_vwap,
    combined_signal,
    momentum_signal,
    mean_reversion_signal,
    breakout_signal,
)


def make_bars(prices, volumes=None):
    # type: (list, list) -> pd.DataFrame
    """Create a DataFrame mimicking Alpaca bars from a list of close prices."""
    n = len(prices)
    if volumes is None:
        volumes = [100000] * n
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=n, freq='h'),
        'open': prices,
        'high': [p * 1.005 for p in prices],
        'low': [p * 0.995 for p in prices],
        'close': prices,
        'volume': volumes,
    })
    return df


class TestCalculateRSI(unittest.TestCase):

    def test_calculate_rsi_overbought(self):
        prices = pd.Series(np.linspace(100, 120, 30))
        rsi = calculate_rsi(prices)
        last_rsi = rsi.iloc[-1]
        self.assertFalse(pd.isna(last_rsi))
        self.assertGreater(last_rsi, 70)

    def test_calculate_rsi_oversold(self):
        prices = pd.Series(np.linspace(100, 80, 30))
        rsi = calculate_rsi(prices)
        last_rsi = rsi.iloc[-1]
        self.assertFalse(pd.isna(last_rsi))
        self.assertLess(last_rsi, 30)

    def test_calculate_rsi_neutral(self):
        prices = pd.Series([100.0] * 30)
        rsi = calculate_rsi(prices)
        last_rsi = rsi.iloc[-1]
        # Flat prices: no gains or losses, RSI is NaN (0/0) or ~50
        self.assertTrue(pd.isna(last_rsi) or (40 <= last_rsi <= 60))


class TestCalculateMA(unittest.TestCase):

    def test_calculate_ma(self):
        prices = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=float)
        ma = calculate_ma(prices, period=5)
        self.assertAlmostEqual(ma.iloc[-1], 8.0)


class TestCalculateMACD(unittest.TestCase):

    def test_calculate_macd(self):
        prices = pd.Series(np.linspace(100, 130, 50))
        macd = calculate_macd(prices)
        self.assertIn('macd_line', macd.columns)
        self.assertIn('signal_line', macd.columns)
        self.assertIn('histogram', macd.columns)
        # histogram == macd_line - signal_line
        expected = macd['macd_line'] - macd['signal_line']
        pd.testing.assert_series_equal(macd['histogram'], expected, check_names=False)


class TestCalculateBollinger(unittest.TestCase):

    def test_calculate_bollinger(self):
        # Varying prices so std > 0
        prices = pd.Series(np.random.RandomState(42).normal(100, 5, 40))
        bb = calculate_bollinger(prices, period=20)
        self.assertIn('upper', bb.columns)
        self.assertIn('middle', bb.columns)
        self.assertIn('lower', bb.columns)

        last = bb.iloc[-1]
        self.assertGreater(last['upper'], last['middle'])
        self.assertGreater(last['middle'], last['lower'])

        # middle should equal 20-period SMA
        sma = prices.rolling(window=20).mean()
        self.assertAlmostEqual(last['middle'], sma.iloc[-1], places=8)


class TestCalculateVWAP(unittest.TestCase):

    def test_calculate_vwap(self):
        df = pd.DataFrame({
            'high': [102.0, 105.0, 108.0],
            'low': [98.0, 101.0, 104.0],
            'close': [100.0, 103.0, 106.0],
            'volume': [1000, 2000, 3000],
        })
        vwap = calculate_vwap(df)

        # Manual calculation
        tp = (df['high'] + df['low'] + df['close']) / 3.0
        expected_vwap = (tp * df['volume']).cumsum() / df['volume'].cumsum()
        pd.testing.assert_series_equal(vwap, expected_vwap, check_names=False)


class TestCombinedSignal(unittest.TestCase):

    def test_combined_signal_buy(self):
        # Steadily falling prices -> RSI oversold, price below MA
        prices = list(np.linspace(120, 80, 40))
        bars = make_bars(prices)
        result = combined_signal(bars)
        self.assertEqual(result['signal'], 'BUY')
        self.assertGreater(result['confidence'], 0)

    def test_combined_signal_sell(self):
        # Steadily rising prices -> RSI overbought, price above MA
        prices = list(np.linspace(80, 120, 40))
        bars = make_bars(prices)
        result = combined_signal(bars)
        self.assertEqual(result['signal'], 'SELL')
        self.assertGreater(result['confidence'], 0)

    def test_combined_signal_hold(self):
        # Flat prices -> neutral RSI, no deviation from MA
        prices = [100.0] * 40
        bars = make_bars(prices)
        result = combined_signal(bars)
        self.assertEqual(result['signal'], 'HOLD')


class TestMomentumSignal(unittest.TestCase):

    def test_momentum_signal_buy(self):
        # Sharply rising prices with high volume on last bar
        base_prices = list(np.linspace(100, 100, 10))
        rising = list(np.linspace(100, 115, 11))  # >3% ROC
        prices = base_prices + rising
        # High volume on last bar to trigger vol_above_avg
        volumes = [50000] * (len(prices) - 1) + [200000]
        bars = make_bars(prices, volumes)
        result = momentum_signal(bars)
        self.assertEqual(result['signal'], 'BUY')
        self.assertGreater(result['confidence'], 0)


class TestMeanReversionSignal(unittest.TestCase):

    def test_mean_reversion_signal_buy(self):
        # 19 bars of slight variance around 100, then 1 big drop.
        # The 20-bar window will have 19 values near 100 and 1 at 70,
        # giving a mean ~98.5 and moderate std, with z-score well below -2.
        stable = [100.0 + (i % 3 - 1) * 0.5 for i in range(19)]
        prices = stable + [70.0]
        bars = make_bars(prices)

        # Need at least 20 bars for the rolling window
        self.assertEqual(len(prices), 20)
        result = mean_reversion_signal(bars)
        self.assertEqual(result['signal'], 'BUY')
        self.assertGreater(result['confidence'], 0)


class TestBreakoutSignal(unittest.TestCase):

    def test_breakout_signal_buy(self):
        # 21 bars of range-bound prices, then a breakout above the 20-bar high
        range_prices = [100.0 + (i % 3) for i in range(21)]
        # Last bar breaks above the max high of previous 20 bars
        max_high = max(p * 1.005 for p in range_prices[:20])
        breakout_price = max_high * 1.02 / 1.005  # close price so that high > prior highs
        prices = range_prices + [breakout_price]
        # High volume on last bar
        volumes = [50000] * (len(prices) - 1) + [200000]
        bars = make_bars(prices, volumes)
        result = breakout_signal(bars)
        self.assertEqual(result['signal'], 'BUY')
        self.assertGreater(result['confidence'], 0)


if __name__ == '__main__':
    unittest.main()
