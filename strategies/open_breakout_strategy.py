import asyncio
import logging
from typing import Dict, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from config.settings import Sector, StrategyConfig, TradingConfig
from models.trading_models import TradingSignal, Position, MarketData
from services.fyers_service import FyersService
from services.analysis_service import TechnicalAnalysisService
from services.position_service import PositionManagementService
from services.market_timing_service import MarketTimingService

logger = logging.getLogger(__name__)


@dataclass
class BreakoutConfig:
    min_breakout_percentage: float = 2.0  # Minimum breakout above opening range
    min_volume_multiplier: float = 1.5  # Volume should be 1.5x average
    opening_range_minutes: int = 15  # First 15 minutes for range calculation
    min_price_range: float = 1.0  # Minimum price range in rupees
    max_price_range: float = 50.0  # Maximum price range in rupees
    risk_reward_ratio: float = 2.0  # Target should be 2x stop loss
    max_positions_per_strategy: int = 2  # Max positions for breakout strategy


class OpenBreakoutSignalService:
    """Service for generating open breakout trading signals"""

    def __init__(self, data_provider: FyersService, analysis_service: TechnicalAnalysisService):
        self.data_provider = data_provider
        self.analysis_service = analysis_service

        # Focus on liquid stocks with good volatility
        self.breakout_stocks = {
            # High Beta Stocks - Good for breakouts
            'RELIANCE.NS': Sector.AUTO,
            'TCS.NS': Sector.IT,
            'HDFCBANK.NS': Sector.BANKING,
            'INFY.NS': Sector.IT,
            'ICICIBANK.NS': Sector.BANKING,
            'HINDUNILVR.NS': Sector.FMCG,
            'ITC.NS': Sector.FMCG,
            'SBIN.NS': Sector.BANKING,
            'BAJFINANCE.NS': Sector.BANKING,
            'MARUTI.NS': Sector.AUTO,
            'TATAMOTORS.NS': Sector.AUTO,
            'WIPRO.NS': Sector.IT,
            'AXISBANK.NS': Sector.BANKING,
            'ULTRACEMCO.NS': Sector.METALS,
            'ASIANPAINT.NS': Sector.FMCG,
            'NESTLEIND.NS': Sector.FMCG,
            'KOTAKBANK.NS': Sector.BANKING,
            'LT.NS': Sector.METALS,
            'TECHM.NS': Sector.IT,
            'HCLTECH.NS': Sector.IT,
        }

        # Sector preferences for breakouts
        self.sector_weights = {
            Sector.IT: 1.0,  # High momentum sector
            Sector.BANKING: 0.9,  # High volume, good for breakouts
            Sector.AUTO: 0.8,  # Cyclical, good breakout potential
            Sector.FMCG: 0.7,  # Stable but less volatile
            Sector.METALS: 0.8,  # High volatility
            Sector.PHARMA: 0.6,
            Sector.REALTY: 0.7
        }

    async def calculate_opening_range(self, symbol: str, config: BreakoutConfig) -> Dict:
        """Calculate opening range for breakout detection"""
        try:
            # Get intraday data for opening range calculation
            current_data = await self.data_provider.get_quotes([symbol])

            if symbol not in current_data:
                return None

            market_data = current_data[symbol]

            # Simulate opening range calculation
            # In real implementation, you'd fetch 1-minute data for first 15 minutes
            opening_range = {
                'high': market_data.open_price * 1.01,  # Simulated range high
                'low': market_data.open_price * 0.99,  # Simulated range low
                'range_size': market_data.open_price * 0.02,  # 2% range
                'volume': market_data.volume,
                'open_price': market_data.open_price
            }

            return opening_range

        except Exception as e:
            logger.error(f"Error calculating opening range for {symbol}: {e}")
            return None

    def calculate_breakout_strength(self, market_data: MarketData, opening_range: Dict) -> float:
        """Calculate strength of breakout"""
        try:
            range_size = opening_range['range_size']
            breakout_distance = market_data.current_price - opening_range['high']

            if breakout_distance <= 0:
                return 0.0

            # Breakout strength as percentage of range
            strength = (breakout_distance / range_size) * 100

            # Volume confirmation
            volume_strength = min(market_data.volume / opening_range['volume'], 3.0) if opening_range['volume'] > 0 else 1.0

            # Combined strength
            total_strength = strength * volume_strength * 0.5

            return min(total_strength, 100.0)

        except Exception as e:
            logger.error(f"Error calculating breakout strength: {e}")
            return 0.0

    async def generate_breakout_signals(self, strategy_config: StrategyConfig,
                                        breakout_config: BreakoutConfig) -> List[TradingSignal]:
        """Generate breakout trading signals"""
        signals = []

        try:
            # Get market data for all breakout stocks
            symbols = list(self.breakout_stocks.keys())
            market_data_dict = await self.data_provider.get_quotes(symbols)

            for symbol, sector in self.breakout_stocks.items():
                try:
                    if symbol not in market_data_dict:
                        continue

                    market_data = market_data_dict[symbol]

                    # Calculate opening range
                    opening_range = await self.calculate_opening_range(symbol, breakout_config)
                    if not opening_range:
                        continue

                    # Check if price is breaking above opening range high
                    if market_data.current_price <= opening_range['high']:
                        continue

                    # Calculate breakout percentage
                    breakout_percentage = ((market_data.current_price - opening_range['high']) /
                                           opening_range['high']) * 100

                    if breakout_percentage < breakout_config.min_breakout_percentage:
                        continue

                    # Check range size constraints
                    range_size = opening_range['range_size']
                    if range_size < breakout_config.min_price_range or range_size > breakout_config.max_price_range:
                        continue

                    # Volume confirmation
                    avg_volume = await self._get_average_volume(symbol)
                    volume_ratio = market_data.volume / avg_volume if avg_volume > 0 else 1.0

                    if volume_ratio < breakout_config.min_volume_multiplier:
                        continue

                    # Calculate breakout strength
                    breakout_strength = self.calculate_breakout_strength(market_data, opening_range)

                    # Technical analysis
                    momentum_score = await self._calculate_momentum_score(symbol)

                    # Calculate confidence
                    sector_preference = self.sector_weights.get(sector, 0.5)
                    confidence = (
                            (breakout_strength / 100) * 0.3 +
                            min(volume_ratio / 3, 1) * 0.25 +
                            (breakout_percentage / 10) * 0.2 +
                            (momentum_score / 100) * 0.15 +
                            sector_preference * 0.1
                    )

                    if confidence < strategy_config.min_confidence:
                        continue

                    # Calculate stop loss and target
                    stop_loss = opening_range['low']  # Stop below opening range low
                    risk = market_data.current_price - stop_loss
                    target_price = market_data.current_price + (risk * breakout_config.risk_reward_ratio)

                    signal = TradingSignal(
                        symbol=symbol,
                        sector=sector,
                        signal_type='LONG_BREAKOUT',
                        entry_price=market_data.current_price,
                        stop_loss=stop_loss,
                        target_price=target_price,
                        confidence=confidence,
                        gap_percentage=breakout_percentage,
                        selling_pressure_score=0.0,  # Not applicable for breakouts
                        volume_ratio=volume_ratio,
                        timestamp=datetime.now()
                    )

                    signals.append(signal)
                    logger.info(f"Breakout signal: {symbol} - Breakout: {breakout_percentage:.2f}%, "
                                f"Volume: {volume_ratio:.1f}x, Confidence: {confidence:.2f}")

                except Exception as e:
                    logger.error(f"Error processing breakout for {symbol}: {e}")

            # Sort by confidence
            signals.sort(key=lambda x: x.confidence, reverse=True)
            return signals

        except Exception as e:
            logger.error(f"Error generating breakout signals: {e}")
            return []

    async def _get_average_volume(self, symbol: str) -> float:
        """Get average volume for the symbol"""
        try:
            hist = self.data_provider.get_historical_data(symbol, "20d")
            if len(hist) > 0:
                return hist['Volume'].mean()
            return 0.0
        except:
            return 0.0

    async def _calculate_momentum_score(self, symbol: str) -> float:
        """Calculate momentum score for breakout confirmation"""
        try:
            hist = self.data_provider.get_historical_data(symbol, "10d")
            if len(hist) < 5:
                return 50.0

            # Simple momentum: recent price vs 5-day average
            recent_close = hist['Close'].iloc[-1]
            sma_5 = hist['Close'].tail(5).mean()

            momentum = ((recent_close - sma_5) / sma_5) * 100

            # Normalize to 0-100 scale
            normalized_momentum = min(max(momentum * 10 + 50, 0), 100)

            return normalized_momentum

        except Exception as e:
            logger.error(f"Error calculating momentum for {symbol}: {e}")
            return 50.0


