"""
News Timeline Manager for WawaTrader

Implements temporal intelligence for news analysis:
- Accumulates news throughout overnight period (4:00 PM - 2:00 AM)
- Synthesizes complete narrative (2:00 AM)
- Validates with pre-market action (6:00 AM)
- Generates actionable recommendations (9:30 AM)

This is NOT reactive analysis. It waits for the complete picture before deciding.

Author: WawaTrader Team
Created: October 24, 2025
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from loguru import logger
import json
from pathlib import Path

from wawatrader.timezone_utils import now_market, format_market_time
from wawatrader.alpaca_client import get_client
from config.settings import settings


@dataclass
class NewsArticle:
    """Single news article with metadata"""
    timestamp: datetime
    headline: str
    summary: str
    source: str
    url: str
    symbols: List[str]
    sentiment: Optional[str] = None  # Will be analyzed by LLM
    importance: Optional[int] = None  # 1-10, will be scored by LLM
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'headline': self.headline,
            'summary': self.summary,
            'source': self.source,
            'url': self.url,
            'symbols': self.symbols,
            'sentiment': self.sentiment,
            'importance': self.importance
        }
    
    @classmethod
    def from_alpaca(cls, article: Dict[str, Any]) -> 'NewsArticle':
        """Create from Alpaca API response"""
        return cls(
            timestamp=datetime.fromisoformat(article['created_at'].replace('Z', '+00:00')),
            headline=article.get('headline', ''),
            summary=article.get('summary', ''),
            source=article.get('source', 'Unknown'),
            url=article.get('url', ''),
            symbols=article.get('symbols', [])
        )


@dataclass
class NarrativeSynthesis:
    """LLM's understanding of the complete news narrative"""
    narrative: str  # Human-readable summary
    net_sentiment: str  # overall, cautiously_positive, neutral, cautiously_negative, negative
    confidence: float  # 0.0-1.0
    key_themes: List[str]  # ["earnings_beat", "guidance_raise", etc]
    contradictions: List[str]  # If any conflicting information
    recommendation: str  # BUY, SELL, HOLD, WAIT_FOR_CLARITY
    reasoning: str  # Why this recommendation
    synthesized_at: datetime = field(default_factory=lambda: now_market())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'narrative': self.narrative,
            'net_sentiment': self.net_sentiment,
            'confidence': self.confidence,
            'key_themes': self.key_themes,
            'contradictions': self.contradictions,
            'recommendation': self.recommendation,
            'reasoning': self.reasoning,
            'synthesized_at': self.synthesized_at.isoformat()
        }


@dataclass
class NewsTimeline:
    """Complete timeline of news for a symbol during overnight period"""
    symbol: str
    date: str  # YYYY-MM-DD
    narrative_type: Optional[str] = None  # EARNINGS, MERGER, REGULATORY, PRODUCT, SCANDAL, GENERAL
    events: List[NewsArticle] = field(default_factory=list)
    synthesis: Optional[NarrativeSynthesis] = None
    last_updated: datetime = field(default_factory=lambda: now_market())
    
    def add_article(self, article: NewsArticle) -> None:
        """Add article if not already present"""
        # Check for duplicates based on headline
        if not any(a.headline == article.headline for a in self.events):
            self.events.append(article)
            self.last_updated = now_market()
            logger.debug(f"📰 Added news to {self.symbol} timeline: {article.headline[:60]}...")
    
    def add_articles(self, articles: List[NewsArticle]) -> int:
        """Add multiple articles, return count of new articles"""
        count = 0
        for article in articles:
            before_count = len(self.events)
            self.add_article(article)
            if len(self.events) > before_count:
                count += 1
        return count
    
    def has_new_articles_since_synthesis(self) -> bool:
        """Check if new articles arrived after last synthesis"""
        if not self.synthesis:
            return len(self.events) > 0
        return any(a.timestamp > self.synthesis.synthesized_at for a in self.events)
    
    def get_articles_by_timeframe(self, start: datetime, end: datetime) -> List[NewsArticle]:
        """Get articles within a specific timeframe"""
        return [a for a in self.events if start <= a.timestamp <= end]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'symbol': self.symbol,
            'date': self.date,
            'narrative_type': self.narrative_type,
            'events': [e.to_dict() for e in self.events],
            'synthesis': self.synthesis.to_dict() if self.synthesis else None,
            'last_updated': self.last_updated.isoformat(),
            'event_count': len(self.events)
        }


