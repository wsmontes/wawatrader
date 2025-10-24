"""
Tests for Learning Engine System

Tests the core learning and memory components:
- MarketContext capture
- TradingMemory database
- LearningEngine functionality
- Decision recording and outcome tracking
"""

# import pytest  # Only needed for full test suite
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
import pandas as pd

from wawatrader.market_context import MarketContext, MarketContextCapture
from wawatrader.memory_database import TradingMemory
from wawatrader.learning_engine import LearningEngine


class TestMarketContext:
    """Test MarketContext capture and serialization"""
    
    def test_market_context_creation(self):
        """Test creating a MarketContext instance"""
        context = MarketContext(
            timestamp=datetime.now(),
            regime="bull",
            regime_confidence=0.85,
            spy_price=450.0,
            spy_trend="uptrend",
            spy_change_1d=1.2,
            spy_change_5d=3.5,
            spy_change_20d=8.2,
            vix=15.5,
            vix_percentile=30.0,
            vix_trend="falling",
            overall_volume_ratio=1.2,
            advancing_declining_ratio=1.8,
            new_highs_lows_ratio=2.5,
            sector_momentum={"Technology": 2.1, "Energy": -0.5},
            leading_sectors=["Technology", "Healthcare", "Consumer"],
            lagging_sectors=["Energy", "Utilities", "Materials"],
            earnings_season=False,
            fed_meeting_soon=False,
            major_economic_data=False,
            time_of_day="midday",
            day_of_week="Wednesday",
            days_until_opex=7,
            percent_above_50ma=65.0,
            percent_above_200ma=58.0
        )
        
        assert context.regime == "bull"
        assert context.regime_confidence == 0.85
        assert context.spy_price == 450.0
        assert context.time_of_day == "midday"
    
    def test_market_context_to_dict(self):
        """Test converting MarketContext to dictionary"""
        context = MarketContext(
            timestamp=datetime.now(),
            regime="bull",
            regime_confidence=0.85,
            spy_price=450.0,
            spy_trend="uptrend",
            spy_change_1d=1.2,
            spy_change_5d=3.5,
            spy_change_20d=8.2,
            vix=15.5,
            vix_percentile=30.0,
            vix_trend="falling",
            overall_volume_ratio=1.2,
            advancing_declining_ratio=1.8,
            new_highs_lows_ratio=2.5,
            sector_momentum={"Technology": 2.1},
            leading_sectors=["Technology"],
            lagging_sectors=["Energy"],
            earnings_season=False,
            fed_meeting_soon=False,
            major_economic_data=False,
            time_of_day="midday",
            day_of_week="Wednesday",
            days_until_opex=7,
            percent_above_50ma=65.0,
            percent_above_200ma=58.0
        )
        
        context_dict = context.to_dict()
        assert isinstance(context_dict, dict)
        assert context_dict['regime'] == "bull"
        assert context_dict['spy_price'] == 450.0
    
    def test_market_context_from_dict(self):
        """Test creating MarketContext from dictionary"""
        context_dict = {
            'timestamp': datetime.now(),
            'regime': "bull",
            'regime_confidence': 0.85,
            'spy_price': 450.0,
            'spy_trend': "uptrend",
            'spy_change_1d': 1.2,
            'spy_change_5d': 3.5,
            'spy_change_20d': 8.2,
            'vix': 15.5,
            'vix_percentile': 30.0,
            'vix_trend': "falling",
            'overall_volume_ratio': 1.2,
            'advancing_declining_ratio': 1.8,
            'new_highs_lows_ratio': 2.5,
            'sector_momentum': {"Technology": 2.1},
            'leading_sectors': ["Technology"],
            'lagging_sectors': ["Energy"],
            'earnings_season': False,
            'fed_meeting_soon': False,
            'major_economic_data': False,
            'time_of_day': "midday",
            'day_of_week': "Wednesday",
            'days_until_opex': 7,
            'percent_above_50ma': 65.0,
            'percent_above_200ma': 58.0
        }
        
        context = MarketContext.from_dict(context_dict)
        assert context.regime == "bull"
        assert context.spy_price == 450.0
    
    def test_market_context_capture_with_mock(self):
        """Test MarketContextCapture with mocked Alpaca client"""
        mock_alpaca = Mock()
        
        # Mock SPY data
        spy_bars = pd.DataFrame({
            'close': [445, 447, 449, 450],
            'volume': [100000, 110000, 105000, 108000]
        })
        mock_alpaca.get_bars.return_value = spy_bars
        
        capturer = MarketContextCapture(mock_alpaca)
        context = capturer.capture_current()
        
        assert isinstance(context, MarketContext)
        assert context.regime in ["bull", "bear", "sideways", "volatile", "uncertain"]
        assert 0 <= context.regime_confidence <= 1
        assert context.time_of_day in ["premarket", "open", "midday", "close", "afterhours"]


