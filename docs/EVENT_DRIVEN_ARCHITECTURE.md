# Event-Driven Architecture for WawaTrader
**Date**: October 28, 2025  
**Status**: Design Document - Based on User Requirements  
**Philosophy**: Professional trading system with dynamic discovery, thesis-based evaluation, and strategy-specific rules

---

## 🎯 Core Philosophy

### What This System IS
✅ **Event-Driven**: Responds to market events (price, news, volume), not time intervals  
✅ **Thesis-Based**: Every position has a thesis, targets, catalysts, and invalidation rules  
✅ **Dynamic Discovery**: All symbols from API/logs, ranked by opportunity quality  
✅ **Strategy-Aware**: Each trade has a strategy (momentum/swing/scalping/custom) with specific rules  
✅ **Context-Preserving**: LLM sees what it previously thought and what actually happened  
✅ **Mathematically-Backed**: Kelly Criterion + LLM conviction for position sizing  

### What This System IS NOT
❌ **Time-Driven**: No arbitrary "check every N minutes"  
❌ **Hardcoded**: No fixed watchlists or symbol lists  
❌ **Arbitrary Limits**: No "max 5 trades/hour" or "30-min minimum hold"  
❌ **Blind Re-Analysis**: No analyzing positions without comparing to original thesis  
❌ **LLM-Only Decisions**: Math validates all sizes and risks  

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    OFF-HOURS PREPARATION                         │
│  Symbol Discovery → News Synthesis → Thesis Building → Research │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       EVENT TRIGGERS                             │
│  Price Alerts | News Events | Volume Spikes | Earnings | Ratings│
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    EVENT QUEUE (FIFO)                            │
│              Prioritized, Deduplicated, Timestamped              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   DECISION CONTEXT RETRIEVAL                     │
│    Existing Position? → Load Thesis + Targets + What Happened   │
│    New Opportunity? → Load Discovery Metadata + Market Context   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      LLM ANALYSIS                                │
│  Custom Strategy Selection → Thesis vs Reality → Action Plan    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   MATHEMATICAL VALIDATION                        │
│    Kelly Criterion Base Size × LLM Conviction → Final Position  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    EXECUTION & MEMORY                            │
│   Execute Trade → Store Full Context → Set Event Triggers       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Component Design

## 1. Symbol Discovery Engine

### **Multi-Source Discovery** (Off-Hours Priority)
Runs during Evening Research and Deep Night phases, ranks opportunities for market open.

```python
class SymbolDiscoveryEngine:
    """Dynamic symbol discovery from multiple ranked sources"""
    
    def discover_opportunities(self) -> List[RankedOpportunity]:
        """
        Run all discovery methods, rank by quality, return top opportunities.
        Universe size is DYNAMIC based on opportunity quality.
        """
        sources = [
            self._scan_unusual_volume(),      # High priority - immediate action
            self._scan_news_mentions(),       # High priority - catalyst-driven
            self._scan_gap_opportunities(),   # Pre-market specific
            self._scan_sector_movers(),       # Medium priority - trend following
            self._scan_earnings_calendar(),   # Medium priority - event-driven
            self._scan_analyst_ratings(),     # Medium priority - sentiment shift
            self._scan_institutional_flows(), # Low priority - slower signal
            self._scan_social_sentiment(),    # Low priority - noisy signal
        ]
        
        # Aggregate, deduplicate, rank
        opportunities = self._aggregate_sources(sources)
        ranked = self._rank_opportunities(opportunities)
        
        # Dynamic universe sizing
        quality_threshold = self._calculate_quality_threshold(ranked)
        return [opp for opp in ranked if opp.quality_score >= quality_threshold]
    
    def _rank_opportunities(self, opportunities: List[Discovery]) -> List[RankedOpportunity]:
        """
        Ranking factors:
        - Liquidity score (can we trade it?)
        - Catalyst strength (why is it moving?)
        - Technical setup (is it actionable?)
        - News sentiment (positive/negative/mixed)
        - Volume anomaly (how unusual?)
        - Sector correlation (isolated or group move?)
        - Time sensitivity (act now or later?)
        """
        for opp in opportunities:
            opp.quality_score = self._calculate_quality(opp)
            opp.urgency = self._calculate_urgency(opp)
            opp.expected_strategy = self._suggest_strategy(opp)
        
        return sorted(opportunities, key=lambda x: (x.urgency, x.quality_score), reverse=True)
```

