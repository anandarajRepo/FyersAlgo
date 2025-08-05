import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from models.trading_models import Position

logger = logging.getLogger(__name__)


class RiskManager:
    """Advanced risk management for multi-strategy system"""

    def __init__(self, multi_strategy_config):
        self.config = multi_strategy_config
        self.daily_start_portfolio_value = 0
        self.current_portfolio_value = 0
        self.risk_violations = []

    def set_daily_start_value(self, value: float) -> None:
        """Set starting portfolio value for the day"""
        self.daily_start_portfolio_value = value
        self.current_portfolio_value = value

    def update_portfolio_value(self, value: float) -> None:
        """Update current portfolio value"""
        self.current_portfolio_value = value

    def check_portfolio_risk(self) -> Dict:
        """Check portfolio-level risk constraints"""
        risk_status = {
            'status': 'SAFE',
            'violations': [],
            'actions_required': []
        }

        if self.daily_start_portfolio_value <= 0:
            return risk_status

        # Calculate daily P&L percentage
        daily_pnl_pct = ((self.current_portfolio_value - self.daily_start_portfolio_value) /
                         self.daily_start_portfolio_value) * 100

        # Check stop loss
        if daily_pnl_pct <= -self.config.portfolio_stop_loss:
            risk_status['status'] = 'STOP_LOSS_HIT'
            risk_status['violations'].append(f"Portfolio down {abs(daily_pnl_pct):.2f}%")
            risk_status['actions_required'].append("CLOSE_ALL_POSITIONS")

        # Check profit target
        elif daily_pnl_pct >= self.config.daily_profit_target:
            risk_status['status'] = 'PROFIT_TARGET_HIT'
            risk_status['violations'].append(f"Portfolio up {daily_pnl_pct:.2f}%")
            risk_status['actions_required'].append("CONSIDER_CLOSING_POSITIONS")

        return risk_status

    def check_position_correlation(self, existing_positions: List[Position],
                                   new_symbol: str, new_sector) -> bool:
        """Check if new position would create excessive correlation"""

        # Count positions in same sector
        sector_count = sum(1 for pos in existing_positions if pos.sector == new_sector)

        # Limit sector concentration
        if sector_count >= 2:  # Max 2 positions per sector
            logger.warning(f"Sector limit reached for {new_sector}")
            return False

        # Check for same stock across strategies
        for pos in existing_positions:
            if pos.symbol == new_symbol:
                logger.warning(f"Already have position in {new_symbol}")
                return False

        return True

    def calculate_position_size_with_correlation(self, base_quantity: int,
                                                 existing_positions: List[Position],
                                                 new_sector) -> int:
        """Adjust position size based on portfolio correlation"""

        # Count positions in same sector
        sector_positions = [pos for pos in existing_positions if pos.sector == new_sector]

        # Reduce size if multiple positions in sector
        if len(sector_positions) >= 1:
            reduction_factor = 0.7  # Reduce by 30%
            adjusted_quantity = int(base_quantity * reduction_factor)
            logger.info(f"Reduced position size due to sector concentration: {base_quantity} -> {adjusted_quantity}")
            return adjusted_quantity

        return base_quantity

    def should_allow_new_position(self, strategy_name: str, current_positions: Dict,
                                  breakout_positions: Dict) -> bool:
        """Determine if new position should be allowed"""

        total_positions = len(current_positions) + len(breakout_positions)

        # Check total position limit
        if total_positions >= self.config.max_total_positions:
            logger.warning(f"Total position limit reached: {total_positions}")
            return False

        # Check strategy-specific limits
        if strategy_name == "gap_up_short" and len(current_positions) >= self.config.max_gap_up_positions:
            logger.warning(f"Gap-up strategy position limit reached")
            return False

        if strategy_name == "breakout" and len(breakout_positions) >= self.config.max_breakout_positions:
            logger.warning(f"Breakout strategy position limit reached")
            return False

        # Check portfolio risk status
        risk_status = self.check_portfolio_risk()
        if risk_status['status'] != 'SAFE':
            logger.warning(f"Portfolio risk violation: {risk_status['status']}")
            return False

        return True