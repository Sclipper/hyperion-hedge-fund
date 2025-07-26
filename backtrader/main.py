#!/usr/bin/env python3

import argparse
import datetime
import backtrader as bt
from pathlib import Path
from data.data_manager import DataManager
from data.regime_detector import RegimeDetector
from data.asset_buckets import AssetBucketManager
from strategies.regime_strategy import RegimeStrategy
from utils.config import BacktestConfig
from utils.analyzers import setup_analyzers
from utils.results import save_results, compare_results


def run_regime_backtest(start_date, end_date, strategy_class=None, cash=100000, commission=0.001, 
                       bucket_names=None, max_assets_per_period=5, rebalance_frequency='monthly',
                       min_score_threshold=0.6, timeframes=['1d', '4h', '1h']):
    cerebro = bt.Cerebro()
    
    strategy_class = strategy_class or RegimeStrategy
    
    regime_detector = RegimeDetector()
    asset_manager = AssetBucketManager()
    data_manager = DataManager()
    
    all_possible_assets = asset_manager.get_all_assets_from_buckets(bucket_names)
    
    cerebro.addstrategy(
        strategy_class,
        regime_detector=regime_detector,
        asset_manager=asset_manager,
        data_manager=data_manager,
        max_assets_per_period=max_assets_per_period,
        bucket_names=bucket_names,
        rebalance_frequency=rebalance_frequency,
        position_min_score=min_score_threshold,
        timeframes=timeframes
    )
    
    for ticker in all_possible_assets:
        data = data_manager.get_data(ticker, start_date, end_date)
        if data is not None:
            cerebro.adddata(data, name=ticker)
    
    cerebro.broker.setcash(cash)
    cerebro.broker.setcommission(commission=commission)
    
    cerebro.addsizer(bt.sizers.PercentSizer, percents=95)
    
    setup_analyzers(cerebro)
    
    print(f'Starting Portfolio Value: {cerebro.broker.getvalue():.2f}')
    print(f'Asset Universe: {len(all_possible_assets)} assets from buckets: {bucket_names}')
    
    results = cerebro.run()
    
    print(f'Final Portfolio Value: {cerebro.broker.getvalue():.2f}')
    
    save_results(results[0], all_possible_assets, start_date, end_date)
    
    return results


