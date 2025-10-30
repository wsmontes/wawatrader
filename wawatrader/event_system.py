"""
Event Trigger System
====================
Event-driven architecture for triggering trading analysis based on market events
rather than arbitrary time intervals.

This module provides:
- Event types (price alerts, news, volume spikes, etc.)
- Event queue with FIFO + priority ordering
- Event deduplication
- Event trigger monitoring
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from enum import Enum
import json
from collections import deque
from loguru import logger


class EventType(Enum):
    """Types of events that trigger trading analysis"""
    
    # Price-based triggers
    BREAKOUT_UPSIDE = "breakout_upside"           # Price > resistance
    BREAKDOWN_DOWNSIDE = "breakdown_downside"      # Price < support
    TARGET_HIT = "target_hit"                      # Reached profit target
    STOP_LOSS_HIT = "stop_loss_hit"               # Hit invalidation price
    PRICE_ALERT = "price_alert"                    # Custom price alert triggered
    
    # Volume-based triggers
    VOLUME_SPIKE = "volume_spike"                  # Volume > 3x average
    VOLUME_DRYING_UP = "volume_drying_up"         # Volume < 0.3x average
    UNUSUAL_ACTIVITY = "unusual_activity"          # Unusual trading pattern
    
    # News-based triggers
    BREAKING_NEWS = "breaking_news"                # Real-time news alert
    EARNINGS_RELEASE = "earnings_release"          # Company reported earnings
    ANALYST_RATING_CHANGE = "analyst_rating"       # Upgrade/downgrade
    NEWS_SENTIMENT_SHIFT = "news_sentiment_shift"  # Major sentiment change
    
    # Time-based (minimal use)
    MARKET_OPEN = "market_open"                    # 9:30 AM ET
    MARKET_CLOSE_WARNING = "market_close_warning"  # 3:50 PM ET
    PRE_MARKET_OPEN = "pre_market_open"           # 4:00 AM ET
    
    # Portfolio-level triggers
    PORTFOLIO_HEAT_HIGH = "portfolio_heat_high"    # Risk concentration warning
    MARGIN_WARNING = "margin_warning"              # Buying power low
    DAILY_LOSS_LIMIT = "daily_loss_limit"         # Emergency stop triggered
    POSITION_SIZE_WARNING = "position_size_warning" # Single position too large
    
    # Sector/Market triggers
    SECTOR_MOVE = "sector_move"                    # Sector moving significantly
    MARKET_REVERSAL = "market_reversal"           # SPY trend reversal
    VIX_SPIKE = "vix_spike"                        # Volatility spike
    
    # Discovery triggers
    NEW_OPPORTUNITY = "new_opportunity"            # Discovery engine found symbol
    GAP_DETECTED = "gap_detected"                  # Pre-market gap
    

class EventPriority:
    """Priority levels for event queue ordering"""
    EMERGENCY = 10      # Daily loss limit, margin call
    CRITICAL = 9        # Stop loss hit
    URGENT = 8          # Breakout/breakdown
    HIGH = 7            # Breaking news, earnings
    MEDIUM_HIGH = 6     # Target hit
    MEDIUM = 5          # Volume spike
    MEDIUM_LOW = 4      # Sector move
    LOW = 3             # Rating change
    SCHEDULED = 2       # Market open/close
    BACKGROUND = 1      # New opportunity discovered


@dataclass
class Event:
    """
    Single event in the queue.
    
    Events trigger trading analysis instead of arbitrary time intervals.
    """
    id: str
    timestamp: datetime
    event_type: EventType
    symbol: str
    data: Dict[str, Any]
    priority: int = EventPriority.MEDIUM
    source: str = "unknown"  # Which monitor generated this
    
    def __lt__(self, other):
        """For priority queue sorting"""
        # Higher priority first, then FIFO within same priority
        if self.priority != other.priority:
            return self.priority > other.priority
        return self.timestamp < other.timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type.value,
            'symbol': self.symbol,
            'data': self.data,
            'priority': self.priority,
            'source': self.source,
        }


class EventQueue:
    """
    FIFO queue with priority sorting and deduplication.
    
    Events are processed in priority order, with FIFO within same priority.
    Duplicate events (same symbol + type within time window) are deduplicated.
    """
    
    def __init__(self, dedup_window_minutes: int = 5):
        self.queue: deque[Event] = deque()
        self.processed_ids: Set[str] = set()
        self.dedup_window = timedelta(minutes=dedup_window_minutes)
        self._event_count = 0
    
    def add_event(self, event: Event) -> bool:
        """
        Add event with deduplication.
        
        Returns True if event was added, False if duplicate.
        """
        # Generate deduplication signature
        # Same symbol + event type within 5-minute window = duplicate
        time_bucket = int(event.timestamp.timestamp() / (self.dedup_window.total_seconds()))
        event_signature = f"{event.symbol}_{event.event_type.value}_{time_bucket}"
        
        if event_signature in self.processed_ids:
            logger.debug(f"⏭️ Skipping duplicate event: {event.event_type.value} {event.symbol}")
            return False
        
        # Add to queue
        self.queue.append(event)
        self.processed_ids.add(event_signature)
        self._event_count += 1
        
        # Sort queue by priority
        self._sort_queue()
        
        logger.debug(
            f"➕ Added event: {event.event_type.value} {event.symbol} "
            f"(priority={event.priority}, queue_size={len(self.queue)})"
        )
        
        return True
    
    def _sort_queue(self):
        """Sort queue by priority (high first), then FIFO within same priority"""
        self.queue = deque(sorted(self.queue, key=lambda e: (-e.priority, e.timestamp)))
    
    def get_next_event(self) -> Optional[Event]:
        """
        Pop next event from queue (highest priority, FIFO within priority).
        
        Returns None if queue is empty.
        """
        if self.queue:
            return self.queue.popleft()
        return None
    
    def peek_next_event(self) -> Optional[Event]:
        """Peek at next event without removing it"""
        if self.queue:
            return self.queue[0]
        return None
    
    def get_pending_count(self) -> int:
        """Get number of events waiting in queue"""
        return len(self.queue)
    
    def get_events_for_symbol(self, symbol: str) -> List[Event]:
        """Get all pending events for a specific symbol"""
        return [e for e in self.queue if e.symbol == symbol]
    
    def clear_events_for_symbol(self, symbol: str):
        """Remove all pending events for a symbol (e.g., after position closed)"""
        before_count = len(self.queue)
        self.queue = deque([e for e in self.queue if e.symbol != symbol])
        after_count = len(self.queue)
        
        if before_count != after_count:
            logger.info(f"🗑️ Cleared {before_count - after_count} events for {symbol}")
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status for monitoring"""
        priority_breakdown = {}
        symbol_breakdown = {}
        
        for event in self.queue:
            # Count by priority
            priority_breakdown[event.priority] = priority_breakdown.get(event.priority, 0) + 1
            
            # Count by symbol
            symbol_breakdown[event.symbol] = symbol_breakdown.get(event.symbol, 0) + 1
        
        return {
            'pending_count': len(self.queue),
            'total_processed': self._event_count,
            'priority_breakdown': priority_breakdown,
            'symbol_breakdown': symbol_breakdown,
            'next_event': self.peek_next_event().to_dict() if self.peek_next_event() else None,
        }
    
    def cleanup_old_dedup_signatures(self, older_than_hours: int = 24):
        """
        Clean up old deduplication signatures to prevent memory growth.
        
        Call periodically (e.g., once per day) to remove old entries.
        """
        # For now, just clear all (could be smarter with timestamps)
        before_count = len(self.processed_ids)
        self.processed_ids.clear()
        logger.info(f"🧹 Cleaned up {before_count} deduplication signatures")


