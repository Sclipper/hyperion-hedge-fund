#!/usr/bin/env python3
"""
Optimized main.py with data pre-loading for better performance
"""

import argparse
import datetime
import backtrader as bt
from pathlib import Path

# Import original components
from data.data_manager import DataManager
from data.regime_detector import RegimeDetector
from data.asset_buckets import AssetBucketManager
from strategies.regime_strategy import RegimeStrategy
from utils.config import BacktestConfig
from utils.analyzers import setup_analyzers
from utils.results import save_results, compare_results

# Import optimizer
from utils.data_preloader import DataPreloader


def run_regime_backtest_optimized(
    start_date, end_date, strategy_class=None, cash=100000, commission=0.001, 
    bucket_names=None, max_assets_per_period=5, rebalance_frequency='monthly',
    min_score_threshold=0.6, timeframes=['1d', '4h', '1h'],
    enable_technical_analysis=True, enable_fundamental_analysis=True,
    technical_weight=0.6, fundamental_weight=0.4, min_trending_confidence=0.7,
    # Core Asset Management Parameters
    enable_core_assets=False, max_core_assets=3, core_override_threshold=0.95,
    core_expiry_days=90, core_underperformance_threshold=0.15, 
    core_underperformance_period=30, core_extension_limit=2, 
    core_performance_check_frequency=7, smart_diversification_overrides=2,
    enable_take_profit_stop_loss=False, data_provider=None,
    enable_visualization=True, export_format='all', chart_style='interactive', 
    benchmark_ticker='SPY', lookback_days=90
):
    """Optimized regime backtest with data pre-loading"""
    
    cerebro = bt.Cerebro()
    
    strategy_class = strategy_class or RegimeStrategy
    
    # Initialize components
    regime_detector = RegimeDetector()
    asset_manager = AssetBucketManager()
    data_manager = DataManager(provider_name=data_provider)
    
    # Get all possible assets
    all_possible_assets = asset_manager.get_all_assets_from_buckets(bucket_names)
    
    print("=" * 80)
    print("OPTIMIZED BACKTESTING WITH DATA PRE-LOADING")
    print("=" * 80)
    print(f"Asset Universe: {len(all_possible_assets)} assets from buckets: {bucket_names}")
    print(f"Timeframes: {timeframes}")
    print(f"Lookback buffer: {lookback_days} days")
    
    # Initialize data preloader
    preloader = DataPreloader(data_manager, lookback_days=lookback_days)
    
    # Pre-load ALL timeframes with lookback buffer
    print(f"\nPre-loading all data (this may take a moment)...")
    print(f"Date range: {(start_date - datetime.timedelta(days=lookback_days)).date()} to {end_date.date()}")
    
    def progress_callback(status, percent):
        print(f"\r{status}... {percent}%", end='', flush=True)
    
    preloaded_data = preloader.preload_all_timeframes(
        assets=all_possible_assets,
        timeframes=timeframes,
        start_date=start_date,
        end_date=end_date,
        progress_callback=progress_callback
    )
    
    print(f"\n✓ Pre-loaded {len(preloaded_data)} assets with {len(timeframes)} timeframes each")
    
    # Check memory usage
    memory_stats = preloader.get_memory_usage()
    print(f"Memory usage: {memory_stats['total_mb']:.1f} MB "
          f"(~{memory_stats['avg_per_asset_mb']:.1f} MB per asset)")
    
    # Add strategy with preloader reference
    cerebro.addstrategy(
        strategy_class,
        regime_detector=regime_detector,
        asset_manager=asset_manager,
        data_manager=data_manager,
        data_preloader=preloader,  # Pass preloader to strategy
        max_assets_per_period=max_assets_per_period,
        bucket_names=bucket_names,
        rebalance_frequency=rebalance_frequency,
        position_min_score=min_score_threshold,
        timeframes=timeframes,
        enable_technical_analysis=enable_technical_analysis,
        enable_fundamental_analysis=enable_fundamental_analysis,
        technical_weight=technical_weight,
        fundamental_weight=fundamental_weight,
        min_trending_confidence=min_trending_confidence,
        # Core Asset Management
        enable_core_assets=enable_core_assets,
        max_core_assets=max_core_assets,
        core_override_threshold=core_override_threshold,
        core_expiry_days=core_expiry_days,
        core_underperformance_threshold=core_underperformance_threshold,
        core_underperformance_period=core_underperformance_period,
        core_extension_limit=core_extension_limit,
        core_performance_check_frequency=core_performance_check_frequency,
        smart_diversification_overrides=smart_diversification_overrides,
        enable_take_profit_stop_loss=enable_take_profit_stop_loss
    )
    
    # Create backtrader feeds from pre-loaded data
    print("\nAdding data feeds to cerebro...")
    feeds = preloader.create_backtrader_feeds(
        cerebro=cerebro,
        assets=all_possible_assets,
        start_date=start_date,
        end_date=end_date,
        primary_timeframe='1d'  # Primary timeframe for backtrader
    )
    
    print(f"Successfully added {len(feeds)} data feeds")
    
    # Configure broker
    cerebro.broker.setcash(cash)
    cerebro.broker.setcommission(commission=commission)
    cerebro.addsizer(bt.sizers.PercentSizer, percents=95)
    
    # Add analyzers
    setup_analyzers(cerebro)
    
    print(f'\nStarting Portfolio Value: ${cerebro.broker.getvalue():,.2f}')
    print("Running backtest...")
    
    # Run backtest
    import time
    start_time = time.time()
    results = cerebro.run()
    run_time = time.time() - start_time
    
    print(f'Final Portfolio Value: ${cerebro.broker.getvalue():,.2f}')
    print(f'Backtest completed in {run_time:.1f} seconds')
    
    # Save results
    save_results(results[0], all_possible_assets, start_date, end_date,
                enable_visualization=enable_visualization,
                export_format=export_format, 
                chart_style=chart_style,
                benchmark_ticker=benchmark_ticker)
    
    return results


