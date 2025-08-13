# examples/scalping_usage_example.py

"""
Example usage of Level II Scalping Strategy
This script demonstrates how to integrate and use the scalping strategy
"""

import asyncio
import logging
from datetime import datetime

# Import the enhanced system
from main_enhanced_scalping import EnhancedMultiStrategyWithScalping, load_enhanced_config
from config.scalping_settings import ScalpingConfig

# Configure logging for the example
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScalpingExample:
    """Example class showing scalping strategy usage"""

    def __init__(self):
        self.config = load_enhanced_config()
        self.system = None

    async def initialize_system(self):
        """Initialize the enhanced trading system"""
        try:
            # Create the enhanced multi-strategy system
            self.system = EnhancedMultiStrategyWithScalping(
                self.config['fyers'],
                self.config['strategy'],
                self.config['trading'],
                self.config['breakout'],
                self.config['scalping'],
                self.config['multi_strategy_scalping']
            )

            # Initialize all components
            success = await self.system.initialize()
            if success:
                logger.info("✓ Enhanced system with scalping initialized successfully")
                return True
            else:
                logger.error("✗ Failed to initialize enhanced system")
                return False

        except Exception as e:
            logger.error(f"Error initializing system: {e}")
            return False

    async def demo_level2_data_analysis(self):
        """Demonstrate Level II data analysis capabilities"""
        print("\n=== Level II Data Analysis Demo ===")

        # Sample symbols for demonstration
        demo_symbols = ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS']

        for symbol in demo_symbols:
            try:
                print(f"\nAnalyzing {symbol}:")

                # Get order book data
                order_book = await self.system.fyers_service.get_market_depth(symbol)

                if order_book:
                    print(f"  ✓ Order book depth: {len(order_book.bids)} bids, {len(order_book.asks)} asks")
                    print(f"  ✓ Spread: Rs.{order_book.spread:.2f}")
                    print(f"  ✓ Mid price: Rs.{order_book.mid_price:.2f}")

                    # Analyze imbalance
                    imbalance = self.system.fyers_service.analyze_order_book_imbalance(order_book)
                    print(f"  ✓ Bid/Ask imbalance ratio: {imbalance['imbalance_ratio']:.2f}")

                    # Identify key levels
                    levels = self.system.fyers_service.identify_support_resistance_levels(order_book)
                    print(f"  ✓ Support levels: {len(levels['support_levels'])}")
                    print(f"  ✓ Resistance levels: {len(levels['resistance_levels'])}")

                    # Check scalping conditions
                    conditions = self.system.fyers_service.check_scalping_conditions(order_book, [])
                    suitable = sum(conditions.values())
                    print(f"  ✓ Scalping suitability: {suitable}/5 conditions met")

                else:
                    print(f"  ✗ No order book data available for {symbol}")

            except Exception as e:
                print(f"  ✗ Error analyzing {symbol}: {e}")

    async def demo_signal_generation(self):
        """Demonstrate scalping signal generation"""
        print("\n=== Scalping Signal Generation Demo ===")

        try:
            # Generate scalping signals
            signals = await self.system.scalping_strategy.signal_service.generate_scalping_signals(
                self.config['scalping']
            )

            print(f"Generated {len(signals)} scalping signals")

            for i, signal in enumerate(signals[:3]):  # Show first 3 signals
                print(f"\nSignal {i + 1}:")
                print(f"  Symbol: {signal.symbol}")
                print(f"  Type: {signal.signal_type}")
                print(f"  Entry: Rs.{signal.entry_price:.2f}")
                print(f"  Stop Loss: Rs.{signal.stop_loss:.2f}")
                print(f"  Target: Rs.{signal.target_price:.2f}")
                print(f"  Confidence: {signal.confidence:.2f}")
                print(f"  Volume Ratio: {signal.volume_ratio:.2f}")

                # Calculate risk-reward
                if 'LONG' in signal.signal_type:
                    risk = signal.entry_price - signal.stop_loss
                    reward = signal.target_price - signal.entry_price
                else:
                    risk = signal.stop_loss - signal.entry_price
                    reward = signal.entry_price - signal.target_price

                rr_ratio = reward / risk if risk > 0 else 0
                print(f"  Risk-Reward: 1:{rr_ratio:.2f}")

        except Exception as e:
            print(f"Error generating signals: {e}")

    async def demo_strategy_coordination(self):
        """Demonstrate strategy coordination features"""
        print("\n=== Strategy Coordination Demo ===")

        # Show current strategy status
        gap_up_positions = len(self.system.gap_up_strategy.positions)
        breakout_positions = len(self.system.breakout_strategy.positions)
        scalping_positions = len(self.system.scalping_strategy.positions)

        print(f"Current positions:")
        print(f"  Gap-Up Strategy: {gap_up_positions}")
        print(f"  Breakout Strategy: {breakout_positions}")
        print(f"  Scalping Strategy: {scalping_positions}")

        # Check if scalping is allowed
        scalping_allowed = self.system._should_allow_scalping()
        print(f"\nScalping currently allowed: {scalping_allowed}")

        # Show coordination settings
        config = self.config['multi_strategy_scalping']
        print(f"\nCoordination settings:")
        print(f"  Allow scalping during signals: {config.allow_scalping_during_signals}")
        print(f"  Cross-strategy cooldown: {config.cross_strategy_cooldown_minutes} minutes")
        print(f"  Max total positions: {config.max_total_positions}")

    async def demo_performance_tracking(self):
        """Demonstrate performance tracking"""
        print("\n=== Performance Tracking Demo ===")

        # Get comprehensive performance data
        performance = self.system.get_comprehensive_performance()

        print("Portfolio Summary:")
        portfolio = performance['portfolio_summary']
        print(f"  Total P&L: Rs.{portfolio['total_pnl']:.2f}")
        print(f"  Daily P&L: Rs.{portfolio['daily_pnl']:.2f}")
        print(f"  Total Positions: {portfolio['total_positions']}")
        print(f"  Active Strategies: {portfolio['strategies_active']}")

        print("\nStrategy Breakdown:")
        strategies = performance['strategy_breakdown']
        for strategy_name, stats in strategies.items():
            print(f"  {strategy_name.title()}:")
            print(f"    Positions: {stats['active_positions']}")
            print(f"    Daily P&L: Rs.{stats['daily_pnl']:.2f}")
            if 'trades_today' in stats:
                print(f"    Trades Today: {stats['trades_today']}")

        print("\nRisk Metrics:")
        risk_metrics = performance['risk_metrics']
        print(f"  Position Distribution: {risk_metrics['position_distribution']}")
        if 'scalping_metrics' in risk_metrics:
            scalping = risk_metrics['scalping_metrics']
            print(f"  Scalping Frequency: {scalping['scalping_frequency']}")
            print(f"  Avg Hold Time: {scalping['avg_hold_time']}")

    async def run_demo(self):
        """Run the complete demonstration"""
        print("🔄 Starting Level II Scalping Strategy Demo")
        print("=" * 50)

        # Initialize system
        if not await self.initialize_system():
            print("❌ Failed to initialize system. Demo cannot continue.")
            return

        # Run demonstration modules
        await self.demo_level2_data_analysis()
        await self.demo_signal_generation()
        await self.demo_strategy_coordination()
        await self.demo_performance_tracking()

        print("\n✅ Level II Scalping Strategy Demo Completed!")
        print("=" * 50)


