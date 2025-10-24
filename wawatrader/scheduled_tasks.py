"""
Scheduled Task Handlers

Implementation of specific tasks that run at different times based on
market state. Each task is designed to provide value at the right time.

All times are in Eastern Time (ET) as that's when markets operate.
System automatically handles timezone conversion regardless of where it runs.

Author: WawaTrader Team
Created: October 2025
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from loguru import logger
import json

# Import timezone utilities for proper time handling
from wawatrader.timezone_utils import now_market, format_market_time, format_local_time

# Import news timeline manager for overnight news accumulation
from wawatrader.news_timeline import get_timeline_manager

# Import settings for configuration
from config.settings import settings


class ScheduledTaskHandlers:
    """
    Handlers for scheduled tasks in different market states.
    
    Each handler is designed to run at specific times and provide
    value appropriate to the current market state.
    """
    
    def __init__(self, trading_agent):
        """
        Initialize task handlers.
        
        Args:
            trading_agent: TradingAgent instance for access to components
        """
        self.agent = trading_agent
        self.alpaca = trading_agent.alpaca
        self.llm_bridge = trading_agent.llm_bridge
        self.risk_manager = trading_agent.risk_manager
        self.intelligence_engine = trading_agent.intelligence_engine
    
    # =================================================================
    # ACTIVE TRADING TASKS (Market Open)
    # =================================================================
    
    def trading_cycle(self) -> Dict[str, Any]:
        """
        Execute regular trading cycle.
        
        Returns:
            Execution summary
        """
        logger.info("🟢 Executing trading cycle...")
        try:
            self.agent.run_cycle()
            return {"status": "success", "task": "trading_cycle"}
        except Exception as e:
            logger.error(f"Trading cycle failed: {e}")
            return {"status": "error", "task": "trading_cycle", "error": str(e)}
    
    def quick_intelligence(self) -> Dict[str, Any]:
        """
        Quick market intelligence check (30-min intervals).
        
        Lightweight checks for major market shifts:
        - Index movements (SPY, QQQ, IWM)
        - Sector momentum changes
        - VIX volatility spikes
        
        Returns:
            Intelligence summary
        """
        logger.info("📊 Running quick market intelligence check...")
        
        try:
            # Quick checks on major indices
            indices = ["SPY", "QQQ", "IWM", "VIX"]
            movements = {}
            
            for symbol in indices:
                try:
                    bars = self.alpaca.get_historical_data(
                        symbol,
                        days=1,
                        timeframe="5Min"
                    )
                    if not bars.empty:
                        open_price = bars.iloc[0]['open']
                        current_price = bars.iloc[-1]['close']
                        pct_change = ((current_price - open_price) / open_price) * 100
                        movements[symbol] = {
                            "price": current_price,
                            "change_pct": round(pct_change, 2)
                        }
                except Exception as e:
                    logger.debug(f"Failed to get {symbol}: {e}")
            
            # Log findings
            logger.info(f"   Market Indices:")
            for symbol, data in movements.items():
                emoji = "🔴" if data['change_pct'] < -1 else "🟢" if data['change_pct'] > 1 else "⚪"
                logger.info(f"   {emoji} {symbol}: {data['change_pct']:+.2f}%")
            
            # Check for alerts
            alerts = []
            if "VIX" in movements and movements["VIX"]["change_pct"] > 10:
                alerts.append("⚠️ VIX spike detected - increased volatility")
            
            if "SPY" in movements and abs(movements["SPY"]["change_pct"]) > 2:
                alerts.append(f"⚠️ SPY significant move: {movements['SPY']['change_pct']:+.2f}%")
            
            for alert in alerts:
                logger.warning(alert)
            
            return {
                "status": "success",
                "task": "quick_intelligence",
                "movements": movements,
                "alerts": alerts
            }
            
        except Exception as e:
            logger.error(f"Quick intelligence failed: {e}")
            return {"status": "error", "task": "quick_intelligence", "error": str(e)}
    
    def deep_analysis(self) -> Dict[str, Any]:
        """
        Comprehensive market intelligence (2-hour intervals).
        
        Full analysis when enough time has passed for meaningful changes:
        - Comprehensive sector analysis
        - Market regime assessment
        - Risk factor updates
        
        Returns:
            Deep analysis results
        """
        logger.info("🔍 Running deep market analysis (2-hour interval)...")
        
        try:
            # Run full background intelligence
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            intelligence = loop.run_until_complete(
                self.intelligence_engine.run_background_analysis()
            )
            loop.close()
            
            if intelligence:
                self.intelligence_engine.save_intelligence(intelligence)
                logger.info(f"   ✓ Market Sentiment: {intelligence.market_sentiment} ({intelligence.confidence}%)")
                logger.info(f"   ✓ Regime: {intelligence.regime_assessment}")
            
            return {
                "status": "success",
                "task": "deep_analysis",
                "intelligence": intelligence
            }
            
        except Exception as e:
            logger.error(f"Deep analysis failed: {e}")
            return {"status": "error", "task": "deep_analysis", "error": str(e)}
    
    # =================================================================
    # MARKET CLOSING TASKS (3:30 PM - 4:30 PM)
    # =================================================================
    
    def pre_close_assessment(self) -> Dict[str, Any]:
        """
        Assess positions before market close (3:30 PM).
        
        Reviews:
        - Current open positions
        - Overnight risk exposure
        - Position sizing appropriateness
        
        Returns:
            Assessment results
        """
        logger.info("🟡 Pre-close position assessment...")
        
        try:
            positions = self.alpaca.get_positions()
            account = self.alpaca.get_account()
            
            total_value = float(account.portfolio_value)
            cash = float(account.cash)
            
            logger.info(f"   Portfolio Value: ${total_value:,.2f}")
            logger.info(f"   Cash Available: ${cash:,.2f}")
            logger.info(f"   Open Positions: {len(positions)}")
            
            # Analyze overnight exposure
            overnight_exposure = sum(
                abs(float(p.market_value)) for p in positions
            )
            exposure_pct = (overnight_exposure / total_value) * 100
            
            logger.info(f"   Overnight Exposure: ${overnight_exposure:,.2f} ({exposure_pct:.1f}%)")
            
            # Risk warning if high exposure
            if exposure_pct > 80:
                logger.warning("   ⚠️ High overnight exposure (>80%)")
            
            return {
                "status": "success",
                "task": "pre_close_assessment",
                "portfolio_value": total_value,
                "positions": len(positions),
                "overnight_exposure_pct": exposure_pct
            }
            
        except Exception as e:
            logger.error(f"Pre-close assessment failed: {e}")
            return {"status": "error", "task": "pre_close_assessment", "error": str(e)}
    
    def daily_summary(self) -> Dict[str, Any]:
        """
        Generate end-of-day summary (4:00 PM).
        
        Produces:
        - Daily P&L report
        - Trade execution summary
        - Performance metrics
        - Tomorrow's watchlist
        
        Returns:
            Summary results
        """
        logger.info("📊 Generating daily summary...")
        
        try:
            # Get account info
            account = self.alpaca.get_account()
            portfolio_value = float(account.portfolio_value)
            
            # Calculate today's P&L
            today_start_value = float(account.last_equity)  # Yesterday's close
            today_pnl = portfolio_value - today_start_value
            today_pnl_pct = (today_pnl / today_start_value) * 100 if today_start_value > 0 else 0
            
            # Get today's decisions
            today = datetime.now().date()
            today_decisions = [
                d for d in self.agent.decisions
                if datetime.fromisoformat(d.timestamp).date() == today
            ]
            
            # Summary stats
            total_trades = len(today_decisions)
            buys = sum(1 for d in today_decisions if d.action == 'buy')
            sells = sum(1 for d in today_decisions if d.action == 'sell')
            holds = sum(1 for d in today_decisions if d.action == 'hold')
            
            logger.info("=" * 60)
            logger.info(f"DAILY SUMMARY - {today.strftime('%Y-%m-%d')}")
            logger.info("=" * 60)
            logger.info(f"Portfolio Value: ${portfolio_value:,.2f}")
            logger.info(f"Today's P&L: ${today_pnl:+,.2f} ({today_pnl_pct:+.2f}%)")
            logger.info(f"Total Decisions: {total_trades}")
            logger.info(f"  Buy: {buys} | Sell: {sells} | Hold: {holds}")
            logger.info("=" * 60)
            
            # Save to file
            summary_path = self.agent.decisions_log.parent / "daily_summaries.jsonl"
            with open(summary_path, 'a') as f:
                summary = {
                    "date": str(today),
                    "portfolio_value": portfolio_value,
                    "pnl": today_pnl,
                    "pnl_pct": today_pnl_pct,
                    "total_decisions": total_trades,
                    "actions": {"buy": buys, "sell": sells, "hold": holds}
                }
                f.write(json.dumps(summary) + '\n')
            
            return {
                "status": "success",
                "task": "daily_summary",
                "pnl": today_pnl,
                "pnl_pct": today_pnl_pct,
                "total_trades": total_trades
            }
            
        except Exception as e:
            logger.error(f"Daily summary failed: {e}")
            return {"status": "error", "task": "daily_summary", "error": str(e)}
    
    def start_news_collection(self) -> Dict[str, Any]:
        """
        Start overnight news collection (4:00 PM - market close).
        
        Builds dynamic trading universe and initializes NewsTimelineManager.
        News will be collected every 30 minutes until 2:00 AM synthesis.
        
        Universe includes:
        - Current positions (always tracked)
        - Watchlist (user-configured)
        - Sector leaders (diversification)
        - High volume stocks (liquidity/opportunities)
        - Recent movers (momentum/news-driven)
        
        Returns:
            Initialization status
        """
        logger.info("📰 Starting overnight news collection...")
        
        try:
            from wawatrader.universe_manager import get_universe_manager
            
            # Build dynamic trading universe
            universe_mgr = get_universe_manager(self.alpaca, max_size=100)
            
            # Try to load from cache first (avoid rebuilding every 30 min)
            symbols = universe_mgr.load_cache()
            
            if not symbols:
                # Build fresh universe (positions + watchlist + discovered stocks)
                watchlist = list(settings.data.symbols)
                symbols = universe_mgr.build_universe(watchlist)
            
            logger.info(f"   🌍 Tracking {len(symbols)} symbols in dynamic universe")
            
            # Log priority breakdown
            by_priority = universe_mgr.get_by_priority()
            logger.info(f"      Priority 1 (Holdings): {len(by_priority[1])} stocks")
            logger.info(f"      Priority 2 (Watchlist/Sectors): {len(by_priority[2])} stocks")
            logger.info(f"      Priority 3 (Discovered): {len(by_priority[3])} stocks")
            
            # Initialize timeline manager
            timeline_mgr = get_timeline_manager()
            result = timeline_mgr.start_overnight_collection(symbols)
            
            logger.info(f"   ✅ Initialized: {result['initial_articles']} articles collected")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to start news collection: {e}")
            return {
                "status": "error",
                "task": "start_news_collection",
                "error": str(e)
            }
    
    def evening_deep_learning(self) -> Dict[str, Any]:
        """
        Deep learning and pattern discovery (4:30 PM).
        
        ENHANCED Post-market learning pipeline:
        1. Analyze today's trading performance
        2. Discover new patterns from recent trades
        3. **ITERATIVE DEEP RESEARCH** on each watchlist stock (NEW)
        4. Generate insights and lessons
        5. Create tomorrow's game plan
        
        This is where the system gets smarter every day.
        
        Returns:
            Learning results summary
        """
        logger.info("=" * 60)
        logger.info("🧠 EVENING DEEP LEARNING SESSION (ENHANCED)")
        logger.info("=" * 60)
        
        try:
            # Ensure we have learning engine
            if not hasattr(self.agent, 'learning_engine'):
                logger.warning("⚠️ Learning engine not available on agent")
                return {
                    "status": "skipped",
                    "task": "evening_deep_learning",
                    "reason": "Learning engine not initialized"
                }
            
            learning_engine = self.agent.learning_engine
            results = {}
            
            # Step 1: Analyze today's performance
            logger.info("\n1️⃣ Analyzing today's trading performance...")
            try:
                performance = learning_engine.analyze_daily_performance()
                results['daily_performance'] = {
                    'total_trades': performance['total_trades'],
                    'win_rate': performance['win_rate'],
                    'total_pnl': performance['total_pnl'],
                    'market_regime': performance['market_regime']
                }
                
                logger.info(f"""
   📊 Daily Performance:
   - Trades: {performance['total_trades']}
   - Win Rate: {performance['win_rate']:.1%}
   - P&L: ${performance['total_pnl']:+.2f}
   - Market: {performance['market_regime']}
                """)
                
                # Log lessons learned
                if performance['lessons_learned']:
                    logger.info("\n   💡 Lessons Learned:")
                    for lesson in performance['lessons_learned']:
                        logger.info(f"   - {lesson}")
                        
            except Exception as e:
                logger.error(f"   ❌ Performance analysis failed: {e}")
                results['daily_performance'] = {'error': str(e)}
            
            # Step 2: Discover patterns
            logger.info("\n2️⃣ Discovering profitable patterns...")
            try:
                patterns = learning_engine.discover_patterns(lookback_days=30)
                results['patterns_discovered'] = len(patterns)
                
                if patterns:
                    logger.info(f"   ✅ Discovered {len(patterns)} patterns")
                    
                    # Show top 3 patterns
                    top_patterns = sorted(patterns, key=lambda x: x['success_rate'], reverse=True)[:3]
                    for i, pattern in enumerate(top_patterns, 1):
                        logger.info(f"""
   {i}. {pattern['pattern_name']}:
      Success Rate: {pattern['success_rate']:.0%}
      Sample Size: {pattern['sample_size']}
      Avg Return: ${pattern['avg_return']:.2f}
                        """)
                else:
                    logger.info("   ℹ️ Not enough data yet to discover patterns (need 10+ trades)")
                    
            except Exception as e:
                logger.error(f"   ❌ Pattern discovery failed: {e}")
                results['patterns_discovered'] = 0
            
            # Step 3: Get overall statistics
            logger.info("\n3️⃣ Overall Performance Statistics...")
            try:
                stats = learning_engine.memory.get_performance_stats(days=30)
                results['30day_stats'] = {
                    'total_trades': stats['total_trades'],
                    'win_rate': stats['win_rate'],
                    'total_pnl': stats['total_pnl']
                }
                
                logger.info(f"""
   📈 Last 30 Days:
   - Total Trades: {stats['total_trades']}
   - Win Rate: {stats['win_rate']:.1%}
   - Total P&L: ${stats['total_pnl']:+.2f}
   - Risk/Reward: {stats['risk_reward_ratio']:.2f}
                """)
                
            except Exception as e:
                logger.error(f"   ❌ Statistics gathering failed: {e}")
                results['30day_stats'] = {'error': str(e)}
            
            # Step 4: Generate insights for tomorrow
            logger.info("\n4️⃣ Generating insights for tomorrow...")
            try:
                # Get learned patterns
                active_patterns = learning_engine.memory.get_patterns(min_success_rate=0.6, min_sample_size=5)
                
                if active_patterns:
                    logger.info(f"\n   🎯 Apply these proven patterns tomorrow:")
                    for pattern in active_patterns[:5]:
                        logger.info(f"""
   - {pattern['pattern_name']}: {pattern['success_rate']:.0%} success
     (Sample: {pattern['sample_size']}, Avg: ${pattern['avg_return']:.2f})
                        """)
                else:
                    logger.info("   ℹ️ Still building pattern library...")
                
                results['actionable_patterns'] = len(active_patterns)
                
            except Exception as e:
                logger.error(f"   ❌ Insight generation failed: {e}")
                results['actionable_patterns'] = 0
            
            # Step 5: ITERATIVE DEEP RESEARCH (NEW - Priority 1 Enhancement)
            logger.info("\n5️⃣ Deep Iterative Research on Watchlist...")
            try:
                from wawatrader.iterative_analyst import IterativeAnalyst
                import pandas as pd
                
                # Initialize iterative analyst for deep research
                analyst = IterativeAnalyst(
                    alpaca_client=self.alpaca,
                    llm_bridge=self.llm_bridge,
                    max_iterations=15  # Allow deep exploration (vs 5 default)
                )
                
                research_reports = {}
                
                for symbol in self.agent.symbols:
                    logger.info(f"\n   🔬 Deep research: {symbol}")
                    
                    try:
                        # Get comprehensive historical data
                        bars = self.alpaca.get_bars(symbol, limit=100, timeframe='1Day')
                        
                        if bars.empty:
                            logger.warning(f"      ⚠️ No data available for {symbol}")
                            continue
                        
                        # Calculate technical indicators
                        signals = self.agent.indicators.calculate_all(bars)
                        
                        # Build comprehensive initial context (JSON serializable)
                        def safe_value(val, default='N/A'):
                            """Safely convert to serializable value"""
                            if val is None:
                                return default
                            if hasattr(val, 'iloc'):
                                try:
                                    return float(val.iloc[-1]) if len(val) > 0 else default
                                except:
                                    return default
                            if pd.isna(val):
                                return default
                            try:
                                return float(val)
                            except:
                                return str(val)
                        
                        # Get recent decisions for context
                        recent_decisions = []
                        if hasattr(learning_engine, 'memory'):
                            try:
                                decision_df = learning_engine.memory.get_recent_decisions(days=7, symbol=symbol)
                                if not decision_df.empty:
                                    recent_decisions = decision_df[['timestamp', 'action', 'confidence', 'outcome']].to_dict('records')[:5]
                            except:
                                pass
                        
                        initial_context = {
                            'symbol': symbol,
                            'current_price': f"${bars['close'].iloc[-1]:.2f}",
                            'price_change_1d': f"{bars['close'].pct_change().iloc[-1]:.2%}",
                            'rsi': f"{safe_value(signals.get('momentum', {}).get('rsi')):.2f}" if safe_value(signals.get('momentum', {}).get('rsi')) != 'N/A' else 'N/A',
                            'macd_signal': f"{safe_value(signals.get('trend', {}).get('macd_signal')):.2f}" if safe_value(signals.get('trend', {}).get('macd_signal')) != 'N/A' else 'N/A',
                            'sma_20': f"${safe_value(signals.get('trend', {}).get('sma_20')):.2f}" if safe_value(signals.get('trend', {}).get('sma_20')) != 'N/A' else 'N/A',
                            'sma_50': f"${safe_value(signals.get('trend', {}).get('sma_50')):.2f}" if safe_value(signals.get('trend', {}).get('sma_50')) != 'N/A' else 'N/A',
                            'recent_price_action_5d': [float(x) for x in bars['close'].pct_change().iloc[-5:].tolist() if not pd.isna(x)],
                            'volume_trend': 'increasing' if bars['volume'].iloc[-5:].mean() > bars['volume'].iloc[-20:-5].mean() else 'decreasing',
                            'recent_decisions': recent_decisions,
                            'today_performance': {
                                'trades_today': results.get('daily_performance', {}).get('total_trades', 0),
                                'market_regime': results.get('daily_performance', {}).get('market_regime', 'unknown')
                            }
                        }
                        
                        # Run iterative deep analysis (can take 5-20 minutes per stock)
                        logger.info(f"      🤖 Starting iterative analysis (up to 15 iterations)...")
                        research = analyst.analyze_with_iterations(
                            symbol=symbol,
                            initial_context=initial_context
                        )
                        
                        research_reports[symbol] = research
                        
                        # Log summary
                        iterations = research.get('iterations', 0)
                        depth = research.get('analysis_depth', 'unknown')
                        logger.info(f"      ✅ Completed: {iterations} iterations ({depth} analysis)")
                        
                        # Save to overnight analysis log
                        import json
                        from pathlib import Path
                        from datetime import datetime
                        
                        log_path = Path('logs/overnight_analysis.json')
                        
                        # Load existing or create new
                        if log_path.exists():
                            with open(log_path, 'r') as f:
                                all_analyses = json.load(f)
                        else:
                            all_analyses = []
                        
                        # Add this analysis
                        all_analyses.append(research)
                        
                        # Save (keep last 30 days)
                        with open(log_path, 'w') as f:
                            json.dump(all_analyses[-30:], f, indent=2)
                        
                    except Exception as e:
                        logger.error(f"      ❌ Deep research failed for {symbol}: {e}")
                        continue
                
                results['deep_research'] = {
                    'stocks_analyzed': len(research_reports),
                    'total_iterations': sum(r.get('iterations', 0) for r in research_reports.values()),
                    'avg_iterations': sum(r.get('iterations', 0) for r in research_reports.values()) / max(len(research_reports), 1)
                }
                
                logger.info(f"\n   📊 Deep Research Summary:")
                logger.info(f"      Stocks Analyzed: {len(research_reports)}")
                logger.info(f"      Total Iterations: {results['deep_research']['total_iterations']}")
                logger.info(f"      Avg Iterations/Stock: {results['deep_research']['avg_iterations']:.1f}")
                
            except Exception as e:
                logger.error(f"   ❌ Deep research pipeline failed: {e}")
                import traceback
                traceback.print_exc()
                results['deep_research'] = {'error': str(e)}
            
            # Summary
            logger.info("\n" + "=" * 60)
            logger.info("✅ EVENING LEARNING SESSION COMPLETE")
            logger.info("=" * 60)
            logger.info(f"""
