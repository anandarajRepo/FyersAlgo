import requests
import hashlib
import hmac
import json
import logging
import pandas as pd
import yfinance as yf
from urllib.parse import urlencode

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

    def _log_request_details(self, method: str, url: str, headers: Dict, data: Dict = None, is_get: bool = False):
        """Log complete request details for debugging"""
        logger.info("=" * 80)
        logger.info("REQUEST DETAILS")
        logger.info("=" * 80)
        logger.info(f"Method: {method}")
        logger.info(f"URL: {url}")

        # Log headers (mask sensitive data)
        safe_headers = headers.copy()
        if 'Authorization' in safe_headers:
            auth_parts = safe_headers['Authorization'].split(':')
            if len(auth_parts) == 2:
                safe_headers['Authorization'] = f"{auth_parts[0]}:***MASKED***"

        logger.info(f"Headers: {json.dumps(safe_headers, indent=2)}")

        if data:
            if is_get:
                # For GET requests, show how data becomes query parameters
                query_string = urlencode(data)
                full_url = f"{url}?{query_string}" if query_string else url
                logger.info(f"Query Parameters: {json.dumps(data, indent=2)}")
                logger.info(f"Full URL with params: {full_url}")
            else:
                # For non-GET requests, show JSON body
                logger.info(f"JSON Body: {json.dumps(data, indent=2)}")
        else:
            logger.info("No data/parameters")

        # Generate equivalent curl command
        self._log_curl_equivalent(method, url, headers, data, is_get)
        logger.info("=" * 80)

    def _log_curl_equivalent(self, method: str, url: str, headers: Dict, data: Dict = None, is_get: bool = False):
        """Generate and log equivalent curl command"""
        curl_cmd = f"curl -X {method}"

        # Add headers
        for key, value in headers.items():
            if key == 'Authorization':
                # Mask token in curl command
                auth_parts = value.split(':')
                if len(auth_parts) == 2:
                    masked_value = f"{auth_parts[0]}:YOUR_ACCESS_TOKEN"
                    curl_cmd += f" -H '{key}: {masked_value}'"
            else:
                curl_cmd += f" -H '{key}: {value}'"

        if data:
            if is_get:
                # For GET, add query parameters to URL
                query_string = urlencode(data)
                full_url = f"{url}?{query_string}" if query_string else url
                curl_cmd += f" '{full_url}'"
            else:
                # For non-GET, add JSON data
                curl_cmd += f" -H 'Content-Type: application/json'"
                curl_cmd += f" -d '{json.dumps(data)}'"
                curl_cmd += f" '{url}'"
        else:
            curl_cmd += f" '{url}'"

        curl_cmd += " -v"  # Add verbose flag

        logger.info("Equivalent curl command:")
        logger.info(curl_cmd)

    def _log_response_details(self, response: requests.Response):
        """Log response details"""
        logger.info("-" * 40)
        logger.info("RESPONSE DETAILS")
        logger.info("-" * 40)
        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Response Headers: {dict(response.headers)}")

        try:
            response_json = response.json()
            logger.info(f"Response Body: {json.dumps(response_json, indent=2)}")
        except:
            logger.info(f"Response Body (raw): {response.text}")

        logger.info("-" * 40)

    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Optional[Dict]:
        """Make HTTP request to Fyers API"""
        try:

            if endpoint.endswith("/data/depth") or endpoint.startswith("/data/quotes"):
                url = f"{self.config.base_url_v1}{endpoint}"
            else:
                url = f"{self.config.base_url}{endpoint}"

            headers = {'Authorization': f"{self.config.client_id}:{self.config.access_token}"}

            # Log request details before making the request
            is_get_request = method.upper() == 'GET'
            # self._log_request_details(method, url, headers, data, is_get_request)

            if method.upper() == 'GET':
                response = self.session.get(url, headers=headers, params=data)
            else:
                response = self.session.request(method, url, headers=headers, json=data)

            # Log response details
            # self._log_response_details(response)

            # Process response (your original logic)
            if response.status_code == 200:
                result = response.json()
                if result['s'] == 'ok':
                    logger.info("Request successful")
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

            result = self._make_request('GET', '/data/quotes', data)

            if not result:
                return {}

            market_data = {}
            for symbol in symbols:
                fyers_symbol = self.symbol_mapping.get(symbol, symbol)
                matches = [item for item in result.get('d', []) if item.get('n') == fyers_symbol]
                if len(matches) > 0:
                # if fyers_symbol in result:
                    quote = matches[0]['v']
                    market_data[symbol] = MarketData(
                        symbol=symbol,
                        current_price=quote['lp'],
                        open_price=quote['open_price'],
                        high_price=quote['high_price'],
                        low_price=quote['low_price'],
                        volume=quote['volume'],
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
            result = self._make_request('GET', '/data/quotes', {
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