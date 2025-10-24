# Quick Reference: Intelligent Scheduling

## At a Glance

### Market States
```
🟢 ACTIVE_TRADING     9:30 AM -  3:30 PM  →  Trading focus
🟡 MARKET_CLOSING     3:30 PM -  4:30 PM  →  End-of-day reports
🔴 EVENING_ANALYSIS   4:30 PM - 10:00 PM  →  Deep research
💤 OVERNIGHT_SLEEP   10:00 PM -  6:00 AM  →  Minimal monitoring
🌅 PREMARKET_PREP     6:00 AM -  9:30 AM  →  Morning preparation
```

### Resource Savings
- **Before**: 288 LLM calls/day
- **After**: 88 LLM calls/day  
- **Savings**: 70% reduction

## Usage

### Start Trading (Automatic)
```bash
python start.py
```
System automatically uses intelligent scheduling.

### Check Current State
```bash
venv/bin/python -c "
from wawatrader.market_state import display_market_state_info
display_market_state_info()
"
```

### Run Tests
```bash
venv/bin/python scripts/test_intelligent_scheduling.py
```

## Task Schedule

### 🟢 Active Trading
- **Every 5 min**: Trading cycle
- **Every 30 min**: Quick intelligence
- **Every 2 hours**: Deep analysis

### 🟡 Market Closing
- **3:00 PM**: Pre-close assessment
- **4:00 PM**: Daily summary

### 🔴 Evening
- **5:00 PM**: Earnings analysis
- **7:00 PM**: Sector deep dive
- **9:00 PM**: International markets

### 💤 Overnight
- **Every 2 hours**: News monitoring only

### 🌅 Pre-Market
- **6:00 AM**: Overnight summary
- **7:00 AM**: Pre-market scanner
- **9:00 AM**: Market open prep

## Code Examples

### Get Current State
```python
from wawatrader.market_state import get_market_state

state = get_market_state()
print(f"{state.emoji} {state.description}")
```

### Use Scheduler
```python
from wawatrader.scheduler import IntelligentScheduler

scheduler = IntelligentScheduler()
next_task = scheduler.get_next_task()

if next_task:
    print(f"Next: {next_task.description}")
```

### Run Agent (New Way)
```python
from wawatrader.trading_agent import TradingAgent

agent = TradingAgent(symbols=["AAPL", "MSFT"])
agent.run_continuous_intelligent()  # ← Intelligent scheduling
```

## What Changed?

### For Regular Users
✅ **Nothing** - System works the same, just smarter

### For Developers
✅ New method: `agent.run_continuous_intelligent()`  
✅ Old method still works (with deprecation warning)  
✅ New modules: `market_state.py`, `scheduler.py`, `scheduled_tasks.py`

## Benefits

✅ 70% fewer LLM calls  
✅ No repetitive overnight analysis  
✅ Strategic task timing  
✅ Cleaner dashboard insights  
✅ Same trading effectiveness  

## Files

### Core Implementation
- `wawatrader/market_state.py` - State detection
- `wawatrader/scheduler.py` - Task scheduling
- `wawatrader/scheduled_tasks.py` - Task handlers
- `wawatrader/trading_agent.py` - Integration

### Documentation
- `docs/INTELLIGENT_TIME_MANAGEMENT_PLAN.md` - Original plan
- `docs/INTELLIGENT_SCHEDULING_IMPLEMENTATION.md` - Implementation details
- `docs/INTELLIGENT_SCHEDULING_QUICKREF.md` - This file

### Testing
- `scripts/test_intelligent_scheduling.py` - Test suite (5/5 passing)