### **Data Sources** (All API-Accessible)

| Source | API/Method | Discovery Type | Priority | Off-Hours? |
|--------|-----------|----------------|----------|------------|
| **Unusual Volume** | Alpaca Market Data | Volume > 2x avg | HIGH | ✅ Yes (prepare) |
| **News Mentions** | Alpaca News API | Breaking news mentions | HIGH | ✅ Yes (synthesize) |
| **Gap Scanner** | Pre-market quotes | Gap > 3% vs close | HIGH | ✅ Yes (pre-market) |
| **Sector Movers** | Alpaca Screener | Sector performance | MEDIUM | ✅ Yes (trends) |
| **Earnings Calendar** | Alpaca Calendar | Upcoming/past earnings | MEDIUM | ✅ Yes (schedule) |
| **Analyst Ratings** | Alpaca News (filtered) | Upgrade/downgrade | MEDIUM | ✅ Yes (sentiment) |
| **Institutional Flows** | Alpaca Historical | Whale trades detected | LOW | ✅ Yes (patterns) |
| **Social Sentiment** | External API (optional) | Social mentions | LOW | ❌ Manual review |

---

## 2. Event Trigger System

### **Event Types**

```python
class EventType(Enum):
    # Price-based triggers
    BREAKOUT_UPSIDE = "breakout_upside"           # Price > resistance
    BREAKDOWN_DOWNSIDE = "breakdown_downside"      # Price < support
    TARGET_HIT = "target_hit"                      # Reached profit target
    STOP_LOSS_HIT = "stop_loss_hit"               # Hit invalidation price
    
    # Volume-based triggers
    VOLUME_SPIKE = "volume_spike"                  # Volume > 3x avg
    VOLUME_DRYING_UP = "volume_drying_up"         # Volume < 0.3x avg
    
    # News-based triggers
    BREAKING_NEWS = "breaking_news"                # Real-time news alert
    EARNINGS_RELEASE = "earnings_release"          # Company reported
    ANALYST_RATING_CHANGE = "analyst_rating"       # Upgrade/downgrade
    
    # Time-based (minimal use)
    MARKET_OPEN = "market_open"                    # 9:30 AM ET
    MARKET_CLOSE_WARNING = "market_close_warning"  # 3:50 PM ET
    
    # Portfolio-level triggers
    PORTFOLIO_HEAT_HIGH = "portfolio_heat_high"    # Risk concentration warning
    MARGIN_WARNING = "margin_warning"              # Buying power low
    DAILY_LOSS_LIMIT = "daily_loss_limit"         # Emergency stop triggered

class Event:
    """Single event in the queue"""
    id: str
    timestamp: datetime
    event_type: EventType
    symbol: str
    data: Dict[str, Any]
    priority: int  # Higher = more urgent
    source: str    # Which scanner/monitor generated this
```

### **Event Queue (FIFO with Priority)**

```python
class EventQueue:
    """FIFO queue with deduplication and priority sorting"""
    
    def __init__(self):
        self.queue: List[Event] = []
        self.processed_ids: Set[str] = set()
    
    def add_event(self, event: Event):
        """Add event with deduplication"""
        # Deduplicate: Same symbol + event type within 5 minutes
        event_signature = f"{event.symbol}_{event.event_type}_{event.timestamp.minute // 5}"
        
        if event_signature not in self.processed_ids:
            self.queue.append(event)
            self.processed_ids.add(event_signature)
            self._sort_queue()
    
    def _sort_queue(self):
        """Sort by priority (high first), then FIFO within same priority"""
        self.queue.sort(key=lambda e: (-e.priority, e.timestamp))
    
    def get_next_event(self) -> Optional[Event]:
        """Pop next event from queue (FIFO within priority)"""
        if self.queue:
            return self.queue.pop(0)
        return None
    
    def get_pending_count(self) -> int:
        return len(self.queue)
```

### **Event Priority Levels**

