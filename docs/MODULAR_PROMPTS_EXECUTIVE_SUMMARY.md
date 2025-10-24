# Modular Prompt Architecture - Executive Summary

## 🎯 Vision

Transform WawaTrader's LLM system from **hardcoded prompts** to a **composable, context-aware architecture** that can handle thousands of different scenarios through intelligent prompt assembly.

---

## ❌ Current Problems

1. **Single prompt for everything** - Same format whether evaluating new stock or reviewing existing position
2. **LLM says BUY for everything** - Aggressive profile overrides position management context
3. **No portfolio intelligence** - Can't answer "What are my weakest holdings?"
4. **No LLM agency** - Cannot request additional data it needs
5. **Hardcoded strings** - Adding new query type requires rewriting entire prompt function

---

## ✅ New Solution: Component-Based Architecture

### Core Concept: Prompts = LEGO Blocks

```
QueryContext (what we want to know)
     ↓
PromptBuilder (assembles relevant blocks)
     ↓
[QueryType] + [Profile] + [Data] + [Instructions] + [Format]
     ↓
Complete, context-aware prompt
     ↓
LLM Response
     ↓
Structured handler (different for each query type)
```

### Example: Same Stock, Different Contexts

**Context 1: NEW_OPPORTUNITY (scanning watchlist)**
```
🎯 QUERY TYPE: NEW OPPORTUNITY EVALUATION
🎯 PROFILE: Aggressive Trader
📊 TECHNICAL DATA: AAPL
   Price: $263.81, Bullish trend, RSI 52

⚡ TASK: Should I BUY this stock?
```

**Context 2: POSITION_REVIEW (already own it)**
```
💼 QUERY TYPE: POSITION REVIEW
🎯 PROFILE: Active Rotator
💼 POSITION DETAILS: AAPL
   YOU ALREADY OWN: 114 shares @ $263.46
   P&L: +0.13% (flat)
📊 TECHNICAL DATA: Trend weakening

⚡ TASK: Should I SELL this position to rotate capital?
   Compare against other opportunities, not absolute merit
```

**Context 3: PORTFOLIO_AUDIT (capital constrained)**
```
📊 QUERY TYPE: PORTFOLIO AUDIT
🔔 TRIGGER: Capital Constraint ($592 buying power)
💼 PORTFOLIO: 10 positions, all data included

⚡ TASK: Rank all holdings. Which 3 should I SELL?
```

---

## 🏗️ Architecture Components

### 1. Query Types (What to ask)
- `NEW_OPPORTUNITY` - Should I buy this new stock?
- `POSITION_REVIEW` - Should I hold/sell this existing position?
- `PORTFOLIO_AUDIT` - Rank all holdings strongest → weakest
- `COMPARATIVE_ANALYSIS` - Compare 3 stocks, which is best?
- `TRADE_POSTMORTEM` - Why did this trade succeed/fail?
- `MARKET_REGIME` - What's the current market environment?
- `SECTOR_ROTATION` - Which sectors are hot/cold?

### 2. Components (Building Blocks)

**Context Components** (who/what/why)
- QueryTypeComponent
- TriggerComponent  
- TradingProfileComponent

**Data Components** (market/portfolio)
- TechnicalDataComponent (adaptive detail level)
- PositionDataComponent (P&L, entry, status)
- PortfolioSummaryComponent (overall state)
- NewsComponent (filtered by relevance)
- MarketRegimeComponent (SPY, VIX, sectors)
- ComparativeDataComponent (side-by-side tables)

**Instruction Components** (task/format)
- TaskInstructionComponent (what to do)
- ResponseFormatComponent (expected structure)

### 3. Trading Profiles (Personality)

- **Conservative** - High confidence required, capital preservation
- **Moderate** - Balanced risk/reward
- **Aggressive** - Quick decisions, high risk tolerance
- **Rotator** - NEW! Continuously reallocate capital to best opportunities
  - Lower bar for SELL (40% confidence vs 45%)
  - Prioritizes position management over new entries
  - Compares positions vs each other, not absolute merit

### 4. Response Handlers (Parse outputs)

- `StandardDecisionHandler` - {action, confidence, reasoning}
- `RankingHandler` - {ranked_positions[...], summary}
- `ComparisonHandler` - {winner, runner_up, avoid}
- `DataRequestHandler` - {needs_more_data, requested_data[]}

---

## 💡 Key Innovations

### 1. Context-Aware Prompts

Same stock, different questions → different prompts → different answers

### 2. Bi-Directional Communication

LLM can respond:
```json
{
  "needs_more_data": true,
  "requested_data": [
    {"type": "sector_performance", "timeframe": "1week"},
    {"type": "historical_trades", "symbol": "AAPL"}
  ],
  "reason": "Cannot evaluate sector rotation without ETF data"
}
```

