"""
Tests for Backtester

Validates backtesting framework logic without running full backtests.
"""

import pytest
from datetime import datetime, timedelta
from wawatrader.backtester import Backtester, BacktestStats, Trade


class TestBacktesterSetup:
    """Test backtester initialization"""
    
    def test_init(self):
        """Test backtester initialization"""
        bt = Backtester(
            symbols=["AAPL", "MSFT"],
            start_date="2024-01-01",
            end_date="2024-12-31",
            initial_capital=100000
        )
        
        assert bt.symbols == ["AAPL", "MSFT"]
        assert bt.initial_capital == 100000
        assert bt.cash == 100000
        assert bt.start_date == datetime(2024, 1, 1)
        assert bt.end_date == datetime(2024, 12, 31)
        assert len(bt.positions) == 0
        assert len(bt.trades) == 0
    
    def test_custom_costs(self):
        """Test custom commission and slippage"""
        bt = Backtester(
            symbols=["AAPL"],
            start_date="2024-01-01",
            end_date="2024-12-31",
            initial_capital=50000,
            commission_per_share=0.01,
            slippage_pct=0.002
        )
        
        assert bt.commission_per_share == 0.01
        assert bt.slippage_pct == 0.002


class TestTradeExecution:
    """Test simulated trade execution"""
    
    def test_buy_trade(self):
        """Test executing a buy trade"""
        bt = Backtester(
            symbols=["AAPL"],
            start_date="2024-01-01",
            end_date="2024-12-31",
            initial_capital=100000,
            commission_per_share=0.0,
            slippage_pct=0.001
        )
        
        # Execute buy
        success = bt.execute_trade(
            symbol="AAPL",
            side="buy",
            shares=100,
            price=150.0,
            current_date=datetime(2024, 1, 15),
            reasoning="Test buy",
            confidence=0.8
        )
        
        assert success is True
        assert bt.positions["AAPL"] == 100
        assert "AAPL" in bt.position_prices
        
        # Check cost with slippage
        expected_price = 150.0 * 1.001  # Buy slippage
        expected_cost = 100 * expected_price
        expected_cash = 100000 - expected_cost
        
        assert abs(bt.cash - expected_cash) < 0.01
    
    def test_sell_trade(self):
        """Test executing a sell trade"""
        bt = Backtester(
            symbols=["AAPL"],
            start_date="2024-01-01",
            end_date="2024-12-31",
            initial_capital=100000,
            commission_per_share=0.0,
            slippage_pct=0.001
        )
        
        # Buy first
        bt.execute_trade(
            symbol="AAPL",
            side="buy",
            shares=100,
            price=150.0,
            current_date=datetime(2024, 1, 15),
            reasoning="Test buy",
            confidence=0.8
        )
        
        initial_cash = bt.cash
        
        # Sell
        success = bt.execute_trade(
            symbol="AAPL",
            side="sell",
            shares=100,
            price=160.0,
            current_date=datetime(2024, 2, 15),
            reasoning="Test sell",
            confidence=0.8
        )
        
        assert success is True
        assert "AAPL" not in bt.positions  # Position closed
        assert len(bt.trades) == 1  # Trade recorded
        
        # Check trade details
        trade = bt.trades[0]
        assert trade.symbol == "AAPL"
        assert trade.shares == 100
        assert trade.pnl > 0  # Profitable trade (bought at 150, sold at 160)
    
    def test_insufficient_cash(self):
        """Test buy with insufficient cash"""
        bt = Backtester(
            symbols=["AAPL"],
            start_date="2024-01-01",
            end_date="2024-12-31",
            initial_capital=1000,  # Low capital
            commission_per_share=0.0,
            slippage_pct=0.001
        )
        
        # Try to buy more than we can afford
        success = bt.execute_trade(
            symbol="AAPL",
            side="buy",
            shares=100,
            price=150.0,
            current_date=datetime(2024, 1, 15),
            reasoning="Test",
            confidence=0.8
        )
        
        assert success is False
        assert len(bt.positions) == 0
    
    def test_insufficient_shares(self):
        """Test sell with insufficient shares"""
        bt = Backtester(
            symbols=["AAPL"],
            start_date="2024-01-01",
            end_date="2024-12-31",
            initial_capital=100000
        )
        
        # Try to sell shares we don't have
        success = bt.execute_trade(
            symbol="AAPL",
            side="sell",
            shares=100,
            price=150.0,
            current_date=datetime(2024, 1, 15),
            reasoning="Test",
            confidence=0.8
        )
        
        assert success is False
        assert len(bt.trades) == 0


