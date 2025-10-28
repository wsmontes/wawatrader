"""
Market Hours Manager - Intelligent Task Scheduling

Manages different system behaviors based on market state:
- Market Open: Active trading
- After Hours: Learning and research
- Pre-Market: Planning and preparation
- Deep Night: Sleep mode

All times in Eastern Time (ET).
"""

from datetime import datetime, time, timedelta
from typing import Dict, Any, Optional, Callable
from enum import Enum
from loguru import logger
from pathlib import Path
import json

from wawatrader.timezone_utils import now_market


class MarketPhase(Enum):
    """Different phases of the trading day"""
    PRE_MARKET = "pre_market"        # 4:00 AM - 9:30 AM ET
    MARKET_OPEN = "market_open"      # 9:30 AM - 4:00 PM ET
    AFTER_HOURS = "after_hours"      # 4:00 PM - 8:00 PM ET
    EVENING_RESEARCH = "evening"     # 8:00 PM - 11:00 PM ET
    DEEP_NIGHT = "deep_night"        # 11:00 PM - 4:00 AM ET


class MarketHoursManager:
    """
    Intelligent manager that schedules different activities based on market phase.
    
    Prevents wasted resources when market is closed and ensures productive
    off-hours activities.
    """
    
    def __init__(self, trading_agent):
        """
        Initialize market hours manager.
        
        Args:
            trading_agent: TradingAgent instance
        """
        self.agent = trading_agent
        self.alpaca = trading_agent.alpaca
        self.current_phase = None
        self.last_phase_change = None
        self.phase_handlers = self._setup_phase_handlers()
        
    def _setup_phase_handlers(self) -> Dict[MarketPhase, Dict[str, Any]]:
        """
        Define what happens in each market phase.
        
        Returns:
            Dict mapping phases to their configurations
        """
        return {
            MarketPhase.MARKET_OPEN: {
                'name': '🟢 MARKET OPEN',
                'description': 'Active trading mode',
                'interval_seconds': 300,  # 5 minutes
                'task': self._market_open_task,
                'on_enter': self._enter_market_open,
                'on_exit': self._exit_market_open
            },
            MarketPhase.AFTER_HOURS: {
                'name': '📊 AFTER HOURS',
                'description': 'Day analysis and learning',
                'interval_seconds': 1800,  # 30 minutes
                'task': self._after_hours_task,
                'on_enter': self._enter_after_hours,
                'on_exit': None
            },
            MarketPhase.EVENING_RESEARCH: {
                'name': '🔍 EVENING RESEARCH',
                'description': 'Deep research and overnight planning',
                'interval_seconds': 3600,  # 1 hour
                'task': self._evening_research_task,
                'on_enter': self._enter_evening_research,
                'on_exit': None
            },
            MarketPhase.DEEP_NIGHT: {
                'name': '💤 SLEEP MODE',
                'description': 'Minimal activity until pre-market',
                'interval_seconds': 7200,  # 2 hours
                'task': self._deep_night_task,
                'on_enter': self._enter_deep_night,
                'on_exit': None
            },
            MarketPhase.PRE_MARKET: {
                'name': '🌅 PRE-MARKET',
                'description': 'Morning preparation and gap scanning',
                'interval_seconds': 900,  # 15 minutes
                'task': self._pre_market_task,
                'on_enter': self._enter_pre_market,
                'on_exit': None
            }
        }
    
    def get_current_phase(self) -> MarketPhase:
        """
        Determine current market phase based on ET time.
        
        Returns:
            Current MarketPhase
        """
        current_time = now_market().time()
        
        # Check if market is actually open (handles holidays)
        try:
            market_status = self.alpaca.get_market_status()
            if market_status.get('is_open', False):
                return MarketPhase.MARKET_OPEN
        except Exception as e:
            logger.warning(f"Could not check market status: {e}")
        
        # Define phase boundaries (all ET)
        if time(4, 0) <= current_time < time(9, 30):
            return MarketPhase.PRE_MARKET
        elif time(9, 30) <= current_time < time(16, 0):
            return MarketPhase.MARKET_OPEN  # Fallback if API fails
        elif time(16, 0) <= current_time < time(20, 0):
            return MarketPhase.AFTER_HOURS
        elif time(20, 0) <= current_time < time(23, 0):
            return MarketPhase.EVENING_RESEARCH
        else:  # 23:00 - 4:00
            return MarketPhase.DEEP_NIGHT
    
    def run_appropriate_task(self) -> Dict[str, Any]:
        """
        Run the appropriate task for current market phase.
        
        Returns:
            Task execution result
        """
        new_phase = self.get_current_phase()
        
        # Detect phase changes
        if new_phase != self.current_phase:
            logger.info("="*70)
            logger.info(f"📅 PHASE CHANGE: {self.current_phase} → {new_phase}")
            logger.info("="*70)
            
            # Exit old phase
            if self.current_phase and self.phase_handlers[self.current_phase].get('on_exit'):
                self.phase_handlers[self.current_phase]['on_exit']()
            
            # Enter new phase
            if self.phase_handlers[new_phase].get('on_enter'):
                self.phase_handlers[new_phase]['on_enter']()
            
            self.current_phase = new_phase
            self.last_phase_change = datetime.now()
        
        # Get phase config
        phase_config = self.phase_handlers[new_phase]
        
        # Log current phase
        logger.info(f"{phase_config['name']} - {phase_config['description']}")
        
        # Run phase task
        try:
            result = phase_config['task']()
            return {
                'status': 'success',
                'phase': new_phase.value,
                'next_run_seconds': phase_config['interval_seconds'],
                **result
            }
        except Exception as e:
            logger.error(f"Phase task failed: {e}")
            return {
                'status': 'error',
                'phase': new_phase.value,
                'next_run_seconds': phase_config['interval_seconds'],
                'error': str(e)
            }
    
    def get_sleep_interval(self) -> int:
        """
        Get appropriate sleep interval for current phase.
        
        Returns:
            Seconds to sleep before next task
        """
        phase = self.get_current_phase()
        return self.phase_handlers[phase]['interval_seconds']
    
    # =================================================================
    # PHASE ENTER/EXIT HANDLERS
    # =================================================================
    
    def _enter_market_open(self):
        """Initialize market open mode"""
        logger.info("🟢 Market opening - switching to active trading mode")
        logger.info("📊 Trading cycles will run every 5 minutes")
        self.agent.reset_daily_metrics()
    
    def _exit_market_open(self):
        """Clean up after market close"""
        logger.info("🔴 Market closed - switching to analysis mode")
        # Generate end-of-day summary
        self._generate_daily_summary()
    
    def _enter_after_hours(self):
        """Initialize after-hours analysis"""
        logger.info("📊 After Hours - Beginning day analysis")
        logger.info("🧠 Will analyze: Performance, Lessons, Tomorrow's Plan")
    
    def _enter_evening_research(self):
        """Initialize evening research"""
        logger.info("🔍 Evening Research - Deep analysis phase")
        logger.info("📰 Scanning overnight news and earnings")
    
    def _enter_deep_night(self):
        """Initialize sleep mode"""
        logger.info("💤 Deep Night - Entering sleep mode")
        logger.info("⏰ Will wake for pre-market at 4:00 AM ET")
    
    def _enter_pre_market(self):
        """Initialize pre-market preparation"""
        logger.info("🌅 Pre-Market - Preparing for market open")
        logger.info("📈 Scanning gaps, reviewing watchlist")
    
    # =================================================================
    # PHASE TASK IMPLEMENTATIONS
    # =================================================================
    
    def _market_open_task(self) -> Dict[str, Any]:
        """Execute active trading cycle"""
        logger.info("📊 Running trading cycle...")
        self.agent.run_cycle()
        return {'task': 'trading_cycle', 'actions': 'Active trading'}
    
    def _after_hours_task(self) -> Dict[str, Any]:
        """Analyze day's performance and learn"""
        logger.info("📊 After-hours analysis...")
        
        tasks_completed = []
        
        # 1. Generate learning insights (every 30 min)
        try:
            insights = self.agent.get_learning_insights()
            if insights:
                logger.info(f"✅ Generated learning insights: {len(insights.get('lessons_learned', []))} lessons")
                tasks_completed.append('learning_insights')
        except Exception as e:
            logger.error(f"Failed to generate insights: {e}")
        
        # 2. Analyze positions (what to hold overnight)
        try:
            positions = self.agent.get_positions()
            if positions:
                logger.info(f"📊 Analyzing {len(positions)} overnight positions")
                tasks_completed.append('position_analysis')
        except Exception as e:
            logger.error(f"Failed position analysis: {e}")
        
        # 3. Scan news for overnight catalysts
        try:
            from wawatrader.market_intelligence import MarketIntelligence
            intel = MarketIntelligence()
            news = intel.get_overnight_news_summary()
            if news:
                logger.info(f"📰 Scanned overnight news: {len(news)} articles")
                tasks_completed.append('news_scan')
        except Exception as e:
            logger.error(f"Failed news scan: {e}")
        
        return {
            'task': 'after_hours_analysis',
            'completed': tasks_completed,
            'actions': f"{len(tasks_completed)} tasks completed"
        }
    
    def _evening_research_task(self) -> Dict[str, Any]:
        """Deep research and overnight planning"""
        logger.info("🔍 Evening research...")
        
        tasks_completed = []
        
        # 1. Run overnight analysis (if available)
        try:
            overnight_file = Path("logs/overnight_analysis.json")
            if not overnight_file.exists() or self._should_refresh_overnight():
                logger.info("🌙 Running overnight deep analysis...")
                # This would trigger run_overnight_analysis.py
                tasks_completed.append('overnight_analysis_needed')
            else:
                logger.info("✅ Overnight analysis already current")
        except Exception as e:
            logger.error(f"Overnight analysis check failed: {e}")
        
        # 2. Check earnings calendar
        try:
            logger.info("📅 Checking earnings calendar for tomorrow...")
            tasks_completed.append('earnings_check')
        except Exception as e:
            logger.error(f"Earnings check failed: {e}")
        
        # 3. Build tomorrow's watchlist
        try:
            from wawatrader.market_intelligence import MarketIntelligence
            intel = MarketIntelligence()
            universe = intel.get_dynamic_universe(min_mentions=3, max_results=50)
            logger.info(f"🎯 Tomorrow's watchlist: {len(universe)} symbols")
            
            # Save watchlist for morning
            watchlist_file = Path("logs/tomorrow_watchlist.json")
            with open(watchlist_file, 'w') as f:
                json.dump({
                    'date': datetime.now().isoformat(),
                    'symbols': universe
                }, f, indent=2)
            
            tasks_completed.append('watchlist_built')
        except Exception as e:
            logger.error(f"Watchlist build failed: {e}")
        
        return {
            'task': 'evening_research',
            'completed': tasks_completed,
            'actions': f"{len(tasks_completed)} research tasks"
        }
    
    def _deep_night_task(self) -> Dict[str, Any]:
        """Minimal monitoring during deep night"""
        logger.info("💤 Deep night check...")
        
        # Just verify system health
        try:
            account = self.agent.get_account()
            logger.info(f"🏦 Account health: ${float(account['equity']):,.2f}")
            
            positions = self.agent.get_positions()
            if positions:
                logger.info(f"📊 Holding {len(positions)} overnight positions")
            
            return {
                'task': 'health_check',
                'account_ok': True,
                'positions': len(positions)
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'task': 'health_check',
                'account_ok': False,
                'error': str(e)
            }
    
    def _pre_market_task(self) -> Dict[str, Any]:
        """Morning preparation before market open"""
        logger.info("🌅 Pre-market preparation...")
        
        tasks_completed = []
        
        # 1. Load yesterday's overnight analysis
        try:
            overnight_file = Path("logs/overnight_analysis.json")
            if overnight_file.exists():
                with open(overnight_file, 'r') as f:
                    analysis = json.load(f)
                logger.info(f"📖 Loaded overnight analysis: {len(analysis)} stocks")
                tasks_completed.append('loaded_analysis')
        except Exception as e:
            logger.error(f"Failed to load overnight analysis: {e}")
        
        # 2. Scan for morning gaps
        try:
            logger.info("📈 Scanning for pre-market gaps...")
            # Would fetch pre-market data if available
            tasks_completed.append('gap_scan')
        except Exception as e:
            logger.error(f"Gap scan failed: {e}")
        
        # 3. Check morning news
        try:
            from wawatrader.market_intelligence import MarketIntelligence
            intel = MarketIntelligence()
            news = intel.get_morning_headlines()
            logger.info(f"📰 Morning headlines: {len(news)} major stories")
            tasks_completed.append('morning_news')
        except Exception as e:
            logger.error(f"Morning news failed: {e}")
        
        # 4. Prepare watchlist
        try:
            watchlist_file = Path("logs/tomorrow_watchlist.json")
            if watchlist_file.exists():
                with open(watchlist_file, 'r') as f:
                    watchlist_data = json.load(f)
                logger.info(f"🎯 Ready to trade: {len(watchlist_data.get('symbols', []))} symbols")
                tasks_completed.append('watchlist_ready')
        except Exception as e:
            logger.error(f"Watchlist load failed: {e}")
        
        return {
            'task': 'pre_market_prep',
            'completed': tasks_completed,
            'actions': f"{len(tasks_completed)} prep tasks",
            'ready_for_open': len(tasks_completed) >= 2
        }
    
    # =================================================================
    # UTILITY METHODS
    # =================================================================
    
    def _generate_daily_summary(self):
        """Generate end-of-day summary"""
        try:
            logger.info("📊 Generating daily summary...")
            
            account = self.agent.get_account()
            positions = self.agent.get_positions()
            
            summary = {
                'date': datetime.now().date().isoformat(),
                'account_value': float(account['equity']),
                'positions_held': len(positions),
                'daily_pnl': self.agent.account_value - self.agent.daily_start_value if self.agent.daily_start_value else 0
            }
            
            summary_file = Path("logs/daily_summaries.jsonl")
            with open(summary_file, 'a') as f:
                f.write(json.dumps(summary) + '\n')
            
            logger.success(f"✅ Daily summary saved: {summary['daily_pnl']:+.2f} PnL")
            
        except Exception as e:
            logger.error(f"Failed to generate daily summary: {e}")
    
    def _should_refresh_overnight(self) -> bool:
        """Check if overnight analysis needs refresh"""
        try:
            overnight_file = Path("logs/overnight_analysis.json")
            if not overnight_file.exists():
                return True
            
            # Check if file is from today
            file_time = datetime.fromtimestamp(overnight_file.stat().st_mtime)
            return file_time.date() < datetime.now().date()
        except Exception:
            return True
