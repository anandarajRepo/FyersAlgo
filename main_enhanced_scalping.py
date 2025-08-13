# main_enhanced_scalping.py

import asyncio
import logging
import sys
import os
from typing import Dict
from dotenv import load_dotenv

# Import configurations
from config.settings import FyersConfig, StrategyConfig, TradingConfig
from config.breakout_settings import BreakoutConfig
from config.scalping_settings import ScalpingConfig, MultiStrategyScalpingConfig

# Import services
from services.enhanced_fyers_service import EnhancedFyersService
from services.market_timing_service import MarketTimingService

# Import strategies
from main_strategy import GapUpShortStrategy
from strategies.open_breakout_strategy import OpenBreakoutStrategy
from strategies.level2_scalping_strategy import Level2ScalpingStrategy

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_strategy_with_scalping.log'),
        logging.StreamHandler()
    ]
)


class EnhancedMultiStrategyWithScalping:
    """Enhanced strategy manager supporting scalping + existing strategies"""

    def __init__(self, fyers_config, strategy_config, trading_config,
                 breakout_config, scalping_config, multi_config):

        # Initialize enhanced services
        self.fyers_service = EnhancedFyersService(fyers_config)
        self.timing_service = MarketTimingService(trading_config)

        # Configuration
        self.strategy_config = strategy_config
        self.trading_config = trading_config
        self.breakout_config = breakout_config
        self.scalping_config = scalping_config
        self.multi_config = multi_config

        # Strategy instances
        self.gap_up_strategy = GapUpShortStrategy(fyers_config, strategy_config, trading_config)
        self.breakout_strategy = OpenBreakoutStrategy(
            self.fyers_service, strategy_config, trading_config, breakout_config
        )
        self.scalping_strategy = Level2ScalpingStrategy(
            self.fyers_service, strategy_config, trading_config, scalping_config
        )

        # Performance tracking
        self.total_portfolio_pnl = 0.0
        self.daily_portfolio_pnl = 0.0

        # Strategy coordination
        self.last_non_scalping_trade_time = None
        self.strategy_activity_log = []

    async def initialize(self) -> bool:
        """Initialize all strategies including scalping"""
        try:
            # Verify connections
            if not await self.gap_up_strategy.initialize():
                logging.error("Failed to initialize gap-up strategy")
                return False

            # Test Level II data connectivity
            test_symbols = ['RELIANCE.NS', 'TCS.NS']
            for symbol in test_symbols:
                order_book = await self.fyers_service.get_market_depth(symbol)
                if order_book:
                    logging.info(f"Level II data available for {symbol}")
                    break
            else:
                logging.warning("Level II data may not be available")

            logging.info("Multi-strategy with scalping initialized successfully")
            return True

        except Exception as e:
            logging.error(f"Multi-strategy initialization failed: {e}")
            return False

    async def run_all_strategies_with_scalping(self) -> None:
        """Run all strategies including scalping with coordination"""
        try:
            # Check trading hours
            if not self.timing_service.is_trading_time():
                logging.info("Outside trading hours, sleeping...")
                await asyncio.sleep(300)
                return

            # Check if scalping should be paused due to other strategy activity
            scalping_allowed = self._should_allow_scalping()

            # Prepare strategy tasks
            strategy_tasks = []

            # Always run main strategies
            strategy_tasks.extend([
                self.gap_up_strategy.run_strategy_cycle(),
                self.breakout_strategy.run_breakout_cycle()
            ])

            # Add scalping if allowed
            if scalping_allowed:
                strategy_tasks.append(self.scalping_strategy.run_scalping_cycle())
            else:
                logging.debug("Scalping paused due to other strategy activity")

            # Run strategies concurrently
            results = await asyncio.gather(*strategy_tasks, return_exceptions=True)

            # Log any exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    strategy_names = ['gap_up', 'breakout', 'scalping']
                    logging.error(f"Error in {strategy_names[i]} strategy: {result}")

            # Update portfolio performance
            self._update_portfolio_performance()

            # Log combined performance
            self._log_portfolio_status()

            # Update strategy coordination tracking
            self._update_strategy_coordination()

        except Exception as e:
            logging.error(f"Error running multi-strategy with scalping: {e}")

    def _should_allow_scalping(self) -> bool:
        """Determine if scalping should be allowed based on other strategy activity"""

        # If scalping not configured to avoid other signals, always allow
        if self.multi_config.allow_scalping_during_signals:
            return True

        # Check if there was recent activity in other strategies
        if self.last_non_scalping_trade_time:
            from datetime import datetime, timedelta
            cooldown_period = timedelta(minutes=self.multi_config.cross_strategy_cooldown_minutes)
            if datetime.now() - self.last_non_scalping_trade_time < cooldown_period:
                return False

        # Check if we're in signal generation time for other strategies
        if self.timing_service.is_signal_generation_time():
            # Check if other strategies have available slots (indicating they're actively looking)
            gap_up_slots = self.multi_config.max_gap_up_positions - len(self.gap_up_strategy.positions)
            breakout_slots = self.multi_config.max_breakout_positions - len(self.breakout_strategy.positions)

            if gap_up_slots > 0 or breakout_slots > 0:
                return False

        return True

    def _update_strategy_coordination(self) -> None:
        """Update coordination tracking between strategies"""
        from datetime import datetime

        # Check for new trades in non-scalping strategies
        gap_up_positions = len(self.gap_up_strategy.positions)
        breakout_positions = len(self.breakout_strategy.positions)

        # Track if there's been recent activity (simplified check)
        current_activity = gap_up_positions + breakout_positions
        if hasattr(self, '_last_activity_count'):
            if current_activity > self._last_activity_count:
                self.last_non_scalping_trade_time = datetime.now()

        self._last_activity_count = current_activity

    def _update_portfolio_performance(self) -> None:
        """Update overall portfolio performance including scalping"""
        gap_up_perf = self.gap_up_strategy.get_performance_summary()
        breakout_perf = self.breakout_strategy.get_breakout_performance()
        scalping_perf = self.scalping_strategy.get_scalping_performance()

        self.total_portfolio_pnl = (gap_up_perf['total_pnl'] +
                                    breakout_perf['total_pnl'] +
                                    scalping_perf['total_pnl'])

        self.daily_portfolio_pnl = (gap_up_perf['daily_pnl'] +
                                    breakout_perf['daily_pnl'] +
                                    scalping_perf['daily_pnl'])

    def _log_portfolio_status(self) -> None:
        """Log overall portfolio status including scalping"""
        gap_up_perf = self.gap_up_strategy.get_performance_summary()
        breakout_perf = self.breakout_strategy.get_breakout_performance()
        scalping_perf = self.scalping_strategy.get_scalping_performance()

        total_positions = (gap_up_perf['active_positions'] +
                           breakout_perf['active_positions'] +
                           scalping_perf['active_positions'])

        logging.info(f"=== ENHANCED PORTFOLIO STATUS ===")
        logging.info(f"Total Positions: {total_positions}")
        logging.info(f"Gap-Up Short: {gap_up_perf['active_positions']} positions, "
                     f"PnL: Rs.{gap_up_perf['daily_pnl']:.2f}")
        logging.info(f"Breakout: {breakout_perf['active_positions']} positions, "
                     f"PnL: Rs.{breakout_perf['daily_pnl']:.2f}")
        logging.info(f"Scalping: {scalping_perf['active_positions']} positions, "
                     f"Trades: {scalping_perf['trades_today']}, "
                     f"PnL: Rs.{scalping_perf['daily_pnl']:.2f}")
        logging.info(f"Portfolio Daily PnL: Rs.{self.daily_portfolio_pnl:.2f}")
        logging.info(f"Portfolio Total PnL: Rs.{self.total_portfolio_pnl:.2f}")

    def get_comprehensive_performance(self) -> Dict:
        """Get comprehensive performance across all strategies"""
        gap_up_perf = self.gap_up_strategy.get_performance_summary()
        breakout_perf = self.breakout_strategy.get_breakout_performance()
        scalping_perf = self.scalping_strategy.get_scalping_performance()

        return {
            'portfolio_summary': {
                'total_pnl': self.total_portfolio_pnl,
                'daily_pnl': self.daily_portfolio_pnl,
                'total_positions': (gap_up_perf['active_positions'] +
                                    breakout_perf['active_positions'] +
                                    scalping_perf['active_positions']),
                'strategies_active': 3
            },
            'strategy_breakdown': {
                'gap_up_short': gap_up_perf,
                'open_breakout': breakout_perf,
                'level2_scalping': scalping_perf
            },
            'risk_metrics': {
                'position_distribution': {
                    'gap_up': gap_up_perf['active_positions'],
                    'breakout': breakout_perf['active_positions'],
                    'scalping': scalping_perf['active_positions']
                },
                'scalping_metrics': {
                    'trades_today': scalping_perf['trades_today'],
                    'avg_hold_time': self._calculate_avg_scalping_hold_time(),
                    'scalping_frequency': f"{scalping_perf['trades_today']}/hour"
                }
            }
        }

    def _calculate_avg_scalping_hold_time(self) -> str:
        """Calculate average hold time for scalping positions"""
        scalping_perf = self.scalping_strategy.get_scalping_performance()

        if not scalping_perf['positions_detail']:
            return "N/A"

        total_hold_time = sum(
            pos['hold_time_seconds'] for pos in scalping_perf['positions_detail']
        )
        avg_hold_time = total_hold_time / len(scalping_perf['positions_detail'])

        return f"{avg_hold_time:.1f}s"

    async def run(self) -> None:
        """Main execution loop for enhanced multi-strategy with scalping"""
        logging.info("Starting Enhanced Multi-Strategy Trading System with Level II Scalping")

        if not await self.initialize():
            logging.error("Enhanced multi-strategy initialization failed")
            return

        try:
            while True:
                await self.run_all_strategies_with_scalping()

                # Shorter sleep interval for scalping responsiveness
                await asyncio.sleep(max(self.trading_config.monitoring_interval, 5))

        except KeyboardInterrupt:
            logging.info("Enhanced multi-strategy system stopped by user")
        except Exception as e:
            logging.error(f"Fatal error in enhanced multi-strategy: {e}")


