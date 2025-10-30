#!/usr/bin/env python3
"""
Simple Demo: Market Data Cache

Shows cache performance by fetching same data twice.
"""

import sys
from pathlib import Path
import time

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def main():
    """Simple cache demo"""
    
    print("🚀 Market Data Cache Demo")
    print("=" * 40)
    
    try:
        from wawatrader.alpaca_client import get_client
        
        # Get client (with cache)
        client = get_client()
        
        # Clear cache for fresh start
        client.clear_cache('AAPL')
        print("🗑️  Cleared AAPL cache")
        
        # First call - should hit API
        print("\n🧊 First call (cold cache - API required):")
        start = time.time()
        data1 = client.get_bars('AAPL', timeframe="1Day")
        time1 = time.time() - start
        
        print(f"   ✅ Got {len(data1)} bars in {time1:.3f}s")
        print(f"   💰 AAPL current price: ${data1['close'].iloc[-1]:.2f}")
        
        # Second call - should hit cache
        print("\n🔥 Second call (hot cache - should be faster):")
        start = time.time()
        data2 = client.get_bars('AAPL', timeframe="1Day")
        time2 = time.time() - start
        
        print(f"   ✅ Got {len(data2)} bars in {time2:.3f}s")
        print(f"   💰 AAPL current price: ${data2['close'].iloc[-1]:.2f}")
        
        # Show performance improvement
        improvement = (time1 - time2) / time1 * 100 if time1 > 0 else 0
        
        print(f"\n📊 Performance Comparison:")
        print(f"   Cold cache: {time1:.3f}s")
        print(f"   Hot cache:  {time2:.3f}s")
        print(f"   Speed up:   {improvement:.0f}%")
        
        # Show cache stats
        print(f"\n📈 Cache Statistics:")
        print(client.get_cache_summary())
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())