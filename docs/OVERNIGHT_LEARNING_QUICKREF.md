# Overnight Learning System - Quick Reference

## Overview

The **Overnight Learning System** runs during off-market hours (4pm-9:30am ET) to continuously improve trading strategy through multi-pass learning cycles.

## Architecture

```
Market Close (4pm ET)
    ↓
╔════════════════════════════════════════════════════╗
║  🌙 OVERNIGHT LEARNING CYCLE (2-4 hours)          ║
╚════════════════════════════════════════════════════╝

Pass 1: EVALUATION (15-30 min)
  → Analyze today's trading performance
  → Calculate win rate, P&L, Sharpe ratio
  → Identify opportunities taken/missed

Pass 2: ANALYSIS (30-60 min)
  → Deep dive into each decision
  → Assess decision quality vs outcome
  → Distinguish skill from luck

Pass 3: LEARNING (30-45 min)
  → Extract actionable patterns
  → Identify what works/doesn't work
  → Build evidence-based insights

Pass 4: OPTIMIZATION (45-90 min)
  → Convert lessons to parameter adjustments
  → Use theory-based optimization (Kelly, Sharpe)
  → Propose concrete improvements

Pass 5: VALIDATION (60-120 min)
  → Test adjustments on historical data
  → Require statistical significance (p < 0.05)
  → Validate across market regimes

Pass 6: APPLICATION (5-10 min)
  → Apply validated improvements
  → Update configuration
  → Log all changes for audit
    ↓
Market Open (9:30am ET)
```

## Key Features

### 🎯 Theory-Based (Not Random)
- Kelly Criterion for position sizing
- Sharpe ratio optimization
- Risk-parity allocation
- Confidence calibration

### 📊 Statistical Rigor
- Distinguishes bad luck from bad decisions
- Requires p < 0.05 for significance
- Minimum 5% improvement threshold
- Out-of-sample validation

### 🛡️ Safety First
- Gradual rollout of changes
- Human approval for major changes
- Full audit trail
- Easy rollback capability

### 🔄 Continuous Improvement
- Learns every night
- Accumulates knowledge over time
- Adapts to changing markets
- Builds on past successes

## Usage

### Automatic Overnight Execution

Add to crontab for automatic nightly execution:

```bash
# Run at 4:30pm ET every weekday (after market close)
30 16 * * 1-5 cd /path/to/wawatrader && source venv/bin/activate && python -c "from wawatrader.overnight_learner import get_overnight_learner; get_overnight_learner().run_overnight_learning()"
```

### Manual Execution

```python
from wawatrader.overnight_learner import get_overnight_learner
from datetime import datetime, timedelta

# Get learner instance
learner = get_overnight_learner()

# Run learning on specific date
yesterday = datetime.now() - timedelta(days=1)
summary = learner.run_overnight_learning(yesterday.date())

# View results
print(f"Lessons learned: {summary['lessons_learned']}")
print(f"Adjustments applied: {summary['adjustments_applied']}")
print(f"Expected improvement: +{summary['expected_improvement_pct']:.1f}%")
```

### Demo Script

```bash
# Run demo
python scripts/demo_overnight_learning.py

# Run demo for specific date
python scripts/demo_overnight_learning.py 2025-10-25
```

## Learning Categories

### 1. LLM Confidence Calibration
**Insight**: "LLM is overconfident on Tech stocks"
**Adjustment**: Lower confidence threshold for Tech from 0.7 to 0.65
**Expected**: +12% accuracy improvement

### 2. Market Regime Adaptation
**Insight**: "Be more aggressive in bull markets"
**Adjustment**: Increase max_position_size from $10K to $12K in bull regimes
**Expected**: +$3,200/month

### 3. Entry Timing
**Insight**: "Morning entries outperform afternoon entries"
**Adjustment**: Prefer entries before 11am ET
**Expected**: +15% win rate

### 4. Risk Management
**Insight**: "Stop losses trigger too early in volatile markets"
**Adjustment**: Widen stops from 2% to 3% when VIX > 20
**Expected**: +8% profit factor

### 5. Opportunity Recognition
**Insight**: "Missing earnings plays in Healthcare"
**Adjustment**: Add Healthcare to high-priority sectors
**Expected**: +5 opportunities/month

## Output Files

### Learning Sessions Log
```
logs/overnight_learning.jsonl
```
Complete session history with metrics.