| Priority | Event Type | Example | Response Time |
|----------|-----------|---------|---------------|
| **10** | Emergency Stop | Daily loss limit, margin call | **IMMEDIATE** |
| **9** | Stop Loss Hit | Position invalidated | **IMMEDIATE** |
| **8** | Breakout/Breakdown | Price crossed key level | **< 30 seconds** |
| **7** | Breaking News | Earnings, FDA approval | **< 1 minute** |
| **6** | Target Hit | Profit target reached | **< 2 minutes** |
| **5** | Volume Spike | Unusual activity | **< 5 minutes** |
| **4** | Sector Move | Group behavior | **< 10 minutes** |
| **3** | Rating Change | Analyst upgrade | **< 30 minutes** |
| **2** | Market Open/Close | Session transition | **At specified time** |
| **1** | Background Research | New opportunity identified | **When queue empty** |

---

## 3. Decision Memory System

### **Comprehensive Memory Structure**

Every decision (entry, exit, hold) stores complete context for later retrieval.

```python
class DecisionMemory:
    """Complete context storage for thesis vs reality comparison"""
    
    # Identity
    decision_id: str
    symbol: str
    timestamp: datetime
    decision_type: str  # "entry" | "exit" | "hold" | "size_adjustment"
    
    # Strategy Context
    strategy: str  # "momentum_breakout" | "swing_support_bounce" | "earnings_run" | custom
    strategy_rules: Dict[str, Any]  # Strategy-specific parameters
    
    # Original Thesis (What We Thought)
    thesis: str  # LLM's narrative reasoning
    catalysts: List[str]  # ["Earnings beat expected", "Sector rotation into tech"]
    bullish_factors: List[str]
    bearish_factors: List[str]
    
    # Targets & Risk Management
    entry_price: float
    target_price: float
    stop_loss_price: float
    expected_holding_period: str  # "intraday" | "swing (2-5 days)" | "position (1-2 weeks)"
    invalidation_conditions: List[str]  # ["Break below $45.50", "Negative earnings"]
    
    # Position Details
    shares: int
    position_size_usd: float
    position_size_pct: float  # % of portfolio
    conviction_score: float  # LLM's 0-100 conviction
    kelly_fraction: float  # Mathematical Kelly Criterion result
    
    # Execution Context
    actual_fill_price: float
    slippage: float
    execution_quality: str  # "excellent" | "good" | "poor"
    
    # Market Context (What Was Happening)
    market_conditions: Dict[str, Any]
    spy_trend: str  # "bullish" | "bearish" | "neutral"
    sector_performance: float
    symbol_technical_state: Dict[str, Any]
    news_sentiment: float  # -1 to +1
    
    # Performance Tracking (What Happened)
    peak_profit_pct: float
    max_drawdown_pct: float
    current_pnl_pct: float
    targets_hit: List[str]  # ["First target $48.50", "Second target $51.00"]
    stops_triggered: List[str]
    
    # Re-evaluation History
    revisits: List[Dict[str, Any]]  # Each time LLM re-evaluated this position
    
    # Metadata for Manual Study
    tags: List[str]  # ["earnings_winner", "false_breakout", "great_exit"]
    notes: str  # Human or LLM notes for later review
    learning_points: List[str]  # What worked/failed for pattern recognition

class MemoryRetrieval:
    """Fetch context for LLM re-evaluation"""
    
    def get_position_context(self, symbol: str) -> Optional[DecisionMemory]:
        """Get full context for existing position"""
        return self.db.query(DecisionMemory).filter_by(
            symbol=symbol, 
            decision_type="entry",
            position_closed=False
        ).order_by(DecisionMemory.timestamp.desc()).first()
    
    def get_thesis_vs_reality(self, memory: DecisionMemory) -> Dict[str, Any]:
        """Build comparison for LLM"""
        current_price = self.get_current_price(memory.symbol)
        
        return {
            "original_thesis": {
                "entry_price": memory.entry_price,
                "target_price": memory.target_price,
                "stop_loss": memory.stop_loss_price,
                "catalysts_expected": memory.catalysts,
                "thesis_narrative": memory.thesis,
                "expected_timeframe": memory.expected_holding_period,
                "invalidation_rules": memory.invalidation_conditions,
            },
            "what_actually_happened": {
                "current_price": current_price,
                "price_change_pct": ((current_price - memory.entry_price) / memory.entry_price) * 100,
                "peak_profit_reached": memory.peak_profit_pct,
                "worst_drawdown": memory.max_drawdown_pct,
                "time_elapsed": (datetime.now() - memory.timestamp).total_seconds() / 3600,  # hours
                "targets_achieved": memory.targets_hit,
                "invalidations_triggered": memory.stops_triggered,
                "recent_news": self.get_news_since_entry(memory.symbol, memory.timestamp),
                "volume_behavior": self.analyze_volume_pattern(memory.symbol, memory.timestamp),
            },
            "questions_for_llm": [
                "Is the original thesis still valid?",
                "Did catalysts play out as expected?",
                "Should we adjust targets or stops?",
                "Is there a better opportunity now?",
            ]
        }
```

