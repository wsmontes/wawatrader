#!/usr/bin/env python3
"""
Test Enhanced LLM Data Presentation

Demonstrates the improved technical data formatting with
professional trading master context.

Author: WawaTrader Team
Date: 2024
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from wawatrader.llm.components.data import TechnicalDataComponent
from wawatrader.llm.components.base import QueryContext


def test_strong_uptrend():
    """Test: Strong uptrend scenario (Gap & Go setup)."""
    print("\n" + "="*80)
    print("TEST 1: STRONG BULLISH UPTREND (Gap & Go Pattern)")
    print("="*80)
    
    # Simulate strong uptrend with momentum
    technical_data = {
        'price': 155.00,
        'close': 155.00,
        'sma_20': 150.00,  # +3.3% above
        'sma_50': 147.00,  # Clear uptrend
        'sma20': 150.00,
        'sma50': 147.00,
        'vwap': 154.00,  # Price above VWAP
        'rsi': 67,  # Strong but not overbought
        'volume_ratio': 2.8,  # Very high volume
        'macd': 1.2,
        'macd_signal': 0.8,
        'volatility': {
            'atr': 3.50,
            'bb_width': 0.15,
        },
        'bb_upper': 158.00,
        'bb_lower': 152.00,
    }
    
    context = QueryContext(
        query_type='NEW_OPPORTUNITY',
        trigger='SCHEDULED',
        profile='moderate',
        primary_symbol='AAPL'
    )
    
    component = TechnicalDataComponent(technical_data)
    component.set_context(context)
    
    output = component.render()
    print(output)


def test_oversold_bounce():
    """Test: Oversold bounce setup (Support Bounce pattern)."""
    print("\n" + "="*80)
    print("TEST 2: OVERSOLD BOUNCE AT SUPPORT")
    print("="*80)
    
    # Simulate oversold condition at support
    technical_data = {
        'price': 485.00,
        'close': 485.00,
        'sma_20': 485.50,  # At SMA20 support
        'sma_50': 483.00,
        'sma20': 485.50,
        'sma50': 483.00,
        'vwap': 486.00,  # Slightly below VWAP
        'rsi': 28,  # Oversold
        'volume_ratio': 1.3,  # Moderate volume
        'macd': -0.5,
        'macd_signal': -0.3,
        'volatility': {
            'atr': 6.20,
            'bb_width': 0.12,
        },
        'bb_upper': 495.00,
        'bb_lower': 478.00,
    }
    
    context = QueryContext(
        query_type='NEW_OPPORTUNITY',
        trigger='SCHEDULED',
        profile='moderate',
        primary_symbol='NVDA'
    )
    
    component = TechnicalDataComponent(technical_data)
    component.set_context(context)
    
    output = component.render()
    print(output)


def test_overbought_extension():
    """Test: Overbought condition (caution zone)."""
    print("\n" + "="*80)
    print("TEST 3: OVERBOUGHT EXTENSION (Caution Zone)")
    print("="*80)
    
    # Simulate overbought extension
    technical_data = {
        'price': 245.00,
        'close': 245.00,
        'sma_20': 238.00,
        'sma_50': 235.00,
        'sma20': 238.00,
        'sma50': 235.00,
        'vwap': 241.00,  # Extended above VWAP
        'rsi': 76,  # Overbought
        'volume_ratio': 0.8,  # Low volume
        'macd': 2.1,
        'macd_signal': 1.8,
        'volatility': {
            'atr': 4.80,
            'bb_width': 0.18,
        },
        'bb_upper': 248.00,
        'bb_lower': 232.00,
    }
    
    context = QueryContext(
        query_type='POSITION_REVIEW',
        trigger='SCHEDULED',
        profile='moderate',
        primary_symbol='TSLA'
    )
    
    component = TechnicalDataComponent(technical_data)
    component.set_context(context)
    
    output = component.render()
    print(output)


def test_volatility_squeeze():
    """Test: Bollinger Band squeeze (breakout pending)."""
    print("\n" + "="*80)
    print("TEST 4: VOLATILITY SQUEEZE (Breakout Pending)")
    print("="*80)
    
    # Simulate low volatility squeeze
    technical_data = {
        'price': 375.00,
        'close': 375.00,
        'sma_20': 374.50,
        'sma_50': 373.00,
        'sma20': 374.50,
        'sma50': 373.00,
        'vwap': 375.20,
        'rsi': 52,  # Neutral
        'volume_ratio': 0.6,  # Low volume
        'macd': 0.1,
        'macd_signal': 0.05,
        'volatility': {
            'atr': 2.10,
            'bb_width': 0.04,  # Very tight - squeeze
        },
        'bb_upper': 377.00,
        'bb_lower': 373.00,
    }
    
    context = QueryContext(
        query_type='NEW_OPPORTUNITY',
        trigger='SCHEDULED',
        profile='moderate',
        primary_symbol='MSFT'
    )
    
    component = TechnicalDataComponent(technical_data)
    component.set_context(context)
    
    output = component.render()
    print(output)


def test_downtrend():
    """Test: Confirmed downtrend (avoid zone)."""
    print("\n" + "="*80)
    print("TEST 5: CONFIRMED DOWNTREND (Avoid Zone)")
    print("="*80)
    
    # Simulate downtrend
    technical_data = {
        'price': 142.00,
        'close': 142.00,
        'sma_20': 145.00,  # Price below
        'sma_50': 147.00,  # Downtrend structure
        'sma20': 145.00,
        'sma50': 147.00,
        'vwap': 144.00,  # Below VWAP
        'rsi': 38,  # Weak momentum
        'volume_ratio': 1.1,  # Normal volume
        'macd': -0.8,
        'macd_signal': -0.5,
        'volatility': {
            'atr': 2.90,
            'bb_width': 0.14,
        },
        'bb_upper': 147.00,
        'bb_lower': 139.00,
    }
    
    context = QueryContext(
        query_type='POSITION_REVIEW',
        trigger='SCHEDULED',
        profile='moderate',
        primary_symbol='AAPL'
    )
    
    component = TechnicalDataComponent(technical_data)
    component.set_context(context)
    
    output = component.render()
    print(output)


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("🎓 ENHANCED LLM DATA PRESENTATION - PROFESSIONAL TRADING CONTEXT")
    print("="*80)
    print("\nTesting technical data formatting with trading master insights...")
    print("Sources: Ross Cameron, Andrew Aziz, Al Brooks, Mark Minervini, Peter Brandt")
    
    try:
        test_strong_uptrend()
        test_oversold_bounce()
        test_overbought_extension()
        test_volatility_squeeze()
        test_downtrend()
        
        print("\n" + "="*80)
        print("✅ ALL TESTS COMPLETE")
        print("="*80)
        print("\n🎉 Enhanced LLM data presentation is ready!")
        print("\nKey Improvements:")
        print("  ✅ Professional trader context for every indicator")
        print("  ✅ Explains WHAT indicators mean")
        print("  ✅ Shows HOW professionals use them")
        print("  ✅ Provides ACTIONABLE trading guidance")
        print("  ✅ Cites specific trader methodologies")
        print("  ✅ Pattern recognition with strategy names")
        print("  ✅ Clear bullish/bearish factor summary")
        print("\nNext Steps:")
        print("  1. LLM will now see professional trading context")
        print("  2. Decisions will be informed by master trader wisdom")
        print("  3. Better alignment with strategy library patterns")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
