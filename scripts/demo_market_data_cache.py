#!/usr/bin/env python3
"""
Demo: Market Data Cache Optimization

Demonstrates the API call reduction achieved through intelligent caching.
Shows before/after comparison and cache performance metrics.

Usage:
    python scripts/demo_market_data_cache.py
"""

import sys
from pathlib import Path
import time
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from wawatrader.alpaca_client import get_client
from config.settings import settings
from loguru import logger


def main():
    """Demo market data cache optimization"""
    
    print("🚀 Market Data Cache Optimization Demo")
    print("=" * 60)
    
    try:
        # Initialize client (with cache)
        client = get_client()
        
        # Test symbols
        test_symbols = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'TSLA']
        timeframe = "1Day"
        
        print(f"📊 Testing cache with symbols: {test_symbols}")
        print(f"📅 Timeframe: {timeframe}")
        
        # Clear cache to start fresh
        client.clear_cache()
        print("\n🗑️  Cache cleared for fresh demo")
        
        # ===== FIRST RUN: COLD CACHE =====
        print("\n" + "="*50)
        print("🧊 COLD CACHE TEST (API calls required)")
        print("="*50)
        
        start_time = time.time()
        cold_cache_data = {}
        
        for symbol in test_symbols:
            symbol_start = time.time()
            data = client.get_bars(symbol, timeframe=timeframe)
            symbol_time = time.time() - symbol_start
            
            cold_cache_data[symbol] = {
                'rows': len(data),
                'time': symbol_time,
                'latest_price': data['close'].iloc[-1] if not data.empty else 0
            }
            
            print(f"   {symbol}: {len(data)} bars in {symbol_time:.2f}s (${data['close'].iloc[-1]:.2f})")
        
        cold_total_time = time.time() - start_time
        cold_stats = client.get_cache_stats()
        
        print(f"\n⏱️  Cold cache total time: {cold_total_time:.2f}s")
        print(f"📈 Cache stats after cold run:")
        print(f"   Requests: {cold_stats['total_requests']}")
        print(f"   Cache hits: {cold_stats['cache_hits']}")
        print(f"   API calls: {cold_stats['cache_misses']}")
        
        # ===== SECOND RUN: HOT CACHE =====
        print("\n" + "="*50)
        print("🔥 HOT CACHE TEST (cache hits expected)")
        print("="*50)
        
        start_time = time.time()
        hot_cache_data = {}
        
        for symbol in test_symbols:
            symbol_start = time.time()
            data = client.get_bars(symbol, timeframe=timeframe)
            symbol_time = time.time() - symbol_start
            
            hot_cache_data[symbol] = {
                'rows': len(data),
                'time': symbol_time,
                'latest_price': data['close'].iloc[-1] if not data.empty else 0
            }
            
            print(f"   {symbol}: {len(data)} bars in {symbol_time:.2f}s (${data['close'].iloc[-1]:.2f}) ✅")
        
        hot_total_time = time.time() - start_time
        hot_stats = client.get_cache_stats()
        
        print(f"\n⏱️  Hot cache total time: {hot_total_time:.2f}s")
        
        # ===== PERFORMANCE COMPARISON =====
        print("\n" + "="*60)
        print("📊 PERFORMANCE COMPARISON")
        print("="*60)
        
        speed_improvement = (cold_total_time - hot_total_time) / cold_total_time * 100
        
        print(f"Cold Cache (API calls):  {cold_total_time:.2f}s")
        print(f"Hot Cache (from disk):   {hot_total_time:.2f}s")
        print(f"Speed Improvement:       {speed_improvement:.1f}%")
        print(f"Time Saved:              {cold_total_time - hot_total_time:.2f}s")
        
        # Cache statistics
        print("\n📈 Final Cache Statistics:")
        print(client.get_cache_summary())
        
        # ===== DATA RANGE TEST =====
        print("\n" + "="*50)
        print("📅 DATE RANGE CACHE TEST")
        print("="*50)
        
        # Test different date ranges on same symbol
        test_symbol = 'AAPL'
        ranges = [
            ("Last 30 days", datetime.now() - timedelta(days=30), datetime.now()),
            ("Last 60 days", datetime.now() - timedelta(days=60), datetime.now()),
            ("Last 90 days", datetime.now() - timedelta(days=90), datetime.now()),
        ]
        
        for range_name, start_date, end_date in ranges:
            range_start = time.time()
            data = client.get_bars(
                test_symbol, 
                start=start_date, 
                end=end_date, 
                timeframe=timeframe
            )
            range_time = time.time() - range_start
            
            print(f"   {range_name}: {len(data)} bars in {range_time:.3f}s")
        
        # ===== CACHE REFRESH TEST =====
        print("\n" + "="*50)
        print("🔄 CACHE REFRESH TEST")
        print("="*50)
        
        refresh_symbol = 'MSFT'
        
        # Regular cache hit
        normal_start = time.time()
        normal_data = client.get_bars(refresh_symbol, timeframe=timeframe)
        normal_time = time.time() - normal_start
        
        # Force refresh
        refresh_start = time.time()
        refresh_data = client.get_bars(refresh_symbol, timeframe=timeframe, force_refresh=True)
        refresh_time = time.time() - refresh_start
        
        print(f"   Cache hit:     {len(normal_data)} bars in {normal_time:.3f}s")
        print(f"   Force refresh: {len(refresh_data)} bars in {refresh_time:.3f}s")
        print(f"   Refresh overhead: {refresh_time - normal_time:.3f}s")
        
        # ===== CACHE FILE INSPECTION =====
        print("\n" + "="*50)
        print("📁 CACHE FILE INSPECTION")
        print("="*50)
        
        cache_dir = settings.project_root / "trading_data" / "historical"
        
        if cache_dir.exists():
            timeframe_dirs = [d for d in cache_dir.iterdir() if d.is_dir()]
            
            for tf_dir in timeframe_dirs:
                cache_files = list(tf_dir.glob("*.parquet"))
                total_size = sum(f.stat().st_size for f in cache_files)
                
                print(f"   {tf_dir.name}/: {len(cache_files)} files, {total_size/1024:.1f} KB")
                
                # Show sample files
                for cache_file in cache_files[:3]:
                    file_size = cache_file.stat().st_size
                    print(f"      {cache_file.name}: {file_size/1024:.1f} KB")
                
                if len(cache_files) > 3:
                    print(f"      ... and {len(cache_files)-3} more files")
        
        # ===== SUMMARY =====
        print("\n" + "="*60)
        print("✅ DEMO COMPLETE - KEY BENEFITS")
        print("="*60)
        
        final_stats = client.get_cache_stats()
        
        benefits = [
            f"🚀 Speed: {speed_improvement:.0f}% faster on cache hits",
            f"💰 API Reduction: {final_stats['api_reduction_pct']:.0f}% fewer API calls",
            f"⚡ Efficiency: {final_stats['cache_hit_rate']:.0f}% cache hit rate",
            f"💾 Storage: Parquet files provide compact, fast access",
            f"🕐 Time Saved: {cold_total_time - hot_total_time:.2f}s per batch"
        ]
        
        for benefit in benefits:
            print(f"   {benefit}")
        
        print(f"\n🎯 Result: Cache system reduces API calls by up to {final_stats['api_reduction_pct']:.0f}%")
        print("   This saves time, reduces rate limiting, and improves reliability!")
        
    except Exception as e:
        logger.error(f"❌ Demo error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())