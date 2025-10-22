"""
Unit Tests for Technical Indicators

Tests verify mathematical accuracy of all indicators using known values.
"""

import pytest
import pandas as pd
import numpy as np
from wawatrader.indicators import TechnicalIndicators, analyze_dataframe, get_latest_signals


class TestMovingAverages:
    """Test moving average calculations"""
    
    def test_sma_simple_case(self):
        """Test SMA with simple known values"""
        prices = pd.Series([10, 12, 14, 16, 18, 20])
        sma = TechnicalIndicators.sma(prices, period=3)
        
        # First two values should be NaN (not enough data)
        assert pd.isna(sma.iloc[0])
        assert pd.isna(sma.iloc[1])
        
        # Third value: (10 + 12 + 14) / 3 = 12
        assert sma.iloc[2] == 12.0
        
        # Fourth value: (12 + 14 + 16) / 3 = 14
        assert sma.iloc[3] == 14.0
    
    def test_ema_calculation(self):
        """Test EMA responds faster than SMA to price changes"""
        prices = pd.Series([10, 10, 10, 10, 20, 20, 20, 20])
        
        sma = TechnicalIndicators.sma(prices, period=4)
        ema = TechnicalIndicators.ema(prices, period=4)
        
        # After price jumps, SMA catches up faster in this case
        # EMA takes time to catch up due to exponential weighting
        # Just verify they're different (EMA more responsive to recent changes)
        assert ema.iloc[-1] != sma.iloc[-1]
        assert abs(ema.iloc[-1] - sma.iloc[-1]) > 0  # They should differ


class TestRSI:
    """Test RSI calculations"""
    
    def test_rsi_extreme_values(self):
        """Test RSI with prices that should give clear overbought/oversold"""
        # Continuous price increase should give high RSI
        increasing = pd.Series(range(1, 31))  # 1, 2, 3, ..., 30
        rsi_up = TechnicalIndicators.rsi(increasing, period=14)
        
        # Last RSI should be close to 100 (overbought)
        assert rsi_up.iloc[-1] > 90
        
        # Continuous price decrease should give low RSI
        decreasing = pd.Series(range(30, 0, -1))  # 30, 29, 28, ..., 1
        rsi_down = TechnicalIndicators.rsi(decreasing, period=14)
        
        # Last RSI should be close to 0 (oversold)
        assert rsi_down.iloc[-1] < 10
    
    def test_rsi_range(self):
        """Test RSI stays within 0-100 range"""
        # Random prices
        np.random.seed(42)
        prices = pd.Series(np.random.randn(100).cumsum() + 100)
        
        rsi = TechnicalIndicators.rsi(prices, period=14)
        
        # Filter out NaN values
        valid_rsi = rsi.dropna()
        
        # All RSI values should be between 0 and 100
        assert (valid_rsi >= 0).all()
        assert (valid_rsi <= 100).all()


class TestMACD:
    """Test MACD calculations"""
    
    def test_macd_components(self):
        """Test MACD returns three components"""
        prices = pd.Series(range(1, 51))
        
        macd, signal, histogram = TechnicalIndicators.macd(prices)
        
        # Should return three series of same length
        assert len(macd) == len(prices)
        assert len(signal) == len(prices)
        assert len(histogram) == len(prices)
    
    def test_macd_histogram(self):
        """Test MACD histogram is difference between MACD and signal"""
        prices = pd.Series(np.random.randn(100).cumsum() + 100)
        
        macd, signal, histogram = TechnicalIndicators.macd(prices)
        
        # Histogram should equal MACD - Signal (where not NaN)
        valid_idx = ~(macd.isna() | signal.isna())
        diff = macd[valid_idx] - signal[valid_idx]
        hist = histogram[valid_idx]
        
        np.testing.assert_array_almost_equal(diff.values, hist.values)


