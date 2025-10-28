# LLM Fallback System - Safety Without LLM

## 🎯 **Philosophy**

**"Never hold a position hostage to LLM availability"**

The system must be able to protect profits and limit losses even when:
- LLM is temporarily unavailable (crashed, busy, network issue)
- LLM is blocked by another request (serial bottleneck)
- Market close is approaching and we can't consult LLM

---

## 🔄 **Three-Tier Fallback Strategy**

### **Tier 1: Immediate Execution (No LLM Needed)**
**Events**: Stop loss, trailing stop  
**Action**: Execute immediately, don't wait for LLM

```python
Event: AAPL hits stop loss @ $245
Decision: SELL immediately (0-5 seconds)
Reason: Stop is stop, no debate needed
```

### **Tier 2: Fallback Plans (LLM Unavailable)**
**Events**: Take profit, RSI flags  
**Action**: Execute predefined conservative plan

```python
Event: TSLA hits TP1 @ $257
LLM Status: Down/Busy
Decision: Execute fallback_on_tp1 = "PARTIAL_EXIT"
Result: Sell 50%, activate trailing stop for rest
```

### **Tier 3: Emergency Exit (Market Close)**
**Condition**: LLM down + <30 minutes to close  
**Action**: Force exit ALL positions

```python
Time: 3:31 PM (29 minutes to close)
LLM Status: Still down
Decision: EMERGENCY EXIT all positions
Reason: Cannot manage risk overnight without LLM
```

---

## 📋 **Fallback Plans Per Event**

### **TAKE_PROFIT_2** (High target reached)
```python
Default Plan: "FULL_EXIT"
Rationale: Lock in substantial profits (3R or ~6%)
Risk: Minimal - we're already winning

Execution:
- Sell 100% of position
- Log P&L
- Remove from tracking
```

### **TAKE_PROFIT_1** (First target reached)
```python
Default Plan: "PARTIAL_EXIT"
Rationale: Take some profit, let rest run with protection
Risk: Low - we're profitable

Execution:
- Sell 50% of position
- Activate trailing stop for remaining 50%
- Mark TP1 as processed (don't trigger again)
```

### **RSI_OVERBOUGHT** (RSI > 75)
```python
Default Plan: "FULL_EXIT"
Rationale: Avoid reversal, technical exhaustion
Risk: Medium - could be false signal

Execution:
- Sell 100% of position
- Log exit reason
- Remove from tracking
```

### **VOLUME_SPIKE** (Volume > 2x average)
```python
Default Plan: "HOLD"
Rationale: Need context - could be good or bad
Risk: Low - informational only

Execution:
- No action
- Log alert
- Wait for LLM to come back online
```

---

## 🚨 **LLM Health Tracking**

### **Failure Detection**
```python
LLM Call Attempt → Timeout (30s) OR Exception
  ↓
Mark failure: llm_consecutive_failures += 1
  ↓
If failures >= 3:
  ↓
  Declare LLM OFFLINE
  ↓
  Switch to FALLBACK mode
```

### **Recovery Detection**
```python
LLM Call Attempt → Success!
  ↓
Reset: llm_consecutive_failures = 0
  ↓
Declare LLM ONLINE
  ↓
Resume normal operation
```

### **Health Status**
```python
HEALTHY:
- llm_consecutive_failures < 3
- Last success < 5 minutes ago
- Processing events with LLM

DEGRADED:
- 1-2 consecutive failures
- Still trying LLM
- Fallbacks ready if needed

OFFLINE:
- 3+ consecutive failures
- Auto-executing fallback plans
- Emergency exit armed
```

---

## ⏰ **Market Close Safety**

### **Timeline Example (Friday 3:00 PM)**

**3:00 PM**: Normal operation
- LLM is processing events
- All good

**3:15 PM**: LLM goes offline
- Detect after 3 failed calls (~90 seconds)
- Switch to fallback mode
- **Still OK**: 45 minutes to close

**3:30 PM**: LLM still offline
- **SAFETY WINDOW TRIGGERED**: 30 minutes to close
- System checks: Any positions still open?

**If YES (positions exist)**:
```
🚨 EMERGENCY MODE ACTIVATED

Action:
1. Log emergency event
2. Iterate all open positions
3. Execute market sell orders for ALL
4. Log P&L for each
5. Clear position tracking

Reason: 
"Cannot manage risk overnight without LLM.
Better to exit flat than hold unmanaged positions."
```

