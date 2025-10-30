"""
Risk Management System

Hard-coded rules to protect capital. NO LLM involvement.
These are fail-safes that override any AI recommendations.

Risk management happens at multiple levels:
1. Position level (max size per stock)
2. Daily level (max loss per day)
3. Portfolio level (max total exposure)
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, date
from dataclasses import dataclass
from loguru import logger
import numpy as np
import pandas as pd

from config.settings import settings

__all__ = ['RiskManager', 'get_risk_manager', 'RiskCheckResult']


@dataclass
class RiskCheckResult:
    """Result of a risk check"""
    approved: bool
    reason: str
    max_shares: Optional[int] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class RiskManager:
    """Enforce hard-coded risk rules with absolute authority.
    
    This is the safety backbone of WawaTrader. All trading decisions must pass
    through risk validation before execution. No LLM recommendation can override
    these mathematically-enforced safety rules.
    
    Safety Features:
        - Position size limits (max 5% per position)
        - Daily loss limits with circuit breakers  
        - Portfolio-wide risk exposure monitoring
        - Real-time account protection
        - Automatic position sizing calculations
        
    Example:
        >>> risk = get_risk_manager()
        >>> result = risk.validate_trade('AAPL', 100, 150.00)
        >>> if result.approved:
        ...     execute_trade()
        
    Note:
        CRITICAL: These rules are ABSOLUTE and mathematically enforced.
        No AI system can override safety parameters.
    """
    
    def __init__(self):
        """Initialize risk manager with settings"""
        self.max_position_size = settings.risk.max_position_size
        self.max_daily_loss = settings.risk.max_daily_loss
        self.max_portfolio_risk = settings.risk.max_portfolio_risk
        
        # Track daily losses
        self.daily_losses: Dict[date, float] = {}
        self.trade_count_today = 0
        
        logger.info(f"Risk Manager initialized:")
        logger.info(f"  Max position size: {self.max_position_size*100:.1f}% of portfolio")
        logger.info(f"  Max daily loss: {self.max_daily_loss*100:.1f}%")
        logger.info(f"  Max portfolio risk: {self.max_portfolio_risk*100:.1f}%")
    
    def check_position_size(
        self,
        symbol: str,
        shares: int,
        price: float,
        account_value: float
    ) -> RiskCheckResult:
        """
        Check if position size is within limits.
        
        Args:
            symbol: Stock ticker
            shares: Number of shares to buy/sell
            price: Current price per share
            account_value: Total account value
        
        Returns:
            RiskCheckResult with approval and reasoning
        """
        position_value = shares * price
        position_pct = position_value / account_value
        max_value = account_value * self.max_position_size
        max_shares = int(max_value / price)
        
        warnings = []
        
        # Check if position is too large
        if position_value > max_value:
            return RiskCheckResult(
                approved=False,
                reason=f"Position too large: ${position_value:,.2f} ({position_pct*100:.1f}%) exceeds max ${max_value:,.2f} ({self.max_position_size*100:.1f}%)",
                max_shares=max_shares
            )
        
        # Warning if position is close to limit (>80%)
        if position_pct > self.max_position_size * 0.8:
            warnings.append(
                f"Position is {position_pct*100:.1f}% of portfolio (close to {self.max_position_size*100:.1f}% limit)"
            )
        
        return RiskCheckResult(
            approved=True,
            reason=f"Position size OK: {shares} shares = ${position_value:,.2f} ({position_pct*100:.1f}%)",
            max_shares=max_shares,
            warnings=warnings
        )
    
    def check_daily_loss_limit(
        self,
        current_pnl: float,
        account_value: float
    ) -> RiskCheckResult:
        """
        Check if we've hit daily loss limit.
        
        Args:
            current_pnl: Today's P&L so far
            account_value: Total account value
        
        Returns:
            RiskCheckResult with approval
        """
        today = date.today()
        
        # Update daily loss tracking
        self.daily_losses[today] = current_pnl
        
        # Calculate loss as percentage
        loss_pct = abs(current_pnl) / account_value if current_pnl < 0 else 0
        max_loss_value = account_value * self.max_daily_loss
        
        warnings = []
        
        # Check if we've exceeded daily loss limit
        if loss_pct > self.max_daily_loss:
            return RiskCheckResult(
                approved=False,
                reason=f"Daily loss limit exceeded: ${current_pnl:,.2f} ({loss_pct*100:.1f}%) exceeds max loss ${max_loss_value:,.2f} ({self.max_daily_loss*100:.1f}%). Trading halted for today."
            )
        
        # Warning if loss is close to limit (>75%)
        if loss_pct > self.max_daily_loss * 0.75:
            warnings.append(
                f"Daily loss at {loss_pct*100:.1f}% (close to {self.max_daily_loss*100:.1f}% limit)"
            )
        
        return RiskCheckResult(
            approved=True,
            reason=f"Daily P&L OK: ${current_pnl:,.2f} ({loss_pct*100:.1f}%)",
            warnings=warnings
        )
    
    def check_portfolio_exposure(
        self,
        positions: List[Dict[str, Any]],
        account_value: float
    ) -> RiskCheckResult:
        """
        Check total portfolio exposure.
        
        This checks if we're over-leveraged or concentrated, NOT if we're fully invested.
        A healthy portfolio should be 80-100% invested (exposure ratio 0.8-1.0).
        
        Args:
            positions: List of current positions
            account_value: Total account value
        
        Returns:
            RiskCheckResult with approval
        """
        # Calculate total market exposure (sum of position values)
        total_exposure = sum(
            abs(float(pos.get('market_value', 0)))
            for pos in positions
        )
        
        # Exposure ratio: 1.0 = fully invested, >1.0 = leveraged
        exposure_ratio = total_exposure / account_value if account_value > 0 else 0
        
        warnings = []
        
        # REALISTIC LIMITS:
        # - < 1.0 = Normal (fully invested or less)
        # - > 1.0 = Leveraged (using margin)
        # - > 1.5 = Dangerous leverage
        
        max_leverage = 1.5  # Allow up to 150% leverage (using margin)
        
        # Check if we're over-leveraged
        if exposure_ratio > max_leverage:
            return RiskCheckResult(
                approved=False,
                reason=f"Excessive leverage: ${total_exposure:,.2f} ({exposure_ratio*100:.1f}%) exceeds max {max_leverage*100:.1f}%"
            )
        
        # Warning if using significant leverage (>110%)
        if exposure_ratio > 1.10:
            warnings.append(
                f"⚠️ Using margin: {exposure_ratio*100:.1f}% exposure (above 100%)"
            )
        
        # Info if under-invested (<70%)
        if exposure_ratio < 0.70:
            warnings.append(
                f"📊 Under-invested: {exposure_ratio*100:.1f}% exposure (consider deploying more capital)"
            )
        
        return RiskCheckResult(
            approved=True,
            reason=f"Portfolio exposure OK: ${total_exposure:,.2f} ({exposure_ratio*100:.1f}% of portfolio)",
            warnings=warnings
        )
    
    def check_trade_frequency(
        self,
        symbol: str,
        action: str
    ) -> RiskCheckResult:
        """
        Check if we're trading too frequently (prevents overtrading).
        
        DYNAMIC FREQUENCY CONTROL:
        - No hard limit on trades if profitable
        - Restricts trading if losing money (poor strategy day)
        - Emergency liquidation if critical loss threshold reached
        
        Args:
            symbol: Stock ticker
            action: "buy" or "sell"
        
        Returns:
            RiskCheckResult with approval
        """
        warnings = []
        
        # Check current P&L performance
        today_pnl = self.daily_losses.get(date.today(), 0)
        
        # RULE 1: Always allow SELL orders (never block position exits)
        if action.lower() == 'sell':
            return RiskCheckResult(
                approved=True,
                reason=f"SELL approved (exit always allowed): {self.trade_count_today} trades today, P&L: ${today_pnl:,.2f}",
                warnings=warnings
            )
        
        # RULE 2: Block BUY orders if losing significant money (poor strategy day)
        # Only restrict NEW positions when bleeding capital
        loss_threshold = -0.01  # -1% loss triggers restriction
        if today_pnl < loss_threshold * 100000:  # Assuming ~100k portfolio
            return RiskCheckResult(
                approved=False,
                reason=f"Trading restricted due to losses: ${today_pnl:,.2f} today. Only SELL orders allowed to reduce exposure."
            )
        
        # RULE 3: Warning if high frequency (informational only)
        if self.trade_count_today >= 20:
            warnings.append(
                f"⚠️ High trade frequency: {self.trade_count_today} trades today (P&L: ${today_pnl:,.2f})"
            )
        
        # All clear - allow trade
        return RiskCheckResult(
            approved=True,
            reason=f"Trade frequency OK: {self.trade_count_today} trades today, P&L: ${today_pnl:,.2f}",
            warnings=warnings
        )
    
    def validate_trade(
        self,
        symbol: str,
        action: str,
        shares: int,
        price: float,
        account_value: float,
        current_pnl: float,
        positions: List[Dict[str, Any]],
        buying_power: float = None  # NEW: Optional buying power parameter
    ) -> RiskCheckResult:
        """
        Comprehensive trade validation (runs all checks).
        
        Args:
            symbol: Stock ticker
            action: "buy" or "sell"
            shares: Number of shares
            price: Current price per share
            account_value: Total account value
            current_pnl: Today's P&L
            positions: Current positions
            buying_power: Available buying power (optional, for BUY orders)
        
        Returns:
            RiskCheckResult (approved only if ALL checks pass)
        """
        logger.info(f"Validating trade: {action.upper()} {shares} {symbol} @ ${price:.2f}")
        
        all_warnings = []
        
        # Check 0: Buying power (CRITICAL for BUY orders)
        if action.lower() == 'buy':
            trade_cost = shares * price
            
            # If buying_power provided, check it
            if buying_power is not None:
                if trade_cost > buying_power:
                    max_affordable_shares = int(buying_power / price)
                    logger.warning(f"❌ Insufficient buying power: Need ${trade_cost:,.2f}, have ${buying_power:,.2f}")
                    
                    # If we can't afford ANY shares, reject immediately
                    if max_affordable_shares < 1:
                        return RiskCheckResult(
                            approved=False,
                            reason=f"Insufficient buying power: ${buying_power:,.2f} available, ${trade_cost:,.2f} required",
                            max_shares=0
                        )
                    
                    # Otherwise, suggest reducing to affordable amount
                    return RiskCheckResult(
                        approved=False,
                        reason=f"Insufficient buying power: Can afford {max_affordable_shares} shares (${max_affordable_shares * price:,.2f}), not {shares} shares (${trade_cost:,.2f})",
                        max_shares=max_affordable_shares
                    )
        
        # Check 1: Position size
        if action.lower() == 'buy':
            size_check = self.check_position_size(symbol, shares, price, account_value)
            if not size_check.approved:
                logger.warning(f"❌ Position size check failed: {size_check.reason}")
                return size_check
            all_warnings.extend(size_check.warnings)
        
        # Check 2: Daily loss limit
        loss_check = self.check_daily_loss_limit(current_pnl, account_value)
        if not loss_check.approved:
            logger.warning(f"❌ Daily loss check failed: {loss_check.reason}")
            return loss_check
        all_warnings.extend(loss_check.warnings)
        
        # Check 3: Portfolio exposure
        # IMPORTANT: Skip for SELL actions - we WANT to sell when over-leveraged!
        if action.lower() == 'buy':
            exposure_check = self.check_portfolio_exposure(positions, account_value)
            if not exposure_check.approved:
                logger.warning(f"❌ Portfolio exposure check failed: {exposure_check.reason}")
                return exposure_check
            all_warnings.extend(exposure_check.warnings)
        elif action.lower() == 'sell':
            # For SELL, exposure check is advisory only (still log warnings)
            exposure_check = self.check_portfolio_exposure(positions, account_value)
            if not exposure_check.approved:
                # If over-leveraged, SELLING is actually GOOD - log as info, not error
                logger.info(f"✅ SELL approved despite high leverage (this will help reduce exposure)")
            all_warnings.extend(exposure_check.warnings)
        
        # Check 4: Trade frequency
        freq_check = self.check_trade_frequency(symbol, action)
        if not freq_check.approved:
            logger.warning(f"❌ Trade frequency check failed: {freq_check.reason}")
            return freq_check
        all_warnings.extend(freq_check.warnings)
        
        # All checks passed
        logger.info(f"✅ Trade validation passed")
        if all_warnings:
            for warning in all_warnings:
                logger.warning(f"⚠️  {warning}")
        
        return RiskCheckResult(
            approved=True,
            reason="All risk checks passed",
            warnings=all_warnings
        )
    
    def record_trade(self, symbol: str, action: str, shares: int, price: float):
        """Record a trade (for frequency tracking)"""
        self.trade_count_today += 1
        logger.debug(f"Recorded trade #{self.trade_count_today}: {action.upper()} {shares} {symbol} @ ${price:.2f}")
    
    def reset_daily_counters(self):
        """Reset daily counters (call at market open)"""
        today = date.today()
        logger.info(f"Resetting daily counters for {today}")
        
        self.trade_count_today = 0
    
    def check_emergency_liquidation(
        self,
        current_pnl: float,
        account_value: float
    ) -> Dict[str, Any]:
        """
        Check if emergency liquidation is needed due to excessive losses.
        
        DYNAMIC LIQUIDATION RULES:
        - WARNING at -1.5% daily loss (prepare to exit)
        - CRITICAL at -1.8% daily loss (suggest liquidation)
        - EMERGENCY at -2.0% daily loss (mandatory liquidation - same as max_daily_loss)
        
        Args:
            current_pnl: Today's P&L
            account_value: Total account value
        
        Returns:
            Dict with:
                - liquidate: bool (True if should liquidate all positions)
                - severity: str ('none', 'warning', 'critical', 'emergency')
                - message: str (explanation)
                - loss_pct: float (current loss percentage)
        """
        loss_pct = abs(current_pnl) / account_value if current_pnl < 0 else 0
        
        # EMERGENCY: Mandatory liquidation (same as daily loss limit)
        if loss_pct >= self.max_daily_loss:
            logger.error(f"🚨 EMERGENCY LIQUIDATION TRIGGERED!")
            logger.error(f"   Loss: ${current_pnl:,.2f} ({loss_pct*100:.2f}%) >= {self.max_daily_loss*100:.1f}% limit")
            logger.error(f"   ACTION: Selling all positions to prevent further damage")
            return {
                'liquidate': True,
                'severity': 'emergency',
                'message': f'EMERGENCY: Loss {loss_pct*100:.2f}% reached max {self.max_daily_loss*100:.1f}% limit. Liquidating all positions.',
                'loss_pct': loss_pct
            }
        
        # CRITICAL: Strong suggestion to liquidate (90% of limit)
        critical_threshold = self.max_daily_loss * 0.90
        if loss_pct >= critical_threshold:
            logger.warning(f"🔴 CRITICAL LOSS LEVEL!")
            logger.warning(f"   Loss: ${current_pnl:,.2f} ({loss_pct*100:.2f}%) approaching {self.max_daily_loss*100:.1f}% limit")
            logger.warning(f"   SUGGESTION: Consider liquidating positions")
            return {
                'liquidate': True,
                'severity': 'critical',
                'message': f'CRITICAL: Loss {loss_pct*100:.2f}% near limit. Strong liquidation recommendation.',
                'loss_pct': loss_pct
            }
        
        # WARNING: Approaching danger zone (75% of limit)
        warning_threshold = self.max_daily_loss * 0.75
        if loss_pct >= warning_threshold:
            logger.warning(f"⚠️ HIGH LOSS WARNING!")
            logger.warning(f"   Loss: ${current_pnl:,.2f} ({loss_pct*100:.2f}%)")
            logger.warning(f"   Monitor closely - approaching {self.max_daily_loss*100:.1f}% limit")
            return {
                'liquidate': False,
                'severity': 'warning',
                'message': f'WARNING: Loss {loss_pct*100:.2f}% approaching danger zone. New positions restricted.',
                'loss_pct': loss_pct
            }
        
        # All clear
        return {
            'liquidate': False,
            'severity': 'none',
            'message': f'Loss levels acceptable: {loss_pct*100:.2f}%',
            'loss_pct': loss_pct
        }
        
        # Keep last 30 days of loss history
        old_dates = [d for d in self.daily_losses.keys() if (today - d).days > 30]
        for d in old_dates:
            del self.daily_losses[d]
    
    def get_daily_stats(self) -> Dict[str, Any]:
        """Get daily risk statistics"""
        today = date.today()
        return {
            'date': today.isoformat(),
            'trades_today': self.trade_count_today,
            'daily_pnl': self.daily_losses.get(today, 0),
            'limits': {
                'max_position_size': f"{self.max_position_size*100:.1f}%",
                'max_daily_loss': f"{self.max_daily_loss*100:.1f}%",
                'max_portfolio_risk': f"{self.max_portfolio_risk*100:.1f}%"
            }
        }


    # ========================================================================
    # ADVANCED OPTIMIZATIONS
    # ========================================================================
    
    def calculate_kelly_position_size(
        self,
        symbol: str,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        account_value: float,
        current_price: float,
        max_kelly_fraction: float = 0.25
    ) -> Dict[str, Any]:
        """
        Calculate optimal position size using Kelly Criterion.
        
        Kelly Formula: f* = (bp - q) / b
        Where:
        - f* = optimal fraction of capital to risk
        - b = win/loss ratio (avg_win / avg_loss)
        - p = probability of win (win_rate)
        - q = probability of loss (1 - win_rate)
        
        Args:
            symbol: Stock ticker
            win_rate: Historical win rate (0.0 to 1.0)
            avg_win: Average winning trade amount
            avg_loss: Average losing trade amount (positive number)
            account_value: Total account value
            current_price: Current stock price
            max_kelly_fraction: Fractional Kelly multiplier (default 0.25 = quarter Kelly)
        
        Returns:
            Dictionary with Kelly recommendations
        """
        # Validate inputs
        if win_rate <= 0 or win_rate >= 1:
            logger.warning(f"Invalid win rate: {win_rate}")
            return self._default_position_size(account_value, current_price)
        
        if avg_win <= 0 or avg_loss <= 0:
            logger.warning(f"Invalid win/loss amounts: win=${avg_win}, loss=${avg_loss}")
            return self._default_position_size(account_value, current_price)
        
        # Calculate win/loss ratio
        win_loss_ratio = avg_win / avg_loss
        
        # Calculate Kelly percentage
        # f* = (bp - q) / b
        kelly_pct = (win_loss_ratio * win_rate - (1 - win_rate)) / win_loss_ratio
        
        # Apply fractional Kelly (typically 25-50% of full Kelly to reduce volatility)
        fractional_kelly = kelly_pct * max_kelly_fraction
        
        # Enforce bounds: never exceed max position size or go negative
        kelly_bounded = max(0, min(fractional_kelly, self.max_position_size))
        
        # Calculate position value and shares
        kelly_position_value = account_value * kelly_bounded
        kelly_shares = int(kelly_position_value / current_price)
        
        # Log recommendation
        logger.info(f"📊 Kelly Criterion for {symbol}:")
        logger.info(f"   Win Rate: {win_rate*100:.1f}% | W/L Ratio: {win_loss_ratio:.2f}")
        logger.info(f"   Full Kelly: {kelly_pct*100:.1f}% | Fractional Kelly ({max_kelly_fraction}x): {fractional_kelly*100:.1f}%")
        logger.info(f"   Recommended: {kelly_shares} shares = ${kelly_position_value:,.2f} ({kelly_bounded*100:.1f}%)")
        
        return {
            'symbol': symbol,
            'full_kelly_pct': kelly_pct,
            'fractional_kelly_pct': fractional_kelly,
            'bounded_kelly_pct': kelly_bounded,
            'recommended_shares': kelly_shares,
            'position_value': kelly_position_value,
            'win_rate': win_rate,
            'win_loss_ratio': win_loss_ratio,
            'reasoning': f"Kelly Criterion recommends {kelly_bounded*100:.1f}% position ({kelly_shares} shares)"
        }
    
    def _default_position_size(self, account_value: float, current_price: float) -> Dict[str, Any]:
        """Return default position size when Kelly calculation fails."""
        default_pct = 0.05  # 5% default
        position_value = account_value * default_pct
        shares = int(position_value / current_price)
        
        return {
            'fractional_kelly_pct': default_pct,
            'bounded_kelly_pct': default_pct,
            'recommended_shares': shares,
            'position_value': position_value,
            'reasoning': 'Default 5% position (Kelly calculation unavailable)'
        }
    
    def calculate_volatility_adjusted_size(
        self,
        symbol: str,
        base_shares: int,
        current_volatility: float,
        target_volatility: float = 0.15,
        price: float = None
    ) -> Dict[str, Any]:
        """
        Adjust position size based on volatility to maintain consistent risk.
        
        Higher volatility → Smaller position
        Lower volatility → Larger position
        
        Args:
            symbol: Stock ticker
            base_shares: Base position size (from Kelly or other method)
            current_volatility: Current annualized volatility (e.g., 0.25 = 25%)
            target_volatility: Target portfolio volatility (default 15%)
            price: Current stock price (for logging)
        
        Returns:
            Dictionary with volatility-adjusted recommendations
        """
        # Validate inputs
        if current_volatility <= 0:
            logger.warning(f"Invalid volatility: {current_volatility}")
            return {
                'adjusted_shares': base_shares,
                'volatility_adjustment': 1.0,
                'reasoning': 'Invalid volatility, no adjustment applied'
            }
        
        # Calculate adjustment factor
        # If current vol = target vol → factor = 1.0 (no change)
        # If current vol > target vol → factor < 1.0 (reduce size)
        # If current vol < target vol → factor > 1.0 (increase size)
        vol_adjustment = target_volatility / current_volatility
        
        # Limit adjustment to prevent extreme positions
        vol_adjustment = max(0.25, min(vol_adjustment, 2.0))  # 0.25x to 2x max
        
        # Apply adjustment
        adjusted_shares = int(base_shares * vol_adjustment)
        
        # Log adjustment
        logger.info(f"📊 Volatility Adjustment for {symbol}:")
        logger.info(f"   Current Vol: {current_volatility*100:.1f}% | Target Vol: {target_volatility*100:.1f}%")
        logger.info(f"   Adjustment: {vol_adjustment:.2f}x")
        logger.info(f"   Base: {base_shares} shares → Adjusted: {adjusted_shares} shares")
        if price:
            logger.info(f"   Value: ${base_shares*price:,.2f} → ${adjusted_shares*price:,.2f}")
        
        return {
            'symbol': symbol,
            'base_shares': base_shares,
            'adjusted_shares': adjusted_shares,
            'volatility_adjustment': vol_adjustment,
            'current_volatility': current_volatility,
            'target_volatility': target_volatility,
            'reasoning': f"Volatility-adjusted from {base_shares} to {adjusted_shares} shares ({vol_adjustment:.2f}x)"
        }
    
    def calculate_portfolio_correlation(
        self,
        positions: List[Dict[str, Any]],
        historical_returns: Dict[str, pd.Series]
    ) -> Dict[str, Any]:
        """
        Calculate portfolio correlation and diversification score.
        
        Lower correlation = Better diversification
        High correlation (>0.7) = Concentrated risk
        
        Args:
            positions: List of current positions with symbols and values
            historical_returns: Dict mapping symbol to returns series
        
        Returns:
            Dictionary with correlation analysis
        """
        if len(positions) < 2:
            return {
                'avg_correlation': 0.0,
                'diversification_score': 1.0,
                'max_correlation': 0.0,
                'highly_correlated_pairs': [],
                'reasoning': 'Single position - no correlation analysis needed'
            }
        
        # Extract symbols and weights
        symbols = [p['symbol'] for p in positions if p['symbol'] in historical_returns]
        
        if len(symbols) < 2:
            return {
                'avg_correlation': 0.0,
                'diversification_score': 1.0,
                'reasoning': 'Insufficient historical data for correlation analysis'
            }
        
        # Build returns matrix
        returns_matrix = pd.DataFrame({
            symbol: historical_returns[symbol]
            for symbol in symbols
        })
        
        # Calculate correlation matrix
        corr_matrix = returns_matrix.corr()
        
        # Extract upper triangle (avoid double-counting pairs)
        upper_triangle = np.triu(corr_matrix.values, k=1)
        correlations = upper_triangle[upper_triangle != 0]
        
        # Calculate metrics
        avg_correlation = np.mean(correlations) if len(correlations) > 0 else 0.0
        max_correlation = np.max(correlations) if len(correlations) > 0 else 0.0
        
        # Diversification score: 1.0 = perfect diversification, 0.0 = perfectly correlated
        diversification_score = 1.0 - abs(avg_correlation)
        
        # Find highly correlated pairs (>0.7)
        highly_correlated = []
        for i in range(len(symbols)):
            for j in range(i+1, len(symbols)):
                corr = corr_matrix.iloc[i, j]
                if abs(corr) > 0.7:
                    highly_correlated.append({
                        'pair': f"{symbols[i]}/{symbols[j]}",
                        'correlation': corr
                    })
        
        logger.info(f"📊 Portfolio Correlation Analysis:")
        logger.info(f"   Symbols: {len(symbols)}")
        logger.info(f"   Avg Correlation: {avg_correlation:.3f}")
        logger.info(f"   Max Correlation: {max_correlation:.3f}")
        logger.info(f"   Diversification Score: {diversification_score:.3f}")
        if highly_correlated:
            logger.warning(f"   ⚠️ {len(highly_correlated)} highly correlated pairs found")
            for pair in highly_correlated[:3]:  # Show first 3
                logger.warning(f"      {pair['pair']}: {pair['correlation']:.3f}")
        
        return {
            'symbols': symbols,
            'avg_correlation': avg_correlation,
            'max_correlation': max_correlation,
            'diversification_score': diversification_score,
            'highly_correlated_pairs': highly_correlated,
            'correlation_matrix': corr_matrix.to_dict(),
            'reasoning': f"Portfolio has {diversification_score:.1%} diversification (avg corr: {avg_correlation:.3f})"
        }
    
    def calculate_sharpe_ratio(
        self,
        returns: pd.Series,
        risk_free_rate: float = 0.05
    ) -> Dict[str, Any]:
        """
        Calculate Sharpe ratio for performance measurement.
        
        Sharpe Ratio = (Return - Risk Free Rate) / Standard Deviation
        
        Interpretation:
        - > 2.0: Excellent
        - 1.0-2.0: Good
        - 0.0-1.0: Suboptimal
        - < 0.0: Losing money
        
        Args:
            returns: Series of returns (daily, weekly, etc.)
            risk_free_rate: Annual risk-free rate (default 5%)
        
        Returns:
            Dictionary with Sharpe ratio and analysis
        """
        if len(returns) < 2:
            return {
                'sharpe_ratio': 0.0,
                'reasoning': 'Insufficient data for Sharpe ratio calculation'
            }
        
        # Calculate metrics
        avg_return = returns.mean()
        std_return = returns.std()
        
        # Annualize if daily returns (assuming 252 trading days)
        periods_per_year = 252
        annualized_return = avg_return * periods_per_year
        annualized_std = std_return * np.sqrt(periods_per_year)
        
        # Calculate Sharpe ratio
        sharpe_ratio = (annualized_return - risk_free_rate) / annualized_std if annualized_std > 0 else 0.0
        
        # Interpret
        if sharpe_ratio > 2.0:
            interpretation = "Excellent"
        elif sharpe_ratio > 1.0:
            interpretation = "Good"
        elif sharpe_ratio > 0.0:
            interpretation = "Suboptimal"
        else:
            interpretation = "Poor (losing money)"
        
        logger.info(f"📊 Sharpe Ratio Analysis:")
        logger.info(f"   Avg Daily Return: {avg_return*100:.3f}%")
        logger.info(f"   Annualized Return: {annualized_return*100:.1f}%")
        logger.info(f"   Annualized Volatility: {annualized_std*100:.1f}%")
        logger.info(f"   Sharpe Ratio: {sharpe_ratio:.2f} ({interpretation})")
        
        return {
            'sharpe_ratio': sharpe_ratio,
            'avg_daily_return': avg_return,
            'daily_std': std_return,
            'annualized_return': annualized_return,
            'annualized_volatility': annualized_std,
            'interpretation': interpretation,
            'reasoning': f"Sharpe ratio {sharpe_ratio:.2f} ({interpretation}) - Risk-adjusted return measure"
        }


# Singleton instance
_risk_manager = None


def get_risk_manager() -> RiskManager:
    """Get or create singleton risk manager"""
    global _risk_manager
    if _risk_manager is None:
        _risk_manager = RiskManager()
    return _risk_manager


if __name__ == "__main__":
    # Test risk manager
    print("\n" + "="*60)
    print("Testing Risk Manager...")
    print("="*60)
    
    rm = get_risk_manager()
    
    # Test 1: Position size check
    print("\n" + "-"*60)
    print("Test 1: Position Size Check")
    print("-"*60)
    
    account_value = 100000
    price = 150
    
    # OK: 5% position
    result = rm.check_position_size("AAPL", 33, price, account_value)
    print(f"33 shares @ $150 = $4,950 (5%): {result.approved} - {result.reason}")
    
    # Too large: 15% position
    result = rm.check_position_size("AAPL", 100, price, account_value)
    print(f"100 shares @ $150 = $15,000 (15%): {result.approved} - {result.reason}")
    if result.max_shares:
        print(f"  → Max allowed: {result.max_shares} shares")
    
    # Test 2: Daily loss limit
    print("\n" + "-"*60)
    print("Test 2: Daily Loss Limit")
    print("-"*60)
    
    # Small loss: OK
    result = rm.check_daily_loss_limit(-500, account_value)
    print(f"Loss $500 (0.5%): {result.approved} - {result.reason}")
    
    # Large loss: STOP
    result = rm.check_daily_loss_limit(-2500, account_value)
    print(f"Loss $2,500 (2.5%): {result.approved} - {result.reason}")
    
    # Test 3: Portfolio exposure
    print("\n" + "-"*60)
    print("Test 3: Portfolio Exposure")
    print("-"*60)
    
    # Low exposure: OK
    positions = [
        {'market_value': 10000},
        {'market_value': 5000}
    ]
    result = rm.check_portfolio_exposure(positions, account_value)
    print(f"$15,000 exposure (15%): {result.approved} - {result.reason}")
    
    # High exposure: WARNING
    positions = [
        {'market_value': 15000},
        {'market_value': 10000},
        {'market_value': 8000}
    ]
    result = rm.check_portfolio_exposure(positions, account_value)
    print(f"$33,000 exposure (33%): {result.approved} - {result.reason}")
    
    # Test 4: Full trade validation
    print("\n" + "-"*60)
    print("Test 4: Full Trade Validation")
    print("-"*60)
    
    result = rm.validate_trade(
        symbol="AAPL",
        action="buy",
        shares=50,
        price=150,
        account_value=account_value,
        current_pnl=-500,
        positions=positions
    )
    print(f"\nValidation result: {result.approved}")
    print(f"Reason: {result.reason}")
    if result.warnings:
        print("Warnings:")
        for w in result.warnings:
            print(f"  - {w}")
    
    # Test 5: Daily stats
    print("\n" + "-"*60)
    print("Test 5: Daily Statistics")
    print("-"*60)
    
    rm.record_trade("AAPL", "buy", 50, 150)
    rm.record_trade("MSFT", "sell", 25, 300)
    
    stats = rm.get_daily_stats()
    print(f"Date: {stats['date']}")
    print(f"Trades today: {stats['trades_today']}")
    print(f"Daily P&L: ${stats['daily_pnl']:,.2f}")
    print(f"Limits: {stats['limits']}")
    
    print("\n" + "="*60)
    print("✅ Risk Manager test complete!")
    print("="*60)
