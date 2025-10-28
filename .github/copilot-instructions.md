# GitHub Copilot Instructions for WawaTrader

You are working on **WawaTrader**, a hybrid LLM-powered algorithmic trading system that combines technical analysis with Large Language Model sentiment analysis for paper trading via Alpaca Markets.

## 🎯 **Project Overview**

WawaTrader is a production-ready trading system with:
- **Hybrid Intelligence**: Technical indicators + LLM sentiment analysis
- **Safety First**: Paper trading only, multiple risk management layers
- **Modular Architecture**: Clean separation of concerns
- **Test-Driven**: 95%+ test coverage

## 🏗️ **Core Architecture**

```
User Interfaces → LLM Layer → Trading Agent → Core Components → External APIs
```

### **Key Safety Principles**
1. **LLM Never Decides Alone**: All trading decisions require numerical validation
2. **Fail-Safe Defaults**: System continues if LLM fails (graceful degradation)
3. **Risk Rules are Absolute**: NO LLM override of risk management
4. **Audit Everything**: All decisions logged with full context

## 📁 **Project Structure & Organization Rules**

**REQUIRED FOLDER STRUCTURE** - Always maintain clean organization:

```
wawatrader/                 # Core trading components ONLY
├── __init__.py
├── alpaca_client.py
├── indicators.py
├── llm_bridge.py
├── risk_manager.py
├── trading_agent.py
├── dashboard.py
├── backtester.py
├── database.py
├── alerts.py
└── config_ui.py

config/                     # Configuration files ONLY
├── __init__.py
└── settings.py

scripts/                    # Executable scripts ONLY
├── __init__.py
├── run_*.py               # Production runners
└── demo_*.py              # Feature demos

tests/                      # All test files ONLY
├── __init__.py
├── test_*.py              # Unit tests
└── integration/           # Integration tests

docs/                       # All documentation ONLY
├── __init__.py
├── *.md                   # Architecture, API, guides
└── assets/                # Images, diagrams

examples/                   # Example code and tutorials
logs/                      # Runtime logs (gitignored)
trading_data/              # Market data cache
```

**ROOT DIRECTORY RULES** - Keep root clean:
- ✅ **ALLOWED**: README.md, SETUP.md, requirements.txt, setup.py, start.py, .env, .gitignore
- ❌ **FORBIDDEN**: Individual test files, scripts, docs, temporary files

**ENFORCEMENT GUIDELINES**:
1. **Test files** → MUST go in `tests/` folder (never in root)
2. **Documentation** → MUST go in `docs/` folder 
3. **Scripts** → MUST go in `scripts/` folder
4. **Status/progress files** → Should go in `docs/` or be deleted
5. **Temporary files** → Delete or add to .gitignore

## 🔧 **Essential Coding Standards**

### **Imports**
```python
# Standard library first, then third-party, then local
from typing import Dict, Any, Optional
import pandas as pd
from loguru import logger
from wawatrader.component import Class
from config.settings import settings
```

### **Error Handling**
```python
# Always use structured error handling with logging
try:
    result = operation()
    logger.info(f"✅ Success: {result}")
    return result
except SpecificError as e:
    logger.error(f"❌ Error: {e}")
    raise
```

### **Configuration**
```python
# Always use settings singleton
from config.settings import settings
max_position = settings.risk.max_position_size
```

### **LLM Integration**
```python
# Always validate LLM responses
def parse_llm_response(self, response: str) -> Optional[Dict]:
    try:
        data = json.loads(response)
        # Validate required fields and values
        return data if self._validate(data) else None
    except json.JSONDecodeError:
        return None
```

## 🚨 **Critical Safety Rules**

- **NEVER** use real money (paper trading only)
- **NEVER** override risk management via LLM
- **ALWAYS** validate LLM responses against schemas  
- **ALWAYS** store API keys in `.env` (never in code)
- **ALWAYS** use vectorized operations for technical indicators

## � **Documentation References**

For detailed information, check these existing docs:
- `docs/ARCHITECTURE.md` - System architecture and design patterns
- `docs/API.md` - API documentation and usage examples
- `docs/USER_GUIDE.md` - User interface and workflow guide
- `docs/DEPLOYMENT.md` - Production deployment guidelines
- `README.md` - Quick start and setup instructions
- `SETUP.md` - Development environment setup

## 🎯 **Common Development Tasks**

1. **Add indicators** → Extend `indicators.py` (pure NumPy/Pandas)
2. **Add LLM models** → Extend `llm_bridge.py`
3. **Add risk checks** → Extend `risk_manager.py` (hard-coded rules)
4. **Add alerts** → Extend `alerts.py`
5. **Add dashboard features** → Extend `dashboard.py` (Plotly/Dash)
6. **Add tests** → Follow existing patterns in `tests/`

## 🧪 **Testing**

Always write tests first:
```python
# Standard test structure
class TestComponent:
    @pytest.fixture
    def component(self):
        return Component()
    
    def test_normal_operation(self, component):
        result = component.method()
        assert result['status'] == 'success'
    
    def test_error_handling(self, component):
        # Test graceful failure
        pass
```

---

**Remember**: WawaTrader prioritizes safety and testing. When in doubt, check the existing documentation in `docs/` or follow established patterns in the codebase. For each python file run and for each script run, ensure that the venv is activated.