class EventMonitor:
    """
    Base class for event monitors.
    
    Subclasses implement specific monitoring logic (price, news, volume, etc.)
    """
    
    def __init__(self, event_queue: EventQueue):
        self.event_queue = event_queue
        self.is_running = False
    
    async def start(self):
        """Start monitoring for events"""
        self.is_running = True
        logger.info(f"▶️ Started {self.__class__.__name__}")
    
    async def stop(self):
        """Stop monitoring"""
        self.is_running = False
        logger.info(f"⏸️ Stopped {self.__class__.__name__}")
    
    def create_event(
        self,
        event_type: EventType,
        symbol: str,
        data: Dict[str, Any],
        priority: int,
        source: str = None
    ) -> Event:
        """Helper to create a new event"""
        import uuid
        
        event = Event(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            event_type=event_type,
            symbol=symbol,
            data=data,
            priority=priority,
            source=source or self.__class__.__name__
        )
        
        return event


class PriceAlertMonitor(EventMonitor):
    """
    Monitor price levels and trigger events for breakouts, breakdowns, targets, stops.
    
    This replaces arbitrary time-based checks with price-driven triggers.
    """
    
    def __init__(self, event_queue: EventQueue):
        super().__init__(event_queue)
        self.price_alerts: Dict[str, List[Dict[str, Any]]] = {}  # symbol -> alerts
    
    def set_price_alert(
        self,
        symbol: str,
        alert_type: str,  # "above" | "below"
        price: float,
        event_type: EventType,
        priority: int,
        metadata: Dict[str, Any] = None
    ):
        """
        Set a price alert that triggers an event.
        
        Example: Set alert for breakout above $50.00
        """
        if symbol not in self.price_alerts:
            self.price_alerts[symbol] = []
        
        alert = {
            'alert_type': alert_type,
            'price': price,
            'event_type': event_type,
            'priority': priority,
            'metadata': metadata or {},
            'created_at': datetime.now(),
        }
        
        self.price_alerts[symbol].append(alert)
        
        logger.debug(
            f"🔔 Set price alert: {symbol} {alert_type} ${price:.2f} "
            f"→ {event_type.value}"
        )
    
    def check_price(self, symbol: str, current_price: float):
        """
        Check if current price triggered any alerts.
        
        Should be called when new price data arrives.
        """
        if symbol not in self.price_alerts:
            return
        
        triggered_alerts = []
        
        for alert in self.price_alerts[symbol]:
            should_trigger = False
            
            if alert['alert_type'] == 'above' and current_price > alert['price']:
                should_trigger = True
            elif alert['alert_type'] == 'below' and current_price < alert['price']:
                should_trigger = True
            
            if should_trigger:
                # Create event
                event = self.create_event(
                    event_type=alert['event_type'],
                    symbol=symbol,
                    data={
                        'current_price': current_price,
                        'alert_price': alert['price'],
                        'alert_type': alert['alert_type'],
                        **alert['metadata']
                    },
                    priority=alert['priority'],
                    source="PriceAlertMonitor"
                )
                
                self.event_queue.add_event(event)
                triggered_alerts.append(alert)
                
                logger.info(
                    f"🔔 Price alert triggered: {symbol} {alert['alert_type']} "
                    f"${alert['price']:.2f} (current: ${current_price:.2f})"
                )
        
        # Remove triggered alerts
        if triggered_alerts:
            self.price_alerts[symbol] = [
                a for a in self.price_alerts[symbol] 
                if a not in triggered_alerts
            ]
    
    def clear_alerts_for_symbol(self, symbol: str):
        """Remove all price alerts for a symbol"""
        if symbol in self.price_alerts:
            count = len(self.price_alerts[symbol])
            del self.price_alerts[symbol]
            logger.debug(f"🗑️ Cleared {count} price alerts for {symbol}")


