# Dynamic Trading Universe System

## 🌍 Overview

WawaTrader now includes a **Dynamic Universe Manager** that automatically discovers and tracks up to 100 stocks for news collection, replacing the previous static 5-10 stock limitation.

**Previous System**: Only tracked watchlist (5 symbols) + positions (0-5 symbols) = **5-10 stocks total**

**New System**: Dynamically builds universe of **100 stocks** including:
- Current holdings (Priority 1)
- Watchlist (Priority 2)
- Sector leaders (Priority 2)
- High-volume stocks (Priority 3)
- Recent movers/volatile stocks (Priority 3)

## 🎯 Problem Solved

### Before (Static Watchlist)
```python
# Old code in scheduled_tasks.py
symbols = list(settings.data.symbols)  # Only 5 stocks
positions = alpaca.get_positions()     # Add 0-5 more
# Total: 5-10 stocks

# Problem: Missed opportunities
# ❌ AMZN announces amazing earnings → Not tracked
# ❌ META announces AI breakthrough → Not tracked  
# ❌ Cannot answer "what to buy" → No alternatives visible
```

### After (Dynamic Universe)
```python
# New code in scheduled_tasks.py
from wawatrader.universe_manager import get_universe_manager

universe_mgr = get_universe_manager(alpaca, max_size=100)
symbols = universe_mgr.build_universe(watchlist)
# Total: 100 stocks

# Solution: Comprehensive coverage
# ✅ AMZN tracked → Opportunity detected
# ✅ META tracked → Breakthrough captured
# ✅ Can answer "what to buy" → 100 alternatives analyzed
```

## 📁 Architecture

### Core Component: `UniverseManager`

Location: `wawatrader/universe_manager.py`

```python
class UniverseManager:
    """
    Manages dynamic trading universe.
    
    Combines:
    - Static core (holdings, watchlist)
    - Dynamic discovery (volume leaders, movers, sector rotation)
    """
    
    def __init__(self, alpaca_client, max_universe_size: int = 100):
        self.alpaca = alpaca_client
        self.max_size = max_universe_size
        self.universe: Dict[str, UniverseStock] = {}
        
    def build_universe(self, watchlist: List[str]) -> List[str]:
        """Build dynamic trading universe with priority ordering."""
        # 1. Add current positions (Priority 1 - always track)
        # 2. Add watchlist (Priority 2 - user-configured)
        # 3. Add sector leaders (Priority 2 - diversification)
        # 4. Add high volume stocks (Priority 3 - liquidity)
        # 5. Add recent movers (Priority 3 - momentum)
        return list(self.universe.keys())
```

### Data Structure: `UniverseStock`

```python
@dataclass
class UniverseStock:
    symbol: str
    reason: str  # Why included: "holdings", "watchlist", "sector_leader", etc.
    priority: int  # 1=highest (positions), 2=watchlist, 3=discovered
    sector: Optional[str] = None
    market_cap: Optional[float] = None
    avg_volume: Optional[float] = None
    added_at: Optional[datetime] = None
```

## 🏗️ Universe Composition

### Priority Tiers

**Priority 1 (Highest)**: Current Holdings
- Always tracked (what we own)
- First to receive news updates
- Example: `AAPL, GOOGL` (if held)

**Priority 2**: Watchlist + Sector Leaders
- User-configured watchlist
- Top 3 stocks per sector (10 sectors × 3 = 30 stocks)
- Ensures diversification
- Example: `MSFT, NVDA, TSLA` (watchlist) + `JPM, UNH, XOM` (sector leaders)

**Priority 3**: Discovered Stocks
- High-volume stocks (liquidity/activity)
- Recent movers (volatility/momentum)
- Fills remaining slots to reach 100
- Example: `PLTR, COIN, GME` (high volume), `SHOP, SNOW, MRNA` (volatile)

### Sector Coverage (10 Sectors)

```python
sector_leaders = {
    'Technology': ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'META', ...],
    'Healthcare': ['UNH', 'JNJ', 'LLY', 'ABBV', 'TMO', ...],
    'Financial': ['JPM', 'BAC', 'V', 'MA', 'GS', ...],
    'Consumer': ['AMZN', 'WMT', 'HD', 'NKE', 'MCD', ...],
    'Energy': ['XOM', 'CVX', 'COP', 'EOG', 'SLB', ...],
    'Industrial': ['CAT', 'BA', 'UNP', 'HON', 'GE', ...],
    'Communication': ['META', 'DIS', 'CMCSA', 'NFLX', 'T', ...],
    'Materials': ['LIN', 'APD', 'ECL', 'SHW', 'FCX', ...],
    'Utilities': ['NEE', 'DUK', 'SO', 'D', 'AEP', ...],
    'Real Estate': ['PLD', 'AMT', 'CCI', 'EQIX', 'PSA', ...]
}
```

