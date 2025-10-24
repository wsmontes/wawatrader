# Modular Prompt Architecture Design
## WawaTrader LLM Integration - Complete Redesign

**Created:** 2025-10-24  
**Status:** Design Phase → Implementation Plan  
**Problem:** Hardcoded prompts with limited flexibility and poor context awareness

---

## 🎯 Core Objectives

1. **Composable Prompts**: Build prompts from reusable blocks
2. **Context-Aware**: Different prompts for different scenarios
3. **Bi-directional Communication**: LLM can request specific data
4. **Type Safety**: Structured inputs/outputs with validation
5. **Scalability**: Easy to add new prompt types and data sources

---

## 📊 Current State Analysis

### Problems Identified

1. **Hardcoded Prompt Assembly** (line 245-420 in llm_bridge.py)
   - Single monolithic `create_analysis_prompt()` function
   - Mixed concerns: position management + technical analysis + news
   - Cannot distinguish between: new opportunity vs existing position review
   
2. **Single Query Type** (analyze_market method)
   - Only supports: "Should I trade this stock?"
   - Cannot answer: "What are my weakest holdings?", "Compare these 3 stocks", "Why did this trade fail?"

3. **No LLM Agency**
   - LLM receives all data whether relevant or not
   - Cannot request: "Show me sector rotation data", "Get me last 5 trades on AAPL"
   
4. **Profile System is Too Generic** (lines 33-104)
   - Same system prompt for all query types
   - Aggressive profile says "BUY ANY bullish signal" even for position management

5. **Response Format is Fixed** (lines 370-420)
   - Only supports: sentiment, confidence, action, reasoning, risk_factors
   - Cannot return: rankings, comparisons, explanations, requests for data

---

## 🏗️ New Architecture Design

### 1. Prompt Component System

```python
class PromptComponent:
    """Base class for all prompt components"""
    
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.priority = 1  # Higher = more important
        
    def render(self) -> str:
        """Convert component data to text"""
        raise NotImplementedError
        
    def is_relevant(self, context: QueryContext) -> bool:
        """Should this component be included?"""
        return True
```

### 2. Component Types

#### A. Context Components (Who/What/Why)

```python
# WHO is asking?
class TradingProfileComponent(PromptComponent):
    """Describes trader risk profile and goals"""
    profiles = ['conservative', 'moderate', 'aggressive', 'rotator']
    
# WHAT is the query type?
class QueryTypeComponent(PromptComponent):
    """Defines what kind of analysis is needed"""
    types = [
        'NEW_OPPORTUNITY',      # Should I buy this stock?
        'POSITION_REVIEW',      # Should I hold/sell this position?
        'PORTFOLIO_AUDIT',      # What are my weakest holdings?
        'COMPARATIVE_ANALYSIS', # Compare these N stocks
        'TRADE_POSTMORTEM',     # Why did this trade succeed/fail?
        'MARKET_REGIME',        # What's the current market environment?
        'SECTOR_ROTATION',      # Which sectors are hot/cold?
        'RISK_ASSESSMENT',      # What are my portfolio risks?
    ]
    
# WHY now?
class TriggerComponent(PromptComponent):
    """What triggered this query"""
    triggers = [
        'SCHEDULED_CYCLE',      # Regular 5-min scan
        'CAPITAL_CONSTRAINT',   # Need to free capital
        'PRICE_ALERT',          # Stock hit price level
        'NEWS_EVENT',           # Breaking news detected
        'TECHNICAL_SIGNAL',     # Indicator crossover
        'USER_REQUEST',         # Manual query
    ]
```

#### B. Data Components (Market/Portfolio/Context)

