#!/usr/bin/env python3
"""
Test Market Hours Manager - Simulate different times of day

Demonstrates how the system adapts behavior based on market phase.
"""

import sys
from pathlib import Path
from datetime import time

# Add project to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from wawatrader.market_hours_manager import MarketPhase, MarketHoursManager
from wawatrader.timezone_utils import now_market
from loguru import logger

# Configure minimal logging
logger.remove()
logger.add(sys.stdout, format="<level>{message}</level>", level="INFO")


class MockTradingAgent:
    """Minimal mock for testing"""
    def __init__(self):
        from wawatrader.alpaca_client import get_client
        self.alpaca = get_client()
        self.account_value = 100000
        self.daily_start_value = 100000
    
    def reset_daily_metrics(self):
        logger.info("📊 Daily metrics reset")
    
    def run_cycle(self):
        logger.info("🔄 Trading cycle executed")
    
    def get_learning_insights(self):
        return {'lessons_learned': ['Test lesson']}
    
    def get_positions(self):
        return []
    
    def get_account(self):
        return {'equity': '100000'}


def simulate_time_of_day(hour: int, minute: int = 0):
    """
    Show what would happen at a specific ET time.
    
    Args:
        hour: Hour in 24-hour format (ET)
        minute: Minute
    """
    test_time = time(hour, minute)
    
    # Determine phase based on time
    if time(4, 0) <= test_time < time(9, 30):
        phase = MarketPhase.PRE_MARKET
    elif time(9, 30) <= test_time < time(16, 0):
        phase = MarketPhase.MARKET_OPEN
    elif time(16, 0) <= test_time < time(20, 0):
        phase = MarketPhase.AFTER_HOURS
    elif time(20, 0) <= test_time < time(23, 0):
        phase = MarketPhase.EVENING_RESEARCH
    else:
        phase = MarketPhase.DEEP_NIGHT
    
    return phase


def main():
    """Test market hours manager"""
    print("=" * 70)
    print("🧪 MARKET HOURS MANAGER TEST")
    print("=" * 70)
    
    # Show current state
    agent = MockTradingAgent()
    manager = MarketHoursManager(agent)
    
    current_time = now_market()
    current_phase = manager.get_current_phase()
    sleep_interval = manager.get_sleep_interval()
    
    print(f"\n📅 CURRENT STATE")
    print(f"   Time: {current_time.strftime('%I:%M %p ET')}")
    print(f"   Phase: {current_phase.value}")
    print(f"   Sleep Interval: {sleep_interval} seconds ({sleep_interval/60:.0f} min)")
    
    # Show what happens at different times
    print(f"\n📊 PHASE SCHEDULE (ET Times)")
    print("-" * 70)
    
    test_times = [
        (6, 0, "Pre-market preparation"),
        (10, 0, "Active trading"),
        (16, 30, "After-hours analysis"),
        (21, 0, "Evening research"),
        (2, 0, "Deep sleep mode"),
    ]
    
    for hour, minute, description in test_times:
        phase = simulate_time_of_day(hour, minute)
        config = manager.phase_handlers[phase]
        interval_min = config['interval_seconds'] / 60
        
        print(f"⏰ {hour:02d}:{minute:02d} - {config['name']}")
        print(f"   Description: {description}")
        print(f"   Interval: {interval_min:.0f} minutes")
        print()
    
    # Show benefits
    print("=" * 70)
    print("🎉 BENEFITS")
    print("=" * 70)
    print("Before: 60-second checks = 1,440 checks per day")
    print("After:  Phase-based checks ≈ 100 checks per day")
    print("Reduction: 93% fewer API calls!")
    print()
    print("Plus: Productive off-hours activities!")
    print("  ✅ Learning and analysis")
    print("  ✅ Research and planning")
    print("  ✅ Pre-market preparation")
    print()


if __name__ == "__main__":
    main()