## 🚀 Usage

### Automatic Integration (Overnight News)

The system automatically uses dynamic universe in `scheduled_tasks.py`:

```python
def start_news_collection(self) -> Dict[str, Any]:
    """Start overnight news collection (4:00 PM)."""
    
    # Build dynamic universe (100 stocks)
    universe_mgr = get_universe_manager(self.alpaca, max_size=100)
    
    # Try cache first (avoid rebuilding every 30 min)
    symbols = universe_mgr.load_cache()
    
    if not symbols:
        # Build fresh universe
        watchlist = list(settings.data.symbols)
        symbols = universe_mgr.build_universe(watchlist)
    
    logger.info(f"🌍 Tracking {len(symbols)} symbols in dynamic universe")
    
    # Initialize news collection
    timeline_mgr = get_timeline_manager()
    result = timeline_mgr.start_overnight_collection(symbols)
    
    return result
```

### Manual Usage

```python
from wawatrader.universe_manager import get_universe_manager
from wawatrader.alpaca_client import AlpacaClient

# Initialize
alpaca = AlpacaClient()
universe_mgr = get_universe_manager(alpaca, max_size=100)

# Build universe
watchlist = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
symbols = universe_mgr.build_universe(watchlist)

print(f"Tracking {len(symbols)} stocks")
# Output: Tracking 100 stocks

# Get priority breakdown
by_priority = universe_mgr.get_by_priority()
print(f"Holdings: {len(by_priority[1])}")
print(f"Watchlist/Sectors: {len(by_priority[2])}")
print(f"Discovered: {len(by_priority[3])}")
```

### Promotion Feature

Add stocks to universe based on news analysis:

```python
# After LLM identifies positive news
promoted_symbols = ['AMZN', 'META', 'NFLX']
universe_mgr.add_to_watchlist(
    symbols=promoted_symbols,
    reason="positive_news_promotion"
)

# Automatically saved to cache
# Will be included in next news collection cycle
```

## 🗄️ Caching System

### Purpose
Avoid rebuilding universe every 30 minutes during overnight news collection.

### Cache File
Location: `trading_data/universe_cache.json`

Structure:
```json
{
  "timestamp": "2025-10-24T16:00:00",
  "max_size": 100,
  "universe": [
    {
      "symbol": "AAPL",
      "reason": "watchlist",
      "priority": 2,
      "sector": null,
      "added_at": "2025-10-24T16:00:00"
    },
    ...
  ]
}
```

### Cache Lifetime
- **Valid**: 24 hours
- **Rebuild**: After 24 hours or if manually deleted
- **Updates**: On promotion (add_to_watchlist)

### Load Cache

```python
# Automatic in scheduled_tasks
symbols = universe_mgr.load_cache()

if not symbols:
    # Cache expired or missing → rebuild
    symbols = universe_mgr.build_universe(watchlist)
```

## 📊 Configuration

### Settings

Added to `config/settings.py`:

```python
class SystemConfig(BaseModel):
    # ... existing fields ...
    
    # Dynamic Universe Configuration
    universe_size: int = Field(
        default=100, 
        ge=10, 
        le=500, 
        description="Number of stocks to track for news"
    )
    universe_cache_hours: int = Field(
        default=24, 
        ge=1, 
        le=168, 
        description="Hours to cache universe"
    )
```

### Environment Variables

Optional override in `.env`:
```bash
# Universe configuration
UNIVERSE_SIZE=100
UNIVERSE_CACHE_HOURS=24
```

## 🧪 Testing

### Test Suite: `scripts/test_dynamic_universe.py`

**6 comprehensive tests:**

1. ✅ **Universe Building**: Constructs 100-stock universe
2. ✅ **Sector Coverage**: Validates diversification (10 sectors)
3. ✅ **Composition Breakdown**: Verifies reason distribution
4. ✅ **Cache Functionality**: Tests save/load cycle
5. ✅ **Watchlist Promotion**: Tests dynamic additions
6. ✅ **Integration**: End-to-end validation

**Run tests:**
```bash
python scripts/test_dynamic_universe.py
```

**Expected Output:**
```
✅ ALL TESTS PASSED
🌍 Dynamic Universe System Ready
   • Universe size: 100 stocks
   • Includes: Holdings + Watchlist + Sector Leaders + Volume Leaders + Movers
   • Cache: Enabled (24h validity)
   • Promotion: Ready for news-based additions

📰 System will now track 100 stocks overnight
   instead of just 5-10 stocks!
```

