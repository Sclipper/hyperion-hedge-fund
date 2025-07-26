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
                       min_score_threshold=0.6, timeframes=['1d', '4h', '1h'],
                       enable_technical_analysis=True, enable_fundamental_analysis=True,
                       technical_weight=0.6, fundamental_weight=0.4, min_trending_confidence=0.7,
                       # Core Asset Management Parameters (Module 5)
                       enable_core_assets=False, max_core_assets=3, core_override_threshold=0.95,
                       core_expiry_days=90, core_underperformance_threshold=0.15, 
                       core_underperformance_period=30, core_extension_limit=2, 
                       core_performance_check_frequency=7, smart_diversification_overrides=2):
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
        timeframes=timeframes,
        enable_technical_analysis=enable_technical_analysis,
        enable_fundamental_analysis=enable_fundamental_analysis,
        technical_weight=technical_weight,
        fundamental_weight=fundamental_weight,
        min_trending_confidence=min_trending_confidence,
        # Core Asset Management Parameters (Module 5)
        enable_core_assets=enable_core_assets,
        max_core_assets=max_core_assets,
        core_override_threshold=core_override_threshold,
        core_expiry_days=core_expiry_days,
        core_underperformance_threshold=core_underperformance_threshold,
        core_underperformance_period=core_underperformance_period,
        core_extension_limit=core_extension_limit,
        core_performance_check_frequency=core_performance_check_frequency,
        smart_diversification_overrides=smart_diversification_overrides
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
    regime_parser.add_argument('--disable-technical', action='store_true',
                              help='Disable technical analysis (use fundamental only)')
    regime_parser.add_argument('--disable-fundamental', action='store_true',
                              help='Disable fundamental analysis (use technical only)')
    regime_parser.add_argument('--technical-weight', type=float, default=0.6,
                              help='Weight for technical analysis (0.0-1.0)')
    regime_parser.add_argument('--fundamental-weight', type=float, default=0.4,
                              help='Weight for fundamental analysis (0.0-1.0)')
    regime_parser.add_argument('--min-trending-confidence', type=float, default=0.7,
                              help='Minimum confidence score for trending assets (0.0-1.0)')
    
    # Core Asset Management Parameters (Module 5)
    regime_parser.add_argument('--enable-core-assets', action='store_true',
                              help='Enable core asset management system')
    regime_parser.add_argument('--max-core-assets', type=int, default=3,
                              help='Maximum number of core assets allowed')
    regime_parser.add_argument('--core-override-threshold', type=float, default=0.95,
                              help='Score threshold for bucket override eligibility (0.0-1.0)')
    regime_parser.add_argument('--core-expiry-days', type=int, default=90,
                              help='Days before core asset designation expires')
    regime_parser.add_argument('--core-underperformance-threshold', type=float, default=0.15,
                              help='Underperformance threshold for auto-revocation (0.0-1.0)')
    regime_parser.add_argument('--core-underperformance-period', type=int, default=30,
                              help='Days to measure underperformance over')
    regime_parser.add_argument('--core-extension-limit', type=int, default=2,
                              help='Maximum number of extensions allowed per core asset')
    regime_parser.add_argument('--core-performance-check-frequency', type=int, default=7,
                              help='Days between performance checks for core assets')
    regime_parser.add_argument('--smart-diversification-overrides', type=int, default=2,
                              help='Maximum bucket overrides per rebalancing cycle')
    
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
        
        # Process analysis configuration
        enable_technical = not args.disable_technical
        enable_fundamental = not args.disable_fundamental
        
        # Validate configuration
        if not enable_technical and not enable_fundamental:
            print("ERROR: Cannot disable both technical and fundamental analysis.")
            print("Please specify only one of --disable-technical or --disable-fundamental")
            return
        
        # Validate weights
        if args.technical_weight < 0 or args.technical_weight > 1:
            print("ERROR: Technical weight must be between 0.0 and 1.0")
            return
        
        if args.fundamental_weight < 0 or args.fundamental_weight > 1:
            print("ERROR: Fundamental weight must be between 0.0 and 1.0")
            return
        
        if args.min_trending_confidence < 0 or args.min_trending_confidence > 1:
            print("ERROR: Minimum trending confidence must be between 0.0 and 1.0")
            return
        
        # Validate core asset management parameters
        if args.enable_core_assets:
            if args.core_override_threshold < 0 or args.core_override_threshold > 1:
                print("ERROR: Core override threshold must be between 0.0 and 1.0")
                return
            if args.core_underperformance_threshold < 0 or args.core_underperformance_threshold > 1:
                print("ERROR: Core underperformance threshold must be between 0.0 and 1.0")
                return
            if args.max_core_assets < 1:
                print("ERROR: Max core assets must be at least 1")
                return
            if args.core_expiry_days < 1:
                print("ERROR: Core expiry days must be at least 1")
                return
        
        # Warn about weight normalization
        total_weight = args.technical_weight + args.fundamental_weight
        if abs(total_weight - 1.0) > 0.01:
            print(f"INFO: Weights sum to {total_weight:.2f}, will be normalized to 1.0")
        
        # Log configuration
        analysis_config = []
        if enable_technical:
            analysis_config.append(f"Technical ({args.technical_weight:.1%})")
        if enable_fundamental:
            analysis_config.append(f"Fundamental ({args.fundamental_weight:.1%})")
        print(f"Analysis Configuration: {', '.join(analysis_config)}")
        print(f"Trending Assets: Min confidence {args.min_trending_confidence:.1%}")
        
        # Log core asset management configuration
        if args.enable_core_assets:
            print(f"🌟 Core Asset Management: ENABLED")
            print(f"   Max core assets: {args.max_core_assets}")
            print(f"   Override threshold: {args.core_override_threshold:.1%}")
            print(f"   Expiry days: {args.core_expiry_days}")
            print(f"   Max overrides per cycle: {args.smart_diversification_overrides}")
        else:
            print(f"🌟 Core Asset Management: DISABLED")
        
        results = run_regime_backtest(
            start_date=start_date,
            end_date=end_date,
            bucket_names=bucket_names,
            max_assets_per_period=args.max_assets,
            cash=args.cash,
            commission=args.commission,
            rebalance_frequency=args.rebalance_freq,
            min_score_threshold=args.min_score,
            timeframes=timeframes,
            enable_technical_analysis=enable_technical,
            enable_fundamental_analysis=enable_fundamental,
            technical_weight=args.technical_weight,
            fundamental_weight=args.fundamental_weight,
            min_trending_confidence=args.min_trending_confidence,
            # Core Asset Management Parameters (Module 5)
            enable_core_assets=args.enable_core_assets,
            max_core_assets=args.max_core_assets,
            core_override_threshold=args.core_override_threshold,
            core_expiry_days=args.core_expiry_days,
            core_underperformance_threshold=args.core_underperformance_threshold,
            core_underperformance_period=args.core_underperformance_period,
            core_extension_limit=args.core_extension_limit,
            core_performance_check_frequency=args.core_performance_check_frequency,
            smart_diversification_overrides=args.smart_diversification_overrides
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