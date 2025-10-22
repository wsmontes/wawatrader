#!/usr/bin/env python3
"""
WawaTrader Professional Dashboard Launcher

Launch the elite professional trading dashboard with LLM transparency.

Features:
- Professional dark theme optimized for trading
- Real-time LLM thought process visualization  
- Advanced market intelligence display
- Responsive grid layout that fits any screen
- Professional-grade performance monitoring

Usage:
    python scripts/run_dashboard_pro.py
    
    Or with custom settings:
    python scripts/run_dashboard_pro.py --host 0.0.0.0 --port 8888
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from wawatrader.dashboard_pro import TradingDashboardPro
from loguru import logger


def main():
    """Launch the professional dashboard"""
    
    parser = argparse.ArgumentParser(description="WawaTrader Professional Dashboard")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8050, help="Port to bind to")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    # Print banner
    print("=" * 70)
    print("🚀 WawaTrader Professional Dashboard")
    print("=" * 70)
    print("🎯 Elite daytrading interface with LLM transparency")
    print("🌙 Professional dark theme optimized for trading")
    print("🤖 Real-time AI decision process visualization")
    print("📊 Advanced market intelligence & performance analytics")
    print("📱 Responsive design that fits any screen size")
    print("=" * 70)
    print()
    
    try:
        # Initialize and run dashboard
        dashboard = TradingDashboardPro()
        
        print(f"🌐 Dashboard URL: http://{args.host}:{args.port}")
        print(f"🔄 Real-time updates every 5 seconds")
        print(f"🧠 LLM thoughts update every 2 seconds")
        print()
        print("Features:")
        print("  • Live portfolio tracking with P&L in header")
        print("  • Professional candlestick charts with AI annotations")
        print("  • Real-time LLM thought process visualization")
        print("  • Market intelligence screener with opportunities")
        print("  • Performance metrics & position monitoring")
        print("  • Interactive AI conversation history")
        print("  • Dark theme optimized for long trading sessions")
        print()
        print("Grid Layout:")
        print("  ┌─────────────┬─────────────┬─────────────┐")
        print("  │ LLM Mind    │ Main Chart  │ Market      │")
        print("  │ Thoughts    │ Candlesticks│ Intelligence│")
        print("  ├─────────────┼─────────────┼─────────────┤")
        print("  │ Performance │ Positions   │ AI Convos   │")
        print("  │ Analytics   │ Monitor     │ History     │")
        print("  └─────────────┴─────────────┴─────────────┘")
        print()
        print("Press Ctrl+C to stop the server")
        print()
        
        dashboard.run(host=args.host, port=args.port, debug=args.debug)
        
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped by user")
        
    except ImportError as e:
        logger.error(f"❌ Missing dependencies: {e}")
        print("\n💡 Install required packages:")
        print("   pip install dash dash-bootstrap-components plotly")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"❌ Dashboard error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()