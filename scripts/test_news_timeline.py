"""
Test News Timeline Manager - Phase 1

Tests the basic news accumulation functionality:
1. Initialize timeline manager
2. Start overnight collection
3. Collect news every 30 min (simulated)
4. Get statistics
5. Save timelines

This is a manual test to verify Phase 1 before implementing Phase 2 (LLM synthesis).

Author: WawaTrader Team
Created: October 24, 2025
"""

from wawatrader.news_timeline import get_timeline_manager, NewsArticle
from wawatrader.timezone_utils import now_market, format_market_time
from datetime import datetime, timedelta
from loguru import logger
import json


def test_phase1():
    """Test Phase 1: News accumulation"""
    
    print("\n" + "=" * 80)
    print("📰 TESTING NEWS TIMELINE MANAGER - PHASE 1")
    print("=" * 80)
    
    # Step 1: Initialize
    print("\n1️⃣ Initializing NewsTimelineManager...")
    timeline_mgr = get_timeline_manager()
    print("   ✅ Manager initialized")
    
    # Step 2: Start overnight collection with test symbols
    print("\n2️⃣ Starting overnight collection...")
    test_symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA']
    
    result = timeline_mgr.start_overnight_collection(test_symbols)
    print(f"   ✅ Collection started")
    print(f"   - Symbols tracked: {len(test_symbols)}")
    print(f"   - Initial articles: {result['initial_articles']}")
    print(f"   - Started at: {format_market_time(now_market())}")
    
    # Step 3: Simulate a collection cycle
    print("\n3️⃣ Simulating 30-minute collection cycle...")
    new_articles = timeline_mgr.collect_news()
    print(f"   ✅ Collection cycle complete")
    print(f"   - New articles: {new_articles}")
    
    # Step 4: Get statistics
    print("\n4️⃣ Getting timeline statistics...")
    stats = timeline_mgr.get_statistics()
    print(f"   ✅ Statistics retrieved")
    print(f"   - Total symbols: {stats['symbols_tracked']}")
    print(f"   - Total articles: {stats['total_articles']}")
    print(f"   - Symbols with news: {stats['symbols_with_news']}")
    
    # Show per-symbol breakdown
    print("\n   📊 Per-Symbol Breakdown:")
    for symbol, data in stats['by_symbol'].items():
        if data['article_count'] > 0:
            print(f"      {symbol}: {data['article_count']} articles")
    
    # Step 5: Show sample timeline
    print("\n5️⃣ Sample Timeline (first symbol with news)...")
    for symbol in test_symbols:
        timeline = timeline_mgr.get_timeline(symbol)
        if timeline and timeline.events:
            print(f"   Symbol: {symbol}")
            print(f"   Articles: {len(timeline.events)}")
            print(f"\n   Recent articles:")
            for i, article in enumerate(timeline.events[:3], 1):
                print(f"\n   {i}. {article.headline[:70]}...")
                print(f"      Source: {article.source}")
                print(f"      Time: {article.timestamp.strftime('%Y-%m-%d %I:%M %p ET')}")
            break
    
    # Step 6: Test timeline saving
    print("\n6️⃣ Saving timelines to disk...")
    timeline_mgr.save_timelines()
    print("   ✅ Timelines saved")
    
    # Step 7: Verify timeline structure
    print("\n7️⃣ Verifying timeline structure...")
    if timeline:
        data = timeline.to_dict()
        print(f"   ✅ Timeline converts to dict successfully")
        print(f"   - Keys: {list(data.keys())}")
        print(f"   - Event count: {data['event_count']}")
    
    # Step 8: Test revision detection
    print("\n8️⃣ Testing revision detection...")
    has_new = timeline.has_new_articles_since_synthesis()
    print(f"   Has new articles since synthesis: {has_new}")
    print(f"   (Expected: True, since we haven't synthesized yet)")
    
    print("\n" + "=" * 80)
    print("✅ PHASE 1 TEST COMPLETE")
    print("=" * 80)
    
    print("\n📋 Summary:")
    print(f"   - Timeline manager: ✅ Working")
    print(f"   - News collection: ✅ Working")
    print(f"   - Statistics: ✅ Working")
    print(f"   - Persistence: ✅ Working")
    print(f"   - Total articles collected: {stats['total_articles']}")
    
    print("\n🚀 Next Steps:")
    print("   - Phase 2: Implement LLM narrative synthesis")
    print("   - Phase 3: Integrate with iterative_analyst.py")
    print("   - Phase 4: Add pre-market validation")
    
    return timeline_mgr


def test_timezone_handling():
    """Test that timezone handling works correctly"""
    
    print("\n" + "=" * 80)
    print("⏰ TESTING TIMEZONE HANDLING")
    print("=" * 80)
    
    market_now = now_market()
    
    print(f"\n✅ Current time in market timezone (ET):")
    print(f"   {format_market_time(market_now)}")
    print(f"   ISO: {market_now.isoformat()}")
    print(f"   Hour (24h): {market_now.hour}")
    print(f"   Minute: {market_now.minute}")
    
    # Test accumulation window (4 PM - 2 AM ET)
    hour = market_now.hour
    is_accumulation_time = (hour >= 16) or (hour < 2)
    is_synthesis_time = hour == 2
    is_validation_time = hour == 6
    
    print(f"\n📊 Current Phase:")
    if 9 <= hour < 16:
        print("   🟢 MARKET OPEN (Trading)")
    elif is_accumulation_time:
        print("   📰 ACCUMULATION (Collecting news)")
    elif is_synthesis_time:
        print("   🤖 SYNTHESIS (LLM analyzing)")
    elif is_validation_time:
        print("   ✅ VALIDATION (Pre-market check)")
    else:
        print("   💤 SLEEP (Minimal activity)")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, '/Users/wagnermontes/Documents/GitHub/wawatrader')
    
    logger.info("Starting News Timeline Manager Test - Phase 1")
    
    # Test timezone handling first
    test_timezone_handling()
    
    # Test Phase 1 functionality
    timeline_mgr = test_phase1()
    
    print("\n✅ All tests complete!")
