#!/usr/bin/env python3
"""
Quick System Test

Tests if WawaTrader is properly configured and ready to run.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_configuration():
    """Test system configuration"""
    print("🧪 Testing WawaTrader Configuration...")
    print("=" * 50)
    
    # Test 1: Environment file
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file exists")
        
        # Check if keys are configured
        with open(env_file) as f:
            content = f.read()
            if "your_api_key_here" in content:
                print("⚠️  .env file needs API keys configured")
                print("   Edit .env and add your Alpaca API keys")
                return False
            else:
                print("✅ .env file appears configured")
    else:
        print("❌ .env file missing")
        return False
    
    # Test 2: Import WawaTrader
    try:
        import wawatrader
        print(f"✅ WawaTrader v{wawatrader.__version__} imported successfully")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Test 3: Dependencies
    try:
        import pandas as pd
        import numpy as np
        import alpaca_trade_api
        import openai
        import dash
        import plotly
        print("✅ All dependencies available")
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        return False
    
    print("\n🎉 System ready!")
    print("\nAvailable commands:")
    print("  python scripts/demo_dashboard.py    # Dashboard demo")
    print("  python scripts/demo_backtest.py     # Backtesting demo")
    print("  python scripts/run_dashboard.py     # Real dashboard")
    print("  python scripts/demo_alerts.py       # Alerts demo")
    
    return True

if __name__ == "__main__":
    success = test_configuration()
    sys.exit(0 if success else 1)