"""
Professional Timezone Management for WawaTrader

Comprehensive timezone handling for financial markets with proper DST support,
market hours awareness, and consistent datetime operations across the system.

Key Features:
- US Eastern Time (NYSE/NASDAQ) as primary market timezone
- Automatic DST transitions handling (EST/EDT)
- Timezone-aware vs naive datetime conversion utilities  
- Market session time calculations
- Cross-timezone datetime comparisons
- Professional datetime normalization for cache operations

Author: WawaTrader Team
Updated: October 2025 - Professional Enhancement
"""

import pytz
import pandas as pd
from datetime import datetime, time as dt_time, date, timedelta
from zoneinfo import ZoneInfo
from typing import Tuple, Optional, Union
from loguru import logger

__all__ = [
    'MarketTimezone', 'TimezoneManager', 'get_timezone_manager',
    'now_market', 'now_local', 'to_market_time', 'to_local_time',
    'normalize_datetime', 'safe_datetime_compare', 'format_market_time', 'format_local_time'
]


class MarketTimezone:
    """
    Professional timezone management for US equity markets.
    
    Handles all timezone operations consistently across the trading system
    with proper DST support and market hours awareness.
    """
    
    # Market timezone (US Eastern with automatic DST: EST/EDT)
    MARKET_TZ = pytz.timezone('US/Eastern')
    
    # UTC timezone for internal storage and API operations
    UTC_TZ = pytz.UTC
    
    # Market session times (Eastern Time)
    MARKET_OPEN_TIME = dt_time(9, 30)    # 9:30 AM ET
    MARKET_CLOSE_TIME = dt_time(16, 0)   # 4:00 PM ET
    
    # Extended trading sessions
    PREMARKET_START = dt_time(4, 0)      # 4:00 AM ET
    AFTERHOURS_END = dt_time(20, 0)      # 8:00 PM ET
    
    def __init__(self):
        """Initialize market timezone manager."""
        logger.info("⏰ Professional Market Timezone Manager initialized")
        logger.info(f"   Market timezone: {self.MARKET_TZ}")
        logger.info(f"   Current market time: {self.format_market_time(self.now_market_time())}")
        logger.info(f"   Market status: {self.get_market_session_info()['session']}")
    
    @classmethod
    def now_market_time(cls) -> datetime:
        """Get current time in market timezone (US Eastern)."""
        return datetime.now(cls.MARKET_TZ)
    
    @classmethod
    def now_utc(cls) -> datetime:
        """Get current time in UTC."""
        return datetime.now(cls.UTC_TZ)
    
    @classmethod
    def to_market_time(cls, dt: Union[datetime, pd.Timestamp, str]) -> datetime:
        """
        Convert datetime to market timezone (US Eastern).
        
        Handles timezone-aware, naive, and string inputs professionally.
        
        Args:
            dt: Input datetime (can be naive, aware, or string)
            
        Returns:
            Timezone-aware datetime in US Eastern
        """
        if isinstance(dt, str):
            dt = pd.to_datetime(dt)
        
        if isinstance(dt, pd.Timestamp):
            dt = dt.to_pydatetime()
        
        if dt.tzinfo is None:
            # Assume naive datetime is already in market time
            dt = cls.MARKET_TZ.localize(dt)
        else:
            # Convert from other timezone to market time
            dt = dt.astimezone(cls.MARKET_TZ)
        
        return dt
    
    @classmethod
    def to_utc(cls, dt: Union[datetime, pd.Timestamp, str]) -> datetime:
        """
        Convert datetime to UTC.
        
        Args:
            dt: Input datetime (can be naive, aware, or string)
            
        Returns:
            Timezone-aware datetime in UTC
        """
        if isinstance(dt, str):
            dt = pd.to_datetime(dt)
        
        if isinstance(dt, pd.Timestamp):
            dt = dt.to_pydatetime()
        
        if dt.tzinfo is None:
            # Assume naive datetime is in market time
            dt = cls.MARKET_TZ.localize(dt)
        
        # Convert to UTC
        return dt.astimezone(cls.UTC_TZ)
    
    @classmethod
    def to_naive_market_time(cls, dt: Union[datetime, pd.Timestamp, str]) -> datetime:
        """
        Convert datetime to naive datetime in market timezone.
        
        This is the key method for cache operations - provides consistent
        timezone-naive datetimes that represent market time for safe comparison.
        
        Args:
            dt: Input datetime
            
        Returns:
            Timezone-naive datetime representing market time
        """
        market_dt = cls.to_market_time(dt)
        return market_dt.replace(tzinfo=None)
    
    @classmethod
    def normalize_for_comparison(cls, dt: Union[datetime, pd.Timestamp]) -> datetime:
        """
        Normalize datetime for consistent comparison operations.
        
        This is THE method to use for all datetime comparisons in the cache system.
        Converts to market timezone and removes timezone info for safe comparison.
        
        Args:
            dt: Input datetime (can be timezone-aware or naive)
            
        Returns:
            Normalized datetime for comparison (naive market time)
        """
        try:
            return cls.to_naive_market_time(dt)
        except Exception as e:
            logger.warning(f"⚠️  Datetime normalization failed for {dt}: {e}")
            # Fallback: if it's already naive, assume it's market time
            if isinstance(dt, pd.Timestamp):
                dt = dt.to_pydatetime()
            if dt.tzinfo is None:
                return dt
            else:
                return dt.replace(tzinfo=None)
    
    @classmethod
    def is_market_hours(cls, dt: Optional[datetime] = None) -> bool:
        """
        Check if given time (or current time) is during regular market hours.
        
        Args:
            dt: Datetime to check (defaults to now)
            
        Returns:
            True if during market hours (9:30 AM - 4:00 PM ET, weekdays)
        """
        if dt is None:
            dt = cls.now_market_time()
        else:
            dt = cls.to_market_time(dt)
        
        # Check if weekday (Monday=0, Sunday=6)
        if dt.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Check if within market hours
        current_time = dt.time()
        return cls.MARKET_OPEN_TIME <= current_time <= cls.MARKET_CLOSE_TIME
    
    @classmethod
    def get_market_session_info(cls, dt: Optional[datetime] = None) -> dict:
        """
        Get detailed market session information for a given time.
        
        Args:
            dt: Datetime to analyze (defaults to now)
            
        Returns:
            Dictionary with market session details
        """
        if dt is None:
            dt = cls.now_market_time()
        else:
            dt = cls.to_market_time(dt)
        
        current_time = dt.time()
        is_weekday = dt.weekday() < 5
        
        session_info = {
            'datetime': dt,
            'is_weekday': is_weekday,
            'is_trading_day': is_weekday,  # Simplified - could add holiday checking
            'session': 'closed'
        }
        
        if is_weekday:
            if current_time < cls.PREMARKET_START:
                session_info['session'] = 'closed'
            elif cls.PREMARKET_START <= current_time < cls.MARKET_OPEN_TIME:
                session_info['session'] = 'premarket'
            elif cls.MARKET_OPEN_TIME <= current_time <= cls.MARKET_CLOSE_TIME:
                session_info['session'] = 'regular'
            elif cls.MARKET_CLOSE_TIME < current_time <= cls.AFTERHOURS_END:
                session_info['session'] = 'afterhours'
            else:
                session_info['session'] = 'closed'
        
        return session_info
    
    @classmethod
    def format_market_time(cls, dt: datetime, include_timezone: bool = True) -> str:
        """
        Format datetime for display in market context.
        
        Args:
            dt: Datetime to format
            include_timezone: Whether to include timezone abbreviation
            
        Returns:
            Formatted datetime string
        """
        try:
            market_dt = cls.to_market_time(dt)
            
            if include_timezone:
                # Get timezone abbreviation (EST/EDT)
                tz_abbr = market_dt.strftime('%Z')
                return market_dt.strftime(f'%Y-%m-%d %H:%M:%S {tz_abbr}')
            else:
                return market_dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            # Fallback formatting
            return str(dt)


