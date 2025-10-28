# Event-Driven Trading System Proposal
## Replacing Fixed-Time Cycles with Smart Triggers

---

## 🎯 **Core Concept**

Instead of checking positions every X minutes, the system **sleeps** until a meaningful event occurs, then wakes up to make a decision.

### **Event Types**
1. **Price Targets Hit** - Take profit or stop loss levels reached
2. **Technical Flags** - RSI extremes, MACD crossover, volume spike
3. **Time-Based** - Held for N days (optional soft limit)
4. **News Events** - Breaking news about the stock
5. **Market Events** - Broad market crash/rally (VIX spike, SPY -2%)

---

## 🏗️ **Proposed Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                    Position Manager                          │
│  - Tracks up to 10 active positions                         │
│  - Each position has PositionTargets object                  │
│  - Monitors market data stream for trigger events            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
         ┌────────────────────────────────────────┐
         │         Event Monitor Thread            │
         │  - Subscribes to price feeds            │
         │  - Checks targets every 1 minute        │
         │  - Fires events when targets hit        │
         └────────────────────────────────────────┘
                              │
                              ▼
         ┌────────────────────────────────────────┐
         │         Event Queue                     │
         │  - FIFO queue of triggered events       │
         │  - Prioritized by urgency               │
         └────────────────────────────────────────┘
                              │
                              ▼
         ┌────────────────────────────────────────┐
         │      Decision Engine (LLM)              │
         │  - Processes ONE event at a time        │
         │  - Gets fresh data for THAT symbol      │
         │  - Makes decision: adjust/hold/exit     │
         └────────────────────────────────────────┘
```

---

## 💾 **Data Structures**

### **1. PositionTargets** (per position)
```python
@dataclass
class PositionTargets:
    """Smart targets and flags for a position"""
    
    # Basic info
    symbol: str
    entry_price: float
    entry_time: datetime
    shares: int
    
    # Price targets (dynamic)
    take_profit_1: float      # First profit target (e.g., +3%)
    take_profit_2: float      # Second target (e.g., +6%)
    stop_loss: float          # Hard stop (e.g., -2%)
    trailing_stop: float      # Trailing stop distance (e.g., -1.5% from peak)
    
    # Technical flags
    rsi_exit_threshold: float = 75.0   # Exit if RSI > 75 (overbought)
    volume_alert: float = 2.0          # Alert if volume > 2x average
    
    # Tracking
    highest_price: float      # For trailing stop
    last_checked: datetime
    
    # Status
    active_alerts: List[str]  # ["RSI_HIGH", "VOLUME_SPIKE"]
    
    def update_trailing_stop(self, current_price: float):
        """Update trailing stop if price moved higher"""
        if current_price > self.highest_price:
            self.highest_price = current_price
            self.trailing_stop = current_price * 0.985  # -1.5%
    
    def check_targets(self, current_price: float, rsi: float, volume_ratio: float) -> List[str]:
        """Check if any targets/flags triggered"""
        triggered = []
        
        # Price targets
        if current_price >= self.take_profit_1:
            triggered.append("TAKE_PROFIT_1")
        if current_price >= self.take_profit_2:
            triggered.append("TAKE_PROFIT_2")
        if current_price <= self.stop_loss:
            triggered.append("STOP_LOSS")
        if current_price <= self.trailing_stop:
            triggered.append("TRAILING_STOP")
        
        # Technical flags
        if rsi > self.rsi_exit_threshold:
            triggered.append("RSI_OVERBOUGHT")
        if volume_ratio > self.volume_alert:
            triggered.append("VOLUME_SPIKE")
        
        return triggered
```

### **2. TradingEvent**
```python
@dataclass
class TradingEvent:
    """Represents an event that requires decision"""
    
    event_type: str           # "STOP_LOSS", "TAKE_PROFIT", "RSI_FLAG", etc.
    symbol: str
    timestamp: datetime
    priority: int             # 1=critical (stop loss), 2=high, 3=normal
    
    # Context
    current_price: float
    trigger_details: Dict[str, Any]
    
    def __lt__(self, other):
        """For priority queue sorting"""
        return self.priority < other.priority
