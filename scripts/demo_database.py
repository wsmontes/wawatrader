#!/usr/bin/env python3
"""
Database Demo

Demonstrates database functionality and usage examples.

Usage:
    python scripts/demo_database.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import date
from wawatrader.database import (
    DatabaseManager,
    Trade,
    TradingDecision,
    LLMInteraction,
    PerformanceSnapshot
)
from loguru import logger


def demo_database_features():
    """Demonstrate database features"""
    
    logger.info("╔═══════════════════════════════════════════════════════════╗")
    logger.info("║       WawaTrader Database - Feature Demo                 ║")
    logger.info("╚═══════════════════════════════════════════════════════════╝")
    logger.info("")
    
    # Create database
    db = DatabaseManager("demo.db")
    
    logger.info("1️⃣  DATABASE INITIALIZATION")
    logger.info("─" * 60)
    logger.info(f"✅ Database created: demo.db")
    logger.info(f"   Path: {db.db_path}")
    logger.info("")
    
    # Show tables
    stats = db.get_table_stats()
    logger.info("📊 Tables:")
    for table, count in stats.items():
        logger.info(f"   • {table}: {count} rows")
    logger.info("")
    
    # 2. Add Trade
    logger.info("2️⃣  TRADE RECORDING")
    logger.info("─" * 60)
    
    trade = Trade(
        symbol="AAPL",
        side="buy",
        quantity=100,
        price=150.0,
        commission=0.0,
        order_id="ORDER-123"
    )
    
    trade_id = db.add_trade(trade)
    logger.info(f"✅ Trade recorded (ID: {trade_id})")
    logger.info(f"   {trade.side.upper()} {trade.quantity} {trade.symbol} @ ${trade.price:.2f}")
    logger.info(f"   Total: ${trade.total_value:,.2f}")
    logger.info("")
    
    # 3. Add Decision
    logger.info("3️⃣  DECISION LOGGING")
    logger.info("─" * 60)
    
    decision = TradingDecision(
        symbol="AAPL",
        action="buy",
        shares=100,
        price=150.0,
        confidence=0.85,
        sentiment="bullish",
        reasoning="Strong technical signals + positive LLM sentiment",
        risk_approved=True,
        risk_reason="Position size within limits",
        executed=True
    )
    
    decision_id = db.add_decision(decision)
    logger.info(f"✅ Decision recorded (ID: {decision_id})")
    logger.info(f"   Action: {decision.action.upper()}")
    logger.info(f"   Confidence: {decision.confidence*100:.1f}%")
    logger.info(f"   Risk Approved: {decision.risk_approved}")
    logger.info(f"   Executed: {decision.executed}")
    logger.info("")
    
    # 4. Add LLM Interaction
    logger.info("4️⃣  LLM INTERACTION TRACKING")
    logger.info("─" * 60)
    
    llm_interaction = LLMInteraction(
        symbol="AAPL",
        prompt="Analyze AAPL with RSI=65, MACD=1.5",
        response='{"action": "buy", "confidence": 0.85, "reasoning": "Strong momentum"}',
        model="gemma-3-4b",
        confidence=0.85,
        action="buy",
        success=True
    )
    
    interaction_id = db.add_llm_interaction(llm_interaction)
    logger.info(f"✅ LLM interaction recorded (ID: {interaction_id})")
    logger.info(f"   Model: {llm_interaction.model}")
    logger.info(f"   Action: {llm_interaction.action}")
    logger.info(f"   Success: {llm_interaction.success}")
    logger.info("")
    
    # 5. Add Performance Snapshot
    logger.info("5️⃣  PERFORMANCE SNAPSHOTS")
    logger.info("─" * 60)
    
    snapshot = PerformanceSnapshot(
        date=date.today().isoformat(),
        portfolio_value=115000.0,
        cash=30000.0,
        positions_value=85000.0,
        daily_pnl=2500.0,
        daily_pnl_pct=2.22,
        total_return=0.15,
        num_positions=3,
        num_trades_today=5
    )
    
    snapshot_id = db.add_performance_snapshot(snapshot)
    logger.info(f"✅ Snapshot recorded (ID: {snapshot_id})")
    logger.info(f"   Portfolio Value: ${snapshot.portfolio_value:,.2f}")
    logger.info(f"   Daily P&L: ${snapshot.daily_pnl:+,.2f} ({snapshot.daily_pnl_pct:+.2f}%)")
    logger.info(f"   Total Return: {snapshot.total_return*100:.2f}%")
    logger.info("")
    
    # 6. Query Data
    logger.info("6️⃣  DATA QUERIES")
    logger.info("─" * 60)
    
    # Get trades
    trades = db.get_trades(symbol="AAPL")
    logger.info(f"📊 Trades for AAPL: {len(trades)}")
    
    # Get decisions
    decisions = db.get_decisions(executed_only=True)
    logger.info(f"📊 Executed decisions: {len(decisions)}")
    
    # Get LLM interactions
    interactions = db.get_llm_interactions(symbol="AAPL")
    logger.info(f"📊 LLM interactions for AAPL: {len(interactions)}")
    
    # Get snapshots
    snapshots = db.get_performance_snapshots(limit=5)
    logger.info(f"📊 Recent snapshots: {len(snapshots)}")
    logger.info("")
    
    # 7. Analytics
    logger.info("7️⃣  ANALYTICS")
    logger.info("─" * 60)
    
    # Trade summary
    summary = db.get_trade_summary(symbol="AAPL")
    logger.info(f"📈 Trade Summary (AAPL):")
    logger.info(f"   Total trades: {summary.get('total_trades', 0)}")
    logger.info(f"   Total bought: {summary.get('total_bought', 0)}")
    logger.info(f"   Total sold: {summary.get('total_sold', 0)}")
    
    # Win rate
    win_rate = db.get_win_rate(symbol="AAPL")
    logger.info(f"")
    logger.info(f"📈 Decision Stats (AAPL):")
    logger.info(f"   Total decisions: {win_rate.get('total_decisions', 0)}")
    logger.info(f"   Executed: {win_rate.get('executed_count', 0)}")
    logger.info(f"   Avg confidence: {win_rate.get('avg_confidence', 0)*100:.1f}%")
    logger.info("")
    
    # 8. Table Stats
    logger.info("8️⃣  DATABASE STATISTICS")
    logger.info("─" * 60)
    
    stats = db.get_table_stats()
    logger.info("📊 Current row counts:")
    for table, count in stats.items():
        logger.info(f"   • {table}: {count} rows")
    logger.info("")
    
    # 9. Export
    logger.info("9️⃣  DATA EXPORT")
    logger.info("─" * 60)
    
    # Export to CSV
    db.export_to_csv('trades', 'demo_trades.csv')
    logger.info("✅ Exported trades to demo_trades.csv")
    
    # Export to JSON
    db.export_to_json('decisions', 'demo_decisions.json')
    logger.info("✅ Exported decisions to demo_decisions.json")
    logger.info("")
    
    # 10. Usage Examples
    logger.info("🔟 USAGE EXAMPLES")
    logger.info("─" * 60)
    logger.info("from wawatrader.database import get_database, Trade")
    logger.info("")
    logger.info("# Get database instance")
    logger.info("db = get_database('wawatrader.db')")
    logger.info("")
    logger.info("# Record a trade")
    logger.info("trade = Trade(")
    logger.info("    symbol='AAPL',")
    logger.info("    side='buy',")
    logger.info("    quantity=100,")
    logger.info("    price=150.0")
    logger.info(")")
    logger.info("trade_id = db.add_trade(trade)")
    logger.info("")
    logger.info("# Query trades")
    logger.info("trades = db.get_trades(symbol='AAPL', limit=10)")
    logger.info("")
    logger.info("# Export data")
    logger.info("db.export_to_csv('trades', 'trades.csv')")
    logger.info("")
    
    logger.success("✅ Database demo complete!")
    logger.info("")
    logger.info("Database features:")
    logger.info("  ✅ SQLite-based (portable)")
    logger.info("  ✅ 4 main tables (trades, decisions, llm, snapshots)")
    logger.info("  ✅ Full CRUD operations")
    logger.info("  ✅ Analytics functions")
    logger.info("  ✅ CSV/JSON export")
    logger.info("  ✅ Indexed for performance")
    logger.info("  ✅ Singleton pattern")
    logger.info("")
    
    # Cleanup
    db.close()
    Path("demo.db").unlink(missing_ok=True)
    Path("demo_trades.csv").unlink(missing_ok=True)
    Path("demo_decisions.json").unlink(missing_ok=True)
    
    logger.info("Demo files cleaned up")


def main():
    """Main entry point"""
    try:
        demo_database_features()
        return 0
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
