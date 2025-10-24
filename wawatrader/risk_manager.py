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

from config.settings import settings


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
    """
    Enforce hard-coded risk rules.
    
    CRITICAL: These rules are ABSOLUTE. No LLM recommendation can override them.
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
        
        Args:
            symbol: Stock ticker
            action: "buy" or "sell"
        
        Returns:
            RiskCheckResult with approval
        """
        max_trades_per_day = 10  # Hard limit
        
        warnings = []
        
        if self.trade_count_today >= max_trades_per_day:
            return RiskCheckResult(
                approved=False,
                reason=f"Daily trade limit reached: {self.trade_count_today}/{max_trades_per_day} trades today"
            )
        
        # Warning if approaching limit
        if self.trade_count_today >= max_trades_per_day * 0.8:
            warnings.append(
                f"High trade frequency: {self.trade_count_today}/{max_trades_per_day} trades today"
            )
        
        return RiskCheckResult(
            approved=True,
            reason=f"Trade frequency OK: {self.trade_count_today}/{max_trades_per_day} trades today",
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