Summary:
- Trades Analyzed: {results.get('daily_performance', {}).get('total_trades', 0)}
- Patterns Discovered: {results.get('patterns_discovered', 0)}
- Actionable Patterns: {results.get('actionable_patterns', 0)}

💡 The system is learning and improving!
            """)
            logger.info("=" * 60 + "\n")
            
            return {
                "status": "success",
                "task": "evening_deep_learning",
                "results": results
            }
            
        except Exception as e:
            logger.error(f"❌ Evening learning session failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "task": "evening_deep_learning",
                "error": str(e)
            }
    
    def weekly_self_critique(self) -> Dict[str, Any]:
        """
        LLM self-analysis of its own decision patterns (Friday 6:00 PM).
        
        PRIORITY 2 ENHANCEMENT - NEW TASK
        
        The LLM reviews its own trading decisions from the past week to discover:
        - Decision biases (e.g., HOLD overuse)
        - Missed opportunities
        - Confidence calibration errors
        - Repeated reasoning mistakes
        - Patterns worth continuing vs eliminating
        
        Generates actionable improvements for next week.
        
        Returns:
            Self-critique insights and action items
        """
        logger.info("=" * 70)
        logger.info("🔍 WEEKLY LLM SELF-CRITIQUE SESSION")
        logger.info("=" * 70)
        logger.info("The LLM will now review its own trading decisions...")
        
        try:
            from pathlib import Path
            import numpy as np
            
            # Load past week's decisions from jsonl log
            decisions_path = Path('logs/decisions.jsonl')
            
            if not decisions_path.exists():
                logger.warning("⚠️ No decisions log found")
                return {
                    "status": "skipped",
                    "task": "weekly_self_critique",
                    "reason": "No decisions.jsonl file found"
                }
            
            # Parse JSONL (one JSON object per line)
            decisions = []
            cutoff_date = datetime.now() - timedelta(days=7)
            
            with open(decisions_path, 'r') as f:
                for line in f:
                    try:
                        decision = json.loads(line.strip())
                        decision_time = datetime.fromisoformat(decision['timestamp'])
                        
                        if decision_time >= cutoff_date:
                            decisions.append(decision)
                    except Exception as e:
                        continue  # Skip malformed lines
            
            if len(decisions) == 0:
                logger.warning("⚠️ No decisions found in past 7 days")
                return {
                    "status": "skipped",
                    "task": "weekly_self_critique",
                    "reason": "No decisions in past week"
                }
            
            logger.info(f"📊 Analyzing {len(decisions)} decisions from past 7 days...\n")
            
            # Calculate statistics
            actions = [d.get('action', 'unknown').lower() for d in decisions]
            confidences = [d.get('confidence', 0) for d in decisions]
            
            stats = {
                'total_decisions': len(decisions),
                'hold_count': sum(1 for a in actions if a == 'hold'),
                'buy_count': sum(1 for a in actions if a == 'buy'),
                'sell_count': sum(1 for a in actions if a == 'sell'),
                'hold_rate': sum(1 for a in actions if a == 'hold') / max(len(actions), 1),
                'buy_rate': sum(1 for a in actions if a == 'buy') / max(len(actions), 1),
                'sell_rate': sum(1 for a in actions if a == 'sell') / max(len(actions), 1),
                'avg_confidence': np.mean(confidences) if confidences else 0,
                'min_confidence': np.min(confidences) if confidences else 0,
                'max_confidence': np.max(confidences) if confidences else 0
            }
            
            # Log statistics
            logger.info("📈 Decision Statistics:")
            logger.info(f"   Total Decisions: {stats['total_decisions']}")
            logger.info(f"   HOLD: {stats['hold_count']} ({stats['hold_rate']:.1%})")
            logger.info(f"   BUY:  {stats['buy_count']} ({stats['buy_rate']:.1%})")
            logger.info(f"   SELL: {stats['sell_count']} ({stats['sell_rate']:.1%})")
            logger.info(f"   Avg Confidence: {stats['avg_confidence']:.0f}%")
            logger.info(f"   Confidence Range: {stats['min_confidence']:.0f}% - {stats['max_confidence']:.0f}%\n")
            
            # Sample decisions for analysis (max 20 to avoid token overflow)
            sample_size = min(20, len(decisions))
            sampled_decisions = decisions[-sample_size:]  # Most recent
            
            # Build self-critique prompt
            prompt = f"""CRITICAL SELF-ANALYSIS SESSION

