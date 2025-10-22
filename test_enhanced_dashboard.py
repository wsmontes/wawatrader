#!/usr/bin/env python3
"""
Test Enhanced Dashboard Features

Quick test to verify the new dashboard enhancements:
- LLM conversation history
- Improved indicator layout
- Trading plan tags
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from wawatrader.dashboard import Dashboard
from loguru import logger

def test_dashboard():
    """Test enhanced dashboard functionality"""
    
    print("🧪 Testing Enhanced WawaTrader Dashboard")
    print("=" * 60)
    
    try:
        # Initialize dashboard
        dashboard = Dashboard()
        print(f"✅ Enhanced dashboard initialized successfully")
        print(f"   New features added:")
        print(f"   • 🤖 LLM Intelligence & Conversations tab")
        print(f"   • 📈 Improved technical indicators layout")  
        print(f"   • 🎯 Trading plan with strategy tags")
        print(f"   • 📊 Market intelligence dashboard")
        print(f"   • 💬 Real-time LLM conversation history")
        
        print(f"\n🚀 Starting enhanced dashboard server...")
        print(f"   Dashboard URL: http://127.0.0.1:8050")
        print(f"   New tabs available:")
        print(f"     - Market Intelligence: Real-time AI analysis")  
        print(f"     - LLM Conversations: Full conversation history")
        print(f"     - Trading Plan: Strategy overview with tags")
        print(f"\n💡 Press Ctrl+C to stop the dashboard")
        print(f"=" * 60)
        
        # Run dashboard
        dashboard.run(debug=False)
        
    except KeyboardInterrupt:
        print(f"\n✅ Dashboard stopped by user")
    except Exception as e:
        print(f"❌ Dashboard test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_dashboard()