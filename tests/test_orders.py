"""
Test Order Execution

Tests order placement, monitoring, and cancellation.
NOTE: These tests interact with the paper trading account.
"""

from wawatrader.alpaca_client import get_client
import time

print("\n" + "="*60)
print("Testing Order Execution")
print("="*60)

client = get_client()

# Test 1: Get current orders
print("\n" + "-"*60)
print("Test 1: List Open Orders")
print("-"*60)

open_orders = client.get_orders(status='open')
print(f"✅ Open orders: {len(open_orders)}")
for order in open_orders[:3]:  # Show first 3
    print(f"   {order['symbol']}: {order['side']} {order['qty']} @ {order['status']}")

# Test 2: Place a limit order (won't fill immediately)
print("\n" + "-"*60)
print("Test 2: Place Limit Order (Test Only)")
print("-"*60)

symbol = "AAPL"
qty = 1
side = "buy"

# Get current price
quote = client.get_latest_quote(symbol)
if quote:
    current_price = quote['ask_price']
    # Set limit price 5% below current (won't fill)
    limit_price = round(current_price * 0.95, 2)
    
    print(f"Current ask: ${current_price:.2f}")
    print(f"Limit price: ${limit_price:.2f} (5% below)")
    print(f"\nPlacing limit order: {side.upper()} {qty} {symbol} @ ${limit_price:.2f}")
    
    order = client.place_limit_order(
        symbol=symbol,
        qty=qty,
        side=side,
        limit_price=limit_price,
        time_in_force='day'
    )
    
    if order:
        print(f"✅ Order placed successfully")
        print(f"   Order ID: {order['id']}")
        print(f"   Status: {order['status']}")
        print(f"   Type: {order['type']}")
        
        # Test 3: Get order status
        print("\n" + "-"*60)
        print("Test 3: Check Order Status")
        print("-"*60)
        
        time.sleep(1)  # Wait a moment
        
        updated_order = client.get_order(order['id'])
        if updated_order:
            print(f"✅ Order status: {updated_order['status']}")
            print(f"   Filled qty: {updated_order['filled_qty']}")
        
        # Test 4: Cancel the order
        print("\n" + "-"*60)
        print("Test 4: Cancel Order")
        print("-"*60)
        
        success = client.cancel_order(order['id'])
        if success:
            print(f"✅ Order canceled successfully")
            
            # Verify cancellation
            time.sleep(1)
            final_order = client.get_order(order['id'])
            if final_order:
                print(f"   Final status: {final_order['status']}")
        else:
            print(f"❌ Failed to cancel order")
    else:
        print(f"❌ Failed to place order")
else:
    print(f"❌ Failed to get quote for {symbol}")

# Test 5: Get order history
print("\n" + "-"*60)
print("Test 5: Get Recent Orders")
print("-"*60)

recent_orders = client.get_orders(status='all', limit=5)
print(f"✅ Recent orders: {len(recent_orders)}")
for order in recent_orders:
    filled_price = f"@ ${order['filled_avg_price']:.2f}" if order['filled_avg_price'] else ""
    print(f"   {order['symbol']}: {order['side']} {order['qty']} - {order['status']} {filled_price}")

print("\n" + "="*60)
print("✅ Order execution tests complete!")
print("="*60)
print("\n⚠️  NOTE: These tests use the paper trading account.")
print("   No real money was used or risked.")