**If NO (all positions already exited via fallbacks)**:
```
✅ All clear - no emergency action needed
System can safely shut down at close
```

---

## 📊 **Fallback Statistics Tracking**

The system tracks:

```python
{
    'events_triggered': 47,          # Total events detected
    'immediate_executions': 8,       # Stops executed without LLM
    'llm_consultations': 32,         # Successful LLM calls
    'fallback_executions': 7,        # Times fallback plan used
    'emergency_exits': 0,            # Market close emergencies
    
    'llm_health': {
        'status': 'HEALTHY',         # HEALTHY/DEGRADED/OFFLINE
        'consecutive_failures': 0,
        'last_success': '2025-10-27 14:32:15',
        'uptime_pct': 98.5,
    },
    
    'fallback_reasons': {
        'llm_timeout': 3,
        'llm_exception': 2,
        'llm_busy': 2,
    }
}
```

You can monitor:
- `fallback_executions` > 10/day → LLM issues, investigate
- `emergency_exits` > 0 → System forced flat, check LLM infrastructure
- `llm_health.uptime_pct` < 95% → Reliability problem

---

## 🔧 **Configuration**

### **Timeouts**
```python
llm_timeout = 30  # Max seconds to wait for LLM response
max_wait_time = 300  # Max seconds event waits in queue before escalation
```

**Tuning**:
- If LLM is fast (5-10s): Keep 30s timeout
- If LLM is slow (20-30s): Increase to 45s
- If false timeouts: Check LLM performance, not timeout setting

### **Failure Threshold**
```python
llm_failure_threshold = 3  # Consecutive failures before declaring offline
```

**Tuning**:
- More tolerant: Set to 5 (fewer false offline declarations)
- More aggressive: Set to 2 (faster fallback activation)
- Recommended: Keep at 3 (balanced)

### **Market Close Safety**
```python
pre_close_safety_minutes = 30  # Start emergency exits 30 min before close
```

**Tuning**:
- More aggressive: 45 minutes (exit earlier if LLM down)
- Less aggressive: 15 minutes (give more time for LLM recovery)
- Recommended: 30 minutes (balance safety vs. opportunity)

### **Fallback Plans**
```python
# Per position, can be customized
position.fallback_on_tp1 = "PARTIAL_EXIT"  # Options: PARTIAL_EXIT, FULL_EXIT, TRAIL_STOP
position.fallback_on_tp2 = "FULL_EXIT"     # Options: FULL_EXIT, TRAIL_STOP
position.fallback_on_rsi_high = "FULL_EXIT"  # Options: FULL_EXIT, HOLD
```

**Conservative Strategy** (default):
- TP1: PARTIAL_EXIT (take some profit, let rest run)
- TP2: FULL_EXIT (lock in big win)
- RSI: FULL_EXIT (avoid reversal)

