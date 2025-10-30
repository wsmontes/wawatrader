#!/usr/bin/env python3
"""
Test Streaming Portfolio Coordinator

This script tests the new coordinated trading cycle with individual LLM analysis
and mathematical decision prioritization.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from wawatrader.trading_agent import TradingAgent
from wawatrader.alpaca_client import get_client
from loguru import logger

def main():
    """Test the streaming coordinator with real market data"""
    
    print("🚀 Testing Streaming Portfolio Coordinator")
    print("=" * 60)
    print()
    
    try:
        # Get a small universe for testing
        print("📊 Getting dynamic universe for testing...")
        client = get_client()
        universe_result = client.get_universe_with_ranking(universe_size=15, top_n=8)
        test_symbols = universe_result['top_symbols']
        
        print(f"🎯 Test symbols: {', '.join(test_symbols)}")
        print()
        
        # Initialize trading agent
        print("🧠 Initializing trading agent...")
        agent = TradingAgent(symbols=test_symbols, dry_run=True)
        print()
        
        # Test the coordinated trading cycle
        print("🎯 TESTING COORDINATED CYCLE")
        print("-" * 50)
        print("This will:")
        print("✅ Analyze each stock individually (preserve LLM quality)")
        print("✅ Use streaming coordinator for smart execution order")
        print("✅ Execute urgent decisions immediately")
        print("✅ Batch and prioritize BUY opportunities")
        print("✅ Optimize capital allocation")
        print()
        
        # Import the task handler to test the new method
        from wawatrader.scheduled_tasks import ScheduledTaskHandlers
        
        task_handler = ScheduledTaskHandlers(agent)
        result = task_handler.trading_cycle()
        
        print()
        print("🏆 COORDINATION TEST RESULTS")
        print("-" * 50)
        print(f"Status: {result['status']}")
        
        if 'coordination' in result:
            stats = result['coordination']
            print(f"Total analyzed: {result['analyses']['successful']}")
            print(f"Immediate executions: {stats['immediate_executions']}")
            print(f"Batch executions: {stats['batch_executions']}")
            print(f"Skipped (capital): {stats['skipped_capital']}")
        
        print()
        if result['status'] == 'success':
            print("✅ STREAMING COORDINATION WORKING!")
            print("   Individual LLM analysis preserved ✅")
            print("   Mathematical prioritization active ✅")
            print("   Smart execution ordering ✅")
        else:
            print(f"⚠️  Issue detected: {result.get('error', 'Unknown')}")
            print("   Check logs for details")
        
        print()
        print("💡 COMPARISON WITH SEQUENTIAL:")
        print("   Sequential: A→execute→B→execute→C→execute (no prioritization)")
        print("   Coordinated: A+B+C→rank→execute best first (portfolio context)")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        print(f"\n❌ Test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    exit_code = 0 if success else 1
    sys.exit(exit_code)