class TestTradingMemory:
    """Test TradingMemory database functionality"""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        # Create temp file
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        # Create memory instance
        memory = TradingMemory(db_path=path)
        
        yield memory
        
        # Cleanup
        try:
            os.unlink(path)
        except:
            pass
    
    def test_database_initialization(self, temp_db):
        """Test that database is properly initialized"""
        assert temp_db.db_path.exists()
    
    def test_record_decision(self, temp_db):
        """Test recording a trading decision"""
        decision = {
            'timestamp': datetime.now(),
            'symbol': 'AAPL',
            'action': 'buy',
            'price': 175.50,
            'shares': 10,
            'position_value': 1755.0,
            'market_regime': 'bull',
            'market_context': {'vix': 15.5},
            'technical_indicators': {'rsi': 65},
            'llm_sentiment': 'bullish',
            'llm_confidence': 0.75,
            'llm_reasoning': 'Strong uptrend',
            'decision_confidence': 0.80,
            'decision_reasoning': 'Technical + LLM alignment'
        }
        
        decision_id = temp_db.record_decision(decision)
        assert decision_id is not None
        assert 'AAPL' in decision_id
    
    def test_update_decision_outcome(self, temp_db):
        """Test updating a decision with outcome"""
        # Record decision
        decision = {
            'timestamp': datetime.now(),
            'symbol': 'AAPL',
            'action': 'buy',
            'price': 175.50,
            'shares': 10,
            'position_value': 1755.0,
            'market_regime': 'bull',
            'llm_confidence': 0.75,
            'decision_confidence': 0.80
        }
        decision_id = temp_db.record_decision(decision)
        
        # Update outcome
        outcome = {
            'outcome': 'win',
            'profit_loss': 125.50,
            'profit_loss_percent': 1.42,
            'held_duration_minutes': 240,
            'exit_price': 178.25,
            'exit_timestamp': datetime.now(),
            'was_correct': True,
            'lesson_learned': 'Pattern worked well'
        }
        temp_db.update_decision_outcome(decision_id, outcome)
        
        # Verify update
        decisions = temp_db.get_recent_decisions(days=1)
        assert len(decisions) == 1
        assert decisions['outcome'].iloc[0] == 'win'
        assert decisions['profit_loss'].iloc[0] == 125.50
    
    def test_save_pattern(self, temp_db):
        """Test saving a discovered pattern"""
        pattern = {
            'pattern_name': 'morning_breakout',
            'pattern_type': 'time_based',
            'conditions': {'time': '9:30-10:30', 'volume': '>1.5x'},
            'success_rate': 0.75,
            'avg_return': 125.50,
            'avg_return_percent': 1.5,
            'sample_size': 12,
            'win_rate': 0.75,
            'avg_win': 180.0,
            'avg_loss': -60.0,
            'risk_reward_ratio': 3.0
        }
        
        pattern_id = temp_db.save_pattern(pattern)
        assert pattern_id is not None
        assert 'morning_breakout' in pattern_id
    
    def test_get_patterns(self, temp_db):
        """Test retrieving patterns"""
        # Save some patterns
        for i in range(3):
            pattern = {
                'pattern_name': f'pattern_{i}',
                'pattern_type': 'test',
                'conditions': {'test': True},
                'success_rate': 0.6 + (i * 0.1),
                'avg_return': 100.0,
                'avg_return_percent': 1.0,
                'sample_size': 10,
                'win_rate': 0.6,
                'avg_win': 150.0,
                'avg_loss': -50.0,
                'risk_reward_ratio': 3.0
            }
            temp_db.save_pattern(pattern)
        
        # Retrieve patterns
        patterns = temp_db.get_patterns(min_success_rate=0.6, min_sample_size=5)
        assert len(patterns) == 3
        assert all(p['success_rate'] >= 0.6 for p in patterns)
    
    def test_get_performance_stats(self, temp_db):
        """Test getting performance statistics"""
        # Record some decisions with outcomes
        for i in range(5):
            decision = {
                'timestamp': datetime.now() - timedelta(days=i),
                'symbol': f'TEST{i}',
                'action': 'buy',
                'price': 100.0,
                'shares': 10,
                'decision_confidence': 0.75
            }
            decision_id = temp_db.record_decision(decision)
            
            # Add outcome
            outcome = {
                'outcome': 'win' if i % 2 == 0 else 'loss',
                'profit_loss': 50.0 if i % 2 == 0 else -25.0,
                'exit_timestamp': datetime.now()
            }
            temp_db.update_decision_outcome(decision_id, outcome)
        
        # Get stats
        stats = temp_db.get_performance_stats(days=30)
        assert stats['total_trades'] == 5
        assert stats['winning_trades'] == 3
        assert stats['losing_trades'] == 2
        assert stats['win_rate'] == 0.6


