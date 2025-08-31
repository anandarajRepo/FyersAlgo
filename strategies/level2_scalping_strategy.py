# strategies/level2_scalping_strategy.py

import asyncio
import logging
import pytz
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import numpy as np

from config.settings import Sector, StrategyConfig, TradingConfig
from models.trading_models import TradingSignal, Position, MarketData
from services.fyers_service import FyersService
from services.position_service import PositionManagementService
from services.market_timing_service import MarketTimingService

logger = logging.getLogger(__name__)
IST = pytz.timezone('Asia/Kolkata')


class ScalpingSignalType(Enum):
    SUPPORT_BOUNCE = "SUPPORT_BOUNCE"
    RESISTANCE_BOUNCE = "RESISTANCE_BOUNCE"
    BID_ASK_IMBALANCE = "BID_ASK_IMBALANCE"


@dataclass
class ScalpingConfig:
    """Configuration for Level II Scalping Strategy"""
    # Order book analysis
    min_bid_ask_imbalance_ratio: float = 2.0  # Minimum bid/ask volume ratio for imbalance
    min_order_book_depth: int = 5  # Minimum depth levels to analyze
    min_volume_at_level: int = 1000  # Minimum volume at support/resistance level

    # Position sizing and risk
    max_positions: int = 1  # Max simultaneous positions (scalping is fast)
    position_size_percentage: float = 0.2  # 0.2% of portfolio per trade
    stop_loss_ticks: int = 2  # Stop loss in ticks (very tight)
    target_ticks: int = 4  # Target in ticks (2:1 RR)

    # Timing constraints
    min_hold_seconds: int = 5  # Minimum hold time
    max_hold_seconds: int = 30  # Maximum hold time
    cooldown_seconds: int = 60  # Cooldown between trades on same symbol

    # Market conditions
    min_spread_ticks: int = 1  # Minimum spread for entry
    max_spread_ticks: int = 3  # Maximum spread for entry
    min_market_volatility: float = 0.5  # Minimum volatility for scalping

    # Quality filters
    min_confidence: float = 0.75  # Higher confidence threshold for scalping


@dataclass
class OrderBookLevel:
    """Represents a level in the order book"""
    price: float
    quantity: int
    orders: int
    side: str  # 'BID' or 'ASK'


@dataclass
class OrderBookSnapshot:
    """Complete order book snapshot"""
    symbol: str
    timestamp: datetime
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    last_traded_price: float
    last_traded_quantity: int


class Level2DataService:
    """Service for handling Level II market data"""

    def __init__(self, fyers_service: FyersService):
        self.fyers_service = fyers_service
        self.order_book_cache = {}

    async def get_order_book(self, symbol: str) -> Optional[OrderBookSnapshot]:
        """Get Level II order book data"""
        try:
            # Using Fyers market depth API
            fyers_symbol = self.fyers_service.symbol_mapping.get(symbol, symbol)

            depth_data = self.fyers_service._make_request('GET', '/data/depth', {
                'symbol': fyers_symbol,
                'ohlcv_flag': '1'
            })

            if not depth_data or fyers_symbol not in depth_data:
                return None

            market_depth = depth_data[fyers_symbol]

            # Parse bid data
            bids = []
            if 'bids' in market_depth:
                for i, bid in enumerate(market_depth['bids']):
                    bids.append(OrderBookLevel(
                        price=bid['price'],
                        quantity=bid['volume'],
                        orders=bid.get('orders', 1),
                        side='BID'
                    ))

            # Parse ask data
            asks = []
            if 'asks' in market_depth:
                for i, ask in enumerate(market_depth['asks']):
                    asks.append(OrderBookLevel(
                        price=ask['price'],
                        quantity=ask['volume'],
                        orders=ask.get('orders', 1),
                        side='ASK'
                    ))

            return OrderBookSnapshot(
                symbol=symbol,
                timestamp=datetime.now(IST),
                bids=sorted(bids, key=lambda x: x.price, reverse=True),  # Highest bid first
                asks=sorted(asks, key=lambda x: x.price),  # Lowest ask first
                last_traded_price=market_depth.get('ltp', 0),
                last_traded_quantity=market_depth.get('ltq', 0)
            )

        except Exception as e:
            logger.error(f"Error getting order book for {symbol}: {e}")
            return None

    def calculate_bid_ask_imbalance(self, order_book: OrderBookSnapshot) -> float:
        """Calculate bid/ask volume imbalance ratio"""
        if not order_book.bids or not order_book.asks:
            return 1.0

        # Sum volumes at best levels
        total_bid_volume = sum(level.quantity for level in order_book.bids[:3])
        total_ask_volume = sum(level.quantity for level in order_book.asks[:3])

        if total_ask_volume == 0:
            return float('inf')

        return total_bid_volume / total_ask_volume

    def identify_support_resistance_levels(self, order_book: OrderBookSnapshot,
                                           config: ScalpingConfig) -> Dict[str, List[float]]:
        """Identify key support and resistance levels from order book"""
        support_levels = []
        resistance_levels = []

        # Look for significant bid accumulation (support)
        for level in order_book.bids:
            if level.quantity >= config.min_volume_at_level:
                support_levels.append(level.price)

        # Look for significant ask accumulation (resistance)
        for level in order_book.asks:
            if level.quantity >= config.min_volume_at_level:
                resistance_levels.append(level.price)

        return {
            'support': support_levels[:3],  # Top 3 support levels
            'resistance': resistance_levels[:3]  # Top 3 resistance levels
        }


