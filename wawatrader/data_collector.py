"""
Historical Data Collector for WawaTrader

Provides systematic historical data collection and local storage for offline simulation.
Enables the learning system to access years of historical data for validation and backtesting.

Key Features:
- Backfill historical data from Alpaca (1Min to 1Day timeframes)
- Store locally in Parquet format (efficient, fast)
- Daily updates via cron (6am before market open)
- Offline access to historical data (no API calls needed)
- Integration with OvernightLearner for validation
"""

from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import json
import time
from loguru import logger
from wawatrader.alpaca_client import AlpacaClient


class HistoricalDataCollector:
    """
    Collects and stores historical market data locally for offline simulation.
    
    Architecture:
        trading_data/historical/
        ├── 1Min/
        │   ├── AAPL.parquet
        │   ├── SPY.parquet
        │   └── ...
        ├── 5Min/
        ├── 15Min/
        ├── 1Hour/
        └── 1Day/
    
    Usage:
        # Initial backfill (run once)
        collector = HistoricalDataCollector()
        collector.backfill_historical_data(
            symbols=['SPY', 'QQQ', 'AAPL'],
            start_date=datetime.now() - timedelta(days=730),
            end_date=datetime.now()
        )
        
        # Daily update (via cron at 6am)
        collector.daily_update(['SPY', 'QQQ', 'AAPL'])
        
        # Offline access (no API call)
        bars = collector.get_offline_data('AAPL', start, end, timeframe='1Min')
    """
    
    def __init__(self, storage_dir: str = "trading_data/historical"):
        """
        Initialize the historical data collector.
        
        Args:
            storage_dir: Base directory for storing historical data
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timeframe directories
        self.timeframes = ['1Min', '5Min', '15Min', '1Hour', '1Day']
        for tf in self.timeframes:
            (self.storage_dir / tf).mkdir(exist_ok=True)
        
        self.alpaca = AlpacaClient()
        
        # Smart collection features
        self.progress_file = self.storage_dir / "collection_progress.json"
        self.max_calls_per_minute = 180  # Conservative API rate limit
        self.call_history = []
        self.progress = self._load_progress()
        
        logger.info(f"📊 Historical Data Collector initialized")
        logger.info(f"   Storage: {self.storage_dir.absolute()}")
        logger.info(f"   Progress tracking: {len(self.progress)} symbols tracked")
    
    def backfill_historical_data(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        timeframes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Backfill historical data for multiple symbols and timeframes.
        
        This is the main method for initial data collection. Run once to populate
        the local data lake with historical data. Can take 30-60 minutes depending
        on the number of symbols and timeframes.
        
        Args:
            symbols: List of ticker symbols to backfill
            start_date: Start date for historical data
            end_date: End date for historical data  
            timeframes: List of timeframes to collect (default: all)
        
        Returns:
            Summary statistics about the backfill operation
        """
        if timeframes is None:
            timeframes = self.timeframes
        
        results = {
            'symbols_processed': 0,
            'total_bars_collected': 0,
            'files_created': 0,
            'errors': [],
            'start_time': datetime.now(),
            'timeframes_processed': {}
        }
        
        logger.info(f"🔄 Starting historical data backfill")
        logger.info(f"   Symbols: {len(symbols)}")
        logger.info(f"   Timeframes: {timeframes}")
        logger.info(f"   Date range: {start_date.date()} to {end_date.date()}")
        logger.info(f"   Estimated time: {len(symbols) * len(timeframes)} API calls")
        
        for timeframe in timeframes:
            logger.info(f"\n📈 Processing timeframe: {timeframe}")
            timeframe_bars = 0
            
            for symbol in symbols:
                try:
                    logger.info(f"   Fetching {symbol} ({timeframe})...")
                    
                    # Fetch data from Alpaca
                    bars = self.alpaca.get_bars(
                        symbol=symbol,
                        timeframe=timeframe,
                        start=start_date,
                        end=end_date
                    )
                    
                    if not bars.empty:
                        # Reset index to make timestamp a column (AlpacaClient returns timestamp as index)
                        bars_to_save = bars.reset_index()
                        
                        # Save to Parquet
                        file_path = self._get_file_path(symbol, timeframe)
                        
                        # If file exists, merge with existing data
                        if file_path.exists():
                            existing = pd.read_parquet(file_path)
                            bars_to_save = pd.concat([existing, bars_to_save]).drop_duplicates(subset=['timestamp']).sort_values('timestamp')
                        
                        bars_to_save.to_parquet(file_path, index=False)
                        
                        results['files_created'] += 1
                        results['total_bars_collected'] += len(bars_to_save)
                        timeframe_bars += len(bars_to_save)
                        
                        logger.info(f"      ✅ Saved {len(bars_to_save):,} bars to {file_path.name}")
                    else:
                        logger.warning(f"      ⚠️ No data returned for {symbol}")
                    
                    results['symbols_processed'] += 1
                    
                except Exception as e:
                    error_msg = f"Error collecting {symbol} {timeframe}: {e}"
                    logger.error(f"      ❌ {error_msg}")
                    results['errors'].append(error_msg)
            
            results['timeframes_processed'][timeframe] = timeframe_bars
            logger.info(f"   ✅ {timeframe}: {timeframe_bars:,} total bars")
        
        results['end_time'] = datetime.now()
        results['duration'] = (results['end_time'] - results['start_time']).total_seconds()
        
        # Print summary
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 BACKFILL COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"✅ Symbols processed: {results['symbols_processed']}/{len(symbols) * len(timeframes)}")
        logger.info(f"✅ Total bars collected: {results['total_bars_collected']:,}")
        logger.info(f"✅ Files created: {results['files_created']}")
        logger.info(f"⏱️  Duration: {results['duration']:.1f} seconds")
        
        if results['errors']:
            logger.warning(f"⚠️  Errors: {len(results['errors'])}")
            for error in results['errors'][:5]:  # Show first 5
                logger.warning(f"   • {error}")
        
        logger.info(f"\n📂 Data stored in: {self.storage_dir.absolute()}")
        logger.info(f"{'='*60}\n")
        
        return results
    
    def daily_update(
        self,
        symbols: List[str],
        timeframes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Daily update: Fetch yesterday's data and append to existing files.
        
        Should be run via cron at 6am before market open:
        0 6 * * 1-5 cd /path/to/wawatrader && source venv/bin/activate && python -c "..."
        
        Args:
            symbols: List of symbols to update
            timeframes: List of timeframes to update (default: all)
        
        Returns:
            Summary of the update operation
        """
        if timeframes is None:
            timeframes = self.timeframes
        
        # Get yesterday's date range
        yesterday = datetime.now() - timedelta(days=1)
        start_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        logger.info(f"🔄 Daily update for {yesterday.date()}")
        
        results = self.backfill_historical_data(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            timeframes=timeframes
        )
        
        return results
    
    def get_offline_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = '1Min'
    ) -> pd.DataFrame:
        """
        Get historical data from local storage (no API call).
        
        This is the key method for offline simulation. Returns data from local
        Parquet files instead of making API calls to Alpaca.
        
        Args:
            symbol: Ticker symbol
            start_date: Start of date range
            end_date: End of date range
            timeframe: Data timeframe (1Min, 5Min, etc.)
        
        Returns:
            DataFrame with OHLCV data, or empty DataFrame if not available
        """
        file_path = self._get_file_path(symbol, timeframe)
        
        if not file_path.exists():
            logger.warning(f"⚠️ No local data for {symbol} {timeframe}")
            logger.warning(f"   Run backfill_historical_data() first")
            return pd.DataFrame()
        
        try:
            # Read Parquet file
            df = pd.read_parquet(file_path)
            
            # Ensure timestamp is datetime and timezone-aware
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            if df['timestamp'].dt.tz is None:
                df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')
            
            # Ensure filter dates are timezone-aware
            if start_date.tzinfo is None:
                from datetime import timezone
                start_date = start_date.replace(tzinfo=timezone.utc)
            if end_date.tzinfo is None:
                from datetime import timezone
                end_date = end_date.replace(tzinfo=timezone.utc)
            
            # Filter by date range
            mask = (df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)
            df = df[mask]
            
            logger.info(f"📊 Loaded {len(df):,} bars for {symbol} ({timeframe}) from local storage")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Error reading {file_path}: {e}")
            return pd.DataFrame()
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the local data storage.
        
        Returns:
            Dictionary with storage statistics
        """
        stats = {
            'total_files': 0,
            'total_size_mb': 0,
            'symbols': set(),
            'timeframes': {},
            'oldest_data': None,
            'newest_data': None
        }
        
        for timeframe in self.timeframes:
            tf_dir = self.storage_dir / timeframe
            if not tf_dir.exists():
                continue
            
            files = list(tf_dir.glob('*.parquet'))
            stats['timeframes'][timeframe] = len(files)
            stats['total_files'] += len(files)
            
            for file in files:
                # Get file size
                stats['total_size_mb'] += file.stat().st_size / 1024 / 1024
                
                # Extract symbol
                symbol = file.stem
                stats['symbols'].add(symbol)
                
                # Check date range (expensive, sample only)
                if len(stats['symbols']) <= 5:  # Only check first 5 symbols
                    try:
                        df = pd.read_parquet(file)
                        if not df.empty:
                            df['timestamp'] = pd.to_datetime(df['timestamp'])
                            oldest = df['timestamp'].min()
                            newest = df['timestamp'].max()
                            
                            if stats['oldest_data'] is None or oldest < stats['oldest_data']:
                                stats['oldest_data'] = oldest
                            if stats['newest_data'] is None or newest > stats['newest_data']:
                                stats['newest_data'] = newest
                    except:
                        pass
        
        stats['symbols'] = sorted(list(stats['symbols']))
        
        return stats
    
    def _get_file_path(self, symbol: str, timeframe: str) -> Path:
        """Get the file path for a symbol and timeframe."""
        return self.storage_dir / timeframe / f"{symbol}.parquet"
    
    def check_data_availability(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = '1Min'
    ) -> Dict[str, Any]:
        """
        Check if data is available locally for the given parameters.
        
        Args:
            symbol: Ticker symbol
            start_date: Desired start date
            end_date: Desired end date
            timeframe: Data timeframe
        
        Returns:
            Dictionary with availability information
        """
        file_path = self._get_file_path(symbol, timeframe)
        
        result = {
            'available': False,
            'file_exists': file_path.exists(),
            'coverage': 0.0,
            'missing_dates': [],
            'message': ''
        }
        
        if not file_path.exists():
            result['message'] = f"No local data file for {symbol} {timeframe}"
            return result
        
        try:
            df = pd.read_parquet(file_path)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            if df['timestamp'].dt.tz is None:
                df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')
            
            # Check coverage
            df_start = df['timestamp'].min()
            df_end = df['timestamp'].max()
            
            # Ensure comparison dates are timezone-aware
            if start_date.tzinfo is None:
                from datetime import timezone
                start_date = start_date.replace(tzinfo=timezone.utc)
            if end_date.tzinfo is None:
                from datetime import timezone
                end_date = end_date.replace(tzinfo=timezone.utc)
            
            if df_start <= start_date and df_end >= end_date:
                result['available'] = True
                result['coverage'] = 1.0
                result['message'] = f"✅ Full coverage available"
            else:
                # Partial coverage
                result['available'] = True
                result['coverage'] = 0.5  # Simplified
                result['message'] = f"⚠️ Partial coverage (data from {df_start.date()} to {df_end.date()})"
                
                if df_start > start_date:
                    result['missing_dates'].append(f"Before {df_start.date()}")
                if df_end < end_date:
                    result['missing_dates'].append(f"After {df_end.date()}")
            
            return result
            
        except Exception as e:
            result['message'] = f"❌ Error checking data: {e}"
            return result


    def _load_progress(self) -> Dict[str, Dict]:
        """Load collection progress from disk."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r') as f:
                    data = json.load(f)
                    logger.info(f"📁 Loaded progress for {len(data)} symbols")
                    return data
            except Exception as e:
                logger.warning(f"⚠️ Could not load progress: {e}")
        return {}
    
    def _save_progress(self):
        """Save collection progress to disk."""
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(self.progress, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"❌ Could not save progress: {e}")
    
    def _respect_rate_limits(self):
        """Intelligent rate limiting to stay under API limits."""
        now = datetime.now()
        
        # Clean old calls (older than 1 minute)
        cutoff = now - timedelta(seconds=60)
        self.call_history = [t for t in self.call_history if t > cutoff]
        
        # Check if we need to throttle
        current_rate = len(self.call_history)
        
        if current_rate >= self.max_calls_per_minute:
            # Wait until we're under the limit
            oldest_call = min(self.call_history) if self.call_history else now
            wait_time = 61 - (now - oldest_call).total_seconds()
            
            if wait_time > 0:
                logger.warning(f"🚨 Rate limit reached ({current_rate}/180). Waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
        
        elif current_rate > self.max_calls_per_minute * 0.8:  # 80% threshold
            logger.info(f"⚠️ Approaching rate limit ({current_rate}/180). Brief pause...")
            time.sleep(1)
        
        # Record this call
        self.call_history.append(now)
    
    def discover_symbols_for_collection(self) -> List[str]:
        """
        Smart symbol discovery for comprehensive data collection.
        
        Returns prioritized list of symbols to collect data for.
        """
        symbols = set()
        
        # From existing cache files
        for tf_dir in self.storage_dir.iterdir():
            if tf_dir.is_dir() and tf_dir.name in self.timeframes:
                for file_path in tf_dir.glob("*.parquet"):
                    symbol = file_path.stem
                    symbols.add(symbol)
        
        # Add major market symbols
        major_symbols = {
            # Major ETFs
            'SPY', 'QQQ', 'IWM', 'EFA', 'VTI', 'GLD', 'SLV', 'TLT', 'HYG',
            'XLF', 'XLK', 'XLE', 'XLV', 'XLP', 'XLI', 'XLU', 'XLB', 'XLRE',
            
            # Major Stocks  
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'BRK.B',
            'JPM', 'JNJ', 'V', 'PG', 'UNH', 'HD', 'MA', 'DIS', 'PYPL', 'NFLX',
            'CRM', 'ADBE', 'INTC', 'AMD', 'ORCL', 'IBM', 'CSCO', 'WMT', 'BAC',
            
            # Popular/Active Stocks
            'RIVN', 'LCID', 'F', 'GM', 'NIO', 'PLTR', 'SOFI', 'AMC', 'GME',
            'COIN', 'HOOD', 'SQ', 'ROKU', 'ZM', 'PTON', 'SNAP', 'TWTR', 'UBER'
        }
        
        symbols.update(major_symbols)
        
        # From universe cache if exists
        universe_file = self.storage_dir.parent / "universe_cache.json"
        if universe_file.exists():
            try:
                with open(universe_file, 'r') as f:
                    universe_data = json.load(f)
                    if 'symbols' in universe_data:
                        symbols.update(universe_data['symbols'])
                        logger.info(f"📊 Added {len(universe_data['symbols'])} symbols from universe cache")
            except Exception as e:
                logger.warning(f"⚠️ Could not load universe cache: {e}")
        
        symbol_list = sorted(list(symbols))
        logger.info(f"🎯 Discovered {len(symbol_list)} symbols for comprehensive collection")
        
        return symbol_list
    
    def collect_comprehensive_history(
        self,
        max_years: int = 5,
        max_api_calls: int = 500,
        priority_symbols: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Intelligent comprehensive historical data collection.
        
        Collects maximum historical data while respecting API limits.
        Uses smart prioritization and resumable progress tracking.
        
        Args:
            max_years: Maximum years of history per symbol
            max_api_calls: Budget of API calls for this session
            priority_symbols: Symbols to prioritize (None = auto-discover)
            timeframes: Timeframes to collect (default: ['1Day'])
        
        Returns:
            Collection statistics
        """
        if timeframes is None:
            timeframes = ['1Day']  # Start with daily data
        
        if priority_symbols is None:
            priority_symbols = self.discover_symbols_for_collection()
        
        # Calculate priority scores
        symbol_priorities = []
        for symbol in priority_symbols:
            priority_score = self._calculate_symbol_priority(symbol)
            symbol_priorities.append((symbol, priority_score))
        
        # Sort by priority (highest first)
        symbol_priorities.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"🚀 Starting comprehensive collection")
        logger.info(f"   Symbols: {len(symbol_priorities)}")
        logger.info(f"   Timeframes: {timeframes}")
        logger.info(f"   Max Years: {max_years}")
        logger.info(f"   API Budget: {max_api_calls}")
        
        stats = {
            'symbols_processed': 0,
            'symbols_completed': 0,
            'total_bars_collected': 0,
            'api_calls_used': 0,
            'errors': 0,
            'timeframes_completed': {tf: 0 for tf in timeframes}
        }
        
        start_time = datetime.now()
        
        for i, (symbol, priority) in enumerate(symbol_priorities):
            if stats['api_calls_used'] >= max_api_calls:
                logger.info(f"🛑 Reached API budget ({max_api_calls}). Stopping.")
                break
                
            logger.info(f"📈 Processing {symbol} ({i+1}/{len(symbol_priorities)}) Priority: {priority:.1f}")
            
            try:
                symbol_stats = self._collect_symbol_comprehensive(
                    symbol, max_years, timeframes
                )
                
                stats['symbols_processed'] += 1
                stats['total_bars_collected'] += symbol_stats['total_bars']
                stats['api_calls_used'] = len(self.call_history)
                
                for tf in timeframes:
                    if symbol_stats.get(f'{tf}_complete', False):
                        stats['timeframes_completed'][tf] += 1
                
                # Update progress
                if symbol not in self.progress:
                    self.progress[symbol] = {}
                
                self.progress[symbol].update({
                    'last_updated': datetime.now().isoformat(),
                    'priority_score': priority,
                    'bars_collected': symbol_stats['total_bars'],
                    'timeframes_complete': symbol_stats['timeframes_complete']
                })
                
                # Respect rate limits
                self._respect_rate_limits()
                
                # Save progress periodically  
                if i % 10 == 0:
                    self._save_progress()
                
            except Exception as e:
                logger.error(f"❌ Error collecting {symbol}: {e}")
                stats['errors'] += 1
                continue
        
        # Final save
        self._save_progress()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        logger.info("🎉 Comprehensive Collection Complete!")
        logger.info(f"   Duration: {duration:.1f}s")
        logger.info(f"   Symbols Processed: {stats['symbols_processed']}")
        logger.info(f"   Total Bars: {stats['total_bars_collected']:,}")
        logger.info(f"   API Calls Used: {stats['api_calls_used']}/{max_api_calls}")
        logger.info(f"   Rate: {stats['api_calls_used']/max(duration/60, 1):.1f} calls/minute")
        
        for tf in timeframes:
            completed = stats['timeframes_completed'][tf]
            logger.info(f"   {tf} Complete: {completed}/{len(symbol_priorities)} symbols")
        
        return stats
    
    def _calculate_symbol_priority(self, symbol: str) -> float:
        """Calculate priority score for symbol collection."""
        priority = 1.0
        
        # Major symbols get highest priority
        major_symbols = {
            'SPY', 'QQQ', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA'
        }
        if symbol in major_symbols:
            priority += 5.0
        
        # Check existing data to estimate activity
        daily_file = self.storage_dir / '1Day' / f'{symbol}.parquet'
        if daily_file.exists():
            try:
                df = pd.read_parquet(daily_file)
                if not df.empty:
                    # More recent data = higher priority
                    latest_date = pd.to_datetime(df.index.max())
                    days_old = (datetime.now() - latest_date).days
                    if days_old < 7:
                        priority += 3.0
                    elif days_old < 30:
                        priority += 1.0
                    
                    # Higher volume = higher priority
                    if 'volume' in df.columns:
                        avg_volume = df['volume'].mean()
                        if avg_volume > 10_000_000:  # Very high volume
                            priority += 2.0
                        elif avg_volume > 1_000_000:  # High volume  
                            priority += 1.0
                        elif avg_volume > 100_000:  # Medium volume
                            priority += 0.5
            except Exception:
                pass
        
        return priority
    
    def _collect_symbol_comprehensive(
        self, symbol: str, max_years: int, timeframes: List[str]
    ) -> Dict[str, Any]:
        """Collect comprehensive data for a single symbol."""
        stats = {
            'total_bars': 0,
            'timeframes_complete': [],
            'errors': []
        }
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * max_years)
        
        for timeframe in timeframes:
            try:
                logger.debug(f"📊 {symbol}: Collecting {timeframe} data")
                
                # Check existing data
                file_path = self.storage_dir / timeframe / f'{symbol}.parquet'
                existing_data = None
                
                if file_path.exists():
                    try:
                        existing_data = pd.read_parquet(file_path)
                    except Exception:
                        pass
                
                # Determine what data to fetch
                fetch_start = start_date
                fetch_end = end_date
                
                if existing_data is not None and not existing_data.empty:
                    existing_start = pd.to_datetime(existing_data.index.min()).to_pydatetime()
                    existing_end = pd.to_datetime(existing_data.index.max()).to_pydatetime()
                    
                    # Only fetch missing data
                    if existing_end >= end_date - timedelta(days=7):
                        # Recent data exists, check if we need older data
                        if existing_start <= start_date:
                            # Complete coverage
                            stats[f'{timeframe}_complete'] = True
                            stats['total_bars'] += len(existing_data)
                            logger.debug(f"✅ {symbol} {timeframe}: Complete coverage")
                            continue
                        else:
                            # Need older data
                            fetch_end = existing_start - timedelta(days=1)
                    else:
                        # Need newer data
                        fetch_start = existing_end + timedelta(days=1)
                
                # Fetch missing data
                self._respect_rate_limits()
                
                bars = self.alpaca.get_bars(
                    symbol=symbol,
                    start=fetch_start,
                    end=fetch_end,
                    timeframe=timeframe
                )
                
                if bars is not None and not bars.empty:
                    # Combine with existing data
                    if existing_data is not None and not existing_data.empty:
                        combined_bars = pd.concat([existing_data, bars]).drop_duplicates()
                        combined_bars = combined_bars.sort_index()
                    else:
                        combined_bars = bars
                    
                    # Save updated data
                    combined_bars.to_parquet(file_path)
                    stats['total_bars'] += len(combined_bars)
                    
                    # Check if complete
                    min_date = pd.to_datetime(combined_bars.index.min()).to_pydatetime()
                    max_date = pd.to_datetime(combined_bars.index.max()).to_pydatetime()
                    target_end = end_date - timedelta(days=7)
                    
                    if (min_date <= start_date and max_date >= target_end):
                        stats[f'{timeframe}_complete'] = True
                        stats['timeframes_complete'].append(timeframe)
                    
                    logger.debug(f"✅ {symbol} {timeframe}: {len(bars)} new bars collected")
                
            except Exception as e:
                logger.warning(f"⚠️ Error collecting {symbol} {timeframe}: {e}")
                stats['errors'].append(f"{timeframe}: {str(e)}")
        
        return stats

    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive collection status report."""
        total_symbols = len(self.progress)
        
        # Count completions by timeframe
        completions = {'1Day': 0, '1Hour': 0, '15Min': 0, '5Min': 0, '1Min': 0}
        total_bars = 0
        
        for symbol_progress in self.progress.values():
            if isinstance(symbol_progress.get('bars_collected'), int):
                total_bars += symbol_progress['bars_collected']
            
            timeframes_complete = symbol_progress.get('timeframes_complete', [])
            for tf in timeframes_complete:
                if tf in completions:
                    completions[tf] += 1
        
        # Check actual file counts
        file_counts = {}
        for tf in self.timeframes:
            tf_dir = self.storage_dir / tf
            if tf_dir.exists():
                file_counts[tf] = len(list(tf_dir.glob("*.parquet")))
            else:
                file_counts[tf] = 0
        
        return {
            'total_symbols_tracked': total_symbols,
            'files_by_timeframe': file_counts,
            'completed_by_timeframe': completions,
            'total_bars_cached': total_bars,
            'storage_size_mb': sum(
                f.stat().st_size for f in self.storage_dir.rglob("*.parquet")
            ) / (1024 * 1024),
            'most_active_symbols': self._get_most_active_symbols(),
            'collection_gaps': self._identify_collection_gaps(),
            'api_rate_status': f"{len(self.call_history)}/180 per minute"
        }
    
    def _get_most_active_symbols(self) -> List[Tuple[str, int]]:
        """Get symbols with most data."""
        symbol_bars = []
        for symbol_data in self.progress.values():
            if isinstance(symbol_data.get('bars_collected'), int):
                bars = symbol_data['bars_collected']
                if bars > 0:
                    symbol_bars.append((symbol_data.get('symbol', 'Unknown'), bars))
        
        return sorted(symbol_bars, key=lambda x: x[1], reverse=True)[:10]
    
    def _identify_collection_gaps(self) -> Dict[str, List[str]]:
        """Identify symbols missing data for each timeframe."""
        gaps = {tf: [] for tf in self.timeframes}
        
        # Check which symbols have files vs which are tracked
        tracked_symbols = set(self.progress.keys())
        
        for tf in self.timeframes:
            tf_dir = self.storage_dir / tf
            if tf_dir.exists():
                existing_files = {f.stem for f in tf_dir.glob("*.parquet")}
                missing = tracked_symbols - existing_files
                gaps[tf] = sorted(list(missing))
        
        return gaps


def get_collector(storage_dir: str = "trading_data/historical") -> HistoricalDataCollector:
    """
    Factory function to get a HistoricalDataCollector instance.
    
    Useful for cron jobs and scripts.
    """
    return HistoricalDataCollector(storage_dir=storage_dir)
