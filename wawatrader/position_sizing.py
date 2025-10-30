"""
Kelly Criterion Position Sizing
================================
Hybrid position sizing using Kelly Criterion (mathematical base) 
combined with LLM conviction (contextual modifier).

This replaces arbitrary position sizing with mathematically-backed sizing
that respects historical performance and LLM intelligence.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from loguru import logger


@dataclass
class PositionSize:
    """Result of position sizing calculation"""
    symbol: str
    kelly_fraction: float
    conviction_adjusted_kelly: float
    fractional_kelly: float
    base_position_usd: float
    final_position_usd: float
    final_position_pct: float
    shares: int
    reasoning: str
    emergency_stops_applied: List[str]


class KellyLLMPositionSizer:
    """
    Hybrid position sizing: Kelly Criterion (math) + LLM conviction (context).
    
    Formula:
    1. Calculate Kelly fraction from historical win rate and R:R
    2. Multiply by LLM conviction (0-100 scale)
    3. Apply fractional Kelly (50% for safety)
    4. Apply emergency stops (20% position, 40% sector, 60% heat)
    
    Kelly Formula: f* = (p*b - q) / b
    Where:
    - p = win rate (from historical data)
    - q = 1 - p
    - b = average_win / average_loss
    """
    
    # Emergency stops (ONLY hardcoded limits)
    MAX_SINGLE_POSITION_PCT = 0.20  # 20% max single position
    MAX_SECTOR_EXPOSURE_PCT = 0.40  # 40% max sector exposure
    MAX_TOTAL_HEAT_PCT = 0.60       # 60% max total portfolio heat
    
    def __init__(self, memory_store):
        """
        Args:
            memory_store: DecisionMemory store for historical performance
        """
        self.memory_store = memory_store
    
    def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        strategy: str,
        llm_conviction: float,  # 0-100
        portfolio_value: float,
        existing_positions: List[Dict[str, Any]],
        sector_map: Dict[str, str] = None
    ) -> PositionSize:
        """
        Calculate position size with Kelly Criterion + LLM conviction.
        
        Args:
            symbol: Stock symbol
            entry_price: Entry price for the position
            strategy: Strategy name (for historical performance lookup)
            llm_conviction: LLM's conviction score (0-100)
            portfolio_value: Total portfolio value
            existing_positions: List of current positions
            sector_map: Optional map of symbol -> sector
        
        Returns:
            PositionSize with all calculations and reasoning
        """
        
        # Step 1: Get historical performance for this strategy
        performance = self.memory_store.get_strategy_performance(strategy)
        
        # Step 2: Calculate pure Kelly fraction
        kelly_fraction = self._calculate_kelly(
            win_rate=performance.get('win_rate', 0.55),
            avg_win_pct=performance.get('avg_win_pct', 3.5),
            avg_loss_pct=performance.get('avg_loss_pct', 2.0),
            num_trades=performance.get('num_trades', 0)
        )
        
        # Step 3: Apply LLM conviction modifier
        conviction_multiplier = llm_conviction / 100.0
        conviction_adjusted = kelly_fraction * conviction_multiplier
        
        # Step 4: Apply fractional Kelly (use 75% - aggressive but still safe)
        fractional_kelly = conviction_adjusted * 0.75
        
        # Step 5: Calculate base dollar amount
        base_position_usd = portfolio_value * fractional_kelly
        
        # Step 6: Apply emergency stops
        final_position_usd, stops_applied = self._apply_emergency_stops(
            base_size=base_position_usd,
            portfolio_value=portfolio_value,
            symbol=symbol,
            existing_positions=existing_positions,
            sector_map=sector_map or {}
        )
        
        # Step 7: Calculate shares
        shares = int(final_position_usd / entry_price) if entry_price > 0 else 0
        
        # Step 8: Generate reasoning
        reasoning = self._generate_reasoning(
            kelly_fraction=kelly_fraction,
            conviction=llm_conviction,
            performance=performance,
            base_size=base_position_usd,
            final_size=final_position_usd,
            portfolio_value=portfolio_value
        )
        
        return PositionSize(
            symbol=symbol,
            kelly_fraction=kelly_fraction,
            conviction_adjusted_kelly=conviction_adjusted,
            fractional_kelly=fractional_kelly,
            base_position_usd=base_position_usd,
            final_position_usd=final_position_usd,
            final_position_pct=(final_position_usd / portfolio_value) * 100,
            shares=shares,
            reasoning=reasoning,
            emergency_stops_applied=stops_applied
        )
    
    def _calculate_kelly(
        self,
        win_rate: float,
        avg_win_pct: float,
        avg_loss_pct: float,
        num_trades: int
    ) -> float:
        """
        Pure Kelly Criterion calculation from historical performance.
        
        Returns fraction of portfolio to risk (0.0 to 1.0)
        """
        # Need at least 10 trades for reliable Kelly
        if num_trades < 10:
            logger.warning(
                f"⚠️ Insufficient trade history ({num_trades} trades) - using bootstrap default (5%)"
            )
            return 0.05  # 5% of portfolio (bootstrap mode - allows initial trading)
        
        # Kelly formula: f* = (p*b - q) / b
        p = win_rate
        q = 1 - win_rate
        b = avg_win_pct / avg_loss_pct if avg_loss_pct > 0 else 1.0
        
        if avg_loss_pct == 0:
            logger.warning("⚠️ Zero average loss - using conservative default")
            return 0.02
        
        kelly = (p * b - q) / b
        
        # Kelly can suggest crazy sizes (even > 100%), cap it
        kelly_capped = max(0, min(kelly, 0.10))  # Never more than 10% from pure Kelly
        
        logger.debug(
            f"📊 Kelly calculation: win_rate={p:.2f}, b={b:.2f}, "
            f"kelly={kelly:.3f}, capped={kelly_capped:.3f}"
        )
        
        return kelly_capped
    
    def _apply_emergency_stops(
        self,
        base_size: float,
        portfolio_value: float,
        symbol: str,
        existing_positions: List[Dict[str, Any]],
        sector_map: Dict[str, str]
    ) -> tuple[float, List[str]]:
        """
        Apply EMERGENCY STOPS (the ONLY hardcoded limits).
        
        Returns: (final_size, list_of_stops_applied)
        """
        final_size = base_size
        stops_applied = []
        
        # Emergency Stop #1: Single position limit (20%)
        max_single = portfolio_value * self.MAX_SINGLE_POSITION_PCT
        if final_size > max_single:
            logger.warning(
                f"⚠️ Position size ${final_size:,.0f} exceeds single-position limit "
                f"${max_single:,.0f} (20%) - capping"
            )
            final_size = max_single
            stops_applied.append(f"Single position limit: ${max_single:,.0f}")
        
        # Emergency Stop #2: Sector concentration limit (40%)
        symbol_sector = sector_map.get(symbol, "Unknown")
        sector_exposure = sum(
            pos.get('value', 0) for pos in existing_positions
            if sector_map.get(pos.get('symbol', ''), '') == symbol_sector
        )
        max_sector = portfolio_value * self.MAX_SECTOR_EXPOSURE_PCT
        
        if sector_exposure + final_size > max_sector:
            logger.warning(
                f"⚠️ Sector exposure ${sector_exposure + final_size:,.0f} exceeds limit "
                f"${max_sector:,.0f} (40% for {symbol_sector}) - capping"
            )
            final_size = max(0, max_sector - sector_exposure)
            stops_applied.append(f"Sector limit ({symbol_sector}): ${max_sector:,.0f}")
        
        # Emergency Stop #3: Total portfolio heat limit (60%)
        total_heat = sum(pos.get('value', 0) for pos in existing_positions)
        max_heat = portfolio_value * self.MAX_TOTAL_HEAT_PCT
        
        if total_heat + final_size > max_heat:
            logger.warning(
                f"⚠️ Total heat ${total_heat + final_size:,.0f} exceeds limit "
                f"${max_heat:,.0f} (60%) - capping"
            )
            final_size = max(0, max_heat - total_heat)
            stops_applied.append(f"Total heat limit: ${max_heat:,.0f}")
        
        return final_size, stops_applied
    
    def _generate_reasoning(
        self,
        kelly_fraction: float,
        conviction: float,
        performance: Dict[str, Any],
        base_size: float,
        final_size: float,
        portfolio_value: float
    ) -> str:
        """Generate human-readable sizing explanation"""
        
        return f"""
