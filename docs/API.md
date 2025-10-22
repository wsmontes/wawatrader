# WawaTrader API Reference

## Table of Contents

- [Alpaca Client](#alpaca-client)
- [Technical Indicators](#technical-indicators)
- [LLM Bridge](#llm-bridge)
- [Risk Manager](#risk-manager)
- [Database](#database)
- [Backtester](#backtester)
- [Alert Manager](#alert-manager)
- [Configuration Manager](#configuration-manager)

---

## Alpaca Client

### `AlpacaClient`

Interface to Alpaca Markets API for paper trading.

#### Constructor

```python
AlpacaClient(
    api_key: str = None,
    secret_key: str = None,
    paper: bool = True
)
```

**Parameters:**
- `api_key` (str, optional): Alpaca API key. Defaults to `ALPACA_API_KEY` env var.
- `secret_key` (str, optional): Alpaca secret key. Defaults to `ALPACA_SECRET_KEY` env var.
- `paper` (bool): Use paper trading. Defaults to `True`.

#### Methods

##### `get_account() -> dict`

Get account information.

**Returns:**
```python
{
    'id': 'account-id',
    'cash': 100000.0,
    'portfolio_value': 105000.0,
    'buying_power': 200000.0,
    'equity': 105000.0
}
```

##### `get_positions() -> List[dict]`

Get all open positions.

**Returns:**
```python
[
    {
        'symbol': 'AAPL',
        'qty': 100,
        'avg_entry_price': 150.0,
        'current_price': 155.0,
        'market_value': 15500.0,
        'unrealized_pl': 500.0,
        'unrealized_plpc': 0.0333
    }
]
```

##### `get_position(symbol: str) -> dict`

Get position for a specific symbol.

**Parameters:**
- `symbol` (str): Stock symbol (e.g., "AAPL")

**Returns:** Same structure as position in `get_positions()`

##### `get_latest_price(symbol: str) -> float`

Get latest trade price for symbol.

**Parameters:**
- `symbol` (str): Stock symbol

**Returns:** Current price as float

##### `get_historical_data(symbol: str, start: datetime, end: datetime, timeframe: str = '1Day') -> pd.DataFrame`

Get historical bar data.

**Parameters:**
- `symbol` (str): Stock symbol
- `start` (datetime): Start date
- `end` (datetime): End date
- `timeframe` (str): Bar timeframe ('1Min', '1Hour', '1Day', etc.)

**Returns:** DataFrame with columns: `['timestamp', 'open', 'high', 'low', 'close', 'volume']`

##### `place_market_order(symbol: str, qty: int, side: str) -> dict`

Place a market order.

**Parameters:**
- `symbol` (str): Stock symbol
- `qty` (int): Number of shares
- `side` (str): 'buy' or 'sell'

**Returns:**
```python
{
    'id': 'order-id',
    'symbol': 'AAPL',
    'qty': 100,
    'side': 'buy',
    'type': 'market',
    'status': 'filled',
    'filled_avg_price': 150.0
}
```

##### `get_order(order_id: str) -> dict`

Get order status.

**Parameters:**
- `order_id` (str): Order ID from `place_market_order()`

**Returns:** Same structure as `place_market_order()`

---

## Technical Indicators

### `TechnicalIndicators`

Calculate technical indicators from price data.

#### Constructor

```python
TechnicalIndicators(df: pd.DataFrame)
```

**Parameters:**
- `df` (pd.DataFrame): Price data with columns `['close', 'high', 'low', 'volume']`

#### Methods

##### `sma(period: int = 20) -> pd.Series`

Simple Moving Average.

**Parameters:**
- `period` (int): Lookback period (default: 20)

**Returns:** Series of SMA values

##### `ema(period: int = 20) -> pd.Series`

Exponential Moving Average.

**Parameters:**
- `period` (int): Lookback period (default: 20)

**Returns:** Series of EMA values

##### `rsi(period: int = 14) -> pd.Series`

Relative Strength Index.

**Parameters:**
- `period` (int): Lookback period (default: 14)

**Returns:** Series of RSI values (0-100)

##### `macd(fast: int = 12, slow: int = 26, signal: int = 9) -> dict`

Moving Average Convergence Divergence.

**Parameters:**
- `fast` (int): Fast EMA period (default: 12)
- `slow` (int): Slow EMA period (default: 26)
- `signal` (int): Signal line period (default: 9)

**Returns:**
```python
{
    'macd': pd.Series,      # MACD line
    'signal': pd.Series,    # Signal line
    'histogram': pd.Series  # MACD - Signal
}
```

##### `bollinger_bands(period: int = 20, std_dev: float = 2.0) -> dict`

Bollinger Bands.

**Parameters:**
- `period` (int): Moving average period (default: 20)
- `std_dev` (float): Standard deviations (default: 2.0)

**Returns:**
```python
{
    'upper': pd.Series,   # Upper band
    'middle': pd.Series,  # Middle band (SMA)
    'lower': pd.Series    # Lower band
}
```

##### `atr(period: int = 14) -> pd.Series`

Average True Range.

**Parameters:**
- `period` (int): Lookback period (default: 14)

**Returns:** Series of ATR values

##### `volume_ratio(period: int = 20) -> pd.Series`

Volume ratio vs average.

**Parameters:**
- `period` (int): Lookback period for average (default: 20)

**Returns:** Series of volume ratios (current / average)

##### `obv() -> pd.Series`

On-Balance Volume.

**Returns:** Series of OBV values

##### `get_signals() -> dict`

Get composite trading signals.

**Returns:**
```python
{
    'rsi': 'OVERSOLD',      # or 'OVERBOUGHT', 'NEUTRAL'
    'macd': 'BUY',          # or 'SELL', 'NEUTRAL'
    'bb': 'NEAR_LOWER',     # or 'NEAR_UPPER', 'MIDDLE'
    'overall': 'BULLISH'    # or 'BEARISH', 'NEUTRAL'
}
```

---

## LLM Bridge

### `LLMBridge`

Interface to LM Studio for market analysis.

#### Constructor

```python
LLMBridge(
    base_url: str = None,
    model: str = None,
    temperature: float = 0.7,
    max_tokens: int = 500
)
```

**Parameters:**
- `base_url` (str, optional): LM Studio URL. Defaults to env var.
- `model` (str, optional): Model name. Defaults to env var.
- `temperature` (float): Sampling temperature (0.0-1.0)
- `max_tokens` (int): Max response tokens

#### Methods

##### `analyze_market_data(symbol: str, price: float, indicators: dict) -> dict`

Analyze market data and generate trading decision.

**Parameters:**
- `symbol` (str): Stock symbol
- `price` (float): Current price
- `indicators` (dict): Technical indicators from `TechnicalIndicators.get_signals()`

**Returns:**
```python
{
    'action': 'BUY',           # or 'SELL', 'HOLD'
    'confidence': 75,          # 0-100
    'reasoning': 'RSI oversold, MACD bullish crossover...'
}
```

##### `test_connection() -> bool`

Test LM Studio connection.

**Returns:** `True` if connected, `False` otherwise

---

## Risk Manager

### `RiskManager`

Validate trading decisions against risk rules.

#### Constructor

```python
RiskManager(
    max_position_size_percent: float = 10.0,
    max_daily_loss_percent: float = 2.0,
    max_portfolio_exposure_percent: float = 30.0,
    max_trades_per_day: int = 10,
    min_confidence_threshold: float = 70.0
)
```

**Parameters:**
- `max_position_size_percent` (float): Max % of portfolio per position
- `max_daily_loss_percent` (float): Max % daily loss allowed
- `max_portfolio_exposure_percent` (float): Max % total exposure
- `max_trades_per_day` (int): Max number of trades per day
- `min_confidence_threshold` (float): Min LLM confidence to execute

#### Methods

##### `check_position_size(symbol: str, shares: int, price: float, portfolio_value: float) -> Tuple[bool, str]`

Check if position size is within limits.

**Parameters:**
- `symbol` (str): Stock symbol
- `shares` (int): Number of shares
- `price` (float): Current price
- `portfolio_value` (float): Total portfolio value

**Returns:**
```python
(True, "Position size OK")  # if approved
(False, "Position size 15.0% exceeds limit of 10.0%")  # if rejected
```

##### `check_daily_loss_limit(current_pnl: float, portfolio_value: float) -> Tuple[bool, str]`

Check if daily loss is within limits.

**Parameters:**
- `current_pnl` (float): Today's P&L
- `portfolio_value` (float): Total portfolio value

**Returns:** `(approved: bool, reason: str)`

##### `check_portfolio_exposure(positions: List[dict], portfolio_value: float) -> Tuple[bool, str]`

Check total portfolio exposure.

**Parameters:**
- `positions` (List[dict]): List of positions from `AlpacaClient.get_positions()`
- `portfolio_value` (float): Total portfolio value

**Returns:** `(approved: bool, reason: str)`

##### `check_trade_frequency(trades_today: int) -> Tuple[bool, str]`

Check if daily trade limit exceeded.

**Parameters:**
- `trades_today` (int): Number of trades executed today

**Returns:** `(approved: bool, reason: str)`

##### `check_confidence_threshold(confidence: float) -> Tuple[bool, str]`

Check if LLM confidence meets threshold.

**Parameters:**
- `confidence` (float): LLM confidence (0-100)

**Returns:** `(approved: bool, reason: str)`

##### `validate_decision(decision: dict, account_info: dict) -> Tuple[bool, str]`

Validate complete trading decision against all rules.

**Parameters:**
- `decision` (dict): Decision from LLMBridge
- `account_info` (dict): Account info from AlpacaClient

**Returns:** `(approved: bool, reason: str)`

---

## Database

### `Database`

Persist trading activity and performance.

#### Constructor

```python
Database(db_path: str = "wawatrader.db")
```

**Parameters:**
- `db_path` (str): Path to SQLite database file

#### Methods

##### `record_trade(symbol: str, side: str, quantity: int, price: float, commission: float = 0.0, order_id: str = None) -> int`

Record executed trade.

**Parameters:**
- `symbol` (str): Stock symbol
- `side` (str): 'buy' or 'sell'
- `quantity` (int): Number of shares
- `price` (float): Execution price
- `commission` (float): Commission paid
- `order_id` (str, optional): Order ID from Alpaca

**Returns:** Trade ID

##### `record_decision(symbol: str, action: str, shares: int, confidence: float, reasoning: str, risk_approved: bool, executed: bool) -> int`

Record trading decision.

**Parameters:**
- `symbol` (str): Stock symbol
- `action` (str): 'buy', 'sell', or 'hold'
- `shares` (int): Number of shares
- `confidence` (float): LLM confidence
- `reasoning` (str): LLM reasoning
- `risk_approved` (bool): Risk manager approval
- `executed` (bool): Whether trade was executed

**Returns:** Decision ID

##### `record_llm_interaction(symbol: str, prompt: str, response: str, model: str, success: bool) -> int`

Record LLM API interaction.

**Parameters:**
- `symbol` (str): Stock symbol
- `prompt` (str): Prompt sent to LLM
- `response` (str): LLM response
- `model` (str): Model name
- `success` (bool): Whether request succeeded

**Returns:** Interaction ID

##### `record_performance_snapshot(date: str, portfolio_value: float, daily_pnl: float, daily_return_percent: float, total_return_percent: float)`

Record daily performance snapshot.

**Parameters:**
- `date` (str): Date (YYYY-MM-DD)
- `portfolio_value` (float): Total portfolio value
- `daily_pnl` (float): Today's P&L
- `daily_return_percent` (float): Today's return %
- `total_return_percent` (float): Total return %

##### `get_trades(symbol: str = None, start_date: str = None, end_date: str = None, limit: int = None) -> List[dict]`

Get trade history.

**Parameters:**
- `symbol` (str, optional): Filter by symbol
- `start_date` (str, optional): Start date (YYYY-MM-DD)
- `end_date` (str, optional): End date (YYYY-MM-DD)
- `limit` (int, optional): Max number of results

**Returns:** List of trade dicts

##### `get_decisions(symbol: str = None, executed: bool = None, limit: int = None) -> List[dict]`

Get decision history.

**Parameters:**
- `symbol` (str, optional): Filter by symbol
- `executed` (bool, optional): Filter by execution status
- `limit` (int, optional): Max number of results

**Returns:** List of decision dicts

##### `export_to_csv(table: str, filepath: str)`

Export table to CSV.

**Parameters:**
- `table` (str): Table name ('trades', 'decisions', etc.)
- `filepath` (str): Output file path

##### `export_to_json(table: str, filepath: str)`

Export table to JSON.

**Parameters:**
- `table` (str): Table name
- `filepath` (str): Output file path

---

## Backtester

### `Backtester`

Test trading strategies on historical data.

#### Constructor

```python
Backtester(
    symbols: List[str],
    start_date: datetime,
    end_date: datetime,
    initial_cash: float = 100000.0,
    commission_percent: float = 0.0,
    slippage_percent: float = 0.1
)
```

**Parameters:**
- `symbols` (List[str]): List of symbols to trade
- `start_date` (datetime): Backtest start date
- `end_date` (datetime): Backtest end date
- `initial_cash` (float): Starting capital
- `commission_percent` (float): Commission per trade (%)
- `slippage_percent` (float): Slippage per trade (%)

#### Methods

##### `run() -> BacktestResults`

Run backtest simulation.

**Returns:**
```python
BacktestResults(
    total_return=0.15,           # 15% return
    sharpe_ratio=1.25,           # Risk-adjusted return
    max_drawdown=-0.08,          # -8% max drawdown
    win_rate=0.60,               # 60% winning trades
    total_trades=50,             # Number of trades
    portfolio_values=[...],      # Daily portfolio values
    trades=[...]                 # Trade history
)
```

##### `plot_results()`

Generate performance visualization charts.

---

## Alert Manager

### `AlertManager`

Send notifications via email and Slack.

#### Constructor

```python
AlertManager(
    email_enabled: bool = False,
    email_from: str = None,
    email_password: str = None,
    email_to: str = None,
    slack_enabled: bool = False,
    slack_webhook_url: str = None
)
```

**Parameters:**
- `email_enabled` (bool): Enable email alerts
- `email_from` (str): Sender email address
- `email_password` (str): Email password/app password
- `email_to` (str): Recipient email address
- `slack_enabled` (bool): Enable Slack alerts
- `slack_webhook_url` (str): Slack webhook URL

#### Methods

##### `send_trade_alert(symbol: str, action: str, quantity: int, price: float, total_cost: float, severity: str = 'MEDIUM')`

Send trade execution alert.

**Parameters:**
- `symbol` (str): Stock symbol
- `action` (str): 'BUY' or 'SELL'
- `quantity` (int): Number of shares
- `price` (float): Execution price
- `total_cost` (float): Total cost/proceeds
- `severity` (str): 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'

##### `send_risk_alert(message: str, details: dict, severity: str = 'HIGH')`

Send risk violation alert.

**Parameters:**
- `message` (str): Alert message
- `details` (dict): Risk details
- `severity` (str): Alert severity

##### `send_pnl_alert(current_value: float, previous_value: float, change_percent: float, severity: str = 'MEDIUM')`

Send P&L change alert.

**Parameters:**
- `current_value` (float): Current portfolio value
- `previous_value` (float): Previous portfolio value
- `change_percent` (float): Change percentage
- `severity` (str): Alert severity

##### `send_daily_summary(total_trades: int, total_pnl: float, win_rate: float, portfolio_value: float, top_performers: List[dict] = None, worst_performers: List[dict] = None)`

Send daily summary report.

**Parameters:**
- `total_trades` (int): Number of trades today
- `total_pnl` (float): Today's P&L
- `win_rate` (float): Win rate (0-100)
- `portfolio_value` (float): End-of-day portfolio value
- `top_performers` (List[dict], optional): Best performing positions
- `worst_performers` (List[dict], optional): Worst performing positions

##### `send_error_alert(error_message: str, traceback_str: str = None, severity: str = 'CRITICAL')`

Send system error alert.

**Parameters:**
- `error_message` (str): Error description
- `traceback_str` (str, optional): Stack trace
- `severity` (str): Alert severity

##### `get_alert_history(limit: int = 100, alert_type: str = None) -> List[dict]`

Get alert history.

**Parameters:**
- `limit` (int): Max number of results
- `alert_type` (str, optional): Filter by type

**Returns:** List of alert dicts

---

## Configuration Manager

### `ConfigurationManager`

Manage system configuration via web UI or API.

#### Constructor

```python
ConfigurationManager(db_path: str = "wawatrader_config.db")
```

**Parameters:**
- `db_path` (str): Path to configuration database

#### Methods

##### `get_config(category: str = None, key: str = None) -> dict`

Get configuration values.

**Parameters:**
- `category` (str, optional): Config category ('risk', 'trading', etc.)
- `key` (str, optional): Specific key within category

**Returns:**
```python
{
    'risk': {
        'max_position_size_percent': 10.0,
        'max_daily_loss_percent': 2.0,
        ...
    },
    'trading': {
        'symbols': ['AAPL', 'TSLA', 'NVDA'],
        ...
    }
}
```

##### `save_config(key: str, value: Any, changed_by: str = 'system') -> bool`

Save configuration value.

**Parameters:**
- `key` (str): Config key (e.g., 'risk.max_position_size_percent')
- `value` (Any): New value
- `changed_by` (str): User/system identifier

**Returns:** `True` if saved, `False` if validation failed

##### `validate_config(key: str, value: Any) -> Tuple[bool, str]`

Validate configuration value.

**Parameters:**
- `key` (str): Config key
- `value` (Any): Value to validate

**Returns:** `(valid: bool, error_message: str)`

##### `get_history(limit: int = 100) -> List[dict]`

Get configuration change history.

**Parameters:**
- `limit` (int): Max number of results

**Returns:**
```python
[
    {
        'timestamp': '2024-10-22 14:30:00',
        'key': 'risk.max_position_size_percent',
        'old_value': '10.0',
        'new_value': '15.0',
        'changed_by': 'admin'
    }
]
```

---

## Utility Functions

### `get_database() -> Database`

Get singleton database instance.

**Returns:** Database instance

### `get_alert_manager() -> AlertManager`

Get singleton alert manager instance.

**Returns:** AlertManager instance

### `get_config_manager() -> ConfigurationManager`

Get singleton configuration manager instance.

**Returns:** ConfigurationManager instance

---

## Error Handling

All API methods may raise the following exceptions:

- `ConnectionError`: Network/API connection failed
- `ValueError`: Invalid parameter value
- `RuntimeError`: Operation failed
- `KeyError`: Required configuration missing

Always use try/except blocks:

```python
try:
    client = AlpacaClient()
    price = client.get_latest_price('AAPL')
except ConnectionError as e:
    logger.error(f"Failed to connect: {e}")
except ValueError as e:
    logger.error(f"Invalid parameter: {e}")
```

---

## Environment Variables

Required environment variables:

```bash
# Alpaca API
export ALPACA_API_KEY="your_api_key"
export ALPACA_SECRET_KEY="your_secret_key"
export ALPACA_PAPER=true

# LM Studio
export LM_STUDIO_BASE_URL="http://localhost:1234/v1"
export LM_STUDIO_MODEL="gemma-3-4b"

# Email Alerts (optional)
export ALERT_EMAIL_ENABLED=true
export ALERT_EMAIL_FROM="your_email@gmail.com"
export ALERT_EMAIL_PASSWORD="your_app_password"
export ALERT_EMAIL_TO="recipient@example.com"

# Slack Alerts (optional)
export ALERT_SLACK_ENABLED=true
export ALERT_SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

---

## Complete Example

```python
from wawatrader.alpaca_client import AlpacaClient
from wawatrader.indicators import TechnicalIndicators
from wawatrader.llm_bridge import LLMBridge
from wawatrader.risk_manager import RiskManager
from wawatrader.database import get_database
from wawatrader.alerts import get_alert_manager
from datetime import datetime, timedelta

# Initialize components
client = AlpacaClient()
risk = RiskManager()
llm = LLMBridge()
db = get_database()
alerts = get_alert_manager()

# Get market data
symbol = 'AAPL'
price = client.get_latest_price(symbol)
bars = client.get_historical_data(
    symbol,
    start=datetime.now() - timedelta(days=30),
    end=datetime.now()
)

# Calculate indicators
indicators = TechnicalIndicators(bars)
signals = indicators.get_signals()

# Get LLM analysis
decision = llm.analyze_market_data(symbol, price, signals)

# Validate with risk manager
account = client.get_account()
approved, reason = risk.validate_decision(decision, account)

if approved and decision['action'] == 'BUY':
    # Execute trade
    order = client.place_market_order(
        symbol=symbol,
        qty=10,
        side='buy'
    )
    
    # Record in database
    db.record_trade(
        symbol=symbol,
        side='buy',
        quantity=10,
        price=order['filled_avg_price'],
        order_id=order['id']
    )
    
    # Send alert
    alerts.send_trade_alert(
        symbol=symbol,
        action='BUY',
        quantity=10,
        price=order['filled_avg_price'],
        total_cost=order['filled_avg_price'] * 10
    )

# Record decision
db.record_decision(
    symbol=symbol,
    action=decision['action'],
    shares=10,
    confidence=decision['confidence'],
    reasoning=decision['reasoning'],
    risk_approved=approved,
    executed=approved
)
```
