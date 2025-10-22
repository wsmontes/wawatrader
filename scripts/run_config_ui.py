"""
Launch Configuration UI for WawaTrader

Quick launch script for the web-based configuration interface.

Usage:
    python scripts/run_config_ui.py [--port PORT] [--host HOST]

Access at: http://localhost:5001 (or specified port)

Author: WawaTrader Team
Date: October 2025
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from wawatrader.config_ui import run_config_ui
from loguru import logger


def main():
    """Launch configuration UI with command-line arguments"""
    parser = argparse.ArgumentParser(
        description='WawaTrader Configuration UI'
    )
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5001,
        help='Port to listen on (default: 5001)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("WawaTrader Configuration UI")
    logger.info("=" * 60)
    logger.info(f"Starting server on http://{args.host}:{args.port}")
    logger.info("")
    logger.info("Features:")
    logger.info("  - Risk management settings")
    logger.info("  - Trading parameters")
    logger.info("  - LLM configuration")
    logger.info("  - Alert settings")
    logger.info("  - Configuration history")
    logger.info("")
    logger.info("Press Ctrl+C to stop the server")
    logger.info("=" * 60)
    
    try:
        run_config_ui(host=args.host, port=args.port, debug=args.debug)
    except KeyboardInterrupt:
        logger.info("\nShutting down configuration UI...")
    except Exception as e:
        logger.error(f"Error running configuration UI: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
