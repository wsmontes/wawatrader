#!/usr/bin/env python3
"""
Test script for dashboard enhancements - verify new tabs load correctly
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_log_readers():
    """Test that the new log reader methods work"""
    from wawatrader.dashboard import Dashboard
    
    # Initialize dashboard (it will create its own alpaca client)
    dashboard = Dashboard()
    
    print("🧪 Testing Dashboard Enhancements\n")
    print("=" * 60)
    
    # Test 1: Reading trading decisions
    print("\n1️⃣ Testing _get_trading_decisions()...")
    try:
        decisions = dashboard._get_trading_decisions(limit=5)
        print(f"   ✅ Found {len(decisions)} decisions")
        if decisions:
            latest = decisions[-1]
            print(f"   📊 Latest: {latest.get('symbol')} - {latest.get('action')} ({latest.get('confidence')}% confident)")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Reading order executions
    print("\n2️⃣ Testing _get_order_executions()...")
    try:
        orders = dashboard._get_order_executions(limit=5)
        print(f"   ✅ Found {len(orders)} order events")
        if orders:
            latest = orders[-1]
            print(f"   📤 Latest: {latest.get('type')} - {latest.get('symbol')} {latest.get('side')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Check log files exist
    print("\n3️⃣ Checking log file structure...")
    log_dir = Path("logs")
    expected_files = [
        "decisions.jsonl",
        "llm_conversations.jsonl",
        "system.log",
        "market_data.jsonl",
        "account_snapshots.jsonl",
        "position_snapshots.jsonl",
        "order_executions.jsonl"
    ]
    
    for filename in expected_files:
        filepath = log_dir / filename
        if filepath.exists():
            size = filepath.stat().st_size
            lines = 0
            if filename.endswith('.jsonl'):
                with open(filepath, 'r') as f:
                    lines = sum(1 for _ in f)
            print(f"   ✅ {filename}: {size:,} bytes, {lines} entries")
        else:
            print(f"   ⚠️  {filename}: Not found (will be created on first use)")
    
    print("\n" + "=" * 60)
    print("✅ Dashboard enhancement test complete!\n")
    print("💡 To test the full dashboard, run:")
    print("   python scripts/run_dashboard.py")

if __name__ == "__main__":
    test_log_readers()
