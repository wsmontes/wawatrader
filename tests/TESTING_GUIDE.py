"""
TEST TEMPLATE - AI-Friendly Testing Guide

This template demonstrates how to write tests for WawaTrader.
Copy this template when creating new test files.

AI Agents: This template shows you:
1. How to structure pytest tests
2. How to use test helpers
3. Common testing patterns
4. How to test async code
5. How to mock external APIs

================================================================================
TEMPLATE STRUCTURE
================================================================================

1. Imports (grouped: stdlib, third-party, local, test helpers)
2. Module-level docstring
3. Test classes (organized by feature)
4. Fixtures (test-specific setup)
5. Test functions (one concept per function)

================================================================================
NAMING CONVENTIONS
================================================================================

- Test files: test_<module>.py
- Test classes: Test<Feature>
- Test functions: test_<specific_behavior>
- Fixtures: <noun>_fixture or mock_<service>

Example:
    test_risk_manager.py
    └── class TestPositionLimits:
        ├── def test_reject_oversized_position():
        ├── def test_accept_normal_position():
        └── fixture: risk_manager()

================================================================================
"""

# ============================================================================
# IMPORTS
# ============================================================================

# Standard library
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Third-party
import pytest
import pandas as pd

# WawaTrader modules
from wawatrader.example_module import ExampleClass
from config.settings import settings

# Test helpers
from tests.helpers import (
    create_mock_ohlcv,
    create_mock_trade,
    create_mock_account,
    mock_alpaca_client,
    assert_valid_trade,
    assert_dataframe_valid
)


# ============================================================================
# TEST CLASS PATTERN
# ============================================================================

class TestExampleFeature:
    """
    Test suite for ExampleFeature functionality.
    
    This class groups related tests for a specific feature or component.
    Use classes to organize tests logically.
    """
    
    @pytest.fixture
    def example_instance(self):
        """
        Fixture: Provides a configured ExampleClass instance.
        
        Fixtures run before each test method and provide setup.
        They're automatically cleaned up after the test.
        
        Yields:
            ExampleClass: Configured instance for testing
        """
        instance = ExampleClass(setting1="value1", setting2=42)
        yield instance
        # Cleanup happens here (if needed)
        instance.cleanup()
    
    def test_basic_functionality(self, example_instance):
        """
        Test: ExampleClass performs basic operation correctly.
        
        Pattern: Arrange-Act-Assert (AAA)
        1. Arrange: Set up test data
        2. Act: Execute the code being tested
        3. Assert: Verify the result
        """
        # Arrange
        input_data = {"key": "value"}
        expected_output = "processed_value"
        
        # Act
        result = example_instance.process(input_data)
        
        # Assert
        assert result == expected_output, f"Expected {expected_output}, got {result}"
        assert example_instance.state == "completed"
    
    def test_error_handling(self, example_instance):
        """
        Test: ExampleClass handles invalid input gracefully.
        
        Pattern: Test error conditions with pytest.raises
        """
        # Arrange
        invalid_input = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="Input cannot be None"):
            example_instance.process(invalid_input)
    
    def test_edge_cases(self, example_instance):
        """
        Test: ExampleClass handles edge cases.
        
        Pattern: Test boundary conditions
        """
        # Test empty input
        result = example_instance.process({})
        assert result is not None
        
        # Test maximum size
        large_input = {"key": "x" * 10000}
        result = example_instance.process(large_input)
        assert len(result) <= 10000


# ============================================================================
# MOCKING EXTERNAL APIs
# ============================================================================

class TestWithExternalAPI:
    """
    Test suite for code that depends on external APIs.
    
    Use mocking to avoid real API calls during testing.
    """
    
    def test_with_mocked_alpaca(self):
        """
        Test: Trading logic works with mocked Alpaca API.
        
        Pattern: Use mock_alpaca_client from helpers
        """
        # Arrange
        client = mock_alpaca_client(
            account_data=create_mock_account(equity=50000.0),
            positions=[create_mock_position("AAPL", 10, 150.0, 155.0)]
        )
        
        # Act
        account = client.get_account()
        positions = client.get_positions()
        
        # Assert
        assert account['equity'] == 50000.0
        assert len(positions) == 1
        assert positions[0]['symbol'] == "AAPL"
    
    def test_with_custom_mock(self, monkeypatch):
        """
        Test: Custom mocking with monkeypatch.
        
        Pattern: Use monkeypatch for more control
        """
        # Arrange
        def mock_api_call(symbol):
            return {"symbol": symbol, "price": 150.0}
        
        # Replace the real function with mock
        monkeypatch.setattr('wawatrader.example_module.api_call', mock_api_call)
        
        # Act
        result = ExampleClass().fetch_price("AAPL")
        
        # Assert
        assert result['price'] == 150.0


