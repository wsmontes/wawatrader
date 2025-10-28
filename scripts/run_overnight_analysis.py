#!/usr/bin/env python3
"""
Overnight Deep Analysis Automation

Runs comprehensive LLM analysis on watchlist after market close.
This performs iterative deep dives on each symbol with full news context,
earnings data, and multi-pass reasoning.

Schedule: Run daily at 4:30 PM ET (after market close)
Duration: 2-4 hours depending on watchlist size

Usage:
    python scripts/run_overnight_analysis.py
    python scripts/run_overnight_analysis.py --symbols AAPL,MSFT,GOOGL
    python scripts/run_overnight_analysis.py --iterations 5
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from wawatrader.alpaca_client import get_client
from wawatrader.llm_bridge import LLMBridge
from wawatrader.indicators import get_bars_and_analyze
from wawatrader.market_intelligence import get_intelligence_engine
from config.settings import settings


class OvernightAnalyzer:
    """
    Performs deep overnight analysis on stocks.
    
    This uses multiple LLM iterations to refine analysis,
    incorporating news, earnings, technical patterns, and
    cross-checking reasoning for higher quality insights.
    """
    
    def __init__(self):
        """Initialize overnight analyzer"""
        self.alpaca = get_client()
        self.llm = LLMBridge()
        self.intelligence = get_intelligence_engine()
        
        # Output file
        self.output_file = Path("logs/overnight_analysis.jsonl")
        self.output_file.parent.mkdir(exist_ok=True)
        
        logger.info("🌙 Overnight analyzer initialized")
    
    def analyze_symbol(
        self, 
        symbol: str, 
        iterations: int = 3,
        use_earnings: bool = True
    ) -> Dict[str, Any]:
        """
        Perform deep analysis on a single symbol.
        
        Args:
            symbol: Stock symbol to analyze
            iterations: Number of refinement iterations (1-5)
            use_earnings: Whether to include earnings context
            
        Returns:
            Analysis results dictionary
        """
        logger.info(f"🔍 Starting overnight analysis: {symbol}")
        
        try:
            # Step 1: Gather comprehensive data
            logger.info(f"📊 Gathering data for {symbol}...")
            
            # Get technical data
            bars, analysis = get_bars_and_analyze(
                self.alpaca, 
                symbol, 
                lookback_days=90,
                timeframe="1Day"
            )
            
            if bars is None or analysis is None:
                logger.warning(f"⚠️ Could not get technical data for {symbol}")
                return self._create_failed_analysis(symbol, "No technical data")
            
            # Get market intelligence (news, sentiment)
            logger.info(f"📰 Fetching news and market intelligence...")
            try:
                market_intel = self.intelligence.get_market_intelligence(
                    days_back=1,
                    focus_symbols=[symbol]
                )
            except Exception as e:
                logger.warning(f"⚠️ Could not get market intelligence: {e}")
                market_intel = None
            
            # Get earnings data if requested
            earnings_context = None
            if use_earnings:
                logger.info(f"📈 Checking for earnings data...")
                try:
                    earnings_context = self._get_earnings_context(symbol)
                except Exception as e:
                    logger.warning(f"⚠️ Could not get earnings: {e}")
            
            # Step 2: Perform iterative analysis
            logger.info(f"🧠 Running {iterations} iteration(s) of LLM analysis...")
            
            analysis_history = []
            final_recommendation = None
            
            for iteration in range(1, iterations + 1):
                logger.info(f"  Iteration {iteration}/{iterations}...")
                
                # Build context for this iteration
                context = self._build_analysis_context(
                    symbol=symbol,
                    bars=bars,
                    technical=analysis,
                    market_intel=market_intel,
                    earnings=earnings_context,
                    previous_analyses=analysis_history,
                    iteration=iteration,
                    total_iterations=iterations
                )
                
                # Get LLM analysis
                llm_result = self.llm.analyze_stock(
                    symbol=symbol,
                    bars=bars,
                    current_price=bars['close'].iloc[-1] if not bars.empty else 0,
                    indicators=analysis['indicators'],
                    patterns=analysis['patterns'],
                    overnight_context=None  # We ARE the overnight analysis
                )
                
                if llm_result['status'] == 'success':
                    analysis_history.append({
                        'iteration': iteration,
                        'recommendation': llm_result.get('action', 'HOLD'),
                        'confidence': llm_result.get('confidence', 50),
                        'reasoning': llm_result.get('reasoning', ''),
                        'sentiment': llm_result.get('sentiment', 'neutral'),
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    final_recommendation = llm_result.get('action', 'HOLD')
                    logger.info(f"    → {final_recommendation} (confidence: {llm_result.get('confidence', 50)}%)")
                else:
                    logger.warning(f"    ⚠️ LLM analysis failed: {llm_result.get('error')}")
            
            # Step 3: Synthesize final analysis
            logger.info(f"✅ Synthesis complete for {symbol}")
            
            result = {
                'symbol': symbol,
                'analyzed_at': datetime.now().isoformat(),
                'analysis_type': 'overnight_deep_dive',
                'iterations': iterations,
                'final_recommendation': final_recommendation or 'HOLD',
                'confidence_level': self._calculate_confidence(analysis_history),
                'reasoning': self._synthesize_reasoning(analysis_history),
                'technical_summary': self._summarize_technical(analysis),
                'market_intel_summary': self._summarize_intel(market_intel),
                'earnings_summary': earnings_context.get('summary') if earnings_context else None,
                'analysis_history': analysis_history,
                'current_price': float(bars['close'].iloc[-1]) if not bars.empty else 0,
                'price_change_today': self._calculate_price_change(bars)
            }
            
            # Save to file
            self._save_analysis(result)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error analyzing {symbol}: {e}")
            return self._create_failed_analysis(symbol, str(e))
    
    def _build_analysis_context(
        self,
        symbol: str,
        bars: Any,
        technical: Dict,
        market_intel: Optional[Dict],
        earnings: Optional[Dict],
        previous_analyses: List[Dict],
        iteration: int,
        total_iterations: int
    ) -> str:
        """Build context string for LLM (not currently used but useful for custom prompts)"""
        context_parts = []
        
        if iteration > 1:
            context_parts.append(f"This is iteration {iteration}/{total_iterations}")
            context_parts.append("Previous analyses:")
            for prev in previous_analyses:
                context_parts.append(
                    f"  - Iter {prev['iteration']}: {prev['recommendation']} "
                    f"({prev['confidence']}%) - {prev['reasoning'][:100]}..."
                )
        
        return "\n".join(context_parts)
    
    def _get_earnings_context(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get recent earnings data if available"""
        # This would integrate with earnings calendar API
        # For now, return None (can be enhanced later)
        return None
    
    def _calculate_confidence(self, history: List[Dict]) -> str:
        """Calculate overall confidence level from iteration history"""
        if not history:
            return 'low'
        
        # Check consistency of recommendations
        recommendations = [h['recommendation'] for h in history]
        most_common = max(set(recommendations), key=recommendations.count)
        consistency = recommendations.count(most_common) / len(recommendations)
        
        # Average confidence
        avg_confidence = sum(h['confidence'] for h in history) / len(history)
        
        if consistency >= 0.8 and avg_confidence >= 70:
            return 'high'
        elif consistency >= 0.6 and avg_confidence >= 60:
            return 'medium'
        else:
            return 'low'
    
    def _synthesize_reasoning(self, history: List[Dict]) -> str:
        """Synthesize final reasoning from all iterations"""
        if not history:
            return "No analysis available"
        
        # Use the last iteration's reasoning as primary
        final = history[-1]
        
        # Note if recommendations changed across iterations
        recommendations = [h['recommendation'] for h in history]
        if len(set(recommendations)) > 1:
            evolution = " → ".join(recommendations)
            prefix = f"Analysis evolved: {evolution}. "
        else:
            prefix = f"Consistent across {len(history)} iterations. "
        
        return prefix + final['reasoning']
    
    def _summarize_technical(self, technical: Dict) -> str:
        """Create brief technical summary"""
        indicators = technical.get('indicators', {})
        patterns = technical.get('patterns', {})
        
        signals = []
        if indicators.get('rsi', 50) < 30:
            signals.append("Oversold (RSI)")
        elif indicators.get('rsi', 50) > 70:
            signals.append("Overbought (RSI)")
        
        if patterns.get('trend') == 'bullish':
            signals.append("Bullish trend")
        elif patterns.get('trend') == 'bearish':
            signals.append("Bearish trend")
        
        return ", ".join(signals) if signals else "Neutral technical setup"
    
    def _summarize_intel(self, market_intel: Optional[Dict]) -> str:
        """Create brief market intelligence summary"""
        if not market_intel:
            return "No market intelligence available"
        
        # Extract key points from intelligence
        summary_parts = []
        
        if 'market_sentiment' in market_intel:
            summary_parts.append(f"Market: {market_intel['market_sentiment']}")
        
        if 'news_count' in market_intel:
            summary_parts.append(f"{market_intel['news_count']} news items")
        
        return ", ".join(summary_parts) if summary_parts else "Limited intelligence"
    
    def _calculate_price_change(self, bars: Any) -> float:
        """Calculate today's price change percentage"""
        if bars is None or len(bars) < 2:
            return 0.0
        
        try:
            prev_close = float(bars['close'].iloc[-2])
            curr_close = float(bars['close'].iloc[-1])
            return ((curr_close - prev_close) / prev_close) * 100
        except:
            return 0.0
    
    def _create_failed_analysis(self, symbol: str, error: str) -> Dict[str, Any]:
        """Create a failed analysis record"""
        return {
            'symbol': symbol,
            'analyzed_at': datetime.now().isoformat(),
            'analysis_type': 'overnight_deep_dive',
            'status': 'failed',
            'error': error,
            'final_recommendation': 'HOLD',
            'confidence_level': 'low',
            'reasoning': f"Analysis failed: {error}"
        }
    
    def _save_analysis(self, result: Dict[str, Any]):
        """Save analysis result to JSONL file"""
        try:
            with open(self.output_file, 'a') as f:
                f.write(json.dumps(result) + '\n')
            logger.info(f"💾 Saved analysis to {self.output_file}")
        except Exception as e:
            logger.error(f"❌ Failed to save analysis: {e}")
    
    def run_watchlist_analysis(
        self,
        symbols: List[str],
        iterations: int = 3,
        use_earnings: bool = True
    ) -> Dict[str, Any]:
        """
        Run overnight analysis on entire watchlist.
        
        Args:
            symbols: List of symbols to analyze
            iterations: Number of refinement iterations per symbol
            use_earnings: Whether to include earnings data
            
        Returns:
            Summary of all analyses
        """
        logger.info("🌙 Starting overnight watchlist analysis")
        logger.info(f"   Symbols: {', '.join(symbols)}")
        logger.info(f"   Iterations per symbol: {iterations}")
        logger.info(f"   Started at: {datetime.now().strftime('%I:%M:%S %p')}")
        
        results = []
        start_time = datetime.now()
        
        for i, symbol in enumerate(symbols, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"📊 Analyzing {symbol} ({i}/{len(symbols)})")
            logger.info(f"{'='*60}")
            
            result = self.analyze_symbol(
                symbol=symbol,
                iterations=iterations,
                use_earnings=use_earnings
            )
            results.append(result)
            
            # Brief pause between symbols to avoid rate limits
            if i < len(symbols):
                import time
                time.sleep(2)
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Create summary
        summary = {
            'run_date': datetime.now().date().isoformat(),
            'run_time': datetime.now().time().isoformat(),
            'duration_seconds': duration.total_seconds(),
            'symbols_analyzed': len(symbols),
            'iterations_per_symbol': iterations,
            'results': results,
            'recommendations_summary': {
                'BUY': sum(1 for r in results if r.get('final_recommendation') == 'BUY'),
                'SELL': sum(1 for r in results if r.get('final_recommendation') == 'SELL'),
                'HOLD': sum(1 for r in results if r.get('final_recommendation') == 'HOLD'),
            }
        }
        
        # Save summary
        summary_file = Path("logs/overnight_summary.jsonl")
        with open(summary_file, 'a') as f:
            f.write(json.dumps(summary) + '\n')
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("✅ OVERNIGHT ANALYSIS COMPLETE")
        logger.info("="*60)
        logger.info(f"Duration: {duration.total_seconds():.0f} seconds ({duration.total_seconds()/60:.1f} minutes)")
        logger.info(f"Symbols: {len(symbols)}")
        logger.info(f"Recommendations:")
        logger.info(f"  🟢 BUY:  {summary['recommendations_summary']['BUY']}")
        logger.info(f"  🔴 SELL: {summary['recommendations_summary']['SELL']}")
        logger.info(f"  🟡 HOLD: {summary['recommendations_summary']['HOLD']}")
        logger.info(f"\n📊 Results saved to: {self.output_file}")
        logger.info(f"📋 Summary saved to: {summary_file}")
        logger.info("="*60)
        
        return summary


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Run overnight deep analysis on watchlist",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze default watchlist with 3 iterations
  python scripts/run_overnight_analysis.py
  
  # Analyze specific symbols
  python scripts/run_overnight_analysis.py --symbols AAPL,MSFT,GOOGL
  
  # Use 5 iterations for deeper analysis
  python scripts/run_overnight_analysis.py --iterations 5
  
  # Skip earnings data (faster)
  python scripts/run_overnight_analysis.py --no-earnings

