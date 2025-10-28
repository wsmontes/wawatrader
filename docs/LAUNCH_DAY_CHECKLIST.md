# Launch Day Checklist - October 28, 2025

**System Status:** 🟢 READY FOR PAPER TRADING  
**All Critical Fixes:** ✅ COMPLETE

---

## ✅ Pre-Launch Verification Complete

### Critical Fixes Applied:
1. ✅ PositionManager auto-starts with monitoring
2. ✅ Market close safety time configured (3:30 PM)
3. ✅ Graceful shutdown implemented  
4. ✅ Position synchronization between systems
5. ✅ All integration tests passing

---

## 🚀 Launch Procedure

### Step 1: Environment Check (5 min before)
```bash
cd /Users/wagnermontes/Documents/GitHub/wawatrader
source venv/bin/activate

# Verify environment
python -c "import wawatrader; print('✅ Package OK')"
python -c "from wawatrader.alpaca_client import get_client; get_client(); print('✅ Alpaca OK')"
```

### Step 2: Start System (9:00 AM)
```bash
# Option 1: Full system (recommended)
python start.py

# Option 2: Trading only (if dashboard issues)
python start.py trading
```

**Expected startup logs:**
```
🚀 WawaTrader - Live Paper Trading System with Dashboard
📊 Checking market status...
🖥️ Starting integrated dashboard...
✅ Dashboard running at http://127.0.0.1:8050
⚡ Initializing trading agent...
📡 Starting event-driven position monitoring...
✅ PositionManager monitoring active (15-second polling)
🎯 SYSTEM READY
```

### Step 3: Verify Startup (First 2 minutes)
Check logs for these critical messages:
- [ ] "PositionManager monitoring active"
- [ ] "Position manager started (polling every 15s)"
- [ ] "Market close time set: 15:30"
- [ ] Market status displayed correctly

If any missing → **STOP AND DEBUG**

---

## 📊 What to Monitor

### First Trading Cycle (9:30-9:50 AM)

**Look for:**
```
🟢 Executing trading cycle...
Analyzing AAPL...
Analyzing MSFT...
...
```

**If BUY executed:**
```
✅ Order filled @ $XXX.XX
📍 Recorded entry time for AAPL
✅ Position handed to PositionManager for monitoring
📍 NEW POSITION: AAPL
   Entry: $XXX.XX x N shares
   🎯 Take Profit 1: $XXX.XX (+X.X%)
   🎯 Take Profit 2: $XXX.XX (+X.X%)
   🛑 Stop Loss: $XXX.XX (-X.X%)
```

### Every 15 Seconds (Background)
PositionManager quietly checks prices. You won't see logs unless:
- Event triggers (TP1/TP2/stop hit)
- Problem detected

**This is GOOD - silence means monitoring working!**

### Event Triggered (When price hits target)
```
🎯 Event triggered: AAPL - TAKE_PROFIT_1
🧠 Consulting LLM: AAPL - TAKE_PROFIT_1
✅ LLM decision: SELL (confidence: 85%)
💰 EXITING 50% of AAPL: LLM: TAKE_PROFIT_1
✅ Order filled @ $XXX.XX
   Actual P&L: +X.XX%
```

---

## 🚨 Error Scenarios & Responses

### Scenario 1: LLM Not Responding
**Symptoms:**
```
⏱️ LLM timeout for AAPL after 30s
🔄 Executing fallback plan: AAPL - TAKE_PROFIT_1 -> PARTIAL_EXIT
```

**Response:** This is NORMAL! Fallback system working as designed.

**Action:** None needed unless happens repeatedly.

---

### Scenario 2: LLM Completely Down
**Symptoms:**
```
❌ 3 consecutive LLM failures, marking as OFFLINE
⚠️ LLM unavailable, executing fallback for AAPL
```

**Response:** System switches to fallback mode automatically.

**Action:** 
1. Check LM Studio is running
2. Check model loaded
3. If can't fix quickly, system will handle with fallbacks
4. Emergency exit triggers at 3:00 PM if still down

---

### Scenario 3: No Trades All Day
**Possible Reasons:**
1. Market conditions don't meet criteria (NORMAL)
2. LLM recommending HOLD (NORMAL)
3. Daily limits hit (check logs)
4. All positions at max (10 limit)

**Action:** Review logs for decision reasoning. No trades is OK if market conditions don't warrant it.

---

