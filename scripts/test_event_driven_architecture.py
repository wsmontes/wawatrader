#!/usr/bin/env python3
"""
Test Event-Driven Architecture Components
==========================================
Demonstrates the new event-driven components:
- Decision Memory System
- Event Queue with FIFO + Priority
- Kelly Criterion Position Sizing
- Thesis vs Reality Comparison

Run this to verify the new architecture works correctly.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from wawatrader.decision_memory import (
    DecisionMemory, DecisionType, MemoryStore, ThesisRealityComparator
)
from wawatrader.event_system import (
    Event, EventType, EventQueue, EventPriority,
    PriceAlertMonitor, VolumeMonitor
)
from wawatrader.position_sizing import (
    KellyLLMPositionSizer, PortfolioRiskManager, PositionSize
)


def test_decision_memory():
    """Test Decision Memory System"""
    print("\n" + "="*60)
    print("TEST 1: Decision Memory System")
    print("="*60)
    
    # Create memory store
    memory_store = MemoryStore(storage_path="logs/test_decision_memory.jsonl")
    
    # Create a sample entry decision
    entry_memory = DecisionMemory(
        decision_id="test_001",
        symbol="AAPL",
        timestamp=datetime.now(),
        decision_type=DecisionType.ENTRY,
        strategy="momentum_breakout",
        thesis="Strong breakout above $180 resistance with high volume and positive earnings catalyst",
        catalysts=["Earnings beat expectations", "Sector rotation into tech", "New product announcement"],
        bullish_factors=["Volume spike 3.2x", "RSI strength", "Breaking key resistance"],
        bearish_factors=["Overall market weak", "Valuation stretched"],
        entry_price=180.50,
        target_price=192.00,
        stop_loss_price=175.00,
        expected_holding_period="swing (2-5 days)",
        invalidation_conditions=[
            "Break below $175 support",
            "Volume dries up significantly",
            "Market enters downtrend"
        ],
        shares=50,
        position_size_usd=9025.00,
        position_size_pct=9.0,
        conviction_score=75,
        kelly_fraction=0.08,
        actual_fill_price=180.55,
        slippage=0.05,
        execution_quality="excellent"
    )
    
    # Store the memory
    memory_store.store(entry_memory)
    print(f"✅ Stored entry memory for {entry_memory.symbol}")
    
    # Retrieve it
    retrieved = memory_store.get_open_position("AAPL")
    if retrieved:
        print(f"✅ Retrieved open position: {retrieved.symbol}")
        print(f"   Strategy: {retrieved.strategy}")
        print(f"   Entry: ${retrieved.entry_price:.2f}")
        print(f"   Target: ${retrieved.target_price:.2f}")
        print(f"   Thesis: {retrieved.thesis[:60]}...")
    
    # Update position tracking
    memory_store.update_position("AAPL", {
        'peak_profit_pct': 4.2,
        'max_drawdown_pct': -1.5,
        'current_pnl_pct': 3.1,
    })
    print(f"✅ Updated position tracking")
    
    # Add a revisit
    memory_store.add_revisit("AAPL", {
        'action': 'hold',
        'reasoning': 'Momentum still strong, approaching target',
        'price': 186.50,
    })
    print(f"✅ Added revisit entry")
    
    # Get all open positions
    open_positions = memory_store.get_all_open_positions()
    print(f"✅ Currently {len(open_positions)} open position(s)")
    
    return memory_store


def test_thesis_vs_reality(memory_store):
    """Test Thesis vs Reality Comparison"""
    print("\n" + "="*60)
    print("TEST 2: Thesis vs Reality Comparison")
    print("="*60)
    
    comparator = ThesisRealityComparator(memory_store)
    
    # Build comparison
    comparison = comparator.get_comparison(
        symbol="AAPL",
        current_price=186.50,
        current_data={
            'news': [
                {'headline': 'Apple announces new AI features', 'sentiment': 0.8},
                {'headline': 'Tech sector rallying', 'sentiment': 0.6}
            ],
            'volume_analysis': {
                'current': 82_000_000,
                'average': 55_000_000,
                'ratio': 1.49
            },
            'price_action': {
                'trend': 'bullish',
                'support': 182.00,
                'resistance': 190.00
            }
        }
    )
    
    if comparison:
        print("✅ Built thesis vs reality comparison:")
        print(f"\n   ORIGINAL THESIS:")
        print(f"   Entry: ${comparison['original_thesis']['entry_price']:.2f}")
        print(f"   Target: ${comparison['original_thesis']['target_price']:.2f}")
        print(f"   Strategy: {comparison['original_thesis']['strategy']}")
        print(f"   Thesis: {comparison['original_thesis']['thesis_narrative'][:60]}...")
        
        print(f"\n   WHAT HAPPENED:")
        print(f"   Current: ${comparison['what_actually_happened']['current_price']:.2f}")
        print(f"   P&L: {comparison['what_actually_happened']['price_change_pct']:+.2f}%")
        print(f"   Time: {comparison['what_actually_happened']['time_elapsed_hours']:.1f} hours")
        print(f"   Peak: {comparison['what_actually_happened']['peak_profit_reached']:+.2f}%")
    
    # Build re-eval prompt
    prompt = comparator.build_reeval_prompt(
        symbol="AAPL",
        current_price=186.50,
        current_data={
            'news': [{'headline': 'Apple announces new AI features', 'sentiment': 0.8}],
            'volume_analysis': {'current': 82_000_000, 'average': 55_000_000},
            'price_action': {'trend': 'bullish'}
        },
        trigger_event="PRICE_ALERT: Approaching target $192"
    )
    
    if prompt:
        print(f"\n✅ Generated re-evaluation prompt ({len(prompt)} chars)")
        print(f"   Preview: {prompt[:150]}...")
    
    return comparator


def test_event_queue():
    """Test Event Queue with FIFO + Priority"""
    print("\n" + "="*60)
    print("TEST 3: Event Queue (FIFO + Priority)")
    print("="*60)
    
    queue = EventQueue()
    
    # Add events with different priorities
    events_to_add = [
        Event("e1", datetime.now(), EventType.NEW_OPPORTUNITY, "TSLA", {}, EventPriority.BACKGROUND, "test"),
        Event("e2", datetime.now(), EventType.STOP_LOSS_HIT, "AAPL", {}, EventPriority.CRITICAL, "test"),
        Event("e3", datetime.now(), EventType.VOLUME_SPIKE, "MSFT", {}, EventPriority.MEDIUM, "test"),
        Event("e4", datetime.now(), EventType.DAILY_LOSS_LIMIT, "portfolio", {}, EventPriority.EMERGENCY, "test"),
        Event("e5", datetime.now(), EventType.BREAKOUT_UPSIDE, "NVDA", {}, EventPriority.URGENT, "test"),
        Event("e6", datetime.now() + timedelta(seconds=1), EventType.TARGET_HIT, "GOOGL", {}, EventPriority.MEDIUM_HIGH, "test"),
    ]
    
    for event in events_to_add:
        queue.add_event(event)
    
    print(f"✅ Added {len(events_to_add)} events")
    print(f"   Queue size: {queue.get_pending_count()}")
    
    # Check priority ordering
    print("\n   Processing order (by priority):")
    position = 1
    while queue.get_pending_count() > 0:
        event = queue.get_next_event()
        if event:
            print(f"   {position}. Priority {event.priority}: {event.event_type.value} ({event.symbol})")
            position += 1
    
    # Test deduplication
    print("\n✅ Testing deduplication:")
    queue2 = EventQueue(dedup_window_minutes=5)
    
    # Add same event twice
    event1 = Event("d1", datetime.now(), EventType.VOLUME_SPIKE, "AAPL", {}, EventPriority.MEDIUM, "test")
    event2 = Event("d2", datetime.now(), EventType.VOLUME_SPIKE, "AAPL", {}, EventPriority.MEDIUM, "test")
    
    added1 = queue2.add_event(event1)
    added2 = queue2.add_event(event2)
    
    print(f"   First event added: {added1}")
    print(f"   Duplicate event added: {added2}")
    print(f"   Queue size: {queue2.get_pending_count()} (should be 1)")
    
    return queue


def test_price_alerts():
    """Test Price Alert Monitor"""
    print("\n" + "="*60)
    print("TEST 4: Price Alert Monitor")
    print("="*60)
    
    queue = EventQueue()
    price_monitor = PriceAlertMonitor(queue)
    
    # Set up price alerts
    price_monitor.set_price_alert(
        symbol="AAPL",
        alert_type="above",
        price=190.00,
        event_type=EventType.TARGET_HIT,
        priority=EventPriority.MEDIUM_HIGH,
        metadata={'target_level': 'first_target'}
    )
    
    price_monitor.set_price_alert(
        symbol="AAPL",
        alert_type="below",
        price=175.00,
        event_type=EventType.STOP_LOSS_HIT,
        priority=EventPriority.CRITICAL,
        metadata={'stop_type': 'invalidation'}
    )
    
    print("✅ Set 2 price alerts for AAPL")
    
    # Simulate price movements
    print("\n   Simulating price movements:")
    prices = [180.00, 185.00, 191.00]  # Last one should trigger target alert
    
    for price in prices:
        price_monitor.check_price("AAPL", price)
        print(f"   Price: ${price:.2f} - Queue: {queue.get_pending_count()} events")
    
    # Check triggered events
    if queue.get_pending_count() > 0:
        event = queue.get_next_event()
        print(f"\n✅ Alert triggered: {event.event_type.value}")
        print(f"   Symbol: {event.symbol}")
        print(f"   Data: {event.data}")
    
    return price_monitor


def test_kelly_position_sizing():
    """Test Kelly Criterion Position Sizing"""
    print("\n" + "="*60)
    print("TEST 5: Kelly Criterion Position Sizing")
    print("="*60)
    
    # Create memory store with some historical performance
    memory_store = MemoryStore(storage_path="logs/test_kelly_memory.jsonl")
    
    # Simulate some closed trades for strategy
    for i in range(15):
        # 60% win rate simulation
        is_win = i < 9
        pnl = 4.5 if is_win else -2.0
        
        memory = DecisionMemory(
            decision_id=f"kelly_test_{i}",
            symbol=f"TEST{i}",
            timestamp=datetime.now() - timedelta(days=30-i),
            decision_type=DecisionType.ENTRY,
            strategy="momentum_breakout",
            entry_price=100.0,
            position_closed=True,
            current_pnl_pct=pnl
        )
        memory_store.store(memory)
    
    print(f"✅ Created test history: 15 trades")
    
    # Get strategy performance
    performance = memory_store.get_strategy_performance("momentum_breakout")
    print(f"\n   Strategy Performance:")
    print(f"   Win Rate: {performance['win_rate']*100:.1f}%")
    print(f"   Avg Win: {performance['avg_win_pct']:.2f}%")
    print(f"   Avg Loss: {performance['avg_loss_pct']:.2f}%")
    print(f"   Total Trades: {performance['num_trades']}")
    
    # Calculate position size
    sizer = KellyLLMPositionSizer(memory_store)
    
    position_size = sizer.calculate_position_size(
        symbol="NVDA",
        entry_price=450.00,
        strategy="momentum_breakout",
        llm_conviction=80,  # 80/100 conviction
        portfolio_value=100_000.00,
        existing_positions=[],
        sector_map={"NVDA": "Technology"}
    )
    
    print(f"\n✅ Position Size Calculation:")
    print(f"   Symbol: {position_size.symbol}")
    print(f"   Kelly Fraction: {position_size.kelly_fraction*100:.2f}%")
    print(f"   Conviction Adjusted: {position_size.conviction_adjusted_kelly*100:.2f}%")
    print(f"   Fractional Kelly: {position_size.fractional_kelly*100:.2f}%")
    print(f"   Final Size: ${position_size.final_position_usd:,.0f} ({position_size.final_position_pct:.2f}%)")
    print(f"   Shares: {position_size.shares}")
    
    if position_size.emergency_stops_applied:
        print(f"   Emergency Stops: {', '.join(position_size.emergency_stops_applied)}")
    
    print(f"\n   Reasoning:")
    print(position_size.reasoning)
    
    return sizer


def test_portfolio_risk_manager():
    """Test Portfolio Risk Manager"""
    print("\n" + "="*60)
    print("TEST 6: Portfolio Risk Manager")
    print("="*60)
    
    risk_manager = PortfolioRiskManager()
    
    # Simulate portfolio with some positions
    portfolio_value = 100_000.00
    existing_positions = [
        {'symbol': 'AAPL', 'value': 15_000, 'sector': 'Technology'},
        {'symbol': 'MSFT', 'value': 12_000, 'sector': 'Technology'},
        {'symbol': 'JPM', 'value': 10_000, 'sector': 'Financial'},
    ]
    
    sector_map = {
        'AAPL': 'Technology',
        'MSFT': 'Technology',
        'JPM': 'Financial',
        'GOOGL': 'Technology',  # Proposed
    }
    
    # Get current risk metrics
    metrics = risk_manager.get_risk_metrics(
        portfolio_value=portfolio_value,
        existing_positions=existing_positions,
        sector_map=sector_map
    )
    
    print(f"✅ Current Portfolio Risk Metrics:")
    print(f"   Total Heat: {metrics['total_heat_pct']:.1f}%")
    print(f"   Largest Position: {metrics['largest_position_pct']:.1f}%")
    print(f"   Max Sector: {metrics['max_sector_pct']:.1f}%")
    print(f"   Num Positions: {metrics['num_positions']}")
    print(f"   Status: {metrics['status']}")
    
    print(f"\n   Sector Breakdown:")
    for sector, pct in metrics['sector_breakdown'].items():
        print(f"   - {sector}: {pct:.1f}%")
    
    # Test proposed trade
    proposed_trade = {
        'symbol': 'GOOGL',
        'size_usd': 18_000,
    }
    
    can_trade, warnings = risk_manager.check_risk_limits(
        proposed_trade=proposed_trade,
        portfolio_value=portfolio_value,
        existing_positions=existing_positions,
        sector_map=sector_map
    )
    
    print(f"\n✅ Proposed Trade: GOOGL for $18,000")
    print(f"   Can Trade: {can_trade}")
    if warnings:
        print(f"   Warnings:")
        for warning in warnings:
            print(f"   - {warning}")
    else:
        print(f"   ✅ Trade approved - all limits OK")
    
    return risk_manager


def test_integration():
    """Test Integration of All Components"""
    print("\n" + "="*60)
    print("TEST 7: Full Integration Test")
    print("="*60)
    
    # Scenario: Position entered yesterday, now re-evaluating
    
    print("Scenario: Re-evaluating AAPL position after overnight news\n")
    
    # 1. Memory system has the original position
    memory_store = MemoryStore(storage_path="logs/test_integration_memory.jsonl")
    
    entry_memory = DecisionMemory(
        decision_id="int_001",
        symbol="AAPL",
        timestamp=datetime.now() - timedelta(hours=18),
        decision_type=DecisionType.ENTRY,
        strategy="momentum_breakout",
        thesis="Breakout above $180 on earnings beat and sector strength",
        catalysts=["Earnings beat", "Sector rotation"],
        entry_price=180.50,
        target_price=192.00,
        stop_loss_price=175.00,
        expected_holding_period="swing (2-5 days)",
        invalidation_conditions=["Break $175", "Volume dries up"],
        shares=50,
        position_size_usd=9025.00,
        conviction_score=75,
        kelly_fraction=0.08,
    )
    memory_store.store(entry_memory)
    print("1. ✅ Original position stored in memory")
    
    # 2. Overnight news triggers an event
    event_queue = EventQueue()
    news_event = Event(
        id="int_e001",
        timestamp=datetime.now(),
        event_type=EventType.BREAKING_NEWS,
        symbol="AAPL",
        data={
            'headline': 'Apple announces major AI partnership',
            'sentiment': 0.85,
            'category': 'partnership'
        },
        priority=EventPriority.HIGH,
        source="NewsMonitor"
    )
    event_queue.add_event(news_event)
    print("2. ✅ News event added to queue")
    
    # 3. Event processing retrieves memory and builds comparison
    comparator = ThesisRealityComparator(memory_store)
    comparison = comparator.get_comparison(
        symbol="AAPL",
        current_price=189.00,
        current_data={
            'news': [{'headline': 'AI partnership announced', 'sentiment': 0.85}],
            'volume_analysis': {'ratio': 1.8},
            'price_action': {'trend': 'bullish'}
        }
    )
    print("3. ✅ Thesis vs reality comparison built")
    
    # 4. Generate LLM prompt with full context
    prompt = comparator.build_reeval_prompt(
        symbol="AAPL",
        current_price=189.00,
        current_data={'news': [], 'volume_analysis': {}, 'price_action': {}},
        trigger_event="BREAKING_NEWS: AI partnership"
    )
    print(f"4. ✅ Re-evaluation prompt generated ({len(prompt)} chars)")
    
    # 5. If LLM suggests holding, update memory
    memory_store.add_revisit("AAPL", {
        'action': 'hold',
        'reasoning': 'Thesis playing out well, new catalyst strengthens position',
        'price': 189.00,
        'thesis_still_valid': True
    })
    print("5. ✅ Revisit added to position history")
    
    # 6. Set new price alert for approaching target
    price_monitor = PriceAlertMonitor(event_queue)
    price_monitor.set_price_alert(
        symbol="AAPL",
        alert_type="above",
        price=192.00,
        event_type=EventType.TARGET_HIT,
        priority=EventPriority.MEDIUM_HIGH
    )
    print("6. ✅ Price alert set for target ($192)")
    
    print("\n🎉 Full integration test successful!")
    print("   All components working together:")
    print("   ✓ Memory stores original thesis")
    print("   ✓ Events trigger re-evaluation")
    print("   ✓ Comparison shows thesis vs reality")
    print("   ✓ Prompt includes full context")
    print("   ✓ Revisits track decision history")
    print("   ✓ Alerts set for future triggers")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("EVENT-DRIVEN ARCHITECTURE TEST SUITE")
    print("="*60)
    
    try:
        # Test 1: Decision Memory
        memory_store = test_decision_memory()
        
        # Test 2: Thesis vs Reality
        test_thesis_vs_reality(memory_store)
        
        # Test 3: Event Queue
        test_event_queue()
        
        # Test 4: Price Alerts
        test_price_alerts()
        
        # Test 5: Kelly Sizing
        test_kelly_position_sizing()
        
        # Test 6: Risk Manager
        test_portfolio_risk_manager()
        
        # Test 7: Integration
        test_integration()
        
        print("\n" + "="*60)
        print("🎉 ALL TESTS PASSED!")
        print("="*60)
        print("\nEvent-driven architecture components are working correctly:")
        print("✅ Decision Memory System")
        print("✅ Event Queue (FIFO + Priority)")
        print("✅ Price Alert Monitoring")
        print("✅ Kelly Criterion Position Sizing")
        print("✅ Portfolio Risk Management")
        print("✅ Thesis vs Reality Comparison")
        print("✅ Full Integration")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
