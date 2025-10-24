# WawaTrader Test Suite

## 📊 Overview

Comprehensive test suite for WawaTrader with **9 test files** covering core functionality.

**Total Coverage**: ~3,200 lines of tests  
**Test Framework**: pytest  
**Status**: ✅ Production-ready

---

## 🗂️ Test Organization

```
tests/
├── helpers/
│   └── __init__.py          # Reusable test utilities (mock data, fixtures, assertions)
├── test_template.py         # AI-friendly template for new tests
├── test_alerts.py           # Alert system (675 lines, 28 tests)
├── test_learning_engine.py  # Learning system (532 lines, 16 tests)
├── test_database.py         # Database operations (527 lines, comprehensive)
├── test_config_ui.py        # Configuration UI (395 lines)
├── test_backtester.py       # Backtesting engine (373 lines)
├── test_indicators.py       # Technical indicators (366 lines)
├── test_risk_manager.py     # Risk management (337 lines, 12 tests)
├── test_enhanced_intelligence.py  # Enhanced intelligence (88 lines, async)
└── test_intelligence.py     # Market intelligence (71 lines, async)
```

---

## 🚀 Quick Start

### Run All Tests
```bash
pytest
```

### Run Specific Test File
```bash
pytest tests/test_risk_manager.py
```

### Run Specific Test
```bash
pytest tests/test_risk_manager.py::TestPositionLimits::test_reject_oversized_position
```

### Run with Verbose Output
```bash
pytest -v
```

### Run with Coverage
```bash
pytest --cov=wawatrader --cov-report=html
```

---

## 📚 Test Helpers

All tests can use these reusable utilities from `tests/helpers/`:

### Mock Data Generators

```python
from tests.helpers import (
    create_mock_ohlcv,        # Generate realistic price data
    create_mock_trade,         # Create trade objects
    create_mock_position,      # Create position objects
    create_mock_account        # Create account objects
)

# Example
df = create_mock_ohlcv("AAPL", days=100, start_price=150.0)
trade = create_mock_trade("AAPL", "buy", 10, 150.0)
```

### Mock API Clients

```python
from tests.helpers import mock_alpaca_client, mock_llm_bridge

# Mock Alpaca with custom data
client = mock_alpaca_client(
    account_data=create_mock_account(equity=50000.0),
    positions=[create_mock_position("AAPL", 10, 150.0, 155.0)]
)

account = client.get_account()  # Returns mock data
```

### Assertions

```python
from tests.helpers import (
    assert_valid_trade,        # Validate trade structure
    assert_valid_position,     # Validate position structure
    assert_dataframe_valid     # Validate DataFrame
)

# Example
assert_valid_trade(trade)
assert_dataframe_valid(df, ['open', 'high', 'low', 'close'])
```

### Fixtures

```python
from tests.helpers import temp_database, sample_ohlcv, mock_client

def test_with_fixtures(temp_database, sample_ohlcv, mock_client):
    # temp_database: Temporary SQLite database
    # sample_ohlcv: 100 days of AAPL data
    # mock_client: Mock Alpaca client
    pass
```

---

## 🎯 Test Coverage by Component

| Component | Test File | Lines | Tests | Status |
|-----------|-----------|-------|-------|--------|
| **Alerts** | test_alerts.py | 675 | 28 | ✅ Complete |
| **Learning** | test_learning_engine.py | 532 | 16 | ✅ Complete |
| **Database** | test_database.py | 527 | ~20 | ✅ Complete |
| **Config** | test_config_ui.py | 395 | ~15 | ✅ Complete |
| **Backtest** | test_backtester.py | 373 | ~12 | ✅ Complete |
| **Indicators** | test_indicators.py | 366 | ~30 | ✅ Complete |
| **Risk** | test_risk_manager.py | 337 | 12 | ✅ Complete |
| **Intelligence** | test_enhanced_intelligence.py | 88 | 1 | ✅ Async |
| **Intelligence** | test_intelligence.py | 71 | 1 | ✅ Async |

---

## 🤖 AI Agent Guide

### Creating New Tests

1. **Copy the template**:
   ```bash
   cp tests/test_template.py tests/test_new_feature.py
   ```

2. **Follow the structure**:
   - Imports at top
   - Test classes for organization
   - One test per specific behavior
   - Use helpers for mock data

3. **Use helpers**:
   ```python
   from tests.helpers import create_mock_ohlcv, assert_valid_trade
   
   def test_something():
       df = create_mock_ohlcv("AAPL")  # Get test data
       result = process(df)
       assert_valid_trade(result)       # Validate result
   ```

