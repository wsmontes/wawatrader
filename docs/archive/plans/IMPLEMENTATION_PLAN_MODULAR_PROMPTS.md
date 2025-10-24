# Implementation Plan: Modular Prompt Architecture
## Concrete Steps with Code Samples

**Target**: Transform LLM system from hardcoded prompts to composable, context-aware architecture  
**Timeline**: 4 weeks (phased rollout)  
**Risk**: MEDIUM (parallel system allows safe migration)

---

## 🎯 Phase 1: Core Infrastructure (Days 1-5)

### Step 1.1: Create Base Component System

**File**: `wawatrader/llm/components/base.py`

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class QueryContext:
    """Complete context for an LLM query"""
    query_type: str
    trigger: str
    profile: str
    primary_symbol: Optional[str] = None
    comparison_symbols: Optional[list] = None
    portfolio_state: Optional[Dict] = None
    include_news: bool = True
    include_market_regime: bool = False
    detail_level: str = 'standard'
    expected_format: str = 'STANDARD_DECISION'
    allow_data_requests: bool = False
    
    # Additional context data
    extra_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.extra_data is None:
            self.extra_data = {}

class PromptComponent(ABC):
    """Base class for all prompt components"""
    
    def __init__(self, data: Optional[Dict[str, Any]] = None, priority: int = 5):
        self.data = data or {}
        self.priority = priority
        self.context = None
    
    def set_context(self, context: QueryContext):
        """Set the query context"""
        self.context = context
    
    @abstractmethod
    def render(self) -> str:
        """Convert component data to prompt text"""
        pass
    
    def is_relevant(self, context: QueryContext) -> bool:
        """Should this component be included in this query?"""
        return True
    
    def validate_data(self) -> bool:
        """Check if component has required data"""
        return bool(self.data)
```

**Testing**: Create 3 dummy components to verify inheritance works

---

### Step 1.2: Create Query Type System

**File**: `wawatrader/llm/components/context.py`

```python
from .base import PromptComponent, QueryContext

class QueryTypeComponent(PromptComponent):
    """Declares what type of analysis is needed"""
    
    QUERY_TYPES = {
        'NEW_OPPORTUNITY': {
            'emoji': '🎯',
            'title': 'NEW OPPORTUNITY EVALUATION',
            'description': 'Evaluating potential BUY entry for new position',
        },
        'POSITION_REVIEW': {
            'emoji': '💼',
            'title': 'POSITION REVIEW',
            'description': 'Evaluating existing holding for SELL/HOLD decision',
        },
        'PORTFOLIO_AUDIT': {
            'emoji': '📊',
            'title': 'PORTFOLIO AUDIT',
            'description': 'Ranking all holdings to identify strongest/weakest',
        },
        'COMPARATIVE_ANALYSIS': {
            'emoji': '⚖️',
            'title': 'COMPARATIVE ANALYSIS',
            'description': 'Side-by-side comparison of multiple stocks',
        },
        'MARKET_REGIME': {
            'emoji': '🌍',
            'title': 'MARKET REGIME ANALYSIS',
            'description': 'Assessing current market environment and trends',
        },
    }
    
    def __init__(self, query_type: str, **kwargs):
        super().__init__(**kwargs)
        self.query_type = query_type
        self.priority = 10  # Always show first
    
    def render(self) -> str:
        config = self.QUERY_TYPES.get(self.query_type, {})
        emoji = config.get('emoji', '📋')
        title = config.get('title', 'ANALYSIS')
        desc = config.get('description', '')
        
        return f"""
{emoji} QUERY TYPE: {title}
{'=' * 70}
{desc}
"""