Position Sizing Breakdown:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Kelly Criterion: {kelly_fraction*100:.1f}% of portfolio
  ├─ Win Rate: {performance.get('win_rate', 0.55)*100:.1f}%
  ├─ Avg Win: {performance.get('avg_win_pct', 3.5):.1f}%
  ├─ Avg Loss: {performance.get('avg_loss_pct', 2.0):.1f}%
  └─ Historical Trades: {performance.get('num_trades', 0)}

LLM Conviction: {conviction:.0f}/100
Fractional Kelly: 75% (aggressive bootstrap mode)

Base Size: {(base_size/portfolio_value)*100:.2f}% of portfolio
(Kelly × Conviction × Fractional)

Final Size: ${final_size:,.0f} ({(final_size/portfolio_value)*100:.2f}%)

Emergency Stops Applied:
  ✓ Single Position: < 20%
  ✓ Sector Exposure: < 40%
  ✓ Total Heat: < 60%
"""


class PortfolioRiskManager:
    """
    SIMPLIFIED risk management: Only emergency stops.
    
    No arbitrary limits - just 3 hardcoded safety limits.
    """
    
    # Same limits as position sizer
    MAX_SINGLE_POSITION_PCT = 0.20
    MAX_SECTOR_EXPOSURE_PCT = 0.40
    MAX_TOTAL_HEAT_PCT = 0.60
    
    def __init__(self):
        pass
    
    def check_risk_limits(
        self,
        proposed_trade: Dict[str, Any],
        portfolio_value: float,
        existing_positions: List[Dict[str, Any]],
        sector_map: Dict[str, str] = None
    ) -> tuple[bool, List[str]]:
        """
        Check ONLY emergency stops.
        
        Returns: (can_trade, list_of_warnings)
        """
        warnings = []
        can_trade = True
        sector_map = sector_map or {}
        
        # Check #1: Single position limit
        position_pct = proposed_trade.get('size_usd', 0) / portfolio_value
        if position_pct > self.MAX_SINGLE_POSITION_PCT:
            warnings.append(
                f"⛔ BLOCKED: Position {position_pct*100:.1f}% exceeds "
                f"max {self.MAX_SINGLE_POSITION_PCT*100:.0f}%"
            )
            can_trade = False
        
        # Check #2: Sector concentration
        symbol = proposed_trade.get('symbol', '')
        symbol_sector = sector_map.get(symbol, 'Unknown')
        sector_exposure = sum(
            pos.get('value', 0) for pos in existing_positions
            if sector_map.get(pos.get('symbol', ''), '') == symbol_sector
        )
        sector_pct = (sector_exposure + proposed_trade.get('size_usd', 0)) / portfolio_value
        
        if sector_pct > self.MAX_SECTOR_EXPOSURE_PCT:
            warnings.append(
                f"⛔ BLOCKED: Sector exposure {sector_pct*100:.1f}% exceeds "
                f"max {self.MAX_SECTOR_EXPOSURE_PCT*100:.0f}%"
            )
            can_trade = False
        
        # Check #3: Total portfolio heat
        total_heat = sum(pos.get('value', 0) for pos in existing_positions)
        heat_pct = (total_heat + proposed_trade.get('size_usd', 0)) / portfolio_value
        
        if heat_pct > self.MAX_TOTAL_HEAT_PCT:
            warnings.append(
                f"⛔ BLOCKED: Total heat {heat_pct*100:.1f}% exceeds "
                f"max {self.MAX_TOTAL_HEAT_PCT*100:.0f}%"
            )
            can_trade = False
        
        return can_trade, warnings
    
    def get_risk_metrics(
        self,
        portfolio_value: float,
        existing_positions: List[Dict[str, Any]],
        sector_map: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Calculate current risk metrics (for monitoring only).
        """
        sector_map = sector_map or {}
        total_heat = sum(pos.get('value', 0) for pos in existing_positions)
        heat_pct = (total_heat / portfolio_value) * 100 if portfolio_value > 0 else 0
        
        # Sector breakdown
        sectors = {}
        for pos in existing_positions:
            sector = sector_map.get(pos.get('symbol', ''), 'Unknown')
            sectors[sector] = sectors.get(sector, 0) + pos.get('value', 0)
        
        max_sector_exposure = max(sectors.values()) if sectors else 0
        max_sector_pct = (max_sector_exposure / portfolio_value) * 100 if portfolio_value > 0 else 0
        
        # Largest position
        largest_position = max(
            (pos.get('value', 0) for pos in existing_positions),
            default=0
        )
        largest_position_pct = (largest_position / portfolio_value) * 100 if portfolio_value > 0 else 0
        
        # Status calculation
        status = self._calculate_status(heat_pct, max_sector_pct, largest_position_pct)
        
        return {
            'total_heat_pct': heat_pct,
            'max_sector_pct': max_sector_pct,
            'largest_position_pct': largest_position_pct,
            'num_positions': len(existing_positions),
            'available_buying_power_pct': 100 - heat_pct,
            'sector_breakdown': {
                sector: (value / portfolio_value) * 100
                for sector, value in sectors.items()
            },
            'emergency_stops': {
                'single_position_limit': self.MAX_SINGLE_POSITION_PCT * 100,
                'sector_limit': self.MAX_SECTOR_EXPOSURE_PCT * 100,
                'total_heat_limit': self.MAX_TOTAL_HEAT_PCT * 100,
            },
            'status': status
        }
    
    def _calculate_status(
        self,
        heat_pct: float,
        sector_pct: float,
        position_pct: float
    ) -> str:
        """Simple traffic light status"""
        if any([
            heat_pct >= self.MAX_TOTAL_HEAT_PCT * 100,
            sector_pct >= self.MAX_SECTOR_EXPOSURE_PCT * 100,
            position_pct >= self.MAX_SINGLE_POSITION_PCT * 100
        ]):
            return "🔴 AT LIMIT - No new positions"
        elif any([
            heat_pct > self.MAX_TOTAL_HEAT_PCT * 80,  # 80% of limit
            sector_pct > self.MAX_SECTOR_EXPOSURE_PCT * 80,
            position_pct > self.MAX_SINGLE_POSITION_PCT * 80
        ]):
            return "🟡 HIGH - Approaching limits"
        else:
            return "🟢 NORMAL - Room for positions"