def main():
    """Main entry point with optimized data loading"""
    
    parser = argparse.ArgumentParser(
        description='Optimized Backtrader Regime-Based Backtesting System'
    )
    
    # Same arguments as original main.py
    parser.add_argument('--buckets', type=str, required=True,
                       help='Comma-separated list of asset buckets')
    parser.add_argument('--start-date', type=str, default='2021-01-01')
    parser.add_argument('--end-date', type=str, default=None)
    parser.add_argument('--max-assets', type=int, default=5)
    parser.add_argument('--cash', type=float, default=100000)
    parser.add_argument('--commission', type=float, default=0.001)
    parser.add_argument('--rebalance-freq', type=str, default='monthly',
                       choices=['daily', 'weekly', 'monthly'])
    parser.add_argument('--min-score', type=float, default=0.6)
    parser.add_argument('--timeframes', type=str, default='1d,4h,1h')
    parser.add_argument('--data-provider', type=str, default=None)
    parser.add_argument('--lookback-days', type=int, default=90,
                       help='Days to pre-load before start date for technical analysis')
    
    # Analysis options
    parser.add_argument('--disable-technical', action='store_true')
    parser.add_argument('--disable-fundamental', action='store_true')
    parser.add_argument('--technical-weight', type=float, default=0.6)
    parser.add_argument('--fundamental-weight', type=float, default=0.4)
    parser.add_argument('--min-trending-confidence', type=float, default=0.7)
    
    # Core asset options
    parser.add_argument('--enable-core-assets', action='store_true')
    parser.add_argument('--max-core-assets', type=int, default=3)
    
    args = parser.parse_args()
    
    # Parse dates
    start_date = datetime.datetime.strptime(args.start_date, '%Y-%m-%d')
    end_date = datetime.datetime.strptime(args.end_date, '%Y-%m-%d') if args.end_date else datetime.datetime.now()
    
    # Parse other inputs
    bucket_names = [bucket.strip() for bucket in args.buckets.split(',')]
    timeframes = [tf.strip() for tf in args.timeframes.split(',')]
    
    # Run optimized backtest
    run_regime_backtest_optimized(
        start_date=start_date,
        end_date=end_date,
        bucket_names=bucket_names,
        max_assets_per_period=args.max_assets,
        cash=args.cash,
        commission=args.commission,
        rebalance_frequency=args.rebalance_freq,
        min_score_threshold=args.min_score,
        timeframes=timeframes,
        enable_technical_analysis=not args.disable_technical,
        enable_fundamental_analysis=not args.disable_fundamental,
        technical_weight=args.technical_weight,
        fundamental_weight=args.fundamental_weight,
        min_trending_confidence=args.min_trending_confidence,
        enable_core_assets=args.enable_core_assets,
        max_core_assets=args.max_core_assets,
        data_provider=args.data_provider,
        lookback_days=args.lookback_days
    )


if __name__ == '__main__':
    main()