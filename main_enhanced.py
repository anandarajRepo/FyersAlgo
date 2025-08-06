import asyncio
import logging
import sys
import os
from typing import Dict
from dotenv import load_dotenv

# Import configurations
from config.settings import FyersConfig, StrategyConfig, TradingConfig
from config.breakout_settings import BreakoutConfig, MultiStrategyConfig

# Import utilities
from utils.auth_helper import FyersAuthHelper

# Import services
from services.fyers_service import FyersService
from services.market_timing_service import MarketTimingService

# Import strategies
from main_strategy import GapUpShortStrategy
from strategies.open_breakout_strategy import OpenBreakoutStrategy

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_strategy.log'),
        logging.StreamHandler()
    ]
)


class EnhancedMultiStrategyManager:
    """Enhanced strategy manager supporting multiple strategies"""

    def __init__(self, fyers_config, strategy_config, trading_config, breakout_config):
        # Initialize services
        self.fyers_service = FyersService(fyers_config)
        self.timing_service = MarketTimingService(trading_config)

        # Configuration
        self.strategy_config = strategy_config
        self.trading_config = trading_config
        self.breakout_config = breakout_config

        # Strategy instances
        self.gap_up_strategy = GapUpShortStrategy(fyers_config, strategy_config, trading_config)
        self.breakout_strategy = OpenBreakoutStrategy(
            self.fyers_service, strategy_config, trading_config, breakout_config
        )

        # Performance tracking
        self.total_portfolio_pnl = 0.0
        self.daily_portfolio_pnl = 0.0

    async def initialize(self) -> bool:
        """Initialize all strategies"""
        try:
            # Verify connections
            if not await self.gap_up_strategy.initialize():
                logging.error("Failed to initialize gap-up strategy")
                return False

            logging.info("Multi-strategy manager initialized successfully")
            return True

        except Exception as e:
            logging.error(f"Multi-strategy initialization failed: {e}")
            return False

    async def run_all_strategies(self) -> None:
        """Run all strategies in parallel"""
        try:
            # Check trading hours
            if not self.timing_service.is_trading_time():
                logging.info("Outside trading hours, sleeping...")
                await asyncio.sleep(300)
                return

            # Run strategies concurrently
            await asyncio.gather(
                self.gap_up_strategy.run_strategy_cycle(),
                self.breakout_strategy.run_breakout_cycle(),
                return_exceptions=True
            )

            # Update portfolio performance
            self._update_portfolio_performance()

            # Log combined performance
            self._log_portfolio_status()

        except Exception as e:
            logging.error(f"Error running multi-strategy: {e}")

    def _update_portfolio_performance(self) -> None:
        """Update overall portfolio performance"""
        gap_up_perf = self.gap_up_strategy.get_performance_summary()
        breakout_perf = self.breakout_strategy.get_breakout_performance()

        self.total_portfolio_pnl = gap_up_perf['total_pnl'] + breakout_perf['total_pnl']
        self.daily_portfolio_pnl = gap_up_perf['daily_pnl'] + breakout_perf['daily_pnl']

    def _log_portfolio_status(self) -> None:
        """Log overall portfolio status"""
        gap_up_perf = self.gap_up_strategy.get_performance_summary()
        breakout_perf = self.breakout_strategy.get_breakout_performance()

        total_positions = gap_up_perf['active_positions'] + breakout_perf['active_positions']

        logging.info(f"=== PORTFOLIO STATUS ===")
        logging.info(f"Total Positions: {total_positions}")
        logging.info(f"Gap-Up Short: {gap_up_perf['active_positions']} positions, "
                     f"PnL: Rs.{gap_up_perf['daily_pnl']:.2f}")
        logging.info(f"Breakout: {breakout_perf['active_positions']} positions, "
                     f"PnL: Rs.{breakout_perf['daily_pnl']:.2f}")
        logging.info(f"Portfolio Daily PnL: Rs.{self.daily_portfolio_pnl:.2f}")
        logging.info(f"Portfolio Total PnL: Rs.{self.total_portfolio_pnl:.2f}")

    async def run(self) -> None:
        """Main multi-strategy execution loop"""
        logging.info("Starting Enhanced Multi-Strategy Trading System")

        if not await self.initialize():
            logging.error("Multi-strategy initialization failed")
            return

        try:
            while True:
                await self.run_all_strategies()

                # Sleep until next cycle
                await asyncio.sleep(self.trading_config.monitoring_interval)

        except KeyboardInterrupt:
            logging.info("Multi-strategy system stopped by user")
        except Exception as e:
            logging.error(f"Fatal error in multi-strategy: {e}")


def load_config() -> Dict:
    """Load configuration from environment or config file"""
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
            monitoring_interval=30,
            execution_delay=5
        ),
        'breakout': BreakoutConfig(
            min_breakout_percentage=2.0,
            min_volume_multiplier=1.5,
            opening_range_minutes=15,
            risk_reward_ratio=2.0,
            max_positions_per_strategy=2
        ),
        'multi_strategy': MultiStrategyConfig(
            gap_up_allocation=0.6,
            breakout_allocation=0.4,
            max_total_positions=5,
            max_gap_up_positions=3,
            max_breakout_positions=2,
            portfolio_stop_loss=5.0,
            daily_profit_target=3.0
        )
    }


