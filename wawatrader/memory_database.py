"""
Trading Memory Database

Persistent storage for all trading decisions, outcomes, patterns, and lessons.
This is the long-term memory that enables continuous learning.

Author: WawaTrader Team
Date: October 23, 2025
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from loguru import logger
import pandas as pd
import numpy as np


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"Type {type(obj)} not serializable")


class TradingMemory:
    """
    Persistent memory database for trading decisions and learning.
    
    Stores:
    - Every trading decision with full context
    - Actual outcomes (P&L, duration, etc.)
    - Discovered patterns
    - Learned lessons
    - Strategy performance metrics
    """
    
    def __init__(self, db_path: str = "trading_data/memory/trading_memory.db"):
        """
        Initialize trading memory database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
        logger.info(f"🧠 Trading memory initialized: {self.db_path}")
    
    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Trading decisions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trading_decisions (
                    id TEXT PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    price REAL NOT NULL,
                    shares INTEGER NOT NULL,
                    position_value REAL NOT NULL,
                    
                    -- Market Context (JSON)
                    market_regime TEXT,
                    market_context JSON,
                    
                    -- Technical Indicators (JSON)
                    technical_indicators JSON,
                    
                    -- LLM Analysis
                    llm_sentiment TEXT,
                    llm_confidence REAL,
                    llm_reasoning TEXT,
                    
                    -- Decision Making
                    decision_confidence REAL,
                    decision_reasoning TEXT,
                    
                    -- Outcome (updated later)
                    outcome TEXT,
                    profit_loss REAL,
                    profit_loss_percent REAL,
                    held_duration_minutes INTEGER,
                    exit_price REAL,
                    exit_timestamp TIMESTAMP,
                    
                    -- Learning
                    was_correct BOOLEAN,
                    lesson_learned TEXT,
                    pattern_matched TEXT,
                    
                    -- Metadata
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Market patterns table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_patterns (
                    id TEXT PRIMARY KEY,
                    pattern_name TEXT NOT NULL,
                    pattern_type TEXT NOT NULL,
                    conditions JSON NOT NULL,
                    
                    -- Performance
                    success_rate REAL NOT NULL,
                    avg_return REAL NOT NULL,
                    avg_return_percent REAL NOT NULL,
                    sample_size INTEGER NOT NULL,
                    
                    -- Risk
                    win_rate REAL NOT NULL,
                    avg_win REAL NOT NULL,
                    avg_loss REAL NOT NULL,
                    risk_reward_ratio REAL NOT NULL,
                    
                    -- Metadata
                    discovered_date TIMESTAMP NOT NULL,
                    last_updated TIMESTAMP NOT NULL,
                    times_used INTEGER DEFAULT 0,
                    active BOOLEAN DEFAULT 1
                )
            """)
            
            # Daily performance table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_performance (
                    date DATE PRIMARY KEY,
                    
                    -- Trading Stats
                    total_trades INTEGER NOT NULL,
                    winning_trades INTEGER NOT NULL,
                    losing_trades INTEGER NOT NULL,
                    neutral_trades INTEGER NOT NULL,
                    
                    -- P&L
                    total_pnl REAL NOT NULL,
                    total_pnl_percent REAL NOT NULL,
                    best_trade REAL NOT NULL,
                    worst_trade REAL NOT NULL,
                    
                    -- Performance Metrics
                    win_rate REAL NOT NULL,
                    avg_win REAL NOT NULL,
                    avg_loss REAL NOT NULL,
                    risk_reward_ratio REAL NOT NULL,
                    
                    -- Market Context
                    market_regime TEXT,
                    dominant_pattern TEXT,
                    
                    -- Learning
                    lessons_learned JSON,
                    best_indicator TEXT,
                    worst_indicator TEXT,
                    
                    -- Metadata
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Learned lessons table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS learned_lessons (
                    id TEXT PRIMARY KEY,
                    lesson_text TEXT NOT NULL,
                    lesson_type TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    sample_size INTEGER NOT NULL,
                    
                    -- Context
                    applies_to TEXT,
                    market_regime TEXT,
                    conditions JSON,
                    
                    -- Performance
                    impact_on_pnl REAL,
                    times_applied INTEGER DEFAULT 0,
                    
                    -- Metadata
                    learned_date TIMESTAMP NOT NULL,
                    last_applied TIMESTAMP,
                    active BOOLEAN DEFAULT 1
                )
            """)
            
            # Strategy parameters table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategy_parameters (
                    parameter_name TEXT PRIMARY KEY,
                    parameter_value TEXT NOT NULL,
                    parameter_type TEXT NOT NULL,
                    
                    -- History
                    previous_value TEXT,
                    change_reason TEXT,
                    
                    -- Performance
                    performance_before REAL,
                    performance_after REAL,
                    
                    -- Metadata
                    last_updated TIMESTAMP NOT NULL
                )
            """)
            
            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_decisions_timestamp ON trading_decisions(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_decisions_symbol ON trading_decisions(symbol)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_decisions_outcome ON trading_decisions(outcome)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_patterns_success_rate ON market_patterns(success_rate DESC)")
            
            conn.commit()
            logger.info("✅ Database schema initialized")
    
    def record_decision(self, decision: Dict[str, Any]) -> str:
        """
        Record a trading decision with full context.
        
        Args:
            decision: Dictionary containing decision details
            
        Returns:
            Decision ID
        """
        try:
            decision_id = f"{decision['timestamp'].strftime('%Y%m%d%H%M%S%f')}_{decision['symbol']}"
            
            # Convert market_context dict to JSON, handling datetime objects
            market_context = decision.get('market_context', {})
            if isinstance(market_context, dict) and 'timestamp' in market_context:
                # Convert datetime to ISO format string
                market_context = market_context.copy()
                if isinstance(market_context['timestamp'], datetime):
                    market_context['timestamp'] = market_context['timestamp'].isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO trading_decisions (
                        id, timestamp, symbol, action, price, shares, position_value,
                        market_regime, market_context, technical_indicators,
                        llm_sentiment, llm_confidence, llm_reasoning,
                        decision_confidence, decision_reasoning, pattern_matched
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    decision_id,
                    decision['timestamp'],
                    decision['symbol'],
                    decision['action'],
                    decision['price'],
                    decision.get('shares', 0),
                    decision.get('position_value', 0),
                    decision.get('market_regime'),
                    json.dumps(market_context, default=json_serial),
                    json.dumps(decision.get('technical_indicators', {}), default=json_serial),
                    decision.get('llm_sentiment'),
                    decision.get('llm_confidence'),
                    decision.get('llm_reasoning'),
                    decision.get('decision_confidence'),
                    decision.get('decision_reasoning'),
                    decision.get('pattern_matched')
                ))
                
                conn.commit()
            
            logger.info(f"💾 Decision recorded: {decision_id}")
            return decision_id
            
        except Exception as e:
            logger.error(f"❌ Error recording decision: {e}")
            raise
    
    def update_decision_outcome(self, decision_id: str, outcome: Dict[str, Any]):
        """
        Update a decision with its actual outcome.
        
        Args:
            decision_id: ID of the decision
            outcome: Dictionary containing outcome details
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE trading_decisions
                    SET outcome = ?,
                        profit_loss = ?,
                        profit_loss_percent = ?,
                        held_duration_minutes = ?,
                        exit_price = ?,
                        exit_timestamp = ?,
                        was_correct = ?,
                        lesson_learned = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    outcome.get('outcome'),
                    outcome.get('profit_loss'),
                    outcome.get('profit_loss_percent'),
                    outcome.get('held_duration_minutes'),
                    outcome.get('exit_price'),
                    outcome.get('exit_timestamp'),
                    outcome.get('was_correct'),
                    outcome.get('lesson_learned'),
                    decision_id
                ))
                
                conn.commit()
            
            logger.info(f"✅ Outcome updated for decision: {decision_id}")
            
        except Exception as e:
            logger.error(f"❌ Error updating outcome: {e}")
            raise
    
    def save_pattern(self, pattern: Dict[str, Any]) -> str:
        """
        Save a discovered pattern.
        
        Args:
            pattern: Dictionary containing pattern details
            
        Returns:
            Pattern ID
        """
        try:
            pattern_id = f"{pattern['pattern_name']}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO market_patterns (
                        id, pattern_name, pattern_type, conditions,
                        success_rate, avg_return, avg_return_percent, sample_size,
                        win_rate, avg_win, avg_loss, risk_reward_ratio,
                        discovered_date, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pattern_id,
                    pattern['pattern_name'],
                    pattern['pattern_type'],
                    json.dumps(pattern['conditions']),
                    pattern['success_rate'],
                    pattern['avg_return'],
                    pattern['avg_return_percent'],
                    pattern['sample_size'],
                    pattern['win_rate'],
                    pattern['avg_win'],
                    pattern['avg_loss'],
                    pattern['risk_reward_ratio'],
                    datetime.now(),
                    datetime.now()
                ))
                
                conn.commit()
            
            logger.info(f"📚 Pattern saved: {pattern_id}")
            return pattern_id
            
        except Exception as e:
            logger.error(f"❌ Error saving pattern: {e}")
            raise
    
    def get_patterns(self, min_success_rate: float = 0.6, min_sample_size: int = 5) -> List[Dict]:
        """
        Get active patterns above threshold.
        
        Args:
            min_success_rate: Minimum success rate
            min_sample_size: Minimum number of samples
            
        Returns:
            List of patterns
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM market_patterns
                    WHERE active = 1
                      AND success_rate >= ?
                      AND sample_size >= ?
                    ORDER BY success_rate DESC
                """, (min_success_rate, min_sample_size))
                
                columns = [desc[0] for desc in cursor.description]
                patterns = []
                
                for row in cursor.fetchall():
                    pattern = dict(zip(columns, row))
                    pattern['conditions'] = json.loads(pattern['conditions'])
                    patterns.append(pattern)
                
                return patterns
                
        except Exception as e:
            logger.error(f"❌ Error getting patterns: {e}")
            return []
    
    def save_daily_performance(self, date: datetime, performance: Dict[str, Any]):
        """
        Save daily performance summary.
        
        Args:
            date: Date
            performance: Performance dictionary
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO daily_performance (
                        date, total_trades, winning_trades, losing_trades, neutral_trades,
                        total_pnl, total_pnl_percent, best_trade, worst_trade,
                        win_rate, avg_win, avg_loss, risk_reward_ratio,
                        market_regime, dominant_pattern, lessons_learned,
                        best_indicator, worst_indicator
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    date.date(),
                    performance['total_trades'],
                    performance['winning_trades'],
                    performance['losing_trades'],
                    performance['neutral_trades'],
                    performance['total_pnl'],
                    performance['total_pnl_percent'],
                    performance['best_trade'],
                    performance['worst_trade'],
                    performance['win_rate'],
                    performance['avg_win'],
                    performance['avg_loss'],
                    performance['risk_reward_ratio'],
                    performance.get('market_regime'),
                    performance.get('dominant_pattern'),
                    json.dumps(performance.get('lessons_learned', [])),
                    performance.get('best_indicator'),
                    performance.get('worst_indicator')
                ))
                
                conn.commit()
            
            logger.info(f"📊 Daily performance saved for {date.date()}")
            
        except Exception as e:
            logger.error(f"❌ Error saving daily performance: {e}")
            raise
    
    def get_recent_decisions(self, days: int = 7, symbol: Optional[str] = None) -> pd.DataFrame:
        """
        Get recent decisions as DataFrame.
        
        Args:
            days: Number of days to look back
            symbol: Optional symbol filter
            
        Returns:
            DataFrame of decisions
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = f"""
                    SELECT * FROM trading_decisions
                    WHERE timestamp >= datetime('now', '-{days} days')
                """
                
                if symbol:
                    query += f" AND symbol = '{symbol}'"
                
                query += " ORDER BY timestamp DESC"
                
                df = pd.read_sql_query(query, conn)
                
                # Parse JSON columns
                if not df.empty:
                    df['market_context'] = df['market_context'].apply(
                        lambda x: json.loads(x) if x else {}
                    )
                    df['technical_indicators'] = df['technical_indicators'].apply(
                        lambda x: json.loads(x) if x else {}
                    )
                
                return df
                
        except Exception as e:
            logger.error(f"❌ Error getting recent decisions: {e}")
            return pd.DataFrame()
    
    def get_performance_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get performance statistics over period.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Performance statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get trading stats
                cursor.execute(f"""
                    SELECT 
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
                        SUM(CASE WHEN outcome = 'loss' THEN 1 ELSE 0 END) as losses,
                        SUM(profit_loss) as total_pnl,
                        AVG(CASE WHEN outcome = 'win' THEN profit_loss END) as avg_win,
                        AVG(CASE WHEN outcome = 'loss' THEN profit_loss END) as avg_loss,
                        MAX(profit_loss) as best_trade,
                        MIN(profit_loss) as worst_trade
                    FROM trading_decisions
                    WHERE timestamp >= datetime('now', '-{days} days')
                      AND outcome IS NOT NULL
                """)
                
                row = cursor.fetchone()
                
                if row and row[0] > 0:
                    total_trades, wins, losses, total_pnl, avg_win, avg_loss, best, worst = row
                    
                    win_rate = (wins / total_trades) if total_trades > 0 else 0
                    risk_reward = abs(avg_win / avg_loss) if avg_loss and avg_loss != 0 else 0
                    
                    return {
                        'total_trades': total_trades,
                        'winning_trades': wins,
                        'losing_trades': losses,
                        'win_rate': win_rate,
                        'total_pnl': total_pnl or 0,
                        'avg_win': avg_win or 0,
                        'avg_loss': avg_loss or 0,
                        'risk_reward_ratio': risk_reward,
                        'best_trade': best or 0,
                        'worst_trade': worst or 0
                    }
                else:
                    return self._empty_stats()
                    
        except Exception as e:
            logger.error(f"❌ Error getting performance stats: {e}")
            return self._empty_stats()
    
    def _empty_stats(self) -> Dict[str, Any]:
        """Return empty stats structure"""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'total_pnl': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'risk_reward_ratio': 0.0,
            'best_trade': 0.0,
            'worst_trade': 0.0
        }
