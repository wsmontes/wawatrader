"""
LLM Bridge Layer V2 - Using Official LM Studio SDK

Enhanced version using the official lmstudio-python SDK for better integration:
- Automatic model loading if not already loaded
- Proper model checking and health monitoring
- Native LM Studio error handling
- Cleaner API with SDK features

Install: pip install lmstudio

CRITICAL: Never trust LLM numerical outputs directly. Always validate against
hard numerical thresholds and risk rules.
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

try:
    import lmstudio as lms
    LMS_AVAILABLE = True
except ImportError:
    LMS_AVAILABLE = False
    logger.warning("lmstudio package not installed. Install with: pip install lmstudio")
    # Fallback to OpenAI client for backward compatibility
    from openai import OpenAI

from config.settings import settings


class LLMBridgeV2:
    """
    Enhanced bridge between numerical technical analysis and LLM using official SDK.
    
    Architecture:
    1. Numerical Data (from indicators.py) → Text Description
    2. Text Description + Market Context → LLM Prompt
    3. LLM Response → Structured JSON
    4. JSON → Validation → Trading Signal
    
    The LLM provides sentiment/interpretation, NOT numerical decisions.
    """
    
    # Trading profile definitions
    TRADING_PROFILES = {
        'conservative': {
            'name': 'Conservative',
            'description': 'Risk-averse with capital preservation focus',
            'system_prompt': (
                "You are a conservative trading analyst focused on capital preservation. "
                "Prioritize safety over gains. Only recommend BUY when indicators show "
                "strong confirmation and low risk. Prefer HOLD over risky positions. "
                "Provide data-driven analysis in JSON format only."
            ),
            'min_confidence_buy': 75,
            'min_confidence_sell': 70,
            'risk_emphasis': 'high'
        },
        'moderate': {
            'name': 'Moderate',
            'description': 'Balanced approach between risk and reward',
            'system_prompt': (
                "You are a balanced trading analyst seeking reasonable risk-adjusted returns. "
                "Recommend trades when technical indicators show good probability. "
                "Consider both opportunities and risks equally. "
                "Provide concise, data-driven analysis in JSON format only."
            ),
            'min_confidence_buy': 65,
            'min_confidence_sell': 60,
            'risk_emphasis': 'medium'
        },
        'aggressive': {
            'name': 'Aggressive',
            'description': 'Active trading seeking high returns',
            'system_prompt': (
                "You are an aggressive day trader focused on capturing market opportunities. "
                "Recommend trades when technical indicators show potential. "
                "Favor action over holding when clear signals appear. "
                "Accept higher risk for higher reward potential. "
                "Provide decisive, action-oriented analysis in JSON format only."
            ),
            'min_confidence_buy': 55,
            'min_confidence_sell': 50,
            'risk_emphasis': 'low'
        },
        'maximum': {
            'name': 'Maximum Revenue and Risk',
            'description': 'Maximum returns with corresponding risk acceptance',
            'system_prompt': (
                "You are a high-risk, high-reward trader seeking maximum returns. "
                "Identify and act on any reasonable opportunity aggressively. "
                "Recommend BUY on bullish signals and SELL on bearish signals without hesitation. "
                "Minimize HOLD recommendations - prefer decisive action. "
                "Accept substantial risk for potential maximum gains. "
                "Provide bold, decisive analysis in JSON format only."
            ),
            'min_confidence_buy': 50,
            'min_confidence_sell': 45,
            'risk_emphasis': 'minimal'
        }
    }
    
    def __init__(self):
        """Initialize LLM connection with official SDK"""
        
        if not LMS_AVAILABLE:
            logger.warning("Falling back to OpenAI-compatible client")
            self.client = OpenAI(
                base_url=settings.lm_studio.base_url,
                api_key="not-needed"
            )
            self.model = None
            self.use_legacy_client = True
        else:
            # Use official LM Studio SDK
            self.client = lms.get_default_client()
            self.model = None
            self.use_legacy_client = False
            logger.info("Using official LM Studio SDK")
        
        self.model_name = settings.lm_studio.model
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
        
        logger.info(f"LLM Bridge V2 initialized (model: {self.model_name}, profile: {self.profile_config['name']})")
    
    def _ensure_model_loaded(self) -> bool:
        """
        Ensure the model is loaded in LM Studio.
        If not loaded, automatically load it.
        
        Returns:
            True if model is ready, False otherwise
        """
        if self.use_legacy_client:
            # Legacy client doesn't support model management
            return True
        
        try:
            # Check if model is already loaded
            loaded_models = lms.list_loaded_models("llm")
            
            for loaded_model in loaded_models:
                if self.model_name in loaded_model.identifier:
                    logger.debug(f"Model {self.model_name} already loaded")
                    self.model = loaded_model
                    return True
            
            # Model not loaded - load it automatically
            logger.info(f"Loading model {self.model_name}...")
            self.model = lms.llm(self.model_name)
            logger.info(f"✅ Model {self.model_name} loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to ensure model is loaded: {e}")
            return False
    
    def check_health(self) -> Dict[str, Any]:
        """
        Check health of LLM connection and model availability.
        
        Returns:
            Dict with health status information
        """
        health = {
            'available': False,
            'model_loaded': False,
            'model_name': self.model_name,
            'using_sdk': not self.use_legacy_client,
            'error': None
        }
        
        try:
            if self.use_legacy_client:
                # Simple ping test for legacy client
                health['available'] = True
                health['model_loaded'] = True  # Assume loaded if server responds
            else:
                # Check with SDK
                loaded_models = lms.list_loaded_models("llm")
                health['available'] = True
                health['loaded_models'] = [m.identifier for m in loaded_models]
                health['model_loaded'] = any(self.model_name in m.identifier for m in loaded_models)
            
        except Exception as e:
            health['error'] = str(e)
            logger.error(f"Health check failed: {e}")
        
        return health
    
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
            macd = trend.get('macd')
            macd_signal = trend.get('macd_signal')
            
            if sma_20 and sma_50:
                if sma_20 > sma_50:
                    parts.append(f"Trend: Bullish (SMA20 ${sma_20:.2f} > SMA50 ${sma_50:.2f})")
                else:
                    parts.append(f"Trend: Bearish (SMA20 ${sma_20:.2f} < SMA50 ${sma_50:.2f})")
            
            if macd and macd_signal:
                if macd > macd_signal:
                    parts.append(f"MACD: Bullish crossover ({macd:.2f} > {macd_signal:.2f})")
                else:
                    parts.append(f"MACD: Bearish crossover ({macd:.2f} < {macd_signal:.2f})")
        
        # Momentum indicators
        if momentum:
            rsi = momentum.get('rsi')
            if rsi:
                if rsi < 30:
                    parts.append(f"RSI: Oversold ({rsi:.1f}) - potential bounce")
                elif rsi > 70:
                    parts.append(f"RSI: Overbought ({rsi:.1f}) - potential reversal")
                else:
                    parts.append(f"RSI: Neutral zone ({rsi:.1f})")
        
        # Volatility
        if volatility:
            bb_position = volatility.get('bb_position')
            if bb_position is not None:
                if bb_position < 0.2:
                    parts.append("Bollinger: Near lower band (oversold)")
                elif bb_position > 0.8:
                    parts.append("Bollinger: Near upper band (overbought)")
                else:
                    parts.append(f"Bollinger: Mid-range ({bb_position:.2f})")
        
        # Volume
        if volume:
            volume_ratio = volume.get('volume_ratio')
            if volume_ratio:
                if volume_ratio > 1.5:
                    parts.append(f"Volume: High ({volume_ratio:.1f}x average)")
                elif volume_ratio < 0.5:
                    parts.append(f"Volume: Low ({volume_ratio:.1f}x average)")
                else:
                    parts.append(f"Volume: Normal ({volume_ratio:.1f}x average)")
        
        return "\n".join(parts) if parts else "Limited market data available."
    
    def create_analysis_prompt(
        self,
        symbol: str,
        indicators_text: str,
        news: Optional[List[Dict[str, Any]]] = None,
        current_position: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create complete prompt for LLM analysis.
        
        Args:
            symbol: Stock ticker
            indicators_text: Pre-formatted indicators text
            news: Optional news articles
            current_position: Optional current position info
        
        Returns:
            Complete prompt string
        """
        prompt_parts = [
            f"MARKET ANALYSIS REQUEST for {symbol}",
            "",
            "TECHNICAL INDICATORS:",
            indicators_text,
            ""
        ]
        
        # Add news if available
        if news:
            prompt_parts.append("RECENT NEWS:")
            for article in news[:3]:  # Top 3 articles
                headline = article.get('headline', '')
                summary = article.get('summary', '')
                prompt_parts.append(f"• {headline}")
                if summary:
                    prompt_parts.append(f"  {summary[:200]}...")
            prompt_parts.append("")
        
        # Add position context
        if current_position:
            shares = current_position.get('qty', 0)
            avg_price = current_position.get('avg_entry_price', 0)
            prompt_parts.append(f"CURRENT POSITION: {shares} shares @ ${avg_price:.2f}")
            prompt_parts.append("")
        
        # Add profile-specific guidance
        risk_emphasis = self.profile_config['risk_emphasis']
        if risk_emphasis == 'high':
            risk_note = "Emphasize risk factors heavily. Only recommend action with strong confirmation."
        elif risk_emphasis == 'medium':
            risk_note = "Balance opportunity and risk equally in your analysis."
        elif risk_emphasis == 'low':
            risk_note = "Focus on opportunities. Mention risks but don't let them prevent action."
        else:  # minimal
            risk_note = "Prioritize opportunities for maximum gains. Accept associated risks."
        
        prompt_parts.extend([
            "",
            f"TRADING STYLE: {self.profile_config['description']}",
            f"RISK APPROACH: {risk_note}",
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
        Send prompt to LLM and get response using official SDK.
        
        Args:
            prompt: The prompt to send
            symbol: Optional symbol for logging
        
        Returns:
            LLM response text, or None if error
        """
        try:
            logger.debug(f"Querying LLM... (prompt length: {len(prompt)} chars)")
            
            # Ensure model is loaded
            if not self.use_legacy_client:
                if not self._ensure_model_loaded():
                    logger.error("Failed to load model")
                    return None
            
            if self.use_legacy_client:
                # Legacy OpenAI-compatible client
                response = self.client.chat.completions.create(
                    model=self.model_name,
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
                content = response.choices[0].message.content
            else:
                # Official LM Studio SDK
                chat = lms.Chat(self.profile_config['system_prompt'])
                chat.add_user_message(prompt)
                
                result = self.model.respond(
                    chat,
                    config={
                        "temperature": self.temperature,
                        "maxTokens": self.max_tokens if self.max_tokens > 0 else None
                    }
                )
                content = result.content
                
                # Log prediction stats
                logger.debug(f"Model: {result.model_info.display_name}")
                logger.debug(f"Tokens: {result.stats.predicted_tokens_count}")
                logger.debug(f"Time to first token: {result.stats.time_to_first_token_sec:.2f}s")
            
            logger.debug(f"LLM response: {content[:100]}...")
            
            # Log the conversation
            self._log_conversation(prompt, content, symbol)
            
            return content
                
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
            conversation_entry = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol or 'unknown',
                'prompt': prompt,
                'response': response,
                'prompt_length': len(prompt),
                'response_length': len(response),
                'using_sdk': not self.use_legacy_client
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
def create_llm_bridge_v2() -> LLMBridgeV2:
    """Create and return an enhanced LLM bridge instance"""
    return LLMBridgeV2()


if __name__ == "__main__":
    # Test the enhanced LLM bridge
    print("\n" + "="*60)
    print("Testing Enhanced LLM Bridge V2...")
    print("="*60)
    
    # Initialize bridge
    bridge = LLMBridgeV2()
    
    # Health check
    print("\n1️⃣ Checking LLM health...")
    health = bridge.check_health()
    print(f"   Available: {health['available']}")
    print(f"   Model loaded: {health['model_loaded']}")
    print(f"   Using SDK: {health['using_sdk']}")
    if 'loaded_models' in health:
        print(f"   Loaded models: {health['loaded_models']}")
    
    # Test with sample data
    print("\n2️⃣ Testing market analysis...")
    sample_signals = {
        'price': {'close': 150.25},
        'trend': {
            'sma_20': 149.80,
            'sma_50': 148.50,
            'macd': 1.25,
            'macd_signal': 0.85
        },
        'momentum': {'rsi': 65.4},
        'volatility': {'bb_position': 0.7},
        'volume': {'volume_ratio': 1.3}
    }
    
    analysis = bridge.analyze_market('AAPL', sample_signals)
    
    if analysis:
        print(f"   ✅ Analysis successful!")
        print(f"   Sentiment: {analysis['sentiment']}")
        print(f"   Confidence: {analysis['confidence']}%")
        print(f"   Action: {analysis['action']}")
        print(f"   Reasoning: {analysis['reasoning']}")
    else:
        print("   ❌ Analysis failed")
    
    print("\n" + "="*60)