class TriggerComponent(PromptComponent):
    """Explains what triggered this query"""
    
    TRIGGERS = {
        'SCHEDULED_CYCLE': 'Regular 5-minute trading cycle',
        'CAPITAL_CONSTRAINT': 'Need to free capital (buying power < 5% of portfolio)',
        'PRICE_ALERT': 'Stock reached price target or stop-loss',
        'TECHNICAL_SIGNAL': 'Indicator generated buy/sell signal',
        'NEWS_EVENT': 'Breaking news detected',
        'USER_REQUEST': 'Manual analysis requested',
    }
    
    def __init__(self, trigger: str, **kwargs):
        super().__init__(**kwargs)
        self.trigger = trigger
        self.priority = 9
    
    def render(self) -> str:
        description = self.TRIGGERS.get(self.trigger, self.trigger)
        return f"🔔 TRIGGER: {description}\n"
```

**Testing**: Verify each query type renders correctly

---

### Step 1.3: Create Trading Profile Components

**File**: `wawatrader/llm/profiles/base_profile.py`

```python
from ..components.base import PromptComponent

class TradingProfileComponent(PromptComponent):
    """Describes trader personality and risk preferences"""
    
    PROFILES = {
        'conservative': {
            'name': 'Conservative Investor',
            'risk_tolerance': 'LOW',
            'decision_style': 'Cautious, requires strong confirmation',
            'hold_preference': 'Prefer HOLD over risky action',
            'min_confidence_buy': 75,
            'min_confidence_sell': 70,
        },
        'moderate': {
            'name': 'Balanced Trader',
            'risk_tolerance': 'MEDIUM',
            'decision_style': 'Evidence-based with reasonable risk acceptance',
            'hold_preference': 'Use HOLD when signals are mixed',
            'min_confidence_buy': 65,
            'min_confidence_sell': 60,
        },
        'aggressive': {
            'name': 'Aggressive Trader',
            'risk_tolerance': 'HIGH',
            'decision_style': 'Quick decisions, accept volatility for returns',
            'hold_preference': 'Prefer action over waiting',
            'min_confidence_buy': 50,
            'min_confidence_sell': 45,
        },
        'rotator': {
            'name': 'Active Capital Rotator',
            'risk_tolerance': 'MEDIUM-HIGH',
            'decision_style': 'Continuously reallocate to best opportunities',
            'hold_preference': 'HOLD only if still best option, otherwise rotate',
            'min_confidence_buy': 60,
            'min_confidence_sell': 40,  # Lower bar for SELL to enable rotation
            'special_rules': [
                'Prioritize SELL decisions when evaluating existing positions',
                'Compare position vs other opportunities, not just absolute merit',
                'Small profits are still profits - rotate early and often',
            ]
        },
    }
    
    def __init__(self, profile: str, **kwargs):
        super().__init__(**kwargs)
        self.profile = profile
        self.priority = 9
    
    def render(self) -> str:
        config = self.PROFILES.get(self.profile, self.PROFILES['moderate'])
        
        output = f"""
🎯 TRADING PROFILE: {config['name']}
{'=' * 70}
Risk Tolerance: {config['risk_tolerance']}
Decision Style: {config['decision_style']}
HOLD Preference: {config['hold_preference']}
Min Confidence: BUY ≥{config['min_confidence_buy']}%, SELL ≥{config['min_confidence_sell']}%
"""
        
        if 'special_rules' in config:
            output += "\n⚠️  SPECIAL RULES:\n"
            for rule in config['special_rules']:
                output += f"   • {rule}\n"
        
        return output + "\n"
```

**Testing**: Verify each profile renders with correct thresholds

---

### Step 1.4: Create Prompt Builder

**File**: `wawatrader/llm/builders/prompt_builder.py`

```python
from typing import List, Dict, Any
from ..components.base import PromptComponent, QueryContext

