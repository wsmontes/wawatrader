"""
Demo: Overnight Multi-Pass Learning System

Demonstrates the 6-pass learning cycle that runs during off-market hours.

Usage:
    python scripts/demo_overnight_learning.py [date]
    
Example:
    python scripts/demo_overnight_learning.py 2025-10-25
"""

from datetime import datetime, timedelta
from wawatrader.overnight_learner import get_overnight_learner
import json


def main():
    """Run overnight learning demo"""
    import sys
    
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║       🌙 OVERNIGHT MULTI-PASS LEARNING SYSTEM DEMO           ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print()
    
    # Determine which date to analyze
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        # Default: Most recent trading day
        date = datetime.now().date() - timedelta(days=1)
    
    print(f"📅 Target Date: {date}")
    print()
    print("This demo will:")
    print("  1. EVALUATE - Analyze trading performance")
    print("  2. ANALYZE - Deep dive into decisions")
    print("  3. LEARNING - Extract patterns")
    print("  4. OPTIMIZATION - Propose improvements")
    print("  5. VALIDATION - Test on historical data")
    print("  6. APPLICATION - Apply validated changes")
    print()
    print("⏱️  This typically takes 2-4 hours in production.")
    print("   For demo, we'll run a quick pass.")
    print()
    input("Press Enter to begin...")
    print()
    
    # Get learning system
    learner = get_overnight_learner()
    
    # Run overnight learning
    summary = learner.run_overnight_learning(date)
    
    # Display detailed results
    print()
    print("═" * 70)
    print("DETAILED SESSION RESULTS")
    print("═" * 70)
    print(json.dumps(summary, indent=2))
    print()
    
    # Display actionable insights
    if summary.get('lessons_learned', 0) > 0:
        print("═" * 70)
        print("💡 TOP LESSONS LEARNED")
        print("═" * 70)
        for i, lesson in enumerate(summary.get('top_lessons', []), 1):
            print(f"\n{i}. {lesson['category'].upper()}")
            print(f"   Insight: {lesson['insight']}")
            print(f"   Confidence: {lesson['confidence']:.0%}")
            print(f"   Expected Improvement: +{lesson['expected_improvement']:.1f}%")
        print()
    
    if summary.get('adjustments_applied', 0) > 0:
        print("═" * 70)
        print("🚀 APPLIED CHANGES")
        print("═" * 70)
        for i, adj in enumerate(summary.get('applied_changes', []), 1):
            print(f"\n{i}. Parameter: {adj['parameter']}")
            print(f"   Old Value: {adj['old_value']}")
            print(f"   New Value: {adj['new_value']}")
            print(f"   Reason: {adj['reason']}")
            if adj.get('validation_score'):
                print(f"   Validated: +{adj['validation_score']:.1f}% improvement")
        print()
    
    # Summary
    print("═" * 70)
    print("NEXT STEPS")
    print("═" * 70)
    print()
    
    if summary.get('adjustments_applied', 0) > 0:
        print("✅ Strategy has been improved!")
        print(f"   Expected improvement: +{summary.get('expected_improvement_pct', 0):.1f}%")
        print()
        print("   Changes will take effect in next trading session.")
        print("   Monitor performance to validate improvements.")
    else:
        print("ℹ️  No changes applied.")
        print()
        if summary.get('lessons_learned', 0) > 0:
            print("   Lessons were learned but didn't pass validation threshold.")
            print("   System will continue learning from more data.")
        else:
            print("   Not enough data to extract actionable lessons yet.")
            print("   System needs more trading history to learn from.")
    
    print()
    print("═" * 70)
    print()
    print("💤 System is ready for tomorrow's trading!")
    print()


if __name__ == "__main__":
    main()