def load_enhanced_config() -> Dict:
    """Load enhanced configuration including scalping settings"""
    return {
        'fyers': FyersConfig(
            client_id=os.environ.get('FYERS_CLIENT_ID'),
            secret_key=os.environ.get('FYERS_SECRET_KEY'),
            redirect_uri=os.environ.get('FYERS_REDIRECT_URI', 'https://trade.fyers.in/api-login/redirect-to-app'),
            access_token=os.environ.get('FYERS_ACCESS_TOKEN')
        ),
        'strategy': StrategyConfig(
            portfolio_value=float(os.environ.get('PORTFOLIO_VALUE', 1000000)),
            risk_per_trade_pct=float(os.environ.get('RISK_PER_TRADE', 1.0)),
            max_positions=int(os.environ.get('MAX_POSITIONS', 3)),
            min_gap_percentage=float(os.environ.get('MIN_GAP_PERCENTAGE', 0.5)),
            min_selling_pressure=float(os.environ.get('MIN_SELLING_PRESSURE', 40.0)),
            min_volume_ratio=float(os.environ.get('MIN_VOLUME_RATIO', 1.2)),
            min_confidence=float(os.environ.get('MIN_CONFIDENCE', 0.6)),
            stop_loss_pct=float(os.environ.get('STOP_LOSS_PCT', 1.5)),
            target_pct=float(os.environ.get('TARGET_PCT', 3.0))
        ),
        'trading': TradingConfig(
            market_start_hour=9,
            market_start_minute=15,
            market_end_hour=15,
            market_end_minute=30,
            signal_generation_end_hour=10,
            signal_generation_end_minute=30,
            monitoring_interval=5,  # Faster for scalping
            execution_delay=2  # Faster execution for scalping
        ),
        'breakout': BreakoutConfig(
            min_breakout_percentage=2.0,
            min_volume_multiplier=1.5,
            opening_range_minutes=15,
            risk_reward_ratio=2.0,
            max_positions_per_strategy=2
        ),
        'scalping': ScalpingConfig(
            min_bid_ask_imbalance_ratio=float(os.environ.get('SCALPING_MIN_IMBALANCE', 2.5)),
            min_volume_at_level=int(os.environ.get('SCALPING_MIN_VOLUME', 2000)),
            max_positions=int(os.environ.get('SCALPING_MAX_POSITIONS', 1)),
            position_size_percentage=float(os.environ.get('SCALPING_POSITION_SIZE', 0.15)),
            stop_loss_ticks=int(os.environ.get('SCALPING_STOP_TICKS', 3)),
            target_ticks=int(os.environ.get('SCALPING_TARGET_TICKS', 6)),
            max_hold_seconds=int(os.environ.get('SCALPING_MAX_HOLD', 45)),
            cooldown_seconds=int(os.environ.get('SCALPING_COOLDOWN', 120)),
            min_confidence=float(os.environ.get('SCALPING_MIN_CONFIDENCE', 0.80))
        ),
        'multi_strategy_scalping': MultiStrategyScalpingConfig(
            scalping_allocation=0.1,
            gap_up_allocation=0.5,
            breakout_allocation=0.4,
            max_total_positions=6,
            max_scalping_positions=1,
            max_gap_up_positions=3,
            max_breakout_positions=2,
            portfolio_stop_loss=4.0,
            daily_profit_target=3.0,
            allow_scalping_during_signals=bool(os.environ.get('ALLOW_SCALPING_DURING_SIGNALS', False)),
            cross_strategy_cooldown_minutes=int(os.environ.get('CROSS_STRATEGY_COOLDOWN', 5))
        )
    }


