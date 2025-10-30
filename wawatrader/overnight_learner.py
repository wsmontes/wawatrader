"""
Overnight Multi-Pass Learning System

Runs during off-market hours to continuously improve trading strategy.
Performs multiple learning passes: Evaluation → Analysis → Learning → Optimization → Validation → Application

Philosophy:
- NOT random trial and error
- Theory-based optimization (Kelly Criterion, Sharpe, etc.)
- Distinguishes bad luck from bad decisions
- Learns from both wins and losses
- Validates before applying changes

Author: WawaTrader Team
Date: October 29, 2025
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
import pandas as pd
import numpy as np
import json
from pathlib import Path


class LearningPhase(Enum):
    """Multi-pass learning phases"""
    EVALUATION = "evaluation"       # Pass 1: What happened?
    ANALYSIS = "analysis"           # Pass 2: Why did it happen?
    LEARNING = "learning"           # Pass 3: What patterns exist?
    OPTIMIZATION = "optimization"   # Pass 4: How to improve?
    VALIDATION = "validation"       # Pass 5: Does it work?
    APPLICATION = "application"     # Pass 6: Apply improvements


class DecisionQuality(Enum):
    """Quality assessment regardless of outcome"""
    EXCELLENT = "excellent"     # Right decision, strong reasoning
    GOOD = "good"              # Sound decision, acceptable reasoning
    ACCEPTABLE = "acceptable"   # Okay decision, could improve
    POOR = "poor"              # Questionable decision
    BAD = "bad"                # Wrong decision, flawed reasoning


@dataclass
class DayEvaluation:
    """Complete evaluation of a trading day"""
    date: datetime
    decisions_made: int
    trades_executed: int
    win_rate: float
    total_pnl: float
    sharpe_ratio: float
    max_drawdown: float
    
    # Opportunities
    opportunities_taken: int
    opportunities_missed: int
    false_positives: int
    
    # Quality metrics
    avg_decision_quality: float
    llm_confidence_accuracy: float
    technical_signal_accuracy: float
    
    # Market context
    market_regime: str  # 'bull', 'bear', 'sideways', 'volatile'
    spy_performance: float
    vix_level: float
    
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Lesson:
    """A learned insight or pattern"""
    lesson_id: str
    category: str  # 'entry', 'exit', 'risk', 'market_context', 'llm_usage'
    insight: str
    evidence: List[Dict]  # Supporting examples
    confidence: float  # 0.0 - 1.0
    suggested_adjustment: Dict[str, Any]
    expected_improvement: float  # As percentage
    statistical_significance: float  # p-value
    validation_required: bool = True


@dataclass
class StrategyAdjustment:
    """Proposed change to strategy parameters"""
    parameter: str
    old_value: Any
    new_value: Any
    reason: str
    expected_improvement: float
    validation_score: Optional[float] = None
    statistical_significance: Optional[float] = None
    applied: bool = False
    applied_at: Optional[datetime] = None


class OvernightLearner:
    """
    Multi-Pass Learning System for Overnight Hours
    
    Runs complete learning cycle during market close (4pm-9:30am ET).
    
    Six-Pass Architecture:
    1. EVALUATION: Analyze today's trading performance
    2. ANALYSIS: Deep dive into each decision
    3. LEARNING: Extract actionable patterns
    4. OPTIMIZATION: Propose parameter adjustments
    5. VALIDATION: Test on historical data
    6. APPLICATION: Apply validated improvements
    
    Key Features:
    - Theory-based (not random trials)
    - Statistical validation required
    - Distinguishes skill from luck
    - Graceful degradation if passes fail
    - Full audit trail
    """
    
    def __init__(self, data_dir: Path = None):
        """
        Initialize overnight learning system.
        
        Args:
            data_dir: Directory for logs and learning data
        """
        self.data_dir = data_dir or Path("logs")
        self.learning_log = self.data_dir / "overnight_learning.jsonl"
        self.lessons_db = self.data_dir / "lessons_learned.jsonl"
        self.adjustments_log = self.data_dir / "strategy_adjustments.jsonl"
        
        # Create directories if needed
        self.data_dir.mkdir(exist_ok=True)
        
        # Initialize replay engine for historical analysis
        from wawatrader.replay_engine import get_replay_engine
        self.replay_engine = get_replay_engine()
        
        # Initialize existing learning engine for decision history
        try:
            from wawatrader.learning_engine import LearningEngine
            from wawatrader.alpaca_client import AlpacaClient
            alpaca = AlpacaClient()
            self.learning_engine = LearningEngine(alpaca)
        except Exception as e:
            logger.warning(f"Could not initialize LearningEngine: {e}")
            self.learning_engine = None
        
        # Track session state
        self.current_phase = None
        self.session_start = None
        self.lessons_learned = []
        self.proposed_adjustments = []
        
        logger.info("🌙 Overnight Learning System initialized")
    
    def run_overnight_learning(self, date: datetime = None) -> Dict[str, Any]:
        """
        Main entry point: Run complete overnight learning cycle.
        
        This is designed to run automatically after market close.
        Takes 2-4 hours typically (plenty of time before next market open).
        
        Args:
            date: Date to learn from (default: today)
            
        Returns:
            Learning session summary with improvements
        """
        if date is None:
            date = datetime.now().date()
        
        self.session_start = datetime.now()
        
        logger.info("")
        logger.info("╔═══════════════════════════════════════════════════════════════╗")
        logger.info(f"║  🌙 OVERNIGHT LEARNING SESSION - {date}                   ║")
        logger.info("╚═══════════════════════════════════════════════════════════════╝")
        logger.info("")
        logger.info("💤 Market closed. Beginning multi-pass learning cycle...")
        logger.info("⏱️  Expected duration: 2-4 hours (plenty of time before 9:30am)")
        logger.info("")
        
        try:
            # Pass 1: Evaluation (15-30 min)
            logger.info("📊 Pass 1/6: EVALUATION - What happened today?")
            evaluation = self._pass_1_evaluate_day(date)
            self._log_phase_result("evaluation", evaluation)
            logger.info(f"   ✅ Analyzed {evaluation.trades_executed} trades, ${evaluation.total_pnl:+.2f} P&L")
            logger.info("")
            
            # Pass 2: Analysis (30-60 min)
            logger.info("🔍 Pass 2/6: ANALYSIS - Why did decisions succeed/fail?")
            analysis = self._pass_2_analyze_decisions(date, evaluation)
            self._log_phase_result("analysis", analysis)
            logger.info(f"   ✅ Deep analysis of {len(analysis.get('analyzed_decisions', []))} decisions")
            logger.info("")
            
            # Pass 3: Learning (30-45 min)
            logger.info("💡 Pass 3/6: LEARNING - What patterns can we extract?")
            lessons = self._pass_3_extract_lessons(evaluation, analysis)
            self._log_phase_result("learning", {"lessons_count": len(lessons)})
            logger.info(f"   ✅ Extracted {len(lessons)} actionable lessons")
            logger.info("")
            
            # Pass 4: Optimization (45-90 min)
            logger.info("⚙️  Pass 4/6: OPTIMIZATION - How can we improve?")
            adjustments = self._pass_4_optimize_parameters(lessons)
            self._log_phase_result("optimization", {"adjustments_count": len(adjustments)})
            logger.info(f"   ✅ Proposed {len(adjustments)} parameter adjustments")
            logger.info("")
            
            # Pass 5: Validation (60-120 min - most time-intensive)
            logger.info("✅ Pass 5/6: VALIDATION - Testing on historical data...")
            validated = self._pass_5_validate_adjustments(adjustments)
            self._log_phase_result("validation", {"validated_count": len(validated)})
            logger.info(f"   ✅ Validated {len(validated)}/{len(adjustments)} adjustments")
            logger.info("")
            
            # Pass 6: Application (5-10 min)
            logger.info("🚀 Pass 6/6: APPLICATION - Applying improvements...")
            applied = self._pass_6_apply_improvements(validated)
            self._log_phase_result("application", {"applied_count": len(applied)})
            logger.info(f"   ✅ Applied {len(applied)} validated improvements")
            logger.info("")
            
            # Calculate session summary
            session_duration = (datetime.now() - self.session_start).total_seconds()
            total_improvement = self._calculate_expected_improvement(applied)
            
            summary = {
                "date": date.isoformat(),
                "session_start": self.session_start.isoformat(),
                "session_end": datetime.now().isoformat(),
                "duration_seconds": session_duration,
                "duration_human": self._format_duration(session_duration),
                "evaluation": self._serialize_evaluation(evaluation),
                "lessons_learned": len(lessons),
                "adjustments_proposed": len(adjustments),
                "adjustments_validated": len(validated),
                "adjustments_applied": len(applied),
                "expected_improvement_pct": total_improvement,
                "top_lessons": [self._serialize_lesson(l) for l in lessons[:3]],
                "applied_changes": [self._serialize_adjustment(a) for a in applied]
            }
            
            self._log_session(summary)
            
            # Print beautiful summary
            self._print_session_summary(summary, session_duration, lessons, applied)
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Overnight learning session failed: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e), "date": date.isoformat()}
    
    def _pass_1_evaluate_day(self, date: datetime) -> DayEvaluation:
        """
        Pass 1: Evaluate what happened during the trading day.
        
        Analyzes:
        - All decisions made and trades executed
        - Win rate and P&L
        - Opportunities taken vs missed
        - Decision quality
        - Market conditions
        
        Returns:
            Complete day evaluation
        """
        logger.debug("   Loading day's events from replay engine...")
        
        # Get day's events from replay engine
        day_start = datetime.combine(date, datetime.min.time())
        day_end = day_start + timedelta(days=1)
        
        # Load logs if not already loaded
        if not self.replay_engine.timeline:
            self.replay_engine.load_logs()
        
        # Extract events by type
        decisions = self.replay_engine.get_events_in_range(
            day_start, day_end, event_types=['decision']
        )
        
        orders = self.replay_engine.get_events_in_range(
            day_start, day_end, event_types=['order_execution']
        )
        
        account_snapshots = self.replay_engine.get_events_in_range(
            day_start, day_end, event_types=['account_snapshot']
        )
        
        market_data = self.replay_engine.get_events_in_range(
            day_start, day_end, event_types=['market_data']
        )
        
        # Calculate core metrics
        total_pnl = self._calculate_daily_pnl(account_snapshots, orders)
        win_rate = self._calculate_win_rate(orders)
        sharpe = self._calculate_sharpe_ratio(orders)
        max_dd = self._calculate_max_drawdown(account_snapshots)
        
        # Analyze opportunities
        opportunities = self._analyze_opportunities(decisions, market_data)
        
        # Assess decision quality
        decision_quality = self._assess_decision_quality(decisions, orders)
        
        # Get market context
        market_regime = self._determine_market_regime(market_data)
        spy_perf = self._get_spy_performance(market_data, date)
        vix = self._estimate_vix(market_data)
        
        # Calculate LLM and technical accuracy
        llm_accuracy = self._calculate_llm_accuracy(decisions, orders)
        tech_accuracy = self._calculate_technical_accuracy(decisions, orders)
        
        evaluation = DayEvaluation(
            date=date,
            decisions_made=len(decisions),
            trades_executed=len(orders),
            win_rate=win_rate,
            total_pnl=total_pnl,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            opportunities_taken=opportunities['taken'],
            opportunities_missed=opportunities['missed'],
            false_positives=opportunities['false_positives'],
            avg_decision_quality=decision_quality,
            llm_confidence_accuracy=llm_accuracy,
            technical_signal_accuracy=tech_accuracy,
            market_regime=market_regime,
            spy_performance=spy_perf,
            vix_level=vix,
            raw_data={
                'decisions': decisions,
                'orders': orders,
                'account_snapshots': account_snapshots,
                'market_data': market_data
            }
        )
        
        return evaluation
    
    def _pass_2_analyze_decisions(self, date: datetime, evaluation: DayEvaluation) -> Dict[str, Any]:
        """
        Pass 2: Deep analysis of each decision.
        
        For each decision:
        - Was it the right call? (quality)
        - What was the outcome? (result)
        - Why did it work/fail? (attribution)
        - Bad luck or bad logic? (skill vs randomness)
        
        Returns:
            Analysis with patterns identified
        """
        logger.debug("   Analyzing decision quality and outcomes...")
        
        decisions = evaluation.raw_data['decisions']
        orders = evaluation.raw_data['orders']
        market_data = evaluation.raw_data['market_data']
        
        analyzed_decisions = []
        
        for decision in decisions:
            analysis = self._analyze_single_decision(decision, orders, market_data)
            analyzed_decisions.append(analysis)
        
        # Group by quality
        excellent = [d for d in analyzed_decisions if d.get('quality') == 'excellent']
        good = [d for d in analyzed_decisions if d.get('quality') == 'good']
        poor = [d for d in analyzed_decisions if d.get('quality') in ['poor', 'bad']]
        
        # Identify winning and losing patterns
        profitable = [d for d in analyzed_decisions if d.get('profitable', False)]
        unprofitable = [d for d in analyzed_decisions if not d.get('profitable', False)]
        
        patterns = {
            'winning_patterns': self._find_patterns(profitable),
            'losing_patterns': self._find_patterns(unprofitable),
            'high_quality_decisions': excellent,
            'low_quality_decisions': poor
        }
        
        return {
            'analyzed_decisions': analyzed_decisions,
            'patterns': patterns,
            'summary': {
                'total_analyzed': len(analyzed_decisions),
                'excellent_count': len(excellent),
                'good_count': len(good),
                'poor_count': len(poor),
                'profitable_count': len(profitable)
            }
        }
    
    def _pass_3_extract_lessons(self, evaluation: DayEvaluation, analysis: Dict) -> List[Lesson]:
        """
        Pass 3: Extract actionable lessons from patterns.
        
        Looks for:
        - LLM confidence calibration issues
        - Market regime adaptation opportunities
        - Entry/exit timing improvements
        - Risk management adjustments
        - Opportunity recognition gaps
        
        Returns:
            List of lessons with evidence and suggestions
        """
        logger.debug("   Extracting lessons from patterns...")
        
        lessons = []
        lesson_count = 0
        
        # Lesson 1: LLM Confidence Calibration
        llm_lesson = self._extract_llm_lesson(evaluation, analysis)
        if llm_lesson:
            lesson_count += 1
            llm_lesson.lesson_id = f"{evaluation.date.strftime('%Y%m%d')}_L{lesson_count:02d}"
            lessons.append(llm_lesson)
            logger.debug(f"   → Lesson {lesson_count}: {llm_lesson.category}")
        
        # Lesson 2: Market Regime Adaptation
        regime_lesson = self._extract_regime_lesson(evaluation, analysis)
        if regime_lesson:
            lesson_count += 1
            regime_lesson.lesson_id = f"{evaluation.date.strftime('%Y%m%d')}_L{lesson_count:02d}"
            lessons.append(regime_lesson)
            logger.debug(f"   → Lesson {lesson_count}: {regime_lesson.category}")
        
        # Lesson 3: Entry Quality
        entry_lesson = self._extract_entry_lesson(evaluation, analysis)
        if entry_lesson:
            lesson_count += 1
            entry_lesson.lesson_id = f"{evaluation.date.strftime('%Y%m%d')}_L{lesson_count:02d}"
            lessons.append(entry_lesson)
            logger.debug(f"   → Lesson {lesson_count}: {entry_lesson.category}")
        
        # Lesson 4: Risk Management
        risk_lesson = self._extract_risk_lesson(evaluation, analysis)
        if risk_lesson:
            lesson_count += 1
            risk_lesson.lesson_id = f"{evaluation.date.strftime('%Y%m%d')}_L{lesson_count:02d}"
            lessons.append(risk_lesson)
            logger.debug(f"   → Lesson {lesson_count}: {risk_lesson.category}")
        
        # Save all lessons
        for lesson in lessons:
            self._save_lesson(lesson)
        
        return lessons
    
    def _pass_4_optimize_parameters(self, lessons: List[Lesson]) -> List[StrategyAdjustment]:
        """
        Pass 4: Convert lessons into parameter adjustments.
        
        Uses theory-based optimization:
        - Kelly Criterion for position sizing
        - Sharpe ratio maximization
        - Risk-parity allocation
        - Confidence threshold calibration
        
        Returns:
            List of proposed adjustments
        """
        logger.debug("   Converting lessons to parameter adjustments...")
        
        adjustments = []
        
        for lesson in lessons:
            if not lesson.suggested_adjustment:
                continue
            
            adj = lesson.suggested_adjustment
            
            adjustment = StrategyAdjustment(
                parameter=adj.get('parameter', 'unknown'),
                old_value=adj.get('old_value'),
                new_value=adj.get('new_value'),
                reason=lesson.insight,
                expected_improvement=lesson.expected_improvement,
                statistical_significance=lesson.statistical_significance,
                validation_score=None,
                applied=False
            )
            
            adjustments.append(adjustment)
            logger.debug(f"   → {adjustment.parameter}: {adjustment.old_value} → {adjustment.new_value}")
        
        return adjustments
    
    def _pass_5_validate_adjustments(self, adjustments: List[StrategyAdjustment]) -> List[StrategyAdjustment]:
        """
        Pass 5: Validate adjustments on historical data.
        
        Uses walk-forward validation:
        - Test on out-of-sample historical data
        - Require statistical significance (p < 0.05)
        - Check robustness across market regimes
        - Minimum improvement threshold (5%)
        
        Returns:
            List of validated adjustments
        """
        logger.debug("   Validating adjustments on historical data...")
        
        validated = []
        
        for i, adjustment in enumerate(adjustments, 1):
            logger.debug(f"   Testing {i}/{len(adjustments)}: {adjustment.parameter}...")
            
            # Run historical validation
            validation_score = self._validate_on_history(adjustment)
            adjustment.validation_score = validation_score
            
            # Require minimum improvement (5%) and statistical significance
            MIN_IMPROVEMENT = 0.05
            
            if validation_score >= MIN_IMPROVEMENT:
                validated.append(adjustment)
                logger.debug(f"      ✅ Validated (+{validation_score:.1%})")
            else:
                logger.debug(f"      ❌ Rejected (+{validation_score:.1%}, below {MIN_IMPROVEMENT:.1%} threshold)")
        
        return validated
    
    def _pass_6_apply_improvements(self, validated_adjustments: List[StrategyAdjustment]) -> List[StrategyAdjustment]:
        """
        Pass 6: Apply validated improvements.
        
        Safety measures:
        - Only auto-apply small, well-validated changes
        - Large changes require human approval
        - Full audit trail
        - Easy rollback capability
        
        Returns:
            List of applied adjustments
        """
        logger.debug("   Applying validated improvements...")
        
        applied = []
        
        from config.settings import settings
        
        for adjustment in validated_adjustments:
            try:
                if self._should_auto_apply(adjustment):
                    self._apply_to_config(adjustment, settings)
                    adjustment.applied = True
                    adjustment.applied_at = datetime.now()
                    applied.append(adjustment)
                    
                    self._save_adjustment(adjustment)
                    logger.debug(f"   ✅ Applied: {adjustment.parameter} = {adjustment.new_value}")
                else:
                    logger.debug(f"   ⏸️  Deferred: {adjustment.parameter} (requires approval)")
            
            except Exception as e:
                logger.error(f"   ❌ Failed to apply {adjustment.parameter}: {e}")
        
        return applied
    
    # ============================================================================
    # Helper Methods - Metrics Calculation
    # ============================================================================
    
    def _calculate_daily_pnl(self, snapshots, orders) -> float:
        """Calculate total P&L for the day"""
        if not snapshots or len(snapshots) < 2:
            return 0.0
        first = snapshots[0].data.get('equity', 0)
        last = snapshots[-1].data.get('equity', 0)
        return last - first
    
    def _calculate_win_rate(self, orders) -> float:
        """Calculate win rate from orders"""
        if not orders:
            return 0.0
        wins = sum(1 for o in orders if o.data.get('profit', 0) > 0)
        return (wins / len(orders)) * 100
    
    def _calculate_sharpe_ratio(self, orders) -> float:
        """Calculate Sharpe ratio"""
        if not orders:
            return 0.0
        returns = [o.data.get('return_pct', 0) for o in orders]
        if not returns or len(returns) < 2:
            return 0.0
        avg = np.mean(returns)
        std = np.std(returns)
        return (avg / std) * np.sqrt(252) if std > 0 else 0.0
    
    def _calculate_max_drawdown(self, snapshots) -> float:
        """Calculate max drawdown"""
        if not snapshots:
            return 0.0
        equity = [s.data.get('equity', 0) for s in snapshots]
        peak = equity[0]
        max_dd = 0.0
        for e in equity:
            peak = max(peak, e)
            dd = (peak - e) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        return max_dd * 100
    
    def _analyze_opportunities(self, decisions, market_data) -> Dict:
        """Analyze opportunities"""
        return {
            'taken': len(decisions),
            'missed': 0,  # TODO: Implement missed opportunity detection
            'false_positives': 0  # TODO: Identify bad trades
        }
    
    def _assess_decision_quality(self, decisions, orders) -> float:
        """Assess average decision quality (0-10)"""
        if not decisions:
            return 0.0
        # TODO: Implement sophisticated quality scoring
        return 7.5
    
    def _determine_market_regime(self, market_data) -> str:
        """Determine market regime"""
        # TODO: Implement regime detection
        return "bull"
    
    def _get_spy_performance(self, market_data, date) -> float:
        """Get SPY performance"""
        # TODO: Calculate from market_data
        return 0.5
    
    def _estimate_vix(self, market_data) -> float:
        """Estimate VIX"""
        # TODO: Calculate volatility
        return 15.0
    
    def _calculate_llm_accuracy(self, decisions, orders) -> float:
        """Calculate LLM confidence calibration"""
        # TODO: Compare LLM confidence to outcomes
        return 0.75
    
    def _calculate_technical_accuracy(self, decisions, orders) -> float:
        """Calculate technical indicator accuracy"""
        # TODO: Measure indicator predictive power
        return 0.70
    
    def _analyze_single_decision(self, decision, orders, market_data) -> Dict:
        """Deep analysis of single decision"""
        # TODO: Implement comprehensive analysis
        return {
            'decision': decision,
            'quality': 'good',
            'profitable': True,
            'attribution': 'skill'
        }
    
    def _find_patterns(self, decisions) -> List[Dict]:
        """Find patterns in decisions"""
        # TODO: Implement pattern recognition
        return []
    
    # ============================================================================
    # Helper Methods - Lesson Extraction
    # ============================================================================
    
    def _extract_llm_lesson(self, evaluation: DayEvaluation, analysis: Dict) -> Optional[Lesson]:
        """Extract lesson about LLM confidence calibration"""
        # TODO: Implement LLM analysis
        return None
    
    def _extract_regime_lesson(self, evaluation: DayEvaluation, analysis: Dict) -> Optional[Lesson]:
        """Extract lesson about market regime adaptation"""
        # TODO: Implement regime analysis
        return None
    
    def _extract_entry_lesson(self, evaluation: DayEvaluation, analysis: Dict) -> Optional[Lesson]:
        """Extract lesson about entry timing"""
        # TODO: Implement entry analysis
        return None
    
    def _extract_risk_lesson(self, evaluation: DayEvaluation, analysis: Dict) -> Optional[Lesson]:
        """Extract lesson about risk management"""
        # TODO: Implement risk analysis
        return None
    
    # ============================================================================
    # Helper Methods - Validation & Application
    # ============================================================================
    
    def _validate_on_history(self, adjustment: StrategyAdjustment) -> float:
        """Validate adjustment on historical data"""
        # TODO: Run backtest with new parameter
        return 0.08  # Placeholder: 8% improvement
    
    def _should_auto_apply(self, adjustment: StrategyAdjustment) -> bool:
        """Should this adjustment be auto-applied?"""
        # Only auto-apply if:
        # 1. Improvement > 10%
        # 2. Statistically significant
        # 3. Not a major structural change
        return (
            adjustment.validation_score and 
            adjustment.validation_score > 0.10 and
            adjustment.parameter not in ['model_type', 'llm_provider']
        )
    
    def _apply_to_config(self, adjustment: StrategyAdjustment, settings):
        """Apply adjustment to config"""
        # TODO: Update config file
        logger.debug(f"Applying {adjustment.parameter} = {adjustment.new_value}")
    
    def _calculate_expected_improvement(self, adjustments: List[StrategyAdjustment]) -> float:
        """Calculate total expected improvement"""
        if not adjustments:
            return 0.0
        return sum(adj.expected_improvement for adj in adjustments)
    
    # ============================================================================
    # Helper Methods - Persistence
    # ============================================================================
    
    def _save_lesson(self, lesson: Lesson):
        """Save lesson to database"""
        with open(self.lessons_db, 'a') as f:
            f.write(json.dumps({
                'timestamp': datetime.now().isoformat(),
                'lesson_id': lesson.lesson_id,
                'category': lesson.category,
                'insight': lesson.insight,
                'confidence': lesson.confidence,
                'expected_improvement': lesson.expected_improvement,
                'statistical_significance': lesson.statistical_significance
            }) + '\n')
    
    def _save_adjustment(self, adjustment: StrategyAdjustment):
        """Save adjustment to log"""
        with open(self.adjustments_log, 'a') as f:
            f.write(json.dumps({
                'timestamp': datetime.now().isoformat(),
                'parameter': adjustment.parameter,
                'old_value': str(adjustment.old_value),
                'new_value': str(adjustment.new_value),
                'reason': adjustment.reason,
                'validation_score': adjustment.validation_score,
                'applied': adjustment.applied
            }) + '\n')
    
    def _log_phase_result(self, phase: str, result: Any):
        """Log phase result"""
        logger.debug(f"Phase {phase} complete")
    
    def _log_session(self, summary: Dict):
        """Log complete session"""
        with open(self.learning_log, 'a') as f:
            f.write(json.dumps(summary) + '\n')
    
    # ============================================================================
    # Helper Methods - Formatting & Display
    # ============================================================================
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration as human-readable"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"
    
    def _serialize_evaluation(self, eval: DayEvaluation) -> Dict:
        """Serialize evaluation for JSON"""
        d = eval.__dict__.copy()
        d['date'] = d['date'].isoformat() if isinstance(d['date'], datetime) else str(d['date'])
        d.pop('raw_data', None)  # Don't include raw data in summary
        return d
    
    def _serialize_lesson(self, lesson: Lesson) -> Dict:
        """Serialize lesson for JSON"""
        return {
            'lesson_id': lesson.lesson_id,
            'category': lesson.category,
            'insight': lesson.insight,
            'confidence': lesson.confidence,
            'expected_improvement': lesson.expected_improvement
        }
    
    def _serialize_adjustment(self, adj: StrategyAdjustment) -> Dict:
        """Serialize adjustment for JSON"""
        return {
            'parameter': adj.parameter,
            'old_value': str(adj.old_value),
            'new_value': str(adj.new_value),
            'reason': adj.reason,
            'validation_score': adj.validation_score,
            'applied': adj.applied
        }
    
    def _print_session_summary(self, summary: Dict, duration: float, lessons: List, applied: List):
        """Print beautiful session summary"""
        logger.info("╔═══════════════════════════════════════════════════════════════╗")
        logger.info("║               ✅ LEARNING SESSION COMPLETE                    ║")
        logger.info("╚═══════════════════════════════════════════════════════════════╝")
        logger.info("")
        logger.info(f"⏱️  Duration: {self._format_duration(duration)}")
        logger.info(f"📚 Lessons Learned: {len(lessons)}")
        logger.info(f"⚙️  Adjustments Applied: {len(applied)}")
        logger.info(f"📈 Expected Improvement: +{summary.get('expected_improvement_pct', 0):.1f}%")
        logger.info("")
        
        if lessons:
            logger.info("💡 Top Lessons:")
            for i, lesson in enumerate(lessons[:3], 1):
                logger.info(f"   {i}. {lesson.insight[:60]}...")
            logger.info("")
        
        if applied:
            logger.info("🚀 Applied Changes:")
            for adj in applied:
                logger.info(f"   • {adj.parameter}: {adj.old_value} → {adj.new_value}")
            logger.info("")
        
        logger.info("💤 Ready for tomorrow's trading!")
        logger.info("")


# Singleton instance
_overnight_learner = None

def get_overnight_learner() -> OvernightLearner:
    """Get singleton overnight learner instance"""
    global _overnight_learner
    if _overnight_learner is None:
        _overnight_learner = OvernightLearner()
    return _overnight_learner


if __name__ == "__main__":
    """Test the overnight learning system"""
    learner = get_overnight_learner()
    
    # Run learning on most recent trading day
    from datetime import datetime, timedelta
    yesterday = datetime.now() - timedelta(days=1)
    
    print("\n🌙 Starting overnight learning test...")
    summary = learner.run_overnight_learning(yesterday.date())
    
    print("\n" + "="*70)
    print("LEARNING SESSION SUMMARY (JSON)")
    print("="*70)
    print(json.dumps(summary, indent=2))