async def run_live_scalping_example():
    """Example of running the scalping strategy live (for a short period)"""
    print("🚀 Starting Live Scalping Example (10 minutes)")

    try:
        # Load configuration
        config = load_enhanced_config()

        # Create enhanced system
        system = EnhancedMultiStrategyWithScalping(
            config['fyers'],
            config['strategy'],
            config['trading'],
            config['breakout'],
            config['scalping'],
            config['multi_strategy_scalping']
        )

        # Initialize
        if not await system.initialize():
            print("❌ Failed to initialize system")
            return

        print("✅ System initialized. Running for 10 minutes...")

        # Run for 10 minutes as example
        import time
        start_time = time.time()
        cycle_count = 0

        while time.time() - start_time < 600:  # 10 minutes
            cycle_count += 1
            print(f"\n--- Cycle {cycle_count} ---")

            # Run one strategy cycle
            await system.run_all_strategies_with_scalping()

            # Show quick status
            scalping_perf = system.scalping_strategy.get_scalping_performance()
            print(f"Scalping: {scalping_perf['active_positions']} positions, "
                  f"{scalping_perf['trades_today']} trades today")

            # Sleep for next cycle
            await asyncio.sleep(10)  # 10 seconds between cycles

        print("\n🏁 Live scalping example completed!")

        # Final performance summary
        final_performance = system.get_comprehensive_performance()
        print("\nFinal Performance Summary:")
        print(f"Total P&L: Rs.{final_performance['portfolio_summary']['total_pnl']:.2f}")

        scalping_stats = final_performance['strategy_breakdown']['level2_scalping']
        print(f"Scalping Trades: {scalping_stats.get('trades_today', 0)}")
        print(f"Scalping P&L: Rs.{scalping_stats['daily_pnl']:.2f}")

    except KeyboardInterrupt:
        print("\n⏹️ Live example stopped by user")
    except Exception as e:
        print(f"❌ Error in live example: {e}")


