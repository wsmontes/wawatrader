# Dashboard Market Status Integration - Implementation Plan

## Problem Statement

The WawaTrader dashboard currently does **not show market status** (open/closed), which is critical information for users. Additionally, the dashboard should **behave differently** when the market is closed, as trading cannot occur and certain data becomes stale.

## Current Gaps

1. **No Visual Market Status Indicator** - Users can't tell at a glance if market is open or closed
2. **No Adaptive Behavior** - Dashboard treats all times the same, regardless of market hours
3. **Stale Data Display** - During market close, real-time price updates are misleading
4. **Confusing Countdown** - No indication of when market will open/close
5. **Trading Expectations** - Users may not understand why trades aren't executing

## Proposed Solution: Smart Market-Aware Dashboard

### 🎯 Design Principles

1. **Visibility**: Market status must be immediately obvious
2. **Context**: Show why certain features are inactive during market close
3. **Guidance**: Help users understand what to expect and when
4. **Accuracy**: Don't show "real-time" data when market is closed
5. **Continuity**: Dashboard remains useful even when market is closed

---

## 📋 Implementation Plan

### Phase 1: Visual Market Status Indicator (Priority: HIGH)

**Location**: Prominent header position, always visible

**Design Options**:

#### Option A: Status Badge in Header (Recommended)
```
┌──────────────────────────────────────────────────────────┐
│ WawaTrader Pro  [🟢 MARKET OPEN]  Closes in: 2h 15m     │
│                                                          │
└──────────────────────────────────────────────────────────┘

OR when closed:

┌──────────────────────────────────────────────────────────┐
│ WawaTrader Pro  [🔴 MARKET CLOSED]  Opens Mon 9:30 AM   │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Features**:
- Large, color-coded badge (Green=Open, Red=Closed)
- Countdown timer to next event (open/close)
- Day name if opening is tomorrow or later
- Pulses/animates during transition times

#### Option B: Full-Width Status Bar
```
┌──────────────────────────────────────────────────────────┐
│                   🔴 MARKET CLOSED                       │
│     Opens Monday at 9:30 AM ET (in 18 hours, 45 min)   │
│  Historical data displayed • Live trading unavailable   │
└──────────────────────────────────────────────────────────┘
```

**When to use**: Market closed (more prominent warning)

---

### Phase 2: Adaptive Dashboard Behavior (Priority: HIGH)

#### When Market is OPEN 🟢

**Behavior**:
- ✅ Real-time price updates (every 5 seconds)
- ✅ LLM analysis runs actively
- ✅ Trade execution available
- ✅ "Live" indicators visible
- ✅ Countdown to market close
- ✅ Normal update intervals

**Labels**:
- "Real-Time Data (IEX)"
- "Live Trading Active"
- "Closes in 2h 15m"

#### When Market is CLOSED 🔴

**Behavior**:
- 🔴 Price updates PAUSED or marked as "Last Close"
- 🔴 Update intervals SLOWED (30s instead of 5s)
- 🔴 LLM shows market intelligence (not trade decisions)
- 🔴 Trade buttons DISABLED with explanation
- 🔴 Countdown to market open
- 🔴 Historical data view mode

**Labels**:
- "Historical Data (Last Close Price)"
- "Live Trading Unavailable"
- "Opens Monday at 9:30 AM"
- "View-Only Mode"

**Visual Changes**:
- Dimmed/grayed out sections
- "Historical" watermark on charts
- Explanatory tooltips on disabled features

---

### Phase 3: Market Status Panel (Priority: MEDIUM)

**New Dashboard Component**: Dedicated Market Status Card

```
┌────────────────────────────────┐
│ 📊 Market Status              │
├────────────────────────────────┤
│ Status: 🔴 CLOSED             │
│ Next Open: Mon 9:30 AM ET     │
│ Time Until: 18h 45m           │
│                               │
│ Trading Hours:                │
│ Mon-Fri: 9:30 AM - 4:00 PM   │
│                               │
│ Mode: Historical Data View   │
└────────────────────────────────┘
```

**Location**: Replace or augment Performance Panel when market is closed

---

### Phase 4: Smart Data Presentation (Priority: MEDIUM)

#### Price Data Labels

**Market Open**:
```
AAPL: $175.50 ⬆ +1.25 (0.72%)
Updated: 2 seconds ago
```

**Market Closed**:
```
AAPL: $175.50 (Last Close)
Market Closed • Opens Mon 9:30 AM
```

#### Chart Behavior

**Market Open**:
- Green "LIVE" indicator
- Real-time candlesticks
- Active volume bars
- Current session highlighted

**Market Closed**:
- Gray "HISTORICAL" watermark
- Last completed day shown
- Volume data dimmed
- Extended hours shown (if available)

---

### Phase 5: User Guidance & Tooltips (Priority: LOW)

**Context-Aware Help Messages**:

When user hovers over disabled trade button during market close:
```
⚠️ Trading Unavailable
Market is currently closed.
Opens Monday at 9:30 AM ET (in 18h 45m)

During market hours, you can execute trades here.
```

When user views dashboard during market close:
```
ℹ️ View-Only Mode
Market is closed - displaying historical data.
Dashboard will automatically resume live updates when market opens.
```

---

### Phase 6: Pre-Market & After-Hours Indicators (Priority: LOW)

**Future Enhancement**: Support for extended hours

```
┌──────────────────────────────────────────────────────────┐
│ WawaTrader Pro  [🟡 PRE-MARKET]  Opens in: 45 minutes   │
└──────────────────────────────────────────────────────────┘

