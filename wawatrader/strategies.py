"""
Professional Day Trading Strategy Library

This module contains proven day trading patterns and execution procedures from
legendary traders. These strategies are TRIGGERED by LLM signals but follow
strict professional execution rules.

Strategy Sources:
- Mark Minervini: Momentum breakouts, SEPA methodology
- Al Brooks: Price action patterns, trend bars
- Ross Cameron: Gap & go, momentum scalping
- Andrew Aziz: VWAP strategies, opening range
- Kristjan Kullamägi: Gap trading specialist
- Peter Brandt: Chart patterns, classic TA

CRITICAL DESIGN:
- LLM identifies the SETUP (bullish signal, support bounce, etc.)
- Strategy library provides EXECUTION (entry, stop, targets, management)
- Combines AI intelligence with proven human trading wisdom

Author: WawaTrader Team
Date: 2024
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, time
from loguru import logger
import pandas as pd
import numpy as np


class StrategyType(Enum):
    """Day trading strategy types."""
    
    # Momentum Strategies
    GAP_AND_GO = "gap_and_go"  # Gap up + volume surge
    BREAKOUT_PULLBACK = "breakout_pullback"  # Break high, pullback, re-entry
    VWAP_MOMENTUM = "vwap_momentum"  # Riding VWAP trend
    
    # Reversal Strategies
    SUPPORT_BOUNCE = "support_bounce"  # Bounce off key support
    RESISTANCE_REJECTION = "resistance_rejection"  # Short at resistance
    VWAP_REVERSION = "vwap_reversion"  # Mean reversion to VWAP
    
    # Pattern Strategies
    BULL_FLAG = "bull_flag"  # Classic continuation pattern
    BEAR_FLAG = "bear_flag"  # Bearish continuation
    OPENING_RANGE_BREAKOUT = "opening_range_breakout"  # First 30min breakout
    
    # Scalping Strategies
    MOMENTUM_SCALP = "momentum_scalp"  # Quick 1-2% moves
    LEVEL_TO_LEVEL = "level_to_level"  # Support to resistance trades
    
    # Advanced Patterns
    ABCD_PATTERN = "abcd_pattern"  # Harmonic price movement
    TRAP_REVERSAL = "trap_reversal"  # False breakout reversal


class TimeOfDay(Enum):
    """Trading session periods."""
    PREMARKET = "premarket"  # 4:00 AM - 9:30 AM ET
    OPENING = "opening"  # 9:30 AM - 10:00 AM ET
    MORNING = "morning"  # 10:00 AM - 11:30 AM ET
    MIDDAY = "midday"  # 11:30 AM - 2:00 PM ET
    AFTERNOON = "afternoon"  # 2:00 PM - 3:00 PM ET
    POWER_HOUR = "power_hour"  # 3:00 PM - 4:00 PM ET
    AFTERHOURS = "afterhours"  # 4:00 PM - 8:00 PM ET


class RiskLevel(Enum):
    """Risk tolerance levels."""
    CONSERVATIVE = "conservative"  # Tight stops, smaller size
    MODERATE = "moderate"  # Balanced approach
    AGGRESSIVE = "aggressive"  # Wider stops, larger size


@dataclass
class StrategySetup:
    """
    Complete strategy execution plan.
    
    This is what gets returned to the trading agent for execution.
    """
    strategy_type: StrategyType
    
    # Entry Rules (required)
    entry_price: float
    entry_condition: str
    
    # Stop Loss (required)
    stop_loss: float
    stop_reason: str
    
    # Profit Targets (required)
    target_1: float  # First target (scale out 50%)
    target_2: float  # Second target (scale out 30%)
    
    # Optional fields with defaults
    max_slippage: float = 0.005  # 0.5% max slippage
    trailing_stop: bool = False
    target_3: Optional[float] = None  # Runner (20%)
    
    # Position Sizing
    position_size_pct: float = 0.10  # 10% of portfolio
    max_shares: Optional[int] = None
    
    # Time Management
    max_hold_time_minutes: int = 240  # 4 hours max
    exit_before_close: bool = True  # Close before 3:55 PM
    
    # Risk Management
    risk_reward_ratio: float = 2.0  # Minimum R:R
    risk_per_trade_pct: float = 0.02  # 2% risk per trade
    
    # Execution Notes
    pattern_confidence: float = 0.0  # How well does setup match pattern?
    best_time_of_day: List[TimeOfDay] = field(default_factory=list)
    volume_requirement: float = 1.5  # Minimum volume ratio
    
    # Metadata
    pattern_source: str = ""  # Which trader's methodology
    setup_notes: str = ""
    invalidation_rules: List[str] = field(default_factory=list)


class DayTradingStrategyLibrary:
    """
    Professional day trading strategy library.
    
    Maps LLM signals to proven execution procedures from trading masters.
    """
    
    def __init__(self):
        """Initialize strategy library."""
        self.strategies = self._build_strategy_catalog()
        logger.info(f"📚 Strategy library initialized with {len(self.strategies)} patterns")
    
    def match_strategy(
        self,
        llm_signal: Dict[str, Any],
        technical_data: Dict[str, Any],
        market_context: Dict[str, Any]
    ) -> Optional[StrategySetup]:
        """
        Match LLM signal to best strategy pattern.
        
        Args:
            llm_signal: LLM decision (action, confidence, reasoning)
            technical_data: Current price, indicators, volume
            market_context: Time of day, market regime, volatility
        
        Returns:
            Complete strategy setup with entry/stop/targets, or None
        """
        action = llm_signal.get('action', '').upper()
        
        if action not in ['BUY', 'SELL']:
            return None
        
        # Extract key data
        price = technical_data.get('price', 0)
        if price == 0:
            return None
        
        # Try to match pattern based on technical setup
        strategy = self._identify_pattern(technical_data, market_context)
        
        if not strategy:
            logger.warning("No strategy pattern matched - using default")
            strategy = self._get_default_strategy(action)
        
        # Build complete execution plan
        setup = self._build_execution_plan(
            strategy_type=strategy,
            action=action,
            price=price,
            technical_data=technical_data,
            market_context=market_context,
            llm_confidence=llm_signal.get('confidence', 50)
        )
        
        return setup
    
    def _identify_pattern(
        self,
        technical_data: Dict[str, Any],
        market_context: Dict[str, Any]
    ) -> Optional[StrategyType]:
        """
        Identify which strategy pattern fits current market setup.
        
        Pattern Recognition Logic:
        1. Check for gap patterns (premarket/opening)
        2. Check for VWAP setups
        3. Check for support/resistance bounces
        4. Check for momentum patterns
        5. Check for classic chart patterns
        
        Returns the BEST matching pattern.
        """
        price = technical_data.get('price', 0)
        rsi = technical_data.get('rsi', 50)
        volume_ratio = technical_data.get('volume_ratio', 1.0)
        vwap = technical_data.get('vwap', price)
        sma_20 = technical_data.get('sma_20', price)
        sma_50 = technical_data.get('sma_50', price)
        
        time_of_day = market_context.get('time_of_day', TimeOfDay.MORNING)
        
        # 1. GAP AND GO Pattern (Ross Cameron)
        # High volume gap up in premarket/opening
        if time_of_day in [TimeOfDay.PREMARKET, TimeOfDay.OPENING]:
            gap_pct = (price - sma_20) / sma_20 if sma_20 > 0 else 0
            if gap_pct > 0.02 and volume_ratio > 2.0:
                logger.info("🎯 Pattern matched: GAP AND GO (Ross Cameron)")
                return StrategyType.GAP_AND_GO
        
        # 2. VWAP Momentum (Andrew Aziz)
        # Price riding above VWAP with strong volume
        if price > vwap and volume_ratio > 1.5:
            vwap_distance = (price - vwap) / vwap
            if 0.001 < vwap_distance < 0.03:  # 0.1% - 3% above VWAP
                logger.info("🎯 Pattern matched: VWAP MOMENTUM (Andrew Aziz)")
                return StrategyType.VWAP_MOMENTUM
        
        # 3. Support Bounce (Al Brooks)
        # Price at key support (VWAP, SMA20) with RSI oversold
        if rsi < 35:
            at_vwap = abs(price - vwap) / price < 0.005  # Within 0.5% of VWAP
            at_sma20 = abs(price - sma_20) / price < 0.005
            if at_vwap or at_sma20:
                logger.info("🎯 Pattern matched: SUPPORT BOUNCE (Al Brooks)")
                return StrategyType.SUPPORT_BOUNCE
        
        # 4. Breakout Pullback (Mark Minervini)
        # Stock breaks out, pulls back to breakout level
        if price > sma_20 > sma_50:  # Uptrend
            pullback_to_20 = abs(price - sma_20) / price < 0.01  # Within 1%
            if pullback_to_20 and volume_ratio > 1.2:
                logger.info("🎯 Pattern matched: BREAKOUT PULLBACK (Minervini)")
                return StrategyType.BREAKOUT_PULLBACK
        
        # 5. Opening Range Breakout (Peter Brandt)
        # Break of first 30-minute range
        if time_of_day == TimeOfDay.MORNING:
            # Would need OR high/low from market data
            # Simplified: look for momentum after 10 AM
            if volume_ratio > 1.3 and rsi > 55:
                logger.info("🎯 Pattern matched: OPENING RANGE BREAKOUT")
                return StrategyType.OPENING_RANGE_BREAKOUT
        
        # 6. VWAP Reversion (Mean Reversion)
        # Price extended from VWAP, likely to snap back
        if price > vwap:
            vwap_distance = (price - vwap) / vwap
            if vwap_distance > 0.05 and rsi > 70:  # >5% above + overbought
                logger.info("🎯 Pattern matched: VWAP REVERSION (mean reversion)")
                return StrategyType.VWAP_REVERSION
        
        # 7. Momentum Scalp (Ross Cameron)
        # Fast moving stock, quick in-and-out
        if volume_ratio > 2.5 and 45 < rsi < 70:
            logger.info("🎯 Pattern matched: MOMENTUM SCALP (Ross Cameron)")
            return StrategyType.MOMENTUM_SCALP
        
        return None
    
    def _build_execution_plan(
        self,
        strategy_type: StrategyType,
        action: str,
        price: float,
        technical_data: Dict[str, Any],
        market_context: Dict[str, Any],
        llm_confidence: float
    ) -> StrategySetup:
        """
        Build complete execution plan based on strategy type.
        
        Each strategy has specific:
        - Entry rules
        - Stop placement
        - Target levels
        - Position sizing
        - Time management
        
        This is where trading master knowledge is encoded.
        """
        if strategy_type == StrategyType.GAP_AND_GO:
            return self._gap_and_go_setup(action, price, technical_data, llm_confidence)
        
        elif strategy_type == StrategyType.VWAP_MOMENTUM:
            return self._vwap_momentum_setup(action, price, technical_data, llm_confidence)
        
        elif strategy_type == StrategyType.SUPPORT_BOUNCE:
            return self._support_bounce_setup(action, price, technical_data, llm_confidence)
        
        elif strategy_type == StrategyType.BREAKOUT_PULLBACK:
            return self._breakout_pullback_setup(action, price, technical_data, llm_confidence)
        
        elif strategy_type == StrategyType.OPENING_RANGE_BREAKOUT:
            return self._opening_range_breakout_setup(action, price, technical_data, llm_confidence)
        
        elif strategy_type == StrategyType.VWAP_REVERSION:
            return self._vwap_reversion_setup(action, price, technical_data, llm_confidence)
        
        elif strategy_type == StrategyType.MOMENTUM_SCALP:
            return self._momentum_scalp_setup(action, price, technical_data, llm_confidence)
        
        else:
            return self._default_setup(action, price, technical_data, llm_confidence)
    
    # ============================================================================
    # STRATEGY IMPLEMENTATIONS - Trading Master Methodologies
    # ============================================================================
    
    def _gap_and_go_setup(
        self,
        action: str,
        price: float,
        technical_data: Dict[str, Any],
        confidence: float
    ) -> StrategySetup:
        """
        GAP AND GO Strategy (Ross Cameron)
        
        Setup: Stock gaps up 2-5% on news/volume surge
        Entry: First pullback after gap (9:30-10:30 AM)
        Stop: Below premarket low or VWAP
        Target: 5-10% gain, scale out in pieces
        
        Key Rules:
        - Must have volume 2x+ average
        - Gap should be 2-5% (not too small, not too extended)
        - Best in first 1-2 hours
        - Exit before lunch (11:30 AM)
        """
        vwap = technical_data.get('vwap', price)
        sma_20 = technical_data.get('sma_20', price * 0.98)
        
        # Entry: Current price (on pullback to VWAP or consolidation)
        entry = price
        
        # Stop: Below VWAP or -2% from entry
        stop_vwap = vwap * 0.995  # 0.5% below VWAP
        stop_pct = price * 0.98  # 2% below entry
        stop = max(stop_vwap, stop_pct)
        
        # Targets: Scale out aggressively
        risk = entry - stop
        target_1 = entry + (risk * 2.0)  # 2R - take 50% off
        target_2 = entry + (risk * 3.5)  # 3.5R - take 30% off
        target_3 = entry + (risk * 5.0)  # 5R - let runner go
        
        return StrategySetup(
            strategy_type=StrategyType.GAP_AND_GO,
            entry_price=entry,
            entry_condition="Enter on first pullback after gap up",
            stop_loss=stop,
            stop_reason="Below VWAP or -2% from entry",
            target_1=target_1,
            target_2=target_2,
            target_3=target_3,
            position_size_pct=0.15,  # Larger size (15%)
            max_hold_time_minutes=120,  # Exit by 11:30 AM
            risk_reward_ratio=2.0,
            risk_per_trade_pct=0.025,  # 2.5% risk (aggressive)
            pattern_confidence=confidence / 100.0,
            best_time_of_day=[TimeOfDay.OPENING, TimeOfDay.MORNING],
            volume_requirement=2.0,
            pattern_source="Ross Cameron - Gap & Go Master",
            setup_notes="Gap up 2-5% on volume, first pullback entry",
            invalidation_rules=[
                "If price drops below premarket low - exit immediately",
                "If volume dies after 10 AM - consider exit",
                "If gap fills (returns to previous close) - exit"
            ]
        )
    
    def _vwap_momentum_setup(
        self,
        action: str,
        price: float,
        technical_data: Dict[str, Any],
        confidence: float
    ) -> StrategySetup:
        """
        VWAP Momentum Strategy (Andrew Aziz)
        
        Setup: Stock trending above VWAP with volume
        Entry: On pullback to VWAP or slight break above
        Stop: Below VWAP
        Target: Previous resistance or +3% move
        
        Key Rules:
        - Stock must be above VWAP
        - VWAP acting as support
        - Volume above average
        - Works best 10 AM - 2 PM
        """
        vwap = technical_data.get('vwap', price * 0.99)
        bb_upper = technical_data.get('bb_upper', price * 1.02)
        
        entry = price
        
        # Stop: Just below VWAP
        stop = vwap * 0.995  # 0.5% below VWAP
        
        # Targets: Conservative scaling
        risk = entry - stop
        target_1 = entry + (risk * 2.0)  # 2R
        target_2 = entry + (risk * 3.0)  # 3R
        target_3 = min(bb_upper, entry + (risk * 4.0))  # 4R or BB upper
        
        return StrategySetup(
            strategy_type=StrategyType.VWAP_MOMENTUM,
            entry_price=entry,
            entry_condition="Price holds above VWAP with volume confirmation",
            stop_loss=stop,
            stop_reason="Break below VWAP = trend failure",
            trailing_stop=True,  # Trail stop to VWAP as price rises
            target_1=target_1,
            target_2=target_2,
            target_3=target_3,
            position_size_pct=0.12,
            max_hold_time_minutes=180,
            risk_reward_ratio=2.0,
            risk_per_trade_pct=0.02,
            pattern_confidence=confidence / 100.0,
            best_time_of_day=[TimeOfDay.MORNING, TimeOfDay.MIDDAY],
            volume_requirement=1.5,
            pattern_source="Andrew Aziz - VWAP Specialist",
            setup_notes="Riding VWAP trend with trailing stop",
            invalidation_rules=[
                "Close below VWAP = exit all",
                "Loss of volume momentum = tighten stops",
                "Multiple rejections at resistance = exit"
            ]
        )
    
    def _support_bounce_setup(
        self,
        action: str,
        price: float,
        technical_data: Dict[str, Any],
        confidence: float
    ) -> StrategySetup:
        """
        Support Bounce Strategy (Al Brooks)
        
        Setup: Price tests key support (VWAP, SMA, previous low)
        Entry: On reversal candle at support
        Stop: Below support level
        Target: Previous resistance or midpoint
        
        Key Rules:
        - Clear support level
        - RSI oversold (<35)
        - Reversal price action (bullish engulfing, hammer)
        - Quick entry/exit (support can break)
        """
        vwap = technical_data.get('vwap', price)
        sma_20 = technical_data.get('sma_20', price * 0.99)
        
        # Support is the stronger of VWAP or SMA20
        support = max(vwap, sma_20)
        
        entry = price
        
        # Stop: Below support with buffer
        stop = support * 0.995  # 0.5% below support
        
        # Targets: Conservative (support plays are lower probability)
        risk = entry - stop
        target_1 = entry + (risk * 1.5)  # 1.5R - take 60% off
        target_2 = entry + (risk * 2.5)  # 2.5R - take 30% off  
        target_3 = entry + (risk * 4.0)  # 4R - runner
        
        return StrategySetup(
            strategy_type=StrategyType.SUPPORT_BOUNCE,
            entry_price=entry,
            entry_condition="Reversal candle at key support level",
            stop_loss=stop,
            stop_reason="Break of support = failed pattern",
            target_1=target_1,
            target_2=target_2,
            target_3=target_3,
            position_size_pct=0.08,  # Smaller size (8%) - lower confidence
            max_hold_time_minutes=120,
            risk_reward_ratio=1.5,  # Lower R:R acceptable
            risk_per_trade_pct=0.015,  # 1.5% risk
            pattern_confidence=confidence / 100.0,
            best_time_of_day=[TimeOfDay.MORNING, TimeOfDay.AFTERNOON],
            volume_requirement=1.2,
            pattern_source="Al Brooks - Price Action Master",
            setup_notes="Bounce off support with reversal confirmation",
            invalidation_rules=[
                "Break below support = exit immediately",
                "No follow-through within 5-10 min = exit",
                "Large red candle after entry = exit"
            ]
        )
    
    def _breakout_pullback_setup(
        self,
        action: str,
        price: float,
        technical_data: Dict[str, Any],
        confidence: float
    ) -> StrategySetup:
        """
        Breakout Pullback Strategy (Mark Minervini - SEPA)
        
        Setup: Stock breaks resistance, pulls back to breakout level
        Entry: On first pullback to 20 SMA after breakout
        Stop: Below 20 SMA or breakout level
        Target: Measured move from base
        
        Key Rules:
        - Stock in uptrend (SMA20 > SMA50)
        - Volume on breakout
        - Pullback on low volume (healthy)
        - Re-entry on volume increase
        """
        sma_20 = technical_data.get('sma_20', price * 0.98)
        sma_50 = technical_data.get('sma_50', price * 0.96)
        
        entry = price
        
        # Stop: Below 20 SMA with buffer
        stop = sma_20 * 0.99  # 1% below SMA20
        
        # Targets: Minervini style - let winners run
        risk = entry - stop
        target_1 = entry + (risk * 2.0)  # 2R - take 40%
        target_2 = entry + (risk * 4.0)  # 4R - take 30%
        target_3 = entry + (risk * 6.0)  # 6R - hold 30%
        
        return StrategySetup(
            strategy_type=StrategyType.BREAKOUT_PULLBACK,
            entry_price=entry,
            entry_condition="Pullback to 20 SMA after breakout",
            stop_loss=stop,
            stop_reason="Below 20 SMA = trend failure",
            trailing_stop=True,  # Trail to 20 SMA
            target_1=target_1,
            target_2=target_2,
            target_3=target_3,
            position_size_pct=0.12,
            max_hold_time_minutes=300,  # Can hold longer (5 hours)
            risk_reward_ratio=2.0,
            risk_per_trade_pct=0.02,
            pattern_confidence=confidence / 100.0,
            best_time_of_day=[TimeOfDay.MORNING, TimeOfDay.MIDDAY, TimeOfDay.AFTERNOON],
            volume_requirement=1.3,
            pattern_source="Mark Minervini - SEPA Methodology",
            setup_notes="Breakout pullback in established uptrend",
            invalidation_rules=[
                "Close below 20 SMA = exit",
                "Loss of uptrend structure = exit",
                "Volume dries up = tighten stops"
            ]
        )
    
    def _opening_range_breakout_setup(
        self,
        action: str,
        price: float,
        technical_data: Dict[str, Any],
        confidence: float
    ) -> StrategySetup:
        """
        Opening Range Breakout (Peter Brandt / Classic TA)
        
        Setup: Break of first 30-minute range with volume
        Entry: On break of OR high (9:30-10:00 AM range)
        Stop: Below OR low
        Target: OR height projected from breakout
        
        Key Rules:
        - Wait for 10:00 AM to define range
        - Volume must increase on breakout
        - Best with tight range (consolidation)
        - Exit by end of day (3:55 PM)
        """
        entry = price
        
        # Stop: Estimate OR low (would be better with actual data)
        # Assume OR is ~2% of price
        or_low = price * 0.98
        stop = or_low * 0.995
        
        # Target: Measured move (OR height from breakout)
        risk = entry - stop
        or_height = risk * 1.5  # Approximate
        target_1 = entry + or_height  # 1x OR height
        target_2 = entry + (or_height * 1.5)  # 1.5x OR height
        target_3 = entry + (or_height * 2.0)  # 2x OR height
        
        return StrategySetup(
            strategy_type=StrategyType.OPENING_RANGE_BREAKOUT,
            entry_price=entry,
            entry_condition="Break of opening range high with volume",
            stop_loss=stop,
            stop_reason="Below opening range low",
            target_1=target_1,
            target_2=target_2,
            target_3=target_3,
            position_size_pct=0.10,
            max_hold_time_minutes=300,
            risk_reward_ratio=1.5,
            risk_per_trade_pct=0.02,
            pattern_confidence=confidence / 100.0,
            best_time_of_day=[TimeOfDay.MORNING],
            volume_requirement=1.5,
            pattern_source="Peter Brandt - Classic Chart Patterns",
            setup_notes="Opening range breakout with volume confirmation",
            invalidation_rules=[
                "False breakout (returns to range) = exit",
                "Loss of momentum = exit",
                "Break back into range = stop out"
            ]
        )
    
    def _vwap_reversion_setup(
        self,
        action: str,
        price: float,
        technical_data: Dict[str, Any],
        confidence: float
    ) -> StrategySetup:
        """
        VWAP Mean Reversion (Fade Extended Moves)
        
        Setup: Stock extended >5% from VWAP, overbought RSI
        Entry: Short when showing weakness
        Stop: Above recent high
        Target: VWAP
        
        Key Rules:
        - COUNTER-TREND trade (higher risk)
        - Must have clear overextension
        - RSI >70 for longs, <30 for shorts
        - Quick in-and-out (mean reversion is fast)
        """
        vwap = technical_data.get('vwap', price * 0.95)
        rsi = technical_data.get('rsi', 70)
        
        entry = price
        
        # Stop: Tight stop above recent high (estimate +1.5%)
        stop = price * 1.015
        
        # Target: VWAP (mean reversion target)
        risk = stop - entry
        target_1 = entry - (risk * 1.5)  # Move toward VWAP
        target_2 = vwap * 1.005  # Near VWAP
        target_3 = vwap * 0.995  # Through VWAP
        
        # Adjust targets based on VWAP distance
        target_1 = max(target_1, (price + vwap) / 2)  # Midpoint
        target_2 = max(target_2, vwap * 1.003)
        
        return StrategySetup(
            strategy_type=StrategyType.VWAP_REVERSION,
            entry_price=entry,
            entry_condition="Extended from VWAP + overbought + weakness",
            stop_loss=stop,
            stop_reason="Continuation above high = wrong side",
            target_1=target_1,
            target_2=target_2,
            target_3=target_3,
            position_size_pct=0.06,  # Small size (counter-trend)
            max_hold_time_minutes=60,  # Quick trade
            risk_reward_ratio=1.5,
            risk_per_trade_pct=0.015,
            pattern_confidence=confidence / 100.0,
            best_time_of_day=[TimeOfDay.MORNING, TimeOfDay.MIDDAY],
            volume_requirement=1.0,
            pattern_source="Mean Reversion / VWAP Fade",
            setup_notes="Counter-trend mean reversion to VWAP",
            invalidation_rules=[
                "Continuation higher = exit immediately",
                "No progress toward VWAP in 15 min = exit",
                "Volume surge against you = exit"
            ]
        )
    
    def _momentum_scalp_setup(
        self,
        action: str,
        price: float,
        technical_data: Dict[str, Any],
        confidence: float
    ) -> StrategySetup:
        """
        Momentum Scalp Strategy (Ross Cameron)
        
        Setup: High volume momentum, quick 1-2% moves
        Entry: On volume surge confirmation
        Stop: Tight stop (-1%)
        Target: Quick 1-2% profit
        
        Key Rules:
        - FAST execution required
        - Volume 2.5x+ average
        - Quick in-and-out (5-15 minutes)
        - Scale out quickly
        - Don't overstay welcome
        """
        entry = price
        
        # Stop: Very tight (-1%)
        stop = price * 0.99
        
        # Targets: Quick profits
        risk = entry - stop
        target_1 = entry + (risk * 1.0)  # 1R - take 70%
        target_2 = entry + (risk * 2.0)  # 2R - take 25%
        target_3 = entry + (risk * 3.0)  # 3R - runner 5%
        
        return StrategySetup(
            strategy_type=StrategyType.MOMENTUM_SCALP,
            entry_price=entry,
            entry_condition="Volume surge with momentum",
            stop_loss=stop,
            stop_reason="Tight stop for scalp (-1%)",
            target_1=target_1,
            target_2=target_2,
            target_3=target_3,
            position_size_pct=0.20,  # Large size for scalp
            max_hold_time_minutes=15,  # Very quick
            risk_reward_ratio=1.0,  # Accept 1:1 (high win rate)
            risk_per_trade_pct=0.01,  # Only 1% risk
            pattern_confidence=confidence / 100.0,
            best_time_of_day=[TimeOfDay.OPENING, TimeOfDay.MORNING],
            volume_requirement=2.5,
            pattern_source="Ross Cameron - Momentum Scalping",
            setup_notes="High volume momentum scalp, quick profits",
            invalidation_rules=[
                "Loss of momentum = exit immediately",
                "No follow-through in 2 min = exit",
                "If down more than -0.5% = exit"
            ]
        )
    
    def _default_setup(
        self,
        action: str,
        price: float,
        technical_data: Dict[str, Any],
        confidence: float
    ) -> StrategySetup:
        """
        Default/Balanced Strategy
        
        Used when no specific pattern matches.
        Conservative entry with standard risk management.
        """
        entry = price
        stop = price * 0.98  # 2% stop
        
        risk = entry - stop
        target_1 = entry + (risk * 2.0)
        target_2 = entry + (risk * 3.0)
        target_3 = entry + (risk * 4.0)
        
        return StrategySetup(
            strategy_type=StrategyType.OPENING_RANGE_BREAKOUT,  # Default
            entry_price=entry,
            entry_condition="Standard entry on LLM signal",
            stop_loss=stop,
            stop_reason="Standard 2% stop",
            target_1=target_1,
            target_2=target_2,
            target_3=target_3,
            position_size_pct=0.10,
            max_hold_time_minutes=240,
            risk_reward_ratio=2.0,
            risk_per_trade_pct=0.02,
            pattern_confidence=confidence / 100.0,
            best_time_of_day=[TimeOfDay.MORNING, TimeOfDay.AFTERNOON],
            volume_requirement=1.0,
            pattern_source="Default Strategy",
            setup_notes="No specific pattern matched - using balanced approach",
            invalidation_rules=["Standard stop loss"]
        )
    
    def _get_default_strategy(self, action: str) -> StrategyType:
        """Get default strategy type."""
        return StrategyType.OPENING_RANGE_BREAKOUT
    
    def _build_strategy_catalog(self) -> Dict[StrategyType, Dict[str, Any]]:
        """
        Build catalog of all available strategies.
        
        Returns metadata about each strategy for selection/display.
        """
        return {
            StrategyType.GAP_AND_GO: {
                'name': 'Gap and Go',
                'source': 'Ross Cameron',
                'win_rate': 0.65,  # Approximate
                'avg_r_multiple': 2.5,
                'best_time': [TimeOfDay.OPENING, TimeOfDay.MORNING],
                'risk_level': RiskLevel.AGGRESSIVE,
            },
            StrategyType.VWAP_MOMENTUM: {
                'name': 'VWAP Momentum',
                'source': 'Andrew Aziz',
                'win_rate': 0.60,
                'avg_r_multiple': 2.0,
                'best_time': [TimeOfDay.MORNING, TimeOfDay.MIDDAY],
                'risk_level': RiskLevel.MODERATE,
            },
            StrategyType.SUPPORT_BOUNCE: {
                'name': 'Support Bounce',
                'source': 'Al Brooks',
                'win_rate': 0.55,
                'avg_r_multiple': 1.5,
                'best_time': [TimeOfDay.MORNING, TimeOfDay.AFTERNOON],
                'risk_level': RiskLevel.CONSERVATIVE,
            },
            StrategyType.BREAKOUT_PULLBACK: {
                'name': 'Breakout Pullback',
                'source': 'Mark Minervini',
                'win_rate': 0.70,
                'avg_r_multiple': 3.0,
                'best_time': [TimeOfDay.MORNING, TimeOfDay.MIDDAY],
                'risk_level': RiskLevel.MODERATE,
            },
            StrategyType.OPENING_RANGE_BREAKOUT: {
                'name': 'Opening Range Breakout',
                'source': 'Peter Brandt',
                'win_rate': 0.58,
                'avg_r_multiple': 1.8,
                'best_time': [TimeOfDay.MORNING],
                'risk_level': RiskLevel.MODERATE,
            },
            StrategyType.MOMENTUM_SCALP: {
                'name': 'Momentum Scalp',
                'source': 'Ross Cameron',
                'win_rate': 0.75,  # High win rate, small R
                'avg_r_multiple': 1.0,
                'best_time': [TimeOfDay.OPENING],
                'risk_level': RiskLevel.AGGRESSIVE,
            },
        }
    
    def get_strategy_info(self, strategy_type: StrategyType) -> Dict[str, Any]:
        """Get information about a specific strategy."""
        return self.strategies.get(strategy_type, {})
    
    def list_strategies(self) -> List[Dict[str, Any]]:
        """List all available strategies."""
        return [
            {
                'type': str(st.value),
                **info
            }
            for st, info in self.strategies.items()
        ]


# ============================================================================
# INTEGRATION HELPERS
# ============================================================================

def apply_strategy_to_trade(
    llm_decision: Dict[str, Any],
    technical_data: Dict[str, Any],
    market_context: Dict[str, Any],
    portfolio_value: float
) -> Optional[Dict[str, Any]]:
    """
    Apply strategy library to LLM decision.
    
    This is the main integration point for TradingAgent.
    
    Args:
        llm_decision: LLM output (action, confidence, reasoning)
        technical_data: Price, indicators, volume
        market_context: Time of day, volatility, market regime
        portfolio_value: Current portfolio size
    
    Returns:
        Complete trade order with strategy-based risk management
    """
    library = DayTradingStrategyLibrary()
    
    # Match pattern and get execution plan
    setup = library.match_strategy(llm_decision, technical_data, market_context)
    
    if not setup:
        logger.warning("No strategy match - skipping trade")
        return None
    
    # Calculate position size based on strategy risk
    risk_dollars = portfolio_value * setup.risk_per_trade_pct
    risk_per_share = setup.entry_price - setup.stop_loss
    
    if risk_per_share <= 0:
        logger.error("Invalid risk calculation")
        return None
    
    shares = int(risk_dollars / risk_per_share)
    
    # Apply max position size limit
    max_position_dollars = portfolio_value * setup.position_size_pct
    max_shares = int(max_position_dollars / setup.entry_price)
    shares = min(shares, max_shares)
    
    if shares < 1:
        logger.warning("Position size too small")
        return None
    
    # Build complete trade order
    trade_order = {
        'symbol': technical_data.get('symbol', 'UNKNOWN'),
        'action': llm_decision.get('action'),
        'shares': shares,
        'entry_price': setup.entry_price,
        'stop_loss': setup.stop_loss,
        'target_1': setup.target_1,
        'target_2': setup.target_2,
        'target_3': setup.target_3,
        'strategy_type': setup.strategy_type.value,
        'strategy_source': setup.pattern_source,
        'max_hold_minutes': setup.max_hold_time_minutes,
        'exit_before_close': setup.exit_before_close,
        'trailing_stop': setup.trailing_stop,
        'risk_reward': setup.risk_reward_ratio,
        'pattern_confidence': setup.pattern_confidence,
        'llm_confidence': llm_decision.get('confidence', 0),
        'setup_notes': setup.setup_notes,
        'invalidation_rules': setup.invalidation_rules,
        'timestamp': datetime.now().isoformat()
    }
    
    logger.info(f"📋 Strategy matched: {setup.strategy_type.value}")
    logger.info(f"   Entry: ${setup.entry_price:.2f} | Stop: ${setup.stop_loss:.2f}")
    target_3_str = f"${setup.target_3:.2f}" if setup.target_3 else "N/A"
    logger.info(f"   Targets: ${setup.target_1:.2f} / ${setup.target_2:.2f} / {target_3_str}")
    logger.info(f"   Position: {shares} shares (${shares * setup.entry_price:.2f})")
    logger.info(f"   Risk: ${shares * risk_per_share:.2f} ({setup.risk_per_trade_pct*100:.1f}%)")
    logger.info(f"   Source: {setup.pattern_source}")
    
    return trade_order


if __name__ == "__main__":
    # Demo: Show strategy library in action
    print("📚 Day Trading Strategy Library - Demo\n")
    
    library = DayTradingStrategyLibrary()
    
    print(f"Loaded {len(library.strategies)} professional strategies:\n")
    for strategy in library.list_strategies():
        print(f"  • {strategy['name']} ({strategy['source']})")
        print(f"    Win Rate: {strategy['win_rate']*100:.0f}% | Avg R: {strategy['avg_r_multiple']}R")
        print(f"    Best Time: {', '.join([t.value for t in strategy['best_time']])}")
        print(f"    Risk: {strategy['risk_level'].value}\n")