class VolumeMonitor(EventMonitor):
    """
    Monitor volume patterns and trigger events for spikes, drying up, unusual activity.
    """
    
    def __init__(self, event_queue: EventQueue):
        super().__init__(event_queue)
        self.volume_baselines: Dict[str, float] = {}  # symbol -> avg volume
    
    def set_volume_baseline(self, symbol: str, avg_volume: float):
        """Set baseline average volume for a symbol"""
        self.volume_baselines[symbol] = avg_volume
    
    def check_volume(self, symbol: str, current_volume: float):
        """Check if current volume is unusual"""
        if symbol not in self.volume_baselines:
            return
        
        avg = self.volume_baselines[symbol]
        ratio = current_volume / avg if avg > 0 else 1.0
        
        # Volume spike: > 3x average
        if ratio > 3.0:
            event = self.create_event(
                event_type=EventType.VOLUME_SPIKE,
                symbol=symbol,
                data={
                    'current_volume': current_volume,
                    'average_volume': avg,
                    'ratio': ratio,
                },
                priority=EventPriority.MEDIUM,
                source="VolumeMonitor"
            )
            self.event_queue.add_event(event)
            logger.info(f"📊 Volume spike: {symbol} {ratio:.1f}x average")
        
        # Volume drying up: < 0.3x average
        elif ratio < 0.3:
            event = self.create_event(
                event_type=EventType.VOLUME_DRYING_UP,
                symbol=symbol,
                data={
                    'current_volume': current_volume,
                    'average_volume': avg,
                    'ratio': ratio,
                },
                priority=EventPriority.MEDIUM,
                source="VolumeMonitor"
            )
            self.event_queue.add_event(event)
            logger.info(f"📉 Volume drying up: {symbol} {ratio:.1f}x average")


class NewsMonitor(EventMonitor):
    """
    Monitor news and trigger events for breaking news, earnings, analyst ratings.
    """
    
    def __init__(self, event_queue: EventQueue):
        super().__init__(event_queue)
        self.last_news_check: Dict[str, datetime] = {}
    
    def process_news_item(self, symbol: str, news: Dict[str, Any]):
        """
        Process a news item and create event if significant.
        
        news should contain: headline, sentiment, category, timestamp
        """
        category = news.get('category', 'general')
        sentiment = news.get('sentiment', 0.0)
        
        # Determine event type and priority based on category
        if 'earnings' in category.lower() or 'earnings' in news.get('headline', '').lower():
            event_type = EventType.EARNINGS_RELEASE
            priority = EventPriority.HIGH
        elif 'rating' in category.lower() or 'upgrade' in news.get('headline', '').lower():
            event_type = EventType.ANALYST_RATING_CHANGE
            priority = EventPriority.LOW
        elif abs(sentiment) > 0.7:  # Strong sentiment
            event_type = EventType.NEWS_SENTIMENT_SHIFT
            priority = EventPriority.MEDIUM_HIGH
        else:
            event_type = EventType.BREAKING_NEWS
            priority = EventPriority.HIGH
        
        event = self.create_event(
            event_type=event_type,
            symbol=symbol,
            data={
                'headline': news.get('headline', ''),
                'sentiment': sentiment,
                'category': category,
                'news_timestamp': news.get('timestamp', datetime.now().isoformat()),
            },
            priority=priority,
            source="NewsMonitor"
        )
        
        self.event_queue.add_event(event)
        logger.info(f"📰 News event: {symbol} - {news.get('headline', '')[:50]}...")


# Convenience functions
_event_queue = None

def get_event_queue() -> EventQueue:
    """Get singleton event queue instance"""
    global _event_queue
    if _event_queue is None:
        _event_queue = EventQueue()
    return _event_queue