---

## 4. LLM Decision Framework

### **Structured Response Format**

The LLM receives full context and responds with structured decisions.

```python
class LLMDecisionRequest:
    """What we send to LLM"""
    
    # Event that triggered analysis
    trigger_event: Event
    
    # Position context (if exists)
    existing_position: Optional[DecisionMemory]
    thesis_vs_reality: Optional[Dict[str, Any]]
    
    # Market context
    symbol_data: Dict[str, Any]  # Price, volume, technicals
    news: List[Dict[str, Any]]
    market_conditions: Dict[str, Any]
    
    # Portfolio context
    portfolio_state: Dict[str, Any]  # Current positions, buying power, heat
    risk_capacity: Dict[str, Any]  # How much risk we can take
    
    # What LLM needs to decide
    decision_needed: str  # "entry" | "exit" | "hold" | "adjust"

class LLMDecisionResponse:
    """What LLM returns (structured JSON)"""
    
    # Decision
    action: str  # "buy" | "sell" | "hold" | "add" | "trim"
    confidence: float  # 0-100
    
    # Strategy Selection (Answer to Q1)
    strategy: str  # "momentum_breakout" | "swing_bounce" | "earnings_run" | custom
    strategy_explanation: str
    
    # Thesis (What LLM Thinks)
    thesis: str  # Narrative explanation
    catalysts: List[str]
    bullish_factors: List[str]
    bearish_factors: List[str]
    
    # Risk Management (Strategy-Specific)
    entry_price: float
    target_levels: List[float]  # [first_target, second_target, moon_shot]
    stop_loss: float
    expected_timeframe: str  # How long to hold
    invalidation_conditions: List[str]  # When to exit regardless
    
    # Position Sizing Input
    conviction_score: float  # 0-100, feeds into Kelly
    risk_reward_ratio: float  # Expected R:R
    suggested_position_pct: float  # LLM's suggestion (Kelly will validate)
    
    # For Existing Positions - Thesis vs Reality
    thesis_still_valid: bool
    what_changed: List[str]  # What's different from original thesis
    adjustment_needed: str  # "none" | "raise_stop" | "take_profit" | "exit"
    
    # Event Triggers to Set
    price_alerts: List[Dict[str, float]]  # [{"type": "above", "price": 50.0}]
    monitor_for: List[str]  # ["earnings_date", "sector_rotation", "volume_spike"]
```

### **LLM Prompt Structure**

