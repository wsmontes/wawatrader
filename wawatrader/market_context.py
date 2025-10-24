"""
Market Context Capture System

Captures comprehensive market state at decision time for learning and pattern recognition.
This context enables the system to learn what works in different market conditions.

Author: WawaTrader Team
Date: October 23, 2025
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any
from loguru import logger
import pandas as pd


@dataclass
class MarketContext:
    """
    Comprehensive snapshot of market conditions at a specific moment.
    
    This rich context enables the learning system to:
    - Identify patterns that work in specific conditions
    - Learn regime-specific strategies
    - Understand when indicators are most reliable
    - Build conditional models (e.g., "RSI < 30 works in bull markets")
    """
    
    # Timestamp
    timestamp: datetime
    
    # Market State
    regime: str  # "bull", "bear", "sideways", "volatile", "uncertain"
    regime_confidence: float  # 0-1, how confident are we in regime classification
    
    # Market-Wide Indicators
    spy_price: float
    spy_trend: str  # "uptrend", "downtrend", "ranging"
    spy_change_1d: float  # % change over 1 day
    spy_change_5d: float  # % change over 5 days
    spy_change_20d: float  # % change over 20 days
    
    # Volatility Measures
    vix: float
    vix_percentile: float  # Where is VIX relative to 60-day range (0-100)
    vix_trend: str  # "rising", "falling", "stable"
    
    # Volume & Liquidity
    overall_volume_ratio: float  # Current volume / 20-day average
    advancing_declining_ratio: float  # Advancing stocks / Declining stocks
    new_highs_lows_ratio: float  # New highs / New lows
    
    # Sector Rotation (which sectors are leading/lagging)
    sector_momentum: Dict[str, float]  # Sector -> % change today
    leading_sectors: List[str]  # Top 3 performing sectors
    lagging_sectors: List[str]  # Bottom 3 performing sectors
    
    # Economic/Event Context
    earnings_season: bool
    fed_meeting_soon: bool  # Within 5 days
    major_economic_data: bool  # Jobs report, CPI, etc.
    
    # Time Context
    time_of_day: str  # "premarket", "open", "midday", "close", "afterhours"
    day_of_week: str  # "Monday", "Tuesday", etc.
    days_until_opex: int  # Days until options expiration
    
    # Market Breadth
    percent_above_50ma: float  # % of stocks above 50-day MA
    percent_above_200ma: float  # % of stocks above 200-day MA
    
    # Sentiment (if available)
    put_call_ratio: Optional[float] = None
    fear_greed_index: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MarketContext':
        """Create from dictionary"""
        # Convert timestamp string back to datetime if needed
        if isinstance(data.get('timestamp'), str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)
    
    def get_summary(self) -> str:
        """Human-readable summary of market conditions"""
        return f"""
Market Context Summary ({self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}):