```

### **3. PositionManager**
```python
class PositionManager:
    """Manages active positions with event-driven monitoring"""
    
    def __init__(self, max_positions: int = 10):
        self.max_positions = max_positions
        self.positions: Dict[str, PositionTargets] = {}  # symbol -> targets
        self.event_queue: PriorityQueue[TradingEvent] = PriorityQueue()
        self.monitoring_thread: Optional[Thread] = None
        self.stop_monitoring = threading.Event()
    
    def open_position(self, symbol: str, entry_price: float, shares: int, 
                     analysis: Dict[str, Any]) -> PositionTargets:
        """
        Open new position with smart targets based on analysis.
        
        Targets are calculated from:
        - Technical levels (support/resistance from LLM analysis)
        - Volatility (ATR-based stop loss)
        - Risk/reward ratio (2:1 minimum)
        """
        if len(self.positions) >= self.max_positions:
            raise PositionLimitError(f"Already have {self.max_positions} positions")
        
        # Calculate smart targets from analysis
        targets = self._calculate_targets(symbol, entry_price, analysis)
        
        self.positions[symbol] = targets
        logger.info(f"📍 Opened position: {symbol}")
        logger.info(f"   Entry: ${entry_price:.2f}")
        logger.info(f"   Take Profit 1: ${targets.take_profit_1:.2f} (+{((targets.take_profit_1/entry_price)-1)*100:.1f}%)")
        logger.info(f"   Take Profit 2: ${targets.take_profit_2:.2f} (+{((targets.take_profit_2/entry_price)-1)*100:.1f}%)")
        logger.info(f"   Stop Loss: ${targets.stop_loss:.2f} ({((targets.stop_loss/entry_price)-1)*100:.1f}%)")
        
        return targets
    
    def _calculate_targets(self, symbol: str, entry_price: float, 
                          analysis: Dict[str, Any]) -> PositionTargets:
        """
        Calculate intelligent targets based on:
        1. LLM-provided price targets (if available)
        2. Technical support/resistance levels
        3. ATR-based volatility (for stop loss)
        4. Risk/reward ratio (minimum 2:1)
        """
        signals = analysis.get('signals', {})
        llm_analysis = analysis.get('llm_analysis', {})
        
        # Extract from LLM if available (e.g., "Target $265 (+6%), stop $245 (-2%)")
        reasoning = llm_analysis.get('reasoning', '')
        llm_target = self._extract_price_target(reasoning)
        llm_stop = self._extract_stop_loss(reasoning)
        
        # Calculate volatility-based stop (ATR method)
        atr = signals.get('volatility', {}).get('atr', 0)
        if atr > 0:
            atr_stop = entry_price - (2 * atr)  # 2 ATR stop loss
        else:
            atr_stop = entry_price * 0.98  # Default -2%
        
        # Use LLM stop if available, otherwise ATR
        stop_loss = llm_stop if llm_stop else max(atr_stop, entry_price * 0.98)
        
        # Calculate profit targets (2:1 and 3:1 risk/reward)
        risk = entry_price - stop_loss
        take_profit_1 = entry_price + (risk * 2)  # 2R
        take_profit_2 = entry_price + (risk * 3)  # 3R
        
        # Override with LLM target if more conservative
        if llm_target and llm_target < take_profit_2:
            take_profit_1 = entry_price + (llm_target - entry_price) * 0.5
            take_profit_2 = llm_target
        
        return PositionTargets(
            symbol=symbol,
            entry_price=entry_price,
            entry_time=datetime.now(),
            shares=1,  # Placeholder
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            stop_loss=stop_loss,
            trailing_stop=entry_price * 0.985,
            highest_price=entry_price,
            last_checked=datetime.now(),
            active_alerts=[]
        )
    
    def start_monitoring(self):
        """Start background thread that monitors positions"""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            return
        
        self.stop_monitoring.clear()
        self.monitoring_thread = threading.Thread(
            target=self._monitor_positions,
            daemon=True,
            name="PositionMonitor"
        )
        self.monitoring_thread.start()
        logger.info("🔍 Position monitoring started")
    
    def _monitor_positions(self):
        """
        Background thread that checks positions every 1 minute.
        
        NOTE: Checking every minute is cheap (no LLM calls).
        We only call LLM when targets are actually hit.
        """
        while not self.stop_monitoring.is_set():
            try:
                for symbol, targets in self.positions.items():
                    # Get current market data (cheap API call)
                    current_data = self._get_current_data(symbol)
                    
                    if not current_data:
                        continue
                    
                    # Check targets
                    triggered = targets.check_targets(
                        current_price=current_data['price'],
                        rsi=current_data.get('rsi', 50),
                        volume_ratio=current_data.get('volume_ratio', 1.0)
                    )
                    
                    # Create events for triggered targets
                    for trigger in triggered:
                        priority = self._get_priority(trigger)
                        event = TradingEvent(
                            event_type=trigger,
                            symbol=symbol,
                            timestamp=datetime.now(),
                            priority=priority,
                            current_price=current_data['price'],
                            trigger_details=current_data
                        )
                        self.event_queue.put(event)
                        logger.info(f"🚨 Event triggered: {symbol} - {trigger} @ ${current_data['price']:.2f}")
                    
                    # Update trailing stop
                    targets.update_trailing_stop(current_data['price'])
                
                # Sleep for 1 minute (cheap monitoring)
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in position monitoring: {e}")
                time.sleep(60)
    
    def _get_priority(self, trigger: str) -> int:
        """Assign priority to event types"""
        priorities = {
            'STOP_LOSS': 1,        # Critical: immediate exit
            'TRAILING_STOP': 1,    # Critical: immediate exit
            'TAKE_PROFIT_2': 2,    # High: strong signal to exit
            'RSI_OVERBOUGHT': 2,   # High: consider exiting
            'TAKE_PROFIT_1': 3,    # Normal: partial exit or trail
            'VOLUME_SPIKE': 3,     # Normal: awareness
        }
        return priorities.get(trigger, 3)
