# Market Hours Management in WawaTrader

## Overview

WawaTrader uses Alpaca's real-time market clock to accurately determine when markets are open or closed. The system provides comprehensive market status information to keep users informed and automatically handles trading during appropriate hours.

## How It Works

### Primary Method: Alpaca Market Clock API

WawaTrader queries Alpaca's market clock API to get real-time market status:

```python
from wawatrader.alpaca_client import get_client

client = get_client()
status = client.get_market_status()

print(status['status_text'])      # "🟢 OPEN" or "🔴 CLOSED"
print(status['status_message'])   # Detailed message with timing
print(status['time_until'])       # Time until next open/close
```

### Why Alpaca's Clock is Best

✅ **Always Accurate**: Real-time data from the exchange  
✅ **Handles Holidays**: Knows about market holidays automatically  
✅ **Early Closes**: Handles half-days (e.g., day before Thanksgiving)  
✅ **No Maintenance**: No need to manually update holiday calendars  
✅ **Timezone Safe**: All times properly converted to ET  

### Regular Market Hours

- **Monday - Friday**: 9:30 AM - 4:00 PM ET
- **Weekends**: Closed
- **Holidays**: Closed (handled automatically)

## User Experience

### Starting Trading When Market is OPEN

```
🚀 WawaTrader - Live Paper Trading System
============================================================

📊 MARKET STATUS
------------------------------------------------------------
   🟢 OPEN
   Market is open. Closes in 3 hours, 45 minutes
   Trading Hours: 9:30 AM - 4:00 PM ET (Mon-Fri)

   🟢 Market is OPEN - Trading will begin immediately!
------------------------------------------------------------

⚡ Starting live trading now...
```

### Starting Trading When Market is CLOSED

```
🚀 WawaTrader - Live Paper Trading System
============================================================

📊 MARKET STATUS
------------------------------------------------------------
   🔴 CLOSED
   Market is closed. Opens Monday at 09:30 AM ET (in 1 day, 18 hours)
   Trading Hours: 9:30 AM - 4:00 PM ET (Mon-Fri)

   💡 Note: Trading agent will start now and wait for market to open
            The system will automatically begin trading when market opens
            You can monitor progress on the dashboard
------------------------------------------------------------

💤 Market is CLOSED - Agent will monitor and wait
   Trading will begin automatically when market opens
```

### During Trading Cycles

When market is closed, the trading agent logs clear information:

```
============================================================
🔴 CLOSED
Market is closed. Opens Monday at 09:30 AM ET (in 1 day, 18 hours)
⏰ Regular trading hours: 9:30 AM - 4:00 PM ET (Mon-Fri)
💤 Trading agent will wait for market to open...
============================================================
```

## API Reference

### `get_market_status()`

Returns comprehensive market status information.

**Returns**: Dictionary with:
```python
{
    'is_open': bool,                    # True if market is open
    'status_text': str,                 # "🟢 OPEN" or "🔴 CLOSED"
    'status_message': str,              # Detailed human-readable message
    'current_time': str,                # ISO timestamp
    'next_open': str,                   # ISO timestamp of next open
    'next_close': str,                  # ISO timestamp of next close
    'next_event': str,                  # "open" or "close"
    'time_until': str,                  # "2 hours, 30 minutes" format
    'time_diff_seconds': int,           # Seconds until next event
    'trading_hours': str                # "9:30 AM - 4:00 PM ET (Mon-Fri)"
}
```

**Example Usage**:
```python
from wawatrader.alpaca_client import get_client

client = get_client()
status = client.get_market_status()

if status['is_open']:
    print(f"Trading now! Market closes in {status['time_until']}")
else:
    print(f"Market closed. Opens in {status['time_until']}")
    print(f"Next open: {status['next_open']}")
```

### `get_clock()`

Returns basic market clock information (simpler version).

**Returns**: Dictionary with:
```python
{
    'timestamp': str,      # Current time (ISO format)
    'is_open': bool,       # Market open status
    'next_open': str,      # Next open time (ISO format)
    'next_close': str      # Next close time (ISO format)
}
```

### `is_market_open()`

Simple boolean check for market status.

**Returns**: `bool` - `True` if market is open, `False` otherwise

**Example Usage**:
```python
from wawatrader.alpaca_client import get_client

client = get_client()
if client.is_market_open():
    # Execute trading logic
    pass
else:
    # Wait or skip
    pass
```

