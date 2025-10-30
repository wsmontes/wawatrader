"""
Strategy Calculator - Pure Math Baseline Recommendations

Calculates what different mathematical strategies would recommend WITHOUT LLM input.
This provides:
1. Control group for measuring LLM value-add
2. Fallback recommendations when LLM unavailable
3. Comparison metrics for each decision

Each strategy provides same fields as LLM analysis for direct comparison.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger
import pandas as pd
import numpy as np


class StrategyCalculator:
    """
    Calculate pure mathematical strategy recommendations.
    
    Provides multiple baseline strategies:
    - Kelly Criterion (optimal position sizing)
    - Technical Momentum (trend following)
    - Mean Reversion (contrarian)
    - Risk Parity (volatility-weighted)
    
    Each strategy returns same structure as LLM analysis.
    """
    
    def __init__(self, risk_manager=None):
        """
        Initialize strategy calculator.
        
        Args:
            risk_manager: RiskManager instance for Kelly calculations
        """
        self.risk_manager = risk_manager
        logger.info("Strategy Calculator initialized")
    
    def calculate_all_strategies(
        self,
        symbol: str,
        signals: Dict[str, Any],
        current_position: Optional[Dict],
        account_value: float,
        historical_performance: Optional[Dict] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calculate recommendations from all baseline strategies.
        
        Args:
            symbol: Stock ticker
            signals: Technical indicators and signals
            current_position: Current position if any
            account_value: Total account value
            historical_performance: Historical win/loss data for Kelly
        
        Returns:
            Dictionary mapping strategy name to recommendation
        """
        strategies = {}
        
        # 1. Kelly Criterion Strategy
        strategies['kelly'] = self._kelly_strategy(
            symbol, signals, current_position, account_value, historical_performance
        )
        
        # 2. Technical Momentum Strategy
        strategies['momentum'] = self._momentum_strategy(
            symbol, signals, current_position, account_value
        )
        
        # 3. Mean Reversion Strategy
        strategies['mean_reversion'] = self._mean_reversion_strategy(
            symbol, signals, current_position, account_value
        )
        
        # 4. Risk Parity Strategy
        strategies['risk_parity'] = self._risk_parity_strategy(
            symbol, signals, current_position, account_value
        )
        
        return strategies
    
    def _kelly_strategy(
        self,
        symbol: str,
        signals: Dict[str, Any],
        current_position: Optional[Dict],
        account_value: float,
        historical_performance: Optional[Dict]
    ) -> Dict[str, Any]:
        """
        Kelly Criterion: Optimal position sizing based on win rate.
        
        BUY: If Kelly recommends positive position and no position held
        SELL: If Kelly recommends zero and position held
        HOLD: Otherwise
        """
        price = signals['price']['close']
        
        # Default historical performance if none provided
        if not historical_performance:
            historical_performance = {
                'win_rate': 0.55,  # 55% default
                'avg_win': 500,
                'avg_loss': 300
            }
        
        # Calculate Kelly position if risk_manager available
        if self.risk_manager:
            kelly_result = self.risk_manager.calculate_kelly_position_size(
                symbol=symbol,
                win_rate=historical_performance.get('win_rate', 0.55),
                avg_win=historical_performance.get('avg_win', 500),
                avg_loss=historical_performance.get('avg_loss', 300),
                account_value=account_value,
                current_price=price,
                max_kelly_fraction=0.25
            )
            
            recommended_shares = kelly_result['recommended_shares']
            kelly_pct = kelly_result['bounded_kelly_pct']
        else:
            # Fallback calculation
            win_rate = historical_performance.get('win_rate', 0.55)
            avg_win = historical_performance.get('avg_win', 500)
            avg_loss = historical_performance.get('avg_loss', 300)
            
            win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 1.5
            kelly_pct = ((win_loss_ratio * win_rate - (1 - win_rate)) / win_loss_ratio) * 0.25
            kelly_pct = max(0, min(kelly_pct, 0.10))
            
            recommended_shares = int((account_value * kelly_pct) / price)
        
        # Determine action
        has_position = current_position is not None and current_position.get('qty', 0) > 0
        
        if kelly_pct > 0.01 and not has_position:
            action = 'buy'
            confidence = min(90, int(kelly_pct * 500))  # Scale to 0-90
            reasoning = f"Kelly Criterion recommends {kelly_pct*100:.1f}% position ({recommended_shares} shares)"
        elif kelly_pct <= 0.01 and has_position:
            action = 'sell'
            confidence = 70
            reasoning = f"Kelly Criterion recommends zero position (current {kelly_pct*100:.1f}%)"
        else:
            action = 'hold'
            confidence = 50
            reasoning = f"Kelly position {kelly_pct*100:.1f}% matches current state"
        
        return {
            'strategy': 'kelly_criterion',
            'action': action,
            'confidence': confidence,
            'sentiment': 'neutral',
            'reasoning': reasoning,
            'recommended_shares': recommended_shares,
            'position_pct': kelly_pct,
            'target_price': price * 1.10,  # +10% target
            'stop_loss': price * 0.95,  # -5% stop
            'time_horizon': 'medium',
            'calculated_at': datetime.now().isoformat()
        }
    
    def _momentum_strategy(
        self,
        symbol: str,
        signals: Dict[str, Any],
        current_position: Optional[Dict],
        account_value: float
    ) -> Dict[str, Any]:
        """
        Momentum: Follow the trend.
        
        BUY: Strong uptrend (price > SMA, RSI < 70, MACD positive)
        SELL: Trend reversal (price < SMA, RSI > 70, MACD negative)
        HOLD: Mixed signals
        """
        price = signals['price']['close']
        sma_20 = signals['indicators'].get('sma_20', price)
        sma_50 = signals['indicators'].get('sma_50', price)
        rsi = signals['indicators'].get('rsi', 50)
        macd = signals['indicators'].get('macd', 0)
        volume = signals['price'].get('volume', 0)
        avg_volume = signals['indicators'].get('avg_volume_20', volume)
        
        # Calculate momentum score
        momentum_score = 0
        
        # Price above moving averages (+2 each)
        if price > sma_20:
            momentum_score += 2
        if price > sma_50:
            momentum_score += 2
        
        # RSI in momentum range (+2)
        if 40 < rsi < 70:
            momentum_score += 2
        elif rsi > 70:
            momentum_score -= 2  # Overbought
        
        # MACD positive (+2)
        if macd > 0:
            momentum_score += 2
        
        # Volume confirmation (+1)
        if volume > avg_volume * 1.2:
            momentum_score += 1
        
        # Determine action based on momentum score
        has_position = current_position is not None and current_position.get('qty', 0) > 0
        
        if momentum_score >= 6 and not has_position:
            action = 'buy'
            confidence = min(90, 50 + momentum_score * 5)
            reasoning = f"Strong momentum (score: {momentum_score}/9): Price>${sma_20:.2f}, RSI={rsi:.0f}, MACD={macd:.2f}"
        elif momentum_score <= 2 and has_position:
            action = 'sell'
            confidence = 70
            reasoning = f"Momentum weakening (score: {momentum_score}/9): Consider exit"
        else:
            action = 'hold'
            confidence = 50
            reasoning = f"Mixed momentum signals (score: {momentum_score}/9)"
        
        # Position sizing: 5% for momentum trades
        recommended_shares = int((account_value * 0.05) / price)
        
        return {
            'strategy': 'momentum',
            'action': action,
            'confidence': confidence,
            'sentiment': 'bullish' if momentum_score > 5 else 'bearish' if momentum_score < 3 else 'neutral',
            'reasoning': reasoning,
            'recommended_shares': recommended_shares,
            'position_pct': 0.05,
            'target_price': price * 1.15,  # +15% for momentum
            'stop_loss': price * 0.92,  # -8% stop
            'time_horizon': 'short',
            'momentum_score': momentum_score,
            'calculated_at': datetime.now().isoformat()
        }
    
    def _mean_reversion_strategy(
        self,
        symbol: str,
        signals: Dict[str, Any],
        current_position: Optional[Dict],
        account_value: float
    ) -> Dict[str, Any]:
        """
        Mean Reversion: Buy oversold, sell overbought.
        
        BUY: Oversold conditions (RSI < 30, price < BB lower)
        SELL: Overbought conditions (RSI > 70, price > BB upper)
        HOLD: Normal range
        """
        price = signals['price']['close']
        rsi = signals['indicators'].get('rsi', 50)
        sma_20 = signals['indicators'].get('sma_20', price)
        bb_lower = signals['indicators'].get('bb_lower', price * 0.95)
        bb_upper = signals['indicators'].get('bb_upper', price * 1.05)
        
        # Calculate reversion score
        reversion_score = 0
        
        # RSI oversold/overbought
        if rsi < 30:
            reversion_score += 3  # Strong oversold
        elif rsi < 40:
            reversion_score += 2  # Moderate oversold
        elif rsi > 70:
            reversion_score -= 3  # Strong overbought
        elif rsi > 60:
            reversion_score -= 2  # Moderate overbought
        
        # Bollinger Band position
        if price < bb_lower:
            reversion_score += 3  # Below lower band
        elif price < sma_20 * 0.98:
            reversion_score += 1  # Below mean
        elif price > bb_upper:
            reversion_score -= 3  # Above upper band
        elif price > sma_20 * 1.02:
            reversion_score -= 1  # Above mean
        
        # Determine action
        has_position = current_position is not None and current_position.get('qty', 0) > 0
        
        if reversion_score >= 4 and not has_position:
            action = 'buy'
            confidence = min(85, 50 + reversion_score * 7)
            reasoning = f"Oversold - Mean reversion opportunity (score: {reversion_score}): RSI={rsi:.0f}, Price=${price:.2f} vs SMA=${sma_20:.2f}"
        elif reversion_score <= -4 and has_position:
            action = 'sell'
            confidence = 75
            reasoning = f"Overbought - Take profits (score: {reversion_score}): RSI={rsi:.0f}"
        else:
            action = 'hold'
            confidence = 50
            reasoning = f"Price near mean (score: {reversion_score}): Wait for extremes"
        
        # Position sizing: 4% for mean reversion
        recommended_shares = int((account_value * 0.04) / price)
        
        return {
            'strategy': 'mean_reversion',
            'action': action,
            'confidence': confidence,
            'sentiment': 'bullish' if reversion_score > 3 else 'bearish' if reversion_score < -3 else 'neutral',
            'reasoning': reasoning,
            'recommended_shares': recommended_shares,
            'position_pct': 0.04,
            'target_price': sma_20,  # Target = mean
            'stop_loss': price * 0.90 if reversion_score > 0 else price * 1.10,
            'time_horizon': 'short',
            'reversion_score': reversion_score,
            'calculated_at': datetime.now().isoformat()
        }
    
    def _risk_parity_strategy(
        self,
        symbol: str,
        signals: Dict[str, Any],
        current_position: Optional[Dict],
        account_value: float
    ) -> Dict[str, Any]:
        """
        Risk Parity: Size positions inversely to volatility.
        
        Lower volatility → Larger position
        Higher volatility → Smaller position
        
        Action based on trend + volatility regime.
        """
        price = signals['price']['close']
        sma_50 = signals['indicators'].get('sma_50', price)
        
        # Estimate volatility from ATR
        atr = signals['indicators'].get('atr', price * 0.02)
        volatility = atr / price  # ATR as % of price
        
        # Target volatility: 15% annual = ~1% daily
        target_daily_vol = 0.01
        vol_adjustment = min(2.0, max(0.25, target_daily_vol / volatility)) if volatility > 0 else 1.0
        
        # Base position: 6%
        base_position_pct = 0.06
        adjusted_position_pct = base_position_pct * vol_adjustment
        adjusted_position_pct = min(0.10, adjusted_position_pct)  # Cap at 10%
        
        # Determine action based on trend
        trend_score = 0
        if price > sma_50:
            trend_score += 2
        if price > sma_50 * 1.05:
            trend_score += 1
        
        has_position = current_position is not None and current_position.get('qty', 0) > 0
        
        if trend_score >= 2 and not has_position:
            action = 'buy'
            confidence = 65
            reasoning = f"Uptrend with vol-adjusted sizing: {adjusted_position_pct*100:.1f}% (vol={volatility*100:.1f}%, adj={vol_adjustment:.2f}x)"
        elif trend_score <= 0 and has_position:
            action = 'sell'
            confidence = 65
            reasoning = f"Downtrend - Exit position"
        else:
            action = 'hold'
            confidence = 50
            reasoning = f"Neutral trend (score: {trend_score}), vol-adjusted sizing ready"
        
        recommended_shares = int((account_value * adjusted_position_pct) / price)
        
        return {
            'strategy': 'risk_parity',
            'action': action,
            'confidence': confidence,
            'sentiment': 'bullish' if trend_score >= 2 else 'bearish' if trend_score <= 0 else 'neutral',
            'reasoning': reasoning,
            'recommended_shares': recommended_shares,
            'position_pct': adjusted_position_pct,
            'target_price': price * 1.08,
            'stop_loss': price * 0.93,
            'time_horizon': 'medium',
            'volatility': volatility,
            'vol_adjustment': vol_adjustment,
            'calculated_at': datetime.now().isoformat()
        }
    
    def get_consensus_recommendation(
        self,
        strategies: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate consensus from all strategies.
        
        Args:
            strategies: Dictionary of strategy recommendations
        
        Returns:
            Consensus recommendation with vote breakdown
        """
        # Count votes
        buy_votes = sum(1 for s in strategies.values() if s['action'] == 'buy')
        sell_votes = sum(1 for s in strategies.values() if s['action'] == 'sell')
        hold_votes = sum(1 for s in strategies.values() if s['action'] == 'hold')
        
        total_votes = len(strategies)
        
        # Determine consensus action
        if buy_votes > total_votes / 2:
            consensus_action = 'buy'
            consensus_confidence = int((buy_votes / total_votes) * 100)
        elif sell_votes > total_votes / 2:
            consensus_action = 'sell'
            consensus_confidence = int((sell_votes / total_votes) * 100)
        else:
            consensus_action = 'hold'
            consensus_confidence = 50
        
        # Average recommended shares from buy strategies
        buy_strategies = [s for s in strategies.values() if s['action'] == 'buy']
        avg_shares = int(np.mean([s['recommended_shares'] for s in buy_strategies])) if buy_strategies else 0
        
        # Average position %
        avg_position_pct = np.mean([s['position_pct'] for s in strategies.values()])
        
        return {
            'strategy': 'consensus',
            'action': consensus_action,
            'confidence': consensus_confidence,
            'sentiment': 'neutral',
            'reasoning': f"Consensus: {buy_votes}B/{sell_votes}S/{hold_votes}H ({total_votes} strategies)",
            'recommended_shares': avg_shares,
            'position_pct': avg_position_pct,
            'vote_breakdown': {
                'buy': buy_votes,
                'sell': sell_votes,
                'hold': hold_votes,
                'total': total_votes
            },
            'contributing_strategies': list(strategies.keys()),
            'calculated_at': datetime.now().isoformat()
        }


def get_strategy_calculator(risk_manager=None) -> StrategyCalculator:
    """Factory function to get StrategyCalculator instance."""
    return StrategyCalculator(risk_manager=risk_manager)
