"""
Event-Driven Position Management with Smart LLM Queue

Key Design Points:
1. Local LLM = unlimited calls, but SERIAL processing (one at a time)
2. Priority queue: Critical events (stops) processed before routine checks
3. Smart batching: Group low-priority events to reduce wait
4. Fast-path decisions: Some actions don't need LLM (hard stops)
5. Concurrent monitoring: Check prices every 15 seconds (fast polling is free!)
"""

import threading
import queue
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import IntEnum
import time

from loguru import logger


class EventPriority(IntEnum):
    """Priority levels for trading events"""
    CRITICAL = 1    # Stop loss, trailing stop - immediate action
    HIGH = 2        # Take profit 2, major technical breakdown
    MEDIUM = 3      # Take profit 1, RSI flags
    LOW = 4         # Volume spikes, informational
    ROUTINE = 5     # Periodic health checks


class EventAction(IntEnum):
    """How to handle the event"""
    EXECUTE_IMMEDIATELY = 1  # Don't wait for LLM, execute now (hard stops)
    REQUIRE_LLM = 2          # Must consult LLM before action
    BATCH_OK = 3             # Can be batched with other low-priority events
    FALLBACK_AVAILABLE = 4   # Can execute fallback plan if LLM unavailable


@dataclass
class PositionTargets:
    """Smart targets and flags for a single position"""
    
    # Identity
    symbol: str
    entry_price: float
    entry_time: datetime
    shares: int
    
    # Price targets (will be dynamically adjusted)
    take_profit_1: float      # Conservative target (2R)
    take_profit_2: float      # Aggressive target (3R)
    stop_loss: float          # Hard stop (cannot be moved down)
    trailing_stop: float      # Dynamic stop (moves up with price)
    
    # Technical flags
    rsi_exit_threshold: float = 75.0
    rsi_entry_threshold: float = 30.0  # For averaging down (future)
    volume_alert_multiplier: float = 2.0
    
    # State tracking
    highest_price_seen: float = field(default=0.0)
    lowest_price_seen: float = field(default=float('inf'))
    last_checked: datetime = field(default_factory=datetime.now)
    last_llm_consultation: datetime = field(default_factory=datetime.now)
    
    # Flags
    take_profit_1_hit: bool = False  # Track if we already processed TP1
    trailing_stop_active: bool = False
    
    # Fallback plans (execute if LLM unavailable)
    fallback_on_tp1: str = "PARTIAL_EXIT"  # "PARTIAL_EXIT", "FULL_EXIT", "TRAIL_STOP"
    fallback_on_tp2: str = "FULL_EXIT"     # "FULL_EXIT", "TRAIL_STOP"
    fallback_on_rsi_high: str = "FULL_EXIT"  # "FULL_EXIT", "HOLD"
    
    def __post_init__(self):
        """Initialize tracking fields"""
        if self.highest_price_seen == 0.0:
            self.highest_price_seen = self.entry_price
        if self.lowest_price_seen == float('inf'):
            self.lowest_price_seen = self.entry_price
    
    def update_price_extremes(self, current_price: float):
        """Track highest/lowest prices for trailing stops and analysis"""
        if current_price > self.highest_price_seen:
            self.highest_price_seen = current_price
            # Update trailing stop to follow price up
            if self.trailing_stop_active:
                # Keep trailing stop 1.5% below highest price
                new_trailing = current_price * 0.985
                # Only move trailing stop UP, never down
                if new_trailing > self.trailing_stop:
                    old_stop = self.trailing_stop
                    self.trailing_stop = new_trailing
                    logger.debug(f"📈 {self.symbol}: Trailing stop raised ${old_stop:.2f} → ${new_trailing:.2f}")
        
        if current_price < self.lowest_price_seen:
            self.lowest_price_seen = current_price
    
    def check_targets(self, current_price: float, rsi: Optional[float] = None, 
                     volume_ratio: Optional[float] = None) -> List[Tuple[str, EventPriority, EventAction]]:
        """
        Check if any targets/flags triggered.
        
        Returns list of (event_type, priority, action) tuples.
        """
        triggered = []
        
        # CRITICAL EVENTS - Execute immediately without LLM
        if current_price <= self.stop_loss:
            triggered.append(("STOP_LOSS", EventPriority.CRITICAL, EventAction.EXECUTE_IMMEDIATELY))
            return triggered  # Stop loss is terminal, return immediately
        
        if self.trailing_stop_active and current_price <= self.trailing_stop:
            triggered.append(("TRAILING_STOP", EventPriority.CRITICAL, EventAction.EXECUTE_IMMEDIATELY))
            return triggered  # Trailing stop is terminal
        
        # HIGH PRIORITY - Require LLM consultation (with fallback)
        if current_price >= self.take_profit_2:
            triggered.append(("TAKE_PROFIT_2", EventPriority.HIGH, EventAction.FALLBACK_AVAILABLE))
        
        # MEDIUM PRIORITY - Require LLM but not urgent (with fallback)
        if current_price >= self.take_profit_1 and not self.take_profit_1_hit:
            triggered.append(("TAKE_PROFIT_1", EventPriority.MEDIUM, EventAction.FALLBACK_AVAILABLE))
        
        # Technical flags - can be batched (with fallback)
        if rsi is not None:
            if rsi > self.rsi_exit_threshold:
                triggered.append(("RSI_OVERBOUGHT", EventPriority.MEDIUM, EventAction.FALLBACK_AVAILABLE))
            elif rsi < self.rsi_entry_threshold:
                triggered.append(("RSI_OVERSOLD", EventPriority.LOW, EventAction.BATCH_OK))
        
        if volume_ratio is not None and volume_ratio > self.volume_alert_multiplier:
            triggered.append(("VOLUME_SPIKE", EventPriority.LOW, EventAction.BATCH_OK))
        
        return triggered


