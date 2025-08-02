from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from config.settings import Sector


@dataclass
class TradingSignal:
    symbol: str
    sector: Sector
    signal_type: str
    entry_price: float
    stop_loss: float
    target_price: float
    confidence: float
    gap_percentage: float
    selling_pressure_score: float
    volume_ratio: float
    timestamp: datetime


@dataclass
class Position:
    symbol: str
    entry_price: float
    quantity: int
    stop_loss: float
    target_price: float
    entry_time: datetime
    sector: Sector
    order_id: Optional[str] = None
    sl_order_id: Optional[str] = None


@dataclass
class MarketData:
    symbol: str
    current_price: float
    open_price: float
    high_price: float
    low_price: float
    volume: int
    previous_close: float
    timestamp: datetime


@dataclass
class PnLSummary:
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    closed_positions: list = None

    def __post_init__(self):
        if self.closed_positions is None:
            self.closed_positions = []