class ScalpingConfigurationHelper:
    """Helper class for configuring scalping parameters"""

    @staticmethod
    def create_conservative_config() -> ScalpingConfig:
        """Create conservative scalping configuration"""
        return ScalpingConfig(
            min_bid_ask_imbalance_ratio=3.0,  # Higher threshold
            min_volume_at_level=5000,  # More volume required
            max_positions=1,  # Single position only
            position_size_percentage=0.1,  # Smaller position size
            stop_loss_ticks=2,  # Tighter stop
            target_ticks=6,  # Same target (3:1 RR)
            max_hold_seconds=30,  # Shorter hold time
            cooldown_seconds=180,  # Longer cooldown
            min_confidence=0.85  # Higher confidence required
        )

    @staticmethod
    def create_aggressive_config() -> ScalpingConfig:
        """Create aggressive scalping configuration"""
        return ScalpingConfig(
            min_bid_ask_imbalance_ratio=2.0,  # Lower threshold
            min_volume_at_level=1000,  # Less volume required
            max_positions=2,  # Multiple positions
            position_size_percentage=0.25,  # Larger position size
            stop_loss_ticks=4,  # Wider stop
            target_ticks=6,  # Same target (1.5:1 RR)
            max_hold_seconds=60,  # Longer hold time
            cooldown_seconds=60,  # Shorter cooldown
            min_confidence=0.70  # Lower confidence threshold
        )

    @staticmethod
    def analyze_config_impact(config: ScalpingConfig) -> dict:
        """Analyze the impact of configuration settings"""
        analysis = {
            'risk_level': 'Unknown',
            'expected_frequency': 'Unknown',
            'capital_efficiency': 'Unknown',
            'recommendations': []
        }

        # Analyze risk level
        risk_factors = []
        if config.position_size_percentage > 0.2:
            risk_factors.append('High position size')
        if config.stop_loss_ticks < 3:
            risk_factors.append('Very tight stops')
        if config.max_positions > 1:
            risk_factors.append('Multiple positions')
        if config.min_confidence < 0.75:
            risk_factors.append('Lower confidence threshold')

        if len(risk_factors) >= 3:
            analysis['risk_level'] = 'High'
        elif len(risk_factors) >= 1:
            analysis['risk_level'] = 'Medium'
        else:
            analysis['risk_level'] = 'Low'

        # Analyze expected frequency
        frequency_factors = 0
        if config.min_bid_ask_imbalance_ratio <= 2.5:
            frequency_factors += 1
        if config.min_confidence <= 0.8:
            frequency_factors += 1
        if config.cooldown_seconds <= 120:
            frequency_factors += 1
        if config.min_volume_at_level <= 2000:
            frequency_factors += 1

        if frequency_factors >= 3:
            analysis['expected_frequency'] = 'High (15-25 trades/day)'
        elif frequency_factors >= 2:
            analysis['expected_frequency'] = 'Medium (8-15 trades/day)'
        else:
            analysis['expected_frequency'] = 'Low (3-8 trades/day)'

        # Calculate risk-reward ratio
        rr_ratio = config.target_ticks / config.stop_loss_ticks

        # Generate recommendations
        if rr_ratio < 1.5:
            analysis['recommendations'].append('Consider increasing target_ticks for better risk-reward')
        if config.position_size_percentage > 0.2:
            analysis['recommendations'].append('Consider reducing position size for better risk management')
        if config.max_hold_seconds > 45:
            analysis['recommendations'].append('Consider shorter hold times for true scalping')

        analysis['risk_reward_ratio'] = f"1:{rr_ratio:.1f}"

        return analysis


def demonstrate_configuration_tuning():
    """Demonstrate how to tune scalping configuration"""
    print("\n🔧 Scalping Configuration Tuning Demo")
    print("=" * 50)

    helper = ScalpingConfigurationHelper()

    # Show different configuration profiles
    configs = {
        'Conservative': helper.create_conservative_config(),
        'Standard': ScalpingConfig(),  # Default config
        'Aggressive': helper.create_aggressive_config()
    }

    for profile_name, config in configs.items():
        print(f"\n{profile_name} Profile:")
        print(f"  Position Size: {config.position_size_percentage}%")
        print(f"  Stop Loss: {config.stop_loss_ticks} ticks")
        print(f"  Target: {config.target_ticks} ticks")
        print(f"  Max Hold: {config.max_hold_seconds}s")
        print(f"  Min Confidence: {config.min_confidence}")

        # Analyze configuration
        analysis = helper.analyze_config_impact(config)
        print(f"  Risk Level: {analysis['risk_level']}")
        print(f"  Expected Frequency: {analysis['expected_frequency']}")
        print(f"  Risk-Reward: {analysis['risk_reward_ratio']}")

        if analysis['recommendations']:
            print(f"  Recommendations:")
            for rec in analysis['recommendations']:
                print(f"    - {rec}")


async def main():
    """Main function to run various examples"""
    print("📈 Level II Scalping Strategy Examples")
    print("=" * 50)

    print("\nAvailable examples:")
    print("1. Complete Demo (recommended)")
    print("2. Live Trading Example (10 minutes)")
    print("3. Configuration Tuning Demo")
    print("4. Level II Data Analysis Only")

    choice = input("\nSelect example (1-4): ").strip()

    if choice == "1":
        demo = ScalpingExample()
        await demo.run_demo()

    elif choice == "2":
        confirm = input("⚠️  This will run live trading for 10 minutes. Continue? (y/N): ")
        if confirm.lower() == 'y':
            await run_live_scalping_example()
        else:
            print("Live example cancelled.")

    elif choice == "3":
        demonstrate_configuration_tuning()

    elif choice == "4":
        demo = ScalpingExample()
        if await demo.initialize_system():
            await demo.demo_level2_data_analysis()

    else:
        print("Invalid choice. Running complete demo...")
        demo = ScalpingExample()
        await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())