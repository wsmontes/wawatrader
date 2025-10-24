# Modular Prompt System - Quick Reference

## ✅ Implementation Status: Phase 2 COMPLETE

### What's Been Implemented

**Phase 1: Core Infrastructure** ✅
- Component system with 9 types
- Query context with 8 query types
- 6 trading profiles (including "rotator")
- PromptBuilder for assembly

**Phase 2: Response Handlers** ✅
- StandardDecisionHandler for BUY/SELL/HOLD
- RankingHandler for portfolio audits
- ComparisonHandler for comparative analysis
- Quality scoring for all responses

**Phase 3: Integration** ✅
- ModularLLMAnalyzer (llm_v2.py)
- Integration with LLMBridge (analyze_market_v2, audit_portfolio_v2, compare_opportunities_v2)
- Trading agent updated to use modular system
- Configuration flag: `use_modular_prompts` (default: True)

---

## 🎯 Key Features

### Context-Aware Prompts
Same stock gets different prompts based on context:

- **NEW_OPPORTUNITY**: "Should I BUY this new stock?"
- **POSITION_REVIEW**: "I OWN 114 shares @ $263.46. SELL or HOLD?"
- **PORTFOLIO_AUDIT**: "Rank all holdings, identify rotation candidates"

### Capital Rotation Support
**"rotator" profile** with special features:
- Lower SELL threshold (40% vs 45% aggressive)
- Explicit bias: "Prioritize SELL decisions for capital rotation"
- Guidance: "Small profits are valid - rotate early and often"

### Intelligent Triggers
System automatically detects context:
- `CAPITAL_CONSTRAINT`: Buying power < 5% → urgent rotation needed
- `SCHEDULED_CYCLE`: Normal scanning cycle
- `TECHNICAL_SIGNAL`: Strong indicator crossed threshold
- `PERFORMANCE_CONCERN`: Position underwater or underperforming

---

## 📖 Usage Examples

### 1. Analyze New Opportunity
```python
from wawatrader.llm_bridge import LLMBridge

bridge = LLMBridge()

# Automatically routes to NEW_OPPORTUNITY if no position
result = bridge.analyze_market_v2(
    symbol='NVDA',
    signals=technical_signals,
    news=news_articles,
    trigger='SCHEDULED_CYCLE',
    use_modular=True  # Use new system
)

# Result includes:
# - action: 'buy' | 'sell' | 'hold'
# - confidence: 0-100
# - reasoning: "Strong bullish momentum with RSI 68..."
# - risk_factors: ["[HIGH]: Overbought conditions", ...]
# - quality_scores: {decisiveness: 85, specificity: 78, ...}
```

### 2. Review Existing Position
```python
# Automatically routes to POSITION_REVIEW if position exists
result = bridge.analyze_market_v2(
    symbol='AAPL',
    signals=technical_signals,
    current_position={
        'qty': 114,
        'avg_entry_price': 263.46,
        'current_price': 263.81
    },
    portfolio_summary={
        'total_value': 100547,
        'buying_power': 592,  # Only $592 left!
        'num_positions': 10,
    },
    trigger='CAPITAL_CONSTRAINT',  # Low buying power
    use_modular=True
)

# Prompt will emphasize:
# - "YOU ALREADY OWN 114 shares"
# - "P&L: +0.13% (small profit)"
# - "Capital constrained - rotate to better opportunities?"
# - "Should you SELL or HOLD?"
```

### 3. Audit Portfolio
```python
# Rank all positions for rotation
result = bridge.audit_portfolio_v2(
    positions=[
        {
            'symbol': 'NVDA',
            'qty': 30,
            'avg_entry_price': 120.50,
            'current_price': 138.20,
            'technical': {...}
        },
        {
            'symbol': 'AAPL',
            'qty': 114,
            'avg_entry_price': 263.46,
            'current_price': 263.81,
            'technical': {...}
        },
        # ... more positions
    ],
    portfolio_summary={
        'total_value': 100547,
        'buying_power': 592,
    },
    trigger='CAPITAL_CONSTRAINT'
)

# Result includes:
# - ranked_positions: [
#     {symbol: 'NVDA', rank: 1, score: 92, action: 'keep', reason: "..."},
#     {symbol: 'AAPL', rank: 8, score: 52, action: 'sell', reason: "..."},
#   ]
# - summary: "Portfolio heavily concentrated, rotate capital from weak positions"
```

### 4. Compare Opportunities
```python
# Compare multiple stocks
result = bridge.compare_opportunities_v2(
    symbols=['NVDA', 'AAPL', 'MSFT'],
    signals_dict={
        'NVDA': technical_signals_nvda,
        'AAPL': technical_signals_aapl,
        'MSFT': technical_signals_msft,
    },
    news_dict={
        'NVDA': news_nvda,
        'AAPL': news_aapl,
        'MSFT': news_msft,
    },
    trigger='SCHEDULED_CYCLE'
)

# Result includes:
# - rankings: [{symbol: 'NVDA', rank: 1, verdict: 'best', ...}, ...]
# - winner: 'NVDA'
# - avoid: ['AAPL']
# - recommendation: "Buy NVDA over alternatives due to..."
```

