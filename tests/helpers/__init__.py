"""
Test Helpers - Reusable Testing Utilities

This module provides common testing utilities, fixtures, and mock data
generators that can be reused across all test files.

Usage:
    from tests.helpers import create_mock_trade, mock_alpaca_client, temp_database
    
AI Agents: Use these helpers to write consistent, DRY tests.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any
from unittest.mock import Mock, MagicMock


# ============================================================================
# MOCK DATA GENERATORS
# ============================================================================

def create_mock_ohlcv(
    symbol: str = "AAPL",
    days: int = 100,
    start_price: float = 150.0
) -> pd.DataFrame:
    """
    Generate realistic OHLCV (candlestick) data for testing.
    
    Args:
        symbol: Stock symbol
        days: Number of days of data
        start_price: Starting price
        
    Returns:
        DataFrame with columns: open, high, low, close, volume
        
    Example:
        >>> df = create_mock_ohlcv("AAPL", days=30)
        >>> assert len(df) == 30
        >>> assert 'close' in df.columns
    """
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    
    # Generate realistic price movements
    returns = np.random.normal(0.001, 0.02, days)  # Mean return 0.1%, std 2%
    prices = start_price * (1 + returns).cumprod()
    
    # Add some noise for high/low
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices * (1 + np.random.uniform(-0.01, 0.01, days)),
        'high': prices * (1 + np.random.uniform(0, 0.02, days)),
        'low': prices * (1 + np.random.uniform(-0.02, 0, days)),
        'close': prices,
        'volume': np.random.randint(10_000_000, 100_000_000, days)
    })
    
    df.set_index('timestamp', inplace=True)
    return df


def create_mock_trade(
    symbol: str = "AAPL",
    action: str = "buy",
    quantity: int = 10,
    price: float = 150.0,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a mock trade object.
    
    Args:
        symbol: Stock symbol
        action: 'buy' or 'sell'
        quantity: Number of shares
        price: Execution price
        **kwargs: Additional fields
        
    Returns:
        Dictionary representing a trade
        
    Example:
        >>> trade = create_mock_trade("AAPL", "buy", 10, 150.0)
        >>> assert trade['symbol'] == "AAPL"
        >>> assert trade['total_value'] == 1500.0
    """
    trade = {
        'symbol': symbol,
        'action': action,
        'quantity': quantity,
        'price': price,
        'timestamp': datetime.now().isoformat(),
        'total_value': quantity * price,
        'status': 'executed',
        **kwargs
    }
    return trade


def create_mock_position(
    symbol: str = "AAPL",
    quantity: int = 10,
    avg_entry_price: float = 150.0,
    current_price: float = 155.0
) -> Dict[str, Any]:
    """
    Create a mock position object.
    
    Args:
        symbol: Stock symbol
        quantity: Number of shares held
        avg_entry_price: Average purchase price
        current_price: Current market price
        
    Returns:
        Dictionary representing a position with P&L
        
    Example:
        >>> pos = create_mock_position("AAPL", 10, 150.0, 155.0)
        >>> assert pos['unrealized_pl'] == 50.0  # (155-150)*10
    """
    market_value = quantity * current_price
    cost_basis = quantity * avg_entry_price
    unrealized_pl = market_value - cost_basis
    unrealized_pl_pct = (unrealized_pl / cost_basis) * 100 if cost_basis > 0 else 0
    
    return {
        'symbol': symbol,
        'quantity': quantity,
        'avg_entry_price': avg_entry_price,
        'current_price': current_price,
        'market_value': market_value,
        'cost_basis': cost_basis,
        'unrealized_pl': unrealized_pl,
        'unrealized_pl_pct': unrealized_pl_pct,
        'side': 'long'
    }


def create_mock_account(
    equity: float = 100000.0,
    buying_power: float = 100000.0,
    cash: float = 100000.0
) -> Dict[str, Any]:
    """
    Create a mock account object.
    
    Args:
        equity: Total account value
        buying_power: Available buying power
        cash: Cash balance
        
    Returns:
        Dictionary representing account status
        
    Example:
        >>> account = create_mock_account(equity=50000.0)
        >>> assert account['equity'] == 50000.0
    """
    return {
        'account_number': 'PA123456789',
        'status': 'ACTIVE',
        'currency': 'USD',
        'equity': equity,
        'buying_power': buying_power,
        'cash': cash,
        'portfolio_value': equity - cash,
        'pattern_day_trader': False
    }


# ============================================================================
# MOCK API CLIENTS
# ============================================================================

