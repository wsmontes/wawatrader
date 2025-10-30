"""
Analyze Past Trading Data using ReplayEngine

This script loads historical logs and extracts:
1. All trading decisions with calculated strategies
2. Performance comparison: LLM vs pure math strategies
3. Agreement analysis between strategies
4. Scenario-specific performance

Usage:
    python scripts/analyze_past_data.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from wawatrader.replay_engine import get_replay_engine
from datetime import datetime
import json
from collections import defaultdict
from typing import Dict, Any, List


def analyze_decisions_with_strategies(replay_engine):
    """
    Analyze all historical trading decisions.
    
    Extracts decisions that have calculated_strategies field
    and compares LLM recommendations vs baselines.
    """
    print("\n" + "="*80)
    print("HISTORICAL TRADING DECISIONS ANALYSIS")
    print("="*80 + "\n")
    
    # Get all decision events
    decision_events = [
        event for event in replay_engine.timeline 
        if event.event_type.value == 'decision'
    ]
    
    print(f"📊 Total Decision Events Found: {len(decision_events)}")
    
    if not decision_events:
        print("\n⚠️  No decision events found in logs.")
        print("   Run some trading cycles first to generate decision data.")
        return
    
    # Analyze decisions
    decisions_with_strategies = []
    decisions_without_strategies = []
    
    for event in decision_events:
        data = event.data
        if 'calculated_strategies' in data and data['calculated_strategies']:
            decisions_with_strategies.append(data)
        else:
            decisions_without_strategies.append(data)
    
    print(f"\n✅ Decisions WITH calculated strategies: {len(decisions_with_strategies)}")
    print(f"⚠️  Decisions WITHOUT calculated strategies: {len(decisions_without_strategies)}")
    
    if not decisions_with_strategies:
        print("\n📝 No decisions with calculated strategies found yet.")
        print("   This is expected if you haven't run trading with the new system.")
        print("\n💡 To generate data with baselines:")
        print("   1. Run: python scripts/run_trading.py")
        print("   2. Let it make a few decisions")
        print("   3. Run this script again")
        return decisions_without_strategies
    
    # Analyze strategy agreement
    print(f"\n{'─'*80}")
    print("STRATEGY AGREEMENT ANALYSIS")
    print(f"{'─'*80}\n")
    
    agreement_scores = []
    llm_vs_kelly = {'agree': 0, 'disagree': 0}
    llm_vs_momentum = {'agree': 0, 'disagree': 0}
    llm_vs_mean_reversion = {'agree': 0, 'disagree': 0}
    llm_vs_risk_parity = {'agree': 0, 'disagree': 0}
    llm_vs_consensus = {'agree': 0, 'disagree': 0}
    
    for decision in decisions_with_strategies:
        llm_action = decision.get('action', 'hold')
        strategies = decision['calculated_strategies']
        
        # Count agreements
        agreements = 0
        total = 5  # 4 strategies + consensus
        
        if strategies.get('kelly', {}).get('action') == llm_action:
            agreements += 1
            llm_vs_kelly['agree'] += 1
        else:
            llm_vs_kelly['disagree'] += 1
        
        if strategies.get('momentum', {}).get('action') == llm_action:
            agreements += 1
            llm_vs_momentum['agree'] += 1
        else:
            llm_vs_momentum['disagree'] += 1
        
        if strategies.get('mean_reversion', {}).get('action') == llm_action:
            agreements += 1
            llm_vs_mean_reversion['agree'] += 1
        else:
            llm_vs_mean_reversion['disagree'] += 1
        
        if strategies.get('risk_parity', {}).get('action') == llm_action:
            agreements += 1
            llm_vs_risk_parity['agree'] += 1
        else:
            llm_vs_risk_parity['disagree'] += 1
        
        if strategies.get('consensus', {}).get('action') == llm_action:
            agreements += 1
            llm_vs_consensus['agree'] += 1
        else:
            llm_vs_consensus['disagree'] += 1
        
        agreement_score = agreements / total
        agreement_scores.append(agreement_score)
    
    # Print agreement statistics
    avg_agreement = sum(agreement_scores) / len(agreement_scores) if agreement_scores else 0
    
    print(f"Average Agreement Score: {avg_agreement*100:.1f}%")
    print(f"\nLLM Agreement by Strategy:")
    print(f"  Kelly Criterion:  {llm_vs_kelly['agree']:3d} agree, {llm_vs_kelly['disagree']:3d} disagree "
          f"({llm_vs_kelly['agree']/(llm_vs_kelly['agree']+llm_vs_kelly['disagree'])*100:.0f}%)")
    print(f"  Momentum:         {llm_vs_momentum['agree']:3d} agree, {llm_vs_momentum['disagree']:3d} disagree "
          f"({llm_vs_momentum['agree']/(llm_vs_momentum['agree']+llm_vs_momentum['disagree'])*100:.0f}%)")
    print(f"  Mean Reversion:   {llm_vs_mean_reversion['agree']:3d} agree, {llm_vs_mean_reversion['disagree']:3d} disagree "
          f"({llm_vs_mean_reversion['agree']/(llm_vs_mean_reversion['agree']+llm_vs_mean_reversion['disagree'])*100:.0f}%)")
    print(f"  Risk Parity:      {llm_vs_risk_parity['agree']:3d} agree, {llm_vs_risk_parity['disagree']:3d} disagree "
          f"({llm_vs_risk_parity['agree']/(llm_vs_risk_parity['agree']+llm_vs_risk_parity['disagree'])*100:.0f}%)")
    print(f"  Consensus:        {llm_vs_consensus['agree']:3d} agree, {llm_vs_consensus['disagree']:3d} disagree "
          f"({llm_vs_consensus['agree']/(llm_vs_consensus['agree']+llm_vs_consensus['disagree'])*100:.0f}%)")
    
    # Show sample decisions
    print(f"\n{'─'*80}")
    print("SAMPLE DECISIONS WITH CALCULATED STRATEGIES")
    print(f"{'─'*80}\n")
    
    for i, decision in enumerate(decisions_with_strategies[:3]):  # Show first 3
        print(f"Decision #{i+1}: {decision['symbol']} at {decision['timestamp']}")
        print(f"  LLM: {decision['action'].upper()} (confidence: {decision['confidence']}%)")
        print(f"  Reasoning: {decision['reasoning'][:80]}...")
        
        strategies = decision['calculated_strategies']
        print(f"\n  Calculated Strategies:")
        for strat_name in ['kelly', 'momentum', 'mean_reversion', 'risk_parity', 'consensus']:
            if strat_name in strategies:
                strat = strategies[strat_name]
                action_emoji = "🟢" if strat['action'] == 'buy' else "🔴" if strat['action'] == 'sell' else "⚪"
                agree = "✓" if strat['action'] == decision['action'] else "✗"
                print(f"    {action_emoji} {agree} {strat_name:15s}: {strat['action'].upper():4s} "
                      f"({strat['confidence']:3d}%) - {strat['reasoning'][:50]}...")
        
        print()
    
    return decisions_with_strategies


def analyze_all_historical_data(replay_engine):
    """
    Comprehensive analysis of ALL historical log data.
    """
    print("\n" + "="*80)
    print("COMPLETE HISTORICAL DATA ANALYSIS")
    print("="*80 + "\n")
    
    # Overall statistics
    total_events = len(replay_engine.timeline)
    print(f"📊 Total Events: {total_events:,}")
    print(f"📅 Time Range: {replay_engine.start_time.strftime('%Y-%m-%d %H:%M')} to "
          f"{replay_engine.end_time.strftime('%Y-%m-%d %H:%M')}")
    
    duration = replay_engine.end_time - replay_engine.start_time
    print(f"⏱️  Duration: {duration.days} days, {duration.seconds // 3600} hours")
    
    # Event breakdown
    print(f"\n{'─'*80}")
    print("EVENT BREAKDOWN BY TYPE")
    print(f"{'─'*80}\n")
    
    event_counts = defaultdict(int)
    for event in replay_engine.timeline:
        event_counts[event.event_type.value] += 1
    
    for event_type, count in sorted(event_counts.items(), key=lambda x: x[1], reverse=True):
        pct = count / total_events * 100
        bar = "█" * int(pct / 2)
        print(f"  {event_type:20s}: {count:6,} ({pct:5.1f}%) {bar}")
    
    # Trading decisions summary
    print(f"\n{'─'*80}")
    print("TRADING DECISIONS SUMMARY")
    print(f"{'─'*80}\n")
    
    decisions = [e for e in replay_engine.timeline if e.event_type.value == 'decision']
    
    if decisions:
        buy_count = sum(1 for d in decisions if d.data.get('action') == 'buy')
        sell_count = sum(1 for d in decisions if d.data.get('action') == 'sell')
        hold_count = sum(1 for d in decisions if d.data.get('action') == 'hold')
        
        print(f"Total Decisions: {len(decisions)}")
        print(f"  🟢 BUY:  {buy_count:4d} ({buy_count/len(decisions)*100:.1f}%)")
        print(f"  🔴 SELL: {sell_count:4d} ({sell_count/len(decisions)*100:.1f}%)")
        print(f"  ⚪ HOLD: {hold_count:4d} ({hold_count/len(decisions)*100:.1f}%)")
        
        # Risk approved decisions
        approved = sum(1 for d in decisions if d.data.get('risk_approved', False))
        print(f"\n  ✅ Risk Approved: {approved} ({approved/len(decisions)*100:.1f}%)")
        
        # Executed decisions
        executed = sum(1 for d in decisions if d.data.get('executed', False))
        print(f"  ⚡ Executed: {executed} ({executed/len(decisions)*100:.1f}%)")
        
        # Symbols traded
        symbols = set(d.data.get('symbol') for d in decisions if d.data.get('symbol'))
        print(f"\n  📈 Unique Symbols: {len(symbols)}")
        print(f"     {', '.join(sorted(symbols))}")
    
    # LLM conversations
    print(f"\n{'─'*80}")
    print("LLM ANALYSIS SUMMARY")
    print(f"{'─'*80}\n")
    
    llm_events = [e for e in replay_engine.timeline if e.event_type.value == 'llm_conversation']
    
    if llm_events:
        print(f"Total LLM Conversations: {len(llm_events):,}")
        
        # Analyze sentiments
        sentiments = defaultdict(int)
        for event in llm_events:
            messages = event.data.get('messages', [])
            for msg in messages:
                if msg.get('role') == 'assistant':
                    content = msg.get('content', '')
                    # Simple sentiment extraction
                    if 'bullish' in content.lower():
                        sentiments['bullish'] += 1
                    elif 'bearish' in content.lower():
                        sentiments['bearish'] += 1
                    elif 'neutral' in content.lower():
                        sentiments['neutral'] += 1
        
        if sentiments:
            print(f"\nSentiment Distribution:")
            for sentiment, count in sorted(sentiments.items(), key=lambda x: x[1], reverse=True):
                print(f"  {sentiment.capitalize():10s}: {count:4d}")


def main():
    """Main analysis script."""
    print("\n" + "="*80)
    print("PAST DATA ANALYSIS - Using ReplayEngine")
    print("="*80)
    
    # Initialize replay engine
    print("\n🔄 Loading historical logs...")
    replay_engine = get_replay_engine()
    
    try:
        events_loaded = replay_engine.load_logs()
        print(f"✅ Loaded {events_loaded:,} events successfully!")
    except Exception as e:
        print(f"❌ Error loading logs: {e}")
        return
    
    if events_loaded == 0:
        print("\n⚠️  No historical data found!")
        print("\nTo generate historical data:")
        print("  1. Run: python scripts/run_trading.py")
        print("  2. Let it run for a few cycles")
        print("  3. Check logs/ directory for generated files")
        return
    
    # Run comprehensive analysis
    analyze_all_historical_data(replay_engine)
    
    # Analyze decisions with calculated strategies
    print("\n" + "="*80)
    decisions_with_strategies = analyze_decisions_with_strategies(replay_engine)
    
    # Export summary
    print(f"\n{'─'*80}")
    print("EXPORT OPTIONS")
    print(f"{'─'*80}\n")
    
    print("Would you like to export detailed analysis?")
    print("  1. All decisions to CSV")
    print("  2. Strategy comparison to JSON")
    print("  3. Full timeline to JSON")
    print("\n(This is informational - modify script to enable exports)")
    
    print("\n" + "="*80)
    print("✅ ANALYSIS COMPLETE")
    print("="*80 + "\n")


if __name__ == '__main__':
    main()
