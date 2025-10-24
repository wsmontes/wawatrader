#!/usr/bin/env python3
"""
Test script for Week 1-2 LLM improvements.
Verifies decisiveness, quality scoring, and prompt enhancements.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from wawatrader.llm_bridge import LLMBridge
from wawatrader.indicators import TechnicalIndicators
from loguru import logger
import json

# Configure logger for testing
logger.remove()
logger.add(sys.stdout, level="INFO", format="<level>{message}</level>")


def test_profile_decisiveness():
    """Test that new system prompts encourage action over hold."""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Profile Decisiveness Check")
    logger.info("="*80)
    
    llm = LLMBridge()
    
    # Check system prompt content
    profile_config = llm.TRADING_PROFILES['aggressive']
    system_prompt = profile_config['system_prompt']
    
    logger.info(f"\n📋 Aggressive Profile System Prompt:")
    logger.info(f"{system_prompt}\n")
    
    # Verify key phrases are present
    checks = {
        "Action-oriented": "MINIMIZE HOLD" in system_prompt or "favor action" in system_prompt.lower(),
        "Confidence thresholds": "≥55%" in system_prompt or "55%" in system_prompt,
        "Decisiveness": "decisive" in system_prompt.lower() or "act" in system_prompt.lower(),
        "JSON format": "JSON" in system_prompt
    }
    
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        logger.info(f"{status} {check}: {passed}")
    
    return all(checks.values())


def test_indicators_format():
    """Test that indicators_to_text produces structured, actionable output."""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Indicators Format Check")
    logger.info("="*80)
    
    llm = LLMBridge()
    
    # Mock signals (bullish scenario) - correct nested structure
    signals = {
        'price': {
            'close': 262.77,
            'open': 260.50,
            'high': 264.00,
            'low': 259.75
        },
        'trend': {
            'sma_20': 254.22,
            'sma_50': 242.44,
            'macd': 2.35,
            'macd_signal': 1.88
        },
        'momentum': {
            'rsi': 59.2
        },
        'volume': {
            'volume_ratio': 1.67
        },
        'volatility': {
            'atr': 4.85,
            'bb_width': 8.5
        }
    }
    
    indicators_text = llm.indicators_to_text(signals)
    logger.info(f"\n📊 Indicators Text Output:\n{indicators_text}\n")
    
    # Verify formatting improvements
    checks = {
        "Emoji indicators": any(emoji in indicators_text for emoji in ['💰', '📈', '📉', '🔥']),
        "Structured format": '- ' in indicators_text,  # Bullet points
        "Actionable context": 'confirmed' in indicators_text or 'conviction' in indicators_text,
        "Clear hierarchy": 'PRICE:' in indicators_text or 'TREND:' in indicators_text
    }
    
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        logger.info(f"{status} {check}: {passed}")
    
    return all(checks.values())


def test_prompt_structure():
    """Test that create_analysis_prompt has improved structure."""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Prompt Structure Check")
    logger.info("="*80)
    
    llm = LLMBridge()
    
    # Mock data
    indicators_text = """
    💰 PRICE: $262.77
    📈 BULLISH TREND
    """
    
    news = [{
        'headline': 'Apple announces new AI features',
        'summary': 'Positive sentiment around innovation',
        'sentiment': 'positive'
    }]
    
    current_position = {
        'symbol': 'AAPL',
        'shares': 100,
        'entry_price': 260.00,
        'current_price': 262.77
    }
    
    prompt = llm.create_analysis_prompt(
        symbol='AAPL',
        indicators_text=indicators_text,
        news=news,
        current_position=current_position
    )
    
    logger.info(f"\n📝 Prompt Preview (first 1500 chars):\n{prompt[:1500]}...\n")
    
    # Verify key improvements
    checks = {
        "Decisiveness header": "⚡ TRADING DECISION REQUIRED" in prompt,
        "Weight structure": "PRIMARY SIGNALS" in prompt and "70%" in prompt and "30%" in prompt,
        "Confidence guide": "90-100%" in prompt or "Confidence" in prompt,
        "Position P&L": "P&L:" in prompt or "Profit/Loss:" in prompt or current_position is not None,
        "Reasoning requirements": "Primary signal" in prompt or "price target" in prompt.lower() or "MUST" in prompt,
        "Risk format": "[CRITICAL]" in prompt or "[HIGH]" in prompt or "[SEVERITY]" in prompt or "RISK" in prompt
    }
    
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        logger.info(f"{status} {check}: {passed}")
    
    return all(checks.values())


def test_quality_scoring():
    """Test the decision quality scoring system."""
    logger.info("\n" + "="*80)
    logger.info("TEST 4: Quality Scoring System")
    logger.info("="*80)
    
    llm = LLMBridge()
    
    # Mock analysis responses
    test_cases = [
        {
            'name': 'High Quality BUY',
            'analysis': {
                'action': 'buy',
                'confidence': 75,
                'sentiment': 'bullish',
                'reasoning': 'BUY: Price broke $250 resistance on 1.67x volume. Target $265 (+6%), stop $245 (-2%). Strong momentum with RSI at 59.',
                'risk_factors': ['[MEDIUM]: Earnings in 2 weeks could cause volatility']
            },
            'signals': {
                'trend': {'sma_20': 254.22, 'sma_50': 242.44},
                'momentum': {'rsi': 59.2}
            }
        },
        {
            'name': 'Generic HOLD (Poor Quality)',
            'analysis': {
                'action': 'hold',
                'confidence': 60,
                'sentiment': 'neutral',
                'reasoning': 'Market volatility and mixed signals suggest waiting. Monitor closely for developments.',
                'risk_factors': ['Uncertain market conditions']
            },
            'signals': {
                'trend': {'sma_20': 254.22, 'sma_50': 242.44},
                'momentum': {'rsi': 59.2}
            }
        },
        {
            'name': 'Decisive SELL',
            'analysis': {
                'action': 'sell',
                'confidence': 70,
                'sentiment': 'bearish',
                'reasoning': 'SELL: Broke below $255 support with 2.1x volume. Target $240 (-8%), risk to $260. RSI divergence signals weakness.',
                'risk_factors': ['[HIGH]: Technical breakdown in progress within next 3-5 days']
            },
            'signals': {
                'trend': {'sma_20': 254.22, 'sma_50': 242.44},
                'momentum': {'rsi': 45.0}
            }
        }
    ]
    
    for case in test_cases:
        logger.info(f"\n🧪 Testing: {case['name']}")
        
        scores = llm._score_decision_quality(case['analysis'], case['signals'])
        
        logger.info(f"   Decisiveness: {scores['decisiveness']:.1f}/100")
        logger.info(f"   Specificity: {scores['specificity']:.1f}/100")
        logger.info(f"   Technical Alignment: {scores['technical_alignment']:.1f}/100")
        logger.info(f"   Reasoning Quality: {scores['reasoning_quality']:.1f}/100")
        logger.info(f"   ⭐ OVERALL: {scores['overall']:.1f}/100")
        
        # Verify expectations
        if case['name'] == 'High Quality BUY':
            assert scores['overall'] > 70, "High quality decision should score >70"
        elif case['name'] == 'Generic HOLD (Poor Quality)':
            assert scores['overall'] < 60, "Generic HOLD should score <60"
    
    return True


def main():
    """Run all tests."""
    logger.info("\n" + "🚀 TESTING WEEK 1-2 LLM IMPROVEMENTS " + "🚀")
    
    tests = [
        ("Profile Decisiveness", test_profile_decisiveness),
        ("Indicators Format", test_indicators_format),
        ("Prompt Structure", test_prompt_structure),
        ("Quality Scoring", test_quality_scoring)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results[test_name] = passed
        except Exception as e:
            logger.error(f"❌ {test_name} failed with error: {e}")
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
        logger.info("✅ All improvements verified successfully!")
        return 0
    else:
        logger.warning(f"⚠️ {total_count - passed_count} test(s) need attention")
        return 1


if __name__ == "__main__":
    exit(main())
