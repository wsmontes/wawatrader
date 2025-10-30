"""
NEW SIMPLIFIED TECHNICAL DATA COMPONENT
For small LLMs (4B-7B parameters)

Key philosophy: Provide INTERPRETATIONS, not raw numbers.
Small LLMs struggle with numerical reasoning, so we:
- Pre-compute all comparisons
- Provide clear verdicts (BULLISH/BEARISH/NEUTRAL)
- Explain what actions to take
- Minimize numeric calculations for the LLM
"""

def render_simplified_technical_analysis(symbol: str, current_price: float, 
                                        trend_data: dict, momentum_data: dict,
                                        volume_data: dict, signals: dict) -> str:
    """
    Simplified format optimized for small LLMs.
    
    Instead of: "RSI is 73.5, which might indicate overbought conditions"
    We say: "MOMENTUM VERDICT: ❌ OVERBOUGHT - Stock rallied too far, risk of pullback"
    """
    
    # Get key values
    sma_20 = trend_data.get('sma20') or trend_data.get('sma_20', 0)
    sma_50 = trend_data.get('sma50') or trend_data.get('sma_50', 0)
    rsi = momentum_data.get('rsi', 50)
    vol_ratio = volume_data.get('ratio') or volume_data.get('volume_ratio', 1.0)
    
    # PRE-COMPUTE TREND VERDICT
    if current_price > sma_20 > sma_50:
        distance = ((current_price - sma_20) / sma_20 * 100) if sma_20 > 0 else 0
        trend_verdict = f"""📈 TREND: ✅ STRONG BULLISH
• Price ${current_price:.2f} is {distance:.1f}% ABOVE the 20-day average
• This is an established uptrend (price > SMA20 > SMA50)  
• Pullbacks to ${sma_20:.2f} are buying opportunities
✅ ACTION: Bullish - favor buying on dips"""
    
    elif current_price > sma_20:
        trend_verdict = f"""📈 TREND: ⚠️  EARLY BULLISH  
• Price ${current_price:.2f} is above short-term average
• But long-term trend not fully confirmed yet
⚠️  ACTION: Cautiously bullish - watch for confirmation"""
    
    elif current_price < sma_20 < sma_50:
        distance = abs(((current_price - sma_20) / sma_20 * 100)) if sma_20 > 0 else 0
        trend_verdict = f"""📉 TREND: ❌ STRONG BEARISH
• Price ${current_price:.2f} is {distance:.1f}% BELOW the 20-day average  
• This is an established downtrend (price < SMA20 < SMA50)
• Resistance at ${sma_20:.2f}
❌ ACTION: Bearish - avoid buying or exit positions"""
    
    elif current_price < sma_20:
        trend_verdict = f"""📉 TREND: ⚠️  WEAKENING
• Price ${current_price:.2f} is below short-term average
• Showing weakness or correction
⚠️  ACTION: Defensive - wait for recovery signs"""
    
    else:
        trend_verdict = f"""➡️  TREND: ⚪ SIDEWAYS
• Price ${current_price:.2f} is choppy, no clear direction
• Market is deciding next move
⚪ ACTION: Wait for breakout or breakdown"""
    
    # PRE-COMPUTE MOMENTUM VERDICT
    if rsi > 70:
        momentum_verdict = f"""⚡ MOMENTUM: ❌ OVERBOUGHT (RSI: {rsi:.0f})
• Stock rallied too far too fast - risk of pullback
❌ WARNING: Consider taking profits or waiting for dip"""
    elif rsi > 60:
        momentum_verdict = f"""⚡ MOMENTUM: ✅ STRONG (RSI: {rsi:.0f})  
• Healthy bullish momentum, not overdone yet
✅ GOOD: Still room to run higher"""
    elif rsi >= 40:
        momentum_verdict = f"""⚡ MOMENTUM: ⚪ NEUTRAL (RSI: {rsi:.0f})
• Balanced - no extreme momentum either way
⚪ NEUTRAL: Rely on trend and volume for decision"""
    elif rsi >= 30:
        momentum_verdict = f"""⚡ MOMENTUM: ⚠️  WEAK (RSI: {rsi:.0f})
• Losing momentum, possible reversal if oversold
⚠️  CAUTION: Watch for support bounce"""
    else:
        momentum_verdict = f"""⚡ MOMENTUM: ✅ OVERSOLD (RSI: {rsi:.0f})
• Stock fell too far - possible bounce coming
✅ OPPORTUNITY: Look for reversal if support holds"""
    
    # PRE-COMPUTE VOLUME VERDICT
    if vol_ratio > 2.5:
        volume_verdict = f"""📊 VOLUME: 🔥 EXPLOSIVE ({vol_ratio:.1f}x normal)
• MAJOR institutional activity - high conviction move
✅ STRONG: Institutions are participating"""
    elif vol_ratio > 1.5:
        volume_verdict = f"""📊 VOLUME: ✅ HIGH ({vol_ratio:.1f}x normal)
• Strong participation - move is well-supported
✅ GOOD: Volume confirms price action"""
    elif vol_ratio > 0.8:
        volume_verdict = f"""📊 VOLUME: ⚪ NORMAL ({vol_ratio:.1f}x normal)
• Typical activity level
⚪ NEUTRAL: Volume neither confirms nor denies"""
    else:
        volume_verdict = f"""📊 VOLUME: ⚠️  LOW ({vol_ratio:.1f}x normal)
• Weak participation - move lacks conviction
⚠️  WARNING: Be skeptical of price moves"""
    
    # BUILD FINAL OUTPUT
    return f"""
══════════════════════════════════════════════════════════════════════
📊 TECHNICAL ANALYSIS: {symbol} @ ${current_price:.2f}
══════════════════════════════════════════════════════════════════════

{trend_verdict}

{momentum_verdict}

{volume_verdict}

══════════════════════════════════════════════════════════════════════
🎯 DECISION FRAMEWORK:
══════════════════════════════════════════════════════════════════════
BUY when: ✅ BULLISH trend + ✅ HEALTHY momentum + ✅ GOOD volume
SELL when: ❌ BEARISH trend OR ⚠️  WEAK momentum OR ❌ OVERBOUGHT  
HOLD when: ⚪ Mixed signals or consolidation

⚠️  YOUR JOB: Synthesize these PRE-ANALYZED verdicts into a decision.
    Do NOT recalculate numbers. The verdicts above are final.
    Focus on combining the signals, not reanalyzing them.
══════════════════════════════════════════════════════════════════════
"""