```python
class TechnicalDataComponent(PromptComponent):
    """Technical indicators for 1+ symbols"""
    
    def render(self) -> str:
        # Adaptive detail level based on query type
        if self.context.query_type == 'POSITION_REVIEW':
            return self._detailed_analysis()
        elif self.context.query_type == 'PORTFOLIO_AUDIT':
            return self._summary_comparison()
        return self._standard_indicators()

class PositionDataComponent(PromptComponent):
    """Current position information"""
    
    def render(self) -> str:
        return f"""
        🎯 POSITION DETAILS:
        Entry: {self.data['avg_price']} @ {self.data['entry_date']}
        Current: {self.data['current_price']} (P&L: {self.data['pnl_pct']:+.2f}%)
        Size: {self.data['shares']} shares (${self.data['market_value']:,.0f})
        Duration: {self.data['days_held']} days
        """

class PortfolioSummaryComponent(PromptComponent):
    """Overall portfolio state"""
    
    def render(self) -> str:
        return f"""
        💼 PORTFOLIO STATE:
        Total Value: ${self.data['total_value']:,.0f}
        Buying Power: ${self.data['buying_power']:,.0f} ({self.data['buying_power_pct']:.1f}%)
        Positions: {self.data['num_positions']}
        Top Holdings: {', '.join(self.data['top_3_symbols'])}
        Today's P&L: {self.data['daily_pnl_pct']:+.2f}%
        """

class NewsComponent(PromptComponent):
    """Recent news with relevance filtering"""
    
    def is_relevant(self, context: QueryContext) -> bool:
        # Only include news for specific stocks, not portfolio audits
        return context.query_type in ['NEW_OPPORTUNITY', 'POSITION_REVIEW']

class MarketRegimeComponent(PromptComponent):
    """Broader market conditions"""
    
    def render(self) -> str:
        return f"""
        🌍 MARKET ENVIRONMENT:
        SPY Trend: {self.data['spy_trend']} (RSI: {self.data['spy_rsi']})
        VIX: {self.data['vix_level']} ({self.data['vix_category']})
        Sector Leaders: {', '.join(self.data['hot_sectors'])}
        """

class ComparativeDataComponent(PromptComponent):
    """Side-by-side comparison data"""
    
    def render(self) -> str:
        # Used for COMPARATIVE_ANALYSIS queries
        table = []
        for symbol, metrics in self.data.items():
            table.append(f"{symbol}: RSI {metrics['rsi']}, Trend {metrics['trend']}, P&L {metrics['pnl_pct']:+.1f}%")
        return "\n".join(table)
```

#### C. Instruction Components (Task/Format/Examples)

```python
class TaskInstructionComponent(PromptComponent):
    """What the LLM should do"""
    
    INSTRUCTIONS = {
        'NEW_OPPORTUNITY': """
        TASK: Evaluate if this is a good BUY opportunity right now.
        
        Consider:
        1. Technical setup (trend, momentum, volume)
        2. Entry timing (is this optimal or wait?)
        3. Price targets and stop-loss levels
        4. Risk/reward ratio
        
        You can HOLD if setup is good but timing is poor (e.g., overbought).
        """,
        
        'POSITION_REVIEW': """
        TASK: Evaluate if you should continue holding or SELL this position.
        
        Consider:
        1. Has the technical setup deteriorated?
        2. Is profit target reached or should you let it run?
        3. Are there better opportunities elsewhere?
        4. Is this a weak holding dragging down portfolio?
        
        BE HONEST: Don't hold losers hoping for recovery. Rotate capital actively.
        """,
        
        'PORTFOLIO_AUDIT': """
        TASK: Rank all holdings from STRONGEST to WEAKEST.
        
        For each position, evaluate:
        1. Technical health (is trend intact?)
        2. P&L status (winning or losing?)
        3. Relative strength vs portfolio average
        
        Identify: Top 3 to KEEP, Bottom 3 to SELL
        """,
        
        'COMPARATIVE_ANALYSIS': """
        TASK: Compare these stocks and rank them by attractiveness.
        
        Output format:
        1. BEST: [Symbol] - Reasoning (score: X/100)
        2. GOOD: [Symbol] - Reasoning (score: X/100)
        3. WEAK: [Symbol] - Reasoning (score: X/100)
        """,
    }

class ResponseFormatComponent(PromptComponent):
    """Expected output structure"""
    
    FORMATS = {
        'STANDARD_DECISION': """
        {
          "sentiment": "bullish|bearish|neutral",
          "confidence": 0-100,
          "action": "buy|sell|hold",
          "reasoning": "...",
          "risk_factors": ["..."]
        }
        """,
        
        'RANKING': """
        {
          "ranked_positions": [
            {"symbol": "AAPL", "rank": 1, "score": 95, "action": "keep", "reason": "..."},
            {"symbol": "TSLA", "rank": 2, "score": 85, "action": "hold", "reason": "..."},
            {"symbol": "META", "rank": 10, "score": 45, "action": "sell", "reason": "..."}
          ],
          "summary": "Portfolio has 3 strong positions, 4 neutral, 3 weak to rotate"
        }
        """,
        
        'COMPARISON': """
        {
          "winner": {"symbol": "NVDA", "score": 92, "reason": "..."},
          "runner_up": {"symbol": "AMD", "score": 78, "reason": "..."},
          "avoid": {"symbol": "INTC", "score": 45, "reason": "..."}
        }
        """,
        
        'DATA_REQUEST': """
        {
          "needs_more_data": true,
          "requested_data": [
            {"type": "sector_performance", "timeframe": "1week"},
            {"type": "historical_trades", "symbol": "AAPL", "limit": 5}
          ],
          "reason": "Cannot evaluate sector rotation without sector ETF performance"
        }
        """,
    }
```