class TestPortfolioValue:
    """Test portfolio valuation"""
    
    def test_cash_only(self):
        """Test portfolio value with cash only"""
        bt = Backtester(
            symbols=["AAPL"],
            start_date="2024-01-01",
            end_date="2024-12-31",
            initial_capital=100000
        )
        
        value = bt.calculate_portfolio_value(datetime(2024, 1, 15))
        assert value == 100000
    
    def test_with_positions(self):
        """Test portfolio value calculation with positions"""
        bt = Backtester(
            symbols=["AAPL"],
            start_date="2024-01-01",
            end_date="2024-12-31",
            initial_capital=100000
        )
        
        # Manually set position (bypass execute_trade)
        bt.positions["AAPL"] = 100
        bt.position_prices["AAPL"] = 150.0
        bt.cash = 85000  # After buying 100 shares at $150
        
        # Mock data cache for price lookup
        import pandas as pd
        bt.data_cache["AAPL"] = pd.DataFrame({
            'close': [160.0]
        }, index=[datetime(2024, 1, 15)])
        
        value = bt.calculate_portfolio_value(datetime(2024, 1, 16))
        
        # Should be: $85,000 cash + 100 shares * $160 = $101,000
        assert abs(value - 101000) < 100  # Allow small margin


class TestStatistics:
    """Test performance metrics calculation"""
    
    def test_benchmark_return_calculation(self):
        """Test benchmark return calculation"""
        bt = Backtester(
            symbols=["AAPL"],
            start_date="2024-01-01",
            end_date="2024-12-31",
            initial_capital=100000
        )
        
        # Mock price data
        import pandas as pd
        dates = pd.date_range(start="2024-01-01", end="2024-12-31", freq='D')
        prices = [100.0 + i for i in range(len(dates))]  # Linear growth
        
        bt.data_cache["AAPL"] = pd.DataFrame({
            'close': prices
        }, index=dates)
        
        benchmark_return = bt.calculate_benchmark_return()
        
        # Should be positive (price went from 100 to ~465)
        assert benchmark_return > 0
        assert benchmark_return < 10  # Sanity check
    
    def test_max_drawdown_calculation(self):
        """Test maximum drawdown calculation"""
        bt = Backtester(
            symbols=["AAPL"],
            start_date="2024-01-01",
            end_date="2024-12-31",
            initial_capital=100000
        )
        
        # Simulate portfolio values with known drawdown
        bt.daily_values = [
            (datetime(2024, 1, 1), 100000),
            (datetime(2024, 1, 2), 110000),  # Peak
            (datetime(2024, 1, 3), 100000),  # -9.09%
            (datetime(2024, 1, 4), 90000),   # -18.18% (max)
            (datetime(2024, 1, 5), 95000),
            (datetime(2024, 1, 6), 105000),
        ]
        
        max_dd, duration = bt.calculate_max_drawdown()
        
        # Max drawdown should be ~18.18%
        assert abs(max_dd - 0.1818) < 0.01
        assert duration >= 1


class TestBacktestStats:
    """Test BacktestStats dataclass"""
    
    def test_stats_creation(self):
        """Test creating BacktestStats"""
        stats = BacktestStats(
            total_return=0.25,
            annualized_return=0.25,
            benchmark_return=0.15,
            alpha=0.10,
            sharpe_ratio=1.5,
            max_drawdown=0.10,
            max_drawdown_duration=30,
            volatility=0.20,
            total_trades=100,
            winning_trades=60,
            losing_trades=40,
            win_rate=0.60,
            avg_win=500,
            avg_loss=-300,
            profit_factor=2.0,
            avg_trade_duration=5.0,
            max_position_size=0.10,
            avg_position_size=0.08,
            total_commissions=100,
            total_slippage=50,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            trading_days=252,
            starting_capital=100000,
            ending_capital=125000
        )
        
        assert stats.total_return == 0.25
        assert stats.win_rate == 0.60
        assert stats.alpha == 0.10
    
    def test_stats_to_dict(self):
        """Test converting stats to dictionary"""
        stats = BacktestStats(
            total_return=0.25,
            annualized_return=0.25,
            benchmark_return=0.15,
            alpha=0.10,
            sharpe_ratio=1.5,
            max_drawdown=0.10,
            max_drawdown_duration=30,
            volatility=0.20,
            total_trades=100,
            winning_trades=60,
            losing_trades=40,
            win_rate=0.60,
            avg_win=500,
            avg_loss=-300,
            profit_factor=2.0,
            avg_trade_duration=5.0,
            max_position_size=0.10,
            avg_position_size=0.08,
            total_commissions=100,
            total_slippage=50,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            trading_days=252,
            starting_capital=100000,
            ending_capital=125000
        )
        
        data = stats.to_dict()
        
        assert isinstance(data, dict)
        assert data['total_return'] == 0.25
        assert isinstance(data['start_date'], str)  # Should be ISO format


class TestTradeDataclass:
    """Test Trade dataclass"""
    
    def test_trade_creation(self):
        """Test creating Trade object"""
        trade = Trade(
            entry_date=datetime(2024, 1, 1),
            exit_date=datetime(2024, 1, 5),
            symbol="AAPL",
            side="buy",
            shares=100,
            entry_price=150.0,
            exit_price=160.0,
            pnl=1000.0,
            pnl_pct=6.67,
            commission=0.0,
            duration_days=4,
            reasoning="Test trade",
            confidence=0.8
        )
        
        assert trade.symbol == "AAPL"
        assert trade.pnl == 1000.0
        assert trade.duration_days == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