def authenticate_fyers_enhanced(config: Dict) -> bool:
    """Enhanced authentication that handles the scalping system requirements"""
    from main_enhanced import FyersAuthManager

    auth_manager = FyersAuthManager()
    access_token = auth_manager.get_valid_access_token()

    if access_token:
        config['fyers'].access_token = access_token
        logging.info("Enhanced Fyers authentication successful")
        return True
    else:
        logging.error("Enhanced Fyers authentication failed")
        return False


async def main_enhanced_scalping_system():
    """Main entry point for enhanced system with scalping"""
    try:
        # Load enhanced configuration
        config = load_enhanced_config()

        # Handle authentication
        if not authenticate_fyers_enhanced(config):
            print("Authentication failed. Exiting...")
            return

        # Initialize enhanced multi-strategy manager with scalping
        enhanced_system = EnhancedMultiStrategyWithScalping(
            config['fyers'],
            config['strategy'],
            config['trading'],
            config['breakout'],
            config['scalping'],
            config['multi_strategy_scalping']
        )

        await enhanced_system.run()

    except Exception as e:
        logging.error(f"Fatal error in enhanced scalping system: {e}")


async def test_scalping_components():
    """Test scalping components independently"""
    try:
        print("Testing Level II Scalping Components...")

        # Load configuration
        config = load_enhanced_config()

        if not authenticate_fyers_enhanced(config):
            print("Authentication failed for testing")
            return

        # Test enhanced Fyers service
        enhanced_fyers = EnhancedFyersService(config['fyers'])

        # Test symbols for Level II data
        test_symbols = ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS']

        print("Testing Level II market data...")
        for symbol in test_symbols:
            try:
                order_book = await enhanced_fyers.get_market_depth(symbol)
                if order_book:
                    print(f"✓ {symbol}: Bids={len(order_book.bids)}, Asks={len(order_book.asks)}, "
                          f"Spread={order_book.spread:.2f}")

                    # Test order book analysis
                    imbalance = enhanced_fyers.analyze_order_book_imbalance(order_book)
                    print(f"  Imbalance ratio: {imbalance['imbalance_ratio']:.2f}")

                    # Test support/resistance identification
                    levels = enhanced_fyers.identify_support_resistance_levels(order_book)
                    print(f"  Support levels: {len(levels['support_levels'])}, "
                          f"Resistance levels: {len(levels['resistance_levels'])}")
                else:
                    print(f"✗ {symbol}: No order book data")
            except Exception as e:
                print(f"✗ {symbol}: Error - {e}")

        # Test scalping strategy initialization
        print("\nTesting scalping strategy...")
        scalping_strategy = Level2ScalpingStrategy(
            enhanced_fyers,
            config['strategy'],
            config['trading'],
            config['scalping']
        )

        # Test signal generation (without execution)
        if scalping_strategy.is_scalping_time():
            signals = await scalping_strategy.signal_service.generate_scalping_signals(
                config['scalping']
            )
            print(f"Generated {len(signals)} scalping signals")

            for signal in signals[:3]:  # Show first 3
                print(f"  {signal.symbol}: {signal.signal_type}, "
                      f"Confidence: {signal.confidence:.2f}")
        else:
            print("Outside scalping hours")

        print("\nLevel II Scalping components test completed!")

    except Exception as e:
        print(f"Error testing scalping components: {e}")


