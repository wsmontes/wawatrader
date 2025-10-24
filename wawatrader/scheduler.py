"""
Intelligent Task Scheduler

Adaptive task scheduling based on market state to optimize resource usage
and focus efforts at the right times. Routes tasks based on market conditions
and time of day.

Author: WawaTrader Team
Created: October 2025
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
from loguru import logger
from wawatrader.market_state import MarketState, MarketStateDetector


class ScheduledTask:
    """Represents a scheduled task with timing and execution details"""
    
    def __init__(
        self,
        name: str,
        description: str,
        task_function: Optional[Callable] = None,
        interval_minutes: Optional[int] = None,
        scheduled_hours: Optional[list[int]] = None,
        market_states: Optional[list[MarketState]] = None,
    ):
        """
        Initialize a scheduled task.
        
        Args:
            name: Task identifier
            description: Human-readable description
            task_function: Callable to execute (optional)
            interval_minutes: Run every N minutes (mutually exclusive with scheduled_hours)
            scheduled_hours: Specific hours to run (mutually exclusive with interval_minutes)
            market_states: List of states where this task applies (None = all states)
        """
        self.name = name
        self.description = description
        self.task_function = task_function
        self.interval_minutes = interval_minutes
        self.scheduled_hours = scheduled_hours or []
        self.market_states = market_states or list(MarketState)
        self.last_run: Optional[datetime] = None
        self.run_count = 0
    
    def should_run(
        self,
        current_state: MarketState,
        current_time: datetime
    ) -> bool:
        """
        Check if task should run now.
        
        Args:
            current_state: Current market state
            current_time: Current datetime
            
        Returns:
            True if task should execute
        """
        # Check if current state is allowed
        if current_state not in self.market_states:
            return False
        
        # If scheduled for specific hours, check the hour
        if self.scheduled_hours:
            if current_time.hour not in self.scheduled_hours:
                return False
            # Only run once per hour
            if self.last_run and self.last_run.hour == current_time.hour:
                return False
            return True
        
        # If interval-based, check time since last run
        if self.interval_minutes:
            if not self.last_run:
                return True
            time_since = (current_time - self.last_run).total_seconds() / 60
            return time_since >= self.interval_minutes
        
        # No timing constraints, run once per state
        if self.last_run:
            # Reset if state changed or it's a new day
            last_run_date = self.last_run.date()
            current_date = current_time.date()
            if last_run_date != current_date:
                return True
        else:
            return True
        
        return False
    
    def mark_run(self) -> None:
        """Mark task as having been run"""
        self.last_run = datetime.now()
        self.run_count += 1


class IntelligentScheduler:
    """
    Adaptive scheduler that routes tasks based on market state.
    
    Manages task execution based on:
    - Current market state (trading, closing, analysis, sleep, prep)
    - Time-based scheduling (intervals or specific hours)
    - Task priority and dependencies
    """
    
    def __init__(self, alpaca_client=None):
        """
        Initialize intelligent scheduler.
        
        Args:
            alpaca_client: Optional AlpacaClient for market status
        """
        self.state_detector = MarketStateDetector(alpaca_client)
        self.tasks: Dict[str, ScheduledTask] = {}
        self._initialize_default_tasks()
        logger.info("🧠 Intelligent Scheduler initialized")
    
    def _initialize_default_tasks(self) -> None:
        """Set up default task schedule"""
        
        # Active Trading Tasks
        self.register_task(ScheduledTask(
            name="trading_cycle",
            description="Execute trading cycle (check prices, analyze, trade)",
            interval_minutes=5,
            market_states=[MarketState.ACTIVE_TRADING],
        ))
        
        self.register_task(ScheduledTask(
            name="quick_intelligence",
            description="Quick market intelligence check (sectors, indices)",
            interval_minutes=30,
            market_states=[MarketState.ACTIVE_TRADING],
        ))
        
        self.register_task(ScheduledTask(
            name="deep_analysis",
            description="Comprehensive market intelligence analysis",
            interval_minutes=120,  # Every 2 hours
            market_states=[MarketState.ACTIVE_TRADING],
        ))
        
        # Market Closing Tasks
        self.register_task(ScheduledTask(
            name="pre_close_assessment",
            description="Assess positions before market close",
            scheduled_hours=[15],  # 3 PM
            market_states=[MarketState.MARKET_CLOSING],
        ))
        
        self.register_task(ScheduledTask(
            name="daily_summary",
            description="Generate end-of-day summary and reports",
            scheduled_hours=[16],  # 4 PM
            market_states=[MarketState.MARKET_CLOSING],
        ))
        
        # Evening Analysis Tasks
        self.register_task(ScheduledTask(
            name="earnings_analysis",
            description="Deep dive into upcoming earnings calendar",
            scheduled_hours=[17],  # 5 PM
            market_states=[MarketState.EVENING_ANALYSIS],
        ))
        
        self.register_task(ScheduledTask(
            name="sector_deep_dive",
            description="Comprehensive sector rotation analysis",
            scheduled_hours=[19],  # 7 PM
            market_states=[MarketState.EVENING_ANALYSIS],
        ))
        
        self.register_task(ScheduledTask(
            name="international_markets",
            description="Review international markets and futures",
            scheduled_hours=[21],  # 9 PM
            market_states=[MarketState.EVENING_ANALYSIS],
        ))
        
        # Overnight Sleep Tasks
        self.register_task(ScheduledTask(
            name="news_monitor",
            description="Monitor for breaking news and alerts",
            interval_minutes=120,  # Every 2 hours
            market_states=[MarketState.OVERNIGHT_SLEEP],
        ))
        
        # Pre-Market Prep Tasks
        self.register_task(ScheduledTask(
            name="overnight_summary",
            description="Summary of overnight developments",
            scheduled_hours=[6],  # 6 AM
            market_states=[MarketState.PREMARKET_PREP],
        ))
        
        self.register_task(ScheduledTask(
            name="premarket_scanner",
            description="Scan for pre-market movers and gaps",
            scheduled_hours=[7],  # 7 AM
            market_states=[MarketState.PREMARKET_PREP],
        ))
        
        self.register_task(ScheduledTask(
            name="market_open_prep",
            description="Final preparation for market open",
            scheduled_hours=[9],  # 9 AM
            market_states=[MarketState.PREMARKET_PREP],
        ))
    
    def register_task(self, task: ScheduledTask) -> None:
        """
        Register a task with the scheduler.
        
        Args:
            task: ScheduledTask to register
        """
        self.tasks[task.name] = task
        logger.debug(f"Registered task: {task.name}")
    
    def get_current_state(self) -> MarketState:
        """Get current market state"""
        return self.state_detector.get_current_state()
    
    def get_next_task(self) -> Optional[ScheduledTask]:
        """
        Determine which task should run next.
        
        Returns:
            ScheduledTask to execute, or None if no tasks are due
        """
        current_state = self.get_current_state()
        current_time = datetime.now()
        
        # Find all tasks that should run
        due_tasks = [
            task for task in self.tasks.values()
            if task.should_run(current_state, current_time)
        ]
        
        if not due_tasks:
            return None
        
        # Prioritize tasks based on state
        priority_order = {
            MarketState.ACTIVE_TRADING: ["trading_cycle", "quick_intelligence", "deep_analysis"],
            MarketState.MARKET_CLOSING: ["pre_close_assessment", "daily_summary"],
            MarketState.EVENING_ANALYSIS: ["earnings_analysis", "sector_deep_dive", "international_markets"],
            MarketState.OVERNIGHT_SLEEP: ["news_monitor"],
            MarketState.PREMARKET_PREP: ["overnight_summary", "premarket_scanner", "market_open_prep"],
        }
        
        # Sort by priority order for current state
        state_priorities = priority_order.get(current_state, [])
        for task_name in state_priorities:
            for task in due_tasks:
                if task.name == task_name:
                    return task
        
        # Return first due task if no priority match
        return due_tasks[0] if due_tasks else None
    
    def mark_task_complete(self, task_name: str) -> None:
        """
        Mark a task as completed.
        
        Args:
            task_name: Name of completed task
        """
        if task_name in self.tasks:
            self.tasks[task_name].mark_run()
            logger.debug(f"✓ Task completed: {task_name}")
    
    def get_sleep_duration(self) -> int:
        """
        Calculate how long to sleep before next task.
        
        Returns:
            Sleep duration in seconds
        """
        current_state = self.get_current_state()
        
        # Default sleep times by state
        default_sleep = {
            MarketState.ACTIVE_TRADING: 60,      # 1 minute (check frequently)
            MarketState.MARKET_CLOSING: 300,     # 5 minutes
            MarketState.EVENING_ANALYSIS: 600,   # 10 minutes
            MarketState.OVERNIGHT_SLEEP: 600,    # 10 minutes
            MarketState.PREMARKET_PREP: 300,     # 5 minutes
        }
        
        return default_sleep.get(current_state, 300)
    
    def get_state_summary(self) -> Dict[str, Any]:
        """
        Get summary of scheduler state.
        
        Returns:
            Dictionary with scheduler statistics and status
        """
        current_state = self.get_current_state()
        state_info = self.state_detector.get_state_info()
        
        # Count tasks by state
        tasks_by_state = {}
        for task in self.tasks.values():
            for state in task.market_states:
                if state not in tasks_by_state:
                    tasks_by_state[state] = []
                tasks_by_state[state].append(task.name)
        
        # Find next due task
        next_task = self.get_next_task()
        
        return {
            "current_state": state_info,
            "total_tasks": len(self.tasks),
            "tasks_for_current_state": len(tasks_by_state.get(current_state, [])),
            "next_task": next_task.name if next_task else None,
            "next_task_description": next_task.description if next_task else None,
            "total_task_runs": sum(task.run_count for task in self.tasks.values()),
        }
    
    def display_status(self) -> None:
        """Display comprehensive scheduler status"""
        summary = self.get_state_summary()
        state_info = summary["current_state"]
        
        logger.info("=" * 70)
        logger.info(f"{state_info['emoji']} INTELLIGENT SCHEDULER STATUS")
        logger.info("=" * 70)
        logger.info(f"Current State: {state_info['description']}")
        logger.info(f"Current Time: {state_info['current_time_et']}")
        logger.info(f"Primary Focus: {state_info['primary_focus']}")
        logger.info("")
        logger.info(f"Total Tasks Registered: {summary['total_tasks']}")
        logger.info(f"Tasks for Current State: {summary['tasks_for_current_state']}")
        logger.info(f"Total Task Runs: {summary['total_task_runs']}")
        logger.info("")
        
        if summary['next_task']:
            logger.info(f"⏭️  Next Task: {summary['next_task']}")
            logger.info(f"   Description: {summary['next_task_description']}")
        else:
            logger.info("⏸️  No tasks currently due")
        
        logger.info("=" * 70)


if __name__ == "__main__":
    """Test the intelligent scheduler"""
    logger.info("Testing Intelligent Scheduler...")
    logger.info("")
    
    # Create scheduler
    scheduler = IntelligentScheduler()
    
    # Display status
    scheduler.display_status()
    
    # Test task routing
    logger.info("\nTesting task routing:")
    current_state = scheduler.get_current_state()
    logger.info(f"Current state: {current_state.emoji} {current_state.description}")
    
    next_task = scheduler.get_next_task()
    if next_task:
        logger.info(f"Next task to run: {next_task.name}")
        logger.info(f"Description: {next_task.description}")
    else:
        logger.info("No tasks due right now")