---

## ⚙️ Configuration

### Enable/Disable Modular System

In `.env` file:
```bash
# Enable new modular prompt system (default: True)
LM_STUDIO_USE_MODULAR_PROMPTS=true

# Trading profile (affects confidence thresholds and behavior)
LM_STUDIO_TRADING_PROFILE=rotator  # or: conservative, moderate, aggressive, maximum
```

In Python:
```python
from config.settings import settings

# Check current setting
print(settings.lm_studio.use_modular_prompts)  # True

# Change profile dynamically
settings.lm_studio.trading_profile = 'rotator'
```

### Trading Profiles

| Profile | Min Buy Conf | Min Sell Conf | Special Features |
|---------|-------------|---------------|------------------|
| **conservative** | 75% | 70% | Capital preservation, high-probability only |
| **moderate** | 65% | 60% | Balanced risk/reward |
| **aggressive** | 55% | 50% | Active trading, momentum focus |
| **rotator** | 60% | 40% | 🔥 **Lower SELL threshold**, prioritize rotation |
| **maximum** | 50% | 40% | Same as rotator + maximum risk acceptance |
| **momentum** | 55% | 50% | Chase trends, ride winners |
| **value** | 70% | 65% | Contrarian, mean reversion |

**💡 Recommendation**: Use **"rotator"** profile when capital is constrained and you need to actively rotate positions for maximum opportunities.

---

## 🔄 Migration Path

### Gradual Rollout (A/B Testing)

**Current State**: Both systems coexist
- **Legacy system** (V1): Hardcoded prompts in `llm_bridge.analyze_market()`
- **Modular system** (V2): Context-aware prompts in `llm_bridge.analyze_market_v2()`

**Switching Between Systems**:

```python
# Option 1: Configuration flag
settings.lm_studio.use_modular_prompts = True   # Use V2
settings.lm_studio.use_modular_prompts = False  # Use V1

# Option 2: Explicit method call
result_v1 = bridge.analyze_market(symbol, signals, news, position)
result_v2 = bridge.analyze_market_v2(symbol, signals, news, position, use_modular=True)

# Option 3: Trading agent respects configuration automatically
# (Just set use_modular_prompts=True in .env)
```

### Testing Checklist

- [x] **Phase 1**: Core infrastructure works
- [x] **Phase 2**: Response handlers parse correctly
- [x] **Phase 3**: Integration with existing code
- [ ] **Phase 4**: Test NEW_OPPORTUNITY query
- [ ] **Phase 5**: Test POSITION_REVIEW query  
- [ ] **Phase 6**: Test PORTFOLIO_AUDIT query
- [ ] **Phase 7**: Test capital rotation with "rotator" profile
- [ ] **Phase 8**: Compare quality scores V1 vs V2
- [ ] **Phase 9**: Production deployment

---

## 🎨 Component Architecture

### Available Components (9 types)

1. **QueryTypeComponent** (priority: 10)
   - Shows what kind of query this is
   - Example: "🎯 QUERY TYPE: POSITION REVIEW"

2. **TriggerComponent** (priority: 9)
   - Shows what triggered the analysis
   - Example: "🔔 TRIGGER: Capital Constraint ⚡ URGENT"

3. **TradingProfileComponent** (priority: 9)
   - Shows active trading profile and strategy
   - Example: "🎯 PROFILE: Active Rotator (prioritize SELL, 40% threshold)"

4. **TechnicalDataComponent** (priority: 8)
   - Adaptive rendering based on context
   - Formats: standard, summary, minimal, detailed
   - Shows: price, trend, RSI, MACD, volume, ATR, Bollinger Bands

5. **PositionDataComponent** (priority: 8)
   - Shows existing position context
   - Example: "⚠️ YOU OWN: 114 shares @ $263.46, P&L: +0.13%"

6. **PortfolioSummaryComponent** (priority: 7)
   - Shows portfolio state and capital status
   - Example: "🔴 CRITICAL: $592 buying power (0.59% - nearly fully invested)"

7. **NewsComponent** (priority: 6)
   - Recent news with relevance filtering
   - Max 3 articles, technical priority guidance

8. **TaskInstructionComponent** (priority: 6)
   - Detailed task instructions for query type
   - Example: "Should you SELL or HOLD? Don't hold losers hoping for recovery."

9. **ResponseFormatComponent** (priority: 1)
   - JSON structure definition
   - Ensures consistent response format

### Query Types (8 types)

1. **NEW_OPPORTUNITY** - Evaluate new stock for BUY
2. **POSITION_REVIEW** - Existing position, SELL or HOLD?
3. **PORTFOLIO_AUDIT** - Rank all holdings
4. **COMPARATIVE_ANALYSIS** - Compare multiple stocks
5. **TRADE_POSTMORTEM** - Learn from past trade
6. **MARKET_REGIME** - Overall market condition
7. **SECTOR_ROTATION** - Sector-level analysis
8. **RISK_ASSESSMENT** - Risk evaluation