# ============================================================================
# TESTING WITH DATA
# ============================================================================

class TestDataProcessing:
    """
    Test suite for functions that process market data.
    
    Use helpers to generate realistic test data.
    """
    
    def test_indicator_calculation(self):
        """
        Test: Technical indicator calculates correctly.
        
        Pattern: Use create_mock_ohlcv for price data
        """
        # Arrange
        df = create_mock_ohlcv("AAPL", days=100, start_price=150.0)
        
        # Act
        from wawatrader.indicators import calculate_sma
        result = calculate_sma(df, period=20)
        
        # Assert
        assert_dataframe_valid(result, ['sma_20'])
        assert len(result) == 100
        assert result['sma_20'].iloc[-1] > 0
    
    @pytest.mark.parametrize("days,expected_len", [
        (10, 10),
        (50, 50),
        (100, 100),
    ])
    def test_multiple_periods(self, days, expected_len):
        """
        Test: Function works with various time periods.
        
        Pattern: Use parametrize to test multiple inputs
        """
        # Arrange
        df = create_mock_ohlcv("AAPL", days=days)
        
        # Act & Assert
        assert len(df) == expected_len


# ============================================================================
# ASYNC TESTING
# ============================================================================

class TestAsyncOperations:
    """
    Test suite for async/await code.
    
    Use @pytest.mark.asyncio for async tests.
    """
    
    @pytest.mark.asyncio
    async def test_async_function(self):
        """
        Test: Async function completes successfully.
        
        Pattern: Mark with @pytest.mark.asyncio
        """
        # Arrange
        from wawatrader.example_module import async_fetch_data
        
        # Act
        result = await async_fetch_data("AAPL")
        
        # Assert
        assert result is not None
        assert 'symbol' in result


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """
    Test suite for multi-component integration.
    
    Integration tests verify components work together.
    """
    
    def test_full_trading_workflow(self):
        """
        Test: Complete trading workflow from signal to execution.
        
        Pattern: Test the full pipeline
        """
        # Arrange
        client = mock_alpaca_client()
        # ... setup other components
        
        # Act
        # 1. Generate signal
        # 2. Risk check
        # 3. Execute trade
        # 4. Log decision
        
        # Assert
        # Verify each step worked
        pass


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """
    Test suite for performance requirements.
    
    Verify code meets speed requirements.
    """
    
    def test_calculation_speed(self):
        """
        Test: Calculation completes within time limit.
        
        Pattern: Use pytest's benchmark or manual timing
        """
        import time
        
        # Arrange
        df = create_mock_ohlcv("AAPL", days=1000)
        
        # Act
        start = time.time()
        result = process_large_dataset(df)
        duration = time.time() - start
        
        # Assert
        assert duration < 1.0, f"Processing took {duration}s, should be < 1s"


# ============================================================================
# FIXTURES (MODULE-LEVEL)
# ============================================================================

@pytest.fixture(scope="module")
def database():
    """
    Module-level fixture: Share across all tests in this file.
    
    Scope options:
    - function: New instance per test (default)
    - class: New instance per test class
    - module: New instance per test module
    - session: One instance for entire test session
    """
    from tests.helpers import temp_database
    db_path = temp_database()
    # Setup
    yield db_path
    # Teardown


# ============================================================================
# USAGE EXAMPLES FOR AI AGENTS
# ============================================================================

"""
QUICK START FOR AI AGENTS
==========================

1. SIMPLE TEST:
   def test_something():
       result = function_to_test()
       assert result == expected_value

2. TEST WITH SETUP:
   @pytest.fixture
   def setup():
       return SomeObject()
   
   def test_with_fixture(setup):
       result = setup.do_something()
       assert result

3. TEST WITH MOCK DATA:
   from tests.helpers import create_mock_ohlcv
   
   def test_with_data():
       df = create_mock_ohlcv("AAPL")
       result = process(df)
       assert len(result) > 0

4. TEST EXCEPTION:
   def test_error():
       with pytest.raises(ValueError):
           function_that_should_fail()

5. ASYNC TEST:
   @pytest.mark.asyncio
   async def test_async():
       result = await async_function()
       assert result

COMMON ASSERTIONS
=================

assert value == expected             # Equality
assert value > 0                      # Comparison
assert value in [1, 2, 3]            # Membership
assert 'key' in dictionary           # Key existence
assert len(list) == 5                # Length
assert obj is not None               # None check
assert callable(func)                # Callable check
assert df.empty == False             # DataFrame not empty

RUNNING TESTS
=============

# All tests
pytest

# Specific file
pytest tests/test_example.py

# Specific test
pytest tests/test_example.py::test_something

# With output
pytest -v

# Stop on first failure
pytest -x

# Show print statements
pytest -s
"""
