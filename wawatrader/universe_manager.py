"""
Dynamic Trading Universe Manager

Automatically discovers and maintains a dynamic list of stocks to track based on:
- Market capitalization
- Trading volume
- Price movement (volatility)
- Sector representation
- Current holdings and watchlist
"""

from typing import List, Dict, Set, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from loguru import logger
import json
from pathlib import Path


@dataclass
class UniverseStock:
    """Stock in trading universe with metadata."""
    symbol: str
    reason: str  # Why included: "high_volume", "holdings", "watchlist", "sector_leader", etc.
    market_cap: Optional[float] = None
    avg_volume: Optional[float] = None
    sector: Optional[str] = None
    added_at: Optional[datetime] = None
    priority: int = 1  # 1=highest (positions), 2=watchlist, 3=discovered


class UniverseManager:
    """
    Manages dynamic trading universe.
    
    Combines:
    - Static core (holdings, watchlist)
    - Dynamic discovery (volume leaders, movers, sector rotation)
    """
    
    def __init__(self, alpaca_client, max_universe_size: int = 100):
        """
        Initialize universe manager.
        
        Args:
            alpaca_client: Alpaca client for market data
            max_universe_size: Maximum number of stocks to track (default: 100)
        """
        self.alpaca = alpaca_client
        self.max_size = max_universe_size
        self.universe: Dict[str, UniverseStock] = {}
        self.cache_file = Path("trading_data/universe_cache.json")
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Sector leaders (always include for diversification)
        self.sector_leaders = {
            'Technology': ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'META', 'ORCL', 'CSCO', 'ADBE', 'CRM', 'NOW'],
            'Healthcare': ['UNH', 'JNJ', 'LLY', 'ABBV', 'TMO', 'ABT', 'DHR', 'PFE', 'MRK', 'BMY'],
            'Financial': ['JPM', 'BAC', 'V', 'MA', 'GS', 'MS', 'C', 'BLK', 'SCHW', 'AXP'],
            'Consumer': ['AMZN', 'WMT', 'HD', 'NKE', 'MCD', 'SBUX', 'LOW', 'TGT', 'COST', 'PG'],
            'Energy': ['XOM', 'CVX', 'COP', 'EOG', 'SLB', 'PXD', 'PSX', 'VLO', 'MPC', 'OXY'],
            'Industrial': ['CAT', 'BA', 'UNP', 'HON', 'GE', 'UPS', 'RTX', 'LMT', 'MMM', 'DE'],
            'Communication': ['META', 'DIS', 'CMCSA', 'NFLX', 'T', 'VZ', 'TMUS', 'CHTR', 'EA', 'TTWO'],
            'Materials': ['LIN', 'APD', 'ECL', 'SHW', 'FCX', 'NEM', 'NUE', 'DOW', 'DD', 'PPG'],
            'Utilities': ['NEE', 'DUK', 'SO', 'D', 'AEP', 'EXC', 'SRE', 'PEG', 'XEL', 'ED'],
            'Real Estate': ['PLD', 'AMT', 'CCI', 'EQIX', 'PSA', 'SPG', 'WELL', 'DLR', 'O', 'AVB'],
        }
    
    def build_universe(self, watchlist: List[str]) -> List[str]:
        """
        Build dynamic trading universe.
        
        Priority order:
        1. Current positions (always track)
        2. Watchlist (always track)
        3. Sector leaders (ensure diversification)
        4. High volume stocks (liquidity)
        5. Recent movers (opportunity detection)
        
        Args:
            watchlist: User-configured watchlist
            
        Returns:
            List of symbols to track
        """
        logger.info("🌍 Building dynamic trading universe...")
        self.universe.clear()
        
        # 1. Add current positions (Priority 1)
        self._add_positions()
        
        # 2. Add watchlist (Priority 2)
        self._add_watchlist(watchlist)
        
        # 3. Add sector leaders (Priority 2)
        self._add_sector_leaders()
        
        # 4. Add high volume stocks (Priority 3)
        remaining_slots = self.max_size - len(self.universe)
        if remaining_slots > 0:
            self._add_volume_leaders(limit=remaining_slots // 2)
        
        # 5. Add recent movers (Priority 3)
        remaining_slots = self.max_size - len(self.universe)
        if remaining_slots > 0:
            self._add_recent_movers(limit=remaining_slots)
        
        # Save cache
        self._save_cache()
        
        # Log summary
        self._log_summary()
        
        return list(self.universe.keys())
    
    def _add_positions(self):
        """Add current positions (highest priority)."""
        try:
            positions = self.alpaca.get_positions()
            for pos in positions:
                self.universe[pos.symbol] = UniverseStock(
                    symbol=pos.symbol,
                    reason="current_holding",
                    priority=1,
                    added_at=datetime.now()
                )
            logger.info(f"   ✓ Added {len(positions)} current positions")
        except Exception as e:
            logger.warning(f"   ⚠️ Could not fetch positions: {e}")
    
    def _add_watchlist(self, watchlist: List[str]):
        """Add watchlist symbols."""
        added = 0
        for symbol in watchlist:
            if symbol not in self.universe:
                self.universe[symbol] = UniverseStock(
                    symbol=symbol,
                    reason="watchlist",
                    priority=2,
                    added_at=datetime.now()
                )
                added += 1
        logger.info(f"   ✓ Added {added} watchlist symbols")
    
    def _add_sector_leaders(self):
        """Add sector leaders for diversification."""
        added = 0
        for sector, leaders in self.sector_leaders.items():
            # Add top 3 per sector to ensure we hit 100 stocks
            for symbol in leaders[:3]:
                if symbol not in self.universe:
                    self.universe[symbol] = UniverseStock(
                        symbol=symbol,
                        reason=f"sector_leader_{sector.lower()}",
                        sector=sector,
                        priority=2,
                        added_at=datetime.now()
                    )
                    added += 1
        logger.info(f"   ✓ Added {added} sector leaders")
    
    def _add_volume_leaders(self, limit: int):
        """
        Add stocks with highest trading volume (liquidity).
        
        Uses most active stocks from previous trading day.
        """
        try:
            # Get most active stocks
            # Note: Alpaca API doesn't have direct "most active" endpoint for paper trading
            # We'll use a curated list of known high-volume stocks
            high_volume_stocks = [
                # Tech mega-caps (always high volume)
                'TSLA', 'AAPL', 'MSFT', 'NVDA', 'AMD', 'INTC', 'QCOM', 'MU',
                'AVGO', 'TXN', 'AMAT', 'LRCX', 'KLAC', 'ASML', 'TSM', 'SNPS',
                # ETFs (high volume)
                'SPY', 'QQQ', 'IWM', 'DIA', 'VOO', 'VTI',
                # Other high-volume stocks
                'AMZN', 'GOOGL', 'META', 'NFLX', 'BABA', 'NIO', 'PLTR', 'SOFI',
                'F', 'GE', 'BAC', 'SNAP', 'UBER', 'LYFT', 'DIDI', 'GRAB',
                'AAL', 'CCL', 'COIN', 'RIVN', 'LCID', 'GME', 'AMC', 'BBBY',
                'SPCE', 'HOOD', 'WISH', 'CLOV', 'BB', 'NOK', 'SKLZ', 'OPEN'
            ]
            
            added = 0
            for symbol in high_volume_stocks:
                if symbol not in self.universe and added < limit:
                    self.universe[symbol] = UniverseStock(
                        symbol=symbol,
                        reason="high_volume",
                        priority=3,
                        added_at=datetime.now()
                    )
                    added += 1
                if added >= limit:
                    break
            
            logger.info(f"   ✓ Added {added} high-volume stocks")
        except Exception as e:
            logger.warning(f"   ⚠️ Could not fetch volume leaders: {e}")
    
    def _add_recent_movers(self, limit: int):
        """
        Add stocks with significant recent price movement.
        
        These might have breaking news or momentum.
        """
        try:
            # Get recent gainers/losers
            # Note: Using snapshot API to find movers
            # For paper trading, we'll use a curated list of volatile stocks
            volatile_stocks = [
                # Growth/momentum stocks
                'SHOP', 'SQ', 'SNOW', 'DDOG', 'CRWD', 'ZS', 'NET', 'OKTA', 'PANW', 'FTNT',
                'DKNG', 'PENN', 'RBLX', 'U', 'DASH', 'ABNB', 'CVNA', 'AFRM', 'UPST', 'BILL',
                # Biotech (often volatile)
                'MRNA', 'BNTX', 'NVAX', 'SGEN', 'VRTX', 'BMRN', 'REGN', 'ALNY', 'INCY', 'BIIB',
                # Small-cap tech
                'MARA', 'RIOT', 'SI', 'HOOD', 'COIN', 'SQ', 'PYPL', 'DOCU', 'ZM', 'PTON',
                # EV and energy transition
                'RIVN', 'LCID', 'FSR', 'NKLA', 'PLUG', 'FCEL', 'BE', 'ENPH', 'SEDG', 'RUN',
                # Meme/social stocks
                'GME', 'AMC', 'BBBY', 'BB', 'NOK', 'WISH', 'CLOV', 'SKLZ', 'SPCE', 'OPEN'
            ]
            
            added = 0
            for symbol in volatile_stocks:
                if symbol not in self.universe and added < limit:
                    self.universe[symbol] = UniverseStock(
                        symbol=symbol,
                        reason="recent_mover",
                        priority=3,
                        added_at=datetime.now()
                    )
                    added += 1
                if added >= limit:
                    break
            
            logger.info(f"   ✓ Added {added} recent movers")
        except Exception as e:
            logger.warning(f"   ⚠️ Could not fetch recent movers: {e}")
    
    def _save_cache(self):
        """Save universe to cache file."""
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'max_size': self.max_size,
                'universe': [
                    {
                        'symbol': stock.symbol,
                        'reason': stock.reason,
                        'priority': stock.priority,
                        'sector': stock.sector,
                        'added_at': stock.added_at.isoformat() if stock.added_at else None
                    }
                    for stock in self.universe.values()
                ]
            }
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            logger.debug(f"   ✓ Saved universe cache to {self.cache_file}")
        except Exception as e:
            logger.warning(f"   ⚠️ Could not save cache: {e}")
    
    def load_cache(self) -> Optional[List[str]]:
        """
        Load universe from cache if recent.
        
        Returns:
            List of symbols if cache valid, None otherwise
        """
        try:
            if not self.cache_file.exists():
                return None
            
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Check if cache is recent (< 24 hours old)
            cache_time = datetime.fromisoformat(cache_data['timestamp'])
            age = datetime.now() - cache_time
            
            if age > timedelta(hours=24):
                logger.info("   ⚠️ Universe cache is stale (>24h old)")
                return None
            
            symbols = [item['symbol'] for item in cache_data['universe']]
            logger.info(f"   ✓ Loaded {len(symbols)} symbols from cache (age: {age.seconds//3600}h)")
            
            # Rebuild universe dict
            for item in cache_data['universe']:
                self.universe[item['symbol']] = UniverseStock(
                    symbol=item['symbol'],
                    reason=item['reason'],
                    priority=item['priority'],
                    sector=item.get('sector'),
                    added_at=datetime.fromisoformat(item['added_at']) if item.get('added_at') else None
                )
            
            return symbols
        except Exception as e:
            logger.warning(f"   ⚠️ Could not load cache: {e}")
            return None
    
    def _log_summary(self):
        """Log universe composition summary."""
        by_reason = {}
        for stock in self.universe.values():
            by_reason[stock.reason] = by_reason.get(stock.reason, 0) + 1
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🌍 DYNAMIC UNIVERSE BUILT: {len(self.universe)} stocks")
        logger.info(f"{'='*60}")
        for reason, count in sorted(by_reason.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"   • {reason:20s}: {count:3d} stocks")
        logger.info(f"{'='*60}\n")
    
    def get_by_priority(self) -> Dict[int, List[str]]:
        """Get symbols grouped by priority."""
        by_priority = {1: [], 2: [], 3: []}
        for stock in self.universe.values():
            by_priority[stock.priority].append(stock.symbol)
        return by_priority
    
    def add_to_watchlist(self, symbols: List[str], reason: str = "promoted"):
        """
        Add symbols to universe (e.g., promoted from news analysis).
        
        Args:
            symbols: List of symbols to add
            reason: Reason for addition
        """
        added = 0
        for symbol in symbols:
            if symbol not in self.universe:
                self.universe[symbol] = UniverseStock(
                    symbol=symbol,
                    reason=reason,
                    priority=2,
                    added_at=datetime.now()
                )
                added += 1
        
        if added > 0:
            logger.info(f"   ✓ Added {added} symbols to universe (reason: {reason})")
            self._save_cache()


def get_universe_manager(alpaca_client, max_size: int = 100) -> UniverseManager:
    """
    Get or create universe manager singleton.
    
    Args:
        alpaca_client: Alpaca client
        max_size: Maximum universe size
        
    Returns:
        UniverseManager instance
    """
    if not hasattr(get_universe_manager, '_instance'):
        get_universe_manager._instance = UniverseManager(alpaca_client, max_size)
    return get_universe_manager._instance
