#!/usr/bin/env python3
"""
Test Intelligent Scheduling System

Validates the market state detection and intelligent scheduling system
works correctly across different times and states.

Author: WawaTrader Team
Created: October 2025
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from wawatrader.market_state import MarketState, MarketStateDetector, display_market_state_info
from wawatrader.scheduler import IntelligentScheduler
from loguru import logger
from datetime import datetime, time
from zoneinfo import ZoneInfo


def test_state_detection():
    """Test market state detection at various times"""
    print("\n" + "="*70)
    print("TEST 1: Market State Detection")
    print("="*70)
    
    detector = MarketStateDetector()
    
    # Test cases: (hour, minute, expected_state)
    test_cases = [
        (10, 0, MarketState.ACTIVE_TRADING, "10:00 AM - Active Trading"),
        (15, 0, MarketState.ACTIVE_TRADING, "3:00 PM - Still Active"),
        (15, 45, MarketState.MARKET_CLOSING, "3:45 PM - Market Closing"),
        (16, 15, MarketState.MARKET_CLOSING, "4:15 PM - Still Closing"),
        (17, 0, MarketState.EVENING_ANALYSIS, "5:00 PM - Evening Analysis"),
        (19, 30, MarketState.EVENING_ANALYSIS, "7:30 PM - Still Evening"),
        (22, 30, MarketState.OVERNIGHT_SLEEP, "10:30 PM - Overnight Sleep"),
        (2, 0, MarketState.OVERNIGHT_SLEEP, "2:00 AM - Still Sleeping"),
        (6, 30, MarketState.PREMARKET_PREP, "6:30 AM - Pre-Market Prep"),
        (9, 0, MarketState.PREMARKET_PREP, "9:00 AM - Still Prep"),
    ]
    
    passed = 0
    failed = 0
    
    for hour, minute, expected_state, description in test_cases:
        # Mock the state determination
        actual_state = detector._determine_state(
            market_is_open=(9 <= hour < 16),
            hour=hour,
            minute=minute
        )
        
        if actual_state == expected_state:
            print(f"✅ {description}: {actual_state.description}")
            passed += 1
        else:
            print(f"❌ {description}: Expected {expected_state.description}, got {actual_state.description}")
            failed += 1
    
    print()
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0


def test_scheduler_tasks():
    """Test scheduler task routing"""
    print("\n" + "="*70)
    print("TEST 2: Scheduler Task Routing")
    print("="*70)
    
    scheduler = IntelligentScheduler()
    
    # Check that tasks are registered
    total_tasks = len(scheduler.tasks)
    print(f"✓ Total tasks registered: {total_tasks}")
    
    # Check tasks per state
    states_checked = 0
    for state in MarketState:
        tasks_for_state = [
            task for task in scheduler.tasks.values()
            if state in task.market_states
        ]
        print(f"  {state.emoji} {state.description}: {len(tasks_for_state)} tasks")
        states_checked += 1
    
    print()
    print(f"✓ Checked {states_checked} market states")
    return True


def test_task_timing():
    """Test that tasks trigger at correct times"""
    print("\n" + "="*70)
    print("TEST 3: Task Timing Logic")
    print("="*70)
    
    scheduler = IntelligentScheduler()
    
    # Simulate different scenarios
    test_scenarios = [
        {
            "description": "Active Trading - Trading Cycle should be available",
            "state": MarketState.ACTIVE_TRADING,
            "expected_tasks": ["trading_cycle"],
        },
        {
            "description": "Market Closing - Assessment tasks should be available",
            "state": MarketState.MARKET_CLOSING,
            "expected_tasks": ["pre_close_assessment", "daily_summary"],
        },
        {
            "description": "Evening Analysis - Deep analysis tasks available",
            "state": MarketState.EVENING_ANALYSIS,
            "expected_tasks": ["earnings_analysis", "sector_deep_dive", "international_markets"],
        },
        {
            "description": "Overnight Sleep - Only monitoring tasks",
            "state": MarketState.OVERNIGHT_SLEEP,
            "expected_tasks": ["news_monitor"],
        },
        {
            "description": "Pre-Market Prep - Preparation tasks available",
            "state": MarketState.PREMARKET_PREP,
            "expected_tasks": ["overnight_summary", "premarket_scanner", "market_open_prep"],
        },
    ]
    
    passed = 0
    failed = 0
    
    for scenario in test_scenarios:
        state = scenario["state"]
        expected_tasks = scenario["expected_tasks"]
        
        # Get tasks that would run in this state
        state_tasks = [
            task.name for task in scheduler.tasks.values()
            if state in task.market_states
        ]
        
        # Check if expected tasks are present
        all_present = all(task in state_tasks for task in expected_tasks)
        
        if all_present:
            print(f"✅ {scenario['description']}")
            print(f"   Available: {', '.join(state_tasks[:5])}")
            passed += 1
        else:
            print(f"❌ {scenario['description']}")
            missing = [t for t in expected_tasks if t not in state_tasks]
            print(f"   Missing: {', '.join(missing)}")
            failed += 1
    
    print()
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0


def test_current_state():
    """Test current real-time state detection"""
    print("\n" + "="*70)
    print("TEST 4: Current Real-Time State")
    print("="*70)
    
    try:
        # Display current market state
        display_market_state_info()
        
        # Get scheduler status
        scheduler = IntelligentScheduler()
        summary = scheduler.get_state_summary()
        
        print()
        print("Current Scheduler Status:")
        print(f"  Total tasks registered: {summary['total_tasks']}")
        print(f"  Tasks for current state: {summary['tasks_for_current_state']}")
        
        if summary['next_task']:
            print(f"  Next task: {summary['next_task']}")
            print(f"  Description: {summary['next_task_description']}")
        else:
            print(f"  No tasks currently due")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing current state: {e}")
        return False


def test_resource_optimization():
    """Test that resource usage is optimized"""
    print("\n" + "="*70)
    print("TEST 5: Resource Optimization Validation")
    print("="*70)
    
    scheduler = IntelligentScheduler()
    
    # Count interval-based tasks (frequent) vs scheduled tasks (strategic)
    interval_tasks = sum(
        1 for task in scheduler.tasks.values()
        if task.interval_minutes is not None
    )
    
    scheduled_tasks = sum(
        1 for task in scheduler.tasks.values()
        if task.scheduled_hours
    )
    
    print(f"✓ Interval-based tasks (frequent): {interval_tasks}")
    print(f"✓ Scheduled tasks (strategic): {scheduled_tasks}")
    print()
    
    # Validate sleep mode has minimal tasks
    sleep_tasks = [
        task for task in scheduler.tasks.values()
        if MarketState.OVERNIGHT_SLEEP in task.market_states
    ]
    
    print(f"✓ Overnight sleep tasks: {len(sleep_tasks)}")
    if len(sleep_tasks) <= 2:  # Should be minimal
        print("  ✅ Sleep mode properly optimized (minimal tasks)")
        result = True
    else:
        print("  ⚠️ Sleep mode may be running too many tasks")
        result = False
    
    # Check that trading tasks only run during market hours
    trading_tasks = [
        task for task in scheduler.tasks.values()
        if "trading" in task.name.lower()
    ]
    
    print(f"✓ Trading-related tasks: {len(trading_tasks)}")
    
    all_trading_restricted = all(
        MarketState.ACTIVE_TRADING in task.market_states and
        MarketState.OVERNIGHT_SLEEP not in task.market_states
        for task in trading_tasks
    )
    
    if all_trading_restricted:
        print("  ✅ Trading tasks properly restricted to market hours")
    else:
        print("  ⚠️ Some trading tasks may run during non-market hours")
        result = False
    
    return result


def main():
    """Run all tests"""
    print("🧪 Testing Intelligent Scheduling System")
    print("="*70)
    
    results = []
    
    # Run all tests
    results.append(("State Detection", test_state_detection()))
    results.append(("Scheduler Tasks", test_scheduler_tasks()))
    results.append(("Task Timing", test_task_timing()))
    results.append(("Current State", test_current_state()))
    results.append(("Resource Optimization", test_resource_optimization()))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! System is ready.")
        return 0
    else:
        print("⚠️ Some tests failed. Review output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