### Response Formats (3 types)

1. **STANDARD_DECISION** - Single stock decision
2. **RANKING** - Multiple positions ranked
3. **COMPARISON** - Side-by-side comparison

---

## 🐛 Troubleshooting

### Issue: LLM still recommending BUY for existing positions

**Solution**: Check if modular system is enabled
```python
from config.settings import settings
print(settings.lm_studio.use_modular_prompts)  # Should be True
```

### Issue: Not seeing capital rotation

**Solution**: Switch to "rotator" profile
```bash
# In .env
LM_STUDIO_TRADING_PROFILE=rotator
```

### Issue: Quality scores too low

**Check**:
- Decisiveness: Is LLM giving clear BUY/SELL or too many HOLDs?
- Specificity: Does reasoning include price levels and indicators?
- Risk awareness: Are risk factors identified with severity tags?

### Issue: Modular system not being used

**Debug**:
```python
# Check configuration
from config.settings import settings
print(f"Modular enabled: {settings.lm_studio.use_modular_prompts}")
print(f"Profile: {settings.lm_studio.trading_profile}")

# Test modular analyzer directly
from wawatrader.llm_v2 import ModularLLMAnalyzer
analyzer = ModularLLMAnalyzer()

# Preview prompt components
from wawatrader.llm.builders.prompt_builder import PromptBuilder
from wawatrader.llm.components.base import QueryContext

context = QueryContext(
    query_type='POSITION_REVIEW',
    trigger='CAPITAL_CONSTRAINT',
    profile='rotator',
    primary_symbol='AAPL'
)

builder = PromptBuilder()
preview = builder.preview_components(context, {})
print(preview)  # Shows which components will be used
```

---

## 📊 Quality Metrics

Each response includes quality scores:

### Standard Decision Scores
- **decisiveness** (0-100): Clear action vs indecisive HOLD
- **specificity** (0-100): Price levels and indicators mentioned
- **risk_awareness** (0-100): Risks identified with severity tags
- **reasoning_depth** (0-100): Detailed vs generic reasoning
- **overall** (0-100): Weighted average

### Ranking Scores
- **rank_distribution** (0-100): Sequential ranks without gaps
- **score_separation** (0-100): Clear score differences
- **action_clarity** (0-100): Good KEEP/HOLD/SELL distribution
- **reasoning_quality** (0-100): Specific vs generic reasons
- **overall** (0-100): Weighted average

### Comparison Scores
- **decisiveness** (0-100): Clear winner/loser identified
- **differentiation** (0-100): Score spread between options
- **reasoning_clarity** (0-100): Comparative terms used
- **recommendation_strength** (0-100): Decisive language
- **overall** (0-100): Weighted average

**Target**: Overall score > 70 indicates good quality decision

---

## 🚀 Next Steps

1. **Test in Production**: Run with `use_modular_prompts=True`
2. **Monitor Quality Scores**: Track improvements over legacy system
3. **Tune Profiles**: Adjust confidence thresholds based on results
4. **Add Advanced Features**:
   - Bi-directional communication (LLM requests more data)
   - Trade postmortem analysis
   - Sector rotation support
   - Market regime detection

---

## 📝 File Structure

```
wawatrader/
├── llm/                          # NEW: Modular prompt system
│   ├── __init__.py
│   ├── components/
│   │   ├── __init__.py
│   │   ├── base.py              # QueryContext, PromptComponent
│   │   ├── context.py           # QueryType, Trigger
│   │   ├── data.py              # Technical, Position, Portfolio, News
│   │   └── instructions.py      # Task, ResponseFormat
│   ├── profiles/
│   │   ├── __init__.py
│   │   └── base_profile.py      # TradingProfile (6 profiles)
│   ├── builders/
│   │   ├── __init__.py
│   │   └── prompt_builder.py    # PromptBuilder (assembly logic)
│   └── handlers/
│       ├── __init__.py
│       ├── base_handler.py      # ResponseHandler (base)
│       ├── standard_handler.py  # StandardDecisionHandler
│       ├── ranking_handler.py   # RankingHandler
│       └── comparison_handler.py # ComparisonHandler
├── llm_v2.py                    # NEW: ModularLLMAnalyzer (main interface)
├── llm_bridge.py                # UPDATED: Added analyze_market_v2(), etc.
└── trading_agent.py             # UPDATED: Uses modular system if enabled

config/
└── settings.py                  # UPDATED: Added use_modular_prompts flag

docs/
├── MODULAR_PROMPT_QUICKREF.md   # THIS FILE
├── MODULAR_PROMPT_ARCHITECTURE.md
├── IMPLEMENTATION_PLAN_MODULAR_PROMPTS.md
├── MODULAR_PROMPTS_EXECUTIVE_SUMMARY.md
└── MODULAR_PROMPTS_VISUAL_GUIDE.md
```

---

**Status**: ✅ Ready for testing
**Last Updated**: Current session
**Author**: AI Assistant + User Collaboration
