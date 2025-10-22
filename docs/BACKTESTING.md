# Backtesting Framework

The WawaTrader backtesting framework simulates your trading strategy on historical data to evaluate performance **before risking real money**.

## Overview

The backtester replays historical market data day-by-day, making trading decisions exactly as the live system would, while tracking performance metrics.

### Key Features

✅ **Point-in-time data** - No lookahead bias  
✅ **Realistic execution** - Slippage and commissions included  
✅ **Complete metrics** - Returns, Sharpe ratio, drawdown, win rate  
✅ **Benchmark comparison** - Compare against buy-and-hold  
✅ **Trade history** - Every trade recorded with reasoning  
✅ **Risk analysis** - Same risk rules as live trading  

## Quick Start

### 1. Run Tests (Recommended First)

```bash
# Validate backtester logic
pytest tests/test_backtester.py -v

# Should show: 13 passed
```

### 2. Run Demo

```bash
# See backtester features in action
python scripts/demo_backtest.py
```

### 3. Run Full Backtest

```bash
# Backtest AAPL for 2024
python scripts/run_backtest.py
```

## Usage Examples

### Basic Backtest

```python
from wawatrader.backtester import Backtester

# Create backtester
bt = Backtester(
    symbols=["AAPL"],
    start_date="2024-01-01",
    end_date="2024-12-31",
    initial_capital=100000
)

# Run simulation
stats = bt.run()

# View results
print(bt.generate_report(stats))

# Save trade history
bt.save_results()
```

### Multi-Symbol Backtest

```python
# Test portfolio strategy
bt = Backtester(
    symbols=["AAPL", "MSFT", "GOOGL"],
    start_date="2023-01-01",
    end_date="2024-12-31",
    initial_capital=250000,
    slippage_pct=0.002  # 0.2% slippage
)

stats = bt.run()
```

### Custom Costs

```python
# Account for transaction costs
bt = Backtester(
    symbols=["AAPL"],
    start_date="2024-01-01",
    end_date="2024-12-31",
    initial_capital=100000,
    commission_per_share=0.01,  # $0.01 per share (Alpaca is $0)
    slippage_pct=0.001  # 0.1% slippage
)
```

## Performance Metrics

The backtester calculates comprehensive performance statistics:

### Return Metrics
- **Total Return** - Overall gain/loss percentage
- **Annualized Return** - Return normalized to annual rate
- **Benchmark Return** - Buy-and-hold return for comparison
- **Alpha** - Excess return vs benchmark

### Risk Metrics
- **Sharpe Ratio** - Risk-adjusted return (higher is better)
- **Max Drawdown** - Largest peak-to-trough decline
- **Drawdown Duration** - Days spent in drawdown
- **Volatility** - Annualized standard deviation of returns

### Trading Stats
- **Total Trades** - Number of completed trades
- **Win Rate** - Percentage of profitable trades
- **Average Win/Loss** - Average profit/loss per trade
- **Profit Factor** - Total wins ÷ Total losses

### Example Report

```
╔══════════════════════════════════════════════════════════════╗
║                    BACKTEST RESULTS                          ║
╚══════════════════════════════════════════════════════════════╝

Period: 2024-01-01 to 2024-12-31 (252 days)
Symbols: AAPL

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RETURNS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Starting Capital:        $     100,000.00
Ending Capital:          $     110,000.00
Total Return:                      10.00%
Annualized Return:                 10.00%
Benchmark Return:                   8.00%
Alpha (vs Benchmark):               2.00%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RISK METRICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sharpe Ratio:                       1.20
Max Drawdown:                       5.00%
Drawdown Duration:                    15 days
Volatility (Annual):               15.00%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TRADING STATISTICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Trades:                         50
Winning Trades:                       30
Losing Trades:                        20
Win Rate:                           60.0%
Average Win:             $         500.00
Average Loss:            $        -300.00
Profit Factor:                      1.67
```

## How It Works

### 1. Data Loading
```python
# Fetches historical bars for all symbols
bt.load_historical_data()
```

The backtester loads historical price data with a buffer period to ensure indicators have enough data.

### 2. Day-by-Day Simulation
```python
# For each trading day:
for current_date in trading_days:
    # Calculate indicators (using only past data)
    signals = analyze_dataframe(historical_data_up_to_date)
    
    # Get LLM analysis
    decision = llm_bridge.analyze_market_data(signals)
    
    # Validate with risk manager
    risk_check = risk_manager.check_trade(decision)
    
    # Execute if approved
    if risk_check.approved:
        execute_trade(decision)
```

### 3. Performance Calculation
```python
# After simulation completes
stats = bt.calculate_statistics()
```

## Important Notes

### No Lookahead Bias
The backtester uses **only data available at the time** of each decision. Future data is never used.

