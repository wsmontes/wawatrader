#!/usr/bin/env python3
"""
Backtest Example

Demonstrates how to run a backtest on historical data.

Usage:
    python scripts/run_backtest.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from wawatrader.backtester import Backtester
from loguru import logger


def main():
    """Run a sample backtest"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Run backtest on historical data')
    parser.add_argument('--symbols', type=str, help='Comma-separated list of symbols (e.g., AAPL,MSFT)')
    parser.add_argument('--start', type=str, default='2024-01-01', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, default='2024-12-31', help='End date (YYYY-MM-DD)')
    parser.add_argument('--capital', type=float, default=100000, help='Initial capital')
    
    args = parser.parse_args()
    
    logger.info("WawaTrader Backtest Example")
    logger.info("=" * 60)
    
    # Get symbols
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(',')]
    else:
        # Let LLM discover interesting symbols for backtesting
        from wawatrader.market_intelligence import MarketIntelligence
        logger.info("🤖 No symbols provided - LLM will discover trending symbols...")
        
        try:
            intel = MarketIntelligence()
            universe = intel.get_dynamic_universe(min_mentions=5, max_results=10)
            symbols = [stock['symbol'] for stock in universe[:5]]  # Top 5 for backtest
            logger.info(f"🧠 Selected {len(symbols)} trending symbols: {', '.join(symbols)}")
        except Exception as e:
            logger.warning(f"Failed to get dynamic symbols: {e}")
            logger.info("📋 Provide symbols with --symbols flag (e.g., --symbols AAPL,MSFT)")
            return
    
    start_date = args.start
    end_date = args.end
    initial_capital = args.capital
    
    logger.info(f"Symbols: {', '.join(symbols)}")
    logger.info(f"Period: {start_date} to {end_date}")
    logger.info(f"Initial capital: ${initial_capital:,.2f}")
    logger.info("")
    
    # Create backtester
    backtester = Backtester(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        commission_per_share=0.0,  # Alpaca has $0 commissions
        slippage_pct=0.001  # 0.1% slippage
    )
    
    try:
        # Run backtest
        stats = backtester.run()
        
        # Generate and print report
        report = backtester.generate_report(stats)
        print(report)
        
        # Save results
        backtester.save_results()
        
        # Summary comparison
        logger.info("\nQUICK COMPARISON:")
        logger.info(f"Strategy Return:     {stats.total_return*100:+.2f}%")
        logger.info(f"Buy-Hold Return:     {stats.benchmark_return*100:+.2f}%")
        logger.info(f"Alpha:               {stats.alpha*100:+.2f}%")
        
        if stats.total_return > stats.benchmark_return:
            logger.success(f"✅ Strategy BEAT buy-and-hold by {stats.alpha*100:.2f}%")
        else:
            logger.warning(f"⚠️  Strategy UNDERPERFORMED buy-and-hold by {abs(stats.alpha)*100:.2f}%")
        
        logger.info("")
        logger.info(f"Sharpe Ratio: {stats.sharpe_ratio:.2f}")
        logger.info(f"Win Rate: {stats.win_rate*100:.1f}%")
        logger.info(f"Max Drawdown: {stats.max_drawdown*100:.2f}%")
        
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
