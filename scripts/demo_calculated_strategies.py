"""
Demo: Calculated Strategy Baselines

Shows how pure mathematical strategies provide baseline recommendations
that can be compared against LLM decisions.

This demonstrates:
1. Kelly Criterion strategy (optimal position sizing)
2. Momentum strategy (trend following)
3. Mean Reversion strategy (contrarian)
4. Risk Parity strategy (volatility-weighted)
5. Consensus recommendation (majority vote)

Usage:
    python scripts/demo_calculated_strategies.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from wawatrader.strategy_calculator import StrategyCalculator
from wawatrader.risk_manager import get_risk_manager
import json


def create_sample_signals(scenario: str = "bullish"):
    """Create sample technical signals for testing."""
    
    if scenario == "bullish":
        return {
            'price': {
                'close': 150.00,
                'open': 148.50,
                'high': 151.00,
                'low': 148.00,
                'volume': 5_000_000
            },
            'indicators': {
                'sma_20': 145.00,  # Price above SMA
                'sma_50': 140.00,
                'rsi': 55,  # Neutral but trending up
                'macd': 2.5,  # Positive
                'bb_upper': 155.00,
                'bb_lower': 135.00,
                'atr': 3.00,
                'avg_volume_20': 4_000_000
            }
        }
    
    elif scenario == "bearish":
        return {
            'price': {
                'close': 150.00,
                'open': 151.50,
                'high': 152.00,
                'low': 149.50,
                'volume': 6_000_000
            },
            'indicators': {
                'sma_20': 155.00,  # Price below SMA
                'sma_50': 160.00,
                'rsi': 35,  # Oversold
                'macd': -2.0,  # Negative
                'bb_upper': 165.00,
                'bb_lower': 145.00,
                'atr': 4.50,
                'avg_volume_20': 4_500_000
            }
        }
    
    elif scenario == "oversold":
        return {
            'price': {
                'close': 140.00,
                'open': 142.00,
                'high': 143.00,
                'low': 139.00,
                'volume': 8_000_000
            },
            'indicators': {
                'sma_20': 150.00,
                'sma_50': 155.00,
                'rsi': 25,  # Very oversold
                'macd': -3.0,
                'bb_upper': 160.00,
                'bb_lower': 138.00,  # Price near lower band
                'atr': 5.00,
                'avg_volume_20': 5_000_000
            }
        }
    
    elif scenario == "overbought":
        return {
            'price': {
                'close': 165.00,
                'open': 163.00,
                'high': 166.00,
                'low': 162.00,
                'volume': 7_000_000
            },
            'indicators': {
                'sma_20': 155.00,
                'sma_50': 150.00,
                'rsi': 78,  # Overbought
                'macd': 4.0,
                'bb_upper': 164.00,  # Price above upper band
                'bb_lower': 145.00,
                'atr': 3.50,
                'avg_volume_20': 4_000_000
            }
        }
    
    else:  # neutral
        return {
            'price': {
                'close': 150.00,
                'open': 150.00,
                'high': 151.00,
                'low': 149.00,
                'volume': 4_000_000
            },
            'indicators': {
                'sma_20': 150.00,
                'sma_50': 150.00,
                'rsi': 50,
                'macd': 0.1,
                'bb_upper': 155.00,
                'bb_lower': 145.00,
                'atr': 2.50,
                'avg_volume_20': 4_000_000
            }
        }


def print_strategy_analysis(strategies: dict, scenario: str):
    """Pretty print strategy analysis."""
    print(f"\n{'='*80}")
    print(f"SCENARIO: {scenario.upper()}")
    print(f"{'='*80}\n")
    
    for strat_name, strat_data in strategies.items():
        if strat_name == 'consensus':
            continue  # Print consensus last
        
        action_emoji = "🟢" if strat_data['action'] == 'buy' else "🔴" if strat_data['action'] == 'sell' else "⚪"
        sentiment_emoji = "📈" if strat_data['sentiment'] == 'bullish' else "📉" if strat_data['sentiment'] == 'bearish' else "➡️"
        
        print(f"{action_emoji} {sentiment_emoji} {strat_name.upper().replace('_', ' ')}")
        print(f"   Action: {strat_data['action'].upper()}")
        print(f"   Confidence: {strat_data['confidence']}%")
        print(f"   Shares: {strat_data['recommended_shares']}")
        print(f"   Position: {strat_data['position_pct']*100:.1f}%")
        print(f"   Reasoning: {strat_data['reasoning']}")
        
        # Strategy-specific metrics
        if 'momentum_score' in strat_data:
            print(f"   Momentum Score: {strat_data['momentum_score']}/9")
        elif 'reversion_score' in strat_data:
            print(f"   Reversion Score: {strat_data['reversion_score']}")
        elif 'volatility' in strat_data:
            print(f"   Volatility: {strat_data['volatility']*100:.1f}% (adj: {strat_data['vol_adjustment']:.2f}x)")
        
        print()
    
    # Print consensus
    if 'consensus' in strategies:
        consensus = strategies['consensus']
        print(f"\n{'─'*80}")
        print(f"🎯 CONSENSUS RECOMMENDATION")
        print(f"{'─'*80}")
        print(f"Action: {consensus['action'].upper()}")
        print(f"Confidence: {consensus['confidence']}%")
        print(f"Reasoning: {consensus['reasoning']}")
        print(f"Vote Breakdown: {consensus['vote_breakdown']}")
        print()


def main():
    """Run demo of calculated strategies."""
    print("\n" + "="*80)
    print("CALCULATED STRATEGY BASELINES DEMO")
    print("="*80)
    print("\nThis demonstrates pure mathematical strategies that provide")
    print("baseline recommendations for comparison with LLM decisions.\n")
    
    # Initialize calculator
    risk_manager = get_risk_manager()
    calculator = StrategyCalculator(risk_manager=risk_manager)
    
    # Test scenarios
    scenarios = ['bullish', 'bearish', 'oversold', 'overbought', 'neutral']
    
    account_value = 100_000
    symbol = "AAPL"
    current_position = None  # No existing position
    
    # Historical performance for Kelly
    historical_performance = {
        'win_rate': 0.60,  # 60% win rate
        'avg_win': 600,
        'avg_loss': 350
    }
    
    for scenario in scenarios:
        signals = create_sample_signals(scenario)
        
        strategies = calculator.calculate_all_strategies(
            symbol=symbol,
            signals=signals,
            current_position=current_position,
            account_value=account_value,
            historical_performance=historical_performance
        )
        
        # Add consensus
        consensus = calculator.get_consensus_recommendation(strategies)
        strategies['consensus'] = consensus
        
        print_strategy_analysis(strategies, scenario)
    
    # Test with existing position (should affect sell decisions)
    print(f"\n{'='*80}")
    print("SCENARIO: WITH EXISTING POSITION")
    print(f"{'='*80}\n")
    
    current_position = {
        'symbol': symbol,
        'qty': 100,
        'avg_entry_price': 145.00,
        'current_price': 150.00
    }
    
    signals = create_sample_signals('bearish')
    
    strategies = calculator.calculate_all_strategies(
        symbol=symbol,
        signals=signals,
        current_position=current_position,
        account_value=account_value,
        historical_performance=historical_performance
    )
    
    consensus = calculator.get_consensus_recommendation(strategies)
    strategies['consensus'] = consensus
    
    for strat_name, strat_data in strategies.items():
        action_emoji = "🟢" if strat_data['action'] == 'buy' else "🔴" if strat_data['action'] == 'sell' else "⚪"
        print(f"{action_emoji} {strat_name}: {strat_data['action'].upper()} - {strat_data['reasoning'][:60]}...")
    
    print(f"\n{'─'*80}")
    print("KEY INSIGHTS:")
    print(f"{'─'*80}")
    print("✅ Kelly Criterion: Optimal position sizing based on win rate")
    print("✅ Momentum: Follows trends, good for trending markets")
    print("✅ Mean Reversion: Buys dips, sells rallies")
    print("✅ Risk Parity: Adjusts for volatility automatically")
    print("✅ Consensus: Democratic vote across all strategies")
    print("\n📊 These baselines create a CONTROL GROUP for measuring LLM value-add")
    print("📊 Every decision logs both LLM and calculated recommendations")
    print("📊 OvernightLearner can analyze: 'Is LLM actually helping?'")
    print()


if __name__ == '__main__':
    main()
