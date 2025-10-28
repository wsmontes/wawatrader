# Data Logging & Replay System

## Overview

WawaTrader implements comprehensive data logging to enable:
- **Strategy Evaluation**: Test different configurations with real market data
- **Decision Analysis**: Review what decisions were made and why
- **Performance Attribution**: Understand what worked and what didn't
- **Backtesting**: Replay days with alternative strategies
- **Debugging**: Trace exactly what happened at any point

## Log Files

All logs are stored in `logs/` directory as JSONL (JSON Lines) format - one JSON object per line.

### 1. `market_data.jsonl`
**What**: All market data fetched from Alpaca (OHLCV bars)

**Structure**:
```json
{
  "timestamp": "2024-10-27T10:30:00.123456",
  "event": "bars_fetch",
  "symbol": "AAPL",
  "timeframe": "1Day",
  "start": "2024-07-27T00:00:00",
  "end": "2024-10-27T16:00:00",
  "count": 65,
  "latest_close": 229.87,
  "latest_volume": 45678900,
  "recent_bars": [
    {
      "timestamp": "2024-10-27T09:30:00",
      "open": 228.50,
      "high": 230.12,
      "low": 228.20,
      "close": 229.87,
      "volume": 45678900,
      "vwap": 229.45
    }
  ]
}
```

**Use Cases**:
- Verify indicator calculations
- Check data quality issues
- Replay price movements
- Test strategies at different times

### 2. `account_snapshots.jsonl`
**What**: Account state every time it's fetched

**Structure**:
```json
{
  "timestamp": "2024-10-27T10:30:05.789012",
  "event": "account_fetch",
  "data": {
    "account_number": "PA1234567890",
    "buying_power": 95234.56,
    "cash": 50000.00,
    "portfolio_value": 105234.56,
    "equity": 105234.56,
    "pattern_day_trader": false,
    "trading_blocked": false
  }
}
```

**Use Cases**:
- Track portfolio value over time
- Calculate returns
- Verify buying power management
- Monitor account health

### 3. `position_snapshots.jsonl`
**What**: Position details every time positions are fetched

**Structure**:
```json
{
  "timestamp": "2024-10-27T10:30:10.345678",
  "event": "positions_fetch",
  "count": 3,
  "positions": [
    {
      "symbol": "AAPL",
      "qty": 100,
      "side": "long",
      "market_value": 22987.00,
      "cost_basis": 22500.00,
      "unrealized_pl": 487.00,
      "unrealized_plpc": 0.0216,
      "current_price": 229.87,
      "avg_entry_price": 225.00,
      "change_today": 1.37
    }
  ]
}
```

**Use Cases**:
- Track position P&L evolution
- Verify entry/exit prices
- Calculate hold times
- Analyze position sizing

### 4. `order_executions.jsonl`
**What**: All order submissions, fills, and failures

**Structure**:
```json
{
  "timestamp": "2024-10-27T10:35:00.123456",
  "event": "order_submitted",
  "order_id": "d4f123e5-6789-0abc-def0-123456789abc",
  "symbol": "AAPL",
  "side": "buy",
  "qty": 100,
  "time_in_force": "day",
  "order_data": {
    "id": "d4f123e5-6789-0abc-def0-123456789abc",
    "status": "pending_new",
    "type": "market"
  }
}
```

```json
{
  "timestamp": "2024-10-27T10:35:01.987654",
  "event": "order_filled",
  "order_id": "d4f123e5-6789-0abc-def0-123456789abc",
  "status": "filled",
  "filled_price": 229.85,
  "filled_qty": 100,
  "wait_time_seconds": 1.864,
  "order_data": {
    "symbol": "AAPL",
    "side": "buy",
    "filled_avg_price": 229.85
  }
}
```

**Use Cases**:
- Verify execution prices
- Calculate slippage
- Track execution speed
- Identify failed orders

### 5. `decisions.jsonl` (Existing)
**What**: All trading decisions made by the system

**Structure**:
```json
{
  "timestamp": "2024-10-27T10:30:15.555555",
  "symbol": "AAPL",
  "action": "buy",
  "shares": 100,
  "confidence": 75,
  "reasoning": "Strong bullish momentum with RSI at 58...",
  "technical_signals": {...},
  "llm_analysis": {...}
}
```

## Replay & Analysis

### Using `replay_trading_day.py`

**Basic Replay**:
```bash
python scripts/replay_trading_day.py --date 2024-10-27
```

