#!/usr/bin/env python3
"""
Start WawaTrader Live Paper Trading

This runs the actual trading system continuously with integrated dashboard.
"""

import sys
from pathlib import Path
import subprocess
import threading
import time
import atexit

# Add project root to path (not scripts directory)
project_root = Path(__file__).parent.parent  # Go up from scripts/ to wawatrader project root
sys.path.insert(0, str(project_root))

from wawatrader.trading_agent import TradingAgent
from wawatrader.dashboard import Dashboard
from loguru import logger
import signal

# Global dashboard thread
dashboard_thread = None

def start_dashboard():
    """Start dashboard in background thread"""
    global dashboard_thread
    try:
        logger.info("🖥️ Starting dashboard server...")
        dashboard = Dashboard()
        dashboard_thread = threading.Thread(
            target=dashboard.run,
            kwargs={
                'host': '127.0.0.1',
                'port': 8050,
                'debug': False
            },
            daemon=True
        )
        dashboard_thread.start()
        time.sleep(3)  # Give dashboard time to start
        logger.info("✅ Dashboard running at http://127.0.0.1:8050")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to start dashboard: {e}")
        logger.warning("⚠️ Trading will continue without dashboard")
        return False

def signal_handler(sig, frame):
    logger.info("🛑 Stopping trading system...")
    logger.info("📊 Dashboard will stop automatically")
    sys.exit(0)

def main():
    print("🚀 WawaTrader - Live Paper Trading System with Dashboard")
    print("=" * 70)
    print()
    
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Step 1: Start Dashboard
        print("🖥️ Starting integrated dashboard...")
        dashboard_success = start_dashboard()
        
        # Step 2: Initialize Trading Agent
        print("⚡ Initializing trading agent...")
        symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]
        agent = TradingAgent(symbols=symbols, dry_run=False)  # NOT dry run - real paper trading
        
        print()
        print("🎯 SYSTEM READY")
        print("=" * 70)
        print(f"📊 Trading Symbols: {', '.join(symbols)}")
        print(f"💰 Account Status: Paper Trading Account")
        print(f"🔄 Trading Interval: 5 minutes")
        print(f"⚡ Mode: LIVE PAPER TRADING")
        if dashboard_success:
            print(f"📈 Dashboard: http://127.0.0.1:8050")
        else:
            print(f"📈 Dashboard: Not available (trading continues)")
        print()
        print("🎯 Trading Rules Active:")
        print("  • Max 10% position size per stock")
        print("  • Max 2% daily loss limit")
        print("  • AI + Technical analysis for decisions")
        print("  • All trades logged and monitored")
        print("  • Real-time dashboard monitoring")
        print()
        print("🔥 FEATURES RUNNING:")
        print("  ✅ Real-time market data (IEX)")
        print("  ✅ Technical analysis (21+ indicators)")
        print("  ✅ LLM sentiment analysis (Gemma 3)")
        print("  ✅ Risk management (conservative)")
        if dashboard_success:
            print("  ✅ Live dashboard (30s updates)")
        else:
            print("  ⚠️ Live dashboard (failed to start)")
        print("  ✅ Complete audit trail")
        print()
        print("Press Ctrl+C to stop the entire system")
        print("=" * 70)
        print()
        
        # Step 3: Start continuous trading
        logger.info("🚀 Starting live paper trading loop...")
        agent.run_continuous(interval_minutes=5)
        
    except KeyboardInterrupt:
        logger.info("🛑 Trading system stopped by user")
        print("\n🛑 System shutdown complete")
        print("📊 Dashboard stopped")
        print("⚡ Trading agent stopped") 
    except Exception as e:
        logger.error(f"❌ Trading system error: {e}")
        raise

if __name__ == "__main__":
    main()