def mock_alpaca_client(
    account_data: Dict = None,
    positions: List[Dict] = None,
    bars_data: pd.DataFrame = None
) -> Mock:
    """
    Create a mock Alpaca client with customizable responses.
    
    Args:
        account_data: Account info to return (default: $100k account)
        positions: List of positions to return (default: empty)
        bars_data: Price data to return (default: AAPL 100 days)
        
    Returns:
        Mock AlpacaClient object
        
    Example:
        >>> client = mock_alpaca_client()
        >>> account = client.get_account()
        >>> assert account['equity'] == 100000.0
    """
    client = Mock()
    
    # Default data
    account_data = account_data or create_mock_account()
    positions = positions or []
    bars_data = bars_data if bars_data is not None else create_mock_ohlcv()
    
    # Configure mock methods
    client.get_account.return_value = account_data
    client.get_positions.return_value = positions
    client.get_bars.return_value = bars_data
    client.get_latest_quote.return_value = {
        'symbol': 'AAPL',
        'bid_price': 149.95,
        'ask_price': 150.05,
        'timestamp': datetime.now().isoformat()
    }
    
    return client


def mock_llm_bridge(response: str = None) -> Mock:
    """
    Create a mock LLM bridge with customizable response.
    
    Args:
        response: JSON string to return (default: BUY recommendation)
        
    Returns:
        Mock LLMBridge object
        
    Example:
        >>> llm = mock_llm_bridge()
        >>> result = llm.analyze_market_v2("AAPL", {}, {})
        >>> assert result['action'] == 'BUY'
    """
    llm = Mock()
    
    default_response = {
        'action': 'BUY',
        'confidence': 75,
        'reasoning': 'Strong technical indicators',
        'risk_level': 'medium'
    }
    
    llm.analyze_market_v2.return_value = default_response
    return llm


# ============================================================================
# PYTEST FIXTURES
# ============================================================================

@pytest.fixture
def temp_database():
    """
    Provide a temporary database for testing.
    Automatically cleaned up after test.
    
    Yields:
        Path to temporary database file
        
    Example:
        def test_database(temp_database):
            db = Database(temp_database)
            # Test database operations
    """
    import tempfile
    import os
    
    # Create temp db
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    yield path
    
    # Cleanup
    try:
        os.unlink(path)
    except:
        pass


@pytest.fixture
def sample_ohlcv():
    """
    Provide sample OHLCV data for testing indicators.
    
    Returns:
        DataFrame with 100 days of AAPL data
        
    Example:
        def test_indicator(sample_ohlcv):
            result = calculate_sma(sample_ohlcv, period=20)
            assert len(result) == len(sample_ohlcv)
    """
    return create_mock_ohlcv("AAPL", days=100)


@pytest.fixture
def mock_client():
    """
    Provide a mock Alpaca client.
    
    Returns:
        Mock client with standard responses
        
    Example:
        def test_trading(mock_client):
            account = mock_client.get_account()
            assert account['status'] == 'ACTIVE'
    """
    return mock_alpaca_client()


# ============================================================================
# ASSERTION HELPERS
# ============================================================================

def assert_valid_trade(trade: Dict):
    """
    Assert that a trade object is valid.
    
    Args:
        trade: Trade dictionary to validate
        
    Raises:
        AssertionError: If trade is invalid
        
    Example:
        >>> trade = create_mock_trade()
        >>> assert_valid_trade(trade)  # Passes
    """
    assert 'symbol' in trade, "Trade must have symbol"
    assert 'action' in trade, "Trade must have action"
    assert trade['action'] in ['buy', 'sell'], f"Invalid action: {trade['action']}"
    assert 'quantity' in trade, "Trade must have quantity"
    assert trade['quantity'] > 0, "Quantity must be positive"
    assert 'price' in trade, "Trade must have price"
    assert trade['price'] > 0, "Price must be positive"


def assert_valid_position(position: Dict):
    """
    Assert that a position object is valid.
    
    Args:
        position: Position dictionary to validate
        
    Raises:
        AssertionError: If position is invalid
    """
    assert 'symbol' in position, "Position must have symbol"
    assert 'quantity' in position, "Position must have quantity"
    assert 'market_value' in position, "Position must have market_value"
    assert 'unrealized_pl' in position, "Position must have unrealized_pl"


def assert_dataframe_valid(df: pd.DataFrame, required_columns: List[str]):
    """
    Assert that a DataFrame has required columns and is not empty.
    
    Args:
        df: DataFrame to validate
        required_columns: List of required column names
        
    Raises:
        AssertionError: If DataFrame is invalid
        
    Example:
        >>> df = create_mock_ohlcv()
        >>> assert_dataframe_valid(df, ['open', 'high', 'low', 'close'])
    """
    assert df is not None, "DataFrame is None"
    assert not df.empty, "DataFrame is empty"
    
    for col in required_columns:
        assert col in df.columns, f"Missing required column: {col}"
    
    assert not df.isnull().all().any(), "DataFrame has all-null columns"


# ============================================================================
# TEST DATA CONSTANTS
# ============================================================================

COMMON_SYMBOLS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

MARKET_HOURS = {
    'pre_market_start': '04:00',
    'market_open': '09:30',
    'market_close': '16:00',
    'after_hours_end': '20:00'
}

TYPICAL_RISK_PARAMS = {
    'max_position_size': 0.1,  # 10% of portfolio
    'max_total_exposure': 0.9,  # 90% of portfolio
    'max_daily_loss_pct': 0.03,  # 3% max daily loss
    'stop_loss_pct': 0.05  # 5% stop loss
}
