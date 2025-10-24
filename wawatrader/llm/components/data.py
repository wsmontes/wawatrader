"""
Data components: Technical, position, and portfolio information.

These components render market data in formats optimized for LLM analysis.
"""

from typing import Dict, Any
from ..components.base import PromptComponent, QueryContext


class TechnicalDataComponent(PromptComponent):
    """
    Technical indicators with adaptive detail level.
    
    Renders technical analysis data with format adjusted based on
    query type and detail level requirements.
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
        """Standard technical analysis format"""
        # Handle both nested and flat data structures
        signals = self.data
        
        # Check if data is nested (has dict values for 'price', 'trend') or flat
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
        
        output = f"""
📊 TECHNICAL DATA: {symbol}
{'=' * 70}
💰 Price: ${current_price:.2f}
"""
        
        # Trend analysis
        sma_20 = trend_data.get('sma20') or trend_data.get('sma_20', 0)
        sma_50 = trend_data.get('sma50') or trend_data.get('sma_50', 0)
        
        if current_price > sma_20 > sma_50:
            trend_emoji = '📈'
            trend_text = 'BULLISH TREND (strong - price > SMA20 > SMA50)'
        elif current_price > sma_20:
            trend_emoji = '📈'
            trend_text = 'BULLISH TREND (price above SMA20 - trend confirmed)'
        elif current_price < sma_20 < sma_50:
            trend_emoji = '📉'
            trend_text = 'BEARISH TREND (weak - price < SMA20 < SMA50)'
        elif current_price < sma_20:
            trend_emoji = '📉'
            trend_text = 'BEARISH TREND (price below SMA20 - downtrend confirmed)'
        else:
            trend_emoji = '➡️'
            trend_text = 'NEUTRAL TREND (consolidating)'
        
        output += f"{trend_emoji} {trend_text}\n"
        output += f"   SMA20: ${sma_20:.2f}, SMA50: ${sma_50:.2f}\n\n"
        
        # Momentum
        rsi = momentum_data.get('rsi', 50) if isinstance(momentum_data, dict) else 50
        if rsi > 75:
            momentum_text = "EXTREMELY OVERBOUGHT (caution - potential pullback)"
            momentum_emoji = "🔴"
        elif rsi > 70:
            momentum_text = "OVERBOUGHT (consider waiting for better entry)"
            momentum_emoji = "🟠"
        elif rsi < 25:
            momentum_text = "EXTREMELY OVERSOLD (potential bounce opportunity)"
            momentum_emoji = "🟢"
        elif rsi < 30:
            momentum_text = "OVERSOLD (potential reversal setup)"
            momentum_emoji = "🟡"
        elif 45 <= rsi <= 55:
            momentum_text = "NEUTRAL (no extreme momentum)"
            momentum_emoji = "⚪"
        elif rsi > 55:
            momentum_text = "POSITIVE MOMENTUM (bullish bias)"
            momentum_emoji = "🟢"
        else:
            momentum_text = "NEGATIVE MOMENTUM (bearish bias)"
            momentum_emoji = "🔴"
        
        output += f"{momentum_emoji} RSI: {rsi:.1f} ({momentum_text})\n"
        
        # MACD if available
        macd_line = momentum_data.get('macd')
        signal_line = momentum_data.get('macd_signal')
        if macd_line is not None and signal_line is not None:
            if macd_line > signal_line:
                output += f"📊 MACD: Bullish (MACD {macd_line:.2f} > Signal {signal_line:.2f})\n"
            else:
                output += f"📊 MACD: Bearish (MACD {macd_line:.2f} < Signal {signal_line:.2f})\n"
        
        # Volume
        vol_ratio = volume_data.get('ratio') or volume_data.get('volume_ratio', 1.0)
        if vol_ratio > 2.0:
            vol_text = "VERY HIGH volume (strong conviction)"
            vol_emoji = "🔥"
        elif vol_ratio > 1.5:
            vol_text = "HIGH volume (good confirmation)"
            vol_emoji = "📈"
        elif vol_ratio > 1.2:
            vol_text = "ABOVE AVERAGE volume (modest confirmation)"
            vol_emoji = "📊"
        elif vol_ratio < 0.7:
            vol_text = "LOW volume (weak conviction - be cautious)"
            vol_emoji = "⚠️"
        else:
            vol_text = "NORMAL volume"
            vol_emoji = "📊"
        
        output += f"{vol_emoji} Volume: {vol_ratio:.2f}x average ({vol_text})\n"
        
        # Volatility
        volatility = signals.get('volatility', {})
        atr = volatility.get('atr', 0)
        if atr:
            atr_pct = (atr / current_price * 100) if current_price > 0 else 0
            output += f"📏 ATR: ${atr:.2f} ({atr_pct:.1f}% of price)\n"
        
        # Bollinger Bands
        bb_width = volatility.get('bb_width', 0)
        if bb_width:
            if bb_width < 0.05:
                bb_text = "VERY LOW volatility - potential breakout pending"
            elif bb_width < 0.10:
                bb_text = "LOW volatility - consolidating"
            elif bb_width > 0.20:
                bb_text = "HIGH volatility - trending strongly"
            else:
                bb_text = "NORMAL volatility"
            
            output += f"📊 Bollinger Bands: {bb_text} (width: {bb_width:.2f})\n"
        
        return output
    
    def _summary_format(self) -> str:
        """Compact format for portfolio comparisons"""
        signals = self.data
        symbol = self.context.primary_symbol if self.context else 'UNKNOWN'
        
        price = signals.get('price', {}).get('close', 0)
        rsi = signals.get('momentum', {}).get('rsi', 50)
        sma_20 = signals.get('trend', {}).get('sma_20', 0)
        
        trend = "📈 Bull" if price > sma_20 else "📉 Bear"
        
        return f"   {symbol}: ${price:.2f}, {trend}, RSI {rsi:.0f}"
    
    def _minimal_format(self) -> str:
        """Minimal format for quick decisions"""
        signals = self.data
        symbol = self.context.primary_symbol if self.context else 'UNKNOWN'
        
        price = signals.get('price', {}).get('close', 0)
        rsi = signals.get('momentum', {}).get('rsi', 50)
        sma_20 = signals.get('trend', {}).get('sma_20', 0)
        
        trend = "Bullish" if price > sma_20 else "Bearish"
        
        return f"\n📊 {symbol}: ${price:.2f}, {trend} trend, RSI {rsi:.1f}\n"
    
    def _detailed_format(self) -> str:
        """Detailed format with all available indicators"""
        # For now, use standard format - can be enhanced later
        return self._standard_format()


class PositionDataComponent(PromptComponent):
    """
    Current position details with P&L context.
    
    Shows position entry, current value, profit/loss, and management
    guidance specific to the position status.
    """
    
    def __init__(self, data: Dict[str, Any], **kwargs):
        super().__init__(data, **kwargs)
        self.priority = 8
    
    def is_relevant(self, context: QueryContext) -> bool:
        """Only relevant for position reviews"""
        return context.query_type == QueryContext.POSITION_REVIEW
    
    def render(self) -> str:
        if not self.validate_data():
            return ""
        
        pos = self.data
        symbol = pos.get('symbol', 'UNKNOWN')
        shares = float(pos.get('qty', 0))
        avg_price = float(pos.get('avg_entry_price', 0))
        current_price = float(pos.get('current_price', 0))
        
        # Calculate P&L
        if avg_price > 0:
            pnl_pct = ((current_price - avg_price) / avg_price * 100)
        else:
            pnl_pct = 0
        
        pnl_dollars = (current_price - avg_price) * shares
        market_value = current_price * shares
        cost_basis = avg_price * shares
        
        # Determine status and guidance
        if pnl_pct < -10:
            status = "🔴 MAJOR LOSS (consider stop-loss immediately)"
            guidance = "Strong SELL signal - cut losses before they worsen"
        elif pnl_pct < -5:
            status = "🟠 SIGNIFICANT LOSS (stop-loss territory)"
            guidance = "Consider SELL - position moving against you"
        elif pnl_pct < -2:
            status = "🟡 UNDERWATER (watch closely)"
            guidance = "Monitor for recovery or further deterioration"
        elif pnl_pct > 20:
            status = "🟢 EXCELLENT PROFIT (consider taking gains)"
            guidance = "Strong candidate for profit-taking or trailing stop"
        elif pnl_pct > 10:
            status = "💚 STRONG PROFIT (let winners run or take partial)"
            guidance = "Good position - consider partial sell or trailing stop"
        elif pnl_pct > 5:
            status = "✅ PROFITABLE (let winners run)"
            guidance = "Keep if trend intact, consider sell if better opportunities"
        elif pnl_pct > 0:
            status = "💚 SMALL PROFIT (monitor)"
            guidance = "Marginal winner - evaluate vs alternatives"
        elif pnl_pct > -1:
            status = "➡️ BREAKEVEN (evaluate trend)"
            guidance = "Flat position - worth the capital allocation?"
        else:
            status = "📉 SMALL LOSS (monitor)"
            guidance = "Minor loss - decide if recovery likely"
        
        output = f"""