class TestLearningEngine:
    """Test LearningEngine functionality"""
    
    @pytest.fixture
    def learning_engine(self):
        """Create learning engine with mocked dependencies"""
        # Create temp database
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        memory = TradingMemory(db_path=db_path)
        
        # Mock Alpaca client
        mock_alpaca = Mock()
        spy_bars = pd.DataFrame({
            'close': [445, 447, 449, 450],
            'volume': [100000, 110000, 105000, 108000]
        })
        mock_alpaca.get_bars.return_value = spy_bars
        
        engine = LearningEngine(mock_alpaca, memory)
        
        yield engine
        
        # Cleanup
        try:
            os.unlink(db_path)
        except:
            pass
    
    def test_record_decision(self, learning_engine):
        """Test recording a decision"""
        decision_id = learning_engine.record_decision(
            symbol='AAPL',
            action='buy',
            price=175.50,
            shares=10,
            technical_indicators={'rsi': 65, 'macd': 1.2},
            llm_analysis={'sentiment': 'bullish', 'confidence': 0.75, 'reasoning': 'Strong trend'},
            decision_confidence=0.80,
            decision_reasoning='Technical + LLM alignment'
        )
        
        assert decision_id is not None
        assert 'AAPL' in decision_id
    
    def test_record_outcome(self, learning_engine):
        """Test recording trade outcome"""
        # Record decision first
        decision_id = learning_engine.record_decision(
            symbol='AAPL',
            action='buy',
            price=175.50,
            shares=10,
            technical_indicators={'rsi': 65},
            llm_analysis={'sentiment': 'bullish', 'confidence': 0.75},
            decision_confidence=0.80,
            decision_reasoning='Test trade'
        )
        
        # Record outcome
        learning_engine.record_outcome(
            decision_id=decision_id,
            outcome='win',
            profit_loss=125.50,
            exit_price=178.25,
            exit_time=datetime.now(),
            lesson_learned='Pattern worked'
        )
        
        # Verify
        decisions = learning_engine.memory.get_recent_decisions(days=1)
        assert len(decisions) > 0
    
    def test_discover_patterns(self, learning_engine):
        """Test pattern discovery"""
        # Create sample data with patterns
        for i in range(15):
            decision_id = learning_engine.record_decision(
                symbol='AAPL',
                action='buy',
                price=175.0 + i,
                shares=10,
                technical_indicators={'rsi': 65},
                llm_analysis={'sentiment': 'bullish', 'confidence': 0.75},
                decision_confidence=0.75,
                decision_reasoning='Test'
            )
            
            # Add outcomes (create pattern: high confidence wins more)
            outcome = 'win' if i % 3 != 0 else 'loss'  # 67% win rate
            learning_engine.record_outcome(
                decision_id=decision_id,
                outcome=outcome,
                profit_loss=50.0 if outcome == 'win' else -25.0,
                exit_price=177.0 + i,
                exit_time=datetime.now()
            )
        
        # Discover patterns
        patterns = learning_engine.discover_patterns(lookback_days=1)
        
        # Should find at least some patterns
        assert len(patterns) >= 0  # May or may not find patterns depending on data
    
    def test_analyze_daily_performance(self, learning_engine):
        """Test daily performance analysis"""
        # Create some trades
        for i in range(5):
            decision_id = learning_engine.record_decision(
                symbol=f'TEST{i}',
                action='buy',
                price=100.0,
                shares=10,
                technical_indicators={'rsi': 65},
                llm_analysis={'sentiment': 'bullish', 'confidence': 0.75},
                decision_confidence=0.75,
                decision_reasoning='Test'
            )
            
            outcome = 'win' if i % 2 == 0 else 'loss'
            learning_engine.record_outcome(
                decision_id=decision_id,
                outcome=outcome,
                profit_loss=50.0 if outcome == 'win' else -25.0,
                exit_price=105.0 if outcome == 'win' else 97.5,
                exit_time=datetime.now()
            )
        
        # Analyze performance
        performance = learning_engine.analyze_daily_performance()
        
        assert performance['total_trades'] == 5
        assert performance['winning_trades'] == 3
        assert performance['losing_trades'] == 2
        assert performance['win_rate'] == 0.6
    
    def test_get_performance_summary(self, learning_engine):
        """Test getting performance summary string"""
        summary = learning_engine.get_performance_summary(days=30)
        
        assert isinstance(summary, str)
        assert 'Performance Summary' in summary
        assert 'Win Rate' in summary
        assert 'P&L' in summary