Schedule with cron (run daily at 4:30 PM ET):
  30 16 * * * cd /path/to/wawatrader && source venv/bin/activate && python scripts/run_overnight_analysis.py
        """
    )
    
    parser.add_argument(
        '--symbols',
        type=str,
        help='Comma-separated list of symbols (default: AAPL,MSFT,GOOGL,TSLA,NVDA)'
    )
    
    parser.add_argument(
        '--iterations',
        type=int,
        default=3,
        help='Number of refinement iterations (1-5, default: 3)'
    )
    
    parser.add_argument(
        '--no-earnings',
        action='store_true',
        help='Skip earnings data (faster analysis)'
    )
    
    args = parser.parse_args()
    
    # Parse symbols
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(',')]
    else:
        # Let LLM discover symbols from market intelligence
        from wawatrader.market_intelligence import MarketIntelligence
        print("🤖 No symbols specified - LLM will discover from market intelligence...")
        
        try:
            intel = MarketIntelligence()
            universe = intel.get_dynamic_universe(min_mentions=3, max_results=20)
            symbols = [stock['symbol'] for stock in universe]
            print(f"🧠 LLM discovered {len(symbols)} symbols with significant market mentions")
        except Exception as e:
            print(f"⚠️ Failed to get dynamic universe: {e}")
            print("📋 Starting with empty list - provide symbols with --symbols flag")
            symbols = []
    
    # Validate iterations
    iterations = max(1, min(5, args.iterations))
    
    print("🌙 WawaTrader - Overnight Deep Analysis")
    print("=" * 70)
    print()
    
    # Check market status
    from wawatrader.alpaca_client import get_client
    temp_client = get_client()
    market_status = temp_client.get_market_status()
    
    if market_status.get('is_open'):
        print("⚠️  WARNING: Market is currently OPEN")
        print("   Overnight analysis is typically run after market close (4:30 PM ET)")
        print("   Continue anyway? (y/n): ", end='')
        response = input().strip().lower()
        if response != 'y':
            print("❌ Analysis cancelled")
            return
        print()
    
    # Run analysis
    analyzer = OvernightAnalyzer()
    summary = analyzer.run_watchlist_analysis(
        symbols=symbols,
        iterations=iterations,
        use_earnings=not args.no_earnings
    )
    
    print("\n✅ Overnight analysis complete!")
    print(f"💡 Use these insights in tomorrow's morning trading session")


if __name__ == "__main__":
    main()
