"""
Technical Indicators Module

Pure NumPy/Pandas implementations of technical analysis indicators.
All calculations are deterministic, fast (<1ms), and vectorized.

NO LLM involvement - this is pure numerical computation.

Indicators implemented:
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- SMA/EMA (Simple & Exponential Moving Averages)
- Bollinger Bands
- ATR (Average True Range)
- Volume Analysis
- Standard Deviation
- Support/Resistance levels
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from loguru import logger


class TechnicalIndicators:
    """
    Technical Analysis Indicators Calculator
    
    All methods are static and work with pandas DataFrames/Series.
    Designed for maximum performance on Mac M4 (vectorized operations).
    """
    
    # =====================================================
    # Moving Averages
    # =====================================================
    
    @staticmethod
    def sma(prices: pd.Series, period: int = 20) -> pd.Series:
        """
        Simple Moving Average
        
        Args:
            prices: Price series (typically 'close')
            period: Number of periods (default: 20)
            
        Returns:
            Series with SMA values
        """
        return prices.rolling(window=period).mean()
    
    @staticmethod
    def ema(prices: pd.Series, period: int = 20) -> pd.Series:
        """
        Exponential Moving Average
        
        Args:
            prices: Price series
            period: Number of periods (default: 20)
            
        Returns:
            Series with EMA values
        """
        return prices.ewm(span=period, adjust=False).mean()
    
    # =====================================================
    # RSI (Relative Strength Index)
    # =====================================================
    
    @staticmethod
    def rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Relative Strength Index
        
        Measures momentum on scale of 0-100.
        - RSI > 70: Overbought (potential sell signal)
        - RSI < 30: Oversold (potential buy signal)
        
        Args:
            prices: Price series
            period: RSI period (default: 14)
            
        Returns:
            Series with RSI values (0-100)
        """
        # Calculate price changes
        delta = prices.diff()
        
        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Calculate average gain and loss
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # Calculate RS (Relative Strength)
        rs = avg_gain / avg_loss
        
        # Calculate RSI
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    # =====================================================
    # MACD (Moving Average Convergence Divergence)
    # =====================================================
    
    @staticmethod
    def macd(
        prices: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        MACD (Moving Average Convergence Divergence)
        
        Trend-following momentum indicator.
        - MACD crossing above signal: Bullish
        - MACD crossing below signal: Bearish
        
        Args:
            prices: Price series
            fast_period: Fast EMA period (default: 12)
            slow_period: Slow EMA period (default: 26)
            signal_period: Signal line period (default: 9)
            
        Returns:
            Tuple of (macd_line, signal_line, histogram)
        """
        # Calculate fast and slow EMAs
        fast_ema = TechnicalIndicators.ema(prices, fast_period)
        slow_ema = TechnicalIndicators.ema(prices, slow_period)
        
        # MACD line
        macd_line = fast_ema - slow_ema
        
        # Signal line (EMA of MACD)
        signal_line = TechnicalIndicators.ema(macd_line, signal_period)
        
        # MACD histogram (difference between MACD and signal)
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    # =====================================================
    # Bollinger Bands
    # =====================================================
    
    @staticmethod
    def bollinger_bands(
        prices: pd.Series,
        period: int = 20,
        num_std: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Bollinger Bands
        
        Volatility indicator with upper and lower bands.
        - Price near upper band: Potentially overbought
        - Price near lower band: Potentially oversold
        - Bands narrowing: Low volatility (potential breakout)
        - Bands widening: High volatility
        
        Args:
            prices: Price series
            period: Period for SMA and std dev (default: 20)
            num_std: Number of standard deviations (default: 2.0)
            
        Returns:
            Tuple of (upper_band, middle_band, lower_band)
        """
        # Middle band (SMA)
        middle_band = TechnicalIndicators.sma(prices, period)
        
        # Calculate standard deviation
        std_dev = prices.rolling(window=period).std()
        
        # Upper and lower bands
        upper_band = middle_band + (std_dev * num_std)
        lower_band = middle_band - (std_dev * num_std)
        
        return upper_band, middle_band, lower_band
    
    # =====================================================
    # ATR (Average True Range)
    # =====================================================
    
    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """
        Average True Range
        
        Measures market volatility.
        Higher ATR = Higher volatility
        Lower ATR = Lower volatility
        
        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: ATR period (default: 14)
            
        Returns:
            Series with ATR values
        """
        # Calculate True Range components
        high_low = high - low
        high_close = np.abs(high - close.shift())
        low_close = np.abs(low - close.shift())
        
        # True Range is the maximum of the three
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        
        # ATR is EMA of True Range
        atr = true_range.ewm(span=period, adjust=False).mean()
        
        return atr
    
    # =====================================================
    # Volume Analysis
    # =====================================================
    
    @staticmethod
    def volume_sma(volume: pd.Series, period: int = 20) -> pd.Series:
        """
        Volume Simple Moving Average
        
        Args:
            volume: Volume series
            period: Period (default: 20)
            
        Returns:
            Series with volume SMA
        """
        return volume.rolling(window=period).mean()
    
    @staticmethod
    def volume_ratio(volume: pd.Series, period: int = 20) -> pd.Series:
        """
        Volume Ratio (current volume / average volume)
        
        Values > 1.0: Above average volume
        Values < 1.0: Below average volume
        
        Args:
            volume: Volume series
            period: Period for average (default: 20)
            
        Returns:
            Series with volume ratios
        """
        avg_volume = TechnicalIndicators.volume_sma(volume, period)
        return volume / avg_volume
    
    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        On-Balance Volume (OBV)
        
        Cumulative volume-based indicator.
        - OBV rising: Buying pressure
        - OBV falling: Selling pressure
        
        Args:
            close: Close prices
            volume: Volume series
            
        Returns:
            Series with OBV values
        """
        # Determine direction (1 for up, -1 for down, 0 for unchanged)
        direction = np.sign(close.diff())
        
        # OBV is cumulative sum of direction * volume
        obv = (direction * volume).cumsum()
        
        return obv
    
    # =====================================================
    # Volatility
    # =====================================================
    
    @staticmethod
    def std_dev(prices: pd.Series, period: int = 20) -> pd.Series:
        """
        Standard Deviation
        
        Measures price volatility.
        
        Args:
            prices: Price series
            period: Period (default: 20)
            
        Returns:
            Series with standard deviation values
        """
        return prices.rolling(window=period).std()
    
    @staticmethod
    def historical_volatility(prices: pd.Series, period: int = 20) -> pd.Series:
        """
        Historical Volatility (annualized)
        
        Standard deviation of log returns, annualized.
        
        Args:
            prices: Price series
            period: Period (default: 20)
            
        Returns:
            Series with annualized volatility (percentage)
        """
        # Calculate log returns
        log_returns = np.log(prices / prices.shift(1))
        
        # Calculate rolling standard deviation
        volatility = log_returns.rolling(window=period).std()
        
        # Annualize (assuming 252 trading days)
        annualized = volatility * np.sqrt(252) * 100
        
        return annualized
    
    # =====================================================
    # Support & Resistance
    # =====================================================
    
    @staticmethod
    def support_resistance(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 20
    ) -> Dict[str, float]:
        """
        Calculate support and resistance levels
        
        Uses recent highs/lows and pivot points.
        
        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: Lookback period (default: 20)
            
        Returns:
            Dictionary with support and resistance levels
        """
        # Get recent data
        recent_high = high.tail(period)
        recent_low = low.tail(period)
        recent_close = close.tail(period)
        
        # Pivot point (standard)
        pivot = (recent_high.max() + recent_low.min() + recent_close.iloc[-1]) / 3
        
        # Resistance levels
        r1 = 2 * pivot - recent_low.min()
        r2 = pivot + (recent_high.max() - recent_low.min())
        
        # Support levels
        s1 = 2 * pivot - recent_high.max()
        s2 = pivot - (recent_high.max() - recent_low.min())
        
        return {
            'pivot': pivot,
            'resistance_1': r1,
            'resistance_2': r2,
            'support_1': s1,
            'support_2': s2,
        }
    
    # =====================================================
    # Composite Indicators
    # =====================================================
    
    @staticmethod
    def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all technical indicators for a DataFrame
        
        Args:
            df: DataFrame with OHLCV data
                Required columns: open, high, low, close, volume
                
        Returns:
            DataFrame with all indicators added as new columns
        """
        df = df.copy()
        
        # Ensure required columns exist
        required = ['open', 'high', 'low', 'close', 'volume']
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        
        logger.debug("Calculating technical indicators...")
        
        # Moving Averages
        df['sma_20'] = TechnicalIndicators.sma(df['close'], 20)
        df['sma_50'] = TechnicalIndicators.sma(df['close'], 50)
        df['ema_12'] = TechnicalIndicators.ema(df['close'], 12)
        df['ema_26'] = TechnicalIndicators.ema(df['close'], 26)
        
        # RSI
        df['rsi'] = TechnicalIndicators.rsi(df['close'], 14)
        
        # MACD
        macd_line, signal_line, histogram = TechnicalIndicators.macd(df['close'])
        df['macd'] = macd_line
        df['macd_signal'] = signal_line
        df['macd_histogram'] = histogram
        
        # Bollinger Bands
        upper, middle, lower = TechnicalIndicators.bollinger_bands(df['close'])
        df['bb_upper'] = upper
        df['bb_middle'] = middle
        df['bb_lower'] = lower
        df['bb_width'] = (upper - lower) / middle  # Normalized width
        
        # ATR
        df['atr'] = TechnicalIndicators.atr(df['high'], df['low'], df['close'])
        
        # Volume indicators
        df['volume_sma'] = TechnicalIndicators.volume_sma(df['volume'])
        df['volume_ratio'] = TechnicalIndicators.volume_ratio(df['volume'])
        df['obv'] = TechnicalIndicators.obv(df['close'], df['volume'])
        
        # Volatility
        df['std_dev'] = TechnicalIndicators.std_dev(df['close'])
        df['volatility'] = TechnicalIndicators.historical_volatility(df['close'])
        
        logger.debug(f"Calculated {len([col for col in df.columns if col not in required])} indicators")
        
        return df


# =====================================================
# Convenience Functions
# =====================================================

def analyze_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convenience function to calculate all indicators
    
    Args:
        df: DataFrame with OHLCV data
        
    Returns:
        DataFrame with all indicators
    """
    return TechnicalIndicators.calculate_all(df)


def get_latest_signals(df: pd.DataFrame) -> Dict[str, any]:
    """
    Get latest indicator values (for trading decisions)
    
    Args:
        df: DataFrame with calculated indicators
        
    Returns:
        Dictionary with latest indicator values
    """
    if df.empty:
        return {}
    
    latest = df.iloc[-1]
    
    signals = {
        'price': {
            'close': latest.get('close'),
            'open': latest.get('open'),
            'high': latest.get('high'),
            'low': latest.get('low'),
        },
        'trend': {
            'sma_20': latest.get('sma_20'),
            'sma_50': latest.get('sma_50'),
            'ema_12': latest.get('ema_12'),
            'ema_26': latest.get('ema_26'),
        },
        'momentum': {
            'rsi': latest.get('rsi'),
            'macd': latest.get('macd'),
            'macd_signal': latest.get('macd_signal'),
            'macd_histogram': latest.get('macd_histogram'),
        },
        'volatility': {
            'bb_upper': latest.get('bb_upper'),
            'bb_middle': latest.get('bb_middle'),
            'bb_lower': latest.get('bb_lower'),
            'bb_width': latest.get('bb_width'),
            'atr': latest.get('atr'),
            'std_dev': latest.get('std_dev'),
            'volatility': latest.get('volatility'),
        },
        'volume': {
            'volume': latest.get('volume'),
            'volume_sma': latest.get('volume_sma'),
            'volume_ratio': latest.get('volume_ratio'),
            'obv': latest.get('obv'),
        }
    }
    
    return signals


if __name__ == "__main__":
    # Test with sample data
    from wawatrader import get_client
    from datetime import datetime, timedelta
    
    print("Testing Technical Indicators...")
    print("=" * 60)
    
    # Get real market data
    client = get_client()
    bars = client.get_bars(
        symbol='AAPL',
        timeframe='1Day',
        start=datetime.now() - timedelta(days=100),
        limit=100
    )
    
    if not bars.empty:
        print(f"\nCalculating indicators for AAPL ({len(bars)} bars)...")
        
        # Calculate all indicators
        df = analyze_dataframe(bars)
        
        print(f"\n✅ Calculated {len(df.columns)} total columns")
        print(f"   Original: {['timestamp', 'open', 'high', 'low', 'close', 'volume']}")
        print(f"   Indicators: {[col for col in df.columns if col not in ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'trade_count', 'vwap']]}")
        
        # Get latest signals
        signals = get_latest_signals(df)
        
        print(f"\n📊 Latest Signals:")
        print(f"   Price: ${signals['price']['close']:.2f}")
        print(f"   RSI: {signals['momentum']['rsi']:.2f}")
        print(f"   MACD: {signals['momentum']['macd']:.4f}")
        print(f"   ATR: {signals['volatility']['atr']:.2f}")
        print(f"   Volume Ratio: {signals['volume']['volume_ratio']:.2f}x")
        
        print("\n✅ Technical Indicators module working!")
    else:
        print("❌ No market data available")
