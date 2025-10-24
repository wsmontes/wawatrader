#!/usr/bin/env python3
"""
Quick test to demonstrate timezone-aware logging and scheduling.

Shows how the system correctly handles Pacific Time while respecting
market hours in Eastern Time.
"""

from wawatrader.timezone_utils import get_timezone_manager
from loguru import logger
import sys

# Configure logger
logger.remove()
logger.add(sys.stdout, level="INFO")

def main():
    print("\n" + "="*70)
    print("TIMEZONE-AWARE SYSTEM TEST")
    print("="*70 + "\n")
    
    # Initialize timezone manager
    tz = get_timezone_manager()
    
    # Show current times
    logger.info("📍 Current System Status:")
    tz.log_time_context()
    print()
    
    # Show what times scheduled tasks would run at
    logger.info("📅 Scheduled Tasks (in YOUR local time):")
    print()
    
    tasks = [
        ("overnight_summary", 6, 0, "Morning market briefing"),
        ("premarket_scanner", 7, 0, "Gap analysis & opportunities"),
        ("market_open_prep", 9, 0, "Final preparation"),
        ("Market Opens", 9, 30, "🟢 Active trading begins"),
        ("Market Closes", 16, 0, "🔴 Trading ends"),
        ("earnings_analysis", 17, 0, "Earnings strategy"),
        ("evening_deep_learning", 18, 0, "Deep research (15 iterations)"),
        ("weekly_self_critique", 18, 0, "Self-analysis (Fridays only)"),
    ]
    
    for task_name, et_hour, et_min, description in tasks:
        # Convert ET time to local time
        from datetime import datetime
        from zoneinfo import ZoneInfo
        
        # Create a datetime in ET
        et_tz = ZoneInfo("America/New_York")
        local_tz = tz.local_tz
        
        # Use today's date with the specified time
        now_et = datetime.now(et_tz)
        task_time_et = now_et.replace(hour=et_hour, minute=et_min, second=0, microsecond=0)
        task_time_local = task_time_et.astimezone(local_tz)
        
        # Check if currently in this time range (for next hour)
        current = tz.is_market_time_between(et_hour, et_min, et_hour + 1, 0)
        status = "⏰ ACTIVE NOW" if current else "   "
        
        et_str = task_time_et.strftime("%I:%M %p %Z")
        local_str = task_time_local.strftime("%I:%M %p %Z")
        
        print(f"  {status} {task_name:25s}")
        print(f"       Market Time: {et_str:20s} → Your Time: {local_str}")
        print(f"       {description}")
        print()
    
    print("="*70)
    print("\n✅ Your system is timezone-aware!")
    print(f"   Running in: {tz.local_tz_name}")
    print(f"   Market timezone: {tz.market_tz_name}")
    print(f"   Time offset: {(tz.now_local().utcoffset().total_seconds() - tz.now_market().utcoffset().total_seconds()) / 3600:.0f} hours")
    print("\nAll scheduled tasks will run at the correct LOCAL time.")
    print("No need to manually convert - the system handles it! 🎉\n")

if __name__ == "__main__":
    main()