You are reviewing YOUR OWN trading decisions from the past week.
Be brutally honest about mistakes, biases, and areas for improvement.

DECISION STATISTICS:
- Total Decisions: {stats['total_decisions']}
- HOLD Rate: {stats['hold_rate']:.1%} ({stats['hold_count']} times)
- BUY Rate: {stats['buy_rate']:.1%} ({stats['buy_count']} times)
- SELL Rate: {stats['sell_rate']:.1%} ({stats['sell_count']} times)
- Average Confidence: {stats['avg_confidence']:.0f}%
- Confidence Range: {stats['min_confidence']:.0f}% to {stats['max_confidence']:.0f}%

TARGET DISTRIBUTION (Ideal):
- ~40% HOLD, ~40% BUY, ~20% SELL

SAMPLE OF RECENT DECISIONS:
{json.dumps(sampled_decisions, indent=2, default=str)}

REQUIRED ANALYSIS:

1. HOLD BIAS ASSESSMENT (Score 1-10):
   - Your HOLD rate is {stats['hold_rate']:.0%}. Is this appropriate?
   - Target should be ~40%. Are you being too cautious?
   - Review 3 HOLD decisions that should have been BUY/SELL
   - What made you hesitate on strong signals?

2. CONFIDENCE CALIBRATION CHECK:
   - Are your confidence scores well-distributed or clustered?
   - Do you use the full 0-100 range or just 60-80?
   - Are 80% confidence decisions actually winning 80% of time?
   - How to better calibrate your confidence?

