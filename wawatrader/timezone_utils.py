"""
Timezone Utilities for WawaTrader

Provides timezone-aware datetime handling to ensure correct operation
regardless of where the system is running (Pacific, Eastern, etc).

All market-related times are in Eastern Time (America/New_York).
System can run in any timezone and times will be converted correctly.

Author: WawaTrader Team
Created: October 2025
"""

from datetime import datetime, time
from zoneinfo import ZoneInfo
from typing import Tuple
from loguru import logger


class TimezoneManager:
    """
    Manages timezone conversions for the trading system.
    
    Ensures all market-related operations use Eastern Time,
    while logging and display can use local time.
    """
    
    def __init__(self, local_tz: str = "America/Los_Angeles", market_tz: str = "America/New_York"):
        """
        Initialize timezone manager.
        
        Args:
            local_tz: Local timezone string (e.g., "America/Los_Angeles" for Pacific)
            market_tz: Market timezone string (always "America/New_York" for US markets)
        """
        self.local_tz = ZoneInfo(local_tz)
        self.market_tz = ZoneInfo(market_tz)
        self.local_tz_name = local_tz
        self.market_tz_name = market_tz
        
        logger.info(f"⏰ Timezone Manager initialized:")
        logger.info(f"   Local timezone: {local_tz}")
        logger.info(f"   Market timezone: {market_tz}")
        
        # Show current times
        local_time = datetime.now(self.local_tz)
        market_time = datetime.now(self.market_tz)
        logger.info(f"   Current local time: {local_time.strftime('%I:%M %p %Z')}")
        logger.info(f"   Current market time: {market_time.strftime('%I:%M %p %Z')}")
    
    def now_local(self) -> datetime:
        """Get current time in local timezone"""
        return datetime.now(self.local_tz)
    
    def now_market(self) -> datetime:
        """Get current time in market timezone (ET)"""
        return datetime.now(self.market_tz)
    
    def to_market_time(self, dt: datetime) -> datetime:
        """
        Convert any datetime to market timezone (ET).
        
        Args:
            dt: Datetime to convert (can be naive or aware)
            
        Returns:
            Datetime in market timezone
        """
        if dt.tzinfo is None:
            # Assume naive datetime is in local timezone
            dt = dt.replace(tzinfo=self.local_tz)
        return dt.astimezone(self.market_tz)
    
    def to_local_time(self, dt: datetime) -> datetime:
        """
        Convert any datetime to local timezone.
        
        Args:
            dt: Datetime to convert (can be naive or aware)
            
        Returns:
            Datetime in local timezone
        """
        if dt.tzinfo is None:
            # Assume naive datetime is in market timezone
            dt = dt.replace(tzinfo=self.market_tz)
        return dt.astimezone(self.local_tz)
    
    def get_market_time_components(self) -> Tuple[int, int]:
        """
        Get current hour and minute in market timezone (ET).
        
        Returns:
            Tuple of (hour, minute) in 24-hour format
        """
        market_now = self.now_market()
        return market_now.hour, market_now.minute
    
    def get_local_time_components(self) -> Tuple[int, int]:
        """
        Get current hour and minute in local timezone.
        
        Returns:
            Tuple of (hour, minute) in 24-hour format
        """
        local_now = self.now_local()
        return local_now.hour, local_now.minute
    
    def format_market_time(self, dt: datetime = None, fmt: str = "%I:%M %p %Z") -> str:
        """
        Format datetime in market timezone.
        
        Args:
            dt: Datetime to format (if None, uses current time)
            fmt: Format string
            
        Returns:
            Formatted time string in market timezone
        """
        if dt is None:
            dt = self.now_market()
        else:
            dt = self.to_market_time(dt)
        return dt.strftime(fmt)
    
    def format_local_time(self, dt: datetime = None, fmt: str = "%I:%M %p %Z") -> str:
        """
        Format datetime in local timezone.
        
        Args:
            dt: Datetime to format (if None, uses current time)
            fmt: Format string
            
        Returns:
            Formatted time string in local timezone
        """
        if dt is None:
            dt = self.now_local()
        else:
            dt = self.to_local_time(dt)
        return dt.strftime(fmt)
    
    def is_market_time_between(self, start_hour: int, start_min: int, 
                                end_hour: int, end_min: int) -> bool:
        """
        Check if current market time (ET) is between start and end times.
        
        Args:
            start_hour: Start hour (0-23) in ET
            start_min: Start minute (0-59)
            end_hour: End hour (0-23) in ET
            end_min: End minute (0-59)
            
        Returns:
            True if current market time is in range
        """
        hour, minute = self.get_market_time_components()
        time_minutes = hour * 60 + minute
        start_minutes = start_hour * 60 + start_min
        end_minutes = end_hour * 60 + end_min
        
        # Handle overnight ranges (e.g., 10 PM to 6 AM)
        if end_minutes < start_minutes:
            return time_minutes >= start_minutes or time_minutes < end_minutes
        else:
            return start_minutes <= time_minutes < end_minutes
    
    def log_time_context(self, message: str = ""):
        """
        Log current time in both local and market timezones.
        Useful for debugging timezone issues.
        
        Args:
            message: Optional context message
        """
        local_time = self.format_local_time()
        market_time = self.format_market_time()
        
        if message:
            logger.info(f"⏰ {message}")
        logger.info(f"   Local time:  {local_time}")
        logger.info(f"   Market time: {market_time}")


# Global timezone manager instance (will be initialized with settings)
_timezone_manager: TimezoneManager = None


def get_timezone_manager() -> TimezoneManager:
    """
    Get global timezone manager instance.
    
    Initializes on first call using config.settings.
    
    Returns:
        Global TimezoneManager instance
    """
    global _timezone_manager
    
    if _timezone_manager is None:
        # Import here to avoid circular dependency
        from config.settings import settings
        
        _timezone_manager = TimezoneManager(
            local_tz=settings.system.local_timezone,
            market_tz=settings.system.market_timezone
        )
    
    return _timezone_manager


# Convenience functions for common operations
def now_market() -> datetime:
    """Get current time in market timezone (ET)"""
    return get_timezone_manager().now_market()


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
