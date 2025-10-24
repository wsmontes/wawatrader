# Modular Prompt Architecture - Visual Guide

## 🎨 System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      TRADING AGENT                              │
│  "I need to know: Should I sell AAPL?"                          │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    QUERY CONTEXT                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ query_type = 'POSITION_REVIEW'                           │  │
│  │ trigger = 'CAPITAL_CONSTRAINT'                           │  │
│  │ profile = 'rotator'                                      │  │
│  │ primary_symbol = 'AAPL'                                  │  │
│  │ expected_format = 'STANDARD_DECISION'                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                   PROMPT BUILDER                                │
│  "Let me select the right components..."                        │
│                                                                  │
│  Component Selection Logic:                                     │
│  ├─ ALWAYS: QueryType, Trigger, Profile, Task, Format          │
│  ├─ IF position review: Add PositionData                        │
│  ├─ IF technical analysis: Add TechnicalData                    │
│  └─ IF capital constraint: Add PortfolioSummary                 │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│               SELECTED COMPONENTS                               │
│  (Priority: High → Low)                                         │
│                                                                  │
│  [10] QueryTypeComponent('POSITION_REVIEW')                     │
│  [ 9] TriggerComponent('CAPITAL_CONSTRAINT')                    │
│  [ 9] TradingProfileComponent('rotator')                        │
│  [ 8] PositionDataComponent({qty: 114, pnl: +0.13%})           │
│  [ 8] TechnicalDataComponent({rsi: 52, trend: bullish})        │
│  [ 6] TaskInstructionComponent('POSITION_REVIEW')               │
│  [ 1] ResponseFormatComponent('STANDARD_DECISION')              │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                ASSEMBLED PROMPT                                 │
│                                                                  │
│  💼 QUERY TYPE: POSITION REVIEW                                 │
│  🔔 TRIGGER: Capital Constraint ($592 available)                │
│  🎯 PROFILE: Active Rotator                                     │
│      • Lower bar for SELL (40% confidence)                      │
│      • Prioritize rotation over holding                         │
│                                                                  │
│  💼 POSITION DETAILS: AAPL                                      │
│      YOU ALREADY OWN: 114 shares @ $263.46                      │
│      Current: $263.81, P&L: +0.13%                             │
│      Status: SMALL PROFIT (evaluate rotation opportunity)       │
│                                                                  │
│  📊 TECHNICAL DATA: AAPL                                        │
│      Price: $263.81, Bullish trend                             │
│      RSI: 52 (neutral)                                         │
│                                                                  │
│  ⚡ TASK: Should you HOLD or SELL this position?               │
│      Compare against other opportunities                        │
│      Small profits are still profits - rotate if better exists  │
│                                                                  │
│  📋 RESPONSE FORMAT: {action, confidence, reasoning...}         │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                      LLM (Gemma 3)                              │
│  "Processing context-aware prompt..."                           │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                   LLM RESPONSE                                  │
│  {                                                              │
│    "sentiment": "neutral",                                      │
│    "confidence": 55,                                            │
│    "action": "sell",                                            │
│    "reasoning": "Position flat (+0.13%), RSI neutral. With     │
│                  capital constrained, rotate to better          │
│                  opportunities. NVDA showing stronger setup.",  │
│    "risk_factors": [...]                                        │
│  }                                                              │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│              RESPONSE HANDLER                                   │
│  StandardDecisionHandler validates and parses JSON              │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                 TRADING DECISION                                │
│  action='sell', confidence=55, reasoning='...'                  │
│  → Execute SELL for AAPL                                        │
│  → Free $30,000+ capital for better opportunities               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Comparison: Old vs New System

### OLD SYSTEM (Current)

```
Trading Agent
    │
    ├─ analyze_symbol('AAPL')
    │       │
    │       └─ create_analysis_prompt()  ← SINGLE FUNCTION
    │               │
    │               └─ Hardcoded prompt with all sections
    │                   "You are aggressive trader..." (SYSTEM PROMPT)
    │                   "Recommend BUY on ANY bullish signal"
    │                   Technical data
    │                   Position data (maybe)
    │                   Task: "Should I trade this?"
    │                       │
    │                       ▼
    │                   PROBLEM: Same prompt whether:
    │                   - New opportunity (should say BUY)
    │                   - Existing position (should consider SELL)
    │                   - Portfolio audit (need ranking)
    │
    └─ LLM Response: "BUY" (even for existing positions!)
```

