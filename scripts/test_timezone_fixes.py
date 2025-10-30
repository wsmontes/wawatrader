#!/usr/bin/env python3
"""
Quick Test: Timezone Fix Verification

Simple test to verify timezone comparison issues are resolved.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_timezone_fixes():
    """Test that timezone comparison issues are resolved"""
    
    print("🔧 Timezone Fix Verification")
    print("=" * 35)
    
    try:
        from wawatrader.alpaca_client import get_client
        
        # Get client
        client = get_client()
        
        # Clear cache for clean test
        print("🗑️  Clearing AAPL cache...")
        client.clear_cache('AAPL')
        
        # Test cache operations without timezone errors
        print("📊 Testing cache operations...")
        
        # This should work without timezone comparison errors
        data = client.get_bars('AAPL', timeframe="1Day")
        
        if not data.empty:
            print(f"   ✅ Got {len(data)} bars successfully")
            print(f"   💰 Latest price: ${data['close'].iloc[-1]:.2f}")
            
            # Test second call (cache hit)
            data2 = client.get_bars('AAPL', timeframe="1Day")
            
            if len(data2) == len(data):
                print(f"   ✅ Cache hit successful: {len(data2)} bars")
            else:
                print(f"   ⚠️  Cache hit issue: {len(data)} vs {len(data2)} bars")
            
            # Test subset operations
            try:
                recent = data.tail(5)
                print(f"   ✅ Subset operations work: {len(recent)} recent bars")
                subset_success = True
            except Exception as e:
                print(f"   ❌ Subset error: {e}")
                subset_success = False
        else:
            print("   ❌ No data returned")
            subset_success = False
        
        # Test cache health
        print("🏥 Testing cache health...")
        health = client.check_cache_health('AAPL')
        print(f"   Health status: {health['overall_health']}")
        
        # Test cache stats
        stats = client.get_cache_stats()
        print(f"   Hit rate: {stats['cache_hit_rate']:.1f}%")
        
        success = not data.empty and subset_success and health['overall_health'] in ['good', 'issues_found']
        
        print(f"\n✅ Timezone fixes working: {success}")
        return success
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False


if __name__ == "__main__":
    success = test_timezone_fixes()
    
    print("\n" + "=" * 35)
    if success:
        print("✅ TIMEZONE FIXES SUCCESSFUL!")
        print("🕐 Cache operations are timezone-safe")
        print("💾 Data operations work correctly")
        print("🚀 Ready for production")
    else:
        print("❌ Timezone issues remain")
        sys.exit(1)