from dataclasses import dataclass
from typing import Dict, List
from config.settings import Sector

@dataclass
class BreakoutConfig:
    # Core breakout parameters
    min_breakout_percentage: float = 2.0
    min_volume_multiplier: float = 1.5
    opening_range_minutes: int = 15
    min_price_range: float = 1.0
    max_price_range: float = 50.0
    risk_reward_ratio: float = 2.0
    max_positions_per_strategy: int = 2

    # Advanced filters
    min_stock_price: float = 50.0  # Avoid penny stocks
    max_stock_price: float = 5000.0  # Avoid very expensive stocks
    min_market_cap: float = 1000.0  # Min market cap in crores
    max_gap_up: float = 5.0  # Max gap up allowed for breakout

    # Momentum filters
    min_momentum_score: float = 60.0
    require_uptrend: bool = True

    # Time-based settings
    breakout_start_minutes: int = 15  # Minutes after market open
    breakout_end_hour: int = 11  # Stop new breakouts after 11:30 AM
    breakout_end_minute: int = 30


@dataclass
class MultiStrategyConfig:
    # Portfolio allocation
    gap_up_allocation: float = 0.6  # 60% for gap-up strategy
    breakout_allocation: float = 0.4  # 40% for breakout strategy

    # Position limits
    max_total_positions: int = 5
    max_gap_up_positions: int = 3
    max_breakout_positions: int = 2

    # Risk management
    portfolio_stop_loss: float = 5.0  # Stop all trading if portfolio down 5%
    daily_profit_target: float = 3.0  # Consider stopping if up 3% for day

    # Strategy weights
    strategy_correlation_limit: float = 0.7