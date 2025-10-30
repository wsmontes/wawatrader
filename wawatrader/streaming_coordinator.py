"""
Streaming Portfolio Decision Coordinator

Balances individual LLM analysis quality with intelligent decision prioritization.
Executes decisions as they complete using mathematical ranking.
"""

import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from loguru import logger

from wawatrader.trading_agent import TradingDecision


class StreamingPortfolioCoordinator:
    """
    Coordinates decision execution with streaming intelligence.
    
    Strategy:
    1. IMMEDIATE: Execute urgent decisions (stop-losses, breakouts)  
    2. ACCUMULATE: Queue BUY decisions for brief comparison window
    3. EXECUTE: Process batches when threshold reached OR timeout
    4. ADAPTIVE: Adjust behavior based on market conditions
    """
    
    def __init__(self, trading_agent):
        """
        Initialize streaming coordinator.
        
        Args:
            trading_agent: TradingAgent instance for context
        """
        self.agent = trading_agent
        self.pending_decisions = []
        self.executed_decisions = []
        self.session_stats = {
            'total_analyzed': 0,
            'immediate_executions': 0,
            'batch_executions': 0,
            'skipped_capital': 0
        }
        
        # Adaptive thresholds
        self.comparison_window = 45  # seconds to wait for more decisions
        self.min_comparison_batch = 2   # minimum to compare
        self.max_comparison_batch = 6   # execute when this many pending
        
        # Market-aware adjustments
        self._adjust_thresholds_for_market()
        
        logger.info("🎯 Streaming Portfolio Coordinator initialized")
        logger.info(f"   Comparison window: {self.comparison_window}s")
        logger.info(f"   Batch size: {self.min_comparison_batch}-{self.max_comparison_batch}")
    
    def process_decision(self, decision: TradingDecision) -> bool:
        """
        Process individual decision with streaming coordination logic.
        
        Args:
            decision: Trading decision from LLM analysis
            
        Returns:
            True if processed successfully
        """
        self.session_stats['total_analyzed'] += 1
        
        # Add timestamp if not present or convert string timestamp to datetime
        if not hasattr(decision, 'timestamp'):
            decision.timestamp = datetime.now()
        elif isinstance(decision.timestamp, str):
            # Convert ISO string to datetime object for comparison
            decision.timestamp = datetime.fromisoformat(decision.timestamp.replace('Z', '+00:00'))
        
        logger.info(f"📋 DECISION: {decision.symbol} {decision.action.upper()} "
                   f"(conf: {decision.confidence}%, ${decision.price:.2f})")
        
        # PHASE 1: IMMEDIATE EXECUTION (Urgent Cases)
        if self._is_urgent(decision):
            logger.info(f"🚨 URGENT EXECUTION: {decision.symbol} {decision.action}")
            success = self._execute_immediately(decision)
            if success:
                self.session_stats['immediate_executions'] += 1
            return success
        
        # PHASE 2: ACCUMULATE BUY DECISIONS FOR COMPARISON
        if decision.action.lower() == "buy":
            self.pending_decisions.append(decision)
            logger.info(f"📊 QUEUED FOR COMPARISON: {decision.symbol} "
                       f"({len(self.pending_decisions)} pending)")
            
            # Execute batch if we have enough decisions
            if len(self.pending_decisions) >= self.max_comparison_batch:
                logger.info(f"🎯 BATCH TRIGGER: {len(self.pending_decisions)} decisions ready")
                return self._execute_best_opportunities()
            
            # Or if oldest decision is getting stale
            if self._is_comparison_window_expired():
                logger.info(f"⏰ TIMEOUT TRIGGER: Executing after {self.comparison_window}s")
                return self._execute_best_opportunities()
        
        # PHASE 3: DIRECT EXECUTION (SELL/HOLD)
        elif decision.action.lower() == "sell":
            logger.info(f"📉 DIRECT SELL: {decision.symbol}")
            return self._execute_immediately(decision)
        
        else:  # HOLD
            logger.debug(f"💤 HOLD: {decision.symbol} (no action)")
            
        return True
    
    def finalize_cycle(self) -> Dict[str, Any]:
        """
        Complete any pending decisions at end of cycle.
        
        Returns:
            Cycle summary statistics
        """
        # Execute any remaining pending decisions
        if self.pending_decisions:
            logger.info(f"🏁 CYCLE END: Executing {len(self.pending_decisions)} remaining decisions")
            self._execute_best_opportunities()
        
        # Return session statistics
        stats = self.session_stats.copy()
        
        # Reset for next cycle
        self.pending_decisions = []
        self.session_stats = {key: 0 for key in self.session_stats.keys()}
        
        return stats
    
    def _is_urgent(self, decision: TradingDecision) -> bool:
        """Detect decisions requiring immediate execution"""
        
        # 1. STOP LOSSES (urgent sells to limit losses)
        if decision.action.lower() == "sell":
            position = self.agent.positions.get(decision.symbol)
            if position:
                entry_price = float(position.get('avg_entry_price', decision.price))
                current_pnl_pct = ((decision.price - entry_price) / entry_price) * 100
                
                if current_pnl_pct < -3.0:  # > 3% loss
                    logger.warning(f"🛑 STOP LOSS: {decision.symbol} at {current_pnl_pct:.1f}% loss")
                    return True
        
        # 2. BREAKOUT SIGNALS (time-sensitive momentum)
        if decision.action.lower() == "buy" and hasattr(decision, 'indicators'):
            indicators = decision.indicators or {}
            volume_ratio = indicators.get('volume_ratio', 1.0)
            rsi = indicators.get('rsi', 50)
            
            # High volume breakout above resistance
            if volume_ratio > 2.5 and 60 <= rsi <= 75:
                logger.info(f"🚀 BREAKOUT: {decision.symbol} (vol: {volume_ratio:.1f}x, RSI: {rsi})")
                return True
        
        # 3. MARKET CLOSING URGENCY (high confidence near close)
        market_minutes_left = self._get_market_minutes_remaining()
        if market_minutes_left < 30 and decision.confidence > 80:
            logger.info(f"⏰ CLOSING URGENCY: {decision.symbol} ({market_minutes_left} min left)")
            return True
        
        return False
    
    def _execute_immediately(self, decision: TradingDecision) -> bool:
        """Execute single decision immediately"""
        try:
            # Use existing agent execution logic
            success = self.agent.execute_decision(decision)
            
            if success:
                self.executed_decisions.append(decision)
                logger.success(f"✅ EXECUTED: {decision.symbol} {decision.action}")
            else:
                logger.error(f"❌ EXECUTION FAILED: {decision.symbol} {decision.action}")
                
            return success
            
        except Exception as e:
            logger.error(f"❌ EXECUTION ERROR: {decision.symbol} - {e}")
            return False
    
    def _is_comparison_window_expired(self) -> bool:
        """Check if we should execute pending decisions due to timeout"""
        if not self.pending_decisions:
            return False
            
        oldest_decision = min(self.pending_decisions, key=lambda d: d.timestamp)
        elapsed_seconds = (datetime.now() - oldest_decision.timestamp).total_seconds()
        
        return elapsed_seconds >= self.comparison_window
    
    def _execute_best_opportunities(self) -> bool:
        """Execute highest priority opportunities from pending batch"""
        
        if not self.pending_decisions:
            return True
        
        logger.info(f"🎯 BATCH EXECUTION: Prioritizing {len(self.pending_decisions)} BUY opportunities")
        
        # Calculate priority scores
        for decision in self.pending_decisions:
            decision.priority_score = self._calculate_priority_score(decision)
        
        # Sort by priority (highest first)
        sorted_decisions = sorted(
            self.pending_decisions,
            key=lambda d: d.priority_score,
            reverse=True
        )
        
        # Log prioritization
        logger.info("📊 PRIORITY RANKING:")
        for i, decision in enumerate(sorted_decisions[:5], 1):
            logger.info(f"   {i}. {decision.symbol}: {decision.priority_score:.1f} "
                       f"(conf: {decision.confidence}%)")
        
        # Execute as many as capital allows
        executed_count = 0
        try:
            available_capital = float(self.agent.alpaca.get_account()['buying_power'])
        except AttributeError:
            # Handle mock agent without alpaca client
            available_capital = getattr(self.agent, 'buying_power', 50000)
        
        for decision in sorted_decisions:
            required_capital = decision.shares * decision.price
            
            if available_capital >= required_capital:
                logger.info(f"✅ EXECUTING #{executed_count+1}: {decision.symbol} "
                           f"(score: {decision.priority_score:.1f})")
                
                success = self._execute_immediately(decision)
                if success:
                    executed_count += 1
                    available_capital -= required_capital
                    self.session_stats['batch_executions'] += 1
                    
            else:
                logger.info(f"💰 CAPITAL LIMIT: {decision.symbol} needs ${required_capital:,.0f}, "
                           f"available ${available_capital:,.0f}")
                self.session_stats['skipped_capital'] += 1
        
        # Clear pending decisions
        self.pending_decisions = []
        
        logger.success(f"🏆 BATCH COMPLETE: {executed_count} decisions executed")
        return True
    
    def _calculate_priority_score(self, decision: TradingDecision) -> float:
        """Calculate mathematical priority score"""
        
        # Base score from LLM confidence
        score = decision.confidence
        
        # Technical indicator bonuses
        if hasattr(decision, 'indicators') and decision.indicators:
            indicators = decision.indicators
            
            # RSI momentum (0-15 points)
            rsi = indicators.get('rsi', 50)
            if 40 <= rsi <= 60:  # Neutral zone
                score += 10
            elif 30 <= rsi <= 40 or 60 <= rsi <= 70:  # Good momentum
                score += 15
            
            # Volume confirmation (0-20 points)
            volume_ratio = indicators.get('volume_ratio', 1.0)
            score += min(volume_ratio * 8, 20)
            
            # MACD signal (0-10 points)
            macd_signal = indicators.get('macd_signal_strength', 0)
            if macd_signal > 0:
                score += min(macd_signal * 5, 10)
        
        # Market timing bonus (0-15 points)
        market_minutes = self._get_market_minutes_remaining()
        if 60 <= market_minutes <= 300:  # 1-5 hours left (optimal window)
            score += 15
        elif market_minutes < 60:  # Less than 1 hour (urgency)
            score += 10
        
        # Portfolio diversification (0-10 points)
        current_positions = len(self.agent.positions)
        if current_positions < 5:  # Room for more positions
            score += 10
        elif current_positions > 8:  # Too many positions
            score -= 5
        
        return max(0, score)
    
    def _get_market_minutes_remaining(self) -> int:
        """Get minutes until market close"""
        try:
            market_status = self.agent.alpaca.get_market_status()
            if market_status.get('is_open', False):
                # Estimate based on typical market close (4 PM ET)
                now = datetime.now()
                market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
                if now.hour >= 16:  # After market close
                    return 0
                else:
                    return int((market_close - now).total_seconds() / 60)
            else:
                return 0
        except:
            return 240  # Default to 4 hours if unknown
    
    def _adjust_thresholds_for_market(self):
        """Adjust coordination thresholds based on market conditions"""
        try:
            market_minutes = self._get_market_minutes_remaining()
            
            # More aggressive near market close
            if market_minutes < 60:
                self.comparison_window = 20  # Shorter wait
                self.max_comparison_batch = 4  # Smaller batches
                logger.info("⏰ MARKET CLOSE MODE: Reduced coordination delays")
            
            # More patient during market open
            elif market_minutes > 300:
                self.comparison_window = 60  # Longer comparison
                self.max_comparison_batch = 8  # Larger batches
                logger.info("🌅 MARKET OPEN MODE: Extended coordination window")
                
        except Exception as e:
            logger.warning(f"Could not adjust thresholds: {e}")