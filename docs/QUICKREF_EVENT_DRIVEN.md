# 🔧 Quick Reference: Using Event-Driven Components
**For Developers Integrating the New Architecture**

---

## 🎯 Quick Start

### 1. Store a Trading Decision

```python
from wawatrader.decision_memory import DecisionMemory, DecisionType, get_memory_store
from datetime import datetime

# Get memory store (singleton)
memory = get_memory_store()

# Create entry decision
decision = DecisionMemory(
    decision_id="unique_id_123",
    symbol="AAPL",
    timestamp=datetime.now(),
    decision_type=DecisionType.ENTRY,
    
    # Strategy
    strategy="momentum_breakout",
    
    # Thesis
    thesis="Strong breakout above $180 with earnings catalyst",
    catalysts=["Earnings beat", "Sector rotation"],
    bullish_factors=["Volume spike", "RSI strength"],
    bearish_factors=["Market weak"],
    
    # Risk management
    entry_price=180.50,
    target_price=192.00,
    stop_loss_price=175.00,
    expected_holding_period="swing (2-5 days)",
    invalidation_conditions=["Break $175", "Volume dries up"],
    
    # Position details
    shares=50,
    position_size_usd=9025.00,
    position_size_pct=9.0,
    conviction_score=75,
    kelly_fraction=0.08
)

# Store it
memory.store(decision)
```

### 2. Retrieve Position for Re-evaluation

```python
from wawatrader.decision_memory import get_memory_store, ThesisRealityComparator

memory = get_memory_store()
comparator = ThesisRealityComparator(memory)

# Get comparison
comparison = comparator.get_comparison(
    symbol="AAPL",
    current_price=186.50,
    current_data={
        'news': [{'headline': '...', 'sentiment': 0.8}],
        'volume_analysis': {'ratio': 1.5},
        'price_action': {'trend': 'bullish'}
    }
)

# Generate LLM prompt
prompt = comparator.build_reeval_prompt(
    symbol="AAPL",
    current_price=186.50,
    current_data=current_data,
    trigger_event="VOLUME_SPIKE: 2.5x average"
)

# Send prompt to LLM...
```

### 3. Add Events to Queue

```python
from wawatrader.event_system import get_event_queue, Event, EventType, EventPriority
from datetime import datetime
import uuid

queue = get_event_queue()

# Create event
event = Event(
    id=str(uuid.uuid4()),
    timestamp=datetime.now(),
    event_type=EventType.BREAKOUT_UPSIDE,
    symbol="AAPL",
    data={'current_price': 185.00, 'resistance': 183.00},
    priority=EventPriority.URGENT,
    source="PriceMonitor"
)

# Add to queue
queue.add_event(event)
```

### 4. Process Event Queue

```python
from wawatrader.event_system import get_event_queue

queue = get_event_queue()

# Get next event (highest priority, FIFO within priority)
event = queue.get_next_event()

if event:
    print(f"Processing: {event.event_type.value} for {event.symbol}")
    # Handle the event...
```

### 5. Set Price Alerts

```python
from wawatrader.event_system import PriceAlertMonitor, get_event_queue, EventType, EventPriority

queue = get_event_queue()
monitor = PriceAlertMonitor(queue)

# Set alert for target
monitor.set_price_alert(
    symbol="AAPL",
    alert_type="above",
    price=192.00,
    event_type=EventType.TARGET_HIT,
    priority=EventPriority.MEDIUM_HIGH,
    metadata={'target_level': 'first_target'}
)

# Set alert for stop loss
monitor.set_price_alert(
    symbol="AAPL",
    alert_type="below",
    price=175.00,
    event_type=EventType.STOP_LOSS_HIT,
    priority=EventPriority.CRITICAL,
    metadata={'stop_type': 'invalidation'}
)

# Check price (call this when new price data arrives)
monitor.check_price("AAPL", current_price=191.00)
# This will add TARGET_HIT event to queue if price > 192
```

### 6. Calculate Position Size