class Level2ScalpingSignalService:
    """Service for generating Level II scalping signals"""

    def __init__(self, fyers_service: FyersService, level2_service: Level2DataService):
        self.fyers_service = fyers_service
        self.level2_service = level2_service

        # Focus on most liquid stocks for scalping
        self.scalping_universe = {
            'RELIANCE.NS': Sector.AUTO,
            'TCS.NS': Sector.IT,
            'HDFCBANK.NS': Sector.BANKING,
            'INFY.NS': Sector.IT,
            'ICICIBANK.NS': Sector.BANKING,
            'ITC.NS': Sector.FMCG,
            'SBIN.NS': Sector.BANKING,
            'HINDUNILVR.NS': Sector.FMCG,
            'LT.NS': Sector.METALS,
            'AXISBANK.NS': Sector.BANKING,
        }

        # Track recent signals to avoid over-trading
        self.recent_signals = {}

    async def generate_scalping_signals(self, config: ScalpingConfig) -> List[TradingSignal]:
        """Generate Level II scalping signals"""
        signals = []

        try:
            # Get market data for all symbols
            symbols = list(self.scalping_universe.keys())
            market_data_dict = await self.fyers_service.get_quotes(symbols)
            logger.info(f"market_data_dict: {market_data_dict}")

            for symbol, sector in self.scalping_universe.items():
                try:
                    # Check cooldown period
                    if self._is_in_cooldown(symbol, config):
                        continue

                    if symbol not in market_data_dict:
                        logger.info(f"Symbol not found in market_data_dict: {symbol}")
                        continue

                    market_data = market_data_dict[symbol]

                    # Get Level II data
                    order_book = await self.level2_service.get_order_book(symbol)
                    if not order_book:
                        logger.info(f"Order book not found for symbol: {order_book}")
                        continue

                    # Check spread constraints
                    if not self._check_spread_constraints(order_book, config):
                        logger.info(f"Check spread constraints for symbol: {symbol}, constraints: {self._check_spread_constraints(order_book, config)}")
                        continue

                    # Analyze for scalping opportunities
                    signal = await self._analyze_scalping_opportunity(
                        symbol, sector, market_data, order_book, config
                    )

                    if signal and signal.confidence >= config.min_confidence:
                        signals.append(signal)
                        self._record_signal_time(symbol)

                        logger.info(f"Level II scalping signal: {symbol} - "
                                    f"Type: {signal.signal_type}, "
                                    f"Confidence: {signal.confidence:.2f}")

                except Exception as e:
                    logger.error(f"Error analyzing {symbol} for scalping: {e}")

            # Sort by confidence
            signals.sort(key=lambda x: x.confidence, reverse=True)
            return signals

        except Exception as e:
            logger.error(f"Error generating scalping signals: {e}")
            return []

    def _is_in_cooldown(self, symbol: str, config: ScalpingConfig) -> bool:
        """Check if symbol is in cooldown period"""
        if symbol not in self.recent_signals:
            return False

        last_signal_time = self.recent_signals[symbol]
        cooldown_end = last_signal_time + timedelta(seconds=config.cooldown_seconds)

        return datetime.now(IST) < cooldown_end

    def _record_signal_time(self, symbol: str) -> None:
        """Record the time of signal generation"""
        self.recent_signals[symbol] = datetime.now(IST)

    def _check_spread_constraints(self, order_book: OrderBookSnapshot,
                                  config: ScalpingConfig) -> bool:
        """Check if spread is within acceptable range for scalping"""
        if not order_book.bids or not order_book.asks:
            return False

        best_bid = order_book.bids[0].price
        best_ask = order_book.asks[0].price

        spread_ticks = int((best_ask - best_bid) * 100)  # Assuming 0.01 tick size

        return config.min_spread_ticks <= spread_ticks <= config.max_spread_ticks

    async def _analyze_scalping_opportunity(self, symbol: str, sector: Sector,
                                            market_data: MarketData,
                                            order_book: OrderBookSnapshot,
                                            config: ScalpingConfig) -> Optional[TradingSignal]:
        """Analyze Level II data for scalping opportunities"""

        try:
            current_price = market_data.current_price

            # Calculate bid/ask imbalance
            imbalance_ratio = self.level2_service.calculate_bid_ask_imbalance(order_book)

            # Identify support/resistance levels
            levels = self.level2_service.identify_support_resistance_levels(order_book, config)

            # Check for imbalance-based signals
            if imbalance_ratio >= config.min_bid_ask_imbalance_ratio:
                # Strong bid imbalance - potential long signal
                signal_type = ScalpingSignalType.BID_ASK_IMBALANCE
                side = 'LONG'
                entry_price = current_price

            elif imbalance_ratio <= (1.0 / config.min_bid_ask_imbalance_ratio):
                # Strong ask imbalance - potential short signal
                signal_type = ScalpingSignalType.BID_ASK_IMBALANCE
                side = 'SHORT'
                entry_price = current_price

            else:
                # Check for support/resistance bounce opportunities
                bounce_signal = self._check_bounce_opportunities(
                    current_price, levels, order_book, config
                )

                if not bounce_signal:
                    return None

                signal_type, side, entry_price = bounce_signal

            # Calculate stop loss and target
            tick_size = 0.05  # Typical tick size, should be symbol-specific

            if side == 'LONG':
                stop_loss = entry_price - (config.stop_loss_ticks * tick_size)
                target_price = entry_price + (config.target_ticks * tick_size)
            else:
                stop_loss = entry_price + (config.stop_loss_ticks * tick_size)
                target_price = entry_price - (config.target_ticks * tick_size)

            # Calculate confidence
            confidence = self._calculate_scalping_confidence(
                order_book, imbalance_ratio, levels, current_price, config
            )

            return TradingSignal(
                symbol=symbol,
                sector=sector,
                signal_type=f"{side}_{signal_type.value}",
                entry_price=entry_price,
                stop_loss=stop_loss,
                target_price=target_price,
                confidence=confidence,
                gap_percentage=0.0,  # Not applicable for scalping
                selling_pressure_score=0.0,  # Not applicable
                volume_ratio=imbalance_ratio,
                timestamp=datetime.now(IST)
            )

        except Exception as e:
            logger.error(f"Error analyzing scalping opportunity for {symbol}: {e}")
            return None

    def _check_bounce_opportunities(self, current_price: float, levels: Dict,
                                    order_book: OrderBookSnapshot,
                                    config: ScalpingConfig) -> Optional[Tuple[ScalpingSignalType, str, float]]:
        """Check for price bounce opportunities at support/resistance"""

        # Check for support bounce (long opportunity)
        for support_level in levels['support']:
            if abs(current_price - support_level) / current_price <= 0.001:  # Within 0.1%
                return (ScalpingSignalType.SUPPORT_BOUNCE, 'LONG', current_price)

        # Check for resistance bounce (short opportunity)
        for resistance_level in levels['resistance']:
            if abs(current_price - resistance_level) / current_price <= 0.001:  # Within 0.1%
                return (ScalpingSignalType.RESISTANCE_BOUNCE, 'SHORT', current_price)

        return None

    def _calculate_scalping_confidence(self, order_book: OrderBookSnapshot,
                                       imbalance_ratio: float, levels: Dict,
                                       current_price: float, config: ScalpingConfig) -> float:
        """Calculate confidence score for scalping signal"""

        confidence = 0.0

        # Order book depth score (deeper book = higher confidence)
        depth_score = min(len(order_book.bids) + len(order_book.asks), 10) / 10 * 0.25
        confidence += depth_score

        # Imbalance strength score
        if imbalance_ratio >= config.min_bid_ask_imbalance_ratio:
            imbalance_score = min(imbalance_ratio / 5.0, 1.0) * 0.35
        elif imbalance_ratio <= (1.0 / config.min_bid_ask_imbalance_ratio):
            imbalance_score = min((1.0 / imbalance_ratio) / 5.0, 1.0) * 0.35
        else:
            imbalance_score = 0.1

        confidence += imbalance_score

        # Volume at best levels score
        best_bid_volume = order_book.bids[0].quantity if order_book.bids else 0
        best_ask_volume = order_book.asks[0].quantity if order_book.asks else 0
        total_volume = best_bid_volume + best_ask_volume

        volume_score = min(total_volume / (config.min_volume_at_level * 2), 1.0) * 0.25
        confidence += volume_score

        # Support/resistance proximity score
        proximity_score = 0.0
        for level in levels['support'] + levels['resistance']:
            distance_pct = abs(current_price - level) / current_price
            if distance_pct <= 0.002:  # Within 0.2%
                proximity_score = 0.15
                break

        confidence += proximity_score

        return min(confidence, 1.0)


