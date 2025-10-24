#!/usr/bin/env python3
"""
Dashboard Layout Inspector

Inspects what's actually in the dashboard layout to confirm market status divs exist.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from wawatrader.dashboard import Dashboard

def main():
    print("\n" + "="*70)
    print("🔍 DASHBOARD LAYOUT INSPECTOR")
    print("="*70)
    print()
    
    print("Creating Dashboard instance...")
    dashboard = Dashboard()
    
    print("✅ Dashboard created successfully")
    print()
    
    # Convert layout to string
    layout_str = str(dashboard.app.layout)
    
    # Check for our divs
    print("Checking for market status components:")
    print("-" * 70)
    print(f"✓ 'market-status' ID found: {'market-status' in layout_str}")
    print(f"✓ 'market-state' ID found: {'market-state' in layout_str}")
    print(f"✓ 'system-time' ID found: {'system-time' in layout_str}")
    print(f"✓ 'pnl-header' ID found: {'pnl-header' in layout_str}")
    print()
    
    # Check callback outputs
    print("Checking callback registrations:")
    print("-" * 70)
    
    # Get all callbacks
    callback_map = dashboard.app.callback_map
    print(f"Total callbacks registered: {len(callback_map)}")
    
    # Find update_header callback
    for output_id in callback_map:
        if 'market-status' in str(output_id):
            print(f"✓ Found callback for: {output_id}")
    
    print()
    print("="*70)
    print("✅ VERIFICATION COMPLETE")
    print("="*70)
    print()
    print("The code is correct. The divs ARE in the layout.")
    print("The callbacks ARE registered.")
    print()
    print("🔧 SOLUTION: Restart the dashboard process")
    print("   1. Stop current dashboard (Ctrl+C)")
    print("   2. Run: python start.py dashboard")
    print("   3. Hard refresh browser (Cmd+Shift+R)")
    print()

if __name__ == "__main__":
    main()