```python
from wawatrader.position_sizing import KellyLLMPositionSizer
from wawatrader.decision_memory import get_memory_store

memory = get_memory_store()
sizer = KellyLLMPositionSizer(memory)

# Calculate position size
position = sizer.calculate_position_size(
    symbol="NVDA",
    entry_price=450.00,
    strategy="momentum_breakout",
    llm_conviction=80,  # 0-100
    portfolio_value=100_000.00,
    existing_positions=[
        {'symbol': 'AAPL', 'value': 15000, 'sector': 'Technology'},
        {'symbol': 'JPM', 'value': 10000, 'sector': 'Financial'}
    ],
    sector_map={'NVDA': 'Technology', 'AAPL': 'Technology', 'JPM': 'Financial'}
)

print(f"Position Size: ${position.final_position_usd:,.0f} ({position.final_position_pct:.2f}%)")
print(f"Shares: {position.shares}")
print(position.reasoning)
```

### 7. Check Risk Limits

```python
from wawatrader.position_sizing import PortfolioRiskManager

risk_manager = PortfolioRiskManager()

# Check if trade is allowed
can_trade, warnings = risk_manager.check_risk_limits(
    proposed_trade={'symbol': 'GOOGL', 'size_usd': 18000},
    portfolio_value=100_000.00,
    existing_positions=[...],
    sector_map={...}
)

if can_trade:
    print("✅ Trade approved")
else:
    print("❌ Trade blocked:")
    for warning in warnings:
        print(f"  {warning}")
```

---

## 🔄 Integration with TradingAgent

### Main Trading Loop (Event-Driven)

```python
from wawatrader.event_system import get_event_queue
from wawatrader.decision_memory import get_memory_store, ThesisRealityComparator
from wawatrader.position_sizing import KellyLLMPositionSizer

class TradingAgent:
    def __init__(self):
        self.event_queue = get_event_queue()
        self.memory = get_memory_store()
        self.comparator = ThesisRealityComparator(self.memory)
        self.sizer = KellyLLMPositionSizer(self.memory)
        self.price_monitor = PriceAlertMonitor(self.event_queue)
    
    async def run_event_driven_loop(self):
        """Main event-driven trading loop"""
        while True:
            # Get next event
            event = self.event_queue.get_next_event()
            
            if event:
                await self.handle_event(event)
            else:
                # No events, wait a bit
                await asyncio.sleep(1)
    
    async def handle_event(self, event):
        """Handle a single event"""
        logger.info(f"📬 Processing: {event.event_type.value} for {event.symbol}")
        
        # Check if we have existing position
        existing = self.memory.get_open_position(event.symbol)
        
        if existing:
            # Re-evaluation flow
            await self.reevaluate_position(event, existing)
        else:
            # New opportunity flow
            await self.evaluate_new_opportunity(event)
    
    async def reevaluate_position(self, event, memory):
        """Re-evaluate existing position with thesis vs reality"""
        
        # Get current data
        current_data = self.get_current_market_data(event.symbol)
        current_price = current_data['price']
        
        # Build comparison
        comparison = self.comparator.get_comparison(
            symbol=event.symbol,
            current_price=current_price,
            current_data=current_data
        )
        
        # Build prompt with thesis vs reality
        prompt = self.comparator.build_reeval_prompt(
            symbol=event.symbol,
            current_price=current_price,
            current_data=current_data,
            trigger_event=f"{event.event_type.value}: {event.data}"
        )
        
        # Get LLM decision
        llm_response = await self.llm_bridge.analyze(prompt)
        
        # Parse response
        if llm_response['action'] == 'exit':
            await self.exit_position(event.symbol, llm_response)
        elif llm_response['action'] == 'hold':
            # Add revisit to memory
            self.memory.add_revisit(event.symbol, {
                'action': 'hold',
                'reasoning': llm_response['reasoning'],
                'price': current_price,
                'thesis_still_valid': llm_response.get('thesis_still_valid', True)
            })
        # ... handle other actions
    
    async def evaluate_new_opportunity(self, event):
        """Evaluate new trading opportunity"""
        
        # Get market data
        data = self.get_current_market_data(event.symbol)
        
        # Get LLM analysis
        llm_response = await self.llm_bridge.analyze_for_entry(event.symbol, data)
        
        if llm_response['action'] == 'buy':
            # Calculate position size
            position = self.sizer.calculate_position_size(
                symbol=event.symbol,
                entry_price=data['price'],
                strategy=llm_response['strategy'],
                llm_conviction=llm_response['confidence'],
                portfolio_value=self.get_portfolio_value(),
                existing_positions=self.get_positions(),
                sector_map=self.get_sector_map()
            )
            
            # Execute trade
            await self.execute_entry(event.symbol, position, llm_response)
            
            # Store decision memory
            decision = DecisionMemory(
                decision_id=str(uuid.uuid4()),
                symbol=event.symbol,
                timestamp=datetime.now(),
                decision_type=DecisionType.ENTRY,
                strategy=llm_response['strategy'],
                thesis=llm_response['thesis'],
                catalysts=llm_response['catalysts'],
                # ... fill in all fields
            )
            self.memory.store(decision)
            
            # Set price alerts
            self.price_monitor.set_price_alert(
                symbol=event.symbol,
                alert_type="above",
                price=llm_response['target_price'],
                event_type=EventType.TARGET_HIT,
                priority=EventPriority.MEDIUM_HIGH
            )
            self.price_monitor.set_price_alert(
                symbol=event.symbol,
                alert_type="below",
                price=llm_response['stop_loss'],
                event_type=EventType.STOP_LOSS_HIT,
                priority=EventPriority.CRITICAL
            )
```

