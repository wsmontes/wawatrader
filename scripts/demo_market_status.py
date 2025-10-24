#!/usr/bin/env python3
"""
Demo: Market Status Information

Demonstrates the enhanced market status checking functionality.
Shows how users are kept informed about market hours and trading readiness.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from wawatrader.alpaca_client import get_client


def main():
    print("\n" + "=" * 70)
    print("WawaTrader - Market Status Information Demo")
    print("=" * 70)
    print()
    
    print("This demo shows the enhanced market status information")
    print("that keeps users informed about market hours and trading readiness.")
    print()
    
    try:
        # Initialize client
        print("🔌 Connecting to Alpaca Markets...")
        client = get_client()
        print("✅ Connected!")
        print()
        
        # Get basic clock info
        print("-" * 70)
        print("1️⃣  Basic Clock Info (Original Method)")
        print("-" * 70)
        
        clock = client.get_clock()
        print(f"   Current Time: {clock['timestamp']}")
        print(f"   Market Open: {'Yes ✅' if clock['is_open'] else 'No ❌'}")
        print(f"   Next Open: {clock['next_open']}")
        print(f"   Next Close: {clock['next_close']}")
        print()
        
        # Get enhanced market status
        print("-" * 70)
        print("2️⃣  Enhanced Market Status (New Method)")
        print("-" * 70)
        
        status = client.get_market_status()
        
        print(f"   Status: {status['status_text']}")
        print(f"   Message: {status['status_message']}")
        print(f"   Trading Hours: {status['trading_hours']}")
        
        if status['is_open']:
            print(f"   Next Event: Market closes in {status['time_until']}")
        else:
            print(f"   Next Event: Market opens in {status['time_until']}")
        
        print()
        
        # Show usage examples
        print("-" * 70)
        print("3️⃣  Usage Examples")
        print("-" * 70)
        print()
        
        print("📝 In Trading Agent:")
        print("   The trading agent now shows detailed status when market is closed:")
        print("   • 🔴 CLOSED")
        print("   • Exact time until market opens")
        print("   • Confirmation that agent will wait automatically")
        print()
        
        print("📝 In Start Script (start.py):")
        print("   Users see market status before starting trading:")
        print("   • Current market state")
        print("   • Time until next open/close")
        print("   • Helpful tips about waiting behavior")
        print()
        
        print("📝 In Status Check (status_check.py):")
        print("   System status includes live market information:")
        print("   • Real-time market open/closed status")
        print("   • Countdown to next market event")
        print("   • Trading readiness indicators")
        print()
        
        # Show what users see during different scenarios
        print("-" * 70)
        print("4️⃣  User Experience Scenarios")
        print("-" * 70)
        print()
        
        if status['is_open']:
            print("🟢 CURRENT SCENARIO: Market is OPEN")
            print()
            print("   When you start trading:")
            print("   ✅ You see: 'Market is OPEN - Trading will begin immediately!'")
            print("   ✅ Agent starts checking symbols right away")
            print("   ✅ Dashboard shows live data")
            print(f"   ⏰ Market closes in: {status['time_until']}")
        else:
            print("🔴 CURRENT SCENARIO: Market is CLOSED")
            print()
            print("   When you start trading:")
            print("   💤 You see: 'Market is CLOSED - Agent will wait for open'")
            print(f"   ⏰ Opens in: {status['time_until']}")
            print("   ✅ Agent starts now but waits for market open")
            print("   ✅ You can leave it running - it will auto-start trading")
            print("   ✅ Dashboard is available for monitoring")
        
        print()
        
        # Benefits summary
        print("-" * 70)
        print("5️⃣  Benefits of Enhanced Market Status")
        print("-" * 70)
        print()
        
        print("✅ User Benefits:")
        print("   • Always know when market opens/closes")
        print("   • Clear countdown timers (hours/minutes)")
        print("   • No guessing about trading readiness")
        print("   • Can start system anytime - it waits intelligently")
        print("   • Better weekend/holiday handling")
        print()
        
        print("✅ Technical Benefits:")
        print("   • Uses Alpaca's real-time clock (always accurate)")
        print("   • Handles holidays and early closes automatically")
        print("   • Works across timezones (all times in ET)")
        print("   • Graceful fallback if API unavailable")
        print()
        
        print("=" * 70)
        print("✅ Demo Complete!")
        print("=" * 70)
        print()
        
        print("💡 Try these commands to see the enhanced status:")
        print("   python start.py              # See market status on startup")
        print("   python start.py status       # Check detailed system status")
        print("   python start.py trading      # Start trading with status info")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        print("💡 Make sure:")
        print("   • Alpaca API keys are configured in .env")
        print("   • Internet connection is available")
        print("   • LM Studio is running (if needed)")


if __name__ == "__main__":
    main()
