"""
Instruction components: Task definitions and response formats.

These components tell the LLM what to do and what format to respond in.
"""

from ..components.base import PromptComponent, QueryContext


class TaskInstructionComponent(PromptComponent):
    """
    Task-specific instructions for the LLM.
    
    Provides clear, detailed instructions about what analysis
    is required and how to approach the decision.
    """
    
    TASKS = {
        'NEW_OPPORTUNITY': """
⚡ YOUR TASK: Evaluate if this is a good BUY opportunity RIGHT NOW
{'=' * 70}

You are evaluating a NEW stock for potential purchase.

Consider these factors:

1. TECHNICAL SETUP (70% weight)
   • Is the trend clear and confirmed?
   • Is momentum healthy (RSI 40-70 range ideal)?
   • Does volume confirm the move (≥1.2x average is good)?
   • Are we near support or resistance levels?

2. ENTRY TIMING (20% weight)
   • Is this the right moment or should we wait?
   • Is the stock overbought (RSI>70) or oversold (RSI<30)?
   • Any near-term catalysts to consider?
   • Better to enter now or wait for pullback?

3. RISK/REWARD (10% weight)
   • Where are support/resistance levels for stops and targets?
   • What's the potential profit vs potential loss?
   • Is risk/reward ratio favorable (ideally 2:1 or better)?

DECISION GUIDELINES:
   • BUY: Strong technical setup with good entry timing
   • HOLD: Good setup but poor timing (e.g., overbought) - wait for better entry
   • SELL: Not applicable for new opportunities

Be specific: Include price levels, support/resistance, and timeframe
""",
        
        'POSITION_REVIEW': """
⚡ YOUR TASK: Decide if you should HOLD or SELL this existing position
{'=' * 70}

⚠️  CRITICAL: You are NOT evaluating whether to buy this stock.
You ALREADY OWN IT. The question is: Should you continue holding or exit?

Evaluation Framework:

1. TECHNICAL HEALTH (40% weight)
   • Has the trend deteriorated or broken down?
   • Is momentum weakening (RSI declining, MACD bearish)?
   • Any technical breakdown signals (break below support, moving avg crossover)?
   • Volume patterns - are sellers dominating?

2. PROFIT/LOSS STATUS (30% weight)
   • If PROFITABLE → Is profit target reached? Time to lock gains?
   • If LOSING → Is stop-loss hit? Cut losses or wait for recovery?
   • If FLAT → Is capital better deployed elsewhere?
   • How long have we held this position?

3. RELATIVE OPPORTUNITY COST (30% weight)
   • Are there better opportunities available right now?
   • Is this still a top holding or just "okay"?
   • What's the opportunity cost of keeping capital here?
   • In a portfolio ranking, where does this position stand?

DECISION GUIDELINES:
   • SELL: If any of these apply:
     - Technical setup has deteriorated significantly
     - Profit target reached (lock in gains)
     - Stop-loss hit (cut losses early)
     - Better opportunities exist elsewhere
     - Position is weak compared to portfolio average
     
   • HOLD: If all of these apply:
     - Trend remains intact and healthy
     - No major red flags
     - Still one of best available holdings
     - P&L status is acceptable
     
   • BUY: Only if ALL of these apply (rare):
     - Strong bullish continuation signal
     - Very high conviction
     - Position sizing rules allow
     - This is THE best opportunity right now

⚠️  BIAS WARNING:
   • Don't hold losers hoping for recovery - that's anchoring bias
   • Don't get emotionally attached to winning positions
   • Capital rotation creates more opportunities than buy-and-hold
   • Be honest: Would you buy this stock today at current price?
""",
        
        'PORTFOLIO_AUDIT': """
⚡ YOUR TASK: Rank ALL holdings from STRONGEST to WEAKEST
{'=' * 70}

You will receive data for multiple positions. Evaluate and rank each one.

Ranking Criteria:

1. Technical Strength (50% weight)
   • Trend direction and strength (bullish > neutral > bearish)
   • Momentum health (positive > neutral > negative)
   • Volume confirmation (high vol moves are stronger)
   • Price action relative to moving averages

2. Performance (30% weight)
   • Current P&L (profits > breakeven > losses)
   • Recent price action (gaining > flat > losing)
   • Consistency (steady gains > volatile > steady losses)
   • Days held (quick winners good, long losers bad)

3. Relative Attractiveness (20% weight)
   • Best risk/reward going forward
   • Strongest setups for continuation
   • Most upside potential remaining
   • Least downside risk

Output Requirements:
   • Rank from 1 (best) to N (worst)
   • Give each a score (0-100)
   • Assign action: KEEP (top positions), HOLD (middle), or SELL (weak)
   • Brief reason for each ranking

Goal: Identify:
   • Top 3-5 positions to KEEP (strongest holdings)
   • Middle positions to HOLD and monitor
   • Bottom 3-5 to SELL for capital rotation

⚠️  Capital Rotation Strategy:
   Selling weak positions frees capital for better opportunities.
   Don't keep losers out of hope - rotate to winners actively.
""",
        
        'COMPARATIVE_ANALYSIS': """
⚡ YOUR TASK: Compare these stocks and rank them by attractiveness
{'=' * 70}

You will receive technical data for multiple stocks. Compare them
side-by-side and determine which are most attractive.

Comparison Factors:

1. Technical Setup
   • Which has the strongest trend?
   • Which has the healthiest momentum?
   • Which has best volume confirmation?

2. Risk/Reward
   • Which has best upside potential?
   • Which has least downside risk?
   • Which has clearest support/resistance levels?

3. Timing
   • Which is best positioned for entry NOW?
   • Which needs to pull back first?
   • Which is overbought/oversold?

Output Format:
   Rank from BEST to WORST with scores and reasoning

Example:
   1. BEST: NVDA (Score: 92/100)
      Reason: Strong uptrend, RSI 62 (healthy), 1.8x volume
   
   2. GOOD: AMD (Score: 78/100)
      Reason: Bullish but overbought RSI 75, wait for pullback
   
   3. WEAK: INTC (Score: 45/100)
      Reason: Broken trend, weak momentum, avoid

Be decisive - clearly identify the winner(s) and loser(s)
""",
    }
    
    def __init__(self, query_type: str, **kwargs):
        super().__init__(**kwargs)
        self.query_type = query_type
        self.priority = 6
    
    def render(self) -> str:
        task_text = self.TASKS.get(
            self.query_type,
            "⚡ TASK: Analyze the provided data and make a trading decision\n"
        )
        
        # Replace any {'=' * 70} patterns with actual separators
        task_text = task_text.replace("{'=' * 70}", "=" * 70)
        
        return task_text