---

## 📝 Common Patterns

### Pattern 1: Entry → Memory → Alerts

```python
# 1. Execute entry
fill = self.execute_buy(symbol, shares)

# 2. Store in memory
memory = DecisionMemory(...)
self.memory.store(memory)

# 3. Set alerts
self.price_monitor.set_price_alert(...)  # Target
self.price_monitor.set_price_alert(...)  # Stop
```

### Pattern 2: Event → Compare → Decide

```python
# 1. Get event
event = queue.get_next_event()

# 2. Get comparison
comparison = comparator.get_comparison(symbol, price, data)

# 3. Build prompt with context
prompt = comparator.build_reeval_prompt(...)

# 4. Get LLM decision
response = llm.analyze(prompt)

# 5. Store revisit
memory.add_revisit(symbol, response)
```

### Pattern 3: Position Sizing Flow

```python
# 1. Get historical performance
performance = memory.get_strategy_performance(strategy)

# 2. Calculate Kelly + conviction
position = sizer.calculate_position_size(
    symbol, price, strategy, conviction,
    portfolio_value, positions, sectors
)

# 3. Check risk limits
can_trade, warnings = risk_manager.check_risk_limits(
    {'symbol': symbol, 'size_usd': position.final_position_usd},
    portfolio_value, positions, sectors
)

# 4. Execute if approved
if can_trade:
    execute_trade(symbol, position.shares)
```

---

## 🎯 Key Principles

1. **Always store DecisionMemory on entry** - needed for thesis vs reality later
2. **Always set price alerts after entry** - creates event-driven monitoring
3. **Always use comparator for re-evaluation** - LLM needs to see its own thoughts
4. **Always use Kelly sizer for positions** - mathematical backing prevents arbitrary sizing
5. **Process events by priority** - critical events (stop loss) before background events
6. **Check risk limits before execution** - emergency stops are non-negotiable

---

## 🐛 Debugging Tips

### Check Event Queue Status
```python
status = queue.get_queue_status()
print(f"Pending: {status['pending_count']}")
print(f"By priority: {status['priority_breakdown']}")
print(f"By symbol: {status['symbol_breakdown']}")
```

### Check Memory Store
```python
open_positions = memory.get_all_open_positions()
print(f"Open positions: {len(open_positions)}")

for pos in open_positions:
    print(f"{pos.symbol}: {pos.strategy}, entry ${pos.entry_price:.2f}")
```

### Check Risk Metrics
```python
metrics = risk_manager.get_risk_metrics(portfolio_value, positions, sectors)
print(f"Status: {metrics['status']}")
print(f"Heat: {metrics['total_heat_pct']:.1f}%")
print(f"Sectors: {metrics['sector_breakdown']}")
```

---

## ✅ Checklist for Integration

- [ ] Replace time-based loop with event processing
- [ ] Store DecisionMemory on every entry decision
- [ ] Use ThesisRealityComparator for all re-evaluations
- [ ] Use KellyLLMPositionSizer for all position sizing
- [ ] Set price alerts after every entry
- [ ] Add events when news/volume/price triggers occur
- [ ] Update LLM prompts to include thesis vs reality
- [ ] Remove all arbitrary limits (cooldowns, trade counts, time minimums)
- [ ] Test with paper trading before going live

---

**Reference this guide when integrating the event-driven components into TradingAgent!** 📚
