"""
Dynamic Symbol Discovery Engine
================================
Multi-source symbol discovery that runs during off-hours to find trading opportunities.

NO HARDCODED WATCHLISTS - all symbols discovered dynamically from API calls.
Universe size is dynamic based on opportunity quality.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from enum import Enum
import statistics
from loguru import logger


class DiscoverySource(Enum):
    """Sources for symbol discovery"""
    UNUSUAL_VOLUME = "unusual_volume"
    NEWS_MENTIONS = "news_mentions"
    GAP_SCANNER = "gap_scanner"
    SECTOR_MOVERS = "sector_movers"
    EARNINGS_CALENDAR = "earnings_calendar"
    ANALYST_RATINGS = "analyst_ratings"
    INSTITUTIONAL_FLOWS = "institutional_flows"
    SOCIAL_SENTIMENT = "social_sentiment"


@dataclass
class RankedOpportunity:
    """
    A discovered trading opportunity with quality ranking.
    """
    symbol: str
    discovery_source: DiscoverySource
    discovery_timestamp: datetime
    
    # Quality metrics
    quality_score: float = 0.0  # 0-100 overall quality
    urgency: int = 0  # 1-10 how urgent
    
    # Ranking factors
    liquidity_score: float = 0.0  # Can we trade it?
    catalyst_strength: float = 0.0  # Why is it moving?
    technical_setup_score: float = 0.0  # Is it actionable?
    news_sentiment: float = 0.0  # -1 to +1
    volume_anomaly: float = 0.0  # How unusual?
    sector_correlation: float = 0.0  # Isolated or group move?
    
    # Strategy suggestion
    expected_strategy: str = ""  # Suggested strategy type
    
    # Discovery data
    discovery_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'symbol': self.symbol,
            'discovery_source': self.discovery_source.value,
            'discovery_timestamp': self.discovery_timestamp.isoformat(),
            'quality_score': self.quality_score,
            'urgency': self.urgency,
            'liquidity_score': self.liquidity_score,
            'catalyst_strength': self.catalyst_strength,
            'technical_setup_score': self.technical_setup_score,
            'news_sentiment': self.news_sentiment,
            'volume_anomaly': self.volume_anomaly,
            'sector_correlation': self.sector_correlation,
            'expected_strategy': self.expected_strategy,
            'discovery_data': self.discovery_data,
        }


class SymbolDiscoveryEngine:
    """
    Dynamic symbol discovery from multiple ranked sources.
    
    Runs during off-hours (Evening Research, Deep Night phases) to prepare
    opportunities for market open.
    
    NO HARDCODED SYMBOLS - all from API/logs.
    """
    
    def __init__(self, alpaca_client, market_intelligence):
        """
        Args:
            alpaca_client: AlpacaClient for market data
            market_intelligence: MarketIntelligence for news/analysis
        """
        self.alpaca_client = alpaca_client
        self.market_intelligence = market_intelligence
        self.discovered_opportunities: List[RankedOpportunity] = []
    
    def discover_opportunities(self) -> List[RankedOpportunity]:
        """
        Run all discovery methods, rank by quality, return top opportunities.
        
        Universe size is DYNAMIC based on opportunity quality.
        Called during MarketHoursManager.EVENING_RESEARCH phase.
        """
        logger.info("🔍 Starting evening symbol discovery...")
        
        # Run all scanners
        sources = []
        
        try:
            sources.append(self._scan_unusual_volume())
        except Exception as e:
            logger.error(f"❌ Unusual volume scanner failed: {e}")
        
        try:
            sources.append(self._scan_news_mentions())
        except Exception as e:
            logger.error(f"❌ News mentions scanner failed: {e}")
        
        try:
            sources.append(self._scan_sector_movers())
        except Exception as e:
            logger.error(f"❌ Sector movers scanner failed: {e}")
        
        try:
            sources.append(self._scan_earnings_calendar())
        except Exception as e:
            logger.error(f"❌ Earnings calendar scanner failed: {e}")
        
        # Aggregate and deduplicate
        all_opportunities = self._aggregate_sources(sources)
        
        # Rank by quality
        ranked = self._rank_opportunities(all_opportunities)
        
        # Dynamic universe sizing (no fixed limit)
        quality_threshold = self._calculate_quality_threshold(ranked)
        filtered = [opp for opp in ranked if opp.quality_score >= quality_threshold]
        
        logger.info(
            f"📊 Discovery results: {len(all_opportunities)} found, "
            f"{len(filtered)} above quality threshold ({quality_threshold:.0f})"
        )
        
        self.discovered_opportunities = filtered
        return filtered
    
    def _scan_unusual_volume(self) -> List[RankedOpportunity]:
        """
        Scan for stocks with unusual volume (> 2x average).
        
        High priority - immediate action potential.
        
        Strategy: Check recent news for mentioned symbols, then verify
        if they have unusual volume using market data.
        """
        logger.debug("📊 Scanning unusual volume...")
        opportunities = []
        
        try:
            # Get recent news to find actively discussed symbols
            news_items = self.alpaca_client.get_news(
                symbols="*",  # All symbols
                start=datetime.now() - timedelta(hours=4),
                limit=50
            )
            
            # Extract unique symbols from news
            candidate_symbols = set()
            for news in news_items:
                symbols = news.get('symbols', [])
                candidate_symbols.update(symbols)
            
            logger.debug(f"   Found {len(candidate_symbols)} symbols in recent news")
            
            # Check volume for each candidate
            for symbol in list(candidate_symbols)[:20]:  # Limit to top 20 to avoid API limits
                try:
                    # Get recent bars to check volume (use daily data after hours)
                    bars = self.alpaca_client.get_bars(symbol, timeframe="1Day", limit=10)
                    
                    if bars is not None and len(bars) > 2:
                        current_volume = bars['volume'].iloc[-1]
                        avg_volume = bars['volume'].iloc[:-1].mean()
                        
                        if avg_volume > 0:
                            volume_ratio = current_volume / avg_volume
                            
                            if volume_ratio > 2.0:  # Unusual volume threshold
                                opp = RankedOpportunity(
                                    symbol=symbol,
                                    discovery_source=DiscoverySource.UNUSUAL_VOLUME,
                                    discovery_timestamp=datetime.now(),
                                    volume_anomaly=volume_ratio,
                                    catalyst_strength=min(volume_ratio * 20, 100),
                                    discovery_data={
                                        'current_volume': int(current_volume),
                                        'avg_volume': int(avg_volume),
                                        'volume_ratio': float(volume_ratio)
                                    }
                                )
                                opportunities.append(opp)
                                logger.debug(f"   📊 {symbol}: {volume_ratio:.1f}x volume")
                
                except Exception as e:
                    logger.debug(f"   ⚠️ Could not check volume for {symbol}: {e}")
                    continue
            
            logger.debug(f"   ✅ Found {len(opportunities)} unusual volume opportunities")
            
        except Exception as e:
            logger.error(f"❌ Error in unusual volume scan: {e}")
        
        return opportunities
    
    def _scan_news_mentions(self) -> List[RankedOpportunity]:
        """
        Scan for stocks mentioned in recent news.
        
        High priority - catalyst-driven opportunities.
        
        Uses Alpaca News API to find symbols with multiple recent mentions
        and significant news impact.
        """
        logger.debug("📰 Scanning news mentions...")
        opportunities = []
        
        try:
            # Get recent news from Alpaca - last 24 hours
            news_items = self.alpaca_client.get_news(
                symbols="*",  # All symbols
                start=datetime.now() - timedelta(hours=24),
                limit=100
            )
            
            logger.debug(f"   Retrieved {len(news_items)} news items")
            
            # Extract symbols with significant mentions
            symbol_mentions: Dict[str, List[Dict]] = {}
            
            for news in news_items:
                symbols = news.get('symbols', [])
                headline = news.get('headline', '').lower()
                summary = news.get('summary', '').lower()
                
                # Simple sentiment analysis (basic keywords)
                sentiment = 0
                if any(word in headline + summary for word in ['surge', 'beat', 'upgrade', 'strong', 'bullish', 'rally']):
                    sentiment = 1
                elif any(word in headline + summary for word in ['drop', 'miss', 'downgrade', 'weak', 'bearish', 'crash']):
                    sentiment = -1
                
                for symbol in symbols:
                    if symbol not in symbol_mentions:
                        symbol_mentions[symbol] = []
                    symbol_mentions[symbol].append({
                        **news,
                        'sentiment': sentiment
                    })
            
            # Create opportunities for symbols with multiple mentions
            for symbol, mentions in symbol_mentions.items():
                if len(mentions) >= 2:  # At least 2 mentions
                    # Calculate average sentiment
                    sentiments = [m.get('sentiment', 0) for m in mentions]
                    avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
                    
                    # Get headlines for context
                    headlines = [m.get('headline', '')[:100] for m in mentions[:3]]
                    
                    opp = RankedOpportunity(
                        symbol=symbol,
                        discovery_source=DiscoverySource.NEWS_MENTIONS,
                        discovery_timestamp=datetime.now(),
                        catalyst_strength=min(len(mentions) * 15, 100),  # More mentions = stronger
                        news_sentiment=avg_sentiment,
                        urgency=8 if abs(avg_sentiment) > 0.5 else 5,  # High urgency for strong sentiment
                        discovery_data={
                            'num_mentions': len(mentions),
                            'headlines': headlines,
                            'avg_sentiment': avg_sentiment,
                        }
                    )
                    opportunities.append(opp)
                    logger.debug(f"   📰 {symbol}: {len(mentions)} mentions, sentiment={avg_sentiment:.2f}")
            
            logger.debug(f"   ✅ Found {len(opportunities)} symbols in news")
            
        except Exception as e:
            logger.error(f"❌ Error in news scan: {e}")
        
        return opportunities
    
    def _scan_sector_movers(self) -> List[RankedOpportunity]:
        """
        Scan for top movers within each sector.
        
        Medium priority - trend following opportunities.
        
        Strategy: Check sector ETFs for strong moves, then find stocks
        mentioned in news from those sectors.
        """
        logger.debug("📈 Scanning sector movers...")
        opportunities = []
        
        try:
            # Major sector ETFs
            sector_etfs = {
                'XLK': 'Technology',
                'XLF': 'Financials',
                'XLV': 'Healthcare',
                'XLE': 'Energy',
                'XLI': 'Industrials',
                'XLY': 'Consumer Discretionary',
                'XLP': 'Consumer Staples',
                'XLU': 'Utilities',
                'XLRE': 'Real Estate'
            }
            
            moving_sectors = []
            
            # Check which sectors are moving
            for etf, sector_name in sector_etfs.items():
                try:
                    bars = self.alpaca_client.get_bars(etf, timeframe="1Day", limit=5)
                    if bars is not None and len(bars) > 1:
                        # Calculate % change over last day
                        close_now = bars['close'].iloc[-1]
                        close_prev = bars['close'].iloc[-2]
                        pct_change = ((close_now - close_prev) / close_prev) * 100
                        
                        if abs(pct_change) > 1.5:  # Sector moving >1.5%
                            moving_sectors.append((sector_name, pct_change))
                            logger.debug(f"   📊 {sector_name} ({etf}): {pct_change:+.2f}%")
                
                except Exception as e:
                    logger.debug(f"   ⚠️  Could not check {etf}: {e}")
            
            # For moving sectors, find stocks in news from those sectors
            # This is a simplified implementation - in production would use
            # more sophisticated sector classification
            
            logger.debug(f"   ✅ Found {len(moving_sectors)} moving sectors")
            
        except Exception as e:
            logger.error(f"❌ Error in sector scan: {e}")
        
        return opportunities
    
    def _scan_earnings_calendar(self) -> List[RankedOpportunity]:
        """
        Scan for upcoming earnings reports.
        
        Medium priority - event-driven opportunities.
        """
        logger.debug("📅 Scanning earnings calendar...")
        opportunities = []
        
        try:
            # Get earnings calendar from Alpaca
            # calendar = self.alpaca_client.get_calendar(start=today, end=next_week)
            
            # Placeholder implementation
            logger.debug("⚠️ Earnings calendar scanner not fully implemented yet")
            
        except Exception as e:
            logger.error(f"❌ Error in earnings scan: {e}")
        
        return opportunities
    
    def _scan_gap_opportunities(self) -> List[RankedOpportunity]:
        """
        Scan for pre-market gaps (> 3% vs previous close).
        
        High priority during pre-market hours.
        
        Strategy: Get symbols from recent news, check if they have significant
        price gap from previous day's close.
        """
        logger.debug("🌅 Scanning pre-market gaps...")
        opportunities = []
        
        try:
            # Get symbols that might have gaps (from overnight news)
            news_items = self.alpaca_client.get_news(
                symbols="*",
                start=datetime.now() - timedelta(hours=16),  # Since market close
                limit=50
            )
            
            # Extract unique symbols
            candidate_symbols = set()
            for news in news_items:
                symbols = news.get('symbols', [])
                candidate_symbols.update(symbols)
            
            logger.debug(f"   Checking {len(candidate_symbols)} symbols for gaps")
            
            # Check each symbol for gap
            for symbol in list(candidate_symbols)[:15]:  # Limit to avoid API limits
                try:
                    # Get yesterday's close and current pre-market price
                    bars = self.alpaca_client.get_bars(symbol, "1Day", limit=2)
                    
                    if bars is not None and len(bars) >= 2:
                        prev_close = bars['close'].iloc[-2]
                        
                        # Try to get latest quote (may be pre-market or yesterday's close)
                        current_bars = self.alpaca_client.get_bars(symbol, "1Min", limit=1)
                        if current_bars is not None and len(current_bars) > 0:
                            current_price = current_bars['close'].iloc[-1]
                            
                            # Calculate gap percentage
                            gap_pct = ((current_price - prev_close) / prev_close) * 100
                            
                            if abs(gap_pct) > 3.0:  # Significant gap
                                opp = RankedOpportunity(
                                    symbol=symbol,
                                    discovery_source=DiscoverySource.GAP_SCANNER,
                                    discovery_timestamp=datetime.now(),
                                    catalyst_strength=min(abs(gap_pct) * 10, 100),
                                    urgency=9,  # High urgency for gaps
                                    discovery_data={
                                        'prev_close': float(prev_close),
                                        'current_price': float(current_price),
                                        'gap_pct': float(gap_pct),
                                        'gap_direction': 'up' if gap_pct > 0 else 'down'
                                    }
                                )
                                opportunities.append(opp)
                                logger.debug(f"   🌅 {symbol}: {gap_pct:+.1f}% gap")
                
                except Exception as e:
                    logger.debug(f"   ⚠️ Could not check gap for {symbol}: {e}")
                    continue
            
            logger.debug(f"   ✅ Found {len(opportunities)} gap opportunities")
            
        except Exception as e:
            logger.error(f"❌ Error in gap scan: {e}")
        
        return opportunities
    
    def _aggregate_sources(self, sources: List[List[RankedOpportunity]]) -> List[RankedOpportunity]:
        """
        Aggregate opportunities from multiple sources and deduplicate.
        
        If same symbol appears in multiple sources, merge the data.
        """
        symbol_map: Dict[str, RankedOpportunity] = {}
        
        for source_list in sources:
            for opp in source_list:
                if opp.symbol in symbol_map:
                    # Symbol already found - merge data
                    existing = symbol_map[opp.symbol]
                    
                    # Combine scores (average)
                    existing.catalyst_strength = (existing.catalyst_strength + opp.catalyst_strength) / 2
                    existing.news_sentiment = (existing.news_sentiment + opp.news_sentiment) / 2
                    
                    # Merge discovery data
                    existing.discovery_data['additional_sources'] = \
                        existing.discovery_data.get('additional_sources', [])
                    existing.discovery_data['additional_sources'].append(opp.discovery_source.value)
                    
                    logger.debug(f"🔗 Merged {opp.symbol} from {opp.discovery_source.value}")
                else:
                    symbol_map[opp.symbol] = opp
        
        return list(symbol_map.values())
    
    def _rank_opportunities(self, opportunities: List[RankedOpportunity]) -> List[RankedOpportunity]:
        """
        Rank opportunities by quality score.
        
        Factors:
        - Liquidity (can we trade it?)
        - Catalyst strength (why is it moving?)
        - Technical setup (is it actionable?)
        - News sentiment
        - Volume anomaly
        - Sector correlation
        """
        for opp in opportunities:
            # Calculate individual scores
            opp.liquidity_score = self._calculate_liquidity_score(opp.symbol)
            opp.technical_setup_score = self._calculate_technical_score(opp.symbol)
            opp.volume_anomaly = self._calculate_volume_anomaly(opp.symbol)
            opp.sector_correlation = self._calculate_sector_correlation(opp.symbol)
            
            # Calculate overall quality (weighted average)
            opp.quality_score = (
                opp.liquidity_score * 0.25 +
                opp.catalyst_strength * 0.25 +
                opp.technical_setup_score * 0.20 +
                abs(opp.news_sentiment) * 50 * 0.15 +  # Convert -1/+1 to 0-50 scale
                min(opp.volume_anomaly * 20, 100) * 0.10 +  # Cap at 100
                opp.sector_correlation * 0.05
            )
            
            # Calculate urgency (1-10)
            opp.urgency = self._calculate_urgency(opp)
            
            # Suggest strategy
            opp.expected_strategy = self._suggest_strategy(opp)
        
        # Sort by urgency (high first), then quality
        return sorted(opportunities, key=lambda x: (x.urgency, x.quality_score), reverse=True)
    
    def _calculate_liquidity_score(self, symbol: str) -> float:
        """
        Calculate liquidity score (0-100).
        
        Based on average volume and bid-ask spread.
        """
        try:
            # Get recent bars to check volume
            # bars = self.alpaca_client.get_bars(symbol, timeframe='1Day', limit=20)
            # avg_volume = calculate_avg_volume(bars)
            
            # Placeholder: return medium score
            return 70.0
            
        except Exception as e:
            logger.debug(f"⚠️ Could not calculate liquidity for {symbol}: {e}")
            return 50.0  # Default medium score
    
    def _calculate_technical_score(self, symbol: str) -> float:
        """
        Calculate technical setup score (0-100).
        
        Based on price action, support/resistance, momentum.
        """
        try:
            # Placeholder: would analyze actual technical indicators
            return 60.0
            
        except Exception as e:
            logger.debug(f"⚠️ Could not calculate technicals for {symbol}: {e}")
            return 50.0
    
    def _calculate_volume_anomaly(self, symbol: str) -> float:
        """
        Calculate volume anomaly (ratio of current to average).
        
        Returns multiplier (e.g., 2.5 means 2.5x normal volume).
        """
        try:
            # Placeholder: would calculate actual volume ratio
            return 1.0  # Normal volume
            
        except Exception as e:
            logger.debug(f"⚠️ Could not calculate volume anomaly for {symbol}: {e}")
            return 1.0
    
    def _calculate_sector_correlation(self, symbol: str) -> float:
        """
        Calculate sector correlation (0-100).
        
        Higher = more correlated with sector (group move).
        Lower = more isolated (symbol-specific).
        """
        try:
            # Placeholder: would analyze sector correlation
            return 50.0  # Medium correlation
            
        except Exception as e:
            logger.debug(f"⚠️ Could not calculate sector correlation for {symbol}: {e}")
            return 50.0
    
    def _calculate_urgency(self, opp: RankedOpportunity) -> int:
        """
        Calculate urgency (1-10).
        
        Higher urgency = need to act sooner.
        """
        urgency = 5  # Default medium
        
        # Urgent if strong catalyst
        if opp.catalyst_strength > 80:
            urgency += 2
        
        # Urgent if high volume anomaly
        if opp.volume_anomaly > 3.0:
            urgency += 2
        
        # Urgent if strong sentiment
        if abs(opp.news_sentiment) > 0.7:
            urgency += 1
        
        # News mentions are more urgent than calendar events
        if opp.discovery_source == DiscoverySource.NEWS_MENTIONS:
            urgency += 1
        
        return min(urgency, 10)
    
    def _suggest_strategy(self, opp: RankedOpportunity) -> str:
        """
        Suggest initial strategy type based on discovery characteristics.
        
        LLM will make final decision, this is just a suggestion.
        """
        # High volume + news = momentum
        if opp.volume_anomaly > 2.0 and opp.catalyst_strength > 70:
            return "momentum_breakout"
        
        # Earnings-related = earnings run
        if opp.discovery_source == DiscoverySource.EARNINGS_CALENDAR:
            return "earnings_run"
        
        # Sector move = trend following
        if opp.discovery_source == DiscoverySource.SECTOR_MOVERS:
            return "sector_trend"
        
        # Default: let LLM decide
        return "custom"
    
    def _calculate_quality_threshold(self, ranked: List[RankedOpportunity]) -> float:
        """
        Calculate dynamic quality threshold.
        
        NO FIXED UNIVERSE SIZE - take as many as meet quality bar.
        """
        if not ranked:
            return 80.0  # High bar if nothing found
        
        scores = [opp.quality_score for opp in ranked]
        
        # Statistical threshold: top quartile (75th percentile)
        if len(scores) >= 4:
            sorted_scores = sorted(scores)
            q3_index = 3 * len(sorted_scores) // 4
            q3 = sorted_scores[q3_index]
            return max(q3, 60.0)  # At least 60/100 quality
        else:
            # Small sample: use medium bar
            return 70.0
    
    def get_morning_briefing(self) -> Dict[str, Any]:
        """
        Generate morning briefing of discovered opportunities.
        
        Called at market open to show what was found overnight.
        """
        if not self.discovered_opportunities:
            return {
                'summary': 'No high-quality opportunities discovered overnight',
                'count': 0,
                'opportunities': []
            }
        
        # Group by strategy
        by_strategy = {}
        for opp in self.discovered_opportunities:
            strategy = opp.expected_strategy
            if strategy not in by_strategy:
                by_strategy[strategy] = []
            by_strategy[strategy].append(opp)
        
        # Get top opportunities
        top_opportunities = self.discovered_opportunities[:10]  # Top 10
        
        return {
            'summary': f'Found {len(self.discovered_opportunities)} opportunities overnight',
            'count': len(self.discovered_opportunities),
            'by_strategy': {
                strategy: len(opps) for strategy, opps in by_strategy.items()
            },
            'top_10': [
                {
                    'symbol': opp.symbol,
                    'quality': opp.quality_score,
                    'urgency': opp.urgency,
                    'strategy': opp.expected_strategy,
                    'catalyst': opp.discovery_data.get('headlines', [''])[0] if opp.discovery_data.get('headlines') else 'N/A'
                }
                for opp in top_opportunities
            ],
            'discovery_sources': {
                source.value: sum(1 for opp in self.discovered_opportunities if opp.discovery_source == source)
                for source in DiscoverySource
            }
        }
