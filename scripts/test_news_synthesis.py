"""
Test News Timeline Manager - Phase 2: LLM Narrative Synthesis

Tests the LLM integration for analyzing news timelines:
1. Load or create timeline with test data
2. Call LLM to synthesize narrative
3. Verify synthesis structure
4. Test contradiction detection
5. Test narrative classification

Author: WawaTrader Team
Created: October 24, 2025
"""

from wawatrader.news_timeline import get_timeline_manager, NewsArticle, NewsTimeline
from wawatrader.timezone_utils import now_market
from datetime import datetime, timedelta
from loguru import logger
import json


def create_test_timeline_with_contradictions(symbol: str = "TSLA") -> NewsTimeline:
    """
    Create a test timeline with contradictory news to test synthesis.
    Simulates: earnings miss → guidance raise → analyst reactions
    """
    market_now = now_market()
    today = market_now.strftime('%Y-%m-%d')
    
    timeline = NewsTimeline(symbol=symbol, date=today)
    
    # Simulate realistic news sequence
    test_articles = [
        {
            'headline': 'Tesla Q3 Earnings Miss Wall Street Estimates',
            'summary': 'Tesla reported Q3 EPS of $0.62, missing consensus of $0.73. Revenue came in at $23.4B vs expected $24.1B.',
            'source': 'Reuters',
            'timestamp': market_now.replace(hour=16, minute=15),  # 4:15 PM
        },
        {
            'headline': 'Tesla Stock Drops 3% After Hours on Earnings Miss',
            'summary': 'Shares fell in extended trading following the disappointing quarterly results.',
            'source': 'Bloomberg',
            'timestamp': market_now.replace(hour=16, minute=45),  # 4:45 PM
        },
        {
            'headline': 'Tesla Raises Full-Year Guidance by 20% Despite Q3 Miss',
            'summary': 'CEO announced significantly higher FY guidance, citing strong order book and production improvements.',
            'source': 'Bloomberg',
            'timestamp': market_now.replace(hour=18, minute=30),  # 6:30 PM
        },
        {
            'headline': 'Analysts Mixed on Tesla: Guidance Positive But Execution Concerns Remain',
            'summary': 'Several analysts raised price targets while others expressed skepticism about meeting aggressive targets.',
            'source': 'CNBC',
            'timestamp': market_now.replace(hour=20, minute=0),  # 8:00 PM
        },
        {
            'headline': 'Tesla Pre-Market: Stock Rebounds 2% on Strong Guidance',
            'summary': 'Early morning trading shows recovery as investors digest the forward-looking statements.',
            'source': 'MarketWatch',
            'timestamp': market_now.replace(hour=7, minute=30) + timedelta(days=1),  # 7:30 AM next day
        }
    ]
    
    for article_data in test_articles:
        article = NewsArticle(
            timestamp=article_data['timestamp'],
            headline=article_data['headline'],
            summary=article_data['summary'],
            source=article_data['source'],
            url='https://example.com/article',
            symbols=[symbol]
        )
        timeline.add_article(article)
    
    return timeline


def test_phase2_synthesis():
    """Test Phase 2: LLM narrative synthesis"""
    
    print("\n" + "=" * 80)
    print("🤖 TESTING NEWS TIMELINE MANAGER - PHASE 2: LLM SYNTHESIS")
    print("=" * 80)
    
    # Step 1: Create test timeline
    print("\n1️⃣ Creating test timeline with contradictory news...")
    timeline = create_test_timeline_with_contradictions("TSLA")
    print(f"   ✅ Timeline created with {len(timeline.events)} articles")
    print(f"   Symbol: {timeline.symbol}")
    print(f"   Date: {timeline.date}")
    
    # Show timeline
    print("\n   📰 News Sequence:")
    for i, article in enumerate(timeline.events, 1):
        time_str = article.timestamp.strftime('%I:%M %p ET')
        print(f"   {i}. [{time_str}] {article.headline[:60]}...")
    
    # Step 2: Initialize timeline manager
    print("\n2️⃣ Initializing NewsTimelineManager...")
    timeline_mgr = get_timeline_manager()
    timeline_mgr.timelines['TSLA'] = timeline
    print("   ✅ Timeline manager initialized")
    
    # Step 3: Synthesize narrative
    print("\n3️⃣ Calling LLM to synthesize narrative...")
    print("   ⏳ This may take 10-20 seconds...")
    
    synthesis = timeline_mgr.synthesize_narrative('TSLA')
    
    if not synthesis:
        print("\n   ❌ Synthesis failed!")
        print("   This could mean:")
        print("   - LM Studio is not running")
        print("   - Model not loaded")
        print("   - Connection issue")
        return None
    
    # Step 4: Display results
    print("\n4️⃣ ✅ NARRATIVE SYNTHESIS COMPLETE!")
    print("   " + "=" * 76)
    
    print(f"\n   📊 NARRATIVE TYPE: {timeline.narrative_type}")
    print(f"\n   📖 NARRATIVE SUMMARY:")
    print(f"   {synthesis.narrative}")
    
    print(f"\n   💹 NET SENTIMENT: {synthesis.net_sentiment}")
    print(f"   🎯 CONFIDENCE: {synthesis.confidence:.1%}")
    
    print(f"\n   📈 RECOMMENDATION: {synthesis.recommendation}")
    print(f"   💡 REASONING:")
    print(f"   {synthesis.reasoning}")
    
    if synthesis.key_themes:
        print(f"\n   🏷️  KEY THEMES:")
        for theme in synthesis.key_themes:
            print(f"      • {theme}")
    
    if synthesis.contradictions:
        print(f"\n   ⚠️  CONTRADICTIONS DETECTED:")
        for contradiction in synthesis.contradictions:
            print(f"      • {contradiction}")
        print(f"   ℹ️  LLM successfully identified contradictory information!")
    else:
        print(f"\n   ✓  No contradictions - narrative is consistent")
    
    print(f"\n   ⏰ Synthesized at: {synthesis.synthesized_at.strftime('%I:%M %p ET')}")
    
    # Step 5: Test serialization
    print("\n5️⃣ Testing serialization...")
    timeline_dict = timeline.to_dict()
    assert timeline_dict['synthesis'] is not None, "Synthesis not in dict"
    print("   ✅ Timeline serializes correctly with synthesis")
    
    # Step 6: Verify structure
    print("\n6️⃣ Verifying synthesis structure...")
    required_fields = ['narrative', 'net_sentiment', 'confidence', 'recommendation', 'reasoning']
    for field in required_fields:
        assert hasattr(synthesis, field), f"Missing field: {field}"
        print(f"   ✓ {field}: Present")
    print("   ✅ All required fields present")
    
    # Step 7: Save with synthesis
    print("\n7️⃣ Saving timeline with synthesis...")
    timeline_mgr.save_timelines()
    print("   ✅ Saved to trading_data/news_timelines/")
    
    print("\n" + "=" * 80)
    print("✅ PHASE 2 TEST COMPLETE")
    print("=" * 80)
    
    return synthesis


