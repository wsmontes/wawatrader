#!/usr/bin/env python3
"""
Run WawaTrader Dashboard

Launches the real-time performance monitoring dashboard.

Usage:
    python scripts/run_dashboard.py
    
Then open http://localhost:8050 in your browser.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger


def check_dependencies():
    """Check if dashboard dependencies are installed"""
    try:
        import dash
        import dash_bootstrap_components
        import plotly
        return True
    except ImportError as e:
        logger.error("Dashboard dependencies not installed!")
        logger.info("Install with: pip install dash dash-bootstrap-components plotly")
        logger.info("Or: pip install -r requirements.txt")
        return False


def main():
    """Run the dashboard"""
    
    logger.info("WawaTrader Performance Dashboard")
    logger.info("=" * 60)
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    # Import dashboard (after dependency check)
    from wawatrader.dashboard import Dashboard
    
    try:
        # Create and run dashboard
        dashboard = Dashboard(data_dir="trading_data")
        
        logger.info("")
        logger.info("🚀 Starting dashboard server...")
        logger.info("📊 Open http://localhost:8050 in your browser")
        logger.info("🔄 Auto-refreshes every 30 seconds")
        logger.info("")
        logger.info("Features:")
        logger.info("  • Real-time portfolio value tracking")
        logger.info("  • Current positions display")
        logger.info("  • P&L metrics (daily, total)")
        logger.info("  • Trade history table")
        logger.info("  • Technical indicator charts")
        logger.info("  • Position allocation pie chart")
        logger.info("")
        logger.info("Press Ctrl+C to stop the server")
        logger.info("")
        
        # Run server
        dashboard.run(
            host="127.0.0.1",
            port=8050,
            debug=False  # Set to True for development
        )
        
    except KeyboardInterrupt:
        logger.info("\n\nShutting down dashboard...")
        return 0
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
