# Calculated Strategy Baselines - Control Group Analysis

**Status:** ✅ Implemented  
**Date:** 2024  
**Purpose:** Measure LLM value-add by comparing against pure mathematical strategies

## 🎯 Overview

Every time the LLM evaluates a position, we now also calculate what **pure mathematical strategies** would recommend WITHOUT any LLM input. This creates a **control group** that enables us to measure whether the LLM is actually adding value or just adding latency.

### Key Benefits

1. **Measure LLM Value-Add**: Direct comparison of LLM vs pure math performance
2. **Automatic Fallback**: When LLM fails/is slow, use best performing baseline
3. **Data-Driven Optimization**: Discover which scenarios LLM truly helps
4. **Transparent Decision Making**: Always know what the "straight math" recommends

## 📊 Four Baseline Strategies

### 1. Kelly Criterion Strategy
**Philosophy:** Optimal position sizing based on historical win rate

**Signal Rules:**
- **BUY**: Kelly recommends positive position AND no position held
- **SELL**: Kelly recommends zero position AND position held  
- **HOLD**: Current state matches Kelly recommendation

**Parameters:**
- Win Rate: From historical performance (default: 55%)
- Avg Win/Loss: From learning engine stats
- Max Kelly Fraction: 25% (conservative)

**Output Example:**
```json
{
  "strategy": "kelly_criterion",
  "action": "buy",
  "confidence": 70,
  "reasoning": "Kelly Criterion recommends 8.5% position (56 shares)",
  "recommended_shares": 56,
  "position_pct": 0.085
}
```

### 2. Momentum Strategy
**Philosophy:** Follow the trend - ride winners

**Signal Rules:**
- **BUY**: Price > SMA20, RSI < 70, MACD > 0, volume > average (score ≥ 6/9)
- **SELL**: Momentum weakening (score ≤ 2/9) AND position held
- **HOLD**: Mixed momentum signals

**Momentum Score Components:**
- Price > SMA20: +2 points
- Price > SMA50: +2 points
- RSI 40-70 (healthy): +2 points
- RSI > 70 (overbought): -2 points
- MACD > 0: +2 points
- Volume > 1.2x average: +1 point

**Output Example:**
```json
{
  "strategy": "momentum",
  "action": "buy",
  "confidence": 80,
  "reasoning": "Strong momentum (score: 8/9): Price>$145.00, RSI=55, MACD=2.50",
  "momentum_score": 8,
  "position_pct": 0.05
}
```

### 3. Mean Reversion Strategy
**Philosophy:** Contrarian - buy dips, sell rallies

**Signal Rules:**
- **BUY**: Oversold (RSI < 30 or price < BB lower) (score ≥ 4)
- **SELL**: Overbought (RSI > 70 or price > BB upper) (score ≤ -4) AND position held
- **HOLD**: Price near mean

**Reversion Score Components:**
- RSI < 30: +3 points (strong oversold)
- RSI < 40: +2 points (moderate oversold)
- RSI > 70: -3 points (strong overbought)
- RSI > 60: -2 points (moderate overbought)
- Price < BB lower: +3 points
- Price < SMA20 * 0.98: +1 point
- Price > BB upper: -3 points
- Price > SMA20 * 1.02: -1 point

**Output Example:**
```json
{
  "strategy": "mean_reversion",
  "action": "buy",
  "confidence": 85,
  "reasoning": "Oversold - Mean reversion opportunity (score: 6): RSI=25, Price=$140 vs SMA=$150",
  "reversion_score": 6,
  "target_price": 150.00
}
```

### 4. Risk Parity Strategy
**Philosophy:** Size positions inversely to volatility

**Signal Rules:**
- **BUY**: Uptrend (price > SMA50) with vol-adjusted sizing
- **SELL**: Downtrend (price < SMA50) AND position held
- **HOLD**: Neutral trend

**Position Sizing:**
- Target daily volatility: 1% (15% annual)
- Adjustment = target_vol / actual_vol
- Example: 
  - 0.5% vol (low) → 2.0x larger position
  - 2.0% vol (high) → 0.5x smaller position