# EXAMPLE OUTPUTS:

# Example 1: Strong Buy Signal
"""
📊 TECHNICAL ANALYSIS: AAPL @ $175.50

📈 TREND: ✅ STRONG BULLISH
• Price $175.50 is 2.3% ABOVE the 20-day average
• This is an established uptrend (price > SMA20 > SMA50)  
• Pullbacks to $171.50 are buying opportunities
✅ ACTION: Bullish - favor buying on dips

⚡ MOMENTUM: ✅ STRONG (RSI: 58)  
• Healthy bullish momentum, not overdone yet
✅ GOOD: Still room to run higher

📊 VOLUME: ✅ HIGH (1.8x normal)
• Strong participation - move is well-supported
✅ GOOD: Volume confirms price action

BUY when: ✅ BULLISH trend + ✅ HEALTHY momentum + ✅ GOOD volume  <- ALL TRUE!
"""

# Example 2: Clear Sell Signal
"""
📊 TECHNICAL ANALYSIS: TSLA @ $245.30

📉 TREND: ❌ STRONG BEARISH
• Price $245.30 is 3.5% BELOW the 20-day average  
• This is an established downtrend (price < SMA20 < SMA50)
• Resistance at $254.00
❌ ACTION: Bearish - avoid buying or exit positions

⚡ MOMENTUM: ❌ OVERBOUGHT (RSI: 72)
• Stock rallied too far too fast - risk of pullback
❌ WARNING: Consider taking profits or waiting for dip

📊 VOLUME: ⚠️  LOW (0.6x normal)
• Weak participation - move lacks conviction
⚠️  WARNING: Be skeptical of price moves

SELL when: ❌ BEARISH trend OR ⚠️  WEAK momentum OR ❌ OVERBOUGHT  <- ALL TRUE!
"""

# Example 3: Hold/Wait Signal  
"""
📊 TECHNICAL ANALYSIS: NVDA @ $890.25

➡️  TREND: ⚪ SIDEWAYS
• Price $890.25 is choppy, no clear direction
• Market is deciding next move
⚪ ACTION: Wait for breakout or breakdown

⚡ MOMENTUM: ⚪ NEUTRAL (RSI: 48)
• Balanced - no extreme momentum either way
⚪ NEUTRAL: Rely on trend and volume for decision

📊 VOLUME: ⚪ NORMAL (0.9x normal)
• Typical activity level
⚪ NEUTRAL: Volume neither confirms nor denies

HOLD when: ⚪ Mixed signals or consolidation  <- THIS IS THE CASE
"""