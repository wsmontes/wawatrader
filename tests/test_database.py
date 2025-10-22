"""
Tests for Database Manager

Validates database operations, schema, and data persistence.
"""

import pytest
import sqlite3
from pathlib import Path
from datetime import datetime, date
import tempfile
import os

from wawatrader.database import (
    DatabaseManager,
    Trade,
    TradingDecision,
    LLMInteraction,
    PerformanceSnapshot,
    get_database
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    # Create temp file
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Create database
    db = DatabaseManager(db_path=path)
    
    yield db
    
    # Cleanup
    db.close()
    Path(path).unlink(missing_ok=True)


class TestDatabaseSetup:
    """Test database initialization and schema"""
    
    def test_database_creation(self, temp_db):
        """Test database file is created"""
        assert Path(temp_db.db_path).exists()
        assert temp_db.conn is not None
    
    def test_tables_created(self, temp_db):
        """Test all tables are created"""
        cursor = temp_db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        
        expected_tables = {
            'trades',
            'decisions',
            'llm_interactions',
            'performance_snapshots'
        }
        
        assert expected_tables.issubset(tables)
    
    def test_indexes_created(self, temp_db):
        """Test indexes are created"""
        cursor = temp_db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )
        indexes = {row[0] for row in cursor.fetchall()}
        
        # Should have indexes on symbol and timestamp
        assert any('trades' in idx and 'symbol' in idx for idx in indexes)
        assert any('decisions' in idx for idx in indexes)


class TestTradeOperations:
    """Test trade CRUD operations"""
    
    def test_add_trade(self, temp_db):
        """Test adding a trade"""
        trade = Trade(
            symbol="AAPL",
            side="buy",
            quantity=100,
            price=150.0,
            commission=0.0,
            order_id="test-123"
        )
        
        trade_id = temp_db.add_trade(trade)
        
        assert trade_id > 0
        assert isinstance(trade_id, int)
    
    def test_get_trades(self, temp_db):
        """Test retrieving trades"""
        # Add some trades
        trade1 = Trade(symbol="AAPL", side="buy", quantity=100, price=150.0)
        trade2 = Trade(symbol="MSFT", side="sell", quantity=50, price=280.0)
        
        temp_db.add_trade(trade1)
        temp_db.add_trade(trade2)
        
        # Get all trades
        trades = temp_db.get_trades()
        assert len(trades) == 2
        
        # Get trades by symbol
        aapl_trades = temp_db.get_trades(symbol="AAPL")
        assert len(aapl_trades) == 1
        assert aapl_trades[0]['symbol'] == "AAPL"
    
    def test_get_trades_with_limit(self, temp_db):
        """Test trade limit"""
        # Add multiple trades
        for i in range(10):
            trade = Trade(symbol="AAPL", side="buy", quantity=10, price=150.0 + i)
            temp_db.add_trade(trade)
        
        # Get with limit
        trades = temp_db.get_trades(limit=5)
        assert len(trades) == 5
    
    def test_trade_summary(self, temp_db):
        """Test trade summary statistics"""
        # Add trades
        temp_db.add_trade(Trade(symbol="AAPL", side="buy", quantity=100, price=150.0))
        temp_db.add_trade(Trade(symbol="AAPL", side="sell", quantity=50, price=160.0))
        
        summary = temp_db.get_trade_summary(symbol="AAPL")
        
        assert summary['total_trades'] == 2
        assert summary['total_bought'] == 100
        assert summary['total_sold'] == 50


class TestDecisionOperations:
    """Test trading decision operations"""
    
    def test_add_decision(self, temp_db):
        """Test adding a decision"""
        decision = TradingDecision(
            symbol="AAPL",
            action="buy",
            shares=100,
            price=150.0,
            confidence=0.85,
            sentiment="bullish",
            reasoning="Strong technical signals",
            risk_approved=True,
            risk_reason="Within limits",
            executed=True
        )
        
        decision_id = temp_db.add_decision(decision)
        
        assert decision_id > 0
        assert isinstance(decision_id, int)
    
    def test_get_decisions(self, temp_db):
        """Test retrieving decisions"""
        # Add decisions
        d1 = TradingDecision(
            symbol="AAPL",
            action="buy",
            shares=100,
            price=150.0,
            confidence=0.8,
            risk_approved=True,
            executed=True
        )
        d2 = TradingDecision(
            symbol="MSFT",
            action="sell",
            shares=50,
            price=280.0,
            confidence=0.7,
            risk_approved=False,
            executed=False
        )
        
        temp_db.add_decision(d1)
        temp_db.add_decision(d2)
        
        # Get all decisions
        decisions = temp_db.get_decisions()
        assert len(decisions) == 2
        
        # Get executed only
        executed = temp_db.get_decisions(executed_only=True)
        assert len(executed) == 1
        assert executed[0]['symbol'] == "AAPL"
    
    def test_decision_with_json_context(self, temp_db):
        """Test decision with JSON context fields"""
        import json
        
        indicators = {"rsi": 65, "macd": 1.5}
        llm_analysis = {"action": "buy", "confidence": 0.85}
        
        decision = TradingDecision(
            symbol="AAPL",
            action="buy",
            shares=100,
            price=150.0,
            confidence=0.85,
            risk_approved=True,
            executed=True,
            indicators_json=json.dumps(indicators),
            llm_analysis_json=json.dumps(llm_analysis)
        )
        
        decision_id = temp_db.add_decision(decision)
        
        # Retrieve and verify
        decisions = temp_db.get_decisions(symbol="AAPL")
        assert len(decisions) == 1
        assert decisions[0]['indicators_json'] is not None
        
        # Parse JSON
        retrieved_indicators = json.loads(decisions[0]['indicators_json'])
        assert retrieved_indicators['rsi'] == 65


