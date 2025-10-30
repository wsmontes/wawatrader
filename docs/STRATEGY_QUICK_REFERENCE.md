# Calculated Strategy Baselines - Quick Reference

**Quick lookup guide for interpreting pure math strategy recommendations**

---

## 🎯 At-a-Glance Strategy Guide

### When to Trust Each Strategy

| Market Condition | Best Strategy | Why |
|-----------------|---------------|-----|
| **Strong Uptrend** | Momentum (score 7-9) | Rides the wave, maximizes gains |
| **Strong Downtrend** | Mean Reversion (wait) | Avoids catching falling knife |
| **Sideways/Choppy** | Mean Reversion | Profits from oscillations |
| **High Volatility** | Risk Parity | Automatically reduces size |
| **Low Volatility** | Kelly Criterion | Optimal sizing in stable conditions |
| **Unknown/Mixed** | Consensus | Democratic safety |

---

## 📊 Reading Strategy Scores

### Kelly Criterion
```
Position %    | Interpretation
-------------|----------------
0-2%         | 🔴 Low confidence, minimal edge
2-5%         | 🟡 Moderate edge, small position
5-10%        | 🟢 Strong edge, recommended size
>10%         | 🟢🟢 Very strong edge (capped at 10%)
0% (negative)| ❌ AVOID - negative expected value
```

### Momentum Score
```
Score  | Interpretation
-------|----------------
0-2    | 🔴 Weak/bearish, consider SELL if holding
3-5    | 🟡 Mixed signals, HOLD
6-7    | 🟢 Good momentum, consider BUY
8-9    | 🟢🟢 Strong momentum, strong BUY
```

**Components (max 9 points):**
- Price > SMA20: +2
- Price > SMA50: +2
- RSI 40-70: +2
- MACD > 0: +2
- Volume > 1.2x avg: +1
- RSI > 70 (overbought): -2

### Mean Reversion Score
```
Score    | Interpretation
---------|----------------
≥ 4      | 🟢🟢 Very oversold, strong BUY
2-3      | 🟢 Oversold, consider BUY
-1 to 1  | 🟡 Near mean, HOLD
-3 to -2 | 🔴 Overbought, consider SELL
≤ -4     | 🔴🔴 Very overbought, strong SELL
```

**Components:**
- RSI < 30: +3 (strong oversold)
- RSI < 40: +2
- RSI > 70: -3 (strong overbought)
- RSI > 60: -2
- Price < BB lower: +3
- Price > BB upper: -3

### Risk Parity Volatility Adjustment
```
Volatility | Adjustment | Position Size
-----------|------------|---------------
0.5%       | 2.00x      | 12% (capped at 10%)
1.0%       | 1.00x      | 6% (base)
1.5%       | 0.67x      | 4%
2.0%       | 0.50x      | 3%
3.0%       | 0.33x      | 2%
```

---

## 🎯 Consensus Interpretation

### Vote Patterns
```
Vote Count    | Consensus | Confidence | Interpretation
--------------|-----------|------------|----------------
4 BUY, 0 SELL | BUY       | 100%       | 🟢🟢🟢 Unanimous - high confidence
3 BUY, 1 SELL | BUY       | 75%        | 🟢🟢 Strong agreement
3 BUY, 1 HOLD | BUY       | 75%        | 🟢🟢 Strong agreement
2 BUY, 2 HOLD | HOLD      | 50%        | 🟡 Split decision - caution
2 BUY, 1 SELL | HOLD      | 50%        | 🟡 Disagreement - neutral
1 BUY, 3 HOLD | HOLD      | 75%        | 🟡 Mostly cautious
3 SELL, 1 BUY | SELL      | 75%        | 🔴🔴 Strong bearish
4 SELL, 0 BUY | SELL      | 100%       | 🔴🔴🔴 Unanimous - strong bearish
```

---

## 🤔 Decision Matrix: LLM vs Baselines

### High Confidence Scenarios

| LLM | Consensus | Kelly | Momentum | Interpretation | Action |
|-----|-----------|-------|----------|----------------|--------|
| BUY | BUY | BUY | BUY | 🟢🟢🟢 Perfect alignment | **STRONG BUY** - Increase size |
| SELL | SELL | SELL | SELL | 🔴🔴🔴 Perfect bearish alignment | **STRONG SELL** - Exit immediately |
| HOLD | HOLD | HOLD | HOLD | ⚪⚪⚪ Universal caution | **HOLD** - Wait for clarity |

### Mixed Signal Scenarios

