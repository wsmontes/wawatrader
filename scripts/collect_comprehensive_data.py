#!/usr/bin/env python3
"""
Comprehensive Historical Data Collection Script

Smart collection of maximum historical data while respecting API limits.
Designed to build comprehensive local data repository for WawaTrader.

Usage:
    python scripts/collect_comprehensive_data.py [options]

Options:
    --years YEARS          Maximum years of history (default: 5)
    --calls CALLS          API calls budget for session (default: 500)  
    --symbols FILE         Optional file with symbol list
    --timeframes TF        Comma-separated timeframes (default: 1Day)
    --status-only          Show status without collecting
    --continue             Continue from where last session stopped

Examples:
    # Default comprehensive collection (500 API calls, 5 years)
    python scripts/collect_comprehensive_data.py
    
    # Conservative collection (200 API calls, 2 years)
    python scripts/collect_comprehensive_data.py --calls 200 --years 2
    
    # Just show current status
    python scripts/collect_comprehensive_data.py --status-only
    
    # Continue large collection project  
    python scripts/collect_comprehensive_data.py --calls 1000 --continue

The script uses intelligent prioritization:
1. Major ETFs and stocks first (SPY, QQQ, AAPL, etc.)
2. Symbols with existing recent data  
3. High-volume symbols
4. Remaining discovered symbols

Rate limiting ensures API compliance (stays under 180 calls/minute).
Progress is saved and resumable across sessions.
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from wawatrader.data_collector import HistoricalDataCollector
from loguru import logger


def load_symbols_from_file(file_path: str) -> List[str]:
    """Load symbols from text file (one per line)."""
    try:
        with open(file_path, 'r') as f:
            symbols = []
            for line in f:
                line = line.strip().upper()
                if line and not line.startswith('#'):
                    symbols.append(line)
        logger.info(f"📁 Loaded {len(symbols)} symbols from {file_path}")
        return symbols
    except Exception as e:
        logger.error(f"❌ Could not load symbols from {file_path}: {e}")
        return []


def print_status_report(collector: HistoricalDataCollector):
    """Print comprehensive status report."""
    status = collector.get_comprehensive_status()
    
    print("\n" + "="*60)
    print("🏢 WAWATRADER DATA COLLECTION STATUS")
    print("="*60)
    
    print(f"\n📊 OVERVIEW")
    print(f"   Symbols Tracked: {status['total_symbols_tracked']:,}")
    print(f"   Total Bars Cached: {status['total_bars_cached']:,}")
    print(f"   Storage Size: {status['storage_size_mb']:.1f} MB")
    
    print(f"\n📁 FILES BY TIMEFRAME")
    for timeframe, count in status['files_by_timeframe'].items():
        print(f"   {timeframe:>8}: {count:,} files")
    
    print(f"\n✅ COMPLETION BY TIMEFRAME")  
    for timeframe, count in status['completed_by_timeframe'].items():
        if count > 0:
            print(f"   {timeframe:>8}: {count:,} symbols")
    
    if status['most_active_symbols']:
        print(f"\n🔥 MOST ACTIVE SYMBOLS")
        for i, (symbol, bars) in enumerate(status['most_active_symbols'][:5], 1):
            print(f"   {i:2}. {symbol:<6}: {bars:,} bars")
    
    gaps_exist = any(gaps for gaps in status['collection_gaps'].values())
    if gaps_exist:
        print(f"\n⚠️  COLLECTION GAPS")
        for timeframe, missing in status['collection_gaps'].items():
            if missing:
                print(f"   {timeframe}: {len(missing)} symbols missing")
                if len(missing) <= 10:
                    print(f"      Missing: {', '.join(missing)}")
                else:
                    print(f"      Missing: {', '.join(missing[:10])}... (+{len(missing)-10} more)")
    
    print(f"\n🌐 API STATUS")
    print(f"   Rate Limit: {status['api_rate_status']}")
    
    print("="*60)


def main():
    parser = argparse.ArgumentParser(
        description="Comprehensive Historical Data Collection for WawaTrader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Default: 500 calls, 5 years
  %(prog)s --calls 200 --years 2             # Conservative collection
  %(prog)s --status-only                     # Show status only
  %(prog)s --calls 1000 --timeframes 1Day,1Hour  # Multi-timeframe collection
        """
    )
    
    parser.add_argument(
        '--years', type=int, default=5,
        help='Maximum years of history per symbol (default: 5)'
    )
    
    parser.add_argument(
        '--calls', type=int, default=500,  
        help='API calls budget for this session (default: 500)'
    )
    
    parser.add_argument(
        '--symbols', type=str,
        help='File containing symbols to collect (one per line)'
    )
    
    parser.add_argument(
        '--timeframes', type=str, default='1Day',
        help='Comma-separated timeframes to collect (default: 1Day)'
    )
    
    parser.add_argument(
        '--status-only', action='store_true',
        help='Show collection status without collecting new data'
    )
    
    parser.add_argument(
        '--continue', dest='continue_collection', action='store_true',
        help='Continue from where last session stopped'
    )
    
    args = parser.parse_args()
    
    # Initialize collector
    logger.info("🚀 Initializing WawaTrader Comprehensive Data Collector")
    collector = HistoricalDataCollector()
    
    # Show status
    print_status_report(collector)
    
    if args.status_only:
        return
    
    # Parse timeframes
    timeframes = [tf.strip() for tf in args.timeframes.split(',')]
    valid_timeframes = {'1Min', '5Min', '15Min', '1Hour', '1Day'}
    timeframes = [tf for tf in timeframes if tf in valid_timeframes]
    
    if not timeframes:
        logger.error("❌ No valid timeframes specified")
        return
    
    # Load symbols if specified
    priority_symbols = None
    if args.symbols:
        priority_symbols = load_symbols_from_file(args.symbols)
        if not priority_symbols:
            logger.error("❌ No symbols loaded from file")
            return
    
    # Confirm collection
    print(f"\n🎯 COLLECTION PLAN")
    print(f"   API Budget: {args.calls} calls")
    print(f"   Max History: {args.years} years")
    print(f"   Timeframes: {', '.join(timeframes)}")
    
    if priority_symbols:
        print(f"   Symbols: {len(priority_symbols)} from file")
    else:
        print(f"   Symbols: Auto-discovered (prioritized)")
    
    print(f"\nEstimated time: {args.calls * 0.4:.0f}-{args.calls * 0.6:.0f} seconds")
    
    if not args.continue_collection:
        response = input(f"\nProceed with collection? [y/N]: ").strip().lower()
        if response not in ['y', 'yes']:
            print("❌ Collection cancelled")
            return
    
    # Start collection
    print(f"\n🚀 Starting comprehensive data collection...")
    start_time = datetime.now()
    
    try:
        stats = collector.collect_comprehensive_history(
            max_years=args.years,
            max_api_calls=args.calls,
            priority_symbols=priority_symbols,
            timeframes=timeframes
        )
        
        # Show results
        duration = (datetime.now() - start_time).total_seconds()
        
        print(f"\n🎉 COLLECTION COMPLETE!")
        print(f"   Duration: {duration:.1f} seconds")
        print(f"   Symbols Processed: {stats['symbols_processed']}")
        print(f"   Total Bars: {stats['total_bars_collected']:,}")
        print(f"   API Calls: {stats['api_calls_used']}/{args.calls}")
        print(f"   Efficiency: {stats['total_bars_collected']/max(stats['api_calls_used'], 1):.1f} bars/call")
        
        if stats['errors'] > 0:
            print(f"   Errors: {stats['errors']}")
        
        for tf in timeframes:
            completed = stats['timeframes_completed'][tf]
            print(f"   {tf} Completed: {completed} symbols")
        
        # Show updated status
        print(f"\n📊 UPDATED STATUS")
        print_status_report(collector)
        
    except KeyboardInterrupt:
        print(f"\n🛑 Collection interrupted by user")
        print(f"   Progress saved. Use --continue to resume.")
        
    except Exception as e:
        logger.error(f"❌ Collection failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()