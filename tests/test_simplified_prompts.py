"""Test the simplified technical data component"""
import sys
sys.path.insert(0, '/Users/wagnermontes/Documents/GitHub/wawatrader')

from wawatrader.llm.components.data import TechnicalDataComponent
from wawatrader.llm.components.base import QueryContext

# Simulate real data for AAPL at $175.50 (hypothetical)
test_data = {
    'price': 175.50,
    'close': 175.50,
    'trend': {
        'sma_20': 171.50,
        'sma_50': 168.00
    },
    'momentum': {
        'rsi': 58.3
    },
    'volume': {
        'ratio': 1.8
    }
}

# Create context
context = QueryContext(
    primary_symbol='AAPL',
    query_type=QueryContext.NEW_OPPORTUNITY,
    trigger='scanner',
    profile='momentum_trader',
    detail_level='standard'
)

# Render component
component = TechnicalDataComponent(data=test_data)
component.context = context
output = component.render()

print("=" * 80)
print("SIMPLIFIED PROMPT FORMAT (What LLM sees)")
print("=" * 80)
print(output)
print("\n" + "=" * 80)
print("KEY CHANGES:")
print("=" * 80)
print("✅ BEFORE: 'RSI: 58.3 - Strong bullish momentum'")
print("   (LLM must interpret: is 58.3 strong? Is it overbought?)")
print()
print("✅ AFTER: 'MOMENTUM: ✅ STRONG (RSI: 58) - Healthy bullish momentum, not overdone yet'")
print("   (LLM just reads the verdict - no calculation needed)")
print()
print("✅ BEFORE: 'Price: $175.50, SMA20: $171.50, SMA50: $168.00'")
print("   (LLM must calculate: is price > SMA20? Is SMA20 > SMA50?)")
print()
print("✅ AFTER: 'TREND: ✅ STRONG BULLISH - Price is 2.3% ABOVE 20-day average'")
print("   (LLM just synthesizes the verdict)")
print()
print("🎯 RESULT: LLM focuses on COMBINING signals, not ANALYZING numbers")
