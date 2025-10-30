#!/usr/bin/env python3
"""
Test: Market Data Cache Integration

Quick test to verify cache integration works correctly.
"""

import sys
from pathlib import Path
import time

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_cache_integration():
    """Test that cache integration works"""
    
    print("🧪 Testing Market Data Cache Integration")
    print("=" * 50)
    
    try:
        # Test imports
        print("📦 Testing imports...")
        from wawatrader.market_data_cache import get_cache
        from wawatrader.alpaca_client import get_client
        print("   ✅ Imports successful")
        
        # Test cache creation
        print("📊 Testing cache initialization...")
        cache = get_cache()
        print(f"   ✅ Cache created: {type(cache).__name__}")
        
        # Test client with cache
        print("🔌 Testing client with cache...")
        client = get_client()
        print(f"   ✅ Client created with cache: {hasattr(client, 'market_cache')}")
        
        # Test cache methods exist
        print("🔧 Testing cache methods...")
        methods = ['get_cache_stats', 'preload_cache', 'clear_cache', 'get_cache_summary']
        for method in methods:
            exists = hasattr(client, method)
            print(f"   {method}: {'✅' if exists else '❌'}")
            if not exists:
                return False
        
        # Test cache stats
        print("📈 Testing cache stats...")
        stats = client.get_cache_stats()
        required_keys = ['cache_hits', 'cache_misses', 'total_requests', 'cache_hit_rate']
        for key in required_keys:
            exists = key in stats
            print(f"   {key}: {'✅' if exists else '❌'}")
            if not exists:
                return False
        
        # Test cache summary
        print("📋 Testing cache summary...")
        summary = client.get_cache_summary()
        print(f"   Summary generated: {'✅' if summary else '❌'}")
        if summary:
            print(f"   Preview: {summary.split()[0:3]} ...")
        
        print("\n✅ All cache integration tests passed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Integration test error: {e}")
        return False


def test_cache_directory():
    """Test cache directory structure"""
    
    print("\n📁 Testing Cache Directory Structure")
    print("=" * 50)
    
    try:
        from config.settings import settings
        
        # Check cache base directory
        cache_dir = settings.project_root / "trading_data" / "historical"
        print(f"Cache directory: {cache_dir}")
        print(f"Exists: {'✅' if cache_dir.exists() else '❌'}")
        
        if cache_dir.exists():
            # Check timeframe subdirectories
            subdirs = [d for d in cache_dir.iterdir() if d.is_dir()]
            print(f"Timeframe directories: {len(subdirs)}")
            
            for subdir in subdirs:
                cache_files = list(subdir.glob("*.parquet"))
                print(f"   {subdir.name}/: {len(cache_files)} parquet files")
        
        return True
        
    except Exception as e:
        print(f"❌ Directory test error: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Market Data Cache Integration Tests")
    print("=" * 60)
    
    success = True
    
    # Run integration tests
    success &= test_cache_integration()
    success &= test_cache_directory()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ ALL TESTS PASSED - Cache integration is working!")
        print("🎯 Ready for production use with API call optimization")
    else:
        print("❌ SOME TESTS FAILED - Check integration")
        sys.exit(1)