3. REASONING QUALITY AUDIT:
   - How many of your reasons include specific price targets? (should be 100%)
   - How many are generic ("market volatility", "uncertain")? (should be 0%)
   - Rate your reasoning quality: 0-100

4. MISSED OPPORTUNITIES (List top 3):
   - Which decisions had strong technical signals but you said HOLD?
   - Why? Was news overweighted vs technicals?
   - What would you do differently now?

5. REPEATED PATTERNS:
   - Do you see any systematic errors?
   - E.g., "Always HOLD when RSI is neutral despite bullish trend"
   - Any decision rules that need adjustment?

6. ACTIONABLE IMPROVEMENTS:
   - What SPECIFIC changes to make next week?
   - New decision thresholds or rules?
   - Prompt modifications needed?

RESPONSE FORMAT (valid JSON):
{{
    "hold_bias_severity": 1-10,
    "hold_bias_analysis": "detailed assessment...",
    "confidence_calibration_score": 0-100,
    "confidence_issues": "specific problems...",
    "reasoning_quality_score": 0-100,
    "reasoning_improvements": "what to change...",
    "missed_opportunities": [
        {{"symbol": "AAPL", "date": "...", "severity": 8, "lesson": "...", "should_have_been": "BUY"}}
    ],
    "repeated_patterns": ["pattern1", "pattern2"],
    "action_items": [
        {{
            "priority": "HIGH|MEDIUM|LOW",
            "change": "specific change to make",
            "implementation": "how to implement",
            "expected_impact": "what improvement expected"
        }}
    ],
    "self_assessment_grade": "A|B|C|D|F",
    "key_insight": "most important finding"
}}