### 3. Query Context

```python
@dataclass
class QueryContext:
    """Complete context for a query"""
    
    # Core context
    query_type: str  # NEW_OPPORTUNITY, POSITION_REVIEW, etc.
    trigger: str     # SCHEDULED_CYCLE, CAPITAL_CONSTRAINT, etc.
    profile: str     # conservative, moderate, aggressive
    
    # Symbols involved
    primary_symbol: Optional[str] = None
    comparison_symbols: Optional[List[str]] = None
    
    # Portfolio state
    portfolio_state: Optional[Dict] = None
    
    # Filters
    include_news: bool = True
    include_market_regime: bool = False
    detail_level: str = 'standard'  # minimal, standard, detailed
    
    # Response expectations
    expected_format: str = 'STANDARD_DECISION'
    allow_data_requests: bool = False
```

### 4. Prompt Builder

```python
class PromptBuilder:
    """Assembles prompts from components based on context"""
    
    def __init__(self):
        self.components_registry = {}
        self._register_all_components()
    
    def build(self, context: QueryContext) -> str:
        """Build prompt from context"""
        
        # 1. Select relevant components
        components = self._select_components(context)
        
        # 2. Sort by priority
        components.sort(key=lambda c: c.priority, reverse=True)
        
        # 3. Render each component
        sections = []
        for component in components:
            if component.is_relevant(context):
                sections.append(component.render())
        
        # 4. Assemble final prompt
        prompt = self._assemble_prompt(sections, context)
        
        return prompt
    
    def _select_components(self, context: QueryContext) -> List[PromptComponent]:
        """Choose which components to include"""
        
        components = []
        
        # Always include
        components.append(QueryTypeComponent(context.query_type))
        components.append(TradingProfileComponent(context.profile))
        components.append(TaskInstructionComponent(context.query_type))
        components.append(ResponseFormatComponent(context.expected_format))
        
        # Conditionally include based on query type
        if context.query_type in ['NEW_OPPORTUNITY', 'POSITION_REVIEW']:
            components.append(TechnicalDataComponent(data=...))
            
        if context.query_type == 'POSITION_REVIEW':
            components.append(PositionDataComponent(data=...))
            
        if context.query_type == 'PORTFOLIO_AUDIT':
            components.append(PortfolioSummaryComponent(data=...))
            components.append(ComparativeDataComponent(data=...))
            
        if context.include_market_regime:
            components.append(MarketRegimeComponent(data=...))
            
        if context.include_news:
            components.append(NewsComponent(data=...))
        
        return components
```

### 5. LLM Response Handlers