- Base position: 6%, capped at 10%

**Output Example:**
```json
{
  "strategy": "risk_parity",
  "action": "buy",
  "confidence": 65,
  "reasoning": "Uptrend with vol-adjusted sizing: 9.6% (vol=0.8%, adj=1.6x)",
  "volatility": 0.008,
  "vol_adjustment": 1.6,
  "position_pct": 0.096
}
```

### 5. Consensus Recommendation
**Philosophy:** Democratic vote across all strategies

**Voting Rules:**
- If >50% vote BUY → Consensus BUY
- If >50% vote SELL → Consensus SELL
- Otherwise → Consensus HOLD
- Confidence = (majority_votes / total_votes) * 100

**Output Example:**
```json
{
  "strategy": "consensus",
  "action": "buy",
  "confidence": 75,
  "reasoning": "Consensus: 3B/0S/1H (4 strategies)",
  "vote_breakdown": {
    "buy": 3,
    "sell": 0,
    "hold": 1,
    "total": 4
  }
}
```

## 🏗️ Architecture Integration

### TradingAgent.make_decision() Flow

```python
def make_decision(self, analysis: Dict[str, Any]) -> TradingDecision:
    # 1. Calculate pure math baselines FIRST
    calculated_strategies = self.strategy_calculator.calculate_all_strategies(
        symbol=symbol,
        signals=signals,
        current_position=current_position,
        account_value=self.account_value,
        historical_performance=self._get_historical_performance(symbol)
    )
    
    # 2. Get LLM recommendation
    llm = analysis['llm_analysis']
    action = llm.get('action', 'hold')
    
    # 3. Create decision with BOTH
    decision = TradingDecision(
        ...,
        llm_analysis=llm,
        calculated_strategies=calculated_strategies,  # NEW
        ...
    )
    
    # 4. Log both for comparison
    # decisions.jsonl now contains LLM + all 4 baselines + consensus
```

### Logged Decision Format

```json
{
  "timestamp": "2024-01-15T10:30:00",
  "symbol": "AAPL",
  "action": "buy",  // LLM decision
  "shares": 50,
  "confidence": 75,
  "reasoning": "Strong technical breakout + positive sentiment",
  
  "llm_analysis": {
    "action": "buy",
    "confidence": 75,
    "reasoning": "..."
  },
  
  "calculated_strategies": {
    "kelly": {
      "action": "buy",
      "confidence": 70,
      "recommended_shares": 56,
      "reasoning": "Kelly recommends 8.5% position"
    },
    "momentum": {
      "action": "buy",
      "confidence": 80,
      "momentum_score": 8,
      "reasoning": "Strong momentum (8/9)"
    },
    "mean_reversion": {
      "action": "hold",
      "confidence": 50,
      "reversion_score": 0,
      "reasoning": "Price near mean"
    },
    "risk_parity": {
      "action": "buy",
      "confidence": 65,
      "reasoning": "Uptrend with vol-adjusted sizing"
    },
    "consensus": {
      "action": "buy",
      "confidence": 75,
      "vote_breakdown": {"buy": 3, "sell": 0, "hold": 1}
    }
  },
  
  "strategy_agreement": {
    "llm_agrees_with_kelly": true,
    "llm_agrees_with_momentum": true,
    "llm_agrees_with_mean_reversion": false,
    "llm_agrees_with_risk_parity": true,
    "llm_agrees_with_consensus": true,
    "agreement_score": 0.80  // 4/5 strategies agree
  }
}
```

## 📈 Analysis & Metrics

### Overnight Learner Integration

The OvernightLearner will add a new analysis pass:

**Pass 6B: Strategy Performance Comparison**

