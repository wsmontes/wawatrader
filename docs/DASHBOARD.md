# Performance Dashboard

Real-time monitoring interface for WawaTrader built with Plotly Dash.

## Quick Start

```bash
# Run the dashboard
python scripts/run_dashboard.py

# Open browser to http://localhost:8050
```

## Features

### 📊 Real-Time Metrics
- **Portfolio Value** - Live portfolio tracking with daily change
- **Daily P&L** - Today's profit/loss in $ and %
- **Open Positions** - Current position count and value
- **Buying Power** - Available buying power and cash

### 📈 Charts & Visualizations
- **Portfolio History** - 30-day value chart
- **Position Allocation** - Pie chart breakdown by symbol
- **Technical Indicators** - Candlestick charts with SMA, RSI, MACD

### 📋 Data Tables
- **Current Positions** - Symbol, quantity, entry price, P&L
- **Recent Trades** - Last 20 orders with timestamps

### ⚙️ Configuration
- Auto-refresh every 30 seconds
- Responsive Bootstrap layout
- Mobile-friendly design
- Works with paper or live accounts

## Installation

Dashboard requires additional dependencies:

```bash
pip install dash dash-bootstrap-components
```

Or install from requirements.txt:

```bash
pip install -r requirements.txt
```

## Usage

### Option 1: Run Script

```bash
python scripts/run_dashboard.py
```

### Option 2: Python Code

```python
from wawatrader.dashboard import Dashboard

dashboard = Dashboard(data_dir='trading_data')
dashboard.run(
    host='127.0.0.1',
    port=8050,
    debug=False
)
```

### Option 3: Standalone

```python
python -m wawatrader.dashboard
```

## Dashboard Components

### Summary Cards (Top Row)
1. **Portfolio Value**
   - Total portfolio value
   - Daily change ($ and %)
   - Color-coded (green/red)

2. **Today's P&L**
   - Daily profit/loss
   - Percentage change
   - Auto-updates

3. **Open Positions**
   - Number of positions
   - Total position value
   - Live tracking

4. **Buying Power**
   - Available buying power
   - Cash balance
   - Account status

### Charts
1. **Portfolio Value Over Time**
   - 30-day historical chart
   - Area chart with fill
   - Hover tooltips
   - Date range selector

2. **Position Allocation**
   - Pie chart by symbol
   - Interactive legend
   - Percentage breakdown
   - Value display

3. **Technical Indicators** (Per Symbol)
   - Candlestick price chart
   - SMA 20/50 overlays
   - RSI indicator (0-100)
   - MACD with histogram
   - Symbol dropdown selector

### Data Tables
1. **Current Positions**
   - Symbol, Qty, Avg Entry, Current Price
   - Market Value, P&L ($), P&L (%)
   - Color-coded profits/losses
   - Sortable columns

2. **Recent Trades**
   - Time, Symbol, Side (BUY/SELL)
   - Quantity, Price, Status
   - Color-coded by side
   - Pagination (10 per page)
   - Last 20 trades displayed

## Technical Details

### Technology Stack
- **Dash** - Web framework
- **Plotly** - Interactive charts
- **Bootstrap** - Responsive layout
- **Alpaca API** - Real-time data

### Data Flow
```
Alpaca API → Dashboard → Plotly Charts → Browser
     ↓           ↓            ↓
  Account    Callbacks    Auto-refresh
   Data      (30s)        (30s)
```

### Update Mechanism
- Interval component triggers every 30 seconds
- Callbacks fetch fresh data from Alpaca
- Charts and tables update automatically
- No manual refresh needed

## Example Output

### Dashboard View
```
┌─────────────────────────────────────────────────────────┐
│  🤖 WawaTrader Dashboard                                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Portfolio Value    Daily P&L      Open Positions      │
│  $125,450.00        +$2,345.50     3                   │
│  +$3,450 (+2.8%)    +1.9%          $98,500             │
│                                                         │
│  Portfolio Value Chart    │  Position Allocation       │
│  ┌─────────────────┐     │  ┌──────────────┐         │
│  │  ╱╲    ╱╲       │     │  │  ◉ AAPL 45%  │         │
│  │ ╱  ╲  ╱  ╲      │     │  │  ◉ MSFT 35%  │         │
│  │╱    ╲╱    ╲     │     │  │  ◉ GOOGL 20% │         │
│  └─────────────────┘     │  └──────────────┘         │
│                                                         │
│  Current Positions                                      │
│  ┌───────────────────────────────────────────────────┐ │
│  │Symbol│Qty│Entry  │Current│Value    │P&L      │%  ││ │
│  │AAPL  │100│$150.00│$165.00│$16,500  │+$1,500  │+10││ │
│  │MSFT  │50 │$280.00│$295.00│$14,750  │+$750    │+5 ││ │
│  └───────────────────────────────────────────────────┘ │
│                                                         │
│  Recent Trades                                          │
│  ┌───────────────────────────────────────────────────┐ │
│  │Time     │Symbol│Side│Qty│Price   │Status        ││ │
│  │14:23:45 │AAPL  │BUY │100│$150.00 │FILLED        ││ │
│  │13:15:22 │MSFT  │BUY │50 │$280.00 │FILLED        ││ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Configuration

### Port Configuration
Default: `http://localhost:8050`

