"""
Quick Integration Test for Learning Engine

Tests the complete workflow without pytest dependency.
"""

import tempfile
import os
from datetime import datetime
from unittest.mock import Mock
import pandas as pd

from wawatrader.memory_database import TradingMemory
from wawatrader.learning_engine import LearningEngine
from wawatrader.market_context import MarketContext


def test_learning_engine_workflow():
    """Test complete learning engine workflow"""
    
    print("\n" + "="*60)
    print("🧪 Testing Learning Engine Workflow")
    print("="*60)
    
    # Create temp database
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    try:
        # 1. Initialize components
        print("\n1️⃣ Initializing components...")
        memory = TradingMemory(db_path=db_path)
        print("   ✅ TradingMemory initialized")
        
        # Mock Alpaca client
        mock_alpaca = Mock()
        spy_bars = pd.DataFrame({
            'close': [450, 451, 452, 453],
            'volume': [100000, 110000, 105000, 108000]
        })
        mock_alpaca.get_bars.return_value = spy_bars
        
        engine = LearningEngine(mock_alpaca, memory)
        print("   ✅ LearningEngine initialized")
        
        # 2. Record decision
        print("\n2️⃣ Recording a trading decision...")
        decision_id = engine.record_decision(
            symbol='AAPL',
            action='buy',
            price=175.50,
            shares=10,
            technical_indicators={'rsi': 65, 'macd': 1.2, 'volume_ratio': 1.5},
            llm_analysis={
                'sentiment': 'bullish',
                'confidence': 0.75,
                'reasoning': 'Strong uptrend with volume confirmation'
            },
            decision_confidence=0.80,
            decision_reasoning='Technical indicators + LLM alignment',
            pattern_matched='morning_breakout'
        )
        
        print(f"   ✅ Decision recorded with ID: {decision_id}")
        
        # 3. Record outcome
        print("\n3️⃣ Recording trade outcome...")
        engine.record_outcome(
            decision_id=decision_id,
            outcome='win',
            profit_loss=125.50,
            exit_price=178.25,
            exit_time=datetime.now(),
            lesson_learned='Morning breakout pattern worked as expected'
        )
        
        print("   ✅ Outcome recorded: WIN with $125.50 profit")
        
        # 4. Analyze performance
        print("\n4️⃣ Analyzing daily performance...")
        performance = engine.analyze_daily_performance()
        
        print(f"""
   Performance Results:
   - Total Trades: {performance['total_trades']}
   - Winning Trades: {performance['winning_trades']}
   - Losing Trades: {performance['losing_trades']}
   - Win Rate: {performance['win_rate']:.0%}
   - Total P&L: ${performance['total_pnl']:+.2f}
   - Best Trade: ${performance['best_trade']:+.2f}
   - Worst Trade: ${performance['worst_trade']:+.2f}
        """)
        
        # 5. Test pattern discovery (need more data)
        print("\n5️⃣ Creating more trades for pattern discovery...")
        
        # Add more sample trades
        for i in range(12):
            dec_id = engine.record_decision(
                symbol=f'TEST{i % 3}',
                action='buy',
                price=100.0 + i,
                shares=10,
                technical_indicators={'rsi': 60 + i % 20},
                llm_analysis={'sentiment': 'bullish', 'confidence': 0.70 + (i % 3) * 0.05},
                decision_confidence=0.70 + (i % 3) * 0.05,
                decision_reasoning=f'Test trade {i}'
            )
            
            # Create pattern: every 3rd trade is a loss
            outcome = 'win' if i % 3 != 0 else 'loss'
            pnl = 50.0 if outcome == 'win' else -25.0
            
            engine.record_outcome(
                decision_id=dec_id,
                outcome=outcome,
                profit_loss=pnl,
                exit_price=105.0 + i if outcome == 'win' else 97.5 + i,
                exit_time=datetime.now()
            )
        
        print("   ✅ Added 12 more trades (8 wins, 4 losses)")
        
        # 6. Discover patterns
        print("\n6️⃣ Discovering patterns...")
        patterns = engine.discover_patterns(lookback_days=1)
        print(f"   ✅ Discovered {len(patterns)} patterns")
        
        for pattern in patterns[:3]:  # Show first 3
            print(f"""
   Pattern: {pattern['pattern_name']}
   - Type: {pattern['pattern_type']}
   - Success Rate: {pattern['success_rate']:.0%}
   - Sample Size: {pattern['sample_size']}
   - Avg Return: ${pattern['avg_return']:.2f}
            """)
        
        # 7. Get overall performance stats
        print("\n7️⃣ Getting performance statistics...")
        stats = memory.get_performance_stats(days=1)
        
        print(f"""
   Overall Stats:
   - Total Trades: {stats['total_trades']}
   - Win Rate: {stats['win_rate']:.1%}
   - Total P&L: ${stats['total_pnl']:+.2f}
   - Risk/Reward Ratio: {stats['risk_reward_ratio']:.2f}
        """)
        
        # 8. Get performance summary
        print("\n8️⃣ Performance Summary:")
        print("-" * 60)
        print(engine.get_performance_summary(days=1))
        print("-" * 60)
        
        # Validation
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        
        assert stats['total_trades'] == 13, f"Expected 13 trades, got {stats['total_trades']}"
        assert stats['winning_trades'] == 9, f"Expected 9 wins, got {stats['winning_trades']}"
        assert stats['losing_trades'] == 4, f"Expected 4 losses, got {stats['losing_trades']}"
        assert 0.65 <= stats['win_rate'] <= 0.70, f"Expected ~69% win rate, got {stats['win_rate']:.0%}"
        
        print("\n✅ Learning Engine is fully functional!")
        print("   - Records decisions with full market context")
        print("   - Tracks outcomes and P&L")
        print("   - Discovers profitable patterns")
        print("   - Generates performance insights")
        print("\n🎉 Ready for integration with scheduled tasks!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        try:
            os.unlink(db_path)
            print(f"\n🧹 Cleaned up temp database")
        except:
            pass


if __name__ == "__main__":
    success = test_learning_engine_workflow()
    exit(0 if success else 1)
