# Replay Learning System - Design Document

## 🎯 Vision: Self-Improving Trading Agent

Transform the timeline replay into a **learning and training system** where WawaTrader can:
- Re-run historical scenarios with current logic
- Compare past decisions vs current strategy
- Learn from successes and failures
- Auto-adjust parameters based on outcomes
- Continuously improve through backtesting

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    REPLAY LEARNING SYSTEM                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    │
│  │   Replay     │    │  Re-execute  │    │   Compare    │    │
│  │   Engine     │───▶│   Trading    │───▶│   Results    │    │
│  │  (Existing)  │    │    Logic     │    │              │    │
│  └──────────────┘    └──────────────┘    └──────────────┘    │
│         │                    │                    │            │
│         │                    │                    │            │
│         ▼                    ▼                    ▼            │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    │
│  │   Feed       │    │   Collect    │    │   Learn &    │    │
│  │  Historical  │    │   Metrics    │    │   Adjust     │    │
│  │    Data      │    │              │    │              │    │
│  └──────────────┘    └──────────────┘    └──────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Components to Build

### 1. **Learning Engine** (`wawatrader/learning_engine.py`)

Orchestrates the learning process:

```python
class LearningEngine:
    """
    Re-runs historical scenarios and learns from outcomes.
    """
    
    def replay_and_learn(self, start_time, end_time):
        """
        Main learning loop:
        1. Get historical events from ReplayEngine
        2. Feed to TradingAgent as if real-time
        3. Collect decisions and outcomes
        4. Compare with actual historical decisions
        5. Analyze performance and adjust
        """
        
    def compare_decisions(self, historical, current):
        """
        Compare what agent decided then vs now:
        - Same decision → Validate strategy consistency
        - Different decision → Analyze why (market data changed? LLM improved?)
        - Better outcome → Reinforce learning
        - Worse outcome → Identify improvement areas
        """
        
    def analyze_performance(self, decisions, outcomes):
        """
        Calculate metrics:
        - Win rate improvement
        - Risk-adjusted returns
        - Decision accuracy
        - LLM confidence calibration
        """
        
    def auto_adjust_parameters(self, analysis):
        """
        Automatically tune:
        - Risk limits (max_position_size, daily_loss_limit)
        - LLM confidence thresholds
        - Technical indicator weights
        - Entry/exit rules
        """
```

### 2. **Simulated Trading Agent** (`wawatrader/sim_trading_agent.py`)

Runs the trading logic without real money:

```python
class SimulatedTradingAgent:
    """
    Wraps TradingAgent for simulation mode.
    - Uses historical market data
    - Paper trades only (no real orders)
    - Tracks simulated P&L
    - Records all decisions for analysis
    """
    
    def __init__(self, replay_engine):
        self.replay_engine = replay_engine
        self.trading_agent = TradingAgent(simulation_mode=True)
        self.sim_portfolio = SimulatedPortfolio()
        
    def process_event(self, event):
        """
        Feed historical event to agent as if real-time:
        - Market data → Update indicators
        - Account snapshot → Sync sim portfolio
        - LLM conversation → Re-run analysis
        - Decision → Execute in sim mode
        """
        
    def get_sim_results(self):
        """
        Return simulation results:
        - Final portfolio value
        - Total return %
        - Sharpe ratio
        - Max drawdown
        - Win/loss ratio
        - All decisions with outcomes
        """
```

### 3. **Decision Comparator** (`wawatrader/decision_comparator.py`)

Analyzes differences between past and present:

```python
class DecisionComparator:
    """
    Compares historical decisions with current strategy.
    """
    
    def compare(self, historical_decision, current_decision, actual_outcome):
        """
        Returns comparison report:
        - Action match: Same/Different
        - Confidence delta: How much more/less confident now
        - Reasoning change: Why different decision?
        - Outcome analysis: Would new decision be better?
        - Market context: What changed in data?
        """
        
    def identify_patterns(self, comparisons):
        """
        Find patterns in decision differences:
        - Consistently better/worse in certain conditions
        - LLM improvements over time
        - Market regime changes
        - Strategy drift
        """
```

### 4. **Parameter Optimizer** (`wawatrader/parameter_optimizer.py`)

Auto-tunes system parameters:

