# Position Manager Integration Guide

## Overview

This guide explains how to integrate the new **event-driven PositionManager** with the existing **time-based TradingAgent** for a hybrid trading system.

## Architecture

```
TradingAgent (Time-Based)        PositionManager (Event-Driven)
     |                                    |
     | Opens positions                    | Monitors positions
     | every 20 minutes                   | every 15 seconds
     |                                    |
     v                                    v
BUY Decision  ---(handoff)--->    add_position()
                                        |
                                   Set Targets
                                        |
                            +--------------------+
                            | Monitor for events |
                            +--------------------+
                                        |
                            TP1, TP2, Stop, RSI
                                        |
                            +--------------------+
                            | Priority Queue LLM |
                            +--------------------+
                                        |
                            +--------------------+
                            | Execute or Fallback|
                            +--------------------+
```

## Integration Steps

### Step 1: Initialize PositionManager in TradingAgent

```python
# In wawatrader/trading_agent.py __init__():

from wawatrader.position_manager import PositionManager

class TradingAgent:
    def __init__(self, symbols: List[str], dry_run: bool = False):
        # ... existing initialization ...
        
        # Initialize position manager (NEW)
        self.position_manager = PositionManager(
            alpaca_client=self.alpaca,
            llm_bridge=self.llm_bridge,
            trading_agent=self  # Pass self for execution callbacks
        )
        
        # Start background monitoring
        self.position_manager.start()
```

### Step 2: Hand Off Positions After BUY

```python
# In wawatrader/trading_agent.py execute_decision():

def execute_decision(self, decision: TradingDecision):
    """Execute a trading decision."""
    # ... existing execution code ...
    
    if decision.executed and decision.action == 'buy':
        # NEW: Hand position to event-driven manager
        llm_hints = decision.llm_analysis
        
        self.position_manager.add_position(
            symbol=decision.symbol,
            shares=decision.shares,
            entry_price=final_order['filled_avg_price'],
            llm_hints=llm_hints
        )
        
        logger.info(f"✅ Position handed to PositionManager for monitoring")
```

### Step 3: Remove Position from TradingAgent Tracking

The PositionManager will now handle exits, so TradingAgent should **not** try to sell positions it didn't open:

```python
# In wawatrader/trading_agent.py analyze_symbol():

def analyze_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
    """Analyze a symbol."""
    
    # Get current position (if any)
    current_position = None
    if symbol in self.positions:
        # Check if position is managed by PositionManager
        if symbol in self.position_manager.positions:
            # Skip - let PositionManager handle it
            logger.debug(f"Skipping {symbol}: managed by PositionManager")
            return None
        
        # Otherwise, analyze normally
        pos = self.positions[symbol]
        current_position = {
            'qty': float(pos['qty']),
            'avg_entry_price': float(pos['avg_entry_price']),
            'current_price': float(pos.get('current_price', 0))
        }
    
    # ... rest of analysis ...
```

### Step 4: Set Market Close Time

```python
# In wawatrader/scheduled_tasks.py or your main loop:

from datetime import datetime, time

# Set market close time for safety checks (3:30 PM EST for 30-min buffer)
market_close = datetime.now().replace(hour=15, minute=30, second=0)
position_manager.set_market_close_time(market_close)
```

### Step 5: Graceful Shutdown

```python
# In your main loop or signal handler:

def shutdown():
    """Graceful shutdown."""
    logger.info("Shutting down...")
    
    # Stop position monitoring
    position_manager.stop()
    
    # ... rest of shutdown ...
```

## Configuration

### Risk Settings (config/settings.py)

```python
# Position Manager specific settings
POSITION_MANAGER = {
    'monitor_interval_seconds': 15,  # How often to check prices
    'pre_close_safety_minutes': 30,  # Exit positions if LLM down
    
    'llm_queue': {
        'max_wait_time': 300,     # 5 minutes max in queue
        'llm_timeout': 30,        # 30 seconds per LLM call
        'failure_threshold': 3,   # 3 failures = LLM offline
    },
    
    'target_defaults': {
        'take_profit_1_r': 2,     # 2R (2x risk) for TP1
        'take_profit_2_r': 3,     # 3R (3x risk) for TP2
        'stop_loss_atr': 2.0,     # 2 ATR stop loss
        'trailing_stop_atr': 1.5, # 1.5 ATR trailing
        'rsi_high_threshold': 75, # Exit if RSI > 75
        'rsi_low_threshold': 30,  # Monitor if RSI < 30
    }
}
```

## Testing Strategy

### Phase 1: Dry Run (1 Day)

```python
# Enable both systems but don't execute PositionManager trades
position_manager = PositionManager(
    alpaca_client=alpaca,
    llm_bridge=llm_bridge,
    trading_agent=None  # No execution
)
```

**What to validate:**
- Events trigger correctly (TP1, TP2, stops, RSI)
- Priority queue orders events properly
- LLM queue processes serially without conflicts
- Fallback plans execute when LLM is disabled

