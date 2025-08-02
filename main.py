import asyncio
import logging
import sys
import os
from typing import Dict
from config.settings import FyersConfig, StrategyConfig, TradingConfig
from utils.auth_helper import FyersAuthHelper
from main_strategy import GapUpShortStrategy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_strategy.log'),
        logging.StreamHandler()
    ]
)


def load_config() -> Dict:
    """Load configuration from environment or config file"""
    # In production, load from environment variables or config file
    return {
        'fyers': FyersConfig(
            client_id=os.environ.get('fyers_client_id'),
            secret_key=os.environ.get('fyers_secret_key'),
            redirect_uri=os.environ.get('fyers_redirect_uri'),
            access_token=os.environ.get('fyers_access_token')
        ),
        'strategy': StrategyConfig(
            portfolio_value=10000,
            risk_per_trade_pct=1.0,
            max_positions=3,
            min_gap_percentage=0.5,
            min_selling_pressure=40.0,
            min_volume_ratio=1.2,
            min_confidence=0.6,
            stop_loss_pct=1.5,
            target_pct=3.0
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
            print("Save this token for future use!")
            return True
        else:
            print("Authentication failed")
            return False

    return True


async def main():
    """Main entry point"""
    try:
        # Load configuration
        config = load_config()

        # Handle authentication
        if not authenticate_fyers(config):
            print("Authentication failed. Exiting...")
            return

        # Initialize and run strategy
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
        print(f"\n=== Configuration for your main.py ===")
        print(f"client_id: '{client_id}'")
        print(f"secret_key: '{secret_key}'")
        print(f"redirect_uri: '{redirect_uri}'")
        print(f"access_token: '{access_token}'")
    else:
        print("Authentication failed!")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "auth":
        setup_auth_only()
    else:
        asyncio.run(main())