## Configuration Options

Market hours are primarily managed by Alpaca's API, but you can configure display preferences in `config/settings.py`:

```python
class SystemConfig(BaseModel):
    market_open_hour: int = Field(default=9, ge=0, le=23)
    market_open_minute: int = Field(default=30, ge=0, le=59)
    market_close_hour: int = Field(default=16, ge=0, le=23)
    market_close_minute: int = Field(default=0, ge=0, le=59)
```

These are used for **display purposes only**. The actual trading schedule is determined by Alpaca's API.

## Trading Agent Behavior

### Automatic Market Hours Handling

The trading agent automatically checks market status at the start of each cycle:

1. **Market Open**: 
   - Proceeds with symbol analysis
   - Executes trades if conditions are met
   - Updates dashboard with live data

2. **Market Closed**:
   - Logs clear status message
   - Skips trading cycle
   - Waits for next cycle (5 minutes default)
   - Checks again automatically

### No Manual Intervention Needed

You can start the trading agent at any time:
- **Before market open**: Agent waits and starts trading when market opens
- **During market hours**: Agent starts trading immediately
- **After market close**: Agent waits for next trading day
- **Weekends**: Agent waits for Monday open

## Testing Market Hours

### Check Current Status

```bash
# Quick status check
python start.py status

# Detailed market status demo
python scripts/demo_market_status.py
```

### Manual Testing

```python
from wawatrader.alpaca_client import get_client

client = get_client()

# Get detailed status
status = client.get_market_status()
print(f"Market: {status['status_text']}")
print(f"Status: {status['status_message']}")

# Simple check
if client.is_market_open():
    print("✅ Ready to trade!")
else:
    print("💤 Market is closed")
```

## Troubleshooting

### Market Status Shows "UNKNOWN"

**Possible causes**:
- No internet connection
- Alpaca API credentials not configured
- Alpaca API temporarily unavailable

**Solution**:
1. Check internet connection
2. Verify `.env` file has correct API keys
3. Test connection: `python start.py status`

### Agent Not Trading During Market Hours

**Check**:
1. Run `python scripts/demo_market_status.py` to verify market is open
2. Check logs for error messages
3. Verify account has buying power
4. Check if risk limits are being hit

**Common issues**:
- Insufficient buying power
- Daily loss limit reached
- Max position size exceeded
- LLM not responding (system continues safely)

## Best Practices

### For Users

✅ **Start agent anytime** - It will wait intelligently  
✅ **Check status first** - Run `python start.py status`  
✅ **Monitor logs** - Clear messages about market status  
✅ **Use dashboard** - Visual confirmation of market state  

### For Developers

✅ **Always use `get_market_status()`** - Most informative  
✅ **Handle errors gracefully** - Market API can fail  
✅ **Log status clearly** - Users need to understand what's happening  
✅ **Don't hardcode hours** - Let Alpaca manage the schedule  

## Extended Hours Trading

**Current Status**: Not implemented

WawaTrader currently only trades during regular market hours (9:30 AM - 4:00 PM ET). Extended hours trading (pre-market and after-hours) is not supported in the current version.

**Rationale**:
- Extended hours have lower liquidity
- Wider bid-ask spreads
- Higher risk for algorithmic trading
- Not recommended for paper trading beginners

**Future Enhancement**: Extended hours support could be added by:
1. Setting `extended_hours=True` in order requests
2. Modifying market hours check to allow extended hours
3. Adding configuration option for extended hours preference

## Market Holidays

Alpaca's API automatically handles market holidays including:
- New Year's Day
- Martin Luther King Jr. Day
- Presidents' Day
- Good Friday
- Memorial Day
- Independence Day
- Labor Day
- Thanksgiving Day
- Christmas Day

**Early Closes** (1:00 PM ET) are also handled automatically:
- Day after Thanksgiving
- Christmas Eve
- Day before Independence Day (when on a weekday)

## Summary

WawaTrader's market hours management is:
- ✅ **Automatic** - No manual schedule management needed
- ✅ **Accurate** - Real-time data from Alpaca
- ✅ **User-friendly** - Clear status messages and countdown timers
- ✅ **Reliable** - Handles holidays, weekends, early closes
- ✅ **Safe** - Only trades during appropriate hours

Users are always well-informed about:
- Current market status (open/closed)
- Time until next market event
- Expected trading behavior
- System readiness status
