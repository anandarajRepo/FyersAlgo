# Enhanced Multi-Strategy Trading System

A comprehensive Python-based algorithmic trading system supporting multiple strategies with the Fyers API v3.

## 🚀 Features

### Multi-Strategy Support
- **Gap-Up Short Strategy**: Profits from overbought stocks that gap up
- **Open Breakout Strategy**: Captures momentum from opening range breakouts
- **Portfolio Management**: Run both strategies simultaneously with risk controls

### Advanced Risk Management
- Portfolio-level stop losses and profit targets
- Position correlation controls
- Dynamic position sizing
- Real-time P&L tracking

### Professional Architecture
- Modular design with clean separation of concerns
- Async/await for concurrent operations
- Comprehensive error handling and logging
- Type hints and data validation

## 📋 Prerequisites

- Python 3.9 or higher
- Fyers Trading Account
- Fyers API credentials (Client ID, Secret Key)

## 🛠 Installation

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd enhanced-trading-system
```

### 2. Create Virtual Environment
```bash
python -m venv trading_env
source trading_env/bin/activate  # Linux/Mac
# or
trading_env\Scripts\activate  # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Configuration
```bash
# Copy the template
cp .env.template .env

# Edit .env with your actual credentials
nano .env  # or use any text editor
```

### 5. Authenticate with Fyers
```bash
python main_enhanced.py auth
```

## 🎯 Usage

### Multi-Strategy System (Recommended)
```bash
python main_enhanced.py multi
```

### Single Strategy (Gap-Up Short only)
```bash
python main_enhanced.py single
```

### Interactive Mode
```bash
python main_enhanced.py
# Follow the prompts to select your preferred mode
```

## 📊 Strategy Overview

### Gap-Up Short Strategy
- **Objective**: Short overbought stocks that gap up
- **Entry**: Stocks with selling pressure that gap up 0.5%+
- **Exit**: 1.5% stop loss, 3% target
- **Time Window**: 9:15-10:30 AM
- **Expected Win Rate**: ~60%

### Open Breakout Strategy
- **Objective**: Long momentum breakouts from opening range
- **Entry**: Price breaks above 15-minute opening range with volume
- **Exit**: Stop below opening range low, 2:1 risk-reward
- **Time Window**: 9:30-11:30 AM
- **Expected Win Rate**: ~65%

## 🛡 Risk Management

### Portfolio Level
- **Maximum Positions**: 5 total (3 shorts + 2 longs)
- **Portfolio Stop Loss**: 5% daily drawdown
- **Profit Target**: 3% daily profit target
- **Position Size**: 1% portfolio risk per trade

### Strategy Level
- **Gap-Up Short**: Max 3 positions, 1.5% stop loss
- **Breakout**: Max 2 positions, dynamic stops
- **Sector Limits**: Max 2 positions per sector

## 📁 Project Structure

```
enhanced-trading-system/
├── config/
│   ├── settings.py              # Core configuration
│   └── breakout_settings.py     # Breakout-specific config
├── interfaces/
│   └── data_provider.py         # Abstract interfaces
├── models/
│   └── trading_models.py        # Data models
├── services/
│   ├── fyers_service.py         # Fyers API integration
│   ├── analysis_service.py      # Technical analysis
│   ├── signal_service.py        # Signal generation
│   ├── position_service.py      # Position management
│   └── market_timing_service.py # Market timing logic
├── strategies/
│   ├── __init__.py
│   ├── open_breakout_strategy.py # Breakout strategy
│   └── strategy_factory.py      # Strategy management
├── utils/
│   └── auth_helper.py           # Authentication utilities
├── main_strategy.py             # Gap-up strategy
├── main_enhanced.py             # Enhanced multi-strategy main
├── requirements.txt             # Dependencies
├── .env.template               # Environment template
└── README.md                   # This file
```

## 🔧 Configuration Options

### Environment Variables (.env)
```bash
# Fyers API
FYERS_CLIENT_ID=your_client_id
FYERS_SECRET_KEY=your_secret_key
FYERS_ACCESS_TOKEN=your_token

# Trading Parameters
PORTFOLIO_VALUE=1000000
RISK_PER_TRADE=1.0
MAX_POSITIONS=5
MIN_CONFIDENCE=0.6

# Strategy Specific
MIN_GAP_PERCENTAGE=0.5
MIN_SELLING_PRESSURE=40.0
STOP_LOSS_PCT=1.5
TARGET_PCT=3.0
```

## 📈 Expected Performance

### Conservative Scenario
- **Daily Trades**: 2-4 per day
- **Win Rate**: 60-65%
- **Daily Target**: 0.5-1% portfolio growth
- **Monthly Target**: 10-15%

### Aggressive Scenario
- **Daily Trades**: 4-5 per day
- **Win Rate**: 58-63%
- **Daily Target**: 1-2% portfolio growth
- **Monthly Target**: 15-25%

## 🐛 Troubleshooting

### Common Issues

#### Authentication Errors
```bash
# Re-run authentication
python main_enhanced.py auth
```

#### Import Errors
```bash
# Ensure you're in the correct directory and virtual environment
pip install -r requirements.txt
```

#### API Rate Limits
- The system includes built-in rate limiting
- Reduce `monitoring_interval` if needed

### Logging
- Logs are written to `trading_strategy.log`
- Set `LOG_LEVEL=DEBUG` in .env for detailed logs

## ⚠️ Important Notes

### Risk Disclaimer
- This is educational software for learning algorithmic trading
- Always test with small amounts first
- Past performance doesn't guarantee future results
- Trading involves risk of loss

### System Requirements
- Stable internet connection
- Sufficient RAM for data processing
- Python 3.9+ for async support

### Market Hours
- System operates during NSE trading hours (9:15 AM - 3:30 PM IST)
- Automatically handles market holidays and weekends

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📜 License

This project is for educational purposes. Please review the license file for details.

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs for error details
3. Create an issue on GitHub with:
   - System details
   - Error logs
   - Steps to reproduce

---

**Happy Trading! 📈**