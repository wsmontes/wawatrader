"""
Example Usage of Alpaca Client

Demonstrates common operations with the Alpaca API client.
"""

from wawatrader import AlpacaClient
from datetime import datetime, timedelta
import pandas as pd


def example_account_info():
    """Example: Get account information"""
    print("=" * 60)
    print("Example 1: Account Information")
    print("=" * 60)
    
    client = AlpacaClient()
    
    # Get account details
    account = client.get_account()
    print(f"\n💰 Account Status:")
    print(f"   Portfolio Value: ${account['portfolio_value']:,.2f}")
    print(f"   Cash: ${account['cash']:,.2f}")
    print(f"   Buying Power: ${account['buying_power']:,.2f}")
    
    # Get positions
    positions = client.get_positions()
    print(f"\n📊 Current Positions: {len(positions)}")
    for pos in positions:
        print(f"   {pos['symbol']}: {pos['qty']} shares @ ${pos['current_price']:.2f}")
        print(f"      P&L: ${pos['unrealized_pl']:.2f} ({pos['unrealized_plpc']*100:.2f}%)")


def example_historical_data():
    """Example: Fetch historical price data"""
    print("\n" + "=" * 60)
    print("Example 2: Historical Market Data")
    print("=" * 60)
    
    client = AlpacaClient()
    
    symbol = 'AAPL'
    end = datetime.now()
    start = end - timedelta(days=30)
    
    # Get daily bars
    bars = client.get_bars(
        symbol=symbol,
        timeframe='1Day',
        start=start,
        end=end,
        limit=30
    )
    
    print(f"\n📈 {symbol} - Last 30 Days:")
    print(f"   Retrieved {len(bars)} bars")
    
    if not bars.empty:
        # Calculate basic stats
        latest = bars.iloc[-1]
        highest = bars['high'].max()
        lowest = bars['low'].min()
        avg_volume = bars['volume'].mean()
        
        print(f"\n   Latest Close: ${latest['close']:.2f}")
        print(f"   30-Day High: ${highest:.2f}")
        print(f"   30-Day Low: ${lowest:.2f}")
        print(f"   Avg Volume: {avg_volume:,.0f}")
        
        # Calculate returns
        first_close = bars['close'].iloc[0]
        last_close = bars['close'].iloc[-1]
        return_pct = ((last_close - first_close) / first_close) * 100
        
        print(f"   30-Day Return: {return_pct:+.2f}%")
        
        # Show last 5 days
        print(f"\n   Last 5 Days:")
        print("   Date          Close     Volume")
        print("   " + "-" * 40)
        for idx, row in bars.tail(5).iterrows():
            date_str = pd.to_datetime(row['timestamp']).strftime('%Y-%m-%d')
            print(f"   {date_str}  ${row['close']:>7.2f}  {row['volume']:>10,.0f}")


def example_realtime_data():
    """Example: Get real-time quotes and trades"""
    print("\n" + "=" * 60)
    print("Example 3: Real-Time Market Data")
    print("=" * 60)
    
    client = AlpacaClient()
    
    symbols = ['AAPL', 'MSFT', 'GOOGL']
    
    print(f"\n📊 Real-Time Quotes:")
    print("   Symbol   Bid       Ask       Spread")
    print("   " + "-" * 45)
    
    for symbol in symbols:
        quote = client.get_latest_quote(symbol)
        if quote:
            spread = quote['ask_price'] - quote['bid_price']
            print(f"   {symbol:<6}  ${quote['bid_price']:>7.2f}  ${quote['ask_price']:>7.2f}  ${spread:>6.4f}")
    
    print(f"\n💹 Latest Trades:")
    print("   Symbol   Price     Size      Exchange")
    print("   " + "-" * 45)
    
    for symbol in symbols:
        trade = client.get_latest_trade(symbol)
        if trade:
            print(f"   {symbol:<6}  ${trade['price']:>7.2f}  {trade['size']:>6}    {trade['exchange']}")


def example_news_feed():
    """Example: Get market news"""
    print("\n" + "=" * 60)
    print("Example 4: News Feed")
    print("=" * 60)
    
    client = AlpacaClient()
    
    symbol = 'AAPL'
    news = client.get_news(symbol=symbol, limit=5)
    
    print(f"\n📰 Latest News for {symbol}:")
    print("   " + "-" * 56)
    
    for article in news:
        created = pd.to_datetime(article['created_at']).strftime('%Y-%m-%d %H:%M')
        print(f"\n   [{created}]")
        print(f"   {article['headline']}")
        if article['summary']:
            summary = article['summary'][:100] + "..." if len(article['summary']) > 100 else article['summary']
            print(f"   {summary}")


def example_market_status():
    """Example: Check market status"""
    print("\n" + "=" * 60)
    print("Example 5: Market Status")
    print("=" * 60)
    
    client = AlpacaClient()
    
    clock = client.get_clock()
    
    print(f"\n🕐 Market Clock:")
    print(f"   Status: {'🟢 OPEN' if clock['is_open'] else '🔴 CLOSED'}")
    print(f"   Current Time: {clock['timestamp']}")
    
    if clock['is_open']:
        print(f"   Closes at: {clock['next_close']}")
    else:
        print(f"   Opens at: {clock['next_open']}")


def example_analysis_ready_data():
    """Example: Prepare data for technical analysis"""
    print("\n" + "=" * 60)
    print("Example 6: Data Ready for Technical Analysis")
    print("=" * 60)
    
    client = AlpacaClient()
    
    symbol = 'AAPL'
    bars = client.get_bars(
        symbol=symbol,
        timeframe='1Day',
        limit=50
    )
    
    if bars.empty:
        print("   No data available")
        return
    
    print(f"\n📊 {symbol} - Ready for Technical Indicators:")
    print(f"   Shape: {bars.shape}")
    print(f"\n   Columns: {list(bars.columns)}")
    print(f"\n   First 3 rows:")
    print(bars[['timestamp', 'open', 'high', 'low', 'close', 'volume']].head(3).to_string(index=False))
    
    print(f"\n   ✅ This DataFrame is ready for:")
    print(f"      - RSI calculation (needs 'close' prices)")
    print(f"      - MACD calculation (needs 'close' prices)")
    print(f"      - Bollinger Bands (needs 'close' and std dev)")
    print(f"      - Volume analysis (has 'volume' column)")
    print(f"      - Any pandas/numpy operations!")


def main():
    """Run all examples"""
    print("\n")
    print("╔══════════════════════════════════════════════════════╗")
    print("║     ALPACA CLIENT - EXAMPLE USAGE                    ║")
    print("╚══════════════════════════════════════════════════════╝")
    
    try:
        example_account_info()
        example_historical_data()
        example_realtime_data()
        example_news_feed()
        example_market_status()
        example_analysis_ready_data()
        
        print("\n" + "=" * 60)
        print("✅ All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        print("\nMake sure:")
        print("1. Alpaca API keys are configured in .env")
        print("2. You're using paper trading keys")
        print("3. LM Studio server is running (if testing LLM features)")


if __name__ == "__main__":
    main()