def run_static_backtest(tickers, start_date, end_date, strategy_class=None, cash=100000, commission=0.001):
    from strategies.base_strategy import BaseStrategy
    
    cerebro = bt.Cerebro()
    
    strategy_class = strategy_class or BaseStrategy
    cerebro.addstrategy(strategy_class)
    
    data_manager = DataManager()
    
    for ticker in tickers:
        data = data_manager.get_data(ticker, start_date, end_date)
        if data is not None:
            cerebro.adddata(data, name=ticker)
    
    cerebro.broker.setcash(cash)
    cerebro.broker.setcommission(commission=commission)
    
    cerebro.addsizer(bt.sizers.PercentSizer, percents=95)
    
    setup_analyzers(cerebro)
    
    print(f'Starting Portfolio Value: {cerebro.broker.getvalue():.2f}')
    
    results = cerebro.run()
    
    print(f'Final Portfolio Value: {cerebro.broker.getvalue():.2f}')
    
    save_results(results[0], tickers, start_date, end_date)
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Backtrader Regime-Based Backtesting System')
    
    subparsers = parser.add_subparsers(dest='mode', help='Backtest mode')
    
    # Regime-based backtest
    regime_parser = subparsers.add_parser('regime', help='Run regime-based backtest')
    regime_parser.add_argument('--buckets', type=str, required=True,
                              help='Comma-separated list of asset buckets (e.g., "Risk Assets,Defensives")')
    regime_parser.add_argument('--start-date', type=str, default='2021-01-01',
                              help='Start date (YYYY-MM-DD)')
    regime_parser.add_argument('--end-date', type=str, default=None,
                              help='End date (YYYY-MM-DD), defaults to today')
    regime_parser.add_argument('--max-assets', type=int, default=5,
                              help='Maximum assets to select per period')
    regime_parser.add_argument('--cash', type=float, default=100000,
                              help='Starting cash amount')
    regime_parser.add_argument('--commission', type=float, default=0.001,
                              help='Commission rate')
    regime_parser.add_argument('--rebalance-freq', type=str, default='monthly',
                              choices=['daily', 'weekly', 'monthly'],
                              help='Rebalancing frequency')
    regime_parser.add_argument('--min-score', type=float, default=0.6,
                              help='Minimum position score threshold')
    regime_parser.add_argument('--timeframes', type=str, default='1d,4h,1h',
                              help='Comma-separated timeframes for technical analysis')
    
    # Compare results command
    compare_parser = subparsers.add_parser('compare', help='Compare backtest results')
    compare_parser.add_argument('--files', type=str, required=True,
                               help='Comma-separated list of result JSON files to compare')
    compare_parser.add_argument('--results-dir', type=str, default='results',
                               help='Directory containing result files')
    compare_parser.add_argument('--output', type=str, default=None,
                               help='Output file for comparison (CSV format)')
    
    # Static backtest (original functionality)
    static_parser = subparsers.add_parser('static', help='Run static ticker backtest')
    static_parser.add_argument('--tickers', type=str, required=True,
                              help='Comma-separated list of tickers to backtest')
    static_parser.add_argument('--start-date', type=str, default='2021-01-01',
                              help='Start date (YYYY-MM-DD)')
    static_parser.add_argument('--end-date', type=str, default=None,
                              help='End date (YYYY-MM-DD), defaults to today')
    static_parser.add_argument('--cash', type=float, default=100000,
                              help='Starting cash amount')
    static_parser.add_argument('--commission', type=float, default=0.001,
                              help='Commission rate')
    
    parser.add_argument('--plot', action='store_true',
                       help='Plot results')
    
    args = parser.parse_args()
    
    if not args.mode:
        parser.print_help()
        return
    
    start_date = datetime.datetime.strptime(args.start_date, '%Y-%m-%d')
    
    if args.end_date:
        end_date = datetime.datetime.strptime(args.end_date, '%Y-%m-%d')
    else:
        end_date = datetime.datetime.now() - datetime.timedelta(days=1)
    
    if args.mode == 'regime':
        bucket_names = [bucket.strip() for bucket in args.buckets.split(',')]
        timeframes = [tf.strip() for tf in args.timeframes.split(',')]
        
        results = run_regime_backtest(
            start_date=start_date,
            end_date=end_date,
            bucket_names=bucket_names,
            max_assets_per_period=args.max_assets,
            cash=args.cash,
            commission=args.commission,
            rebalance_frequency=args.rebalance_freq,
            min_score_threshold=args.min_score,
            timeframes=timeframes
        )
    elif args.mode == 'compare':
        # Compare results mode
        result_files = [f.strip() for f in args.files.split(',')]
        
        print(f"Comparing {len(result_files)} result files...")
        comparison_df = compare_results(result_files, args.results_dir)
        
        if comparison_df.empty:
            print("No valid results found to compare")
            return
        
        # Display comparison
        print("\n" + "="*80)
        print("BACKTEST RESULTS COMPARISON")
        print("="*80)
        print(comparison_df.to_string(index=False, float_format='%.4f'))
        
        # Save to file if requested
        if args.output:
            output_path = Path(args.output)
            comparison_df.to_csv(output_path, index=False)
            print(f"\nComparison saved to: {output_path}")
        
        return
    elif args.mode == 'static':
        tickers = [ticker.strip() for ticker in args.tickers.split(',')]
        results = run_static_backtest(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            cash=args.cash,
            commission=args.commission
        )
    
    if args.plot:
        import matplotlib
        matplotlib.use('Agg')
        cerebro = bt.Cerebro()
        cerebro.plot(style='candlestick')


if __name__ == '__main__':
    main()