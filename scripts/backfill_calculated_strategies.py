"""
Backfill Calculated Strategies for Historical Decisions

This script:
1. Loads historical trading decisions
2. Reconstructs signals from market data
3. Calculates what pure math strategies would have recommended
4. Exports enhanced decisions with baseline comparisons

Usage:
    python scripts/backfill_calculated_strategies.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from wawatrader.replay_engine import get_replay_engine
from wawatrader.strategy_calculator import StrategyCalculator
from wawatrader.risk_manager import get_risk_manager
from datetime import datetime
import json


def extract_signals_from_decision(decision_data):
    """
    Extract technical signals from decision data.
    
    Historical decisions contain indicators in the 'indicators' field.
    """
    indicators = decision_data.get('indicators', {})
    
    # Extract price data
    price_data = indicators.get('price', {})
    if not price_data and 'price' in decision_data:
        # Fallback to decision-level price
        price = decision_data['price']
        price_data = {
            'close': price,
            'open': price,
            'high': price,
            'low': price,
            'volume': 1000000  # Default
        }
    
    # Extract technical indicators
    technical = indicators.get('indicators', {})
    
    return {
        'price': price_data,
        'indicators': technical
    }


def backfill_historical_decisions(replay_engine, limit=None):
    """
    Backfill calculated strategies for historical decisions.
    
    Args:
        replay_engine: ReplayEngine instance with loaded data
        limit: Optional limit on number of decisions to process
    """
    print("\n" + "="*80)
    print("BACKFILLING CALCULATED STRATEGIES")
    print("="*80 + "\n")
    
    # Get all decision events
    decision_events = [
        event for event in replay_engine.timeline 
        if event.event_type.value == 'decision'
    ]
    
    if not decision_events:
        print("❌ No decision events found!")
        return []
    
    if limit:
        decision_events = decision_events[:limit]
        print(f"🔢 Processing first {limit} decisions (out of {len(decision_events)} total)")
    else:
        print(f"🔢 Processing all {len(decision_events)} decisions")
    
    # Initialize strategy calculator
    risk_manager = get_risk_manager()
    calculator = StrategyCalculator(risk_manager=risk_manager)
    
    # Default historical performance (we'll use conservative defaults)
    default_performance = {
        'win_rate': 0.55,
        'avg_win': 500,
        'avg_loss': 300
    }
    
    # Process each decision
    enhanced_decisions = []
    success_count = 0
    error_count = 0
    
    print("\n🔄 Processing decisions...")
    
    for i, event in enumerate(decision_events, 1):
        if i % 100 == 0:
            print(f"   Progress: {i}/{len(decision_events)} ({i/len(decision_events)*100:.0f}%)")
        
        try:
            decision_data = event.data.copy()
            
            # Extract signals from decision
            signals = extract_signals_from_decision(decision_data)
            
            # Skip if no price data
            if not signals['price'].get('close'):
                error_count += 1
                continue
            
            # Determine current position (from decision context)
            symbol = decision_data.get('symbol')
            current_position = None  # Historical data doesn't have position info
            
            # Estimate account value from decision
            account_value = decision_data.get('account_value', 100000)
            
            # Calculate strategies
            calculated_strategies = calculator.calculate_all_strategies(
                symbol=symbol,
                signals=signals,
                current_position=current_position,
                account_value=account_value,
                historical_performance=default_performance
            )
            
            # Add consensus
            consensus = calculator.get_consensus_recommendation(calculated_strategies)
            calculated_strategies['consensus'] = consensus
            
            # Add calculated strategies to decision
            decision_data['calculated_strategies'] = calculated_strategies
            
            # Calculate agreement score
            llm_action = decision_data.get('action', 'hold')
            agreements = 0
            total = 5
            
            for strat_name in ['kelly', 'momentum', 'mean_reversion', 'risk_parity', 'consensus']:
                if calculated_strategies.get(strat_name, {}).get('action') == llm_action:
                    agreements += 1
            
            decision_data['strategy_agreement_score'] = agreements / total
            
            enhanced_decisions.append(decision_data)
            success_count += 1
            
        except Exception as e:
            error_count += 1
            if error_count <= 5:  # Show first 5 errors
                print(f"   ⚠️  Error processing decision {i}: {e}")
    
    print(f"\n✅ Successfully processed: {success_count}")
    print(f"❌ Errors: {error_count}")
    
    return enhanced_decisions


def analyze_enhanced_decisions(enhanced_decisions):
    """
    Analyze backfilled decisions to show strategy performance.
    """
    if not enhanced_decisions:
        return
    
    print("\n" + "="*80)
    print("STRATEGY PERFORMANCE ANALYSIS (HISTORICAL)")
    print("="*80 + "\n")
    
    # Agreement statistics
    print("📊 LLM vs Strategy Agreement:\n")
    
    llm_vs_kelly = {'agree': 0, 'disagree': 0}
    llm_vs_momentum = {'agree': 0, 'disagree': 0}
    llm_vs_mean_reversion = {'agree': 0, 'disagree': 0}
    llm_vs_risk_parity = {'agree': 0, 'disagree': 0}
    llm_vs_consensus = {'agree': 0, 'disagree': 0}
    
    for decision in enhanced_decisions:
        llm_action = decision.get('action', 'hold')
        strategies = decision['calculated_strategies']
        
        if strategies.get('kelly', {}).get('action') == llm_action:
            llm_vs_kelly['agree'] += 1
        else:
            llm_vs_kelly['disagree'] += 1
        
        if strategies.get('momentum', {}).get('action') == llm_action:
            llm_vs_momentum['agree'] += 1
        else:
            llm_vs_momentum['disagree'] += 1
        
        if strategies.get('mean_reversion', {}).get('action') == llm_action:
            llm_vs_mean_reversion['agree'] += 1
        else:
            llm_vs_mean_reversion['disagree'] += 1
        
        if strategies.get('risk_parity', {}).get('action') == llm_action:
            llm_vs_risk_parity['agree'] += 1
        else:
            llm_vs_risk_parity['disagree'] += 1
        
        if strategies.get('consensus', {}).get('action') == llm_action:
            llm_vs_consensus['agree'] += 1
        else:
            llm_vs_consensus['disagree'] += 1
    
    total = len(enhanced_decisions)
    
    print(f"  Kelly Criterion:  {llm_vs_kelly['agree']:3d} agree ({llm_vs_kelly['agree']/total*100:.1f}%), "
          f"{llm_vs_kelly['disagree']:3d} disagree ({llm_vs_kelly['disagree']/total*100:.1f}%)")
    print(f"  Momentum:         {llm_vs_momentum['agree']:3d} agree ({llm_vs_momentum['agree']/total*100:.1f}%), "
          f"{llm_vs_momentum['disagree']:3d} disagree ({llm_vs_momentum['disagree']/total*100:.1f}%)")
    print(f"  Mean Reversion:   {llm_vs_mean_reversion['agree']:3d} agree ({llm_vs_mean_reversion['agree']/total*100:.1f}%), "
          f"{llm_vs_mean_reversion['disagree']:3d} disagree ({llm_vs_mean_reversion['disagree']/total*100:.1f}%)")
    print(f"  Risk Parity:      {llm_vs_risk_parity['agree']:3d} agree ({llm_vs_risk_parity['agree']/total*100:.1f}%), "
          f"{llm_vs_risk_parity['disagree']:3d} disagree ({llm_vs_risk_parity['disagree']/total*100:.1f}%)")
    print(f"  Consensus:        {llm_vs_consensus['agree']:3d} agree ({llm_vs_consensus['agree']/total*100:.1f}%), "
          f"{llm_vs_consensus['disagree']:3d} disagree ({llm_vs_consensus['disagree']/total*100:.1f}%)")
    
    # Average agreement score
    avg_agreement = sum(d['strategy_agreement_score'] for d in enhanced_decisions) / len(enhanced_decisions)
    print(f"\n📈 Average Agreement Score: {avg_agreement*100:.1f}%")
    
    # Show interesting cases
    print(f"\n{'─'*80}")
    print("INTERESTING CASES (High Disagreement)")
    print(f"{'─'*80}\n")
    
    # Find decisions where LLM strongly disagreed with consensus
    disagreements = [
        d for d in enhanced_decisions 
        if d['action'] != d['calculated_strategies'].get('consensus', {}).get('action')
    ]
    
    print(f"Decisions where LLM disagreed with consensus: {len(disagreements)} ({len(disagreements)/total*100:.1f}%)\n")
    
    for decision in disagreements[:5]:  # Show first 5
        print(f"📅 {decision['timestamp'][:19]} | {decision['symbol']}")
        print(f"   LLM: {decision['action'].upper()} (confidence: {decision['confidence']}%)")
        print(f"   Consensus: {decision['calculated_strategies']['consensus']['action'].upper()} "
              f"(confidence: {decision['calculated_strategies']['consensus']['confidence']}%)")
        print(f"   Reasoning: {decision['reasoning'][:70]}...")
        print()


def export_enhanced_decisions(enhanced_decisions, output_file='logs/decisions_with_strategies.jsonl'):
    """
    Export enhanced decisions to JSONL file.
    """
    if not enhanced_decisions:
        return
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        for decision in enhanced_decisions:
            f.write(json.dumps(decision) + '\n')
    
    print(f"\n💾 Exported {len(enhanced_decisions)} enhanced decisions to: {output_file}")


def main():
    """Main backfill script."""
    print("\n" + "="*80)
    print("BACKFILL CALCULATED STRATEGIES FOR HISTORICAL DATA")
    print("="*80)
    print("\nThis will:")
    print("  1. Load all historical trading decisions")
    print("  2. Calculate what pure math strategies would have recommended")
    print("  3. Add baseline comparisons to each decision")
    print("  4. Export enhanced dataset for analysis")
    
    # Load replay engine
    print("\n🔄 Loading historical logs...")
    replay_engine = get_replay_engine()
    
    try:
        events_loaded = replay_engine.load_logs()
        print(f"✅ Loaded {events_loaded:,} events")
    except Exception as e:
        print(f"❌ Error loading logs: {e}")
        return
    
    # Backfill strategies
    enhanced_decisions = backfill_historical_decisions(replay_engine, limit=None)
    
    if enhanced_decisions:
        # Analyze results
        analyze_enhanced_decisions(enhanced_decisions)
        
        # Export
        export_enhanced_decisions(enhanced_decisions)
        
        print("\n" + "="*80)
        print("✅ BACKFILL COMPLETE")
        print("="*80)
        print(f"\n📊 {len(enhanced_decisions)} decisions now have calculated strategy baselines!")
        print("\n💡 You can now analyze:")
        print("   - Which strategy agrees most with LLM")
        print("   - When LLM adds value vs when math is better")
        print("   - Performance by market regime")
        print("   - Agreement patterns over time")
    else:
        print("\n❌ No decisions were successfully enhanced.")


if __name__ == '__main__':
    main()