```

---

## 🔄 **Main Trading Loop**

```python
class EventDrivenTradingAgent:
    """Event-driven trading with smart position management"""
    
    def __init__(self):
        self.position_manager = PositionManager(max_positions=10)
        self.llm_bridge = LLMBridge()
        self.alpaca = AlpacaClient()
        
        # Opportunity scanner runs periodically (only for NEW positions)
        self.scanner_interval = 60  # Check for new opportunities every hour
    
    def run(self):
        """Main event-driven loop"""
        logger.info("🚀 Starting event-driven trading system")
        
        # Start position monitoring
        self.position_manager.start_monitoring()
        
        # Main loop: Process events + scan for new opportunities
        last_scan = datetime.now()
        
        while True:
            try:
                # 1. Process triggered events (blocking with timeout)
                try:
                    event = self.position_manager.event_queue.get(timeout=60)
                    self._process_event(event)
                except queue.Empty:
                    pass  # No events, continue
                
                # 2. Scan for new opportunities (only if positions < 10)
                if (datetime.now() - last_scan).seconds >= self.scanner_interval * 60:
                    if len(self.position_manager.positions) < 10:
                        self._scan_for_opportunities()
                    last_scan = datetime.now()
                
                # 3. Check market hours (sleep overnight)
                if not self._is_market_open():
                    logger.info("💤 Market closed, sleeping...")
                    time.sleep(3600)  # Check again in 1 hour
                
            except KeyboardInterrupt:
                logger.info("🛑 Shutting down...")
                self.position_manager.stop_monitoring.set()
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(60)
    
    def _process_event(self, event: TradingEvent):
        """
        Process a triggered event.
        
        This is the ONLY place we call the LLM for position management.
        Only called when something actually changed.
        """
        logger.info(f"⚡ Processing event: {event.symbol} - {event.event_type}")
        
        # Get fresh analysis (LLM call)
        analysis = self._analyze_position(event.symbol, event)
        
        # Decide action based on event type and LLM recommendation
        if event.event_type in ['STOP_LOSS', 'TRAILING_STOP']:
            # Critical stops: execute immediately
            self._exit_position(event.symbol, reason=event.event_type)
        
        elif event.event_type == 'TAKE_PROFIT_2':
            # Strong profit signal: likely exit
            if analysis['action'] in ['sell', 'hold']:
                self._exit_position(event.symbol, reason="TAKE_PROFIT_2")
            else:
                # LLM says keep going, adjust trailing stop tighter
                self._tighten_trailing_stop(event.symbol)
        
        elif event.event_type == 'TAKE_PROFIT_1':
            # First profit target: partial exit or tighten stops
            if analysis['action'] == 'sell':
                self._partial_exit(event.symbol, percent=50)
            self._tighten_trailing_stop(event.symbol)
        
        elif event.event_type == 'RSI_OVERBOUGHT':
            # Technical warning: consider exit
            if analysis['action'] == 'sell':
                self._exit_position(event.symbol, reason="RSI_OVERBOUGHT")
        
        else:
            # Other events: informational, update targets if needed
            self._update_targets_from_analysis(event.symbol, analysis)
    
    def _scan_for_opportunities(self):
        """
        Scan universe for new positions (only when < 10 positions).
        
        This is LESS FREQUENT than old system (every 1-2 hours vs every 5-20 min).
        """
        logger.info("🔍 Scanning for new opportunities...")
        
        available_slots = 10 - len(self.position_manager.positions)
        if available_slots == 0:
            return
        
        # Get watchlist
        candidates = self._get_candidates()
        
        # Analyze top candidates (use LLM budget wisely)
        for symbol in candidates[:available_slots * 2]:  # Analyze 2x slots
            analysis = self._analyze_symbol(symbol)
            
            if analysis['action'] == 'buy' and analysis['confidence'] >= 75:
                # Strong buy signal: open position
                self._open_new_position(symbol, analysis)
                
                if len(self.position_manager.positions) >= 10:
                    break  # Full, stop scanning
