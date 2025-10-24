"""
Market State Detection and Management

This module provides intelligent market state detection to enable adaptive
behavior based on time of day and market hours. The system operates in 5
distinct modes to optimize resource usage and focus.

Author: WawaTrader Team
Created: October 2025
"""

from datetime import datetime, time
from enum import Enum
from typing import Dict, Any, Optional
from loguru import logger
from zoneinfo import ZoneInfo


class MarketState(Enum):
    """
    Defines the operational states of the trading system.
    
    Each state has different objectives and activities:
    - ACTIVE_TRADING: Live trading with real-time decisions
    - MARKET_CLOSING: End-of-day transition and summary
    - EVENING_ANALYSIS: Deep research and preparation
    - OVERNIGHT_SLEEP: Minimal monitoring, resource conservation
    - PREMARKET_PREP: Strategic preparation for market open
    """
    ACTIVE_TRADING = "active_trading"      # 9:30 AM - 3:30 PM ET
    MARKET_CLOSING = "market_closing"      # 3:30 PM - 4:30 PM ET
    EVENING_ANALYSIS = "evening_analysis"  # 4:30 PM - 10:00 PM ET
    OVERNIGHT_SLEEP = "overnight_sleep"    # 10:00 PM - 6:00 AM ET
    PREMARKET_PREP = "premarket_prep"      # 6:00 AM - 9:30 AM ET

    @property
    def emoji(self) -> str:
        """Get emoji representation of state"""
        return {
            MarketState.ACTIVE_TRADING: "🟢",
            MarketState.MARKET_CLOSING: "🟡",
            MarketState.EVENING_ANALYSIS: "🔴",
            MarketState.OVERNIGHT_SLEEP: "💤",
            MarketState.PREMARKET_PREP: "🌅",
        }[self]
    
    @property
    def description(self) -> str:
        """Get human-readable description"""
        return {
            MarketState.ACTIVE_TRADING: "Active Trading",
            MarketState.MARKET_CLOSING: "Market Closing",
            MarketState.EVENING_ANALYSIS: "Evening Analysis",
            MarketState.OVERNIGHT_SLEEP: "Overnight Sleep",
            MarketState.PREMARKET_PREP: "Pre-Market Prep",
        }[self]
    
    @property
    def primary_focus(self) -> str:
        """Get primary focus for this state"""
        return {
            MarketState.ACTIVE_TRADING: "Live trading with real-time decisions",
            MarketState.MARKET_CLOSING: "End-of-day summary and preparation",
            MarketState.EVENING_ANALYSIS: "Deep analysis, research, and preparation",
            MarketState.OVERNIGHT_SLEEP: "Minimal monitoring, resource conservation",
            MarketState.PREMARKET_PREP: "Strategic preparation for market open",
        }[self]


