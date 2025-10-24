# Trading Profiles Guide

## Overview

WawaTrader now supports **4 distinct trading profiles** that change how the LLM interprets market data and makes recommendations. Each profile uses the **same temperature** (no hallucinations) but different decision-making styles.

## Available Profiles

### 1. 🛡️ **Conservative**
**Best for:** Capital preservation, risk-averse traders

**Characteristics:**
- Requires **75%+ confidence** for BUY signals
- Requires **70%+ confidence** for SELL signals  
- **High emphasis on risk factors**
- Only acts on strong confirmations
- Prefers HOLD over uncertain positions

**LLM Behavior:**
> "Risk-averse with capital preservation focus. Only recommend BUY when indicators show strong confirmation and low risk."

---

### 2. ⚖️ **Moderate** (Default)
**Best for:** Balanced risk/reward approach

**Characteristics:**
- Requires **65%+ confidence** for BUY signals
- Requires **60%+ confidence** for SELL signals
- **Medium risk emphasis**
- Balanced consideration of opportunities and risks
- Standard trading approach

**LLM Behavior:**
> "Balanced analyst seeking reasonable risk-adjusted returns. Consider both opportunities and risks equally."

---

### 3. 🚀 **Aggressive**
**Best for:** Active trading, higher risk tolerance

**Characteristics:**
- Requires **55%+ confidence** for BUY signals
- Requires **50%+ confidence** for SELL signals
- **Low risk emphasis**
- Favors action over holding
- Focuses on opportunities

**LLM Behavior:**
> "Aggressive day trader focused on capturing market opportunities. Favor action over holding when clear signals appear."

---

### 4. 💎 **Maximum Revenue and Risk**
**Best for:** Maximum returns, very high risk tolerance

**Characteristics:**
- Requires **50%+ confidence** for BUY signals
- Requires **45%+ confidence** for SELL signals
- **Minimal risk concern**
- Acts on any reasonable opportunity
- Minimizes HOLD recommendations
- Decisive and bold

**LLM Behavior:**
> "High-risk, high-reward trader seeking maximum returns. Act on any reasonable opportunity aggressively."

---

## How to Change Profiles

### Method 1: Environment Variable (Recommended)

Edit your `.env` file:

```bash
# Choose one: conservative, moderate, aggressive, maximum
TRADING_PROFILE=aggressive
```

Then restart your dashboard/trading agent.

### Method 2: Runtime Change

```python
from wawatrader.llm_bridge import LLMBridge

bridge = LLMBridge()

# Change profile
bridge.set_profile('aggressive')

# Check current profile
profile = bridge.get_current_profile()
print(f"Using: {profile['name']}")
```

### Method 3: View All Profiles

```python
from wawatrader.llm_bridge import LLMBridge

profiles = LLMBridge.get_available_profiles()
for name, config in profiles.items():
    print(f"{config['name']}: {config['description']}")
```

---

## Testing Profiles

Run the demo to see how each profile interprets the same market data:

```bash
python scripts/demo_trading_profiles.py
```

This will:
1. Fetch current market data for AAPL
2. Run analysis with each profile
3. Show how recommendations differ

---

## Technical Details

### What Changes Between Profiles?

1. **System Prompt**: Each profile has a unique persona that guides the LLM's interpretation
2. **Confidence Thresholds**: Minimum confidence required for BUY/SELL actions
3. **Risk Emphasis**: How heavily risks are weighted in decision-making
4. **Action Bias**: Preference for action vs holding

### What DOESN'T Change?

- ✅ Temperature stays at 0.7 (no hallucinations)
- ✅ Same technical indicators
- ✅ Same risk management rules (overrides LLM)
- ✅ Same validation logic
- ✅ Same market data

### Safety Note

**The risk manager still enforces hard limits regardless of profile:**
- Position size limits
- Daily loss limits
- Portfolio exposure limits

Even "Maximum" profile cannot override safety rules!

---

## Comparison Table

| Feature | Conservative | Moderate | Aggressive | Maximum |
|---------|-------------|----------|------------|---------|
| Min Buy Confidence | 75% | 65% | 55% | 50% |
| Min Sell Confidence | 70% | 60% | 50% | 45% |
| Risk Emphasis | High | Medium | Low | Minimal |
| Action Bias | Low | Medium | High | Very High |
| Best For | Safety | Balance | Growth | Max Returns |

---

## Example Output Differences

**Same Market Condition:**
- Price: $150 (+2% above SMA20)
- RSI: 58 (neutral)
- MACD: Slightly positive

**Conservative:** "HOLD - Wait for stronger confirmation"
**Moderate:** "HOLD - Signals are neutral, monitor for clearer direction"
**Aggressive:** "BUY - Uptrend forming, good entry opportunity"
**Maximum:** "BUY - Capitalize on emerging uptrend momentum"

---

## Recommendations

- **New traders:** Start with **Conservative**
- **Experienced traders:** Use **Moderate** or **Aggressive**
- **High-risk appetite:** Use **Maximum** (understand the risks!)
- **Testing:** Try **demo_trading_profiles.py** to see differences

---

**Remember:** Profiles change LLM *interpretation*, not data quality. Always monitor your positions and understand the risks!
