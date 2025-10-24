"""
Alpaca Market Client - Modern Implementation

Updated to use the official alpaca-py library instead of legacy alpaca-trade-api.
Maintains the same interface for backward compatibility while providing:
- Better async support
- Native type hints
- Pydantic models for data validation
- Improved error handling
- More reliable market data access

Migration from alpaca-trade-api to alpaca-py while preserving existing API.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from loguru import logger

# Modern alpaca-py imports
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest, OrderSide, OrderType, TimeInForce
from alpaca.trading.enums import OrderStatus, AssetClass
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockQuotesRequest, StockTradesRequest, NewsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.common.exceptions import APIError

from config import settings


class AlpacaClient:
    """
    Modern Alpaca API Client using alpaca-py
    
    Manages connections to both Trading API and Market Data API
    while maintaining backward compatibility with existing interface.
    """
    
    def __init__(self):
        """Initialize Alpaca API clients"""
        logger.info("Initializing Alpaca client...")
        
        try:
            # Initialize trading client
            self.trading_client = TradingClient(
                api_key=settings.alpaca.api_key,
                secret_key=settings.alpaca.secret_key,
                paper=True  # Always use paper trading for safety
            )
            
            # Initialize market data client  
            self.data_client = StockHistoricalDataClient(
                api_key=settings.alpaca.api_key,
                secret_key=settings.alpaca.secret_key
            )
            
            # Verify connection by getting account
            account = self.trading_client.get_account()
            logger.info(f"✅ Connected to Alpaca (Account: {account.account_number})")
            logger.info(f"   Status: {account.status}")
            logger.info(f"   Buying Power: ${float(account.buying_power):,.2f}")
            
        except APIError as e:
            logger.error(f"❌ Failed to connect to Alpaca: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error initializing Alpaca: {e}")
            raise
    
    def _get_best_feed(self, prefer_sip: bool = True) -> str:
        """
        Get the best available data feed based on subscription
        
        Paper trading accounts get:
        - Free IEX real-time data ✅
        - SIP historical data (15+ minutes old) ✅
        - SIP real-time data requires AlgoTrader Plus subscription ❌
        
        Args:
            prefer_sip: Whether to prefer SIP data if available
            
        Returns:
            Feed name ('iex' or 'sip')
        """
        # For paper trading, default to IEX which is always available
        # SIP will only work for historical data >15 minutes old
        # or with AlgoTrader Plus subscription
        return 'iex'  # Safe default for paper trading
    
    def get_subscription_info(self) -> Dict[str, Any]:
        """
        Get information about current market data subscription capabilities
        
        Returns:
            Dictionary with subscription details and available data
        """
        return {
            'account_type': 'paper_trading',
            'free_data_available': {
                'iex_real_time': True,
                'iex_historical': True,
                'sip_historical_15min_plus': True,
                'crypto_free': True
            },
            'paid_subscription_required': {
                'sip_real_time': 'AlgoTrader Plus',
                'sip_recent_15min': 'AlgoTrader Plus',
                'options_data': 'AlgoTrader Plus',
                'otc_data': 'Broker Partner Special'
            },
            'data_explanation': {
                'IEX': 'Single exchange (Investors Exchange) - free real-time data',
                'SIP': 'Securities Information Processor - consolidated market data'
            },
            'library': 'alpaca-py v2 (modern)',
            'migration_complete': True
        }

    def get_account(self) -> Dict[str, Any]:
        """
        Get account information
        
        Returns:
            Dictionary with account details
        """
        try:
            account = self.trading_client.get_account()
            
            return {
                'account_number': account.account_number,
                'status': account.status.value,
                'currency': account.currency,
                'buying_power': float(account.buying_power),
                'cash': float(account.cash),
                'portfolio_value': float(account.portfolio_value),
                'equity': float(account.equity),
                'last_equity': float(account.last_equity),
                'multiplier': float(account.multiplier),
                'initial_margin': float(account.initial_margin),
                'maintenance_margin': float(account.maintenance_margin),
                'pattern_day_trader': account.pattern_day_trader,
                'trading_blocked': account.trading_blocked,
                'transfers_blocked': account.transfers_blocked,
                'account_blocked': account.account_blocked
            }
            
        except APIError as e:
            logger.error(f"❌ Failed to get account info: {e}")
            return {}
        except Exception as e:
            logger.error(f"❌ Unexpected error getting account: {e}")
            return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get all open positions
        
        Returns:
            List of position dictionaries
        """
        try:
            positions = self.trading_client.get_all_positions()
            
            result = []
            for pos in positions:
                result.append({
                    'asset_id': pos.asset_id,
                    'symbol': pos.symbol,
                    'asset_class': pos.asset_class.value,
                    'qty': float(pos.qty),
                    'side': 'long' if float(pos.qty) > 0 else 'short',
                    'market_value': float(pos.market_value) if pos.market_value else 0.0,
                    'cost_basis': float(pos.cost_basis) if pos.cost_basis else 0.0,
                    'unrealized_pl': float(pos.unrealized_pl) if pos.unrealized_pl else 0.0,
                    'unrealized_plpc': float(pos.unrealized_plpc) if pos.unrealized_plpc else 0.0,
                    'current_price': float(pos.current_price) if pos.current_price else 0.0,
                    'avg_entry_price': float(pos.avg_entry_price) if pos.avg_entry_price else 0.0,
                    'change_today': float(pos.change_today) if pos.change_today else 0.0
                })
            
            return result
            
        except APIError as e:
            logger.error(f"❌ Failed to get positions: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Unexpected error getting positions: {e}")
            return []

    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get position for specific symbol
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            
        Returns:
            Position dictionary or None if not found
        """
        try:
            position = self.trading_client.get_open_position(symbol)
            
            return {
                'asset_id': position.asset_id,
                'symbol': position.symbol,
                'asset_class': position.asset_class.value,
                'qty': float(position.qty),
                'side': 'long' if float(position.qty) > 0 else 'short',
                'market_value': float(position.market_value) if position.market_value else 0.0,
                'cost_basis': float(position.cost_basis) if position.cost_basis else 0.0,
                'unrealized_pl': float(position.unrealized_pl) if position.unrealized_pl else 0.0,
                'unrealized_plpc': float(position.unrealized_plpc) if position.unrealized_plpc else 0.0,
                'current_price': float(position.current_price) if position.current_price else 0.0,
                'avg_entry_price': float(position.avg_entry_price) if position.avg_entry_price else 0.0,
                'change_today': float(position.change_today) if position.change_today else 0.0
            }
            
        except APIError as e:
            logger.debug(f"No position found for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error getting position for {symbol}: {e}")
            return None

    def get_portfolio_history(self, period: str = "1M", timeframe: str = "1D") -> Optional[Dict[str, Any]]:
        """
        Get portfolio history
        
        Args:
            period: Time period (1D, 1W, 1M, 3M, 1Y, 5Y, max)
            timeframe: Resolution (1Min, 5Min, 15Min, 1H, 1D)
            
        Returns:
            Portfolio history data
        """
        try:
            # Convert period to actual dates
            end_date = datetime.now()
            if period == "1D":
                start_date = end_date - timedelta(days=1)
            elif period == "1W":
                start_date = end_date - timedelta(weeks=1)
            elif period == "1M":
                start_date = end_date - timedelta(days=30)
            elif period == "3M":
                start_date = end_date - timedelta(days=90)
            elif period == "1Y":
                start_date = end_date - timedelta(days=365)
            elif period == "5Y":
                start_date = end_date - timedelta(days=365*5)
            else:  # max
                start_date = end_date - timedelta(days=365*10)
            
            portfolio_history = self.trading_client.get_portfolio_history(
                period=period,
                timeframe=timeframe,
                extended_hours=False
            )
            
            if portfolio_history:
                return {
                    'timestamp': [ts.isoformat() for ts in portfolio_history.timestamp],
                    'equity': [float(eq) if eq else 0.0 for eq in portfolio_history.equity],
                    'profit_loss': [float(pl) if pl else 0.0 for pl in portfolio_history.profit_loss],
                    'profit_loss_pct': [float(plp) if plp else 0.0 for plp in portfolio_history.profit_loss_pct],
                    'base_value': float(portfolio_history.base_value) if portfolio_history.base_value else 0.0,
                    'timeframe': timeframe,
                    'period': period
                }
            
            return None
            
        except APIError as e:
            logger.error(f"❌ Failed to get portfolio history: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error getting portfolio history: {e}")
            return None

    def get_bars(
        self, 
        symbol: str,
        start: Union[datetime, str, None] = None,
        end: Union[datetime, str, None] = None,
        timeframe: str = "1Day",
        limit: int = 1000
    ) -> pd.DataFrame:
        """
        Get historical bars (OHLCV) data using modern alpaca-py
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            start: Start date (default: 100 days ago)
            end: End date (default: now)
            timeframe: Bar timeframe (1Min, 5Min, 15Min, 1Hour, 1Day)
            limit: Maximum number of bars
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Handle default dates
            if end is None:
                end = datetime.now()
            elif isinstance(end, str):
                end = pd.to_datetime(end)
                
            if start is None:
                start = end - timedelta(days=100)
            elif isinstance(start, str):
                start = pd.to_datetime(start)
            
            # Convert timeframe string to TimeFrame object
            if timeframe == "1Min":
                tf = TimeFrame.Minute
            elif timeframe == "5Min":
                tf = TimeFrame(5, TimeFrameUnit.Minute)
            elif timeframe == "15Min":
                tf = TimeFrame(15, TimeFrameUnit.Minute)
            elif timeframe == "1Hour":
                tf = TimeFrame.Hour
            elif timeframe in ["1Day", "1D"]:
                tf = TimeFrame.Day
            else:
                tf = TimeFrame.Day  # Default fallback
            
            # Create request - explicitly use IEX feed for free tier/paper trading
            request = StockBarsRequest(
                symbol_or_symbols=[symbol],
                timeframe=tf,
                start=start,
                end=end,
                limit=limit,
                feed='iex'  # Use IEX for paper trading (free tier)
            )
            
            logger.debug(f"Requesting bars for {symbol} from {start} to {end} using IEX feed")
            
            # Get data
            try:
                bars = self.data_client.get_stock_bars(request)
                
                if symbol in bars.data and bars.data[symbol]:
                    # Convert to DataFrame
                    bar_list = bars.data[symbol]
                    
                    data = {
                        'timestamp': [bar.timestamp for bar in bar_list],
                        'open': [float(bar.open) for bar in bar_list],
                        'high': [float(bar.high) for bar in bar_list],
                        'low': [float(bar.low) for bar in bar_list],
                        'close': [float(bar.close) for bar in bar_list],
                        'volume': [int(bar.volume) for bar in bar_list],
                        'trade_count': [bar.trade_count if bar.trade_count else 0 for bar in bar_list],
                        'vwap': [float(bar.vwap) if bar.vwap else 0.0 for bar in bar_list]
                    }
                    
                    df = pd.DataFrame(data)
                    df.set_index('timestamp', inplace=True)
                    
                    logger.debug(f"Retrieved {len(df)} bars for {symbol}")
                    return df
                else:
                    logger.warning(f"No bars returned for {symbol}")
                    return pd.DataFrame()
                    
            except APIError as e:
                if "SIP data unavailable" in str(e) or "feed" in str(e).lower():
                    logger.debug(f"📊 {symbol} SIP data unavailable, using free IEX data")
                    # Already using IEX, so this shouldn't happen
                    return pd.DataFrame()
                else:
                    raise e
                    
        except Exception as e:
            logger.error(f"❌ Error getting bars for {symbol}: {e}")
            return pd.DataFrame()

    def get_latest_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get latest quote data for symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with quote data or None
        """
        try:
            request = StockQuotesRequest(
                symbol_or_symbols=[symbol],
                feed='iex'
            )
            
            quotes = self.data_client.get_stock_quotes(request)
            
            if symbol in quotes.data and quotes.data[symbol]:
                quote = quotes.data[symbol][-1]  # Get latest quote
                
                return {
                    'symbol': symbol,
                    'timestamp': quote.timestamp.isoformat(),
                    'bid': float(quote.bid_price),
                    'ask': float(quote.ask_price),
                    'bid_size': int(quote.bid_size),
                    'ask_size': int(quote.ask_size)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting quote for {symbol}: {e}")
            return None

    def get_latest_trade(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get latest trade data for symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with trade data or None
        """
        try:
            request = StockTradesRequest(
                symbol_or_symbols=[symbol],
                feed='iex'
            )
            
            trades = self.data_client.get_stock_trades(request)
            
            if symbol in trades.data and trades.data[symbol]:
                trade = trades.data[symbol][-1]  # Get latest trade
                
                return {
                    'symbol': symbol,
                    'timestamp': trade.timestamp.isoformat(),
                    'price': float(trade.price),
                    'size': int(trade.size)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting trade for {symbol}: {e}")
            return None

    def get_news(
        self, 
        symbols: List[str], 
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get news articles for symbols
        
        Args:
            symbols: List of symbols
            start: Start date
            end: End date  
            limit: Maximum number of articles
            
        Returns:
            List of news articles
        """
        try:
            if start is None:
                start = datetime.now() - timedelta(days=7)
            if end is None:
                end = datetime.now()
                
            request = NewsRequest(
                symbols=symbols,
                start=start,
                end=end,
                limit=limit
            )
            
            news = self.data_client.get_news(request)
            
            articles = []
            for article in news.data:
                articles.append({
                    'id': article.id,
                    'headline': article.headline,
                    'summary': article.summary,
                    'author': article.author,
                    'created_at': article.created_at.isoformat(),
                    'updated_at': article.updated_at.isoformat() if article.updated_at else None,
                    'url': article.url,
                    'symbols': article.symbols if article.symbols else []
                })
            
            return articles
            
        except Exception as e:
            logger.error(f"❌ Error getting news: {e}")
            return []

    def get_clock(self) -> Dict[str, Any]:
        """
        Get market clock information
        
        Returns:
            Dictionary with market timing info
        """
        try:
            clock = self.trading_client.get_clock()
            
            return {
                'timestamp': clock.timestamp.isoformat(),
                'is_open': clock.is_open,
                'next_open': clock.next_open.isoformat(),
                'next_close': clock.next_close.isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting market clock: {e}")
            return {}

    def is_market_open(self) -> bool:
        """Check if market is currently open"""
        try:
            clock = self.trading_client.get_clock()
            return clock.is_open
        except Exception:
            return False

    def get_market_status(self) -> Dict[str, Any]:
        """
        Get comprehensive market status with user-friendly information
        
        Returns:
            Dictionary with detailed market status including:
            - is_open: Boolean market status
            - status_text: Human-readable status
            - current_time: Current timestamp
            - next_open: Next market open time
            - next_close: Next market close time
            - time_until_event: Time until next open/close
            - trading_day: Whether today is a trading day
        """
        try:
            clock = self.trading_client.get_clock()
            
            from datetime import datetime, timezone
            
            current_time = clock.timestamp
            is_open = clock.is_open
            next_open = clock.next_open
            next_close = clock.next_close
            
            # Calculate time until next event
            if is_open:
                next_event = next_close
                event_name = "close"
            else:
                next_event = next_open
                event_name = "open"
            
            # Calculate time difference
            time_diff = next_event - current_time
            hours = int(time_diff.total_seconds() // 3600)
            minutes = int((time_diff.total_seconds() % 3600) // 60)
            
            # Format time until
            if time_diff.days > 0:
                if time_diff.days == 1:
                    time_until = f"{time_diff.days} day, {hours % 24} hours"
                else:
                    time_until = f"{time_diff.days} days, {hours % 24} hours"
            elif hours > 0:
                time_until = f"{hours} hours, {minutes} minutes"
            else:
                time_until = f"{minutes} minutes"
            
            # Determine status text
            if is_open:
                status_text = "🟢 OPEN"
                status_message = f"Market is open. Closes in {time_until}"
            else:
                status_text = "🔴 CLOSED"
                # Check if it's weekend/holiday (more than 1 day)
                if time_diff.days > 0:
                    day_name = next_open.strftime('%A')
                    status_message = f"Market is closed. Opens {day_name} at {next_open.strftime('%I:%M %p ET')} (in {time_until})"
                else:
                    status_message = f"Market is closed. Opens today at {next_open.strftime('%I:%M %p ET')} (in {time_until})"
            
            return {
                'is_open': is_open,
                'status_text': status_text,
                'status_message': status_message,
                'current_time': current_time.isoformat(),
                'next_open': next_open.isoformat(),
                'next_close': next_close.isoformat(),
                'next_event': event_name,
                'time_until': time_until,
                'time_diff_seconds': int(time_diff.total_seconds()),
                'trading_hours': '9:30 AM - 4:00 PM ET (Mon-Fri)'
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting market status: {e}")
            return {
                'is_open': False,
                'status_text': '⚠️ UNKNOWN',
                'status_message': 'Unable to determine market status',
                'error': str(e)
            }

    def get_orders(self, status: str = 'open') -> List[Dict[str, Any]]:
        """
        Get orders by status
        
        Args:
            status: Order status ('open', 'closed', 'all')
            
        Returns:
            List of order dictionaries
        """
        try:
            # Convert status string to enum
            if status == 'open':
                order_status = OrderStatus.OPEN
            elif status == 'closed':
                order_status = OrderStatus.CLOSED
            else:
                order_status = None  # Get all orders
            
            request = GetOrdersRequest(
                status=order_status,
                limit=500
            )
            
            orders = self.trading_client.get_orders(request)
            
            result = []
            for order in orders:
                result.append({
                    'id': order.id,
                    'client_order_id': order.client_order_id,
                    'created_at': order.created_at.isoformat(),
                    'updated_at': order.updated_at.isoformat() if order.updated_at else None,
                    'submitted_at': order.submitted_at.isoformat() if order.submitted_at else None,
                    'filled_at': order.filled_at.isoformat() if order.filled_at else None,
                    'expired_at': order.expired_at.isoformat() if order.expired_at else None,
                    'canceled_at': order.canceled_at.isoformat() if order.canceled_at else None,
                    'failed_at': order.failed_at.isoformat() if order.failed_at else None,
                    'asset_id': order.asset_id,
                    'symbol': order.symbol,
                    'asset_class': order.asset_class.value,
                    'qty': float(order.qty) if order.qty else 0.0,
                    'filled_qty': float(order.filled_qty) if order.filled_qty else 0.0,
                    'type': order.order_type.value,
                    'side': order.side.value,
                    'time_in_force': order.time_in_force.value,
                    'limit_price': float(order.limit_price) if order.limit_price else None,
                    'stop_price': float(order.stop_price) if order.stop_price else None,
                    'status': order.status.value,
                    'extended_hours': order.extended_hours if hasattr(order, 'extended_hours') else False
                })
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error getting orders: {e}")
            return []

    def get_account_summary(self) -> str:
        """
        Get formatted account summary
        
        Returns:
            Human-readable account summary
        """
        try:
            account = self.get_account()
            positions = self.get_positions()
            
            summary = []
            summary.append(f"🏦 Account: {account.get('account_number', 'Unknown')}")
            summary.append(f"💰 Portfolio Value: ${account.get('portfolio_value', 0):,.2f}")
            summary.append(f"💵 Cash: ${account.get('cash', 0):,.2f}")
            summary.append(f"💳 Buying Power: ${account.get('buying_power', 0):,.2f}")
            
            if positions:
                summary.append(f"📊 Positions: {len(positions)}")
                for pos in positions[:5]:  # Show first 5
                    pnl = pos.get('unrealized_pl', 0)
                    pnl_sign = "+" if pnl >= 0 else ""
                    summary.append(f"  • {pos['symbol']}: {pos['qty']} shares ({pnl_sign}${pnl:.2f})")
            else:
                summary.append("📊 Positions: None")
            
            summary.append(f"📈 Status: {account.get('status', 'Unknown')}")
            summary.append("🔒 Mode: Paper Trading (Safe)")
            
            return "\n".join(summary)
            
        except Exception as e:
            return f"❌ Error getting account summary: {e}"


# Global client instance for singleton pattern
_alpaca_client = None

def get_client() -> AlpacaClient:
    """
    Get singleton Alpaca client instance
    
    Returns:
        AlpacaClient instance
    """
    global _alpaca_client
    if _alpaca_client is None:
        _alpaca_client = AlpacaClient()
    return _alpaca_client