### NEW SYSTEM (Modular)

```
Trading Agent
    │
    ├─ For new stock: query_type='NEW_OPPORTUNITY'
    │       │
    │       └─ Prompt emphasizes: "Should I BUY?"
    │           Components: QueryType + Technical + Task(BUY focus)
    │               │
    │               └─ LLM Response: "BUY" ✅ Correct!
    │
    ├─ For existing position: query_type='POSITION_REVIEW'
    │       │
    │       └─ Prompt emphasizes: "Should I SELL or HOLD?"
    │           Components: QueryType + Position + Technical + Task(SELL focus)
    │               │
    │               └─ LLM Response: "SELL" or "HOLD" ✅ Context-aware!
    │
    └─ For portfolio: query_type='PORTFOLIO_AUDIT'
            │
            └─ Prompt emphasizes: "Rank all holdings"
                Components: QueryType + Portfolio + Comparative + Task(Ranking)
                    │
                    └─ LLM Response: Ranked list ✅ Right format!
```

---

## 🎯 Component Interaction Map

```
┌─────────────────────────────────────────────────────────────────┐
│                     QUERY CONTEXT                               │
│  (Defines WHAT we want to know)                                 │
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐   │
│  │  Query Type    │  │    Trigger     │  │    Profile     │   │
│  │ ───────────    │  │ ───────────    │  │ ───────────    │   │
│  │ NEW_OPP        │  │ SCHEDULED      │  │ conservative   │   │
│  │ POS_REVIEW     │  │ CAPITAL_LOW    │  │ moderate       │   │
│  │ PORTFOLIO      │  │ PRICE_ALERT    │  │ aggressive     │   │
│  │ COMPARISON     │  │ NEWS_EVENT     │  │ rotator        │   │
│  └────────────────┘  └────────────────┘  └────────────────┘   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  COMPONENT REGISTRY                             │
│  (Available building blocks)                                    │
│                                                                  │
│  CONTEXT          DATA              INSTRUCTIONS                │
│  ─────────────    ─────────────     ─────────────               │
│  QueryType        Technical         Task                        │
│  Trigger          Position          Format                      │
│  Profile          Portfolio         Examples                    │
│                   News                                          │
│                   MarketRegime                                  │
│                   Comparative                                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  SELECTION LOGIC                                │
│  (PromptBuilder decides which components to use)                │
│                                                                  │
│  IF query_type == 'NEW_OPPORTUNITY':                            │
│      Use: QueryType + Profile + Technical + Task + Format       │
│                                                                  │
│  IF query_type == 'POSITION_REVIEW':                            │
│      Use: QueryType + Profile + Position + Technical +          │
│           Task(SELL-focused) + Format                           │
│                                                                  │
│  IF query_type == 'PORTFOLIO_AUDIT':                            │
│      Use: QueryType + Profile + Portfolio + Comparative +       │
│           Task(Ranking) + Format(Ranking)                       │
│                                                                  │
│  IF include_news == True:                                       │
│      Add: News component                                        │
│                                                                  │
│  IF include_market_regime == True:                              │
│      Add: MarketRegime component                                │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                 ASSEMBLY & RENDERING                            │
│                                                                  │
│  1. Sort components by priority (10 → 1)                        │
│  2. Render each component.render()                              │
│  3. Join sections with "\n\n"                                   │
│  4. Return complete prompt string                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Data Flow: Real-World Scenario

### Scenario: Capital Constrained Portfolio Review

```
┌─────────────────────────────────────────────────────────────────┐
│  TIME: 10:45 AM - Trading Cycle Starts                         │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: Agent checks account state                            │
│  ─────────────────────────────────────────────────────          │
│  Portfolio: $100,547                                            │
│  Buying Power: $592 (0.59%) ← CRITICAL!                        │
│  Positions: 10                                                  │
│                                                                  │
│  Decision: buying_power < 5% of portfolio                       │
│  → Trigger PORTFOLIO_AUDIT                                      │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: Build Query Context                                   │
│  ─────────────────────────────────────────────────────          │
│  context = QueryContext(                                        │
│      query_type = 'PORTFOLIO_AUDIT',                            │
│      trigger = 'CAPITAL_CONSTRAINT',                            │
│      profile = 'rotator',                                       │
│      portfolio_state = {                                        │
│          'buying_power': 592,                                   │
│          'total_value': 100547,                                 │
│          'positions': [...]  # All 10 positions                 │
│      },                                                         │
│      expected_format = 'RANKING'                                │
│  )                                                              │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: PromptBuilder assembles components                    │
│  ─────────────────────────────────────────────────────          │
│  Selected Components:                                           │
│  ├─ QueryTypeComponent('PORTFOLIO_AUDIT')                       │
│  │   → "📊 QUERY TYPE: PORTFOLIO AUDIT"                        │
│  │                                                              │
│  ├─ TriggerComponent('CAPITAL_CONSTRAINT')                      │
│  │   → "🔔 TRIGGER: Need to free capital ($592 available)"     │
│  │                                                              │
│  ├─ TradingProfileComponent('rotator')                          │
│  │   → "🎯 PROFILE: Active Capital Rotator"                    │
│  │      "Lower bar for SELL (40% confidence)"                  │
│  │                                                              │
│  ├─ PortfolioSummaryComponent({...})                            │
│  │   → "💼 PORTFOLIO STATE:"                                   │
│  │      "10 positions, $592 buying power (0.59%)"              │
│  │                                                              │
│  ├─ ComparativeDataComponent([AAPL, MSFT, ...])                │
│  │   → "AAPL: RSI 52, Bullish, P&L +0.13%"                    │
│  │      "MSFT: RSI 54, Bullish, P&L +0.38%"                   │
│  │      "TSLA: RSI 48, Neutral, P&L -1.2%"                     │
│  │      ... (all 10 positions)                                 │
│  │                                                              │
│  ├─ TaskInstructionComponent('PORTFOLIO_AUDIT')                 │
│  │   → "⚡ TASK: Rank all holdings from STRONGEST to WEAKEST"  │
│  │      "Identify bottom 3 to SELL for capital rotation"       │
│  │                                                              │
│  └─ ResponseFormatComponent('RANKING')                          │
│      → "📋 RESPONSE FORMAT:"                                   │
│         "{ ranked_positions: [...], summary: '...' }"          │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 4: LLM analyzes and responds                             │
│  ─────────────────────────────────────────────────────          │
│  {                                                              │
│    "ranked_positions": [                                        │
│      {                                                          │
│        "symbol": "NVDA",                                        │
│        "rank": 1,                                               │
│        "score": 92,                                             │
│        "action": "keep",                                        │
│        "reason": "Strongest momentum, RSI healthy, leading     │
│                   tech sector"                                  │
│      },                                                         │
│      {                                                          │
│        "symbol": "MSFT",                                        │
│        "rank": 2,                                               │
│        "score": 88,                                             │
│        "action": "keep",                                        │
│        "reason": "Solid uptrend, best P&L, reliable"           │
│      },                                                         │
│      ...                                                        │
│      {                                                          │
│        "symbol": "AAPL",                                        │
│        "rank": 8,                                               │
│        "score": 52,                                             │
│        "action": "sell",                                        │
│        "reason": "Flat P&L (+0.13%), neutral momentum,         │
│                   better opportunities exist"                   │
│      },                                                         │
│      {                                                          │
│        "symbol": "TSLA",                                        │
│        "rank": 9,                                               │
│        "score": 45,                                             │
│        "action": "sell",                                        │
│        "reason": "Losing position (-1.2%), weak technicals"    │
│      },                                                         │
│      {                                                          │
│        "symbol": "INTC",                                        │
│        "rank": 10,                                              │
│        "score": 38,                                             │
│        "action": "sell",                                        │
│        "reason": "Worst holding, broken trend, cut losses"     │
│      }                                                          │
│    ],                                                           │
│    "summary": "Portfolio has 4 strong positions (keep), 3      │
│                neutral (monitor), 3 weak (sell). Rotating      │
│                ~$60K capital will free funds for better         │
│                opportunities."                                  │
│  }                                                              │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 5: Execute SELL decisions                                │
│  ─────────────────────────────────────────────────────────────  │
│  For each position where action == 'sell':                      │
│      ├─ SELL AAPL: 114 shares → Free $30,000                   │
│      ├─ SELL TSLA: 85 shares → Free $20,000                    │
│      └─ SELL INTC: 200 shares → Free $10,000                   │
│                                                                  │
│  Result:                                                        │
│      Buying Power: $592 → $60,592 ✅                           │
│      Can now buy 100+ shares of strong opportunities           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎨 Component Reusability Matrix

