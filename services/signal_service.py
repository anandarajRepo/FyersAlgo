from typing import List, Dict
from datetime import datetime
from config.settings import Sector, StrategyConfig
from models.trading_models import TradingSignal
from interfaces.data_provider import IDataProvider
from services.analysis_service import TechnicalAnalysisService

import logging

logger = logging.getLogger(__name__)


class SignalGenerationService:
    """Service for generating trading signals"""

    def __init__(self, data_provider: IDataProvider, analysis_service: TechnicalAnalysisService):
        self.data_provider = data_provider
        self.analysis_service = analysis_service

        self.sector_weights = {
            Sector.FMCG: 1.0,
            Sector.IT: 0.9,
            Sector.BANKING: 0.6,
            Sector.AUTO: 0.3,
            Sector.PHARMA: 0.7,
            Sector.METALS: 0.5,
            Sector.REALTY: 0.4
        }

        self.stock_sectors = {
            'NESTLEIND.NS': Sector.FMCG,
            'COLPAL.NS': Sector.FMCG,
            'TATACONSUM.NS': Sector.FMCG,
            'HINDUNILVR.NS': Sector.FMCG,
            'ITC.NS': Sector.FMCG,
            'BRITANNIA.NS': Sector.FMCG,
            'DABUR.NS': Sector.FMCG,
            'MARICO.NS': Sector.FMCG,
            'TCS.NS': Sector.IT,
            'INFY.NS': Sector.IT,
            'WIPRO.NS': Sector.IT,
            'HCLTECH.NS': Sector.IT,
            'TECHM.NS': Sector.IT,
            'LTI.NS': Sector.IT,
            'COFORGE.NS': Sector.IT,
            'PERSISTENT.NS': Sector.IT,
            'HDFCBANK.NS': Sector.BANKING,
            'ICICIBANK.NS': Sector.BANKING,
            'SBIN.NS': Sector.BANKING,
            'AXISBANK.NS': Sector.BANKING,
            'KOTAKBANK.NS': Sector.BANKING,
            'INDUSINDBK.NS': Sector.BANKING,
            'MARUTI.NS': Sector.AUTO,
            'TATAMOTORS.NS': Sector.AUTO,
            'BAJAJ-AUTO.NS': Sector.AUTO,
            'M&M.NS': Sector.AUTO,
            'HEROMOTOCO.NS': Sector.AUTO,
            'EICHERMOT.NS': Sector.AUTO,
        }

    async def generate_signals(self, index_data: Dict, config: StrategyConfig) -> List[TradingSignal]:
        """Generate trading signals"""
        signals = []

        if index_data['gap_percentage'] <= 0:
            logger.info("No gap-up indication from index")
            return signals

        logger.info(f"Index gap-up: {index_data['gap_percentage']:.2f}%")

        # Get market data for all stocks
        symbols = list(self.stock_sectors.keys())
        market_data_dict = await self.data_provider.get_quotes(symbols)

        for symbol, sector in self.stock_sectors.items():
            try:
                if symbol not in market_data_dict:
                    continue

                market_data = market_data_dict[symbol]

                # Check gap-up condition
                gap_percentage = ((market_data.open_price - market_data.previous_close) /
                                  market_data.previous_close) * 100

                if gap_percentage < config.min_gap_percentage:
                    continue

                # Calculate indicators
                selling_pressure = self.analysis_service.calculate_selling_pressure_score(symbol)
                volume_ratio = await self.analysis_service.calculate_volume_ratio(symbol, market_data)

                # Check criteria
                if (selling_pressure >= config.min_selling_pressure and
                        volume_ratio >= config.min_volume_ratio):
                    # Calculate confidence
                    sector_preference = self.sector_weights.get(sector, 0.5)
                    confidence = (
                            (selling_pressure / 100) * 0.4 +
                            min(volume_ratio / 3, 1) * 0.3 +
                            (gap_percentage / 5) * 0.2 +
                            sector_preference * 0.1
                    )

                    # Calculate levels
                    stop_loss = market_data.current_price * (1 + config.stop_loss_pct / 100)
                    target_price = market_data.current_price * (1 - config.target_pct / 100)

                    signal = TradingSignal(
                        symbol=symbol,
                        sector=sector,
                        signal_type='SHORT',
                        entry_price=market_data.current_price,
                        stop_loss=stop_loss,
                        target_price=target_price,
                        confidence=confidence,
                        gap_percentage=gap_percentage,
                        selling_pressure_score=selling_pressure,
                        volume_ratio=volume_ratio,
                        timestamp=datetime.now()
                    )

                    signals.append(signal)
                    logger.info(f"Signal: {symbol} - Gap: {gap_percentage:.2f}%, "
                                f"Pressure: {selling_pressure:.1f}, Confidence: {confidence:.2f}")

            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")

        # Sort by confidence
        signals.sort(key=lambda x: x.confidence, reverse=True)
        return signals