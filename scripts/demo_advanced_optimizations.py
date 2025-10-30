"""
Demo: Advanced Risk Management Optimizations

Tests the new advanced optimization features:
1. Kelly Criterion position sizing
2. Volatility-adjusted position sizing
3. Portfolio correlation analysis
4. Sharpe ratio calculation
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from wawatrader.risk_manager import RiskManager
from loguru import logger


def main():
    print("╔════════════════════════════════════════════════════════════╗")
    print("║  📊 Advanced Risk Management Optimizations Demo           ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()
    
    rm = RiskManager()
    account_value = 100000  # $100k portfolio
    
    # Test 1: Kelly Criterion
    print("━" * 60)
    print("TEST 1: Kelly Criterion Position Sizing")
    print("━" * 60)
    print()
    
    # Example: Stock with 60% win rate, avg win $500, avg loss $300
    print("📈 AAPL - Strong performer")
    print("   Historical: 60% win rate, $500 avg win, $300 avg loss")
    
    kelly_result = rm.calculate_kelly_position_size(
        symbol="AAPL",
        win_rate=0.60,
        avg_win=500,
        avg_loss=300,
        account_value=account_value,
        current_price=150,
        max_kelly_fraction=0.25
    )
    
    print(f"\n✅ Kelly Recommendation:")
    print(f"   Full Kelly: {kelly_result['full_kelly_pct']*100:.1f}%")
    print(f"   Fractional Kelly (25%): {kelly_result['fractional_kelly_pct']*100:.1f}%")
    print(f"   Bounded: {kelly_result['bounded_kelly_pct']*100:.1f}%")
    print(f"   Shares: {kelly_result['recommended_shares']}")
    print(f"   Value: ${kelly_result['position_value']:,.2f}")
    print()
    
    # Example: Stock with 45% win rate (losing strategy)
    print("📉 TSLA - Weak performer")
    print("   Historical: 45% win rate, $400 avg win, $350 avg loss")
    
    kelly_result2 = rm.calculate_kelly_position_size(
        symbol="TSLA",
        win_rate=0.45,
        avg_win=400,
        avg_loss=350,
        account_value=account_value,
        current_price=200,
        max_kelly_fraction=0.25
    )
    
    print(f"\n✅ Kelly Recommendation:")
    print(f"   Full Kelly: {kelly_result2['full_kelly_pct']*100:.1f}%")
    print(f"   Recommendation: {'AVOID' if kelly_result2['full_kelly_pct'] <= 0 else 'Small position'}")
    print()
    
    # Test 2: Volatility Adjustment
    print("━" * 60)
    print("TEST 2: Volatility-Adjusted Position Sizing")
    print("━" * 60)
    print()
    
    base_shares = 100
    price = 150
    
    # Low volatility stock
    print(f"📊 Low Vol Stock (10% volatility)")
    print(f"   Base position: {base_shares} shares")
    
    vol_result1 = rm.calculate_volatility_adjusted_size(
        symbol="MSFT",
        base_shares=base_shares,
        current_volatility=0.10,
        target_volatility=0.15,
        price=price
    )
    
    print(f"✅ Adjustment: {vol_result1['volatility_adjustment']:.2f}x")
    print(f"   Adjusted shares: {vol_result1['adjusted_shares']} (increased for low vol)")
    print()
    
    # High volatility stock
    print(f"📊 High Vol Stock (30% volatility)")
    print(f"   Base position: {base_shares} shares")
    
    vol_result2 = rm.calculate_volatility_adjusted_size(
        symbol="NVDA",
        base_shares=base_shares,
        current_volatility=0.30,
        target_volatility=0.15,
        price=price
    )
    
    print(f"✅ Adjustment: {vol_result2['volatility_adjustment']:.2f}x")
    print(f"   Adjusted shares: {vol_result2['adjusted_shares']} (reduced for high vol)")
    print()
    
    # Test 3: Portfolio Correlation
    print("━" * 60)
    print("TEST 3: Portfolio Correlation Analysis")
    print("━" * 60)
    print()
    
    # Generate synthetic returns data
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
    
    # Create correlated returns
    returns_spy = pd.Series(np.random.randn(100) * 0.01, index=dates)
    returns_qqq = pd.Series(returns_spy * 0.8 + np.random.randn(100) * 0.005, index=dates)  # High correlation with SPY
    returns_aapl = pd.Series(returns_spy * 0.6 + np.random.randn(100) * 0.008, index=dates)  # Medium correlation
    returns_gld = pd.Series(-returns_spy * 0.2 + np.random.randn(100) * 0.006, index=dates)  # Negative correlation (hedge)
    
    historical_returns = {
        'SPY': returns_spy,
        'QQQ': returns_qqq,
        'AAPL': returns_aapl,
        'GLD': returns_gld
    }
    
    positions = [
        {'symbol': 'SPY', 'market_value': 30000},
        {'symbol': 'QQQ', 'market_value': 25000},
        {'symbol': 'AAPL', 'market_value': 20000},
        {'symbol': 'GLD', 'market_value': 15000}
    ]
    
    print("📊 Portfolio Positions:")
    for pos in positions:
        print(f"   {pos['symbol']}: ${pos['market_value']:,}")
    print()
    
    corr_result = rm.calculate_portfolio_correlation(
        positions=positions,
        historical_returns=historical_returns
    )
    
    print(f"✅ Correlation Analysis:")
    print(f"   Average Correlation: {corr_result['avg_correlation']:.3f}")
    print(f"   Max Correlation: {corr_result['max_correlation']:.3f}")
    print(f"   Diversification Score: {corr_result['diversification_score']:.3f}")
    
    if corr_result['highly_correlated_pairs']:
        print(f"\n⚠️  Highly Correlated Pairs (>0.7):")
        for pair in corr_result['highly_correlated_pairs']:
            print(f"      {pair['pair']}: {pair['correlation']:.3f}")
    else:
        print(f"\n✅ No highly correlated pairs found")
    print()
    
    # Test 4: Sharpe Ratio
    print("━" * 60)
    print("TEST 4: Sharpe Ratio Calculation")
    print("━" * 60)
    print()
    
    # Generate synthetic portfolio returns
    # Scenario 1: Good performance (positive returns, moderate vol)
    good_returns = pd.Series(np.random.randn(252) * 0.01 + 0.0005, index=pd.date_range('2024-01-01', periods=252))
    
    print("📊 Good Performance Portfolio:")
    print(f"   252 days of trading data")
    
    sharpe_result1 = rm.calculate_sharpe_ratio(good_returns)
    
    print(f"\n✅ Sharpe Analysis:")
    print(f"   Sharpe Ratio: {sharpe_result1['sharpe_ratio']:.2f}")
    print(f"   Interpretation: {sharpe_result1['interpretation']}")
    print(f"   Annualized Return: {sharpe_result1['annualized_return']*100:.1f}%")
    print(f"   Annualized Volatility: {sharpe_result1['annualized_volatility']*100:.1f}%")
    print()
    
    # Scenario 2: Poor performance (negative returns)
    poor_returns = pd.Series(np.random.randn(252) * 0.015 - 0.0003, index=pd.date_range('2024-01-01', periods=252))
    
    print("📊 Poor Performance Portfolio:")
    print(f"   252 days of trading data")
    
    sharpe_result2 = rm.calculate_sharpe_ratio(poor_returns)
    
    print(f"\n✅ Sharpe Analysis:")
    print(f"   Sharpe Ratio: {sharpe_result2['sharpe_ratio']:.2f}")
    print(f"   Interpretation: {sharpe_result2['interpretation']}")
    print(f"   Annualized Return: {sharpe_result2['annualized_return']*100:.1f}%")
    print(f"   Annualized Volatility: {sharpe_result2['annualized_volatility']*100:.1f}%")
    print()
    
    # Summary
    print("═" * 60)
    print("✅ DEMO COMPLETE")
    print("═" * 60)
    print()
    print("📊 Advanced Optimizations Available:")
    print("   ✅ Kelly Criterion - Optimal position sizing")
    print("   ✅ Volatility Adjustment - Risk-normalized sizing")
    print("   ✅ Correlation Analysis - Diversification measurement")
    print("   ✅ Sharpe Ratio - Performance evaluation")
    print()
    print("🎯 Integration Points:")
    print("   • Use in TradingAgent for position sizing")
    print("   • Use in OvernightLearner for performance analysis")
    print("   • Use in Dashboard for risk metrics display")
    print()


if __name__ == "__main__":
    main()
