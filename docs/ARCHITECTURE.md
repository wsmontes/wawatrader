# WawaTrader Architecture

## System Overview

WawaTrader is a hybrid AI trading system that combines Large Language Model (LLM) analysis with traditional algorithmic trading. The system follows a layered architecture with clear separation of concerns.

## Core Principles

1. **LLM Never Decides Alone**: All trading decisions require validation from numerical risk rules
2. **Fast Path for Numbers**: Technical indicators run in <1ms using NumPy/Pandas
3. **Slow Path for Context**: LLM interpretation ~50-200ms, only when needed
4. **Fail-Safe Defaults**: System continues operating if LLM fails
5. **Audit Everything**: All decisions logged with explanations

## Architecture Layers

```
┌──────────────────────────────────────────────────────────┐
│                   User Interfaces                         │
│  ┌──────────────────┐         ┌──────────────────┐       │
│  │  Configuration   │         │   Performance    │       │
│  │      UI          │         │    Dashboard     │       │
│  │  (Flask/Web)     │         │  (Plotly/Dash)   │       │
│  └──────────────────┘         └──────────────────┘       │
└──────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────┐
│                      LLM Layer                            │
│  ┌──────────────────────────────────────────────────┐   │
│  │  LLM Bridge (llm_bridge.py)                       │   │
│  │  • Natural language analysis                      │   │
│  │  • Market sentiment interpretation                │   │
│  │  • Trade reasoning generation                     │   │
│  │  • Connection: LM Studio (Gemma 3 4B)            │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────┐
│                   Trading Agent                           │
│  ┌──────────────────────────────────────────────────┐   │
│  │  TradingAgent (trading_agent.py)                  │   │
│  │  • Main orchestration loop                        │   │
│  │  • Watchlist monitoring                           │   │
│  │  • Decision coordination                          │   │
│  │  • Order execution                                │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────┐
│                  Core Components                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │ Technical   │  │  LLM Bridge │  │    Risk     │      │
│  │ Indicators  │  │             │  │  Manager    │      │
│  │ (NumPy)     │  │ (OpenAI)    │  │  (Rules)    │      │
│  └─────────────┘  └─────────────┘  └─────────────┘      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │   Order     │  │  Backtester │  │   Alerts    │      │
│  │ Execution   │  │ (Vectorized)│  │ (Email/Slack)      │
│  └─────────────┘  └─────────────┘  └─────────────┘      │
└──────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────┐
│                    Data Layer                             │
│  ┌──────────────────┐  ┌──────────────────┐             │
│  │  Trading DB      │  │  Configuration   │             │
│  │  (SQLite)        │  │  DB (SQLite)     │             │
│  │  • Trades        │  │  • Settings      │             │
│  │  • Decisions     │  │  • History       │             │
│  │  • LLM Logs      │  │  • Audit Trail   │             │
│  │  • Performance   │  │                  │             │
│  └──────────────────┘  └──────────────────┘             │
└──────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────┐
│                 External Services                         │
│  ┌──────────────────┐         ┌──────────────────┐      │
│  │   Alpaca API     │         │   LM Studio      │      │
│  │   (Markets)      │         │   (Local LLM)    │      │
│  └──────────────────┘         └──────────────────┘      │
└──────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Trading Agent (`trading_agent.py`)

**Responsibilities:**
- Main event loop coordination
- Watchlist monitoring
- Technical indicator calculation
- LLM analysis coordination
- Risk validation
- Order execution
- Performance tracking

**Key Methods:**
- `run()`: Main trading loop
- `_check_symbols()`: Analyze watchlist
- `_analyze_symbol()`: Single symbol analysis
- `_execute_decision()`: Execute approved trades

**Interactions:**
- Uses: `TechnicalIndicators`, `LLMBridge`, `RiskManager`, `AlpacaClient`
- Updates: `Database`, `AlertManager`

### 2. Technical Indicators (`indicators.py`)

**Responsibilities:**
- Calculate technical indicators
- Generate trading signals
- Fast numerical analysis

**Implemented Indicators:**
- **Trend**: SMA, EMA
- **Momentum**: RSI, MACD
- **Volatility**: Bollinger Bands, ATR, Standard Deviation
- **Volume**: Volume Ratio, OBV

**Performance:**
- All calculations: < 1ms per symbol
- Vectorized operations (NumPy/Pandas)
- Cached results when appropriate

### 3. LLM Bridge (`llm_bridge.py`)

**Responsibilities:**
- Communicate with LM Studio
- Format prompts with market data
- Parse LLM responses
- Extract structured decisions

**Prompt Structure:**
```
Market Data:
- Symbol: AAPL
- Current Price: $150.00
- Technical Indicators:
  • RSI: 65.4
  • MACD: BUY signal
  • Bollinger: Near lower band
  