```python
class ParameterOptimizer:
    """
    Uses historical replay to find optimal parameters.
    """
    
    def optimize(self, parameter, search_range, historical_period):
        """
        Grid search or Bayesian optimization:
        1. For each parameter value in range
        2. Re-run historical period
        3. Measure performance
        4. Find optimal value
        """
        
    def validate(self, parameters, validation_period):
        """
        Test optimized parameters on out-of-sample data
        to avoid overfitting.
        """
        
    def apply_with_confidence(self, optimized_params):
        """
        Only apply if:
        - Statistically significant improvement
        - Robust across multiple periods
        - Passes validation tests
        """
```

### 5. **Learning Dashboard** (`wawatrader/learning_dashboard.py`)

Visualize learning progress:

```python
class LearningDashboard:
    """
    New dashboard tab for learning insights.
    """
    
    Features:
    - Performance comparison charts (then vs now)
    - Decision accuracy heatmap
    - Parameter evolution over time
    - Learning curve visualization
    - Improvement suggestions
    - Confidence calibration plots
```

---

## 🔄 Learning Workflows

### Workflow 1: **Nightly Learning Session**

Every night after market close:

```python
def nightly_learning():
    """
    1. Load today's events
    2. Re-run with current strategy
    3. Compare decisions
    4. Calculate performance delta
    5. Adjust parameters if improvement found
    6. Log insights for review
    """
    
    learning_engine = LearningEngine()
    
    # Get today's data
    today = datetime.now().date()
    events = replay_engine.get_events_in_range(
        start=today,
        end=today + timedelta(days=1),
        event_types=['decision', 'order_execution', 'market_data']
    )
    
    # Re-run with current strategy
    sim_results = sim_agent.replay_period(events)
    
    # Compare
    comparison = comparator.compare_day(
        historical=events,
        simulated=sim_results
    )
    
    # Learn
    if comparison.performance_improved():
        logger.info(f"✅ Strategy improved by {comparison.improvement_pct:.2f}%")
        optimizer.apply_improvements(comparison.better_params)
    else:
        logger.info("📊 No improvement found today")
```

### Workflow 2: **Parameter Optimization Run**

Optimize specific parameter:

```python
def optimize_risk_limit():
    """
    Find optimal max_position_size using last 30 days.
    """
    
    optimizer = ParameterOptimizer()
    
    # Test range: 5% to 20% position size
    best_params = optimizer.optimize(
        parameter='max_position_size',
        search_range=np.arange(5, 21, 1),  # 5%, 6%, ..., 20%
        historical_period=timedelta(days=30)
    )
    
    # Validate on different period
    validation = optimizer.validate(
        parameters=best_params,
        validation_period=timedelta(days=60, weeks=-60)  # 60 days before
    )
    
    if validation.is_robust():
        config.update(best_params)
        logger.info(f"✅ Updated max_position_size to {best_params['max_position_size']}%")
```

### Workflow 3: **Strategy Comparison**

Compare multiple strategies:

```python
def compare_strategies():
    """
    Test different strategies on same historical data.
    """
    
    strategies = [
        'aggressive',  # High confidence threshold, larger positions
        'conservative',  # Low threshold, small positions
        'adaptive',  # Dynamic based on market conditions
        'current'  # Current production strategy
    ]
    
    results = {}
    for strategy in strategies:
        sim_agent.set_strategy(strategy)
        results[strategy] = sim_agent.replay_period(
            start=datetime.now() - timedelta(days=90),
            end=datetime.now()
        )
    
    # Compare metrics
    comparison = StrategyComparison(results)
    comparison.plot_performance()
    comparison.rank_strategies()
    
    # Apply best if significantly better
    if comparison.best_strategy != 'current':
        logger.info(f"🚀 Found better strategy: {comparison.best_strategy}")
        recommendation = comparison.get_recommendation()
```

### Workflow 4: **LLM Improvement Tracking**

Track how LLM gets better over time:

