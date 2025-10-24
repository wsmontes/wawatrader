# Test Cleanup Plan

## 📊 Current State

**Total Files**: 17 test files (4,127 lines)

### ✅ Keep (Proper pytest tests): 9 files (2,905 lines)
- `test_alerts.py` (675 lines) - Comprehensive alert system tests
- `test_learning_engine.py` (532 lines) - Learning system tests  
- `test_database.py` (527 lines) - Database operations
- `test_config_ui.py` (395 lines) - Configuration UI
- `test_backtester.py` (373 lines) - Backtesting engine
- `test_indicators.py` (366 lines) - Technical indicators
- `test_risk_manager.py` (337 lines) - Risk management
- `test_enhanced_intelligence.py` (88 lines) - Enhanced intelligence (async)
- `test_intelligence.py` (71 lines) - Market intelligence (async)

### ❌ Delete (Manual scripts): 6 files (553 lines)
- `test_alpaca.py` (179 lines) - Manual connection test
- `test_order_system.py` (117 lines) - Manual order tests (broken)
- `test_orders.py` (110 lines) - Duplicate order tests (broken)
- `test_trading_agent.py` (100 lines) - Manual agent test
- `test_lm_studio.py` (84 lines) - LM Studio connection (optional)
- `test_system.py` (71 lines) - Basic system check
- `test_dashboard_layout.py` (61 lines) - Layout verification
- `test_enhanced_dashboard.py` (58 lines) - Dashboard runner

### 🔄 Consolidate (2 files duplicated)
- `test_orders.py` + `test_order_system.py` → Already tested in `test_alpaca.py` integration

## 🎯 Actions

### Phase 1: Delete Manual Scripts
Delete 8 files that are either:
- Manual test scripts (not pytest)
- Broken/empty tests
- Dashboard runners (should be in scripts/)

### Phase 2: Create Unified Test Helpers
Create `/tests/helpers/` with reusable fixtures:
- Mock data generators
- Common assertions
- Test database setup
- API mocking utilities

### Phase 3: Create AI-Friendly Test Template
Create `/tests/test_template.py` with:
- Standard pytest structure
- Common fixtures
- Documentation for AI agents
- Examples of each test type

## 📉 Impact

**Before**: 17 files, 4,127 lines
**After**: 9 files + helpers, ~3,200 lines
**Reduction**: 8 files, ~930 lines (22% reduction)

**Benefits**:
- Clearer test structure
- Easier for AI to understand
- Faster test execution
- Better maintainability
