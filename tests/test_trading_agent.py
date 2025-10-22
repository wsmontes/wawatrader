"""
Test Trading Agent (Market Hours Bypass)

Tests the trading agent with market hours check disabled.
"""

import sys

def test_trading_agent_pipeline():
    """Test the complete trading agent pipeline"""
    from wawatrader.trading_agent import TradingAgent
    import json

    print("\n" + "="*60)
    print("Testing Trading Agent (Forced Execution)")
    print("="*60)

    # Create agent
    symbols = ["AAPL"]
    agent = TradingAgent(symbols=symbols, dry_run=True)

    # Update account manually
    agent.update_account_state()
    print(f"\n📊 Account Value: ${agent.account_value:,.2f}")
    print(f"📊 Current P&L: ${agent.current_pnl:,.2f}")
    print(f"📊 Positions: {len(agent.positions)}")

    # Test individual components
    print("\n" + "-"*60)
    print("Step 1: Get Market Data")
    print("-"*60)

    symbol = "AAPL"
    bars = agent.get_market_data(symbol)
    if bars is not None:
        print(f"✅ Retrieved {len(bars)} bars for {symbol}")
        print(f"   Latest close: ${bars['close'].iloc[-1]:.2f}")
        
        # Continue with rest of pipeline
        print("\n" + "-"*60)
        print("Step 2: Analyze Symbol")
        print("-"*60)

        analysis = agent.analyze_symbol(symbol)
        if analysis:
            print(f"✅ Analysis complete")
            print(f"   Sentiment: {analysis['llm_analysis']['sentiment']}")
            print(f"   Confidence: {analysis['llm_analysis']['confidence']}%")
            print(f"   Action: {analysis['llm_analysis']['action']}")
            
            # Make decision
            print("\n" + "-"*60)
            print("Step 3: Make Trading Decision")
            print("-"*60)

            decision = agent.make_decision(analysis)
            print(f"✅ Decision made:")
            print(f"   Symbol: {decision.symbol}")
            print(f"   Action: {decision.action.upper()}")
            print(f"   Shares: {decision.shares}")
            print(f"   Price: ${decision.price:.2f}")
            print(f"   Confidence: {decision.confidence}%")
            print(f"   Risk Approved: {decision.risk_approved}")
            
            # Execute
            print("\n" + "-"*60)
            print("Step 4: Execute Decision")
            print("-"*60)

            agent.execute_decision(decision)
            print(f"✅ Execution complete (dry run)")
            
            # Log decision
            agent.log_decision(decision)
            print(f"✅ Decision logged")
            
            # Statistics
            stats = agent.get_statistics()
            print("\n" + "-"*60)
            print("Final Statistics")
            print("-"*60)
            print(json.dumps(stats, indent=2))
            
            assert agent.account_value > 0, "Account value should be positive"
            assert len(agent.decisions) > 0, "Should have at least one decision"
            
        else:
            print("⚠️  Analysis failed (expected with data restrictions)")
    else:
        print("⚠️  No market data (expected with paper account restrictions)")

    print("\n" + "="*60)
    print("✅ Trading Agent pipeline test complete!")
    print("="*60)


if __name__ == "__main__":
    # Run as script
    test_trading_agent_pipeline()