### Common Patterns

#### Test with Mock Data
```python
def test_indicator():
    df = create_mock_ohlcv("AAPL", days=100)
    result = calculate_sma(df, period=20)
    assert len(result) == 100
```

#### Test with Fixtures
```python
@pytest.fixture
def risk_manager():
    return RiskManager(max_position=0.1)

def test_position_check(risk_manager):
    result = risk_manager.check_position_size(0.15)
    assert result == False
```

#### Test Exceptions
```python
def test_invalid_input():
    with pytest.raises(ValueError, match="Invalid symbol"):
        process_symbol(None)
```

#### Async Tests
```python
@pytest.mark.asyncio
async def test_async_operation():
    result = await async_function()
    assert result is not None
```

#### Parametrized Tests
```python
@pytest.mark.parametrize("input,expected", [
    (10, 20),
    (20, 40),
    (30, 60),
])
def test_multiple_inputs(input, expected):
    assert process(input) == expected
```

---

## 📖 Test Documentation Standards

### Test Function Docstrings

```python
def test_specific_behavior():
    """
    Test: Component performs expected action under condition.
    
    This test verifies that [specific behavior] works correctly
    when [specific condition].
    
    Pattern: Arrange-Act-Assert
    """
    # Arrange
    setup_data = ...
    
    # Act
    result = function_under_test(setup_data)
    
    # Assert
    assert result == expected
```

### Test Class Docstrings

```python
class TestFeatureGroup:
    """
    Test suite for Feature functionality.
    
    Tests verify that Feature correctly handles:
    - Normal operation
    - Error conditions
    - Edge cases
    """
```

---

## ⚠️ Testing Best Practices

### DO ✅

- Use helpers for mock data (DRY principle)
- One assertion concept per test
- Clear test names (`test_reject_oversized_position`)
- Test both success and failure cases
- Use fixtures for setup/teardown
- Mock external APIs (Alpaca, OpenAI)
- Document complex test logic

### DON'T ❌

- Make real API calls in tests
- Test multiple concepts in one test
- Use hardcoded test data (use helpers)
- Skip cleanup in fixtures
- Ignore edge cases
- Write tests without docstrings

---

## 🔍 Debugging Tests

### Show Print Statements
```bash
pytest -s
```

### Stop on First Failure
```bash
pytest -x
```

### Run Last Failed
```bash
pytest --lf
```

### Show Full Diff
```bash
pytest -vv
```

### Debug Mode (drop into debugger on failure)
```bash
pytest --pdb
```

---

## 📊 Test Metrics

### Current Statistics
- **Total test files**: 9
- **Total lines**: ~3,200
- **Test functions**: ~135
- **Test classes**: ~40
- **Async tests**: 2
- **Fixtures**: ~30

### Deleted (Code Cleanup)
- ❌ `test_alpaca.py` (179 lines) - Manual script
- ❌ `test_orders.py` (110 lines) - Duplicate/broken
- ❌ `test_order_system.py` (117 lines) - Duplicate/broken
- ❌ `test_trading_agent.py` (100 lines) - Manual script
- ❌ `test_lm_studio.py` (84 lines) - Optional local LLM
- ❌ `test_system.py` (71 lines) - Basic check
- ❌ `test_dashboard_layout.py` (61 lines) - UI script
- ❌ `test_enhanced_dashboard.py` (58 lines) - UI runner

**Total removed**: 780 lines (18% reduction)

---

## 🎓 Learning Resources

### Pytest Documentation
- [Official Docs](https://docs.pytest.org/)
- [Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Parametrize](https://docs.pytest.org/en/stable/parametrize.html)
- [Mocking](https://docs.pytest.org/en/stable/monkeypatch.html)

### WawaTrader-Specific
- `tests/test_template.py` - Complete example file
- `tests/helpers/__init__.py` - All available helpers
- `docs/API.md` - Component documentation

---

## ✅ Test Quality Checklist

Before committing new tests:

- [ ] Tests follow naming convention (`test_<specific_behavior>`)
- [ ] Uses helpers for mock data (no hardcoded values)
- [ ] Has docstrings explaining what's being tested
- [ ] Tests both success and failure cases
- [ ] Uses appropriate fixtures
- [ ] Mocks external APIs
- [ ] Runs successfully with `pytest`
- [ ] No real API calls or side effects

---

*Last updated: Code cleanup phase - October 2025*