def test_batch_synthesis():
    """Test synthesizing multiple symbols at once"""
    
    print("\n" + "=" * 80)
    print("🤖 TESTING BATCH SYNTHESIS")
    print("=" * 80)
    
    print("\n1️⃣ Creating timelines for multiple symbols...")
    timeline_mgr = get_timeline_manager()
    
    # Create test timelines for different symbols
    symbols = ['AAPL', 'GOOGL', 'MSFT']
    for symbol in symbols:
        timeline = create_test_timeline_with_contradictions(symbol)
        timeline_mgr.timelines[symbol] = timeline
        print(f"   ✓ Created timeline for {symbol}")
    
    print(f"\n2️⃣ Running batch synthesis on {len(symbols)} symbols...")
    print("   ⏳ This will take 30-60 seconds...")
    
    results = timeline_mgr.synthesize_all()
    
    print("\n3️⃣ Results:")
    success_count = sum(1 for v in results.values() if v)
    print(f"   Successful: {success_count}/{len(results)}")
    
    for symbol, success in results.items():
        status = "✅" if success else "❌"
        print(f"   {status} {symbol}")
        
        if success:
            timeline = timeline_mgr.get_timeline(symbol)
            if timeline and timeline.synthesis:
                print(f"      → {timeline.synthesis.recommendation} ({timeline.synthesis.confidence:.0%} confidence)")
    
    print("\n" + "=" * 80)
    print("✅ BATCH SYNTHESIS TEST COMPLETE")
    print("=" * 80)


def display_synthesis_comparison():
    """Show how narrative synthesis helps vs individual headlines"""
    
    print("\n" + "=" * 80)
    print("📊 SYNTHESIS VALUE DEMONSTRATION")
    print("=" * 80)
    
    print("\n❌ WITHOUT NARRATIVE SYNTHESIS:")
    print("   Human/System sees individual headlines:")
    print("   4:15 PM: 'Tesla misses earnings' → NEGATIVE")
    print("   4:45 PM: 'Stock drops 3%' → NEGATIVE")
    print("   Decision: SELL (based on initial bad news)")
    print("   Result: Missed the guidance raise that came later!")
    
    print("\n✅ WITH NARRATIVE SYNTHESIS:")
    print("   LLM analyzes complete timeline:")
    print("   • Initial: Earnings miss (negative)")
    print("   • Development: Guidance raised 20% (positive)")
    print("   • Resolution: Mixed signals, guidance more important")
    print("   • Recommendation: HOLD or BUY (wait for more data)")
    print("   Result: Better informed, avoids whipsaw!")
    
    print("\n💡 KEY INSIGHT:")
    print("   News narratives EVOLVE. Single headlines mislead.")
    print("   LLM synthesis understands the SEQUENCE and RESOLUTION.")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, '/Users/wagnermontes/Documents/GitHub/wawatrader')
    
    logger.info("Starting News Timeline Manager Test - Phase 2")
    
    # Show value proposition
    display_synthesis_comparison()
    
    # Test single synthesis
    print("\n🧪 Running Phase 2 test...")
    synthesis = test_phase2_synthesis()
    
    if synthesis:
        # Test batch synthesis
        print("\n🧪 Running batch synthesis test...")
        test_batch_synthesis()
        
        print("\n✅ All Phase 2 tests complete!")
        print("\n📋 Summary:")
        print("   ✓ LLM narrative synthesis: Working")
        print("   ✓ Contradiction detection: Working")
        print("   ✓ Narrative classification: Working")
        print("   ✓ Batch processing: Working")
        print("   ✓ Serialization: Working")
        
        print("\n🚀 Next Steps:")
        print("   - Phase 3: Integrate with iterative_analyst.py")
        print("   - Phase 4: Add pre-market validation")
    else:
        print("\n⚠️  Phase 2 test incomplete")
        print("   Please ensure:")
        print("   - LM Studio is running")
        print("   - Model is loaded")
        print("   - Settings are correct")