**Output**:
```
Loading logs for 2024-10-27...
✅ Loaded:
   - 125 market data entries
   - 8 decisions
   - 12 order events
   - 45 account snapshots
   - 38 position snapshots

📊 Decision Analysis:
✅ 2024-10-27 10:30:15 | AAPL BUY @ $229.50
   1hr later: $231.25 (+0.76%)
   Reasoning: Strong bullish momentum with RSI at 58...

❌ 2024-10-27 13:45:22 | MSFT SELL @ $420.15
   1hr later: $422.30 (-0.51%)
   Reasoning: Overbought conditions, RSI above 70...

📈 Performance Metrics:
Start Value: $100,000.00
End Value: $100,847.50
P&L: $847.50 (+0.85%)
Total Trades: 12
Win Rate: 66.7% (4W / 2L)
```

**Symbol-Specific Analysis**:
```bash
python scripts/replay_trading_day.py --date 2024-10-27 --symbol AAPL
```

**Export for Spreadsheet Analysis**:
```bash
python scripts/replay_trading_day.py --date 2024-10-27 --export
# Creates logs/replay_2024-10-27.csv
```

### Manual Analysis

**Read Logs with Python**:
```python
import json
from pathlib import Path

# Read all market data
with open('logs/market_data.jsonl', 'r') as f:
    for line in f:
        entry = json.loads(line)
        print(f"{entry['timestamp']}: {entry['symbol']} @ ${entry['latest_close']}")
```

**Query with jq** (command line):
```bash
# All AAPL data
cat logs/market_data.jsonl | jq 'select(.symbol == "AAPL")'

# Orders filled at specific price range
cat logs/order_executions.jsonl | jq 'select(.event == "order_filled" and .filled_price > 200 and .filled_price < 250)'

# Daily P&L
cat logs/account_snapshots.jsonl | jq '.data.portfolio_value'
```

## Strategy Testing

### Test Alternative Configuration

1. **Save current results**:
   ```bash
   python scripts/replay_trading_day.py --date 2024-10-27 --export
   ```

2. **Modify configuration** in `config/settings.py`:
   ```python
   # Test more aggressive profile
   trading_profile = 'aggressive'  # was 'moderate'
   
   # Test tighter stop loss
   stop_loss_pct = 0.03  # was 0.05
   ```

3. **Run backtest with logged data**:
   ```bash
   # TODO: Implement backtest replay mode
   python scripts/run_backtest.py --replay logs/replay_2024-10-27.csv
   ```

4. **Compare results**:
   - Original: $847.50 profit, 66.7% win rate
   - Aggressive: $1,234.25 profit, 75% win rate
   - Decision: Use aggressive profile!

## Best Practices

### Storage Management

Logs can grow large. Recommended practices:

1. **Rotate Daily**:
   ```bash
   # Add to cron
   0 0 * * * cd /path/to/wawatrader && ./scripts/rotate_logs.sh
   ```

2. **Compress Old Logs**:
   ```bash
   gzip logs/market_data_2024-10-*.jsonl
   ```

3. **Archive Monthly**:
   ```bash
   tar -czf archives/logs_2024_10.tar.gz logs/*_2024-10-*.jsonl.gz
   rm logs/*_2024-10-*.jsonl.gz
   ```

### Privacy & Security

- Logs contain account numbers (masked in examples above)
- Do NOT commit logs to version control (already in `.gitignore`)
- Sanitize logs before sharing
- Consider encrypting archived logs

### Performance Impact

Logging is designed to be minimal impact:
- Async writes (non-blocking)
- Only essential data logged
- Estimated overhead: <5ms per operation
- Daily log size: ~10-50 MB depending on activity

## Troubleshooting

**Issue**: Missing logs for specific time period

**Solution**: Check system was running
```bash
# Check if logs exist for date range
ls -lh logs/*.jsonl
grep "2024-10-27" logs/*.jsonl | wc -l
```

**Issue**: Logs too large

**Solution**: Reduce retention or increase sampling
```python
# In alpaca_client.py, adjust logging frequency
if should_log_detailed():  # Add sampling logic
    self._log_to_file(...)
```

**Issue**: Corrupted JSONL

**Solution**: Validate and repair
```bash
# Find bad lines
cat logs/market_data.jsonl | while read line; do
  echo "$line" | jq . >/dev/null 2>&1 || echo "Bad line: $line"
done

# Remove bad lines (backup first!)
cp logs/market_data.jsonl logs/market_data.jsonl.bak
cat logs/market_data.jsonl | while read line; do
  echo "$line" | jq . >/dev/null 2>&1 && echo "$line"
done > logs/market_data_clean.jsonl
```

## Future Enhancements

Planned logging improvements:

- [ ] LLM conversation logs (prompts/responses) - **Already done via `llm_conversations.jsonl`**
- [ ] Technical indicator values at decision time
- [ ] Risk check results (why trades were rejected)
- [ ] Real-time performance dashboard integration
- [ ] Automatic anomaly detection in logs
- [ ] ML model for pattern recognition in decisions

---

**Remember**: These logs are your system's black box recorder. They enable continuous improvement through data-driven analysis!
