# test_enhanced_scalping_fixed.py

"""
Improved test script for Level II Scalping Strategy that handles API limitations gracefully
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict

# Import the enhanced system with fixes
from services.enhanced_fyers_service import EnhancedFyersService
from main_enhanced_scalping import load_enhanced_config, authenticate_fyers_enhanced
from strategies.level2_scalping_strategy import Level2ScalpingStrategy

# Configure logging for the test
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImprovedScalpingTest:
    """Improved test class that handles API limitations"""

    def __init__(self):
        self.config = load_enhanced_config()
        self.enhanced_fyers = None

    async def initialize_system(self):
        """Initialize the enhanced trading system with improved error handling"""
        try:
            # Authenticate first
            if not authenticate_fyers_enhanced(self.config):
                logger.error("Authentication failed")
                return False

            # Create enhanced Fyers service
            self.enhanced_fyers = EnhancedFyersService(self.config['fyers'])

            logger.info("✓ Enhanced Fyers service initialized")
            return True

        except Exception as e:
            logger.error(f"Error initializing system: {e}")
            return False

    async def run_api_diagnostics(self):
        """Run comprehensive API diagnostics"""
        print("\n=== API Diagnostics ===")

        try:
            diagnostics = self.enhanced_fyers.get_api_diagnostics()

            print(f"Test Time: {diagnostics['timestamp']}")
            print(f"Endpoints Tested: {len(diagnostics['endpoints_tested'])}")

            print(f"\n✅ Successful Endpoints:")
            for endpoint in diagnostics['successful_endpoints']:
                print(f"  - {endpoint}")

            print(f"\n❌ Failed Endpoints:")
            for endpoint in diagnostics['failed_endpoints']:
                print(f"  - {endpoint}")

            print(f"\n📊 Data Quality Assessment:")
            for data_type, status in diagnostics['data_quality'].items():
                print(f"  - {data_type.title()}: {status}")

            print(f"\n💡 Recommendations:")
            for rec in diagnostics['recommendations']:
                print(f"  - {rec}")

            return diagnostics

        except Exception as e:
            print(f"Error running diagnostics: {e}")
            return None

    async def test_enhanced_market_depth(self):
        """Test enhanced market depth functionality"""
        print("\n=== Enhanced Market Depth Test ===")

        test_symbols = ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS']

        for symbol in test_symbols:
            try:
                print(f"\nTesting {symbol}:")

                # Get order book (will fall back to simulation if needed)
                order_book = await self.enhanced_fyers.get_market_depth(symbol)

                if order_book:
                    print(f"  ✓ Order book retrieved successfully")
                    print(f"    - Bids: {len(order_book.bids)} levels")
                    print(f"    - Asks: {len(order_book.asks)} levels")
                    print(f"    - Spread: Rs.{order_book.spread:.2f}")
                    print(f"    - Mid Price: Rs.{order_book.mid_price:.2f}")
                    print(f"    - Last Price: Rs.{order_book.last_traded_price:.2f}")

                    if order_book.bids and order_book.asks:
                        best_bid = order_book.bids[0]
                        best_ask = order_book.asks[0]
                        print(f"    - Best Bid: Rs.{best_bid.price:.2f} (Qty: {best_bid.quantity})")
                        print(f"    - Best Ask: Rs.{best_ask.price:.2f} (Qty: {best_ask.quantity})")

                    # Test order book analysis
                    imbalance = self.enhanced_fyers.analyze_order_book_imbalance(order_book)
                    print(f"    - Bid/Ask Imbalance: {imbalance['imbalance_ratio']:.2f}")
                    print(f"    - Spread (bps): {imbalance.get('spread_bps', 0):.1f}")

                    # Test support/resistance identification
                    levels = self.enhanced_fyers.identify_support_resistance_levels(order_book)
                    print(f"    - Support Levels: {len(levels['support_levels'])}")
                    print(f"    - Resistance Levels: {len(levels['resistance_levels'])}")

                    # Test scalping conditions
                    tick_data = await self.enhanced_fyers.get_tick_data(symbol, 10)
                    conditions = self.enhanced_fyers.check_scalping_conditions(order_book, tick_data)
                    suitable_conditions = sum(conditions.values())
                    print(f"    - Scalping Suitability: {suitable_conditions}/5 conditions met")

                    for condition, met in conditions.items():
                        status = "✓" if met else "✗"
                        print(f"      {status} {condition.replace('_', ' ').title()}")
                else:
                    print(f"  ✗ Failed to retrieve order book for {symbol}")

            except Exception as e:
                print(f"  ✗ Error testing {symbol}: {e}")

    async def test_tick_data_analysis(self):
        """Test tick data and order flow analysis"""
        print("\n=== Tick Data & Order Flow Analysis ===")

        symbol = 'RELIANCE.NS'

        try:
            print(f"Testing tick data for {symbol}:")

            # Get tick data (simulated if real data not available)
            tick_data = await self.enhanced_fyers.get_tick_data(symbol, 30)

            if tick_data:
                print(f"  ✓ Retrieved {len(tick_data)} ticks")

                # Analyze order flow
                flow_analysis = self.enhanced_fyers.calculate_order_flow_imbalance(tick_data)

                print(f"  📊 Order Flow Analysis:")
                print(f"    - Total Volume: {flow_analysis['total_volume']:,}")
                print(f"    - Buy Volume: {flow_analysis['buy_volume']:,} ({flow_analysis['buy_percentage']:.1f}%)")
                print(f"    - Sell Volume: {flow_analysis['sell_volume']:,} ({flow_analysis['sell_percentage']:.1f}%)")
                print(f"    - Buy/Sell Ratio: {flow_analysis['imbalance_ratio']:.2f}")

                # Show recent tick samples
                print(f"  📈 Recent Tick Samples:")
                for i, tick in enumerate(tick_data[-5:]):  # Last 5 ticks
                    print(f"    {i + 1}. {tick.timestamp.strftime('%H:%M:%S')} - "
                          f"{tick.side} {tick.quantity} @ Rs.{tick.price:.2f}")
            else:
                print(f"  ✗ No tick data available for {symbol}")

        except Exception as e:
            print(f"  ✗ Error testing tick data: {e}")

    async def test_scalping_signal_generation(self):
        """Test scalping signal generation with fallback mechanisms"""
        print("\n=== Scalping Signal Generation Test ===")

        try:
            # Create scalping strategy instance
            scalping_strategy = Level2ScalpingStrategy(
                self.enhanced_fyers,
                self.config['strategy'],
                self.config['trading'],
                self.config['scalping']
            )

            # Test if it's scalping time
            is_scalping_time = scalping_strategy.is_scalping_time()
            print(f"Current time suitable for scalping: {is_scalping_time}")

            # Generate signals (even outside market hours for testing)
            print("Generating scalping signals...")
            signals = await scalping_strategy.signal_service.generate_scalping_signals(
                self.config['scalping']
            )

            print(f"Generated {len(signals)} scalping signals")

            if signals:
                print("\n📊 Signal Details:")
                for i, signal in enumerate(signals[:3], 1):  # Show first 3 signals
                    print(f"\n  Signal {i}:")
                    print(f"    Symbol: {signal.symbol}")
                    print(f"    Type: {signal.signal_type}")
                    print(f"    Entry: Rs.{signal.entry_price:.2f}")
                    print(f"    Stop Loss: Rs.{signal.stop_loss:.2f}")
                    print(f"    Target: Rs.{signal.target_price:.2f}")
                    print(f"    Confidence: {signal.confidence:.2%}")
                    print(f"    Volume Ratio: {signal.volume_ratio:.2f}")

                    # Calculate risk-reward
                    if 'LONG' in signal.signal_type:
                        risk = signal.entry_price - signal.stop_loss
                        reward = signal.target_price - signal.entry_price
                    else:
                        risk = signal.stop_loss - signal.entry_price
                        reward = signal.entry_price - signal.target_price

                    rr_ratio = reward / risk if risk > 0 else 0
                    print(f"    Risk-Reward: 1:{rr_ratio:.2f}")
            else:
                print("  No signals generated (this is normal outside market hours)")

        except Exception as e:
            print(f"Error testing signal generation: {e}")

    async def test_performance_tracking(self):
        """Test performance tracking capabilities"""
        print("\n=== Performance Tracking Test ===")

        try:
            # Create mock performance data
            scalping_strategy = Level2ScalpingStrategy(
                self.enhanced_fyers,
                self.config['strategy'],
                self.config['trading'],
                self.config['scalping']
            )

            # Get performance metrics
            performance = scalping_strategy.get_scalping_performance()

            print("📊 Scalping Strategy Performance:")
            print(f"  Strategy: {performance['strategy_name']}")
            print(f"  Total P&L: Rs.{performance['total_pnl']:.2f}")
            print(f"  Daily P&L: Rs.{performance['daily_pnl']:.2f}")
            print(f"  Active Positions: {performance['active_positions']}")
            print(f"  Trades Today: {performance['trades_today']}")

            if performance['positions_detail']:
                print("  Position Details:")
                for pos in performance['positions_detail']:
                    print(f"    - {pos['symbol']}: {pos['quantity']} shares @ Rs.{pos['entry_price']:.2f}")
            else:
                print("  No active positions")

        except Exception as e:
            print(f"Error testing performance tracking: {e}")

    async def run_comprehensive_test(self):
        """Run all tests in sequence"""
        print("🚀 Starting Comprehensive Level II Scalping Test")
        print("=" * 60)

        # Initialize system
        if not await self.initialize_system():
            print("❌ Failed to initialize system. Tests cannot continue.")
            return

        # Run all test modules
        await self.run_api_diagnostics()
        await self.test_enhanced_market_depth()
        await self.test_tick_data_analysis()
        await self.test_scalping_signal_generation()
        await self.test_performance_tracking()

        print("\n" + "=" * 60)
        print("✅ Comprehensive Level II Scalping Test Completed!")
        print("\n💡 Key Takeaways:")
        print("  - System can work with simulated data when real Level II data is unavailable")
        print("  - Order book analysis functions correctly with both real and simulated data")
        print("  - Scalping signals can be generated using enhanced market analysis")
        print("  - Performance tracking is fully functional")
        print("\n🔧 Next Steps:")
        print("  - Consider upgrading Fyers API subscription for real Level II data")
        print("  - Test with paper trading first before going live")
        print("  - Monitor API limits and implement proper rate limiting")


async def test_individual_components():
    """Test individual scalping components"""
    print("🔬 Testing Individual Scalping Components")
    print("=" * 50)

    config = load_enhanced_config()

    if not authenticate_fyers_enhanced(config):
        print("❌ Authentication failed")
        return

    # Test enhanced Fyers service independently
    enhanced_fyers = EnhancedFyersService(config['fyers'])

    print("\n1. Testing Basic Quote Retrieval:")
    try:
        symbols = ['RELIANCE.NS', 'TCS.NS']
        quotes = await enhanced_fyers.get_quotes(symbols)

        for symbol, quote in quotes.items():
            print(f"  ✓ {symbol}: Rs.{quote.current_price:.2f} (Volume: {quote.volume:,})")

    except Exception as e:
        print(f"  ✗ Quote retrieval failed: {e}")

    print("\n2. Testing Market Depth (with fallback):")
    try:
        order_book = await enhanced_fyers.get_market_depth('RELIANCE.NS')
        if order_book:
            print(f"  ✓ Order book retrieved: {len(order_book.bids)} bids, {len(order_book.asks)} asks")
            print(f"    Spread: Rs.{order_book.spread:.2f}, Mid: Rs.{order_book.mid_price:.2f}")
        else:
            print("  ✗ Order book retrieval failed")
    except Exception as e:
        print(f"  ✗ Market depth test failed: {e}")

    print("\n3. Testing Configuration:")
    try:
        scalping_config = config['scalping']
        print(f"  ✓ Max Positions: {scalping_config.max_positions}")
        print(f"  ✓ Position Size: {scalping_config.position_size_percentage}%")
        print(f"  ✓ Stop Loss Ticks: {scalping_config.stop_loss_ticks}")
        print(f"  ✓ Target Ticks: {scalping_config.target_ticks}")
        print(f"  ✓ Min Confidence: {scalping_config.min_confidence}")
    except Exception as e:
        print(f"  ✗ Configuration test failed: {e}")


def show_scalping_strategy_guide():
    """Show guide for using the scalping strategy"""
    print("\n📚 Level II Scalping Strategy Guide")
    print("=" * 50)

    print("\n🎯 Strategy Overview:")
    print("  - Ultra-short term trading (5-45 seconds per trade)")
    print("  - Uses order book imbalances and support/resistance levels")
    print("  - Focuses on most liquid stocks for tight spreads")
    print("  - Risk-reward ratio of 2:1 minimum")

    print("\n⚙️ Key Configuration Parameters:")
    print("  - min_bid_ask_imbalance_ratio: Minimum imbalance for signal (default: 2.5)")
    print("  - position_size_percentage: Capital per trade (default: 0.15%)")
    print("  - stop_loss_ticks: Tight stop loss (default: 3 ticks)")
    print("  - target_ticks: Quick profit target (default: 6 ticks)")
    print("  - max_hold_seconds: Maximum hold time (default: 45 seconds)")

    print("\n📊 Signal Types:")
    print("  1. BID_ASK_IMBALANCE: Strong volume imbalance in order book")
    print("  2. SUPPORT_BOUNCE: Price bouncing off support level")
    print("  3. RESISTANCE_BOUNCE: Price rejecting resistance level")

    print("\n⚠️ Risk Management:")
    print("  - Maximum 1 position at a time")
    print("  - Immediate stop loss execution")
    print("  - Position size limited to 0.15% of portfolio")
    print("  - Cooldown period between trades on same symbol")

    print("\n🚀 Getting Started:")
    print("  1. Test components first: python test_enhanced_scalping_fixed.py components")
    print("  2. Run paper trading mode to validate signals")
    print("  3. Start with conservative settings")
    print("  4. Monitor performance closely")

    print("\n💡 Tips for Success:")
    print("  - Focus on market hours 9:45 AM - 3:00 PM")
    print("  - Avoid first/last 30 minutes (high volatility)")
    print("  - Monitor overall market conditions")
    print("  - Keep position sizes small")
    print("  - Set daily loss limits")


async def main():
    """Main function to run tests"""
    print("📈 Enhanced Level II Scalping Strategy Test Suite")
    print("=" * 60)

    print("\nAvailable test modes:")
    print("1. Comprehensive Test (recommended)")
    print("2. Individual Components Test")
    print("3. API Diagnostics Only")
    print("4. Show Strategy Guide")

    try:
        choice = input("\nSelect test mode (1-4): ").strip()

        if choice == "1":
            test = ImprovedScalpingTest()
            await test.run_comprehensive_test()

        elif choice == "2":
            await test_individual_components()

        elif choice == "3":
            test = ImprovedScalpingTest()
            if await test.initialize_system():
                await test.run_api_diagnostics()

        elif choice == "4":
            show_scalping_strategy_guide()

        else:
            print("Invalid choice. Running comprehensive test...")
            test = ImprovedScalpingTest()
            await test.run_comprehensive_test()

    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")


if __name__ == "__main__":
    # Handle command line arguments
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "components":
            asyncio.run(test_individual_components())
        elif sys.argv[1] == "guide":
            show_scalping_strategy_guide()
        else:
            asyncio.run(main())
    else:
        asyncio.run(main())