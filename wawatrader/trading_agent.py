"""
Trading Agent Orchestrator

Main loop that coordinates all components:
- Market data collection
- Technical analysis
- LLM sentiment analysis
- Risk validation
- Trade execution
- Decision logging

This is the "brain" of WawaTrader.
"""

import json
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from pathlib import Path
from loguru import logger

from wawatrader.alpaca_client import get_client
from wawatrader.indicators import analyze_dataframe, get_latest_signals
from wawatrader.llm_v2 import ModularLLMAnalyzer  # NEW: Modular prompt system with simplified format
from wawatrader.risk_manager import get_risk_manager
from wawatrader.strategy_calculator import get_strategy_calculator  # NEW: Pure math strategy baselines
from wawatrader.startup_tasks import run_startup_tasks  # NEW: Automatic backfilling and initialization
from wawatrader.market_intelligence import get_intelligence_engine
from wawatrader.learning_engine import LearningEngine
from wawatrader.position_manager import PositionManager
from config.settings import settings

# EVENT-DRIVEN ARCHITECTURE IMPORTS
from wawatrader.decision_memory import (
    get_memory_store, 
    DecisionMemory, 
    DecisionType,
    ThesisRealityComparator
)
from wawatrader.event_system import (
    get_event_queue,
    Event,
    EventType,
    EventPriority,
    PriceAlertMonitor,
    VolumeMonitor
)
from wawatrader.position_sizing import (
    KellyLLMPositionSizer,
    PortfolioRiskManager
)

# PHASE 4: MARKET HOURS INTEGRATION
from wawatrader.market_hours_manager import MarketHoursManager, MarketPhase
from wawatrader.symbol_discovery import SymbolDiscoveryEngine


@dataclass
class TradingDecision:
    """Record of a trading decision"""
    timestamp: str
    symbol: str
    action: str  # "buy", "sell", "hold"
    shares: int
    price: float
    confidence: float
    sentiment: str
    reasoning: str
    risk_approved: bool
    risk_reason: str
    executed: bool
    execution_error: Optional[str] = None
    
    # Context
    indicators: Optional[Dict[str, Any]] = None
    llm_analysis: Optional[Dict[str, Any]] = None
    calculated_strategies: Optional[Dict[str, Any]] = None  # NEW: Pure math strategy baselines
    account_value: Optional[float] = None
    current_pnl: Optional[float] = None