Shows which components are used for which query types:

```
┌────────────────────┬─────┬─────┬────────┬────────┬────────┐
│ Component          │ NEW │ POS │ PORT   │ COMP   │ MARKET │
│                    │ OPP │ REV │ AUDIT  │ ANAL   │ REGIME │
├────────────────────┼─────┼─────┼────────┼────────┼────────┤
│ QueryType          │  ✓  │  ✓  │   ✓    │   ✓    │   ✓    │
│ Trigger            │  ✓  │  ✓  │   ✓    │   ✓    │   ✓    │
│ TradingProfile     │  ✓  │  ✓  │   ✓    │   ✓    │   ✓    │
├────────────────────┼─────┼─────┼────────┼────────┼────────┤
│ TechnicalData      │  ✓  │  ✓  │   ✓    │   ✓    │        │
│ PositionData       │     │  ✓  │        │        │        │
│ PortfolioSummary   │     │     │   ✓    │        │        │
│ ComparativeData    │     │     │   ✓    │   ✓    │        │
│ News               │  ✓  │  ✓  │        │   ✓    │        │
│ MarketRegime       │     │     │   ✓    │        │   ✓    │
├────────────────────┼─────┼─────┼────────┼────────┼────────┤
│ TaskInstruction    │  ✓  │  ✓  │   ✓    │   ✓    │   ✓    │
│ ResponseFormat     │  ✓  │  ✓  │   ✓    │   ✓    │   ✓    │
└────────────────────┴─────┴─────┴────────┴────────┴────────┘

Legend:
  NEW OPP = NEW_OPPORTUNITY
  POS REV = POSITION_REVIEW
  PORT AUDIT = PORTFOLIO_AUDIT
  COMP ANAL = COMPARATIVE_ANALYSIS
  MARKET REGIME = MARKET_REGIME
```

