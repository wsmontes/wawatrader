#!/usr/bin/env python3
"""
Backtester Quick Demo

Demonstrates backtester functionality with a quick test.
Shows key features without running a full year-long backtest.

Usage:
    python scripts/demo_backtest.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from wawatrader.backtester import Backtester, BacktestStats
from loguru import logger


def demo_backtest_components():
    """Demonstrate backtester components"""
    
    logger.info("╔═══════════════════════════════════════════════════════════╗")
    logger.info("║         WawaTrader Backtester - Component Demo           ║")
    logger.info("╚═══════════════════════════════════════════════════════════╝")
    logger.info("")
    
    # 1. Initialization
    logger.info("1️⃣  INITIALIZATION")
    logger.info("─" * 60)
    
    bt = Backtester(
        symbols=["AAPL", "MSFT"],
        start_date="2024-01-01",
        end_date="2024-12-31",
        initial_capital=100000,
        commission_per_share=0.0,
        slippage_pct=0.001
    )
    
    logger.info(f"✅ Backtester created")
    logger.info(f"   Symbols: {', '.join(bt.symbols)}")
    logger.info(f"   Period: 2024-01-01 to 2024-12-31")
    logger.info(f"   Capital: ${bt.initial_capital:,.2f}")
    logger.info(f"   Commission: ${bt.commission_per_share}/share")
    logger.info(f"   Slippage: {bt.slippage_pct*100:.2f}%")
    logger.info("")
    
    # 2. Simulated Trade Execution
    logger.info("2️⃣  TRADE EXECUTION")
    logger.info("─" * 60)
    
    current_date = datetime(2024, 1, 15)
    
    # Buy AAPL
    success = bt.execute_trade(
        symbol="AAPL",
        side="buy",
        shares=100,
        price=150.0,
        current_date=current_date,
        reasoning="Strong technical signals + positive LLM sentiment",
        confidence=0.85
    )
    
    logger.info(f"✅ BUY executed: {success}")
    logger.info(f"   Symbol: AAPL")
    logger.info(f"   Shares: 100")
    logger.info(f"   Price: $150.00")
    logger.info(f"   Position: {bt.positions.get('AAPL', 0)} shares")
    logger.info(f"   Cash remaining: ${bt.cash:,.2f}")
    logger.info("")
    
    # Sell AAPL (profitable)
    success = bt.execute_trade(
        symbol="AAPL",
        side="sell",
        shares=100,
        price=165.0,
        current_date=datetime(2024, 2, 15),
        reasoning="Target price reached, take profit",
        confidence=0.80
    )
    
    logger.info(f"✅ SELL executed: {success}")
    logger.info(f"   Symbol: AAPL")
    logger.info(f"   Shares: 100")
    logger.info(f"   Price: $165.00")
    logger.info(f"   Position: {bt.positions.get('AAPL', 0)} shares")
    logger.info(f"   Cash: ${bt.cash:,.2f}")
    
    if bt.trades:
        trade = bt.trades[-1]
        logger.info(f"   P&L: ${trade.pnl:+,.2f} ({trade.pnl_pct:+.2f}%)")
    logger.info("")
    
    # 3. Portfolio Valuation
    logger.info("3️⃣  PORTFOLIO VALUATION")
    logger.info("─" * 60)
    
    # Add some daily values for testing
    bt.daily_values = [
        (datetime(2024, 1, 1), 100000),
        (datetime(2024, 1, 15), 100000),
        (datetime(2024, 2, 15), 101500),
        (datetime(2024, 12, 31), 110000),
    ]
    
    for date, value in bt.daily_values:
        logger.info(f"   {date.strftime('%Y-%m-%d')}: ${value:>12,.2f}")
    
    logger.info("")
    
    # 4. Performance Metrics
    logger.info("4️⃣  PERFORMANCE METRICS")
    logger.info("─" * 60)
    
    # Test drawdown calculation
    max_dd, dd_duration = bt.calculate_max_drawdown()
    logger.info(f"✅ Max Drawdown: {max_dd*100:.2f}%")
    logger.info(f"   Duration: {dd_duration} days")
    logger.info("")
    
    # 5. Report Generation
    logger.info("5️⃣  REPORT GENERATION")
    logger.info("─" * 60)
    
    # Create sample stats
    stats = BacktestStats(
        total_return=0.10,
        annualized_return=0.10,
        benchmark_return=0.08,
        alpha=0.02,
        sharpe_ratio=1.2,
        max_drawdown=0.05,
        max_drawdown_duration=15,
        volatility=0.15,
        total_trades=50,
        winning_trades=30,
        losing_trades=20,
        win_rate=0.60,
        avg_win=500,
        avg_loss=-300,
        profit_factor=1.67,
        avg_trade_duration=5.0,
        max_position_size=0.10,
        avg_position_size=0.08,
        total_commissions=0,
        total_slippage=150,
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 12, 31),
        trading_days=252,
        starting_capital=100000,
        ending_capital=110000
    )
    
    report = bt.generate_report(stats)
    print(report)
    
    # 6. Key Features
    logger.info("6️⃣  KEY FEATURES")
    logger.info("─" * 60)
    logger.info("✅ Point-in-time data (no lookahead bias)")
    logger.info("✅ Realistic trade execution (slippage + commission)")
    logger.info("✅ Complete performance metrics")
    logger.info("✅ Benchmark comparison (buy-and-hold)")
    logger.info("✅ Trade history tracking")
    logger.info("✅ Risk-adjusted returns (Sharpe ratio)")
    logger.info("✅ Drawdown analysis")
    logger.info("")
    
    # 7. Usage Examples
    logger.info("7️⃣  USAGE EXAMPLES")
    logger.info("─" * 60)
    logger.info("Run full backtest:")
    logger.info("  python scripts/run_backtest.py")
    logger.info("")
    logger.info("Custom parameters:")
    logger.info("  bt = Backtester(")
    logger.info('    symbols=["AAPL", "MSFT", "GOOGL"],')
    logger.info('    start_date="2023-01-01",')
    logger.info('    end_date="2024-12-31",')
    logger.info("    initial_capital=250000,")
    logger.info("    slippage_pct=0.002")
    logger.info("  )")
    logger.info("  stats = bt.run()")
    logger.info("  bt.save_results()")
    logger.info("")
    
    logger.success("✅ Backtester demo complete!")
    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. Review test results: pytest tests/test_backtester.py -v")
    logger.info("  2. Run full backtest: python scripts/run_backtest.py")
    logger.info("  3. Analyze results in backtest_results/ directory")
    logger.info("")


def main():
    """Main entry point"""
    try:
        demo_backtest_components()
        return 0
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