```python
def build_llm_prompt(request: LLMDecisionRequest) -> str:
    """Build comprehensive prompt with all context"""
    
    if request.existing_position:
        # RE-EVALUATION PROMPT (Thesis vs Reality)
        return f"""
You are analyzing an EXISTING position in {request.existing_position.symbol}.

ORIGINAL THESIS (What You Previously Thought):
- Entry Price: ${request.existing_position.entry_price}
- Target: ${request.existing_position.target_price}
- Stop Loss: ${request.existing_position.stop_loss_price}
- Strategy: {request.existing_position.strategy}
- Your Thesis: "{request.existing_position.thesis}"
- Expected Catalysts: {request.existing_position.catalysts}
- Expected Timeframe: {request.existing_position.expected_holding_period}
- Invalidation Rules: {request.existing_position.invalidation_conditions}

WHAT ACTUALLY HAPPENED:
- Current Price: ${request.thesis_vs_reality['what_actually_happened']['current_price']}
- P&L: {request.thesis_vs_reality['what_actually_happened']['price_change_pct']:.2f}%
- Peak Profit Reached: {request.thesis_vs_reality['what_actually_happened']['peak_profit_reached']:.2f}%
- Time Elapsed: {request.thesis_vs_reality['what_actually_happened']['time_elapsed']:.1f} hours
- Targets Hit: {request.thesis_vs_reality['what_actually_happened']['targets_achieved']}
- Recent News: {request.thesis_vs_reality['what_actually_happened']['recent_news']}

CURRENT EVENT TRIGGER: {request.trigger_event.event_type}
{request.trigger_event.data}

YOUR TASK:
1. Compare your original thesis to what actually happened
2. Decide: Is the thesis still valid?
3. If yes: Should we hold, add more, or take partial profits?
4. If no: What changed? Should we exit immediately or adjust stops?

Respond in JSON format with your analysis.
"""
    else:
        # NEW OPPORTUNITY PROMPT
        return f"""
You are analyzing a NEW opportunity in {request.trigger_event.symbol}.

DISCOVERY CONTEXT:
- Why It's Interesting: {request.symbol_data.get('discovery_reason')}
- Current Price: ${request.symbol_data['price']}
- Volume: {request.symbol_data['volume']} (Avg: {request.symbol_data['avg_volume']})
- Recent News: {request.news}
- Technical Setup: {request.symbol_data['technicals']}

MARKET CONDITIONS:
- SPY Trend: {request.market_conditions['spy_trend']}
- Sector Performance: {request.market_conditions['sector_performance']}

PORTFOLIO STATE:
- Buying Power: ${request.portfolio_state['buying_power']}
- Current Positions: {request.portfolio_state['num_positions']}
- Portfolio Heat: {request.portfolio_state['heat_level']}

YOUR TASK:
1. Select an appropriate strategy (momentum/swing/scalping/custom)
2. Build a thesis: Why is this a good trade?
3. Define targets, stops, and invalidation conditions
4. Suggest position size based on conviction and risk-reward

Respond in JSON format with your complete analysis.
"""
```

---

## 5. Position Sizing System

### **Kelly Criterion + LLM Hybrid**

Answer to Q9: Kelly provides mathematical base, LLM provides conviction modifier.

```python
class PositionSizer:
    """Hybrid Kelly Criterion + LLM conviction sizing"""
    
    def calculate_position_size(
        self, 
        llm_decision: LLMDecisionResponse,
        portfolio_value: float,
        risk_capacity: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Kelly Criterion: f* = (p*b - q) / b
        Where:
        - p = probability of win (from win rate history)
        - q = probability of loss (1 - p)
        - b = win/loss ratio (average_win / average_loss)
        
        Then modify by LLM conviction
        """
        
        # 1. Calculate Kelly fraction from historical data
        kelly_fraction = self._calculate_kelly_fraction(
            symbol=llm_decision.symbol,
            strategy=llm_decision.strategy,
            risk_reward=llm_decision.risk_reward_ratio
        )
        
        # 2. Apply LLM conviction modifier (0-100 scale)
        conviction_multiplier = llm_decision.conviction_score / 100.0
        adjusted_kelly = kelly_fraction * conviction_multiplier
        
        # 3. Apply fractional Kelly (conservative: use 25-50% of Kelly)
        fractional_kelly = adjusted_kelly * 0.5  # Use half Kelly for safety
        
        # 4. Calculate dollar amount
        base_position_size = portfolio_value * fractional_kelly
        
        # 5. Apply portfolio-level constraints
        final_size = self._apply_portfolio_limits(
            base_size=base_position_size,
            portfolio_value=portfolio_value,
            existing_positions=risk_capacity['existing_positions'],
            symbol=llm_decision.symbol
        )
        
        return {
            "kelly_fraction": kelly_fraction,
            "conviction_adjusted_kelly": adjusted_kelly,
            "fractional_kelly": fractional_kelly,
            "base_position_size_usd": base_position_size,
            "final_position_size_usd": final_size,
            "final_position_pct": (final_size / portfolio_value) * 100,
            "shares": int(final_size / llm_decision.entry_price),
            "reasoning": self._explain_sizing_decision(kelly_fraction, conviction_multiplier)
        }
    
    def _calculate_kelly_fraction(self, symbol: str, strategy: str, risk_reward: float) -> float:
        """Calculate Kelly from historical performance"""
        # Get win rate for this strategy
        historical = self.db.get_strategy_performance(strategy)
        
        if not historical or historical['num_trades'] < 10:
            # Not enough data, use conservative default
            return 0.02  # 2% of portfolio
        
        win_rate = historical['win_rate']
        avg_win = historical['avg_win_pct']
        avg_loss = abs(historical['avg_loss_pct'])
        
        if avg_loss == 0:
            return 0.02  # Avoid division by zero
        
        b = avg_win / avg_loss  # Win/loss ratio
        p = win_rate
        q = 1 - win_rate
        
        kelly = (p * b - q) / b
        
        # Kelly can suggest crazy sizes, cap it
        return max(0, min(kelly, 0.10))  # Never more than 10% from pure Kelly
    
    def _apply_portfolio_limits(
        self, 
        base_size: float, 
        portfolio_value: float,
        existing_positions: List[Dict],
        symbol: str
    ) -> float:
        """Apply emergency stops and portfolio heat limits"""
        
        # EMERGENCY STOPS (Answer to Q10: These are hardcoded)
        MAX_SINGLE_POSITION = portfolio_value * 0.20  # Never more than 20% in one position
        MAX_SECTOR_EXPOSURE = portfolio_value * 0.40  # Never more than 40% in one sector
        MAX_TOTAL_HEAT = portfolio_value * 0.60       # Never more than 60% deployed
        
        # Check single position limit
        if base_size > MAX_SINGLE_POSITION:
            base_size = MAX_SINGLE_POSITION
        
        # Check sector exposure
        symbol_sector = self.get_sector(symbol)
        sector_exposure = sum(
            pos['value'] for pos in existing_positions 
            if self.get_sector(pos['symbol']) == symbol_sector
        )
        if sector_exposure + base_size > MAX_SECTOR_EXPOSURE:
            base_size = max(0, MAX_SECTOR_EXPOSURE - sector_exposure)
        
        # Check total heat
        total_heat = sum(pos['value'] for pos in existing_positions)
        if total_heat + base_size > MAX_TOTAL_HEAT:
            base_size = max(0, MAX_TOTAL_HEAT - total_heat)
        
        return base_size
```