Be harsh but constructive. The goal is continuous improvement.
"""
            
            logger.info("🤖 Querying LLM for self-analysis...")
            
            # Get LLM self-analysis
            response = self.llm_bridge.query_llm(prompt, symbol='SELF_CRITIQUE')
            
            if not response:
                logger.error("❌ No response from LLM")
                return {
                    "status": "error",
                    "task": "weekly_self_critique",
                    "error": "No LLM response"
                }
            
            # Parse response
            try:
                # Try to extract JSON from response
                if '```json' in response:
                    json_str = response.split('```json')[1].split('```')[0].strip()
                elif '```' in response:
                    json_str = response.split('```')[1].split('```')[0].strip()
                else:
                    json_str = response.strip()
                
                critique = json.loads(json_str)
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to parse LLM response as JSON: {e}")
                logger.debug(f"Raw response: {response[:500]}...")
                
                # Store raw response for manual review
                critique = {
                    "error": "Failed to parse JSON",
                    "raw_response": response,
                    "parse_error": str(e)
                }
            
            # Store critique in log
            critique_path = Path('logs/self_critique.jsonl')
            
            with open(critique_path, 'a') as f:
                f.write(json.dumps({
                    'timestamp': datetime.now().isoformat(),
                    'week_ending': datetime.now().strftime('%Y-%m-%d'),
                    'stats': stats,
                    'critique': critique
                }) + '\n')
            
            # Log key findings
            logger.info("\n" + "=" * 70)
            logger.info("📊 SELF-CRITIQUE RESULTS")
            logger.info("=" * 70)
            
            if 'error' not in critique:
                logger.info(f"Self-Assessment Grade: {critique.get('self_assessment_grade', 'N/A')}")
                logger.info(f"Hold Bias Severity: {critique.get('hold_bias_severity', 'N/A')}/10")
                logger.info(f"Confidence Calibration: {critique.get('confidence_calibration_score', 'N/A')}/100")
                logger.info(f"Reasoning Quality: {critique.get('reasoning_quality_score', 'N/A')}/100")
                
                logger.info(f"\n💡 Key Insight: {critique.get('key_insight', 'N/A')}")
                
                logger.info("\n🎯 Action Items:")
                action_items = critique.get('action_items', [])
                for i, item in enumerate(action_items[:5], 1):
                    logger.info(f"   {i}. [{item.get('priority', 'MEDIUM')}] {item.get('change', 'N/A')}")
                    logger.info(f"      → {item.get('implementation', 'N/A')}")
                
                logger.info(f"\n🔁 Repeated Patterns Detected:")
                for pattern in critique.get('repeated_patterns', [])[:3]:
                    logger.info(f"   - {pattern}")
            else:
                logger.warning("⚠️ Critique parsing failed, stored for manual review")
            
            logger.info("\n" + "=" * 70)
            logger.info(f"✅ Self-critique saved to: {critique_path}")
            logger.info("=" * 70 + "\n")
            
            return {
                "status": "success",
                "task": "weekly_self_critique",
                "decisions_analyzed": len(decisions),
                "stats": stats,
                "critique": critique
            }
            
        except Exception as e:
            logger.error(f"❌ Weekly self-critique failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "task": "weekly_self_critique",
                "error": str(e)
            }
    
    # =================================================================
    # EVENING ANALYSIS TASKS (4:30 PM - 10:00 PM)
    # =================================================================
    
    def earnings_analysis(self) -> Dict[str, Any]:
        """
        Deep dive into upcoming earnings (5:00 PM).
        
        Analyzes:
        - Earnings calendar for next 7 days
        - Historical earnings patterns
        - Pre-earnings volatility
        - Trading strategy for earnings plays
        
        Uses LLM to develop earnings-specific trading strategies.
        
        Returns:
            Earnings insights and strategy recommendations
        """
        logger.info("📅 Analyzing upcoming earnings calendar...")
        
        try:
            # Step 1: Analyze watchlist for earnings context
            logger.info("   📊 Gathering earnings context for watchlist...")
            
            earnings_context = {}
            for symbol in self.agent.symbols:
                try:
                    # Get historical volatility around earnings
                    bars = self.alpaca.get_historical_data(symbol, days=90, timeframe='1Day')
                    
                    if len(bars) >= 60:
                        # Calculate recent volatility
                        returns = bars['close'].pct_change()
                        volatility_20d = returns.tail(20).std() * (252 ** 0.5) * 100  # Annualized
                        volatility_60d = returns.tail(60).std() * (252 ** 0.5) * 100
                        
                        # Get recent price action
                        current_price = bars.iloc[-1]['close']
                        price_20d_ago = bars.iloc[-20]['close'] if len(bars) >= 20 else bars.iloc[0]['close']
                        price_60d_ago = bars.iloc[-60]['close'] if len(bars) >= 60 else bars.iloc[0]['close']
                        
                        return_20d = ((current_price - price_20d_ago) / price_20d_ago) * 100
                        return_60d = ((current_price - price_60d_ago) / price_60d_ago) * 100
                        
                        # Get technical indicators
                        indicators = self.agent.indicators
                        rsi = indicators.calculate_rsi(bars['close'].values)
                        macd, signal = indicators.calculate_macd(bars['close'].values)
                        
                        earnings_context[symbol] = {
                            'current_price': float(current_price),
                            'volatility_20d': round(volatility_20d, 2),
                            'volatility_60d': round(volatility_60d, 2),
                            'return_20d': round(return_20d, 2),
                            'return_60d': round(return_60d, 2),
                            'rsi': round(float(rsi[-1]), 2) if len(rsi) > 0 else None,
                            'macd': round(float(macd[-1]), 2) if len(macd) > 0 else None,
                            'macd_signal': round(float(signal[-1]), 2) if len(signal) > 0 else None,
                            'trend': 'BULLISH' if return_20d > 5 else 'BEARISH' if return_20d < -5 else 'NEUTRAL',
                            'volatility_regime': 'HIGH' if volatility_20d > volatility_60d * 1.2 else 'LOW' if volatility_20d < volatility_60d * 0.8 else 'NORMAL'
                        }
                        
                        logger.info(f"   ✓ {symbol}: {earnings_context[symbol]['trend']} trend, {earnings_context[symbol]['volatility_regime']} vol")
                        
                except Exception as e:
                    logger.debug(f"   Failed to analyze {symbol}: {e}")
            
            # Step 2: Load recent performance data
            logger.info("   📈 Loading recent trading performance...")
            
            recent_decisions = []
            from pathlib import Path
            decisions_file = Path('logs/decisions.jsonl')
            
            if decisions_file.exists():
                try:
                    with open(decisions_file, 'r') as f:
                        all_decisions = [json.loads(line) for line in f]
                        # Get last 30 days
                        cutoff = datetime.now() - timedelta(days=30)
                        recent_decisions = [
                            d for d in all_decisions
                            if datetime.fromisoformat(d.get('timestamp', '2020-01-01')) > cutoff
                        ]
                    logger.info(f"   ✓ Loaded {len(recent_decisions)} decisions from last 30 days")
                except Exception as e:
                    logger.debug(f"   Could not load decisions: {e}")
            
            # Calculate win rate by symbol for earnings context
            symbol_performance = {}
            for symbol in self.agent.symbols:
                symbol_decisions = [d for d in recent_decisions if d.get('symbol') == symbol]
                if symbol_decisions:
                    buy_decisions = [d for d in symbol_decisions if d.get('action') == 'BUY']
                    sell_decisions = [d for d in symbol_decisions if d.get('action') == 'SELL']
                    
                    symbol_performance[symbol] = {
                        'total_decisions': len(symbol_decisions),
                        'buy_count': len(buy_decisions),
                        'sell_count': len(sell_decisions),
                        'avg_confidence': round(sum(d.get('confidence', 0) for d in symbol_decisions) / len(symbol_decisions), 1) if symbol_decisions else 0
                    }
            
            # Step 3: Build comprehensive earnings analysis prompt
            logger.info("   🤖 Querying LLM for earnings strategy...")
            
            prompt = f"""
EARNINGS ANALYSIS & STRATEGY - {datetime.now().strftime('%A, %B %d, %Y')}

You are developing trading strategies for stocks with potential earnings events in the next 7-14 days.

=== WATCHLIST EARNINGS CONTEXT ===
{json.dumps(earnings_context, indent=2)}

=== RECENT TRADING PERFORMANCE ===
{json.dumps(symbol_performance, indent=2) if symbol_performance else "No recent data"}

=== YOUR TASK ===

For each stock in the watchlist, develop an earnings-aware trading strategy:

1. EARNINGS PROXIMITY ASSESSMENT:
   - Is this stock likely to report earnings soon? (Based on typical quarterly patterns)
   - Typical reporting pattern: Tech (late Jan, late Apr, late Jul, late Oct)
   - Current date context matters

2. PRE-EARNINGS STRATEGY:
   - Should we hold through earnings or close before?
   - Current position: Are we long/short/neutral?
   - Volatility suggests risk level?

3. EARNINGS PLAY RECOMMENDATIONS:
   - BUY opportunity if expecting beat?
   - SELL/AVOID if expecting miss?
   - Wait until after earnings for clarity?
   - Straddle/strangle options strategy? (if applicable)

4. POSITION SIZING ADJUSTMENTS:
   - Reduce size before earnings (high risk)?
   - Increase size (high conviction)?
   - Stay normal size?

5. POST-EARNINGS PLAN:
   - If stock gaps up 5%+, what's the play?
   - If stock gaps down 5%+, what's the play?
   - Re-entry levels after volatility settles

For each stock, provide specific action items and reasoning.

