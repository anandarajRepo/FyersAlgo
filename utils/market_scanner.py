import asyncio
import logging
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from services.fyers_service import FyersService
from models.trading_models import MarketData

logger = logging.getLogger(__name__)


class MarketScanner:
    """Advanced market scanning for opportunity identification"""

    def __init__(self, fyers_service: FyersService):
        self.fyers_service = fyers_service

        # Expanded universe of stocks for scanning
        self.scan_universe = {
            # Large Cap
            'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS',
            'HINDUNILVR.NS', 'ITC.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'LT.NS',

            # Mid Cap - High momentum potential
            'BAJFINANCE.NS', 'MARUTI.NS', 'TATAMOTORS.NS', 'AXISBANK.NS',
            'ULTRACEMCO.NS', 'ASIANPAINT.NS', 'NESTLEIND.NS', 'KOTAKBANK.NS',
            'TECHM.NS', 'HCLTECH.NS', 'WIPRO.NS', 'DRREDDY.NS',

            # Sectoral leaders
            'BAJAJ-AUTO.NS', 'HEROMOTOCO.NS', 'TATASTEEL.NS', 'HINDALCO.NS',
            'JSWSTEEL.NS', 'COALINDIA.NS', 'ONGC.NS', 'IOC.NS', 'BPCL.NS',
            'SUNPHARMA.NS', 'CIPLA.NS', 'DIVISLAB.NS', 'BIOCON.NS'
        }

    async def scan_for_gap_opportunities(self) -> List[Dict]:
        """Scan for gap-up/gap-down opportunities"""
        opportunities = []

        try:
            # Get quotes for all symbols
            symbols = list(self.scan_universe)
            market_data = await self.fyers_service.get_quotes(symbols)

            for symbol, data in market_data.items():
                # Calculate gap percentage
                gap_pct = ((data.open_price - data.previous_close) / data.previous_close) * 100

                # Identify significant gaps
                if abs(gap_pct) >= 1.0:  # 1% or more gap
                    opportunity = {
                        'symbol': symbol,
                        'gap_type': 'GAP_UP' if gap_pct > 0 else 'GAP_DOWN',
                        'gap_percentage': gap_pct,
                        'current_price': data.current_price,
                        'volume': data.volume,
                        'opportunity_score': self._calculate_gap_score(data, gap_pct)
                    }
                    opportunities.append(opportunity)

            # Sort by opportunity score
            opportunities.sort(key=lambda x: x['opportunity_score'], reverse=True)

            logger.info(f"Found {len(opportunities)} gap opportunities")
            return opportunities

        except Exception as e:
            logger.error(f"Error scanning for gap opportunities: {e}")
            return []

    async def scan_for_breakout_setups(self) -> List[Dict]:
        """Scan for potential breakout setups"""
        setups = []

        try:
            symbols = list(self.scan_universe)
            market_data = await self.fyers_service.get_quotes(symbols)

            for symbol, data in market_data.items():
                # Check for consolidation patterns and volume
                setup_score = await self._analyze_breakout_potential(symbol, data)

                if setup_score > 70:  # High potential threshold
                    setup = {
                        'symbol': symbol,
                        'current_price': data.current_price,
                        'volume_ratio': data.volume / await self._get_avg_volume(symbol),
                        'setup_score': setup_score,
                        'breakout_level': await self._calculate_breakout_level(symbol),
                        'setup_type': 'BREAKOUT_SETUP'
                    }
                    setups.append(setup)

            setups.sort(key=lambda x: x['setup_score'], reverse=True)

            logger.info(f"Found {len(setups)} breakout setups")
            return setups

        except Exception as e:
            logger.error(f"Error scanning for breakout setups: {e}")
            return []

    def _calculate_gap_score(self, data: MarketData, gap_pct: float) -> float:
        """Calculate opportunity score for gap trades"""
        score = 0

        # Gap size score (optimal range 1-4%)
        if 1 <= abs(gap_pct) <= 4:
            score += 30
        elif abs(gap_pct) > 4:
            score += 20  # Too large gaps can be risky

        # Volume score (higher volume = better)
        if data.volume > 0:
            score += min(data.volume / 100000, 20)  # Cap at 20 points

        # Price range score (avoid penny stocks and very expensive stocks)
        if 50 <= data.current_price <= 3000:
            score += 25

        # Current vs open price momentum
        momentum = ((data.current_price - data.open_price) / data.open_price) * 100
        if abs(momentum) < 1:  # Stability after gap
            score += 15

        return min(score, 100)

    async def _analyze_breakout_potential(self, symbol: str, data: MarketData) -> float:
        """Analyze breakout potential for a stock"""
        try:
            # Get historical data
            hist = self.fyers_service.get_historical_data(symbol, "20d")
            if len(hist) < 10:
                return 0

            score = 0

            # Volume analysis
            recent_volume = hist['Volume'].tail(5).mean()
            avg_volume = hist['Volume'].mean()
            if recent_volume > avg_volume * 1.2:
                score += 25

            # Price consolidation analysis
            high_20 = hist['High'].max()
            current_price = data.current_price

            # Check if near resistance
            if current_price >= high_20 * 0.95:  # Within 5% of 20-day high
                score += 30

            # Volatility analysis
            returns = hist['Close'].pct_change().dropna()
            volatility = returns.std()
            if 0.02 <= volatility <= 0.05:  # Optimal volatility range
                score += 20

            # Trend analysis
            sma_10 = hist['Close'].tail(10).mean()
            sma_20 = hist['Close'].tail(20).mean()
            if sma_10 > sma_20:  # Uptrend
                score += 25

            return score

        except Exception as e:
            logger.error(f"Error analyzing breakout potential for {symbol}: {e}")
            return 0

    async def _get_avg_volume(self, symbol: str) -> float:
        """Get average volume for symbol"""
        try:
            hist = self.fyers_service.get_historical_data(symbol, "20d")
            return hist['Volume'].mean() if len(hist) > 0 else 1
        except:
            return 1

    async def _calculate_breakout_level(self, symbol: str) -> float:
        """Calculate potential breakout level"""
        try:
            hist = self.fyers_service.get_historical_data(symbol, "20d")
            if len(hist) > 0:
                return hist['High'].max()
            return 0
        except:
            return 0