### Phase 2: Paper Trading (3-5 Days)

```python
# Enable full integration
position_manager = PositionManager(
    alpaca_client=alpaca,
    llm_bridge=llm_bridge,
    trading_agent=trading_agent
)
position_manager.start()
```

**What to validate:**
- Actual orders execute correctly
- P&L calculations match expectations
- No double-execution (TradingAgent + PositionManager)
- Emergency exit before market close works
- LLM health tracking works (test by killing LM Studio)

### Phase 3: Optimization (1-2 Weeks)

Monitor logs for:
- **False triggers**: Events that shouldn't have triggered
- **Missed opportunities**: Should have triggered but didn't
- **LLM queue backlog**: Too many events waiting
- **Fallback frequency**: How often LLM fails

## Monitoring

### Key Metrics to Track

```python
stats = position_manager.get_stats()

# Daily summary
print(f"Monitored: {stats['positions_monitored']}")
print(f"Events: {stats['events_created']}")
print(f"Executed: {stats['events_executed']}")
print(f"Fallbacks: {stats['fallback_executions']}")
print(f"LLM Requests: {stats['llm_requests_processed']}")
print(f"LLM Health: {stats['llm_consecutive_failures']} failures")
```

### Log Analysis

Look for these patterns:

**Good Signs:**
```
🎯 Event triggered: AAPL - TAKE_PROFIT_1
🧠 Consulting LLM: AAPL - TAKE_PROFIT_1
✅ LLM decision: SELL (confidence: 85%)
💰 EXITING 50% of AAPL: LLM: TAKE_PROFIT_1
```

**Warning Signs:**
```
⏱️ LLM timeout for AAPL after 30s
🔄 Executing fallback plan: AAPL - TAKE_PROFIT_1 -> PARTIAL_EXIT
❌ 3 consecutive LLM failures, marking as OFFLINE
```

**Critical Issues:**
```
🚨 EMERGENCY: LLM offline 30min before close, exiting ALL positions
❌ Error executing exit for AAPL: [error message]
```

## Common Issues & Solutions

### Issue 1: LLM Queue Backlog

**Symptom:** Events waiting 5+ minutes in queue

**Solution:**
- Reduce monitoring frequency (15s → 30s)
- Increase LLM timeout (30s → 45s)
- Use more fallback plans (fewer LLM consultations)

### Issue 2: False Triggers

**Symptom:** TP1 triggers on noise, not real moves

**Solution:**
- Increase target distances (2R → 2.5R)
- Add volume confirmation to event detection
- Require multiple bars above target

### Issue 3: LLM Always Times Out

**Symptom:** Every LLM call fails with timeout

**Solution:**
- Check LM Studio is running
- Increase timeout (30s → 60s for slow models)
- Use smaller model (Gemma-3-4b → Phi-3)

### Issue 4: Double Execution

**Symptom:** Position sold by both TradingAgent and PositionManager

**Solution:**
- Ensure TradingAgent skips positions in `position_manager.positions`
- Add mutex lock around position tracking dict
- Check logs for race conditions

## Performance Expectations

### Before (Time-Based Only)
- **Trading Frequency**: 70+ opportunities/day
- **Actual Trades**: 20-40/day (many false positives)
- **Hold Time**: 15-45 minutes (too short for daily strategy)
- **Transaction Costs**: $500-800/day

### After (Hybrid Event-Driven)
- **Trading Frequency**: 10-20 trades/day (higher quality)
- **Actual Trades**: 8-15/day (validated by targets)
- **Hold Time**: 2-8 hours (proper daily timeframe)
- **Transaction Costs**: $150-300/day (70% reduction)

### Expected Improvements
- **60-80% reduction** in trading frequency
- **40-60% reduction** in transaction costs
- **Better profit targets** (2R and 3R exits vs random)
- **Controlled risk** (2 ATR stops vs ad-hoc)

## Migration Checklist

- [ ] Add `position_manager` to TradingAgent.__init__()
- [ ] Call `position_manager.add_position()` after BUY execution
- [ ] Skip analyzing symbols in `position_manager.positions`
- [ ] Set market close time in scheduler
- [ ] Add graceful shutdown to stop monitoring
- [ ] Configure targets and thresholds in settings
- [ ] Test with dry run (1 day)
- [ ] Test with paper trading (3-5 days)
- [ ] Monitor logs for issues
- [ ] Optimize based on performance data

## Next Steps

1. **Implement opportunity scanner** (for opening NEW positions)
2. **Add real-time RSI calculation** (currently returns None)
3. **Integrate with dashboard** (show event queue, LLM health)
4. **Add historical backtesting** (validate strategy on past data)
5. **Performance analytics** (compare before/after metrics)

## Support

If you encounter issues:
1. Check logs in `logs/` directory
2. Review `FALLBACK_SYSTEM.md` for safety mechanism details
3. See `EVENT_DRIVEN_TRADING_PROPOSAL.md` for architecture overview
4. Check `position_manager.py` docstrings for API reference
