"""
Test that different stocks get different analysis with simplified prompts.
This verifies the fix for the repetitive "$250 resistance" problem.
"""
import sys
sys.path.insert(0, '/Users/wagnermontes/Documents/GitHub/wawatrader')

from wawatrader.llm.components.data import TechnicalDataComponent
from wawatrader.llm.components.base import QueryContext

# Test 3 different stocks with VERY different prices and signals

stocks = {
    'NVDA': {
        'price': 890.25,
        'trend': {'sma_20': 850.00, 'sma_50': 820.00},
        'momentum': {'rsi': 48.0},
        'volume': {'ratio': 0.9}
    },
    'INTC': {
        'price': 52.30,
        'trend': {'sma_20': 58.50, 'sma_50': 61.00},
        'momentum': {'rsi': 35.0},
        'volume': {'ratio': 0.6}
    },
    'TSLA': {
        'price': 460.15,
        'trend': {'sma_20': 445.00, 'sma_50': 440.00},
        'momentum': {'rsi': 72.0},
        'volume': {'ratio': 2.8}
    }
}

print("=" * 80)
print("STOCK-SPECIFIC ANALYSIS TEST")
print("=" * 80)
print("\nGenerating analysis for 3 very different stocks...")
print("NVDA: $890 (sideways, neutral)")
print("INTC: $52 (bearish, oversold, low volume)")
print("TSLA: $460 (bullish, overbought, explosive volume)")
print("\n" + "=" * 80 + "\n")

for symbol, data in stocks.items():
    context = QueryContext(
        primary_symbol=symbol,
        query_type=QueryContext.NEW_OPPORTUNITY,
        trigger='scanner',
        profile='momentum_trader',
        detail_level='standard'
    )
    
    component = TechnicalDataComponent(data=data)
    component.context = context
    output = component.render()
    
    print(output)
    print("\n" + "=" * 80 + "\n")

print("✅ VERIFICATION CHECKLIST:")
print("=" * 80)
print("1. Do all three stocks show DIFFERENT prices?")
print("   → NVDA: $890, INTC: $52, TSLA: $460")
print()
print("2. Do they have DIFFERENT trend verdicts?")
print("   → NVDA: SIDEWAYS, INTC: BEARISH, TSLA: BULLISH")
print()
print("3. Do they have DIFFERENT momentum verdicts?")
print("   → NVDA: NEUTRAL, INTC: WEAK, TSLA: OVERBOUGHT")
print()
print("4. Do they have DIFFERENT volume verdicts?")
print("   → NVDA: NORMAL, INTC: LOW, TSLA: EXPLOSIVE")
print()
print("5. Is each support/resistance level UNIQUE to that stock?")
print("   → NOT all saying '$250 resistance'")
print()
print("✅ If all checks pass → Simplified prompts working correctly!")
print("❌ If stocks still similar → Need to upgrade LLM to 8B+")