---

## 6. LLM Failure Mode Handling

### **Answer to Q10: Graceful Degradation (B)**

```python
class LLMFailureHandler:
    """Handle LLM failures without blocking system"""
    
    def __init__(self):
        self.consecutive_failures = 0
        self.fallback_mode = False
    
    def handle_llm_call(self, request: LLMDecisionRequest) -> LLMDecisionResponse:
        """Call LLM with fallback logic"""
        
        try:
            # Try primary LLM
            response = self.llm_bridge.analyze(request)
            
            # Validate response structure
            if not self._validate_response(response):
                raise ValueError("Invalid LLM response structure")
            
            # Reset failure counter on success
            self.consecutive_failures = 0
            self.fallback_mode = False
            
            return response
            
        except Exception as e:
            logger.error(f"LLM failure: {e}")
            self.consecutive_failures += 1
            
            # Enter fallback mode after 3 consecutive failures
            if self.consecutive_failures >= 3:
                self.fallback_mode = True
                logger.warning("⚠️ Entering LLM fallback mode")
            
            # Return safe fallback decision
            return self._generate_fallback_decision(request)
    
    def _generate_fallback_decision(self, request: LLMDecisionRequest) -> LLMDecisionResponse:
        """Technical-only decision when LLM fails"""
        
        if request.existing_position:
            # For existing positions: Use technical stops and targets
            return self._technical_exit_decision(request)
        else:
            # For new opportunities: SKIP (don't enter without LLM)
            return LLMDecisionResponse(
                action="hold",
                confidence=0,
                thesis="LLM unavailable - skipping new entry for safety",
                strategy="none",
                # ... rest of fields as safe defaults
            )
    
    def _technical_exit_decision(self, request: LLMDecisionRequest) -> LLMDecisionResponse:
        """Manage existing position with pure technicals"""
        memory = request.existing_position
        current_price = request.symbol_data['price']
        
        # Check hard stops
        if current_price <= memory.stop_loss_price:
            return LLMDecisionResponse(
                action="sell",
                confidence=100,
                thesis=f"Stop loss hit at ${current_price}",
                strategy=memory.strategy,
                adjustment_needed="exit"
            )
        
        # Check profit targets
        if current_price >= memory.target_price:
            return LLMDecisionResponse(
                action="sell",
                confidence=80,
                thesis=f"Profit target reached at ${current_price}",
                strategy=memory.strategy,
                adjustment_needed="exit"
            )
        
        # Check invalidation conditions (time-based fallback)
        hours_held = (datetime.now() - memory.timestamp).total_seconds() / 3600
        if memory.expected_holding_period == "intraday" and hours_held > 6:
            return LLMDecisionResponse(
                action="sell",
                confidence=60,
                thesis="Intraday hold exceeded 6 hours - closing position",
                strategy=memory.strategy,
                adjustment_needed="exit"
            )
        
        # Otherwise: HOLD
        return LLMDecisionResponse(
            action="hold",
            confidence=50,
            thesis="Position within parameters - holding (LLM fallback mode)",
            strategy=memory.strategy,
            adjustment_needed="none"
        )
```