class Level2ScalpingStrategy:
    """Level II Market Data Scalping Strategy"""

    def __init__(self, fyers_service: FyersService, strategy_config: StrategyConfig,
                 trading_config: TradingConfig, scalping_config: ScalpingConfig):

        # Services
        self.fyers_service = fyers_service
        self.level2_service = Level2DataService(fyers_service)
        self.signal_service = Level2ScalpingSignalService(fyers_service, self.level2_service)
        self.position_service = PositionManagementService(fyers_service, fyers_service)
        self.timing_service = MarketTimingService(trading_config)

        # Configuration
        self.strategy_config = strategy_config
        self.trading_config = trading_config
        self.scalping_config = scalping_config

        # State
        self.positions: Dict[str, Position] = {}
        self.position_entry_times: Dict[str, datetime] = {}
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        self.trades_today = 0

    def is_scalping_time(self) -> bool:
        """Check if it's appropriate time for scalping"""
        now = datetime.now(IST)

        if not self.timing_service.is_trading_time():
            return False

        # Avoid first 15 minutes (volatile opening)
        market_start = now.replace(hour=9, minute=30, second=0, microsecond=0)

        # Avoid last 30 minutes (closing volatility)
        market_end = now.replace(hour=15, minute=0, second=0, microsecond=0)

        return market_start <= now <= market_end

    async def run_scalping_cycle(self) -> None:
        """Run one scalping strategy cycle"""
        try:
            # Check position timing and exit if needed
            await self._check_position_timing()

            # Monitor existing positions
            pnl_summary = self.position_service.monitor_positions(self.positions)
            self.daily_pnl += pnl_summary.realized_pnl
            self.total_pnl += pnl_summary.realized_pnl

            # Update trades count
            self.trades_today += len(pnl_summary.closed_positions)

            # Log closed positions
            for closed_pos in pnl_summary.closed_positions:
                logger.info(f"Scalping position closed: {closed_pos['symbol']}, "f"PnL: Rs.{closed_pos['pnl']:.2f}")

            # Generate new signals if in scalping time and have available slots
            if (self.is_scalping_time() and
                    len(self.positions) < self.scalping_config.max_positions):
                await self._generate_and_execute_scalping_signals()

            # Log current status
            self._log_scalping_status(pnl_summary.unrealized_pnl)

        except Exception as e:
            logger.error(f"Error in scalping strategy cycle: {e}")

    async def _check_position_timing(self) -> None:
        """Check if positions should be closed based on time limits"""
        now = datetime.now(IST)
        positions_to_close = []

        for symbol, position in self.positions.items():
            if symbol not in self.position_entry_times:
                continue

            entry_time = self.position_entry_times[symbol]
            hold_duration = (now - entry_time).total_seconds()

            # Close if held for maximum time
            if hold_duration >= self.scalping_config.max_hold_seconds:
                positions_to_close.append(symbol)
                logger.info(f"Closing {symbol} due to max hold time: {hold_duration:.1f}s")

        # Close positions that exceeded time limit
        for symbol in positions_to_close:
            await self._close_position(symbol, "TIME_LIMIT")

    async def _close_position(self, symbol: str, reason: str) -> None:
        """Close a scalping position"""
        try:
            if symbol not in self.positions:
                return

            position = self.positions[symbol]

            # Determine order side based on position
            side = '-1' if position.quantity > 0 else '1'  # Opposite side to close

            # Place market order to close
            close_order = self.fyers_service.place_order(
                symbol=symbol,
                side=side,
                quantity=abs(position.quantity),
                order_type='2',  # Market order for quick exit
                price=0
            )

            if close_order:
                logger.info(f"Closed scalping position {symbol}, reason: {reason}")

                # Remove from tracking
                if symbol in self.positions:
                    del self.positions[symbol]
                if symbol in self.position_entry_times:
                    del self.position_entry_times[symbol]

        except Exception as e:
            logger.error(f"Error closing position {symbol}: {e}")

    async def _generate_and_execute_scalping_signals(self) -> None:
        """Generate and execute scalping signals"""
        try:
            # Generate scalping signals
            signals = await self.signal_service.generate_scalping_signals(self.scalping_config)

            # Execute first valid signal (scalping is typically single position)
            for signal in signals:
                if signal.confidence >= self.scalping_config.min_confidence:
                    success = await self._execute_scalping_signal(signal)
                    if success:
                        break  # Only one position at a time for scalping

        except Exception as e:
            logger.error(f"Error in scalping signal generation/execution: {e}")

    async def _execute_scalping_signal(self, signal: TradingSignal) -> bool:
        """Execute a scalping signal"""
        try:
            # Calculate position size for scalping
            portfolio_value = self.strategy_config.portfolio_value
            position_value = portfolio_value * (self.scalping_config.position_size_percentage / 100)
            quantity = int(position_value / signal.entry_price)

            if quantity <= 0:
                logger.warning(f"Invalid quantity for scalping {signal.symbol}")
                return False

            # Determine order side
            side = '1' if 'LONG' in signal.signal_type else '-1'

            # Place market order for immediate execution
            order_result = self.fyers_service.place_order(
                symbol=signal.symbol,
                side=side,
                quantity=quantity,
                order_type='2',  # Market order
                price=0
            )

            if order_result:
                # Create position record
                position = Position(
                    symbol=signal.symbol,
                    entry_price=signal.entry_price,
                    quantity=quantity if side == '1' else -quantity,
                    stop_loss=signal.stop_loss,
                    target_price=signal.target_price,
                    entry_time=datetime.now(IST),
                    sector=signal.sector,
                    order_id=order_result.get('id')
                )

                self.positions[signal.symbol] = position
                self.position_entry_times[signal.symbol] = datetime.now(IST)

                logger.info(f"New scalping position: {signal.symbol} - "
                            f"Type: {signal.signal_type}, Qty: {quantity}, "
                            f"Entry: Rs.{signal.entry_price:.2f}")

                # Place stop loss order
                await self._place_scalping_stop_loss(position)

                return True

            return False

        except Exception as e:
            logger.error(f"Error executing scalping signal for {signal.symbol}: {e}")
            return False

    async def _place_scalping_stop_loss(self, position: Position) -> None:
        """Place tight stop loss for scalping position"""
        try:
            # Determine stop loss order side
            sl_side = '-1' if position.quantity > 0 else '1'

            sl_order = self.fyers_service.place_order(
                symbol=position.symbol,
                side=sl_side,
                quantity=abs(position.quantity),
                order_type='4',  # Stop loss market order
                price=position.stop_loss
            )

            if sl_order:
                position.sl_order_id = sl_order.get('id')
                logger.info(f"Stop loss placed for scalping position {position.symbol} "
                            f"at Rs.{position.stop_loss:.2f}")

        except Exception as e:
            logger.error(f"Error placing stop loss for {position.symbol}: {e}")

    def _log_scalping_status(self, unrealized_pnl: float) -> None:
        """Log current scalping strategy status"""
        avg_hold_time = 0
        if self.position_entry_times:
            now = datetime.now(IST)
            total_hold_time = sum(
                (now - entry_time).total_seconds()
                for entry_time in self.position_entry_times.values()
            )
            avg_hold_time = total_hold_time / len(self.position_entry_times)

        logger.info(f"Scalping Strategy - Active: {len(self.positions)}, "
                    f"Today's Trades: {self.trades_today}, "
                    f"Daily PnL: Rs.{self.daily_pnl:.2f}, "
                    f"Avg Hold: {avg_hold_time:.1f}s, "
                    f"Unrealized: Rs.{unrealized_pnl:.2f}")

    def get_scalping_performance(self) -> Dict:
        """Get scalping strategy performance"""
        now = datetime.now(IST)
        active_positions_detail = []

        for symbol, position in self.positions.items():
            entry_time = self.position_entry_times.get(symbol, now)
            hold_duration = (now - entry_time).total_seconds()

            active_positions_detail.append({
                'symbol': symbol,
                'sector': position.sector.value,
                'entry_price': position.entry_price,
                'quantity': position.quantity,
                'hold_time_seconds': hold_duration,
                'signal_type': 'SCALPING',
                'order_id': position.order_id
            })

        return {
            'strategy_name': 'Level II Scalping',
            'total_pnl': self.total_pnl,
            'daily_pnl': self.daily_pnl,
            'active_positions': len(self.positions),
            'trades_today': self.trades_today,
            'positions_detail': active_positions_detail
        }