```python
def analyze_strategy_performance(self):
    """
    Compare LLM vs baseline strategies.
    
    Metrics:
    1. Win Rate: LLM vs Kelly vs Momentum vs Mean Reversion vs Risk Parity
    2. Avg P&L: Which strategy generates better returns?
    3. Sharpe Ratio: Risk-adjusted performance
    4. Agreement Rate: How often does LLM agree with each strategy?
    5. Value-Add Analysis: When LLM differs, does it outperform?
    6. Scenario Performance: Which strategy works best in:
       - Trending markets
       - Choppy markets
       - High volatility
       - Low volatility
    """
```

### Key Questions Answered

1. **Is LLM adding value?**
   - Compare LLM win rate vs Kelly win rate
   - Compare LLM Sharpe ratio vs baseline Sharpe ratios
   
2. **When does LLM help most?**
   - Analyze scenarios where LLM outperforms baselines
   - Identify scenarios where baselines outperform LLM
   
3. **Which baseline is strongest?**
   - Overall win rate by strategy
   - Best strategy per market regime
   
4. **Should we trust LLM when it disagrees?**
   - When LLM differs from consensus, what's the outcome distribution?
   - When LLM differs from Kelly, what's the outcome?

### Example Analysis Output

```
STRATEGY PERFORMANCE ANALYSIS (Last 30 Days)
============================================

Overall Performance:
  LLM:            65% win rate, Sharpe 1.2, +$5,200 P&L
  Kelly:          60% win rate, Sharpe 1.0, +$4,100 P&L
  Momentum:       58% win rate, Sharpe 0.9, +$3,800 P&L
  Mean Reversion: 52% win rate, Sharpe 0.7, +$2,400 P&L
  Risk Parity:    57% win rate, Sharpe 0.85, +$3,500 P&L
  Consensus:      62% win rate, Sharpe 1.1, +$4,500 P&L

LLM Agreement Analysis:
  Agrees with Kelly: 78% of time
  Agrees with Momentum: 65% of time
  Agrees with Mean Reversion: 42% of time
  Agrees with Risk Parity: 70% of time
  Agrees with Consensus: 82% of time

LLM Value-Add:
  When LLM agrees with consensus: 70% win rate
  When LLM disagrees with consensus: 55% win rate
  ✅ LLM adds value when aligned with math
  ⚠️  LLM underperforms when contrarian

Best Strategy by Regime:
  Trending Markets: Momentum (72% win rate)
  Choppy Markets: Mean Reversion (68% win rate)
  High Volatility: Risk Parity (65% win rate)
  Low Volatility: Kelly (70% win rate)
  Unknown Regime: LLM (63% win rate)

RECOMMENDATION: Keep using LLM, but weight towards consensus when LLM differs.
```

## 🛡️ Fallback Mechanism

### When LLM Fails

```python
def make_decision_with_fallback(self, analysis):
    try:
        # Try LLM first
        return self.make_decision(analysis)
    except Exception as e:
        logger.warning(f"LLM failed: {e}, using best baseline strategy")
        
        # Calculate baselines
        calculated_strategies = self.strategy_calculator.calculate_all_strategies(...)
        
        # Use consensus (democratic fallback)
        consensus = calculated_strategies['consensus']
        
        return TradingDecision(
            action=consensus['action'],
            shares=consensus['recommended_shares'],
            confidence=consensus['confidence'],
            reasoning=f"Fallback: Consensus (LLM unavailable)",
            llm_analysis=None,
            calculated_strategies=calculated_strategies,
            ...
        )
```

### Fallback Strategy Selection

**Primary:** Use consensus (democratic vote)  
**Alternative:** Use Kelly Criterion (mathematically optimal)  
**Tertiary:** Use best performing strategy from last 30 days

## 🧪 Testing

### Demo Script

```bash
python scripts/demo_calculated_strategies.py
```

Tests 5 scenarios:
1. **Bullish**: Strong uptrend signals
2. **Bearish**: Downtrend signals
3. **Oversold**: Extreme negative deviation
4. **Overbought**: Extreme positive deviation
5. **Neutral**: Mixed signals

For each scenario, shows:
- All 4 strategy recommendations
- Consensus vote
- Reasoning and confidence
- Strategy-specific metrics

### Integration Testing

