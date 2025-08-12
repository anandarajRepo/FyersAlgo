import numpy as np
import pandas as pd
import logging
import pytz
from interfaces.data_provider import IDataProvider
from models.trading_models import MarketData
from datetime import datetime

logger = logging.getLogger(__name__)

# Add IST timezone handling
IST = pytz.timezone('Asia/Kolkata')


class TechnicalAnalysisService:
    """Service for technical analysis calculations"""

    def __init__(self, data_provider: IDataProvider):
        self.data_provider = data_provider

    def calculate_selling_pressure_score(self, symbol: str, period_days: int = 5) -> float:
        """Calculate selling pressure score"""
        try:
            hist = self.data_provider.get_historical_data(symbol, f"{period_days + 5}d")

            if len(hist) < period_days:
                return 0.0

            recent_data = hist.tail(period_days)

            # Price decline
            price_decline = (recent_data['Close'].iloc[-1] - recent_data['Close'].iloc[0]) / recent_data['Close'].iloc[0]

            # Red candles ratio
            red_candles = (recent_data['Close'] < recent_data['Open']).sum() / len(recent_data)

            # Volume trend
            volume_trend = (recent_data['Volume'].tail(2).mean() / recent_data['Volume'].head(3).mean())

            # Lower closes ratio
            lower_closes = (recent_data['Close'].diff() < 0).sum() / (len(recent_data) - 1)

            # RSI calculation
            rsi = self._calculate_rsi(recent_data['Close'])

            # Weighted score
            score = (
                    (-price_decline * 100 * 0.3) +
                    (red_candles * 100 * 0.2) +
                    (volume_trend * 20 * 0.2) +
                    (lower_closes * 100 * 0.2) +
                    ((100 - rsi) * 0.1)
            )

            return min(max(score, 0), 100)

        except Exception as e:
            logger.error(f"Error calculating selling pressure for {symbol}: {e}")
            return 0.0

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=min(period, len(delta))).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=min(period, len(delta))).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)).iloc[-1]
            return rsi if not np.isnan(rsi) else 50.0
        except:
            return 50.0

    async def calculate_volume_ratio(self, symbol: str, market_data: MarketData) -> float:
        """Calculate volume ratio vs average"""
        try:
            hist = self.data_provider.get_historical_data(symbol, "20d")
            if len(hist) == 0:
                return 1.0

            avg_volume = hist['Volume'].mean()
            current_volume = market_data.volume

            # Estimate full day volume
            now = datetime.now(IST)
            market_hours_elapsed = (now.hour - 9) + (now.minute - 15) / 60
            market_hours_elapsed = max(market_hours_elapsed, 0.5)

            estimated_full_day_volume = current_volume * (6.5 / market_hours_elapsed)
            volume_ratio = estimated_full_day_volume / avg_volume if avg_volume > 0 else 1.0

            return volume_ratio

        except Exception as e:
            logger.error(f"Error calculating volume ratio for {symbol}: {e}")
            return 1.0