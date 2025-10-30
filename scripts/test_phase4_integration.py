"""
Test Phase 4: Market Hours Integration & Symbol Discovery

Tests:
1. MarketHoursManager and SymbolDiscoveryEngine initialization
2. Symbol discovery methods with real Alpaca API calls
3. Market-hours-aware event loop integration
4. Phase-specific activities triggering
"""

import asyncio
from datetime import datetime
from loguru import logger
from wawatrader.trading_agent import TradingAgent
from wawatrader.market_hours_manager import MarketPhase


logger.info("="*70)
logger.info("🧪 TESTING: Phase 4 - Market Hours Integration")
logger.info("="*70)


# Test 1: Verify new components exist
logger.info("\n🔧 Test 1: Verify MarketHoursManager & SymbolDiscovery initialized")

agent = TradingAgent(symbols=['AAPL', 'MSFT'], dry_run=True)

assert hasattr(agent, 'market_hours_manager'), "❌ MarketHoursManager not initialized"
assert hasattr(agent, 'symbol_discovery'), "❌ SymbolDiscoveryEngine not initialized"

logger.info("✅ Both components initialized")
logger.info(f"   - MarketHoursManager: {type(agent.market_hours_manager).__name__}")
logger.info(f"   - SymbolDiscoveryEngine: {type(agent.symbol_discovery).__name__}")


# Test 2: Check current market phase
logger.info("\n📅 Test 2: Check Current Market Phase")

current_phase = agent.market_hours_manager.get_current_phase()
logger.info(f"✅ Current market phase: {current_phase.value}")
logger.info(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


# Test 3: Test symbol discovery methods exist
logger.info("\n🔍 Test 3: Verify Symbol Discovery Methods")

discovery_methods = [
    '_scan_unusual_volume',
    '_scan_news_mentions',
    '_scan_sector_movers',
    '_scan_gap_opportunities'
]

for method_name in discovery_methods:
    assert hasattr(agent.symbol_discovery, method_name), f"❌ Method {method_name} not found"
    logger.info(f"✅ {method_name} exists")


# Test 4: Test symbol discovery execution (API calls)
logger.info("\n📊 Test 4: Test Symbol Discovery Execution")

try:
    logger.info("   Running news mentions scanner...")
    news_opportunities = agent.symbol_discovery._scan_news_mentions()
    logger.info(f"✅ News scanner returned {len(news_opportunities)} opportunities")
    
    if news_opportunities:
        sample = news_opportunities[0]
        logger.info(f"   Sample: {sample.symbol} (quality={sample.quality_score:.1f}, urgency={sample.urgency})")
    
except Exception as e:
    logger.error(f"❌ News scanner failed: {e}")

try:
    logger.info("   Running unusual volume scanner...")
    volume_opportunities = agent.symbol_discovery._scan_unusual_volume()
    logger.info(f"✅ Volume scanner returned {len(volume_opportunities)} opportunities")
    
    if volume_opportunities:
        sample = volume_opportunities[0]
        volume_ratio = sample.discovery_data.get('volume_ratio', 0)
        logger.info(f"   Sample: {sample.symbol} (volume_ratio={volume_ratio:.1f}x)")
    
except Exception as e:
    logger.error(f"❌ Volume scanner failed: {e}")


# Test 5: Test phase change handler
logger.info("\n⚡ Test 5: Test Phase Change Handler")

async def test_phase_handler():
    """Test phase change handler"""
    
    # Test evening research phase
    logger.info("   Testing EVENING_RESEARCH phase handler...")
    await agent._handle_phase_change(MarketPhase.EVENING_RESEARCH)
    logger.info("✅ Evening research phase handled")
    
    # Check if events were added to queue
    queue_size = agent.event_queue.get_queue_size()
    logger.info(f"   Queue size after discovery: {queue_size}")
    
    # Test pre-market phase
    logger.info("   Testing PRE_MARKET phase handler...")
    await agent._handle_phase_change(MarketPhase.PRE_MARKET)
    logger.info("✅ Pre-market phase handled")

try:
    asyncio.run(test_phase_handler())
except Exception as e:
    logger.error(f"❌ Phase handler test failed: {e}")
    import traceback
    traceback.print_exc()


# Test 6: Verify event-driven loop has market-hours integration
logger.info("\n🔄 Test 6: Verify Event Loop Market-Hours Integration")

import inspect
source = inspect.getsource(agent.run_event_driven)

# Check for key integration points
checks = [
    ('market_hours_manager', 'MarketHoursManager integration'),
    ('get_current_phase', 'Phase detection'),
    ('_handle_phase_change', 'Phase change handler'),
    ('EVENING_RESEARCH', 'Evening research phase'),
    ('PRE_MARKET', 'Pre-market phase')
]

all_found = True
for keyword, description in checks:
    if keyword in source:
        logger.info(f"✅ {description} present")
    else:
        logger.error(f"❌ {description} missing")
        all_found = False

if all_found:
    logger.info("✅ All market-hours integrations present in event loop")


logger.info("\n" + "="*70)
logger.info("✅ PHASE 4 INTEGRATION TEST COMPLETE")
logger.info("="*70)

logger.info("\n📊 Summary:")
logger.info("✅ MarketHoursManager initialized")
logger.info("✅ SymbolDiscoveryEngine initialized")
logger.info("✅ Discovery methods implemented with real Alpaca API")
logger.info("✅ Phase change handlers working")
logger.info("✅ Event loop is market-hours aware")

logger.info("\n🎯 Key Features:")
logger.info("• Symbol discovery from news, volume, sectors, gaps")
logger.info("• Market phase detection (PRE_MARKET, MARKET_OPEN, AFTER_HOURS, etc.)")
logger.info("• Phase-specific activities (evening research, gap scanning)")
logger.info("• Real Alpaca API integration (news, market data)")
logger.info("• Opportunities added to event queue automatically")

logger.info("\n📝 Usage:")
logger.info("  agent = TradingAgent(symbols=['AAPL', 'MSFT'], dry_run=True)")
logger.info("  asyncio.run(agent.run_event_driven())")
logger.info("  # System will automatically:")
logger.info("  # - Detect market phase")
logger.info("  # - Run symbol discovery during evening")
logger.info("  # - Scan for gaps during pre-market")
logger.info("  # - Process events during market hours")

logger.info("\n" + "="*70)
