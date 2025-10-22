# WawaTrader User Guide

## Table of Contents

- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Running Backtests](#running-backtests)
- [Paper Trading](#paper-trading)
- [Monitoring Performance](#monitoring-performance)
- [Managing Alerts](#managing-alerts)
- [Best Practices](#best-practices)
- [FAQ](#faq)

---

## Getting Started

### First-Time Setup

1. **Install WawaTrader**
   ```bash
   git clone https://github.com/yourusername/WawaTrader.git
   cd WawaTrader
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Get Alpaca API Keys**
   - Visit [Alpaca Markets](https://alpaca.markets/)
   - Sign up for free paper trading account
   - Navigate to API Keys section
   - Generate new API key pair
   - Save keys securely

3. **Install and Configure LM Studio**
   - Download [LM Studio](https://lmstudio.ai/)
   - Install application
   - Download Gemma 3 4B model
   - Start local server:
     - Click "Local Server" tab
     - Select Gemma 3 4B model
     - Click "Start Server"
     - Note URL (usually http://localhost:1234)

4. **Set Environment Variables**
   ```bash
   export ALPACA_API_KEY="your_api_key"
   export ALPACA_SECRET_KEY="your_secret_key"
   export ALPACA_PAPER=true
   export LM_STUDIO_BASE_URL="http://localhost:1234/v1"
   export LM_STUDIO_MODEL="gemma-3-4b"
   ```

5. **Verify Setup**
   ```bash
   # Run tests
   pytest tests/ -v
   
   # Should see: 134 passed
   ```

### Quick Start

```bash
# 1. Launch Configuration UI
python scripts/run_config_ui.py
# Open http://localhost:5001

# 2. Set your watchlist
# In Config UI, go to "Trading" tab
# Enter symbols: AAPL, TSLA, NVDA

# 3. Run a backtest (recommended before live trading)
python scripts/demo_backtesting.py

# 4. Start dashboard
python -m wawatrader.dashboard
# Open http://localhost:8050

# 5. Begin paper trading (in new terminal)
python -m wawatrader.trading_agent
```

---

## Configuration

### Using the Web Interface

1. **Start Configuration UI**
   ```bash
   python scripts/run_config_ui.py
   ```

2. **Access in Browser**
   - Navigate to http://localhost:5001
   - You'll see 5 configuration tabs

3. **Risk Management Tab**
   
   | Setting | Default | Recommended | Description |
   |---------|---------|-------------|-------------|
   | Max Position Size | 10% | 5-15% | Maximum % of portfolio per position |
   | Max Daily Loss | 2% | 1-3% | Stop trading if daily loss exceeds this |
   | Max Portfolio Exposure | 30% | 20-40% | Maximum % of portfolio invested |
   | Max Trades Per Day | 10 | 5-20 | Limit on number of trades |
   | Min Confidence | 70% | 60-80% | Minimum LLM confidence to execute |

4. **Trading Settings Tab**
   
   | Setting | Default | Description |
   |---------|---------|-------------|
   | Symbols | AAPL, TSLA, NVDA | Watchlist symbols (comma-separated) |
   | Check Interval | 60 seconds | How often to check symbols |
   | Market Open | 09:30 | Market open time (ET) |
   | Market Close | 16:00 | Market close time (ET) |
   | Dry Run | false | If true, no real orders placed |

5. **LLM Configuration Tab**
   
   | Setting | Default | Description |
   |---------|---------|-------------|
   | Model | gemma-3-4b | LLM model name |
   | Base URL | http://localhost:1234/v1 | LM Studio endpoint |
   | Temperature | 0.7 | Sampling temperature (0.0-1.0) |
   | Max Tokens | 500 | Maximum response length |
   | Timeout | 30 | Request timeout (seconds) |

6. **Alerts Tab**
   
   Enable email and/or Slack notifications for:
   - Trade executions
   - Risk violations
   - Significant P&L changes
   - Daily summaries
   - System errors

7. **Backtesting Tab**
   
   | Setting | Default | Description |
   |---------|---------|-------------|
   | Commission | 0.0% | Commission per trade |
   | Slippage | 0.1% | Expected slippage |

### Programmatic Configuration

```python
from wawatrader.config_ui import ConfigurationManager

config = ConfigurationManager()

# Update risk settings
config.save_config('risk.max_position_size_percent', 15.0)
config.save_config('risk.max_daily_loss_percent', 3.0)

# Update watchlist
config.save_config('trading.symbols', ["AAPL", "MSFT", "GOOGL"])

# Update LLM settings
config.save_config('llm.temperature', 0.5)
config.save_config('llm.max_tokens', 1000)

# View current config
print(config.get_config())

# View change history
history = config.get_history(limit=10)
for change in history:
    print(f"{change['timestamp']}: {change['key']} = {change['new_value']}")
```

---

## Running Backtests

Backtesting validates your strategy on historical data before risking real money.

### Using Demo Script

```bash
python scripts/demo_backtesting.py
```

This will:
- Load 9 months of historical data
- Run trading strategy simulation
- Calculate performance metrics
- Generate visualization charts

### Custom Backtest

```python
from wawatrader.backtester import Backtester
from datetime import datetime

# Create backtester
backtest = Backtester(
    symbols=['AAPL', 'TSLA', 'NVDA'],
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 10, 1),
    initial_cash=100000.0,
    commission_percent=0.0,
    slippage_percent=0.1
)

# Run simulation
results = backtest.run()

# View results
print(f"Total Return: {results.total_return:.2%}")
print(f"Sharpe Ratio: {results.sharpe_ratio:.2f}")
print(f"Max Drawdown: {results.max_drawdown:.2%}")
print(f"Win Rate: {results.win_rate:.2%}")
print(f"Total Trades: {results.total_trades}")

# Plot results
backtest.plot_results()
```

### Interpreting Results

**Good Strategy Indicators:**
- ✅ Total Return > 10% annually
- ✅ Sharpe Ratio > 1.0
- ✅ Max Drawdown < 15%
- ✅ Win Rate > 50%
- ✅ Consistent returns (not one lucky trade)

**Red Flags:**
- ❌ High volatility (Sharpe < 0.5)
- ❌ Large drawdowns (> 20%)
- ❌ Low win rate (< 40%)
- ❌ Most profit from one trade
- ❌ Strategy works only in bull markets

### Optimization Tips

1. **Test Multiple Time Periods**
   ```python
   # Bull market (2023)
   backtest_bull = Backtester(symbols, datetime(2023,1,1), datetime(2023,12,31))
   
   # Bear market (2022)
   backtest_bear = Backtester(symbols, datetime(2022,1,1), datetime(2022,12,31))
   
   # Mixed market (2024)
   backtest_mixed = Backtester(symbols, datetime(2024,1,1), datetime(2024,10,1))
   ```

2. **Test Different Symbols**
   ```python
   # Tech stocks
   tech = Backtester(['AAPL', 'MSFT', 'GOOGL'], ...)
   
   # Blue chips
   bluechip = Backtester(['SPY', 'QQQ', 'DIA'], ...)
   
   # Growth stocks
   growth = Backtester(['TSLA', 'NVDA', 'AMD'], ...)
   ```

3. **Adjust Risk Parameters**
   ```python
   # Conservative
   config.save_config('risk.max_position_size_percent', 5.0)
   
   # Moderate
   config.save_config('risk.max_position_size_percent', 10.0)
   
   # Aggressive
   config.save_config('risk.max_position_size_percent', 20.0)
   ```

---

## Paper Trading

### Starting Paper Trading

```bash
# Terminal 1: Start LM Studio server
# (Use LM Studio GUI)

# Terminal 2: Start dashboard
python -m wawatrader.dashboard

# Terminal 3: Start trading agent
python -m wawatrader.trading_agent
```

### What Happens During Trading

1. **Market Hours Check**
   - Agent only trades during configured market hours
   - Default: 9:30 AM - 4:00 PM ET

2. **Symbol Monitoring**
   - Every 60 seconds (default), agent checks each symbol
   - Fetches latest price data
   - Calculates technical indicators

3. **LLM Analysis**
   - Sends market data to LLM
   - Receives trading recommendation
   - Extracts action (BUY/SELL/HOLD), confidence, reasoning

4. **Risk Validation**
   - Checks all 5 risk rules
   - If any rule fails, trade is rejected
   - Rejection reason is logged

5. **Order Execution**
   - If approved, market order is placed
   - Order status is tracked
   - Trade is recorded in database

6. **Notifications**
   - Alert sent via email/Slack
   - Dashboard updated in real-time

### Monitoring Active Trading

**Dashboard View:**
- Real-time portfolio value chart
- Current positions table
- Daily P&L summary
- Recent trades list

**Terminal Output:**
```
[2024-10-22 10:30:15] Checking AAPL...
[2024-10-22 10:30:16] Price: $150.25
[2024-10-22 10:30:16] RSI: 45.2 (OVERSOLD)
[2024-10-22 10:30:16] MACD: BUY signal
[2024-10-22 10:30:17] LLM recommends: BUY (confidence: 75%)
[2024-10-22 10:30:17] Risk check: APPROVED
[2024-10-22 10:30:18] Order placed: BUY 50 AAPL @ $150.25
[2024-10-22 10:30:18] Alert sent: Trade execution
```

### Pausing/Stopping Trading

```bash
# Graceful stop (Ctrl+C)
# - Finishes current symbol check
# - Closes all pending orders
# - Saves state to database

# Emergency stop
# - Kill process (not recommended)
# - May leave orders in uncertain state
```

### Daily Routine

**Morning (Before Market Open):**
1. Check LM Studio is running
2. Review configuration (any changes needed?)
3. Check yesterday's performance
4. Start trading agent

**During Market Hours:**
1. Monitor dashboard periodically
2. Review trade decisions
3. Check for risk violations
4. Respond to alerts

**Evening (After Market Close):**
1. Review daily summary alert
2. Analyze trades in database
3. Check system logs for errors
4. Plan adjustments for tomorrow

---

## Monitoring Performance

### Real-Time Dashboard

Access at http://localhost:8050

**Portfolio Value Chart:**
- Shows portfolio value over time
- Updates every 30 seconds
- Hover for exact values

**Positions Table:**
- Symbol, quantity, entry price
- Current price, market value
- Unrealized P&L ($ and %)
- Color-coded: green (profit), red (loss)

**P&L Summary:**
- Today's P&L
- Total unrealized P&L
- Realized P&L (from closed positions)
- Total return %

**Technical Indicators:**
- RSI chart (14-period)
- MACD chart
- Bollinger Bands
- Volume analysis

### Database Queries

```python
from wawatrader.database import get_database

db = get_database()

# Get today's trades
trades = db.get_trades(
    start_date='2024-10-22',
    end_date='2024-10-22'
)

for trade in trades:
    print(f"{trade['symbol']}: {trade['side']} {trade['quantity']} @ ${trade['price']}")

# Get winning trades
decisions = db.get_decisions(executed=True)
winning = [d for d in decisions if d['action'] == 'SELL' and d['shares'] > 0]

print(f"Win rate: {len(winning)/len(decisions)*100:.1f}%")

# Export to CSV for analysis
db.export_to_csv('trades', 'trades_october.csv')
db.export_to_csv('decisions', 'decisions_october.csv')
```

### Performance Metrics

```python
from wawatrader.backtester import calculate_metrics

# Get portfolio values over time
snapshots = db.get_performance_snapshots()
values = [s['portfolio_value'] for s in snapshots]

# Calculate metrics
metrics = calculate_metrics(values, initial_value=100000.0)

print(f"Total Return: {metrics['total_return']:.2%}")
print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {metrics['max_drawdown']:.2%}")
print(f"Volatility: {metrics['volatility']:.2%}")
```

---

## Managing Alerts

### Email Alerts

1. **Gmail Setup**
   ```bash
   # Enable 2-Factor Authentication in Google Account
   # Generate App Password:
   # 1. Go to https://myaccount.google.com/apppasswords
   # 2. Select "Mail" and "Other"
   # 3. Copy generated password
   
   export ALERT_EMAIL_ENABLED=true
   export ALERT_EMAIL_FROM="your_email@gmail.com"
   export ALERT_EMAIL_PASSWORD="your_app_password"
   export ALERT_EMAIL_TO="recipient@example.com"
   ```

2. **Other Email Providers**
   ```bash
   # Outlook/Office 365
   export ALERT_EMAIL_SMTP_SERVER="smtp.office365.com"
   export ALERT_EMAIL_SMTP_PORT=587
   
   # Yahoo
   export ALERT_EMAIL_SMTP_SERVER="smtp.mail.yahoo.com"
   export ALERT_EMAIL_SMTP_PORT=587
   ```

### Slack Alerts

1. **Create Slack Webhook**
   - Go to https://api.slack.com/apps
   - Click "Create New App"
   - Select "From scratch"
   - Name: "WawaTrader Alerts"
   - Choose workspace
   - Click "Incoming Webhooks"
   - Toggle "Activate Incoming Webhooks"
   - Click "Add New Webhook to Workspace"
   - Select channel (e.g., #trading-alerts)
   - Copy webhook URL

2. **Configure WawaTrader**
   ```bash
   export ALERT_SLACK_ENABLED=true
   export ALERT_SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
   ```

### Alert Types

**Trade Alerts** (every trade):
```
🔔 TRADE EXECUTED
Symbol: AAPL
Action: BUY
Quantity: 50 shares
Price: $150.25
Total Cost: $7,512.50
Time: 2024-10-22 10:30:18
```

**Risk Alerts** (violations):
```
⚠️ RISK VIOLATION
Position size for AAPL exceeds limit
Position: 15.2% of portfolio
Limit: 10.0%
Action: REJECTED
Time: 2024-10-22 11:15:42
```

**P&L Alerts** (significant changes):
```
📈 P&L ALERT
Portfolio value increased 2.5%
Previous: $100,000
Current: $102,500
Change: +$2,500
Time: 2024-10-22 15:45:30
```

**Daily Summary** (end of day):
```
📊 DAILY SUMMARY - 2024-10-22

Total Trades: 8
Total P&L: +$2,150 (+2.15%)
Win Rate: 75.0%
Portfolio Value: $102,150

Top Performers:
• AAPL: +$1,200 (+8.5%)
• NVDA: +$800 (+5.2%)

Worst Performers:
• TSLA: -$350 (-2.1%)
```

**Error Alerts** (system issues):
```
🚨 SYSTEM ERROR
LM Studio connection failed
Error: Connection refused
Time: 2024-10-22 12:00:00
Action: Using technical indicators only
```

### Customizing Alerts

```python
from wawatrader.alerts import get_alert_manager

alerts = get_alert_manager()

# Send custom alert
alerts.send_custom_alert(
    subject="Custom Alert",
    message="Portfolio reached $110,000 milestone!",
    severity="MEDIUM"
)

# View alert history
history = alerts.get_alert_history(limit=50, alert_type="trade")
for alert in history:
    print(f"{alert['timestamp']}: {alert['message']}")
```

---

## Best Practices

### Risk Management

1. **Start Conservative**
   - Begin with 5% position sizes
   - Keep daily loss limit at 1-2%
   - Trade only 2-3 symbols initially

2. **Gradual Scaling**
   - After 1 month of profitable trading, increase position size to 10%
   - After 3 months, consider adding more symbols
   - Never exceed 20% position size

3. **Diversification**
   - Trade at least 3 different symbols
   - Avoid correlated stocks (e.g., all tech)
   - Consider different sectors

4. **Loss Management**
   - If daily loss limit hit, stop trading for the day
   - Review what went wrong
   - Adjust strategy before resuming

### Strategy Optimization

1. **Backtest First**
   - Always backtest new strategies
   - Test on at least 6 months of data
   - Verify on different market conditions

2. **Paper Trade Duration**
   - Minimum 1 month of paper trading
   - Ideal: 3-6 months
   - Track all metrics (return, Sharpe, drawdown)

3. **LLM Temperature**
   - Lower (0.3-0.5): More conservative, consistent
   - Higher (0.7-0.9): More creative, varied
   - Start with 0.7, adjust based on results

4. **Confidence Threshold**
   - Higher threshold (80%+): Fewer trades, higher quality
   - Lower threshold (60%): More trades, potentially lower quality
   - Monitor win rate to optimize

### System Maintenance

1. **Daily Checks**
   - Verify LM Studio is running
   - Check system logs for errors
   - Review alert history

2. **Weekly Reviews**
   - Analyze trading performance
   - Review rejected trades (were they good calls?)
   - Adjust configuration if needed

3. **Monthly Tasks**
   - Backup databases
   - Review and archive old logs
   - Update software dependencies
   - Rerun backtests with new data

4. **Database Maintenance**
   ```bash
   # Vacuum database monthly
   sqlite3 wawatrader.db "VACUUM;"
   
   # Backup before major changes
   cp wawatrader.db wawatrader_backup_$(date +%Y%m%d).db
   ```

---

## FAQ

**Q: How much money do I need to start?**

A: Paper trading is free! Start with $100,000 virtual cash (Alpaca default). For live trading (not recommended yet), minimum is $2,000 for a margin account, but $10,000+ is recommended for proper diversification.

**Q: What symbols should I trade?**

A: Start with liquid, well-known stocks:
- **Safe**: SPY, QQQ, IWM (ETFs)
- **Tech**: AAPL, MSFT, GOOGL
- **Growth**: TSLA, NVDA, AMD

Avoid: Penny stocks, low-volume stocks, highly volatile stocks

**Q: How often should I check the dashboard?**

A: During market hours, check every 1-2 hours. The system runs automatically, but monitoring helps you learn and catch any issues.

**Q: What if LM Studio crashes?**

A: The trading agent will:
1. Detect LM Studio is unavailable
2. Fall back to technical indicators only
3. Send alert to notify you
4. Continue operating in "safe mode"

Restart LM Studio and the agent will automatically reconnect.

**Q: Can I trade after hours?**

A: By default, no. The system only trades during market hours (9:30 AM - 4:00 PM ET). You can modify this in the configuration, but after-hours trading has wider spreads and lower liquidity.

**Q: How do I know if my strategy is working?**

A: Track these metrics after 30 days:
- **Good**: Total return > 2%, Sharpe > 0.5, Win rate > 50%
- **Excellent**: Total return > 5%, Sharpe > 1.0, Win rate > 60%

Also compare to buy-and-hold SPY. If you're underperforming SPY, stick with index funds.

**Q: Should I use auto-trading or manual approval?**

A: Start with auto-trading in paper mode. The risk manager provides sufficient protection. For live trading (future), consider adding manual approval for large trades.

**Q: What if I get too many risk rejections?**

A: This is good! Risk rejections protect you. However, if >80% of trades are rejected:
1. Lower confidence threshold (e.g., 70% → 65%)
2. Increase position size limit slightly
3. Review rejected trades - were they actually good?

**Q: How do I add a new symbol to the watchlist?**

A:
```bash
# Option 1: Web UI
# Go to http://localhost:5001
# Click "Trading" tab
# Update "Symbols" field
# Click "Save"

# Option 2: Python
from wawatrader.config_ui import ConfigurationManager
config = ConfigurationManager()
current = config.get_config('trading.symbols')
current.append('GOOGL')
config.save_config('trading.symbols', current)
```

**Q: Can I run multiple trading agents?**

A: Yes! Run separate instances with different symbols:
```bash
# Terminal 1
export TRADING_SYMBOLS="AAPL,MSFT"
python -m wawatrader.trading_agent

# Terminal 2
export TRADING_SYMBOLS="TSLA,NVDA"
python -m wawatrader.trading_agent
```

Each instance uses the same database, so positions are tracked centrally.

**Q: How do I export trading data for tax purposes?**

A:
```python
from wawatrader.database import get_database
db = get_database()

# Export all trades for 2024
db.export_to_csv('trades', 'trades_2024.csv')

# Filter in Excel/Sheets by date range
# Columns: symbol, side, quantity, price, commission, timestamp
```

**Q: What's the difference between "dry run" and paper trading?**

A:
- **Dry Run**: Simulates trades but doesn't send orders to Alpaca. Use for testing logic changes.
- **Paper Trading**: Sends orders to Alpaca's paper trading environment. Use for realistic testing.

**Q: How do I know if LLM analysis is adding value?**

A: Run two backtests:
1. With LLM analysis (current system)
2. Without LLM (technical indicators only)

Compare results. If LLM version has higher Sharpe ratio and lower drawdown, it's adding value.

**Q: My trades are getting rejected due to buying power. What's wrong?**

A: Check:
1. Do you have enough cash? (`client.get_account()['cash']`)
2. Are you trying to buy too many shares?
3. Is another position using up buying power?

Adjust position sizes or wait for trades to close.

**Q: How do I update WawaTrader to the latest version?**

A:
```bash
# Stop trading agent (Ctrl+C)

# Pull latest code
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Run tests
pytest tests/ -v

# Restart trading agent
python -m wawatrader.trading_agent
```

---

## Getting Help

- **Documentation**: Check docs/ folder
- **GitHub Issues**: https://github.com/yourusername/WawaTrader/issues
- **Email Support**: support@wawatrader.com
- **Community**: Join our Discord/Slack

---

**Happy Trading! 📈**

Remember: Start with paper trading, test thoroughly, and never risk more than you can afford to lose.

---

**Last Updated**: October 22, 2025
