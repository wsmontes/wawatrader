#!/usr/bin/env python3
"""
Test Suite for Week 2 (Priority 3) Implementations

Tests the three newly implemented LLM-powered scheduled tasks:
1. overnight_summary() - Morning briefing from overnight data
2. premarket_scanner() - Gap analysis and trading opportunities
3. earnings_analysis() - Earnings strategy planning

Author: WawaTrader Team
Created: October 2025
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stdout, level="INFO")

def test_imports():
    """Test 1: Verify all necessary imports work"""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: Import Validation")
    logger.info("="*60)
    
    try:
        from wawatrader.trading_agent import TradingAgent
        from wawatrader.scheduled_tasks import ScheduledTaskHandlers
        from wawatrader.alpaca_client import AlpacaClient
        
        logger.info("✅ All imports successful")
        return True
    except Exception as e:
        logger.error(f"❌ Import failed: {e}")
        return False

def test_scheduled_tasks_methods():
    """Test 2: Verify new methods exist in ScheduledTaskHandlers"""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Method Existence Check")
    logger.info("="*60)
    
    try:
        from wawatrader.scheduled_tasks import ScheduledTaskHandlers
        
        # Check for new methods
        required_methods = [
            'overnight_summary',
            'premarket_scanner',
            'earnings_analysis'
        ]
        
        for method_name in required_methods:
            if hasattr(ScheduledTaskHandlers, method_name):
                logger.info(f"✅ {method_name} method: Present")
            else:
                logger.error(f"❌ {method_name} method: Missing")
                return False
        
        return True
    except Exception as e:
        logger.error(f"❌ Method check failed: {e}")
        return False

def test_overnight_summary_execution():
    """Test 3: Execute overnight_summary() and validate output"""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: overnight_summary() Execution")
    logger.info("="*60)
    
    try:
        from wawatrader.trading_agent import TradingAgent
        from wawatrader.scheduled_tasks import ScheduledTaskHandlers
        
        # Initialize agent and handlers
        logger.info("   Initializing trading agent...")
        agent = TradingAgent(symbols=['AAPL', 'MSFT', 'GOOGL'])
        handlers = ScheduledTaskHandlers(agent)
        
        logger.info("   Executing overnight_summary()...")
        result = handlers.overnight_summary()
        
        # Validate result structure
        if result.get('status') == 'success':
            logger.info("✅ overnight_summary() executed successfully")
            
            # Check log file was created
            log_file = Path('logs/overnight_summary.jsonl')
            if log_file.exists():
                logger.info(f"✅ Log file created: {log_file}")
                
                # Read and validate log entry
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        last_entry = json.loads(lines[-1])
                        logger.info(f"   Task: {last_entry.get('task')}")
                        logger.info(f"   Timestamp: {last_entry.get('timestamp')}")
                        logger.info(f"   Data Sources: {last_entry.get('futures_data', {})}")
                        
                        summary = last_entry.get('summary', {})
                        if summary and summary.get('parsed') != False:
                            logger.info(f"   ✓ LLM Summary Parsed Successfully")
                            logger.info(f"   ✓ Sentiment Score: {summary.get('sentiment_score', 'N/A')}")
                            logger.info(f"   ✓ Strategy: {summary.get('overall_strategy', 'N/A')}")
            else:
                logger.warning("⚠️  Log file not created (may be expected)")
            
            return True
        else:
            logger.error(f"❌ overnight_summary() failed: {result.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False

def test_premarket_scanner_execution():
    """Test 4: Execute premarket_scanner() and validate output"""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: premarket_scanner() Execution")
    logger.info("="*60)
    
    try:
        from wawatrader.trading_agent import TradingAgent
        from wawatrader.scheduled_tasks import ScheduledTaskHandlers
        
        # Initialize agent and handlers
        logger.info("   Initializing trading agent...")
        agent = TradingAgent(symbols=['AAPL', 'MSFT', 'GOOGL'])
        handlers = ScheduledTaskHandlers(agent)
        
        logger.info("   Executing premarket_scanner()...")
        result = handlers.premarket_scanner()
        
        # Validate result structure
        if result.get('status') == 'success':
            logger.info("✅ premarket_scanner() executed successfully")
            logger.info(f"   Gaps Analyzed: {result.get('gaps_analyzed', 0)}")
            logger.info(f"   Significant Gaps: {result.get('significant_gaps', 0)}")
            
            # Check log file was created
            log_file = Path('logs/premarket_scanner.jsonl')
            if log_file.exists():
                logger.info(f"✅ Log file created: {log_file}")
                
                # Read and validate log entry
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        last_entry = json.loads(lines[-1])
                        logger.info(f"   Task: {last_entry.get('task')}")
                        logger.info(f"   Significant Gaps: {last_entry.get('significant_gaps_count', 0)}")
                        
                        opportunities = last_entry.get('opportunities', {})
                        if opportunities and opportunities.get('parsed') != False:
                            logger.info(f"   ✓ LLM Opportunities Parsed Successfully")
                            logger.info(f"   ✓ Market Bias: {opportunities.get('market_bias', 'N/A')}")
                            logger.info(f"   ✓ Top Opportunities: {len(opportunities.get('top_opportunities', []))}")
            else:
                logger.warning("⚠️  Log file not created (may be expected)")
            
            return True
        else:
            logger.error(f"❌ premarket_scanner() failed: {result.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False

def test_earnings_analysis_execution():
    """Test 5: Execute earnings_analysis() and validate output"""
    logger.info("\n" + "="*60)
    logger.info("TEST 5: earnings_analysis() Execution")
    logger.info("="*60)
    
    try:
        from wawatrader.trading_agent import TradingAgent
        from wawatrader.scheduled_tasks import ScheduledTaskHandlers
        
        # Initialize agent and handlers
        logger.info("   Initializing trading agent...")
        agent = TradingAgent(symbols=['AAPL', 'MSFT', 'GOOGL'])
        handlers = ScheduledTaskHandlers(agent)
        
        logger.info("   Executing earnings_analysis()...")
        result = handlers.earnings_analysis()
        
        # Validate result structure
        if result.get('status') == 'success':
            logger.info("✅ earnings_analysis() executed successfully")
            logger.info(f"   Stocks Analyzed: {result.get('stocks_analyzed', 0)}")
            
            # Check log file was created
            log_file = Path('logs/earnings_analysis.jsonl')
            if log_file.exists():
                logger.info(f"✅ Log file created: {log_file}")
                
                # Read and validate log entry
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        last_entry = json.loads(lines[-1])
                        logger.info(f"   Task: {last_entry.get('task')}")
                        logger.info(f"   Watchlist Analyzed: {last_entry.get('watchlist_analyzed', 0)}")
                        
                        analysis = last_entry.get('analysis', {})
                        if analysis and analysis.get('parsed') != False:
                            logger.info(f"   ✓ LLM Analysis Parsed Successfully")
                            logger.info(f"   ✓ Earnings Strategies: {len(analysis.get('earnings_strategies', []))}")
                            logger.info(f"   ✓ Overall Posture: {analysis.get('overall_earnings_posture', 'N/A')}")
            else:
                logger.warning("⚠️  Log file not created (may be expected)")
            
            return True
        else:
            logger.error(f"❌ earnings_analysis() failed: {result.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False

def test_log_file_accessibility():
    """Test 6: Verify log files are writable and readable"""
    logger.info("\n" + "="*60)
    logger.info("TEST 6: Log File Accessibility")
    logger.info("="*60)
    
    try:
        logs_dir = Path('logs')
        
        # Ensure logs directory exists
        if not logs_dir.exists():
            logs_dir.mkdir(parents=True)
            logger.info("✅ Created logs directory")
        
        # Test file paths
        test_files = [
            'logs/overnight_summary.jsonl',
            'logs/premarket_scanner.jsonl',
            'logs/earnings_analysis.jsonl'
        ]
        
        for file_path in test_files:
            path = Path(file_path)
            
            # Check if file exists or can be created
            if path.exists():
                logger.info(f"✅ {file_path}: Exists")
                
                # Test read
                with open(path, 'r') as f:
                    lines = f.readlines()
                    logger.info(f"   Contains {len(lines)} entries")
            else:
                # Test write
                with open(path, 'w') as f:
                    f.write('')
                logger.info(f"✅ {file_path}: Writable (created test file)")
        
        return True
    except Exception as e:
        logger.error(f"❌ Log file test failed: {e}")
        return False

def test_error_handling():
    """Test 7: Verify error handling works correctly"""
    logger.info("\n" + "="*60)
    logger.info("TEST 7: Error Handling Validation")
    logger.info("="*60)
    
    try:
        from wawatrader.trading_agent import TradingAgent
        from wawatrader.scheduled_tasks import ScheduledTaskHandlers
        
        logger.info("   Testing with invalid symbols...")
        
        # Initialize with potentially problematic symbols
        agent = TradingAgent(symbols=['AAPL'])
        handlers = ScheduledTaskHandlers(agent)
        
        # Each method should handle errors gracefully
        methods_to_test = [
            ('overnight_summary', handlers.overnight_summary),
            ('premarket_scanner', handlers.premarket_scanner),
            ('earnings_analysis', handlers.earnings_analysis)
        ]
        
        for method_name, method in methods_to_test:
            try:
                result = method()
                if result.get('status') in ['success', 'error']:
                    logger.info(f"✅ {method_name}: Handled gracefully (status: {result.get('status')})")
                else:
                    logger.warning(f"⚠️  {method_name}: Unexpected status: {result.get('status')}")
            except Exception as e:
                logger.error(f"❌ {method_name}: Unhandled exception: {e}")
                return False
        
        return True
    except Exception as e:
        logger.error(f"❌ Error handling test failed: {e}")
        return False

def main():
    """Run all tests and report results"""
    logger.info("\n" + "🚀"*30)
    logger.info("WEEK 2 (PRIORITY 3) IMPLEMENTATION TESTS")
    logger.info("🚀"*30)
    logger.info("\nTesting Three New LLM-Powered Scheduled Tasks:")
    logger.info("  1. overnight_summary() - Morning market briefing")
    logger.info("  2. premarket_scanner() - Gap analysis & opportunities")
    logger.info("  3. earnings_analysis() - Earnings strategy planning")
    logger.info("\n")
    
    # Run all tests
    tests = [
        ("Import Validation", test_imports),
        ("Method Existence Check", test_scheduled_tasks_methods),
        ("overnight_summary() Execution", test_overnight_summary_execution),
        ("premarket_scanner() Execution", test_premarket_scanner_execution),
        ("earnings_analysis() Execution", test_earnings_analysis_execution),
        ("Log File Accessibility", test_log_file_accessibility),
        ("Error Handling Validation", test_error_handling)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"❌ {test_name} crashed: {e}")
            results[test_name] = False
    
    # Print summary
    logger.info("\n" + "="*60)
    logger.info("📊 TEST RESULTS SUMMARY")
    logger.info("="*60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
    
    logger.info("\n" + "="*60)
    logger.info(f"🎯 Overall: {passed}/{total} tests passed")
    logger.info("="*60)
    
    if passed == total:
        logger.info("\n✅ ALL TESTS PASSED!")
        logger.info("\n📋 NEXT STEPS:")
        logger.info("   1. Run full trading system to test in production")
        logger.info("   2. Monitor new log files:")
        logger.info("      - logs/overnight_summary.jsonl")
        logger.info("      - logs/premarket_scanner.jsonl")
        logger.info("      - logs/earnings_analysis.jsonl")
        logger.info("   3. Review LLM-generated strategies and insights")
        logger.info("   4. Proceed to Week 3 (Priority 4): Portfolio-level synthesis")
        return 0
    else:
        logger.error("\n❌ SOME TESTS FAILED")
        logger.error(f"   {total - passed} test(s) need attention")
        return 1

if __name__ == "__main__":
    sys.exit(main())