```python
# ✅ CORRECT: Point-in-time data
df = get_data_at_date(symbol, current_date)  # Data BEFORE current_date

# ❌ WRONG: Would be lookahead bias
df = get_all_data(symbol)  # Includes future data
```

### Realistic Execution

**Slippage**: Market orders don't fill at exact price
- Buy: Price × (1 + slippage_pct)
- Sell: Price × (1 - slippage_pct)

**Commissions**: Transaction costs (Alpaca is $0)
- Total cost = shares × commission_per_share

### Risk Management
The backtester uses the **same risk rules** as live trading:
- Max 10% position size
- Max 2% daily loss
- Max 30% portfolio exposure
- Max 10 trades per day

## Output Files

Results are saved to `backtest_results/` directory:

### trades_YYYYMMDD_YYYYMMDD.json
Complete trade history with entry/exit prices, P&L, and reasoning:

```json
[
  {
    "entry_date": "2024-01-15T00:00:00",
    "exit_date": "2024-02-15T00:00:00",
    "symbol": "AAPL",
    "side": "sell",
    "shares": 100,
    "entry_price": 150.15,
    "exit_price": 164.84,
    "pnl": 1468.50,
    "pnl_pct": 9.78,
    "commission": 0.0,
    "duration_days": 31,
    "reasoning": "Strong technical signals + positive LLM sentiment",
    "confidence": 0.85
  }
]
```

### daily_values_YYYYMMDD_YYYYMMDD.csv
Daily portfolio values:

```csv
date,portfolio_value
2024-01-01,100000.00
2024-01-02,100150.00
2024-01-03,99875.00
...
```

## Interpreting Results

### Good Strategy Indicators
- ✅ Alpha > 0 (beats buy-and-hold)
- ✅ Sharpe ratio > 1.0
- ✅ Win rate > 50%
- ✅ Profit factor > 1.5
- ✅ Max drawdown < 20%

### Warning Signs
- ⚠️ Negative alpha (underperforms market)
- ⚠️ Sharpe ratio < 0.5
- ⚠️ Win rate < 40%
- ⚠️ Profit factor < 1.0
- ⚠️ Max drawdown > 30%

### Example Interpretation

```
Total Return:     +12.5%
Benchmark Return: +8.0%
Alpha:            +4.5%  ← Strategy beat market by 4.5%!

Sharpe Ratio:     1.8    ← Good risk-adjusted return
Max Drawdown:     -8.2%  ← Manageable risk
Win Rate:         62%    ← Slightly above 50/50

✅ This looks promising!
```

## Limitations

1. **Historical data access**: Paper accounts have limited real-time data
2. **LLM consistency**: LLM responses may vary between runs
3. **Market conditions**: Past performance ≠ future results
4. **Execution assumptions**: Real slippage may vary
5. **Liquidity**: Assumes all orders fill (may not be true for large orders)

## Next Steps

After backtesting:

1. **Review metrics** - Is the strategy profitable?
2. **Analyze trades** - Why did winners win? Why did losers lose?
3. **Test different periods** - Does it work in bear markets?
4. **Test multiple symbols** - Does it generalize?
5. **Paper trade** - Test live with paper account
6. **Go live** - Start with small capital

## Advanced Usage

### Custom Backtest Loop

```python
# Manual control over backtest process
bt = Backtester(symbols=["AAPL"], ...)
bt.load_historical_data()

# Custom logic
for trading_day in bt.get_trading_days():
    # Your custom analysis
    decision = my_custom_strategy(trading_day)
    
    # Execute through backtester
    if decision:
        bt.execute_trade(**decision)

# Calculate results
stats = bt.calculate_statistics()
```

### Comparing Strategies

```python
# Strategy A: Original settings
bt_a = Backtester(symbols=["AAPL"], initial_capital=100000)
stats_a = bt_a.run()

# Strategy B: Different settings
bt_b = Backtester(symbols=["AAPL"], initial_capital=100000)
# Modify settings here
stats_b = bt_b.run()

# Compare
print(f"Strategy A return: {stats_a.total_return*100:.2f}%")
print(f"Strategy B return: {stats_b.total_return*100:.2f}%")
```

## Troubleshooting

### "No historical data loaded"
**Cause**: Paper account data restrictions or invalid date range  
**Solution**: Use dates within last 6 months or upgrade to live account

### "Insufficient cash"
**Cause**: Position sizing too aggressive  
**Solution**: Reduce position size in risk settings

### "Sharpe ratio is NaN"
**Cause**: Not enough trades or zero volatility  
**Solution**: Run longer backtest or check if strategy is trading

## See Also

- [Risk Management](../wawatrader/risk_manager.py) - Risk rules
- [Trading Agent](../wawatrader/trading_agent.py) - Live trading
- [Technical Indicators](../wawatrader/indicators.py) - Analysis tools
- [LLM Bridge](../wawatrader/llm_bridge.py) - Sentiment analysis
