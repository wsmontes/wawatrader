"""
Startup Tasks - Automatic initialization on application start

This module handles:
1. Backfilling calculated strategies for historical decisions
2. Loading historical data for analysis
3. Preparing the system for trading

Called automatically when TradingAgent is initialized.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from loguru import logger
import json


def backfill_historical_strategies(
    strategy_calculator,
    risk_manager,
    max_decisions: int = 1000
) -> Dict[str, Any]:
    """
    Backfill calculated strategies for historical decisions.
    
    This runs on startup to ensure all past decisions have baseline strategies
    for comparison analysis.
    
    Args:
        strategy_calculator: StrategyCalculator instance
        risk_manager: RiskManager instance
        max_decisions: Maximum number of decisions to backfill
    
    Returns:
        Dict with statistics about backfill operation
    """
    logger.info("🔄 Starting automatic backfill of calculated strategies...")
    
    decisions_path = Path("logs/decisions.jsonl")
    enhanced_path = Path("logs/decisions_with_strategies.jsonl")
    
    if not decisions_path.exists():
        logger.info("   No historical decisions found - skipping backfill")
        return {
            'processed': 0,
            'enhanced': 0,
            'errors': 0,
            'skipped': 0
        }
    
    # Load existing enhanced decisions to avoid duplicates
    existing_enhanced = set()
    if enhanced_path.exists():
        try:
            with open(enhanced_path, 'r') as f:
                for line in f:
                    try:
                        decision = json.loads(line)
                        # Use timestamp + symbol as unique key
                        key = f"{decision.get('timestamp')}_{decision.get('symbol')}"
                        existing_enhanced.add(key)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.warning(f"   Could not load existing enhanced decisions: {e}")
    
    # Load historical decisions
    decisions_to_process = []
    try:
        with open(decisions_path, 'r') as f:
            for line in f:
                try:
                    decision = json.loads(line)
                    key = f"{decision.get('timestamp')}_{decision.get('symbol')}"
                    
                    # Skip if already enhanced
                    if key in existing_enhanced:
                        continue
                    
                    # Skip if already has calculated_strategies
                    if 'calculated_strategies' in decision and decision['calculated_strategies']:
                        continue
                    
                    decisions_to_process.append(decision)
                    
                    if len(decisions_to_process) >= max_decisions:
                        break
                        
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logger.error(f"   Error loading decisions: {e}")
        return {'processed': 0, 'enhanced': 0, 'errors': 1, 'skipped': 0}
    
    if not decisions_to_process:
        logger.info("   All historical decisions already have calculated strategies ✓")
        return {
            'processed': 0,
            'enhanced': 0,
            'errors': 0,
            'skipped': len(existing_enhanced)
        }
    
    logger.info(f"   Found {len(decisions_to_process)} decisions to enhance")
    
    # Default historical performance
    default_performance = {
        'win_rate': 0.55,
        'avg_win': 500,
        'avg_loss': 300
    }
    
    # Process decisions
    enhanced_count = 0
    error_count = 0
    
    enhanced_decisions = []
    
    for decision in decisions_to_process:
        try:
            # Extract signals from decision
            indicators = decision.get('indicators', {})
            price_data = indicators.get('price', {})
            
            if not price_data or not price_data.get('close'):
                error_count += 1
                continue
            
            # Build signals dict
            signals = {
                'price': price_data,
                'indicators': indicators.get('indicators', {})
            }
            
            # Calculate strategies
            calculated_strategies = strategy_calculator.calculate_all_strategies(
                symbol=decision.get('symbol'),
                signals=signals,
                current_position=None,
                account_value=decision.get('account_value', 100000),
                historical_performance=default_performance
            )
            
            # Add consensus
            consensus = strategy_calculator.get_consensus_recommendation(calculated_strategies)
            calculated_strategies['consensus'] = consensus
            
            # Add to decision
            decision['calculated_strategies'] = calculated_strategies
            
            # Calculate agreement score
            llm_action = decision.get('action', 'hold')
            agreements = sum(
                1 for strat_name in ['kelly', 'momentum', 'mean_reversion', 'risk_parity', 'consensus']
                if calculated_strategies.get(strat_name, {}).get('action') == llm_action
            )
            decision['strategy_agreement_score'] = agreements / 5
            
            enhanced_decisions.append(decision)
            enhanced_count += 1
            
        except Exception as e:
            error_count += 1
            if error_count <= 3:
                logger.debug(f"   Error processing decision: {e}")
    
    # Append to enhanced file
    if enhanced_decisions:
        try:
            enhanced_path.parent.mkdir(parents=True, exist_ok=True)
            with open(enhanced_path, 'a') as f:
                for decision in enhanced_decisions:
                    f.write(json.dumps(decision) + '\n')
            
            logger.info(f"   ✅ Enhanced {enhanced_count} decisions with calculated strategies")
            if error_count > 0:
                logger.warning(f"   ⚠️  {error_count} decisions had errors during processing")
        except Exception as e:
            logger.error(f"   ❌ Error writing enhanced decisions: {e}")
            return {
                'processed': len(decisions_to_process),
                'enhanced': 0,
                'errors': error_count + 1,
                'skipped': len(existing_enhanced)
            }
    
    return {
        'processed': len(decisions_to_process),
        'enhanced': enhanced_count,
        'errors': error_count,
        'skipped': len(existing_enhanced)
    }


def load_historical_performance_stats() -> Dict[str, Dict[str, float]]:
    """
    Load historical performance statistics by symbol.
    
    Analyzes past trades to calculate win rates and average P&L
    for Kelly Criterion calculations.
    
    Returns:
        Dict mapping symbol to performance stats
    """
    logger.info("📊 Loading historical performance statistics...")
    
    decisions_path = Path("logs/decisions_with_strategies.jsonl")
    
    if not decisions_path.exists():
        logger.info("   No enhanced decisions found - using default stats")
        return {}
    
    # Track performance by symbol
    symbol_stats = {}
    
    try:
        with open(decisions_path, 'r') as f:
            for line in f:
                try:
                    decision = json.loads(line)
                    symbol = decision.get('symbol')
                    
                    if not symbol:
                        continue
                    
                    if symbol not in symbol_stats:
                        symbol_stats[symbol] = {
                            'trades': 0,
                            'wins': 0,
                            'losses': 0,
                            'total_win_amount': 0,
                            'total_loss_amount': 0
                        }
                    
                    # For now, just count decisions
                    # In future, calculate actual P&L from position data
                    symbol_stats[symbol]['trades'] += 1
                    
                except json.JSONDecodeError:
                    continue
        
        # Calculate statistics
        performance_by_symbol = {}
        
        for symbol, stats in symbol_stats.items():
            if stats['trades'] < 5:
                # Not enough data - use defaults
                continue
            
            # Use conservative estimates until we have real P&L tracking
            performance_by_symbol[symbol] = {
                'win_rate': 0.55,  # 55% default
                'avg_win': 500,
                'avg_loss': 300
            }
        
        if performance_by_symbol:
            logger.info(f"   ✅ Loaded stats for {len(performance_by_symbol)} symbols")
        else:
            logger.info("   Using default performance stats (not enough historical data)")
        
        return performance_by_symbol
        
    except Exception as e:
        logger.error(f"   Error loading performance stats: {e}")
        return {}


def run_startup_tasks(strategy_calculator, risk_manager) -> Dict[str, Any]:
    """
    Run all startup tasks.
    
    Args:
        strategy_calculator: StrategyCalculator instance
        risk_manager: RiskManager instance
    
    Returns:
        Dict with results from all startup tasks
    """
    start_time = datetime.now()
    
    logger.info("=" * 80)
    logger.info("🚀 RUNNING STARTUP TASKS")
    logger.info("=" * 80)
    
    results = {}
    
    # Task 1: Backfill calculated strategies
    try:
        backfill_result = backfill_historical_strategies(
            strategy_calculator=strategy_calculator,
            risk_manager=risk_manager,
            max_decisions=1000  # Limit to avoid long startup times
        )
        results['backfill'] = backfill_result
    except Exception as e:
        logger.error(f"❌ Backfill task failed: {e}")
        results['backfill'] = {'error': str(e)}
    
    # Task 2: Load historical performance stats
    try:
        performance_stats = load_historical_performance_stats()
        results['performance_stats'] = {
            'symbols_loaded': len(performance_stats)
        }
    except Exception as e:
        logger.error(f"❌ Performance stats task failed: {e}")
        results['performance_stats'] = {'error': str(e)}
    
    # Calculate elapsed time
    elapsed = (datetime.now() - start_time).total_seconds()
    results['elapsed_time'] = elapsed
    
    logger.info("=" * 80)
    logger.info(f"✅ STARTUP TASKS COMPLETE ({elapsed:.1f}s)")
    logger.info("=" * 80)
    
    # Print summary
    if 'backfill' in results and 'enhanced' in results['backfill']:
        backfill = results['backfill']
        logger.info(f"   Backfill: {backfill['enhanced']} enhanced, "
                   f"{backfill['skipped']} already done, "
                   f"{backfill['errors']} errors")
    
    if 'performance_stats' in results:
        stats = results['performance_stats']
        logger.info(f"   Performance: {stats.get('symbols_loaded', 0)} symbols loaded")
    
    logger.info("")
    
    return results