| LLM | Consensus | Kelly | Interpretation | Suggested Action |
|-----|-----------|-------|----------------|------------------|
| BUY | BUY | HOLD | 🟢🟡 LLM + Consensus agree | **BUY** (75% confidence) |
| BUY | HOLD | BUY | 🟢⚪ Kelly + LLM agree | **BUY** (65% confidence) |
| BUY | HOLD | HOLD | 🟢⚪ Only LLM bullish | **HOLD or small BUY** (50% size) |
| SELL | HOLD | HOLD | 🔴⚪ Only LLM bearish | **HOLD** - Wait for confirmation |
| HOLD | BUY | BUY | ⚪🟢 Math says BUY, LLM cautious | **HOLD or small BUY** - Check LLM reasoning |

### Contrarian Scenarios (LLM Disagrees)

| LLM | Consensus | Interpretation | Investigation Needed |
|-----|-----------|----------------|---------------------|
| BUY | SELL | 🟢🔴 Major disagreement | Check: News? Sentiment? Unusual event? |
| SELL | BUY | 🔴🟢 Major disagreement | Check: Why is LLM bearish? Technical looks good |
| BUY | HOLD | 🟢⚪ LLM more aggressive | Proceed with 50% size - log for later analysis |
| HOLD | BUY | ⚪🟢 LLM more cautious | Math says opportunity - consider small position |

---

## 📈 Real-World Examples

### Example 1: Strong Bullish Setup (AAPL)
```
Kelly:          BUY 9.2% (61 shares) - 70% confidence
Momentum:       BUY (score 8/9) - 80% confidence
Mean Reversion: HOLD (near mean) - 50% confidence
Risk Parity:    BUY 3.0% - 65% confidence
Consensus:      BUY (3B/0S/1H) - 75% confidence

LLM:            BUY - 85% confidence
                "Strong technical breakout above resistance + positive earnings sentiment"

INTERPRETATION: 🟢🟢🟢 High conviction trade
- 80% strategy agreement (4/5 strategies agree on BUY/HOLD, none say SELL)
- LLM confidence (85%) exceeds consensus (75%)
- LLM adding sentiment layer to technical setup

ACTION: ✅ Execute BUY with full Kelly-recommended size (9.2%)
        ✅ Set stop loss at -5% (Kelly recommendation)
        ✅ Target +10% (Kelly target)
```

### Example 2: Contrarian Situation (TSLA)
```
Kelly:          HOLD (2.5% - below threshold) - 50% confidence
Momentum:       SELL (score 1/9) - 60% confidence  
Mean Reversion: HOLD (score -1) - 50% confidence
Risk Parity:    HOLD - 50% confidence
Consensus:      HOLD (0B/1S/3H) - 75% confidence

LLM:            BUY - 70% confidence
                "Despite technical weakness, news of major Tesla factory expansion + analyst upgrades"

INTERPRETATION: 🟡🤔 LLM sees something math doesn't
- 0% strategy agreement (no other strategy says BUY)
- LLM relying on news/sentiment not visible to technical indicators
- Math shows weak momentum, neutral reversion

ACTION: 🔶 Proceed with CAUTION
        - Buy only 50% of normal size (4.6% → 2.3%)
        - Tighter stop loss (-3% instead of -5%)
        - Flag as "LLM-only trade" for performance tracking
        - If this wins, validates LLM's news integration
        - If this loses, suggests over-reliance on sentiment
```

### Example 3: Perfect Agreement (NVDA)
```
Kelly:          BUY 8.5% (50 shares) - 75% confidence
Momentum:       BUY (score 9/9) - 90% confidence
Mean Reversion: BUY (oversold, score 5) - 80% confidence
Risk Parity:    BUY 4.2% - 70% confidence
Consensus:      BUY (4B/0S/0H) - 100% confidence

LLM:            BUY - 95% confidence
                "Unanimous bullish signals: breakout + oversold bounce + positive AI sector momentum"

INTERPRETATION: 🟢🟢🟢🟢 RARE unanimous agreement
- 100% strategy agreement (all 4 + LLM say BUY)
- Combines trend (momentum 9/9) + value (mean reversion oversold)
- LLM confidence (95%) at maximum
- Risk-adjusted sizing still conservative (8.5%)

ACTION: ✅✅ STRONG BUY - highest conviction
        ✅ Use full Kelly size (8.5%)
        ✅ Consider adding 25% more if risk limits allow
        ✅ Trail stop loss as position moves in profit
        ✅ Flag as "unanimous trade" - expect high win rate
```

