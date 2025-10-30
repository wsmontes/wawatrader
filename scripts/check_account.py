import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

load_dotenv()

client = TradingClient(
    api_key=os.getenv('ALPACA_API_KEY'),
    secret_key=os.getenv('ALPACA_SECRET_KEY'),
    paper=True
)

account = client.get_account()
print(f"💰 Account Status:")
print(f"  Equity: ${float(account.equity):,.2f}")
print(f"  Cash: ${float(account.cash):,.2f}")
print(f"  Buying Power: ${float(account.buying_power):,.2f}")
print(f"  Portfolio Value: ${float(account.portfolio_value):,.2f}")
print(f"  Long Market Value: ${float(account.long_market_value):,.2f}")
print(f"  Short Market Value: ${float(account.short_market_value):,.2f}")
print(f"  Multiplier: {account.multiplier}")
print(f"  Leverage: {float(account.long_market_value) / float(account.equity):.2%}")
