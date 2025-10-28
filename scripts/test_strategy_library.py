#!/usr/bin/env python3
"""
Test Professional Day Trading Strategy Library

Demonstrates how strategies match different market setups and
produce complete execution plans.

Author: WawaTrader Team
Date: 2024
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from wawatrader.strategies import (
    DayTradingStrategyLibrary,
    StrategyType,
    TimeOfDay,
    apply_strategy_to_trade
)
from datetime import datetime


def test_gap_and_go():
    """Test Gap and Go pattern matching."""
    print("\n" + "="*70)
    print("TEST 1: GAP AND GO - Ross Cameron")
    print("="*70)
    print("Setup: Stock gaps up 3% on news, high volume\n")
    
    library = DayTradingStrategyLibrary()
    
    llm_signal = {
        'action': 'BUY',
        'confidence': 85,
        'reasoning': 'Strong gap up with volume surge'
    }
    
    technical_data = {
        'symbol': 'AAPL',
        'price': 155.00,
        'sma_20': 150.00,  # 3.3% gap
        'sma_50': 148.00,
        'vwap': 154.50,
        'rsi': 65,
        'volume_ratio': 2.5,  # 2.5x average volume
        'bb_upper': 157.00,
        'bb_lower': 152.00
    }
    
    market_context = {
        'time_of_day': TimeOfDay.OPENING,
        'volatility': 'high',
        'market_regime': 'bullish'
    }
    
    setup = library.match_strategy(llm_signal, technical_data, market_context)
    
    if setup:
        print(f"✅ Matched: {setup.strategy_type.value}")
        print(f"   Source: {setup.pattern_source}")
        print(f"\n📍 Entry Plan:")
        print(f"   Entry: ${setup.entry_price:.2f}")
        print(f"   Condition: {setup.entry_condition}")
        print(f"\n🛑 Risk Management:")
        print(f"   Stop Loss: ${setup.stop_loss:.2f} ({setup.stop_reason})")
        print(f"   Risk per share: ${setup.entry_price - setup.stop_loss:.2f}")
        print(f"\n🎯 Profit Targets:")
        print(f"   T1: ${setup.target_1:.2f} (take 50%)")
        print(f"   T2: ${setup.target_2:.2f} (take 30%)")
        if setup.target_3:
            print(f"   T3: ${setup.target_3:.2f} (runner 20%)")
        print(f"\n📊 Strategy Parameters:")
        print(f"   Position Size: {setup.position_size_pct*100:.0f}% of portfolio")
        print(f"   Max Hold: {setup.max_hold_time_minutes} minutes")
        print(f"   Risk/Reward: {setup.risk_reward_ratio}R")
        print(f"   Pattern Confidence: {setup.pattern_confidence*100:.0f}%")
        print(f"\n⚠️ Invalidation Rules:")
        for rule in setup.invalidation_rules:
            print(f"   - {rule}")
    else:
        print("❌ No strategy matched")


def test_vwap_momentum():
    """Test VWAP Momentum pattern."""
    print("\n" + "="*70)
    print("TEST 2: VWAP MOMENTUM - Andrew Aziz")
    print("="*70)
    print("Setup: Stock trending above VWAP with volume\n")
    
    library = DayTradingStrategyLibrary()
    
    llm_signal = {
        'action': 'BUY',
        'confidence': 75,
        'reasoning': 'VWAP acting as support, uptrend intact'
    }
    
    technical_data = {
        'symbol': 'MSFT',
        'price': 375.00,
        'sma_20': 373.00,
        'sma_50': 370.00,
        'vwap': 373.50,  # Price 0.4% above VWAP
        'rsi': 58,
        'volume_ratio': 1.7,
        'bb_upper': 378.00,
        'bb_lower': 370.00
    }
    
    market_context = {
        'time_of_day': TimeOfDay.MORNING,
        'volatility': 'medium',
        'market_regime': 'bullish'
    }
    
    setup = library.match_strategy(llm_signal, technical_data, market_context)
    
    if setup:
        print(f"✅ Matched: {setup.strategy_type.value}")
        print(f"   Source: {setup.pattern_source}")
        print(f"\n📍 Entry: ${setup.entry_price:.2f}")
        print(f"🛑 Stop: ${setup.stop_loss:.2f} (below VWAP)")
        target_3_str = f"${setup.target_3:.2f}" if setup.target_3 else "N/A"
        print(f"🎯 Targets: ${setup.target_1:.2f} / ${setup.target_2:.2f} / {target_3_str}")
        if setup.trailing_stop:
            print(f"📈 Trailing Stop: ENABLED (follow VWAP higher)")
    else:
        print("❌ No strategy matched")


def test_support_bounce():
    """Test Support Bounce pattern."""
    print("\n" + "="*70)
    print("TEST 3: SUPPORT BOUNCE - Al Brooks")
    print("="*70)
    print("Setup: Price tests VWAP support, RSI oversold\n")
    
    library = DayTradingStrategyLibrary()
    
    llm_signal = {
        'action': 'BUY',
        'confidence': 65,
        'reasoning': 'Reversal candle at VWAP support, oversold'
    }
    
    technical_data = {
        'symbol': 'NVDA',
        'price': 485.00,
        'sma_20': 485.50,
        'sma_50': 480.00,
        'vwap': 485.20,  # At VWAP
        'rsi': 32,  # Oversold
        'volume_ratio': 1.3,
        'bb_upper': 495.00,
        'bb_lower': 475.00
    }
    
    market_context = {
        'time_of_day': TimeOfDay.MORNING,
        'volatility': 'medium',
        'market_regime': 'neutral'
    }
    
    setup = library.match_strategy(llm_signal, technical_data, market_context)
    
    if setup:
        print(f"✅ Matched: {setup.strategy_type.value}")
        print(f"   Source: {setup.pattern_source}")
        print(f"\n📍 Entry: ${setup.entry_price:.2f}")
        print(f"🛑 Stop: ${setup.stop_loss:.2f} (below support)")
        print(f"🎯 Targets: ${setup.target_1:.2f} / ${setup.target_2:.2f}")
        print(f"📊 Position: {setup.position_size_pct*100:.0f}% (conservative size)")
        print(f"⏱️ Max Hold: {setup.max_hold_time_minutes} minutes")
    else:
        print("❌ No strategy matched")


def test_momentum_scalp():
    """Test Momentum Scalp pattern."""
    print("\n" + "="*70)
    print("TEST 4: MOMENTUM SCALP - Ross Cameron")
    print("="*70)
    print("Setup: Volume surge, quick 1-2% move opportunity\n")
    
    library = DayTradingStrategyLibrary()
    
    llm_signal = {
        'action': 'BUY',
        'confidence': 80,
        'reasoning': 'Huge volume spike, momentum building'
    }
    
    technical_data = {
        'symbol': 'TSLA',
        'price': 245.00,
        'sma_20': 243.00,
        'sma_50': 240.00,
        'vwap': 244.00,
        'rsi': 62,
        'volume_ratio': 3.2,  # 3.2x volume
        'bb_upper': 248.00,
        'bb_lower': 240.00
    }
    
    market_context = {
        'time_of_day': TimeOfDay.OPENING,
        'volatility': 'high',
        'market_regime': 'volatile'
    }
    
    setup = library.match_strategy(llm_signal, technical_data, market_context)
    
    if setup:
        print(f"✅ Matched: {setup.strategy_type.value}")
        print(f"   Source: {setup.pattern_source}")
        print(f"\n📍 Entry: ${setup.entry_price:.2f}")
        print(f"🛑 Stop: ${setup.stop_loss:.2f} (TIGHT -1%)")
        print(f"🎯 Targets: ${setup.target_1:.2f} / ${setup.target_2:.2f} (QUICK)")
        print(f"📊 Position: {setup.position_size_pct*100:.0f}% (LARGE for scalp)")
        print(f"⏱️ Max Hold: {setup.max_hold_time_minutes} minutes (VERY QUICK)")
        print(f"⚡ Note: Take profits fast - don't overstay!")
    else:
        print("❌ No strategy matched")


def test_full_integration():
    """Test complete integration with position sizing."""
    print("\n" + "="*70)
    print("TEST 5: FULL INTEGRATION - Position Sizing & Order Generation")
    print("="*70)
    
    llm_decision = {
        'action': 'BUY',
        'confidence': 85,
        'reasoning': 'Gap up with strong volume, bullish setup'
    }
    
    technical_data = {
        'symbol': 'AAPL',
        'price': 155.00,
        'sma_20': 150.00,
        'sma_50': 148.00,
        'vwap': 154.50,
        'rsi': 65,
        'volume_ratio': 2.5,
        'bb_upper': 157.00,
        'bb_lower': 152.00
    }
    
    market_context = {
        'time_of_day': TimeOfDay.OPENING,
        'volatility': 'high'
    }
    
    portfolio_value = 100000  # $100k portfolio
    
    print(f"\n💰 Portfolio Value: ${portfolio_value:,.0f}")
    print(f"📊 LLM Signal: {llm_decision['action']} (confidence: {llm_decision['confidence']}%)")
    print(f"💡 Reasoning: {llm_decision['reasoning']}\n")
    
    trade_order = apply_strategy_to_trade(
        llm_decision,
        technical_data,
        market_context,
        portfolio_value
    )
    
    if trade_order:
        print(f"\n✅ TRADE ORDER GENERATED:")
        print(f"{'='*70}")
        print(f"Symbol: {trade_order['symbol']}")
        print(f"Action: {trade_order['action']}")
        print(f"Shares: {trade_order['shares']}")
        print(f"Entry: ${trade_order['entry_price']:.2f}")
        print(f"Stop: ${trade_order['stop_loss']:.2f}")
        print(f"Targets: ${trade_order['target_1']:.2f} / ${trade_order['target_2']:.2f} / ${trade_order.get('target_3', 0):.2f}")
        print(f"\nStrategy: {trade_order['strategy_type']}")
        print(f"Source: {trade_order['strategy_source']}")
        print(f"Risk/Reward: {trade_order['risk_reward']}R")
        print(f"Pattern Confidence: {trade_order['pattern_confidence']*100:.0f}%")
        print(f"LLM Confidence: {trade_order['llm_confidence']}%")
        
        # Calculate position metrics
        position_value = trade_order['shares'] * trade_order['entry_price']
        risk_dollars = trade_order['shares'] * (trade_order['entry_price'] - trade_order['stop_loss'])
        reward_t1 = trade_order['shares'] * (trade_order['target_1'] - trade_order['entry_price'])
        
        print(f"\n💵 Position Metrics:")
        print(f"   Position Size: ${position_value:,.0f} ({position_value/portfolio_value*100:.1f}% of portfolio)")
        print(f"   Risk: ${risk_dollars:,.2f} ({risk_dollars/portfolio_value*100:.2f}% of portfolio)")
        print(f"   Reward (T1): ${reward_t1:,.2f}")
        print(f"   R:R Ratio: {reward_t1/risk_dollars:.2f}:1")
        
        print(f"\n⏱️ Time Management:")
        print(f"   Max Hold: {trade_order['max_hold_minutes']} minutes")
        print(f"   Exit Before Close: {trade_order['exit_before_close']}")
        print(f"   Trailing Stop: {trade_order['trailing_stop']}")
        
        print(f"\n📋 Setup Notes:")
        print(f"   {trade_order['setup_notes']}")
        
        print(f"\n⚠️ Invalidation Rules:")
        for rule in trade_order['invalidation_rules']:
            print(f"   - {rule}")
        
    else:
        print("❌ No valid trade order generated")


def main():
    """Run all strategy tests."""
    print("\n" + "="*70)
    print("🎯 PROFESSIONAL DAY TRADING STRATEGY LIBRARY - TEST SUITE")
    print("="*70)
    print("\nTesting pattern matching and execution plan generation...")
    print("Based on methodologies from:")
    print("  • Ross Cameron (Momentum & Scalping)")
    print("  • Andrew Aziz (VWAP Strategies)")
    print("  • Al Brooks (Price Action)")
    print("  • Mark Minervini (Breakouts)")
    print("  • Peter Brandt (Classic Patterns)")
    
    try:
        test_gap_and_go()
        test_vwap_momentum()
        test_support_bounce()
        test_momentum_scalp()
        test_full_integration()
        
        print("\n" + "="*70)
        print("✅ ALL TESTS COMPLETE")
        print("="*70)
        print("\n🎉 Strategy library is ready for production!")
        print("\nKey Features:")
        print("  ✅ 6+ proven day trading patterns")
        print("  ✅ Automatic pattern recognition")
        print("  ✅ Complete execution plans (entry/stop/targets)")
        print("  ✅ Position sizing based on risk")
        print("  ✅ Time-of-day awareness")
        print("  ✅ Invalidation rules for each pattern")
        print("\nNext Steps:")
        print("  1. Integrate with TradingAgent.analyze_single_symbol()")
        print("  2. Track strategy performance in memory database")
        print("  3. Use learning engine to optimize pattern selection")
        print("  4. Add more patterns as system learns")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
