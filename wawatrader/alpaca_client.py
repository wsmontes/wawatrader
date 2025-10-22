"""
Alpaca Market Client

Wrapper around Alpaca API for paper trading.
Provides clean interface for:
- Account information
- Market data (bars, quotes, trades)
- News feed
- Position and order management

All methods handle errors gracefully and return structured data.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from loguru import logger

import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import APIError, TimeFrame, TimeFrameUnit

from config import settings


class AlpacaClient:
    """
    Alpaca API Client for Paper Trading
    
    Manages connection to Alpaca Markets API and provides
    clean interface for trading operations.
    """
    
    def __init__(self):
        """Initialize Alpaca API client"""
        logger.info("Initializing Alpaca client...")
        
        try:
            self.api = tradeapi.REST(
                key_id=settings.alpaca.api_key,
                secret_key=settings.alpaca.secret_key,
                base_url=settings.alpaca.base_url
            )
            
            # Verify connection by getting account
            account = self.api.get_account()
            logger.info(f"✅ Connected to Alpaca (Account: {account.account_number})")
            logger.info(f"   Status: {account.status}")
            logger.info(f"   Buying Power: ${float(account.buying_power):,.2f}")
            
        except APIError as e:
            logger.error(f"❌ Failed to connect to Alpaca: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error initializing Alpaca: {e}")
            raise
    
    # =====================================================
    # Account Information
    # =====================================================
    
    def get_account(self) -> Dict[str, Any]:
        """
        Get account information
        
        Returns:
            Dictionary with account details including:
            - account_number
            - status
            - cash
            - buying_power
            - portfolio_value
            - equity
            - daytrade_count
        """
        try:
            account = self.api.get_account()
            
            return {
                'account_number': account.account_number,
                'status': account.status,
                'cash': float(account.cash),
                'buying_power': float(account.buying_power),
                'portfolio_value': float(account.portfolio_value),
                'equity': float(account.equity),
                'daytrade_count': int(account.daytrade_count),
                'pattern_day_trader': account.pattern_day_trader,
                'trading_blocked': account.trading_blocked,
                'account_blocked': account.account_blocked,
                'last_equity': float(account.last_equity)
            }
        except APIError as e:
            logger.error(f"Failed to get account: {e}")
            raise
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get all open positions
        
        Returns:
            List of position dictionaries
        """
        try:
            positions = self.api.list_positions()
            
            return [
                {
                    'symbol': pos.symbol,
                    'qty': float(pos.qty),
                    'side': pos.side,
                    'market_value': float(pos.market_value),
                    'cost_basis': float(pos.cost_basis),
                    'unrealized_pl': float(pos.unrealized_pl),
                    'unrealized_plpc': float(pos.unrealized_plpc),
                    'current_price': float(pos.current_price),
                    'avg_entry_price': float(pos.avg_entry_price),
                }
                for pos in positions
            ]
        except APIError as e:
            logger.error(f"Failed to get positions: {e}")
            return []
    
    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get position for specific symbol
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            
        Returns:
            Position dictionary or None if no position
        """
        try:
            pos = self.api.get_position(symbol)
            return {
                'symbol': pos.symbol,
                'qty': float(pos.qty),
                'side': pos.side,
                'market_value': float(pos.market_value),
                'cost_basis': float(pos.cost_basis),
                'unrealized_pl': float(pos.unrealized_pl),
                'unrealized_plpc': float(pos.unrealized_plpc),
                'current_price': float(pos.current_price),
                'avg_entry_price': float(pos.avg_entry_price),
            }
        except APIError:
            # No position exists
            return None
    
    def get_portfolio_history(self, period: str = "1M", timeframe: str = "1D") -> Optional[Dict[str, Any]]:
        """
        Get portfolio history for charting
        
        Args:
            period: Time period (1D, 7D, 1M, 3M, 1Y, 5Y, max)
            timeframe: Data resolution (1Min, 5Min, 15Min, 1H, 1D)
            
        Returns:
            Dictionary with timestamp and equity arrays
        """
        try:
            # Use Alpaca's portfolio history endpoint
            history = self.api.get_portfolio_history(
                period=period,
                timeframe=timeframe
            )
            
            if history and hasattr(history, 'timestamp') and hasattr(history, 'equity'):
                return {
                    'timestamp': history.timestamp,
                    'equity': history.equity
                }
            else:
                # Fallback to account value if no history
                account = self.get_account()
                current_time = pd.Timestamp.now().timestamp()
                return {
                    'timestamp': [current_time],
                    'equity': [account['portfolio_value']]
                }
                
        except APIError as e:
            logger.error(f"Failed to get portfolio history: {e}")
            # Return current account value as fallback
            try:
                account = self.get_account()
                current_time = pd.Timestamp.now().timestamp()
                return {
                    'timestamp': [current_time],
                    'equity': [account['portfolio_value']]
                }
            except:
                return None
    
    # =====================================================
    # Market Data - Historical Bars
    # =====================================================
    
    def get_bars(
        self,
        symbol: str,
        timeframe: str = '1Day',
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Get historical price bars
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            timeframe: Bar timeframe ('1Min', '5Min', '1Hour', '1Day')
            start: Start date (default: 100 days ago)
            end: End date (default: now)
            limit: Maximum number of bars (default: 100)
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Parse timeframe
            tf_map = {
                '1Min': TimeFrame.Minute,
                '5Min': TimeFrame(5, TimeFrameUnit.Minute),
                '15Min': TimeFrame(15, TimeFrameUnit.Minute),
                '1Hour': TimeFrame.Hour,
                '1Day': TimeFrame.Day,
            }
            tf = tf_map.get(timeframe, TimeFrame.Day)
            
            # Default date range
            if end is None:
                end = datetime.now()
            if start is None:
                start = end - timedelta(days=100)
            
            # Fetch bars
            bars = self.api.get_bars(
                symbol,
                tf,
                start=start.strftime('%Y-%m-%d'),
                end=end.strftime('%Y-%m-%d'),
                limit=limit,
                adjustment='raw'
            )
            
            # Convert to DataFrame
            df = bars.df
            
            if df.empty:
                logger.warning(f"No bars returned for {symbol}")
                return pd.DataFrame()
            
            # Clean up column names
            df.columns = [col.lower() for col in df.columns]
            
            # Reset index to make timestamp a column
            df = df.reset_index()
            df.columns = ['timestamp'] + list(df.columns[1:])
            
            logger.debug(f"Retrieved {len(df)} bars for {symbol}")
            return df
            
        except APIError as e:
            logger.error(f"Failed to get bars for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_latest_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get latest quote (bid/ask)
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Quote dictionary with bid/ask prices and sizes
        """
        try:
            quote = self.api.get_latest_quote(symbol)
            return {
                'symbol': symbol,
                'bid_price': float(quote.bp),
                'bid_size': int(quote.bs),
                'ask_price': float(quote.ap),
                'ask_size': int(quote.as_),  # Note: 'as' is Python keyword
                'timestamp': quote.t
            }
        except AttributeError:
            # Handle different API response format
            quote = self.api.get_latest_quote(symbol)
            return {
                'symbol': symbol,
                'bid_price': float(quote.bp),
                'bid_size': int(quote.bs),
                'ask_price': float(quote.ap),
                'ask_size': int(quote.ask_size) if hasattr(quote, 'ask_size') else int(quote.bs),
                'timestamp': quote.t
            }
        except APIError as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            return None
    
    def get_latest_trade(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get latest trade
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Trade dictionary with price and size
        """
        try:
            trade = self.api.get_latest_trade(symbol)
            return {
                'symbol': symbol,
                'price': float(trade.p),
                'size': int(trade.s),
                'timestamp': trade.t,
                'exchange': trade.x
            }
        except APIError as e:
            logger.error(f"Failed to get trade for {symbol}: {e}")
            return None
    
    # =====================================================
    # News Feed
    # =====================================================
    
    def get_news(
        self,
        symbol: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get news articles
        
        Args:
            symbol: Stock symbol (None for general market news)
            start: Start date
            end: End date
            limit: Maximum number of articles
            
        Returns:
            List of news article dictionaries
        """
        try:
            news = self.api.get_news(
                symbol=symbol,
                start=start.isoformat() if start else None,
                end=end.isoformat() if end else None,
                limit=limit
            )
            
            return [
                {
                    'id': article.id,
                    'headline': article.headline,
                    'summary': article.summary,
                    'author': article.author,
                    'created_at': article.created_at,
                    'updated_at': article.updated_at,
                    'url': article.url,
                    'symbols': article.symbols if hasattr(article, 'symbols') else []
                }
                for article in news
            ]
        except APIError as e:
            logger.error(f"Failed to get news: {e}")
            return []
    
    # =====================================================
    # Market Status
    # =====================================================
    
    def get_clock(self) -> Dict[str, Any]:
        """
        Get market clock
        
        Returns:
            Dictionary with market status:
            - is_open: Boolean
            - next_open: Next market open time
            - next_close: Next market close time
            - timestamp: Current time
        """
        try:
            clock = self.api.get_clock()
            return {
                'is_open': clock.is_open,
                'next_open': clock.next_open,
                'next_close': clock.next_close,
                'timestamp': clock.timestamp
            }
        except APIError as e:
            logger.error(f"Failed to get clock: {e}")
            return {'is_open': False}
    
    def is_market_open(self) -> bool:
        """Check if market is currently open"""
        clock = self.get_clock()
        return clock.get('is_open', False)
    
    # =====================================================
    # Order Management
    # =====================================================
    
    def get_orders(self, status: str = 'open') -> List[Dict[str, Any]]:
        """
        Get orders
        
        Args:
            status: Order status ('open', 'closed', 'all')
            
        Returns:
            List of order dictionaries
        """
        try:
            orders = self.api.list_orders(status=status)
            
            return [
                {
                    'id': order.id,
                    'symbol': order.symbol,
                    'qty': float(order.qty),
                    'filled_qty': float(order.filled_qty),
                    'side': order.side,
                    'type': order.type,
                    'status': order.status,
                    'limit_price': float(order.limit_price) if order.limit_price else None,
                    'stop_price': float(order.stop_price) if order.stop_price else None,
                    'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                    'created_at': order.created_at,
                    'updated_at': order.updated_at,
                }
                for order in orders
            ]
        except APIError as e:
            logger.error(f"Failed to get orders: {e}")
            return []
    
    # =====================================================
    # Utilities
    # =====================================================
    
    def get_account_summary(self) -> str:
        """
        Get human-readable account summary
        
        Returns:
            Formatted string with account details
        """
        try:
            account = self.get_account()
            positions = self.get_positions()
            orders = self.get_orders(status='open')
            
            summary = f"""
╔══════════════════════════════════════════════════════╗
║          ALPACA PAPER TRADING ACCOUNT                ║
╚══════════════════════════════════════════════════════╝

Account Number: {account['account_number']}
Status: {account['status']}

💰 Account Value:
   Portfolio Value:    ${account['portfolio_value']:>15,.2f}
   Cash:              ${account['cash']:>15,.2f}
   Buying Power:      ${account['buying_power']:>15,.2f}
   Equity:            ${account['equity']:>15,.2f}

📊 Positions: {len(positions)}
"""
            
            if positions:
                summary += "\n   Symbol    Qty      Value      P&L      P&L%\n"
                summary += "   " + "-" * 50 + "\n"
                for pos in positions:
                    pl_sign = "+" if pos['unrealized_pl'] >= 0 else ""
                    plpc_sign = "+" if pos['unrealized_plpc'] >= 0 else ""
                    summary += f"   {pos['symbol']:<6} {pos['qty']:>6.0f}  ${pos['market_value']:>10,.2f}  {pl_sign}${pos['unrealized_pl']:>8,.2f}  {plpc_sign}{pos['unrealized_plpc']*100:>6.2f}%\n"
            
            summary += f"\n📝 Open Orders: {len(orders)}\n"
            
            if orders:
                summary += "\n   Symbol    Side    Qty    Type      Status\n"
                summary += "   " + "-" * 50 + "\n"
                for order in orders[:5]:  # Show first 5
                    summary += f"   {order['symbol']:<6}  {order['side']:<4}  {order['qty']:>6.0f}  {order['type']:<8}  {order['status']}\n"
            
            summary += "\n" + "═" * 58
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate account summary: {e}")
            return "❌ Failed to generate account summary"


# =====================================================
# Convenience Functions
    # =====================================================
    # ORDER EXECUTION & MANAGEMENT
    # =====================================================
    
    def place_market_order(
        self,
        symbol: str,
        qty: int,
        side: str,
        time_in_force: str = 'day'
    ) -> Optional[Dict[str, Any]]:
        """
        Place a market order (execute at current price).
        
        Args:
            symbol: Stock ticker
            qty: Number of shares
            side: 'buy' or 'sell'
            time_in_force: 'day', 'gtc' (good til canceled), 'ioc', 'fok'
        
        Returns:
            Order dict with details, or None if failed
        """
        try:
            logger.info(f"Placing market order: {side.upper()} {qty} {symbol}")
            
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type='market',
                time_in_force=time_in_force
            )
            
            result = {
                'id': order.id,
                'client_order_id': order.client_order_id,
                'symbol': order.symbol,
                'qty': float(order.qty),
                'side': order.side,
                'type': order.type,
                'time_in_force': order.time_in_force,
                'status': order.status,
                'created_at': str(order.created_at),
                'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                'filled_qty': float(order.filled_qty) if order.filled_qty else 0
            }
            
            logger.info(f"✅ Order placed: {result['id']} ({result['status']})")
            return result
            
        except APIError as e:
            logger.error(f"Failed to place market order: {e}")
            return None
    
    def place_limit_order(
        self,
        symbol: str,
        qty: int,
        side: str,
        limit_price: float,
        time_in_force: str = 'day'
    ) -> Optional[Dict[str, Any]]:
        """
        Place a limit order (execute at specified price or better).
        
        Args:
            symbol: Stock ticker
            qty: Number of shares
            side: 'buy' or 'sell'
            limit_price: Price limit
            time_in_force: 'day', 'gtc', 'ioc', 'fok'
        
        Returns:
            Order dict with details, or None if failed
        """
        try:
            logger.info(f"Placing limit order: {side.upper()} {qty} {symbol} @ ${limit_price:.2f}")
            
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type='limit',
                limit_price=limit_price,
                time_in_force=time_in_force
            )
            
            result = {
                'id': order.id,
                'client_order_id': order.client_order_id,
                'symbol': order.symbol,
                'qty': float(order.qty),
                'side': order.side,
                'type': order.type,
                'limit_price': float(order.limit_price),
                'time_in_force': order.time_in_force,
                'status': order.status,
                'created_at': str(order.created_at),
                'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                'filled_qty': float(order.filled_qty) if order.filled_qty else 0
            }
            
            logger.info(f"✅ Limit order placed: {result['id']} ({result['status']})")
            return result
            
        except APIError as e:
            logger.error(f"Failed to place limit order: {e}")
            return None
    
    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get order details by ID.
        
        Args:
            order_id: Order ID
        
        Returns:
            Order dict, or None if not found
        """
        try:
            order = self.api.get_order(order_id)
            
            return {
                'id': order.id,
                'client_order_id': order.client_order_id,
                'symbol': order.symbol,
                'qty': float(order.qty),
                'side': order.side,
                'type': order.type,
                'status': order.status,
                'created_at': str(order.created_at),
                'updated_at': str(order.updated_at) if order.updated_at else None,
                'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                'filled_qty': float(order.filled_qty) if order.filled_qty else 0,
                'limit_price': float(order.limit_price) if hasattr(order, 'limit_price') and order.limit_price else None
            }
            
        except APIError as e:
            logger.error(f"Failed to get order {order_id}: {e}")
            return None
    
    def get_orders(
        self,
        status: str = 'all',
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get orders with optional status filter.
        
        Args:
            status: 'all', 'open', 'closed'
            limit: Max number of orders to return
        
        Returns:
            List of order dicts
        """
        try:
            orders = self.api.list_orders(
                status=status,
                limit=limit
            )
            
            return [
                {
                    'id': order.id,
                    'symbol': order.symbol,
                    'qty': float(order.qty),
                    'side': order.side,
                    'type': order.type,
                    'status': order.status,
                    'created_at': str(order.created_at),
                    'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                    'filled_qty': float(order.filled_qty) if order.filled_qty else 0
                }
                for order in orders
            ]
            
        except APIError as e:
            logger.error(f"Failed to get orders: {e}")
            return []
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an open order.
        
        Args:
            order_id: Order ID to cancel
        
        Returns:
            True if canceled successfully, False otherwise
        """
        try:
            self.api.cancel_order(order_id)
            logger.info(f"✅ Order {order_id} canceled")
            return True
            
        except APIError as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    def cancel_all_orders(self) -> bool:
        """
        Cancel all open orders.
        
        Returns:
            True if all canceled successfully, False otherwise
        """
        try:
            self.api.cancel_all_orders()
            logger.info("✅ All orders canceled")
            return True
            
        except APIError as e:
            logger.error(f"Failed to cancel all orders: {e}")
            return False
    
    def wait_for_order_fill(
        self,
        order_id: str,
        timeout_seconds: int = 60,
        poll_interval: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """
        Wait for an order to fill (blocking).
        
        Args:
            order_id: Order ID to monitor
            timeout_seconds: Max seconds to wait
            poll_interval: Seconds between checks
        
        Returns:
            Final order dict if filled, None if timeout or error
        """
        import time
        
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            order = self.get_order(order_id)
            
            if not order:
                logger.error(f"Order {order_id} not found")
                return None
            
            status = order['status']
            
            if status == 'filled':
                logger.info(f"✅ Order {order_id} filled @ ${order['filled_avg_price']:.2f}")
                return order
            
            if status in ['canceled', 'expired', 'rejected']:
                logger.warning(f"⚠️  Order {order_id} {status}")
                return order
            
            time.sleep(poll_interval)
        
        logger.warning(f"⏱️  Order {order_id} timeout after {timeout_seconds}s")
        return self.get_order(order_id)

    # =====================================================

def get_client() -> AlpacaClient:
    """Get configured Alpaca client instance"""
    return AlpacaClient()
if __name__ == "__main__":
    # Test the client
    from loguru import logger
    import sys
    
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    
    print("Testing Alpaca Client...")
    print("=" * 60)
    
    try:
        client = AlpacaClient()
        
        print("\n" + client.get_account_summary())
        
        print("\n✅ Alpaca client test successful!")
        
    except Exception as e:
        print(f"\n❌ Alpaca client test failed: {e}")
        sys.exit(1)