**Key Insight**: 
- 3 components used by ALL queries (QueryType, Trigger, Profile)
- Data components are query-specific
- Instructions components are always used but content varies

---

## 💡 Example Prompt Variations

### Same Stock (NVDA), 3 Different Contexts

#### Context 1: NEW_OPPORTUNITY
```
🎯 NEW OPPORTUNITY: NVDA
🎯 PROFILE: Aggressive (act fast, accept risk)
📊 TECHNICAL: $850, Bullish, RSI 62
⚡ TASK: Should I BUY this new stock?

RESULT → "BUY" (85% confidence)
```

#### Context 2: POSITION_REVIEW
```
💼 POSITION REVIEW: NVDA
🎯 PROFILE: Rotator (continuous rotation)
💼 POSITION: Own 50 shares @ $800, P&L +6.25%
📊 TECHNICAL: $850, Bullish, RSI 62
⚡ TASK: Should I SELL to take profits or HOLD?

RESULT → "HOLD" (70% confidence) "Let winner run, still strong"
```

#### Context 3: PORTFOLIO_AUDIT
```
📊 PORTFOLIO AUDIT
🎯 PROFILE: Rotator
💼 10 positions compared:
   NVDA: Rank 1/10, Score 92, Action: KEEP
   AAPL: Rank 8/10, Score 52, Action: SELL
   ...

RESULT → Ranking with NVDA as top holding
```

---

**This visual guide shows how the same components combine in different ways to create context-aware, intelligent prompts! 🎨**
