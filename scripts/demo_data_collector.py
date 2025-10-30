"""
Demo: Historical Data Collector

Tests the new HistoricalDataCollector functionality:
1. Small backfill (last 7 days for testing)
2. Check storage stats
3. Test offline data retrieval
4. Check data availability
"""

from datetime import datetime, timedelta
from wawatrader.data_collector import HistoricalDataCollector
from loguru import logger


def main():
    print("╔════════════════════════════════════════════════════════════╗")
    print("║  📊 Historical Data Collector Demo                        ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()
    
    # Initialize collector
    collector = HistoricalDataCollector()
    print()
    
    # Test 1: Small backfill (last 7 days, limited symbols)
    print("━" * 60)
    print("TEST 1: Small Backfill (Last 7 Days)")
    print("━" * 60)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    print(f"📅 Date range: {start_date.date()} to {end_date.date()}")
    print(f"📈 Symbols: SPY, AAPL")
    print(f"⏰ Timeframes: 1Day only (faster for demo)")
    print()
    
    input("Press Enter to start backfill (takes ~30 seconds)...")
    
    results = collector.backfill_historical_data(
        symbols=['SPY', 'AAPL'],
        start_date=start_date,
        end_date=end_date,
        timeframes=['1Day']  # Just daily for speed
    )
    
    print()
    print(f"✅ Backfill complete!")
    print(f"   Files created: {results['files_created']}")
    print(f"   Bars collected: {results['total_bars_collected']:,}")
    print(f"   Duration: {results['duration']:.1f}s")
    print()
    
    # Test 2: Storage stats
    print("━" * 60)
    print("TEST 2: Storage Statistics")
    print("━" * 60)
    
    stats = collector.get_storage_stats()
    
    print(f"📊 Total files: {stats['total_files']}")
    print(f"💾 Total size: {stats['total_size_mb']:.2f} MB")
    print(f"📈 Symbols: {', '.join(stats['symbols'])}")
    print(f"⏰ Timeframes:")
    for tf, count in stats['timeframes'].items():
        if count > 0:
            print(f"   • {tf}: {count} files")
    
    if stats['oldest_data'] and stats['newest_data']:
        print(f"📅 Data range: {stats['oldest_data'].date()} to {stats['newest_data'].date()}")
    print()
    
    # Test 3: Offline data retrieval
    print("━" * 60)
    print("TEST 3: Offline Data Retrieval")
    print("━" * 60)
    
    print("🔍 Retrieving AAPL data from local storage (no API call)...")
    
    bars = collector.get_offline_data(
        symbol='AAPL',
        start_date=start_date,
        end_date=end_date,
        timeframe='1Day'
    )
    
    if not bars.empty:
        print(f"✅ Retrieved {len(bars)} bars")
        print(f"\n📊 Sample data:")
        print(bars[['timestamp', 'open', 'high', 'low', 'close', 'volume']].head())
        print()
        print(f"💰 Price range: ${bars['low'].min():.2f} - ${bars['high'].max():.2f}")
        print(f"📊 Avg volume: {bars['volume'].mean():,.0f}")
    else:
        print("❌ No data retrieved")
    print()
    
    # Test 4: Check availability
    print("━" * 60)
    print("TEST 4: Data Availability Check")
    print("━" * 60)
    
    # Check available data
    avail = collector.check_data_availability(
        symbol='AAPL',
        start_date=start_date,
        end_date=end_date,
        timeframe='1Day'
    )
    
    print(f"Symbol: AAPL")
    print(f"File exists: {avail['file_exists']}")
    print(f"Available: {avail['available']}")
    print(f"Coverage: {avail['coverage']*100:.0f}%")
    print(f"Message: {avail['message']}")
    print()
    
    # Check unavailable data (1Min - not collected in demo)
    avail_1min = collector.check_data_availability(
        symbol='AAPL',
        start_date=start_date,
        end_date=end_date,
        timeframe='1Min'
    )
    
    print(f"Symbol: AAPL (1Min timeframe)")
    print(f"File exists: {avail_1min['file_exists']}")
    print(f"Message: {avail_1min['message']}")
    print()
    
    # Summary
    print("═" * 60)
    print("✅ DEMO COMPLETE")
    print("═" * 60)
    print()
    print("📂 Data stored in: trading_data/historical/")
    print()
    print("🔧 Next steps:")
    print("   1. Run full backfill: collector.backfill_historical_data()")
    print("      • symbols=['SPY', 'QQQ', 'AAPL', 'MSFT', 'GOOGL']")
    print("      • start_date=datetime.now() - timedelta(days=730)  # 2 years")
    print("      • timeframes=['1Min', '5Min', '15Min', '1Hour', '1Day']")
    print()
    print("   2. Set up daily cron job at 6am:")
    print("      0 6 * * 1-5 cd /path/to/wawatrader && ...")
    print()
    print("   3. Integrate with OvernightLearner for offline validation")
    print()


if __name__ == "__main__":
    main()