class PromptBuilder:
    """Assembles prompts from components based on context"""
    
    def __init__(self):
        self.component_classes = {}
        self.default_components = []
    
    def register_component(self, name: str, component_class):
        """Register a component class"""
        self.component_classes[name] = component_class
    
    def build(self, context: QueryContext, data: Dict[str, Any]) -> str:
        """
        Build prompt from context and data.
        
        Args:
            context: Query context defining what to ask
            data: All available data (technical, portfolio, news, etc.)
        
        Returns:
            Complete prompt string
        """
        # 1. Select and instantiate relevant components
        components = self._select_components(context, data)
        
        # 2. Set context on all components
        for component in components:
            component.set_context(context)
        
        # 3. Filter by relevance
        relevant = [c for c in components if c.is_relevant(context)]
        
        # 4. Sort by priority (higher = more important = shown first)
        relevant.sort(key=lambda c: c.priority, reverse=True)
        
        # 5. Render each component
        sections = []
        for component in relevant:
            try:
                rendered = component.render()
                if rendered and rendered.strip():
                    sections.append(rendered.strip())
            except Exception as e:
                logger.warning(f"Component {component.__class__.__name__} failed: {e}")
        
        # 6. Assemble final prompt
        prompt = "\n\n".join(sections)
        
        return prompt
    
    def _select_components(self, context: QueryContext, data: Dict[str, Any]) -> List[PromptComponent]:
        """Choose which components to include based on query type"""
        
        components = []
        
        # Import here to avoid circular dependencies
        from ..components.context import QueryTypeComponent, TriggerComponent
        from ..components.data import TechnicalDataComponent, PositionDataComponent
        from ..components.instructions import TaskInstructionComponent, ResponseFormatComponent
        from ..profiles.base_profile import TradingProfileComponent
        
        # Always include these
        components.append(QueryTypeComponent(context.query_type))
        components.append(TriggerComponent(context.trigger))
        components.append(TradingProfileComponent(context.profile))
        
        # Add task-specific components
        if context.query_type in ['NEW_OPPORTUNITY', 'POSITION_REVIEW']:
            if 'technical' in data:
                components.append(TechnicalDataComponent(data['technical']))
        
        if context.query_type == 'POSITION_REVIEW':
            if 'position' in data:
                components.append(PositionDataComponent(data['position']))
        
        # Always include instructions and format
        components.append(TaskInstructionComponent(context.query_type))
        components.append(ResponseFormatComponent(context.expected_format))
        
        return components
```

**Testing**: Build sample prompts for each query type

---

## 🎯 Phase 2: Essential Components (Days 6-10)

### Step 2.1: Technical Data Component

**File**: `wawatrader/llm/components/data.py`

```python
from .base import PromptComponent, QueryContext
from typing import Dict, Any

class TechnicalDataComponent(PromptComponent):
    """Technical indicators with adaptive detail level"""
    
    def __init__(self, data: Dict[str, Any], **kwargs):
        super().__init__(data, **kwargs)
        self.priority = 8
    
    def render(self) -> str:
        if not self.validate_data():
            return ""
        
        # Adaptive rendering based on query type
        if self.context and self.context.query_type == 'PORTFOLIO_AUDIT':
            return self._summary_format()
        elif self.context and self.context.detail_level == 'detailed':
            return self._detailed_format()
        else:
            return self._standard_format()
    
    def _standard_format(self) -> str:
        """Standard technical analysis format"""
        signals = self.data
        price = signals.get('price', {})
        trend = signals.get('trend', {})
        momentum = signals.get('momentum', {})
        
        symbol = self.context.primary_symbol if self.context else 'UNKNOWN'
        
        output = f"""
📊 TECHNICAL DATA: {symbol}
{'=' * 70}
💰 Price: ${price.get('close', 0):.2f}
"""
        
        # Trend analysis
        sma_20 = trend.get('sma_20', 0)
        sma_50 = trend.get('sma_50', 0)
        current_price = price.get('close', 0)
        
        if current_price > sma_20:
            trend_emoji = '📈'
            trend_text = 'BULLISH TREND (price above SMA20)'
        else:
            trend_emoji = '📉'
            trend_text = 'BEARISH TREND (price below SMA20)'
        
        output += f"{trend_emoji} {trend_text}\n"
        output += f"   SMA20: ${sma_20:.2f}, SMA50: ${sma_50:.2f}\n\n"
        
        # Momentum
        rsi = momentum.get('rsi', 50)
        if rsi > 70:
            momentum_text = "OVERBOUGHT (consider waiting)"
        elif rsi < 30:
            momentum_text = "OVERSOLD (potential bounce)"
        else:
            momentum_text = "NEUTRAL"
        
        output += f"📊 RSI: {rsi:.1f} ({momentum_text})\n"
        
        # Volume
        volume = signals.get('volume', {})
        vol_ratio = volume.get('ratio', 1.0)
        output += f"📊 Volume: {vol_ratio:.2f}x average\n"
        
        return output
    
    def _summary_format(self) -> str:
        """Compact format for portfolio comparisons"""
        signals = self.data
        symbol = self.context.primary_symbol if self.context else 'UNKNOWN'
        
        price = signals.get('price', {}).get('close', 0)
        rsi = signals.get('momentum', {}).get('rsi', 50)
        trend = "Bullish" if price > signals.get('trend', {}).get('sma_20', 0) else "Bearish"
        
        return f"{symbol}: ${price:.2f}, {trend}, RSI {rsi:.0f}"
