from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class BacktestConfig:
    tickers: List[str]
    start_date: datetime
    end_date: datetime
    initial_cash: float = 100000.0
    commission: float = 0.001
    slippage: float = 0.0
    use_cache: bool = True
    plot_results: bool = False
    save_results: bool = True
    results_dir: str = "results"
    
    @classmethod
    def from_args(cls, args):
        return cls(
            tickers=args.tickers,
            start_date=args.start_date,
            end_date=args.end_date,
            initial_cash=args.cash,
            commission=args.commission,
            plot_results=args.plot,
        )


@dataclass
class StrategyConfig:
    name: str
    params: dict
    description: Optional[str] = None
    
    @classmethod
    def get_default_configs(cls):
        return {
            'sma_crossover': cls(
                name='SMA Crossover',
                params={'fast_period': 10, 'slow_period': 30},
                description='Simple moving average crossover strategy'
            ),
            'rsi_mean_reversion': cls(
                name='RSI Mean Reversion',
                params={'rsi_period': 14, 'rsi_lower': 30, 'rsi_upper': 70},
                description='RSI-based mean reversion strategy'
            ),
            'momentum': cls(
                name='Momentum',
                params={'lookback_period': 20, 'momentum_threshold': 0.05},
                description='Price momentum strategy'
            ),
        }