class TradingAgent:
    """
    Main trading agent - orchestrates all components.
    
    Architecture:
    1. Fetch market data (prices, news)
    2. Calculate technical indicators
    3. Get LLM sentiment analysis
    4. Validate with risk manager
    5. Execute trade (if approved)
    6. Log decision (success or failure)
    """
    
    def __init__(self, symbols: List[str], dry_run: bool = False):
        """
        Initialize trading agent.
        
        Args:
            symbols: List of stock symbols to trade (e.g., ["AAPL", "MSFT"])
            dry_run: If True, don't execute trades (simulation mode)
        """
        self.symbols = symbols
        self.dry_run = dry_run
        
        # Initialize components
        self.alpaca = get_client()
        self.llm_bridge = ModularLLMAnalyzer()  # NEW: Using modular LLM with simplified prompts
        self.risk_manager = get_risk_manager()
        self.strategy_calculator = get_strategy_calculator(risk_manager=self.risk_manager)  # NEW: Pure math baselines
        self.intelligence_engine = get_intelligence_engine()
        self.learning_engine = LearningEngine(self.alpaca)
        
        # EVENT-DRIVEN ARCHITECTURE COMPONENTS (NEW)
        self.event_queue = get_event_queue()
        self.memory_store = get_memory_store()
        self.comparator = ThesisRealityComparator(self.memory_store)
        self.kelly_sizer = KellyLLMPositionSizer(self.memory_store)
        self.portfolio_risk_manager = PortfolioRiskManager()
        self.price_monitor = PriceAlertMonitor(self.event_queue)
        self.volume_monitor = VolumeMonitor(self.event_queue)
        
        # PHASE 4: MARKET HOURS & SYMBOL DISCOVERY
        self.symbol_discovery = SymbolDiscoveryEngine(self.alpaca, self.intelligence_engine)
        self.market_hours_manager = MarketHoursManager(self)
        
        # Initialize event-driven position manager (LEGACY - will be replaced)
        self.position_manager = PositionManager(
            alpaca_client=self.alpaca,
            llm_bridge=self.llm_bridge,
            trading_agent=self,
            max_positions=10,
            poll_interval=15  # Check prices every 15 seconds
        )
        
        # State tracking
        self.decisions: List[TradingDecision] = []
        self.positions: Dict[str, Any] = {}
        self.position_entry_times: Dict[str, datetime] = {}  # Track when we entered each position
        self.account_value: float = 0
        self.current_pnl: float = 0
        self.active_decision_ids: Dict[str, str] = {}  # symbol -> decision_id for tracking outcomes
        self.daily_start_value: float = 0  # Track starting value for daily loss limit
        self.daily_trade_count: int = 0  # Track number of trades today
        self.daily_traded_value: float = 0  # Track total value traded for turnover calc
        self.last_reset_date: Optional[datetime] = None  # Track when we last reset daily metrics
        
        # Learning insights cache (generated once per day)
        self.daily_learning_insights: Optional[Dict[str, Any]] = None
        self.learning_insights_date: Optional[datetime] = None
        
        # Configuration
        self.min_confidence = settings.trading.min_confidence
        self.lookback_days = 90  # Historical data for indicators
        
        # LEGACY CONSTRAINTS (DEPRECATED - now handled by event-driven architecture)
        # These arbitrary limits are replaced by:
        # - Strategy-specific rules stored in DecisionMemory
        # - Event-driven re-evaluation triggers
        # - Kelly Criterion position sizing
        # - Emergency portfolio stops only (20/40/60 via PortfolioRiskManager)
        # BUT keep these as final safety backstops:
        self.MAX_DAILY_TRADES = 20
        self.MAX_DAILY_LOSS_PCT = 0.01
        self.MAX_TURNOVER_RATIO = 3.0
        self.MIN_EXPECTED_PROFIT = 50.0
        # self.MIN_HOLD_PERIOD = timedelta(hours=2)
        
        # Logging
        self.setup_logging()
        
        logger.info(f"Trading Agent initialized")
        logger.info(f"  Symbols: {', '.join(symbols)}")
        logger.info(f"  Dry run: {dry_run}")
        logger.info(f"  Min confidence: {self.min_confidence}%")
        
        # Run startup tasks (backfill strategies, load historical data)
        try:
            startup_results = run_startup_tasks(
                strategy_calculator=self.strategy_calculator,
                risk_manager=self.risk_manager
            )
            self.startup_results = startup_results
        except Exception as e:
            logger.error(f"⚠️  Startup tasks failed (continuing anyway): {e}")
            self.startup_results = {'error': str(e)}
    
    def setup_logging(self) -> None:
        """Setup decision logging to file for audit trail and analysis."""
        log_dir = settings.project_root / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # Add file handler for decisions
        decision_log = log_dir / "decisions.jsonl"
        logger.add(
            decision_log,
            format="{message}",
            level="INFO",
            filter=lambda record: "DECISION" in record["extra"]
        )
    
    def reset_daily_metrics(self) -> None:
        """Reset daily tracking metrics at start of new trading day."""
        today = datetime.now().date()
        
        if self.last_reset_date != today:
            logger.info(f"🔄 Resetting daily metrics for {today}")
            self.daily_start_value = self.account_value
            self.daily_trade_count = 0
            self.daily_traded_value = 0
            self.last_reset_date = today
            
            # Generate morning insights for new day
            self._generate_morning_insights()
    
    def _generate_morning_insights(self):
        """Generate learning insights for the trading day (cached)"""
        try:
            today = datetime.now().date()
            
            # Only generate once per day
            if self.learning_insights_date == today and self.daily_learning_insights:
                logger.debug("Using cached morning insights")
                return
            
            logger.info("🌅 Generating morning learning insights...")
            self.daily_learning_insights = self.learning_engine.generate_morning_insights()
            self.learning_insights_date = today
            
            # Log summary
            insights = self.daily_learning_insights
            if insights.get('yesterday'):
                yesterday = insights['yesterday']
                logger.info(f"   Yesterday: {yesterday.get('total_trades', 0)} trades, "
                          f"{yesterday.get('win_rate', 0):.1%} win rate, "
                          f"${yesterday.get('total_pnl', 0):+.2f} P&L")
            
            pattern_count = len(insights.get('patterns', []))
            if pattern_count > 0:
                logger.info(f"   Discovered {pattern_count} profitable patterns")
            
            focus_count = len(insights.get('focus_areas', []))
            if focus_count > 0:
                logger.info(f"   {focus_count} focus areas for today")
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to generate morning insights: {e}")
            self.daily_learning_insights = None
    
    def get_learning_insights(self) -> Optional[Dict[str, Any]]:
        """
        Get learning insights for LLM context.
        
        Returns:
            Learning insights dict or None if not available
        """
        # Ensure insights are generated for today
        today = datetime.now().date()
        if self.learning_insights_date != today:
            self._generate_morning_insights()
        
        return self.daily_learning_insights
    
    def calculate_transaction_costs(self, shares: int, price: float) -> float:
        """
        Calculate estimated transaction costs for a trade.
        
        Includes:
        - Commission: $2 per trade
        - Slippage: $0.03 per share (market orders often get filled worse than mid-price)
        - Bid-ask spread: $0.02 per share
        
        Args:
            shares: Number of shares
            price: Price per share
            
        Returns:
            Total estimated cost ($)
        """
        commission = 2.0
        slippage = shares * 0.03
        spread = shares * 0.02
        
        total_cost = commission + slippage + spread
        
        logger.debug(f"Transaction costs for {shares} shares: Commission=${commission:.2f} + Slippage=${slippage:.2f} + Spread=${spread:.2f} = ${total_cost:.2f}")
        
        return total_cost
    
    def can_sell_position(self, symbol: str) -> tuple[bool, str]:
        """
        Check if we can sell a position based on hold period constraints.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            (can_sell, reason) tuple
        """
        if symbol not in self.position_entry_times:
            return True, "No entry time tracked (legacy position)"
        
        entry_time = self.position_entry_times[symbol]
        time_held = datetime.now() - entry_time
        
        if time_held < self.MIN_HOLD_PERIOD:
            remaining = self.MIN_HOLD_PERIOD - time_held
            remaining_minutes = int(remaining.total_seconds() / 60)
            return False, f"Position held only {int(time_held.total_seconds()/60)} minutes, need {remaining_minutes} more minutes (min hold: {self.MIN_HOLD_PERIOD.total_seconds()/3600:.1f} hours)"
        
        return True, f"Position held for {int(time_held.total_seconds()/3600):.1f} hours, OK to sell"
    
    def check_daily_limits(self) -> tuple[bool, str]:
        """
        Check if we've hit any daily trading limits.
        
        Returns:
            (can_trade, reason) tuple
        """
        self.reset_daily_metrics()
        
        # Check daily trade count
        if self.daily_trade_count >= self.MAX_DAILY_TRADES:
            return False, f"Daily trade limit reached ({self.daily_trade_count}/{self.MAX_DAILY_TRADES})"
        
        # Check daily loss limit
        if self.daily_start_value > 0:
            daily_pnl = self.account_value - self.daily_start_value
            daily_loss_pct = abs(daily_pnl / self.daily_start_value)
            
            if daily_pnl < 0 and daily_loss_pct > self.MAX_DAILY_LOSS_PCT:
                return False, f"Daily loss limit exceeded ({daily_loss_pct*100:.2f}% > {self.MAX_DAILY_LOSS_PCT*100:.1f}%)"
        
        # Check turnover ratio
        if self.account_value > 0:
            turnover_ratio = self.daily_traded_value / self.account_value
            
            if turnover_ratio > self.MAX_TURNOVER_RATIO:
                return False, f"Daily turnover limit exceeded ({turnover_ratio:.1f}x > {self.MAX_TURNOVER_RATIO:.1f}x)"
        
        return True, "All daily limits OK"

    
    def update_account_state(self) -> None:
        """Update account value, positions, and P&L for risk monitoring."""
        try:
            account = self.alpaca.get_account()
            self.account_value = float(account['equity'])
            
            # Get current positions
            positions = self.alpaca.get_positions()
            self.positions = {pos['symbol']: pos for pos in positions}
            
            # Calculate today's P&L (simplified - would need to track opening value)
            self.current_pnl = float(account['equity']) - 100000  # Starting capital
            
            logger.debug(f"Account updated: ${self.account_value:,.2f}, {len(self.positions)} positions")
            
        except Exception as e:
            logger.error(f"Failed to update account state: {e}")
    
    def get_market_data(self, symbol: str) -> Optional[Any]:
        """
        Fetch market data for a symbol.
        
        Args:
            symbol: Stock ticker
        
        Returns:
            DataFrame with OHLCV data, or None if error
        """
        try:
            # For basic subscription, use data that's definitely outside real-time restrictions
            end_date = datetime.now() - timedelta(days=1)  # Yesterday's data (should always be available)
            start_date = end_date - timedelta(days=self.lookback_days)
            
            bars = self.alpaca.get_bars(
                symbol=symbol,
                timeframe='1Day',
                start=start_date,
                end=end_date,
                limit=self.lookback_days
            )
            
            if bars is None or len(bars) == 0:
                logger.warning(f"No market data for {symbol}")
                return None
            
            logger.debug(f"Retrieved {len(bars)} bars for {symbol}")
            return bars
            
        except Exception as e:
            logger.error(f"Failed to get market data for {symbol}: {e}")
            return None
    
    def get_news(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Fetch recent news for a symbol.
        
        Args:
            symbol: Stock ticker
        
        Returns:
            List of news articles
        """
        try:
            news = self.alpaca.get_news(symbol, limit=3)
            logger.debug(f"Retrieved {len(news)} news articles for {symbol}")
            return news
        except Exception as e:
            logger.warning(f"Failed to get news for {symbol}: {e}")
            return []
    
    def analyze_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Complete analysis pipeline for a symbol.
        
        1. Get market data
        2. Calculate indicators
        3. Get LLM analysis
        4. Combine results
        
        Args:
            symbol: Stock ticker
        
        Returns:
            Analysis dict with indicators and LLM sentiment
        """
        logger.info(f"Analyzing {symbol}...")
        
        # NEW: Skip if position is managed by PositionManager (event-driven exits)
        if symbol in self.position_manager.positions:
            logger.debug(f"⏭️  Skipping {symbol}: managed by PositionManager")
            return None
        
        # Step 1: Get market data
        bars = self.get_market_data(symbol)
        if bars is None:
            return None
        
        # Step 2: Calculate indicators
        df_with_indicators = analyze_dataframe(bars)
        signals = get_latest_signals(df_with_indicators)
        
        if not signals:
            logger.warning(f"No signals for {symbol}")
            return None
        
        # Step 3: Get news
        news = self.get_news(symbol)
        
        # Step 4: Get current position (if any)
        current_position = None
        if symbol in self.positions:
            pos = self.positions[symbol]
            current_position = {
                'qty': float(pos['qty']),
                'avg_entry_price': float(pos['avg_entry_price']),
                'current_price': float(pos.get('current_price', signals['price']['close']))
            }
        
        # Step 5: Get learning insights (NEW - closes feedback loop!)
        learning_insights = self.get_learning_insights()
        
        # Step 6: LLM analysis with learning context
        # EVENT-DRIVEN: Use thesis vs reality for position re-evaluation
        if current_position and symbol in [m.symbol for m in self.memory_store.get_all_open_positions()]:
            # We have an open position with stored memory - use thesis vs reality
            llm_analysis = self._analyze_with_thesis_vs_reality(
                symbol=symbol,
                signals=signals,
                news=news,
                current_position=current_position,
                learning_insights=learning_insights
            )
        elif current_position:
            # Analyzing existing position (no thesis stored yet)
            account = self.alpaca.get_account()
            portfolio_data = {
                'total_value': float(account['equity']),
                'buying_power': float(account['buying_power']),
                'positions_count': len(self.positions),
                'daily_pnl': self.current_pnl
            }
            llm_analysis = self.llm_bridge.analyze_position(
                symbol=symbol,
                technical_data=signals,
                position_data=current_position,
                portfolio_data=portfolio_data,
                news=news,
                learning_insights=learning_insights
            )
        else:
            # New opportunity
            llm_analysis = self.llm_bridge.analyze_new_opportunity(
                symbol=symbol,
                technical_data=signals,
                news=news,
                learning_insights=learning_insights
            )
        
        # If LLM fails, use fallback
        if not llm_analysis:
            logger.warning(f"LLM analysis failed for {symbol}, using fallback")
            llm_analysis = self.llm_bridge.get_fallback_analysis(signals)
        
        return {
            'symbol': symbol,
            'signals': signals,
            'llm_analysis': llm_analysis,
            'news': news,
            'current_position': current_position
        }
    
    def _analyze_with_thesis_vs_reality(
        self,
        symbol: str,
        signals: Dict[str, Any],
        news: List[Dict[str, Any]],
        current_position: Dict[str, Any],
        learning_insights: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Re-evaluate position using thesis vs reality comparison.
        
        EVENT-DRIVEN: Shows LLM what it originally thought vs what actually happened.
        This enables self-correction and learning from thesis invalidation.
        
        Args:
            symbol: Stock ticker
            signals: Technical indicators
            news: Recent news
            current_position: Current position details
            learning_insights: Historical learning data
        
        Returns:
            LLM analysis dict with action, confidence, reasoning
        """
        try:
            # Get current price
            current_price = signals['price']['close']
            
            # Build current market data
            current_data = {
                'price': current_price,
                'signals': signals,
                'news': news,
                'position': current_position,
                'learning_insights': learning_insights
            }
            
            # Get thesis vs reality comparison
            comparison = self.comparator.get_comparison(
                symbol=symbol,
                current_price=current_price,
                current_data=current_data
            )
            
            if not comparison:
                logger.warning(f"⚠️ No memory found for {symbol}, falling back to standard analysis")
                # Has position but no memory - use analyze_position
                account = self.alpaca.get_account()
                portfolio_data = {
                    'total_value': float(account['equity']),
                    'buying_power': float(account['buying_power']),
                    'positions_count': len(self.positions),
                    'daily_pnl': self.current_pnl
                }
                return self.llm_bridge.analyze_position(
                    symbol=symbol,
                    technical_data=signals,
                    position_data=current_position,
                    portfolio_data=portfolio_data,
                    news=news,
                    learning_insights=learning_insights
                )
            
            # Build enhanced prompt with thesis vs reality
            prompt = self.comparator.build_reeval_prompt(
                symbol=symbol,
                current_price=current_price,
                current_data=current_data,
                trigger_event="Scheduled re-evaluation cycle"
            )
            
            logger.info(f"🔄 Re-evaluating {symbol} with thesis vs reality context")
            logger.debug(f"   Original entry: ${comparison['original_thesis']['entry_price']:.2f}")
            logger.debug(f"   Current price: ${current_price:.2f}")
            logger.debug(f"   P&L: {comparison['position_details']['unrealized_pnl_pct']:+.2f}%")
            logger.debug(f"   Original thesis: {comparison['original_thesis']['thesis_narrative'][:80]}...")
            
            # Send enhanced prompt to LLM with thesis vs reality context
            account = self.alpaca.get_account()
            portfolio_data = {
                'total_value': float(account['equity']),
                'buying_power': float(account['buying_power']),
                'positions_count': len(self.positions),
                'daily_pnl': self.current_pnl
            }
            
            llm_response = self.llm_bridge.analyze_position(
                symbol=symbol,
                technical_data=signals,
                position_data=current_position,
                portfolio_data=portfolio_data,
                news=news,
                learning_insights={
                    'thesis_vs_reality': comparison,
                    'reeval_prompt': prompt
                }
            )
            
            # Store revisit in memory
            if llm_response and llm_response.get('action'):
                self.memory_store.add_revisit(
                    symbol=symbol,
                    revisit_data={
                        'timestamp': datetime.now().isoformat(),
                        'price': current_price,
                        'action': llm_response['action'],
                        'confidence': llm_response.get('confidence', 0),
                        'reasoning': llm_response.get('reasoning', ''),
                        'thesis_still_valid': llm_response.get('thesis_still_valid', True),
                        'comparison_context': {
                            'entry_price': comparison['original_thesis']['entry_price'],
                            'pnl_pct': comparison['position_details']['unrealized_pnl_pct'],
                            'target_progress': (current_price - comparison['original_thesis']['entry_price']) / 
                                             (comparison['original_thesis']['target_price'] - comparison['original_thesis']['entry_price']) * 100
                        }
                    }
                )
                logger.debug(f"💾 Revisit stored for {symbol}: {llm_response['action']}")
            
            return llm_response
            
        except Exception as e:
            logger.error(f"❌ Thesis vs reality analysis failed for {symbol}: {e}")
            logger.warning(f"   Falling back to standard analysis")
            
            # Fallback to standard analysis
            account = self.alpaca.get_account()
            portfolio_data = {
                'total_value': float(account['equity']),
                'buying_power': float(account['buying_power']),
                'positions_count': len(self.positions),
                'daily_pnl': self.current_pnl
            }
            return self.llm_bridge.analyze_position(
                symbol=symbol,
                technical_data=signals,
                position_data=current_position,
                portfolio_data=portfolio_data,
                news=news,
                learning_insights=learning_insights
            )
    
    def make_decision(self, analysis: Dict[str, Any]) -> TradingDecision:
        """
        Make trading decision based on analysis.
        
        Args:
            analysis: Combined analysis from analyze_symbol()
        
        Returns:
            TradingDecision with action and reasoning
        """
        symbol = analysis['symbol']
        llm = analysis['llm_analysis']
        signals = analysis['signals']
        current_position = analysis['current_position']
        
        # NEW: Calculate what pure math strategies would recommend (CONTROL GROUP)
        historical_performance = self._get_historical_performance(symbol)
        calculated_strategies = self.strategy_calculator.calculate_all_strategies(
            symbol=symbol,
            signals=signals,
            current_position=current_position,
            account_value=self.account_value,
            historical_performance=historical_performance
        )
        
        # Also get consensus recommendation
        consensus = self.strategy_calculator.get_consensus_recommendation(calculated_strategies)
        calculated_strategies['consensus'] = consensus
        
        logger.info(f"📊 {symbol} Calculated Strategies:")
        for strat_name, strat_data in calculated_strategies.items():
            action_emoji = "🟢" if strat_data['action'] == 'buy' else "🔴" if strat_data['action'] == 'sell' else "⚪"
            logger.info(f"  {action_emoji} {strat_name}: {strat_data['action'].upper()} "
                       f"({strat_data['confidence']}%) - {strat_data['reasoning'][:60]}...")
        
        # Extract LLM recommendation
        action = llm.get('action', 'hold')
        confidence = llm.get('confidence', 0)
        sentiment = llm.get('sentiment', 'neutral')
        reasoning = llm.get('reasoning', 'No reasoning provided')
        
        # Get current price
        price = signals['price']['close']
        
        # Determine shares to trade (EVENT-DRIVEN: uses Kelly+LLM sizing)
        strategy = llm.get('strategy', 'unknown')
        shares = self._calculate_position_size(
            symbol=symbol,
            price=price,
            action=action,
            strategy=strategy,
            llm_conviction=confidence
        )
        
        # Create decision
        decision = TradingDecision(
            timestamp=datetime.now().isoformat(),
            symbol=symbol,
            action=action,
            shares=shares,
            price=price,
            confidence=confidence,
            sentiment=sentiment,
            reasoning=reasoning,
            risk_approved=False,
            risk_reason="Not yet validated",
            executed=False,
            indicators=signals,
            llm_analysis=llm,
            calculated_strategies=calculated_strategies,  # NEW: Pure math baselines for comparison
            account_value=self.account_value,
            current_pnl=self.current_pnl
        )
        
        # Check confidence threshold
        if confidence < self.min_confidence:
            decision.risk_approved = False
            decision.risk_reason = f"Confidence {confidence}% below minimum {self.min_confidence}%"
            logger.info(f"❌ {symbol}: Low confidence ({confidence}% < {self.min_confidence}%)")
            return decision
        
        # Don't trade if action is "hold"
        if action == 'hold':
            decision.risk_approved = True
            decision.risk_reason = "Hold recommended, no action needed"
            logger.info(f"⏸️  {symbol}: HOLD - {reasoning}")
            return decision
        
        # NEW: Validate action against position state (prevent LLM hallucinations)
        if action == 'sell' and not current_position:
            decision.risk_approved = False
            decision.risk_reason = "Cannot SELL - no position exists (possible LLM error)"
            logger.warning(f"❌ {symbol}: LLM recommended SELL but no position exists! Rejecting trade.")
            return decision
        
        if action == 'buy' and current_position:
            # We could allow adding to positions, but current strategy doesn't support it
            logger.info(f"ℹ️  {symbol}: LLM recommended BUY but position already exists. Converting to HOLD.")
            decision.action = 'hold'
            decision.risk_approved = True
            decision.risk_reason = "Position already exists, maintaining current holding"
            return decision
        
        # NEW: Check daily trading limits before proceeding
        can_trade, limit_reason = self.check_daily_limits()
        if not can_trade:
            decision.risk_approved = False
            decision.risk_reason = f"Daily limit reached: {limit_reason}"
            logger.warning(f"❌ {symbol}: {limit_reason}")
            return decision
        
        # NEW: Check minimum hold period for SELL actions
        if action == 'sell':
            can_sell, hold_reason = self.can_sell_position(symbol)
            if not can_sell:
                decision.risk_approved = False
                decision.risk_reason = f"Minimum hold period not met: {hold_reason}"
                logger.warning(f"❌ {symbol}: {hold_reason}")
                return decision
        
        # NEW: Calculate transaction costs and check profitability
        est_costs = self.calculate_transaction_costs(shares, price)
        trade_value = shares * price
        
        # For BUY: Only proceed if we expect profit > costs (use MIN_EXPECTED_PROFIT threshold)
        if action == 'buy':
            min_profit_needed = est_costs * 3  # Need 3x costs to justify trade
            if min_profit_needed > self.MIN_EXPECTED_PROFIT:
                decision.risk_approved = False
                decision.risk_reason = f"Expected profit too low. Est costs: ${est_costs:.2f}, min profit: ${min_profit_needed:.2f}"
                logger.warning(f"❌ {symbol}: Trade costs (${est_costs:.2f}) too high relative to expected profit")
                return decision
        
        # For SELL: Log the transaction costs but allow (we're closing position)
        if action == 'sell':
            logger.info(f"💰 {symbol}: Estimated transaction costs: ${est_costs:.2f}")
            current_pnl_est = (price - current_position['avg_entry_price']) * shares - est_costs if current_position else 0
            logger.info(f"💰 {symbol}: Estimated P&L after costs: ${current_pnl_est:.2f}")
            logger.info(f"💰 {symbol}: Estimated transaction costs: ${est_costs:.2f}")
            current_pnl_est = (price - current_position['avg_entry_price']) * shares - est_costs if current_position else 0
            logger.info(f"💰 {symbol}: Estimated P&L after costs: ${current_pnl_est:.2f}")
        
        # Validate with risk manager
        risk_result = self.risk_manager.validate_trade(
            symbol=symbol,
            action=action,
            shares=shares,
            price=price,
            account_value=self.account_value,
            current_pnl=self.current_pnl,
            positions=list(self.positions.values())
        )
        
        decision.risk_approved = risk_result.approved
        decision.risk_reason = risk_result.reason
        
        if not risk_result.approved:
            logger.warning(f"❌ {symbol}: Risk check failed - {risk_result.reason}")
        else:
            logger.info(f"✅ {symbol}: {action.upper()} {shares} shares @ ${price:.2f} (confidence: {confidence}%, est costs: ${est_costs:.2f})")
        
        # NEW: Record decision in learning engine (for learning and pattern discovery)
        try:
            if action != 'hold' and decision.risk_approved:
                decision_id = self.learning_engine.record_decision(
                    symbol=symbol,
                    action=action,
                    price=price,
                    shares=shares,
                    technical_indicators=signals,
                    llm_analysis=llm,
                    decision_confidence=confidence / 100.0,  # Convert to 0-1
                    decision_reasoning=reasoning,
                    pattern_matched=None  # Will be set if pattern matching is added
                )
                # Track this decision ID for outcome recording later
                self.active_decision_ids[symbol] = decision_id
                logger.debug(f"💾 Decision recorded in learning engine: {decision_id}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to record decision in learning engine: {e}")
        
        return decision
    
    
    def _get_historical_performance(self, symbol: str) -> Dict[str, Any]:
        """
        Get historical performance metrics for a symbol.
        
        Used by strategy calculator for Kelly Criterion and other math-based strategies.
        
        Args:
            symbol: Stock ticker
        
        Returns:
            Dict with win_rate, avg_win, avg_loss
        """
        # Try to get from learning engine if available
        if hasattr(self, 'learning_engine') and self.learning_engine:
            try:
                stats = self.learning_engine.get_symbol_stats(symbol)
                if stats:
                    return {
                        'win_rate': stats.get('win_rate', 0.55),
                        'avg_win': stats.get('avg_win', 500),
                        'avg_loss': stats.get('avg_loss', 300)
                    }
            except Exception as e:
                logger.debug(f"Could not get learning engine stats for {symbol}: {e}")
        
        # Fallback: Use conservative defaults
        return {
            'win_rate': 0.55,  # 55% win rate
            'avg_win': 500,    # $500 average win
            'avg_loss': 300    # $300 average loss
        }
    
    def _calculate_position_size(
        self, 
        symbol: str, 
        price: float, 
        action: str, 
        strategy: str = "unknown",
        llm_conviction: int = 50
    ) -> int:
        """
        Calculate position size using Kelly Criterion + LLM conviction.
        
        EVENT-DRIVEN ARCHITECTURE: Uses KellyLLMPositionSizer for mathematical backing.
        
        Args:
            symbol: Stock ticker
            price: Current price
            action: "buy" or "sell"
            strategy: Trading strategy name (e.g., "momentum_breakout")
            llm_conviction: LLM conviction score (0-100)
        
        Returns:
            Number of shares
        """
        if action == 'hold':
            return 0
        
        if action == 'sell':
            # Sell entire position
            if symbol in self.positions:
                return abs(int(float(self.positions[symbol]['qty'])))
            return 0
        
        # EVENT-DRIVEN: Use Kelly+LLM position sizer
        try:
            # Build existing positions list with sector info
            # Quick sector mapping (proper solution: get from API)
            SECTOR_MAP = {
                # Technology
                'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology', 'GOOG': 'Technology',
                'NVDA': 'Technology', 'AMD': 'Technology', 'INTC': 'Technology', 'AVGO': 'Technology',
                'QCOM': 'Technology', 'TXN': 'Technology', 'AMAT': 'Technology', 'MU': 'Technology',
                'ADBE': 'Technology', 'CRM': 'Technology', 'NOW': 'Technology', 'ORCL': 'Technology',
                'CSCO': 'Technology', 'PANW': 'Technology', 'INTU': 'Technology', 'SNPS': 'Technology',
                'CDNS': 'Technology',
                # Communication
                'META': 'Communication', 'GOOGL': 'Communication', 'GOOG': 'Communication',
                # Consumer Cyclical
                'AMZN': 'Consumer Cyclical', 'TSLA': 'Consumer Cyclical',
                # Financial
                'JPM': 'Financial', 'BAC': 'Financial', 'WFC': 'Financial', 'GS': 'Financial',
                'MS': 'Financial', 'C': 'Financial', 'BX': 'Financial', 'SCHW': 'Financial',
                'AXP': 'Financial', 'USB': 'Financial', 'PNC': 'Financial', 'TFC': 'Financial',
                'COF': 'Financial', 'BLK': 'Financial', 'SPGI': 'Financial', 'CME': 'Financial',
                'ICE': 'Financial',
                # Healthcare
                'JNJ': 'Healthcare', 'UNH': 'Healthcare', 'LLY': 'Healthcare', 'ABBV': 'Healthcare',
                'MRK': 'Healthcare', 'PFE': 'Healthcare', 'TMO': 'Healthcare', 'ABT': 'Healthcare',
                'DHR': 'Healthcare',
            }
            
            existing_positions = []
            sector_map = {}
            
            for sym, pos in self.positions.items():
                pos_value = float(pos['qty']) * float(pos.get('current_price', price))
                sector = SECTOR_MAP.get(sym, 'Other')
                existing_positions.append({
                    'symbol': sym,
                    'value': pos_value,
                    'sector': sector
                })
                sector_map[sym] = sector
            
            # Get sector for new symbol
            sector_map[symbol] = SECTOR_MAP.get(symbol, 'Other')
            
            # Calculate position using Kelly+LLM
            position_result = self.kelly_sizer.calculate_position_size(
                symbol=symbol,
                entry_price=price,
                strategy=strategy,
                llm_conviction=llm_conviction,
                portfolio_value=self.account_value,
                existing_positions=existing_positions,
                sector_map=sector_map
            )
            
            if position_result:
                logger.info(f"📊 Kelly+LLM Sizing for {symbol}:")
                logger.info(f"   Kelly Fraction: {position_result.kelly_fraction:.2%}")
                logger.info(f"   Conviction Adjusted: {position_result.conviction_adjusted_kelly:.2%}")
                logger.info(f"   Final Position: ${position_result.final_position_usd:,.0f} ({position_result.final_position_pct:.2f}%)")
                logger.info(f"   Shares: {position_result.shares}")
                logger.debug(f"   Reasoning: {position_result.reasoning}")
                
                return position_result.shares
            else:
                logger.warning(f"⚠️ Kelly sizing failed, using fallback")
                
        except Exception as e:
            logger.error(f"❌ Error calculating Kelly position size: {e}")
        
        # FALLBACK: Use simple max position size
        max_position_value = self.account_value * settings.risk.max_position_size
        shares = int(max_position_value / price)
        
        # Ensure at least 1 share if we have enough capital
        if shares == 0 and self.account_value >= price:
            shares = 1
        
        logger.debug(f"Using fallback sizing: {shares} shares (${shares * price:,.0f})")
        return shares
    
    def execute_decision(self, decision: TradingDecision):
        """
        Execute a trading decision (place order).
        
        Args:
            decision: TradingDecision to execute
        """
        if not decision.risk_approved:
            logger.debug(f"Skipping execution - not approved: {decision.risk_reason}")
            return
        
        # Skip execution if shares is 0 (e.g., trying to sell non-existent position)
        if decision.shares == 0:
            logger.debug(f"Skipping execution for {decision.symbol} - 0 shares (likely no position to sell)")
            return
        
        if decision.action == 'hold':
            logger.debug("No execution needed for HOLD action")
            return
        
        if self.dry_run:
            logger.info(f"🔷 DRY RUN: Would {decision.action.upper()} {decision.shares} {decision.symbol} @ ${decision.price:.2f}")
            decision.executed = True
            self.risk_manager.record_trade(decision.symbol, decision.action, decision.shares, decision.price)
            return
        
        # ACTUAL ORDER EXECUTION
        try:
            logger.info(f"🔥 EXECUTING: {decision.action.upper()} {decision.shares} {decision.symbol}")
            
            # Place market order
            order = self.alpaca.place_market_order(
                symbol=decision.symbol,
                qty=decision.shares,
                side=decision.action  # 'buy' or 'sell'
            )
            
            if not order:
                decision.executed = False
                decision.execution_error = "Order placement failed (API error)"
                logger.error(f"❌ Order placement failed for {decision.symbol}")
                return
            
            # Log order details
            logger.info(f"📋 Order ID: {order['id']}")
            logger.info(f"📋 Status: {order['status']}")
            
            # Wait for fill (with timeout)
            logger.info(f"⏳ Waiting for order to fill...")
            final_order = self.alpaca.wait_for_order_fill(
                order_id=order['id'],
                timeout_seconds=30
            )
            
            if final_order and final_order['status'] == 'filled':
                decision.executed = True
                filled_price = final_order['filled_avg_price']
                decision.price = filled_price  # Update with actual fill price
                logger.info(f"✅ Order filled @ ${filled_price:.2f}")
                
                # Record trade for risk tracking
                self.risk_manager.record_trade(
                    decision.symbol,
                    decision.action,
                    decision.shares,
                    filled_price
                )
                
                # EVENT-DRIVEN: Store DecisionMemory for thesis vs reality tracking
                if decision.llm_analysis:
                    decision_id = self._store_decision_memory(
                        symbol=decision.symbol,
                        decision=decision,
                        llm_analysis=decision.llm_analysis,
                        filled_price=filled_price
                    )
                    if decision_id:
                        self.active_decision_ids[decision.symbol] = decision_id
                
                # NEW: Track entry time for position holds
                if decision.action == 'buy':
                    self.position_entry_times[decision.symbol] = datetime.now()
                    logger.debug(f"📍 Recorded entry time for {decision.symbol}")
                    
                    # EVENT-DRIVEN: Set price alerts for target and stop loss
                    if decision.llm_analysis:
                        target_price = decision.llm_analysis.get('target_price', filled_price * 1.05)
                        stop_loss = decision.llm_analysis.get('stop_loss', filled_price * 0.95)
                        
                        try:
                            # Set target alert
                            self.price_monitor.set_price_alert(
                                symbol=decision.symbol,
                                alert_type="above",
                                price=target_price,
                                event_type=EventType.TARGET_HIT,
                                priority=EventPriority.MEDIUM_HIGH,
                                metadata={'level': 'first_target', 'entry_price': filled_price}
                            )
                            
                            # Set stop loss alert
                            self.price_monitor.set_price_alert(
                                symbol=decision.symbol,
                                alert_type="below",
                                price=stop_loss,
                                event_type=EventType.STOP_LOSS_HIT,
                                priority=EventPriority.CRITICAL,
                                metadata={'stop_type': 'invalidation', 'entry_price': filled_price}
                            )
                            
                            logger.info(f"🔔 Price alerts set: Target=${target_price:.2f}, Stop=${stop_loss:.2f}")
                        except Exception as e:
                            logger.error(f"❌ Failed to set price alerts: {e}")
                    
                    # NEW: Hand position to PositionManager for event-driven monitoring (LEGACY)
                    try:
                        analysis = {
                            'signals': decision.indicators,
                            'llm_analysis': decision.llm_analysis,
                        }
                        self.position_manager.add_position(
                            symbol=decision.symbol,
                            entry_price=filled_price,
                            shares=decision.shares,
                            analysis=analysis
                        )
                        logger.info(f"✅ Position handed to PositionManager for monitoring")
                    except Exception as e:
                        logger.error(f"❌ Failed to add position to PositionManager: {e}")
                        
                elif decision.action == 'sell':
                    # Remove entry time when position is closed
                    if decision.symbol in self.position_entry_times:
                        entry_time = self.position_entry_times[decision.symbol]
                        hold_duration = datetime.now() - entry_time
                        logger.info(f"⏱️  {decision.symbol}: Held for {hold_duration}")
                        del self.position_entry_times[decision.symbol]
                
                # NEW: Update daily metrics
                self.daily_trade_count += 1
                self.daily_traded_value += decision.shares * final_order['filled_avg_price']
                logger.debug(f"📊 Daily metrics: {self.daily_trade_count} trades, ${self.daily_traded_value:,.2f} traded")
                
                # CRITICAL: Update positions immediately after trade execution
                # This ensures subsequent trades in the same cycle see accurate position data
                if decision.action == 'sell':
                    # Remove position after selling
                    if decision.symbol in self.positions:
                        del self.positions[decision.symbol]
                        logger.debug(f"Updated positions: removed {decision.symbol}")
                elif decision.action == 'buy':
                    # Refresh positions from API to get accurate new position
                    # (We could try to update locally, but API is source of truth)
                    try:
                        updated_positions = self.alpaca.get_positions()
                        self.positions = {pos['symbol']: pos for pos in updated_positions}
                        logger.debug(f"Updated positions: refreshed from API ({len(self.positions)} positions)")
                    except Exception as e:
                        logger.warning(f"Failed to refresh positions after buy: {e}")
                
                # Also update account value to reflect new equity after trade
                try:
                    account = self.alpaca.get_account()
                    self.account_value = float(account['equity'])
                    logger.debug(f"Updated account value: ${self.account_value:,.2f}")
                except Exception as e:
                    logger.warning(f"Failed to refresh account value: {e}")
            else:
                decision.executed = False
                status = final_order['status'] if final_order else 'unknown'
                decision.execution_error = f"Order not filled (status: {status})"
                logger.warning(f"⚠️  Order not filled: {status}")
            
        except Exception as e:
            logger.error(f"Failed to execute trade: {e}")
            decision.executed = False
            decision.execution_error = str(e)
    
    def record_trade_outcome(self, symbol: str):
        """
        Record the outcome of a trade when position is closed.
        
        This enables the learning engine to learn from actual results.
        
        Args:
            symbol: Symbol of closed position
        """
        try:
            # Check if we have a tracked decision for this symbol
            if symbol not in self.active_decision_ids:
                return
            
            decision_id = self.active_decision_ids[symbol]
            
            # Get historical decisions to find entry details
            recent_decisions = self.learning_engine.memory.get_recent_decisions(days=7, symbol=symbol)
            decision_row = recent_decisions[recent_decisions['id'] == decision_id]
            
            if decision_row.empty:
                logger.warning(f"⚠️ Could not find decision {decision_id} to record outcome")
                return
            
            entry_price = decision_row['price'].iloc[0]
            entry_action = decision_row['action'].iloc[0]
            
            # Get current price (exit price)
            bars = self.alpaca.get_bars(symbol, "1Day", limit=1)
            if bars.empty:
                logger.warning(f"⚠️ Could not get current price for {symbol}")
                return
            
            exit_price = bars['close'].iloc[-1]
            exit_time = datetime.now()
            
            # Calculate P&L
            if entry_action == 'buy':
                profit_loss = (exit_price - entry_price) * decision_row['shares'].iloc[0]
            else:  # sell
                profit_loss = (entry_price - exit_price) * decision_row['shares'].iloc[0]
            
            # Determine outcome
            if profit_loss > 5:
                outcome = "win"
            elif profit_loss < -5:
                outcome = "loss"
            else:
                outcome = "neutral"
            
            # Generate lesson
            if outcome == "win":
                lesson = f"Profitable trade on {symbol}: {entry_action} @ ${entry_price:.2f}, exit @ ${exit_price:.2f}"
            elif outcome == "loss":
                lesson = f"Loss on {symbol}: {entry_action} @ ${entry_price:.2f}, exit @ ${exit_price:.2f}. Review decision reasoning."
            else:
                lesson = None
            
            # Record outcome in learning engine
            self.learning_engine.record_outcome(
                decision_id=decision_id,
                outcome=outcome,
                profit_loss=profit_loss,
                exit_price=exit_price,
                exit_time=exit_time,
                lesson_learned=lesson
            )
            
            # Remove from active tracking
            del self.active_decision_ids[symbol]
            
            logger.info(f"📊 Trade outcome recorded: {symbol} {outcome} (${profit_loss:+.2f})")
            
        except Exception as e:
            logger.error(f"❌ Error recording trade outcome: {e}")
    
    def _store_decision_memory(
        self, 
        symbol: str, 
        decision: TradingDecision,
        llm_analysis: Dict[str, Any],
        filled_price: Optional[float] = None
    ) -> Optional[str]:
        """
        Store complete decision context in DecisionMemory for thesis vs reality comparison.
        
        This enables the system to show the LLM what it originally thought vs what actually happened.
        
        Args:
            symbol: Stock ticker
            decision: TradingDecision object with action details
            llm_analysis: Full LLM analysis dict (contains thesis, catalysts, etc.)
            filled_price: Actual fill price (use if different from decision.price)
        
        Returns:
            Decision ID if stored successfully, None otherwise
        """
        import uuid
        
        try:
            # Extract LLM analysis components
            thesis = llm_analysis.get('reasoning', 'No thesis provided')
            strategy = llm_analysis.get('strategy', 'unknown')
            
            # Parse catalysts
            catalysts_raw = llm_analysis.get('catalysts', [])
            if isinstance(catalysts_raw, str):
                catalysts = [c.strip() for c in catalysts_raw.split(',') if c.strip()]
            elif isinstance(catalysts_raw, list):
                catalysts = catalysts_raw
            else:
                catalysts = []
            
            # Parse bullish/bearish factors
            bullish = llm_analysis.get('bullish_factors', [])
            bearish = llm_analysis.get('bearish_factors', [])
            if isinstance(bullish, str):
                bullish = [b.strip() for b in bullish.split(',') if b.strip()]
            if isinstance(bearish, str):
                bearish = [b.strip() for b in bearish.split(',') if b.strip()]
            
            # Get target and stop levels
            target_price = llm_analysis.get('target_price', decision.price * 1.05)
            stop_loss_price = llm_analysis.get('stop_loss', decision.price * 0.95)
            
            # Expected holding period
            holding_period = llm_analysis.get('expected_holding_period', 'swing (2-5 days)')
            
            # Invalidation conditions
            invalidation_conditions = llm_analysis.get('invalidation_conditions', [
                f"Break below ${stop_loss_price:.2f}",
                "Volume dries up significantly",
                "Negative catalyst emerges"
            ])
            
            # Create DecisionMemory
            memory = DecisionMemory(
                decision_id=str(uuid.uuid4()),
                symbol=symbol,
                timestamp=datetime.now(),
                decision_type=DecisionType.ENTRY if decision.action == 'buy' else DecisionType.EXIT,
                
                # Strategy
                strategy=strategy,
                
                # Thesis
                thesis=thesis,
                catalysts=catalysts,
                bullish_factors=bullish,
                bearish_factors=bearish,
                
                # Risk management
                entry_price=filled_price or decision.price,
                target_price=target_price,
                stop_loss_price=stop_loss_price,
                expected_holding_period=holding_period,
                invalidation_conditions=invalidation_conditions,
                
                # Position details
                shares=decision.shares,
                position_size_usd=decision.shares * (filled_price or decision.price),
                position_size_pct=(decision.shares * (filled_price or decision.price)) / self.account_value * 100 if self.account_value > 0 else 0,
                conviction_score=int(decision.confidence),
                
                # Kelly sizing (if available)
                kelly_fraction=getattr(decision, 'kelly_fraction', 0.0),
                
                # Market conditions (as dict)
                market_conditions={
                    'market_regime': llm_analysis.get('market_regime', 'unknown'),
                    'sector_sentiment': llm_analysis.get('sector_sentiment', 'neutral'),
                    'rsi': decision.indicators.get('rsi') if decision.indicators else None,
                    'trend': decision.indicators.get('trend') if decision.indicators else None,
                    'volume_vs_avg': decision.indicators.get('volume_ratio') if decision.indicators else None,
                }
            )
            
            # Store in memory
            self.memory_store.store(memory)
            
            logger.info(f"💾 DecisionMemory stored: {symbol} {decision.action.upper()} @ ${filled_price or decision.price:.2f}")
            logger.debug(f"   Thesis: {thesis[:100]}...")
            logger.debug(f"   Catalysts: {', '.join(catalysts[:3])}")
            
            return memory.decision_id
            
        except Exception as e:
            logger.error(f"❌ Failed to store DecisionMemory: {e}")
            return None
    
    def _emergency_liquidate_all(self):
        """
        Emergency liquidation of all positions due to excessive losses.
        
        This bypasses normal LLM decision-making and sells everything immediately.
        Only called when daily loss limit is reached or nearly reached.
        """
        logger.error("🚨 INITIATING EMERGENCY LIQUIDATION")
        logger.error(f"   Current positions: {len(self.positions)}")
        
        if not self.positions:
            logger.info("   No positions to liquidate")
            return
        
        liquidated = 0
        failed = 0
        
        for symbol, position in list(self.positions.items()):
            try:
                qty = abs(int(float(position['qty'])))
                if qty == 0:
                    continue
                
                logger.error(f"   🔥 LIQUIDATING: {symbol} ({qty} shares)")
                
                # Place market sell order
                order = self.alpaca.place_market_order(
                    symbol=symbol,
                    qty=qty,
                    side='sell'
                )
                
                if order:
                    # Wait for fill
                    final_order = self.alpaca.wait_for_order_fill(
                        order_id=order['id'],
                        timeout_seconds=30
                    )
                    
                    if final_order and final_order['status'] == 'filled':
                        logger.error(f"   ✅ {symbol} liquidated @ ${final_order['filled_avg_price']:.2f}")
                        liquidated += 1
                        
                        # Update positions immediately
                        if symbol in self.positions:
                            del self.positions[symbol]
                    else:
                        logger.error(f"   ❌ {symbol} liquidation failed (order not filled)")
                        failed += 1
                else:
                    logger.error(f"   ❌ {symbol} liquidation failed (order placement failed)")
                    failed += 1
                    
            except Exception as e:
                logger.error(f"   ❌ Error liquidating {symbol}: {e}")
                failed += 1
        
        logger.error("="*60)
        logger.error(f"🚨 EMERGENCY LIQUIDATION COMPLETE")
        logger.error(f"   Liquidated: {liquidated} positions")
        logger.error(f"   Failed: {failed} positions")
        logger.error(f"   Trading halted for today")
        logger.error("="*60)
        
        # Update account state after liquidation
        self.update_account_state()
    
    def log_decision(self, decision: TradingDecision):
        """
        Log trading decision to both file and memory
        
        Args:
            decision: TradingDecision to log
        """
        # Add to in-memory list
        self.decisions.append(decision)
        
        # Convert to dict and handle numpy types
        decision_dict = asdict(decision)
        
        # Convert numpy types to Python types for JSON serialization
        def convert_numpy_types(obj):
            if hasattr(obj, 'item'):  # numpy scalar
                return obj.item()
            elif isinstance(obj, dict):
                return {k: convert_numpy_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(item) for item in obj]
            return obj
        
        decision_dict = convert_numpy_types(decision_dict)
        
        # Log to structured file
        logger.bind(DECISION=True).info(json.dumps(decision_dict))
    
    def run_cycle_batch(self):
        """
        MASTER STRATEGY: Run portfolio-optimized batch analysis cycle.
        
        Unlike sequential analysis, this evaluates ALL opportunities simultaneously
        and makes coordinated portfolio decisions (what pros do).
        
        1. Update account state
        2. Get ALL symbols data in parallel
        3. Batch LLM analysis (comparative ranking)
        4. Execute portfolio-optimized decisions
        5. Log comprehensive analysis
        """
        logger.info("="*60)
        logger.info(f"🎯 MASTER BATCH CYCLE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*60)
        
        # Update account state
        self.update_account_state()
        
        # Emergency checks
        liquidation_check = self.risk_manager.check_emergency_liquidation(
            current_pnl=self.current_pnl,
            account_value=self.account_value
        )
        
        if liquidation_check['liquidate']:
            logger.error("🚨 EMERGENCY LIQUIDATION - BATCH ANALYSIS ABORTED")
            self._emergency_liquidate_all()
            return
        
        # Market status check
        try:
            market_status = self.alpaca.get_market_status()
            if not market_status.get('is_open', False):
                logger.info("💤 Market closed - batch analysis skipped")
                return
        except Exception as e:
            logger.error(f"Market status check failed: {e}")
            return
        
        # STEP 1: Collect ALL opportunity data in parallel
        logger.info(f"📊 Collecting data for {len(self.symbols)} symbols...")
        
        opportunities = []
        current_positions = []
        
        for symbol in self.symbols:
            try:
                # Get market data and indicators
                bars = self.get_market_data(symbol)
                if bars is None:
                    continue
                
                df_with_indicators = analyze_dataframe(bars)
                signals = get_latest_signals(df_with_indicators)
                if not signals:
                    continue
                
                # Check if this is a current position or opportunity
                if symbol in self.positions:
                    pos = self.positions[symbol]
                    current_positions.append({
                        'symbol': symbol,
                        'signals': signals,
                        'entry_price': float(pos['avg_entry_price']),
                        'current_price': signals['price']['close'],
                        'size': float(pos['qty']),
                        'pnl_pct': ((signals['price']['close'] - float(pos['avg_entry_price'])) / float(pos['avg_entry_price']) * 100)
                    })
                else:
                    # This is a potential new opportunity
                    opportunities.append({
                        'symbol': symbol,
                        'signals': signals,
                        'composite_score': self._calculate_composite_score(signals),
                        'tier': self._determine_tier(symbol, signals)
                    })
                
            except Exception as e:
                logger.error(f"Data collection failed for {symbol}: {e}")
                continue
        
        logger.info(f"📈 Found {len(opportunities)} opportunities, {len(current_positions)} positions")
        
        if not opportunities and not current_positions:
            logger.warning("No data available for batch analysis")
            return
        
        # STEP 2: Batch LLM Analysis (THE MASTER MOVE)
        try:
            logger.info("🧠 Running BATCH portfolio analysis...")
            
            portfolio_analysis = self.llm_bridge.analyze_portfolio_batch(
                opportunities=opportunities,
                current_positions=current_positions
            )
            
            # STEP 3: Execute coordinated decisions based on portfolio analysis
            self._execute_portfolio_decisions(portfolio_analysis, opportunities, current_positions)
            
            # STEP 4: Log comprehensive batch analysis
            self._log_batch_analysis(portfolio_analysis, opportunities, current_positions)
            
        except Exception as e:
            logger.error(f"Batch analysis failed: {e}")
            logger.info("Falling back to sequential analysis...")
            self.run_cycle()  # Fallback to old method
            return
        
        logger.info("="*60)
        logger.info(f"🎯 BATCH CYCLE COMPLETE: {len(opportunities)+len(current_positions)} symbols analyzed")
        logger.info("="*60)

    def run_cycle(self):
        """
        Run one complete trading cycle for all symbols.
        
        1. Update account state
        2. For each symbol:
           - Analyze market
           - Make decision
           - Execute trade
           - Log decision
        """
        logger.info("="*60)
        logger.info(f"Starting trading cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*60)
        
        # Update account state
        self.update_account_state()
        
        # CRITICAL: Check for emergency liquidation before normal trading
        liquidation_check = self.risk_manager.check_emergency_liquidation(
            current_pnl=self.current_pnl,
            account_value=self.account_value
        )
        
        if liquidation_check['liquidate']:
            logger.error("="*60)
            logger.error(f"🚨 EMERGENCY LIQUIDATION IN PROGRESS")
            logger.error(f"   Reason: {liquidation_check['message']}")
            logger.error(f"   Loss: {liquidation_check['loss_pct']*100:.2f}%")
            logger.error("="*60)
            
            # Liquidate all positions immediately
            self._emergency_liquidate_all()
            return
        elif liquidation_check['severity'] == 'warning':
            logger.warning(f"⚠️ {liquidation_check['message']}")
        
        # Check market status with detailed information
        try:
            market_status = self.alpaca.get_market_status()
            
            if not market_status.get('is_open', False):
                logger.info("="*60)
                logger.info(f"{market_status.get('status_text', '🔴 CLOSED')}")
                logger.info(f"{market_status.get('status_message', 'Market is closed')}")
                logger.info(f"⏰ Regular trading hours: {market_status.get('trading_hours', '9:30 AM - 4:00 PM ET (Mon-Fri)')}")
                logger.info("💤 Trading agent will wait for market to open...")
                logger.info("="*60)
                return
            else:
                logger.debug(f"✅ Market status: {market_status.get('status_message', 'Market is open')}")
                
        except Exception as e:
            logger.error(f"Failed to check market status: {e}")
            logger.warning("⚠️ Proceeding with caution - market status unknown")
            return
        
        # Process each symbol
        for symbol in self.symbols:
            try:
                # Analyze
                analysis = self.analyze_symbol(symbol)
                if not analysis:
                    logger.warning(f"Skipping {symbol} - analysis failed")
                    continue
                
                # Decide
                decision = self.make_decision(analysis)
                
                # Execute
                self.execute_decision(decision)
                
                # Log
                self.log_decision(decision)
                
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                continue
        
        logger.info("="*60)
        logger.info(f"Cycle complete - Processed {len(self.symbols)} symbols")
        logger.info("="*60)
    
    def _calculate_composite_score(self, signals: Dict[str, Any]) -> float:
        """Calculate a composite score for ranking opportunities."""
        
        score = 0.0
        
        # Price momentum (30% weight)
        price = signals.get('price', {})
        if price:
            daily_return = price.get('daily_return', 0)
            score += daily_return * 0.3
        
        # RSI momentum (25% weight) 
        momentum = signals.get('momentum', {})
        if momentum:
            rsi = momentum.get('rsi', 50)
            # Normalize RSI: 0-30 → negative, 30-70 → neutral, 70-100 → positive
            rsi_score = (rsi - 50) / 50  # -1 to +1
            score += rsi_score * 0.25
        
        # Volume activity (20% weight)
        volume = signals.get('volume', {})
        if volume:
            vol_ratio = volume.get('volume_ratio', 1)
            # Logarithmic scaling for volume spikes
            import math
            vol_score = math.log10(max(vol_ratio, 0.1)) / 2  # Scale log10(10) = 0.5
            score += vol_score * 0.2
        
        # Trend alignment (25% weight)
        trend = signals.get('trend', {})
        price_data = signals.get('price', {})
        if trend and price_data:
            close = price_data.get('close', 0)
            sma_20 = trend.get('sma_20', close)
            sma_50 = trend.get('sma_50', close)
            
            trend_score = 0
            if close > sma_20 > sma_50:
                trend_score = 1  # Strong uptrend
            elif close > sma_20:
                trend_score = 0.5  # Moderate uptrend
            elif close < sma_20 < sma_50:
                trend_score = -1  # Strong downtrend
            else:
                trend_score = -0.5  # Moderate downtrend
            
            score += trend_score * 0.25
        
        return max(-1.0, min(1.0, score))  # Clamp between -1 and 1
    
    def _determine_tier(self, symbol: str, signals: Dict[str, Any]) -> str:
        """Determine which tier this symbol belongs to."""
        
        price = signals.get('price', {}).get('close', 0)
        
        # Simple tier classification
        if price > 100:
            return 'Tier1_HighInfo'
        elif len(symbol) <= 4 and price > 20:
            return 'Tier2_Momentum'
        elif price > 5:
            return 'Tier3_Emerging'
        else:
            return 'Tier5_Speculative'
    
    def _execute_portfolio_decisions(
        self, 
        portfolio_analysis: Dict[str, Any], 
        opportunities: List[Dict[str, Any]], 
        current_positions: List[Dict[str, Any]]
    ):
        """Execute the coordinated portfolio decisions from batch analysis."""
        
        try:
            analysis = portfolio_analysis.get('portfolio_analysis', {})
            
            # Execute BUY recommendations
            best_opportunities = analysis.get('best_opportunities', [])
            logger.info(f"🚀 Executing {len(best_opportunities)} BUY recommendations...")
            
            for opp in best_opportunities:
                symbol = opp.get('symbol')
                confidence = opp.get('confidence', 0)
                target_allocation = opp.get('target_allocation', 3)  # Default 3%
                
                if confidence >= 70:  # Minimum confidence threshold
                    # Create decision structure for execution
                    decision = {
                        'symbol': symbol,
                        'action': 'BUY',
                        'confidence': confidence,
                        'reasoning': opp.get('reasoning', 'Portfolio batch recommendation'),
                        'position_size_pct': target_allocation,
                        'source': 'portfolio_batch'
                    }
                    
                    self.execute_decision(decision)
                    logger.info(f"✅ Executed BUY {symbol} (confidence: {confidence}%, allocation: {target_allocation}%)")
            
            # Execute SELL recommendations  
            positions_to_exit = analysis.get('positions_to_exit', [])
            logger.info(f"📉 Executing {len(positions_to_exit)} SELL recommendations...")
            
            for exit_rec in positions_to_exit:
                symbol = exit_rec.get('symbol')
                confidence = exit_rec.get('confidence', 0)
                
                if confidence >= 60 and symbol in self.positions:  # Lower threshold for sells
                    decision = {
                        'symbol': symbol,
                        'action': 'SELL',
                        'confidence': confidence,
                        'reasoning': exit_rec.get('reasoning', 'Portfolio rotation recommendation'),
                        'position_size_pct': 100,  # Full position exit
                        'source': 'portfolio_batch'
                    }
                    
                    self.execute_decision(decision)
                    logger.info(f"✅ Executed SELL {symbol} (confidence: {confidence}%)")
            
        except Exception as e:
            logger.error(f"Portfolio decision execution failed: {e}")
    
    def _log_batch_analysis(
        self, 
        portfolio_analysis: Dict[str, Any], 
        opportunities: List[Dict[str, Any]], 
        current_positions: List[Dict[str, Any]]
    ):
        """Log the comprehensive batch analysis results."""
        
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'type': 'portfolio_batch_cycle',
                'market_data': {
                    'opportunities_analyzed': len(opportunities),
                    'positions_analyzed': len(current_positions),
                    'account_value': self.account_value,
                    'buying_power': self.buying_power,
                    'current_pnl': self.current_pnl
                },
                'portfolio_analysis': portfolio_analysis,
                'top_opportunities': [
                    {
                        'symbol': opp['symbol'], 
                        'score': opp['composite_score'], 
                        'tier': opp['tier']
                    } for opp in sorted(opportunities, key=lambda x: x['composite_score'], reverse=True)[:5]
                ],
                'position_performance': [
                    {
                        'symbol': pos['symbol'],
                        'pnl_pct': pos['pnl_pct'],
                        'current_price': pos['current_price']
                    } for pos in current_positions
                ]
            }
            
            # Log to decisions file
            decisions_log = settings.project_root / "logs" / "decisions.jsonl"
            with open(decisions_log, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
                
            # Summary log  
            analysis = portfolio_analysis.get('portfolio_analysis', {})
            logger.info("📊 BATCH ANALYSIS SUMMARY:")
            logger.info(f"   Market Overview: {analysis.get('market_overview', 'N/A')[:100]}...")
            logger.info(f"   Best Opportunities: {len(analysis.get('best_opportunities', []))}")
            logger.info(f"   Positions to Exit: {len(analysis.get('positions_to_exit', []))}")
            logger.info(f"   Risk Assessment: {analysis.get('risk_assessment', 'N/A')[:100]}...")
            
        except Exception as e:
            logger.error(f"Batch analysis logging failed: {e}")
    
    async def run_background_intelligence(self):
        """
        Run background market intelligence analysis during idle time.
        
        Returns:
            MarketIntelligence object or None if failed
        """
        try:
            # Run intelligence analysis
            intelligence = await self.intelligence_engine.run_background_analysis()
            
            # Save intelligence for historical tracking
            if intelligence:
                self.intelligence_engine.save_intelligence(intelligence)
                
                # Store in memory for next trading cycle
                self._last_market_intelligence = intelligence
            
            return intelligence
            
        except Exception as e:
            logger.error(f"❌ Background intelligence failed: {e}")
            return None
    
    def run_continuous(self, interval_minutes: int = 5):
        """
        Run trading agent continuously with background market intelligence.
        
        DEPRECATED: Use run_continuous_intelligent() for adaptive scheduling.
        
        Args:
            interval_minutes: Minutes between cycles
        """
        logger.warning("⚠️ Using legacy run_continuous(). Consider run_continuous_intelligent() for better resource usage.")
        logger.info(f"Starting continuous trading (interval: {interval_minutes} min)")
        
        try:
            while True:
                # Run trading cycle
                self.run_cycle()
                
                # Run background market intelligence during wait time
                logger.info(f"🔍 Running background market analysis during {interval_minutes}-minute wait...")
                
                start_wait = time.time()
                # Run async background intelligence from sync context
                try:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    intelligence = loop.run_until_complete(self.run_background_intelligence())
                    loop.close()
                except Exception as e:
                    logger.error(f"Failed to run background intelligence: {e}")
                    intelligence = None
                
                # Log intelligence findings
                if intelligence:
                    logger.info(f"📊 Market Intelligence Summary:")
                    logger.info(f"   Sentiment: {intelligence.market_sentiment} ({intelligence.confidence}%)")
                    logger.info(f"   Regime: {intelligence.regime_assessment}")
                    if intelligence.key_findings:
                        # Handle both strings and other types
                        findings = [str(f) for f in intelligence.key_findings[:3]]
                        logger.info(f"   Key Findings: {', '.join(findings)}")
                    if intelligence.recommended_actions:
                        # Handle both strings and other types
                        actions = [str(a) for a in intelligence.recommended_actions[:2]]
                        logger.info(f"   Recommended Actions: {', '.join(actions)}")
                
                # Calculate remaining wait time
                elapsed = time.time() - start_wait
                remaining_wait = (interval_minutes * 60) - elapsed
                
                if remaining_wait > 0:
                    logger.info(f"⏱️ Analysis completed in {elapsed:.1f}s, waiting {remaining_wait:.1f}s more...")
                    time.sleep(remaining_wait)
                else:
                    logger.info(f"✅ Analysis took {elapsed:.1f}s (full interval used)")
                
        except KeyboardInterrupt:
            logger.info("Trading agent stopped by user")
        except Exception as e:
            logger.error(f"Fatal error in trading loop: {e}")
            raise
    
    def run_continuous_intelligent(self):
        """
        Run trading agent with intelligent adaptive scheduling.
        
        Uses market state detection to:
        - Trade actively during market hours
        - Run strategic analysis during evenings
        - Sleep during overnight hours
        - Prepare during pre-market
        
        This method provides 70% reduction in LLM usage while maintaining
        or improving decision quality through strategic timing.
        """
        from wawatrader.scheduler import IntelligentScheduler
        from wawatrader.scheduled_tasks import ScheduledTaskHandlers
        
        logger.info("🧠 Starting intelligent adaptive operation...")
        logger.info("   Market-aware scheduling enabled")
        logger.info("   Resource optimization active")
        logger.info("")
        
        # Initialize scheduler and task handlers
        scheduler = IntelligentScheduler(alpaca_client=self.alpaca)
        task_handlers = ScheduledTaskHandlers(trading_agent=self)
        
        # Display initial status
        scheduler.display_status()
        
        # Map task names to handler methods
        task_map = {
            "trading_cycle": task_handlers.trading_cycle,
            "quick_intelligence": task_handlers.quick_intelligence,
            "deep_analysis": task_handlers.deep_analysis,
            "pre_close_assessment": task_handlers.pre_close_assessment,
            "daily_summary": task_handlers.daily_summary,
            "earnings_analysis": task_handlers.earnings_analysis,
            "sector_deep_dive": task_handlers.sector_deep_dive,
            "international_markets": task_handlers.international_markets,
            "news_monitor": task_handlers.news_monitor,
            "overnight_summary": task_handlers.overnight_summary,
            "premarket_scanner": task_handlers.premarket_scanner,
            "market_open_prep": task_handlers.market_open_prep,
        }
        
        try:
            last_state = None
            
            while True:
                # Get current market state
                current_state = scheduler.get_current_state()
                
                # Log state transitions
                if current_state != last_state:
                    logger.info("")
                    logger.info("=" * 70)
                    logger.info(
                        f"{current_state.emoji} STATE TRANSITION: {current_state.description.upper()}"
                    )
                    logger.info(f"   Focus: {current_state.primary_focus}")
                    logger.info("=" * 70)
                    logger.info("")
                    last_state = current_state
                
                # Get next task to run
                next_task = scheduler.get_next_task()
                
                if next_task:
                    # Execute the task
                    logger.info(f"▶️  Executing: {next_task.description}")
                    
                    if next_task.name in task_map:
                        try:
                            result = task_map[next_task.name]()
                            scheduler.mark_task_complete(next_task.name)
                            
                            if result.get("status") == "success":
                                logger.info(f"✅ {next_task.name} completed successfully")
                            else:
                                logger.warning(f"⚠️ {next_task.name} completed with errors")
                        
                        except Exception as e:
                            logger.error(f"❌ Task {next_task.name} failed: {e}")
                    else:
                        logger.warning(f"⚠️ No handler for task: {next_task.name}")
                        scheduler.mark_task_complete(next_task.name)
                
                # Sleep based on market state
                sleep_duration = scheduler.get_sleep_duration()
                
                if next_task:
                    logger.debug(f"⏸️  Sleeping {sleep_duration}s until next check...")
                else:
                    # More verbose logging when idle
                    logger.debug(
                        f"💤 {current_state.description} - "
                        f"No tasks due, sleeping {sleep_duration}s..."
                    )
                
                time.sleep(sleep_duration)
        
        except KeyboardInterrupt:
            logger.info("")
            logger.info("🛑 Intelligent scheduler stopped by user")
            
            # Display final statistics
            logger.info("")
            scheduler.display_status()
        
        except Exception as e:
            logger.error(f"❌ Fatal error in intelligent scheduler: {e}")
            raise
    
    async def run_event_driven(self):
        """
        Event-driven trading loop (Phase 3+4).
        
        PHASE 4 INTEGRATION: Market-hours-aware event processing
        
        Different activities based on market phase:
        - MARKET_OPEN: Process events from EventQueue
        - AFTER_HOURS: Learning and analysis
        - EVENING_RESEARCH: Symbol discovery
        - DEEP_NIGHT: News synthesis and briefing
        - PRE_MARKET: Gap scanning
        
        Processes events from EventQueue:
        - Price alerts (targets, stops, breakouts)
        - News events
        - Volume spikes
        - Portfolio-level triggers
        
        EVENT-DRIVEN ARCHITECTURE: Replaces arbitrary 5-minute checks with
        intelligent event-based triggers + market-hours awareness.
        """
        logger.info("="*70)
        logger.info("🚀 Starting Event-Driven Trading System (Market-Hours Aware)")
        logger.info("="*70)
        logger.info("")
        logger.info("📊 System Configuration:")
        logger.info(f"   Symbols: {', '.join(self.symbols)}")
        logger.info(f"   Dry run: {self.dry_run}")
        logger.info(f"   Event queue: Active")
        logger.info(f"   Memory store: Active")
        logger.info(f"   Kelly sizing: Active")
        logger.info(f"   Market hours manager: Active")
        logger.info(f"   Symbol discovery: Active")
        logger.info("")
        
        # Start monitoring current prices for alerts
        self._start_price_monitoring()
        
        try:
            event_count = 0
            last_status_time = datetime.now()
            last_phase_check = datetime.now()
            current_phase = None
            
            while True:
                # Check market phase every 5 minutes
                now = datetime.now()
                if (now - last_phase_check).total_seconds() > 300:
                    new_phase = self.market_hours_manager.get_current_phase()
                    
                    if new_phase != current_phase:
                        current_phase = new_phase
                        logger.info("")
                        logger.info("="*70)
                        logger.info(f"📅 MARKET PHASE CHANGE: {current_phase.value.upper()}")
                        logger.info("="*70)
                        
                        # Trigger phase-specific activities
                        await self._handle_phase_change(current_phase)
                    
                    last_phase_check = now
                
                # Get next event (FIFO with priority)
                event = self.event_queue.get_next_event()
                
                if event:
                    event_count += 1
                    logger.info("")
                    logger.info(f"📬 Event #{event_count}: {event.event_type.value}")
                    logger.info(f"   Symbol: {event.symbol}")
                    logger.info(f"   Priority: {event.priority}")
                    logger.info(f"   Source: {event.source}")
                    logger.info(f"   Data: {event.data}")
                    
                    # Handle event
                    await self._handle_event(event)
                    
                else:
                    # No events - brief sleep then check again
                    await asyncio.sleep(1)
                    
                    # Status update every 5 minutes when idle
                    if (datetime.now() - last_status_time).total_seconds() > 300:
                        self._log_event_queue_status()
                        self._log_memory_status()
                        last_status_time = datetime.now()
        
        except KeyboardInterrupt:
            logger.info("")
            logger.info("="*70)
            logger.info("🛑 Event-Driven System Stopped")
            logger.info("="*70)
            self._log_event_queue_status()
            self._log_memory_status()
        
        except Exception as e:
            logger.error(f"❌ Fatal error in event-driven loop: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    async def _handle_phase_change(self, phase: MarketPhase):
        """
        Handle transition to new market phase (Phase 4).
        
        Triggers phase-specific activities:
        - EVENING_RESEARCH: Run symbol discovery
        - DEEP_NIGHT: Synthesize news and prepare briefing
        - PRE_MARKET: Run gap scanner
        - MARKET_OPEN: Resume normal event processing
        - AFTER_HOURS: Daily learning and analysis
        """
        from wawatrader.event_system import EventType, EventPriority
        
        if phase == MarketPhase.EVENING_RESEARCH:
            logger.info("🔍 Evening Research Phase - Running symbol discovery...")
            try:
                opportunities = self.symbol_discovery.discover_opportunities()
                logger.info(f"✅ Discovered {len(opportunities)} opportunities")
                
                # Add opportunities to event queue
                for opp in opportunities:
                    event = Event(
                        event_type=EventType.NEW_OPPORTUNITY,
                        symbol=opp.symbol,
                        priority=EventPriority.MEDIUM,
                        source="symbol_discovery",
                        data=opp.to_dict()
                    )
                    self.event_queue.add_event(event)
                    
            except Exception as e:
                logger.error(f"❌ Symbol discovery failed: {e}")
        
        elif phase == MarketPhase.DEEP_NIGHT:
            logger.info("💤 Deep Night Phase - News synthesis...")
            # TODO: Implement overnight news synthesis
            # This would use the overnight analyst to synthesize news
            # and prepare morning briefing
            logger.info("ℹ️  Overnight news synthesis not yet implemented")
        
        elif phase == MarketPhase.PRE_MARKET:
            logger.info("🌅 Pre-Market Phase - Running gap scanner...")
            try:
                # Scan for pre-market gaps
                gaps = self.symbol_discovery._scan_gap_opportunities()
                logger.info(f"✅ Found {len(gaps)} gap opportunities")
                
                # Add gaps to event queue as high-priority
                for gap in gaps:
                    event = Event(
                        event_type=EventType.GAP_DETECTED,
                        symbol=gap.symbol,
                        priority=EventPriority.HIGH,
                        source="gap_scanner",
                        data=gap.to_dict()
                    )
                    self.event_queue.add_event(event)
                    
            except Exception as e:
                logger.error(f"❌ Gap scanner failed: {e}")
        
        elif phase == MarketPhase.MARKET_OPEN:
            logger.info("🟢 Market Open - Processing events from queue...")
            logger.info(f"   Current queue size: {self.event_queue.get_queue_size()}")
        
        elif phase == MarketPhase.AFTER_HOURS:
            logger.info("📊 After Hours - Daily learning and analysis...")
            # Could trigger end-of-day learning here
            try:
                self._generate_morning_insights()
            except Exception as e:
                logger.error(f"❌ Daily learning failed: {e}")

    
    def _start_price_monitoring(self):
        """Start monitoring prices for alert triggers"""
        logger.info("🔔 Starting price monitoring...")
        logger.info(f"   Monitoring {len(self.symbols)} symbols for price alerts")
        
        # Schedule periodic price checks
        # This will check prices and trigger events if alerts crossed
        import threading
        
        def check_prices():
            while True:
                try:
                    for symbol in self.symbols:
                        # Get current price
                        bars = self.alpaca.get_bars(symbol, "1Min", limit=1)
                        if bars is not None and len(bars) > 0:
                            current_price = bars['close'].iloc[-1]
                            
                            # Check price alerts
                            self.price_monitor.check_price(symbol, current_price)
                            
                            # Check volume alerts
                            volume = bars['volume'].iloc[-1]
                            avg_volume = bars['volume'].mean() if len(bars) > 20 else volume
                            self.volume_monitor.check_volume(symbol, volume, avg_volume)
                    
                    # Sleep between checks
                    import time
                    time.sleep(60)  # Check every minute
                    
                except Exception as e:
                    logger.error(f"❌ Price monitoring error: {e}")
                    import time
                    time.sleep(60)
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=check_prices, daemon=True)
        monitor_thread.start()
        logger.info("✅ Price monitoring started")
    
    async def _handle_event(self, event: 'Event'):
        """
        Handle a single event from the queue.
        
        Routes events to appropriate handlers based on type.
        """
        from wawatrader.event_system import EventType
        
        try:
            # Route based on event type
            if event.event_type == EventType.TARGET_HIT:
                await self._handle_target_hit(event)
            
            elif event.event_type == EventType.STOP_LOSS_HIT:
                await self._handle_stop_loss(event)
            
            elif event.event_type == EventType.BREAKOUT_UPSIDE:
                await self._handle_breakout(event)
            
            elif event.event_type == EventType.BREAKDOWN_DOWNSIDE:
                await self._handle_breakdown(event)
            
            elif event.event_type == EventType.VOLUME_SPIKE:
                await self._handle_volume_spike(event)
            
            elif event.event_type == EventType.BREAKING_NEWS:
                await self._handle_breaking_news(event)
            
            elif event.event_type == EventType.NEW_OPPORTUNITY:
                await self._handle_new_opportunity(event)
            
            else:
                logger.warning(f"⚠️ Unhandled event type: {event.event_type.value}")
        
        except Exception as e:
            logger.error(f"❌ Error handling event {event.event_type.value}: {e}")
            import traceback
            traceback.print_exc()
    
    async def _handle_target_hit(self, event: 'Event'):
        """Handle target price hit event"""
        logger.info(f"🎯 TARGET HIT: {event.symbol}")
        
        # Get position memory
        memory = self.memory_store.get_open_position(event.symbol)
        if not memory:
            logger.warning(f"⚠️ No memory found for {event.symbol}")
            return
        
        # Re-evaluate with thesis vs reality
        analysis = self.analyze_symbol(event.symbol)
        if not analysis:
            return
        
        decision = self.make_decision(analysis)
        
        # Log decision
        self.log_decision(decision)
        
        # Execute if approved
        if decision.risk_approved and decision.action == 'sell':
            self.execute_decision(decision)
    
    async def _handle_stop_loss(self, event: 'Event'):
        """Handle stop loss hit - CRITICAL priority exit"""
        logger.error(f"🚨 STOP LOSS HIT: {event.symbol}")
        
        # Emergency exit - bypass normal decision making
        if event.symbol in self.positions:
            pos = self.positions[event.symbol]
            qty = abs(int(float(pos['qty'])))
            
            if qty > 0:
                # Create emergency sell decision
                from wawatrader.trading_agent import TradingDecision
                
                decision = TradingDecision(
                    timestamp=datetime.now().isoformat(),
                    symbol=event.symbol,
                    action='sell',
                    shares=qty,
                    price=event.data.get('current_price', 0),
                    confidence=100,
                    sentiment='bearish',
                    reasoning=f"Stop loss triggered at ${event.data.get('stop_price', 0):.2f}",
                    risk_approved=True,
                    risk_reason="Emergency stop loss exit",
                    executed=False
                )
                
                # Execute immediately
                self.execute_decision(decision)
                logger.info(f"✅ Emergency exit executed for {event.symbol}")
    
    async def _handle_breakout(self, event: 'Event'):
        """Handle breakout above resistance"""
        logger.info(f"📈 BREAKOUT: {event.symbol}")
        
        # Analyze for potential entry
        analysis = self.analyze_symbol(event.symbol)
        if not analysis:
            return
        
        decision = self.make_decision(analysis)
        self.log_decision(decision)
        
        if decision.risk_approved:
            self.execute_decision(decision)
    
    async def _handle_breakdown(self, event: 'Event'):
        """Handle breakdown below support"""
        logger.info(f"📉 BREAKDOWN: {event.symbol}")
        
        # If we have position, consider exit
        if event.symbol in self.positions:
            analysis = self.analyze_symbol(event.symbol)
            if analysis:
                decision = self.make_decision(analysis)
                self.log_decision(decision)
                if decision.risk_approved:
                    self.execute_decision(decision)
    
    async def _handle_volume_spike(self, event: 'Event'):
        """Handle unusual volume spike"""
        logger.info(f"📊 VOLUME SPIKE: {event.symbol} ({event.data.get('ratio', 0):.1f}x)")
        
        # Analyze for opportunity
        analysis = self.analyze_symbol(event.symbol)
        if not analysis:
            return
        
        decision = self.make_decision(analysis)
        self.log_decision(decision)
        
        if decision.risk_approved:
            self.execute_decision(decision)
    
    async def _handle_breaking_news(self, event: 'Event'):
        """Handle breaking news event"""
        logger.info(f"📰 BREAKING NEWS: {event.symbol}")
        logger.info(f"   {event.data.get('headline', 'No headline')}")
        
        # Re-evaluate position or analyze for entry
        analysis = self.analyze_symbol(event.symbol)
        if not analysis:
            return
        
        decision = self.make_decision(analysis)
        self.log_decision(decision)
        
        if decision.risk_approved:
            self.execute_decision(decision)
    
    async def _handle_new_opportunity(self, event: 'Event'):
        """Handle new opportunity discovered"""
        logger.info(f"💡 NEW OPPORTUNITY: {event.symbol}")
        logger.info(f"   Quality: {event.data.get('quality_score', 0)}/100")
        
        # Analyze opportunity
        analysis = self.analyze_symbol(event.symbol)
        if not analysis:
            return
        
        decision = self.make_decision(analysis)
        self.log_decision(decision)
        
        if decision.risk_approved:
            self.execute_decision(decision)
    
    def _log_event_queue_status(self):
        """Log current event queue status"""
        status = self.event_queue.get_queue_status()
        
        logger.info("")
        logger.info("📊 Event Queue Status:")
        logger.info(f"   Pending: {status['pending_count']}")
        logger.info(f"   Processed: {status['total_processed']}")
        logger.info(f"   By Priority: {status['priority_breakdown']}")
        logger.info(f"   By Symbol: {status['symbol_breakdown']}")
    
    def _log_memory_status(self):
        """Log current memory store status"""
        open_positions = self.memory_store.get_all_open_positions()
        
        logger.info("")
        logger.info("💾 Memory Store Status:")
        logger.info(f"   Open Positions: {len(open_positions)}")
        
        for pos in open_positions[:5]:
            pnl_pct = ((self.positions.get(pos.symbol, {}).get('current_price', pos.entry_price) - pos.entry_price) / pos.entry_price) * 100
            logger.info(f"   - {pos.symbol}: {pos.strategy}, ${pos.entry_price:.2f} ({pnl_pct:+.2f}%)")
    
    def start_position_monitoring(self):
        """Start the PositionManager background monitoring"""
        try:
            self.position_manager.start()
            logger.info("✅ PositionManager monitoring started")
        except Exception as e:
            logger.error(f"❌ Failed to start PositionManager: {e}")
    
    def stop_position_monitoring(self):
        """Stop the PositionManager background monitoring"""
        try:
            self.position_manager.stop()
            logger.info("🛑 PositionManager monitoring stopped")
        except Exception as e:
            logger.error(f"❌ Failed to stop PositionManager: {e}")
    
    def set_market_close_time(self, close_time: datetime):
        """
        Set market close time for PositionManager safety checks.
        
        Args:
            close_time: Time to consider market close (e.g., 3:30 PM EST for 30-min buffer)
        """
        self.position_manager.set_market_close_time(close_time)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about trading decisions.
        
        Returns:
            Dict with counts and metrics
        """
        total = len(self.decisions)
        if total == 0:
            return {
                'total_decisions': 0,
                'message': 'No decisions yet'
            }
        
        # Count by action
        buys = sum(1 for d in self.decisions if d.action == 'buy')
        sells = sum(1 for d in self.decisions if d.action == 'sell')
        holds = sum(1 for d in self.decisions if d.action == 'hold')
        
        # Count by risk approval
        approved = sum(1 for d in self.decisions if d.risk_approved)
        rejected = total - approved
        
        # Count by execution
        executed = sum(1 for d in self.decisions if d.executed)
        
        # Average confidence
        avg_confidence = sum(d.confidence for d in self.decisions) / total
        
        return {
            'total_decisions': total,
            'by_action': {
                'buy': buys,
                'sell': sells,
                'hold': holds
            },
            'risk_approval': {
                'approved': approved,
                'rejected': rejected,
                'approval_rate': f"{(approved/total)*100:.1f}%"
            },
            'execution': {
                'executed': executed,
                'execution_rate': f"{(executed/total)*100:.1f}%"
            },
            'avg_confidence': f"{avg_confidence:.1f}%"
        }


if __name__ == "__main__":
    # Test the trading agent
    print("\n" + "="*60)
    print("Testing Trading Agent...")
    print("="*60)
    
    # Create agent
    symbols = ["AAPL", "MSFT"]
    agent = TradingAgent(symbols=symbols, dry_run=True)
    
    print("\nRunning one trading cycle...")
    agent.run_cycle()
    
    print("\n" + "-"*60)
    print("Trading Statistics")
    print("-"*60)
    stats = agent.get_statistics()
    print(json.dumps(stats, indent=2))
    
    print("\n" + "="*60)
    print("✅ Trading Agent test complete!")
    print("="*60)
    print("\nTo run continuously:")
    print("  agent.run_continuous(interval_minutes=5)")