Change port:
```python
dashboard.run(port=8080)  # Use port 8080
```

### Host Configuration
```python
# Local only (default)
dashboard.run(host='127.0.0.1')

# Network accessible
dashboard.run(host='0.0.0.0')
```

### Debug Mode
```python
# Development (hot reload)
dashboard.run(debug=True)

# Production
dashboard.run(debug=False)
```

## Troubleshooting

### Dashboard won't start
**Cause**: Missing dependencies or port conflict  
**Solution**:
```bash
pip install dash dash-bootstrap-components
# Or check if port 8050 is in use
lsof -i :8050
```

### No data showing
**Cause**: Alpaca API issues or no positions  
**Solution**:
- Verify `.env` has correct API keys
- Check account is active
- Ensure you have some trade history

### Charts not updating
**Cause**: Browser cache or callback errors  
**Solution**:
- Hard refresh browser (Cmd+Shift+R)
- Check browser console for errors
- Verify Alpaca API is responding

### Slow performance
**Cause**: Too many data points or network issues  
**Solution**:
- Reduce history period
- Check network connection
- Increase refresh interval

## Advanced Usage

### Custom Refresh Interval

Edit `wawatrader/dashboard.py`:
```python
dcc.Interval(
    id='interval-component',
    interval=60*1000,  # 60 seconds instead of 30
    n_intervals=0
)
```

### Custom Theme

Use different Bootstrap theme:
```python
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],  # Dark theme
    title="WawaTrader Dashboard"
)
```

Available themes:
- BOOTSTRAP (default)
- DARKLY (dark mode)
- FLATLY (flat design)
- PULSE (modern)
- SOLAR (yellow/blue)

### Add Custom Metrics

Extend dashboard with custom callbacks:
```python
@self.app.callback(
    Output("custom-metric", "children"),
    [Input("interval-component", "n_intervals")]
)
def update_custom_metric(n):
    # Your custom calculation
    return "Custom Value"
```

## Browser Compatibility

✅ **Supported Browsers**:
- Chrome/Edge (recommended)
- Firefox
- Safari
- Opera
- Mobile browsers (iOS Safari, Chrome Mobile)

⚠️ **Not Supported**:
- IE 11 or older

## Performance Tips

1. **Limit History Period**
   - Use 30 days instead of 1 year
   - Reduces data loading time

2. **Increase Refresh Interval**
   - 30s for active trading
   - 60s for monitoring
   - 300s for passive tracking

3. **Reduce Chart Complexity**
   - Disable unused indicators
   - Simplify chart layouts

4. **Use Dedicated Browser**
   - Keep dashboard in separate browser
   - Reduces interference with other tabs

## Security Notes

⚠️ **Important**:
- Dashboard runs on localhost by default (127.0.0.1)
- Only accessible from your computer
- Contains sensitive trading data
- Don't expose to public internet
- Use VPN if accessing remotely

### Network Access
If you need network access (e.g., other devices):
```python
# Enable network access (use with caution)
dashboard.run(host='0.0.0.0', port=8050)

# Add authentication (recommended)
# Implement before exposing to network
```

## Integration

### With Trading Agent
```python
from wawatrader.trading_agent import TradingAgent
from wawatrader.dashboard import Dashboard
import threading

# Run trading agent in background
agent = TradingAgent(symbols=["AAPL"], dry_run=False)
threading.Thread(target=agent.run_forever).start()

# Run dashboard in foreground
dashboard = Dashboard()
dashboard.run()
```

### With Backtester
```python
# Run backtest first
from wawatrader.backtester import Backtester

bt = Backtester(symbols=["AAPL"], ...)
stats = bt.run()
bt.save_results()

# Then view results in dashboard
# (Dashboard will show live account, not backtest)
```

## See Also

- [Backtesting Framework](./BACKTESTING.md) - Historical testing
- [Trading Agent](../wawatrader/trading_agent.py) - Live trading
- [Risk Management](../wawatrader/risk_manager.py) - Risk rules
- [Technical Indicators](../wawatrader/indicators.py) - Analysis

## Demo

Run the demo to see features:
```bash
python scripts/demo_dashboard.py
```

Then start the actual dashboard:
```bash
python scripts/run_dashboard.py
```