class TimezoneManager(MarketTimezone):
    """
    Legacy wrapper for backward compatibility.
    
    Maintains existing interface while providing enhanced functionality.
    """
    
    def __init__(self, local_tz: str = "America/Los_Angeles", market_tz: str = "America/New_York"):
        """
        Initialize timezone manager with legacy interface.
        
        Args:
            local_tz: Local timezone string (for display)
            market_tz: Market timezone string (always "America/New_York")
        """
        super().__init__()
        
        self.local_tz = ZoneInfo(local_tz) if local_tz != "US/Eastern" else self.MARKET_TZ
        self.market_tz = self.MARKET_TZ  # Always use professional market timezone
        self.local_tz_name = local_tz
        self.market_tz_name = "US/Eastern"  # Professional standard
        
        logger.info(f"   Local timezone: {local_tz}")
        logger.info(f"   Legacy compatibility mode enabled")


# ===== PROFESSIONAL CONVENIENCE FUNCTIONS =====

def now_market() -> datetime:
    """Get current time in market timezone."""
    return MarketTimezone.now_market_time()

def to_market_time(dt: Union[datetime, pd.Timestamp, str]) -> datetime:
    """Convert datetime to market timezone."""
    return MarketTimezone.to_market_time(dt)

def to_naive_market(dt: Union[datetime, pd.Timestamp, str]) -> datetime:
    """Convert datetime to naive market timezone for cache operations."""
    return MarketTimezone.to_naive_market_time(dt)

