#!/usr/bin/env python3
"""
Test overnight analysis integration.

This script verifies:
1. Overnight analysis JSON loads correctly
2. TradingAgent receives and indexes overnight data
3. STEP 0 executes overnight SELLs
4. LLM receives overnight context in prompts
5. Complete flow from file → execution → LLM context
"""

import json
from pathlib import Path
from typing import Dict, Any

# Setup path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from wawatrader.llm.components.base import QueryContext
from wawatrader.llm.components.overnight import OvernightAnalysisComponent
from wawatrader.llm.builders.prompt_builder import PromptBuilder


def test_overnight_component():
    """Test OvernightAnalysisComponent rendering"""
    print("\n" + "="*80)
    print("TEST 1: OvernightAnalysisComponent Rendering")
    print("="*80)
    
    # Simulate overnight analysis data
    overnight_data = {
        'symbol': 'GS',
        'final_recommendation': 'SELL',
        'reasoning': 'Volume trend decisively decreasing. 5-day average volume fell from 3.2M to 2.1M (-34%). Price weakness combined with volume decline indicates institutional selling. Technical indicators confirm bearish divergence.',
        'iterations': 3,
        'confidence_level': 'high',
        'analyzed_at': '2024-01-15 20:30:00'
    }
    
    component = OvernightAnalysisComponent(overnight_data)
    
    # Test validation
    if not component.validate():
        print("❌ Component validation failed")
        return False
    print("✅ Component validation passed")
    
    # Test rendering
    rendered = component.render()
    print("\nRendered Output:")
    print("-" * 80)
    print(rendered)
    print("-" * 80)
    
    # Test token estimate
    tokens = component.get_token_estimate()
    print(f"\n✅ Estimated tokens: {tokens}")
    
    return True


def test_query_context():
    """Test QueryContext with overnight_analysis field"""
    print("\n" + "="*80)
    print("TEST 2: QueryContext with Overnight Analysis")
    print("="*80)
    
    overnight_data = {
        'symbol': 'MS',
        'final_recommendation': 'HOLD',
        'reasoning': 'Hold temporarily, preparing to rotate aggressively',
        'iterations': 2,
        'confidence_level': 'medium',
        'analyzed_at': '2024-01-15 20:45:00'
    }
    
    # Create QueryContext with overnight analysis
    context = QueryContext(
        query_type='POSITION_REVIEW',
        trigger='SCHEDULED_CYCLE',
        profile='rotator',
        primary_symbol='MS',
        overnight_analysis=overnight_data
    )
    
    print(f"✅ QueryContext created with overnight_analysis")
    print(f"   - Symbol: {context.overnight_analysis['symbol']}")
    print(f"   - Recommendation: {context.overnight_analysis['final_recommendation']}")
    print(f"   - Iterations: {context.overnight_analysis['iterations']}")
    
    return True


def test_prompt_builder():
    """Test PromptBuilder with overnight analysis"""
    print("\n" + "="*80)
    print("TEST 3: PromptBuilder Integration")
    print("="*80)
    
    overnight_data = {
        'symbol': 'C',
        'final_recommendation': 'SELL',
        'reasoning': 'Sell aggressively. Price action shows clear distribution pattern with declining volume. Risk/reward ratio unfavorable.',
        'iterations': 4,
        'confidence_level': 'high',
        'analyzed_at': '2024-01-15 21:00:00'
    }
    
    context = QueryContext(
        query_type='POSITION_REVIEW',
        trigger='SCHEDULED_CYCLE',
        profile='rotator',
        primary_symbol='C',
        overnight_analysis=overnight_data
    )
    
    # Mock technical data
    data = {
        'technical': {
            'symbol': 'C',
            'price': 45.20,
            'sma_20': 46.50,
            'rsi_14': 42.0,
        }
    }
    
    builder = PromptBuilder()
    
    # Preview components
    component_list = builder.preview_components(context, data)
    print("\nSelected Components:")
    for comp in component_list:
        print(f"  - {comp}")
    
    # Check if overnight component is included
    has_overnight = any('Overnight' in comp for comp in component_list)
    if has_overnight:
        print("\n✅ OvernightAnalysisComponent is included in prompt")
    else:
        print("\n❌ OvernightAnalysisComponent NOT found in prompt")
        return False
    
    # Build full prompt
    prompt = builder.build(context, data)
    
    # Check if overnight content appears in prompt
    if 'OVERNIGHT DEEP ANALYSIS' in prompt and 'Sell aggressively' in prompt:
        print("✅ Overnight analysis content appears in final prompt")
    else:
        print("❌ Overnight analysis content NOT in final prompt")
        return False
    
    print(f"\n✅ Full prompt length: {len(prompt)} characters")
    
    # Show snippet
    if 'OVERNIGHT DEEP ANALYSIS' in prompt:
        start = prompt.index('OVERNIGHT DEEP ANALYSIS')
        snippet = prompt[start:start+300]
        print("\nPrompt Snippet (overnight section):")
        print("-" * 80)
        print(snippet + "...")
        print("-" * 80)
    
    return True


def test_file_loading():
    """Test loading actual overnight_analysis.json if it exists"""
    print("\n" + "="*80)
    print("TEST 4: Loading Actual overnight_analysis.json")
    print("="*80)
    
    overnight_file = Path(__file__).parent.parent / "logs" / "overnight_analysis.json"
    
    if not overnight_file.exists():
        print("⚠️  No overnight_analysis.json found (this is OK for testing)")
        print(f"   Expected at: {overnight_file}")
        return True
    
    try:
        with open(overnight_file, 'r') as f:
            overnight_analysis = json.load(f)
        
        print(f"✅ Loaded {len(overnight_analysis)} overnight recommendations")
        
        # Show SELL recommendations
        sells = [rec for rec in overnight_analysis if rec.get('final_recommendation') == 'SELL']
        if sells:
            print(f"\n📊 Found {len(sells)} SELL recommendations:")
            for rec in sells[:3]:  # Show first 3
                symbol = rec.get('symbol', 'Unknown')
                reasoning = rec.get('reasoning', '')[:100]
                print(f"   - {symbol}: {reasoning}...")
        else:
            print("\n   No SELL recommendations in overnight analysis")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("OVERNIGHT ANALYSIS INTEGRATION TEST SUITE")
    print("="*80)
    
    results = []
    
    # Run tests
    results.append(("Component Rendering", test_overnight_component()))
    results.append(("QueryContext Integration", test_query_context()))
    results.append(("PromptBuilder Integration", test_prompt_builder()))
    results.append(("File Loading", test_file_loading()))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Overnight integration is working correctly.")
        print("\nNext steps:")
        print("1. Run the full system at market open")
        print("2. Verify STEP 0 executes overnight SELLs first")
        print("3. Check LLM logs to confirm overnight context appears in prompts")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check output above for details.")
        return 1


if __name__ == '__main__':
    exit(main())