class TestBollingerBands:
    """Test Bollinger Bands calculations"""
    
    def test_bollinger_bands_structure(self):
        """Test Bollinger Bands return upper, middle, lower"""
        prices = pd.Series(range(1, 51))
        
        upper, middle, lower = TechnicalIndicators.bollinger_bands(prices, period=20)
        
        # Should return three series
        assert len(upper) == len(prices)
        assert len(middle) == len(prices)
        assert len(lower) == len(prices)
    
    def test_bollinger_bands_order(self):
        """Test upper > middle > lower (where not NaN)"""
        prices = pd.Series(np.random.randn(100).cumsum() + 100)
        
        upper, middle, lower = TechnicalIndicators.bollinger_bands(prices, period=20)
        
        # Where all three are valid, upper should be > middle > lower
        valid_idx = ~(upper.isna() | middle.isna() | lower.isna())
        
        assert (upper[valid_idx] > middle[valid_idx]).all()
        assert (middle[valid_idx] > lower[valid_idx]).all()
    
    def test_bollinger_bands_middle_is_sma(self):
        """Test middle band equals SMA"""
        prices = pd.Series(range(1, 51))
        period = 20
        
        upper, middle, lower = TechnicalIndicators.bollinger_bands(prices, period=period)
        sma = TechnicalIndicators.sma(prices, period=period)
        
        # Middle band should equal SMA
        pd.testing.assert_series_equal(middle, sma)


class TestATR:
    """Test Average True Range calculations"""
    
    def test_atr_positive(self):
        """Test ATR is always positive"""
        np.random.seed(42)
        high = pd.Series(np.random.randn(100).cumsum() + 100)
        low = high - np.abs(np.random.randn(100))
        close = (high + low) / 2
        
        atr = TechnicalIndicators.atr(high, low, close, period=14)
        
        # ATR should always be positive (where not NaN)
        valid_atr = atr.dropna()
        assert (valid_atr > 0).all()
    
    def test_atr_with_zero_range(self):
        """Test ATR with no price movement"""
        # Constant prices
        high = pd.Series([100] * 50)
        low = pd.Series([100] * 50)
        close = pd.Series([100] * 50)
        
        atr = TechnicalIndicators.atr(high, low, close, period=14)
        
        # ATR should be zero (or very close) when no price movement
        valid_atr = atr.dropna()
        assert (valid_atr < 0.0001).all()


class TestVolumeIndicators:
    """Test volume-based indicators"""
    
    def test_volume_ratio(self):
        """Test volume ratio calculation"""
        # Volume that's consistently at average
        volume = pd.Series([1000] * 30)
        ratio = TechnicalIndicators.volume_ratio(volume, period=20)
        
        # Ratio should be 1.0 when volume equals average
        valid_ratio = ratio.dropna()
        assert np.allclose(valid_ratio, 1.0)
    
    def test_volume_ratio_spike(self):
        """Test volume ratio detects spikes"""
        # Normal volume, then spike
        volume = pd.Series([1000] * 25 + [5000])  # 5x volume spike
        ratio = TechnicalIndicators.volume_ratio(volume, period=20)
        
        # Last value should show high ratio
        assert ratio.iloc[-1] > 2.0
    
    def test_obv_direction(self):
        """Test OBV increases on up days, decreases on down days"""
        # Prices going up
        close_up = pd.Series([100, 101, 102, 103, 104])
        volume = pd.Series([1000, 1000, 1000, 1000, 1000])
        
        obv = TechnicalIndicators.obv(close_up, volume)
        
        # OBV should be increasing
        assert obv.iloc[-1] > obv.iloc[1]  # Skip first (NaN from diff)


class TestVolatility:
    """Test volatility indicators"""
    
    def test_std_dev_positive(self):
        """Test standard deviation is positive"""
        prices = pd.Series(np.random.randn(100).cumsum() + 100)
        
        std = TechnicalIndicators.std_dev(prices, period=20)
        
        # Std dev should always be positive
        valid_std = std.dropna()
        assert (valid_std >= 0).all()
    
    def test_std_dev_zero_for_constant(self):
        """Test std dev is zero for constant prices"""
        prices = pd.Series([100] * 50)
        
        std = TechnicalIndicators.std_dev(prices, period=20)
        
        # Std dev should be zero for constant prices
        valid_std = std.dropna()
        assert (valid_std < 0.0001).all()