### Scenario 4: Excessive Trading
**Symptoms:**
- More than 5 trades in first hour
- Daily trade count approaching 20

**Response:** Daily limits will auto-stop at 20 trades.

**Action:** Review decision logs to understand why. May need to adjust confidence threshold.

---

## 🎯 Success Metrics (First Day)

### Must Haves:
- ✅ No crashes
- ✅ Positions properly monitored
- ✅ At least one event-driven exit (if position opened)
- ✅ Clean shutdown when stopped

### Good Signs:
- 📈 0-5 trades (quality over quantity)
- 📈 Hold times > 2 hours
- 📈 Transaction costs < $100
- 📈 P&L positive or small negative

### Warning Signs:
- 🚨 More than 10 trades
- 🚨 Trades < 2 hours apart
- 🚨 Multiple LLM failures
- 🚨 Any error stack traces

---

## 📝 Log Monitoring Commands

### Watch key events:
```bash
# In a separate terminal
cd /Users/wagnermontes/Documents/GitHub/wawatrader
tail -f logs/wawatrader.log | grep -E "(EXITING|Event triggered|LLM decision|Position handed|STOP)"
```

### Check position status:
```bash
# Every 30 minutes
grep "NEW POSITION\|Position CLOSED" logs/wawatrader.log | tail -10
```

### Monitor trade count:
```bash
# Check daily progress
grep "Daily metrics:" logs/wawatrader.log | tail -1
```

---

## ⏰ Timeline

### 9:00 AM - Pre-Market
- Start system
- Verify startup
- Check dashboard loading
- Pre-market scanner runs

### 9:30 AM - Market Open
- First trading cycle
- Watch for initial trades
- Monitor position handoff

### 10:00 AM - First Check
- Verify PositionManager working
- Check any positions opened
- Review decision logs

### 12:00 PM - Midday Check
- Count trades so far (expect 0-3)
- Check any events triggered
- Verify LLM health

### 3:00 PM - Pre-Close
- Final position check
- Prepare for close
- Emergency exit window (if LLM down)

### 4:00 PM - Market Close
- System continues (overnight mode)
- Review day's performance
- Check all positions closed or monitoring

### 5:00 PM - End of Day
- Stop system (Ctrl+C)
- Verify clean shutdown
- Review full logs
- Document any issues

---

## 🛑 Emergency Stop Procedure

**If system needs immediate stop:**

1. Press `Ctrl+C` in terminal
2. Wait for shutdown messages:
   ```
   🛑 Stopping trading system...
   ✅ PositionManager stopped
   🏁 Shutdown complete
   ```
3. If hangs > 10 seconds: `Ctrl+C` again (force)

**If trades need manual intervention:**
```bash
# Check current positions
python -c "from wawatrader.alpaca_client import get_client; c = get_client(); print(c.get_positions())"

# Close position manually if needed (emergency only!)
# Use Alpaca dashboard: https://app.alpaca.markets/paper/dashboard/overview
```

---

## 📞 Support Checklist

**Have ready:**
- Alpaca dashboard: https://app.alpaca.markets/paper/dashboard/overview
- LM Studio running with Gemma-3-4b loaded
- System logs: `logs/wawatrader.log`
- Decision logs: `logs/decisions.jsonl`

**Key documents:**
- `docs/PRE_LAUNCH_REVIEW.md` - Issues found & fixed
- `docs/INTEGRATION_COMPLETE.md` - System overview
- `docs/FALLBACK_SYSTEM.md` - Safety features

---

## ✅ Final Pre-Flight Check

Before clicking start tomorrow:

- [ ] Virtual environment activated
- [ ] LM Studio running
- [ ] Gemma-3-4b model loaded
- [ ] Alpaca API keys valid (check .env)
- [ ] Terminal window sized to see full logs
- [ ] Separate terminal ready for log monitoring
- [ ] Dashboard browser tab ready (http://localhost:8050)
- [ ] This checklist printed or on second monitor
- [ ] Calendar clear for first hour monitoring

---

## 🎯 Launch Command

```bash
cd /Users/wagnermontes/Documents/GitHub/wawatrader
source venv/bin/activate
python start.py
```

**Then:** Watch the logs like a hawk for the first hour. After that, periodic checks are fine.

---

**Good luck! The system is ready. All safety features are operational. 🚀**

---

**Created:** October 27, 2025  
**Launch Date:** October 28, 2025  
**System Status:** 🟢 APPROVED FOR LAUNCH