---

## 7. Strategy Framework

### **Answer to Q1: Custom Strategy per Symbol (D)**

Each symbol gets a custom strategy selected by LLM, not predefined templates.

```python
class Strategy:
    """Strategy definition - LLM creates custom strategies"""
    
    name: str  # "AAPL_earnings_momentum" (custom per symbol)
    strategy_type: str  # "momentum" | "swing" | "scalping" | "event" | "custom"
    
    # Strategy-Specific Rules (Answer to Q2)
    entry_rules: List[str]
    exit_rules: List[str]
    position_management: Dict[str, Any]
    
    # Re-evaluation triggers (Answer to Q2)
    reeval_triggers: List[str]  # ["price_moves_2pct", "volume_spike", "news_event"]
    
    # Example strategies:
    
    @staticmethod
    def momentum_breakout_strategy():
        return {
            "entry_rules": [
                "Price breaks above resistance with volume",
                "RSI > 60 but not overbought",
                "Market in uptrend"
            ],
            "exit_rules": [
                "Hit profit target (5-10% gain)",
                "Break back below breakout level",
                "Volume dries up significantly",
                "Market reverses to downtrend"
            ],
            "reeval_triggers": [
                "Price moves 2% in either direction",
                "Volume spike > 3x average",
                "Break of intraday high/low"
            ],
            "expected_timeframe": "1-5 days",
            "typical_hold": "2-3 days"
        }
    
    @staticmethod
    def swing_support_bounce_strategy():
        return {
            "entry_rules": [
                "Price at key support level",
                "Bullish divergence on RSI",
                "Recent pullback in uptrend"
            ],
            "exit_rules": [
                "Hit resistance zone (5-8% gain)",
                "Break below support (2% stop)",
                "Failed to bounce within 2 days"
            ],
            "reeval_triggers": [
                "Price moves 1.5% in either direction",
                "Approach resistance zone",
                "New support test"
            ],
            "expected_timeframe": "2-7 days",
            "typical_hold": "3-5 days"
        }
    
    @staticmethod
    def earnings_run_strategy():
        return {
            "entry_rules": [
                "Positive setup into earnings",
                "Historical earnings beat pattern",
                "Options flow shows bullish positioning"
            ],
            "exit_rules": [
                "Before earnings report (take profit)",
                "Earnings date passes",
                "Momentum fades before report"
            ],
            "reeval_triggers": [
                "Daily: check momentum",
                "Any earnings-related news",
                "3% move in either direction"
            ],
            "expected_timeframe": "1-10 days (before earnings)",
            "typical_hold": "3-7 days"
        }
```

---

## 8. Integration with Existing System

### **MarketHoursManager Integration**