class MarketStateDetector:
    """
    Detects current market state based on market hours and time of day.
    
    Uses Alpaca market clock to determine if market is open, then applies
    time-based rules to determine the appropriate operational state.
    """
    
    def __init__(self, alpaca_client=None):
        """
        Initialize market state detector.
        
        Args:
            alpaca_client: Optional AlpacaClient instance for market status.
                          If None, will be imported when needed.
        """
        self.alpaca_client = alpaca_client
        self._last_state = None
        self._last_check = None
    
    def get_current_state(self, force_refresh: bool = False) -> MarketState:
        """
        Determine the current market state.
        
        Args:
            force_refresh: If True, bypass cache and check fresh state
            
        Returns:
            Current MarketState enum value
        """
        # Cache for 1 minute to avoid excessive API calls
        now = datetime.now()
        if not force_refresh and self._last_check:
            time_since = (now - self._last_check).total_seconds()
            if time_since < 60 and self._last_state:
                return self._last_state
        
        # Get market status if we have alpaca client
        market_is_open = False
        if self.alpaca_client:
            try:
                market_status = self.alpaca_client.get_market_status()
                market_is_open = market_status.get('is_open', False)
            except Exception as e:
                logger.warning(f"Failed to get market status, assuming closed: {e}")
        
        # Get current time in ET
        et_tz = ZoneInfo("America/New_York")
        current_time_et = datetime.now(et_tz)
        current_hour = current_time_et.hour
        current_minute = current_time_et.minute
        
        # Determine state based on market status and time
        state = self._determine_state(
            market_is_open=market_is_open,
            hour=current_hour,
            minute=current_minute
        )
        
        # Log state transitions
        if state != self._last_state:
            logger.info(
                f"{state.emoji} Market state transition: "
                f"{self._last_state.description if self._last_state else 'None'} → "
                f"{state.description}"
            )
            logger.info(f"   Primary focus: {state.primary_focus}")
        
        self._last_state = state
        self._last_check = now
        
        return state
    
    def _determine_state(
        self,
        market_is_open: bool,
        hour: int,
        minute: int
    ) -> MarketState:
        """
        Determine market state based on market hours and time.
        
        Args:
            market_is_open: Whether the market is currently open
            hour: Current hour (0-23) in ET
            minute: Current minute (0-59)
            
        Returns:
            Appropriate MarketState
        """
        # Convert hour and minute to total minutes since midnight
        time_minutes = hour * 60 + minute
        
        # Market hours in ET (9:30 AM = 570 min, 4:00 PM = 960 min)
        market_open_time = 9 * 60 + 30   # 9:30 AM = 570 minutes
        market_close_time = 16 * 60       # 4:00 PM = 960 minutes
        closing_prep_time = 15 * 60 + 30 # 3:30 PM = 930 minutes
        closing_end_time = 16 * 60 + 30  # 4:30 PM = 990 minutes
        evening_end_time = 22 * 60        # 10:00 PM = 1320 minutes
        premarket_start_time = 6 * 60     # 6:00 AM = 360 minutes
        
        # Active trading: Market is open and after 9:30 AM, before closing prep
        if market_is_open and time_minutes >= market_open_time and time_minutes < closing_prep_time:
            return MarketState.ACTIVE_TRADING
        
        # Market closing: 3:30 PM - 4:30 PM ET
        if closing_prep_time <= time_minutes < closing_end_time:
            return MarketState.MARKET_CLOSING
        
        # Pre-market prep: 6:00 AM - 9:30 AM ET
        if premarket_start_time <= time_minutes < market_open_time:
            return MarketState.PREMARKET_PREP
        
        # Evening analysis: 4:30 PM - 10:00 PM ET
        if closing_end_time <= time_minutes < evening_end_time:
            return MarketState.EVENING_ANALYSIS
        
        # Overnight sleep: 10:00 PM - 6:00 AM ET
        return MarketState.OVERNIGHT_SLEEP
    
    def get_state_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about current market state.
        
        Returns:
            Dictionary with state details, timing, and recommendations
        """
        current_state = self.get_current_state()
        
        et_tz = ZoneInfo("America/New_York")
        current_time_et = datetime.now(et_tz)
        
        return {
            "state": current_state.value,
            "emoji": current_state.emoji,
            "description": current_state.description,
            "primary_focus": current_state.primary_focus,
            "current_time_et": current_time_et.strftime("%I:%M %p ET"),
            "recommendations": self._get_recommendations(current_state),
        }
    
    def _get_recommendations(self, state: MarketState) -> list[str]:
        """Get recommended activities for current state"""
        recommendations = {
            MarketState.ACTIVE_TRADING: [
                "Run trading cycles every 5 minutes",
                "Quick intelligence checks every 30 minutes",
                "Deep analysis every 2 hours",
                "Focus on real-time decision making",
            ],
            MarketState.MARKET_CLOSING: [
                "Assess open positions for overnight risk",
                "Calculate day's P&L and performance",
                "Generate daily summary report",
                "Prepare tomorrow's watchlist",
            ],
            MarketState.EVENING_ANALYSIS: [
                "Comprehensive earnings calendar analysis",
                "Deep sector rotation analysis",
                "International markets preview",
                "Tomorrow's game plan preparation",
            ],
            MarketState.OVERNIGHT_SLEEP: [
                "Monitor for breaking news (every 2 hours)",
                "Check futures for significant moves (>2%)",
                "System maintenance and cleanup",
                "Minimal resource usage",
            ],
            MarketState.PREMARKET_PREP: [
                "Review overnight international markets",
                "Analyze pre-market movers and gaps",
                "Update sector momentum analysis",
                "Finalize market open strategy",
            ],
        }
        return recommendations[state]
    
    def should_run_intensive_tasks(self) -> bool:
        """
        Check if intensive tasks (LLM analysis, deep research) should run.
        
        Returns:
            True if current state allows intensive tasks
        """
        current_state = self.get_current_state()
        return current_state in [
            MarketState.ACTIVE_TRADING,
            MarketState.EVENING_ANALYSIS,
            MarketState.PREMARKET_PREP,
        ]
    
    def should_sleep(self) -> bool:
        """
        Check if system should be in minimal activity mode.
        
        Returns:
            True if in overnight sleep mode
        """
        return self.get_current_state() == MarketState.OVERNIGHT_SLEEP


def get_market_state(alpaca_client=None) -> MarketState:
    """
    Convenience function to get current market state.
    
    Args:
        alpaca_client: Optional AlpacaClient instance
        
    Returns:
        Current MarketState
    """
    detector = MarketStateDetector(alpaca_client)
    return detector.get_current_state()


def display_market_state_info(alpaca_client=None) -> None:
    """
    Display comprehensive market state information.
    
    Args:
        alpaca_client: Optional AlpacaClient instance
    """
    detector = MarketStateDetector(alpaca_client)
    info = detector.get_state_info()
    
    logger.info("=" * 60)
    logger.info(f"{info['emoji']} MARKET STATE: {info['description'].upper()}")
    logger.info("=" * 60)
    logger.info(f"Current Time: {info['current_time_et']}")
    logger.info(f"Primary Focus: {info['primary_focus']}")
    logger.info("")
    logger.info("Recommended Activities:")
    for i, rec in enumerate(info['recommendations'], 1):
        logger.info(f"  {i}. {rec}")
    logger.info("=" * 60)


if __name__ == "__main__":
    """Quick test of market state detection"""
    logger.info("Testing Market State Detection System...")
    logger.info("")
    
    # Display current state
    display_market_state_info()
    
    # Test state detection at various times
    logger.info("\nTesting state detection at various times:")
    detector = MarketStateDetector()
    
    test_cases = [
        (10, 0, "10:00 AM - Active Trading"),
        (15, 0, "3:00 PM - Still Active Trading"),
        (15, 45, "3:45 PM - Market Closing"),
        (17, 0, "5:00 PM - Evening Analysis"),
        (22, 30, "10:30 PM - Overnight Sleep"),
        (7, 0, "7:00 AM - Pre-Market Prep"),
    ]
    
    for hour, minute, description in test_cases:
        state = detector._determine_state(
            market_is_open=(9 <= hour < 16),
            hour=hour,
            minute=minute
        )
        logger.info(f"  {state.emoji} {description}: {state.description}")
