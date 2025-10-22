#!/usr/bin/env python3
"""
Execute a Live Paper Trade

This demonstrates actual trade execution on the Alpaca paper trading account.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from wawatrader.alpaca_client import get_client
from wawatrader.risk_manager import get_risk_manager
from wawatrader.alerts import get_alert_manager
from loguru import logger
import time

def execute_sample_trade():
    """Execute a sample paper trade to demonstrate the system"""
    
    print("🔥 WawaTrader - LIVE PAPER TRADE EXECUTION")
    print("=" * 60)
    print()
    
    try:
        # Get components
        client = get_client()
        risk_manager = get_risk_manager()
        alerts = get_alert_manager()
        
        # Get account info
        account = client.get_account()
        print(f"📊 Account Status:")
        print(f"   Account: {account.account_number}")
        print(f"   Buying Power: ${float(account.buying_power):,.2f}")
        print(f"   Portfolio Value: ${float(account.portfolio_value):,.2f}")
        print()
        
        # Sample trade parameters
        symbol = "AAPL"
        shares = 10  # Small position for demo
        action = "BUY"
        
        print(f"🎯 Preparing Paper Trade:")
        print(f"   Symbol: {symbol}")
        print(f"   Action: {action}")
        print(f"   Shares: {shares}")
        print()
        
        # Get current price (if available)
        try:
            quote = client.get_latest_quote(symbol)
            if quote:
                current_price = float(quote.ask_price) if hasattr(quote, 'ask_price') else 225.0
            else:
                current_price = 225.0  # Fallback price
        except:
            current_price = 225.0  # Fallback price
            
        print(f"💰 Estimated Price: ${current_price:.2f}")
        estimated_cost = shares * current_price
        print(f"📈 Estimated Cost: ${estimated_cost:,.2f}")
        print()
        
        # Risk check
        print("🛡️ Risk Management Check:")
        portfolio_value = float(account.portfolio_value) or 100000
        position_pct = (estimated_cost / portfolio_value) * 100
        
        if position_pct <= 10:  # 10% max position size
            print(f"   ✅ Position Size: {position_pct:.1f}% (within 10% limit)")
            risk_approved = True
        else:
            print(f"   ❌ Position Size: {position_pct:.1f}% (exceeds 10% limit)")
            risk_approved = False
            
        print()
        
        if risk_approved:
            print("🚀 Executing Paper Trade...")
            
            try:
                # Execute market order
                order = client.submit_order(
                    symbol=symbol,
                    qty=shares,
                    side=action.lower(),
                    type='market',
                    time_in_force='day'
                )
                
                print(f"✅ ORDER SUBMITTED!")
                print(f"   Order ID: {order.id}")
                print(f"   Status: {order.status}")
                print(f"   Symbol: {order.symbol}")
                print(f"   Qty: {order.qty}")
                print(f"   Side: {order.side}")
                print()
                
                # Send alert
                try:
                    alerts.send_trade_alert(
                        symbol=symbol,
                        action=action,
                        quantity=shares,
                        price=current_price,
                        total_cost=estimated_cost
                    )
                    print("📧 Trade alert sent!")
                except Exception as e:
                    print(f"⚠️ Alert failed: {e}")
                
                print()
                print("🎉 PAPER TRADE EXECUTED SUCCESSFULLY!")
                print("📊 Check the dashboard for updates")
                
            except Exception as e:
                print(f"❌ Trade execution failed: {e}")
                
        else:
            print("❌ Trade blocked by risk management")
            
        print()
        print("=" * 60)
        print("Dashboard: http://127.0.0.1:8050")
        print("✅ WawaTrader is operational for paper trading!")
        
    except Exception as e:
        logger.error(f"❌ Error in trade execution: {e}")
        raise

if __name__ == "__main__":
    execute_sample_trade()