def create_scalping_env_template():
    """Create environment template with scalping settings"""
    template = """
# Existing settings
FYERS_CLIENT_ID=your_client_id
FYERS_SECRET_KEY=your_secret_key
FYERS_ACCESS_TOKEN=your_token
PORTFOLIO_VALUE=1000000
RISK_PER_TRADE=1.0

# Scalping Strategy Settings
SCALPING_MIN_IMBALANCE=2.5
SCALPING_MIN_VOLUME=2000
SCALPING_MAX_POSITIONS=1
SCALPING_POSITION_SIZE=0.15
SCALPING_STOP_TICKS=3
SCALPING_TARGET_TICKS=6
SCALPING_MAX_HOLD=45
SCALPING_COOLDOWN=120
SCALPING_MIN_CONFIDENCE=0.80

# Multi-Strategy Coordination
ALLOW_SCALPING_DURING_SIGNALS=False
CROSS_STRATEGY_COOLDOWN=5
"""

    with open('.env.scalping.template', 'w') as f:
        f.write(template.strip())

    print("Created .env.scalping.template with scalping settings")


def main():
    """Enhanced main entry point with scalping options"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "scalping":
            print("Starting Enhanced Multi-Strategy System with Level II Scalping...")
            asyncio.run(main_enhanced_scalping_system())
        elif command == "test-scalping":
            print("Testing Level II Scalping Components...")
            asyncio.run(test_scalping_components())
        elif command == "create-scalping-env":
            create_scalping_env_template()
        elif command == "multi":
            print("Starting Standard Multi-Strategy System...")
            from main_enhanced import main_multi_strategy
            asyncio.run(main_multi_strategy())
        elif command == "single":
            print("Starting Gap-Up Short Strategy...")
            from main_enhanced import main_single_strategy
            asyncio.run(main_single_strategy())
        elif command == "auth":
            from main_enhanced import setup_auth_only
            setup_auth_only()
        else:
            print("Available commands:")
            print("  python main_enhanced_scalping.py scalping         - Run with Level II scalping")
            print("  python main_enhanced_scalping.py test-scalping    - Test scalping components")
            print("  python main_enhanced_scalping.py create-scalping-env - Create env template")
            print("  python main_enhanced_scalping.py multi            - Run standard multi-strategy")
            print("  python main_enhanced_scalping.py single           - Run gap-up strategy only")
            print("  python main_enhanced_scalping.py auth             - Setup authentication")
    else:
        print("🔧 Select enhanced trading mode:")
        print("1. Enhanced Multi-Strategy with Level II Scalping")
        print("2. Test Level II Scalping Components")
        print("3. Standard Multi-Strategy System")
        print("4. Single Strategy (Gap-Up Short only)")
        print("5. Setup Authentication")

        choice = input("\nEnter choice (1/2/3/4/5): ").strip()

        if choice == "1":
            print("Starting Enhanced Multi-Strategy System with Level II Scalping...")
            asyncio.run(main_enhanced_scalping_system())
        elif choice == "2":
            print("Testing Level II Scalping Components...")
            asyncio.run(test_scalping_components())
        elif choice == "3":
            print("Starting Standard Multi-Strategy System...")
            from main_enhanced import main_multi_strategy
            asyncio.run(main_multi_strategy())
        elif choice == "4":
            print("Starting Gap-Up Short Strategy...")
            from main_enhanced import main_single_strategy
            asyncio.run(main_single_strategy())
        elif choice == "5":
            from main_enhanced import setup_auth_only
            setup_auth_only()
        else:
            print("Invalid choice")


if __name__ == "__main__":
    main()