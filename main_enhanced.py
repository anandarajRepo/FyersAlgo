import asyncio
import logging
import sys
import os
import requests
import json
import hashlib
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

# Import Fyers API
from fyers_apiv3 import fyersModel

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


class FyersAuthManager:
    """Enhanced Fyers authentication manager with refresh token support"""

    def __init__(self):
        self.client_id = os.environ.get('FYERS_CLIENT_ID')
        self.secret_key = os.environ.get('FYERS_SECRET_KEY')
        self.redirect_uri = os.environ.get('FYERS_REDIRECT_URI', "https://trade.fyers.in/api-login/redirect-to-app")
        self.refresh_token = os.environ.get('FYERS_REFRESH_TOKEN')
        self.access_token = os.environ.get('FYERS_ACCESS_TOKEN')

    def save_to_env(self, key, value):
        """Save or update environment variable in .env file"""
        env_file = '.env'

        # Read existing .env file
        env_vars = {}
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        k, v = line.strip().split('=', 1)
                        env_vars[k] = v

        # Update the specific key
        env_vars[key] = value

        # Write back to .env file
        with open(env_file, 'w') as f:
            for k, v in env_vars.items():
                f.write(f"{k}={v}\n")

        # Update current environment
        os.environ[key] = value

    def generate_access_token_with_refresh(self, refresh_token):
        """Generate new access token using refresh token"""
        url = "https://api-t1.fyers.in/api/v3/validate-refresh-token"

        headers = {
            "Content-Type": "application/json"
        }

        data = {
            "grant_type": "refresh_token",
            "appIdHash": self.get_app_id_hash(),
            "refresh_token": refresh_token
        }

        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            response_data = response.json()

            if response_data.get('s') == 'ok' and 'access_token' in response_data:
                return response_data['access_token'], response_data.get('refresh_token')
            else:
                logging.error(f"Error refreshing token: {response_data.get('message', 'Unknown error')}")
                return None, None

        except Exception as e:
            logging.error(f"Exception while refreshing token: {e}")
            return None, None

    def get_app_id_hash(self):
        """Generate app_id_hash for API calls"""
        app_id = f"{self.client_id}:{self.secret_key}"
        return hashlib.sha256(app_id.encode()).hexdigest()

    def get_tokens_from_auth_code(self, auth_code):
        """Get both access and refresh tokens from auth code"""
        url = "https://api-t1.fyers.in/api/v3/validate-authcode"

        headers = {
            "Content-Type": "application/json"
        }

        data = {
            "grant_type": "authorization_code",
            "appIdHash": self.get_app_id_hash(),
            "code": auth_code
        }

        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            response_data = response.json()

            if response_data.get('s') == 'ok':
                return (response_data.get('access_token'),
                        response_data.get('refresh_token'))
            else:
                logging.error(f"Error getting tokens: {response_data.get('message', 'Unknown error')}")
                return None, None

        except Exception as e:
            logging.error(f"Exception while getting tokens: {e}")
            return None, None

    def is_token_valid(self, access_token):
        """Check if access token is still valid"""
        if not access_token:
            return False

        # Create a test Fyers model instance
        fyers = fyersModel.FyersModel(client_id=self.client_id, token=access_token)

        try:
            # Make a simple API call to test token validity
            profile = fyers.get_profile()
            return profile.get('s') == 'ok'
        except:
            return False

    def get_valid_access_token(self):
        """Get a valid access token, using refresh token if available"""

        # First, check if current access token is still valid
        if self.access_token and self.is_token_valid(self.access_token):
            logging.info("✅ Current access token is still valid")
            return self.access_token

        # Try to use refresh token if available
        if self.refresh_token:
            logging.info("🔄 Access token expired, trying to refresh...")
            new_access_token, new_refresh_token = self.generate_access_token_with_refresh(self.refresh_token)

            if new_access_token:
                logging.info("✅ Successfully refreshed access token")

                # Save new tokens
                self.save_to_env('FYERS_ACCESS_TOKEN', new_access_token)
                self.access_token = new_access_token

                if new_refresh_token:
                    self.save_to_env('FYERS_REFRESH_TOKEN', new_refresh_token)
                    self.refresh_token = new_refresh_token

                return new_access_token
            else:
                logging.warning("❌ Failed to refresh access token, need to re-authenticate")

        # If refresh failed or no refresh token, do full authentication
        return self.setup_full_authentication()

    def setup_full_authentication(self):
        """Complete authentication flow to get new tokens"""
        print("=== Fyers API Full Authentication Setup ===")

        if not all([self.client_id, self.secret_key]):
            print("❌ Missing CLIENT_ID or SECRET_KEY in environment variables")
            return None

        # Generate auth URL
        auth_url = FyersAuthHelper.generate_auth_url(self.client_id, self.redirect_uri)

        print(f"\n1. Open this URL: {auth_url}")
        print("2. Complete authorization and get the code")

        auth_code = input("\nEnter authorization code: ").strip()

        # Get both access and refresh tokens
        access_token, refresh_token = self.get_tokens_from_auth_code(auth_code)

        if access_token:
            print(f"\n=== Saving tokens to .env file ===")

            # Save all tokens to .env
            self.save_to_env('FYERS_CLIENT_ID', self.client_id)
            self.save_to_env('FYERS_SECRET_KEY', self.secret_key)
            self.save_to_env('FYERS_REDIRECT_URI', self.redirect_uri)
            self.save_to_env('FYERS_ACCESS_TOKEN', access_token)

            if refresh_token:
                self.save_to_env('FYERS_REFRESH_TOKEN', refresh_token)
                print(f"FYERS_REFRESH_TOKEN saved ✅")

            print(f"\n✅ Authentication successful!")
            print(f"Access Token: {access_token[:20]}...")
            if refresh_token:
                print(f"Refresh Token: {refresh_token[:20]}...")

            return access_token
        else:
            print("❌ Authentication failed!")
            return None


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
                     f"PnL: ₹{gap_up_perf['daily_pnl']:.2f}")
        logging.info(f"Breakout: {breakout_perf['active_positions']} positions, "
                     f"PnL: ₹{breakout_perf['daily_pnl']:.2f}")
        logging.info(f"Portfolio Daily PnL: ₹{self.daily_portfolio_pnl:.2f}")
        logging.info(f"Portfolio Total PnL: ₹{self.total_portfolio_pnl:.2f}")

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
    """Handle Fyers authentication with refresh token support"""
    auth_manager = FyersAuthManager()

    # Get valid access token (will auto-refresh if needed)
    access_token = auth_manager.get_valid_access_token()

    if access_token:
        # Update config with the valid token
        config['fyers'].access_token = access_token
        logging.info("✅ Fyers authentication successful")
        return True
    else:
        logging.error("❌ Fyers authentication failed")
        return False


