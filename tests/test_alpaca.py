"""
Test Alpaca API Connection and Functionality

Comprehensive tests for Alpaca Markets paper trading API.
Verifies account access, market data retrieval, and order management.
"""

import sys
from datetime import datetime, timedelta
from wawatrader.alpaca_client import AlpacaClient


def test_alpaca_connection():
    """Test complete Alpaca API integration"""
    
    print("🔌 Testing Alpaca API Connection...")
    print("=" * 60)
    
    try:
        # Test 1: Initialize client
        print("\n1️⃣ Initializing Alpaca client...")
        client = AlpacaClient()
        print("   ✅ Client initialized successfully")
        
        # Test 2: Get account information
        print("\n2️⃣ Testing account access...")
        account = client.get_account()
        print(f"   Account Number: {account['account_number']}")
        print(f"   Status: {account['status']}")
        print(f"   Buying Power: ${account['buying_power']:,.2f}")
        print(f"   Portfolio Value: ${account['portfolio_value']:,.2f}")
        print("   ✅ Account access successful")
        
        # Test 3: Check market status
        print("\n3️⃣ Testing market clock...")
        clock = client.get_clock()
        print(f"   Market is: {'🟢 OPEN' if clock['is_open'] else '🔴 CLOSED'}")
        print(f"   Next open: {clock['next_open']}")
        print(f"   Next close: {clock['next_close']}")
        print("   ✅ Market clock working")
        
        # Test 4: Get positions
        print("\n4️⃣ Testing positions retrieval...")
        positions = client.get_positions()
        print(f"   Current positions: {len(positions)}")
        if positions:
            for pos in positions[:3]:  # Show first 3
                print(f"   - {pos['symbol']}: {pos['qty']} shares @ ${pos['current_price']:.2f}")
        print("   ✅ Positions retrieved")
        
        # Test 5: Get historical data
        print("\n5️⃣ Testing market data retrieval...")
        symbol = 'AAPL'
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        bars = client.get_bars(
            symbol=symbol,
            timeframe='1Day',
            start=start_date,
            end=end_date,
            limit=30
        )
        
        if not bars.empty:
            print(f"   Retrieved {len(bars)} bars for {symbol}")
            print(f"   Date range: {bars['timestamp'].min()} to {bars['timestamp'].max()}")
            print(f"   Latest close: ${bars['close'].iloc[-1]:.2f}")
            print("   ✅ Market data retrieved")
        else:
            print("   ⚠️ No market data returned (might be outside market hours)")
        
        # Test 6: Get latest quote
        print("\n6️⃣ Testing real-time quotes...")
        quote = client.get_latest_quote(symbol)
        if quote:
            print(f"   {symbol} Quote:")
            print(f"   Bid: ${quote['bid_price']:.2f} x {quote['bid_size']}")
            print(f"   Ask: ${quote['ask_price']:.2f} x {quote['ask_size']}")
            print("   ✅ Quote retrieved")
        else:
            print("   ⚠️ Quote not available (market might be closed)")
        
        # Test 7: Get latest trade
        print("\n7️⃣ Testing trade data...")
        trade = client.get_latest_trade(symbol)
        if trade:
            print(f"   {symbol} Last Trade:")
            print(f"   Price: ${trade['price']:.2f}")
            print(f"   Size: {trade['size']} shares")
            print(f"   Exchange: {trade['exchange']}")
            print("   ✅ Trade data retrieved")
        else:
            print("   ⚠️ Trade data not available")
        
        # Test 8: Get news
        print("\n8️⃣ Testing news feed...")
        news = client.get_news(symbol=symbol, limit=3)
        if news:
            print(f"   Retrieved {len(news)} news articles for {symbol}:")
            for article in news:
                print(f"   - {article['headline'][:60]}...")
            print("   ✅ News feed working")
        else:
            print("   ⚠️ No news articles available")
        
        # Test 9: Get orders
        print("\n9️⃣ Testing order retrieval...")
        orders = client.get_orders(status='open')
        print(f"   Open orders: {len(orders)}")
        if orders:
            for order in orders[:3]:
                print(f"   - {order['symbol']}: {order['side']} {order['qty']} @ {order['type']}")
        print("   ✅ Order retrieval working")
        
        # Test 10: Account summary
        print("\n🔟 Testing account summary...")
        summary = client.get_account_summary()
        print(summary)
        
        # Final result
        print("\n" + "=" * 60)
        print("✅ All Alpaca API tests passed!")
        print("=" * 60)
        print("\n🎯 Your Alpaca paper trading account is ready!")
        print("   You can now:")
        print("   • Fetch market data for technical analysis")
        print("   • Read news for LLM sentiment analysis")
        print("   • Place paper trades (when order manager is built)")
        print("   • Monitor positions and P&L")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ Test failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure you have Alpaca API keys in .env file")
        print("2. Verify you're using PAPER TRADING keys (not live)")
        print("3. Check that keys start with PK... and SK...")
        print("4. Ensure ALPACA_BASE_URL=https://paper-api.alpaca.markets")
        print("5. Try regenerating keys in Alpaca dashboard")
        print("\nTo set up .env:")
        print("   cp .env.example .env")
        print("   # Edit .env and add your keys")
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = test_alpaca_connection()
    sys.exit(0 if success else 1)