Respond in JSON format:
{{
    "analysis_date": "2025-10-23",
    "next_earnings_week": "Estimated week of Nov 1-7, 2025",
    "earnings_strategies": [
        {{
            "symbol": "AAPL",
            "likely_earnings_date": "~Nov 2, 2025 (estimated)",
            "days_until_earnings": 10,
            "current_strategy": "HOLD_THROUGH/CLOSE_BEFORE/WAIT_AFTER",
            "reasoning": "Why this strategy makes sense",
            "pre_earnings_action": {{
                "action": "REDUCE_SIZE/INCREASE_SIZE/HOLD/CLOSE",
                "target_size_pct": 10,
                "rationale": "Specific reason"
            }},
            "volatility_assessment": {{
                "current_vol": 25.5,
                "earnings_vol_expectation": "WILL_SPIKE/NORMAL/DECLINING",
                "risk_level": "HIGH/MEDIUM/LOW"
            }},
            "upside_scenario": {{
                "probability": 60,
                "expected_move": "+8%",
                "action": "Take profits at +5%, let rest run",
                "target": 275.00
            }},
            "downside_scenario": {{
                "probability": 40,
                "expected_move": "-6%",
                "action": "Cut position at -3%",
                "stop_loss": 245.00
            }},
            "confidence": 75,
            "key_factors": ["Revenue growth", "iPhone sales", "Services segment"]
        }},
        ...
    ],
    "high_risk_stocks": ["Stocks to avoid or reduce before earnings"],
    "high_opportunity_stocks": ["Stocks with good earnings setups"],
    "portfolio_adjustments": [
        "Specific action 1: Reduce AAPL to 10% from 15%",
        "Specific action 2: Add cash buffer for post-earnings opportunities"
    ],
    "overall_earnings_posture": "AGGRESSIVE/BALANCED/DEFENSIVE"
}}
"""
            
            # Query LLM
            response = self.llm_bridge.query_llm(prompt, symbol='EARNINGS_ANALYSIS')
            
            # Parse response
            analysis = None
            try:
                # Try direct JSON parse
                analysis = json.loads(response)
            except json.JSONDecodeError:
                # Try extracting JSON from markdown
                import re
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group(1))
                else:
                    # Fallback
                    analysis = {
                        'raw_response': response,
                        'parsed': False
                    }
            
            # Log key findings
            if analysis and analysis.get('parsed') != False:
                logger.info(f"   📊 Earnings Strategies Generated: {len(analysis.get('earnings_strategies', []))}")
                logger.info(f"   🚨 High Risk Stocks: {len(analysis.get('high_risk_stocks', []))}")
                logger.info(f"   🎯 High Opportunity Stocks: {len(analysis.get('high_opportunity_stocks', []))}")
                logger.info(f"   📋 Portfolio Adjustments: {len(analysis.get('portfolio_adjustments', []))}")
                logger.info(f"   🎲 Overall Posture: {analysis.get('overall_earnings_posture', 'N/A')}")
                
                # Log specific strategies
                for strategy in analysis.get('earnings_strategies', [])[:3]:
                    logger.info(f"   • {strategy.get('symbol')}: {strategy.get('current_strategy')} (Days: ~{strategy.get('days_until_earnings', 'TBD')})")
                    logger.info(f"     Risk: {strategy.get('volatility_assessment', {}).get('risk_level', 'N/A')}, Confidence: {strategy.get('confidence', 'N/A')}%")
            
            # Save to log
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'task': 'earnings_analysis',
                'watchlist_analyzed': len(earnings_context),
                'earnings_context': earnings_context,
                'symbol_performance': symbol_performance,
                'analysis': analysis
            }
            
            log_file = Path('logs/earnings_analysis.jsonl')
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
            
            logger.info(f"   ✅ Earnings analysis complete and saved")
            
            return {
                "status": "success",
                "task": "earnings_analysis",
                "analysis": analysis,
                "stocks_analyzed": len(earnings_context)
            }
            
        except Exception as e:
            logger.error(f"❌ Earnings analysis failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            
            return {
                "status": "error",
                "task": "earnings_analysis",
                "error": str(e)
            }
    
    def sector_deep_dive(self) -> Dict[str, Any]:
        """
        Comprehensive sector analysis (7:00 PM).
        
        Deep analysis of:
        - Sector rotation patterns
        - Relative strength analysis
        - Momentum shifts
        
        Returns:
            Sector analysis
        """
        logger.info("🏭 Running comprehensive sector analysis...")
        
        # Placeholder - would use sector ETF analysis
        logger.info("   ℹ️ Sector deep dive not yet implemented")
        logger.info("   TODO: Implement sector rotation analysis")
        
        return {
            "status": "success",
            "task": "sector_deep_dive",
            "note": "Not yet implemented"
        }
    
    def international_markets(self) -> Dict[str, Any]:
        """
        Review international markets (9:00 PM).
        
        Checks:
        - Asian markets opening
        - European market close
        - Futures market activity
        
        Returns:
            International market summary
        """
        logger.info("🌍 Reviewing international markets...")
        
        # Placeholder - would integrate with international data
        logger.info("   ℹ️ International markets review not yet implemented")
        logger.info("   TODO: Integrate international market data")
        
        return {
            "status": "success",
            "task": "international_markets",
            "note": "Not yet implemented"
        }
    
    # =================================================================
    # OVERNIGHT SLEEP TASKS (10:00 PM - 6:00 AM)
    # =================================================================
    
    def news_monitor(self) -> Dict[str, Any]:
        """
        Monitor for breaking news (every 30 minutes overnight).
        
        ACCUMULATION PHASE: Collect news without making decisions.
        The complete narrative will be synthesized at 2:00 AM.
        
        Strategy:
        - 4:00 PM - 2:00 AM: Just accumulate news (this method)
        - 2:00 AM: Synthesize complete narrative (overnight_summary)
        - 6:00 AM: Validate with late-breaking news
        
        Returns:
            News collection status
        """
        logger.debug("� Collecting overnight news...")
        
        try:
            timeline_mgr = get_timeline_manager()
            
            # Collect news for all tracked symbols
            new_articles = timeline_mgr.collect_news()
            
            if new_articles > 0:
                logger.info(f"✅ Collected {new_articles} new articles")
            
            # Get statistics
            stats = timeline_mgr.get_statistics()
            
            return {
                "status": "success",
                "task": "news_monitor",
                "new_articles": new_articles,
                "total_articles": stats['total_articles'],
                "symbols_with_news": stats['symbols_with_news']
            }
            
        except Exception as e:
            logger.error(f"❌ Error in news monitoring: {e}")
            return {
                "status": "error",
                "task": "news_monitor",
                "error": str(e)
            }
    
    # =================================================================
    # PRE-MARKET PREP TASKS (6:00 AM - 9:30 AM)
    # =================================================================
    
    def overnight_summary(self) -> Dict[str, Any]:
        """
        Summary of overnight developments (6:00 AM).
        
        Reviews:
        - Overnight futures performance
        - International market results
        - Breaking news overnight
        - Key levels and watchlist updates
        
        Uses LLM to synthesize overnight data into actionable morning brief.
        
        Returns:
            Overnight summary with key insights
        """
        logger.info("🌅 Preparing overnight summary...")
        
        try:
            # Step 1: Gather overnight data
            logger.info("   📊 Gathering overnight market data...")
            
            # Get futures data (ES, NQ, RTY)
            futures_data = {}
            futures_symbols = {
                'SPY': 'S&P 500 Futures',
                'QQQ': 'Nasdaq Futures', 
                'IWM': 'Russell 2000 Futures'
            }
            
            for symbol, name in futures_symbols.items():
                try:
                    bars = self.alpaca.get_historical_data(symbol, days=2, timeframe='1Day')
                    if len(bars) >= 2:
                        prev_close = bars.iloc[-2]['close']
                        current_price = bars.iloc[-1]['close']
                        change_pct = ((current_price - prev_close) / prev_close) * 100
                        
                        futures_data[symbol] = {
                            'name': name,
                            'price': float(current_price),
                            'change_pct': round(change_pct, 2),
                            'prev_close': float(prev_close)
                        }
                        logger.info(f"   ✓ {name}: {change_pct:+.2f}%")
                except Exception as e:
                    logger.debug(f"   Failed to get {symbol}: {e}")
            
            # Step 2: Check overnight analysis results
            overnight_research = {}
            from pathlib import Path
            research_file = Path('logs/overnight_analysis.json')
            
            if research_file.exists():
                try:
                    with open(research_file, 'r') as f:
                        all_research = json.load(f)
                        # Get most recent analysis for each symbol
                        for symbol in self.agent.symbols:
                            symbol_research = [r for r in all_research if r.get('symbol') == symbol]
                            if symbol_research:
                                latest = symbol_research[-1]
                                overnight_research[symbol] = {
                                    'iterations': latest.get('iterations', 0),
                                    'recommendation': latest.get('final_recommendation', {}),
                                    'depth': latest.get('analysis_depth', 'unknown')
                                }
                        logger.info(f"   ✓ Loaded overnight research for {len(overnight_research)} stocks")
                except Exception as e:
                    logger.debug(f"   Could not load overnight research: {e}")
            
            # Step 3: Get watchlist current prices
            watchlist_data = {}
            for symbol in self.agent.symbols:
                try:
                    bars = self.alpaca.get_historical_data(symbol, days=2, timeframe='1Day')
                    if len(bars) >= 2:
                        prev_close = bars.iloc[-2]['close']
                        current_price = bars.iloc[-1]['close']
                        change_pct = ((current_price - prev_close) / prev_close) * 100
                        
                        watchlist_data[symbol] = {
                            'price': float(current_price),
                            'prev_close': float(prev_close),
                            'change_pct': round(change_pct, 2)
                        }
                except Exception as e:
                    logger.debug(f"   Failed to get {symbol}: {e}")
            
            # Step 4: Build comprehensive prompt for LLM
            logger.info("   🤖 Querying LLM for morning synthesis...")
            
            prompt = f"""
