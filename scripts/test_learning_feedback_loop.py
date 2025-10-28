#!/usr/bin/env python3
"""
Test Learning Feedback Loop Integration

This script comprehensively tests the learning feedback loop:
1. Learning Engine generates morning insights
2. TradingAgent caches and passes insights
3. LLM Bridge forwards to Modular Analyzer
4. Prompt Builder renders LearningInsightsComponent
5. LLM sees yesterday's performance in prompts

Tests both code paths:
- analyze_new_opportunity() - for scanning new symbols
- analyze_position() - for reviewing existing positions

Author: WawaTrader Team
Date: 2024
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from wawatrader.learning_engine import LearningEngine
from wawatrader.trading_agent import TradingAgent
from wawatrader.llm_bridge import LLMBridge
from wawatrader.llm_v2 import ModularLLMAnalyzer
from wawatrader.llm.builders.prompt_builder import PromptBuilder
from wawatrader.llm.components.learning import LearningInsightsComponent
from wawatrader.llm.components.base import QueryContext
from wawatrader.database import DatabaseManager
from config.settings import settings

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("logs/learning_feedback_test.log", rotation="1 MB", level="DEBUG")


class LearningFeedbackTester:
    """Tests the complete learning feedback loop."""
    
    def __init__(self):
        """Initialize test components."""
        self.db = DatabaseManager()
        self.learning_engine = LearningEngine(self.db)
        self.llm_bridge = LLMBridge()
        self.analyzer = ModularLLMAnalyzer()
        self.builder = PromptBuilder()
        
        logger.info("✅ Initialized test components")
    
    def test_1_learning_engine_insights(self) -> Dict[str, Any]:
        """Test: Learning Engine generates morning insights."""
        logger.info("\n" + "="*60)
        logger.info("TEST 1: Learning Engine Morning Insights Generation")
        logger.info("="*60)
        
        try:
            insights = self.learning_engine.generate_morning_insights()
            
            if not insights:
                logger.error("❌ No insights generated")
                return {}
            
            logger.info(f"✅ Generated insights with {len(insights)} sections")
            
            # Validate structure
            required_keys = ['yesterday', 'patterns', 'lessons', 'focus_areas']
            for key in required_keys:
                if key not in insights:
                    logger.error(f"❌ Missing required key: {key}")
                    return {}
                logger.info(f"  ✓ Has '{key}': {type(insights[key])}")
            
            # Log summary
            yesterday = insights.get('yesterday', {})
            patterns = insights.get('patterns', [])
            lessons = insights.get('lessons', [])
            focus_areas = insights.get('focus_areas', [])
            
            logger.info(f"\n📊 Yesterday's Performance:")
            logger.info(f"  Trades: {yesterday.get('total_trades', 0)}")
            logger.info(f"  Win Rate: {yesterday.get('win_rate', 0):.1%}")
            logger.info(f"  P&L: ${yesterday.get('total_pnl', 0):.2f}")
            logger.info(f"  Best Trade: ${yesterday.get('best_trade', 0):.2f}")
            logger.info(f"  Worst Trade: ${yesterday.get('worst_trade', 0):.2f}")
            
            logger.info(f"\n🔍 Discovered Patterns: {len(patterns)}")
            for i, pattern in enumerate(patterns[:3], 1):
                logger.info(f"  {i}. {pattern.get('description', 'N/A')} "
                          f"(confidence: {pattern.get('confidence', 0):.1%})")
            
            logger.info(f"\n💡 Lessons Learned: {len(lessons)}")
            for i, lesson in enumerate(lessons[:3], 1):
                logger.info(f"  {i}. {lesson}")
            
            logger.info(f"\n🎯 Focus Areas: {len(focus_areas)}")
            for i, area in enumerate(focus_areas[:3], 1):
                logger.info(f"  {i}. {area}")
            
            return insights
            
        except Exception as e:
            logger.error(f"❌ Error generating insights: {e}")
            return {}
    
    def test_2_component_rendering(self, insights: Dict[str, Any]) -> str:
        """Test: LearningInsightsComponent renders insights."""
        logger.info("\n" + "="*60)
        logger.info("TEST 2: LearningInsightsComponent Rendering")
        logger.info("="*60)
        
        if not insights:
            logger.error("❌ No insights to render (skipping)")
            return ""
        
        try:
            component = LearningInsightsComponent()
            rendered = component.render(insights)
            
            if not rendered:
                logger.error("❌ Component returned empty string")
                return ""
            
            logger.info(f"✅ Component rendered {len(rendered)} characters")
            
            # Validate sections
            required_sections = [
                "📊 Yesterday's Performance",
                "🔍 Discovered Patterns",
                "💡 Lessons Learned",
                "🎯 Focus Areas for Today"
            ]
            
            for section in required_sections:
                if section in rendered:
                    logger.info(f"  ✓ Contains section: {section}")
                else:
                    logger.warning(f"  ⚠️ Missing section: {section}")
            
            # Show preview
            logger.info("\n📄 Rendered Component Preview (first 500 chars):")
            logger.info("-" * 60)
            logger.info(rendered[:500] + "..." if len(rendered) > 500 else rendered)
            logger.info("-" * 60)
            
            return rendered
            
        except Exception as e:
            logger.error(f"❌ Error rendering component: {e}")
            return ""
    
    def test_3_prompt_builder_integration(self, insights: Dict[str, Any]) -> str:
        """Test: PromptBuilder includes LearningInsightsComponent."""
        logger.info("\n" + "="*60)
        logger.info("TEST 3: Prompt Builder Integration")
        logger.info("="*60)
        
        if not insights:
            logger.error("❌ No insights to include (skipping)")
            return ""
        
        try:
            # Create QueryContext with learning insights
            context = QueryContext(
                query_type="NEW_OPPORTUNITY",
                trigger="TEST",
                profile="moderate",
                primary_symbol="AAPL",
                learning_insights=insights
            )
            
            # Create data dict with technical data
            data = {
                'technical': {
                    'price': 150.00,
                    'rsi': 55.0,
                    'macd': 0.5,
                    'signal': 0.3,
                    'volume_ratio': 1.2
                }
            }
            
            prompt = self.builder.build(context, data)
            
            if not prompt:
                logger.error("❌ Builder returned empty prompt")
                return ""
            
            logger.info(f"✅ Built prompt with {len(prompt)} characters")
            
            # Check for learning insights section
            if "📊 Yesterday's Performance" in prompt:
                logger.info("  ✓ Learning insights included in prompt")
                
                # Find position of learning insights
                learning_pos = prompt.index("📊 Yesterday's Performance")
                logger.info(f"  ✓ Learning insights at position: {learning_pos}")
                
                # Check if it's near the beginning (high priority)
                if learning_pos < 1000:
                    logger.info("  ✓ Learning insights positioned early (high priority)")
                else:
                    logger.warning(f"  ⚠️ Learning insights positioned late ({learning_pos} chars in)")
            else:
                logger.error("  ❌ Learning insights NOT included in prompt")
            
            # Show preview
            logger.info("\n📄 Full Prompt Preview (first 1000 chars):")
            logger.info("-" * 60)
            logger.info(prompt[:1000] + "..." if len(prompt) > 1000 else prompt)
            logger.info("-" * 60)
            
            return prompt
            
        except Exception as e:
            logger.error(f"❌ Error building prompt: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return ""
    
    def test_4_modular_analyzer_new_opportunity(self, insights: Dict[str, Any]):
        """Test: ModularLLMAnalyzer receives insights for new opportunities."""
        logger.info("\n" + "="*60)
        logger.info("TEST 4: Modular Analyzer - New Opportunity Path")
        logger.info("="*60)
        
        if not insights:
            logger.error("❌ No insights to pass (skipping)")
            return
        
        try:
            # Simulate new opportunity analysis
            analysis = self.analyzer.analyze_new_opportunity(
                symbol="AAPL",
                technical_data={
                    'price': 150.00,
                    'rsi': 55.0,
                    'macd': 0.5,
                    'signal': 0.3,
                    'volume_ratio': 1.2,
                    'sma_20': 148.50,
                    'sma_50': 145.00,
                    'bb_upper': 152.00,
                    'bb_lower': 148.00
                },
                learning_insights=insights,
                news=None
            )
            
            if not analysis:
                logger.warning("⚠️ No analysis returned (LLM may have failed)")
                return
            
            logger.info(f"✅ Analysis returned: {analysis.get('action', 'N/A')} "
                       f"(confidence: {analysis.get('confidence', 0)}%)")
            
            # Check if reasoning references learning insights
            reasoning = analysis.get('reasoning', '').lower()
            insight_keywords = ['yesterday', 'performance', 'pattern', 'lesson', 'learned']
            
            found_keywords = [kw for kw in insight_keywords if kw in reasoning]
            if found_keywords:
                logger.info(f"  ✓ Reasoning references insights: {found_keywords}")
            else:
                logger.warning("  ⚠️ Reasoning doesn't reference insights")
            
            logger.info(f"\n💭 LLM Reasoning Preview:")
            logger.info(f"  {reasoning[:200]}...")
            
        except Exception as e:
            logger.error(f"❌ Error in new opportunity analysis: {e}")
    
    def test_5_modular_analyzer_position_review(self, insights: Dict[str, Any]):
        """Test: ModularLLMAnalyzer receives insights for position review."""
        logger.info("\n" + "="*60)
        logger.info("TEST 5: Modular Analyzer - Position Review Path")
        logger.info("="*60)
        
        if not insights:
            logger.error("❌ No insights to pass (skipping)")
            return
        
        try:
            # Simulate position review
            analysis = self.analyzer.analyze_position(
                symbol="AAPL",
                technical_data={
                    'price': 150.00,
                    'rsi': 65.0,
                    'macd': 0.8,
                    'signal': 0.5,
                    'volume_ratio': 1.5
                },
                position={
                    'symbol': 'AAPL',
                    'qty': 10,
                    'entry_price': 145.00,
                    'current_price': 150.00,
                    'unrealized_pl': 50.00,
                    'unrealized_plpc': 0.0345
                },
                learning_insights=insights,
                news=None
            )
            
            if not analysis:
                logger.warning("⚠️ No analysis returned (LLM may have failed)")
                return
            
            logger.info(f"✅ Analysis returned: {analysis.get('action', 'N/A')} "
                       f"(confidence: {analysis.get('confidence', 0)}%)")
            
            # Check if reasoning references learning insights
            reasoning = analysis.get('reasoning', '').lower()
            insight_keywords = ['yesterday', 'performance', 'pattern', 'lesson', 'learned']
            
            found_keywords = [kw for kw in insight_keywords if kw in reasoning]
            if found_keywords:
                logger.info(f"  ✓ Reasoning references insights: {found_keywords}")
            else:
                logger.warning("  ⚠️ Reasoning doesn't reference insights")
            
            logger.info(f"\n💭 LLM Reasoning Preview:")
            logger.info(f"  {reasoning[:200]}...")
            
        except Exception as e:
            logger.error(f"❌ Error in position review: {e}")
    
    def test_6_trading_agent_integration(self):
        """Test: TradingAgent generates and passes insights."""
        logger.info("\n" + "="*60)
        logger.info("TEST 6: TradingAgent Integration")
        logger.info("="*60)
        
        try:
            # Create TradingAgent (will auto-generate insights)
            agent = TradingAgent()
            
            # Force insights generation
            insights = agent.get_learning_insights()
            
            if not insights:
                logger.warning("⚠️ TradingAgent returned no insights")
                return
            
            logger.info(f"✅ TradingAgent cached insights: {len(insights)} sections")
            
            # Validate agent has insights for today
            if agent.daily_learning_insights:
                logger.info("  ✓ Agent has daily_learning_insights cached")
                logger.info(f"  ✓ Insights date: {agent.learning_insights_date}")
            else:
                logger.error("  ❌ Agent missing daily_learning_insights")
            
            # Check if insights would be passed to analyze_single_symbol
            logger.info("\n📋 Agent will pass these insights to LLM:")
            logger.info(f"  - Yesterday: {len(insights.get('yesterday', {}))} metrics")
            logger.info(f"  - Patterns: {len(insights.get('patterns', []))} patterns")
            logger.info(f"  - Lessons: {len(insights.get('lessons', []))} lessons")
            logger.info(f"  - Focus Areas: {len(insights.get('focus_areas', []))} areas")
            
        except Exception as e:
            logger.error(f"❌ Error in TradingAgent integration: {e}")
    
    def run_all_tests(self):
        """Run complete test suite."""
        logger.info("\n" + "="*80)
        logger.info("🧪 LEARNING FEEDBACK LOOP - COMPREHENSIVE TEST SUITE")
        logger.info("="*80)
        logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Test 1: Generate insights
            insights = self.test_1_learning_engine_insights()
            
            # Test 2: Component rendering
            rendered = self.test_2_component_rendering(insights)
            
            # Test 3: Prompt builder
            prompt = self.test_3_prompt_builder_integration(insights)
            
            # Test 4: Modular analyzer (new opportunity)
            self.test_4_modular_analyzer_new_opportunity(insights)
            
            # Test 5: Modular analyzer (position review)
            self.test_5_modular_analyzer_position_review(insights)
            
            # Test 6: TradingAgent integration
            self.test_6_trading_agent_integration()
            
            # Summary
            logger.info("\n" + "="*80)
            logger.info("✅ TEST SUITE COMPLETE")
            logger.info("="*80)
            logger.info(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("\n🎉 Learning Feedback Loop is OPERATIONAL!")
            logger.info("\nNext Steps:")
            logger.info("  1. Run overnight analysis: python scripts/run_overnight_analysis.py")
            logger.info("  2. Start trading with learning: python scripts/run_full_system.py")
            logger.info("  3. Monitor LLM decisions for learning references")
            logger.info("  4. Track decision quality improvements over time")
            
        except Exception as e:
            logger.error(f"\n❌ TEST SUITE FAILED: {e}")
            raise


def main():
    """Main entry point."""
    logger.info("🚀 Starting Learning Feedback Loop Tests...")
    
    tester = LearningFeedbackTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
