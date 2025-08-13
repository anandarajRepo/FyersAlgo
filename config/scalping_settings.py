# config/scalping_settings.py

from dataclasses import dataclass
from typing import Dict, List
from config.settings import Sector


@dataclass
class ScalpingConfig:
    """Configuration for Level II Scalping Strategy"""

    # Order book analysis parameters
    min_bid_ask_imbalance_ratio: float = 2.5  # Minimum bid/ask volume ratio for strong imbalance
    min_order_book_depth: int = 5  # Minimum depth levels to analyze
    min_volume_at_level: int = 2000  # Minimum volume at support/resistance level
    order_book_refresh_seconds: float = 0.5  # How often to refresh order book data

    # Position sizing and risk management
    max_positions: int = 1  # Max simultaneous positions (scalping needs focus)
    position_size_percentage: float = 0.15  # 0.15% of portfolio per trade (small size)
    stop_loss_ticks: int = 3  # Stop loss in ticks (very tight for scalping)
    target_ticks: int = 6  # Target in ticks (2:1 risk-reward minimum)

    # Timing constraints for scalping
    min_hold_seconds: int = 5  # Minimum hold time to avoid wash trading
    max_hold_seconds: int = 45  # Maximum hold time for scalping
    cooldown_seconds: int = 120  # Cooldown between trades on same symbol
    max_trades_per_hour: int = 20  # Limit to avoid overtrading

    # Market microstructure filters
    min_spread_ticks: int = 1  # Minimum spread for viable scalping
    max_spread_ticks: int = 4  # Maximum spread that still allows profit
    min_tick_value: float = 0.05  # Minimum tick size for calculations
    min_market_volatility: float = 0.3  # Minimum ATR for viable scalping
    max_market_volatility: float = 3.0  # Maximum volatility to avoid chaos

    # Quality and confidence filters
    min_confidence: float = 0.80  # Higher confidence threshold for scalping
    min_volume_ratio: float = 1.5  # Minimum volume vs average for entry
    require_momentum_confirmation: bool = True  # Require price momentum

    # Advanced order book analysis
    imbalance_lookback_levels: int = 3  # How many levels to check for imbalance
    support_resistance_strength: float = 2.0  # Multiplier for strong S/R levels
    order_flow_window_seconds: int = 10  # Window for order flow analysis

    # Risk management
    daily_loss_limit: float = 0.5  # Stop scalping if daily loss exceeds 0.5%
    max_consecutive_losses: int = 3  # Stop after 3 consecutive losses
    profit_target_multiplier: float = 3.0  # Take profits at 3x average win

    # Symbol-specific settings
    preferred_symbols: List[str] = None  # Will be set in __post_init__
    avoid_symbols: List[str] = None  # Symbols to avoid for scalping

    def __post_init__(self):
        if self.preferred_symbols is None:
            # Most liquid stocks suitable for scalping
            self.preferred_symbols = [
                'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS',
                'ICICIBANK.NS', 'ITC.NS', 'SBIN.NS', 'HINDUNILVR.NS',
                'LT.NS', 'AXISBANK.NS', 'BAJFINANCE.NS', 'MARUTI.NS'
            ]

        if self.avoid_symbols is None:
            # Avoid low liquidity or highly volatile stocks
            self.avoid_symbols = [
                'SUZLON.NS', 'YESBANK.NS', 'RPOWER.NS'  # Example low-quality stocks
            ]


@dataclass
class MultiStrategyScalpingConfig:
    """Configuration for integrating scalping with existing strategies"""

    # Portfolio allocation
    scalping_allocation: float = 0.1  # 10% allocation for scalping
    gap_up_allocation: float = 0.5  # 50% for gap-up strategy
    breakout_allocation: float = 0.4  # 40% for breakout strategy

    # Position limits with scalping
    max_total_positions: int = 6  # Increased to accommodate scalping
    max_scalping_positions: int = 1  # Scalping positions
    max_gap_up_positions: int = 3  # Gap-up positions
    max_breakout_positions: int = 2  # Breakout positions

    # Risk coordination between strategies
    strategy_correlation_limit: float = 0.6  # Lower correlation limit
    portfolio_stop_loss: float = 4.0  # Slightly lower portfolio stop
    daily_profit_target: float = 3.0  # Same daily target

    # Scalping-specific integration rules
    allow_scalping_during_signals: bool = False  # Don't scalp during other strategy signals
    scalping_priority: int = 3  # Lower priority than main strategies
    cross_strategy_cooldown_minutes: int = 5  # Cooldown after other strategy trades