# GitHub Copilot Instructions for WawaTrader

You are working on **WawaTrader**, a hybrid LLM-powered algorithmic trading system that combines technical analysis with Large Language Model sentiment analysis for paper trading via Alpaca Markets.

## 🎯 **Project Overview**

WawaTrader is a production-ready trading system with the following key characteristics:
- **Hybrid Intelligence**: Technical indicators (NumPy/Pandas) + LLM sentiment (Gemma 3 via LM Studio)
- **Safety First**: Multiple risk management layers, paper trading only
- **Modular Architecture**: Clean separation of concerns with singleton patterns
- **Comprehensive Monitoring**: Real-time dashboard, alerts, and logging
- **Test-Driven**: 95%+ test coverage with 134 passing tests

## 🏗️ **Architecture Patterns**

### **Core Architecture Flow**
```
User Interfaces (Flask/Dash) → LLM Layer (Gemma 3) → Trading Agent → Core Components → Data Layer → External APIs
```

### **Key Design Principles**
1. **LLM Never Decides Alone**: All trading decisions require numerical validation
2. **Fast Path for Numbers**: Technical indicators run in <1ms using vectorized operations
3. **Slow Path for Context**: LLM interpretation ~50-200ms, only when needed
4. **Fail-Safe Defaults**: System continues if LLM fails (fallback mode)
5. **Audit Everything**: All decisions logged with full context

## 📁 **Project Structure**

### **Core Modules** (`wawatrader/`)
- `alpaca_client.py` - Alpaca API wrapper with error handling
- `indicators.py` - Pure NumPy/Pandas technical analysis (no LLM)
- `llm_bridge.py` - LLM integration with validation
- `risk_manager.py` - Hard-coded safety rules (NO LLM override)
- `trading_agent.py` - Main orchestrator (trading loop)
- `backtester.py` - Historical simulation with realistic costs
- `dashboard.py` - Real-time Plotly/Dash monitoring
- `database.py` - SQLite data persistence
- `alerts.py` - Email/Slack notifications
- `config_ui.py` - Web-based configuration interface

### **Configuration** (`config/`)
- `settings.py` - Pydantic models with validation
- Environment variables via `.env` file

### **Scripts** (`scripts/`)
- `demo_*.py` - Feature demonstrations
- `run_*.py` - Launch scripts for production components

### **Tests** (`tests/`)
- Comprehensive test suite (134 tests, 95%+ coverage)
- Mock external dependencies for reliable testing

## 🔧 **Coding Standards & Patterns**

### **Import Standards**
```python
# Standard library first
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

# Third-party imports
import pandas as pd
import numpy as np
from loguru import logger
from pydantic import BaseModel, Field, field_validator

# Local imports (relative imports within package)
from wawatrader.alpaca_client import get_client
from wawatrader.indicators import analyze_dataframe
from config.settings import settings
```

### **Error Handling Patterns**

**Standard Exception Pattern:**
```python
def api_operation(self) -> Dict[str, Any]:
    """Operation with comprehensive error handling"""
    try:
        result = self.external_api.get_data()
        logger.info(f"✅ Operation successful: {result['status']}")
        return result
        
    except APIError as e:
        logger.error(f"❌ API Error: {e}")
        # Send alert for critical operations
        alerts = get_alert_manager()
        alerts.send_error_alert(str(e), "APIError")
        raise
        
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        raise
```

**Graceful Degradation Pattern:**
```python
def get_llm_analysis(self, data: Dict) -> Optional[Dict]:
    """LLM analysis with fallback"""
    try:
        return self.llm_bridge.analyze(data)
    except Exception as e:
        logger.warning(f"LLM analysis failed: {e}, using fallback")
        return {"sentiment": "neutral", "confidence": 50, "action": "hold"}
```

### **Logging Standards**

**Use loguru for structured logging:**
```python
from loguru import logger

# Success messages
logger.info(f"✅ Connected to Alpaca (Account: {account.id})")

# Warnings (non-critical issues)
logger.warning(f"⚠️ RSI overbought: {rsi:.1f}")

# Errors (with context)
logger.error(f"❌ Failed to execute {symbol} order: {error}")

# Debug (detailed info)
logger.debug(f"🔍 Technical analysis: RSI={rsi:.1f}, MACD={macd:.2f}")

# Trading decisions (special format)
logger.bind(DECISION=True).info(json.dumps(decision_dict))
```

### **Configuration Management**

**Always use settings singleton:**
```python
from config.settings import settings

# Access configuration
max_position = settings.risk.max_position_size
api_key = settings.alpaca.api_key
llm_model = settings.lm_studio.model
```

