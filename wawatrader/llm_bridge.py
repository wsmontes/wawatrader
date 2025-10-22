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
    
    def __init__(self):
        """Initialize LLM connection"""
        
        self.client = OpenAI(
            base_url=settings.lm_studio.base_url,
            api_key="not-needed"  # LM Studio doesn't require API key
        )
        
        self.model = settings.lm_studio.model
        self.temperature = settings.lm_studio.temperature
        self.max_tokens = settings.lm_studio.max_tokens
        
        # Initialize conversation logging
        self.conversation_log = settings.project_root / "logs" / "llm_conversations.jsonl"
        self.conversation_log.parent.mkdir(exist_ok=True)
        
        logger.info(f"LLM Bridge initialized (model: {self.model})")
    
    def indicators_to_text(self, signals: Dict[str, Any]) -> str:
        """
        Convert numerical indicators to human-readable text.
        
        This is what the LLM "sees" - contextual interpretation of numbers.
        
        Args:
            signals: Dict from get_latest_signals() with price, trend, momentum, etc.
        
        Returns:
            Formatted text description of market state
        """
        if not signals:
            return "No market data available."
        
        # Extract components
        price = signals.get('price', {})
        trend = signals.get('trend', {})
        momentum = signals.get('momentum', {})
        volatility = signals.get('volatility', {})
        volume = signals.get('volume', {})
        
        # Build text description
        parts = []
        
        # Price action
        if price:
            close = price.get('close')
            if close:
                parts.append(f"Current price: ${close:.2f}")
        
        # Trend indicators
        if trend:
            sma_20 = trend.get('sma_20')
            sma_50 = trend.get('sma_50')
            if sma_20 and sma_50:
                trend_desc = "bullish uptrend" if sma_20 > sma_50 else "bearish downtrend"
                parts.append(f"Trend: {trend_desc} (SMA20: ${sma_20:.2f}, SMA50: ${sma_50:.2f})")
            
            macd = trend.get('macd')
            macd_signal = trend.get('macd_signal')
            if macd is not None and macd_signal is not None:
                macd_position = "above signal (bullish)" if macd > macd_signal else "below signal (bearish)"
                parts.append(f"MACD: {macd:.2f} {macd_position}")
        
        # Momentum
        if momentum:
            rsi = momentum.get('rsi')
            if rsi:
                if rsi > 70:
                    rsi_desc = f"{rsi:.1f} (OVERBOUGHT - potentially due for pullback)"
                elif rsi < 30:
                    rsi_desc = f"{rsi:.1f} (OVERSOLD - potentially due for bounce)"
                else:
                    rsi_desc = f"{rsi:.1f} (neutral zone)"
                parts.append(f"RSI: {rsi_desc}")
        
        # Volatility
        if volatility:
            atr = volatility.get('atr')
            bb_width = volatility.get('bb_width')
            if atr:
                parts.append(f"ATR: ${atr:.2f} (average true range)")
            if bb_width:
                width_desc = "high volatility" if bb_width > 10 else "low volatility"
                parts.append(f"Bollinger Bands: {width_desc} (width: {bb_width:.2f})")
        
        # Volume
        if volume:
            volume_ratio = volume.get('volume_ratio')
            if volume_ratio:
                if volume_ratio > 1.5:
                    vol_desc = f"{volume_ratio:.2f}x average (HIGH volume - strong conviction)"
                elif volume_ratio < 0.5:
                    vol_desc = f"{volume_ratio:.2f}x average (LOW volume - weak conviction)"
                else:
                    vol_desc = f"{volume_ratio:.2f}x average (normal)"
                parts.append(f"Volume: {vol_desc}")
        
        return ". ".join(parts) + "."
    
    def create_analysis_prompt(
        self,
        symbol: str,
        indicators_text: str,
        news: Optional[List[Dict[str, Any]]] = None,
        current_position: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a prompt for the LLM to analyze the market state.
        
        Args:
            symbol: Stock ticker (e.g., "AAPL")
            indicators_text: Human-readable indicator description
            news: Optional list of recent news articles
            current_position: Optional current position info (shares, avg_price, etc.)
        
        Returns:
            Formatted prompt for LLM
        """
        prompt_parts = [
            f"You are a trading analyst for {symbol}.",
            "",
            "TECHNICAL INDICATORS:",
            indicators_text,
        ]
        
        # Add news context if available
        if news:
            prompt_parts.append("")
            prompt_parts.append("RECENT NEWS:")
            for article in news[:3]:  # Max 3 articles to avoid token overflow
                headline = article.get('headline', '')
                summary = article.get('summary', '')
                if headline:
                    prompt_parts.append(f"- {headline}")
                    if summary:
                        # Truncate summary to 100 chars
                        summary_short = summary[:100] + "..." if len(summary) > 100 else summary
                        prompt_parts.append(f"  {summary_short}")
        
        # Add position context if exists
        if current_position:
            shares = current_position.get('qty', 0)
            avg_price = current_position.get('avg_entry_price', 0)
            current_price = current_position.get('current_price', 0)
            
            if shares and avg_price and current_price:
                pnl_pct = ((current_price - avg_price) / avg_price) * 100
                prompt_parts.append("")
                prompt_parts.append("CURRENT POSITION:")
                prompt_parts.append(f"- Holding {shares} shares at ${avg_price:.2f} avg entry")
                prompt_parts.append(f"- Current P&L: {pnl_pct:+.2f}%")
        
        prompt_parts.extend([
            "",
            "Based on this information, provide your analysis in JSON format:",
            "{",
            '  "sentiment": "bullish" | "bearish" | "neutral",',
            '  "confidence": 0-100 (how confident are you?),',
            '  "action": "buy" | "sell" | "hold",',
            '  "reasoning": "brief explanation of your recommendation",',
            '  "risk_factors": ["list", "of", "key", "risks"]',
            "}",
            "",
            "IMPORTANT: Only respond with valid JSON. No other text."
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
                        "content": "You are a professional trading analyst. "
                                   "Provide concise, data-driven analysis in JSON format only."
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
        
        return analysis
    
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