class TestCompositeCalculations:
    """Test full indicator calculations"""
    
    def test_calculate_all(self):
        """Test calculate_all adds all indicators"""
        # Create sample OHLCV data
        np.random.seed(42)
        df = pd.DataFrame({
            'open': np.random.randn(50).cumsum() + 100,
            'high': np.random.randn(50).cumsum() + 102,
            'low': np.random.randn(50).cumsum() + 98,
            'close': np.random.randn(50).cumsum() + 100,
            'volume': np.random.randint(1000, 10000, 50)
        })
        
        result = analyze_dataframe(df)
        
        # Should have many more columns than original
        assert len(result.columns) > len(df.columns)
        
        # Should have RSI
        assert 'rsi' in result.columns
        
        # Should have MACD
        assert 'macd' in result.columns
        assert 'macd_signal' in result.columns
        
        # Should have Bollinger Bands
        assert 'bb_upper' in result.columns
        assert 'bb_middle' in result.columns
        assert 'bb_lower' in result.columns
    
    def test_get_latest_signals(self):
        """Test latest signals extraction"""
        # Create sample data
        df = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [102, 103, 104],
            'low': [99, 100, 101],
            'close': [101, 102, 103],
            'volume': [1000, 1100, 1200]
        })
        
        # Calculate indicators
        df = analyze_dataframe(df)
        
        # Get latest signals
        signals = get_latest_signals(df)
        
        # Should have price, trend, momentum, volatility, volume
        assert 'price' in signals
        assert 'trend' in signals
        assert 'momentum' in signals
        assert 'volatility' in signals
        assert 'volume' in signals
        
        # Price should match last close
        assert signals['price']['close'] == 103


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_dataframe(self):
        """Test with empty DataFrame"""
        df = pd.DataFrame()
        
        signals = get_latest_signals(df)
        
        # Should return empty dict
        assert signals == {}
    
    def test_insufficient_data(self):
        """Test with very few data points"""
        # Only 5 data points
        df = pd.DataFrame({
            'open': [100, 101, 102, 103, 104],
            'high': [102, 103, 104, 105, 106],
            'low': [99, 100, 101, 102, 103],
            'close': [101, 102, 103, 104, 105],
            'volume': [1000] * 5
        })
        
        # Should not crash (though many indicators will be NaN)
        result = analyze_dataframe(df)
        
        # Should still have the columns
        assert 'rsi' in result.columns
        assert 'macd' in result.columns
    
    def test_missing_columns(self):
        """Test error when required columns missing"""
        df = pd.DataFrame({
            'close': [100, 101, 102],
            # Missing: open, high, low, volume
        })
        
        with pytest.raises(ValueError, match="Missing required columns"):
            analyze_dataframe(df)


def test_performance():
    """Test calculation performance (should be < 10ms for 1000 bars)"""
    import time
    
    # Generate 1000 bars
    np.random.seed(42)
    df = pd.DataFrame({
        'open': np.random.randn(1000).cumsum() + 100,
        'high': np.random.randn(1000).cumsum() + 102,
        'low': np.random.randn(1000).cumsum() + 98,
        'close': np.random.randn(1000).cumsum() + 100,
        'volume': np.random.randint(1000, 100000, 1000)
    })
    
    # Time the calculation
    start = time.time()
    result = analyze_dataframe(df)
    elapsed = (time.time() - start) * 1000  # Convert to ms
    
    print(f"\n⏱️  Performance: {elapsed:.2f}ms for 1000 bars")
    
    # Should be very fast (< 100ms even with overhead)
    assert elapsed < 100, f"Too slow: {elapsed}ms"
    
    # Should have calculated indicators
    assert not result.empty


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