OVERNIGHT MARKET SUMMARY - {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}

You are preparing the morning briefing for a day trader. Synthesize overnight developments into actionable insights.

=== FUTURES PERFORMANCE ===
{json.dumps(futures_data, indent=2) if futures_data else "Data unavailable"}

=== WATCHLIST STATUS ===
{json.dumps(watchlist_data, indent=2) if watchlist_data else "Data unavailable"}

=== OVERNIGHT DEEP RESEARCH ===
{json.dumps(overnight_research, indent=2) if overnight_research else "No overnight research available"}

=== YOUR TASK ===

Provide a concise morning brief covering:

1. MARKET SENTIMENT (2-3 sentences):
   - Overall market direction based on futures
   - Risk-on or risk-off environment?
   - Any concerning moves overnight?

2. KEY WATCHLIST INSIGHTS (bullet points):
   - Which stocks show strength/weakness vs market?
   - Any gap up/down situations forming?
   - Stocks to prioritize today based on overnight research

3. TODAY'S FOCUS (3-4 action items):
   - Specific stocks to watch closely at open
   - Key price levels to monitor
   - Risk management adjustments if needed

4. WATCH OUTS (if any):
   - Unusual overnight moves requiring caution
   - Potential volatility sources today
   - Positions to avoid or reduce

Keep it concise, actionable, and focused on TODAY's trading decisions.

Respond in JSON format:
{{
    "market_sentiment": "2-3 sentence summary",
    "sentiment_score": 0-100 (0=very bearish, 50=neutral, 100=very bullish),
    "watchlist_insights": [
        {{"symbol": "AAPL", "note": "Brief insight", "priority": "HIGH/MEDIUM/LOW"}},
        ...
    ],
    "todays_focus": ["action item 1", "action item 2", ...],
    "watch_outs": ["concern 1", "concern 2", ...],
    "key_levels": {{"SPY": 450.00, "QQQ": 380.00, ...}},
    "overall_strategy": "AGGRESSIVE/NORMAL/CAUTIOUS"
}}
"""
            
            # Query LLM
            response = self.llm_bridge.query_llm(prompt, symbol='OVERNIGHT_SUMMARY')
            
            # Parse response
            summary = None
            try:
                # Try direct JSON parse
                summary = json.loads(response)
            except json.JSONDecodeError:
                # Try extracting JSON from markdown
                import re
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
                if json_match:
                    summary = json.loads(json_match.group(1))
                else:
                    # Fallback: store raw response
                    summary = {
                        'raw_response': response,
                        'parsed': False
                    }
            
            # Log key findings
            if summary and summary.get('parsed') != False:
                logger.info(f"   📈 Market Sentiment Score: {summary.get('sentiment_score', 'N/A')}/100")
                logger.info(f"   🎯 Strategy: {summary.get('overall_strategy', 'N/A')}")
                logger.info(f"   🔍 High Priority Stocks: {len([s for s in summary.get('watchlist_insights', []) if s.get('priority') == 'HIGH'])}")
                logger.info(f"   ⚠️  Watch Outs: {len(summary.get('watch_outs', []))}")
                
                # Log top insights
                for insight in summary.get('watchlist_insights', [])[:3]:
                    logger.info(f"      • {insight.get('symbol')}: {insight.get('note')}")
            
            # Save to log
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'task': 'overnight_summary',
                'futures_data': futures_data,
                'watchlist_count': len(watchlist_data),
                'research_count': len(overnight_research),
                'summary': summary
            }
            
            log_file = Path('logs/overnight_summary.jsonl')
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
            
            logger.info(f"   ✅ Overnight summary complete and saved")
            
            return {
                "status": "success",
                "task": "overnight_summary",
                "summary": summary,
                "data_sources": {
                    "futures": len(futures_data),
                    "watchlist": len(watchlist_data),
                    "research": len(overnight_research)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Overnight summary failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            
            return {
                "status": "error",
                "task": "overnight_summary",
                "error": str(e)
            }
    
    def premarket_scanner(self) -> Dict[str, Any]:
        """
        Scan for pre-market movers (7:00 AM).
        
        Identifies:
        - Gap up/down stocks
        - Unusual pre-market volume
        - News-driven movers
        - Trading opportunities at open
        
        Uses LLM to analyze pre-market data and identify best opportunities.
        
        Returns:
            Pre-market opportunities with action plan
        """
        logger.info("🔍 Scanning pre-market movers...")
        
        try:
            # Step 1: Analyze watchlist for gaps
            logger.info("   📊 Analyzing watchlist for gaps...")
            
            gap_analysis = {}
            for symbol in self.agent.symbols:
                try:
                    # Get yesterday's close and pre-market data
                    bars = self.alpaca.get_historical_data(symbol, days=2, timeframe='1Day')
                    if len(bars) >= 2:
                        yesterday_close = bars.iloc[-2]['close']
                        
                        # Get latest available price (could be pre-market or yesterday's close)
                        current_bars = self.alpaca.get_historical_data(symbol, days=1, timeframe='5Min')
                        if not current_bars.empty:
                            latest_price = current_bars.iloc[-1]['close']
                            latest_volume = current_bars['volume'].sum()
                            
                            # Calculate gap
                            gap_pct = ((latest_price - yesterday_close) / yesterday_close) * 100
                            
                            # Get technical indicators for context
                            indicators = self.agent.indicators
                            tech_bars = self.alpaca.get_historical_data(symbol, days=20, timeframe='1Day')
                            rsi = indicators.calculate_rsi(tech_bars['close'].values)
                            
                            gap_analysis[symbol] = {
                                'yesterday_close': float(yesterday_close),
                                'current_price': float(latest_price),
                                'gap_pct': round(gap_pct, 2),
                                'gap_direction': 'UP' if gap_pct > 0 else 'DOWN' if gap_pct < 0 else 'FLAT',
                                'gap_size': abs(gap_pct),
                                'volume': int(latest_volume),
                                'rsi': round(float(rsi[-1]), 2) if len(rsi) > 0 else None,
                                'is_significant': abs(gap_pct) >= 1.0  # 1%+ gap is significant
                            }
                            
                            if abs(gap_pct) >= 1.0:
                                emoji = "🚀" if gap_pct > 0 else "📉"
                                logger.info(f"   {emoji} {symbol}: {gap_pct:+.2f}% gap (RSI: {gap_analysis[symbol]['rsi']})")
                                
                except Exception as e:
                    logger.debug(f"   Failed to analyze {symbol}: {e}")
            
            # Step 2: Get sector/market context
            logger.info("   🌐 Checking market context...")
            
            market_context = {}
            indices = ['SPY', 'QQQ', 'IWM']
            for symbol in indices:
                try:
                    bars = self.alpaca.get_historical_data(symbol, days=2, timeframe='1Day')
                    if len(bars) >= 2:
                        prev_close = bars.iloc[-2]['close']
                        current = bars.iloc[-1]['close']
                        change = ((current - prev_close) / prev_close) * 100
                        market_context[symbol] = round(change, 2)
                except Exception as e:
                    logger.debug(f"   Failed to get {symbol}: {e}")
            
            # Step 3: Load overnight summary if available
            overnight_context = None
            from pathlib import Path
            summary_file = Path('logs/overnight_summary.jsonl')
            
            if summary_file.exists():
                try:
                    # Read last line (most recent summary)
                    with open(summary_file, 'r') as f:
                        lines = f.readlines()
                        if lines:
                            last_entry = json.loads(lines[-1])
                            overnight_context = last_entry.get('summary', {})
                            logger.info(f"   ✓ Loaded overnight summary context")
                except Exception as e:
                    logger.debug(f"   Could not load overnight summary: {e}")
            
            # Step 4: Build LLM prompt for opportunity analysis
            logger.info("   🤖 Querying LLM for opportunity analysis...")
            
            # Identify significant movers
            significant_gaps = {k: v for k, v in gap_analysis.items() if v.get('is_significant', False)}
            
            prompt = f"""
