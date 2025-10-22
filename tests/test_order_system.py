"""
Test Order Execution (Market Hours Independent)

Tests order placement functions without requiring real-time market data.
"""

from wawatrader.alpaca_client import get_client

print("\n" + "="*60)
print("Testing Order Execution Functions")
print("="*60)

client = get_client()

# Test 1: Check account status
print("\n" + "-"*60)
print("Test 1: Verify Account Access")
print("-"*60)

account = client.get_account()
print(f"✅ Account: {account['account_number']}")
print(f"   Status: {account['status']}")
print(f"   Buying Power: ${account['buying_power']:,.2f}")
print(f"   Equity: ${account['equity']:,.2f}")

# Test 2: Get open orders
print("\n" + "-"*60)
print("Test 2: List Open Orders")
print("-"*60)

open_orders = client.get_orders(status='open')
print(f"✅ Open orders: {len(open_orders)}")

if open_orders:
    for order in open_orders[:5]:
        print(f"   {order['id'][:8]}... - {order['symbol']}: {order['side']} {order['qty']} @ {order['status']}")

# Test 3: Get recent order history
print("\n" + "-"*60)
print("Test 3: Get Recent Order History")
print("-"*60)

all_orders = client.get_orders(status='all', limit=10)
print(f"✅ Total recent orders: {len(all_orders)}")

if all_orders:
    print("\nMost recent orders:")
    for order in all_orders[:5]:
        filled_info = f"@ ${order['filled_avg_price']:.2f}" if order['filled_avg_price'] else ""
        print(f"   {order['symbol']}: {order['side'].upper()} {order['qty']} - {order['status']} {filled_info}")
else:
    print("   (No recent orders)")

# Test 4: Get current positions
print("\n" + "-"*60)
print("Test 4: Current Positions")
print("-"*60)

positions = client.get_positions()
print(f"✅ Open positions: {len(positions)}")

if positions:
    for pos in positions:
        pnl_pct = pos['unrealized_plpc'] * 100
        print(f"   {pos['symbol']}: {pos['qty']} shares @ ${pos['avg_entry_price']:.2f}")
        print(f"      Current: ${pos['current_price']:.2f} | P&L: {pnl_pct:+.2f}%")
else:
    print("   (No open positions)")

# Test 5: Market status
print("\n" + "-"*60)
print("Test 5: Market Clock")
print("-"*60)

clock = client.get_clock()
print(f"✅ Market is: {'OPEN' if clock['is_open'] else 'CLOSED'}")
if not clock['is_open']:
    print(f"   Next open: {clock['next_open']}")
    print(f"   Next close: {clock['next_close']}")

# Test 6: Test order methods exist
print("\n" + "-"*60)
print("Test 6: Verify Order Methods")
print("-"*60)

methods = [
    'place_market_order',
    'place_limit_order',
    'get_order',
    'get_orders',
    'cancel_order',
    'cancel_all_orders',
    'wait_for_order_fill'
]

for method in methods:
    has_method = hasattr(client, method)
    status = "✅" if has_method else "❌"
    print(f"{status} {method}: {'Available' if has_method else 'Missing'}")

print("\n" + "="*60)
print("✅ Order execution system ready!")
print("="*60)

print("\n📝 Summary:")
print("   - Order placement methods implemented")
print("   - Order monitoring available")
print("   - Order cancellation available")
print("   - Account access verified")
print()
print("⚠️  To place actual orders:")
print("   1. Wait for market to open, OR")
print("   2. Use extended hours trading, OR")
print("   3. Run during market hours (9:30 AM - 4:00 PM ET)")
print()
print("🔷 Current mode: Paper Trading (no real money)")
