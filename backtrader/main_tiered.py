#!/usr/bin/env python3
"""
Tiered Main Entry Point for Hedge Fund Backtesting System

This provides the tiered configuration interface (basic, intermediate, advanced, expert)
as described in CONFIGURATION.md while maintaining compatibility with the existing
main.py regime-based backtesting system.
"""

import os
import sys
from datetime import datetime

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.cli_parser import TieredArgumentParser
from config.parameter_registry import ParameterRegistry
from config.data_models import StrategyConfiguration
from main import run_regime_backtest


def convert_args_to_regime_params(args, tier_config):
    """Convert tiered configuration args to regime backtest parameters"""
    
    # Map tier configuration to regime function parameters
    regime_params = {
        'start_date': datetime.strptime(args.start_date, '%Y-%m-%d'),
        'end_date': datetime.strptime(args.end_date, '%Y-%m-%d') if args.end_date else datetime.now(),
        'cash': getattr(args, 'cash', 100000),
        'commission': getattr(args, 'commission', 0.001),
        'bucket_names': getattr(args, 'buckets', 'Risk Assets').split(',') if hasattr(args, 'buckets') else ['Risk Assets'],
        'max_assets_per_period': getattr(args, 'max_total_positions', 5),
        'rebalance_frequency': getattr(args, 'rebalance_frequency', 'monthly'),
        'min_score_threshold': getattr(args, 'min_score_threshold', 0.6),
        'timeframes': getattr(args, 'timeframes', '1d,4h,1h').split(',') if hasattr(args, 'timeframes') else ['1d'],
        'enable_technical_analysis': getattr(args, 'enable_technical_analysis', True),
        'enable_fundamental_analysis': getattr(args, 'enable_fundamental_analysis', True),
        'technical_weight': getattr(args, 'technical_weight', 0.6),
        'fundamental_weight': getattr(args, 'fundamental_weight', 0.4),
        'min_trending_confidence': getattr(args, 'min_trending_confidence', 0.7),
        'data_provider': getattr(args, 'data_provider', None),
        
        # Core Asset Management Parameters
        'enable_core_assets': getattr(args, 'enable_core_assets', False),
        'max_core_assets': getattr(args, 'max_core_assets', 3),
        'core_override_threshold': getattr(args, 'core_override_threshold', 0.95),
        'core_expiry_days': getattr(args, 'core_expiry_days', 90),
        'core_underperformance_threshold': getattr(args, 'core_underperformance_threshold', 0.15),
        'core_underperformance_period': getattr(args, 'core_underperformance_period', 30),
        'core_extension_limit': getattr(args, 'core_extension_limit', 2),
        'core_performance_check_frequency': getattr(args, 'core_performance_check_frequency', 7),
        'smart_diversification_overrides': getattr(args, 'smart_diversification_overrides', 2),
        
        # Visualization and export
        'enable_visualization': getattr(args, 'enable_visualization', True),
        'export_format': getattr(args, 'export_format', 'all'),
        'chart_style': getattr(args, 'chart_style', 'interactive'),
        'benchmark_ticker': getattr(args, 'benchmark_ticker', 'SPY')
    }
    
    return regime_params


def run_tiered_backtest(args, tier_level: int):
    """Run backtest using tiered configuration"""
    
    print(f"🎯 Running {args.mode.upper()} tier backtest (Tier {tier_level})")
    print("=" * 60)
    
    # Load tier configuration
    registry = ParameterRegistry()
    tier_config = registry.get_parameters_by_tier(tier_level)
    
    # Show configuration summary
    print(f"📊 Configuration Summary:")
    print(f"   Tier Level: {tier_level} ({args.mode.title()})")
    print(f"   Parameters: {len(tier_config)} available")
    print(f"   Start Date: {args.start_date}")
    print(f"   Cash: ${getattr(args, 'cash', 100000):,.2f}")
    print(f"   Asset Buckets: {getattr(args, 'buckets', 'Risk Assets')}")
    print(f"   Max Positions: {getattr(args, 'max_total_positions', 5)}")
    
    # Convert arguments to regime parameters
    regime_params = convert_args_to_regime_params(args, tier_config)
    
    print("\n🚀 Starting Backtest...")
    print("=" * 60)
    
    # Run the regime-based backtest
    results = run_regime_backtest(**regime_params)
    
    return results


def main():
    """Main entry point with tiered configuration"""
    
    # Initialize tiered parser
    registry = ParameterRegistry()
    parser = TieredArgumentParser(registry)
    
    try:
        args = parser.parser.parse_args()
        
        if not args.mode:
            parser.parser.print_help()
            return
        
        # Handle configuration management commands
        if args.mode == 'config':
            print("🔧 Configuration management not implemented in this version")
            print("   Use the full config module: python -m config.cli_parser")
            return
        
        # Handle preset mode
        if args.mode == 'preset':
            print("🎨 Preset mode not implemented in this version")
            print("   Use direct tier modes: basic, intermediate, advanced, expert")
            return
        
        # Map tier modes to levels
        tier_mapping = {
            'basic': 1,
            'intermediate': 2,
            'advanced': 3,
            'expert': 4
        }
        
        if args.mode in tier_mapping:
            tier_level = tier_mapping[args.mode]
            results = run_tiered_backtest(args, tier_level)
            
            print("\n✅ Backtest completed successfully!")
            return results
        
        elif args.mode == 'regime':
            # Legacy regime mode - pass through to original main.py
            print("🔄 Using legacy regime mode")
            print("   For tiered interface, use: basic, intermediate, advanced, expert")
            
            # Import and run original main
            from main import main as original_main
            return original_main()
        
        else:
            print(f"❌ Unknown mode: {args.mode}")
            print("   Available modes: basic, intermediate, advanced, expert, regime")
            parser.parser.print_help()
            return
            
    except KeyboardInterrupt:
        print("\n⚠️  Backtest interrupted by user")
        return
    except Exception as e:
        print(f"\n❌ Error running backtest: {e}")
        import traceback
        traceback.print_exc()
        return


if __name__ == '__main__':
    main()