💼 POSITION DETAILS: {symbol}
{'=' * 70}
⚠️  YOU ALREADY OWN THIS STOCK - Evaluation for SELL/HOLD decision

Current Holdings:
   • Shares: {shares:,.0f}
   • Entry Price: ${avg_price:.2f}
   • Current Price: ${current_price:.2f}
   • Cost Basis: ${cost_basis:,.0f}
   • Market Value: ${market_value:,.0f}

Performance:
   • P&L: {pnl_pct:+.2f}% (${pnl_dollars:+,.0f})
   • Status: {status}
   • Guidance: {guidance}

🎯 POSITION MANAGEMENT CONTEXT:
This is an EXISTING position. Your decision options:
   
   1️⃣ SELL: Exit position if:
      • Technical setup has deteriorated
      • Profit target reached (lock in gains)
      • Stop-loss hit (cut losses)
      • Better opportunities exist elsewhere
      • Position is weak compared to portfolio average
      • Capital needed for higher-conviction trades
   
   2️⃣ HOLD: Keep position if:
      • Trend remains intact and healthy
      • No technical red flags
      • Still one of best holdings in portfolio
      • P&L status acceptable and improving
   
   3️⃣ BUY: Add to position ONLY if:
      • Strong bullish continuation setup
      • High conviction (rare case)
      • Position sizing rules allow
      • Best opportunity available right now

