"""
Timeline Replay Engine

Provides event-driven replay of historical trading sessions from JSONL logs.
Allows step-by-step inspection of trading decisions, market data, and account states.

Inspired by:
- Backtrader's event-driven replay architecture
- VectorBT's interactive timeline controls
- LiuAlgoTrader's live/backtest mode switching

Author: WawaTrader Team
"""

from typing import Dict, List, Optional, Any, Generator, Tuple
from datetime import datetime
from pathlib import Path
import json
from dataclasses import dataclass
from enum import Enum
from loguru import logger
import pandas as pd


class ReplayState(Enum):
    """Replay engine state"""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    FINISHED = "finished"


class EventType(Enum):
    """Types of events in timeline"""
    DECISION = "decision"
    MARKET_DATA = "market_data"
    ACCOUNT_SNAPSHOT = "account_snapshot"
    ORDER_EXECUTION = "order_execution"
    POSITION_SNAPSHOT = "position_snapshot"
    LLM_CONVERSATION = "llm_conversation"


@dataclass
class TimelineEvent:
    """Single event in the timeline"""
    timestamp: datetime
    event_type: EventType
    data: Dict[str, Any]
    
    def __lt__(self, other):
        """Allow sorting by timestamp"""
        return self.timestamp < other.timestamp


class ReplayEngine:
    """
    Event-driven replay engine for historical trading sessions.
    
    Loads JSONL logs and provides controlled playback with pause/play/speed controls.
    """
    
    def __init__(self, log_dir: Path):
        """
        Initialize replay engine
        
        Args:
            log_dir: Directory containing JSONL log files
        """
        self.log_dir = Path(log_dir)
        self.timeline: List[TimelineEvent] = []
        self.current_index: int = 0
        self.state: ReplayState = ReplayState.STOPPED
        self.speed: float = 1.0  # Playback speed multiplier
        
        # Time range
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.current_time: Optional[datetime] = None
        
        logger.info(f"ReplayEngine initialized with log_dir: {log_dir}")
    
    def load_logs(self) -> bool:
        """
        Load all JSONL logs into timeline
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Loading JSONL logs into timeline...")
            
            # Define log files to load
            log_files = {
                'decisions.jsonl': EventType.DECISION,
                'market_data.jsonl': EventType.MARKET_DATA,
                'account_snapshots.jsonl': EventType.ACCOUNT_SNAPSHOT,
                'order_executions.jsonl': EventType.ORDER_EXECUTION,
                'position_snapshots.jsonl': EventType.POSITION_SNAPSHOT,
                'llm_conversations.jsonl': EventType.LLM_CONVERSATION,
            }
            
            total_events = 0
            
            for filename, event_type in log_files.items():
                filepath = self.log_dir / filename
                
                if not filepath.exists():
                    logger.warning(f"Log file not found: {filepath}")
                    continue
                
                # Load events from file
                events_loaded = self._load_jsonl_file(filepath, event_type)
                total_events += events_loaded
                logger.info(f"  Loaded {events_loaded} events from {filename}")
            
            # Sort timeline by timestamp
            self.timeline.sort()
            
            # Set time range
            if self.timeline:
                self.start_time = self.timeline[0].timestamp
                self.end_time = self.timeline[-1].timestamp
                self.current_time = self.start_time
                
                logger.info(f"✅ Timeline loaded: {total_events} events")
                logger.info(f"   Time range: {self.start_time} to {self.end_time}")
                logger.info(f"   Duration: {self.end_time - self.start_time}")
                
                return True
            else:
                logger.error("No events loaded from logs")
                return False
                
        except Exception as e:
            logger.error(f"Error loading logs: {e}")
            return False
    
    def _load_jsonl_file(self, filepath: Path, event_type: EventType) -> int:
        """
        Load events from a JSONL file
        
        Args:
            filepath: Path to JSONL file
            event_type: Type of events in this file
            
        Returns:
            Number of events loaded
        """
        count = 0
        
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            
                            # Extract timestamp (varies by log type)
                            timestamp_str = data.get('timestamp')
                            if not timestamp_str:
                                continue
                            
                            # Parse timestamp
                            timestamp = pd.to_datetime(timestamp_str)
                            
                            # Create event
                            event = TimelineEvent(
                                timestamp=timestamp,
                                event_type=event_type,
                                data=data
                            )
                            
                            self.timeline.append(event)
                            count += 1
                            
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse line in {filepath}: {e}")
                            continue
                            
        except Exception as e:
            logger.error(f"Error reading {filepath}: {e}")
        
        return count
    
    def seek_to_time(self, target_time: datetime) -> bool:
        """
        Seek to specific timestamp in timeline
        
        Args:
            target_time: Target timestamp
            
        Returns:
            True if successful
        """
        if not self.timeline:
            return False
        
        # Binary search for closest event
        left, right = 0, len(self.timeline) - 1
        
        while left <= right:
            mid = (left + right) // 2
            
            if self.timeline[mid].timestamp <= target_time:
                left = mid + 1
            else:
                right = mid - 1
        
        # Set to closest event before or at target time
        self.current_index = max(0, right)
        self.current_time = self.timeline[self.current_index].timestamp
        
        logger.info(f"Seeked to {self.current_time} (index {self.current_index})")
        return True
    
    def seek_to_index(self, index: int) -> bool:
        """
        Seek to specific index in timeline
        
        Args:
            index: Timeline index
            
        Returns:
            True if successful
        """
        if 0 <= index < len(self.timeline):
            self.current_index = index
            self.current_time = self.timeline[index].timestamp
            logger.debug(f"Seeked to index {index}: {self.current_time}")
            return True
        return False
    
    def get_current_event(self) -> Optional[TimelineEvent]:
        """
        Get current event
        
        Returns:
            Current TimelineEvent or None
        """
        if 0 <= self.current_index < len(self.timeline):
            return self.timeline[self.current_index]
        return None
    
    def get_events_at_time(self, timestamp: datetime) -> List[TimelineEvent]:
        """
        Get all events at specific timestamp
        
        Args:
            timestamp: Target timestamp
            
        Returns:
            List of events at that timestamp
        """
        return [
            event for event in self.timeline
            if event.timestamp == timestamp
        ]
    
    def get_events_in_range(
        self, 
        start: datetime, 
        end: datetime,
        event_types: Optional[List[EventType]] = None
    ) -> List[TimelineEvent]:
        """
        Get events in time range
        
        Args:
            start: Start timestamp
            end: End timestamp
            event_types: Optional filter by event types
            
        Returns:
            List of events in range
        """
        events = [
            event for event in self.timeline
            if start <= event.timestamp <= end
        ]
        
        if event_types:
            events = [e for e in events if e.event_type in event_types]
        
        return events
    
    def play(self) -> bool:
        """
        Start playback
        
        Returns:
            True if started successfully
        """
        if not self.timeline:
            logger.warning("Cannot play: timeline is empty")
            return False
        
        if self.state == ReplayState.FINISHED:
            # Restart from beginning
            self.current_index = 0
            self.current_time = self.start_time
        
        self.state = ReplayState.PLAYING
        logger.info(f"▶️  Playback started at {self.current_time} (speed: {self.speed}x)")
        return True
    
    def pause(self) -> bool:
        """
        Pause playback
        
        Returns:
            True if paused successfully
        """
        if self.state == ReplayState.PLAYING:
            self.state = ReplayState.PAUSED
            logger.info(f"⏸️  Playback paused at {self.current_time}")
            return True
        return False
    
    def stop(self) -> bool:
        """
        Stop playback and reset to beginning
        
        Returns:
            True if stopped successfully
        """
        self.state = ReplayState.STOPPED
        self.current_index = 0
        self.current_time = self.start_time
        logger.info(f"⏹️  Playback stopped, reset to {self.start_time}")
        return True
    
    def next_event(self) -> Optional[TimelineEvent]:
        """
        Advance to next event
        
        Returns:
            Next TimelineEvent or None if at end
        """
        if self.current_index < len(self.timeline) - 1:
            self.current_index += 1
            self.current_time = self.timeline[self.current_index].timestamp
            
            # Check if finished
            if self.current_index >= len(self.timeline) - 1:
                self.state = ReplayState.FINISHED
                logger.info("🏁 Playback finished")
            
            return self.timeline[self.current_index]
        else:
            self.state = ReplayState.FINISHED
            return None
    
    def previous_event(self) -> Optional[TimelineEvent]:
        """
        Go back to previous event
        
        Returns:
            Previous TimelineEvent or None if at start
        """
        if self.current_index > 0:
            self.current_index -= 1
            self.current_time = self.timeline[self.current_index].timestamp
            
            if self.state == ReplayState.FINISHED:
                self.state = ReplayState.PAUSED
            
            return self.timeline[self.current_index]
        return None
    
    def set_speed(self, speed: float) -> bool:
        """
        Set playback speed
        
        Args:
            speed: Speed multiplier (1.0 = normal, 2.0 = 2x, etc.)
            
        Returns:
            True if successful
        """
        if speed > 0:
            self.speed = speed
            logger.info(f"⏩ Playback speed set to {speed}x")
            return True
        return False
    
    def get_progress(self) -> float:
        """
        Get playback progress as percentage
        
        Returns:
            Progress (0.0 to 1.0)
        """
        if not self.timeline:
            return 0.0
        return self.current_index / (len(self.timeline) - 1)
    
    def get_state_summary(self) -> Dict[str, Any]:
        """
        Get current state summary
        
        Returns:
            Dictionary with state information
        """
        return {
            'state': self.state.value,
            'current_time': self.current_time.isoformat() if self.current_time else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'current_index': self.current_index,
            'total_events': len(self.timeline),
            'progress': self.get_progress(),
            'speed': self.speed,
            'has_data': len(self.timeline) > 0
        }
    
    def get_event_markers(self) -> List[Dict[str, Any]]:
        """
        Get event markers for timeline visualization
        
        Returns:
            List of marker dictionaries with timestamp and event type
        """
        markers = []
        
        # Sample events for markers (to avoid overwhelming the UI)
        # Get decisions and order executions
        important_events = [
            e for e in self.timeline 
            if e.event_type in [EventType.DECISION, EventType.ORDER_EXECUTION]
        ]
        
        for event in important_events:
            marker_type = "🤖" if event.event_type == EventType.DECISION else "💰"
            
            markers.append({
                'timestamp': event.timestamp,
                'type': event.event_type.value,
                'label': f"{marker_type} {event.data.get('symbol', 'N/A')}",
                'data': event.data
            })
        
        return markers
    
    def iter_events(self, start_index: int = 0) -> Generator[TimelineEvent, None, None]:
        """
        Iterator over events from start_index
        
        Args:
            start_index: Starting index
            
        Yields:
            TimelineEvent objects
        """
        for i in range(start_index, len(self.timeline)):
            self.current_index = i
            self.current_time = self.timeline[i].timestamp
            yield self.timeline[i]


# Singleton instance
_replay_engine: Optional[ReplayEngine] = None


def get_replay_engine(log_dir: Optional[Path] = None) -> ReplayEngine:
    """
    Get or create singleton ReplayEngine instance
    
    Args:
        log_dir: Optional log directory (uses default if not provided)
        
    Returns:
        ReplayEngine instance
    """
    global _replay_engine
    
    if _replay_engine is None:
        from config.settings import settings
        log_dir = log_dir or settings.project_root / "logs"
        _replay_engine = ReplayEngine(log_dir)
    
    return _replay_engine


if __name__ == "__main__":
    """Test the replay engine"""
    from config.settings import settings
    
    logger.info("Testing ReplayEngine...")
    
    # Create engine
    engine = ReplayEngine(settings.project_root / "logs")
    
    # Load logs
    if engine.load_logs():
        logger.info(f"\n{'='*60}")
        logger.info("Timeline Statistics:")
        logger.info(f"{'='*60}")
        
        # Count by event type
        from collections import Counter
        event_counts = Counter(e.event_type for e in engine.timeline)
        
        for event_type, count in event_counts.items():
            logger.info(f"  {event_type.value}: {count}")
        
        logger.info(f"\n{'='*60}")
        logger.info("Sample Events:")
        logger.info(f"{'='*60}")
        
        # Show first 5 events
        for i, event in enumerate(engine.timeline[:5]):
            logger.info(f"\n[{i}] {event.timestamp} - {event.event_type.value}")
            if event.event_type == EventType.DECISION:
                logger.info(f"    Symbol: {event.data.get('symbol')}")
                logger.info(f"    Action: {event.data.get('action')}")
                logger.info(f"    Confidence: {event.data.get('confidence')}")
        
        logger.info(f"\n{'='*60}")
        logger.info("State Summary:")
        logger.info(f"{'='*60}")
        logger.info(engine.get_state_summary())
        
        logger.info(f"\n{'='*60}")
        logger.info("✅ ReplayEngine test complete!")
        logger.info(f"{'='*60}")
    else:
        logger.error("Failed to load logs")
