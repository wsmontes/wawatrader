"""
Real-time Log Viewer

Monitor trading system logs in real-time with filtering and formatting.
Useful for watching system behavior during paper trading.

Usage:
    python scripts/view_logs.py                    # All events
    python scripts/view_logs.py --type market     # Just market data
    python scripts/view_logs.py --symbol AAPL     # Specific symbol
    python scripts/view_logs.py --follow          # Tail mode (like tail -f)
"""

import json
import argparse
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from loguru import logger

from config.settings import settings


class LogViewer:
    """View and filter trading system logs"""
    
    LOG_FILES = {
        'market': 'market_data.jsonl',
        'account': 'account_snapshots.jsonl',
        'position': 'position_snapshots.jsonl',
        'order': 'order_executions.jsonl',
        'decision': 'decisions.jsonl'
    }
    
    def __init__(self):
        self.log_dir = settings.project_root / "logs"
    
    def format_entry(self, entry: Dict[str, Any], log_type: str) -> str:
        """Format log entry for display"""
        ts = entry.get('timestamp', 'N/A')
        event = entry.get('event', 'N/A')
        
        if log_type == 'market':
            symbol = entry.get('symbol', 'N/A')
            close = entry.get('latest_close', 0)
            volume = entry.get('latest_volume', 0)
            return f"[{ts[:19]}] 📊 {symbol} @ ${close:.2f} (vol: {volume:,})"
        
        elif log_type == 'account':
            value = entry.get('data', {}).get('portfolio_value', 0)
            cash = entry.get('data', {}).get('cash', 0)
            bp = entry.get('data', {}).get('buying_power', 0)
            return f"[{ts[:19]}] 💰 Portfolio: ${value:,.2f} | Cash: ${cash:,.2f} | BP: ${bp:,.2f}"
        
        elif log_type == 'position':
            if event == 'positions_fetch':
                count = entry.get('count', 0)
                positions = entry.get('positions', [])
                lines = [f"[{ts[:19]}] 📍 {count} positions:"]
                for pos in positions:
                    pnl_pct = pos.get('unrealized_plpc', 0) * 100
                    lines.append(f"   {pos['symbol']}: {pos['qty']} @ ${pos['current_price']:.2f} ({pnl_pct:+.2f}%)")
                return '\n'.join(lines)
            else:
                symbol = entry.get('symbol', 'N/A')
                data = entry.get('data', {})
                pnl_pct = data.get('unrealized_plpc', 0) * 100
                return f"[{ts[:19]}] 📍 {symbol}: {data.get('qty')} @ ${data.get('current_price', 0):.2f} ({pnl_pct:+.2f}%)"
        
        elif log_type == 'order':
            symbol = entry.get('symbol', 'N/A')
            if event == 'order_submitted':
                side = entry.get('side', 'N/A')
                qty = entry.get('qty', 0)
                return f"[{ts[:19]}] 📤 ORDER: {side.upper()} {qty} {symbol}"
            elif event == 'order_filled':
                price = entry.get('filled_price', 0)
                qty = entry.get('filled_qty', 0)
                wait = entry.get('wait_time_seconds', 0)
                return f"[{ts[:19]}] ✅ FILLED: {qty} {symbol} @ ${price:.2f} ({wait:.2f}s)"
            elif event == 'order_failed':
                error = entry.get('error', 'Unknown')
                return f"[{ts[:19]}] ❌ FAILED: {symbol} - {error}"
            elif event == 'order_timeout':
                return f"[{ts[:19]}] ⏰ TIMEOUT: {entry.get('order_id', 'N/A')[:8]}..."
        
        elif log_type == 'decision':
            symbol = entry.get('symbol', 'N/A')
            action = entry.get('action', 'N/A')
            shares = entry.get('shares', 0)
            confidence = entry.get('confidence', 0)
            reasoning = entry.get('reasoning', '')[:80]
            return f"[{ts[:19]}] 🧠 {symbol} {action.upper()} {shares} shares (conf: {confidence}%)\n   {reasoning}..."
        
        return f"[{ts[:19]}] {event}: {json.dumps(entry, indent=2)}"
    
    def view(self, log_type: str = None, symbol: str = None, follow: bool = False, limit: int = None):
        """
        View logs with optional filtering
        
        Args:
            log_type: Type of log ('market', 'account', 'position', 'order', 'decision')
            symbol: Filter by symbol
            follow: Tail mode (continuously watch for new entries)
            limit: Show only last N entries
        """
        # Determine which log files to read
        if log_type and log_type in self.LOG_FILES:
            log_files = {log_type: self.LOG_FILES[log_type]}
        else:
            log_files = self.LOG_FILES
        
        if follow:
            print("📺 Watching logs (Ctrl+C to stop)...\n")
            self._follow_logs(log_files, symbol)
        else:
            self._read_logs(log_files, symbol, limit)
    
    def _read_logs(self, log_files: Dict[str, str], symbol: str = None, limit: int = None):
        """Read and display log files"""
        entries = []
        
        for log_type, filename in log_files.items():
            log_path = self.log_dir / filename
            
            if not log_path.exists():
                continue
            
            with open(log_path, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        
                        # Filter by symbol if specified
                        if symbol and entry.get('symbol') != symbol:
                            # Also check in nested data
                            if 'positions' in entry:
                                # Filter positions array
                                entry['positions'] = [p for p in entry['positions'] 
                                                     if p.get('symbol') == symbol]
                                if not entry['positions']:
                                    continue
                            elif 'order_data' in entry:
                                if entry.get('order_data', {}).get('symbol') != symbol:
                                    continue
                            else:
                                continue
                        
                        entries.append((entry, log_type))
                    except json.JSONDecodeError:
                        continue
        
        # Sort by timestamp
        entries.sort(key=lambda x: x[0].get('timestamp', ''))
        
        # Apply limit if specified
        if limit:
            entries = entries[-limit:]
        
        # Display
        for entry, log_type in entries:
            print(self.format_entry(entry, log_type))
            print()
    
    def _follow_logs(self, log_files: Dict[str, str], symbol: str = None):
        """Tail log files continuously"""
        # Track file positions
        positions = {}
        
        for log_type, filename in log_files.items():
            log_path = self.log_dir / filename
            if log_path.exists():
                # Start at end of file
                positions[log_type] = {
                    'path': log_path,
                    'position': log_path.stat().st_size
                }
        
        try:
            while True:
                for log_type, info in positions.items():
                    log_path = info['path']
                    
                    # Check if file has new data
                    current_size = log_path.stat().st_size
                    
                    if current_size > info['position']:
                        # Read new entries
                        with open(log_path, 'r') as f:
                            f.seek(info['position'])
                            
                            for line in f:
                                try:
                                    entry = json.loads(line)
                                    
                                    # Filter by symbol
                                    if symbol and entry.get('symbol') != symbol:
                                        continue
                                    
                                    print(self.format_entry(entry, log_type))
                                    print()
                                except json.JSONDecodeError:
                                    continue
                            
                            info['position'] = f.tell()
                
                time.sleep(0.5)  # Check every 500ms
        
        except KeyboardInterrupt:
            print("\n👋 Stopped watching logs")


def main():
    parser = argparse.ArgumentParser(description='View trading system logs')
    parser.add_argument('--type', choices=['market', 'account', 'position', 'order', 'decision'],
                       help='Type of log to view')
    parser.add_argument('--symbol', help='Filter by symbol')
    parser.add_argument('--follow', '-f', action='store_true', 
                       help='Follow log file (like tail -f)')
    parser.add_argument('--limit', '-n', type=int, 
                       help='Show last N entries only')
    
    args = parser.parse_args()
    
    viewer = LogViewer()
    viewer.view(
        log_type=args.type,
        symbol=args.symbol,
        follow=args.follow,
        limit=args.limit
    )


if __name__ == "__main__":
    main()