### Lessons Learned Database
```
logs/lessons_learned.jsonl
```
All extracted lessons with evidence and confidence scores.

### Strategy Adjustments Log
```
logs/strategy_adjustments.jsonl
```
All proposed and applied parameter changes.

## Monitoring

### Check Recent Learning

```python
import json
from pathlib import Path

# Load recent sessions
with open('logs/overnight_learning.jsonl', 'r') as f:
    sessions = [json.loads(line) for line in f]

# Get last 5 sessions
for session in sessions[-5:]:
    print(f"{session['date']}: {session['lessons_learned']} lessons, {session['adjustments_applied']} applied")
```

### View Applied Changes

```python
# Load adjustments
with open('logs/strategy_adjustments.jsonl', 'r') as f:
    adjustments = [json.loads(line) for line in f if json.loads(line)['applied']]

# Show recent changes
for adj in adjustments[-10:]:
    print(f"{adj['timestamp']}: {adj['parameter']} = {adj['new_value']}")
```

## Integration with Existing System

### Works With
- ✅ **ReplayEngine**: Uses timeline for historical analysis
- ✅ **LearningEngine**: Uses decision history database
- ✅ **AlpacaClient**: Fetches historical market data
- ✅ **Config/Settings**: Updates strategy parameters

### Complements
- **Live Trading**: Learns from real trading sessions
- **Backtesting**: Validates improvements on history
- **Dashboard**: Displays learning insights (future)

## Configuration

### Thresholds

```python
# In config/settings.py or environment variables

LEARNING_MIN_IMPROVEMENT = 0.05  # Minimum 5% improvement required
LEARNING_SIGNIFICANCE = 0.05     # p < 0.05 for statistical significance
LEARNING_AUTO_APPLY_THRESHOLD = 0.10  # Auto-apply if >10% improvement
LEARNING_VALIDATION_LOOKBACK = 30  # Days of history for validation
```

### Schedule

```python
# Recommended schedule
LEARNING_START_TIME = "16:30"  # 30 min after market close
LEARNING_MAX_DURATION = 240    # 4 hours maximum (plenty before 9:30am)
```

## Troubleshooting

### No Lessons Learned

**Cause**: Not enough trading data
**Solution**: System needs at least 10 trades to identify patterns. Continue trading and learning will improve.

### No Adjustments Applied

**Cause**: Lessons didn't pass validation threshold
**Solution**: This is working as intended. System only applies changes with strong statistical evidence.

### Long Execution Time

**Cause**: Pass 5 (Validation) is time-intensive
**Solution**: Normal. Historical backtesting takes 1-2 hours. Runs overnight when time isn't critical.

## Best Practices

### 1. Let It Run Overnight
Don't interrupt the learning cycle. It's designed to use off-market hours efficiently.

### 2. Review Weekly
Check `overnight_learning.jsonl` weekly to see learning trends over time.

### 3. Trust the Process
The system is conservative by design. It won't apply changes unless they're statistically validated.

### 4. Monitor Performance
Track whether applied changes actually improve live trading performance.

### 5. Manual Review for Big Changes
Large parameter changes (>20%) require human approval. Review these carefully.

## Future Enhancements

- [ ] Reinforcement learning integration
- [ ] Multi-strategy ensemble testing
- [ ] Transfer learning across symbols
- [ ] Real-time learning during market hours
- [ ] Learning dashboard tab
- [ ] Automated A/B testing

## Related Documentation

- `docs/REPLAY_LEARNING_SYSTEM.md` - Complete architecture
- `docs/ARCHITECTURE.md` - Overall system design
- `docs/API.md` - API documentation
- `docs/USER_GUIDE.md` - User guide

## Quick Commands

```bash
# Run learning for yesterday
python -c "from wawatrader.overnight_learner import get_overnight_learner; get_overnight_learner().run_overnight_learning()"

# Run demo
python scripts/demo_overnight_learning.py

# View recent sessions
tail -n 5 logs/overnight_learning.jsonl | python -m json.tool

# View applied changes
grep '"applied":true' logs/strategy_adjustments.jsonl | tail -n 10

# Check lesson categories
grep -o '"category":"[^"]*"' logs/lessons_learned.jsonl | sort | uniq -c
```

---

**Status**: ✅ Implemented (Phase 1 - Foundation)  
**Last Updated**: October 29, 2025  
**Next Phase**: Implement actual lesson extraction algorithms