class NewsTimelineManager:
    """
    Manages news timelines for overnight analysis.
    
    Strategy:
    1. ACCUMULATION (4 PM - 2 AM): Collect news every 30 min, no decisions
    2. SYNTHESIS (2 AM): LLM analyzes complete narrative
    3. VALIDATION (6 AM): Check for late-breaking news, validate with pre-market
    4. EXECUTION (9:30 AM): Generate final recommendations
    """
    
    def __init__(self, storage_dir: str = "trading_data/news_timelines"):
        """
        Initialize news timeline manager.
        
        Args:
            storage_dir: Directory to store timeline data
        """
        self.timelines: Dict[str, NewsTimeline] = {}
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.alpaca = get_client()
        
        logger.info("📰 NewsTimelineManager initialized")
        logger.info(f"   Storage: {self.storage_dir}")
    
    def start_overnight_collection(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Initialize timelines for overnight collection.
        Called at market close (4:00 PM ET).
        
        Args:
            symbols: List of symbols to track
            
        Returns:
            Status dict
        """
        market_now = now_market()
        today = market_now.strftime('%Y-%m-%d')
        
        logger.info(f"📰 Starting overnight news collection for {len(symbols)} symbols")
        logger.info(f"   Date: {today}")
        logger.info(f"   Time: {format_market_time(market_now)}")
        
        for symbol in symbols:
            self.timelines[symbol] = NewsTimeline(
                symbol=symbol,
                date=today
            )
        
        # Do initial collection
        initial_count = self.collect_news(symbols)
        
        logger.info(f"✅ Overnight collection started - {initial_count} initial articles")
        
        return {
            'status': 'success',
            'symbols': len(symbols),
            'initial_articles': initial_count,
            'started_at': market_now.isoformat()
        }
    
    def collect_news(self, symbols: Optional[List[str]] = None) -> int:
        """
        Collect news for symbols. Runs every 30 minutes during accumulation phase.
        
        Args:
            symbols: List of symbols, or None to use all tracked symbols
            
        Returns:
            Count of new articles added
        """
        if symbols is None:
            symbols = list(self.timelines.keys())
        
        if not symbols:
            logger.warning("No symbols to collect news for")
            return 0
        
        total_new = 0
        market_now = now_market()
        
        logger.debug(f"📰 Collecting news for {len(symbols)} symbols at {format_market_time(market_now)}")
        
        for symbol in symbols:
            try:
                # Get news from Alpaca (last 24 hours)
                # This ensures we catch after-hours news
                news_data = self.alpaca.get_news(symbol, limit=20)
                
                if not news_data:
                    continue
                
                # Convert to NewsArticle objects
                articles = [NewsArticle.from_alpaca(item) for item in news_data]
                
                # Add to timeline
                if symbol not in self.timelines:
                    # Create timeline if it doesn't exist
                    self.timelines[symbol] = NewsTimeline(
                        symbol=symbol,
                        date=market_now.strftime('%Y-%m-%d')
                    )
                
                new_count = self.timelines[symbol].add_articles(articles)
                total_new += new_count
                
                if new_count > 0:
                    logger.info(f"   {symbol}: +{new_count} new articles ({len(self.timelines[symbol].events)} total)")
                
            except Exception as e:
                logger.error(f"❌ Error collecting news for {symbol}: {e}")
                continue
        
        if total_new > 0:
            logger.info(f"✅ Collected {total_new} new articles across {len(symbols)} symbols")
        
        return total_new
    
    def get_timeline(self, symbol: str) -> Optional[NewsTimeline]:
        """Get timeline for a symbol"""
        return self.timelines.get(symbol)
    
    def get_all_timelines(self) -> Dict[str, NewsTimeline]:
        """Get all timelines"""
        return self.timelines.copy()
    
    def synthesize_narrative(self, symbol: str) -> Optional[NarrativeSynthesis]:
        """
        Synthesize complete narrative for a symbol using LLM.
        Called at 2:00 AM during SYNTHESIS phase.
        
        Args:
            symbol: Symbol to synthesize
            
        Returns:
            NarrativeSynthesis or None
        """
        timeline = self.timelines.get(symbol)
        if not timeline or not timeline.events:
            logger.warning(f"No timeline or events for {symbol}")
            return None
        
        logger.info(f"📊 Synthesizing narrative for {symbol}: {len(timeline.events)} articles")
        
        try:
            # Import LLM bridge
            from wawatrader.llm_bridge import LLMBridge
            
            # Create LLM bridge instance
            llm = LLMBridge()
            
            # Analyze news narrative
            synthesis_dict = llm.analyze_news_narrative(timeline)
            
            if not synthesis_dict:
                logger.error(f"LLM failed to synthesize narrative for {symbol}")
                return None
            
            # Convert to NarrativeSynthesis object
            synthesis = NarrativeSynthesis(
                narrative=synthesis_dict.get('narrative', ''),
                net_sentiment=synthesis_dict.get('net_sentiment', 'neutral'),
                confidence=float(synthesis_dict.get('confidence', 0.0)),
                key_themes=synthesis_dict.get('key_themes', []),
                contradictions=synthesis_dict.get('contradictions', []),
                recommendation=synthesis_dict.get('recommendation', 'HOLD'),
                reasoning=synthesis_dict.get('reasoning', '')
            )
            
            # Store in timeline
            timeline.synthesis = synthesis
            timeline.narrative_type = self._classify_narrative_type(synthesis_dict.get('key_themes', []))
            
            logger.info(f"✅ Narrative synthesized for {symbol}:")
            logger.info(f"   Type: {timeline.narrative_type}")
            logger.info(f"   Sentiment: {synthesis.net_sentiment}")
            logger.info(f"   Confidence: {synthesis.confidence:.2f}")
            logger.info(f"   Recommendation: {synthesis.recommendation}")
            
            return synthesis
            
        except Exception as e:
            logger.error(f"❌ Error synthesizing narrative for {symbol}: {e}")
            return None
    
    def _classify_narrative_type(self, themes: List[str]) -> str:
        """
        Classify narrative type based on themes.
        
        Args:
            themes: List of key themes from LLM analysis
            
        Returns:
            Narrative type: EARNINGS, MERGER, REGULATORY, PRODUCT, SCANDAL, GENERAL
        """
        themes_lower = [t.lower() for t in themes]
        
        if any(t in themes_lower for t in ['earnings', 'revenue', 'profit', 'eps']):
            return 'EARNINGS'
        elif any(t in themes_lower for t in ['merger', 'acquisition', 'buyout', 'takeover']):
            return 'MERGER'
        elif any(t in themes_lower for t in ['regulatory', 'regulation', 'legal', 'lawsuit', 'investigation']):
            return 'REGULATORY'
        elif any(t in themes_lower for t in ['product', 'launch', 'innovation', 'technology']):
            return 'PRODUCT'
        elif any(t in themes_lower for t in ['scandal', 'fraud', 'controversy', 'misconduct']):
            return 'SCANDAL'
        else:
            return 'GENERAL'
    
    def revise_if_needed(self, symbol: str) -> bool:
        """
        Check if narrative needs revision due to late-breaking news.
        Called at 6:00 AM during VALIDATION phase.
        
        Args:
            symbol: Symbol to check
            
        Returns:
            True if revision was performed
        """
        timeline = self.timelines.get(symbol)
        if not timeline:
            return False
        
        if timeline.has_new_articles_since_synthesis():
            logger.info(f"🔄 Late-breaking news for {symbol} - triggering re-synthesis")
            self.synthesize_narrative(symbol)
            return True
        
        return False
    
    def synthesize_all(self) -> Dict[str, bool]:
        """
        Synthesize narratives for all timelines.
        Called at 2:00 AM during SYNTHESIS phase.
        
        Returns:
            Dict mapping symbol to success/failure
        """
        logger.info(f"🤖 Starting narrative synthesis for {len(self.timelines)} symbols")
        
        results = {}
        success_count = 0
        
        for symbol in self.timelines.keys():
            try:
                synthesis = self.synthesize_narrative(symbol)
                results[symbol] = synthesis is not None
                if synthesis:
                    success_count += 1
            except Exception as e:
                logger.error(f"❌ Synthesis failed for {symbol}: {e}")
                results[symbol] = False
        
        logger.info(f"✅ Synthesis complete: {success_count}/{len(self.timelines)} successful")
        
        # Save timelines with synthesis
        self.save_timelines()
        
        return results
    
    def save_timelines(self) -> None:
        """Save all timelines to disk"""
        market_now = now_market()
        filename = f"news_timeline_{market_now.strftime('%Y%m%d')}.json"
        filepath = self.storage_dir / filename
        
        data = {
            'saved_at': market_now.isoformat(),
            'symbols': list(self.timelines.keys()),
            'timelines': {
                symbol: timeline.to_dict()
                for symbol, timeline in self.timelines.items()
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"💾 Saved news timelines to {filepath}")
    
    def load_timelines(self, date: str) -> bool:
        """
        Load timelines from disk.
        
        Args:
            date: Date string YYYYMMDD
            
        Returns:
            True if loaded successfully
        """
        filename = f"news_timeline_{date}.json"
        filepath = self.storage_dir / filename
        
        if not filepath.exists():
            logger.warning(f"No timeline file found: {filepath}")
            return False
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            logger.info(f"📂 Loaded news timelines from {filepath}")
            # TODO: Reconstruct NewsTimeline objects from dict
            # This is Phase 1 - just logging for now
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading timelines: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about current timelines"""
        market_now = now_market()
        
        stats = {
            'timestamp': market_now.isoformat(),
            'symbols_tracked': len(self.timelines),
            'total_articles': sum(len(t.events) for t in self.timelines.values()),
            'symbols_with_news': sum(1 for t in self.timelines.values() if len(t.events) > 0),
            'symbols_synthesized': sum(1 for t in self.timelines.values() if t.synthesis is not None),
            'by_symbol': {}
        }
        
        for symbol, timeline in self.timelines.items():
            stats['by_symbol'][symbol] = {
                'article_count': len(timeline.events),
                'has_synthesis': timeline.synthesis is not None,
                'last_updated': timeline.last_updated.isoformat()
            }
        
        return stats


# Singleton instance
_timeline_manager: Optional[NewsTimelineManager] = None


def get_timeline_manager() -> NewsTimelineManager:
    """Get or create timeline manager singleton"""
    global _timeline_manager
    if _timeline_manager is None:
        _timeline_manager = NewsTimelineManager()
    return _timeline_manager