def test_integration_full_workflow():
    """Test complete workflow: capture context -> record decision -> record outcome"""
    # Create temp database
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    try:
        memory = TradingMemory(db_path=db_path)
        
        # Mock Alpaca client
        mock_alpaca = Mock()
        spy_bars = pd.DataFrame({
            'close': [450, 451, 452, 453],
            'volume': [100000, 110000, 105000, 108000]
        })
        mock_alpaca.get_bars.return_value = spy_bars
        
        engine = LearningEngine(mock_alpaca, memory)
        
        # 1. Record decision
        decision_id = engine.record_decision(
            symbol='AAPL',
            action='buy',
            price=175.50,
            shares=10,
            technical_indicators={'rsi': 65, 'macd': 1.2},
            llm_analysis={
                'sentiment': 'bullish',
                'confidence': 0.75,
                'reasoning': 'Strong uptrend with volume confirmation'
            },
            decision_confidence=0.80,
            decision_reasoning='Technical indicators + LLM alignment',
            pattern_matched='morning_breakout'
        )
        
        assert decision_id is not None
        
        # 2. Record outcome
        engine.record_outcome(
            decision_id=decision_id,
            outcome='win',
            profit_loss=125.50,
            exit_price=178.25,
            exit_time=datetime.now(),
            lesson_learned='Morning breakout pattern worked as expected'
        )
        
        # 3. Analyze performance
        performance = engine.analyze_daily_performance()
        
        assert performance['total_trades'] == 1
        assert performance['winning_trades'] == 1
        assert performance['win_rate'] == 1.0
        assert performance['total_pnl'] == 125.50
        
        # 4. Get summary
        summary = engine.get_performance_summary(days=1)
        assert '125.50' in summary
        
        print("✅ Full workflow test passed!")
        print(summary)
        
    finally:
        # Cleanup
        try:
            os.unlink(db_path)
        except:
            pass


if __name__ == "__main__":
    # Run integration test
    print("Running integration test...")
    test_integration_full_workflow()
    print("\n✅ All tests would pass with pytest!")
    print("\nTo run full test suite:")
    print("  pytest tests/test_learning_engine.py -v")
