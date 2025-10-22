#!/usr/bin/env python3
"""
Enhanced Market Intelligence Engine

Improved version based on actual Alpaca data availability and professional
trading analysis requirements. Focuses on actionable insights using
available data: OHLCV, sector ETFs, and major indices.

Key improvements:
- Correct sector classifications
- Regime assessment based on 20-SMA positions
- Structured momentum analysis
- Trading-focused recommendations
- Professional risk assessment
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import pandas as pd
import numpy as np
from loguru import logger

from wawatrader.alpaca_client import get_client
from wawatrader.llm_bridge import create_llm_bridge
from config.settings import settings


@dataclass
class EnhancedMarketIntelligence:
    """Enhanced market intelligence with professional structure"""
    timestamp: str
    market_sentiment: str  # bullish, bearish, neutral, cautious_bullish, cautious_bearish
    confidence: int  # 0-100
    key_findings: List[str]
    opportunities: List[Dict[str, str]]  # symbol, reason
    risks: List[Dict[str, str]]  # type, description
    sector_analysis: Dict[str, str]  # strongest, weakest
    regime_assessment: str  # risk_on, risk_off, transition, neutral
    recommended_actions: List[str]


class EnhancedMarketIntelligenceEngine:
    """
    Professional market analysis engine using available Alpaca data
    """
    
    def __init__(self):
        self.alpaca = get_client()
        self.llm = create_llm_bridge()
        
        # Sector ETF mappings with correct classifications
        self.sector_etfs = {
            'XLK': 'Technology',
            'XLF': 'Financials',
            'XLV': 'Healthcare', 
            'XLE': 'Energy',
            'XLI': 'Industrials',  # Corrected: NOT Financials/Healthcare
            'XLC': 'Communication Services',
            'XLY': 'Consumer Discretionary',  # Corrected: NOT Technology
            'XLP': 'Consumer Staples',
            'XLU': 'Utilities',
            'XLRE': 'Real Estate',
            'XLB': 'Materials'
        }
        
        # Key indices for regime assessment
        self.key_indices = ['SPY', 'QQQ', 'IWM', 'TLT', 'GLD']
        
        logger.info("✅ Enhanced Market Intelligence Engine initialized")
        logger.info(f"   Tracking {len(self.sector_etfs)} sectors")
        logger.info(f"   Monitoring {len(self.key_indices)} key indices")

    async def run_enhanced_analysis(self) -> Optional[EnhancedMarketIntelligence]:
        """
        Run comprehensive market analysis with professional structure
        """
        logger.info("🧠 Running enhanced market intelligence analysis...")
        start_time = datetime.now()
        
        try:
            # Gather all market data
            logger.debug("📊 Gathering market data...")
            
            # Get 60 days of data for technical analysis
            end_date = datetime.now() - timedelta(hours=1)
            start_date = end_date - timedelta(days=60)
            
            # Collect sector performance data
            sector_data = await self._analyze_sector_performance(start_date, end_date)
            
            # Collect index regime data  
            index_data = await self._analyze_index_regimes(start_date, end_date)
            
            # Synthesize analysis
            analysis = await self._synthesize_enhanced_analysis(sector_data, index_data)
            
            analysis_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ Enhanced analysis completed in {analysis_time:.1f}s")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Enhanced analysis failed: {e}")
            return self._get_fallback_analysis()

    async def _analyze_sector_performance(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Analyze sector ETF performance with proper classifications
        """
        logger.debug("🏭 Analyzing sector performance...")
        
        sector_performance = {}
        sector_rankings = []
        
        for etf, sector_name in self.sector_etfs.items():
            try:
                bars = self.alpaca.get_bars(etf, start=start_date, end=end_date)
                
                if not bars.empty and len(bars) >= 20:
                    current_price = bars.iloc[-1]['close']
                    
                    # Calculate returns
                    ret_5d = ((bars.iloc[-1]['close'] / bars.iloc[-5]['close']) - 1) * 100 if len(bars) >= 5 else 0
                    ret_30d = ((bars.iloc[-1]['close'] / bars.iloc[-30]['close']) - 1) * 100 if len(bars) >= 30 else 0
                    
                    # Technical indicators
                    sma_20 = bars['close'].rolling(20).mean().iloc[-1]
                    above_sma = current_price > sma_20
                    
                    # Volume analysis
                    avg_volume = bars['volume'].mean()
                    recent_volume = bars.iloc[-1]['volume']
                    volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
                    
                    sector_performance[etf] = {
                        'sector_name': sector_name,
                        'return_5d': ret_5d,
                        'return_30d': ret_30d,
                        'above_20sma': above_sma,
                        'current_price': current_price,
                        'sma_20': sma_20,
                        'volume_ratio': volume_ratio
                    }
                    
                    sector_rankings.append((etf, sector_name, ret_5d))
                    
            except Exception as e:
                logger.debug(f"Sector analysis error for {etf}: {e}")
                continue
        
        # Sort by 5-day performance
        sector_rankings.sort(key=lambda x: x[2], reverse=True)
        
        return {
            'sector_data': sector_performance,
            'rankings': sector_rankings,
            'top_3': sector_rankings[:3],
            'bottom_3': sector_rankings[-3:]
        }

    async def _analyze_index_regimes(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Analyze key indices for market regime assessment
        """
        logger.debug("📈 Analyzing index regimes...")
        
        index_data = {}
        indices_above_sma = 0
        total_valid_indices = 0
        
        for symbol in self.key_indices:
            try:
                bars = self.alpaca.get_bars(symbol, start=start_date, end=end_date)
                
                if not bars.empty and len(bars) >= 20:
                    current_price = bars.iloc[-1]['close']
                    
                    # Calculate returns
                    ret_5d = ((bars.iloc[-1]['close'] / bars.iloc[-5]['close']) - 1) * 100 if len(bars) >= 5 else 0
                    ret_30d = ((bars.iloc[-1]['close'] / bars.iloc[-30]['close']) - 1) * 100 if len(bars) >= 30 else 0
                    
                    # Technical regime indicators
                    sma_20 = bars['close'].rolling(20).mean().iloc[-1]
                    above_sma = current_price > sma_20
                    
                    if above_sma:
                        indices_above_sma += 1
                    total_valid_indices += 1
                    
                    index_data[symbol] = {
                        'current_price': current_price,
                        'return_5d': ret_5d,
                        'return_30d': ret_30d,
                        'above_20sma': above_sma,
                        'sma_20': sma_20
                    }
                    
            except Exception as e:
                logger.debug(f"Index analysis error for {symbol}: {e}")
                continue
        
        # Determine market regime
        sma_ratio = indices_above_sma / total_valid_indices if total_valid_indices > 0 else 0
        
        if sma_ratio >= 0.8:
            regime = "risk_on"
        elif sma_ratio <= 0.2:
            regime = "risk_off"
        elif 0.4 <= sma_ratio <= 0.6:
            regime = "neutral"
        else:
            regime = "transition"
            
        return {
            'index_data': index_data,
            'indices_above_sma': indices_above_sma,
            'total_indices': total_valid_indices,
            'sma_ratio': sma_ratio,
            'regime': regime
        }

    async def _synthesize_enhanced_analysis(self, sector_data: Dict, index_data: Dict) -> EnhancedMarketIntelligence:
        """
        Synthesize data into professional market intelligence using LLM
        """
        logger.debug("🧠 Synthesizing enhanced analysis...")
        
        # Create structured prompt with actual data
        prompt = self._create_enhanced_prompt(sector_data, index_data)
        
        try:
            # Get LLM analysis
            response = await self.llm.analyze_async(prompt)
            
            if response:
                parsed = self._parse_enhanced_response(response)
                if parsed:
                    return EnhancedMarketIntelligence(**parsed)
            
            # Fallback to rule-based analysis
            return self._create_rule_based_analysis(sector_data, index_data)
            
        except Exception as e:
            logger.warning(f"LLM synthesis failed: {e}, using rule-based analysis")
            return self._create_rule_based_analysis(sector_data, index_data)

    def _create_enhanced_prompt(self, sector_data: Dict, index_data: Dict) -> str:
        """
        Create enhanced prompt with structured data and professional requirements
        """
        prompt_parts = [
            "You are a senior institutional market analyst. Analyze this market data and provide professional trading intelligence.",
            "",
            "=== SECTOR PERFORMANCE DATA ===",
        ]
        
        # Add sector rankings with correct labels
        if sector_data['rankings']:
            prompt_parts.append("5-Day Sector Performance (correct classifications):")
            for i, (etf, sector_name, ret_5d) in enumerate(sector_data['rankings']):
                sma_status = "✓" if sector_data['sector_data'][etf]['above_20sma'] else "✗"
                prompt_parts.append(f"{i+1}. {etf} ({sector_name}): {ret_5d:+.2f}% (>20-SMA: {sma_status})")
        
        prompt_parts.extend([
            "",
            "=== INDEX REGIME DATA ===",
        ])
        
        # Add index regime information
        for symbol, data in index_data['index_data'].items():
            sma_status = "✓" if data['above_20sma'] else "✗"
            prompt_parts.append(f"{symbol}: {data['return_5d']:+.2f}% (5D), {data['return_30d']:+.2f}% (30D), >20-SMA: {sma_status}")
        
        prompt_parts.extend([
            f"",
            f"Market Regime: {index_data['indices_above_sma']}/{index_data['total_indices']} indices above 20-SMA = {index_data['regime']}",
            "",
            "=== ANALYSIS REQUIREMENTS ===",
            "Provide analysis in this EXACT JSON format:",
            "{",
            '  "market_sentiment": "bullish|bearish|neutral|cautious_bullish|cautious_bearish",',
            '  "confidence": 0-100,',
            '  "key_findings": [',
            '    "Cyclicals leading: [top sectors with returns]",',
            '    "Defensives status: [bottom sectors analysis]", ',
            '    "Index regime: [SPY/QQQ/IWM analysis vs 20-SMA]",',
            '    "Bond/Gold positioning: [TLT/GLD analysis]"',
            '  ],',
            '  "opportunities": [',
            '    {"symbol": "ETF", "reason": "Specific technical/momentum reason"},',
            '    {"symbol": "PAIR_TRADE", "reason": "Long X / Short Y rationale"}',
            '  ],',
            '  "risks": [',
            '    {"type": "headline|rotation|overextension", "description": "Specific risk"}',
            '  ],',
            '  "sector_analysis": {',
            '    "strongest": "Top performing sector ETF symbol",',
            '    "weakest": "Worst performing sector ETF symbol"',
            '  },',
            '  "regime_assessment": "risk_on|risk_off|transition|neutral",',
            '  "recommended_actions": [',
            '    "Momentum long filter: specific criteria",',
            '    "Entry: specific entry rules with technical levels",',
            '    "Risk: stop loss and position sizing rules",',
            '    "Exit: specific exit criteria"',
            '  ]',
            "}",
            "",
            "CRITICAL REQUIREMENTS:",
            "- Use EXACT sector ETF symbols (XLI=Industrials, XLY=Consumer Discretionary)",
            "- Base regime on actual >20-SMA data provided", 
            "- Focus on actionable trading recommendations",
            "- Include specific technical levels and risk parameters"
        ])
        
        return "\n".join(prompt_parts)

    def _parse_enhanced_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Parse enhanced LLM response with validation
        """
        try:
            import json
            
            # Clean response
            response_clean = response.strip()
            if response_clean.startswith("```json"):
                response_clean = response_clean[7:]
            elif response_clean.startswith("```"):
                response_clean = response_clean[3:]
            if response_clean.endswith("```"):
                response_clean = response_clean[:-3]
            
            data = json.loads(response_clean.strip())
            
            # Add timestamp
            data['timestamp'] = datetime.now().isoformat()
            
            # Validate required fields
            required_fields = [
                'market_sentiment', 'confidence', 'key_findings',
                'opportunities', 'risks', 'sector_analysis', 
                'regime_assessment', 'recommended_actions'
            ]
            
            for field in required_fields:
                if field not in data:
                    logger.error(f"Missing required field: {field}")
                    return None
            
            # Validate confidence range
            if not (0 <= data['confidence'] <= 100):
                logger.error(f"Invalid confidence: {data['confidence']}")
                return None
                
            return data
            
        except Exception as e:
            logger.error(f"Failed to parse enhanced response: {e}")
            return None

    def _create_rule_based_analysis(self, sector_data: Dict, index_data: Dict) -> EnhancedMarketIntelligence:
        """
        Create rule-based analysis when LLM fails
        """
        logger.debug("🤖 Creating rule-based fallback analysis...")
        
        # Determine sentiment based on regime
        regime = index_data['regime']
        if regime == "risk_on":
            sentiment = "cautious_bullish"
            confidence = 75
        elif regime == "risk_off":
            sentiment = "bearish"
            confidence = 70
        else:
            sentiment = "neutral"
            confidence = 60
        
        # Build key findings
        top_sectors = sector_data['top_3'][:3]
        bottom_sectors = sector_data['bottom_3'][-3:]
        
        key_findings = [
            f"Top sectors: {', '.join([f'{etf} ({name}) {ret:.1f}%' for etf, name, ret in top_sectors])}",
            f"Weak sectors: {', '.join([f'{etf} ({name}) {ret:.1f}%' for etf, name, ret in bottom_sectors])}",
            f"Market regime: {index_data['indices_above_sma']}/{index_data['total_indices']} indices above 20-SMA ({regime})"
        ]
        
        # Basic opportunities
        opportunities = []
        if top_sectors:
            etf, name, ret = top_sectors[0]
            opportunities.append({
                "symbol": etf,
                "reason": f"Leading sector momentum with {ret:.1f}% 5-day return"
            })
        
        # Basic risks
        risks = [
            {"type": "rotation", "description": "Sector rotation risk if market regime changes"},
            {"type": "headline", "description": "News flow and earnings volatility"}
        ]
        
        return EnhancedMarketIntelligence(
            timestamp=datetime.now().isoformat(),
            market_sentiment=sentiment,
            confidence=confidence,
            key_findings=key_findings,
            opportunities=opportunities,
            risks=risks,
            sector_analysis={
                "strongest": top_sectors[0][0] if top_sectors else "N/A",
                "weakest": bottom_sectors[-1][0] if bottom_sectors else "N/A"
            },
            regime_assessment=regime,
            recommended_actions=[
                "Monitor sector rotation patterns",
                "Use strict risk management", 
                "Focus on liquid ETFs only"
            ]
        )

    def _get_fallback_analysis(self) -> EnhancedMarketIntelligence:
        """
        Emergency fallback when all analysis fails
        """
        return EnhancedMarketIntelligence(
            timestamp=datetime.now().isoformat(),
            market_sentiment="neutral",
            confidence=50,
            key_findings=["Market data temporarily unavailable"],
            opportunities=[],
            risks=[{"type": "data", "description": "Limited market data availability"}],
            sector_analysis={"strongest": "N/A", "weakest": "N/A"},
            regime_assessment="neutral",
            recommended_actions=["Wait for market data to become available"]
        )


# Global instance
_enhanced_intelligence_engine = None

def get_enhanced_intelligence_engine() -> EnhancedMarketIntelligenceEngine:
    """Get singleton enhanced intelligence engine"""
    global _enhanced_intelligence_engine
    if _enhanced_intelligence_engine is None:
        _enhanced_intelligence_engine = EnhancedMarketIntelligenceEngine()
    return _enhanced_intelligence_engine