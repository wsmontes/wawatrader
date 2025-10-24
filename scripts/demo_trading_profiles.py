#!/usr/bin/env python3
"""
Demo: Trading Profiles

Shows how to use different trading profiles (Conservative, Moderate, Aggressive, Maximum).
Demonstrates how each profile interprets the same market data differently.
"""

from wawatrader.llm_bridge import LLMBridge
from wawatrader.alpaca_client import get_client
from wawatrader.indicators import analyze_dataframe, get_latest_signals
from datetime import datetime, timedelta
from loguru import logger

def demo_trading_profiles():
    """Test all trading profiles with same market data"""
    
    print("\n" + "="*70)
    print("🎯 WawaTrader Trading Profiles Demo")
    print("="*70)
    
    # Get market data (using IEX historical data - free tier)
    print("\n📊 Fetching market data for AAPL...")
    print("   (Using IEX data from ~15 days ago to avoid subscription limits)")
    client = get_client()
    symbol = "AAPL"
    
    # Use data from 15-75 days ago (IEX free tier has 15-day delay)
    end_date = datetime.now() - timedelta(days=15)
    start_date = end_date - timedelta(days=60)
    
    print(f"   Date range: {start_date.date()} to {end_date.date()}")
    df = client.get_bars(symbol, start_date, end_date, limit=100)
    
    if df is None or len(df) == 0:
        print("❌ No data retrieved. Trying older timeframe...")
        # Try much older data (2+ months ago)
        end_date = datetime.now() - timedelta(days=60)
        start_date = end_date - timedelta(days=60)
        print(f"   Trying: {start_date.date()} to {end_date.date()}")
        df = client.get_bars(symbol, start_date, end_date, limit=100)
    
    if df is None or len(df) == 0:
        print("❌ Error: Could not retrieve market data.")
        print("   This may be due to Alpaca API restrictions.")
        print("   Note: IEX free data has a 15-day delay for paper accounts.")
        return
    
    print(f"✅ Retrieved {len(df)} bars (from {df.index[0].date()} to {df.index[-1].date()})")
    
    # Calculate indicators
    df_with_indicators = analyze_dataframe(df)
    signals = get_latest_signals(df_with_indicators)
    
    # Show available profiles
    print("\n" + "="*70)
    print("Available Trading Profiles:")
    print("="*70)
    
    profiles = LLMBridge.get_available_profiles()
    for key, profile in profiles.items():
        print(f"\n📋 {profile['name'].upper()} ({key})")
        print(f"   Description: {profile['description']}")
        print(f"   Min Confidence (Buy): {profile['min_confidence_buy']}%")
        print(f"   Min Confidence (Sell): {profile['min_confidence_sell']}%")
        print(f"   Risk Emphasis: {profile['risk_emphasis']}")
    
    # Test each profile with same data
    print("\n" + "="*70)
    print("Testing Each Profile with Same Market Data")
    print("="*70)
    
    # Initialize bridge
    bridge = LLMBridge()
    
    for profile_key in ['conservative', 'moderate', 'aggressive', 'maximum']:
        print(f"\n{'='*70}")
        print(f"🎯 {profiles[profile_key]['name'].upper()} Profile")
        print(f"{'='*70}")
        
        # Change profile
        bridge.set_profile(profile_key)
        
        # Get analysis
        analysis = bridge.analyze_market(
            symbol=symbol,
            signals=signals
        )
        
        if analysis:
            print(f"✅ Analysis Complete:")
            print(f"   Sentiment: {analysis['sentiment'].upper()}")
            print(f"   Confidence: {analysis['confidence']}%")
            print(f"   🎯 ACTION: {analysis['action'].upper()}")
            print(f"   Reasoning: {analysis['reasoning']}")
            
            if 'risk_factors' in analysis and analysis['risk_factors']:
                print(f"   ⚠️  Risk Factors:")
                for risk in analysis['risk_factors']:
                    print(f"      • {risk}")
        else:
            print("❌ Analysis failed for this profile")
    
    # Show current profile
    print("\n" + "="*70)
    current = bridge.get_current_profile()
    print(f"Current Active Profile: {current['name']}")
    print("="*70)
    
    print("\n💡 To change profiles:")
    print("   1. Set TRADING_PROFILE in .env file:")
    print("      TRADING_PROFILE=aggressive")
    print("   2. Or change at runtime:")
    print("      bridge.set_profile('conservative')")
    print("\n✅ Demo complete!\n")


if __name__ == "__main__":
    demo_trading_profiles()
