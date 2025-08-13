import requests
import hashlib
import hmac
import json
import logging
import pandas as pd
import yfinance as yf

from typing import Dict, List, Optional
from config.settings import FyersConfig
from interfaces.data_provider import IDataProvider, IBroker
from models.trading_models import MarketData
from datetime import datetime

logger = logging.getLogger(__name__)


class FyersService(IDataProvider, IBroker):
    """Fyers API implementation"""

    def __init__(self, config: FyersConfig):
        self.config = config
        self.session = requests.Session()

        # Symbol mapping
        self.symbol_mapping = {
            'NESTLEIND.NS': 'NSE:NESTLEIND-EQ',
            'COLPAL.NS': 'NSE:COLPAL-EQ',
            'TATACONSUM.NS': 'NSE:TATACONSUM-EQ',
            'HINDUNILVR.NS': 'NSE:HINDUNILVR-EQ',
            'ITC.NS': 'NSE:ITC-EQ',
            'BRITANNIA.NS': 'NSE:BRITANNIA-EQ',
            'DABUR.NS': 'NSE:DABUR-EQ',
            'MARICO.NS': 'NSE:MARICO-EQ',
            'TCS.NS': 'NSE:TCS-EQ',
            'INFY.NS': 'NSE:INFY-EQ',
            'WIPRO.NS': 'NSE:WIPRO-EQ',
            'HCLTECH.NS': 'NSE:HCLTECH-EQ',
            'TECHM.NS': 'NSE:TECHM-EQ',
            'LTI.NS': 'NSE:LTI-EQ',
            'COFORGE.NS': 'NSE:COFORGE-EQ',
            'PERSISTENT.NS': 'NSE:PERSISTENT-EQ',
            'HDFCBANK.NS': 'NSE:HDFCBANK-EQ',
            'ICICIBANK.NS': 'NSE:ICICIBANK-EQ',
            'SBIN.NS': 'NSE:SBIN-EQ',
            'AXISBANK.NS': 'NSE:AXISBANK-EQ',
            'KOTAKBANK.NS': 'NSE:KOTAKBANK-EQ',
            'INDUSINDBK.NS': 'NSE:INDUSINDBK-EQ',
            'MARUTI.NS': 'NSE:MARUTI-EQ',
            'TATAMOTORS.NS': 'NSE:TATAMOTORS-EQ',
            'BAJAJ-AUTO.NS': 'NSE:BAJAJ-AUTO-EQ',
            'M&M.NS': 'NSE:M&M-EQ',
            'HEROMOTOCO.NS': 'NSE:HEROMOTOCO-EQ',
            'EICHERMOT.NS': 'NSE:EICHERMOT-EQ',
            'RELIANCE.NS': 'NSE:RELIANCE-EQ',
        }

    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Optional[Dict]:
        """Make HTTP request to Fyers API"""
        try:

            if endpoint.endswith("/data/depth"):
                url = f"{self.config.base_url_v1}{endpoint}"
            else:
                url = f"{self.config.base_url}{endpoint}"

            headers = {'Authorization': f"{self.config.client_id}:{self.config.access_token}"}

            if method.upper() == 'GET':
                response = self.session.get(url, headers=headers, params=data)
            else:
                response = self.session.request(method, url, headers=headers, json=data)

            if response.status_code == 200:
                result = response.json()
                if result['s'] == 'ok':
                    return result.get('data', result)
                else:
                    logger.error(f"API Error: {result['message']}")
                    return None
            else:
                logger.error(f"HTTP Error: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None

    async def get_quotes(self, symbols: List[str]) -> Dict[str, MarketData]:
        """Get real-time quotes"""
        try:
            fyers_symbols = [self.symbol_mapping.get(s, s) for s in symbols]

            data = {
                'symbols': ','.join(fyers_symbols),
                'ohlcv_flag': '1'
            }

            result = self._make_request('POST', '/data/quotes', data)

            if not result:
                return {}

            market_data = {}
            for symbol in symbols:
                fyers_symbol = self.symbol_mapping.get(symbol, symbol)
                if fyers_symbol in result:
                    quote = result[fyers_symbol]
                    market_data[symbol] = MarketData(
                        symbol=symbol,
                        current_price=quote['lp'],
                        open_price=quote['o'],
                        high_price=quote['h'],
                        low_price=quote['l'],
                        volume=quote.get('vol', 0),
                        previous_close=quote['prev_close_price'],
                        timestamp=datetime.now()
                    )

            return market_data

        except Exception as e:
            logger.error(f"Error fetching quotes: {e}")
            return {}

    def get_historical_data(self, symbol: str, period: str) -> pd.DataFrame:
        """Get historical data using yfinance as fallback"""
        try:
            stock = yf.Ticker(symbol)
            return stock.history(period=period)
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return pd.DataFrame()

    async def get_index_data(self, index_symbol: str = 'NSE:NIFTY50-INDEX') -> Dict:
        """Get index data"""
        try:
            result = self._make_request('POST', '/data/quotes', {
                'symbols': index_symbol,
                'ohlcv_flag': '1'
            })

            if result and index_symbol in result:
                quote = result[index_symbol]
                return {
                    'current_price': quote['lp'],
                    'previous_close': quote['prev_close_price'],
                    'gap_percentage': ((quote['lp'] - quote['prev_close_price']) /
                                       quote['prev_close_price']) * 100
                }

            return {'current_price': 25000, 'previous_close': 24950, 'gap_percentage': 0.2}

        except Exception as e:
            logger.error(f"Error fetching index data: {e}")
            return {'current_price': 25000, 'previous_close': 24950, 'gap_percentage': 0.2}

    def place_order(self, symbol: str, side: str, quantity: int,
                    order_type: str = "2", price: float = 0) -> Optional[Dict]:
        """Place single order"""
        try:
            fyers_symbol = self.symbol_mapping.get(symbol, symbol)

            data = {
                'symbol': fyers_symbol,
                'qty': quantity,
                'type': order_type,
                'side': side,
                'productType': 'INTRADAY',
                'limitPrice': price if order_type == "1" else 0,
                'validity': 'DAY',
                'disclosedQty': 0,
                'offlineOrder': 'False'
            }

            return self._make_request('POST', '/orders', data)

        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None

    def place_bracket_order(self, symbol: str, quantity: int, price: float,
                            stop_loss: float, target: float) -> Optional[Dict]:
        """Place bracket order"""
        try:
            fyers_symbol = self.symbol_mapping.get(symbol, symbol)

            sl_percentage = ((stop_loss - price) / price) * 100
            target_percentage = ((price - target) / price) * 100

            data = {
                'symbol': fyers_symbol,
                'qty': quantity,
                'type': '2',
                'side': '-1',
                'productType': 'BRACKET',
                'validity': 'DAY',
                'stopLoss': round(sl_percentage, 2),
                'takeProfit': round(target_percentage, 2),
                'disclosedQty': 0,
                'offlineOrder': 'False'
            }

            return self._make_request('POST', '/orders', data)

        except Exception as e:
            logger.error(f"Error placing bracket order: {e}")
            return None

    def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        try:
            result = self._make_request('DELETE', '/orders', {'id': order_id})
            return result is not None
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False

    def get_positions(self) -> List[Dict]:
        """Get positions"""
        try:
            result = self._make_request('GET', '/positions')
            return result.get('netPositions', []) if result else []
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []

    def get_orders(self) -> List[Dict]:
        """Get orders"""
        try:
            result = self._make_request('GET', '/orders')
            return result.get('orderBook', []) if result else []
        except Exception as e:
            logger.error(f"Error fetching orders: {e}")
            return []