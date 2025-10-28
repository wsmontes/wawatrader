"""
Replay Trading Day from Logs

This script reads logged market data, decisions, and order executions 
to replay and analyze trading days. Useful for:

1. Strategy evaluation - Compare decisions against actual outcomes
2. Configuration testing - Test different settings with historical data
3. Decision analysis - Review what the LLM decided vs market movement
4. Performance metrics - Calculate actual vs potential returns

Usage:
    python scripts/replay_trading_day.py --date 2024-10-27
    python scripts/replay_trading_day.py --date 2024-10-27 --symbol AAPL
    python scripts/replay_trading_day.py --compare-config alternate_config.yaml
"""

import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any
import pandas as pd
from loguru import logger

from config import settings


class TradingDayReplay:
    """Replay and analyze a trading day from logs"""
    
    def __init__(self, date: str):
        """
        Initialize replay for specific date
        
        Args:
            date: Date string (YYYY-MM-DD)
        """
        self.date = datetime.strptime(date, '%Y-%m-%d')
        self.log_dir = settings.project_root / "logs"
        
        # Log files
        self.market_data_log = self.log_dir / "market_data.jsonl"
        self.decisions_log = self.log_dir / "decisions.jsonl"
        self.order_log = self.log_dir / "order_executions.jsonl"
        self.account_log = self.log_dir / "account_snapshots.jsonl"
        self.position_log = self.log_dir / "position_snapshots.jsonl"
        
        # Loaded data
        self.market_data = []
        self.decisions = []
        self.orders = []
        self.account_snapshots = []
        self.position_snapshots = []
        
    def load_logs(self, symbol: str = None):
        """Load all log data for the replay date"""
        logger.info(f"Loading logs for {self.date.date()}...")
        
        # Load market data
        if self.market_data_log.exists():
            with open(self.market_data_log, 'r') as f:
                for line in f:
                    entry = json.loads(line)
                    ts = datetime.fromisoformat(entry['timestamp'])
                    if ts.date() == self.date.date():
                        if symbol is None or entry.get('symbol') == symbol:
                            self.market_data.append(entry)
        
        # Load decisions
        if self.decisions_log.exists():
            with open(self.decisions_log, 'r') as f:
                for line in f:
                    entry = json.loads(line)
                    ts = datetime.fromisoformat(entry['timestamp'])
                    if ts.date() == self.date.date():
                        if symbol is None or entry.get('symbol') == symbol:
                            self.decisions.append(entry)
        
        # Load orders
        if self.order_log.exists():
            with open(self.order_log, 'r') as f:
                for line in f:
                    entry = json.loads(line)
                    ts = datetime.fromisoformat(entry['timestamp'])
                    if ts.date() == self.date.date():
                        if symbol is None or entry.get('symbol') == symbol:
                            self.orders.append(entry)
        
        # Load account snapshots
        if self.account_log.exists():
            with open(self.account_log, 'r') as f:
                for line in f:
                    entry = json.loads(line)
                    ts = datetime.fromisoformat(entry['timestamp'])
                    if ts.date() == self.date.date():
                        self.account_snapshots.append(entry)
        
        # Load position snapshots
        if self.position_log.exists():
            with open(self.position_log, 'r') as f:
                for line in f:
                    entry = json.loads(line)
                    ts = datetime.fromisoformat(entry['timestamp'])
                    if ts.date() == self.date.date():
                        if symbol is None or entry.get('symbol') == symbol:
                            self.position_snapshots.append(entry)
        
        logger.info(f"✅ Loaded:")
        logger.info(f"   - {len(self.market_data)} market data entries")
        logger.info(f"   - {len(self.decisions)} decisions")
        logger.info(f"   - {len(self.orders)} order events")
        logger.info(f"   - {len(self.account_snapshots)} account snapshots")
        logger.info(f"   - {len(self.position_snapshots)} position snapshots")
    
    def analyze_decisions(self):
        """Analyze trading decisions vs market movement"""
        logger.info("\n📊 Decision Analysis:")
        
        for decision in self.decisions:
            symbol = decision.get('symbol')
            action = decision.get('action')
            timestamp = decision['timestamp']
            
            # Find corresponding market data
            market_entries = [m for m in self.market_data 
                            if m.get('symbol') == symbol 
                            and m['timestamp'] <= timestamp]
            
            if market_entries:
                latest_market = market_entries[-1]
                price_at_decision = latest_market.get('latest_close', 0)
                
                # Find subsequent market data to see outcome
                future_entries = [m for m in self.market_data 
                                if m.get('symbol') == symbol 
                                and m['timestamp'] > timestamp]
                
                if future_entries:
                    # Check price movement 1 hour and 4 hours later
                    decision_time = datetime.fromisoformat(timestamp)
                    
                    one_hour_later = [m for m in future_entries 
                                     if datetime.fromisoformat(m['timestamp']) 
                                     <= decision_time + timedelta(hours=1)]
                    
                    if one_hour_later:
                        later_price = one_hour_later[-1].get('latest_close', 0)
                        price_change_pct = ((later_price - price_at_decision) / price_at_decision) * 100
                        
                        outcome = "✅" if (action == 'buy' and price_change_pct > 0) or (action == 'sell' and price_change_pct < 0) else "❌"
                        
                        logger.info(f"{outcome} {timestamp[:19]} | {symbol} {action.upper()} @ ${price_at_decision:.2f}")
                        logger.info(f"   1hr later: ${later_price:.2f} ({price_change_pct:+.2f}%)")
                        
                        # Show LLM reasoning
                        if 'reasoning' in decision:
                            logger.info(f"   Reasoning: {decision['reasoning'][:100]}...")
    
    def calculate_performance(self):
        """Calculate trading performance metrics"""
        logger.info("\n📈 Performance Metrics:")
        
        if not self.account_snapshots:
            logger.warning("No account snapshots available")
            return
        
        # First and last account values
        first_snapshot = self.account_snapshots[0]
        last_snapshot = self.account_snapshots[-1]
        
        start_value = first_snapshot['data']['portfolio_value']
        end_value = last_snapshot['data']['portfolio_value']
        
        pnl = end_value - start_value
        pnl_pct = (pnl / start_value) * 100
        
        logger.info(f"Start Value: ${start_value:,.2f}")
        logger.info(f"End Value: ${end_value:,.2f}")
        logger.info(f"P&L: ${pnl:,.2f} ({pnl_pct:+.2f}%)")
        
        # Count trades
        filled_orders = [o for o in self.orders if o.get('event') == 'order_filled']
        logger.info(f"Total Trades: {len(filled_orders)}")
        
        # Calculate win rate
        if filled_orders:
            # Group buys and sells
            buys = {o['order_data']['symbol']: o for o in filled_orders 
                   if o['order_data']['side'] == 'buy'}
            sells = {o['order_data']['symbol']: o for o in filled_orders 
                    if o['order_data']['side'] == 'sell'}
            
            wins = 0
            losses = 0
            
            for symbol, sell in sells.items():
                if symbol in buys:
                    buy_price = buys[symbol]['filled_price']
                    sell_price = sell['filled_price']
                    if sell_price > buy_price:
                        wins += 1
                    else:
                        losses += 1
            
            if wins + losses > 0:
                win_rate = (wins / (wins + losses)) * 100
                logger.info(f"Win Rate: {win_rate:.1f}% ({wins}W / {losses}L)")
    
    def export_replay_csv(self, output_path: str = None):
        """Export replay data to CSV for further analysis"""
        if output_path is None:
            output_path = self.log_dir / f"replay_{self.date.date()}.csv"
        
        # Combine all data into timeline
        timeline = []
        
        for entry in self.market_data:
            timeline.append({
                'timestamp': entry['timestamp'],
                'type': 'market_data',
                'symbol': entry.get('symbol'),
                'price': entry.get('latest_close'),
                'data': json.dumps(entry)
            })
        
        for entry in self.decisions:
            timeline.append({
                'timestamp': entry['timestamp'],
                'type': 'decision',
                'symbol': entry.get('symbol'),
                'action': entry.get('action'),
                'data': json.dumps(entry)
            })
        
        for entry in self.orders:
            timeline.append({
                'timestamp': entry['timestamp'],
                'type': 'order',
                'symbol': entry.get('symbol'),
                'data': json.dumps(entry)
            })
        
        # Sort by timestamp
        timeline.sort(key=lambda x: x['timestamp'])
        
        # Create DataFrame and save
        df = pd.DataFrame(timeline)
        df.to_csv(output_path, index=False)
        
        logger.info(f"✅ Exported replay data to {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Replay and analyze trading day from logs')
    parser.add_argument('--date', required=True, help='Date to replay (YYYY-MM-DD)')
    parser.add_argument('--symbol', help='Filter by specific symbol')
    parser.add_argument('--export', action='store_true', help='Export to CSV')
    
    args = parser.parse_args()
    
    # Create replay
    replay = TradingDayReplay(args.date)
    
    # Load logs
    replay.load_logs(symbol=args.symbol)
    
    # Analyze
    replay.analyze_decisions()
    replay.calculate_performance()
    
    # Export if requested
    if args.export:
        replay.export_replay_csv()


if __name__ == "__main__":
    main()
