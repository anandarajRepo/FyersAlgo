from typing import Dict, List
import logging
from interfaces.data_provider import IBroker
from interfaces.data_provider import IDataProvider
from models.trading_models import TradingSignal
from models.trading_models import Position
from models.trading_models import PnLSummary
from config.settings import StrategyConfig
from typing import Optional

logger = logging.getLogger(__name__)


class PositionManagementService:
    """Service for managing positions"""

    def __init__(self, broker: IBroker, data_provider: IDataProvider):
        self.broker = broker
        self.data_provider = data_provider

    def calculate_position_size(self, signal: TradingSignal, config: StrategyConfig) -> int:
        """Calculate position size based on risk management"""
        try:
            risk_amount = config.portfolio_value * (config.risk_per_trade_pct / 100)
            price_risk = abs(signal.stop_loss - signal.entry_price)

            if price_risk <= 0:
                return 0

            quantity = int(risk_amount / price_risk)
            return max(quantity, 0)

        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0

    def execute_trade(self, signal: TradingSignal, quantity: int) -> Optional[Dict]:
        """Execute trade via broker"""
        try:
            if quantity <= 0:
                logger.warning(f"Invalid quantity for {signal.symbol}")
                return None

            order_result = self.broker.place_bracket_order(
                symbol=signal.symbol,
                quantity=quantity,
                price=signal.entry_price,
                stop_loss=signal.stop_loss,
                target=signal.target_price
            )

            if order_result:
                logger.info(f"Trade executed: {signal.symbol} - Qty: {quantity}, "
                            f"Order ID: {order_result.get('id')}")

            return order_result

        except Exception as e:
            logger.error(f"Error executing trade for {signal.symbol}: {e}")
            return None

    def monitor_positions(self, positions: Dict[str, Position]) -> PnLSummary:
        """Monitor and update positions"""
        pnl_summary = PnLSummary()

        try:
            broker_positions = self.broker.get_positions()
            current_orders = self.broker.get_orders()

            closed_positions = []

            for symbol, position in positions.items():
                try:
                    # Find position in broker data
                    broker_position = self._find_broker_position(symbol, broker_positions)

                    if broker_position:
                        # Position still active
                        current_price = float(broker_position['ltp'])
                        unrealized_pnl = (position.entry_price - current_price) * position.quantity
                        pnl_summary.unrealized_pnl += unrealized_pnl

                    else:
                        # Position closed
                        order_info = self._find_order_info(position.order_id, current_orders)
                        if order_info and order_info['status'] in ['TRADED', 'COMPLETE']:
                            realized_pnl = self._calculate_realized_pnl(position, order_info)
                            pnl_summary.realized_pnl += realized_pnl
                            pnl_summary.closed_positions.append({
                                'symbol': symbol,
                                'reason': 'BRACKET_EXECUTED',
                                'pnl': realized_pnl
                            })
                            closed_positions.append(symbol)

                except Exception as e:
                    logger.error(f"Error monitoring position {symbol}: {e}")

            # Update closed positions list
            for symbol in closed_positions:
                if symbol in positions:
                    del positions[symbol]

        except Exception as e:
            logger.error(f"Error in position monitoring: {e}")

        return pnl_summary

    def _find_broker_position(self, symbol: str, broker_positions: List[Dict]) -> Optional[Dict]:
        """Find position in broker data"""
        # Implementation depends on broker response format
        # This is a simplified version
        for pos in broker_positions:
            if symbol in pos.get('symbol', ''):
                return pos
        return None

    def _find_order_info(self, order_id: str, orders: List[Dict]) -> Optional[Dict]:
        """Find order information"""
        for order in orders:
            if order.get('id') == order_id:
                return order
        return None

    def _calculate_realized_pnl(self, position: Position, order_info: Dict) -> float:
        """Calculate realized PnL"""
        # Simplified calculation - depends on broker response format
        exit_price = position.stop_loss  # Default assumption
        return (position.entry_price - exit_price) * position.quantity