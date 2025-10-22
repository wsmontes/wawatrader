"""
Backtesting Framework

Simulate trading strategy on historical data to evaluate performance
BEFORE risking real money.

Key Features:
- Walk-forward simulation (point-in-time data only)
- Realistic order fills (no lookahead bias)
- Transaction costs (commissions + slippage)
- Performance metrics (return, Sharpe, drawdown, win rate)
- Benchmark comparison (buy-and-hold)

Architecture:
1. Load historical data for all symbols
2. Simulate day-by-day trading decisions
3. Track positions, P&L, trades
4. Calculate performance metrics
5. Generate comparison report
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from pathlib import Path
import json
from loguru import logger

from wawatrader.alpaca_client import get_client
from wawatrader.indicators import analyze_dataframe, get_latest_signals
from wawatrader.llm_bridge import LLMBridge
from wawatrader.risk_manager import RiskManager
from config.settings import settings


@dataclass
class Trade:
    """Record of a completed trade"""
    entry_date: datetime
    exit_date: datetime
    symbol: str
    side: str  # "buy" or "sell"
    shares: int
    entry_price: float
    exit_price: float
    pnl: float
    pnl_pct: float
    commission: float
    duration_days: int
    reasoning: str
    confidence: float


@dataclass
class BacktestStats:
    """Performance statistics for a backtest"""
    # Returns
    total_return: float
    annualized_return: float
    benchmark_return: float
    alpha: float  # Excess return vs benchmark
    
    # Risk metrics
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_duration: int
    volatility: float
    
    # Trading stats
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float  # Total wins / Total losses
    
    # Position stats
    avg_trade_duration: float
    max_position_size: float
    avg_position_size: float
    
    # Cost analysis
    total_commissions: float
    total_slippage: float
    
    # Time period
    start_date: datetime
    end_date: datetime
    trading_days: int
    
    # Final values
    starting_capital: float
    ending_capital: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['start_date'] = self.start_date.isoformat()
        result['end_date'] = self.end_date.isoformat()
        return result


class Backtester:
    """
    Backtest trading strategy on historical data.
    
    This simulates the TradingAgent's decisions on past data to see
    how the strategy would have performed.
    
    CRITICAL: Uses point-in-time data only (no lookahead bias)
    """
    
    def __init__(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        initial_capital: float = 100000,
        commission_per_share: float = 0.0,  # Alpaca has $0 commissions
        slippage_pct: float = 0.001  # 0.1% slippage per trade
    ):
        """
        Initialize backtester.
        
        Args:
            symbols: List of stock symbols to backtest
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            initial_capital: Starting account value
            commission_per_share: Commission per share (default $0 for Alpaca)
            slippage_pct: Slippage as percentage of price
        """
        self.symbols = symbols
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        self.initial_capital = initial_capital
        self.commission_per_share = commission_per_share
        self.slippage_pct = slippage_pct
        
        # Initialize components
        self.alpaca = get_client()
        self.llm_bridge = LLMBridge()
        self.risk_manager = RiskManager()
        
        # Backtest state
        self.cash = initial_capital
        self.positions: Dict[str, int] = {}  # symbol -> shares
        self.position_prices: Dict[str, float] = {}  # symbol -> avg entry price
        self.trades: List[Trade] = []
        self.daily_values: List[Tuple[datetime, float]] = []
        self.daily_returns: List[float] = []
        
        # Historical data cache
        self.data_cache: Dict[str, pd.DataFrame] = {}
        
        # Configuration
        self.min_confidence = settings.trading.min_confidence
        self.lookback_bars = 90  # Bars needed for indicators
        
        logger.info(f"Backtester initialized")
        logger.info(f"  Symbols: {', '.join(symbols)}")
        logger.info(f"  Period: {start_date} to {end_date}")
        logger.info(f"  Initial capital: ${initial_capital:,.2f}")
        logger.info(f"  Commission: ${commission_per_share}/share")
        logger.info(f"  Slippage: {slippage_pct*100:.2f}%")
    
    def load_historical_data(self):
        """Load historical price data for all symbols"""
        logger.info("Loading historical data...")
        
        # Add buffer for indicators (need data before start_date)
        buffer_days = 120
        fetch_start = self.start_date - timedelta(days=buffer_days)
        
        for symbol in self.symbols:
            try:
                logger.info(f"  Fetching {symbol}...")
                
                # Get bars from Alpaca
                bars = self.alpaca.get_bars(
                    symbol=symbol,
                    start=fetch_start.strftime("%Y-%m-%d"),
                    end=self.end_date.strftime("%Y-%m-%d"),
                    timeframe="1Day"
                )
                
                if bars.empty:
                    logger.warning(f"  No data for {symbol}")
                    continue
                
                # Ensure datetime index
                if 'timestamp' in bars.columns:
                    bars['timestamp'] = pd.to_datetime(bars['timestamp'])
                    bars.set_index('timestamp', inplace=True)
                
                self.data_cache[symbol] = bars
                logger.info(f"  {symbol}: {len(bars)} bars loaded")
                
            except Exception as e:
                logger.error(f"  Failed to load {symbol}: {e}")
                continue
        
        logger.info(f"Data loaded for {len(self.data_cache)} symbols")
    
    def get_data_at_date(self, symbol: str, current_date: datetime) -> pd.DataFrame:
        """
        Get point-in-time data (no lookahead bias).
        
        Args:
            symbol: Stock symbol
            current_date: Current simulation date
        
        Returns:
            DataFrame with data up to (but not including) current_date
        """
        if symbol not in self.data_cache:
            return pd.DataFrame()
        
        df = self.data_cache[symbol]
        
        # Only include data BEFORE current_date (point-in-time)
        mask = df.index < current_date
        return df[mask].copy()
    
    def calculate_portfolio_value(self, current_date: datetime) -> float:
        """
        Calculate total portfolio value at a given date.
        
        Args:
            current_date: Date to calculate value at
        
        Returns:
            Total portfolio value (cash + positions)
        """
        total_value = self.cash
        
        for symbol, shares in self.positions.items():
            if shares == 0:
                continue
            
            # Get current price
            df = self.get_data_at_date(symbol, current_date + timedelta(days=1))
            if df.empty:
                # Use last known price
                price = self.position_prices.get(symbol, 0)
            else:
                price = df.iloc[-1]['close']
            
            total_value += shares * price
        
        return total_value
    
    def execute_trade(
        self,
        symbol: str,
        side: str,
        shares: int,
        price: float,
        current_date: datetime,
        reasoning: str,
        confidence: float
    ) -> bool:
        """
        Execute a simulated trade.
        
        Args:
            symbol: Stock symbol
            side: "buy" or "sell"
            shares: Number of shares
            price: Current price
            current_date: Trade date
            reasoning: LLM reasoning
            confidence: Confidence level
        
        Returns:
            True if trade executed, False if insufficient funds/shares
        """
        # Apply slippage
        if side == "buy":
            execution_price = price * (1 + self.slippage_pct)
        else:
            execution_price = price * (1 - self.slippage_pct)
        
        # Calculate costs
        commission = shares * self.commission_per_share
        
        if side == "buy":
            total_cost = (shares * execution_price) + commission
            
            # Check if we have enough cash
            if total_cost > self.cash:
                logger.warning(f"  Insufficient cash: need ${total_cost:,.2f}, have ${self.cash:,.2f}")
                return False
            
            # Execute buy
            self.cash -= total_cost
            self.positions[symbol] = self.positions.get(symbol, 0) + shares
            
            # Track entry price (weighted average)
            current_shares = self.positions[symbol] - shares
            if current_shares > 0:
                old_price = self.position_prices.get(symbol, 0)
                avg_price = (old_price * current_shares + execution_price * shares) / self.positions[symbol]
                self.position_prices[symbol] = avg_price
            else:
                self.position_prices[symbol] = execution_price
            
            logger.info(f"  BUY {shares} {symbol} @ ${execution_price:.2f} (cost: ${total_cost:,.2f})")
            
        else:  # sell
            # Check if we have enough shares
            current_shares = self.positions.get(symbol, 0)
            if shares > current_shares:
                logger.warning(f"  Insufficient shares: need {shares}, have {current_shares}")
                return False
            
            # Execute sell
            total_proceeds = (shares * execution_price) - commission
            self.cash += total_proceeds
            self.positions[symbol] -= shares
            
            # Record completed trade
            entry_price = self.position_prices.get(symbol, 0)
            pnl = (execution_price - entry_price) * shares - commission
            pnl_pct = ((execution_price - entry_price) / entry_price) * 100
            
            trade = Trade(
                entry_date=current_date,  # Simplified - would need actual entry date
                exit_date=current_date,
                symbol=symbol,
                side=side,
                shares=shares,
                entry_price=entry_price,
                exit_price=execution_price,
                pnl=pnl,
                pnl_pct=pnl_pct,
                commission=commission,
                duration_days=0,  # Simplified
                reasoning=reasoning,
                confidence=confidence
            )
            self.trades.append(trade)
            
            logger.info(f"  SELL {shares} {symbol} @ ${execution_price:.2f} (P&L: ${pnl:+,.2f})")
            
            # Clean up if position closed
            if self.positions[symbol] == 0:
                del self.positions[symbol]
                if symbol in self.position_prices:
                    del self.position_prices[symbol]
        
        return True
    
    def make_trading_decision(
        self,
        symbol: str,
        current_date: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        Make a trading decision for a symbol at a given date.
        
        This simulates the TradingAgent's decision process using
        only point-in-time data.
        
        Args:
            symbol: Stock symbol
            current_date: Current simulation date
        
        Returns:
            Decision dict or None
        """
        # Get point-in-time data
        df = self.get_data_at_date(symbol, current_date)
        
        if df.empty or len(df) < self.lookback_bars:
            return None
        
        # Calculate indicators (using only past data)
        df = analyze_dataframe(df)
        signals = get_latest_signals(df)
        
        if not signals:
            return None
        
        # Get LLM analysis
        llm_result = self.llm_bridge.analyze_market_data(
            symbol=symbol,
            signals=signals,
            current_price=df.iloc[-1]['close']
        )
        
        if not llm_result:
            return None
        
        # Extract decision
        action = llm_result.get('action', 'hold').lower()
        confidence = llm_result.get('confidence', 0)
        reasoning = llm_result.get('reasoning', 'No reasoning provided')
        
        # Check confidence threshold
        if confidence < self.min_confidence:
            return None
        
        # Only consider buy/sell
        if action not in ['buy', 'sell']:
            return None
        
        # Get current price and account value
        current_price = df.iloc[-1]['close']
        account_value = self.calculate_portfolio_value(current_date)
        
        # Calculate position size (simplified - use risk manager logic)
        max_position_value = account_value * settings.risk.max_position_size
        shares = int(max_position_value / current_price)
        
        if shares == 0:
            return None
        
        # Risk check
        risk_result = self.risk_manager.check_trade(
            symbol=symbol,
            side=action,
            shares=shares,
            price=current_price,
            account_value=account_value,
            current_positions=self.positions,
            position_prices=self.position_prices
        )
        
        if not risk_result.approved:
            logger.debug(f"  Risk rejected: {risk_result.reason}")
            return None
        
        # Adjust shares if risk manager limited them
        if risk_result.max_shares is not None:
            shares = min(shares, risk_result.max_shares)
        
        return {
            'action': action,
            'shares': shares,
            'price': current_price,
            'confidence': confidence,
            'reasoning': reasoning
        }
    
    def run(self) -> BacktestStats:
        """
        Run the backtest simulation.
        
        Returns:
            BacktestStats with performance metrics
        """
        logger.info("Starting backtest simulation...")
        
        # Load all data
        self.load_historical_data()
        
        if not self.data_cache:
            raise ValueError("No historical data loaded")
        
        # Get trading days (use first symbol as reference)
        reference_symbol = list(self.data_cache.keys())[0]
        trading_days = self.data_cache[reference_symbol].index
        trading_days = trading_days[(trading_days >= self.start_date) & (trading_days <= self.end_date)]
        
        logger.info(f"Simulating {len(trading_days)} trading days...")
        
        # Simulate day by day
        for current_date in trading_days:
            # Track daily portfolio value
            portfolio_value = self.calculate_portfolio_value(current_date)
            self.daily_values.append((current_date, portfolio_value))
            
            # Calculate daily return
            if len(self.daily_values) > 1:
                prev_value = self.daily_values[-2][1]
                daily_return = (portfolio_value - prev_value) / prev_value
                self.daily_returns.append(daily_return)
            
            # Make trading decisions for each symbol
            for symbol in self.symbols:
                try:
                    decision = self.make_trading_decision(symbol, current_date)
                    
                    if decision:
                        self.execute_trade(
                            symbol=symbol,
                            side=decision['action'],
                            shares=decision['shares'],
                            price=decision['price'],
                            current_date=current_date,
                            reasoning=decision['reasoning'],
                            confidence=decision['confidence']
                        )
                except Exception as e:
                    logger.error(f"Error processing {symbol} on {current_date}: {e}")
                    continue
        
        # Calculate final statistics
        stats = self.calculate_statistics()
        
        logger.info("Backtest complete!")
        logger.info(f"  Total return: {stats.total_return*100:+.2f}%")
        logger.info(f"  Sharpe ratio: {stats.sharpe_ratio:.2f}")
        logger.info(f"  Max drawdown: {stats.max_drawdown*100:.2f}%")
        logger.info(f"  Total trades: {stats.total_trades}")
        logger.info(f"  Win rate: {stats.win_rate*100:.1f}%")
        
        return stats
    
    def calculate_statistics(self) -> BacktestStats:
        """Calculate comprehensive performance statistics"""
        
        # Basic values
        ending_capital = self.calculate_portfolio_value(self.end_date)
        total_return = (ending_capital - self.initial_capital) / self.initial_capital
        
        # Calculate benchmark (buy-and-hold first symbol)
        benchmark_return = self.calculate_benchmark_return()
        alpha = total_return - benchmark_return
        
        # Time metrics
        trading_days = len(self.daily_values)
        years = (self.end_date - self.start_date).days / 365.25
        annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        
        # Risk metrics
        returns_array = np.array(self.daily_returns)
        volatility = np.std(returns_array) * np.sqrt(252) if len(returns_array) > 0 else 0
        
        # Sharpe ratio (assuming 0% risk-free rate)
        sharpe_ratio = (annualized_return / volatility) if volatility > 0 else 0
        
        # Drawdown analysis
        max_dd, max_dd_duration = self.calculate_max_drawdown()
        
        # Trading statistics
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl <= 0]
        
        win_rate = len(winning_trades) / len(self.trades) if self.trades else 0
        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0
        
        total_wins = sum(t.pnl for t in winning_trades)
        total_losses = abs(sum(t.pnl for t in losing_trades))
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Position statistics
        avg_trade_duration = np.mean([t.duration_days for t in self.trades]) if self.trades else 0
        
        # Cost analysis
        total_commissions = sum(t.commission for t in self.trades)
        total_slippage = sum(abs(t.pnl) * self.slippage_pct for t in self.trades)
        
        return BacktestStats(
            total_return=total_return,
            annualized_return=annualized_return,
            benchmark_return=benchmark_return,
            alpha=alpha,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_dd,
            max_drawdown_duration=max_dd_duration,
            volatility=volatility,
            total_trades=len(self.trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            avg_trade_duration=avg_trade_duration,
            max_position_size=settings.risk.max_position_size,
            avg_position_size=settings.risk.max_position_size,  # Simplified
            total_commissions=total_commissions,
            total_slippage=total_slippage,
            start_date=self.start_date,
            end_date=self.end_date,
            trading_days=trading_days,
            starting_capital=self.initial_capital,
            ending_capital=ending_capital
        )
    
    def calculate_benchmark_return(self) -> float:
        """Calculate buy-and-hold return for first symbol"""
        if not self.symbols or not self.data_cache:
            return 0.0
        
        symbol = self.symbols[0]
        if symbol not in self.data_cache:
            return 0.0
        
        df = self.data_cache[symbol]
        
        # Get prices at start and end dates
        start_mask = df.index >= self.start_date
        end_mask = df.index <= self.end_date
        
        start_price = df[start_mask].iloc[0]['close'] if any(start_mask) else 0
        end_price = df[end_mask].iloc[-1]['close'] if any(end_mask) else 0
        
        if start_price == 0:
            return 0.0
        
        return (end_price - start_price) / start_price
    
    def calculate_max_drawdown(self) -> Tuple[float, int]:
        """
        Calculate maximum drawdown and duration.
        
        Returns:
            (max_drawdown, duration_in_days)
        """
        if not self.daily_values:
            return 0.0, 0
        
        values = [v for _, v in self.daily_values]
        peak = values[0]
        max_dd = 0
        max_dd_duration = 0
        current_dd_duration = 0
        
        for value in values:
            if value > peak:
                peak = value
                current_dd_duration = 0
            else:
                drawdown = (peak - value) / peak
                max_dd = max(max_dd, drawdown)
                current_dd_duration += 1
                max_dd_duration = max(max_dd_duration, current_dd_duration)
        
        return max_dd, max_dd_duration
    
    def save_results(self, output_dir: str = "backtest_results"):
        """
        Save backtest results to files.
        
        Args:
            output_dir: Directory to save results
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Save trades
        trades_file = output_path / f"trades_{self.start_date.strftime('%Y%m%d')}_{self.end_date.strftime('%Y%m%d')}.json"
        with open(trades_file, 'w') as f:
            trades_data = [asdict(t) for t in self.trades]
            # Convert datetime to string
            for trade in trades_data:
                trade['entry_date'] = trade['entry_date'].isoformat()
                trade['exit_date'] = trade['exit_date'].isoformat()
            json.dump(trades_data, f, indent=2)
        
        logger.info(f"Saved {len(self.trades)} trades to {trades_file}")
        
        # Save daily values
        daily_file = output_path / f"daily_values_{self.start_date.strftime('%Y%m%d')}_{self.end_date.strftime('%Y%m%d')}.csv"
        daily_df = pd.DataFrame(self.daily_values, columns=['date', 'portfolio_value'])
        daily_df.to_csv(daily_file, index=False)
        
        logger.info(f"Saved daily values to {daily_file}")
    
    def generate_report(self, stats: BacktestStats) -> str:
        """
        Generate a formatted text report.
        
        Args:
            stats: BacktestStats object
        
        Returns:
            Formatted report string
        """
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║                    BACKTEST RESULTS                          ║
╚══════════════════════════════════════════════════════════════╝

Period: {stats.start_date.strftime('%Y-%m-%d')} to {stats.end_date.strftime('%Y-%m-%d')} ({stats.trading_days} days)
Symbols: {', '.join(self.symbols)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RETURNS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Starting Capital:        ${stats.starting_capital:>15,.2f}
Ending Capital:          ${stats.ending_capital:>15,.2f}
Total Return:            {stats.total_return*100:>15.2f}%
Annualized Return:       {stats.annualized_return*100:>15.2f}%
Benchmark Return:        {stats.benchmark_return*100:>15.2f}%
Alpha (vs Benchmark):    {stats.alpha*100:>15.2f}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RISK METRICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sharpe Ratio:            {stats.sharpe_ratio:>15.2f}
Max Drawdown:            {stats.max_drawdown*100:>15.2f}%
Drawdown Duration:       {stats.max_drawdown_duration:>15} days
Volatility (Annual):     {stats.volatility*100:>15.2f}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TRADING STATISTICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Trades:            {stats.total_trades:>15}
Winning Trades:          {stats.winning_trades:>15}
Losing Trades:           {stats.losing_trades:>15}
Win Rate:                {stats.win_rate*100:>15.1f}%
Average Win:             ${stats.avg_win:>15.2f}
Average Loss:            ${stats.avg_loss:>15.2f}
Profit Factor:           {stats.profit_factor:>15.2f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COSTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Commissions:       ${stats.total_commissions:>15.2f}
Total Slippage:          ${stats.total_slippage:>15.2f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return report