class TestLLMInteractions:
    """Test LLM interaction logging"""
    
    def test_add_llm_interaction(self, temp_db):
        """Test adding LLM interaction"""
        interaction = LLMInteraction(
            symbol="AAPL",
            prompt="Analyze this stock",
            response='{"action": "buy", "confidence": 0.8}',
            model="gemma-3-4b",
            confidence=0.8,
            action="buy",
            success=True
        )
        
        interaction_id = temp_db.add_llm_interaction(interaction)
        
        assert interaction_id > 0
    
    def test_get_llm_interactions(self, temp_db):
        """Test retrieving LLM interactions"""
        # Add interactions
        i1 = LLMInteraction(
            symbol="AAPL",
            prompt="Test",
            response="Response",
            model="test-model",
            success=True
        )
        i2 = LLMInteraction(
            symbol="MSFT",
            prompt="Test",
            response="Response",
            model="test-model",
            success=False,
            error_message="Connection failed"
        )
        
        temp_db.add_llm_interaction(i1)
        temp_db.add_llm_interaction(i2)
        
        # Get all
        interactions = temp_db.get_llm_interactions()
        assert len(interactions) == 2
        
        # Filter by symbol
        aapl_interactions = temp_db.get_llm_interactions(symbol="AAPL")
        assert len(aapl_interactions) == 1


class TestPerformanceSnapshots:
    """Test performance snapshot operations"""
    
    def test_add_snapshot(self, temp_db):
        """Test adding performance snapshot"""
        snapshot = PerformanceSnapshot(
            date="2024-01-01",
            portfolio_value=100000.0,
            cash=25000.0,
            positions_value=75000.0,
            daily_pnl=1500.0,
            daily_pnl_pct=1.5,
            total_return=0.05,
            num_positions=3,
            num_trades_today=5
        )
        
        snapshot_id = temp_db.add_performance_snapshot(snapshot)
        
        assert snapshot_id > 0
    
    def test_snapshot_upsert(self, temp_db):
        """Test snapshot update on duplicate date"""
        # Add initial snapshot
        s1 = PerformanceSnapshot(
            date="2024-01-01",
            portfolio_value=100000.0,
            cash=25000.0,
            positions_value=75000.0,
            daily_pnl=1000.0,
            daily_pnl_pct=1.0,
            total_return=0.05,
            num_positions=3,
            num_trades_today=2
        )
        temp_db.add_performance_snapshot(s1)
        
        # Update with new values (same date)
        s2 = PerformanceSnapshot(
            date="2024-01-01",
            portfolio_value=102000.0,
            cash=27000.0,
            positions_value=75000.0,
            daily_pnl=2000.0,
            daily_pnl_pct=2.0,
            total_return=0.07,
            num_positions=3,
            num_trades_today=5
        )
        temp_db.add_performance_snapshot(s2)
        
        # Should only have one record
        snapshots = temp_db.get_performance_snapshots()
        assert len(snapshots) == 1
        assert snapshots[0]['portfolio_value'] == 102000.0
        assert snapshots[0]['num_trades_today'] == 5
    
    def test_get_snapshots_date_range(self, temp_db):
        """Test getting snapshots in date range"""
        # Add snapshots for multiple days
        for i in range(5):
            snapshot = PerformanceSnapshot(
                date=f"2024-01-0{i+1}",
                portfolio_value=100000.0 + (i * 1000),
                cash=25000.0,
                positions_value=75000.0,
                daily_pnl=0.0,
                daily_pnl_pct=0.0,
                total_return=0.0,
                num_positions=0,
                num_trades_today=0
            )
            temp_db.add_performance_snapshot(snapshot)
        
        # Get range
        snapshots = temp_db.get_performance_snapshots(
            start_date="2024-01-02",
            end_date="2024-01-04"
        )
        
        assert len(snapshots) == 3