**Aggressive Strategy**:
- TP1: TRAIL_STOP (let it all run)
- TP2: TRAIL_STOP (keep riding)
- RSI: HOLD (don't exit on technicals)

**Balanced Strategy**:
- TP1: PARTIAL_EXIT
- TP2: TRAIL_STOP (let big winner run)
- RSI: FULL_EXIT

---

## 🎯 **Decision Flow**

```
Event Triggered (e.g., AAPL hits TP1)
  │
  ├─> Is event CRITICAL (stop loss)?
  │   YES → Execute immediately (Tier 1)
  │   NO ↓
  │
  ├─> Does event allow fallback?
  │   NO → Must wait for LLM
  │   YES ↓
  │
  ├─> Is LLM healthy?
  │   YES → Add to LLM queue, process normally
  │   NO ↓
  │
  ├─> Execute fallback plan (Tier 2)
      │
      └─> Log: "FALLBACK: AAPL TP1 → PARTIAL_EXIT (LLM offline)"

Meanwhile (every 15 seconds):
  │
  ├─> Check time to market close
  │   > 30 min → Continue
  │   < 30 min AND LLM offline ↓
  │
  └─> EMERGENCY EXIT all positions (Tier 3)
```

---

## ✅ **Benefits**

1. **Never Stuck**: Always have a path forward, even if LLM fails
2. **Conservative**: Fallback plans prioritize capital preservation
3. **Fast**: No waiting for LLM timeout on critical stops
4. **Safe**: Won't hold unmanaged overnight positions
5. **Monitored**: Track fallback usage to detect LLM issues

---

## 🚨 **Warning Signs to Watch**

### **High Fallback Rate**
```
fallback_executions > 30% of events
```
**Problem**: LLM is unreliable  
**Action**: Investigate LLM health, check logs, verify timeout settings

### **Emergency Exits Triggered**
```
emergency_exits > 0 (should be rare!)
```
**Problem**: LLM was down for extended period near close  
**Action**: Critical issue - check LLM service, may need restart/fix

### **Long Queue Wait Times**
```
avg_queue_wait > 120 seconds
```
**Problem**: LLM too slow or too many events  
**Action**: Optimize LLM, reduce monitoring frequency, or increase poll interval

---

## 📝 **Example Scenarios**

### **Scenario 1: Normal Operation**
```
10:30 AM - AAPL hits TP1 @ $257
  └─> LLM healthy
  └─> Add to queue (2 events ahead)
  └─> Process in 45 seconds
  └─> LLM says: "Strong momentum, hold with trailing stop"
  └─> Execute: Activate trailing stop
  └─> ✅ Normal operation
```

### **Scenario 2: LLM Temporarily Busy**
```
2:15 PM - TSLA hits TP2 @ $265
  └─> LLM processing GOOGL (busy)
  └─> Add to queue (priority: HIGH)
  └─> Wait 20 seconds
  └─> Process when GOOGL completes
  └─> ✅ Slight delay, but handled
```

### **Scenario 3: LLM Offline**
```
1:45 PM - MSFT hits TP1 @ $442
  └─> Try LLM call → Timeout (30s)
  └─> Failure #1, retry
  └─> Try LLM call → Timeout (30s)
  └─> Failure #2, retry
  └─> Try LLM call → Timeout (30s)
  └─> Failure #3 → Declare LLM OFFLINE
  └─> Execute fallback: PARTIAL_EXIT
  └─> Sell 50%, activate trailing stop
  └─> ⚠️ Fallback mode active
```

### **Scenario 4: Emergency Exit**
```
3:32 PM - LLM still offline (been down since 1:45 PM)
  └─> Check: Time to close = 28 minutes
  └─> Check: LLM health = OFFLINE
  └─> Check: Open positions = 3 (AAPL, MSFT, META)
  └─> 🚨 EMERGENCY MODE
  └─> Execute market sells:
      ├─> AAPL: Sell 100 shares @ $256.50 → +2.6% profit
      ├─> MSFT: Sell 50 shares @ $441.20 → +0.8% profit
      └─> META: Sell 25 shares @ $523.10 → -0.3% loss
  └─> All positions closed
  └─> 🚨 Emergency exit complete
  └─> Total: +$427 (after emergency)
```

---

## 🔧 **Testing Recommendations**

### **Test 1: LLM Timeout**
```python
# Simulate LLM timeout
def test_llm_timeout():
    # Force LLM to timeout
    mock_llm.set_timeout(100)  # Force timeout
    
    # Trigger TP1 event
    event = create_tp1_event("AAPL", 257.00)
    
    # Verify fallback executed
    assert event.fallback_executed == True
    assert "PARTIAL_EXIT" in logs
```

### **Test 2: LLM Offline Detection**
```python
def test_llm_offline():
    # Cause 3 consecutive failures
    for i in range(3):
        mock_llm.fail_next_call()
        process_event(test_event)
    
    # Verify offline detected
    assert llm_queue.is_llm_healthy() == False
    assert "LLM OFFLINE" in logs
```

### **Test 3: Emergency Exit**
```python
def test_emergency_exit():
    # Set time to 3:35 PM (25 min to close)
    mock_time("15:35:00")
    
    # Set LLM offline
    llm_queue.llm_available = False
    
    # Add positions
    add_position("AAPL", entry=250, current=256)
    add_position("TSLA", entry=400, current=405)
    
    # Trigger safety check
    position_manager.check_market_close_safety()
    
    # Verify emergency exit
    assert len(positions) == 0
    assert "EMERGENCY EXIT" in logs
```

---

## 💡 **Best Practices**

1. **Monitor fallback rate**: Should be <5% of events under normal operation
2. **Test offline mode**: Periodically test by disabling LLM
3. **Review emergency exits**: If triggered, investigate root cause immediately
4. **Tune timeouts**: Based on actual LLM response times
5. **Log everything**: Fallback decisions should be traceable

---

**Remember**: The goal is never to NEED fallbacks, but always to BE READY with them! 🎯