@dataclass
class TradingEvent:
    """Event requiring attention (possibly LLM consultation)"""
    
    event_type: str           # "STOP_LOSS", "TAKE_PROFIT_1", etc.
    symbol: str
    timestamp: datetime
    priority: EventPriority
    action_type: EventAction  # Whether to execute immediately or consult LLM
    
    # Market context at trigger time
    trigger_price: float
    trigger_details: Dict[str, Any] = field(default_factory=dict)
    
    # LLM processing
    requires_llm: bool = field(init=False)
    llm_processed: bool = False
    llm_decision: Optional[Dict[str, Any]] = None
    
    # Fallback tracking
    fallback_executed: bool = False
    fallback_reason: Optional[str] = None
    
    def __post_init__(self):
        self.requires_llm = (self.action_type in [EventAction.REQUIRE_LLM, EventAction.FALLBACK_AVAILABLE])
    
    def __lt__(self, other):
        """For priority queue - lower number = higher priority"""
        if self.priority != other.priority:
            return self.priority < other.priority
        # Same priority: older events first (FIFO)
        return self.timestamp < other.timestamp


class LLMRequestQueue:
    """
    Smart queue manager for serial LLM processing.
    
    Features:
    - Priority-based processing
    - Smart batching of low-priority requests
    - Timeout protection (don't wait forever)
    - Concurrent request detection (warn if queue backs up)
    - Fallback execution when LLM unavailable
    """
    
    def __init__(self, max_wait_time: int = 300, llm_timeout: int = 30):
        """
        Args:
            max_wait_time: Max seconds an event can wait before escalating priority
            llm_timeout: Max seconds to wait for LLM response before using fallback
        """
        self.queue: queue.PriorityQueue[TradingEvent] = queue.PriorityQueue()
        self.max_wait_time = max_wait_time
        self.llm_timeout = llm_timeout
        self.processing_lock = threading.Lock()
        self.current_request: Optional[str] = None  # Symbol being processed
        self.queue_depth_alert_threshold = 5
        
        # LLM health tracking
        self.llm_available = True
        self.llm_consecutive_failures = 0
        self.llm_last_success = datetime.now()
        self.llm_failure_threshold = 3  # After 3 failures, assume LLM is down
    
    def submit(self, event: TradingEvent):
        """Add event to queue"""
        self.queue.put(event)
        depth = self.queue.qsize()
        
        if depth > self.queue_depth_alert_threshold:
            logger.warning(f"⚠️ LLM queue depth: {depth} events waiting! Bottleneck detected.")
        
        logger.info(f"📥 Queued: {event.symbol} - {event.event_type} (Priority: {event.priority.name}, Queue: {depth})")
    
    def get_next(self, timeout: Optional[int] = None) -> Optional[TradingEvent]:
        """
        Get next event from queue (blocking).
        
        Args:
            timeout: Max seconds to wait for next event
        
        Returns:
            Next event or None if timeout
        """
        try:
            event = self.queue.get(timeout=timeout)
            
            # Check if event has been waiting too long
            wait_time = (datetime.now() - event.timestamp).total_seconds()
            if wait_time > self.max_wait_time:
                logger.warning(f"⏰ {event.symbol}: Event waited {wait_time:.0f}s (max: {self.max_wait_time}s)")
                # Escalate priority if waited too long
                if event.priority > EventPriority.HIGH:
                    logger.warning(f"⬆️ Escalating {event.symbol} to HIGH priority")
                    event.priority = EventPriority.HIGH
            
            return event
            
        except queue.Empty:
            return None
    
    def mark_processing(self, symbol: str):
        """Mark that we're processing this symbol"""
        with self.processing_lock:
            self.current_request = symbol
            logger.debug(f"🔄 Processing: {symbol}")
    
    def mark_complete(self, symbol: str):
        """Mark processing complete"""
        with self.processing_lock:
            if self.current_request == symbol:
                self.current_request = None
            logger.debug(f"✅ Completed: {symbol}")
    
    def is_processing(self, symbol: str) -> bool:
        """Check if symbol is currently being processed"""
        with self.processing_lock:
            return self.current_request == symbol
    
    def get_queue_depth(self) -> int:
        """Get current queue size"""
        return self.queue.qsize()
    
    def mark_llm_success(self):
        """Mark successful LLM call"""
        self.llm_consecutive_failures = 0
        self.llm_last_success = datetime.now()
        if not self.llm_available:
            logger.info("✅ LLM back online!")
            self.llm_available = True
    
    def mark_llm_failure(self):
        """Mark failed LLM call"""
        self.llm_consecutive_failures += 1
        
        if self.llm_consecutive_failures >= self.llm_failure_threshold and self.llm_available:
            logger.error(f"🚨 LLM OFFLINE: {self.llm_consecutive_failures} consecutive failures")
            logger.warning("⚠️ Switching to FALLBACK mode - will execute predefined plans")
            self.llm_available = False
    
    def is_llm_healthy(self) -> bool:
        """Check if LLM is considered available"""
        return self.llm_available


