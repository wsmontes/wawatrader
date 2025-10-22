"""
Database Manager

Persistent storage for WawaTrader using SQLite.

Stores:
- Trade history (executed orders)
- Trading decisions (all decisions, executed or not)
- LLM interactions (prompts and responses)
- Performance metrics (daily snapshots)
- Account snapshots (portfolio value over time)

Features:
- Automatic schema creation
- Migration support
- Query helpers
- Data export (CSV, JSON)
- Performance analytics
"""

import sqlite3
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
import json
from loguru import logger


@dataclass
class Trade:
    """Record of an executed trade"""
    trade_id: Optional[int] = None
    timestamp: Optional[str] = None
    symbol: str = ""
    side: str = ""  # "buy" or "sell"
    quantity: int = 0
    price: float = 0.0
    total_value: float = 0.0
    commission: float = 0.0
    order_id: Optional[str] = None
    status: str = "filled"
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.total_value == 0:
            self.total_value = self.quantity * self.price


@dataclass
class TradingDecision:
    """Record of a trading decision (executed or not)"""
    decision_id: Optional[int] = None
    timestamp: Optional[str] = None
    symbol: str = ""
    action: str = ""  # "buy", "sell", "hold"
    shares: int = 0
    price: float = 0.0
    confidence: float = 0.0
    sentiment: str = ""
    reasoning: str = ""
    risk_approved: bool = False
    risk_reason: str = ""
    executed: bool = False
    execution_error: Optional[str] = None
    
    # Context
    indicators_json: Optional[str] = None
    llm_analysis_json: Optional[str] = None
    account_value: Optional[float] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class LLMInteraction:
    """Record of an LLM API call"""
    interaction_id: Optional[int] = None
    timestamp: Optional[str] = None
    symbol: str = ""
    prompt: str = ""
    response: str = ""
    model: str = ""
    confidence: Optional[float] = None
    action: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class PerformanceSnapshot:
    """Daily performance snapshot"""
    snapshot_id: Optional[int] = None
    date: Optional[str] = None
    portfolio_value: float = 0.0
    cash: float = 0.0
    positions_value: float = 0.0
    daily_pnl: float = 0.0
    daily_pnl_pct: float = 0.0
    total_return: float = 0.0
    num_positions: int = 0
    num_trades_today: int = 0
    
    def __post_init__(self):
        if self.date is None:
            self.date = date.today().isoformat()