⚠️  CRITICAL REMINDER:
   • Don't hold losers hoping for recovery - cut losses decisively
   • Don't get emotionally attached to positions
   • Capital rotation creates more opportunities than buy-and-hold
   • Compare this position vs alternatives, not just absolute merit
"""
        
        return output


class PortfolioSummaryComponent(PromptComponent):
    """
    Overall portfolio state and context.
    
    Provides high-level portfolio metrics relevant for portfolio-level
    decisions like audits and rotation strategies.
    """
    
    def __init__(self, data: Dict[str, Any], **kwargs):
        super().__init__(data, **kwargs)
        self.priority = 7
    
    def is_relevant(self, context: QueryContext) -> bool:
        """Relevant for portfolio-level queries"""
        return context.query_type in [
            QueryContext.PORTFOLIO_AUDIT,
            QueryContext.RISK_ASSESSMENT,
        ] or context.trigger == QueryContext.CAPITAL_CONSTRAINT
    
    def render(self) -> str:
        if not self.validate_data():
            return ""
        
        portfolio = self.data
        total_value = portfolio.get('total_value', 0)
        buying_power = portfolio.get('buying_power', 0)
        num_positions = portfolio.get('num_positions', 0)
        daily_pnl = portfolio.get('daily_pnl', 0)
        daily_pnl_pct = portfolio.get('daily_pnl_pct', 0)
        
        # Calculate buying power percentage
        bp_pct = (buying_power / total_value * 100) if total_value > 0 else 0
        
        # Determine capital status
        if bp_pct < 1:
            capital_status = "🔴 CRITICAL - Nearly fully invested"
            capital_advice = "Need to sell positions to free capital for opportunities"
        elif bp_pct < 5:
            capital_status = "🟠 CONSTRAINED - Very limited dry powder"
            capital_advice = "Consider rotating capital from weaker positions"
        elif bp_pct < 10:
            capital_status = "🟡 LOW - Limited buying power"
            capital_advice = "Be selective with new positions"
        elif bp_pct < 25:
            capital_status = "🟢 MODERATE - Reasonable flexibility"
            capital_advice = "Good balance between deployment and flexibility"
        else:
            capital_status = "💚 HIGH - Significant dry powder"
            capital_advice = "Plenty of capital available for opportunities"
        
        # Get top holdings if available
        top_symbols = portfolio.get('top_3_symbols', [])
        top_holdings_text = ""
        if top_symbols:
            top_holdings_text = f"   • Top Holdings: {', '.join(top_symbols)}\n"
        
        output = f"""
💼 PORTFOLIO STATE
{'=' * 70}
   • Total Value: ${total_value:,.0f}
   • Buying Power: ${buying_power:,.0f} ({bp_pct:.1f}%)
   • Positions: {num_positions}
{top_holdings_text}   • Today's P&L: {daily_pnl_pct:+.2f}% (${daily_pnl:+,.0f})

📊 Capital Status: {capital_status}
   → {capital_advice}
"""
        
        return output


class NewsComponent(PromptComponent):
    """
    Recent news with relevance filtering.
    
    Includes recent news articles for context, but with clear guidance
    that technical signals should take priority.
    """
    
    def __init__(self, data: Dict[str, Any], **kwargs):
        super().__init__(data, **kwargs)
        self.priority = 5
    
    def is_relevant(self, context: QueryContext) -> bool:
        """Only include news for specific query types"""
        return (
            context.include_news and
            context.query_type in [
                QueryContext.NEW_OPPORTUNITY,
                QueryContext.POSITION_REVIEW,
                QueryContext.COMPARATIVE_ANALYSIS,
            ]
        )
    
    def render(self) -> str:
        if not self.validate_data():
            return ""
        
        # Handle different data formats
        if isinstance(self.data, list):
            # Data is directly a list of news articles
            news_items = self.data
        elif isinstance(self.data, dict):
            # Data is a dict with 'articles' key, or might be empty
            news_items = self.data.get('articles', self.data.get('news', []))
        else:
            return ""
        
        if not news_items:
            return ""
        
        output = f"""
📰 MARKET CONTEXT (30% Decision Weight)
{'=' * 70}
Recent news (context only - don't override strong technical signals):

"""
        
        # Show up to 3 most recent articles
        for article in news_items[:3]:
            if isinstance(article, dict):
                headline = article.get('headline', article.get('title', ''))
                if headline:
                    # Truncate to 100 chars for clarity
                    headline_short = headline[:100] + "..." if len(headline) > 100 else headline
                    output += f"   • {headline_short}\n"
            elif isinstance(article, str):
                # Article is just a string
                headline_short = article[:100] + "..." if len(article) > 100 else article
                output += f"   • {headline_short}\n"
        
        output += "\n⚠️  Technical signals (70% weight) should take priority over news\n"
        
        return output
