#!/usr/bin/env python3
"""
WawaTrader Market Intelligence Engine

Leverages LLM during idle time to perform continuous market analysis:
- Market screening and opportunity detection
- Sector rotation analysis
- Risk monitoring and early warning
- Portfolio optimization suggestions
- Earnings and news intelligence

This module runs during the 5-minute intervals between trading cycles.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import pandas as pd
from loguru import logger

from wawatrader.alpaca_client import get_client
from wawatrader.llm_bridge import create_llm_bridge
from wawatrader.database import get_database
from config.settings import settings


@dataclass
class MarketIntelligence:
    """Container for market intelligence results"""
    timestamp: str
    market_sentiment: str  # bullish, bearish, neutral
    confidence: float
    key_findings: List[str]
    opportunities: List[Dict[str, Any]]
    risks: List[Dict[str, Any]]
    sector_analysis: Dict[str, Any]
    regime_assessment: str  # bull_market, bear_market, sideways, transition
    recommended_actions: List[str]


class MarketIntelligenceEngine:
    """
    Advanced market analysis using LLM during trading idle time
    """
    
    def __init__(self):
        self.alpaca = get_client()
        self.llm = create_llm_bridge()
        self.db = get_database()
        
        # Market tracking lists
        self.sp500_symbols = self._get_sp500_sample()
        self.sector_etfs = [
            'XLK',  # Technology
            'XLF',  # Financials  
            'XLV',  # Healthcare
            'XLE',  # Energy
            'XLI',  # Industrials
            'XLC',  # Communication Services
            'XLY',  # Consumer Discretionary
            'XLP',  # Consumer Staples
            'XLU',  # Utilities
            'XLRE', # Real Estate
            'XLB'   # Materials
        ]
        
        # Market indices for regime analysis
        self.market_indices = ['SPY', 'QQQ', 'IWM', 'VIX', 'TLT', 'GLD']
        
        logger.info("Market Intelligence Engine initialized")
        logger.info(f"  Monitoring {len(self.sp500_symbols)} stocks")
        logger.info(f"  Tracking {len(self.sector_etfs)} sector ETFs")
        logger.info(f"  Analyzing {len(self.market_indices)} market indices")

    def _get_sp500_sample(self) -> List[str]:
        """
        Get a sample of S&P 500 stocks to monitor
        
        Returns:
            List of top 50 S&P 500 symbols by market cap
        """
        # Top 50 S&P 500 by market cap (representative sample)
        return [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK.B',
            'UNH', 'JNJ', 'XOM', 'JPM', 'V', 'PG', 'MA', 'HD', 'CVX', 'LLY',
            'ABBV', 'PFE', 'BAC', 'KO', 'AVGO', 'PEP', 'TMO', 'COST', 'MRK',
            'WMT', 'CSCO', 'ACN', 'DHR', 'VZ', 'ABT', 'ADBE', 'NKE', 'TXN',
            'CRM', 'DIS', 'BMY', 'NFLX', 'PM', 'T', 'RTX', 'QCOM', 'HON',
            'SCHW', 'UPS', 'AMGN', 'LOW', 'IBM'
        ]

    async def run_background_analysis(self) -> MarketIntelligence:
        """
        Run comprehensive background market analysis during idle time
        
        Returns:
            MarketIntelligence object with findings
        """
        logger.info("🔍 Starting background market intelligence analysis...")
        start_time = datetime.now()
        
        try:
            # Run analysis tasks in parallel for speed
            tasks = [
                self.analyze_market_screening(),
                self.analyze_sector_momentum(),  
                self.analyze_market_regime(),
                self.analyze_news_sentiment(),
                self.analyze_earnings_calendar(),
                self.analyze_risk_factors()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine results
            market_screening = results[0] if not isinstance(results[0], Exception) else {}
            sector_analysis = results[1] if not isinstance(results[1], Exception) else {}
            regime_analysis = results[2] if not isinstance(results[2], Exception) else {}
            news_sentiment = results[3] if not isinstance(results[3], Exception) else {}
            earnings_intel = results[4] if not isinstance(results[4], Exception) else {}
            risk_analysis = results[5] if not isinstance(results[5], Exception) else {}
            
            # Use LLM to synthesize all findings
            synthesis = await self.synthesize_intelligence({
                'market_screening': market_screening,
                'sector_analysis': sector_analysis,
                'regime_analysis': regime_analysis,
                'news_sentiment': news_sentiment,
                'earnings_intel': earnings_intel,
                'risk_analysis': risk_analysis
            })
            
            analysis_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ Background analysis completed in {analysis_time:.1f}s")
            
            return synthesis
            
        except Exception as e:
            logger.error(f"❌ Background analysis failed: {e}")
            return self._get_fallback_intelligence()

    async def analyze_market_screening(self) -> Dict[str, Any]:
        """
        Screen market for unusual activity and opportunities
        """
        logger.debug("📊 Scanning market for opportunities...")
        
        try:
            # Get recent data for screening
            screening_data = []
            
            # Sample 20 stocks for performance (full S&P 500 would be too slow)
            sample_symbols = self.sp500_symbols[:20]
            
            for symbol in sample_symbols:
                try:
                    # Get 2 days of data for change analysis
                    bars = self.alpaca.get_bars(
                        symbol=symbol,
                        start=datetime.now() - timedelta(days=2),
                        end=datetime.now() - timedelta(hours=24),
                        timeframe='1Day'
                    )
                    
                    if not bars.empty and len(bars) >= 2:
                        current_price = bars.iloc[-1]['close']
                        prev_price = bars.iloc[-2]['close'] if len(bars) > 1 else current_price
                        volume = bars.iloc[-1]['volume']
                        avg_volume = bars['volume'].mean()
                        
                        pct_change = ((current_price - prev_price) / prev_price) * 100
                        volume_ratio = volume / avg_volume if avg_volume > 0 else 1
                        
                        screening_data.append({
                            'symbol': symbol,
                            'price': current_price,
                            'pct_change': pct_change,
                            'volume_ratio': volume_ratio,
                            'unusual_volume': volume_ratio > 1.5,
                            'big_mover': abs(pct_change) > 3
                        })
                        
                except Exception as e:
                    logger.debug(f"Screening error for {symbol}: {e}")
                    continue
            
            if screening_data:
                # Find notable patterns
                big_movers = [s for s in screening_data if s['big_mover']]
                high_volume = [s for s in screening_data if s['unusual_volume']]
                
                return {
                    'total_screened': len(screening_data),
                    'big_movers': big_movers[:5],  # Top 5
                    'high_volume': high_volume[:5],  # Top 5
                    'avg_market_change': sum(s['pct_change'] for s in screening_data) / len(screening_data)
                }
            
            return {'status': 'no_data'}
            
        except Exception as e:
            logger.error(f"Market screening error: {e}")
            return {'status': 'error', 'message': str(e)}

    async def analyze_sector_momentum(self) -> Dict[str, Any]:
        """
        Analyze sector ETF performance and rotation
        """
        logger.debug("🏭 Analyzing sector momentum...")
        
        try:
            sector_data = {}
            
            for etf in self.sector_etfs:
                try:
                    bars = self.alpaca.get_bars(
                        symbol=etf,
                        start=datetime.now() - timedelta(days=5),
                        end=datetime.now() - timedelta(hours=24),
                        timeframe='1Day'
                    )
                    
                    if not bars.empty:
                        recent_return = ((bars.iloc[-1]['close'] - bars.iloc[0]['close']) / bars.iloc[0]['close']) * 100
                        
                        sector_data[etf] = {
                            'return_5d': recent_return,
                            'current_price': bars.iloc[-1]['close'],
                            'volume': bars.iloc[-1]['volume']
                        }
                        
                except Exception as e:
                    logger.debug(f"Sector analysis error for {etf}: {e}")
                    continue
            
            if sector_data:
                # Rank sectors by performance
                sorted_sectors = sorted(sector_data.items(), 
                                      key=lambda x: x[1]['return_5d'], 
                                      reverse=True)
                
                return {
                    'top_sectors': sorted_sectors[:3],
                    'bottom_sectors': sorted_sectors[-3:],
                    'sector_data': sector_data
                }
            
            return {'status': 'no_data'}
            
        except Exception as e:
            logger.error(f"Sector analysis error: {e}")
            return {'status': 'error', 'message': str(e)}

    async def analyze_market_regime(self) -> Dict[str, Any]:
        """
        Analyze market indices to determine current regime
        """
        logger.debug("📈 Analyzing market regime...")
        
        try:
            regime_data = {}
            
            for index in self.market_indices:
                try:
                    bars = self.alpaca.get_bars(
                        symbol=index,
                        start=datetime.now() - timedelta(days=30),
                        end=datetime.now() - timedelta(hours=24),
                        timeframe='1Day'
                    )
                    
                    if not bars.empty and len(bars) >= 20:
                        # Calculate key metrics
                        prices = bars['close']
                        sma_20 = prices.rolling(20).mean().iloc[-1]
                        current_price = prices.iloc[-1]
                        volatility = prices.pct_change().std() * 100
                        
                        regime_data[index] = {
                            'price': current_price,
                            'sma_20': sma_20,
                            'above_sma': current_price > sma_20,
                            'volatility': volatility,
                            'return_30d': ((current_price - prices.iloc[0]) / prices.iloc[0]) * 100
                        }
                        
                except Exception as e:
                    logger.debug(f"Regime analysis error for {index}: {e}")
                    continue
            
            return regime_data
            
        except Exception as e:
            logger.error(f"Market regime analysis error: {e}")
            return {'status': 'error', 'message': str(e)}

    async def analyze_news_sentiment(self) -> Dict[str, Any]:
        """
        Aggregate and analyze market-wide news sentiment
        """
        logger.debug("📰 Analyzing news sentiment...")
        
        try:
            # Get news for major indices and our stocks
            news_symbols = ['SPY', 'QQQ'] + ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
            all_news = []
            
            for symbol in news_symbols:
                try:
                    news = self.alpaca.get_news(symbol, limit=5)
                    if news:
                        all_news.extend(news)
                except Exception as e:
                    logger.debug(f"News fetch error for {symbol}: {e}")
                    continue
            
            if all_news:
                return {
                    'total_articles': len(all_news),
                    'recent_headlines': [n.get('headline', '') for n in all_news[:10]],
                    'news_data': all_news[:20]  # Limit for LLM processing
                }
            
            return {'status': 'no_news'}
            
        except Exception as e:
            logger.error(f"News sentiment error: {e}")
            return {'status': 'error', 'message': str(e)}

    async def analyze_earnings_calendar(self) -> Dict[str, Any]:
        """
        Check upcoming earnings for portfolio and market
        """
        logger.debug("📅 Checking earnings calendar...")
        
        # Placeholder for earnings calendar analysis
        # In a full implementation, this would connect to earnings calendar APIs
        return {
            'status': 'placeholder',
            'message': 'Earnings calendar analysis not yet implemented'
        }

    async def analyze_risk_factors(self) -> Dict[str, Any]:
        """
        Identify current market risks and stress factors
        """
        logger.debug("⚠️ Analyzing risk factors...")
        
        try:
            risk_indicators = {}
            
            # Check VIX for fear/greed
            try:
                vix_bars = self.alpaca.get_bars(
                    symbol='VIX',
                    start=datetime.now() - timedelta(days=5),
                    end=datetime.now() - timedelta(hours=24),
                    timeframe='1Day'
                )
                
                if not vix_bars.empty:
                    current_vix = vix_bars.iloc[-1]['close']
                    risk_indicators['vix'] = {
                        'level': current_vix,
                        'risk_level': 'high' if current_vix > 25 else 'medium' if current_vix > 15 else 'low'
                    }
            except Exception as e:
                logger.debug(f"VIX analysis error: {e}")
            
            return risk_indicators
            
        except Exception as e:
            logger.error(f"Risk analysis error: {e}")
            return {'status': 'error', 'message': str(e)}

    async def synthesize_intelligence(self, analysis_data: Dict[str, Any]) -> MarketIntelligence:
        """
        Use LLM to synthesize all analysis into actionable intelligence
        """
        logger.debug("🧠 Synthesizing market intelligence with LLM...")
        
        try:
            # Create comprehensive prompt for LLM
            prompt = self._create_synthesis_prompt(analysis_data)
            
            # Query LLM for synthesis
            response = self.llm.query_llm(prompt)
            
            if response:
                # Parse JSON directly since it's a custom format
                parsed = self._parse_intelligence_response(response)
                if parsed:
                    return MarketIntelligence(
                        timestamp=datetime.now().isoformat(),
                        market_sentiment=parsed.get('market_sentiment', 'neutral'),
                        confidence=parsed.get('confidence', 50),
                        key_findings=parsed.get('key_findings', []),
                        opportunities=parsed.get('opportunities', []),
                        risks=parsed.get('risks', []),
                        sector_analysis=parsed.get('sector_analysis', {}),
                        regime_assessment=parsed.get('regime_assessment', 'unknown'),
                        recommended_actions=parsed.get('recommended_actions', [])
                    )
            
            return self._get_fallback_intelligence()
            
        except Exception as e:
            logger.error(f"Intelligence synthesis error: {e}")
            return self._get_fallback_intelligence()

    def _create_synthesis_prompt(self, data: Dict[str, Any]) -> str:
        """Create LLM prompt for market intelligence synthesis"""
        
        prompt_parts = [
            "You are a senior market analyst. Analyze the following market data and provide comprehensive intelligence.",
            "",
            "MARKET SCREENING DATA:",
            str(data.get('market_screening', 'No data available')),
            "",
            "SECTOR ANALYSIS:",
            str(data.get('sector_analysis', 'No data available')),
            "",
            "MARKET REGIME INDICATORS:",
            str(data.get('regime_analysis', 'No data available')),
            "",
            "NEWS SENTIMENT:",
            str(data.get('news_sentiment', 'No data available')),
            "",
            "RISK FACTORS:",
            str(data.get('risk_analysis', 'No data available')),
            "",
            "Provide analysis in JSON format:",
            "{",
            '  "market_sentiment": "bullish|bearish|neutral",',
            '  "confidence": 0-100,',
            '  "key_findings": ["finding1", "finding2", ...],',
            '  "opportunities": [{"symbol": "XYZ", "reason": "..."}],',
            '  "risks": [{"type": "risk_type", "description": "..."}],',
            '  "sector_analysis": {"strongest": "sector", "weakest": "sector"},',
            '  "regime_assessment": "bull_market|bear_market|sideways|transition",',
            '  "recommended_actions": ["action1", "action2", ...]',
            "}",
            "",
            "Focus on actionable insights for algorithmic trading decisions."
        ]
        
        return "\n".join(prompt_parts)

    def _parse_intelligence_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse intelligence response JSON"""
        try:
            import json
            
            # Clean up response
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
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to parse intelligence response: {e}")
            return None

    def _get_fallback_intelligence(self) -> MarketIntelligence:
        """Return fallback intelligence when analysis fails"""
        return MarketIntelligence(
            timestamp=datetime.now().isoformat(),
            market_sentiment='neutral',
            confidence=50,
            key_findings=['Analysis system temporarily unavailable'],
            opportunities=[],
            risks=[{'type': 'system', 'description': 'Market intelligence system error'}],
            sector_analysis={},
            regime_assessment='unknown',
            recommended_actions=['Continue with current strategy']
        )

    def save_intelligence(self, intelligence: MarketIntelligence):
        """Save intelligence to database for historical tracking"""
        try:
            # In a full implementation, this would save to database
            logger.debug("💾 Saving market intelligence to database...")
            
        except Exception as e:
            logger.error(f"Failed to save intelligence: {e}")


# Singleton pattern
_intelligence_engine = None

def get_intelligence_engine():
    """Get market intelligence engine singleton"""
    global _intelligence_engine
    if _intelligence_engine is None:
        _intelligence_engine = MarketIntelligenceEngine()
    return _intelligence_engine


if __name__ == "__main__":
    # Test the intelligence engine
    import asyncio
    
    async def test_intelligence():
        engine = get_intelligence_engine()
        intelligence = await engine.run_background_analysis()
        print(f"Market Sentiment: {intelligence.market_sentiment}")
        print(f"Confidence: {intelligence.confidence}%")
        print(f"Key Findings: {intelligence.key_findings}")
    
    asyncio.run(test_intelligence())