class DatabaseManager:
    """
    Manage all database operations for WawaTrader.
    
    Uses SQLite for simplicity and portability.
    All data is stored in a single database file.
    """
    
    def __init__(self, db_path: str = "wawatrader.db"):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None
        
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Connect and initialize
        self.connect()
        self.create_tables()
        
        logger.info(f"Database initialized: {self.db_path}")
    
    def connect(self):
        """Connect to database"""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Return rows as dicts
        logger.debug(f"Connected to database: {self.db_path}")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.debug("Database connection closed")
    
    def create_tables(self):
        """Create all database tables"""
        
        # Trades table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                total_value REAL NOT NULL,
                commission REAL DEFAULT 0.0,
                order_id TEXT,
                status TEXT DEFAULT 'filled',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Trading decisions table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                shares INTEGER NOT NULL,
                price REAL NOT NULL,
                confidence REAL NOT NULL,
                sentiment TEXT,
                reasoning TEXT,
                risk_approved INTEGER NOT NULL,
                risk_reason TEXT,
                executed INTEGER NOT NULL,
                execution_error TEXT,
                indicators_json TEXT,
                llm_analysis_json TEXT,
                account_value REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # LLM interactions table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS llm_interactions (
                interaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                prompt TEXT NOT NULL,
                response TEXT NOT NULL,
                model TEXT NOT NULL,
                confidence REAL,
                action TEXT,
                success INTEGER NOT NULL,
                error_message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Performance snapshots table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS performance_snapshots (
                snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                portfolio_value REAL NOT NULL,
                cash REAL NOT NULL,
                positions_value REAL NOT NULL,
                daily_pnl REAL NOT NULL,
                daily_pnl_pct REAL NOT NULL,
                total_return REAL NOT NULL,
                num_positions INTEGER NOT NULL,
                num_trades_today INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for better query performance
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_decisions_symbol ON decisions(symbol)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_decisions_timestamp ON decisions(timestamp)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_symbol ON llm_interactions(symbol)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_performance_date ON performance_snapshots(date)")
        
        self.conn.commit()
        logger.debug("Database tables created/verified")
    
    # ==================== TRADES ====================
    
    def add_trade(self, trade: Trade) -> int:
        """
        Add a trade record.
        
        Args:
            trade: Trade object
        
        Returns:
            trade_id of inserted record
        """
        cursor = self.conn.execute("""
            INSERT INTO trades (
                timestamp, symbol, side, quantity, price, 
                total_value, commission, order_id, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade.timestamp,
            trade.symbol,
            trade.side,
            trade.quantity,
            trade.price,
            trade.total_value,
            trade.commission,
            trade.order_id,
            trade.status
        ))
        
        self.conn.commit()
        trade_id = cursor.lastrowid
        
        logger.info(f"Trade recorded: {trade.side.upper()} {trade.quantity} {trade.symbol} @ ${trade.price:.2f}")
        return trade_id
    
    def get_trades(
        self,
        symbol: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get trade history with optional filters.
        
        Args:
            symbol: Filter by symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            limit: Maximum number of records
        
        Returns:
            List of trade dictionaries
        """
        query = "SELECT * FROM trades WHERE 1=1"
        params = []
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
        
        query += " ORDER BY timestamp DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor = self.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_trade_summary(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Get summary statistics for trades.
        
        Args:
            symbol: Filter by symbol (optional)
        
        Returns:
            Dictionary with trade statistics
        """
        where_clause = f"WHERE symbol = '{symbol}'" if symbol else ""
        
        query = f"""
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN side = 'buy' THEN quantity ELSE 0 END) as total_bought,
                SUM(CASE WHEN side = 'sell' THEN quantity ELSE 0 END) as total_sold,
                SUM(total_value) as total_volume,
                AVG(price) as avg_price,
                SUM(commission) as total_commissions
            FROM trades
            {where_clause}
        """
        
        cursor = self.conn.execute(query)
        row = cursor.fetchone()
        return dict(row) if row else {}
    
    # ==================== DECISIONS ====================
    
    def add_decision(self, decision: TradingDecision) -> int:
        """
        Add a trading decision record.
        
        Args:
            decision: TradingDecision object
        
        Returns:
            decision_id of inserted record
        """
        cursor = self.conn.execute("""
            INSERT INTO decisions (
                timestamp, symbol, action, shares, price,
                confidence, sentiment, reasoning,
                risk_approved, risk_reason, executed, execution_error,
                indicators_json, llm_analysis_json, account_value
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            decision.timestamp,
            decision.symbol,
            decision.action,
            decision.shares,
            decision.price,
            decision.confidence,
            decision.sentiment,
            decision.reasoning,
            1 if decision.risk_approved else 0,
            decision.risk_reason,
            1 if decision.executed else 0,
            decision.execution_error,
            decision.indicators_json,
            decision.llm_analysis_json,
            decision.account_value
        ))
        
        self.conn.commit()
        decision_id = cursor.lastrowid
        
        logger.info(f"Decision recorded: {decision.action.upper()} {decision.symbol} (executed: {decision.executed})")
        return decision_id
    
    def get_decisions(
        self,
        symbol: Optional[str] = None,
        executed_only: bool = False,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get decision history.
        
        Args:
            symbol: Filter by symbol
            executed_only: Only return executed decisions
            limit: Maximum number of records
        
        Returns:
            List of decision dictionaries
        """
        query = "SELECT * FROM decisions WHERE 1=1"
        params = []
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        
        if executed_only:
            query += " AND executed = 1"
        
        query += " ORDER BY timestamp DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor = self.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    # ==================== LLM INTERACTIONS ====================
    
    def add_llm_interaction(self, interaction: LLMInteraction) -> int:
        """
        Add an LLM interaction record.
        
        Args:
            interaction: LLMInteraction object
        
        Returns:
            interaction_id of inserted record
        """
        cursor = self.conn.execute("""
            INSERT INTO llm_interactions (
                timestamp, symbol, prompt, response, model,
                confidence, action, success, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            interaction.timestamp,
            interaction.symbol,
            interaction.prompt,
            interaction.response,
            interaction.model,
            interaction.confidence,
            interaction.action,
            1 if interaction.success else 0,
            interaction.error_message
        ))
        
        self.conn.commit()
        interaction_id = cursor.lastrowid
        
        logger.debug(f"LLM interaction recorded: {interaction.symbol} (success: {interaction.success})")
        return interaction_id
    
    def get_llm_interactions(
        self,
        symbol: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get LLM interaction history.
        
        Args:
            symbol: Filter by symbol
            limit: Maximum number of records
        
        Returns:
            List of interaction dictionaries
        """
        query = "SELECT * FROM llm_interactions WHERE 1=1"
        params = []
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        
        query += " ORDER BY timestamp DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor = self.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    # ==================== PERFORMANCE SNAPSHOTS ====================
    
    def add_performance_snapshot(self, snapshot: PerformanceSnapshot) -> int:
        """
        Add a performance snapshot (upsert - update if date exists).
        
        Args:
            snapshot: PerformanceSnapshot object
        
        Returns:
            snapshot_id of inserted/updated record
        """
        cursor = self.conn.execute("""
            INSERT OR REPLACE INTO performance_snapshots (
                date, portfolio_value, cash, positions_value,
                daily_pnl, daily_pnl_pct, total_return,
                num_positions, num_trades_today
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            snapshot.date,
            snapshot.portfolio_value,
            snapshot.cash,
            snapshot.positions_value,
            snapshot.daily_pnl,
            snapshot.daily_pnl_pct,
            snapshot.total_return,
            snapshot.num_positions,
            snapshot.num_trades_today
        ))
        
        self.conn.commit()
        snapshot_id = cursor.lastrowid
        
        logger.debug(f"Performance snapshot saved: {snapshot.date} (${snapshot.portfolio_value:,.2f})")
        return snapshot_id
    
    def get_performance_snapshots(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get performance snapshots.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            limit: Maximum number of records
        
        Returns:
            List of snapshot dictionaries
        """
        query = "SELECT * FROM performance_snapshots WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        query += " ORDER BY date DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor = self.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    # ==================== ANALYTICS ====================
    
    def get_win_rate(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculate win rate from executed decisions.
        
        Args:
            symbol: Filter by symbol (optional)
        
        Returns:
            Dictionary with win rate statistics
        """
        where_clause = f"AND symbol = '{symbol}'" if symbol else ""
        
        # This is simplified - in reality, need to match buy/sell pairs
        query = f"""
            SELECT 
                COUNT(*) as total_decisions,
                SUM(CASE WHEN executed = 1 THEN 1 ELSE 0 END) as executed_count,
                SUM(CASE WHEN risk_approved = 1 THEN 1 ELSE 0 END) as approved_count,
                SUM(CASE WHEN action = 'buy' THEN 1 ELSE 0 END) as buy_signals,
                SUM(CASE WHEN action = 'sell' THEN 1 ELSE 0 END) as sell_signals,
                SUM(CASE WHEN action = 'hold' THEN 1 ELSE 0 END) as hold_signals,
                AVG(confidence) as avg_confidence
            FROM decisions
            WHERE 1=1 {where_clause}
        """
        
        cursor = self.conn.execute(query)
        row = cursor.fetchone()
        return dict(row) if row else {}
    
    def get_daily_stats(self, date_str: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics for a specific day.
        
        Args:
            date_str: Date (YYYY-MM-DD), defaults to today
        
        Returns:
            Dictionary with daily statistics
        """
        if date_str is None:
            date_str = date.today().isoformat()
        
        # Get trades for the day (timestamp starts with date)
        query = "SELECT COUNT(*) FROM trades WHERE timestamp LIKE ?"
        cursor = self.conn.execute(query, (f"{date_str}%",))
        num_trades = cursor.fetchone()[0]
        
        # Get decisions for the day
        query = "SELECT COUNT(*) FROM decisions WHERE timestamp LIKE ?"
        cursor = self.conn.execute(query, (f"{date_str}%",))
        num_decisions = cursor.fetchone()[0]
        
        # Get performance snapshot
        snapshots = self.get_performance_snapshots(start_date=date_str, end_date=date_str)
        snapshot = snapshots[0] if snapshots else None
        
        return {
            'date': date_str,
            'num_trades': num_trades,
            'num_decisions': num_decisions,
            'snapshot': snapshot
        }
    
    # ==================== DATA EXPORT ====================
    
    def export_to_csv(self, table: str, output_path: str):
        """
        Export table to CSV.
        
        Args:
            table: Table name (trades, decisions, etc.)
            output_path: Output CSV file path
        """
        import csv
        
        cursor = self.conn.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        
        if not rows:
            logger.warning(f"No data to export from {table}")
            return
        
        # Get column names
        columns = [description[0] for description in cursor.description]
        
        # Write CSV
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)
        
        logger.info(f"Exported {len(rows)} rows from {table} to {output_path}")
    
    def export_to_json(self, table: str, output_path: str):
        """
        Export table to JSON.
        
        Args:
            table: Table name
            output_path: Output JSON file path
        """
        cursor = self.conn.execute(f"SELECT * FROM {table}")
        rows = [dict(row) for row in cursor.fetchall()]
        
        with open(output_path, 'w') as f:
            json.dump(rows, f, indent=2)
        
        logger.info(f"Exported {len(rows)} rows from {table} to {output_path}")
    
    # ==================== UTILITIES ====================
    
    def get_table_stats(self) -> Dict[str, int]:
        """
        Get row counts for all tables.
        
        Returns:
            Dictionary with table names and row counts
        """
        tables = ['trades', 'decisions', 'llm_interactions', 'performance_snapshots']
        stats = {}
        
        for table in tables:
            cursor = self.conn.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cursor.fetchone()[0]
        
        return stats
    
    def vacuum(self):
        """Optimize database (reclaim space, rebuild indexes)"""
        self.conn.execute("VACUUM")
        logger.info("Database optimized")
    
    def clear_all_data(self):
        """Clear all data from all tables (use with caution!)"""
        tables = ['trades', 'decisions', 'llm_interactions', 'performance_snapshots']
        
        for table in tables:
            self.conn.execute(f"DELETE FROM {table}")
        
        self.conn.commit()
        logger.warning("All data cleared from database")


# Singleton instance
_db_instance: Optional[DatabaseManager] = None


def get_database(db_path: str = "wawatrader.db") -> DatabaseManager:
    """
    Get database manager singleton instance.
    
    Args:
        db_path: Path to database file
    
    Returns:
        DatabaseManager instance
    """
    global _db_instance
    
    if _db_instance is None:
        _db_instance = DatabaseManager(db_path)
    
    return _db_instance