### Example 4: Split Decision (COIN)
```
Kelly:          HOLD (0.5% - below threshold) - 40% confidence
Momentum:       HOLD (score 4/9) - 50% confidence
Mean Reversion: BUY (oversold, score 4) - 75% confidence
Risk Parity:    HOLD - 45% confidence
Consensus:      HOLD (1B/0S/3H) - 75% confidence

LLM:            HOLD - 55% confidence
                "Mixed signals: oversold technically but Bitcoin weakness concerns"

INTERPRETATION: 🟡 Neutral setup - wait for clarity
- Only Mean Reversion says BUY (contrarian play on oversold)
- Kelly below threshold (edge too small)
- Momentum neutral (not trending)
- LLM agrees with consensus HOLD

ACTION: ⚪ HOLD - Wait for clearer setup
        - Mean Reversion sees oversold opportunity
        - BUT only 25% strategy agreement (1/4)
        - Better opportunities exist with higher agreement
        - Re-evaluate if momentum improves (score > 6)
```

---

## 🚨 Warning Signals

### Red Flags - Do NOT Trade

| Pattern | Meaning | Action |
|---------|---------|--------|
| Kelly < 1% | No mathematical edge | ❌ AVOID - negative expected value |
| All strategies HOLD | No clear opportunity | ⏸️ WAIT - patience required |
| LLM contradicts all 4 strategies | Possible LLM hallucination | 🔶 Verify LLM reasoning carefully |
| Momentum SELL + already down 10%+ | Potential falling knife | 🔴 Exit or stay out |
| Mean Reversion BUY but momentum score 0-1 | Counter-trend in strong downtrend | 🔶 High risk - small size only |

---

## 🎯 Quick Decision Tree

```
1. Check Consensus
   ├─ 100% agreement → STRONG signal (follow it)
   ├─ 75%+ agreement → Good signal (follow it)
   ├─ 50% agreement → Neutral (HOLD or wait)
   └─ < 50% agreement → Confused (definitely wait)

2. If Consensus = BUY or SELL, check LLM agreement
   ├─ LLM agrees → ✅ Execute (high confidence)
   ├─ LLM neutral → 🔶 Execute with 75% size
   └─ LLM disagrees → 🔶 Execute with 50% size OR investigate further

3. If Consensus = HOLD but LLM says BUY/SELL
   ├─ Check LLM reasoning (news? sentiment?)
   ├─ If strong fundamental reason → 🔶 Execute with 50% size
   └─ If only technical → ⏸️ Wait for math to agree

4. Check Kelly %
   ├─ > 5% → Good edge, normal size
   ├─ 2-5% → Moderate edge, normal size
   ├─ 1-2% → Weak edge, 50% size or skip
   └─ < 1% → ❌ No edge, skip trade

5. Check Market Regime
   ├─ Trending → Weight Momentum higher (2x)
   ├─ Choppy → Weight Mean Reversion higher (2x)
   ├─ Volatile → Weight Risk Parity higher (2x)
   └─ Calm → Weight Kelly higher (2x)
```

---

## 📊 Performance Tracking

### What to Log for Each Decision

```python
{
    "llm_action": "buy",
    "llm_confidence": 75,
    
    "consensus_action": "buy",
    "consensus_confidence": 75,
    
    "agreement_score": 0.80,  # 4/5 strategies agree
    
    "kelly_edge": 0.092,  # 9.2% position
    "momentum_score": 8,
    "reversion_score": -1,
    "volatility": 0.020,  # 2.0%
    
    "outcome_pnl": +420.00,  # Track actual P&L
    "outcome_pct": 0.028,    # +2.8% return
    "hold_duration": "2 days"
}
```

### Weekly Analysis Questions

1. **LLM vs Kelly**: Win rate comparison?
2. **LLM vs Consensus**: When LLM differs, who wins?
3. **Agreement Correlation**: Does higher agreement % = higher win rate?
4. **Strategy by Regime**: Which works best in trending vs choppy?
5. **Contrarian Trades**: When LLM alone says BUY/SELL, success rate?

---

## 🎓 Strategy Philosophy Summary

| Strategy | Philosophy | Best For | Risk Profile |
|----------|-----------|----------|--------------|
| **Kelly** | Maximize long-term growth | Stable markets | Moderate |
| **Momentum** | Trend is your friend | Trending markets | Aggressive |
| **Mean Reversion** | Buy low, sell high | Range-bound markets | Moderate |
| **Risk Parity** | Equal risk weighting | All markets | Conservative |
| **Consensus** | Wisdom of the crowd | Unknown conditions | Moderate |
| **LLM** | Integrate all signals + sentiment | Complex setups | Adaptive |

---

**Remember:** No single strategy is always right. The goal is to understand WHY each recommends what it does, then make an informed decision. The baselines provide a **sanity check** - if LLM wildly disagrees with all math, investigate carefully! 🔍
