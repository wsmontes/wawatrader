"""
Learning Engine - Core Intelligence System

Learns from past trading decisions to continuously improve performance.
This is the "brain" that discovers patterns, optimizes strategies, and builds intelligence.

Author: WawaTrader Team
Date: October 23, 2025
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from loguru import logger
import pandas as pd
import numpy as np

from wawatrader.market_context import MarketContext, MarketContextCapture
from wawatrader.memory_database import TradingMemory


class LearningEngine:
    """
    Core learning system that builds intelligence from trading history.
    
    Responsibilities:
    - Record every decision with full context
    - Analyze what works and what doesn't
    - Discover profitable patterns
    - Optimize strategy parameters
    - Generate insights for tomorrow
    """
    
    def __init__(self, alpaca_client, memory_db: Optional[TradingMemory] = None):
        """
        Initialize learning engine.
        
        Args:
            alpaca_client: Alpaca client for market data
            memory_db: Optional TradingMemory instance
        """
        self.alpaca = alpaca_client
        self.memory = memory_db or TradingMemory()
        self.context_capture = MarketContextCapture(alpaca_client)
        
        logger.info("🧠 Learning engine initialized")
    
    def record_decision(
        self,
        symbol: str,
        action: str,
        price: float,
        shares: int,
        technical_indicators: Dict[str, Any],
        llm_analysis: Dict[str, Any],
        decision_confidence: float,
        decision_reasoning: str,
        pattern_matched: Optional[str] = None
    ) -> str:
        """
        Record a trading decision with full context.
        
        Args:
            symbol: Stock symbol
            action: "BUY", "SELL", "HOLD"
            price: Current price
            shares: Number of shares
            technical_indicators: Technical analysis results
            llm_analysis: LLM analysis results
            decision_confidence: Final decision confidence
            decision_reasoning: Why this decision was made
            pattern_matched: Optional pattern that was matched
            
        Returns:
            Decision ID
        """
        try:
            # Capture current market context
            market_context = self.context_capture.capture_current(symbol)
            
            # Build decision record
            decision = {
                'timestamp': datetime.now(),
                'symbol': symbol,
                'action': action,
                'price': price,
                'shares': shares,
                'position_value': price * shares,
                'market_regime': market_context.regime,
                'market_context': market_context.to_dict(),
                'technical_indicators': technical_indicators,
                'llm_sentiment': llm_analysis.get('sentiment'),
                'llm_confidence': llm_analysis.get('confidence'),
                'llm_reasoning': llm_analysis.get('reasoning'),
                'decision_confidence': decision_confidence,
                'decision_reasoning': decision_reasoning,
                'pattern_matched': pattern_matched
            }
            
            # Store in database
            decision_id = self.memory.record_decision(decision)
            
            logger.info(f"💾 Decision recorded: {symbol} {action} @ ${price:.2f} (ID: {decision_id})")
            
            return decision_id
            
        except Exception as e:
            logger.error(f"❌ Error recording decision: {e}")
            raise
    
    def record_outcome(
        self,
        decision_id: str,
        outcome: str,
        profit_loss: float,
        exit_price: float,
        exit_time: datetime,
        lesson_learned: Optional[str] = None
    ):
        """
        Record the outcome of a decision.
        
        Args:
            decision_id: ID of the original decision
            outcome: "win", "loss", or "neutral"
            profit_loss: Actual P&L
            exit_price: Exit price
            exit_time: Exit time
            lesson_learned: Optional lesson from this trade
        """
        try:
            # Calculate metrics
            decisions_df = self.memory.get_recent_decisions(days=1)
            decision_row = decisions_df[decisions_df['id'] == decision_id]
            
            if decision_row.empty:
                logger.warning(f"⚠️ Decision {decision_id} not found")
                return
            
            entry_time = pd.to_datetime(decision_row['timestamp'].iloc[0])
            entry_price = decision_row['price'].iloc[0]
            
            held_duration = int((exit_time - entry_time).total_seconds() / 60)
            profit_loss_percent = ((exit_price - entry_price) / entry_price) * 100
            
            was_correct = outcome == "win"
            
            # Update outcome
            outcome_data = {
                'outcome': outcome,
                'profit_loss': profit_loss,
                'profit_loss_percent': profit_loss_percent,
                'held_duration_minutes': held_duration,
                'exit_price': exit_price,
                'exit_timestamp': exit_time,
                'was_correct': was_correct,
                'lesson_learned': lesson_learned
            }
            
            self.memory.update_decision_outcome(decision_id, outcome_data)
            
            logger.info(f"✅ Outcome recorded: {decision_id} → {outcome} (${profit_loss:+.2f})")
            
        except Exception as e:
            logger.error(f"❌ Error recording outcome: {e}")
            raise
    
    def analyze_daily_performance(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Analyze trading performance for a specific day.
        
        Args:
            date: Date to analyze (defaults to today)
            
        Returns:
            Performance analysis dictionary
        """
        try:
            if date is None:
                date = datetime.now()
            
            logger.info(f"📊 Analyzing performance for {date.date()}")
            
            # Get today's completed trades
            decisions_df = self.memory.get_recent_decisions(days=1)
            completed = decisions_df[decisions_df['outcome'].notna()]
            
            if completed.empty:
                logger.warning("⚠️ No completed trades to analyze")
                return self._empty_performance()
            
            # Calculate stats
            total_trades = len(completed)
            winning_trades = len(completed[completed['outcome'] == 'win'])
            losing_trades = len(completed[completed['outcome'] == 'loss'])
            neutral_trades = len(completed[completed['outcome'] == 'neutral'])
            
            total_pnl = completed['profit_loss'].sum()
            total_pnl_percent = completed['profit_loss_percent'].sum()
            
            wins = completed[completed['outcome'] == 'win']
            losses = completed[completed['outcome'] == 'loss']
            
            avg_win = wins['profit_loss'].mean() if not wins.empty else 0
            avg_loss = losses['profit_loss'].mean() if not losses.empty else 0
            
            best_trade = completed['profit_loss'].max()
            worst_trade = completed['profit_loss'].min()
            
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            risk_reward = abs(avg_win / avg_loss) if avg_loss != 0 else 0
            
            # Identify dominant market regime
            market_regime = completed['market_regime'].mode()[0] if not completed.empty else 'unknown'
            
            # Identify most common pattern
            patterns = completed['pattern_matched'].dropna()
            dominant_pattern = patterns.mode()[0] if not patterns.empty else None
            
            # Identify best/worst indicators
            # (Would need more sophisticated analysis of indicator performance)
            best_indicator = "RSI"  # Placeholder
            worst_indicator = "None"  # Placeholder
            
            performance = {
                'date': date,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'neutral_trades': neutral_trades,
                'total_pnl': total_pnl,
                'total_pnl_percent': total_pnl_percent,
                'best_trade': best_trade,
                'worst_trade': worst_trade,
                'win_rate': win_rate,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'risk_reward_ratio': risk_reward,
                'market_regime': market_regime,
                'dominant_pattern': dominant_pattern,
                'lessons_learned': self._extract_lessons(completed),
                'best_indicator': best_indicator,
                'worst_indicator': worst_indicator
            }
            
            # Save to database
            self.memory.save_daily_performance(date, performance)
            
            logger.info(f"""
            📊 Daily Performance Summary:
            - Total Trades: {total_trades}
            - Win Rate: {win_rate:.1%}
            - P&L: ${total_pnl:+.2f}
            - Best Trade: ${best_trade:+.2f}
            - Worst Trade: ${worst_trade:+.2f}
            """)
            
            return performance
            
        except Exception as e:
            logger.error(f"❌ Error analyzing daily performance: {e}")
            return self._empty_performance()
    
    def discover_patterns(self, lookback_days: int = 30) -> List[Dict[str, Any]]:
        """
        Discover profitable trading patterns from recent history.
        
        Args:
            lookback_days: Number of days to analyze
            
        Returns:
            List of discovered patterns
        """
        try:
            logger.info(f"🔍 Discovering patterns from last {lookback_days} days...")
            
            # Get recent decisions with outcomes
            decisions_df = self.memory.get_recent_decisions(days=lookback_days)
            completed = decisions_df[decisions_df['outcome'].notna()].copy()
            
            if len(completed) < 10:
                logger.warning("⚠️ Not enough data to discover patterns (need at least 10 trades)")
                return []
            
            patterns = []
            
            # Pattern 1: Time of day analysis
            time_patterns = self._analyze_time_patterns(completed)
            patterns.extend(time_patterns)
            
            # Pattern 2: Market regime analysis
            regime_patterns = self._analyze_regime_patterns(completed)
            patterns.extend(regime_patterns)
            
            # Pattern 3: Confidence level analysis
            confidence_patterns = self._analyze_confidence_patterns(completed)
            patterns.extend(confidence_patterns)
            
            # Pattern 4: Technical setup analysis
            # (Would require more sophisticated analysis of technical indicators)
            
            # Save discovered patterns
            for pattern in patterns:
                if pattern['success_rate'] >= 0.6 and pattern['sample_size'] >= 5:
                    self.memory.save_pattern(pattern)
                    logger.info(f"✅ Pattern discovered: {pattern['pattern_name']} ({pattern['success_rate']:.0%} success)")
            
            return patterns
            
        except Exception as e:
            logger.error(f"❌ Error discovering patterns: {e}")
            return []
    
    def _analyze_time_patterns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Analyze patterns based on time of day"""
        patterns = []
        
        try:
            # Parse market context to get time of day
            df['time_of_day'] = df['market_context'].apply(
                lambda x: x.get('time_of_day', 'unknown') if isinstance(x, dict) else 'unknown'
            )
            
            # Analyze each time period
            for time_period in df['time_of_day'].unique():
                if time_period == 'unknown':
                    continue
                
                subset = df[df['time_of_day'] == time_period]
                
                if len(subset) < 5:
                    continue
                
                wins = len(subset[subset['outcome'] == 'win'])
                total = len(subset)
                success_rate = wins / total
                avg_return = subset['profit_loss'].mean()
                avg_return_pct = subset['profit_loss_percent'].mean()
                
                avg_win = subset[subset['outcome'] == 'win']['profit_loss'].mean()
                avg_loss = subset[subset['outcome'] == 'loss']['profit_loss'].mean()
                risk_reward = abs(avg_win / avg_loss) if avg_loss != 0 else 0
                
                pattern = {
                    'pattern_name': f'time_{time_period}',
                    'pattern_type': 'time_of_day',
                    'conditions': {'time_of_day': time_period},
                    'success_rate': success_rate,
                    'avg_return': avg_return,
                    'avg_return_percent': avg_return_pct,
                    'sample_size': total,
                    'win_rate': success_rate,
                    'avg_win': avg_win if not pd.isna(avg_win) else 0,
                    'avg_loss': avg_loss if not pd.isna(avg_loss) else 0,
                    'risk_reward_ratio': risk_reward
                }
                
                patterns.append(pattern)
        
        except Exception as e:
            logger.warning(f"⚠️ Error analyzing time patterns: {e}")
        
        return patterns
    
    def _analyze_regime_patterns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Analyze patterns based on market regime"""
        patterns = []
        
        try:
            # Analyze each market regime
            for regime in df['market_regime'].unique():
                if pd.isna(regime):
                    continue
                
                subset = df[df['market_regime'] == regime]
                
                if len(subset) < 5:
                    continue
                
                wins = len(subset[subset['outcome'] == 'win'])
                total = len(subset)
                success_rate = wins / total
                avg_return = subset['profit_loss'].mean()
                avg_return_pct = subset['profit_loss_percent'].mean()
                
                avg_win = subset[subset['outcome'] == 'win']['profit_loss'].mean()
                avg_loss = subset[subset['outcome'] == 'loss']['profit_loss'].mean()
                risk_reward = abs(avg_win / avg_loss) if avg_loss != 0 else 0
                
                pattern = {
                    'pattern_name': f'regime_{regime}',
                    'pattern_type': 'market_regime',
                    'conditions': {'market_regime': regime},
                    'success_rate': success_rate,
                    'avg_return': avg_return,
                    'avg_return_percent': avg_return_pct,
                    'sample_size': total,
                    'win_rate': success_rate,
                    'avg_win': avg_win if not pd.isna(avg_win) else 0,
                    'avg_loss': avg_loss if not pd.isna(avg_loss) else 0,
                    'risk_reward_ratio': risk_reward
                }
                
                patterns.append(pattern)
        
        except Exception as e:
            logger.warning(f"⚠️ Error analyzing regime patterns: {e}")
        
        return patterns
    
    def _analyze_confidence_patterns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Analyze patterns based on decision confidence"""
        patterns = []
        
        try:
            # Define confidence buckets
            df['confidence_bucket'] = pd.cut(
                df['decision_confidence'],
                bins=[0, 0.6, 0.8, 1.0],
                labels=['low', 'medium', 'high']
            )
            
            # Analyze each confidence level
            for confidence_level in ['low', 'medium', 'high']:
                subset = df[df['confidence_bucket'] == confidence_level]
                
                if len(subset) < 5:
                    continue
                
                wins = len(subset[subset['outcome'] == 'win'])
                total = len(subset)
                success_rate = wins / total
                avg_return = subset['profit_loss'].mean()
                avg_return_pct = subset['profit_loss_percent'].mean()
                
                avg_win = subset[subset['outcome'] == 'win']['profit_loss'].mean()
                avg_loss = subset[subset['outcome'] == 'loss']['profit_loss'].mean()
                risk_reward = abs(avg_win / avg_loss) if avg_loss != 0 else 0
                
                pattern = {
                    'pattern_name': f'confidence_{confidence_level}',
                    'pattern_type': 'confidence_level',
                    'conditions': {'confidence_level': confidence_level},
                    'success_rate': success_rate,
                    'avg_return': avg_return,
                    'avg_return_percent': avg_return_pct,
                    'sample_size': total,
                    'win_rate': success_rate,
                    'avg_win': avg_win if not pd.isna(avg_win) else 0,
                    'avg_loss': avg_loss if not pd.isna(avg_loss) else 0,
                    'risk_reward_ratio': risk_reward
                }
                
                patterns.append(pattern)
        
        except Exception as e:
            logger.warning(f"⚠️ Error analyzing confidence patterns: {e}")
        
        return patterns
    
    def _extract_lessons(self, df: pd.DataFrame) -> List[str]:
        """Extract lessons from trading data"""
        lessons = []
        
        try:
            # Lesson 1: Best time to trade
            df['time_of_day'] = df['market_context'].apply(
                lambda x: x.get('time_of_day', 'unknown') if isinstance(x, dict) else 'unknown'
            )
            
            time_performance = df.groupby('time_of_day')['outcome'].apply(
                lambda x: (x == 'win').sum() / len(x) if len(x) > 0 else 0
            )
            
            if not time_performance.empty:
                best_time = time_performance.idxmax()
                best_rate = time_performance.max()
                if best_rate > 0.6:
                    lessons.append(f"Best trading time: {best_time} ({best_rate:.0%} win rate)")
                
                worst_time = time_performance.idxmin()
                worst_rate = time_performance.min()
                if worst_rate < 0.5:
                    lessons.append(f"Avoid trading during: {worst_time} ({worst_rate:.0%} win rate)")
            
            # Lesson 2: Confidence correlation
            high_conf = df[df['decision_confidence'] > 0.8]
            if len(high_conf) > 0:
                high_conf_rate = (high_conf['outcome'] == 'win').sum() / len(high_conf)
                if high_conf_rate > 0.7:
                    lessons.append(f"High-confidence trades win {high_conf_rate:.0%} of the time")
            
            # Lesson 3: Pattern-matched trades
            pattern_matched = df[df['pattern_matched'].notna()]
            if len(pattern_matched) > 0:
                pattern_rate = (pattern_matched['outcome'] == 'win').sum() / len(pattern_matched)
                if pattern_rate > 0.6:
                    lessons.append(f"Pattern-matched trades have {pattern_rate:.0%} success rate")
        
        except Exception as e:
            logger.warning(f"⚠️ Error extracting lessons: {e}")
        
        return lessons
    
    def get_performance_summary(self, days: int = 30) -> str:
        """
        Get a human-readable performance summary.
        
        Args:
            days: Number of days to summarize
            
        Returns:
            Formatted summary string
        """
        stats = self.memory.get_performance_stats(days)
        
        return f"""
📊 Performance Summary (Last {days} Days):

Trading Stats:
- Total Trades: {stats['total_trades']}
- Win Rate: {stats['win_rate']:.1%}
- Winning Trades: {stats['winning_trades']}
- Losing Trades: {stats['losing_trades']}

P&L:
- Total P&L: ${stats['total_pnl']:+.2f}
- Average Win: ${stats['avg_win']:+.2f}
- Average Loss: ${stats['avg_loss']:+.2f}
- Risk/Reward Ratio: {stats['risk_reward_ratio']:.2f}

Best/Worst:
- Best Trade: ${stats['best_trade']:+.2f}
- Worst Trade: ${stats['worst_trade']:+.2f}
"""
    
    def _empty_performance(self) -> Dict[str, Any]:
        """Return empty performance structure"""
        return {
            'date': datetime.now(),
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'neutral_trades': 0,
            'total_pnl': 0.0,
            'total_pnl_percent': 0.0,
            'best_trade': 0.0,
            'worst_trade': 0.0,
            'win_rate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'risk_reward_ratio': 0.0,
            'market_regime': 'unknown',
            'dominant_pattern': None,
            'lessons_learned': [],
            'best_indicator': None,
            'worst_indicator': None
        }