Status Options:
🟢 MARKET OPEN (9:30 AM - 4:00 PM)
🟡 PRE-MARKET (4:00 AM - 9:30 AM)
🟡 AFTER-HOURS (4:00 PM - 8:00 PM)
🔴 MARKET CLOSED (8:00 PM - 4:00 AM)
⚪ WEEKEND/HOLIDAY
```

---

## 🛠️ Technical Implementation

### Data Flow

```
Dashboard Component
    ↓
Call: alpaca_client.get_market_status()
    ↓
Returns: {
    'is_open': bool,
    'status_text': '🟢 OPEN',
    'status_message': 'Market is open. Closes in 2h 15m',
    'time_until': '2 hours, 15 minutes',
    'next_event': 'close',
    ...
}
    ↓
Update Dashboard:
    - Header badge
    - Data refresh intervals
    - Component visibility
    - Labels and tooltips
```

### Code Structure

```python
# New callback for market status
@app.callback(
    Output('market-status-badge', 'children'),
    Output('market-status-badge', 'className'),
    Output('main-interval', 'interval'),
    Output('chart-live-indicator', 'style'),
    Input('market-interval', 'n_intervals')
)
def update_market_status(n):
    """Update market status and adapt dashboard behavior"""
    
    status = alpaca.get_market_status()
    is_open = status.get('is_open', False)
    
    # Badge content
    badge_text = [
        html.Span(status.get('status_text', '⚠️ UNKNOWN')),
        html.Span(f" • {status.get('time_until', 'N/A')}", 
                 style={'fontSize': '11px', 'opacity': '0.8'})
    ]
    
    # Badge styling (green if open, red if closed)
    badge_class = 'market-badge-open' if is_open else 'market-badge-closed'
    
    # Update interval (5s if open, 30s if closed)
    update_interval = 5000 if is_open else 30000
    
    # Chart indicator visibility
    chart_indicator_style = {'display': 'block'} if is_open else {'display': 'none'}
    
    return badge_text, badge_class, update_interval, chart_indicator_style
```

### New Dashboard Elements

```python
# Market status badge in header
html.Div(id='market-status-badge', className='market-badge'),

# New market-specific interval
dcc.Interval(
    id='market-interval',
    interval=10000,  # Check every 10 seconds
    n_intervals=0
),

# Historical data watermark (shown when market closed)
html.Div(
    "HISTORICAL DATA",
    id='historical-watermark',
    style={'display': 'none'}
),
```

---

## 📊 Success Metrics

After implementation, users should:

1. ✅ **Immediately see** if market is open or closed
2. ✅ **Understand why** trades aren't executing (if market closed)
3. ✅ **Know when** market will open/close
4. ✅ **Recognize** historical vs live data
5. ✅ **Experience** faster dashboard during market close (reduced API calls)

---

## 🚀 Implementation Priority

### Phase 1 - Must Have (Week 1)
- [ ] Market status badge in header
- [ ] Adaptive update intervals (5s vs 30s)
- [ ] "Historical" vs "Live" data labels
- [ ] Basic market closed overlay

### Phase 2 - Should Have (Week 2)
- [ ] Dedicated market status panel
- [ ] Chart watermarks
- [ ] Disabled trade buttons with tooltips
- [ ] Countdown timers

### Phase 3 - Nice to Have (Future)
- [ ] Pre-market / after-hours support
- [ ] Animated status transitions
- [ ] Market holiday calendar
- [ ] Email/push notifications for market open

---

## 🎨 UI Mockups

### Header - Market Open
```
╔════════════════════════════════════════════════════════╗
║ 🤖 WawaTrader Pro    [🟢 MARKET OPEN • Closes in 2h]  ║
║                                              ⚙️ Config  ║
╚════════════════════════════════════════════════════════╝
```

### Header - Market Closed
```
╔════════════════════════════════════════════════════════╗
║ 🤖 WawaTrader Pro  [🔴 CLOSED • Opens Mon 9:30 AM]    ║
║                                              ⚙️ Config  ║
╚════════════════════════════════════════════════════════╝
```

### Chart Panel - Market Closed
```
┌────────────────────────────────────────┐
│  AAPL - Historical Chart         📊    │
│  🔴 Market Closed • Last Close Price   │
├────────────────────────────────────────┤
│                                        │
│     [Chart with "HISTORICAL"           │
│      watermark overlay]                │
│                                        │
└────────────────────────────────────────┘
```

---

## 📝 Additional Considerations

### Performance
- Cache market status for 10 seconds to reduce API calls
- Graceful degradation if market status API fails
- Optimize dashboard rendering when market closed

### User Experience
- Smooth transitions between open/closed states
- Clear visual hierarchy (status is immediately obvious)
- Consistent messaging across all components
- Mobile-responsive status indicators

### Edge Cases
- Early market close (holidays)
- Daylight saving time changes
- International users (always show ET)
- API failures (show "Unknown" status)

---

## 🔍 Testing Scenarios

1. **Dashboard during market hours** - Verify live indicators, 5s updates
2. **Dashboard during market close** - Verify historical labels, 30s updates
3. **Transition at market open** - Verify smooth switch to live mode
4. **Transition at market close** - Verify smooth switch to historical mode
5. **Weekend display** - Verify "Opens Monday" messaging
6. **Holiday display** - Verify next trading day detection
7. **API failure** - Verify graceful degradation

---

## 📚 Related Documentation

- `docs/MARKET_HOURS.md` - Market hours management
- `docs/API.md` - AlpacaClient.get_market_status() documentation
- `docs/USER_GUIDE.md` - User-facing market hours information

---

## Summary

This plan transforms the WawaTrader dashboard from a **static display** into a **market-aware intelligent interface** that:

✅ Shows market status prominently  
✅ Adapts behavior based on market hours  
✅ Guides users with clear context  
✅ Prevents confusion about data freshness  
✅ Improves performance during market close  

Implementation can be done incrementally, with Phase 1 (status badge + adaptive intervals) providing immediate value.
