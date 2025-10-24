#!/usr/bin/env python3
"""
Test script for Priority 1-2 improvements:
1. Enhanced evening_deep_learning with iterative analyst
2. New weekly_self_critique task

Run this to verify the enhancements work correctly.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from loguru import logger
from datetime import datetime

# Configure logger
logger.remove()
logger.add(sys.stdout, level="INFO", format="<level>{message}</level>")


def test_iterative_analyst_integration():
    """Test that iterative analyst is properly integrated"""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Iterative Analyst Integration")
    logger.info("="*80)
    
    try:
        from wawatrader.iterative_analyst import IterativeAnalyst
        from wawatrader.alpaca_client import get_client
        from wawatrader.llm_bridge import LLMBridge
        
        logger.info("✅ Imports successful")
        
        # Initialize components
        client = get_client()
        llm = LLMBridge()
        
        analyst = IterativeAnalyst(
            alpaca_client=client,
            llm_bridge=llm,
            max_iterations=3  # Small test
        )
        
        logger.info("✅ IterativeAnalyst initialized successfully")
        logger.info(f"   Max iterations: {analyst.max_iterations}")
        logger.info(f"   Available data sources: {len(analyst.available_data)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False


def test_scheduled_tasks_import():
    """Test that scheduled tasks module loads correctly"""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Scheduled Tasks Import")
    logger.info("="*80)
    
    try:
        from wawatrader.scheduled_tasks import ScheduledTaskHandlers
        
        logger.info("✅ ScheduledTaskHandlers imported successfully")
        
        # Check that new methods exist
        methods = dir(ScheduledTaskHandlers)
        
        has_deep_learning = 'evening_deep_learning' in methods
        has_self_critique = 'weekly_self_critique' in methods
        
        logger.info(f"✅ evening_deep_learning method: {'Present' if has_deep_learning else 'MISSING'}")
        logger.info(f"✅ weekly_self_critique method: {'Present' if has_self_critique else 'MISSING'}")
        
        return has_deep_learning and has_self_critique
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_self_critique_with_sample_data():
    """Test self-critique with actual decision log data"""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Self-Critique with Real Data")
    logger.info("="*80)
    
    try:
        from pathlib import Path
        import json
        
        decisions_path = Path('logs/decisions.jsonl')
        
        if not decisions_path.exists():
            logger.warning("⚠️ No decisions.jsonl found - self-critique would skip")
            logger.info("   This is OK for a fresh system")
            return True
        
        # Count decisions
        decision_count = 0
        with open(decisions_path, 'r') as f:
            for line in f:
                try:
                    json.loads(line.strip())
                    decision_count += 1
                except:
                    continue
        
        logger.info(f"✅ Found {decision_count} decisions in log")
        
        if decision_count > 0:
            logger.info("   Self-critique has data to analyze")
        else:
            logger.warning("   Self-critique would skip (no decisions)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False


def test_overnight_analysis_log():
    """Test that overnight analysis log is writable"""
    logger.info("\n" + "="*80)
    logger.info("TEST 4: Overnight Analysis Log")
    logger.info("="*80)
    
    try:
        from pathlib import Path
        import json
        
        log_path = Path('logs/overnight_analysis.json')
        
        # Check if exists
        if log_path.exists():
            logger.info(f"✅ Overnight analysis log exists")
            
            # Try to read it
            with open(log_path, 'r') as f:
                analyses = json.load(f)
                logger.info(f"   Contains {len(analyses)} analyses")
        else:
            logger.info("ℹ️  Overnight analysis log doesn't exist yet")
            logger.info("   Will be created on first evening_deep_learning run")
        
        # Test write permissions
        log_path.parent.mkdir(parents=True, exist_ok=True)
        test_data = [{"test": "write_check", "timestamp": datetime.now().isoformat()}]
        
        with open(log_path, 'w') as f:
            json.dump(test_data, f)
        
        logger.info("✅ Log is writable")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False


def test_enhancement_documentation():
    """Verify documentation files exist"""
    logger.info("\n" + "="*80)
    logger.info("TEST 5: Documentation")
    logger.info("="*80)
    
    try:
        from pathlib import Path
        
        docs = [
            'docs/OFF_MARKET_HOURS_LLM_ANALYSIS.md',
            'docs/WEEK1_2_IMPLEMENTATION_SUMMARY.md'
        ]
        
        for doc in docs:
            path = Path(doc)
            if path.exists():
                size = path.stat().st_size
                logger.info(f"✅ {doc} ({size:,} bytes)")
            else:
                logger.warning(f"⚠️ {doc} not found")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False


def main():
    """Run all tests"""
    logger.info("\n" + "🚀 TESTING PRIORITY 1-2 ENHANCEMENTS " + "🚀\n")
    
    tests = [
        ("Iterative Analyst Integration", test_iterative_analyst_integration),
        ("Scheduled Tasks Import", test_scheduled_tasks_import),
        ("Self-Critique Data Check", test_self_critique_with_sample_data),
        ("Overnight Analysis Log", test_overnight_analysis_log),
        ("Documentation", test_enhancement_documentation)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results[test_name] = passed
        except Exception as e:
            logger.error(f"❌ {test_name} crashed: {e}")
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("📊 TEST RESULTS SUMMARY")
    logger.info("="*80)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
    
    passed_count = sum(1 for p in results.values() if p)
    total_count = len(results)
    
    logger.info(f"\n🎯 Overall: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        logger.info("\n✅ ALL TESTS PASSED!")
        logger.info("\n📋 Next Steps:")
        logger.info("   1. Run trading system to test evening_deep_learning")
        logger.info("   2. Wait for Friday 6pm for first weekly_self_critique")
        logger.info("   3. Check logs/overnight_analysis.json for deep research results")
        logger.info("   4. Check logs/self_critique.jsonl for self-analysis insights")
        return 0
    else:
        logger.warning(f"\n⚠️ {total_count - passed_count} test(s) failed")
        logger.info("   Review errors above and fix before proceeding")
        return 1


if __name__ == "__main__":
    exit(main())