```

---

## 📊 **Comparison: Old vs New**

### **LLM Usage**
| Scenario | Old System | New System | Savings |
|----------|-----------|-----------|---------|
| 5 positions, no events | 5 calls/20min = **15/hour** | 0 calls | **100%** |
| 1 stop loss hit | Background | 1 call | 0% |
| Daily total (5 pos) | ~100-150 calls | ~10-20 calls | **85-90%** |

### **Reaction Time**
| Event | Old System | New System | Improvement |
|-------|-----------|-----------|-------------|
| Stop loss hit | Up to 20 min | ~1 minute | **20x faster** |
| Take profit reached | Up to 20 min | ~1 minute | **20x faster** |
| News breaks | Next cycle | Real-time* | Immediate |

*With news webhook integration (future enhancement)

### **Flexibility**
| Feature | Old System | New System |
|---------|-----------|-----------|
| Hold time | Fixed 2-hour min | Natural (exit on conditions) |
| Per-stock logic | Same for all | Custom targets per position |
| Position limit | None | 10 (smart) |
| Target adjustment | Manual | Automatic (trailing stops) |

---

## 🎯 **Implementation Plan**

### **Phase 1: Core Infrastructure** (2-3 days)
- [ ] Create `PositionTargets` dataclass
- [ ] Create `PositionManager` class
- [ ] Implement background monitoring thread
- [ ] Build event queue system

### **Phase 2: Integration** (2-3 days)
- [ ] Modify `trading_agent.py` to use `PositionManager`
- [ ] Add target calculation logic
- [ ] Integrate event processing
- [ ] Update `execute_decision()` to set targets on entry

### **Phase 3: Testing** (1-2 days)
- [ ] Unit tests for target calculations
- [ ] Test event triggering with historical data
- [ ] Validate LLM call reduction
- [ ] Paper trade for 2-3 days

### **Phase 4: Enhancements** (optional)
- [ ] Add news webhook integration
- [ ] Implement partial exits (scale out)
- [ ] Add position sizing based on volatility
- [ ] Create dashboard for active targets

---

## 🚨 **Risks & Mitigations**

### **Risk 1: Missed Events**
**Problem**: What if monitoring thread crashes?  
**Mitigation**: 
- Supervisor thread that restarts monitoring
- Fallback: Daily health check at 3 PM
- Alert if no monitoring for 10 minutes

### **Risk 2: False Triggers**
**Problem**: Noise in 1-minute data causes too many events  
**Mitigation**:
- Require target breach for 2 consecutive checks (2-minute confirmation)
- Use ATR-based buffers around targets
- Exponential backoff on repeated triggers

### **Risk 3: No Positions**
**Problem**: System finds nothing to buy, sits idle  
**Mitigation**:
- Scanner runs every 1-2 hours regardless
- Relaxed criteria when 0 positions (lower confidence threshold)
- Can manually add to watchlist

### **Risk 4: Market Gaps**
**Problem**: Stop loss gapped through overnight  
**Mitigation**:
- Pre-close check at 3:55 PM (exit risky positions)
- After-hours monitoring (if supported by API)
- Accept that gaps happen (part of trading)

---

## 💡 **Key Benefits**

1. **90% fewer LLM calls** - Only query when needed, not on schedule
2. **Faster exits** - React in ~1 minute vs up to 20 minutes
3. **Smarter holds** - No artificial time limits, exit on conditions
4. **Per-stock intelligence** - Custom targets based on each stock's behavior
5. **Budget-aware** - 10 position limit respects LLM quota
6. **Natural trading** - Mimics how humans trade (set orders, walk away)

---

## ✅ **Recommendation**

**YES, implement event-driven approach.** It's superior in every way:

1. ✅ Respects LLM budget (10 positions manageable)
2. ✅ More intelligent (custom targets per stock)
3. ✅ Faster reactions (critical for stops)
4. ✅ Less friction (natural hold times)
5. ✅ Scales better (adding positions doesn't linearly increase LLM calls)

**Suggested Timeline**:
- Week 1: Build infrastructure (PositionManager, events)
- Week 2: Integration & testing
- Week 3: Paper trading validation
- Week 4: Production deployment

This is a **fundamental architecture improvement**, not just a parameter tweak. Worth the investment! 🚀