```

---

### Step 2.2: Position Data Component

```python
class PositionDataComponent(PromptComponent):
    """Current position details with P&L context"""
    
    def __init__(self, data: Dict[str, Any], **kwargs):
        super().__init__(data, **kwargs)
        self.priority = 8
    
    def is_relevant(self, context: QueryContext) -> bool:
        return context.query_type == 'POSITION_REVIEW'
    
    def render(self) -> str:
        if not self.validate_data():
            return ""
        
        pos = self.data
        symbol = pos.get('symbol', 'UNKNOWN')
        shares = pos.get('qty', 0)
        avg_price = pos.get('avg_entry_price', 0)
        current_price = pos.get('current_price', 0)
        
        # Calculate P&L
        pnl_pct = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0
        pnl_dollars = (current_price - avg_price) * shares
        market_value = current_price * shares
        
        # Determine status
        if pnl_pct < -5:
            status = "⚠️  LOSING POSITION (consider stop-loss)"
        elif pnl_pct < -2:
            status = "📉 UNDERWATER (watch closely)"
        elif pnl_pct > 10:
            status = "🎯 STRONG PROFIT (consider taking gains)"
        elif pnl_pct > 5:
            status = "✅ PROFITABLE (let winners run)"
        elif pnl_pct > 0:
            status = "💚 SMALL PROFIT (monitor)"
        else:
            status = "➡️  BREAKEVEN (evaluate trend)"
        
        output = f"""
💼 POSITION DETAILS: {symbol}
{'=' * 70}
⚠️  YOU ALREADY OWN THIS STOCK

Current Holdings:
   • Shares: {shares:,.0f}
   • Entry Price: ${avg_price:.2f}
   • Current Price: ${current_price:.2f}
   • Market Value: ${market_value:,.0f}

Performance:
   • P&L: {pnl_pct:+.2f}% (${pnl_dollars:+,.0f})
   • Status: {status}

🎯 POSITION MANAGEMENT CONTEXT:
This is an EXISTING position. Your decision options:
   
   1️⃣ SELL: Exit position if:
      • Technical setup deteriorated
      • Profit target reached
      • Better opportunities exist elsewhere
      • Position is weak compared to portfolio average
   
   2️⃣ HOLD: Keep position if:
      • Trend remains intact
      • No red flags
      • Still one of best holdings
   
   3️⃣ BUY: Add to position ONLY if:
      • Strong bullish continuation setup
      • High conviction
      • Position sizing allows (rare case)

⚠️  KEY PRINCIPLE: Don't hold losers hoping for recovery. Cut losses early, rotate capital actively.
"""
        
        return output