Question: Should we BUY, SELL, or HOLD?
Provide: action, confidence (0-100), reasoning
```

**Response Parsing:**
- Extracts action (BUY/SELL/HOLD)
- Confidence percentage
- Reasoning text
- Handles malformed responses

### 4. Risk Manager (`risk_manager.py`)

**Responsibilities:**
- Validate all trading decisions
- Enforce risk limits
- Track portfolio exposure
- Monitor daily losses

**Risk Rules:**
1. **Position Size**: Max 10% per position
2. **Daily Loss**: Max 2% portfolio loss
3. **Portfolio Exposure**: Max 30% total
4. **Trade Frequency**: Max 10 trades/day
5. **Confidence**: Min 70% threshold

**Validation Flow:**
```python
decision = {"symbol": "AAPL", "action": "BUY", "shares": 100}

# Check all rules
position_ok = risk_manager.check_position_size(...)
loss_ok = risk_manager.check_daily_loss_limit(...)
exposure_ok = risk_manager.check_portfolio_exposure(...)
frequency_ok = risk_manager.check_trade_frequency(...)
confidence_ok = risk_manager.check_confidence_threshold(...)

# All must pass
approved = position_ok and loss_ok and exposure_ok and frequency_ok and confidence_ok
```

### 5. Order Execution (`alpaca_client.py`)

**Responsibilities:**
- Execute market orders
- Track order status
- Manage positions
- Retrieve account data

**Order Flow:**
```
1. Trading Agent decides to buy
2. Risk Manager approves
3. AlpacaClient submits order
4. Order status tracked
5. Database updated
6. Alert sent
```

**Error Handling:**
- Retry logic for network errors
- Validation before submission
- Order status polling
- Failure alerts

### 6. Database (`database.py`)

**Responsibilities:**
- Persist all trading activity
- Store LLM interactions
- Track performance
- Export data

**Schema:**
- **trades**: Executed trades with P&L
- **decisions**: All trading decisions (executed or not)
- **llm_interactions**: Prompts and responses
- **performance_snapshots**: Daily portfolio values

**Export Formats:**
- CSV for spreadsheet analysis
- JSON for programmatic access

### 7. Backtester (`backtester.py`)

**Responsibilities:**
- Historical strategy testing
- Performance metrics calculation
- Visualization
- Parameter optimization

**Features:**
- Vectorized calculations (fast)
- Multiple symbols
- Commission/slippage modeling
- Trade analysis
- Sharpe ratio, max drawdown, win rate

### 8. Performance Dashboard (`dashboard.py`)

**Responsibilities:**
- Real-time portfolio monitoring
- Interactive charts
- Position tracking
- Technical indicator visualization

**Components:**
- Portfolio value chart (time series)
- Position table (live updates)
- P&L summary
- Technical indicator charts

**Technology:**
- Plotly Dash (reactive framework)
- Auto-refresh every 30 seconds
- Responsive layout

### 9. Alert System (`alerts.py`)

**Responsibilities:**
- Real-time notifications
- Trade execution alerts
- Risk violation alerts
- Daily summaries
- Error notifications

**Delivery Channels:**
- Email (SMTP)
- Slack (webhooks)

**Alert Types:**
1. **Trade**: Buy/sell execution
2. **Risk**: Limit violations
3. **P&L**: Significant changes
4. **Daily Summary**: End-of-day report
5. **Error**: System failures

### 10. Configuration UI (`config_ui.py`)

**Responsibilities:**
- Web-based configuration
- Parameter validation
- Change history tracking
- Real-time updates

**Configuration Categories:**
- **Risk**: Position limits, loss limits
- **Trading**: Symbols, intervals, hours
- **LLM**: Model, temperature, tokens
- **Alerts**: Email/Slack settings
- **Backtesting**: Commission, slippage

**Technology:**
- Flask web framework
- SQLite persistence
- HTML/CSS UI
- REST API

## Data Flow

### Trading Decision Flow

```
1. Timer triggers symbol check
   ↓
2. Fetch latest price data (Alpaca API)
   ↓
3. Calculate technical indicators (TechnicalIndicators)
   ↓
4. Send data to LLM for analysis (LLMBridge)
   ↓
5. Parse LLM response → decision
   ↓
6. Validate decision (RiskManager)
   ↓
7a. If approved → Execute order (AlpacaClient)
7b. If rejected → Log reason, skip
   ↓
8. Record decision in database (Database)
   ↓
9. Send notification (AlertManager)
   ↓
10. Update dashboard metrics
```

### Backtesting Flow

```
1. Load historical price data (Alpaca API)
   ↓
2. For each time period:
   a. Calculate indicators
   b. Generate LLM decision (simulated)
   c. Validate with risk manager
   d. Simulate order execution
   e. Track portfolio value
   ↓
3. Calculate performance metrics
   ↓
4. Generate visualization
   ↓