**Validation patterns:**
```python
class TradingConfig(BaseModel):
    """Config with validation"""
    min_confidence: int = Field(default=60, ge=0, le=100)
    
    @field_validator('min_confidence')
    @classmethod
    def validate_confidence(cls, v):
        if v < 0 or v > 100:
            raise ValueError("Confidence must be 0-100")
        return v
```

### **Data Processing Patterns**

**Technical Analysis (Pure NumPy/Pandas):**
```python
@staticmethod
def rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """RSI calculation - vectorized, no loops"""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))
```

**Data Validation:**
```python
def validate_price_data(self, data: pd.DataFrame) -> bool:
    """Validate price data integrity"""
    required_columns = ['open', 'high', 'low', 'close', 'volume']
    
    if not all(col in data.columns for col in required_columns):
        logger.error(f"Missing required columns: {required_columns}")
        return False
        
    if data.empty:
        logger.warning("Empty price data received")
        return False
        
    # Check for reasonable price values
    if (data['close'] <= 0).any():
        logger.error("Invalid price data: prices <= 0")
        return False
        
    return True
```

### **Risk Management Patterns**

**Hard-coded safety rules (NO LLM override):**
```python
def check_position_size(self, symbol: str, shares: int, price: float) -> RiskCheckResult:
    """CRITICAL: These rules are ABSOLUTE"""
    position_value = shares * price
    max_value = self.account_value * self.max_position_size
    
    if position_value > max_value:
        return RiskCheckResult(
            approved=False,
            reason=f"Position too large: ${position_value:,.2f} exceeds max ${max_value:,.2f}"
        )
    
    return RiskCheckResult(approved=True, reason="Position size OK")
```

### **LLM Integration Patterns**

**Structured prompts with validation:**
```python
def create_analysis_prompt(self, signals: Dict) -> str:
    """Convert numerical data to text for LLM"""
    return f"""
Analyze this market data and provide trading recommendation:

Price: ${signals['price']['close']:.2f}
RSI: {signals['momentum']['rsi']:.1f} (30=oversold, 70=overbought)
MACD: {signals['trend']['macd']:.2f}
Trend: {signals['trend']['direction']}

Respond with JSON only:
{{"sentiment": "bullish|bearish|neutral", "confidence": 0-100, "action": "buy|sell|hold", "reasoning": "brief explanation"}}
"""

def parse_llm_response(self, response: str) -> Optional[Dict]:
    """Parse and validate LLM JSON response"""
    try:
        data = json.loads(response)
        
        # Validate required fields
        required = ['sentiment', 'confidence', 'action', 'reasoning']
        if not all(field in data for field in required):
            logger.error(f"Missing required fields: {required}")
            return None
            
        # Validate values
        if data['sentiment'] not in ['bullish', 'bearish', 'neutral']:
            logger.error(f"Invalid sentiment: {data['sentiment']}")
            return None
            
        if not (0 <= data['confidence'] <= 100):
            logger.error(f"Invalid confidence: {data['confidence']}")
            return None
            
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON from LLM: {e}")
        return None
```

### **Database Patterns**

**Singleton pattern with connection management:**
```python
class Database:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._setup_database()
        self._initialized = True
```

**Transaction patterns:**
```python
def save_trade(self, trade_data: Dict) -> bool:
    """Save trade with transaction safety"""
    try:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trades (symbol, action, shares, price, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (trade_data['symbol'], trade_data['action'], 
                  trade_data['shares'], trade_data['price'], 
                  trade_data['timestamp']))
            conn.commit()
            logger.info(f"✅ Trade saved: {trade_data['symbol']}")
            return True
            
    except Exception as e:
        logger.error(f"❌ Failed to save trade: {e}")
        return False
```

## 🧪 **Testing Patterns**

### **Test Structure**
```python
"""
Test Module Name

Tests the [component] functionality including:
- [Feature 1]
- [Feature 2]
- Error handling and edge cases
"""

import pytest
from unittest.mock import Mock, patch
from wawatrader.component import ComponentClass

class TestComponentClass:
    """Test suite for ComponentClass"""
    
    @pytest.fixture
    def component(self):
        """Setup component for testing"""
        return ComponentClass()
    
    def test_normal_operation(self, component):
        """Test normal operation flow"""
        result = component.method()
        assert result is not None
        assert result['status'] == 'success'
    
    def test_error_handling(self, component):
        """Test error handling"""
        with patch('wawatrader.component.external_api') as mock_api:
            mock_api.side_effect = Exception("API Error")
            result = component.method()
            assert result is None  # Graceful failure
    
    @patch('wawatrader.component.logger')
    def test_logging(self, mock_logger, component):
        """Test logging behavior"""
        component.method()
        mock_logger.info.assert_called()
```

