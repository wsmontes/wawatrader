"""
Unit Tests for Risk Manager

Validates all risk management rules.
"""

import pytest
from datetime import date
from wawatrader.risk_manager import RiskManager, RiskCheckResult


class TestPositionSizeCheck:
    """Test position size validation"""
    
    def test_small_position_approved(self):
        """Test small position passes"""
        rm = RiskManager()
        
        # 5% position should pass (limit is 10%)
        result = rm.check_position_size(
            symbol="AAPL",
            shares=33,
            price=150,
            account_value=100000
        )
        
        assert result.approved is True
        assert result.max_shares is not None
    
    def test_large_position_rejected(self):
        """Test oversized position fails"""
        rm = RiskManager()
        
        # 15% position should fail (limit is 10%)
        result = rm.check_position_size(
            symbol="AAPL",
            shares=100,
            price=150,
            account_value=100000
        )
        
        assert result.approved is False
        assert "too large" in result.reason.lower()
        assert result.max_shares == 66  # 10% of 100k at $150
    
    def test_max_position_size(self):
        """Test exactly at limit"""
        rm = RiskManager()
        
        # Exactly 10% should pass
        result = rm.check_position_size(
            symbol="AAPL",
            shares=66,
            price=150,
            account_value=100000
        )
        
        assert result.approved is True


class TestDailyLossLimit:
    """Test daily loss validation"""
    
    def test_small_loss_approved(self):
        """Test small loss passes"""
        rm = RiskManager()
        
        # 0.5% loss should pass (limit is 2%)
        result = rm.check_daily_loss_limit(
            current_pnl=-500,
            account_value=100000
        )
        
        assert result.approved is True
    
    def test_large_loss_rejected(self):
        """Test large loss fails"""
        rm = RiskManager()
        
        # 2.5% loss should fail (limit is 2%)
        result = rm.check_daily_loss_limit(
            current_pnl=-2500,
            account_value=100000
        )
        
        assert result.approved is False
        assert "exceeded" in result.reason.lower()
    
    def test_profit_always_approved(self):
        """Test profits are always OK"""
        rm = RiskManager()
        
        # Profit should always pass
        result = rm.check_daily_loss_limit(
            current_pnl=5000,
            account_value=100000
        )
        
        assert result.approved is True
    
    def test_warning_near_limit(self):
        """Test warning when approaching limit"""
        rm = RiskManager()
        
        # 1.6% loss (80% of 2% limit) should warn
        result = rm.check_daily_loss_limit(
            current_pnl=-1600,
            account_value=100000
        )
        
        assert result.approved is True
        assert len(result.warnings) > 0


class TestPortfolioExposure:
    """Test portfolio exposure validation"""
    
    def test_low_exposure_approved(self):
        """Test low exposure passes"""
        rm = RiskManager()
        
        positions = [
            {'market_value': 10000},
            {'market_value': 5000}
        ]
        
        # 15% exposure should pass (limit is 30%)
        result = rm.check_portfolio_exposure(
            positions=positions,
            account_value=100000
        )
        
        assert result.approved is True
    
    def test_high_exposure_rejected(self):
        """Test high exposure fails"""
        rm = RiskManager()
        
        positions = [
            {'market_value': 15000},
            {'market_value': 12000},
            {'market_value': 8000}
        ]
        
        # 35% exposure should fail (limit is 30%)
        result = rm.check_portfolio_exposure(
            positions=positions,
            account_value=100000
        )
        
        assert result.approved is False
        assert "too high" in result.reason.lower()
    
    def test_short_positions(self):
        """Test short positions count as exposure"""
        rm = RiskManager()
        
        positions = [
            {'market_value': 10000},
            {'market_value': -5000}  # Short position
        ]
        
        # Should count absolute value (15k total)
        result = rm.check_portfolio_exposure(
            positions=positions,
            account_value=100000
        )
        
        assert result.approved is True
        assert "15,000" in result.reason


