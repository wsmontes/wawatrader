#!/usr/bin/env python3
"""
Demo: Dashboard Market Status Display

Quick test to verify market status is displayed correctly in the dashboard.

Usage:
    python scripts/demo_market_status_dashboard.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from wawatrader.alpaca_client import get_client
from wawatrader.market_state import get_market_state, display_market_state_info
from loguru import logger

def main():
    """Display current market status information"""
    print("\n" + "="*70)
    print("🖥️  DASHBOARD MARKET STATUS TEST")
    print("="*70)
    print()
    
    # Get Alpaca client
    logger.info("Connecting to Alpaca...")
    alpaca = get_client()
    
    # Display market status
    logger.info("Fetching market status...")
    display_market_state_info(alpaca)
    
    # Get detailed status for dashboard
    market_status = alpaca.get_market_status()
    market_state = get_market_state(alpaca)
    
    print()
    print("📊 Dashboard Display Preview:")
    print("-" * 70)
    print(f"   Market Status Badge: {market_status.get('status_text', '⚠️ UNKNOWN')}")
    print(f"   Color: {'🟢 GREEN (pulsing)' if market_status.get('is_open') else '🔴 RED'}")
    print(f"   Market State Badge: {market_state.emoji} {market_state.description}")
    print(f"   Time Until: {market_status.get('time_until', 'N/A')}")
    print("-" * 70)
    
    print()
    print("✅ Market status is now displayed in the dashboard header!")
    print()
    print("🎯 What you'll see in the dashboard:")
    print("   - Left side: WawaTrader Beta title")
    print("   - Right side status badges:")
    print(f"     1. LIVE (green)")
    print(f"     2. {market_status.get('status_text', 'UNKNOWN')} ({'pulsing green' if market_status.get('is_open') else 'red'})")
    print(f"     3. {market_state.emoji} {market_state.description} (gray)")
    print(f"     4. Current time")
    print(f"     5. P&L")
    print(f"     6. Config button")
    print()
    print("🚀 Start the dashboard to see it live:")
    print("   python start.py dashboard")
    print("   # Opens at http://localhost:8050")
    print()

if __name__ == "__main__":
    main()
