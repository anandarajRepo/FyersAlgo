# services/enhanced_fyers_service.py

import requests
import logging
import pandas as pd
import yfinance as yf
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from config.settings import FyersConfig
from services.fyers_service import FyersService
from models.trading_models import MarketData

logger = logging.getLogger(__name__)


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
    spread: float
    mid_price: float


@dataclass
class TickData:
    """Individual tick data"""
    symbol: str
    timestamp: datetime
    price: float
    quantity: int
    side: str  # 'BUY' or 'SELL'


class EnhancedFyersService(FyersService):
    """Enhanced Fyers service with Level II data and order flow analysis"""

    def __init__(self, config: FyersConfig):
        super().__init__(config)

        # Level II data caching
        self.order_book_cache = {}
        self.tick_data_cache = {}
        self.last_update_times = {}

        # Order flow tracking
        self.order_flow_history = {}
        self.imbalance_history = {}

    async def get_market_depth(self, symbol: str) -> Optional[OrderBookSnapshot]:
        """Get Level II market depth data"""
        try:
            fyers_symbol = self.symbol_mapping.get(symbol, symbol)

            # Check cache freshness (Level II data should be very fresh)
            cache_key = f"depth_{symbol}"
            now = datetime.now()

            if (cache_key in self.last_update_times and
                    (now - self.last_update_times[cache_key]).total_seconds() < 1.0):
                return self.order_book_cache.get(cache_key)

            # Fetch market depth from Fyers API
            depth_data = self._make_request('GET', '/data/depth', {
                'symbol': fyers_symbol,
                'ohlcv_flag': '1'
            })

            depth_data = depth_data["d"]

            if not depth_data or fyers_symbol not in depth_data:
                logger.warning(f"No market depth data for {symbol}")
                return None

            market_depth = depth_data[fyers_symbol]

            # Parse and create order book snapshot
            order_book = self._parse_order_book(symbol, market_depth)

            # Cache the result
            self.order_book_cache[cache_key] = order_book
            self.last_update_times[cache_key] = now

            return order_book

        except Exception as e:
            logger.error(f"Error getting market depth for {symbol}: {e}")
            return None

    def _parse_order_book(self, symbol: str, market_depth: Dict) -> OrderBookSnapshot:
        """Parse Fyers market depth response into OrderBookSnapshot"""

        # Parse bid levels
        bids = []
        if 'bids' in market_depth:
            for bid_data in market_depth['bids']:
                bids.append(OrderBookLevel(
                    price=float(bid_data.get('price', 0)),
                    quantity=int(bid_data.get('volume', 0)),
                    orders=int(bid_data.get('orders', 1)),
                    side='BID'
                ))

        # Parse ask levels
        asks = []
        if 'asks' in market_depth:
            for ask_data in market_depth['asks']:
                asks.append(OrderBookLevel(
                    price=float(ask_data.get('price', 0)),
                    quantity=int(ask_data.get('volume', 0)),
                    orders=int(ask_data.get('orders', 1)),
                    side='ASK'
                ))

        # Sort bids (highest first) and asks (lowest first)
        bids = sorted(bids, key=lambda x: x.price, reverse=True)
        asks = sorted(asks, key=lambda x: x.price)

        # Calculate spread and mid-price
        best_bid = bids[0].price if bids else 0
        best_ask = asks[0].price if asks else 0
        spread = best_ask - best_bid if best_bid > 0 and best_ask > 0 else 0
        mid_price = (best_bid + best_ask) / 2 if best_bid > 0 and best_ask > 0 else 0

        return OrderBookSnapshot(
            symbol=symbol,
            timestamp=datetime.now(),
            bids=bids,
            asks=asks,
            last_traded_price=float(market_depth.get('ltp', 0)),
            last_traded_quantity=int(market_depth.get('ltq', 0)),
            spread=spread,
            mid_price=mid_price
        )

    async def get_tick_data(self, symbol: str, duration_seconds: int = 10) -> List[TickData]:
        """Get recent tick data for order flow analysis"""
        try:
            # In a real implementation, this would connect to tick data stream
            # For now, we'll simulate tick data based on recent quotes

            fyers_symbol = self.symbol_mapping.get(symbol, symbol)

            # Get recent quotes to simulate tick data
            quotes_data = self._make_request('POST', '/data/quotes', {
                'symbols': fyers_symbol,
                'ohlcv_flag': '1'
            })

            if not quotes_data or fyers_symbol not in quotes_data:
                return []

            quote = quotes_data[fyers_symbol]

            # Simulate tick data (in real implementation, this would be actual ticks)
            ticks = []
            base_time = datetime.now()

            for i in range(duration_seconds):
                # Simulate price movement around last traded price
                base_price = float(quote.get('ltp', 0))
                price_variation = base_price * 0.001  # 0.1% variation

                tick = TickData(
                    symbol=symbol,
                    timestamp=base_time - timedelta(seconds=duration_seconds - i),
                    price=base_price + (i % 3 - 1) * price_variation,
                    quantity=100 + (i * 50),
                    side='BUY' if i % 2 == 0 else 'SELL'
                )
                ticks.append(tick)

            return ticks

        except Exception as e:
            logger.error(f"Error getting tick data for {symbol}: {e}")
            return []

    def calculate_order_flow_imbalance(self, ticks: List[TickData]) -> Dict[str, float]:
        """Calculate order flow imbalance from tick data"""
        if not ticks:
            return {'buy_volume': 0, 'sell_volume': 0, 'imbalance_ratio': 1.0}

        buy_volume = sum(tick.quantity for tick in ticks if tick.side == 'BUY')
        sell_volume = sum(tick.quantity for tick in ticks if tick.side == 'SELL')

        total_volume = buy_volume + sell_volume
        if total_volume == 0:
            return {'buy_volume': 0, 'sell_volume': 0, 'imbalance_ratio': 1.0}

        imbalance_ratio = buy_volume / sell_volume if sell_volume > 0 else float('inf')

        return {
            'buy_volume': buy_volume,
            'sell_volume': sell_volume,
            'total_volume': total_volume,
            'buy_percentage': (buy_volume / total_volume) * 100,
            'sell_percentage': (sell_volume / total_volume) * 100,
            'imbalance_ratio': imbalance_ratio
        }

    def analyze_order_book_imbalance(self, order_book: OrderBookSnapshot,
                                     levels: int = 3) -> Dict[str, float]:
        """Analyze bid/ask imbalance in order book"""
        if not order_book.bids or not order_book.asks:
            return {'bid_volume': 0, 'ask_volume': 0, 'imbalance_ratio': 1.0}

        # Sum volumes at top levels
        bid_volume = sum(
            level.quantity for level in order_book.bids[:levels]
        )
        ask_volume = sum(
            level.quantity for level in order_book.asks[:levels]
        )

        total_volume = bid_volume + ask_volume
        if total_volume == 0:
            return {'bid_volume': 0, 'ask_volume': 0, 'imbalance_ratio': 1.0}

        imbalance_ratio = bid_volume / ask_volume if ask_volume > 0 else float('inf')

        return {
            'bid_volume': bid_volume,
            'ask_volume': ask_volume,
            'total_volume': total_volume,
            'bid_percentage': (bid_volume / total_volume) * 100,
            'ask_percentage': (ask_volume / total_volume) * 100,
            'imbalance_ratio': imbalance_ratio,
            'spread_bps': (order_book.spread / order_book.mid_price) * 10000 if order_book.mid_price > 0 else 0
        }

    def identify_support_resistance_levels(self, order_book: OrderBookSnapshot,
                                           min_volume_threshold: int = 1000) -> Dict[str, List[float]]:
        """Identify support and resistance levels from order book"""
        support_levels = []
        resistance_levels = []

        # Identify significant bid levels (support)
        for level in order_book.bids:
            if level.quantity >= min_volume_threshold:
                support_levels.append(level.price)

        # Identify significant ask levels (resistance)
        for level in order_book.asks:
            if level.quantity >= min_volume_threshold:
                resistance_levels.append(level.price)

        return {
            'support_levels': support_levels[:5],  # Top 5 support levels
            'resistance_levels': resistance_levels[:5],  # Top 5 resistance levels
            'strongest_support': support_levels[0] if support_levels else None,
            'strongest_resistance': resistance_levels[0] if resistance_levels else None
        }

    async def get_real_time_volatility(self, symbol: str, period_minutes: int = 5) -> float:
        """Calculate real-time volatility from recent price movements"""
        try:
            # Get historical data for volatility calculation
            hist_data = self.get_historical_data(symbol, "1d")

            if len(hist_data) < period_minutes:
                return 0.0

            # Calculate returns and volatility
            recent_data = hist_data.tail(period_minutes)
            returns = recent_data['Close'].pct_change().dropna()

            if len(returns) == 0:
                return 0.0

            # Annualized volatility
            volatility = returns.std() * (252 ** 0.5) * 100  # Percentage

            return volatility

        except Exception as e:
            logger.error(f"Error calculating volatility for {symbol}: {e}")
            return 0.0

    def check_scalping_conditions(self, order_book: OrderBookSnapshot,
                                  ticks: List[TickData]) -> Dict[str, bool]:
        """Check if market conditions are suitable for scalping"""
        conditions = {
            'adequate_spread': False,
            'sufficient_volume': False,
            'stable_book': False,
            'good_imbalance': False,
            'active_trading': False
        }

        try:
            # Check spread (not too wide, not too narrow)
            if order_book.spread > 0:
                spread_bps = (order_book.spread / order_book.mid_price) * 10000
                conditions['adequate_spread'] = 5 <= spread_bps <= 50  # 0.5 to 5 bps

            # Check volume at best levels
            if order_book.bids and order_book.asks:
                best_bid_vol = order_book.bids[0].quantity
                best_ask_vol = order_book.asks[0].quantity
                conditions['sufficient_volume'] = (best_bid_vol + best_ask_vol) >= 500

            # Check order book stability (depth)
            conditions['stable_book'] = len(order_book.bids) >= 3 and len(order_book.asks) >= 3

            # Check imbalance
            imbalance = self.analyze_order_book_imbalance(order_book)
            conditions['good_imbalance'] = (
                    imbalance['imbalance_ratio'] >= 1.5 or
                    imbalance['imbalance_ratio'] <= 0.67
            )

            # Check recent trading activity
            if ticks:
                recent_volume = sum(tick.quantity for tick in ticks[-10:])  # Last 10 ticks
                conditions['active_trading'] = recent_volume >= 1000

        except Exception as e:
            logger.error(f"Error checking scalping conditions: {e}")

        return conditions

    async def place_scalping_order(self, symbol: str, side: str, quantity: int,
                                   order_type: str = "1", price: float = None) -> Optional[Dict]:
        """Place order optimized for scalping (with immediate execution checks)"""
        try:
            # Get current market depth for optimal pricing
            order_book = await self.get_market_depth(symbol)

            if not order_book:
                logger.error(f"Cannot get market depth for {symbol}")
                return None

            # Determine optimal price for scalping
            if price is None:
                if side == '1':  # Buy order
                    # Use best ask price for immediate execution
                    price = order_book.asks[0].price if order_book.asks else order_book.mid_price
                else:  # Sell order
                    # Use best bid price for immediate execution
                    price = order_book.bids[0].price if order_book.bids else order_book.mid_price

            # Place the order
            order_result = self.place_order(symbol, side, quantity, order_type, price)

            if order_result:
                logger.info(f"Scalping order placed: {symbol} {side} {quantity} @ {price}")

            return order_result

        except Exception as e:
            logger.error(f"Error placing scalping order for {symbol}: {e}")
            return None