```python
def track_llm_improvement():
    """
    Re-run old decisions with current LLM to see improvement.
    """
    
    # Get decisions from 1 month ago
    old_decisions = db.get_decisions(
        start=datetime.now() - timedelta(days=30),
        end=datetime.now() - timedelta(days=29)
    )
    
    # Re-run same market conditions with current LLM
    for decision in old_decisions:
        # Get market data from that time
        market_data = replay_engine.get_market_data_at(decision.timestamp)
        
        # Ask current LLM
        new_analysis = llm_bridge.analyze_now(
            symbol=decision.symbol,
            market_data=market_data
        )
        
        # Compare
        comparison = {
            'old_confidence': decision.confidence,
            'new_confidence': new_analysis['confidence'],
            'old_action': decision.action,
            'new_action': new_analysis['action'],
            'outcome': get_actual_outcome(decision),
            'improvement': calculate_improvement(decision, new_analysis)
        }
        
        log_llm_improvement(comparison)
```

---

## 💾 Data Schema Enhancements

### New Tables:

```sql
-- Track learning sessions
CREATE TABLE learning_sessions (
    id INTEGER PRIMARY KEY,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    period_start TIMESTAMP,  -- Historical period start
    period_end TIMESTAMP,    -- Historical period end
    strategy_version TEXT,
    performance_delta REAL,  -- Improvement vs historical
    decisions_analyzed INTEGER,
    parameters_adjusted JSONB,
    insights JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Store decision comparisons
CREATE TABLE decision_comparisons (
    id INTEGER PRIMARY KEY,
    learning_session_id INTEGER,
    historical_decision_id INTEGER,
    timestamp TIMESTAMP,
    symbol TEXT,
    historical_action TEXT,
    historical_confidence REAL,
    current_action TEXT,
    current_confidence REAL,
    actual_outcome REAL,
    historical_would_profit REAL,
    current_would_profit REAL,
    improvement REAL,
    reasoning_delta TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Track parameter evolution
CREATE TABLE parameter_history (
    id INTEGER PRIMARY KEY,
    parameter_name TEXT,
    old_value REAL,
    new_value REAL,
    reason TEXT,
    validation_score REAL,
    applied_at TIMESTAMP,
    performance_after_30d REAL  -- Track if it actually helped
);

-- Store optimization results
CREATE TABLE optimization_runs (
    id INTEGER PRIMARY KEY,
    parameter_name TEXT,
    search_range JSONB,
    optimal_value REAL,
    performance_improvement REAL,
    validation_period TEXT,
    validation_passed BOOLEAN,
    applied BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🎮 Dashboard Enhancements

### New Tab: "Learning & Training"

```python
layout = html.Div([
    # Section 1: Learning Status
    html.Div([
        html.H3("🎓 Learning Status"),
        html.Div([
            Card("Last Learning Session", last_session_time),
            Card("Decisions Analyzed", decisions_count),
            Card("Performance Delta", f"+{improvement}%"),
            Card("Parameters Optimized", param_count)
        ])
    ]),
    
    # Section 2: Strategy Comparison
    html.Div([
        html.H3("📊 Strategy Performance"),
        dcc.Graph(id='strategy-comparison-chart'),
        html.P("Compare current strategy vs historical decisions")
    ]),
    
    # Section 3: Parameter Evolution
    html.Div([
        html.H3("⚙️ Parameter Tuning"),
        dcc.Graph(id='parameter-evolution'),
        html.Div(id='parameter-recommendations')
    ]),
    
    # Section 4: LLM Improvement
    html.Div([
        html.H3("🤖 LLM Learning Curve"),
        dcc.Graph(id='llm-confidence-calibration'),
        dcc.Graph(id='llm-accuracy-over-time')
    ]),
    
    # Section 5: Run Learning
    html.Div([
        html.H3("▶️ Run Learning Session"),
        dcc.DatePickerRange(id='learning-period'),
        html.Button("Start Learning", id='start-learning-btn'),
        dcc.Loading(html.Div(id='learning-progress'))
    ])
])
```

---

## 🚀 Implementation Phases

### **Phase 1: Foundation** (Week 1)
- [x] ReplayEngine (Done!)
- [ ] SimulatedTradingAgent wrapper
- [ ] Basic decision comparison
- [ ] Database schema for learning data

### **Phase 2: Learning Loop** (Week 2)
- [ ] LearningEngine core loop
- [ ] Nightly learning session
- [ ] Decision comparison with outcome analysis
- [ ] Basic metrics dashboard

### **Phase 3: Optimization** (Week 3)
- [ ] ParameterOptimizer with grid search
- [ ] Validation framework
- [ ] Auto-apply improvements
- [ ] Parameter evolution tracking

### **Phase 4: Advanced Features** (Week 4)
- [ ] Multi-strategy comparison
- [ ] LLM improvement tracking
- [ ] Confidence calibration
- [ ] A/B testing framework

### **Phase 5: Dashboard** (Week 5)
- [ ] Learning dashboard tab
- [ ] Visualization of improvements
- [ ] Manual learning triggers
- [ ] Insight recommendations

---

## 💡 Learning Insights Examples

### Insight 1: "Conservative in Bull Markets"

```
🎯 Pattern Detected:
During strong uptrends (SPY +1% days), your strategy is too conservative.

