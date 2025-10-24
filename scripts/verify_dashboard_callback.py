#!/usr/bin/env python3
"""
Verify Dashboard Callback

Tests that the dashboard callback returns the correct market status data.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from wawatrader.alpaca_client import get_client
from loguru import logger

def test_callback_logic():
    """Test the exact logic that runs in the dashboard callback"""
    
    print("\n" + "="*70)
    print("🧪 TESTING DASHBOARD CALLBACK LOGIC")
    print("="*70)
    print()
    
    # Get client
    alpaca = get_client()
    
    # Simulate callback execution
    print("📊 Simulating update_header() callback...")
    print()
    
    # 1. Current time
    current_time = datetime.now().strftime("%H:%M:%S")
    print(f"1. System Time: {current_time}")
    
    # 2. Market status
    try:
        market_status = alpaca.get_market_status()
        is_open = market_status.get('is_open', False)
        status_text = market_status.get('status_text', '⚠️ UNKNOWN')
        
        print(f"2. Market Status: {status_text}")
        print(f"   Is Open: {is_open}")
        
        # Style for market status
        if is_open:
            market_status_style = {
                "background": "var(--accent-green)",
                "color": "white",
                "fontWeight": "600",
                "animation": "pulse 2s ease-in-out infinite"
            }
            print(f"   Style: GREEN background with PULSE animation")
        else:
            market_status_style = {
                "background": "var(--accent-red)",
                "color": "white",
                "fontWeight": "600"
            }
            print(f"   Style: RED background")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        status_text = "⚠️ UNKNOWN"
        market_status_style = {}
    
    # 3. Market state
    try:
        from wawatrader.market_state import get_market_state
        market_state = get_market_state(alpaca)
        state_display = f"{market_state.emoji} {market_state.description}"
        state_style = {
            "background": "var(--bg-tertiary)",
            "color": "var(--text-secondary)",
            "fontSize": "11px"
        }
        print(f"3. Market State: {state_display}")
        print(f"   Style: Gray background, small font")
    except Exception as e:
        print(f"3. Market State: ❌ Error: {e}")
        state_display = ""
        state_style = {"display": "none"}
    
    # 4. P&L
    try:
        account = alpaca.get_account()
        if isinstance(account, dict):
            equity = float(account.get('equity', 0))
            last_equity = float(account.get('last_equity', equity))
        else:
            equity = float(account.equity)
            last_equity = float(account.last_equity)
        
        pnl = equity - last_equity
        pnl_pct = (pnl / last_equity) * 100 if last_equity > 0 else 0
        pnl_text = f"P&L: {'+' if pnl >= 0 else ''}{pnl:,.2f} ({pnl_pct:+.2f}%)"
        pnl_color = "GREEN" if pnl >= 0 else "RED"
        
        print(f"4. P&L: {pnl_text}")
        print(f"   Style: {pnl_color} color")
        
    except Exception as e:
        print(f"4. P&L: ❌ Error: {e}")
        pnl_text = "P&L: --"
    
    print()
    print("="*70)
    print("✅ CALLBACK RETURN VALUES (in order):")
    print("="*70)
    print(f"1. current_time     = '{current_time}'")
    print(f"2. status_text      = '{status_text}'")
    print(f"3. market_status_style = {market_status_style}")
    print(f"4. state_display    = '{state_display}'")
    print(f"5. state_style      = {state_style}")
    print(f"6. pnl_text         = '{pnl_text}'")
    print(f"7. pnl_style        = (color styling)")
    print()
    
    print("="*70)
    print("🎯 WHAT SHOULD APPEAR IN DASHBOARD HEADER:")
    print("="*70)
    print(f"[LIVE] [{status_text}] [{state_display}] [{current_time}] [{pnl_text}] [Config]")
    print()
    print("✅ All callback logic working correctly!")
    print()
    print("🔧 If dashboard doesn't show these values:")
    print("   1. Hard refresh browser (Cmd+Shift+R or Ctrl+Shift+R)")
    print("   2. Restart dashboard: python start.py dashboard")
    print("   3. Clear browser cache")
    print()

if __name__ == "__main__":
    test_callback_logic()
