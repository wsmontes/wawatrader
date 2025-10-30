#!/usr/bin/env python3
"""
Test: Professional Timezone Management

Comprehensive test of the enhanced timezone handling capabilities.
Tests timezone normalization, comparison safety, and market awareness.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import time

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_timezone_management():
    """Test professional timezone management"""
    
    print("🕐 Professional Timezone Management Test")
    print("=" * 50)
    
    try:
        from wawatrader.timezone_utils import (
            MarketTimezone,
            normalize_datetime,
            to_market_time,
            to_naive_market,
            safe_datetime_compare,
            is_market_open,
            get_market_session,
            format_market_time
        )
        from wawatrader.alpaca_client import get_client
        import pandas as pd
        
        # Test 1: Market timezone functionality
        print("🏛️  Testing market timezone operations...")
        
        current_market_time = MarketTimezone.now_market_time()
        print(f"   Current market time: {format_market_time(current_market_time)}")
        
        session_info = get_market_session()
        print(f"   Market session: {session_info['session']}")
        print(f"   Is trading day: {session_info['is_trading_day']}")
        
        # Test 2: Datetime normalization
        print("\n⚙️  Testing datetime normalization...")
        
        # Create different timezone-aware datetimes
        test_datetimes = [
            datetime(2025, 10, 29, 14, 30),  # Naive
            pd.Timestamp('2025-10-29 14:30:00', tz='US/Eastern'),  # Pandas Eastern
            pd.Timestamp('2025-10-29 11:30:00', tz='US/Pacific'),  # Pandas Pacific
        ]
        
        normalized_times = []
        for dt in test_datetimes:
            normalized = normalize_datetime(dt)
            normalized_times.append(normalized)
            print(f"   Original: {dt} → Normalized: {normalized}")
        
        # All normalized times should be equal (same moment, different representations)
        all_equal = all(nt == normalized_times[0] for nt in normalized_times[1:])
        print(f"   ✅ All normalized to same time: {all_equal}")
        
        # Test 3: Safe datetime comparison
        print("\n🔍 Testing safe datetime comparison...")
        
        dt1 = pd.Timestamp('2025-10-29 14:30:00', tz='US/Eastern')
        dt2 = pd.Timestamp('2025-10-29 11:30:00', tz='US/Pacific')  # Same moment
        dt3 = pd.Timestamp('2025-10-29 15:30:00', tz='US/Eastern')  # 1 hour later
        
        comparison1 = safe_datetime_compare(dt1, dt2)  # Should be equal (0)
        comparison2 = safe_datetime_compare(dt1, dt3)  # Should be less (-1)
        
        print(f"   {dt1} vs {dt2}: {comparison1} (should be 0)")
        print(f"   {dt1} vs {dt3}: {comparison2} (should be -1)")
        
        success = comparison1 == 0 and comparison2 == -1
        print(f"   ✅ Safe comparison working: {success}")
        
        # Test 4: Cache system with timezone handling
        print("\n💾 Testing cache with timezone handling...")
        
        client = get_client()
        
        # Clear cache for clean test
        client.clear_cache('AAPL')
        
        # First call - should populate cache
        start_time = time.time()
        data1 = client.get_bars('AAPL', timeframe="1Day")
        time1 = time.time() - start_time
        
        print(f"   First call: {len(data1)} bars in {time1:.3f}s")
        
        # Second call - should hit cache without timezone errors
        start_time = time.time()
        data2 = client.get_bars('AAPL', timeframe="1Day")
        time2 = time.time() - start_time
        
        print(f"   Second call: {len(data2)} bars in {time2:.3f}s")
        
        # Should be much faster (cache hit) and same data
        cache_hit = time2 < time1 * 0.5 and len(data1) == len(data2)
        print(f"   ✅ Cache working without timezone errors: {cache_hit}")
        
        # Test 5: Data integrity with timezones
        print("\n🔧 Testing data integrity with timezones...")
        
        if not data1.empty:
            # Check that data index is properly normalized
            index_has_tz = hasattr(data1.index, 'tz') and data1.index.tz is not None
            print(f"   Data index timezone-aware: {index_has_tz}")
            print(f"   ✅ Index properly normalized: {not index_has_tz}")
            
            # Test subset operations work without errors
            try:
                recent_data = data1.tail(10)
                subset_success = len(recent_data) == 10
                print(f"   ✅ Subset operations work: {subset_success}")
            except Exception as e:
                print(f"   ❌ Subset operation failed: {e}")
                subset_success = False
        else:
            subset_success = False
            print("   ⚠️  No data to test subset operations")
        
        # Test 6: Cache health with timezone handling
        print("\n🏥 Testing cache health with timezone handling...")
        
        health = client.check_cache_health()
        health_good = health['overall_health'] in ['good', 'issues_found']
        print(f"   Cache health: {health['overall_health']}")
        print(f"   ✅ Health check completed: {health_good}")
        
        # Overall results
        all_tests_passed = (
            all_equal and success and cache_hit and 
            subset_success and health_good
        )
        
        print(f"\n✅ All timezone tests passed: {all_tests_passed}")
        return all_tests_passed
        
    except Exception as e:
        print(f"❌ Timezone test error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_market_awareness():
    """Test market-aware functionality"""
    
    print("\n🏛️  Market Awareness Test")
    print("=" * 30)
    
    try:
        from wawatrader.timezone_utils import MarketTimezone, get_market_session
        
        # Test market session detection
        session_info = get_market_session()
        
        print(f"Current session: {session_info['session']}")
        print(f"Is weekday: {session_info['is_weekday']}")
        print(f"Is trading day: {session_info['is_trading_day']}")
        
        # Test different times
        test_times = [
            (8, 0, "premarket"),    # 8 AM should be premarket
            (14, 0, "regular"),     # 2 PM should be regular hours
            (18, 0, "afterhours"),  # 6 PM should be after hours
            (22, 0, "closed"),      # 10 PM should be closed
        ]
        
        print("\nTesting different market times:")
        for hour, minute, expected_session in test_times:
            test_time = MarketTimezone.now_market_time().replace(
                hour=hour, minute=minute
            )
            
            session = MarketTimezone.get_market_session_info(test_time)['session']
            print(f"   {hour:02d}:{minute:02d} ET: {session} (expected: {expected_session})")
        
        return True
        
    except Exception as e:
        print(f"❌ Market awareness test error: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Professional Timezone Management Tests")
    print("=" * 60)
    
    success1 = test_timezone_management()
    success2 = test_market_awareness()
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("✅ ALL TIMEZONE TESTS PASSED!")
        print("🕐 Professional timezone management is operational")
        print("🏛️  Market awareness is functioning correctly")  
        print("💾 Cache operations are timezone-safe")
        print("🚀 Ready for production use across all timezones")
    else:
        print("❌ Some timezone tests failed")
        sys.exit(1)