class TestAnalytics:
    """Test analytics functions"""
    
    def test_win_rate_calculation(self, temp_db):
        """Test win rate statistics"""
        # Add decisions
        for i in range(10):
            decision = TradingDecision(
                symbol="AAPL",
                action="buy" if i % 2 == 0 else "sell",
                shares=100,
                price=150.0,
                confidence=0.8,
                risk_approved=True,
                executed=i < 7  # 7 executed, 3 not
            )
            temp_db.add_decision(decision)
        
        stats = temp_db.get_win_rate(symbol="AAPL")
        
        assert stats['total_decisions'] == 10
        assert stats['executed_count'] == 7
        assert stats['buy_signals'] == 5
        assert stats['sell_signals'] == 5
    
    def test_daily_stats(self, temp_db):
        """Test daily statistics"""
        test_date = "2024-01-15"
        
        # Add some data for test date with explicit timestamp
        trade = Trade(
            timestamp=f"{test_date}T10:00:00",
            symbol="AAPL",
            side="buy",
            quantity=100,
            price=150.0
        )
        temp_db.add_trade(trade)
        
        decision = TradingDecision(
            timestamp=f"{test_date}T10:00:00",
            symbol="AAPL",
            action="buy",
            shares=100,
            price=150.0,
            confidence=0.8,
            risk_approved=True,
            executed=True
        )
        temp_db.add_decision(decision)
        
        stats = temp_db.get_daily_stats(test_date)
        
        assert stats['date'] == test_date
        assert stats['num_trades'] >= 1
        assert stats['num_decisions'] >= 1


class TestDataExport:
    """Test data export functionality"""
    
    def test_export_to_csv(self, temp_db, tmp_path):
        """Test CSV export"""
        # Add some data
        trade = Trade(symbol="AAPL", side="buy", quantity=100, price=150.0)
        temp_db.add_trade(trade)
        
        # Export
        output_file = tmp_path / "trades.csv"
        temp_db.export_to_csv('trades', str(output_file))
        
        assert output_file.exists()
        
        # Verify content
        with open(output_file, 'r') as f:
            content = f.read()
            assert 'AAPL' in content
            assert 'buy' in content
    
    def test_export_to_json(self, temp_db, tmp_path):
        """Test JSON export"""
        import json
        
        # Add data
        trade = Trade(symbol="MSFT", side="sell", quantity=50, price=280.0)
        temp_db.add_trade(trade)
        
        # Export
        output_file = tmp_path / "trades.json"
        temp_db.export_to_json('trades', str(output_file))
        
        assert output_file.exists()
        
        # Verify content
        with open(output_file, 'r') as f:
            data = json.load(f)
            assert len(data) > 0
            assert data[0]['symbol'] == 'MSFT'


class TestUtilities:
    """Test utility functions"""
    
    def test_table_stats(self, temp_db):
        """Test table statistics"""
        # Add some data
        temp_db.add_trade(Trade(symbol="AAPL", side="buy", quantity=100, price=150.0))
        temp_db.add_decision(TradingDecision(
            symbol="AAPL",
            action="buy",
            shares=100,
            price=150.0,
            confidence=0.8,
            risk_approved=True,
            executed=True
        ))
        
        stats = temp_db.get_table_stats()
        
        assert 'trades' in stats
        assert 'decisions' in stats
        assert stats['trades'] == 1
        assert stats['decisions'] == 1
    
    def test_clear_all_data(self, temp_db):
        """Test clearing all data"""
        # Add data
        temp_db.add_trade(Trade(symbol="AAPL", side="buy", quantity=100, price=150.0))
        temp_db.add_decision(TradingDecision(
            symbol="AAPL",
            action="buy",
            shares=100,
            price=150.0,
            confidence=0.8,
            risk_approved=True,
            executed=True
        ))
        
        # Verify data exists
        stats_before = temp_db.get_table_stats()
        assert stats_before['trades'] == 1
        
        # Clear
        temp_db.clear_all_data()
        
        # Verify empty
        stats_after = temp_db.get_table_stats()
        assert stats_after['trades'] == 0
        assert stats_after['decisions'] == 0


class TestSingleton:
    """Test singleton pattern"""
    
    def test_get_database_singleton(self):
        """Test get_database returns same instance"""
        db1 = get_database("test_singleton.db")
        db2 = get_database("test_singleton.db")
        
        assert db1 is db2
        
        # Cleanup
        db1.close()
        Path("test_singleton.db").unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