5. Return results
```

## Performance Characteristics

### Latency

| Component | Latency | Notes |
|-----------|---------|-------|
| Technical Indicators | < 1ms | NumPy vectorized |
| LLM Analysis | 50-200ms | Network + inference |
| Risk Validation | < 1ms | Pure Python rules |
| Order Execution | 50-100ms | API call |
| Database Write | < 10ms | SQLite local |
| Total Decision | ~100-300ms | End-to-end |

### Throughput

- **Symbols/minute**: 30-60 (with LLM)
- **Symbols/minute**: 1000+ (without LLM)
- **Database writes/second**: 100+
- **Dashboard refresh rate**: 30 seconds

### Resource Usage

- **Memory**: ~500MB (with LLM loaded)
- **CPU**: < 5% during market hours
- **Disk**: ~100MB (database + logs)
- **Network**: Minimal (API calls only)

## Error Handling

### Failure Modes

1. **LLM Unavailable**
   - Fallback: Technical indicators only
   - Action: Alert administrator
   - Recovery: Retry with exponential backoff

2. **API Connection Lost**
   - Fallback: Use cached data (if recent)
   - Action: Halt trading, send alert
   - Recovery: Automatic reconnection

3. **Database Write Failure**
   - Fallback: Log to file
   - Action: Continue trading, send alert
   - Recovery: Retry write later

4. **Risk Limit Exceeded**
   - Fallback: Reject trade
   - Action: Log rejection, send alert
   - Recovery: Wait for limits to reset

5. **Invalid Configuration**
   - Fallback: Use defaults
   - Action: Alert administrator
   - Recovery: Fix configuration

## Security

### API Keys

- Stored in environment variables
- Never committed to version control
- Alpaca paper trading only (no real money)

### Database

- Local SQLite (no network exposure)
- File permissions: owner read/write only
- Regular backups recommended

### Web UI

- Localhost only (no external access)
- No authentication (local use)
- For production: Add authentication layer

## Scalability

### Current Limits

- **Symbols**: 10-20 recommended
- **Check Interval**: 60 seconds minimum
- **Database Size**: Unlimited (SQLite handles TB+)
- **Concurrent Users**: 1 (single instance)

### Scaling Options

1. **More Symbols**: Add more watchlist symbols
2. **Faster Checks**: Reduce interval (increases API usage)
3. **Multiple Strategies**: Run separate instances
4. **Distributed**: Use PostgreSQL, message queue
5. **Cloud**: Deploy to AWS/GCP for 24/7 operation

## Testing Strategy

### Unit Tests

- Each component tested independently
- Mocked external dependencies
- 134 tests, 95%+ coverage

### Integration Tests

- Component interaction tests
- Real API calls (paper trading)
- End-to-end workflow validation

### Backtesting

- Historical validation
- Multiple time periods
- Various market conditions

### Paper Trading

- 3-6 months recommended
- Monitor all metrics
- Compare to buy-and-hold

## Monitoring

### Key Metrics

1. **Trading Performance**
   - Total return
   - Sharpe ratio
   - Max drawdown
   - Win rate

2. **System Health**
   - API connection status
   - LLM response time
   - Database size
   - Error rate

3. **Risk Metrics**
   - Current exposure
   - Daily P&L
   - Position sizes
   - Trade frequency

### Alerts

- Trade execution (all trades)
- Risk violations (immediate)
- Daily summary (end of day)
- System errors (immediate)

## Future Enhancements

### Planned Features

1. **Multi-Strategy Support**
   - Different strategies per symbol
   - Strategy performance comparison
   - Dynamic strategy allocation

2. **Advanced Risk Models**
   - Value at Risk (VaR)
   - Conditional VaR (CVaR)
   - Correlation analysis

3. **Machine Learning**
   - Price prediction models
   - Sentiment analysis
   - Pattern recognition

4. **Options Trading**
   - Options chain analysis
   - Strategy builder
   - Greeks calculation

5. **Social Integration**
   - Twitter sentiment
   - Reddit mentions
   - News aggregation

### Infrastructure

1. **Containerization**
   - Docker images
   - Docker Compose orchestration
   - Kubernetes deployment

2. **CI/CD Pipeline**
   - Automated testing
   - Deployment automation
   - Version management

3. **Cloud Deployment**
   - AWS/GCP/Azure support
   - Auto-scaling
   - High availability

4. **Monitoring**
   - Prometheus metrics
   - Grafana dashboards
   - Log aggregation

## Conclusion

WawaTrader's architecture is designed for:
- **Safety**: Multiple validation layers
- **Observability**: Comprehensive logging and alerts
- **Maintainability**: Clear component separation
- **Extensibility**: Easy to add new features
- **Performance**: Optimized for low latency

The hybrid LLM + algorithmic approach provides the best of both worlds: contextual market understanding with numerical safety guarantees.
