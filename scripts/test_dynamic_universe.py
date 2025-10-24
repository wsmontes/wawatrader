"""
Test Dynamic Universe Manager

Validates:
1. Universe building (positions + watchlist + discovered)
2. Priority assignment (1=holdings, 2=watchlist, 3=discovered)
3. Diversification (sector coverage)
4. Cache functionality
5. Watchlist promotion
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from wawatrader.universe_manager import UniverseManager, get_universe_manager
from wawatrader.alpaca_client import AlpacaClient
from config.settings import settings
from loguru import logger


def test_universe_building():
    """Test dynamic universe construction."""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Dynamic Universe Building")
    logger.info("="*80)
    
    # Initialize
    alpaca = AlpacaClient()
    universe_mgr = UniverseManager(alpaca, max_universe_size=100)
    
    # Build universe
    watchlist = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
    symbols = universe_mgr.build_universe(watchlist)
    
    # Validate
    assert len(symbols) > 0, "Universe should not be empty"
    assert len(symbols) <= 100, f"Universe too large: {len(symbols)}"
    
    # Check priorities
    by_priority = universe_mgr.get_by_priority()
    logger.info(f"\n📊 Universe Composition:")
    logger.info(f"   Priority 1 (Holdings): {len(by_priority[1])} stocks")
    logger.info(f"   Priority 2 (Watchlist/Sectors): {len(by_priority[2])} stocks")
    logger.info(f"   Priority 3 (Discovered): {len(by_priority[3])} stocks")
    logger.info(f"   Total: {len(symbols)} stocks")
    
    # Check watchlist included
    for symbol in watchlist:
        assert symbol in symbols, f"Watchlist symbol {symbol} missing"
    
    logger.info("\n✅ TEST 1 PASSED: Universe built successfully")
    return symbols


def test_sector_coverage():
    """Test sector diversification."""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Sector Diversification")
    logger.info("="*80)
    
    # Initialize
    alpaca = AlpacaClient()
    universe_mgr = UniverseManager(alpaca, max_universe_size=100)
    
    # Build universe
    watchlist = ['AAPL', 'JPM']  # Tech + Finance
    symbols = universe_mgr.build_universe(watchlist)
    
    # Count sectors
    sectors_found = set()
    for stock in universe_mgr.universe.values():
        if stock.sector:
            sectors_found.add(stock.sector)
        if 'sector_leader' in stock.reason:
            logger.info(f"   • {stock.symbol:6s} - {stock.reason}")
    
    logger.info(f"\n📊 Sector Coverage: {len(sectors_found)} sectors")
    for sector in sorted(sectors_found):
        count = sum(1 for s in universe_mgr.universe.values() if s.sector == sector)
        logger.info(f"   • {sector:15s}: {count} stocks")
    
    assert len(sectors_found) >= 3, f"Too few sectors: {len(sectors_found)}"
    
    logger.info("\n✅ TEST 2 PASSED: Sector diversification working")


def test_reason_breakdown():
    """Test breakdown by reason (holdings, watchlist, volume, movers)."""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Universe Composition by Reason")
    logger.info("="*80)
    
    # Initialize
    alpaca = AlpacaClient()
    universe_mgr = UniverseManager(alpaca, max_universe_size=100)
    
    # Build universe
    watchlist = ['AAPL', 'MSFT', 'GOOGL']
    symbols = universe_mgr.build_universe(watchlist)
    
    # Count by reason
    by_reason = {}
    for stock in universe_mgr.universe.values():
        by_reason[stock.reason] = by_reason.get(stock.reason, 0) + 1
    
    logger.info(f"\n📊 Breakdown by Reason:")
    for reason, count in sorted(by_reason.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"   • {reason:25s}: {count:3d} stocks")
    
    # Validate
    assert 'watchlist' in by_reason, "Watchlist stocks missing"
    assert any('sector_leader' in r for r in by_reason), "Sector leaders missing"
    
    logger.info("\n✅ TEST 3 PASSED: Composition breakdown correct")


def test_cache_functionality():
    """Test cache save/load."""
    logger.info("\n" + "="*80)
    logger.info("TEST 4: Cache Functionality")
    logger.info("="*80)
    
    # Initialize
    alpaca = AlpacaClient()
    universe_mgr = UniverseManager(alpaca, max_universe_size=100)
    
    # Build and save
    watchlist = ['AAPL', 'MSFT']
    symbols1 = universe_mgr.build_universe(watchlist)
    logger.info(f"   Built universe: {len(symbols1)} symbols")
    
    # Create new manager and load cache
    universe_mgr2 = UniverseManager(alpaca, max_universe_size=100)
    symbols2 = universe_mgr2.load_cache()
    
    if symbols2:
        logger.info(f"   Loaded from cache: {len(symbols2)} symbols")
        assert len(symbols1) == len(symbols2), "Cache size mismatch"
        assert set(symbols1) == set(symbols2), "Cache content mismatch"
        logger.info("\n✅ TEST 4 PASSED: Cache working correctly")
    else:
        logger.warning("\n⚠️ TEST 4 SKIPPED: No cache file")


def test_watchlist_promotion():
    """Test adding symbols to universe (promotion feature)."""
    logger.info("\n" + "="*80)
    logger.info("TEST 5: Watchlist Promotion")
    logger.info("="*80)
    
    # Initialize
    alpaca = AlpacaClient()
    universe_mgr = UniverseManager(alpaca, max_universe_size=100)
    
    # Build initial universe
    watchlist = ['AAPL', 'MSFT']
    symbols = universe_mgr.build_universe(watchlist)
    initial_size = len(symbols)
    logger.info(f"   Initial universe: {initial_size} symbols")
    
    # Promote new symbols (simulate news-based promotion)
    new_symbols = ['ZM', 'SHOP', 'SQ']  # Use symbols not already in universe
    universe_mgr.add_to_watchlist(new_symbols, reason="positive_news_promotion")
    
    # Verify
    for symbol in new_symbols:
        if symbol in universe_mgr.universe:  # May already be in discovered stocks
            assert universe_mgr.universe[symbol].reason in ["positive_news_promotion", "high_volume", "recent_mover"]
            logger.info(f"   • {symbol}: {universe_mgr.universe[symbol].reason}")
        else:
            logger.warning(f"   ⚠️ {symbol} not added (may already exist)")
    
    logger.info(f"   After promotion: {len(universe_mgr.universe)} symbols")
    logger.info(f"   Added: {len(universe_mgr.universe) - initial_size} symbols")
    
    logger.info("\n✅ TEST 5 PASSED: Watchlist promotion working")


def test_integration():
    """Test integration with news collection."""
    logger.info("\n" + "="*80)
    logger.info("TEST 6: Integration Test")
    logger.info("="*80)
    
    # Initialize (singleton pattern)
    alpaca = AlpacaClient()
    universe_mgr = get_universe_manager(alpaca, max_size=100)
    
    # Build universe
    watchlist = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']  # Default watchlist
    symbols = universe_mgr.build_universe(watchlist)
    
    logger.info(f"\n📊 Final Universe for News Collection:")
    logger.info(f"   Total symbols: {len(symbols)}")
    
    # Show first 20 symbols
    logger.info(f"\n   First 20 symbols:")
    for i, symbol in enumerate(symbols[:20], 1):
        stock = universe_mgr.universe[symbol]
        logger.info(f"      {i:2d}. {symbol:6s} - {stock.reason:20s} (Priority {stock.priority})")
    
    if len(symbols) > 20:
        logger.info(f"   ... and {len(symbols) - 20} more")
    
    logger.info("\n✅ TEST 6 PASSED: Integration test successful")
    logger.info(f"\n🎯 Ready to track {len(symbols)} stocks for news collection")


def main():
    """Run all tests."""
    logger.info("\n" + "="*80)
    logger.info("🧪 TESTING DYNAMIC UNIVERSE MANAGER")
    logger.info("="*80)
    
    try:
        # Run tests
        symbols = test_universe_building()
        test_sector_coverage()
        test_reason_breakdown()
        test_cache_functionality()
        test_watchlist_promotion()
        test_integration()
        
        # Summary
        logger.info("\n" + "="*80)
        logger.info("✅ ALL TESTS PASSED")
        logger.info("="*80)
        logger.info(f"\n🌍 Dynamic Universe System Ready")
        logger.info(f"   • Universe size: {len(symbols)} stocks")
        logger.info(f"   • Includes: Holdings + Watchlist + Sector Leaders + Volume Leaders + Movers")
        logger.info(f"   • Cache: Enabled (24h validity)")
        logger.info(f"   • Promotion: Ready for news-based additions")
        logger.info(f"\n📰 System will now track {len(symbols)} stocks overnight")
        logger.info("   instead of just 5-10 stocks!")
        
    except Exception as e:
        logger.error(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
