"""
Decision Memory System
======================
Stores complete context for every trading decision to enable thesis vs reality comparison.

This module provides comprehensive memory for the LLM to compare its original thesis
with what actually happened when re-evaluating positions.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum
import json
from pathlib import Path
from loguru import logger


class DecisionType(Enum):
    """Type of trading decision"""
    ENTRY = "entry"
    EXIT = "exit"
    HOLD = "hold"
    SIZE_ADJUSTMENT = "size_adjustment"
    ADD = "add"
    TRIM = "trim"


@dataclass
class DecisionMemory:
    """
    Complete context storage for a trading decision.
    
    Every decision (entry, exit, hold) stores complete context for later retrieval
    and thesis vs reality comparison.
    """
    
    # Identity
    decision_id: str
    symbol: str
    timestamp: datetime
    decision_type: DecisionType
    
    # Strategy Context
    strategy: str  # "momentum_breakout" | "swing_support_bounce" | "earnings_run" | custom
    strategy_rules: Dict[str, Any] = field(default_factory=dict)
    
    # Original Thesis (What We Thought)
    thesis: str = ""
    catalysts: List[str] = field(default_factory=list)
    bullish_factors: List[str] = field(default_factory=list)
    bearish_factors: List[str] = field(default_factory=list)
    
    # Targets & Risk Management
    entry_price: float = 0.0
    target_price: float = 0.0
    stop_loss_price: float = 0.0
    expected_holding_period: str = ""  # "intraday" | "swing (2-5 days)" | "position (1-2 weeks)"
    invalidation_conditions: List[str] = field(default_factory=list)
    
    # Position Details
    shares: int = 0
    position_size_usd: float = 0.0
    position_size_pct: float = 0.0  # % of portfolio
    conviction_score: float = 0.0  # LLM's 0-100 conviction
    kelly_fraction: float = 0.0  # Mathematical Kelly Criterion result
    
    # Execution Context
    actual_fill_price: float = 0.0
    slippage: float = 0.0
    execution_quality: str = ""  # "excellent" | "good" | "poor"
    
    # Market Context (What Was Happening)
    market_conditions: Dict[str, Any] = field(default_factory=dict)
    spy_trend: str = ""  # "bullish" | "bearish" | "neutral"
    sector_performance: float = 0.0
    symbol_technical_state: Dict[str, Any] = field(default_factory=dict)
    news_sentiment: float = 0.0  # -1 to +1
    
    # Performance Tracking (What Happened)
    peak_profit_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    current_pnl_pct: float = 0.0
    targets_hit: List[str] = field(default_factory=list)
    stops_triggered: List[str] = field(default_factory=list)
    
    # Position Status
    position_closed: bool = False
    close_timestamp: Optional[datetime] = None
    close_price: float = 0.0
    close_reason: str = ""
    
    # Re-evaluation History
    revisits: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata for Manual Study
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    learning_points: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert datetime objects to ISO format
        data['timestamp'] = self.timestamp.isoformat()
        if self.close_timestamp:
            data['close_timestamp'] = self.close_timestamp.isoformat()
        data['decision_type'] = self.decision_type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DecisionMemory':
        """Create from dictionary"""
        # Convert ISO format back to datetime
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        if data.get('close_timestamp'):
            data['close_timestamp'] = datetime.fromisoformat(data['close_timestamp'])
        data['decision_type'] = DecisionType(data['decision_type'])
        return cls(**data)


class MemoryStore:
    """
    Persistent storage for decision memories.
    
    Stores memories in JSONL format for easy analysis and manual study.
    """
    
    def __init__(self, storage_path: str = "logs/decision_memory.jsonl"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache for fast lookups
        self._cache: Dict[str, List[DecisionMemory]] = {}  # symbol -> list of memories
        self._load_cache()
    
    def _load_cache(self):
        """Load existing memories into cache"""
        if not self.storage_path.exists():
            return
        
        try:
            with open(self.storage_path, 'r') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        memory = DecisionMemory.from_dict(data)
                        
                        if memory.symbol not in self._cache:
                            self._cache[memory.symbol] = []
                        self._cache[memory.symbol].append(memory)
            
            logger.info(f"✅ Loaded {sum(len(v) for v in self._cache.values())} memories from {self.storage_path}")
        except Exception as e:
            logger.error(f"❌ Error loading memory cache: {e}")
    
    def store(self, memory: DecisionMemory):
        """Store a decision memory"""
        try:
            # Add to cache
            if memory.symbol not in self._cache:
                self._cache[memory.symbol] = []
            self._cache[memory.symbol].append(memory)
            
            # Append to file
            with open(self.storage_path, 'a') as f:
                f.write(json.dumps(memory.to_dict()) + '\n')
            
            logger.debug(f"💾 Stored memory: {memory.decision_type.value} {memory.symbol} at {memory.timestamp}")
        except Exception as e:
            logger.error(f"❌ Error storing memory: {e}")
    
    def get_open_position(self, symbol: str) -> Optional[DecisionMemory]:
        """Get the most recent open position for a symbol"""
        if symbol not in self._cache:
            return None
        
        # Find most recent entry that hasn't been closed
        for memory in reversed(self._cache[symbol]):
            if memory.decision_type == DecisionType.ENTRY and not memory.position_closed:
                return memory
        
        return None
    
    def get_last_closed_position(self, symbol: str) -> Optional[DecisionMemory]:
        """Get the most recently closed position for a symbol"""
        if symbol not in self._cache:
            return None
        
        # Find most recent closed entry
        for memory in reversed(self._cache[symbol]):
            if memory.decision_type == DecisionType.ENTRY and memory.position_closed:
                return memory
        
        return None
    
    def get_position_history(self, symbol: str) -> List[DecisionMemory]:
        """Get all memories for a symbol"""
        return self._cache.get(symbol, [])
    
    def update_position(self, symbol: str, updates: Dict[str, Any]):
        """Update an open position's tracking data"""
        memory = self.get_open_position(symbol)
        if not memory:
            logger.warning(f"⚠️ No open position found for {symbol} to update")
            return
        
        # Update in-memory cache
        for key, value in updates.items():
            if hasattr(memory, key):
                setattr(memory, key, value)
        
        # Rewrite entire file (could optimize with database later)
        self._rewrite_storage()
        
        logger.debug(f"📝 Updated position: {symbol} with {len(updates)} changes")
    
    def close_position(self, symbol: str, close_price: float, close_reason: str):
        """Mark a position as closed"""
        memory = self.get_open_position(symbol)
        if not memory:
            logger.warning(f"⚠️ No open position found for {symbol} to close")
            return
        
        memory.position_closed = True
        memory.close_timestamp = datetime.now()
        memory.close_price = close_price
        memory.close_reason = close_reason
        
        # Calculate final P&L
        memory.current_pnl_pct = ((close_price - memory.entry_price) / memory.entry_price) * 100
        
        self._rewrite_storage()
        
        logger.info(f"🔒 Closed position: {symbol} at ${close_price} - {close_reason}")
    
    def add_revisit(self, symbol: str, revisit_data: Dict[str, Any]):
        """Add a re-evaluation entry to position history"""
        memory = self.get_open_position(symbol)
        if not memory:
            logger.warning(f"⚠️ No open position found for {symbol} to add revisit")
            return
        
        revisit_data['timestamp'] = datetime.now().isoformat()
        memory.revisits.append(revisit_data)
        
        self._rewrite_storage()
        
        logger.debug(f"📋 Added revisit to {symbol}: {revisit_data.get('action', 'N/A')}")
    
    def _rewrite_storage(self):
        """Rewrite entire storage file (used after updates)"""
        try:
            with open(self.storage_path, 'w') as f:
                for memories in self._cache.values():
                    for memory in memories:
                        f.write(json.dumps(memory.to_dict()) + '\n')
        except Exception as e:
            logger.error(f"❌ Error rewriting storage: {e}")
    
    def get_all_open_positions(self) -> List[DecisionMemory]:
        """Get all currently open positions"""
        open_positions = []
        for symbol in self._cache:
            position = self.get_open_position(symbol)
            if position:
                open_positions.append(position)
        return open_positions
    
    def get_strategy_performance(self, strategy: str) -> Dict[str, Any]:
        """
        Calculate historical performance for a strategy.
        Used for Kelly Criterion calculation.
        """
        closed_positions = []
        for memories in self._cache.values():
            for memory in memories:
                if (memory.decision_type == DecisionType.ENTRY and 
                    memory.position_closed and 
                    memory.strategy == strategy):
                    closed_positions.append(memory)
        
        if not closed_positions:
            return {
                'num_trades': 0,
                'win_rate': 0.55,  # Default conservative
                'avg_win_pct': 3.5,
                'avg_loss_pct': 2.0,
            }
        
        # Calculate metrics
        wins = [m for m in closed_positions if m.current_pnl_pct > 0]
        losses = [m for m in closed_positions if m.current_pnl_pct <= 0]
        
        win_rate = len(wins) / len(closed_positions) if closed_positions else 0.5
        avg_win_pct = sum(m.current_pnl_pct for m in wins) / len(wins) if wins else 3.5
        avg_loss_pct = abs(sum(m.current_pnl_pct for m in losses) / len(losses)) if losses else 2.0
        
        return {
            'num_trades': len(closed_positions),
            'win_rate': win_rate,
            'avg_win_pct': avg_win_pct,
            'avg_loss_pct': avg_loss_pct,
            'total_return_pct': sum(m.current_pnl_pct for m in closed_positions),
        }