### 3. Adaptive Detail Levels

- `PORTFOLIO_AUDIT` → Compact summaries for 10 stocks
- `POSITION_REVIEW` → Full technical details + P&L context
- `NEW_OPPORTUNITY` → Focus on entry timing

### 4. Profile-Specific Logic

**Rotator Profile** special rules:
```python
'special_rules': [
    'Prioritize SELL decisions when evaluating existing positions',
    'Compare position vs other opportunities, not just absolute merit',
    'Small profits are still profits - rotate early and often',
]
```

---

## 📋 Implementation Plan

### Phase 1: Core Infrastructure (Week 1)
- PromptComponent base class
- QueryContext dataclass
- PromptBuilder
- Basic components (QueryType, Profile, Task, Format)

### Phase 2: Essential Query Types (Week 1-2)
- NEW_OPPORTUNITY implementation
- POSITION_REVIEW implementation
- PORTFOLIO_AUDIT implementation
- Response handlers

### Phase 3: Integration (Week 2-3)
- Update LLMBridge with analyze_market_v2()
- Update trading_agent.py to use new query types
- Parallel testing (old vs new system)

### Phase 4: Advanced Features (Week 3-4)
- Bi-directional communication
- Sector rotation support
- Trade postmortem analysis
- Market regime detection

---

## 🎯 Success Metrics

1. **Flexibility**: Generate 20+ distinct prompt types ✅
2. **Context Awareness**: Different advice for same stock in different contexts ✅
3. **Actionability**: Makes SELL decisions when capital-constrained ✅
4. **Intent Matching**: LLM responses match query intent 95%+ ✅
5. **Extensibility**: Add new query type in <30 minutes ✅

---

## 🚀 Expected Benefits

### For the System
- **Modularity**: Add new query types without touching existing code
- **Testability**: Each component tested independently
- **Maintainability**: Clear separation of concerns
- **Scalability**: Thousands of prompt combinations from ~20 components

### For Trading Performance
- **Better SELL decisions**: Position-aware prompts prioritize rotation
- **Capital efficiency**: Portfolio audits identify weak holdings
- **Comparative analysis**: Can rank opportunities instead of binary yes/no
- **Learning capability**: Trade postmortems improve future decisions

### For Future Development
- **Multi-LLM support**: Different LLMs for different query types
- **A/B testing**: Compare prompt strategies easily
- **Prompt optimization**: Machine learning on component combinations
- **User customization**: Custom profiles and components

---

## 📂 File Structure

```
wawatrader/
├── llm/                          # NEW module
│   ├── __init__.py
│   ├── bridge.py                # Refactored LLMBridge
│   ├── components/
│   │   ├── base.py             # PromptComponent, QueryContext
│   │   ├── context.py          # QueryType, Trigger
│   │   ├── data.py             # Technical, Position, Portfolio
│   │   ├── instructions.py     # Task, Format
│   ├── builders/
│   │   ├── prompt_builder.py   # PromptBuilder
│   ├── handlers/
│   │   ├── response_handler.py # Base handler
│   │   ├── decision_handler.py # Standard decisions
│   │   ├── ranking_handler.py  # Portfolio audits
│   │   ├── comparison_handler.py
│   │   ├── data_request_handler.py
│   └── profiles/
│       ├── base_profile.py     # TradingProfileComponent
│       ├── conservative.py
│       ├── aggressive.py
│       └── rotator.py          # NEW profile
```

---

## 🔄 Migration Strategy

1. **Build in parallel** - New system alongside old
2. **A/B test** - Compare prompt quality
3. **Gradual rollout** - One query type at a time
4. **Keep fallback** - Old system as backup
5. **Full cutover** - Replace llm_bridge.py when ready

**Risk Level**: MEDIUM (parallel system allows safe testing)

---

## 📚 Documentation

- **Architecture**: `docs/MODULAR_PROMPT_ARCHITECTURE.md` (complete design)
- **Implementation**: `docs/IMPLEMENTATION_PLAN_MODULAR_PROMPTS.md` (step-by-step code)
- **This File**: Executive summary for decision-making

---

## ✅ Next Steps

1. **Review** this design with team/stakeholders
2. **Approve** architecture and timeline
3. **Begin Phase 1** - Core infrastructure (5 days)
4. **Test incrementally** - Don't wait for full completion
5. **Deploy gradually** - Start with NEW_OPPORTUNITY query type

---

**Question**: Ready to transform WawaTrader's intelligence layer? 🚀

**Estimated Impact**: 10x more flexible, 5x more context-aware, infinite scalability