```

---

### Step 2.3: Task Instructions Component

**File**: `wawatrader/llm/components/instructions.py`

```python
from .base import PromptComponent, QueryContext

class TaskInstructionComponent(PromptComponent):
    """Task-specific instructions for the LLM"""
    
    TASKS = {
        'NEW_OPPORTUNITY': """
⚡ YOUR TASK: Evaluate if this is a good BUY opportunity RIGHT NOW
{'=' * 70}

Consider these factors:

1. TECHNICAL SETUP (70% weight)
   • Is the trend clear and confirmed?
   • Is momentum healthy (RSI 40-70 range)?
   • Does volume confirm the move?

2. ENTRY TIMING (20% weight)
   • Is this the right moment or should I wait?
   • Is the stock overbought/oversold?
   • Any near-term catalysts?

3. RISK/REWARD (10% weight)
   • Where are support/resistance levels?
   • What's the potential profit vs risk?

DECISION GUIDELINES:
   • BUY: Strong technical setup with good entry timing
   • HOLD: Good setup but poor timing (wait for better entry)
   • SELL: Not applicable for new opportunities
""",
        
        'POSITION_REVIEW': """
⚡ YOUR TASK: Decide if you should HOLD or SELL this existing position
{'=' * 70}

You are NOT evaluating whether to buy this stock. You ALREADY OWN IT.
The question is: Should you continue holding or exit?

Evaluation Framework:

1. TECHNICAL HEALTH (40% weight)
   • Has the trend deteriorated?
   • Is momentum weakening?
   • Any breakdown signals?

2. PROFIT/LOSS STATUS (30% weight)
   • Is profit target reached → SELL to lock gains
   • Is position losing → SELL to cut losses
   • Is position flat → Evaluate if capital better used elsewhere

3. RELATIVE OPPORTUNITY COST (30% weight)
   • Are there better opportunities available?
   • Is this still a top holding or just "okay"?
   • What's the opportunity cost of keeping capital here?

DECISION GUIDELINES:
   • SELL: If technical deteriorated OR better opportunities exist OR profit target hit
   • HOLD: If trend intact AND still one of best holdings
   • BUY: Only if adding to winning position with strong setup (rare)

⚠️  BIAS WARNING: Don't be emotionally attached to positions. Rotate capital actively!
""",
        
        'PORTFOLIO_AUDIT': """
⚡ YOUR TASK: Rank ALL holdings from STRONGEST to WEAKEST
{'=' * 70}

You will receive data for multiple positions. Evaluate each one and create a ranking.

Ranking Criteria:

1. Technical Strength (50% weight)
   • Trend direction and strength
   • Momentum health
   • Volume confirmation

2. Performance (30% weight)
   • Current P&L
   • Recent price action
   • Consistency

3. Relative Attractiveness (20% weight)
   • Best risk/reward
   • Strongest setups
   • Most upside potential

Output Requirements:
   • Rank from 1 (best) to N (worst)
   • Give each a score (0-100)
   • Assign action: KEEP, HOLD, or SELL
   • Brief reason for each

Goal: Identify top 3 to KEEP and bottom 3 to SELL for capital rotation
""",
    }
    
    def __init__(self, query_type: str, **kwargs):
        super().__init__(**kwargs)
        self.query_type = query_type
        self.priority = 6
    
    def render(self) -> str:
        return self.TASKS.get(self.query_type, "")