class PositionManager:
    """
    Event-driven position manager with smart LLM queue.
    
    Design for LOCAL LLM:
    - Poll prices FAST (every 15 seconds) - it's free!
    - Queue events by priority
    - Process LLM requests serially but efficiently
    - Execute critical stops immediately (no LLM needed)
    """
    
    def __init__(self, alpaca_client=None, llm_bridge=None, trading_agent=None,
                 max_positions: int = 10, poll_interval: int = 15):
        """
        Args:
            alpaca_client: AlpacaClient instance for market data
            llm_bridge: LLMBridge instance for analysis
            trading_agent: TradingAgent instance for execution
            max_positions: Max concurrent positions (10 for budget management)
            poll_interval: Seconds between price checks (15 = fast polling, it's free!)
        """
        self.max_positions = max_positions
        self.poll_interval = poll_interval
        
        # External integrations
        self.alpaca = alpaca_client
        self.llm_bridge = llm_bridge
        self.trading_agent = trading_agent
        
        # Position tracking
        self.positions: Dict[str, PositionTargets] = {}
        
        # Event management
        self.llm_queue = LLMRequestQueue()
        self.immediate_actions: queue.Queue[TradingEvent] = queue.Queue()
        
        # Threading
        self.monitor_thread: Optional[threading.Thread] = None
        self.processor_thread: Optional[threading.Thread] = None
        self.stop_flag = threading.Event()
        
        # Statistics
        self.stats = {
            'events_triggered': 0,
            'immediate_executions': 0,
            'llm_consultations': 0,
            'fallback_executions': 0,
            'avg_queue_wait': 0.0,
        }
        
        # Market close safety
        self.market_close_time = None  # Will be set to market close time
        self.pre_close_safety_minutes = 30  # Start emergency exits 30 min before close
    
    def add_position(self, symbol: str, entry_price: float, shares: int,
                    analysis: Dict[str, Any]) -> PositionTargets:
        """
        Add new position with smart targets.
        
        Targets calculated from:
        - LLM analysis (if it provided specific targets)
        - ATR-based stops (volatility-adjusted)
        - Risk/reward ratios (2:1 and 3:1)
        """
        if len(self.positions) >= self.max_positions:
            raise ValueError(f"Position limit reached ({self.max_positions})")
        
        # Calculate smart targets
        targets = self._calculate_targets(symbol, entry_price, shares, analysis)
        
        self.positions[symbol] = targets
        
        logger.info(f"📍 NEW POSITION: {symbol}")
        logger.info(f"   Entry: ${entry_price:.2f} x {shares} shares")
        logger.info(f"   🎯 Take Profit 1: ${targets.take_profit_1:.2f} ({self._pct_change(entry_price, targets.take_profit_1):+.1f}%)")
        logger.info(f"   🎯 Take Profit 2: ${targets.take_profit_2:.2f} ({self._pct_change(entry_price, targets.take_profit_2):+.1f}%)")
        logger.info(f"   🛑 Stop Loss: ${targets.stop_loss:.2f} ({self._pct_change(entry_price, targets.stop_loss):+.1f}%)")
        logger.info(f"   📊 Trailing Stop: ${targets.trailing_stop:.2f} (inactive until TP1)")
        
        return targets
    
    def _calculate_targets(self, symbol: str, entry_price: float, shares: int,
                          analysis: Dict[str, Any]) -> PositionTargets:
        """
        Calculate intelligent targets based on analysis.
        
        Priority:
        1. LLM-provided targets (if present in reasoning)
        2. ATR-based targets (volatility-adjusted)
        3. Fixed percentages (fallback)
        """
        signals = analysis.get('signals', {})
        llm_analysis = analysis.get('llm_analysis', {})
        reasoning = llm_analysis.get('reasoning', '')
        
        # Try to extract targets from LLM reasoning
        llm_target = self._extract_target_from_reasoning(reasoning)
        llm_stop = self._extract_stop_from_reasoning(reasoning)
        
        # Get ATR for volatility-adjusted stops
        volatility = signals.get('volatility', {})
        atr = volatility.get('atr', 0)
        
        # Calculate stop loss
        if llm_stop:
            stop_loss = llm_stop
            logger.debug(f"Using LLM stop: ${stop_loss:.2f}")
        elif atr > 0:
            # 2 ATR stop (volatility-adjusted)
            stop_loss = entry_price - (2 * atr)
            logger.debug(f"Using ATR stop: ${stop_loss:.2f} (2 x ${atr:.2f})")
        else:
            # Default -2%
            stop_loss = entry_price * 0.98
            logger.debug(f"Using default -2% stop: ${stop_loss:.2f}")
        
        # Calculate profit targets based on risk
        risk = entry_price - stop_loss
        
        if llm_target and llm_target > entry_price:
            # LLM provided target
            take_profit_2 = llm_target
            take_profit_1 = entry_price + (llm_target - entry_price) * 0.5
            logger.debug(f"Using LLM target: ${take_profit_2:.2f}")
        else:
            # Risk-reward based (2R and 3R)
            take_profit_1 = entry_price + (risk * 2)  # 2:1 R/R
            take_profit_2 = entry_price + (risk * 3)  # 3:1 R/R
            logger.debug(f"Using R/R targets: ${take_profit_1:.2f} (2R), ${take_profit_2:.2f} (3R)")
        
        return PositionTargets(
            symbol=symbol,
            entry_price=entry_price,
            entry_time=datetime.now(),
            shares=shares,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            stop_loss=stop_loss,
            trailing_stop=entry_price * 0.985,  # Initial trailing stop (inactive)
            highest_price_seen=entry_price,
            lowest_price_seen=entry_price,
        )
    
    def _extract_target_from_reasoning(self, reasoning: str) -> Optional[float]:
        """Extract price target from LLM reasoning"""
        import re
        # Look for patterns like "Target $265" or "target: $265" or "$265 target"
        patterns = [
            r'[Tt]arget[:\s]+\$(\d+\.?\d*)',
            r'\$(\d+\.?\d*)\s+target',
        ]
        for pattern in patterns:
            match = re.search(pattern, reasoning)
            if match:
                return float(match.group(1))
        return None
    
    def _extract_stop_from_reasoning(self, reasoning: str) -> Optional[float]:
        """Extract stop loss from LLM reasoning"""
        import re
        # Look for patterns like "stop $245" or "stop-loss: $245"
        patterns = [
            r'stop[:\s-]*loss[:\s]+\$(\d+\.?\d*)',
            r'stop[:\s]+\$(\d+\.?\d*)',
        ]
        for pattern in patterns:
            match = re.search(pattern, reasoning)
            if match:
                return float(match.group(1))
        return None
    
    def _pct_change(self, from_price: float, to_price: float) -> float:
        """Calculate percentage change"""
        return ((to_price - from_price) / from_price) * 100
    
    def start(self):
        """Start monitoring and processing threads"""
        if self.monitor_thread and self.monitor_thread.is_alive():
            logger.warning("Position manager already running")
            return
        
        self.stop_flag.clear()
        
        # Start price monitoring thread (fast polling)
        self.monitor_thread = threading.Thread(
            target=self._monitor_positions,
            daemon=True,
            name="PositionMonitor"
        )
        self.monitor_thread.start()
        
        # Start LLM processor thread (serial processing)
        self.processor_thread = threading.Thread(
            target=self._process_llm_queue,
            daemon=True,
            name="LLMProcessor"
        )
        self.processor_thread.start()
        
        logger.info(f"🚀 Position manager started (polling every {self.poll_interval}s)")
    
    def stop(self):
        """Stop all threads"""
        logger.info("🛑 Stopping position manager...")
        self.stop_flag.set()
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        if self.processor_thread:
            self.processor_thread.join(timeout=5)
        
        logger.info("✅ Position manager stopped")
    
    def _monitor_positions(self):
        """
        Background thread: Monitor positions for target hits.
        
        Runs FAST (every 15 seconds) because:
        - Local LLM = no API costs
        - Price checks are cheap
        - Fast reaction to stops is critical
        """
        logger.info(f"👁️ Monitoring started (checking every {self.poll_interval}s)")
        
        while not self.stop_flag.is_set():
            try:
                for symbol, targets in list(self.positions.items()):
                    # Get current market data
                    current_data = self._get_current_market_data(symbol)
                    
                    if not current_data:
                        continue
                    
                    current_price = current_data['price']
                    rsi = current_data.get('rsi')
                    volume_ratio = current_data.get('volume_ratio')
                    
                    # Update price extremes (for trailing stops)
                    targets.update_price_extremes(current_price)
                    targets.last_checked = datetime.now()
                    
                    # Check for triggered targets
                    triggered_events = targets.check_targets(current_price, rsi, volume_ratio)
                    
                    # Process triggered events
                    for event_type, priority, action_type in triggered_events:
                        event = TradingEvent(
                            event_type=event_type,
                            symbol=symbol,
                            timestamp=datetime.now(),
                            priority=priority,
                            action_type=action_type,
                            trigger_price=current_price,
                            trigger_details=current_data
                        )
                        
                        self.stats['events_triggered'] += 1
                        
                        # Route event based on action type
                        if action_type == EventAction.EXECUTE_IMMEDIATELY:
                            # Critical stops: immediate execution queue
                            self.immediate_actions.put(event)
                            logger.warning(f"🚨 IMMEDIATE: {symbol} - {event_type} @ ${current_price:.2f}")
                        else:
                            # Requires LLM: add to priority queue
                            self.llm_queue.submit(event)
                
                # Check market close safety (if LLM is down near close)
                self.check_market_close_safety()
                
                # Sleep until next check
                time.sleep(self.poll_interval)
                
            except Exception as e:
                logger.error(f"Error in position monitoring: {e}")
                time.sleep(self.poll_interval)
    
    def _process_llm_queue(self):
        """
        Background thread: Process LLM requests serially.
        
        LLM is BUSY with one request at a time, so:
        - Process queue in priority order
        - Handle immediate actions first
        - Track wait times
        """
        logger.info("🤖 LLM processor started")
        
        while not self.stop_flag.is_set():
            try:
                # Check for immediate actions first (critical stops)
                try:
                    immediate = self.immediate_actions.get(timeout=0.1)
                    self._execute_immediate_action(immediate)
                    self.stats['immediate_executions'] += 1
                    continue
                except queue.Empty:
                    pass
                
                # Process LLM queue (blocking with timeout)
                event = self.llm_queue.get_next(timeout=1)
                
                if event:
                    wait_time = (datetime.now() - event.timestamp).total_seconds()
                    logger.info(f"🤖 Processing: {event.symbol} - {event.event_type} (waited {wait_time:.1f}s)")
                    
                    # Mark as processing
                    self.llm_queue.mark_processing(event.symbol)
                    
                    # Check if LLM is healthy
                    if not self.llm_queue.is_llm_healthy() and event.action_type == EventAction.FALLBACK_AVAILABLE:
                        # LLM is down, execute fallback plan
                        logger.warning(f"⚠️ LLM unavailable, executing fallback for {event.symbol}")
                        self._execute_fallback_plan(event)
                        self.stats['fallback_executions'] += 1
                    else:
                        # This is where the LLM gets called (serial bottleneck)
                        success = self._process_event_with_llm(event)
                        
                        if success:
                            self.llm_queue.mark_llm_success()
                            self.stats['llm_consultations'] += 1
                        else:
                            self.llm_queue.mark_llm_failure()
                            # If LLM failed and fallback available, execute fallback
                            if event.action_type == EventAction.FALLBACK_AVAILABLE:
                                logger.warning(f"⚠️ LLM call failed, executing fallback for {event.symbol}")
                                self._execute_fallback_plan(event)
                                self.stats['fallback_executions'] += 1
                    
                    # Mark complete
                    self.llm_queue.mark_complete(event.symbol)
                    
                    # Update average wait time
                    if self.stats['llm_consultations'] > 0:
                        self.stats['avg_queue_wait'] = (
                            (self.stats['avg_queue_wait'] * (self.stats['llm_consultations'] - 1) + wait_time) /
                            self.stats['llm_consultations']
                        )
            
            except Exception as e:
                logger.error(f"Error in LLM processor: {e}")
                time.sleep(1)
    
    def _get_current_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current market data (price, RSI, volume).
        
        Fetches latest bar and calculates quick indicators.
        """
        if not self.alpaca:
            logger.warning("AlpacaClient not configured, cannot fetch market data")
            return None
        
        try:
            # Get recent bars for RSI calculation (need 14+ bars)
            from datetime import timedelta
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=20)
            
            bars = self.alpaca.get_bars(
                symbol=symbol,
                timeframe='1Min',
                start=start_time.isoformat(),
                end=end_time.isoformat(),
                limit=20
            )
            
            if bars.empty or len(bars) < 2:
                logger.debug(f"Not enough bars for {symbol}")
                return None
            
            # Get current price from latest bar
            current_price = float(bars['close'].iloc[-1])
            
            if current_price == 0:
                return None
            
            # Calculate volume ratio (current vs recent average)
            current_volume = float(bars['volume'].iloc[-1])
            avg_volume = float(bars['volume'].iloc[:-1].mean()) if len(bars) > 1 else current_volume
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            # Calculate RSI (if enough data)
            rsi = None
            if len(bars) >= 14:
                try:
                    # Simple RSI calculation
                    import pandas as pd
                    closes = bars['close']
                    delta = closes.diff()
                    
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    
                    rs = gain / loss
                    rsi = 100 - (100 / (1 + rs))
                    rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None
                except Exception as e:
                    logger.debug(f"RSI calculation failed for {symbol}: {e}")
            
            return {
                'price': current_price,
                'volume': current_volume,
                'volume_ratio': volume_ratio,
                'rsi': rsi,
                'timestamp': datetime.now(),
            }
            
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol}: {e}")
            return None
    
    def _execute_immediate_action(self, event: TradingEvent):
        """
        Execute critical action immediately (no LLM needed).
        
        Used for:
        - Stop loss hits
        - Trailing stop hits
        """
        logger.warning(f"⚡ EXECUTING IMMEDIATELY: {event.symbol} - {event.event_type}")
        
        if not self.trading_agent:
            logger.error("TradingAgent not configured, cannot execute trade")
            return
        
        # Execute the exit
        self._execute_exit(event.symbol, percent=100, reason=event.event_type)
        
        # Remove position from tracking
        if event.symbol in self.positions:
            targets = self.positions[event.symbol]
            pnl_pct = self._pct_change(targets.entry_price, event.trigger_price)
            logger.info(f"💰 {event.symbol} closed: {pnl_pct:+.2f}% (${event.trigger_price:.2f})")
            del self.positions[event.symbol]
    
    def _process_event_with_llm(self, event: TradingEvent) -> bool:
        """
        Process event with LLM consultation.
        
        This is the SERIAL BOTTLENECK - only one at a time!
        
        Returns:
            True if LLM call succeeded, False if failed
        """
        logger.info(f"🧠 Consulting LLM: {event.symbol} - {event.event_type}")
        
        if not self.llm_bridge:
            logger.error("LLMBridge not configured")
            return False
        
        try:
            # Get fresh analysis from LLM with timeout
            targets = self.positions.get(event.symbol)
            if not targets:
                logger.error(f"Position {event.symbol} not found for LLM analysis")
                return False
            
            # Prepare context for LLM
            context = {
                'event_type': event.event_type,
                'trigger_price': event.trigger_price,
                'entry_price': targets.entry_price,
                'current_pnl_pct': self._pct_change(targets.entry_price, event.trigger_price),
                'targets': {
                    'take_profit_1': targets.take_profit_1,
                    'take_profit_2': targets.take_profit_2,
                    'stop_loss': targets.stop_loss,
                    'trailing_stop': targets.trailing_stop,
                },
            }
            
            # Call LLM for fresh analysis (with timeout)
            # This would use your existing analyze_market method
            analysis = self.llm_bridge.analyze_market(
                symbol=event.symbol,
                signals=event.trigger_details,
                news=None,
                current_position={
                    'qty': targets.shares,
                    'avg_entry_price': targets.entry_price,
                    'current_price': event.trigger_price,
                }
            )
            
            if not analysis:
                logger.error(f"LLM returned no analysis for {event.symbol}")
                return False
            
            # Process LLM decision
            action = analysis.get('action', 'hold')
            confidence = analysis.get('confidence', 0)
            reasoning = analysis.get('reasoning', '')
            
            logger.info(f"🧠 LLM decision: {action.upper()} (confidence: {confidence}%)")
            logger.info(f"   Reasoning: {reasoning[:100]}...")
            
            # Execute based on LLM recommendation
            if action == 'sell':
                self._execute_exit(event.symbol, percent=100, reason=f"LLM: {event.event_type}")
            elif action == 'hold':
                # Update targets if needed based on analysis
                logger.info(f"   ⏸️ LLM recommends HOLD, no action")
                # Could adjust trailing stop here if analysis suggests it
                if event.event_type == "TAKE_PROFIT_1" and not targets.trailing_stop_active:
                    targets.trailing_stop_active = True
                    logger.info(f"   📊 Activated trailing stop")
            
            event.llm_processed = True
            event.llm_decision = analysis
            
            return True
            
        except TimeoutError:
            logger.error(f"⏱️ LLM timeout for {event.symbol} after {self.llm_queue.llm_timeout}s")
            return False
        except Exception as e:
            logger.error(f"❌ LLM error for {event.symbol}: {e}")
            return False
    
    def _execute_fallback_plan(self, event: TradingEvent):
        """
        Execute predefined fallback plan when LLM is unavailable.
        
        Fallback plans are conservative and ensure we:
        1. Protect profits (exit at take profit levels)
        2. Limit losses (respect stops)
        3. Don't hold overnight if LLM is down
        """
        symbol = event.symbol
        targets = self.positions.get(symbol)
        
        if not targets:
            logger.warning(f"⚠️ Cannot execute fallback: {symbol} position not found")
            return
        
        event.fallback_executed = True
        event.fallback_reason = f"LLM unavailable: {event.event_type}"
        
        action = None
        reason = None
        
        # Determine fallback action based on event type
        if event.event_type == "TAKE_PROFIT_2":
            # TP2 hit: Default to FULL EXIT (lock in profits)
            action = targets.fallback_on_tp2
            reason = f"TP2 reached (${event.trigger_price:.2f}), LLM down - executing {action}"
        
        elif event.event_type == "TAKE_PROFIT_1":
            # TP1 hit: Default to PARTIAL EXIT or TRAIL STOP
            action = targets.fallback_on_tp1
            reason = f"TP1 reached (${event.trigger_price:.2f}), LLM down - executing {action}"
        
        elif event.event_type == "RSI_OVERBOUGHT":
            # RSI high: Default to FULL EXIT (avoid reversal)
            action = targets.fallback_on_rsi_high
            reason = f"RSI overbought, LLM down - executing {action}"
        
        else:
            logger.warning(f"⚠️ No fallback plan for {event.event_type}, defaulting to HOLD")
            return
        
        # Execute the fallback action
        logger.warning(f"🔄 FALLBACK: {symbol} - {reason}")
        
        if action == "FULL_EXIT":
            self._execute_exit(symbol, percent=100, reason=f"Fallback: {event.event_type}")
        
        elif action == "PARTIAL_EXIT":
            # Exit 50% of position
            self._execute_exit(symbol, percent=50, reason=f"Fallback: {event.event_type} (partial)")
            # Activate trailing stop for remaining position
            targets.trailing_stop_active = True
            targets.take_profit_1_hit = True
            logger.info(f"   📊 Trailing stop activated for remaining 50%")
        
        elif action == "TRAIL_STOP":
            # Just activate trailing stop
            targets.trailing_stop_active = True
            targets.take_profit_1_hit = True
            logger.info(f"   📊 Trailing stop activated")
        
        elif action == "HOLD":
            # Do nothing, just log
            logger.info(f"   ⏸️ Fallback plan is HOLD, no action taken")
    
    def _execute_exit(self, symbol: str, percent: int = 100, reason: str = ""):
        """
        Execute position exit (full or partial) via AlpacaClient.
        
        Args:
            symbol: Stock symbol
            percent: Percentage of position to exit (50 or 100)
            reason: Reason for exit (for logging)
        """
        if symbol not in self.positions:
            logger.warning(f"⚠️ Cannot exit {symbol}: position not found")
            return
        
        targets = self.positions[symbol]
        
        logger.warning(f"💰 EXITING {percent}% of {symbol}: {reason}")
        
        if not self.alpaca:
            logger.error("AlpacaClient not configured, cannot execute exit")
            return
        
        # Calculate shares to sell
        shares_to_sell = int(targets.shares * (percent / 100))
        if shares_to_sell <= 0:
            logger.warning(f"Cannot exit {symbol}: calculated shares = {shares_to_sell}")
            return
        
        try:
            # Get current price for P&L estimation
            current_price = targets.highest_price_seen  # Fallback
            try:
                bars = self.alpaca.get_bars(
                    symbol=symbol,
                    timeframe='1Min',
                    start=(datetime.now() - timedelta(minutes=5)).isoformat(),
                    end=datetime.now().isoformat(),
                    limit=1
                )
                if not bars.empty:
                    current_price = bars['close'].iloc[-1]
            except Exception as e:
                logger.warning(f"Could not get current price for {symbol}: {e}")
            
            # Calculate estimated P&L before execution
            pnl_pct = self._pct_change(targets.entry_price, current_price)
            logger.info(f"   Entry: ${targets.entry_price:.2f}")
            logger.info(f"   Current: ${current_price:.2f} (Est. P&L: {pnl_pct:+.2f}%)")
            
            # Place market sell order
            order = self.alpaca.place_market_order(
                symbol=symbol,
                qty=shares_to_sell,
                side='sell'
            )
            
            if not order:
                logger.error(f"❌ Failed to place sell order for {symbol}")
                return
            
            order_id = order['id']
            logger.info(f"📤 Sell order placed: {order_id}")
            
            # Wait for order to fill (up to 30 seconds)
            final_order = self.alpaca.wait_for_order_fill(order_id, timeout_seconds=30)
            
            if final_order and final_order['status'] == 'filled':
                fill_price = final_order['filled_avg_price']
                actual_pnl_pct = self._pct_change(targets.entry_price, fill_price)
                
                logger.info(f"✅ Order filled @ ${fill_price:.2f}")
                logger.info(f"   Actual P&L: {actual_pnl_pct:+.2f}%")
                
                # Update position tracking
                if percent >= 100:
                    # Full exit - remove position
                    logger.info(f"🎯 Position CLOSED: {symbol}")
                    del self.positions[symbol]
                    
                    # CRITICAL: Also remove from TradingAgent positions to keep in sync
                    if self.trading_agent and hasattr(self.trading_agent, 'positions'):
                        if symbol in self.trading_agent.positions:
                            del self.trading_agent.positions[symbol]
                            logger.debug(f"   Synced: Removed {symbol} from TradingAgent positions")
                else:
                    # Partial exit - reduce shares
                    targets.shares -= shares_to_sell
                    logger.info(f"📉 Position reduced: {symbol} ({targets.shares} shares remaining)")
                    
            else:
                status = final_order['status'] if final_order else 'timeout'
                logger.error(f"❌ Order not filled: {status}")
                
        except Exception as e:
            logger.error(f"❌ Error executing exit for {symbol}: {e}")
    
    def check_market_close_safety(self):
        """
        Pre-market close safety check.
        
        If LLM is still down X minutes before close, force exit all positions
        to avoid holding overnight without ability to manage risk.
        """
        if not self.market_close_time:
            return
        
        now = datetime.now()
        time_to_close = (self.market_close_time - now).total_seconds() / 60  # minutes
        
        # If we're within safety window and LLM is down
        if time_to_close <= self.pre_close_safety_minutes and not self.llm_queue.is_llm_healthy():
            logger.error(f"🚨 EMERGENCY: {time_to_close:.0f} min to close, LLM still down!")
            logger.error(f"🚨 Executing EMERGENCY EXIT of all positions")
            
            # Force exit ALL positions
            for symbol in list(self.positions.keys()):
                self._execute_exit(
                    symbol, 
                    percent=100, 
                    reason=f"EMERGENCY: LLM down {self.pre_close_safety_minutes}min before close"
                )
            
            logger.error(f"🚨 All positions closed for safety")
    
    def set_market_close_time(self, close_time: datetime):
        """Set market close time for safety checks"""
        self.market_close_time = close_time
        logger.info(f"📅 Market close time set: {close_time.strftime('%H:%M')}")
    
    def scan_for_opportunities(self, candidate_symbols: List[str]) -> List[str]:
        """
        Scan universe for NEW position opportunities.
        
        This is the ENTRY scanner - runs less frequently than monitoring.
        Recommended: Run every 1-2 hours when positions < max_positions.
        
        Args:
            candidate_symbols: List of symbols to scan
        
        Returns:
            List of symbols that passed screening
        """
        if len(self.positions) >= self.max_positions:
            logger.info(f"Position limit reached ({self.max_positions}), skipping scan")
            return []
        
        if not self.llm_bridge:
            logger.warning("LLMBridge not configured, cannot scan for opportunities")
            return []
        
        logger.info(f"🔍 Scanning {len(candidate_symbols)} symbols for opportunities...")
        
        opportunities = []
        
        for symbol in candidate_symbols:
            # Skip if already in position
            if symbol in self.positions:
                continue
            
            try:
                # Get market data
                bars = self.alpaca.get_bars(
                    symbol=symbol,
                    timeframe='1Day',
                    start=(datetime.now() - timedelta(days=30)).isoformat(),
                    end=datetime.now().isoformat(),
                    limit=30
                )
                
                if bars.empty:
                    continue
                
                # Calculate indicators
                from wawatrader.indicators import analyze_dataframe, get_latest_signals
                df_with_indicators = analyze_dataframe(bars)
                signals = get_latest_signals(df_with_indicators)
                
                if not signals:
                    continue
                
                # Quick technical filter (before LLM)
                # Only consider if:
                # 1. Price above 20-day SMA
                # 2. RSI between 40-60 (not overbought/oversold)
                # 3. Volume above average
                
                price = signals['price']['close']
                sma_20 = df_with_indicators['SMA_20'].iloc[-1] if 'SMA_20' in df_with_indicators else price
                rsi = signals.get('momentum', {}).get('rsi', 50)
                volume_ratio = signals.get('volume', {}).get('volume_ratio', 1.0)
                
                # Technical filter
                if price < sma_20:
                    logger.debug(f"   ❌ {symbol}: Price below SMA_20")
                    continue
                if not (40 <= rsi <= 60):
                    logger.debug(f"   ❌ {symbol}: RSI {rsi:.1f} outside 40-60 range")
                    continue
                if volume_ratio < 0.8:
                    logger.debug(f"   ❌ {symbol}: Low volume ({volume_ratio:.2f}x avg)")
                    continue
                
                # Passed technical filter - add to opportunities
                logger.info(f"   ✅ {symbol}: Passed technical filter (RSI={rsi:.1f}, Vol={volume_ratio:.2f}x)")
                opportunities.append(symbol)
                
            except Exception as e:
                logger.warning(f"   ⚠️ Error scanning {symbol}: {e}")
                continue
        
        if opportunities:
            logger.info(f"🎯 Found {len(opportunities)} opportunities: {', '.join(opportunities)}")
        else:
            logger.info(f"🔍 No opportunities found")
        
        return opportunities
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status and statistics"""
        return {
            'active_positions': len(self.positions),
            'max_positions': self.max_positions,
            'llm_queue_depth': self.llm_queue.get_queue_depth(),
            'immediate_queue_depth': self.immediate_actions.qsize(),
            'stats': self.stats.copy(),
        }