class OpenBreakoutStrategy:
    """Open Breakout Strategy Implementation"""

    def __init__(self, fyers_service: FyersService, strategy_config: StrategyConfig,
                 trading_config: TradingConfig, breakout_config: BreakoutConfig):

        # Services
        self.fyers_service = fyers_service
        self.analysis_service = TechnicalAnalysisService(fyers_service)
        self.signal_service = OpenBreakoutSignalService(fyers_service, self.analysis_service)
        self.position_service = PositionManagementService(fyers_service, fyers_service)
        self.timing_service = MarketTimingService(trading_config)

        # Configuration
        self.strategy_config = strategy_config
        self.trading_config = trading_config
        self.breakout_config = breakout_config

        # State
        self.positions: Dict[str, Position] = {}
        self.daily_pnl = 0.0
        self.total_pnl = 0.0

    def is_breakout_time(self) -> bool:
        """Check if it's time to look for breakouts (after opening range formation)"""
        now = datetime.now()

        if not self.timing_service.is_trading_time():
            return False

        # Start looking for breakouts after opening range period
        breakout_start = now.replace(
            hour=9,
            minute=15 + self.breakout_config.opening_range_minutes,
            second=0,
            microsecond=0
        )

        # Stop generating new breakout signals after 11:30 AM
        breakout_end = now.replace(hour=11, minute=30, second=0, microsecond=0)

        return breakout_start <= now <= breakout_end

    async def run_breakout_cycle(self) -> None:
        """Run one breakout strategy cycle"""
        try:
            # Monitor existing positions
            pnl_summary = self.position_service.monitor_positions(self.positions)
            self.daily_pnl += pnl_summary.realized_pnl
            self.total_pnl += pnl_summary.realized_pnl

            # Log closed positions
            for closed_pos in pnl_summary.closed_positions:
                logger.info(f"Breakout position closed: {closed_pos['symbol']}, "
                            f"PnL: Rs.{closed_pos['pnl']:.2f}")

            # Generate new breakout signals if in breakout time window
            if self.is_breakout_time():
                await self._generate_and_execute_breakout_signals()

            # Log current status
            self._log_breakout_status(pnl_summary.unrealized_pnl)

        except Exception as e:
            logger.error(f"Error in breakout strategy cycle: {e}")

    async def _generate_and_execute_breakout_signals(self) -> None:
        """Generate and execute breakout signals"""
        try:
            # Check available position slots
            available_slots = (self.breakout_config.max_positions_per_strategy -
                               len(self.positions))

            if available_slots <= 0:
                return

            # Generate breakout signals
            signals = await self.signal_service.generate_breakout_signals(
                self.strategy_config, self.breakout_config
            )

            # Execute top signals
            executed_count = 0
            for signal in signals[:available_slots]:
                if signal.confidence >= self.strategy_config.min_confidence:
                    success = await self._execute_breakout_signal(signal)
                    if success:
                        executed_count += 1
                        await asyncio.sleep(self.trading_config.execution_delay)

            if executed_count > 0:
                logger.info(f"Executed {executed_count} new breakout trades")

        except Exception as e:
            logger.error(f"Error in breakout signal generation/execution: {e}")

    async def _execute_breakout_signal(self, signal: TradingSignal) -> bool:
        """Execute a breakout signal"""
        try:
            # Calculate position size
            quantity = self.position_service.calculate_position_size(signal, self.strategy_config)

            if quantity <= 0:
                logger.warning(f"Invalid quantity calculated for breakout {signal.symbol}")
                return False

            # For breakouts, we use regular orders instead of bracket orders for more control
            order_result = self.fyers_service.place_order(
                symbol=signal.symbol,
                side='1',  # Buy for long breakout
                quantity=quantity,
                order_type='2',  # Market order
                price=0
            )

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

                logger.info(f"New breakout position: {signal.symbol} - Qty: {quantity}, "
                            f"Entry: Rs.{signal.entry_price:.2f}")

                # Place stop loss order
                await self._place_stop_loss_order(position)

                return True

            return False

        except Exception as e:
            logger.error(f"Error executing breakout signal for {signal.symbol}: {e}")
            return False

    async def _place_stop_loss_order(self, position: Position) -> None:
        """Place stop loss order for breakout position"""
        try:
            sl_order = self.fyers_service.place_order(
                symbol=position.symbol,
                side='-1',  # Sell to close long position
                quantity=position.quantity,
                order_type='4',  # Stop loss market order
                price=position.stop_loss
            )

            if sl_order:
                position.sl_order_id = sl_order.get('id')
                logger.info(f"Stop loss placed for {position.symbol} at Rs.{position.stop_loss:.2f}")

        except Exception as e:
            logger.error(f"Error placing stop loss for {position.symbol}: {e}")

    def _log_breakout_status(self, unrealized_pnl: float) -> None:
        """Log current breakout strategy status"""
        logger.info(f"Breakout Strategy - Active Positions: {len(self.positions)}, "
                    f"Daily PnL: Rs.{self.daily_pnl:.2f}, "
                    f"Total PnL: Rs.{self.total_pnl:.2f}, "
                    f"Unrealized: Rs.{unrealized_pnl:.2f}")

    def get_breakout_performance(self) -> Dict:
        """Get breakout strategy performance"""
        return {
            'strategy_name': 'Open Breakout',
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
                    'order_id': pos.order_id,
                    'signal_type': 'BREAKOUT'
                }
                for pos in self.positions.values()
            ]
        }