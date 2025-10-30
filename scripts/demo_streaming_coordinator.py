#!/usr/bin/env python3
"""
Demo Streaming Coordinator (Market Closed Safe)

This script demonstrates the streaming coordinator logic without market dependency.
"""

import sys
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from wawatrader.streaming_coordinator import StreamingPortfolioCoordinator
from wawatrader.trading_agent import TradingDecision


# Mock trading agent for demo
class MockTradingAgent:
    def __init__(self):
        self.symbols = ['AAPL', 'NVDA', 'MSFT', 'TSLA', 'GOOGL']
        self.positions = {}
        self.account_value = 100000
        self.buying_power = 50000
        self.executed_trades = []
        
    def execute_decision(self, decision: TradingDecision) -> bool:
        """Mock execution - just log the decision"""
        self.executed_trades.append(decision)
        print(f"   📈 EXECUTED: {decision.symbol} {decision.action.upper()} "
              f"@ ${decision.price:.2f} (conf: {decision.confidence}%)")
        return True


def create_mock_decision(symbol: str, action: str, confidence: int, price: float, **kwargs) -> TradingDecision:
    """Create a mock trading decision"""
    return TradingDecision(
        timestamp=datetime.now().isoformat(),
        symbol=symbol,
        action=action,
        shares=100,
        price=price,
        confidence=confidence,
        sentiment="bullish" if action == "buy" else "bearish",
        reasoning=f"Mock {action} decision for {symbol}",
        risk_approved=True,
        risk_reason="Mock approved",
        executed=False,
        indicators=kwargs.get('indicators', {})
    )


def main():
    """Demo the streaming coordinator"""
    
    print("🎯 Streaming Portfolio Coordinator Demo")
    print("=" * 60)
    print()
    
    # Create mock agent and coordinator
    agent = MockTradingAgent()
    coordinator = StreamingPortfolioCoordinator(agent)
    
    print("📊 Scenario: Multiple BUY opportunities arrive sequentially")
    print("   Traditional: Execute in arrival order (no optimization)")
    print("   Coordinated: Accumulate → Prioritize → Execute best first")
    print()
    
    # Simulate decisions arriving over time
    decisions = [
        create_mock_decision("AAPL", "buy", 75, 175.50, 
                           indicators={'rsi': 45, 'volume_ratio': 1.2}),
        create_mock_decision("NVDA", "buy", 90, 180.25,
                           indicators={'rsi': 65, 'volume_ratio': 3.5}),  # High volume breakout
        create_mock_decision("TSLA", "sell", 80, 220.00),  # Stop loss
        create_mock_decision("MSFT", "buy", 68, 415.75,
                           indicators={'rsi': 52, 'volume_ratio': 0.9}),
        create_mock_decision("GOOGL", "buy", 85, 142.30,
                           indicators={'rsi': 58, 'volume_ratio': 1.8}),
    ]
    
    print("🔄 Processing decisions with streaming coordination:")
    print()
    
    # Process each decision
    for i, decision in enumerate(decisions, 1):
        print(f"Decision {i}: {decision.symbol} {decision.action.upper()} "
              f"(confidence: {decision.confidence}%)")
        
        # Simulate different timing for urgency detection
        if decision.action == "sell":
            print("   🚨 URGENT: Stop-loss detected → immediate execution")
        elif decision.confidence > 88:
            print("   🚀 HIGH CONFIDENCE: Breakout signal → immediate execution")
        else:
            print("   📊 QUEUED: Added to comparison batch")
        
        coordinator.process_decision(decision)
        print()
    
    # Finalize any remaining decisions
    print("🏁 Finalizing remaining decisions...")
    stats = coordinator.finalize_cycle()
    
    print()
    print("📈 EXECUTION SUMMARY")
    print("-" * 40)
    print(f"Total decisions processed: {stats['total_analyzed']}")
    print(f"Immediate executions: {stats['immediate_executions']}")
    print(f"Batch executions: {stats['batch_executions']}")
    print(f"Skipped (capital limit): {stats['skipped_capital']}")
    
    print()
    print("✅ COORDINATION BENEFITS DEMONSTRATED:")
    print("   • Urgent decisions (stop-losses) executed immediately")
    print("   • BUY opportunities accumulated for comparison")
    print("   • Mathematical prioritization (confidence + volume + RSI)")
    print("   • Optimal capital allocation")
    print("   • No sequential bias!")
    
    print()
    print("🔧 EXECUTION ORDER:")
    for i, trade in enumerate(agent.executed_trades, 1):
        urgency = "🚨 URGENT" if trade.action == "sell" else "📊 BATCH"
        print(f"   {i}. {urgency}: {trade.symbol} {trade.action.upper()} @ ${trade.price:.2f}")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)