"""
Iterative LLM Analyst

Enables multi-turn conversations where the LLM can:
1. Ask for specific data (volume patterns, institutional flows, news, etc.)
2. Request deeper technical analysis
3. Compare with sector peers
4. Dig into specific time periods
5. Build comprehensive analysis through iteration

This creates a research loop where the LLM acts as a curious analyst
exploring data until it has enough confidence to make recommendations.
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger

class IterativeAnalyst:
    """
    Manages iterative analysis sessions where LLM can request more data.
    
    Architecture:
    1. Initial prompt with basic data
    2. LLM responds with either:
       - Analysis + Questions for more data
       - Final recommendation when satisfied
    3. System fetches requested data
    4. Loop continues until LLM is satisfied or max iterations reached
    """
    
    def __init__(self, alpaca_client, llm_bridge, max_iterations: int = 5):
        """
        Initialize iterative analyst
        
        Args:
            alpaca_client: Alpaca API client for data fetching
            llm_bridge: LLM bridge for AI communication
            max_iterations: Maximum number of back-and-forth exchanges
        """
        self.alpaca = alpaca_client
        self.llm = llm_bridge
        self.max_iterations = max_iterations
        
        # Available data sources the LLM can request
        self.available_data = {
            'volume_profile': self._get_volume_profile,
            'intraday_patterns': self._get_intraday_patterns,
            'sector_comparison': self._get_sector_comparison,
            'historical_volatility': self._get_historical_volatility,
            'support_resistance_zones': self._get_support_resistance,
            'gap_analysis': self._get_gap_analysis,
            'momentum_indicators': self._get_momentum_indicators,
            'earnings_proximity': self._get_earnings_info,
            'institutional_holdings': self._get_institutional_data,
            'options_flow': self._get_options_data
        }
    
    def analyze_with_iterations(self, symbol: str, initial_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run iterative analysis session
        
        Args:
            symbol: Stock symbol to analyze
            initial_context: Initial technical data (RSI, MACD, etc.)
            
        Returns:
            Final analysis with conversation history
        """
        logger.info(f"🔄 Starting iterative analysis for {symbol}")
        
        conversation_history = []
        iteration = 0
        final_recommendation = None
        
        # Initial prompt
        current_prompt = self._build_initial_prompt(symbol, initial_context)
        conversation_history.append({
            'role': 'system',
            'content': 'Initial data provided',
            'data': initial_context
        })
        
        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"   💭 Iteration {iteration}/{self.max_iterations}")
            
            # Get LLM response
            response = self.llm.query_llm(current_prompt, symbol=symbol)
            
            if not response:
                logger.error(f"   ❌ No response from LLM")
                break
            
            # Parse response
            parsed = self._parse_llm_response(response)
            conversation_history.append({
                'role': 'assistant',
                'iteration': iteration,
                'response': parsed
            })
            
            # Check if LLM has final recommendation or wants more data
            if parsed.get('status') == 'final':
                logger.success(f"   ✅ Final recommendation reached")
                final_recommendation = parsed.get('recommendation', {})
                break
            
            elif parsed.get('status') == 'need_more_data':
                # LLM wants more information
                requested_data = parsed.get('data_requests', [])
                logger.info(f"   📊 LLM requesting: {', '.join(requested_data)}")
                
                # Fetch requested data
                additional_data = self._fetch_requested_data(symbol, requested_data)
                
                conversation_history.append({
                    'role': 'system',
                    'iteration': iteration,
                    'content': 'Additional data provided',
                    'data': additional_data
                })
                
                # Build next prompt with conversation context
                current_prompt = self._build_followup_prompt(
                    symbol, 
                    conversation_history,
                    additional_data
                )
            
            else:
                logger.warning(f"   ⚠️  Unclear LLM response status")
                break
        
        # Compile final result
        result = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'iterations': iteration,
            'conversation_history': conversation_history,
            'final_recommendation': final_recommendation or self._extract_best_recommendation(conversation_history),
            'analysis_depth': 'deep' if iteration > 2 else 'shallow'
        }
        
        logger.info(f"   🎯 Analysis complete: {iteration} iterations")
        return result
    
    def _build_initial_prompt(self, symbol: str, context: Dict[str, Any]) -> str:
        """Build initial analysis prompt"""
        
        prompt = f"""You are an expert trading analyst conducting deep research on {symbol}.

**ITERATIVE ANALYSIS MODE**

You can request additional data in multiple iterations to build a comprehensive analysis.

**Initial Data Available:**
{json.dumps(context, indent=2)}

**Available Data Sources You Can Request:**
- volume_profile: Detailed volume distribution and buying/selling pressure
- intraday_patterns: How the stock behaves during different market hours
- sector_comparison: Performance vs sector peers
- historical_volatility: Volatility trends and patterns
- support_resistance_zones: Key technical levels with strength scores
- gap_analysis: Gap ups/downs and fill patterns
- momentum_indicators: Additional momentum metrics (Stochastic, Williams %R)
- earnings_proximity: Distance to next earnings, historical reactions
- institutional_holdings: Recent institutional buying/selling activity
- options_flow: Unusual options activity and sentiment

**Your Response Format:**

If you need more data to make a confident recommendation:
```json
{{
    "status": "need_more_data",
    "current_assessment": "brief thoughts on what you've seen so far",
    "data_requests": ["source1", "source2"],
    "reasoning": "why you need this specific data"
}}
```

If you have enough information for final recommendation:
```json
{{
    "status": "final",
    "recommendation": {{
        "outlook": "bullish|bearish|neutral",
        "confidence": 0-100,
        "action": "BUY|SELL|HOLD",
        "entry_price": price or null,
        "stop_loss": price or null,
        "target_price": price or null,
        "key_levels": {{"support": price, "resistance": price}},
        "reasoning": "comprehensive explanation based on all data gathered",
        "risk_factors": ["risk1", "risk2"],
        "catalysts": ["catalyst1", "catalyst2"]
    }}
}}
```

Begin your analysis. Request the data you need to build confidence.
"""
        return prompt
    
    def _build_followup_prompt(self, symbol: str, history: List[Dict], new_data: Dict) -> str:
        """Build follow-up prompt with conversation context"""
        
        # Summarize conversation so far
        summary = f"Analyzing {symbol} - Iteration {len([h for h in history if h['role'] == 'assistant']) + 1}\n\n"
        
        # Add last LLM thoughts
        last_assistant = [h for h in history if h['role'] == 'assistant']
        if last_assistant:
            last = last_assistant[-1]
            summary += f"Your previous assessment: {last['response'].get('current_assessment', 'N/A')}\n\n"
        
        # Add new data
        summary += "**New Data You Requested:**\n"
        summary += json.dumps(new_data, indent=2)
        summary += "\n\n"
        
        summary += """**Continue your analysis:**

You can either:
1. Request more data if needed (same format as before)
2. Provide final recommendation if you have sufficient confidence

Remember, you're building a comprehensive picture. Don't rush to conclusion.
What do you see in this new data? Do you need anything else?
"""
        
        return summary
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response, extracting JSON"""
        try:
            # Try to extract JSON from response
            if '```json' in response:
                json_str = response.split('```json')[1].split('```')[0].strip()
            elif '```' in response:
                json_str = response.split('```')[1].split('```')[0].strip()
            else:
                json_str = response.strip()
            
            parsed = json.loads(json_str)
            return parsed
        
        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            # Try to extract any useful information
            return {
                'status': 'error',
                'raw_response': response
            }
    
    def _fetch_requested_data(self, symbol: str, requests: List[str]) -> Dict[str, Any]:
        """Fetch all requested data sources"""
        data = {}
        
        for request in requests:
            if request in self.available_data:
                try:
                    logger.debug(f"      Fetching {request}...")
                    data[request] = self.available_data[request](symbol)
                except Exception as e:
                    logger.warning(f"      Failed to fetch {request}: {e}")
                    data[request] = {"error": str(e)}
            else:
                data[request] = {"error": "Data source not available"}
        
        return data
    
    def _extract_best_recommendation(self, history: List[Dict]) -> Optional[Dict]:
        """Extract best recommendation from conversation if final wasn't reached"""
        for entry in reversed(history):
            if entry['role'] == 'assistant' and 'recommendation' in entry.get('response', {}):
                return entry['response']['recommendation']
        return None
    
    # Data fetching methods
    
    def _get_volume_profile(self, symbol: str) -> Dict[str, Any]:
        """Get volume profile analysis"""
        try:
            bars = self.alpaca.get_bars(symbol, limit=30, timeframe='1Day')
            
            avg_volume = bars['volume'].mean()
            recent_volume = bars['volume'].iloc[-5:].mean()
            volume_trend = "increasing" if recent_volume > avg_volume * 1.2 else "decreasing" if recent_volume < avg_volume * 0.8 else "stable"
            
            # Calculate buying vs selling pressure (simplified)
            bars['buying_pressure'] = (bars['close'] - bars['low']) / (bars['high'] - bars['low'])
            avg_buying_pressure = bars['buying_pressure'].iloc[-10:].mean()
            
            return {
                'average_volume_30d': f"{avg_volume:,.0f}",
                'recent_volume_5d': f"{recent_volume:,.0f}",
                'volume_trend': volume_trend,
                'buying_pressure_score': f"{avg_buying_pressure:.2f}",
                'buying_pressure_interpretation': "bullish" if avg_buying_pressure > 0.6 else "bearish" if avg_buying_pressure < 0.4 else "neutral"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _get_intraday_patterns(self, symbol: str) -> Dict[str, Any]:
        """Get intraday behavior patterns"""
        # Simplified - would need intraday data for real implementation
        return {
            "note": "Intraday data requires higher timeframe access",
            "typical_pattern": "Need subscription upgrade for detailed intraday analysis"
        }
    
    def _get_sector_comparison(self, symbol: str) -> Dict[str, Any]:
        """Compare with sector peers"""
        # Simplified - would compare with sector ETF or similar stocks
        return {
            "note": "Sector comparison requires additional data sources",
            "suggestion": "Compare manually with sector ETF like XLK (tech) or XLF (finance)"
        }
    
    def _get_historical_volatility(self, symbol: str) -> Dict[str, Any]:
        """Calculate historical volatility metrics"""
        try:
            bars = self.alpaca.get_bars(symbol, limit=30, timeframe='1Day')
            
            returns = bars['close'].pct_change()
            volatility_30d = returns.std() * (252 ** 0.5)  # Annualized
            
            recent_vol = returns.iloc[-10:].std() * (252 ** 0.5)
            vol_trend = "increasing" if recent_vol > volatility_30d * 1.2 else "decreasing" if recent_vol < volatility_30d * 0.8 else "stable"
            
            return {
                'annualized_volatility_30d': f"{volatility_30d:.2%}",
                'recent_volatility_10d': f"{recent_vol:.2%}",
                'volatility_trend': vol_trend,
                'interpretation': "high_risk" if recent_vol > 0.5 else "moderate_risk" if recent_vol > 0.3 else "low_risk"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _get_support_resistance(self, symbol: str) -> Dict[str, Any]:
        """Calculate support and resistance zones"""
        try:
            from wawatrader.indicators import TechnicalIndicators
            bars = self.alpaca.get_bars(symbol, limit=60, timeframe='1Day')
            
            ta = TechnicalIndicators()
            signals = ta.calculate_all(bars)
            
            return {
                'support': signals.get('support', 'N/A'),
                'resistance': signals.get('resistance', 'N/A'),
                'current_price': f"${bars['close'].iloc[-1]:.2f}",
                'distance_to_support': f"{((bars['close'].iloc[-1] - signals.get('support', bars['close'].iloc[-1])) / bars['close'].iloc[-1]) * 100:.2f}%",
                'distance_to_resistance': f"{((signals.get('resistance', bars['close'].iloc[-1]) - bars['close'].iloc[-1]) / bars['close'].iloc[-1]) * 100:.2f}%"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _get_gap_analysis(self, symbol: str) -> Dict[str, Any]:
        """Analyze price gaps"""
        try:
            bars = self.alpaca.get_bars(symbol, limit=30, timeframe='1Day')
            
            # Find gaps
            gaps = []
            for i in range(1, len(bars)):
                prev_close = bars['close'].iloc[i-1]
                curr_open = bars['open'].iloc[i]
                gap_pct = ((curr_open - prev_close) / prev_close) * 100
                
                if abs(gap_pct) > 2:  # Significant gap
                    gaps.append({
                        'date': str(bars.index[i].date()),
                        'type': 'gap_up' if gap_pct > 0 else 'gap_down',
                        'size': f"{gap_pct:.2f}%"
                    })
            
            return {
                'recent_gaps': gaps[-5:] if gaps else [],
                'gap_count_30d': len(gaps)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _get_momentum_indicators(self, symbol: str) -> Dict[str, Any]:
        """Get additional momentum indicators"""
        try:
            bars = self.alpaca.get_bars(symbol, limit=30, timeframe='1Day')
            
            # Stochastic Oscillator (simplified)
            low_14 = bars['low'].rolling(14).min()
            high_14 = bars['high'].rolling(14).max()
            stoch_k = ((bars['close'] - low_14) / (high_14 - low_14)) * 100
            
            return {
                'stochastic_k': f"{stoch_k.iloc[-1]:.2f}",
                'stochastic_interpretation': "overbought" if stoch_k.iloc[-1] > 80 else "oversold" if stoch_k.iloc[-1] < 20 else "neutral",
                'price_momentum_5d': f"{bars['close'].pct_change(5).iloc[-1]:.2%}"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _get_earnings_info(self, symbol: str) -> Dict[str, Any]:
        """Get earnings proximity information"""
        # Simplified - would need earnings calendar API
        return {
            "note": "Earnings calendar requires additional data source",
            "suggestion": "Check earnings calendar manually"
        }
    
    def _get_institutional_data(self, symbol: str) -> Dict[str, Any]:
        """Get institutional holdings information"""
        # Would require institutional data feed
        return {
            "note": "Institutional data requires premium data source",
            "suggestion": "Check Form 13F filings manually"
        }
    
    def _get_options_data(self, symbol: str) -> Dict[str, Any]:
        """Get options flow data"""
        # Would require options data feed
        return {
            "note": "Options data requires additional subscription",
            "suggestion": "Check options chain manually for unusual activity"
        }
