import json
import pandas as pd
from datetime import datetime, date
from typing import Dict, List, Optional
from dataclasses import asdict
import logging

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """Track and analyze strategy performance"""

    def __init__(self, data_file: str = "performance_data.json"):
        self.data_file = data_file
        self.daily_data = []
        self.trade_data = []
        self.load_historical_data()

    def load_historical_data(self) -> None:
        """Load historical performance data"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                self.daily_data = data.get('daily_performance', [])
                self.trade_data = data.get('trade_history', [])
        except FileNotFoundError:
            logger.info("No historical data found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading performance data: {e}")

    def save_data(self) -> None:
        """Save performance data to file"""
        try:
            data = {
                'daily_performance': self.daily_data,
                'trade_history': self.trade_data,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving performance data: {e}")

    def record_trade(self, trade_data: Dict) -> None:
        """Record individual trade data"""
        trade_record = {
            'timestamp': datetime.now().isoformat(),
            'date': date.today().isoformat(),
            **trade_data
        }
        self.trade_data.append(trade_record)
        self.save_data()

    def record_daily_performance(self, performance_data: Dict) -> None:
        """Record daily performance summary"""
        daily_record = {
            'date': date.today().isoformat(),
            'timestamp': datetime.now().isoformat(),
            **performance_data
        }

        # Update existing record for today or add new one
        today = date.today().isoformat()
        for i, record in enumerate(self.daily_data):
            if record['date'] == today:
                self.daily_data[i] = daily_record
                self.save_data()
                return

        self.daily_data.append(daily_record)
        self.save_data()

    def get_strategy_metrics(self, strategy_name: str, days: int = 30) -> Dict:
        """Calculate strategy-specific metrics"""
        try:
            # Filter trades for specific strategy and time period
            cutoff_date = (datetime.now() - pd.Timedelta(days=days)).date()
            strategy_trades = [
                trade for trade in self.trade_data
                if (trade.get('strategy') == strategy_name and
                    datetime.fromisoformat(trade['date']).date() >= cutoff_date)
            ]

            if not strategy_trades:
                return {'error': 'No trades found for strategy'}

            # Calculate metrics
            total_trades = len(strategy_trades)
            winning_trades = len([t for t in strategy_trades if t.get('pnl', 0) > 0])
            losing_trades = total_trades - winning_trades

            total_pnl = sum(t.get('pnl', 0) for t in strategy_trades)
            winning_pnl = sum(t.get('pnl', 0) for t in strategy_trades if t.get('pnl', 0) > 0)
            losing_pnl = sum(t.get('pnl', 0) for t in strategy_trades if t.get('pnl', 0) < 0)

            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            avg_win = winning_pnl / winning_trades if winning_trades > 0 else 0
            avg_loss = losing_pnl / losing_trades if losing_trades > 0 else 0
            profit_factor = abs(winning_pnl / losing_pnl) if losing_pnl != 0 else float('inf')

            return {
                'strategy': strategy_name,
                'period_days': days,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': round(win_rate, 2),
                'total_pnl': round(total_pnl, 2),
                'avg_win': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2),
                'profit_factor': round(profit_factor, 2),
                'best_trade': max((t.get('pnl', 0) for t in strategy_trades), default=0),
                'worst_trade': min((t.get('pnl', 0) for t in strategy_trades), default=0)
            }

        except Exception as e:
            logger.error(f"Error calculating strategy metrics: {e}")
            return {'error': str(e)}

    def get_portfolio_metrics(self, days: int = 30) -> Dict:
        """Calculate overall portfolio metrics"""
        try:
            cutoff_date = (datetime.now() - pd.Timedelta(days=days)).date()
            recent_daily_data = [
                d for d in self.daily_data
                if datetime.fromisoformat(d['date']).date() >= cutoff_date
            ]

            if not recent_daily_data:
                return {'error': 'No daily data available'}

            # Calculate portfolio metrics
            daily_returns = [d.get('daily_pnl', 0) for d in recent_daily_data]
            total_return = sum(daily_returns)

            positive_days = len([r for r in daily_returns if r > 0])
            negative_days = len([r for r in daily_returns if r < 0])

            max_drawdown = self._calculate_max_drawdown(daily_returns)
            sharpe_ratio = self._calculate_sharpe_ratio(daily_returns)

            return {
                'period_days': len(recent_daily_data),
                'total_return': round(total_return, 2),
                'avg_daily_return': round(total_return / len(daily_returns), 2),
                'positive_days': positive_days,
                'negative_days': negative_days,
                'win_rate_days': round(positive_days / len(daily_returns) * 100, 2),
                'max_drawdown': round(max_drawdown, 2),
                'sharpe_ratio': round(sharpe_ratio, 2),
                'best_day': round(max(daily_returns, default=0), 2),
                'worst_day': round(min(daily_returns, default=0), 2)
            }

        except Exception as e:
            logger.error(f"Error calculating portfolio metrics: {e}")
            return {'error': str(e)}

    def _calculate_max_drawdown(self, returns: List[float]) -> float:
        """Calculate maximum drawdown"""
        if not returns:
            return 0.0

        cumulative = 0
        peak = 0
        max_dd = 0

        for ret in returns:
            cumulative += ret
            peak = max(peak, cumulative)
            drawdown = peak - cumulative
            max_dd = max(max_dd, drawdown)

        return max_dd

    def _calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.05) -> float:
        """Calculate Sharpe ratio"""
        if not returns or len(returns) < 2:
            return 0.0

        returns_array = pd.Series(returns)
        excess_returns = returns_array - (risk_free_rate / 252)  # Daily risk-free rate

        if excess_returns.std() == 0:
            return 0.0

        return excess_returns.mean() / excess_returns.std() * (252 ** 0.5)