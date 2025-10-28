#!/usr/bin/env python3
"""
WawaTrader Full System Orchestrator

Starts and manages all components of the WawaTrader system:
- LM Studio health check and model verification
- Alpaca connection verification
- Real-time dashboard server
- System monitoring and health checks

This is the recommended way to run WawaTrader for a complete experience.
"""

import sys
import time
import subprocess
import signal
import atexit
from pathlib import Path
from typing import Optional, Dict, Any
import threading
from datetime import datetime, timedelta

# Add project to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from loguru import logger
from wawatrader.alpaca_client import get_client
from wawatrader.dashboard import Dashboard
from wawatrader.market_hours_manager import MarketHoursManager
from wawatrader.trading_agent import TradingAgent

# Configure logging
logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>", level="INFO")
logger.add(PROJECT_ROOT / "logs" / "system.log", rotation="1 day", retention="7 days", level="DEBUG")

class SystemOrchestrator:
    """Orchestrates all WawaTrader components"""
    
    def __init__(self):
        self.processes = []
        self.shutdown_requested = False
        
        # Register cleanup handlers
        atexit.register(self.cleanup)
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)
    
    def handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully"""
        if not self.shutdown_requested:
            logger.info("🛑 Shutdown requested...")
            self.shutdown_requested = True
            self.cleanup()
            sys.exit(0)
    
    def cleanup(self):
        """Clean up all running processes"""
        logger.info("🧹 Cleaning up processes...")
        for proc in self.processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                try:
                    proc.kill()
                except:
                    pass
    
    def check_lm_studio(self) -> Dict[str, Any]:
        """Check LM Studio availability and model status"""
        logger.info("🤖 Checking LM Studio...")
        
        try:
            # Direct API test without full LLMBridge initialization
            import requests
            
            lm_studio_url = "http://localhost:1234/v1/chat/completions"
            
            test_payload = {
                "model": "google/gemma-3-4b",
                "messages": [{"role": "user", "content": "Respond with just: OK"}],
                "temperature": 0.1,
                "max_tokens": 10
            }
            
            logger.debug("Testing LM Studio API...")
            response = requests.post(lm_studio_url, json=test_payload, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    content = data['choices'][0]['message']['content']
                    logger.success("✅ LM Studio: Connected and responding")
                    logger.debug(f"   Test response: {content}")
                    return {
                        'available': True,
                        'responding': True,
                        'message': 'LM Studio connected and model responding'
                    }
            
            logger.warning("⚠️  LM Studio: Unexpected response format")
            return {
                'available': True,
                'responding': False,
                'message': 'LM Studio connected but response format unexpected'
            }
                    
        except requests.exceptions.ConnectionError:
            logger.warning("⚠️  LM Studio: Cannot connect to http://localhost:1234")
            logger.info("   💡 Start LM Studio server and load a model")
            return {
                'available': False,
                'responding': False,
                'message': 'Cannot connect to LM Studio - start the server'
            }
        except requests.exceptions.Timeout:
            logger.warning("⚠️  LM Studio: Connection timeout")
            logger.info("   💡 LM Studio may be busy or model not loaded")
            return {
                'available': True,
                'responding': False,
                'message': 'LM Studio timeout - check if model is loaded'
            }
        except Exception as e:
            logger.error(f"❌ LM Studio check failed: {type(e).__name__}: {str(e)}")
            return {
                'available': False,
                'responding': False,
                'message': f'LM Studio check failed: {str(e)}'
            }
    
    def check_alpaca(self) -> Dict[str, Any]:
        """Check Alpaca API connection"""
        logger.info("📊 Checking Alpaca connection...")
        
        try:
            client = get_client()
            account = client.get_account()
            
            # Get account info
            if isinstance(account, dict):
                equity = float(account.get('equity', 0))
                buying_power = float(account.get('buying_power', 0))
                account_number = account.get('account_number', 'Unknown')
            else:
                equity = float(account.equity)
                buying_power = float(account.buying_power)
                account_number = account.account_number
            
            # Get market status
            market_status = client.get_market_status()
            is_open = market_status.get('is_open', False)
            status_text = market_status.get('status_text', 'UNKNOWN')
            
            logger.success(f"✅ Alpaca: Connected (Account: {account_number})")
            logger.info(f"   Portfolio: ${equity:,.2f} | Buying Power: ${buying_power:,.2f}")
            logger.info(f"   Market: {status_text}")
            
            return {
                'connected': True,
                'account_number': account_number,
                'equity': equity,
                'buying_power': buying_power,
                'market_open': is_open,
                'market_status': status_text
            }
            
        except Exception as e:
            logger.error(f"❌ Alpaca: Connection failed - {e}")
            return {
                'connected': False,
                'error': str(e)
            }
    
    def print_system_status(self, lm_studio_status: Dict, alpaca_status: Dict):
        """Print comprehensive system status"""
        print()
        print("=" * 70)
        print("🎯 WAWATRADER SYSTEM STATUS")
        print("=" * 70)
        
        # LM Studio Status
        print("\n🤖 LLM (LM Studio):")
        if lm_studio_status['available']:
            if lm_studio_status['responding']:
                print("   ✅ Connected and responding")
                print("   ✅ Model loaded and ready")
            else:
                print("   ⚠️  Connected but model may need manual loading")
                print("   💡 Open LM Studio and load a model manually")
        else:
            print("   ❌ Not available")
            print("   💡 Start LM Studio and load a model")
            print("   💡 System will continue without LLM sentiment analysis")
        
        # Alpaca Status  
        print("\n📊 Alpaca Markets:")
        if alpaca_status['connected']:
            print(f"   ✅ Connected (Account: {alpaca_status['account_number']})")
            print(f"   💰 Portfolio: ${alpaca_status['equity']:,.2f}")
            print(f"   💵 Buying Power: ${alpaca_status['buying_power']:,.2f}")
            print(f"   📈 Market: {alpaca_status['market_status']}")
        else:
            print("   ❌ Not connected")
            print("   💡 Check your .env file for ALPACA_API_KEY and ALPACA_SECRET_KEY")
        
        # Dashboard
        print("\n📊 Dashboard:")
        print("   🚀 Starting on http://localhost:8050")
        print("   🔄 Auto-refreshes every 30 seconds")
        print("   📈 Real-time portfolio and P&L tracking")
        
        # System Notes
        print("\n💡 System Notes:")
        if not alpaca_status['market_open']:
            print("   ⏰ Market is closed - system will monitor and wait")
        
        if not lm_studio_status['responding']:
            print("   ⚠️  LLM analysis disabled - using technical indicators only")
        
        print("\n" + "=" * 70)
        print("🚀 STARTING DASHBOARD...")
        print("=" * 70)
        print()
        print("   📱 Open: http://localhost:8050")
        print("   🛑 Stop: Press Ctrl+C")
        print()
    
    def start_active_trading(self):
        """Run active trading during market hours"""
        logger.info("💹 Starting active trading mode...")
        
        def trading_loop():
            """Background thread for active trading"""
            import time
            import json
            from wawatrader.trading_agent import TradingAgent
            
            # Get actively traded stocks from Alpaca (dynamic watchlist)
            alpaca = get_client()
            watchlist = []
            
            try:
                # Try to get dynamic watchlist from Alpaca
                watchlist = alpaca.get_active_stocks(limit=50)
                logger.info(f"📋 Dynamic watchlist loaded: {len(watchlist)} stocks")
            except Exception as e:
                logger.warning(f"⚠️  Failed to get dynamic watchlist from Alpaca: {e}")
                logger.info("🤖 LLM will build watchlist from market intelligence...")
            
            # If no watchlist from Alpaca, LLM will discover symbols from:
            # 1. News analysis (MarketIntelligence.get_dynamic_universe)
            # 2. Sector momentum analysis
            # 3. Unusual volume/price action
            # 4. Overnight analysis recommendations
            
            if not watchlist:
                from wawatrader.market_intelligence import MarketIntelligence
                intel = MarketIntelligence()
                universe = intel.get_dynamic_universe(min_mentions=2, max_results=50)
                watchlist = [stock['symbol'] for stock in universe]
                logger.info(f"🧠 LLM-discovered watchlist: {len(watchlist)} symbols from market intelligence")
            
            # Load overnight analysis if available
            overnight_analysis = []
            overnight_file = PROJECT_ROOT / "logs" / "overnight_analysis.json"
            if overnight_file.exists():
                try:
                    with open(overnight_file, 'r') as f:
                        overnight_analysis = json.load(f)
                    logger.info(f"🌙 Loaded overnight analysis: {len(overnight_analysis)} stocks analyzed")
                    
                    # Log high-confidence recommendations
                    sell_recs = [a for a in overnight_analysis if a.get('final_recommendation') == 'SELL']
                    if sell_recs:
                        logger.info(f"⚠️  Overnight SELL recommendations: {len(sell_recs)} stocks")
                        for rec in sell_recs[:5]:  # Show first 5
                            logger.info(f"   • {rec['symbol']}: {rec.get('reasoning', 'N/A')[:80]}...")
                except Exception as e:
                    logger.warning(f"⚠️  Failed to load overnight analysis: {e}")
            else:
                logger.info("ℹ️  No overnight analysis available (file not found)")
            
            agent = TradingAgent(symbols=watchlist, dry_run=False)
            
            logger.info(f"🎯 Trading agent initialized")
            logger.info(f"   Watchlist: {', '.join(watchlist[:10])}{'...' if len(watchlist) > 10 else ''}")
            
            # Initialize intelligent market hours manager
            hours_manager = MarketHoursManager(agent)
            logger.success("✅ Market hours manager initialized")
            logger.info("🌍 System will adapt behavior based on market phase:")
            logger.info("   🟢 Market Open: Active trading (5 min cycles)")
            logger.info("   📊 After Hours: Learning and analysis (30 min)")
            logger.info("   🔍 Evening: Deep research (1 hour)")
            logger.info("   💤 Deep Night: Sleep mode (2 hours)")
            logger.info("   🌅 Pre-Market: Preparation (15 min)")
            
            while not self.shutdown_requested:
                try:
                    # Run appropriate task for current market phase
                    result = hours_manager.run_appropriate_task()
                    
                    # Log result
                    if result['status'] == 'success':
                        logger.success(f"✅ {result.get('task', 'Task')} complete")
                    else:
                        logger.warning(f"⚠️  {result.get('task', 'Task')} had issues")
                    
                    # Sleep for appropriate interval
                    sleep_seconds = result.get('next_run_seconds', 300)
                    next_run = datetime.now() + timedelta(seconds=sleep_seconds)
                    logger.info(f"⏰ Next check at {next_run.strftime('%I:%M %p')} ({sleep_seconds/60:.0f} min)")
                    time.sleep(sleep_seconds)
                        
                except Exception as e:
                    logger.error(f"❌ System error: {e}")
                    time.sleep(300)  # Wait 5 minutes on error
        
        # Start trading in background thread
        trading_thread = threading.Thread(target=trading_loop, daemon=True)
        trading_thread.start()
        logger.success("✅ Active trading mode enabled")
    
    def start_market_closed_planning(self):
        """Run intelligent market-closed activities in background"""
        logger.info("📋 Starting market-closed planning mode...")
        
        def planning_loop():
            """Background thread for market-closed intelligence"""
            import time
            import pandas as pd
            import json
            
            # Import dependencies at the start of the loop
            from wawatrader.llm_bridge import LLMBridge
            from wawatrader.alpaca_client import get_client
            from wawatrader.indicators import TechnicalIndicators
            from wawatrader.iterative_analyst import IterativeAnalyst
            
            while not self.shutdown_requested:
                try:
                    logger.info("🧠 Running market analysis and planning...")
                    
                    # Get dynamic watchlist (same as trading mode)
                    alpaca_client = get_client()
                    try:
                        watchlist = alpaca_client.get_active_stocks(limit=50)
                        logger.info(f"📋 Planning watchlist: {len(watchlist)} stocks")
                    except Exception as e:
                        watchlist = [
                            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK.B',
                            'JPM', 'JNJ', 'V', 'PG', 'MA', 'HD', 'UNH', 'DIS', 'BAC', 'XOM',
                            'CSCO', 'ADBE', 'NFLX', 'PFE', 'KO', 'PEP', 'TMO', 'ABBV', 'COST',
                            'MRK', 'AVGO', 'WMT', 'CRM', 'ACN', 'TXN', 'MDT', 'LLY', 'NKE'
                        ]
                        logger.info(f"📋 Using fallback watchlist: {len(watchlist)} stocks")
                    
                    bridge = LLMBridge()
                    client = get_client()
                    ta = TechnicalIndicators()
                    
                    # Initialize iterative analyst
                    analyst = IterativeAnalyst(
                        alpaca_client=client,
                        llm_bridge=bridge,
                        max_iterations=5  # Allow up to 5 rounds of Q&A
                    )
                    
                    analyses = []
                    
                    for symbol in watchlist:
                        try:
                            logger.info(f"   📊 Starting iterative analysis for {symbol}...")
                            
                            # Get historical data
                            bars = client.get_bars(symbol, limit=100, timeframe='1Day')
                            
                            if bars.empty:
                                continue
                            
                            # Calculate indicators for initial context
                            signals = ta.calculate_all(bars)
                            
                            # Build initial context (ensure everything is JSON serializable)
                            rsi_value = signals.get('rsi', 'N/A')
                            if hasattr(rsi_value, 'iloc'):
                                rsi_value = float(rsi_value.iloc[-1]) if len(rsi_value) > 0 else 'N/A'
                            
                            macd_value = signals.get('macd_signal', 'N/A')
                            if hasattr(macd_value, 'iloc'):
                                macd_value = float(macd_value.iloc[-1]) if len(macd_value) > 0 else 'N/A'
                            
                            initial_context = {
                                'symbol': symbol,
                                'current_price': f"${bars['close'].iloc[-1]:.2f}",
                                'rsi': f"{rsi_value:.2f}" if isinstance(rsi_value, (int, float)) else str(rsi_value),
                                'macd_signal': f"{macd_value:.2f}" if isinstance(macd_value, (int, float)) else str(macd_value),
                                'trend': str(signals.get('trend', 'N/A')),
                                'support': f"${signals.get('support', 0):.2f}" if signals.get('support') else 'N/A',
                                'resistance': f"${signals.get('resistance', 0):.2f}" if signals.get('resistance') else 'N/A',
                                'recent_price_action_5d': [float(x) for x in bars['close'].pct_change().iloc[-5:].tolist() if not pd.isna(x)],
                                'volume_trend': 'increasing' if bars['volume'].iloc[-5:].mean() > bars['volume'].iloc[-20:-5].mean() else 'decreasing'
                            }
                            
                            # Run iterative analysis - LLM can ask for more data
                            analysis_result = analyst.analyze_with_iterations(symbol, initial_context)
                            
                            if analysis_result and analysis_result.get('final_recommendation'):
                                analyses.append(analysis_result)
                                
                                # Log summary
                                iterations = analysis_result.get('iterations', 0)
                                depth = analysis_result.get('analysis_depth', 'shallow')
                                logger.success(f"   ✅ {symbol} complete: {iterations} Q&A rounds, {depth} depth")
                            
                            # Rate limiting
                            time.sleep(2)
                            
                        except Exception as e:
                            logger.warning(f"   ⚠️  {symbol} analysis failed: {e}")
                    
                    # Log summary
                    if analyses:
                        logger.info(f"📊 Market Analysis Complete: {len(analyses)} stocks analyzed")
                        logger.info("💾 Analyses saved for tomorrow's market open")
                        
                        # Save to file for dashboard display
                        import json
                        analysis_file = PROJECT_ROOT / "logs" / "overnight_analysis.json"
                        with open(analysis_file, 'w') as f:
                            json.dump(analyses, f, indent=2)
                    
                    # Wait 30 minutes before next analysis cycle
                    logger.info("⏰ Next analysis cycle in 30 minutes...")
                    time.sleep(1800)  # 30 minutes
                    
                except Exception as e:
                    logger.error(f"❌ Planning loop error: {e}")
                    time.sleep(300)  # Wait 5 minutes on error
        
        # Start planning in background thread
        planning_thread = threading.Thread(target=planning_loop, daemon=True)
        planning_thread.start()
        logger.success("✅ Market-closed planning mode active")
    
    def start_dashboard(self):
        """Start the dashboard server"""
        try:
            # Initialize dashboard
            logger.info("🎨 Initializing dashboard...")
            dashboard = Dashboard()
            
            # Start the dashboard server
            logger.info("🚀 Starting dashboard server...")
            dashboard.run(debug=False, host='127.0.0.1', port=8050)
            
        except Exception as e:
            logger.error(f"❌ Dashboard failed to start: {e}")
            raise
    
    def run(self):
        """Run the full orchestrated system"""
        logger.info("🚀 WawaTrader Full System Starting...")
        logger.info("=" * 60)
        
        # Step 1: Check all components
        lm_studio_status = self.check_lm_studio()
        alpaca_status = self.check_alpaca()
        
        # Step 2: Verify critical components
        if not alpaca_status['connected']:
            logger.error("❌ Cannot start without Alpaca connection")
            logger.error("   Please check your .env file and API credentials")
            sys.exit(1)
        
        # Step 3: Print system status
        self.print_system_status(lm_studio_status, alpaca_status)
        
        # Step 4A: Start active trading if market is open
        if alpaca_status['market_open']:
            logger.info("")
            logger.info("🟢 Market is OPEN - activating trading mode")
            logger.info("   💹 Trading cycles run every 5 minutes")
            logger.info("   📊 Dynamic watchlist: Up to 50 actively traded stocks")
            logger.info("   🔄 Dashboard updates in real-time")
            logger.info("")
            self.start_active_trading()
        
        # Step 4B: Start market-closed planning if market is closed and LLM available
        elif not alpaca_status['market_open'] and lm_studio_status['responding']:
            logger.info("")
            logger.info("🌙 Market is closed - activating intelligent planning mode")
            logger.info("   📊 Analyzing dynamic watchlist")
            logger.info("   🧠 Preparing strategies for market open")
            logger.info("   ⏰ Analyses run every 30 minutes")
            logger.info("")
            self.start_market_closed_planning()
        elif not alpaca_status['market_open']:
            logger.warning("⚠️  Market closed but LLM not available - monitoring only")
        
        # Step 5: Start dashboard (this blocks until shutdown)
        try:
            self.start_dashboard()
        except KeyboardInterrupt:
            logger.info("🛑 Shutdown requested by user")
        except Exception as e:
            logger.error(f"❌ System error: {e}")
            raise
        finally:
            self.cleanup()

def main():
    """Main entry point"""
    try:
        orchestrator = SystemOrchestrator()
        orchestrator.run()
    except KeyboardInterrupt:
        logger.info("🛑 Shutdown complete")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
