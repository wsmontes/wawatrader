"""
LLM Bridge Layer

Orchestrates communication between numerical indicators and Gemma 3 LLM.
Converts numbers → text → LLM → structured data → validation.

CRITICAL: Never trust LLM numerical outputs directly. Always validate against
hard numerical thresholds and risk rules.
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger
from openai import OpenAI  # LM Studio uses OpenAI-compatible API

from config.settings import settings

# New modular system (lazy import to avoid circular dependency)
_modular_analyzer = None

def get_modular_analyzer():
    """Get or create modular analyzer instance."""
    global _modular_analyzer
    if _modular_analyzer is None:
        from wawatrader.llm_v2 import ModularLLMAnalyzer
        _modular_analyzer = ModularLLMAnalyzer()
    return _modular_analyzer


class LLMBridge:
    """
    Bridge between numerical technical analysis and LLM sentiment analysis.
    
    Architecture:
    1. Numerical Data (from indicators.py) → Text Description
    2. Text Description + Market Context → LLM Prompt
    3. LLM Response → Structured JSON
    4. JSON → Validation → Trading Signal
    
    The LLM provides sentiment/interpretation, NOT numerical decisions.
    """
    
    # Trading profile definitions (Week 1-2: More action-oriented system prompts)
    TRADING_PROFILES = {
        'conservative': {
            'name': 'Conservative',
            'description': 'Risk-averse with capital preservation focus',
            'system_prompt': (
                "You are a professional conservative trading analyst. Your priority is capital preservation "
                "while capturing high-probability opportunities. \n\n"
                "KEY PRINCIPLES:\n"
                "- Only recommend BUY when trend, momentum, and volume all confirm with >75% confidence\n"
                "- Recommend SELL at first signs of technical breakdown or major negative catalysts\n"
                "- HOLD is acceptable but should not be default - make decisions when signals are clear\n"
                "- Be specific: include price levels, stop-losses, and timeframes\n\n"
                "Respond ONLY with valid JSON. No markdown, no explanations outside JSON structure."
            ),
            'min_confidence_buy': 75,
            'min_confidence_sell': 70,
            'risk_emphasis': 'high'
        },
        'moderate': {
            'name': 'Moderate',
            'description': 'Balanced approach between risk and reward',
            'system_prompt': (
                "You are a professional balanced trading analyst seeking optimal risk-adjusted returns. "
                "You make decisive calls when technical indicators show clear probability. \n\n"
                "KEY PRINCIPLES:\n"
                "- Recommend BUY when trend aligns with momentum, even if news is mixed (≥65% confidence)\n"
                "- Recommend SELL when technicals weaken or major risks emerge (≥60% confidence)\n"
                "- Favor ACTION over HOLD - only hold when truly uncertain (<60% either direction)\n"
                "- Balance opportunities and risks, but don't let minor concerns prevent good trades\n\n"
                "Respond ONLY with valid JSON. Be specific with price targets and risk levels."
            ),
            'min_confidence_buy': 65,
            'min_confidence_sell': 60,
            'risk_emphasis': 'medium'
        },
        'aggressive': {
            'name': 'Aggressive',
            'description': 'Active trading seeking high returns',
            'system_prompt': (
                "You are a professional aggressive trader focused on capturing momentum opportunities quickly. "
                "You act decisively on technical signals and favor action over waiting. \n\n"
                "KEY PRINCIPLES:\n"
                "- Recommend BUY on bullish trend + momentum, don't wait for perfect confirmation (≥55% confidence)\n"
                "- Recommend SELL on any technical weakness or negative catalysts (≥50% confidence)\n"
                "- MINIMIZE HOLD recommendations - take action when any clear signal appears\n"
                "- Accept higher risk for potential outsized gains\n"
                "- Specify aggressive price targets with appropriate stop-losses\n\n"
                "Respond ONLY with valid JSON. Be decisive and action-oriented."
            ),
            'min_confidence_buy': 55,
            'min_confidence_sell': 50,
            'risk_emphasis': 'low'
        },
        'maximum': {
            'name': 'Maximum Revenue and Risk',
            'description': 'Maximum returns with corresponding risk acceptance',
            'system_prompt': (
                "You are a high-octane trader seeking maximum returns through active portfolio rotation. "
                "You identify opportunities aggressively and act without hesitation.\n\n"
                "KEY PRINCIPLES:\n"
                "- PORTFOLIO MANAGEMENT FIRST: If analyzing an existing position, prioritize SELL decisions to rotate capital into better opportunities\n"
                "- For NEW opportunities: Recommend BUY on bullish technical signals (≥50% confidence)\n"
                "- For EXISTING positions: Recommend SELL aggressively on ANY of:\n"
                "  * Weakening momentum (RSI dropping, MACD turning negative)\n"
                "  * Better opportunities available elsewhere\n"
                "  * Profit target reached (even small gains - rotate fast)\n"
                "  * Position underwater with no recovery signs\n"
                "- RARELY recommend HOLD - prefer decisive action (BUY new or SELL existing)\n"
                "- Portfolio rotation creates more opportunities than buy-and-hold\n"
                "- Set aggressive price targets and wider stop-losses for big moves\n\n"
                "💡 TRADING WISDOM: 'The best traders rotate capital constantly. Don't marry your positions!'\n\n"
                "Respond ONLY with valid JSON. Be bold, decisive, and rotation-focused."
            ),
            'min_confidence_buy': 50,
            'min_confidence_sell': 40,  # Lower threshold for SELL to enable rotation
            'risk_emphasis': 'minimal'
        }
    }
    
    def __init__(self):
        """Initialize LLM connection"""
        
        self.client = OpenAI(
            base_url=settings.lm_studio.base_url,
            api_key="not-needed"  # LM Studio doesn't require API key
        )
        
        self.model = settings.lm_studio.model
        self.temperature = settings.lm_studio.temperature
        self.max_tokens = settings.lm_studio.max_tokens
        self.trading_profile = settings.lm_studio.trading_profile
        
        # Initialize conversation logging
        self.conversation_log = settings.project_root / "logs" / "llm_conversations.jsonl"
        self.conversation_log.parent.mkdir(exist_ok=True)
        
        # Validate and get profile config
        self.profile_config = self.TRADING_PROFILES.get(
            self.trading_profile, 
            self.TRADING_PROFILES['moderate']
        )
        
        logger.info(f"LLM Bridge initialized (model: {self.model}, profile: {self.profile_config['name']})")
    
    def indicators_to_text(self, signals: Dict[str, Any]) -> str:
        """
        Convert numerical indicators to structured, decision-focused text.
        
        Week 1-2 Optimization: Clearer hierarchy and actionable interpretation.
        
        Args:
            signals: Dict from get_latest_signals() with price, trend, momentum, etc.
        
        Returns:
            Structured text description optimized for LLM decision-making
        """
        if not signals:
            return "No market data available."
        
        # Extract components
        price = signals.get('price', {})
        trend = signals.get('trend', {})
        momentum = signals.get('momentum', {})
        volatility = signals.get('volatility', {})
        volume = signals.get('volume', {})
        
        # Build structured description with clear hierarchy
        parts = []
        
        # 1. PRICE & TREND (Most important for decisions)
        if price:
            close = price.get('close')
            if close:
                parts.append(f"💰 PRICE: ${close:.2f}")
        
        if trend:
            sma_20 = trend.get('sma_20')
            sma_50 = trend.get('sma_50')
            close_price = price.get('close')
            
            if sma_20 and sma_50 and close_price:
                # Determine trend with actionable context
                if sma_20 > sma_50:
                    trend_desc = "📈 BULLISH TREND"
                    if close_price > sma_20:
                        trend_strength = "(price above SMA20 - trend confirmed)"
                    else:
                        trend_strength = "(price below SMA20 - potential pullback)"
                else:
                    trend_desc = "📉 BEARISH TREND"
                    if close_price < sma_20:
                        trend_strength = "(price below SMA20 - trend confirmed)"
                    else:
                        trend_strength = "(price above SMA20 - potential reversal?)"
                
                parts.append(f"{trend_desc} {trend_strength}")
                parts.append(f"   - SMA20: ${sma_20:.2f}, SMA50: ${sma_50:.2f}")
            
            macd = trend.get('macd')
            macd_signal = trend.get('macd_signal')
            if macd is not None and macd_signal is not None:
                macd_desc = "bullish crossover" if macd > macd_signal else "bearish crossover"
                parts.append(f"   - MACD: {macd:.2f} ({macd_desc})")
        
        # 2. MOMENTUM (Key for timing)
        if momentum:
            rsi = momentum.get('rsi')
            if rsi:
                if rsi > 70:
                    rsi_desc = f"⚠️  RSI: {rsi:.1f} (OVERBOUGHT - caution on new longs)"
                elif rsi > 60:
                    rsi_desc = f"📊 RSI: {rsi:.1f} (strong bullish momentum)"
                elif rsi < 30:
                    rsi_desc = f"⚠️  RSI: {rsi:.1f} (OVERSOLD - potential bounce opportunity)"
                elif rsi < 40:
                    rsi_desc = f"📊 RSI: {rsi:.1f} (weak/bearish momentum)"
                else:
                    rsi_desc = f"📊 RSI: {rsi:.1f} (neutral momentum)"
                parts.append(rsi_desc)
        
        # 3. VOLUME (Confirms conviction)
        if volume:
            volume_ratio = volume.get('volume_ratio')
            if volume_ratio:
                if volume_ratio > 1.5:
                    vol_desc = f"🔥 VOLUME: {volume_ratio:.2f}x average (HIGH - strong institutional conviction)"
                elif volume_ratio > 1.2:
                    vol_desc = f"📊 VOLUME: {volume_ratio:.2f}x average (above average - confirmed move)"
                elif volume_ratio < 0.7:
                    vol_desc = f"💤 VOLUME: {volume_ratio:.2f}x average (LOW - weak conviction, be cautious)"
                else:
                    vol_desc = f"📊 VOLUME: {volume_ratio:.2f}x average (normal)"
                parts.append(vol_desc)
        
        # 4. VOLATILITY (Risk assessment)
        if volatility:
            atr = volatility.get('atr')
            bb_width = volatility.get('bb_width')
            if atr:
                parts.append(f"📏 Volatility: ATR ${atr:.2f}")
            if bb_width:
                if bb_width > 10:
                    width_desc = "high volatility - larger position sizing risk"
                elif bb_width < 5:
                    width_desc = "low volatility - potential breakout pending"
                else:
                    width_desc = "moderate volatility"
                parts.append(f"   - Bollinger Bands: {width_desc} (width: {bb_width:.2f})")
        
        return "\n".join(parts)
    
    def create_analysis_prompt(
        self,
        symbol: str,
        indicators_text: str,
        news: Optional[List[Dict[str, Any]]] = None,
        current_position: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create an optimized prompt for decisive, specific trading recommendations.
        
        Week 1-2 Optimizations:
        - Forces decisiveness (reduces HOLD bias)
        - Rebalances technical vs news weight (70/30)
        - Adds confidence calibration examples
        - Enhances position-aware decision logic
        - Requires specific reasoning with price targets
        
        Args:
            symbol: Stock ticker (e.g., "AAPL")
            indicators_text: Human-readable indicator description
            news: Optional list of recent news articles
            current_position: Optional current position info (shares, avg_price, etc.)
        
        Returns:
            Optimized formatted prompt for LLM
        """
        prompt_parts = [
            f"⚡ TRADING DECISION REQUIRED: {symbol}",
            "=" * 60,
            "",
            f"TRADING PROFILE: {self.profile_config['name']}",
            f"Style: {self.profile_config['description']}",
            f"Min Confidence for Action: BUY ≥{self.profile_config['min_confidence_buy']}%, SELL ≥{self.profile_config['min_confidence_sell']}%",
            "",
            "=" * 60,
            "📊 PRIMARY SIGNALS (70% Decision Weight)",
            "=" * 60,
            "",
            indicators_text,
        ]
        
        # Add position context with actionable insights
        if current_position:
            shares = current_position.get('qty', 0)
            avg_price = current_position.get('avg_entry_price', 0)
            current_price = current_position.get('current_price', 0)
            
            if shares and avg_price and current_price:
                pnl_pct = ((current_price - avg_price) / avg_price) * 100
                
                # Determine position status and action hint
                if pnl_pct < -2:
                    status = "UNDERWATER (consider stop-loss or averaging down if trend confirms)"
                elif pnl_pct > 5:
                    status = "PROFITABLE (consider taking profits or trailing stop)"
                elif pnl_pct > 0:
                    status = "SMALL PROFIT (let winners run if trend intact)"
                else:
                    status = "NEAR BREAKEVEN (evaluate trend strength carefully)"
                
                prompt_parts.extend([
                    "",
                    "=" * 60,
                    "💼 POSITION MANAGEMENT - CRITICAL",
                    "=" * 60,
                    f"⚠️  YOU ALREADY OWN: {shares} shares @ ${avg_price:.2f} avg entry",
                    f"Current Price: ${current_price:.2f}",
                    f"Position P&L: {pnl_pct:+.2f}%",
                    f"Position Status: {status}",
                    "",
                    "🎯 PORTFOLIO MANAGEMENT PRIORITIES:",
                    "   1. Weak holdings → SELL to free capital for better opportunities",
                    "   2. Deteriorating technicals → SELL to limit losses",
                    "   3. Profit targets reached → SELL to lock in gains",
                    "   4. Better opportunities exist → Consider rotating capital",
                    "",
                    "⚡ DECISION OPTIONS:",
                    "   • SELL: Exit if technicals turned bearish OR profit target reached OR better opportunities available",
                    "   • HOLD: Keep if trend remains intact and no red flags",
                    "   • BUY: Add to position ONLY if showing strong bullish continuation (rare)",
                    "",
                    "❌ BIAS ALERT: Don't hold losers hoping for recovery - cut losses early!",
                ])
        
        # Add news as CONTEXT not PRIMARY DRIVER (reduced from 3 to 2 articles)
        if news:
            prompt_parts.extend([
                "",
                "=" * 60,
                "📰 MARKET CONTEXT (30% Decision Weight)",
                "=" * 60,
                "Recent news (context only - don't override strong technical signals):",
                ""
            ])
            for article in news[:2]:  # Reduced to 2 articles
                headline = article.get('headline', '')
                if headline:
                    # Truncate to 120 chars for clarity
                    headline_short = headline[:120] + "..." if len(headline) > 120 else headline
                    prompt_parts.append(f"• {headline_short}")
            prompt_parts.append("")
        
        # FORCE DECISIVENESS with clear framework
        prompt_parts.extend([
            "=" * 60,
            "⚠️  DECISION FRAMEWORK - BE DECISIVE",
            "=" * 60,
            "",
            "You MUST choose BUY, SELL, or HOLD based on:",
            "",
            "✅ BUY Criteria:",
            "   - Bullish trend (price > SMA20) + positive momentum (RSI 50-70)",
            "   - Volume confirms (≥1.2x average shows conviction)",
            "   - News is neutral-to-positive OR technical signals override news",
            f"   - Confidence ≥{self.profile_config['min_confidence_buy']}%",
            "",
            "❌ SELL Criteria:",
            "   - Bearish trend (price < SMA20) OR weakening momentum (RSI <40 or >75)",
            "   - Major negative catalyst OR technical breakdown",
            f"   - Confidence ≥{self.profile_config['min_confidence_sell']}%",
            "",
            "⏸️  HOLD - Reserve for GENUINELY MIXED signals only:",
            "   - Conflicting technical + fundamental signals of equal strength",
            "   - Awaiting key catalyst within 24-48 hours (earnings, Fed decision)",
            "   - Confidence <60% in either direction",
            "",
            "⚡ DEFAULT TO ACTION: If trend and momentum align, favor BUY or SELL over HOLD",
            ""
        ])
        
        # Add confidence calibration guide
        prompt_parts.extend([
            "=" * 60,
            "📊 CONFIDENCE CALIBRATION GUIDE",
            "=" * 60,
            "",
            "90-100%: All indicators strongly aligned, clear direction",
            "         Example: Bullish trend + RSI 60 + high volume + positive catalyst",
            "",
            "75-89%:  Most indicators aligned, one minor conflict",
            "         Example: Bullish trend + neutral RSI + positive news",
            "",
            "60-74%:  Mixed signals but dominant factor clear",
            "         Example: Bullish trend + negative news (trend usually prevails)",
            "",
            "40-59%:  Genuinely conflicting signals, TRUE uncertainty",
            "         Example: Bullish long-term but bearish short-term momentum",
            "",
            "<40%:    Insufficient conviction - Default to HOLD",
            ""
        ])
        
        # Enhanced response format with specific requirements
        prompt_parts.extend([
            "=" * 60,
            "📝 RESPONSE FORMAT - STRICT REQUIREMENTS",
            "=" * 60,
            "",
            "Provide your analysis in this JSON format:",
            "{",
            '  "sentiment": "bullish" | "bearish" | "neutral",',
            '  "confidence": 0-100,',
            '  "action": "buy" | "sell" | "hold",',
            '  "reasoning": "MUST include: (1) Primary technical signal driving decision, (2) Key price level (support/resistance), (3) Catalyst or confirmation",',
            '  "risk_factors": [',
            '    "[CRITICAL|HIGH|MEDIUM]: Specific risk with timeframe",',
            '    "Format: [SEVERITY]: What could go wrong and when"',
            '  ]',
            "}",
            "",
            "REASONING QUALITY REQUIREMENTS:",
            "❌ BAD: 'Bullish trend suggests holding position'",
            "✅ GOOD: 'BUY: Price broke $250 resistance on 1.67x volume. RSI at 56 shows room to run. Target $265 (+6%), stop $245 (-2%)'",
            "",
            "RISK FACTOR REQUIREMENTS:",
            "❌ BAD: ['Market volatility', 'Economic uncertainty']",
            "✅ GOOD: ['[CRITICAL]: Earnings Oct 30 could trigger -8% if miss', '[HIGH]: Fed meeting Oct 25 may shift sentiment']",
            "",
            "⚠️  CRITICAL: Respond ONLY with valid JSON. No markdown code blocks, no extra text."
        ])
        
        return "\n".join(prompt_parts)
    
    def query_llm(self, prompt: str, symbol: str = None) -> Optional[str]:
        """
        Send prompt to LLM and get response.
        
        Args:
            prompt: The prompt to send
        
        Returns:
            LLM response text, or None if error
        """
        try:
            logger.debug(f"Querying LLM... (prompt length: {len(prompt)} chars)")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self.profile_config['system_prompt']
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                logger.debug(f"LLM response: {content[:100]}...")
                
                # Log the conversation
                self._log_conversation(prompt, content, symbol)
                
                return content
            else:
                logger.error("LLM returned empty response")
                return None
                
        except Exception as e:
            logger.error(f"LLM query failed: {e}")
            return None
    
    def _log_conversation(self, prompt: str, response: str, symbol: str = None):
        """
        Log LLM conversation for dashboard display and debugging.
        
        Args:
            prompt: The input prompt sent to LLM
            response: The response received from LLM
            symbol: Optional symbol being analyzed
        """
        try:
            import json
            from datetime import datetime
            
            conversation_entry = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol or 'unknown',
                'prompt': prompt,
                'response': response,
                'prompt_length': len(prompt),
                'response_length': len(response)
            }
            
            with open(self.conversation_log, 'a') as f:
                f.write(json.dumps(conversation_entry) + '\n')
                
        except Exception as e:
            logger.error(f"Failed to log LLM conversation: {e}")
    
    def parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Parse LLM response into structured data.
        
        CRITICAL: Validates structure but does NOT trust numerical decisions.
        The trading agent must apply its own risk rules.
        
        Args:
            response: Raw LLM response text
        
        Returns:
            Parsed and validated dict, or None if invalid
        """
        if not response:
            return None
        
        try:
            # Try to extract JSON from response
            # LLM might wrap it in markdown code blocks
            response_clean = response.strip()
            
            # Remove markdown code blocks if present
            if response_clean.startswith("```json"):
                response_clean = response_clean[7:]
            elif response_clean.startswith("```"):
                response_clean = response_clean[3:]
            
            if response_clean.endswith("```"):
                response_clean = response_clean[:-3]
            
            response_clean = response_clean.strip()
            
            # Parse JSON
            data = json.loads(response_clean)
            
            # Validate required fields
            required_fields = ['sentiment', 'confidence', 'action', 'reasoning']
            for field in required_fields:
                if field not in data:
                    logger.error(f"LLM response missing required field: {field}")
                    return None
            
            # Validate sentiment
            if data['sentiment'] not in ['bullish', 'bearish', 'neutral']:
                logger.error(f"Invalid sentiment: {data['sentiment']}")
                return None
            
            # Validate action
            if data['action'] not in ['buy', 'sell', 'hold']:
                logger.error(f"Invalid action: {data['action']}")
                return None
            
            # Validate confidence (0-100)
            try:
                confidence = float(data['confidence'])
                if confidence < 0 or confidence > 100:
                    logger.error(f"Confidence out of range: {confidence}")
                    return None
                data['confidence'] = confidence
            except (ValueError, TypeError):
                logger.error(f"Invalid confidence value: {data['confidence']}")
                return None
            
            # Ensure reasoning is a string
            if not isinstance(data['reasoning'], str):
                logger.error("Reasoning must be a string")
                return None
            
            # Risk factors are optional but should be a list if present
            if 'risk_factors' in data and not isinstance(data['risk_factors'], list):
                logger.warning("risk_factors should be a list, converting")
                data['risk_factors'] = [str(data['risk_factors'])]
            
            logger.debug(f"Parsed LLM response: {data['sentiment']} ({data['confidence']}%) - {data['action']}")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response was: {response[:200]}...")
            return None
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return None
    
    # ========================================================================
    # NEW MODULAR ANALYSIS METHODS (V2)
    # ========================================================================
    
    def analyze_market_v2(
        self,
        symbol: str,
        signals: Dict[str, Any],
        news: Optional[List[Dict[str, Any]]] = None,
        current_position: Optional[Dict[str, Any]] = None,
        portfolio_summary: Optional[Dict[str, Any]] = None,
        trigger: str = 'SCHEDULED_CYCLE',
        overnight_context: Optional[Dict[str, Any]] = None,
        use_modular: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Enhanced market analysis using new modular prompt system.
        
        Automatically routes to appropriate query type:
        - NEW_OPPORTUNITY if no current_position
        - POSITION_REVIEW if current_position exists
        
        Args:
            symbol: Stock ticker
            signals: Dict from get_latest_signals()
            news: Optional news articles
            current_position: Optional current position info
            portfolio_summary: Optional portfolio context
            trigger: What triggered this analysis
            overnight_context: Optional overnight deep analysis results
            use_modular: If True, use new modular system; if False, fall back to legacy
        
        Args:
            symbol: Stock ticker
            signals: Dict from get_latest_signals()
            news: Optional news articles
            current_position: Optional current position info
            portfolio_summary: Optional portfolio context
            trigger: What triggered this analysis
            use_modular: If True, use new modular system; if False, fall back to legacy
        
        Returns:
            Parsed LLM analysis with context-aware recommendations
        """
        if not use_modular:
            # Fall back to legacy system
            return self.analyze_market(symbol, signals, news, current_position)
        
        try:
            analyzer = get_modular_analyzer()
            
            # Convert signals to technical_data format
            technical_data = self._signals_to_technical_data(signals)
            
            # DEBUG: Log routing decision
            logger.debug(f"🔍 Routing decision for {symbol}: current_position={current_position}")
            
            # Log overnight context if available
            if overnight_context:
                logger.info(f"🌙 Using overnight analysis context for {symbol}")
                logger.debug(f"   Overnight recommendation: {overnight_context.get('final_recommendation')}")
            
            # Route based on context
            if current_position and current_position.get('qty', 0) > 0:
                # POSITION REVIEW - analyzing existing holding
                logger.info(f"📊 Using modular POSITION_REVIEW for {symbol} (qty={current_position.get('qty')})")
                
                return analyzer.analyze_position(
                    symbol=symbol,
                    technical_data=technical_data,
                    position_data=current_position,
                    portfolio_data=portfolio_summary or {},
                    trigger=trigger,
                    profile=self.trading_profile,
                    news=news,
                    overnight_context=overnight_context
                )
            else:
                # NEW OPPORTUNITY - scanning watchlist
                logger.info(f"🎯 Using modular NEW_OPPORTUNITY for {symbol}")
                
                return analyzer.analyze_new_opportunity(
                    symbol=symbol,
                    technical_data=technical_data,
                    news=news,
                    profile=self.trading_profile,
                    trigger=trigger,
                    overnight_context=overnight_context
                )
                
        except Exception as e:
            logger.error(f"Modular analysis failed, falling back to legacy: {e}")
            return self.analyze_market(symbol, signals, news, current_position)
    
    def audit_portfolio_v2(
        self,
        positions: List[Dict[str, Any]],
        portfolio_summary: Dict[str, Any],
        trigger: str = 'SCHEDULED_CYCLE'
    ) -> Optional[Dict[str, Any]]:
        """
        Audit entire portfolio using modular PORTFOLIO_AUDIT query.
        
        Returns ranked positions with KEEP/HOLD/SELL recommendations.
        
        Args:
            positions: List of positions with technical data and P&L
            portfolio_summary: Portfolio summary (value, buying power, etc.)
            trigger: What triggered this audit
        
        Returns:
            Ranked positions with quality scores
        """
        try:
            analyzer = get_modular_analyzer()
            
            logger.info(f"📋 Using modular PORTFOLIO_AUDIT ({len(positions)} positions)")
            
            return analyzer.audit_portfolio(
                positions_data=positions,
                portfolio_data=portfolio_summary,
                trigger=trigger,
                profile=self.trading_profile
            )
            
        except Exception as e:
            logger.error(f"Portfolio audit failed: {e}")
            return None
    
    def compare_opportunities_v2(
        self,
        symbols: List[str],
        signals_dict: Dict[str, Dict[str, Any]],
        news_dict: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        trigger: str = 'SCHEDULED_CYCLE'
    ) -> Optional[Dict[str, Any]]:
        """
        Compare multiple opportunities using modular COMPARATIVE_ANALYSIS.
        
        Args:
            symbols: List of symbols to compare
            signals_dict: Dict mapping symbol -> signals
            news_dict: Optional dict mapping symbol -> news
            trigger: What triggered this comparison
        
        Returns:
            Comparative ranking with winner/runner-up/avoid
        """
        try:
            analyzer = get_modular_analyzer()
            
            # Convert signals to technical data for each symbol
            technical_data = {
                symbol: self._signals_to_technical_data(signals_dict[symbol])
                for symbol in symbols
                if symbol in signals_dict
            }
            
            logger.info(f"⚖️  Using modular COMPARATIVE_ANALYSIS ({len(symbols)} stocks)")
            
            return analyzer.compare_opportunities(
                symbols=symbols,
                technical_data=technical_data,
                profile=self.trading_profile,
                trigger=trigger,
                news=news_dict
            )
            
        except Exception as e:
            logger.error(f"Comparison analysis failed: {e}")
            return None
    
    def _signals_to_technical_data(self, signals: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert signals format to technical_data format for modular system.
        
        Args:
            signals: Output from get_latest_signals()
        
        Returns:
            Technical data dict for modular components
        """
        technical = {}
        
        # Price data
        if 'price' in signals:
            price = signals['price']
            technical['price'] = price.get('close')
            technical['open'] = price.get('open')
            technical['high'] = price.get('high')
            technical['low'] = price.get('low')
        
        # Trend data
        if 'trend' in signals:
            trend = signals['trend']
            technical['sma20'] = trend.get('sma_20')
            technical['sma50'] = trend.get('sma_50')
            technical['macd'] = trend.get('macd')
            technical['macd_signal'] = trend.get('macd_signal')
            technical['macd_histogram'] = trend.get('macd_histogram')
        
        # Momentum data
        if 'momentum' in signals:
            momentum = signals['momentum']
            technical['rsi'] = momentum.get('rsi')
        
        # Volume data
        if 'volume' in signals:
            volume = signals['volume']
            technical['volume'] = volume.get('volume')
            technical['volume_ratio'] = volume.get('volume_ratio')
            technical['volume_avg'] = volume.get('volume_avg')
        
        # Volatility data
        if 'volatility' in signals:
            volatility = signals['volatility']
            technical['atr'] = volatility.get('atr')
            technical['bb_upper'] = volatility.get('bb_upper')
            technical['bb_middle'] = volatility.get('bb_middle')
            technical['bb_lower'] = volatility.get('bb_lower')
            technical['bb_width'] = volatility.get('bb_width')
        
        return technical
    
    # ========================================================================
    # LEGACY ANALYSIS METHODS (V1 - Backward Compatible)
    # ========================================================================
    
    def analyze_market(
        self,
        symbol: str,
        signals: Dict[str, Any],
        news: Optional[List[Dict[str, Any]]] = None,
        current_position: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Complete pipeline: indicators → text → LLM → structured analysis.
        
        LEGACY METHOD - Use analyze_market_v2() for modular system.
        
        Args:
            symbol: Stock ticker
            signals: Dict from get_latest_signals()
            news: Optional news articles
            current_position: Optional current position info
        
        Returns:
            Parsed LLM analysis, or None if any step fails
        """
        logger.info(f"Analyzing {symbol} market state...")
        
        # Step 1: Convert indicators to text
        indicators_text = self.indicators_to_text(signals)
        logger.debug(f"Indicators text: {indicators_text}")
        
        # Step 2: Create prompt
        prompt = self.create_analysis_prompt(
            symbol=symbol,
            indicators_text=indicators_text,
            news=news,
            current_position=current_position
        )
        
        # Step 3: Query LLM
        response = self.query_llm(prompt, symbol)
        if not response:
            return None
        
        # Step 4: Parse and validate response
        analysis = self.parse_llm_response(response)
        
        if analysis:
            # Add metadata
            analysis['timestamp'] = datetime.now().isoformat()
            analysis['symbol'] = symbol
            analysis['raw_response'] = response  # Keep for debugging
            
            # Week 1-2: Track decision quality metrics
            analysis['quality_score'] = self._score_decision_quality(analysis, signals)
        
        return analysis
    
    def _score_decision_quality(self, analysis: Dict[str, Any], signals: Dict[str, Any]) -> Dict[str, Any]:
        """
        Week 1-2 Optimization: Score decision quality to track improvements.
        
        Metrics:
        - decisiveness: Is action clear and justified? (0-100)
        - specificity: Are price targets and levels included? (0-100)
        - technical_alignment: Does decision match technical signals? (0-100)
        - reasoning_quality: Is reasoning concrete vs generic? (0-100)
        
        Returns dict with individual scores and overall quality score.
        """
        scores = {}
        
        # 1. Decisiveness Score (0-100)
        action = analysis.get('action', '').lower()
        confidence = analysis.get('confidence', 0)
        
        if action in ['buy', 'sell']:
            # Action decisions get bonus for decisiveness
            scores['decisiveness'] = min(100, confidence + 20)
        elif action == 'hold':
            # HOLD is less decisive - penalize based on confidence
            if confidence < 50:
                scores['decisiveness'] = confidence  # Uncertain HOLD is okay
            else:
                scores['decisiveness'] = confidence - 20  # High confidence HOLD suggests over-caution
        else:
            scores['decisiveness'] = 0
        
        # 2. Specificity Score (0-100)
        reasoning = analysis.get('reasoning', '')
        specificity_points = 0
        
        # Check for specific price mentions ($XXX pattern)
        import re
        if re.search(r'\$\d+\.?\d*', reasoning):
            specificity_points += 40
        
        # Check for percentage targets
        if re.search(r'[+-]?\d+\.?\d*%', reasoning):
            specificity_points += 30
        
        # Check for timeframe mentions
        if any(term in reasoning.lower() for term in ['week', 'day', 'month', 'tomorrow', 'short-term', 'near-term']):
            specificity_points += 30
        
        scores['specificity'] = specificity_points
        
        # 3. Technical Alignment Score (0-100)
        sentiment = analysis.get('sentiment', 'neutral').lower()
        
        # Extract trend from nested structure
        trend_data = signals.get('trend', {})
        if isinstance(trend_data, dict):
            # Determine trend from SMA relationship
            sma_20 = trend_data.get('sma_20', 0)
            sma_50 = trend_data.get('sma_50', 0)
            if sma_20 > sma_50:
                trend = 'bullish'
            elif sma_20 < sma_50:
                trend = 'bearish'
            else:
                trend = 'neutral'
        else:
            # Fallback if trend is string (for backwards compatibility)
            trend = str(trend_data).lower() if trend_data else 'neutral'
        
        alignment_score = 0
        if action == 'buy':
            # BUY should align with bullish trend/sentiment
            if sentiment == 'bullish' and trend == 'bullish':
                alignment_score = 100
            elif sentiment == 'bullish' or trend == 'bullish':
                alignment_score = 70
            else:
                alignment_score = 30  # Contrarian play
        elif action == 'sell':
            # SELL should align with bearish trend/sentiment
            if sentiment == 'bearish' and trend == 'bearish':
                alignment_score = 100
            elif sentiment == 'bearish' or trend == 'bearish':
                alignment_score = 70
            else:
                alignment_score = 30  # Contrarian play
        elif action == 'hold':
            # HOLD with neutral or conflicting signals makes sense
            if sentiment == 'neutral' or trend == 'neutral':
                alignment_score = 80
            else:
                alignment_score = 50  # HOLD despite clear signals - could be over-cautious
        
        scores['technical_alignment'] = alignment_score
        
        # 4. Reasoning Quality Score (0-100)
        reasoning_quality = 0
        
        # Penalty for generic phrases
        generic_phrases = ['market volatility', 'uncertain', 'mixed signals', 'wait and see', 'monitor closely']
        generic_count = sum(1 for phrase in generic_phrases if phrase in reasoning.lower())
        reasoning_quality -= (generic_count * 20)
        
        # Bonus for specific terms
        specific_terms = ['resistance', 'support', 'breakout', 'breakdown', 'target', 'stop-loss', 'volume', 'momentum']
        specific_count = sum(1 for term in specific_terms if term in reasoning.lower())
        reasoning_quality += (specific_count * 15)
        
        # Bonus for risk factor specificity
        risk_factors = analysis.get('risk_factors', [])
        if risk_factors:
            # Check if risks follow [SEVERITY]: format
            formatted_risks = sum(1 for risk in risk_factors if any(severity in risk for severity in ['[CRITICAL]', '[HIGH]', '[MEDIUM]']))
            reasoning_quality += (formatted_risks * 10)
        
        scores['reasoning_quality'] = max(0, min(100, reasoning_quality + 50))  # Base score of 50
        
        # Overall Quality Score (weighted average)
        overall = (
            scores['decisiveness'] * 0.35 +
            scores['specificity'] * 0.25 +
            scores['technical_alignment'] * 0.25 +
            scores['reasoning_quality'] * 0.15
        )
        
        scores['overall'] = round(overall, 1)
        
        return scores
    
    def get_fallback_analysis(
        self, 
        signals: Dict[str, Any],
        current_position: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Fallback analysis when LLM fails.
        
        Uses pure numerical rules (no LLM involvement).
        System must continue operating even if LLM is down.
        
        NOW INCLUDES: Position management logic for SELL decisions
        
        Args:
            signals: Dict from get_latest_signals()
            current_position: Optional current position info
        
        Returns:
            Simple analysis based on indicators
        """
        logger.warning("Using fallback analysis (LLM unavailable)")
        
        # Extract key indicators
        momentum = signals.get('momentum', {})
        trend = signals.get('trend', {})
        price = signals.get('price', {})
        
        rsi = momentum.get('rsi', 50)
        macd = trend.get('macd', 0)
        macd_signal = trend.get('macd_signal', 0)
        sma_20 = trend.get('sma_20', 0)
        sma_50 = trend.get('sma_50', 0)
        current_price = price.get('close', 0)
        
        # POSITION MANAGEMENT LOGIC
        if current_position:
            shares = current_position.get('qty', 0)
            avg_price = current_position.get('avg_entry_price', 0)
            
            if shares > 0 and avg_price > 0 and current_price > 0:
                pnl_pct = ((current_price - avg_price) / avg_price) * 100
                
                # SELL RULES (for existing positions)
                # 1. Stop loss: Down 5% or more
                if pnl_pct <= -5:
                    return {
                        'sentiment': 'bearish',
                        'confidence': 75,
                        'action': 'sell',
                        'reasoning': f'Stop loss triggered: Position down {pnl_pct:.1f}% - Cut losses',
                        'risk_factors': ['Stop loss', 'Capital preservation'],
                        'timestamp': datetime.now().isoformat(),
                        'fallback_mode': True
                    }
                
                # 2. Take profits: Up 10% or more AND showing weakness
                if pnl_pct >= 10:
                    if rsi > 70:  # Overbought
                        return {
                            'sentiment': 'profit_taking',
                            'confidence': 70,
                            'action': 'sell',
                            'reasoning': f'Take profits: Up {pnl_pct:.1f}% with RSI overbought ({rsi:.0f}) - Lock in gains',
                            'risk_factors': ['Overbought conditions', 'Profit protection'],
                            'timestamp': datetime.now().isoformat(),
                            'fallback_mode': True
                        }
                    elif macd < macd_signal:  # MACD turned bearish
                        return {
                            'sentiment': 'profit_taking',
                            'confidence': 65,
                            'action': 'sell',
                            'reasoning': f'Take profits: Up {pnl_pct:.1f}% with MACD weakening - Secure gains',
                            'risk_factors': ['Momentum weakening', 'Profit protection'],
                            'timestamp': datetime.now().isoformat(),
                            'fallback_mode': True
                        }
                
                # 3. Technical breakdown: Bearish signals on existing position
                bearish_count = 0
                if rsi < 40:  # Weak momentum
                    bearish_count += 1
                if macd < macd_signal:  # Bearish crossover
                    bearish_count += 1
                if current_price < sma_20 < sma_50:  # Below moving averages
                    bearish_count += 1
                
                if bearish_count >= 2:
                    return {
                        'sentiment': 'bearish',
                        'confidence': 60,
                        'action': 'sell',
                        'reasoning': f'Technical breakdown: {bearish_count}/3 bearish signals - Exit position',
                        'risk_factors': ['Weak technicals', 'Trend deterioration'],
                        'timestamp': datetime.now().isoformat(),
                        'fallback_mode': True
                    }
        
        # BUY/HOLD RULES (for new positions or when holding is OK)
        bullish_signals = 0
        bearish_signals = 0
        
        # RSI signals
        if rsi < 30:  # Oversold
            bullish_signals += 1
        elif rsi > 70:  # Overbought
            bearish_signals += 1
        
        # MACD signals
        if macd > macd_signal:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        # Trend signals
        if sma_20 > sma_50:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        # Determine sentiment
        if bullish_signals > bearish_signals:
            sentiment = "bullish"
            action = "buy"
            confidence = 50 + (bullish_signals * 5)
        elif bearish_signals > bullish_signals:
            sentiment = "bearish"
            action = "sell" if current_position else "hold"
            confidence = 50 + (bearish_signals * 5)
        else:
            sentiment = "neutral"
            action = "hold"
            confidence = 45
        
        return {
            'sentiment': sentiment,
            'confidence': min(confidence, 75),  # Cap at 75% for fallback
            'action': action,
            'reasoning': f'Fallback: {bullish_signals}B/{bearish_signals}Be signals (RSI:{rsi:.0f}, MACD trend, SMA position)',
            'risk_factors': ['LLM unavailable', 'Using simplified rules'],
            'timestamp': datetime.now().isoformat(),
            'fallback_mode': True
        }
    
    def get_current_profile(self) -> Dict[str, Any]:
        """Get current trading profile information"""
        return {
            'profile': self.trading_profile,
            'name': self.profile_config['name'],
            'description': self.profile_config['description'],
            'min_confidence_buy': self.profile_config['min_confidence_buy'],
            'min_confidence_sell': self.profile_config['min_confidence_sell'],
            'risk_emphasis': self.profile_config['risk_emphasis']
        }
    
    def set_profile(self, profile_name: str) -> bool:
        """
        Change trading profile at runtime
        
        Args:
            profile_name: One of 'conservative', 'moderate', 'aggressive', 'maximum'
        
        Returns:
            True if successful, False if invalid profile
        """
        if profile_name not in self.TRADING_PROFILES:
            logger.error(f"Invalid profile: {profile_name}")
            return False
        
        self.trading_profile = profile_name
        self.profile_config = self.TRADING_PROFILES[profile_name]
        logger.info(f"Trading profile changed to: {self.profile_config['name']}")
        return True
    
    @classmethod
    def get_available_profiles(cls) -> Dict[str, Dict[str, Any]]:
        """Get all available trading profiles"""
        return {
            name: {
                'name': config['name'],
                'description': config['description'],
                'min_confidence_buy': config['min_confidence_buy'],
                'min_confidence_sell': config['min_confidence_sell'],
                'risk_emphasis': config['risk_emphasis']
            }
            for name, config in cls.TRADING_PROFILES.items()
        }
    
    def analyze_news_narrative(self, timeline: Any) -> Optional[Dict[str, Any]]:
        """
        Synthesize complete news narrative from timeline using LLM.
        
        This is Phase 2 of the News Timeline system. The LLM analyzes
        the complete sequence of news events to understand:
        1. Initial news vs final consensus
        2. Contradictions and how they resolved
        3. Net sentiment and confidence
        4. Trading recommendation with reasoning
        
        Args:
            timeline: NewsTimeline object with accumulated articles
            
        Returns:
            Dict with narrative synthesis or None if failed
        """
        if not timeline or not timeline.events:
            logger.warning("No news events to analyze")
            return None
        
        try:
            # Build chronological narrative prompt
            prompt = self._build_narrative_prompt(timeline)
            
            # Get LLM analysis
            logger.info(f"🤖 Analyzing news narrative for {timeline.symbol} ({len(timeline.events)} articles)")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a professional financial news analyst. Your job is to analyze "
                            "the complete timeline of news for a stock and synthesize the narrative. "
                            "Focus on understanding how the story EVOLVED, not just individual headlines. "
                            "Detect contradictions and explain how they resolved. "
                            "Respond ONLY with valid JSON in the specified format."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent analysis
                max_tokens=1000
            )
            
            # Parse response
            content = response.choices[0].message.content.strip()
            
            # Log conversation
            self._log_conversation(
                prompt=prompt,
                response=content,
                symbol=getattr(timeline, 'symbol', 'unknown')
            )
            
            # Parse JSON - handle markdown code blocks
            try:
                # Remove markdown code blocks if present
                if content.startswith('```'):
                    # Remove ```json or ``` at start
                    lines = content.split('\n')
                    if lines[0].startswith('```'):
                        lines = lines[1:]
                    # Remove ``` at end
                    if lines and lines[-1].startswith('```'):
                        lines = lines[:-1]
                    content = '\n'.join(lines).strip()
                
                synthesis = json.loads(content)
                
                # Validate required fields
                required = ['narrative', 'net_sentiment', 'confidence', 'recommendation', 'reasoning']
                if not all(field in synthesis for field in required):
                    logger.error(f"Missing required fields in synthesis: {synthesis.keys()}")
                    return None
                
                # Add metadata
                synthesis['analyzed_at'] = datetime.now().isoformat()
                synthesis['article_count'] = len(timeline.events)
                synthesis['symbol'] = getattr(timeline, 'symbol', 'unknown')
                
                logger.info(f"✅ Narrative synthesis complete:")
                logger.info(f"   Sentiment: {synthesis['net_sentiment']}")
                logger.info(f"   Confidence: {synthesis['confidence']}")
                logger.info(f"   Recommendation: {synthesis['recommendation']}")
                
                return synthesis
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.debug(f"Response was: {content}")
                return None
                
        except Exception as e:
            logger.error(f"Error analyzing news narrative: {e}")
            return None
    
    def _build_narrative_prompt(self, timeline: Any) -> str:
        """
        Build prompt for narrative synthesis.
        
        Args:
            timeline: NewsTimeline with events
            
        Returns:
            Structured prompt for LLM
        """
        # Sort events chronologically
        events = sorted(timeline.events, key=lambda x: x.timestamp)
        
        # Build timeline text
        timeline_text = f"SYMBOL: {timeline.symbol}\n"
        timeline_text += f"DATE: {timeline.date}\n"
        timeline_text += f"TOTAL ARTICLES: {len(events)}\n\n"
        timeline_text += "CHRONOLOGICAL TIMELINE:\n"
        timeline_text += "=" * 80 + "\n\n"
        
        for i, article in enumerate(events, 1):
            time_str = article.timestamp.strftime('%I:%M %p ET')
            timeline_text += f"{i}. [{time_str}] {article.headline}\n"
            if article.summary:
                # Truncate summary to avoid token overflow
                summary = article.summary[:200] + "..." if len(article.summary) > 200 else article.summary
                timeline_text += f"   Summary: {summary}\n"
            timeline_text += f"   Source: {article.source}\n\n"
        
        # Build analysis prompt
        prompt = f"""{timeline_text}

TASK: Analyze the EVOLUTION of this news story throughout the day/overnight.

QUESTIONS TO ANSWER:
1. What was the INITIAL news that came out first?
2. How did the narrative DEVELOP over time?
3. Were there any CONTRADICTIONS? (e.g., bad news followed by good news)
4. If contradictions exist, which information is more RECENT and CREDIBLE?
5. What is the FINAL CONSENSUS at the end of the timeline?
6. What is the NET IMPACT on the stock?

RESPONSE FORMAT (JSON only):
{{
    "narrative": "One paragraph summary of how the story evolved",
    "initial_news": "What came out first",
    "key_developments": ["Major turning points in the story"],
    "contradictions": ["Any conflicting information, or empty list"],
    "net_sentiment": "positive|cautiously_positive|neutral|cautiously_negative|negative",
    "confidence": 0.0-1.0,
    "key_themes": ["earnings", "regulatory", "product", "scandal", "market", etc],
    "recommendation": "BUY|SELL|HOLD|WAIT_FOR_CLARITY",
    "reasoning": "Why this recommendation based on news narrative",
    "material_impact": "high|medium|low"
}}

IMPORTANT GUIDELINES:
- Focus on NARRATIVE EVOLUTION, not just individual headlines
- More recent news typically supersedes earlier news
- Reuters/Bloomberg are more credible than social media
- Contradictions reduce confidence
- If story is unclear or contradictory, recommend WAIT_FOR_CLARITY
- Material impact should reflect how much this news matters for the stock

Respond with ONLY the JSON object, no other text."""
        
        return prompt


# Convenience function
def create_llm_bridge() -> LLMBridge:
    """Create and return an LLM bridge instance"""
    return LLMBridge()


if __name__ == "__main__":
    # Test the LLM bridge
    from wawatrader.alpaca_client import get_client
    from wawatrader.indicators import get_latest_signals, analyze_dataframe
    from datetime import datetime, timedelta
    
    print("\n" + "="*60)
    print("Testing LLM Bridge...")
    print("="*60)
    
    # Get market data
    client = get_client()
    symbol = "AAPL"
    
    # Get historical data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    df = client.get_bars(symbol, start_date, end_date)
    print(f"\nRetrieved {len(df)} bars for {symbol}")
    
    # Calculate indicators
    df_with_indicators = analyze_dataframe(df)
    signals = get_latest_signals(df_with_indicators)
    
    # Get news
    news = client.get_news(symbol, limit=3)
    
    # Create bridge and analyze
    bridge = create_llm_bridge()
    
    # Test 1: Indicators to text
    print("\n" + "-"*60)
    print("Test 1: Indicators → Text")
    print("-"*60)
    indicators_text = bridge.indicators_to_text(signals)
    print(indicators_text)
    
    # Test 2: Full analysis
    print("\n" + "-"*60)
    print("Test 2: Full Market Analysis")
    print("-"*60)
    analysis = bridge.analyze_market(
        symbol=symbol,
        signals=signals,
        news=news
    )
    
    if analysis:
        print(f"\n✅ LLM Analysis:")
        print(f"   Sentiment: {analysis['sentiment']}")
        print(f"   Confidence: {analysis['confidence']}%")
        print(f"   Action: {analysis['action']}")
        print(f"   Reasoning: {analysis['reasoning']}")
        if 'risk_factors' in analysis:
            print(f"   Risk Factors: {', '.join(analysis['risk_factors'])}")
    else:
        print("\n❌ LLM analysis failed, testing fallback...")
        fallback = bridge.get_fallback_analysis(signals)
        print(f"\n✅ Fallback Analysis:")
        print(f"   Sentiment: {fallback['sentiment']}")
        print(f"   Action: {fallback['action']}")
        print(f"   Reasoning: {fallback['reasoning']}")
    
    print("\n" + "="*60)
    print("✅ LLM Bridge test complete!")
    print("="*60)
    