async def main_multi_strategy():
    """Main entry point for multi-strategy system"""
    try:
        # Load configuration
        config = load_config()

        # Handle authentication with refresh token support
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

        # Handle authentication with refresh token support
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
    """Enhanced authentication setup with refresh token support"""
    print("=== Enhanced Fyers API Authentication Setup ===")

    # Check if we already have credentials in environment
    if os.environ.get('FYERS_CLIENT_ID') and os.environ.get('FYERS_SECRET_KEY'):
        print("Found existing credentials in environment")
        auth_manager = FyersAuthManager()
        access_token = auth_manager.get_valid_access_token()

        if access_token:
            print("✅ Authentication successful using existing/refreshed tokens!")
            return

    # Manual setup if no credentials or auth failed
    print("\n=== Manual Authentication Setup ===")
    client_id = input("Enter your Fyers Client ID: ").strip()
    secret_key = input("Enter your Fyers Secret Key: ").strip()
    redirect_uri = input("Enter Redirect URI (or press Enter for default): ").strip()

    if not redirect_uri:
        redirect_uri = "https://trade.fyers.in/api-login/redirect-to-app"

    # Update environment temporarily for this session
    os.environ['FYERS_CLIENT_ID'] = client_id
    os.environ['FYERS_SECRET_KEY'] = secret_key
    os.environ['FYERS_REDIRECT_URI'] = redirect_uri

    # Use the auth manager for enhanced authentication
    auth_manager = FyersAuthManager()
    access_token = auth_manager.setup_full_authentication()

    if access_token:
        print("\n✅ Enhanced authentication setup completed!")
        print("Refresh token has been saved for automatic token renewal.")
    else:
        print("❌ Authentication setup failed!")


def create_fyers_session():
    """Create authenticated Fyers session with refresh token support"""
    auth_manager = FyersAuthManager()
    access_token = auth_manager.get_valid_access_token()

    if access_token:
        client_id = os.environ.get('FYERS_CLIENT_ID')
        fyers = fyersModel.FyersModel(client_id=client_id, token=access_token)
        return fyers
    else:
        logging.error("❌ Failed to create Fyers session")
        return None


def main():
    """Main entry point with command options"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "multi":
            print("🚀 Starting Enhanced Multi-Strategy Trading System...")
            asyncio.run(main_multi_strategy())
        elif command == "single":
            print("📈 Starting Gap-Up Short Strategy...")
            asyncio.run(main_single_strategy())
        elif command == "auth":
            setup_auth_only()
        elif command == "test-auth":
            # Test authentication without running strategies
            config = load_config()
            if authenticate_fyers(config):
                print("✅ Authentication test successful!")
                # Test API call
                fyers = create_fyers_session()
                if fyers:
                    profile = fyers.get_profile()
                    print(f"Profile: {profile}")
            else:
                print("❌ Authentication test failed!")
        else:
            print("❓ Unknown command. Available options:")
            print("  python main_enhanced.py multi      - Run multi-strategy system")
            print("  python main_enhanced.py single     - Run gap-up short strategy only")
            print("  python main_enhanced.py auth       - Setup Fyers authentication")
            print("  python main_enhanced.py test-auth  - Test authentication")
    else:
        print("🔧 Select trading mode:")
        print("1. Multi-Strategy System (Gap-Up Short + Breakout)")
        print("2. Single Strategy (Gap-Up Short only)")
        print("3. Setup Authentication")
        print("4. Test Authentication")

        choice = input("\nEnter choice (1/2/3/4): ").strip()

        if choice == "1":
            print("🚀 Starting Enhanced Multi-Strategy Trading System...")
            asyncio.run(main_multi_strategy())
        elif choice == "2":
            print("📈 Starting Gap-Up Short Strategy...")
            asyncio.run(main_single_strategy())
        elif choice == "3":
            setup_auth_only()
        elif choice == "4":
            config = load_config()
            if authenticate_fyers(config):
                print("✅ Authentication test successful!")
                fyers = create_fyers_session()
                if fyers:
                    profile = fyers.get_profile()
                    print(f"Profile: {profile}")
            else:
                print("❌ Authentication test failed!")
        else:
            print("❌ Invalid choice")


if __name__ == "__main__":
    main()