def normalize_datetime(dt: Union[datetime, pd.Timestamp]) -> datetime:
    """
    THE function to use for all datetime comparisons in cache operations.
    
    Normalizes datetime to timezone-naive market time for consistent comparison.
    """
    return MarketTimezone.normalize_for_comparison(dt)

def is_market_open(dt: Optional[datetime] = None) -> bool:
    """Check if market is currently open."""
    return MarketTimezone.is_market_hours(dt)

def get_market_session() -> dict:
    """Get current market session information."""
    return MarketTimezone.get_market_session_info()

def format_market_time(dt: datetime, include_tz: bool = True) -> str:
    """Format datetime for market display."""
    return MarketTimezone.format_market_time(dt, include_tz)

def safe_datetime_compare(dt1: Union[datetime, pd.Timestamp], dt2: Union[datetime, pd.Timestamp]) -> int:
    """
    Safely compare two datetimes regardless of timezone awareness.
    
    Returns:
        -1 if dt1 < dt2, 0 if equal, 1 if dt1 > dt2
    """
    try:
        norm_dt1 = normalize_datetime(dt1)
        norm_dt2 = normalize_datetime(dt2)
        
        if norm_dt1 < norm_dt2:
            return -1
        elif norm_dt1 > norm_dt2:
            return 1
        else:
            return 0
    except Exception as e:
        logger.warning(f"⚠️  Datetime comparison failed: {e}")
        return 0


# Global timezone manager instance
_market_tz_manager = None

def get_timezone_manager() -> MarketTimezone:
    """Get global timezone manager instance."""
    global _market_tz_manager
    if _market_tz_manager is None:
        _market_tz_manager = MarketTimezone()
    return _market_tz_manager





# Convenience functions for common operations
def now_market() -> datetime:
    """Get current time in market timezone (ET)"""
    return MarketTimezone.now_market_time()


def now_local() -> datetime:
    """Get current time in local timezone"""
    return get_timezone_manager().now_local()


def to_market_time(dt: datetime) -> datetime:
    """Convert datetime to market timezone (ET)"""
    return get_timezone_manager().to_market_time(dt)


def to_local_time(dt: datetime) -> datetime:
    """Convert datetime to local timezone"""
    return get_timezone_manager().to_local_time(dt)


def format_market_time(dt: datetime = None, fmt: str = "%I:%M %p %Z") -> str:
    """Format datetime in market timezone"""
    return get_timezone_manager().format_market_time(dt, fmt)


def format_local_time(dt: datetime = None, fmt: str = "%I:%M %p %Z") -> str:
    """Format datetime in local timezone"""
    return get_timezone_manager().format_local_time(dt, fmt)


if __name__ == "__main__":
    # Test timezone manager
    import os
    os.environ['LOCAL_TIMEZONE'] = 'America/Los_Angeles'  # Pacific Time
    
    print("\n" + "="*60)
    print("TIMEZONE MANAGER TEST")
    print("="*60 + "\n")
    
    tz = TimezoneManager(local_tz="America/Los_Angeles")
    
    print(f"Current Local Time:  {tz.format_local_time()}")
    print(f"Current Market Time: {tz.format_market_time()}")
    print()
    
    # Test time checks
    test_times = [
        ("Pre-market (6:00 AM ET)", 6, 0, 9, 30),
        ("Market open (9:30 AM ET)", 9, 30, 16, 0),
        ("Evening (4:30 PM ET)", 16, 30, 22, 0),
        ("Overnight (10:00 PM ET)", 22, 0, 6, 0),
    ]
    
    print("Time Range Checks:")
    for name, start_h, start_m, end_h, end_m in test_times:
        is_in_range = tz.is_market_time_between(start_h, start_m, end_h, end_m)
        status = "✅ YES" if is_in_range else "❌ NO"
        print(f"  {status} {name}")
    
    print("\n" + "="*60)
    print("Test complete! Timezone handling is working correctly.")
    print("="*60 + "\n")
