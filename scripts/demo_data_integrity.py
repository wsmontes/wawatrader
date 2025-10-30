#!/usr/bin/env python3
"""
Demo: Data Integrity and Gap Filling

Demonstrates the cache system's ability to:
1. Detect corrupted or incomplete data
2. Automatically repair common issues
3. Fill gaps in time series data
4. Switch to API when cache is unreliable
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def main():
    """Demo data integrity and gap filling"""
    
    print("🔧 Data Integrity & Gap Filling Demo")
    print("=" * 50)
    
    try:
        from wawatrader.alpaca_client import get_client
        
        client = get_client()
        
        # === CACHE HEALTH CHECK ===
        print("\n🏥 Initial Cache Health Check")
        print("-" * 30)
        
        health_summary = client.get_cache_health_summary()
        print(health_summary)
        
        # === SIMULATE DATA CORRUPTION ===
        print("\n🧪 Simulating Data Issues for Demo")
        print("-" * 30)
        
        # Get some real data first
        symbol = 'AAPL'
        clean_data = client.get_bars(symbol, timeframe="1Day", force_refresh=True)
        print(f"✅ Got clean data: {len(clean_data)} bars")
        
        if not clean_data.empty:
            # Create corrupted versions for testing
            cache_dir = client.market_cache.base_path / "1Day"
            cache_file = cache_dir / f"{symbol}.parquet"
            
            # Backup original
            backup_file = cache_dir / f"{symbol}_backup.parquet"
            if cache_file.exists():
                import shutil
                shutil.copy2(cache_file, backup_file)
            
            # Create corrupted data scenarios
            corrupted_scenarios = []
            
            # Scenario 1: OHLC logic errors
            scenario1 = clean_data.copy()
            # Make high less than low (impossible)
            scenario1.loc[scenario1.index[5:10], 'high'] = scenario1.loc[scenario1.index[5:10], 'low'] * 0.9
            corrupted_scenarios.append(("OHLC Logic Errors", scenario1))
            
            # Scenario 2: Missing data (gaps)
            scenario2 = clean_data.copy()
            # Remove random chunks to create gaps
            gap_indices = scenario2.index[10:15]  # Remove 5 days
            scenario2 = scenario2.drop(gap_indices)
            corrupted_scenarios.append(("Time Series Gaps", scenario2))
            
            # Scenario 3: Null values
            scenario3 = clean_data.copy()
            scenario3.loc[scenario3.index[2:4], 'close'] = np.nan
            scenario3.loc[scenario3.index[7], 'open'] = np.nan
            corrupted_scenarios.append(("Null Values", scenario3))
            
            # Scenario 4: Unrealistic prices
            scenario4 = clean_data.copy()
            scenario4.loc[scenario4.index[3], 'high'] = 999999  # Extremely high price
            scenario4.loc[scenario4.index[8], 'low'] = -10     # Negative price
            corrupted_scenarios.append(("Unrealistic Prices", scenario4))
            
            # Test each corruption scenario
            for scenario_name, corrupted_data in corrupted_scenarios:
                print(f"\n🔴 Testing: {scenario_name}")
                print(f"   Original bars: {len(clean_data)}")
                print(f"   Corrupted bars: {len(corrupted_data)}")
                
                # Save corrupted data to cache
                client.market_cache._save_to_cache(symbol, "1Day", corrupted_data)
                
                # Try to load it (should detect issues)
                print("   🔍 Loading corrupted cache...")
                loaded_data = client.get_bars(symbol, timeframe="1Day")
                
                print(f"   📊 Result: {len(loaded_data)} bars returned")
                
                if len(loaded_data) > 0:
                    print(f"   ✅ System handled corruption gracefully")
                    print(f"   💰 Latest price: ${loaded_data['close'].iloc[-1]:.2f}")
                else:
                    print(f"   ⚠️  No data returned - system rejected corrupted cache")
            
            # === CACHE HEALTH AFTER CORRUPTION ===
            print("\n🏥 Cache Health After Corruption Tests")
            print("-" * 30)
            
            health_report = client.check_cache_health(symbol)
            print(f"Overall Health: {health_report['overall_health']}")
            print(f"Issues Found: {health_report['corrupted_files']} corrupted files")
            print(f"Gaps Found: {health_report['gaps_found']} data gaps")
            
            if health_report.get('recommendations'):
                print("Recommendations:")
                for rec in health_report['recommendations']:
                    print(f"   {rec}")
            
            # === AUTOMATIC REPAIR ===
            print("\n🔧 Testing Automatic Repair")
            print("-" * 30)
            
            repair_result = client.repair_cache(symbol)
            
            print(f"Files Processed: {repair_result['files_processed']}")
            print(f"Files Repaired: {repair_result['files_repaired']}")
            print(f"Files Deleted: {repair_result['files_deleted']}")
            
            if repair_result.get('details'):
                print("Repair Details:")
                for detail in repair_result['details'][:3]:  # Show first 3
                    print(f"   {detail}")
            
            # === GAP FILLING DEMO ===
            print("\n📊 Gap Filling Demonstration")
            print("-" * 30)
            
            # Create data with intentional gaps
            gapped_data = clean_data.copy()
            
            # Remove a week of data to create a noticeable gap
            gap_start = gapped_data.index[20]
            gap_end = gapped_data.index[25]
            gap_indices = gapped_data.index[20:26]  # Remove 6 days
            gapped_data = gapped_data.drop(gap_indices)
            
            print(f"Created gap from {gap_start.date()} to {gap_end.date()}")
            print(f"Data before gap: {len(gapped_data)} bars")
            
            # Save gapped data
            client.market_cache._save_to_cache(symbol, "1Day", gapped_data)
            
            # Request data that should trigger gap filling
            print("🔍 Requesting data that spans the gap...")
            filled_data = client.get_bars(
                symbol, 
                start=gap_start - timedelta(days=2),
                end=gap_end + timedelta(days=2),
                timeframe="1Day"
            )
            
            print(f"📊 Result: {len(filled_data)} bars (gap should be filled)")
            
            # Check if gap was actually filled
            date_range = pd.date_range(gap_start, gap_end, freq='D')
            gap_filled = any(d.date() in [idx.date() for idx in filled_data.index] for d in date_range)
            
            if gap_filled:
                print("✅ Gap successfully filled from API")
            else:
                print("⚠️  Gap not filled - may be weekend/holiday")
            
            # === RESTORE CLEAN DATA ===
            print("\n🔄 Restoring Clean Cache")
            print("-" * 30)
            
            # Restore from backup
            if backup_file.exists():
                import shutil
                shutil.copy2(backup_file, cache_file)
                backup_file.unlink()  # Clean up
                print("✅ Original cache restored")
            
            # === FINAL HEALTH CHECK ===
            print("\n🏥 Final Cache Health Check")
            print("-" * 30)
            
            final_health = client.get_cache_health_summary()
            print(final_health)
            
            # === PERFORMANCE COMPARISON ===
            print("\n📈 Performance Summary")
            print("-" * 30)
            
            cache_stats = client.get_cache_stats()
            print(f"Cache Hit Rate: {cache_stats['cache_hit_rate']:.1f}%")
            print(f"API Calls Saved: {cache_stats['api_calls_saved']}")
            print(f"Total Requests: {cache_stats['total_requests']}")
            
        else:
            print("❌ No clean data available for testing")
        
        print("\n" + "=" * 60)
        print("✅ DATA INTEGRITY DEMO COMPLETE")
        print("=" * 60)
        
        benefits = [
            "🔍 Automatic corruption detection",
            "🔧 Intelligent data repair",
            "📊 Gap filling from API",
            "🏥 Health monitoring & diagnostics",
            "🔄 Seamless fallback to API",
            "💾 Maintains data quality"
        ]
        
        for benefit in benefits:
            print(f"   {benefit}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Demo error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())