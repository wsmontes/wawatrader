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
    """Graceful shutdown handler"""
    logger.info("")
    logger.info("🛑 Stopping trading system...")
    
    # Stop position monitoring first
    try:
        if 'agent' in globals():
            agent.stop_position_monitoring()
            logger.info("✅ PositionManager stopped")
    except Exception as e:
        logger.error(f"⚠️  Error stopping PositionManager: {e}")
    
    logger.info("📊 Dashboard will stop automatically")
    logger.info("⚡ Trading agent stopped")
    logger.info("🏁 Shutdown complete")
    sys.exit(0)

def main():
    print("🚀 WawaTrader - Live Paper Trading System with Dashboard")
    print("=" * 70)
    print()
    
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Step 0: Check market status first
        print("📊 Checking market status...")
        from wawatrader.alpaca_client import get_client
        temp_client = get_client()
        market_status = temp_client.get_market_status()
        
        print()
        print("🕐 MARKET STATUS")
        print("-" * 70)
        print(f"   {market_status.get('status_text', '⚠️ UNKNOWN')}")
        print(f"   {market_status.get('status_message', 'Unable to determine status')}")
        print(f"   Trading Hours: {market_status.get('trading_hours', '9:30 AM - 4:00 PM ET')}")
        
        if not market_status.get('is_open', False):
            print()
            print("   💡 Note: Trading agent will start now and wait for market to open")
            print("            The system will automatically begin trading when market opens")
            print(f"            You can monitor progress on the dashboard")
        else:
            print()
            print("   🟢 Market is OPEN - Trading will begin immediately!")
        
        print("-" * 70)
        print()
        
        # Step 1: Start Dashboard
        print("🖥️ Starting integrated dashboard...")
        dashboard_success = start_dashboard()
        
        # Step 2: Initialize Trading Agent
        print("⚡ Initializing trading agent...")
        
        # Let LLM build dynamic watchlist from market intelligence
        from wawatrader.market_intelligence import MarketIntelligence
        
        logger.info("🤖 LLM will build dynamic watchlist from market intelligence...")
        
        symbols = []
        try:
            # Try Alpaca active stocks first
            symbols = temp_client.get_active_stocks(limit=50)
            logger.info(f"📋 Got {len(symbols)} active stocks from Alpaca")
        except Exception as e:
            logger.warning(f"Alpaca active stocks unavailable: {e}")
            # Fall back to market intelligence
            try:
                intel = MarketIntelligence()
                universe = intel.get_dynamic_universe(min_mentions=2, max_results=50)
                symbols = [stock['symbol'] for stock in universe]
                logger.info(f"🧠 LLM discovered {len(symbols)} symbols from market intelligence")
            except Exception as e2:
                logger.error(f"Failed to build dynamic watchlist: {e2}")
                logger.info("⚠️ Starting with empty watchlist - LLM will discover symbols from news")
                symbols = []
        
        agent = TradingAgent(symbols=symbols, dry_run=False)  # Paper trading mode - no real money
        
        # Step 2.5: Start PositionManager monitoring (CRITICAL!)
        print("📡 Starting event-driven position monitoring...")
        from datetime import datetime, time as dt_time
        # Set market close time (3:30 PM EST for 30-min safety buffer)
        market_close = datetime.now().replace(hour=15, minute=30, second=0, microsecond=0)
        agent.set_market_close_time(market_close)
        agent.start_position_monitoring()
        print("✅ PositionManager monitoring active (15-second polling)")
        
        print()
        print("🎯 SYSTEM READY")
        print("=" * 70)
        print(f"📊 Trading Symbols: {', '.join(symbols)}")
        print(f"💰 Account Status: Paper Trading Account")
        print(f"🧠 Scheduling: Intelligent & Adaptive")
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
        print("  ✅ Intelligent scheduling (70% resource reduction)")
        if dashboard_success:
            print("  ✅ Live dashboard (30s updates)")
        else:
            print("  ⚠️ Live dashboard (failed to start)")
        print("  ✅ Complete audit trail")
        print()
        
        # Market-specific guidance
        if market_status.get('is_open', False):
            print("🟢 Market is OPEN - Trading actively now!")
            print("   - 5-min trading cycles")
            print("   - 30-min quick intelligence checks")
            print("   - 2-hour deep analysis")
        else:
            print("💤 Market is CLOSED - Adaptive mode active")
            print(f"   Trading will begin automatically when market opens")
            print("   - Minimal overnight monitoring")
            print("   - Strategic pre-market prep (6-9:30 AM)")
            print("   - Evening deep analysis (optional)")
        
        print()
        print("Press Ctrl+C to stop the entire system")
        print("=" * 70)
        print()
        
        # Step 3: Start continuous trading with intelligent scheduling
        logger.info("🧠 Starting intelligent trading system...")
        logger.info("   Adaptive scheduling enabled for optimal resource usage")
        agent.run_continuous_intelligent()
        
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