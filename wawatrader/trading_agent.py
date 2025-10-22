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
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from pathlib import Path
from loguru import logger

from wawatrader.alpaca_client import get_client
from wawatrader.indicators import analyze_dataframe, get_latest_signals
from wawatrader.llm_bridge import LLMBridge
from wawatrader.risk_manager import get_risk_manager
from config.settings import settings


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
        self.llm_bridge = LLMBridge()
        self.risk_manager = get_risk_manager()
        
        # State tracking
        self.decisions: List[TradingDecision] = []
        self.positions: Dict[str, Any] = {}
        self.account_value: float = 0
        self.current_pnl: float = 0
        
        # Configuration
        self.min_confidence = settings.trading.min_confidence
        self.lookback_days = 90  # Historical data for indicators
        
        # Logging
        self.setup_logging()
        
        logger.info(f"Trading Agent initialized")
        logger.info(f"  Symbols: {', '.join(symbols)}")
        logger.info(f"  Dry run: {dry_run}")
        logger.info(f"  Min confidence: {self.min_confidence}%")
    
    def setup_logging(self):
        """Setup decision logging to file"""
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
    
    def update_account_state(self):
        """Update account value, positions, and P&L"""
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
        
        # Step 5: LLM analysis
        llm_analysis = self.llm_bridge.analyze_market(
            symbol=symbol,
            signals=signals,
            news=news,
            current_position=current_position
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
        
        # Extract LLM recommendation
        action = llm.get('action', 'hold')
        confidence = llm.get('confidence', 0)
        sentiment = llm.get('sentiment', 'neutral')
        reasoning = llm.get('reasoning', 'No reasoning provided')
        
        # Get current price
        price = signals['price']['close']
        
        # Determine shares to trade
        shares = self._calculate_position_size(symbol, price, action)
        
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
            logger.info(f"✅ {symbol}: {action.upper()} {shares} shares @ ${price:.2f} (confidence: {confidence}%)")
        
        return decision
    
    def _calculate_position_size(self, symbol: str, price: float, action: str) -> int:
        """
        Calculate position size based on account value and risk limits.
        
        Args:
            symbol: Stock ticker
            price: Current price
            action: "buy" or "sell"
        
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
        
        # For buy: calculate based on max position size
        max_position_value = self.account_value * settings.risk.max_position_size
        shares = int(max_position_value / price)
        
        # Ensure at least 1 share if we have enough capital
        if shares == 0 and self.account_value >= price:
            shares = 1
        
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
                decision.price = final_order['filled_avg_price']  # Update with actual fill price
                logger.info(f"✅ Order filled @ ${final_order['filled_avg_price']:.2f}")
                
                # Record trade for risk tracking
                self.risk_manager.record_trade(
                    decision.symbol,
                    decision.action,
                    decision.shares,
                    final_order['filled_avg_price']
                )
            else:
                decision.executed = False
                status = final_order['status'] if final_order else 'unknown'
                decision.execution_error = f"Order not filled (status: {status})"
                logger.warning(f"⚠️  Order not filled: {status}")
            
        except Exception as e:
            logger.error(f"Failed to execute trade: {e}")
            decision.executed = False
            decision.execution_error = str(e)
    
    def log_decision(self, decision: TradingDecision):
        """
        Log trading decision to both file and memory
        
        Args:
            decision: TradingDecision to log
        """
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
        
        # Check market status
        try:
            clock = self.alpaca.get_clock()
            if not clock['is_open']:
                logger.info("Market is closed, skipping cycle")
                return
        except Exception as e:
            logger.error(f"Failed to check market status: {e}")
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
    
    def run_continuous(self, interval_minutes: int = 5):
        """
        Run trading agent continuously.
        
        Args:
            interval_minutes: Minutes between cycles
        """
        logger.info(f"Starting continuous trading (interval: {interval_minutes} min)")
        
        try:
            while True:
                # Run cycle
                self.run_cycle()
                
                # Wait for next cycle
                logger.info(f"Waiting {interval_minutes} minutes until next cycle...")
                time.sleep(interval_minutes * 60)
                
        except KeyboardInterrupt:
            logger.info("Trading agent stopped by user")
        except Exception as e:
            logger.error(f"Fatal error in trading loop: {e}")
            raise
    
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