class ThesisRealityComparator:
    """
    Compare LLM's original thesis to current reality.
    Builds comprehensive context for re-evaluation prompts.
    """
    
    def __init__(self, memory_store: MemoryStore):
        self.memory_store = memory_store
    
    def get_comparison(
        self, 
        symbol: str, 
        current_price: float,
        current_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Build thesis vs reality comparison for a symbol.
        
        Returns comprehensive context showing what LLM originally thought
        versus what actually happened.
        """
        memory = self.memory_store.get_open_position(symbol)
        if not memory:
            return None
        
        time_elapsed = datetime.now() - memory.timestamp
        hours_elapsed = time_elapsed.total_seconds() / 3600
        days_elapsed = hours_elapsed / 24
        
        pnl_pct = ((current_price - memory.entry_price) / memory.entry_price) * 100
        pnl_usd = (current_price - memory.entry_price) * memory.shares
        
        return {
            "original_thesis": {
                "timestamp": memory.timestamp.isoformat(),
                "strategy": memory.strategy,
                "entry_price": memory.entry_price,
                "target_price": memory.target_price,
                "stop_loss": memory.stop_loss_price,
                "expected_gain_pct": ((memory.target_price / memory.entry_price) - 1) * 100,
                "expected_loss_pct": ((memory.entry_price / memory.stop_loss_price) - 1) * 100,
                "catalysts_expected": memory.catalysts,
                "bullish_factors": memory.bullish_factors,
                "bearish_factors": memory.bearish_factors,
                "thesis_narrative": memory.thesis,
                "expected_timeframe": memory.expected_holding_period,
                "invalidation_rules": memory.invalidation_conditions,
                "conviction": memory.conviction_score,
            },
            "what_actually_happened": {
                "current_price": current_price,
                "price_change_pct": pnl_pct,
                "price_change_usd": pnl_usd,
                "peak_profit_reached": memory.peak_profit_pct,
                "worst_drawdown": memory.max_drawdown_pct,
                "time_elapsed_hours": hours_elapsed,
                "time_elapsed_days": days_elapsed,
                "targets_achieved": memory.targets_hit,
                "invalidations_triggered": memory.stops_triggered,
                "recent_news": current_data.get('news', []),
                "volume_behavior": current_data.get('volume_analysis', {}),
                "price_action": current_data.get('price_action', {}),
            },
            "position_details": {
                "shares": memory.shares,
                "position_size_usd": memory.position_size_usd,
                "position_size_pct": memory.position_size_pct,
                "unrealized_pnl_usd": pnl_usd,
                "unrealized_pnl_pct": pnl_pct,
            },
            "revisit_history": [
                {
                    "timestamp": r.get('timestamp'),
                    "action": r.get('action'),
                    "reasoning": r.get('reasoning', '')[:100],  # Summary
                }
                for r in memory.revisits[-3:]  # Last 3 revisits
            ],
            "questions_for_llm": [
                "Is the original thesis still valid?",
                "Did the expected catalysts play out?",
                "Should we adjust targets or stops?",
                "Is there a better opportunity elsewhere?",
                "What changed from your expectations?",
            ]
        }
    
    def build_reeval_prompt(
        self,
        symbol: str,
        current_price: float,
        current_data: Dict[str, Any],
        trigger_event: str
    ) -> Optional[str]:
        """
        Build comprehensive re-evaluation prompt for LLM.
        
        Shows LLM its original thesis and what actually happened.
        """
        comparison = self.get_comparison(symbol, current_price, current_data)
        if not comparison:
            return None
        
        orig = comparison['original_thesis']
        actual = comparison['what_actually_happened']
        
        prompt = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POSITION RE-EVALUATION: {symbol}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

YOUR ORIGINAL THESIS ({actual['time_elapsed_hours']:.1f} hours ago):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Strategy: {orig['strategy']}
Entry Price: ${orig['entry_price']:.2f}
Target: ${orig['target_price']:.2f} (+{orig['expected_gain_pct']:.1f}%)
Stop Loss: ${orig['stop_loss']:.2f} (-{orig['expected_loss_pct']:.1f}%)
Conviction: {orig['conviction']:.0f}/100

Your Thesis:
"{orig['thesis_narrative']}"

Expected Catalysts:
{chr(10).join(f"  • {c}" for c in orig['catalysts_expected'])}

Expected Holding Period: {orig['expected_timeframe']}

Invalidation Conditions:
{chr(10).join(f"  • {c}" for c in orig['invalidation_rules'])}

WHAT ACTUALLY HAPPENED:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Current Price: ${actual['current_price']:.2f}
P&L: {actual['price_change_pct']:+.2f}% (${actual['price_change_usd']:+,.2f})
Time Held: {actual['time_elapsed_hours']:.1f} hours ({actual['time_elapsed_days']:.1f} days)

Performance:
  • Peak Profit: {actual['peak_profit_reached']:+.2f}%
  • Max Drawdown: {actual['worst_drawdown']:.2f}%

Targets/Stops Status:
  • Targets Hit: {', '.join(actual['targets_achieved']) if actual['targets_achieved'] else 'None'}
  • Stops Triggered: {', '.join(actual['invalidations_triggered']) if actual['invalidations_triggered'] else 'None'}

EVENT TRIGGER: {trigger_event}

YOUR TASK:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Compare your original thesis to what actually happened and decide:

1. Is your original thesis still valid? Why or why not?
2. Did the expected catalysts play out as anticipated?
3. Should we HOLD, ADD, TRIM, or EXIT this position?
4. What changed from your expectations?

Respond in JSON format:
{{
  "thesis_still_valid": true/false,
  "what_changed": ["List of key differences from expectations"],
  "catalysts_status": {{"catalyst_name": "played_out/pending/failed"}},
  "action": "hold/add/trim/exit",
  "confidence": 0-100,
  "reasoning": "Detailed comparison of thesis vs reality",
  "adjustment_needed": "none/raise_stop/take_profit/exit_immediately"
}}
"""
        return prompt


# Convenience function for quick access
_memory_store = None

def get_memory_store() -> MemoryStore:
    """Get singleton memory store instance"""
    global _memory_store
    if _memory_store is None:
        _memory_store = MemoryStore()
    return _memory_store
