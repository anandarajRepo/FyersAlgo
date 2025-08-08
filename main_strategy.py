import asyncio
import logging
from typing import Dict
from datetime import datetime
from config.settings import FyersConfig, StrategyConfig, TradingConfig
from models.trading_models import Position
from services.fyers_service import FyersService
from services.analysis_service import TechnicalAnalysisService
from services.signal_service import SignalGenerationService
from services.position_service import PositionManagementService
from services.market_timing_service import MarketTimingService
from models.trading_models import TradingSignal

logger = logging.getLogger(__name__)


class GapUpShortStrategy:
    """Main strategy orchestrator"""

    def __init__(self,
                 fyers_config: FyersConfig,
                 strategy_config: StrategyConfig,
                 trading_config: TradingConfig):

        # Initialize services
        self.fyers_service = FyersService(fyers_config)
        self.analysis_service = TechnicalAnalysisService(self.fyers_service)
        self.signal_service = SignalGenerationService(self.fyers_service, self.analysis_service)
        self.position_service = PositionManagementService(self.fyers_service, self.fyers_service)
        self.timing_service = MarketTimingService(trading_config)

        # Configuration
        self.strategy_config = strategy_config
        self.trading_config = trading_config

        # State
        self.positions: Dict[str, Position] = {}
        self.daily_pnl = 0.0
        self.total_pnl = 0.0

    async def initialize(self) -> bool:
        """Initialize strategy and verify connections"""
        try:
            # Verify Fyers connection
            profile = self.fyers_service._make_request('GET', '/profile')
            if not profile:
                logger.error("Failed to connect to Fyers API")
                return False

            logger.info(f"Connected to Fyers: {profile.get('name', 'Unknown')}")
            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False

    async def run_strategy_cycle(self) -> None:
        """Run one strategy cycle"""
        try:
            # Monitor existing positions
            pnl_summary = self.position_service.monitor_positions(self.positions)
            self.daily_pnl += pnl_summary.realized_pnl
            self.total_pnl += pnl_summary.realized_pnl

            # Log closed positions
            for closed_pos in pnl_summary.closed_positions:
                logger.info(f"Position closed: {closed_pos['symbol']}, "
                            f"PnL: Rs.{closed_pos['pnl']:.2f}")

            # Generate new signals if in signal generation window
            if self.timing_service.is_signal_generation_time():
                await self._generate_and_execute_signals()

            # Log current status
            self._log_status(pnl_summary.unrealized_pnl)

        except Exception as e:
            logger.error(f"Error in strategy cycle: {e}")

    async def _generate_and_execute_signals(self) -> None:
        """Generate and execute new trading signals"""
        try:
            # Check available position slots
            available_slots = self.strategy_config.max_positions - len(self.positions)
            if available_slots <= 0:
                return

            # Get index data
            index_data = await self.fyers_service.get_index_data()

            # Generate signals
            signals = await self.signal_service.generate_signals(index_data, self.strategy_config)

            # Execute top signals
            executed_count = 0
            for signal in signals[:available_slots]:
                if signal.confidence >= self.strategy_config.min_confidence:
                    success = await self._execute_signal(signal)
                    if success:
                        executed_count += 1
                        await asyncio.sleep(self.trading_config.execution_delay)

            if executed_count > 0:
                logger.info(f"Executed {executed_count} new trades")

        except Exception as e:
            logger.error(f"Error in signal generation/execution: {e}")

    async def _execute_signal(self, signal: TradingSignal) -> bool:
        """Execute a single trading signal"""
        try:
            # Calculate position size
            quantity = self.position_service.calculate_position_size(signal, self.strategy_config)

            if quantity <= 0:
                logger.warning(f"Invalid quantity calculated for {signal.symbol}")
                return False

            # Execute trade
            order_result = self.position_service.execute_trade(signal, quantity)

            if order_result:
                # Create position record
                position = Position(
                    symbol=signal.symbol,
                    entry_price=signal.entry_price,
                    quantity=quantity,
                    stop_loss=signal.stop_loss,
                    target_price=signal.target_price,
                    entry_time=datetime.now(),
                    sector=signal.sector,
                    order_id=order_result.get('id')
                )

                self.positions[signal.symbol] = position

                logger.info(f"New position: {signal.symbol} - Qty: {quantity}, "
                            f"Entry: Rs.{signal.entry_price:.2f}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error executing signal for {signal.symbol}: {e}")
            return False

    def _log_status(self, unrealized_pnl: float) -> None:
        """Log current strategy status"""
        logger.info(f"Strategy Status - Active Positions: {len(self.positions)}, "
                    f"Daily PnL: Rs.{self.daily_pnl:.2f}, "
                    f"Total PnL: Rs.{self.total_pnl:.2f}, "
                    f"Unrealized: Rs.{unrealized_pnl:.2f}")

    def get_performance_summary(self) -> Dict:
        """Get comprehensive performance summary"""
        return {
            'total_pnl': self.total_pnl,
            'daily_pnl': self.daily_pnl,
            'active_positions': len(self.positions),
            'positions_detail': [
                {
                    'symbol': pos.symbol,
                    'sector': pos.sector.value,
                    'entry_price': pos.entry_price,
                    'quantity': pos.quantity,
                    'entry_time': pos.entry_time.strftime('%H:%M:%S'),
                    'order_id': pos.order_id
                }
                for pos in self.positions.values()
            ]
        }

    async def run(self) -> None:
        """Main strategy execution loop"""
        logger.info("Starting Gap-Up Short Selling Strategy")

        if not await self.initialize():
            logger.error("Strategy initialization failed")
            return

        try:
            while True:
                # Check trading hours
                if not self.timing_service.is_trading_time():
                    logger.info("Outside trading hours, sleeping...")
                    await asyncio.sleep(300)  # 5 minutes
                    continue

                # Run strategy cycle
                await self.run_strategy_cycle()

                # Sleep until next cycle
                await asyncio.sleep(self.trading_config.monitoring_interval)

        except KeyboardInterrupt:
            logger.info("Strategy stopped by user")
        except Exception as e:
            logger.error(f"Fatal error in strategy: {e}")
        finally:
            # Print final performance
            performance = self.get_performance_summary()
            logger.info(f"Final Performance: Total PnL: Rs.{performance['total_pnl']:.2f}")