```bash
# Run full system with calculated baselines enabled
python scripts/run_trading.py

# Check logs for calculated strategies
tail -f logs/decisions.jsonl | jq '.calculated_strategies'

# Analyze strategy performance
python scripts/run_backtest.py --compare-strategies
```

## 📊 Dashboard Visualization (Future)

Potential dashboard additions:

1. **Strategy Comparison Chart**: Line chart showing cumulative P&L for LLM vs each baseline
2. **Agreement Heatmap**: Matrix showing how often strategies agree
3. **Value-Add Scatter**: X-axis: strategy confidence, Y-axis: outcome P&L
4. **Regime Performance Table**: Best strategy per market condition

## 🎯 Key Insights

### Why This Matters

1. **Scientific Approach**: We're not blindly trusting LLM - we measure its value
2. **Risk Mitigation**: If LLM quality degrades, we have automatic fallback
3. **Continuous Improvement**: Data-driven insights show where LLM helps most
4. **Transparency**: Always know what pure math would recommend

### Example Use Cases

**Scenario 1: LLM Says BUY, All Baselines Say HOLD**
```
Decision: Proceed with caution
- LLM might see news/sentiment not in technical indicators
- Log with flag for later analysis
- Reduce position size by 50% (hedge uncertainty)
```

**Scenario 2: LLM Says HOLD, Kelly + Momentum Say BUY**
```
Decision: Consider math
- LLM might be overly cautious
- Check LLM reasoning for non-technical factors
- If no strong sentiment reason, follow math (75% weight)
```

**Scenario 3: All Strategies Agree on BUY**
```
Decision: High confidence trade
- Increase position size (within risk limits)
- Tighten stop loss (clear exit if wrong)
- Log as "unanimous" for performance tracking
```

## 🔧 Configuration

### Strategy Calculator Settings

Located in `wawatrader/strategy_calculator.py`:

```python
# Kelly Criterion
MAX_KELLY_FRACTION = 0.25  # Conservative 25% of optimal Kelly
DEFAULT_WIN_RATE = 0.55
DEFAULT_AVG_WIN = 500
DEFAULT_AVG_LOSS = 300

# Momentum
MOMENTUM_THRESHOLD_BUY = 6   # Score out of 9
MOMENTUM_THRESHOLD_SELL = 2
BASE_MOMENTUM_POSITION = 0.05  # 5% of account

# Mean Reversion
REVERSION_THRESHOLD_BUY = 4    # Oversold score
REVERSION_THRESHOLD_SELL = -4  # Overbought score
BASE_REVERSION_POSITION = 0.04  # 4% of account

# Risk Parity
TARGET_DAILY_VOL = 0.01  # 1% daily = 15% annual
BASE_RISK_PARITY_POSITION = 0.06  # 6% of account
MAX_VOL_ADJUSTED_POSITION = 0.10  # Cap at 10%
```

## 📚 References

- **Kelly Criterion**: Optimal position sizing based on edge
- **Momentum Investing**: Ride trends, cut losers early
- **Mean Reversion**: Markets oscillate around mean value
- **Risk Parity**: Equal risk contribution from each position

## ✅ Implementation Checklist

- [x] Create `strategy_calculator.py` module (456 lines)
- [x] Implement Kelly Criterion strategy
- [x] Implement Momentum strategy
- [x] Implement Mean Reversion strategy
- [x] Implement Risk Parity strategy
- [x] Implement Consensus calculator
- [x] Add `calculated_strategies` field to `TradingDecision`
- [x] Integrate into `TradingAgent.make_decision()`
- [x] Add `_get_historical_performance()` helper
- [x] Create demo script
- [x] Create documentation
- [ ] Add strategy comparison to OvernightLearner (Pass 6B)
- [ ] Add fallback mechanism for LLM failures
- [ ] Add dashboard visualizations
- [ ] Add backtesting comparison mode

---

**Next Steps:**
1. Run `demo_calculated_strategies.py` to verify implementation
2. Run live trading to collect comparison data
3. Analyze first week of LLM vs baseline performance
4. Tune strategy weights based on results
