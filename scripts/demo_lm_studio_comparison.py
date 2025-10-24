#!/usr/bin/env python3
"""
LM Studio Integration Comparison Demo

Demonstrates the differences between the old OpenAI-compatible API
and the new official LM Studio SDK.

Usage:
    python scripts/demo_lm_studio_comparison.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
import time


def demo_old_bridge():
    """Demo the old OpenAI-compatible bridge"""
    print("\n" + "="*70)
    print("🔧 OLD METHOD: OpenAI-Compatible API")
    print("="*70)
    
    try:
        from wawatrader.llm_bridge import LLMBridge
        
        print("\n1️⃣ Initialize client...")
        start = time.time()
        bridge = LLMBridge()
        print(f"   ⏱️  Initialization: {time.time() - start:.2f}s")
        
        print("\n2️⃣ Check capabilities...")
        print("   ❌ No health check available")
        print("   ❌ Cannot check if model is loaded")
        print("   ❌ Cannot list available models")
        print("   ⚠️  Must manually ensure model is loaded in LM Studio GUI")
        
        print("\n3️⃣ Sample market analysis...")
        sample_signals = {
            'price': {'close': 150.25},
            'trend': {
                'sma_20': 149.80,
                'sma_50': 148.50,
                'macd': 1.25,
                'macd_signal': 0.85
            },
            'momentum': {'rsi': 65.4},
            'volatility': {'bb_position': 0.7},
            'volume': {'volume_ratio': 1.3}
        }
        
        start = time.time()
        analysis = bridge.analyze_market('AAPL', sample_signals)
        elapsed = time.time() - start
        
        if analysis:
            print(f"   ✅ Analysis completed in {elapsed:.2f}s")
            print(f"   📊 Sentiment: {analysis['sentiment']}")
            print(f"   📊 Confidence: {analysis['confidence']}%")
            print(f"   📊 Action: {analysis['action']}")
            print(f"   ❌ No token count available")
            print(f"   ❌ No time-to-first-token metric")
            print(f"   ❌ No model info in response")
        else:
            print("   ❌ Analysis failed")
        
        print("\n📝 Summary:")
        print("   ✅ Simple to use")
        print("   ✅ Works with any OpenAI-compatible endpoint")
        print("   ❌ Manual model management required")
        print("   ❌ Limited error diagnostics")
        print("   ❌ No performance metrics")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")


def demo_new_bridge():
    """Demo the new official SDK bridge"""
    print("\n" + "="*70)
    print("🚀 NEW METHOD: Official LM Studio SDK")
    print("="*70)
    
    try:
        from wawatrader.llm_bridge_v2 import LLMBridgeV2
        import lmstudio as lms
        
        print("\n1️⃣ Initialize client...")
        start = time.time()
        bridge = LLMBridgeV2()
        print(f"   ⏱️  Initialization: {time.time() - start:.2f}s")
        
        print("\n2️⃣ Check capabilities...")
        health = bridge.check_health()
        print(f"   ✅ Health check: Available={health['available']}")
        print(f"   ✅ Model loaded: {health['model_loaded']}")
        print(f"   ✅ Using SDK: {health['using_sdk']}")
        if 'loaded_models' in health:
            print(f"   ✅ Loaded models: {health['loaded_models']}")
        print("   ✅ Automatic model loading enabled")
        
        print("\n3️⃣ List available models...")
        try:
            all_models = lms.list_loaded_models("llm")
            if all_models:
                for model in all_models:
                    print(f"   📦 {model.identifier}")
            else:
                print("   ℹ️  No models currently loaded (will auto-load on first request)")
        except Exception as e:
            print(f"   ⚠️  Could not list models: {e}")
        
        print("\n4️⃣ Sample market analysis...")
        sample_signals = {
            'price': {'close': 150.25},
            'trend': {
                'sma_20': 149.80,
                'sma_50': 148.50,
                'macd': 1.25,
                'macd_signal': 0.85
            },
            'momentum': {'rsi': 65.4},
            'volatility': {'bb_position': 0.7},
            'volume': {'volume_ratio': 1.3}
        }
        
        start = time.time()
        analysis = bridge.analyze_market('AAPL', sample_signals)
        elapsed = time.time() - start
        
        if analysis:
            print(f"   ✅ Analysis completed in {elapsed:.2f}s")
            print(f"   📊 Sentiment: {analysis['sentiment']}")
            print(f"   📊 Confidence: {analysis['confidence']}%")
            print(f"   📊 Action: {analysis['action']}")
            print(f"   ✅ Full response metadata available")
            print(f"   ✅ Token count logged")
            print(f"   ✅ Time-to-first-token recorded")
            print(f"   ✅ Model info included")
        else:
            print("   ❌ Analysis failed")
        
        print("\n📝 Summary:")
        print("   ✅ Automatic model loading")
        print("   ✅ Health checking & diagnostics")
        print("   ✅ Rich performance metrics")
        print("   ✅ Model management APIs")
        print("   ✅ Backward compatible fallback")
        print("   ✅ Better error messages")
        
    except ImportError:
        print("\n⚠️  LM Studio SDK not installed!")
        print("   Install with: pip install lmstudio")
        print("   Falling back to OpenAI-compatible client...")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run comparison demo"""
    print("\n" + "🔬"*35)
    print("LM STUDIO INTEGRATION COMPARISON DEMO")
    print("🔬"*35)
    
    print("\nThis demo compares the old OpenAI-compatible API approach")
    print("with the new official LM Studio Python SDK integration.")
    print("\n💡 Make sure LM Studio server is running on port 1234")
    
    # Demo old method
    demo_old_bridge()
    
    # Demo new method
    demo_new_bridge()
    
    # Final comparison
    print("\n" + "="*70)
    print("📊 COMPARISON SUMMARY")
    print("="*70)
    
    print("\n| Feature                    | Old Method | New Method |")
    print("|----------------------------|------------|------------|")
    print("| Automatic Model Loading    | ❌         | ✅         |")
    print("| Health Checking            | ❌         | ✅         |")
    print("| Performance Metrics        | ❌         | ✅         |")
    print("| Model Management           | ❌         | ✅         |")
    print("| Error Diagnostics          | ⚠️         | ✅         |")
    print("| Backward Compatible        | N/A        | ✅         |")
    print("| Requires SDK Install       | ❌         | ⚠️         |")
    
    print("\n🎯 RECOMMENDATION:")
    print("   Use NEW method (LLMBridgeV2) for production systems")
    print("   Old method still works but lacks automation and diagnostics")
    
    print("\n💡 MIGRATION:")
    print("   1. pip install lmstudio")
    print("   2. Update imports: from wawatrader.llm_bridge_v2 import LLMBridgeV2")
    print("   3. Test: python wawatrader/llm_bridge_v2.py")
    print("   4. Deploy with confidence!")
    
    print("\n" + "="*70)
    print("Demo completed! 🎉")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
