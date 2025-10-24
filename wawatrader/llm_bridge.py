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
                "You are a high-octane trader seeking maximum returns. You identify opportunities aggressively "
                "and act without hesitation when signals appear. \n\n"
                "KEY PRINCIPLES:\n"
                "- Recommend BUY on ANY bullish technical signal, even with minor concerns (≥50% confidence)\n"
                "- Recommend SELL immediately on bearish signals or negative catalysts (≥45% confidence)\n"
                "- RARELY recommend HOLD - prefer decisive action in both directions\n"
                "- Accept substantial risk and volatility for maximum gain potential\n"
                "- Set aggressive price targets and wider stop-losses for big moves\n\n"
                "Respond ONLY with valid JSON. Be bold, decisive, and action-focused."
            ),
            'min_confidence_buy': 50,
            'min_confidence_sell': 45,
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
                    "💼 POSITION MANAGEMENT CONTEXT",
                    "=" * 60,
                    f"Current Position: {shares} shares @ ${avg_price:.2f} avg entry",
                    f"Current P&L: {pnl_pct:+.2f}%",
                    f"Status: {status}",
                    "",
                    "Consider: Should you HOLD, ADD to position, or EXIT?",
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
    
    def analyze_market(
        self,
        symbol: str,
        signals: Dict[str, Any],
        news: Optional[List[Dict[str, Any]]] = None,
        current_position: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Complete pipeline: indicators → text → LLM → structured analysis.
        
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
    
    def get_fallback_analysis(self, signals: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback analysis when LLM fails.
        
        Uses pure numerical rules (no LLM involvement).
        System must continue operating even if LLM is down.
        
        Args:
            signals: Dict from get_latest_signals()
        
        Returns:
            Simple analysis based on indicators
        """
        logger.warning("Using fallback analysis (LLM unavailable)")
        
        # Extract key indicators
        momentum = signals.get('momentum', {})
        trend = signals.get('trend', {})
        
        rsi = momentum.get('rsi', 50)
        macd = trend.get('macd', 0)
        macd_signal = trend.get('macd_signal', 0)
        sma_20 = trend.get('sma_20', 0)
        sma_50 = trend.get('sma_50', 0)
        
        # Simple rules
        bullish_signals = 0
        bearish_signals = 0
        
        if rsi < 30:
            bullish_signals += 1
        elif rsi > 70:
            bearish_signals += 1
        
        if macd > macd_signal:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        if sma_20 > sma_50:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        # Determine sentiment
        if bullish_signals > bearish_signals:
            sentiment = "bullish"
            action = "buy"
        elif bearish_signals > bullish_signals:
            sentiment = "bearish"
            action = "sell"
        else:
            sentiment = "neutral"
            action = "hold"
        
        return {
            'sentiment': sentiment,
            'confidence': 50,  # Low confidence (fallback mode)
            'action': action,
            'reasoning': 'Fallback analysis based on RSI, MACD, and SMA trend',
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