class ResponseFormatComponent(PromptComponent):
    """Expected response structure"""
    
    FORMATS = {
        'STANDARD_DECISION': """
📋 RESPONSE FORMAT - REQUIRED STRUCTURE
{'=' * 70}

Respond with ONLY valid JSON in this exact format:

{
  "sentiment": "bullish" | "bearish" | "neutral",
  "confidence": 0-100,
  "action": "buy" | "sell" | "hold",
  "reasoning": "Detailed explanation with specific levels and catalysts",
  "risk_factors": [
    "[CRITICAL|HIGH|MEDIUM]: Specific risk with timeframe",
    "[CRITICAL|HIGH|MEDIUM]: Another risk"
  ]
}

REQUIREMENTS:
✅ Include specific price levels (support, resistance, targets)
✅ Mention key technical indicators driving decision
✅ Risk factors must have severity tags
❌ No markdown code blocks (```json)
❌ No additional text outside JSON
❌ No generic/vague reasoning
""",
        
        'RANKING': """
📋 RESPONSE FORMAT - RANKING STRUCTURE
{'=' * 70}

{
  "ranked_positions": [
    {
      "symbol": "AAPL",
      "rank": 1,
      "score": 92,
      "action": "keep",
      "reason": "Strong uptrend, RSI healthy, best technical setup in portfolio"
    },
    {
      "symbol": "TSLA",
      "rank": 10,
      "score": 38,
      "action": "sell",
      "reason": "Broken support, momentum weak, capital better deployed elsewhere"
    }
  ],
  "summary": "Overall assessment of portfolio health and rotation recommendation"
}
""",
    }
    
    def __init__(self, expected_format: str, **kwargs):
        super().__init__(**kwargs)
        self.expected_format = expected_format
        self.priority = 1  # Show last
    
    def render(self) -> str:
        return self.FORMATS.get(self.expected_format, self.FORMATS['STANDARD_DECISION'])
```

---

## 🎯 Phase 3: Integration (Days 11-15)

### Step 3.1: Update LLMBridge to use new system

**File**: `wawatrader/llm_bridge.py` (modified)

```python
# Add at top of file
from wawatrader.llm.builders.prompt_builder import PromptBuilder
from wawatrader.llm.components.base import QueryContext