### **Mock External Dependencies**
```python
@patch('wawatrader.alpaca_client.tradeapi.REST')
def test_alpaca_client(self, mock_rest):
    """Test Alpaca client with mocked API"""
    mock_api = Mock()
    mock_api.get_account.return_value = Mock(
        account_number='TEST123',
        buying_power=100000.0
    )
    mock_rest.return_value = mock_api
    
    client = AlpacaClient()
    account = client.get_account()
    
    assert account['account_number'] == 'TEST123'
    assert account['buying_power'] == 100000.0
```

## 🚨 **Security & Safety Rules**

### **Financial Safety**
- **NEVER** use real money without extensive testing
- **ALWAYS** validate position sizes against account value
- **NEVER** override risk management rules via LLM
- **ALWAYS** use paper trading for development/testing

### **API Security**
- **Store API keys in .env file only** (never in code)
- **Use environment variable validation**
- **Implement rate limiting for API calls**
- **Log API errors but not sensitive data**

### **LLM Safety**
- **Never trust LLM numerical outputs directly**
- **Always validate LLM responses against schemas**
- **Implement fallback modes if LLM fails**
- **Use structured prompts with clear constraints**

## 📊 **Performance Guidelines**

### **Optimization Patterns**
- Use vectorized NumPy/Pandas operations (no loops)
- Cache frequently accessed data with TTL
- Minimize API calls through batching
- Use async operations for I/O-bound tasks

### **Memory Management**
- Use generators for large datasets
- Clean up DataFrames after processing
- Implement connection pooling for databases
- Monitor memory usage in long-running processes

### **Real-time Requirements**
- Technical indicators: <1ms
- LLM analysis: <200ms (acceptable)
- API calls: <5s timeout
- Dashboard updates: 30s intervals

## 🔍 **Debugging Guidelines**

### **Debug Mode Activation**
```python
# Enable debug logging
export LOG_LEVEL=DEBUG

# Enable LLM request/response logging
export LLM_DEBUG=true

# Enable API call logging
export API_DEBUG=true
```

### **Common Debugging Patterns**
```python
# Add debug checkpoints
logger.debug(f"🔍 Processing {symbol}: price=${price:.2f}, rsi={rsi:.1f}")

# Log function entry/exit
def critical_function(self, symbol: str):
    logger.debug(f"🔍 ENTER: {self.__class__.__name__}.critical_function({symbol})")
    try:
        result = self.process(symbol)
        logger.debug(f"🔍 EXIT: result={result}")
        return result
    except Exception as e:
        logger.debug(f"🔍 ERROR: {e}")
        raise
```

## 📈 **Feature Development Workflow**

### **Adding New Features**
1. **Design**: Update architecture docs if needed
2. **Test First**: Write tests before implementation
3. **Implement**: Follow existing patterns
4. **Document**: Add docstrings and examples
5. **Demo**: Create demo script in `scripts/`
6. **Integration**: Add to main trading loop if applicable

### **Code Review Checklist**
- [ ] Error handling with proper logging
- [ ] Input validation and type hints
- [ ] Unit tests with good coverage
- [ ] Documentation strings
- [ ] Follows project patterns
- [ ] No hardcoded values (use config)
- [ ] Proper resource cleanup
- [ ] Security considerations

## 🎯 **Common Tasks**

When working on WawaTrader, you will frequently need to:

1. **Add new technical indicators** → Follow `indicators.py` patterns
2. **Integrate new LLM models** → Extend `llm_bridge.py`
3. **Add risk checks** → Extend `risk_manager.py` (keep rules hard-coded)
4. **Create new alerts** → Add to `alerts.py` alert types
5. **Add dashboard widgets** → Extend `dashboard.py` with Plotly components
6. **Improve backtesting** → Enhance `backtester.py` metrics
7. **Add configuration options** → Update `settings.py` with validation

## 🚀 **Deployment Considerations**

- **Development**: Use paper trading with mock data
- **Testing**: Run full test suite before deployment
- **Production**: Requires monitoring, logging, and alerts
- **Scaling**: Consider database performance and API rate limits

---

**Remember**: WawaTrader is designed for paper trading and educational purposes. Always prioritize safety, testing, and risk management over performance or complexity. The system should fail safely and provide clear audit trails for all decisions.