def authenticate_fyers(config: Dict) -> bool:
    """Handle Fyers authentication"""
    fyers_config = config['fyers']

    if not fyers_config.access_token:
        print("No access token found. Starting authentication...")

        # Generate auth URL
        auth_url = FyersAuthHelper.generate_auth_url(
            fyers_config.client_id,
            fyers_config.redirect_uri
        )

        print(f"\n1. Open this URL in your browser: {auth_url}")
        print("2. Login and authorize the application")
        print("3. Copy the authorization code from the redirect URL")

        auth_code = input("\nEnter the authorization code: ").strip()

        # Generate access token
        access_token = FyersAuthHelper.generate_access_token(
            fyers_config.client_id,
            fyers_config.secret_key,
            auth_code
        )

        if access_token:
            fyers_config.access_token = access_token
            print(f"Access token generated: {access_token}")
            print("💡 Save this to your .env file as FYERS_ACCESS_TOKEN={access_token}")
            return True
        else:
            print("Authentication failed")
            return False

    return True


async def main_multi_strategy():
    """Main entry point for multi-strategy system"""
    try:
        # Load configuration
        config = load_config()

        # Handle authentication
        if not authenticate_fyers(config):
            print("Authentication failed. Exiting...")
            return

        # Initialize multi-strategy manager
        multi_strategy = EnhancedMultiStrategyManager(
            config['fyers'],
            config['strategy'],
            config['trading'],
            config['breakout']
        )

        await multi_strategy.run()

    except Exception as e:
        logging.error(f"Fatal error in multi-strategy: {e}")


async def main_single_strategy():
    """Main entry point for single gap-up strategy"""
    try:
        # Load configuration
        config = load_config()

        # Handle authentication
        if not authenticate_fyers(config):
            print("Authentication failed. Exiting...")
            return

        # Initialize and run single strategy
        from main_strategy import GapUpShortStrategy
        strategy = GapUpShortStrategy(
            config['fyers'],
            config['strategy'],
            config['trading']
        )

        await strategy.run()

    except Exception as e:
        logging.error(f"Fatal error: {e}")


def setup_auth_only():
    """Standalone authentication setup"""
    print("=== Fyers API Authentication Setup ===")

    client_id = input("Enter your Fyers Client ID: ").strip()
    secret_key = input("Enter your Fyers Secret Key: ").strip()
    redirect_uri = input("Enter Redirect URI (or press Enter for default): ").strip()

    if not redirect_uri:
        redirect_uri = "https://trade.fyers.in/api-login/redirect-to-app"

    # Generate auth URL
    auth_url = FyersAuthHelper.generate_auth_url(client_id, redirect_uri)

    print(f"\n1. Open this URL: {auth_url}")
    print("2. Complete authorization and get the code")

    auth_code = input("\nEnter authorization code: ").strip()

    # Generate token
    access_token = FyersAuthHelper.generate_access_token(client_id, secret_key, auth_code)

    if access_token:
        print(f"\n=== Add these to your .env file ===")
        print(f"FYERS_CLIENT_ID={client_id}")
        print(f"FYERS_SECRET_KEY={secret_key}")
        print(f"FYERS_REDIRECT_URI={redirect_uri}")
        print(f"FYERS_ACCESS_TOKEN={access_token}")
        print(f"\n✅ Authentication successful!")
    else:
        print("❌ Authentication failed!")


def main():
    """Main entry point with command options"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "multi":
            print("🚀 Starting Multi-Strategy Trading System...")
            asyncio.run(main_multi_strategy())
        elif command == "single":
            print("📈 Starting Gap-Up Short Strategy...")
            asyncio.run(main_single_strategy())
        elif command == "auth":
            setup_auth_only()
        else:
            print("❓ Unknown command. Available options:")
            print("  python main_enhanced.py multi   - Run multi-strategy system")
            print("  python main_enhanced.py single  - Run gap-up short strategy only")
            print("  python main_enhanced.py auth    - Setup Fyers authentication")
    else:
        print("🔧 Select trading mode:")
        print("1. Multi-Strategy System (Gap-Up Short + Breakout)")
        print("2. Single Strategy (Gap-Up Short only)")
        print("3. Setup Authentication")

        choice = input("\nEnter choice (1/2/3): ").strip()

        if choice == "1":
            print("🚀 Starting Multi-Strategy Trading System...")
            asyncio.run(main_multi_strategy())
        elif choice == "2":
            print("📈 Starting Gap-Up Short Strategy...")
            asyncio.run(main_single_strategy())
        elif choice == "3":
            setup_auth_only()
        else:
            print("❌ Invalid choice")


if __name__ == "__main__":
    main()