PRE-MARKET SCANNER ANALYSIS - {datetime.now().strftime('%I:%M %p')}

You are scanning for the best trading opportunities at today's market open (9:30 AM).

=== MARKET CONTEXT ===
{json.dumps(market_context, indent=2) if market_context else "Data unavailable"}

=== OVERNIGHT SUMMARY ===
{json.dumps(overnight_context, indent=2) if overnight_context else "No overnight summary available"}

=== WATCHLIST GAP ANALYSIS ===
{json.dumps(gap_analysis, indent=2)}

=== SIGNIFICANT GAPS (>1%) ===
{json.dumps(significant_gaps, indent=2) if significant_gaps else "No significant gaps detected"}

=== YOUR TASK ===

Identify the TOP 3 trading opportunities for market open. For each:

1. GAP ANALYSIS:
   - Gap up/down significant enough to trade?
   - Gap likely to fill or continue?
   - What's driving the gap?

2. ENTRY STRATEGY:
   - Wait for pullback or chase immediately?
   - Specific entry price or condition
   - Position size recommendation (% of capital)

3. RISK MANAGEMENT:
   - Stop loss level
   - Take profit target(s)
   - Maximum hold time

4. PROBABILITY ASSESSMENT:
   - Win probability (0-100%)
   - Risk/reward ratio
   - Confidence in setup

Also identify any stocks to AVOID today (gaps that look like traps).

Respond in JSON format:
{{
    "market_bias": "BULLISH/BEARISH/NEUTRAL",
    "gap_count": {{"up": X, "down": Y, "significant": Z}},
    "top_opportunities": [
        {{
            "rank": 1,
            "symbol": "AAPL",
            "opportunity_type": "GAP_AND_GO/GAP_FILL/BREAKOUT/etc",
            "entry_strategy": "Wait for 9:35 pullback to $260",
            "entry_price": 260.00,
            "stop_loss": 255.00,
            "take_profit": 268.00,
            "position_size_pct": 15,
            "win_probability": 70,
            "risk_reward_ratio": 2.67,
            "confidence": 85,
            "reasoning": "Why this is a good setup"
        }},
        ...
    ],
    "stocks_to_avoid": [
        {{
            "symbol": "TSLA",
            "reason": "Gap up on low volume, likely trap",
            "risk": "HIGH"
        }}
    ],
    "key_levels_to_watch": {{"SPY": 450.00, "QQQ": 380.00, ...}},
    "overall_strategy": "AGGRESSIVE/SELECTIVE/DEFENSIVE"
}}
"""
            
            # Query LLM
            response = self.llm_bridge.query_llm(prompt, symbol='PREMARKET_SCANNER')
            
            # Parse response
            opportunities = None
            try:
                # Try direct JSON parse
                opportunities = json.loads(response)
            except json.JSONDecodeError:
                # Try extracting JSON from markdown
                import re
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
                if json_match:
                    opportunities = json.loads(json_match.group(1))
                else:
                    # Fallback
                    opportunities = {
                        'raw_response': response,
                        'parsed': False
                    }
            
            # Log key findings
            if opportunities and opportunities.get('parsed') != False:
                logger.info(f"   🎯 Market Bias: {opportunities.get('market_bias', 'N/A')}")
                logger.info(f"   🚀 Top Opportunities: {len(opportunities.get('top_opportunities', []))}")
                logger.info(f"   ⚠️  Stocks to Avoid: {len(opportunities.get('stocks_to_avoid', []))}")
                
                # Log top 3 opportunities
                for i, opp in enumerate(opportunities.get('top_opportunities', [])[:3], 1):
                    logger.info(f"   #{i}. {opp.get('symbol')} - {opp.get('opportunity_type')}")
                    logger.info(f"       Entry: ${opp.get('entry_price')}, Target: ${opp.get('take_profit')}, R/R: {opp.get('risk_reward_ratio')}:1")
                    logger.info(f"       Confidence: {opp.get('confidence')}%, Win Rate: {opp.get('win_probability')}%")
            
            # Save to log
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'task': 'premarket_scanner',
                'gap_analysis': gap_analysis,
                'significant_gaps_count': len(significant_gaps),
                'market_context': market_context,
                'opportunities': opportunities
            }
            
            log_file = Path('logs/premarket_scanner.jsonl')
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
            
            logger.info(f"   ✅ Pre-market scan complete and saved")
            
            return {
                "status": "success",
                "task": "premarket_scanner",
                "opportunities": opportunities,
                "gaps_analyzed": len(gap_analysis),
                "significant_gaps": len(significant_gaps)
            }
            
        except Exception as e:
            logger.error(f"❌ Pre-market scanner failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            
            return {
                "status": "error",
                "task": "premarket_scanner",
                "error": str(e)
            }
    
    def market_open_prep(self) -> Dict[str, Any]:
        """
        Final preparation for market open (9:00 AM).
        
        Finalizes:
        - Today's watchlist
        - Key levels to watch
        - Position sizing plan
        
        Returns:
            Market open game plan
        """
        logger.info("🎯 Finalizing market open preparation...")
        
        # Get market status
        market_status = self.alpaca.get_market_status()
        logger.info(f"   Market opens in: {market_status.get('time_until', 'Unknown')}")
        
        # Review watchlist
        logger.info(f"   Today's watchlist: {', '.join(self.agent.symbols)}")
        
        return {
            "status": "success",
            "task": "market_open_prep",
            "watchlist": self.agent.symbols
        }
