"""
Data components: Technical, position, and portfolio information.

SIMPLIFIED FOR SMALL LLMs (4B-7B parameters)
Philosophy: Provide PRE-COMPUTED INTERPRETATIONS, not raw numbers.
"""

from typing import Dict, Any
from ..components.base import PromptComponent, QueryContext


class TechnicalDataComponent(PromptComponent):
    """
    Technical indicators optimized for small LLMs.
    
    Pre-computes all analysis and provides clear verdicts instead of raw numbers.
    This eliminates numerical reasoning requirements for 4B parameter models.
    """
    
    def __init__(self, data: Dict[str, Any], **kwargs):
        super().__init__(data, **kwargs)
        self.priority = 8
    
    def render(self) -> str:
        if not self.validate_data():
            return ""
        
        # Adaptive rendering based on context
        if self.context:
            if self.context.query_type == QueryContext.PORTFOLIO_AUDIT:
                return self._summary_format()
            elif self.context.detail_level == 'detailed':
                return self._detailed_format()
            elif self.context.detail_level == 'minimal':
                return self._minimal_format()
        
        return self._standard_format()
    
    def _standard_format(self) -> str:
        """
        SIMPLIFIED format for small LLMs.
        Provides PRE-COMPUTED verdicts instead of raw numbers.
        """
        signals = self.data
        
        # Handle both nested and flat data structures
        has_nested_price = isinstance(signals.get('price'), dict)
        has_nested_trend = isinstance(signals.get('trend'), dict)
        
        if has_nested_price or has_nested_trend:
            # Nested structure (from get_latest_signals)
            price_data = signals.get('price', {})
            trend_data = signals.get('trend', {})
            momentum_data = signals.get('momentum', {})
            volume_data = signals.get('volume', {})
            current_price = price_data.get('close', price_data.get('price', 0)) if isinstance(price_data, dict) else 0
        else:
            # Flat structure (from _signals_to_technical_data)
            price_data = signals
            trend_data = signals
            momentum_data = signals
            volume_data = signals
            current_price = signals.get('price', signals.get('close', 0))
        
        symbol = self.context.primary_symbol if self.context else 'UNKNOWN'
        
        # Get key values
        sma_20 = trend_data.get('sma20') or trend_data.get('sma_20', 0)
        sma_50 = trend_data.get('sma50') or trend_data.get('sma_50', 0)
        rsi = momentum_data.get('rsi', 50) if isinstance(momentum_data, dict) else 50
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
        
        # BUILD OUTPUT
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
    
    def _summary_format(self) -> str:
        """Quick summary for portfolio audits"""
        signals = self.data
        symbol = self.context.primary_symbol if self.context else 'UNKNOWN'
        
        price = signals.get('price', {}).get('close', 0) if isinstance(signals.get('price'), dict) else signals.get('price', 0)
        rsi = signals.get('momentum', {}).get('rsi', 50) if isinstance(signals.get('momentum'), dict) else signals.get('rsi', 50)
        sma_20 = signals.get('trend', {}).get('sma_20', 0)
        
        trend = "📈 Bull" if price > sma_20 else "📉 Bear"
        
        return f"   {symbol}: ${price:.2f}, {trend}, RSI {rsi:.0f}"
    
    def _minimal_format(self) -> str:
        """Minimal format for quick decisions"""
        signals = self.data
        symbol = self.context.primary_symbol if self.context else 'UNKNOWN'
        
        price = signals.get('price', {}).get('close', 0) if isinstance(signals.get('price'), dict) else signals.get('price', 0)
        trend = signals.get('trend', "Unknown")
        
        return f"{symbol}: ${price:.2f} - {trend}"
    
    def _detailed_format(self) -> str:
        """Detailed format (same as standard for now)"""
        return self._standard_format()


class PositionDataComponent(PromptComponent):
    """Current position information"""
    
    def __init__(self, data: Dict[str, Any], **kwargs):
        super().__init__(data, **kwargs)
        self.priority = 9
    
    def render(self) -> str:
        if not self.validate_data():
            return ""
        
        position = self.data
        symbol = position.get('symbol', 'UNKNOWN')
        qty = position.get('qty', 0)
        entry = position.get('avg_entry_price', 0)
        current = position.get('current_price', entry)
        pl = position.get('unrealized_pl', 0)
        pl_pct = position.get('unrealized_plpc', 0) * 100
        
        output = f"""
{'=' * 70}
📌 EXISTING POSITION: {symbol}
{'=' * 70}
Quantity: {qty} shares
Entry Price: ${entry:.2f}
Current Price: ${current:.2f}
P/L: ${pl:.2f} ({pl_pct:+.2f}%)

🤔 CONTEXT: You ALREADY OWN this position.
   → Consider if you should ADD, HOLD, or REDUCE exposure
   → Review if original thesis still holds
   → Check if stop loss or profit target hit
"""
        
        return output


class PortfolioDataComponent(PromptComponent):
    """Portfolio-level metrics"""
    
    def __init__(self, data: Dict[str, Any], **kwargs):
        super().__init__(data, **kwargs)
        self.priority = 7
    
    def render(self) -> str:
        if not self.validate_data():
            return ""
        
        portfolio = self.data
        equity = portfolio.get('equity', 0)
        cash = portfolio.get('cash', 0)
        pl_today = portfolio.get('pl_today', 0)
        pl_total = portfolio.get('pl_total', 0)
        
        output = f"""
{'=' * 70}
💼 PORTFOLIO STATUS
{'=' * 70}
Total Equity: ${equity:,.2f}
Available Cash: ${cash:,.2f}
Today's P/L: ${pl_today:+,.2f}
Total P/L: ${pl_total:+,.2f}
"""
        
        return output
