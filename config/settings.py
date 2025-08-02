import os
from dataclasses import dataclass
from typing import Dict, Optional
from enum import Enum

class Sector(Enum):
    FMCG = "FMCG"
    IT = "IT"
    BANKING = "BANKING"
    AUTO = "AUTO"
    PHARMA = "PHARMA"
    METALS = "METALS"
    REALTY = "REALTY"

@dataclass
class FyersConfig:
    client_id: str
    secret_key: str
    redirect_uri: str
    access_token: Optional[str] = None
    base_url: str = "https://api-t1.fyers.in/api/v3"

@dataclass
class StrategyConfig:
    portfolio_value: float = 1000000
    risk_per_trade_pct: float = 1.0
    max_positions: int = 3
    min_gap_percentage: float = 0.5
    min_selling_pressure: float = 40.0
    min_volume_ratio: float = 1.2
    min_confidence: float = 0.6
    stop_loss_pct: float = 1.5
    target_pct: float = 3.0

@dataclass
class TradingConfig:
    market_start_hour: int = 9
    market_start_minute: int = 15
    market_end_hour: int = 15
    market_end_minute: int = 30
    signal_generation_end_hour: int = 10
    signal_generation_end_minute: int = 30
    monitoring_interval: int = 30
    execution_delay: int = 5