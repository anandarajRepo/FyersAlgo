from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from models.trading_models import MarketData
import pandas as pd


class IDataProvider(ABC):
    """Interface for market data providers"""

    @abstractmethod
    async def get_quotes(self, symbols: List[str]) -> Dict[str, MarketData]:
        """Get real-time quotes for symbols"""
        pass

    @abstractmethod
    def get_historical_data(self, symbol: str, period: str) -> pd.DataFrame:
        """Get historical data for analysis"""
        pass

    @abstractmethod
    async def get_index_data(self, index_symbol: str) -> Dict:
        """Get index data (like Nifty)"""
        pass


class IBroker(ABC):
    """Interface for broker operations"""

    @abstractmethod
    def place_order(self, symbol: str, side: str, quantity: int,
                    order_type: str, price: float = 0) -> Optional[Dict]:
        """Place a single order"""
        pass

    @abstractmethod
    def place_bracket_order(self, symbol: str, quantity: int, price: float,
                            stop_loss: float, target: float) -> Optional[Dict]:
        """Place bracket order with SL and target"""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict]:
        """Get current positions"""
        pass

    @abstractmethod
    def get_orders(self) -> List[Dict]:
        """Get order book"""
        pass