```python
class EventDrivenTradingLoop:
    """Main loop - replaces time-based polling"""
    
    def __init__(self):
        self.event_queue = EventQueue()
        self.symbol_discovery = SymbolDiscoveryEngine()
        self.memory = MemoryRetrieval()
        self.llm_handler = LLMFailureHandler()
        self.position_sizer = PositionSizer()
        self.hours_manager = MarketHoursManager()
    
    async def run(self):
        """Event-driven main loop"""
        
        while True:
            phase = self.hours_manager.get_current_phase()
            
            if phase == MarketPhase.MARKET_OPEN:
                # During market hours: Process event queue
                await self._process_event_queue()
                
            elif phase == MarketPhase.AFTER_HOURS:
                # After hours: Light monitoring + queue processing
                await self._monitor_after_hours()
                await self._process_event_queue()
                
            elif phase == MarketPhase.EVENING_RESEARCH:
                # Evening: Symbol discovery and research
                await self._run_symbol_discovery()
                await self._synthesize_news()
                await self._prepare_morning_watchlist()
                
            elif phase == MarketPhase.DEEP_NIGHT:
                # Deep night: Background research only
                await self._run_deep_research()
                
            elif phase == MarketPhase.PRE_MARKET:
                # Pre-market: Gap scanner + final prep
                await self._scan_gaps()
                await self._prepare_market_open()
            
            # Sleep until next event or phase change
            await asyncio.sleep(self._calculate_sleep_duration())
    
    async def _process_event_queue(self):
        """Process events from queue (FIFO within priority)"""
        
        while event := self.event_queue.get_next_event():
            try:
                # Build decision request
                request = self._build_decision_request(event)
                
                # Get LLM decision (with fallback)
                llm_decision = self.llm_handler.handle_llm_call(request)
                
                # Validate with math
                if llm_decision.action in ["buy", "add"]:
                    position_size = self.position_sizer.calculate_position_size(
                        llm_decision, 
                        self.portfolio_value,
                        self.risk_capacity
                    )
                    
                    # Execute trade
                    await self._execute_trade(llm_decision, position_size)
                
                elif llm_decision.action in ["sell", "trim"]:
                    # Execute exit
                    await self._execute_exit(llm_decision)
                
                # Store decision in memory
                self._store_decision_memory(event, llm_decision, request)
                
                # Set new event triggers based on LLM decision
                self._set_event_triggers(llm_decision)
                
            except Exception as e:
                logger.error(f"Error processing event {event.id}: {e}")
                continue
    
    async def _run_symbol_discovery(self):
        """Off-hours symbol discovery (Answer to Q3)"""
        
        logger.info("🔍 Running evening symbol discovery...")
        
        # Run all discovery methods
        opportunities = self.symbol_discovery.discover_opportunities()
        
        logger.info(f"Found {len(opportunities)} ranked opportunities")
        
        # Store for morning review
        for opp in opportunities[:50]:  # Top 50
            self._store_opportunity(opp)
        
        # Generate morning briefing
        self._generate_morning_briefing(opportunities)
```

---

## 9. Migration Path from Old System

### **Phase 1: Add Event Infrastructure (Week 1)**
- [ ] Create `EventQueue` class
- [ ] Create `Event` and `EventType` classes
- [ ] Add event monitoring to existing TradingAgent
- [ ] Log events alongside current time-based checks

### **Phase 2: Add Memory System (Week 2)**
- [ ] Create `DecisionMemory` database schema
- [ ] Update TradingAgent to store full context
- [ ] Create `MemoryRetrieval` class
- [ ] Add thesis vs reality comparison

### **Phase 3: Add Symbol Discovery (Week 3)**
- [ ] Create `SymbolDiscoveryEngine` class
- [ ] Implement multi-source scanning
- [ ] Add ranking algorithm
- [ ] Integrate with MarketHoursManager evening phase

### **Phase 4: Update LLM Integration (Week 4)**
- [ ] Create structured `LLMDecisionRequest`/`Response`
- [ ] Update LLM prompts to include thesis context
- [ ] Add `LLMFailureHandler` with fallback mode
- [ ] Add response validation

### **Phase 5: Add Position Sizing (Week 5)**
- [ ] Create `PositionSizer` class
- [ ] Implement Kelly Criterion calculation
- [ ] Add historical performance tracking
- [ ] Integrate with portfolio limits

### **Phase 6: Full Event-Driven Loop (Week 6)**
- [ ] Replace time-based loop with event processing
- [ ] Integrate all components
- [ ] Add comprehensive logging
- [ ] Test full system in paper trading

---

## 🎯 Key Takeaways

1. **Events Drive Everything**: Price alerts, news, volume - not arbitrary timers
2. **LLM Sees Its Own Thoughts**: Thesis vs reality comparison on every revisit
3. **Math Validates Everything**: Kelly Criterion + LLM conviction = position size
4. **No Arbitrary Limits**: Only emergency stops (20% position, 40% sector, 60% total)
5. **Dynamic Discovery**: All symbols from API/logs, ranked by opportunity quality
6. **Strategy-Specific Rules**: Each trade has custom strategy with specific exit rules
7. **Graceful Degradation**: System continues safely if LLM fails
8. **Complete Memory**: Store everything for manual study later

---

**This architecture transforms WawaTrader from a time-driven amateur system into an event-driven professional trading platform.** 🚀