## 📈 Performance Impact

### API Calls (Alpaca News API)

**Before**: 5-10 stocks × 10 articles = 50-100 API calls/night
**After**: 100 stocks × 10 articles = 1000 API calls/night

**Alpaca Limits**: 200 requests/minute
**Our Usage**: ~50 requests/minute (well under limit)
**Conclusion**: ✅ No problem

### LLM Processing (LM Studio)

**Before**: 5-10 syntheses × 10 sec = 1-2 minutes
**After**: 100 syntheses × 10 sec = 17 minutes

**Available Time**: 4 PM - 9:30 AM = 17.5 hours
**Our Usage**: ~17 minutes
**Conclusion**: ✅ Plenty of time

### Storage

**Before**: ~50-100 news articles/night
**After**: ~1000 news articles/night

**Storage**: ~1 MB per night (negligible)
**Conclusion**: ✅ No problem

## 🎯 Benefits

### 1. Comprehensive Market Coverage
- **Before**: Blind to 99% of market (only 5-10 stocks)
- **After**: Visibility into 100 stocks across all sectors

### 2. Opportunity Discovery
- **Before**: Can only act on watchlist stocks
- **After**: Can discover and act on any of 100 stocks

### 3. Portfolio Rotation
- **Before**: "HOLD AAPL" (no alternatives known)
- **After**: "SELL AAPL → BUY META" (comparative analysis possible)

### 4. Sector Diversification
- **Before**: Watchlist might be tech-heavy
- **After**: Automatic coverage of all 10 sectors

### 5. Intelligent Watchlist
- **Before**: Static, user must manually add stocks
- **After**: Dynamic, system promotes stocks with positive news

## 🔄 Future Enhancements

### Phase 3B: LLM Comparative Analysis (Planned)

```python
# wawatrader/llm_bridge.py (future enhancement)
def compare_opportunities(
    self, 
    syntheses: Dict[str, NarrativeSynthesis],
    current_holdings: List[str]
) -> Dict[str, Any]:
    """
    Compare all 100 news syntheses and rank opportunities.
    
    Returns:
        {
            "top_10_opportunities": [ranked list],
            "rotation_recommendations": [
                {"sell": "GOOGL", "buy": "META", "reason": "..."}
            ],
            "keep_holdings": [list with reasons],
            "watchlist_additions": [symbols to add]
        }
    """
```

### Phase 3C: Dynamic Discovery (Future)

- Real-time top movers from Alpaca API
- Unusual volume detection
- Earnings calendar integration
- Social sentiment trending stocks

### Phase 3D: ML-Based Selection (Future)

- Predict which stocks will have news
- Learn from historical patterns
- Optimize universe composition

## 📝 Code Files

### Created
- **`wawatrader/universe_manager.py`** (401 lines)
  - `UniverseManager` class
  - `UniverseStock` dataclass
  - Sector leader definitions
  - Cache management

### Modified
- **`wawatrader/scheduled_tasks.py`** (lines 297-349)
  - `start_news_collection()` updated to use dynamic universe
  - Added universe_mgr initialization
  - Added priority logging

- **`config/settings.py`** (lines 70-91)
  - Added `universe_size` config
  - Added `universe_cache_hours` config

### Tests
- **`scripts/test_dynamic_universe.py`** (238 lines)
  - 6 comprehensive test cases
  - Integration validation
  - Cache testing

### Documentation
- **`docs/DYNAMIC_UNIVERSE.md`** (this file)
  - Complete architecture
  - Usage examples
  - Performance analysis

## 🎉 Summary

**The dynamic universe system transforms WawaTrader from a narrow-focus tool (5-10 stocks) into a comprehensive market intelligence platform (100 stocks).**

Key achievements:
- ✅ 10-20x increase in market coverage (5-10 → 100 stocks)
- ✅ Automatic sector diversification (10 sectors)
- ✅ Intelligent stock discovery (volume + volatility)
- ✅ Dynamic watchlist management (news-based promotion)
- ✅ Efficient caching (avoid rebuilds)
- ✅ Configurable universe size (10-500 stocks)
- ✅ Zero performance impact (within API limits)
- ✅ Fully tested (6/6 tests passing)

**Next step**: Integrate with Phase 3 LLM comparative analysis to enable portfolio rotation recommendations ("SELL X → BUY Y based on news").

---

**Version**: 1.0
**Date**: October 24, 2025
**Status**: ✅ Production Ready