Historical Performance:
- Average position size: 8% on bull days
- Win rate: 73%
- Average gain: +2.1%

Simulated with 12% positions:
- Win rate: 71% (similar)
- Average gain: +3.2% (50% better!)

Recommendation:
Increase max_position_size from 10% to 12% on days when:
- Market trend > +0.5%
- VIX < 20
- LLM confidence > 70%

Expected improvement: +$3,200 over 30 days
```

### Insight 2: "LLM Confidence Calibration"

```
🤖 LLM Analysis:
Your LLM is overconfident in the 70-80% range.

Confidence vs Outcome:
- 70-80% confidence → 58% actual win rate (should be 75%)
- 60-70% confidence → 67% actual win rate (should be 65%)

Recommendation:
Adjust confidence threshold:
- OLD: Trade if confidence > 60%
- NEW: Trade if confidence > 70%

This filters out the overconfident false positives.

Expected improvement: +12% win rate accuracy
```

### Insight 3: "Tech Stock Specialization"

```
📊 Sector Analysis:
You perform significantly better on Tech stocks.

Performance by Sector:
- Tech (AAPL, MSFT, NVDA): 68% win rate, +2.8% avg
- Finance (JPM, BAC, GS): 52% win rate, +1.1% avg
- Healthcare (UNH, JNJ): 49% win rate, +0.9% avg

Recommendation:
Focus capital on Tech sector:
- Allocate 60% of capital to Tech
- 30% to other sectors
- 10% reserve for opportunities

Expected improvement: +$5,400 over 30 days
```

---

## 🎯 Success Metrics

Track learning system effectiveness:

1. **Decision Accuracy Improvement**
   - Win rate delta (current vs historical)
   - P&L improvement when re-running old scenarios

2. **Parameter Optimization ROI**
   - Performance lift from optimized parameters
   - Robustness across different market conditions

3. **LLM Learning Curve**
   - Confidence calibration improvement
   - Decision quality over time

4. **Strategy Evolution**
   - Number of successful parameter adjustments
   - Cumulative performance improvement

5. **Time to Improvement**
   - How quickly system finds better strategies
   - Speed of parameter convergence

---

## 🔒 Safety Guardrails

1. **Validation Required**
   - Never apply parameters without validation on separate period
   - Require statistical significance (p < 0.05)

2. **Conservative Changes**
   - Limit parameter changes to ±20% per adjustment
   - Gradual rollout over multiple days

3. **Human Approval**
   - Major strategy changes require manual review
   - Dashboard shows recommendations, not auto-applies

4. **Rollback Capability**
   - Track all parameter changes
   - Easy revert if performance degrades

5. **Overfitting Detection**
   - Monitor validation vs training performance
   - Alert if gap too large

---

## 🌟 Future Possibilities

Once foundation is solid:

1. **Reinforcement Learning**
   - Train RL agent using replay as environment
   - Reward function based on actual outcomes

2. **Multi-Agent Learning**
   - Multiple strategies compete
   - Best performers get more capital

3. **Transfer Learning**
   - Learn patterns from one stock/period
   - Apply to others

4. **Ensemble Methods**
   - Combine multiple strategies
   - Weight by historical performance

5. **Continuous Learning**
   - Real-time updates as new data comes in
   - Always improving

---

## 📚 Technical References

- **Backtesting**: Walk-forward analysis, out-of-sample validation
- **Optimization**: Bayesian optimization, genetic algorithms
- **Reinforcement Learning**: Q-learning, policy gradients
- **Time Series**: Stationarity checks, regime detection

---

**This transforms WawaTrader from a trading bot into a self-improving AI system! 🚀**
