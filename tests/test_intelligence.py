#!/usr/bin/env python3
"""
Test Market Intelligence Engine

Quick test to validate the background analysis system.
"""

import sys
from pathlib import Path
import asyncio

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from wawatrader.market_intelligence import get_intelligence_engine
from loguru import logger
import pytest


@pytest.mark.asyncio
async def test_market_intelligence():
    """Test market intelligence engine functionality"""
    
    print("🧪 Testing WawaTrader Market Intelligence Engine")
    print("=" * 60)
    
    try:
        # Initialize engine
        engine = get_intelligence_engine()
        print(f"✅ Intelligence engine initialized")
        
        # Run background analysis
        print("🔍 Running background market analysis...")
        intelligence = await engine.run_background_analysis()
        
        if intelligence:
            print("\n📊 Market Intelligence Results:")
            print(f"   Timestamp: {intelligence.timestamp}")
            print(f"   Market Sentiment: {intelligence.market_sentiment}")
            print(f"   Confidence: {intelligence.confidence}%")
            print(f"   Regime Assessment: {intelligence.regime_assessment}")
            
            if intelligence.key_findings:
                print(f"   Key Findings:")
                for finding in intelligence.key_findings[:3]:
                    print(f"     • {finding}")
            
            if intelligence.opportunities:
                print(f"   Opportunities Found: {len(intelligence.opportunities)}")
                
            if intelligence.risks:
                print(f"   Risks Identified: {len(intelligence.risks)}")
                
            if intelligence.recommended_actions:
                print(f"   Recommended Actions:")
                for action in intelligence.recommended_actions[:3]:
                    print(f"     • {action}")
            
            print(f"\n✅ Background analysis completed successfully!")
            
        else:
            print("❌ Background analysis returned no results")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_market_intelligence())