class ResponseFormatComponent(PromptComponent):
    """
    Expected response structure.
    
    Defines the exact JSON format the LLM should respond with,
    including required fields and validation rules.
    """
    
    FORMATS = {
        'STANDARD_DECISION': """
📋 RESPONSE FORMAT - REQUIRED STRUCTURE
{'=' * 70}

Respond with ONLY valid JSON in this exact format:

{
  "sentiment": "bullish" | "bearish" | "neutral",
  "confidence": 0-100,
  "action": "buy" | "sell" | "hold",
  "reasoning": "Detailed explanation with specific price levels and catalysts",
  "risk_factors": [
    "[CRITICAL|HIGH|MEDIUM]: Specific risk with timeframe",
    "[CRITICAL|HIGH|MEDIUM]: Another risk"
  ]
}

REQUIREMENTS:

✅ MUST INCLUDE:
   • Specific price levels (support, resistance, targets)
   • Key technical indicators driving decision
   • Risk factors with severity tags
   • Concrete reasoning, not generic statements

❌ DO NOT INCLUDE:
   • Markdown code blocks (```json)
   • Any text outside the JSON structure
   • Generic/vague reasoning like "mixed signals" or "uncertain"
   • Risks without severity tags

⚠️  IMPORTANT: Generate UNIQUE analysis for THIS stock - DO NOT copy examples!

REASONING QUALITY GUIDELINES:
   ❌ BAD:  "Bullish trend suggests holding position"
              (Too vague - no specific data)
   
   ✅ GOOD: "[ACTION]: [Position status if applicable]. [Key technical levels].
             [Trigger context if relevant]. [Specific support/resistance].
             [Concrete risk/reward assessment]."
   
   Example structure (adapt to YOUR analysis):
   "SELL: Position up +5.2%, approaching resistance at $145. With capital
    tight ($500 available), better opportunities exist. XYZ showing stronger
    momentum (RSI 68 vs 52). Risk/reward unfavorable here."

RISK FACTORS GUIDELINES:
   ❌ BAD:  ["Market volatility", "Economic uncertainty"]
              (Too generic - could apply to any stock any time)
   
   ✅ GOOD: ["[CRITICAL]: Earnings [specific date] could trigger [specific %] if miss",
             "[HIGH]: Fed meeting [specific date] may shift sentiment",
             "[MEDIUM]: Overbought RSI [actual value] suggests near-term pullback risk"]

⚠️  CRITICAL: Respond ONLY with valid JSON. No markdown blocks. No example text!
""",
        
        'RANKING': """
📋 RESPONSE FORMAT - RANKING STRUCTURE
{'=' * 70}

Respond with ONLY valid JSON in this format:

{
  "ranked_positions": [
    {
      "symbol": "NVDA",
      "rank": 1,
      "score": 92,
      "action": "keep",
      "reason": "Strongest technical setup: uptrend intact, RSI 62 (healthy), leading sector"
    },
    {
      "symbol": "AAPL",
      "rank": 8,
      "score": 52,
      "action": "sell",
      "reason": "Flat P&L (+0.13%), neutral momentum, better opportunities exist"
    }
  ],
  "summary": "Portfolio has 3 strong positions (keep), 4 neutral (hold), 3 weak (sell). Rotating ~$60K from bottom 3 will free capital for better opportunities."
}

REQUIREMENTS:
   • Include ALL positions provided
   • Rank from 1 (best) to N (worst)
   • Score each 0-100
   • Action must be: "keep", "hold", or "sell"
   • Reason must be specific with technical details
   • Summary should recommend total capital to rotate

ACTION GUIDELINES:
   • "keep": Top 20-30% of holdings (strongest)
   • "hold": Middle 40-60% (acceptable but monitor)
   • "sell": Bottom 20-30% (weak, rotate capital)

Be decisive - clearly identify winners and losers!
""",
        
        'COMPARISON': """
📋 RESPONSE FORMAT - COMPARISON STRUCTURE
{'=' * 70}

{
  "rankings": [
    {
      "symbol": "NVDA",
      "rank": 1,
      "score": 92,
      "reason": "Strongest setup: bullish trend, RSI 62, 1.8x volume, clear $870 target"
    },
    {
      "symbol": "AMD",
      "rank": 2,
      "score": 78,
      "reason": "Good trend but overbought RSI 75, better to wait for pullback to $140"
    },
    {
      "symbol": "INTC",
      "rank": 3,
      "score": 45,
      "reason": "Broken trend, RSI 38, weak momentum - avoid"
    }
  ],
  "recommendation": "Buy NVDA now. Wait for AMD pullback. Avoid INTC.",
  "summary": "Clear winner is NVDA with best risk/reward. AMD is second choice but timing not optimal. INTC shows weakness."
}

Be clear and decisive about which stock(s) to choose!
""",
    }
    
    def __init__(self, expected_format: str, **kwargs):
        super().__init__(**kwargs)
        self.expected_format = expected_format
        self.priority = 1  # Show last
    
    def render(self) -> str:
        format_text = self.FORMATS.get(
            self.expected_format,
            self.FORMATS['STANDARD_DECISION']
        )
        
        # Replace any {'=' * 70} patterns with actual separators
        format_text = format_text.replace("{'=' * 70}", "=" * 70)
        
        return format_text