📊 Market Regime: {self.regime.upper()} (confidence: {self.regime_confidence:.0%})
📈 SPY Trend: {self.spy_trend} ({self.spy_change_1d:+.2f}% today)
😨 VIX: {self.vix:.2f} (percentile: {self.vix_percentile:.0f})
📊 Volume: {self.overall_volume_ratio:.2f}x average
🔄 Leading Sectors: {', '.join(self.leading_sectors)}
📉 Lagging Sectors: {', '.join(self.lagging_sectors)}
🕐 Time: {self.time_of_day} ({self.day_of_week})
📅 Days to OPEX: {self.days_until_opex}
🎯 Breadth: {self.percent_above_50ma:.1f}% above 50MA
"""


class MarketContextCapture:
    """
    Captures current market context for decision logging.
    
    This class interfaces with market data sources to build
    comprehensive context snapshots.
    """
    
    def __init__(self, alpaca_client):
        """
        Initialize with data sources.
        
        Args:
            alpaca_client: Alpaca client for market data
        """
        self.alpaca = alpaca_client
        logger.info("📸 MarketContextCapture initialized")
    
    def capture_current(self, symbol: Optional[str] = None) -> MarketContext:
        """
        Capture current market context.
        
        Args:
            symbol: Optional specific symbol context
            
        Returns:
            MarketContext snapshot
        """
        try:
            logger.info("📸 Capturing market context...")
            
            # Get current time
            now = datetime.now()
            
            # Determine time of day
            time_of_day = self._get_time_of_day(now)
            
            # Get SPY data for market-wide context
            spy_data = self._get_spy_context()
            
            # Get VIX data
            vix_data = self._get_vix_context()
            
            # Get sector rotation
            sector_data = self._get_sector_rotation()
            
            # Get market breadth
            breadth_data = self._get_market_breadth()
            
            # Determine market regime
            regime, regime_confidence = self._determine_regime(spy_data, vix_data, breadth_data)
            
            # Build context
            context = MarketContext(
                timestamp=now,
                regime=regime,
                regime_confidence=regime_confidence,
                
                # SPY data
                spy_price=spy_data['price'],
                spy_trend=spy_data['trend'],
                spy_change_1d=spy_data['change_1d'],
                spy_change_5d=spy_data['change_5d'],
                spy_change_20d=spy_data['change_20d'],
                
                # VIX data
                vix=vix_data['level'],
                vix_percentile=vix_data['percentile'],
                vix_trend=vix_data['trend'],
                
                # Volume & breadth
                overall_volume_ratio=breadth_data.get('volume_ratio', 1.0),
                advancing_declining_ratio=breadth_data.get('adv_dec_ratio', 1.0),
                new_highs_lows_ratio=breadth_data.get('highs_lows_ratio', 1.0),
                
                # Sector rotation
                sector_momentum=sector_data['momentum'],
                leading_sectors=sector_data['leading'],
                lagging_sectors=sector_data['lagging'],
                
                # Economic/event context
                earnings_season=self._is_earnings_season(now),
                fed_meeting_soon=self._is_fed_meeting_soon(now),
                major_economic_data=self._is_major_data_day(now),
                
                # Time context
                time_of_day=time_of_day,
                day_of_week=now.strftime("%A"),
                days_until_opex=self._days_until_opex(now),
                
                # Market breadth
                percent_above_50ma=breadth_data.get('pct_above_50ma', 50.0),
                percent_above_200ma=breadth_data.get('pct_above_200ma', 50.0),
                
                # Sentiment (optional)
                put_call_ratio=breadth_data.get('put_call_ratio'),
                fear_greed_index=breadth_data.get('fear_greed'),
            )
            
            logger.info(f"✅ Market context captured: {regime} regime, VIX={vix_data['level']:.2f}")
            return context
            
        except Exception as e:
            logger.error(f"❌ Error capturing market context: {e}")
            # Return a minimal context if capture fails
            return self._get_minimal_context()
    
    def _get_spy_context(self) -> Dict[str, Any]:
        """Get SPY context (market-wide proxy)"""
        try:
            # Get SPY bars for multiple timeframes
            bars = self.alpaca.get_bars("SPY", "1Day", limit=30)
            
            if bars.empty:
                return self._default_spy_context()
            
            # Calculate metrics
            current_price = bars['close'].iloc[-1]
            change_1d = ((current_price / bars['close'].iloc[-2]) - 1) * 100
            change_5d = ((current_price / bars['close'].iloc[-6]) - 1) * 100 if len(bars) >= 6 else 0
            change_20d = ((current_price / bars['close'].iloc[-21]) - 1) * 100 if len(bars) >= 21 else 0
            
            # Determine trend
            ma_20 = bars['close'].rolling(20).mean().iloc[-1]
            trend = "uptrend" if current_price > ma_20 else "downtrend"
            
            return {
                'price': current_price,
                'change_1d': change_1d,
                'change_5d': change_5d,
                'change_20d': change_20d,
                'trend': trend
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Could not get SPY context: {e}")
            return self._default_spy_context()
    
    def _get_vix_context(self) -> Dict[str, Any]:
        """Get VIX context"""
        try:
            # Try to get VIX data (may not be available in all accounts)
            bars = self.alpaca.get_bars("VIX", "1Day", limit=60)
            
            if bars.empty:
                return self._default_vix_context()
            
            current_vix = bars['close'].iloc[-1]
            vix_60d_min = bars['close'].min()
            vix_60d_max = bars['close'].max()
            
            # Calculate percentile
            percentile = ((current_vix - vix_60d_min) / (vix_60d_max - vix_60d_min)) * 100
            
            # Determine trend
            vix_5d_ago = bars['close'].iloc[-6] if len(bars) >= 6 else current_vix
            if current_vix > vix_5d_ago * 1.1:
                trend = "rising"
            elif current_vix < vix_5d_ago * 0.9:
                trend = "falling"
            else:
                trend = "stable"
            
            return {
                'level': current_vix,
                'percentile': percentile,
                'trend': trend
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Could not get VIX context: {e}")
            return self._default_vix_context()
    
    def _get_sector_rotation(self) -> Dict[str, Any]:
        """Get sector rotation data"""
        try:
            # Sector ETFs
            sectors = {
                'Technology': 'XLK',
                'Financials': 'XLF',
                'Healthcare': 'XLV',
                'Energy': 'XLE',
                'Consumer': 'XLY',
                'Industrials': 'XLI',
                'Materials': 'XLB',
                'Utilities': 'XLU',
                'Real Estate': 'XLRE'
            }
            
            momentum = {}
            for sector_name, etf in sectors.items():
                try:
                    bars = self.alpaca.get_bars(etf, "1Day", limit=2)
                    if not bars.empty:
                        change = ((bars['close'].iloc[-1] / bars['close'].iloc[-2]) - 1) * 100
                        momentum[sector_name] = change
                except:
                    continue
            
            # If we got data, sort by momentum
            if momentum:
                sorted_sectors = sorted(momentum.items(), key=lambda x: x[1], reverse=True)
                leading = [s[0] for s in sorted_sectors[:3]]
                lagging = [s[0] for s in sorted_sectors[-3:]]
            else:
                leading = ["Unknown"]
                lagging = ["Unknown"]
                momentum = {"Unknown": 0.0}
            
            return {
                'momentum': momentum,
                'leading': leading,
                'lagging': lagging
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Could not get sector rotation: {e}")
            return {
                'momentum': {"Unknown": 0.0},
                'leading': ["Unknown"],
                'lagging': ["Unknown"]
            }
    
    def _get_market_breadth(self) -> Dict[str, Any]:
        """Get market breadth indicators"""
        # This would require more sophisticated data
        # For now, return defaults
        return {
            'volume_ratio': 1.0,
            'adv_dec_ratio': 1.0,
            'highs_lows_ratio': 1.0,
            'pct_above_50ma': 50.0,
            'pct_above_200ma': 50.0,
            'put_call_ratio': None,
            'fear_greed': None
        }
    
    def _determine_regime(self, spy_data: Dict, vix_data: Dict, breadth_data: Dict) -> tuple:
        """
        Determine market regime based on multiple factors.
        
        Returns:
            (regime_name, confidence_score)
        """
        # Simple regime classification based on SPY trend and VIX
        spy_trend = spy_data['trend']
        spy_change_20d = spy_data['change_20d']
        vix_level = vix_data['level']
        
        # Bull market: uptrend, low VIX
        if spy_trend == "uptrend" and spy_change_20d > 5 and vix_level < 20:
            return "bull", 0.85
        
        # Bear market: downtrend, high VIX
        elif spy_trend == "downtrend" and spy_change_20d < -5 and vix_level > 25:
            return "bear", 0.85
        
        # Volatile: high VIX
        elif vix_level > 30:
            return "volatile", 0.80
        
        # Sideways: minimal change
        elif abs(spy_change_20d) < 3:
            return "sideways", 0.75
        
        # Uncertain: mixed signals
        else:
            return "uncertain", 0.60
    
    def _get_time_of_day(self, dt: datetime) -> str:
        """Determine time of day for market"""
        hour = dt.hour
        
        if hour < 9 or (hour == 9 and dt.minute < 30):
            return "premarket"
        elif hour == 9 and dt.minute >= 30:
            return "open"
        elif 10 <= hour < 15:
            return "midday"
        elif 15 <= hour < 16:
            return "close"
        else:
            return "afterhours"
    
    def _is_earnings_season(self, dt: datetime) -> bool:
        """Check if we're in earnings season"""
        # Earnings seasons are typically: Jan, Apr, Jul, Oct
        month = dt.month
        # Within 3 weeks of these months
        return month in [1, 4, 7, 10]
    
    def _is_fed_meeting_soon(self, dt: datetime) -> bool:
        """Check if Fed meeting is within 5 days"""
        # Would need actual Fed calendar
        # For now, return False
        return False
    
    def _is_major_data_day(self, dt: datetime) -> bool:
        """Check if major economic data is released today"""
        # Would need economic calendar
        # For now, return False
        return False
    
    def _days_until_opex(self, dt: datetime) -> int:
        """Calculate days until options expiration (3rd Friday)"""
        # Find 3rd Friday of current month
        year = dt.year
        month = dt.month
        
        # Find first day of month
        first_day = datetime(year, month, 1)
        
        # Find first Friday
        days_until_friday = (4 - first_day.weekday()) % 7
        first_friday = first_day + pd.Timedelta(days=days_until_friday)
        
        # Third Friday is 14 days after first Friday
        third_friday = first_friday + pd.Timedelta(days=14)
        
        # If we're past it, get next month's
        if dt > third_friday:
            next_month = month + 1 if month < 12 else 1
            next_year = year if month < 12 else year + 1
            first_day = datetime(next_year, next_month, 1)
            days_until_friday = (4 - first_day.weekday()) % 7
            first_friday = first_day + pd.Timedelta(days=days_until_friday)
            third_friday = first_friday + pd.Timedelta(days=14)
        
        days_until = (third_friday - dt).days
        return max(0, days_until)
    
    def _default_spy_context(self) -> Dict[str, Any]:
        """Default SPY context when data unavailable"""
        return {
            'price': 450.0,
            'change_1d': 0.0,
            'change_5d': 0.0,
            'change_20d': 0.0,
            'trend': 'ranging'
        }
    
    def _default_vix_context(self) -> Dict[str, Any]:
        """Default VIX context when data unavailable"""
        return {
            'level': 18.0,
            'percentile': 50.0,
            'trend': 'stable'
        }
    
    def _get_minimal_context(self) -> MarketContext:
        """Minimal context when capture fails"""
        now = datetime.now()
        return MarketContext(
            timestamp=now,
            regime="uncertain",
            regime_confidence=0.5,
            spy_price=450.0,
            spy_trend="ranging",
            spy_change_1d=0.0,
            spy_change_5d=0.0,
            spy_change_20d=0.0,
            vix=18.0,
            vix_percentile=50.0,
            vix_trend="stable",
            overall_volume_ratio=1.0,
            advancing_declining_ratio=1.0,
            new_highs_lows_ratio=1.0,
            sector_momentum={"Unknown": 0.0},
            leading_sectors=["Unknown"],
            lagging_sectors=["Unknown"],
            earnings_season=False,
            fed_meeting_soon=False,
            major_economic_data=False,
            time_of_day=self._get_time_of_day(now),
            day_of_week=now.strftime("%A"),
            days_until_opex=0,
            percent_above_50ma=50.0,
            percent_above_200ma=50.0
        )


# Convenience function for quick context capture
def capture_market_context(alpaca_client) -> MarketContext:
    """
    Quick function to capture current market context.
    
    Args:
        alpaca_client: Alpaca client
        
    Returns:
        MarketContext snapshot
    """
    capturer = MarketContextCapture(alpaca_client)
    return capturer.capture_current()