```python
class ResponseHandler:
    """Parse and validate LLM responses"""
    
    HANDLERS = {
        'STANDARD_DECISION': StandardDecisionHandler,
        'RANKING': RankingHandler,
        'COMPARISON': ComparisonHandler,
        'DATA_REQUEST': DataRequestHandler,
    }
    
    @classmethod
    def parse(cls, response: str, expected_format: str) -> Dict[str, Any]:
        handler = cls.HANDLERS.get(expected_format)
        if not handler:
            raise ValueError(f"Unknown format: {expected_format}")
        
        return handler.parse(response)

class DataRequestHandler:
    """Handle when LLM requests more data"""
    
    @staticmethod
    def parse(response: str) -> Dict[str, Any]:
        data = json.loads(response)
        
        if data.get('needs_more_data'):
            # LLM is asking for specific data
            return {
                'type': 'DATA_REQUEST',
                'requests': data['requested_data'],
                'reason': data['reason']
            }
        
        return data
```

---

## 🎬 Usage Examples

### Example 1: New Opportunity Scan

```python
# Context: Regular trading cycle, found bullish signal
context = QueryContext(
    query_type='NEW_OPPORTUNITY',
    trigger='TECHNICAL_SIGNAL',
    profile='aggressive',
    primary_symbol='NVDA',
    include_news=True,
    include_market_regime=False,
    expected_format='STANDARD_DECISION'
)

prompt = prompt_builder.build(context)
response = llm.query(prompt)
decision = ResponseHandler.parse(response, 'STANDARD_DECISION')
```

**Generated Prompt:**
```
⚡ QUERY TYPE: NEW OPPORTUNITY
🎯 PROFILE: Aggressive Trader (High-octane, quick decisions)
🔔 TRIGGER: Technical Signal Detected

📊 TECHNICAL DATA: NVDA
Price: $850.50 (bullish trend)
RSI: 62 (positive momentum)
Volume: 1.8x average (strong conviction)
...

📰 RECENT NEWS:
• NVIDIA announces new AI chip series
• Data center demand surges 40% YoY

⚡ TASK: Evaluate if this is a good BUY opportunity right now...

📋 RESPONSE FORMAT:
{
  "sentiment": "bullish|bearish|neutral",
  "confidence": 0-100,
  "action": "buy|sell|hold",
  ...
}
```

### Example 2: Portfolio Audit (Capital Constrained)

```python
context = QueryContext(
    query_type='PORTFOLIO_AUDIT',
    trigger='CAPITAL_CONSTRAINT',
    profile='rotator',  # New profile: active capital rotation
    portfolio_state=portfolio_data,
    include_news=False,
    include_market_regime=True,
    expected_format='RANKING'
)

prompt = prompt_builder.build(context)
response = llm.query(prompt)
rankings = ResponseHandler.parse(response, 'RANKING')

# Now we know which positions to SELL
for pos in rankings['ranked_positions']:
    if pos['action'] == 'sell':
        execute_sell(pos['symbol'])
```

**Generated Prompt:**
```
⚡ QUERY TYPE: PORTFOLIO AUDIT
🎯 PROFILE: Active Rotator (Continuous capital reallocation)
🔔 TRIGGER: Capital Constraint ($592 buying power, need to free capital)

💼 PORTFOLIO STATE:
Total: $100,547
Positions: 10
Buying Power: $592 (0.6% - CRITICAL)

🌍 MARKET ENVIRONMENT:
SPY: Bullish (RSI 58)
VIX: 14 (Low volatility)
Hot Sectors: Technology, Financial

📊 COMPARATIVE DATA:
AAPL: RSI 52, Bullish, P&L +0.13%
MSFT: RSI 54, Bullish, P&L +0.38%
TSLA: RSI 48, Neutral, P&L -1.2%
...

⚡ TASK: Rank all holdings from STRONGEST to WEAKEST...
Identify: Top 3 to KEEP, Bottom 3 to SELL

📋 RESPONSE FORMAT:
{
  "ranked_positions": [
    {"symbol": "...", "rank": 1, "score": 95, "action": "keep", "reason": "..."},
    ...
  ]
}
```

### Example 3: LLM Requests More Data

