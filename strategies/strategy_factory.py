from typing import Dict, List, Type
from abc import ABC, abstractmethod
import asyncio
import logging

logger = logging.getLogger(__name__)


class BaseStrategy(ABC):
    """Base class for all trading strategies"""

    def __init__(self, name: str, config: Dict):
        self.name = name
        self.config = config
        self.positions = {}
        self.daily_pnl = 0.0
        self.total_pnl = 0.0

    @abstractmethod
    async def generate_signals(self) -> List:
        """Generate trading signals"""
        pass

    @abstractmethod
    async def execute_signal(self, signal) -> bool:
        """Execute a trading signal"""
        pass

    @abstractmethod
    def get_performance(self) -> Dict:
        """Get strategy performance metrics"""
        pass

    def get_name(self) -> str:
        return self.name


class StrategyFactory:
    """Factory for creating and managing trading strategies"""

    _strategies: Dict[str, Type] = {}

    @classmethod
    def register_strategy(cls, name: str, strategy_class: Type):
        """Register a strategy class"""
        cls._strategies[name] = strategy_class
        logger.info(f"Registered strategy: {name}")

    @classmethod
    def create_strategy(cls, name: str, config: Dict):
        """Create a strategy instance"""
        if name not in cls._strategies:
            raise ValueError(f"Unknown strategy: {name}")

        strategy_class = cls._strategies[name]
        return strategy_class(**config)

    @classmethod
    def get_available_strategies(cls) -> List[str]:
        """Get list of available strategies"""
        return list(cls._strategies.keys())


class StrategyPortfolio:
    """Portfolio manager for multiple strategies"""

    def __init__(self, strategies: List):
        self.strategies = strategies
        self.portfolio_pnl = 0.0
        self.daily_portfolio_pnl = 0.0

    async def run_all_strategies(self) -> None:
        """Run all strategies concurrently"""
        try:
            # Run all strategies in parallel
            tasks = []
            for strategy in self.strategies:
                if hasattr(strategy, 'run_strategy_cycle'):
                    tasks.append(strategy.run_strategy_cycle())
                elif hasattr(strategy, 'run_breakout_cycle'):
                    tasks.append(strategy.run_breakout_cycle())

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            # Update portfolio performance
            self._update_portfolio_performance()

        except Exception as e:
            logger.error(f"Error running strategy portfolio: {e}")

    def _update_portfolio_performance(self) -> None:
        """Update overall portfolio performance"""
        self.portfolio_pnl = sum(getattr(strategy, 'total_pnl', 0) for strategy in self.strategies)
        self.daily_portfolio_pnl = sum(getattr(strategy, 'daily_pnl', 0) for strategy in self.strategies)

    def get_portfolio_summary(self) -> Dict:
        """Get comprehensive portfolio summary"""
        total_positions = sum(len(getattr(strategy, 'positions', {})) for strategy in self.strategies)

        strategy_performance = {}
        for strategy in self.strategies:
            if hasattr(strategy, 'get_performance_summary'):
                strategy_performance[strategy.__class__.__name__] = strategy.get_performance_summary()
            elif hasattr(strategy, 'get_breakout_performance'):
                strategy_performance[strategy.__class__.__name__] = strategy.get_breakout_performance()

        return {
            'portfolio_total_pnl': self.portfolio_pnl,
            'portfolio_daily_pnl': self.daily_portfolio_pnl,
            'total_active_positions': total_positions,
            'strategies': strategy_performance,
            'strategy_count': len(self.strategies)
        }