class TestTradeFrequency:
    """Test trade frequency validation"""
    
    def test_normal_frequency_approved(self):
        """Test normal trading frequency passes"""
        rm = RiskManager()
        
        result = rm.check_trade_frequency("AAPL", "buy")
        
        assert result.approved is True
    
    def test_excessive_frequency_rejected(self):
        """Test excessive trading fails"""
        rm = RiskManager()
        
        # Simulate 10 trades
        rm.trade_count_today = 10
        
        result = rm.check_trade_frequency("AAPL", "buy")
        
        assert result.approved is False
        assert "limit reached" in result.reason.lower()
    
    def test_warning_near_limit(self):
        """Test warning when approaching limit"""
        rm = RiskManager()
        
        # 8 trades (80% of 10 limit)
        rm.trade_count_today = 8
        
        result = rm.check_trade_frequency("AAPL", "buy")
        
        assert result.approved is True
        assert len(result.warnings) > 0


class TestFullTradeValidation:
    """Test comprehensive trade validation"""
    
    def test_valid_trade_approved(self):
        """Test valid trade passes all checks"""
        rm = RiskManager()
        
        result = rm.validate_trade(
            symbol="AAPL",
            action="buy",
            shares=33,
            price=150,
            account_value=100000,
            current_pnl=-500,
            positions=[{'market_value': 10000}]
        )
        
        assert result.approved is True
    
    def test_oversized_position_rejected(self):
        """Test oversized position fails validation"""
        rm = RiskManager()
        
        result = rm.validate_trade(
            symbol="AAPL",
            action="buy",
            shares=100,  # Too many
            price=150,
            account_value=100000,
            current_pnl=0,
            positions=[]
        )
        
        assert result.approved is False
        assert "too large" in result.reason.lower()
    
    def test_daily_loss_limit_rejected(self):
        """Test daily loss limit stops trading"""
        rm = RiskManager()
        
        result = rm.validate_trade(
            symbol="AAPL",
            action="buy",
            shares=33,
            price=150,
            account_value=100000,
            current_pnl=-2500,  # Over limit
            positions=[]
        )
        
        assert result.approved is False
        assert "loss" in result.reason.lower()
    
    def test_sell_bypasses_position_size(self):
        """Test selling doesn't check position size"""
        rm = RiskManager()
        
        # Selling large position should work (not buying)
        result = rm.validate_trade(
            symbol="AAPL",
            action="sell",
            shares=100,
            price=150,
            account_value=100000,
            current_pnl=0,
            positions=[{'market_value': 15000}]
        )
        
        assert result.approved is True


class TestTradeRecording:
    """Test trade recording and counters"""
    
    def test_record_trade(self):
        """Test trade recording increments counter"""
        rm = RiskManager()
        
        assert rm.trade_count_today == 0
        
        rm.record_trade("AAPL", "buy", 10, 150)
        assert rm.trade_count_today == 1
        
        rm.record_trade("MSFT", "sell", 5, 300)
        assert rm.trade_count_today == 2
    
    def test_daily_counter_reset(self):
        """Test daily counters reset"""
        rm = RiskManager()
        
        rm.trade_count_today = 5
        rm.reset_daily_counters()
        
        assert rm.trade_count_today == 0


class TestDailyStats:
    """Test daily statistics"""
    
    def test_get_daily_stats(self):
        """Test daily stats retrieval"""
        rm = RiskManager()
        
        rm.trade_count_today = 3
        rm.daily_losses[date.today()] = -250
        
        stats = rm.get_daily_stats()
        
        assert stats['trades_today'] == 3
        assert stats['daily_pnl'] == -250
        assert 'limits' in stats
        assert 'max_position_size' in stats['limits']


def test_singleton():
    """Test risk manager singleton"""
    from wawatrader.risk_manager import get_risk_manager
    
    rm1 = get_risk_manager()
    rm2 = get_risk_manager()
    
    # Should be same instance
    assert rm1 is rm2


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