```python
context = QueryContext(
    query_type='SECTOR_ROTATION',
    trigger='USER_REQUEST',
    profile='moderate',
    expected_format='DATA_REQUEST',
    allow_data_requests=True  # Enable LLM to ask for data
)

prompt = prompt_builder.build(context)
response = llm.query(prompt)
result = ResponseHandler.parse(response, 'DATA_REQUEST')

if result['type'] == 'DATA_REQUEST':
    # LLM needs more data
    for request in result['requests']:
        if request['type'] == 'sector_performance':
            data = get_sector_etf_performance(request['timeframe'])
            # Re-query with additional data
            context.add_data('sector_performance', data)
            prompt = prompt_builder.build(context)
            response = llm.query(prompt)
```

---

## 📋 Implementation Plan

### Phase 1: Core Infrastructure (Week 1)
- [ ] Create `PromptComponent` base class
- [ ] Implement `QueryContext` dataclass
- [ ] Build `PromptBuilder` with component registry
- [ ] Create 5 basic components:
  - QueryTypeComponent
  - TradingProfileComponent  
  - TechnicalDataComponent
  - TaskInstructionComponent
  - ResponseFormatComponent

### Phase 2: Essential Query Types (Week 1-2)
- [ ] Implement `NEW_OPPORTUNITY` query type
- [ ] Implement `POSITION_REVIEW` query type
- [ ] Implement `PORTFOLIO_AUDIT` query type
- [ ] Create corresponding response handlers
- [ ] Update trading_agent.py to use new system

### Phase 3: Advanced Features (Week 2-3)
- [ ] Add `COMPARATIVE_ANALYSIS` query type
- [ ] Add `TRADE_POSTMORTEM` query type
- [ ] Implement bi-directional communication (DATA_REQUEST)
- [ ] Add MarketRegimeComponent
- [ ] Add sector rotation support

### Phase 4: Optimization (Week 3-4)
- [ ] Add prompt caching for common queries
- [ ] Implement adaptive detail levels
- [ ] Add prompt templates library
- [ ] Performance testing and refinement

### Phase 5: New Trading Profiles (Week 4)
- [ ] Create 'rotator' profile (aggressive capital rotation)
- [ ] Create 'momentum' profile (chase trends)
- [ ] Create 'mean_reversion' profile (buy dips)
- [ ] Profile-specific response validation

---

## 🎯 Success Metrics

1. **Flexibility**: Can create 20+ distinct prompt types from components
2. **Context Awareness**: LLM gives different advice for same stock in different contexts
3. **Actionability**: System makes SELL decisions when capital-constrained
4. **Clarity**: LLM responses match query intent 95%+ of the time
5. **Extensibility**: Adding new query type takes <30 minutes

---

## 🔄 Migration Strategy

1. **Parallel System**: Build new system alongside old
2. **A/B Testing**: Compare old vs new prompt quality
3. **Gradual Rollout**: Start with NEW_OPPORTUNITY, then POSITION_REVIEW, etc.
4. **Fallback Mode**: Keep old system as backup during transition
5. **Full Cutover**: Replace old LLMBridge once all query types working

---

## 📚 File Structure

```
wawatrader/
├── llm/
│   ├── __init__.py
│   ├── bridge.py              # Main LLMBridge (refactored)
│   ├── components/
│   │   ├── __init__.py
│   │   ├── base.py           # PromptComponent base class
│   │   ├── context.py        # Context components
│   │   ├── data.py           # Data components
│   │   ├── instructions.py   # Instruction components
│   ├── builders/
│   │   ├── __init__.py
│   │   ├── prompt_builder.py
│   │   ├── query_context.py
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── response_handler.py
│   │   ├── decision_handler.py
│   │   ├── ranking_handler.py
│   │   ├── comparison_handler.py
│   │   ├── data_request_handler.py
│   └── profiles/
│       ├── __init__.py
│       ├── base_profile.py
│       ├── conservative.py
│       ├── aggressive.py
│       └── rotator.py
```

---

## 💡 Key Insights

1. **Separation of Concerns**: Query type, data, instructions are independent
2. **Composability**: Combine components in any order/combination
3. **Type Safety**: QueryContext ensures valid queries
4. **Testability**: Each component can be tested independently
5. **Scalability**: Add new components without touching existing code
6. **Intelligence**: LLM can request exactly what it needs

---

**Next Step**: Review this design, then begin Phase 1 implementation.