class LLMBridge:
    def __init__(self):
        # ... existing code ...
        
        # NEW: Initialize prompt builder
        self.prompt_builder = PromptBuilder()
    
    def analyze_market_v2(
        self,
        symbol: str,
        signals: Dict[str, Any],
        query_type: str = 'NEW_OPPORTUNITY',
        current_position: Optional[Dict[str, Any]] = None,
        portfolio_state: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        NEW VERSION: Uses modular prompt system
        
        Args:
            symbol: Stock ticker
            signals: Technical indicators
            query_type: NEW_OPPORTUNITY, POSITION_REVIEW, etc.
            current_position: If reviewing existing position
            portfolio_state: Overall portfolio context
        """
        # Build context
        context = QueryContext(
            query_type=query_type,
            trigger='SCHEDULED_CYCLE',  # Or detect from caller
            profile=self.trading_profile,
            primary_symbol=symbol,
            include_news=True,
            expected_format='STANDARD_DECISION',
        )
        
        # Gather all data
        data = {
            'technical': signals,
        }
        
        if current_position:
            data['position'] = current_position
        
        if portfolio_state:
            data['portfolio'] = portfolio_state
        
        # Build prompt using new system
        prompt = self.prompt_builder.build(context, data)
        
        # Query LLM
        response = self.query_llm(prompt, symbol)
        if not response:
            return None
        
        # Parse response
        analysis = self.parse_llm_response(response)
        
        return analysis
```

---

### Step 3.2: Update trading_agent.py

**File**: `wawatrader/trading_agent.py` (modified)

```python
def run_trading_cycle(self):
    """Enhanced trading cycle with modular LLM queries"""
    
    # STEP 1: Portfolio Review (if capital-constrained)
    if self.buying_power < (self.account_value * 0.05):
        logger.info("💰 CAPITAL CONSTRAINED - Running portfolio audit")
        
        # NEW: Use PORTFOLIO_AUDIT query type
        audit_result = self.llm_bridge.audit_portfolio(
            positions=list(self.positions.values()),
            portfolio_state={
                'total_value': self.account_value,
                'buying_power': self.buying_power,
                'num_positions': len(self.positions),
            }
        )
        
        # Execute SELL recommendations
        for pos in audit_result['ranked_positions']:
            if pos['action'] == 'sell':
                self._execute_sell(pos['symbol'], pos['reason'])
    
    # STEP 2: Review individual positions
    for symbol in list(self.positions.keys()):
        signals = self.alpaca_client.get_latest_signals(symbol)
        
        # NEW: Use POSITION_REVIEW query type
        analysis = self.llm_bridge.analyze_market_v2(
            symbol=symbol,
            signals=signals,
            query_type='POSITION_REVIEW',
            current_position=self.positions[symbol],
        )
        
        decision = self.make_decision(analysis)
        if decision.action == 'sell':
            self.execute_decision(decision)
    
    # STEP 3: Scan watchlist for new opportunities
    if self.buying_power > 100:
        for symbol in self.symbols[:10]:
            if symbol in self.positions:
                continue
            
            signals = self.alpaca_client.get_latest_signals(symbol)
            
            # NEW: Use NEW_OPPORTUNITY query type
            analysis = self.llm_bridge.analyze_market_v2(
                symbol=symbol,
                signals=signals,
                query_type='NEW_OPPORTUNITY',
            )
            
            decision = self.make_decision(analysis)
            if decision.action == 'buy':
                self.execute_decision(decision)
```

---

## 📋 Testing Strategy

### Unit Tests

```python
# tests/test_prompt_components.py
def test_query_type_component():
    component = QueryTypeComponent('NEW_OPPORTUNITY')
    output = component.render()
    assert 'NEW OPPORTUNITY' in output
    assert '🎯' in output

def test_position_component_with_loss():
    data = {
        'symbol': 'AAPL',
        'qty': 100,
        'avg_entry_price': 200,
        'current_price': 180,
    }
    component = PositionDataComponent(data)
    output = component.render()
    assert 'LOSING POSITION' in output
    assert '-10.00%' in output

def test_prompt_builder_new_opportunity():
    context = QueryContext(
        query_type='NEW_OPPORTUNITY',
        trigger='TECHNICAL_SIGNAL',
        profile='aggressive',
        primary_symbol='NVDA',
    )
    data = {'technical': {...}}
    
    prompt = PromptBuilder().build(context, data)
    assert 'NEW OPPORTUNITY' in prompt
    assert 'NVDA' in prompt
    assert 'Aggressive' in prompt
```

### Integration Tests

```python
# tests/test_llm_integration.py
def test_position_review_generates_sell():
    """Test that POSITION_REVIEW with weak position recommends SELL"""
    
    # Simulate weak position
    signals = {
        'price': {'close': 180},
        'trend': {'sma_20': 190, 'sma_50': 195},  # Below SMAs
        'momentum': {'rsi': 35},  # Oversold
    }
    
    position = {
        'symbol': 'WEAK',
        'qty': 100,
        'avg_entry_price': 200,
        'current_price': 180,
    }
    
    analysis = llm_bridge.analyze_market_v2(
        symbol='WEAK',
        signals=signals,
        query_type='POSITION_REVIEW',
        current_position=position,
    )
    
    assert analysis['action'] == 'sell'
    assert analysis['confidence'] >= 45
```

---

## 📊 Success Criteria

- [ ] Can generate 5+ distinct prompt types
- [ ] Position reviews prioritize SELL over BUY
- [ ] Portfolio audits correctly rank holdings
- [ ] LLM responses match query intent 90%+
- [ ] System makes SELL decisions when capital-constrained
- [ ] All tests pass
- [ ] Performance: <2 second prompt generation
- [ ] Documentation complete

---

## 🚀 Rollout Plan

1. **Day 1-5**: Build core infrastructure
2. **Day 6-10**: Implement essential components
3. **Day 11-15**: Integration and testing
4. **Day 16-20**: Deploy to production (parallel mode)
5. **Day 21-25**: Monitor and refine
6. **Day 26-30**: Full cutover, deprecate old system

---

**Ready to begin implementation?** Start with Phase 1, Step 1.1
