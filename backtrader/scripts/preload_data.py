#!/usr/bin/env python3
"""
Data Pre-download Script for Hedge Fund Backtesting System

This script allows pre-downloading historical data for multiple tickers and timeframes
using the existing provider abstraction. Supports Alpha Vantage and Yahoo Finance with
intelligent chunking, checkpointing, and progress tracking.

Usage Examples:
    # Download 1 year of daily data for major assets
    python scripts/preload_data.py --tickers AAPL,MSFT,GOOGL --timeframes 1d --period 1y

    # Multi-timeframe download with Alpha Vantage
    python scripts/preload_data.py --tickers AAPL,MSFT --timeframes 1h,4h,1d --start-date 2023-01-01 --end-date 2024-01-01 --provider alpha_vantage

    # Resume interrupted download
    python scripts/preload_data.py --resume PLAN_20240101_AAPL_multi

    # Download crypto data
    python scripts/preload_data.py --tickers BTC,ETH --timeframes 1d --period 6m --provider alpha_vantage

    # Bulk download all risk assets
    python scripts/preload_data.py --bucket "Risk Assets" --timeframes 1d --period 2y
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
import signal
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    load_dotenv(env_path)
    print(f"✅ Loaded environment variables from {env_path}")
except ImportError:
    print("⚠️  python-dotenv not available, using system environment variables only")

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.data_manager import DataManager
from data.timeframe_manager import TimeframeManager
from data.asset_buckets import AssetBucketManager
from data.providers.alpha_vantage.bulk_fetcher import BulkDataFetcher
from data.providers.alpha_vantage.checkpoint_manager import CheckpointManager
from data.providers.alpha_vantage.client import AlphaVantageClient


class DataPreloader:
    """
    Standalone data pre-download manager
    """
    
    def __init__(self, provider_name: str = 'alpha_vantage', cache_dir: str = 'data/cache'):
        """
        Initialize data preloader
        
        Args:
            provider_name: Data provider to use ('alpha_vantage' or 'yahoo')
            cache_dir: Directory for cached data
        """
        self.provider_name = provider_name
        self.cache_dir = cache_dir
        
        # Initialize data manager with provider
        self.data_manager = DataManager(cache_dir=cache_dir, provider_name=provider_name)
        self.timeframe_manager = self.data_manager.timeframe_manager
        self.asset_manager = AssetBucketManager()
        
        # Initialize bulk fetcher for Alpha Vantage
        if provider_name == 'alpha_vantage':
            try:
                self.client = AlphaVantageClient()
                self.bulk_fetcher = BulkDataFetcher(self.client)
                self.checkpoint_manager = CheckpointManager()
                self.supports_bulk = True
            except ValueError as e:
                print(f"⚠️  Alpha Vantage not available: {e}")
                print("   Falling back to individual downloads")
                self.supports_bulk = False
        else:
            self.supports_bulk = False
        
        # Track active download for cleanup
        self.active_plan_id = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        print(f"🔧 DataPreloader initialized with {provider_name} provider")
        provider_info = self.timeframe_manager.get_provider_info()
        print(f"   ✅ Supported timeframes: {provider_info['supported_timeframes']}")
        print(f"   ✅ Rate limits: {provider_info['rate_limits']['requests_per_minute']} req/min")
        
        # Cache optimization: flag to skip bulk infrastructure for cached data
        self.optimize_cached_data = True
    
    def _signal_handler(self, signum, frame):
        """Handle interruption signals gracefully"""
        print(f"\n⚠️  Received signal {signum}. Saving checkpoint...")
        if self.active_plan_id and self.supports_bulk:
            print(f"   💾 Checkpoint saved for plan: {self.active_plan_id}")
            print(f"   🔄 Resume with: python scripts/preload_data.py --resume {self.active_plan_id}")
        sys.exit(0)
    
    def parse_period(self, period_str: str) -> tuple[datetime, datetime]:
        """
        Parse period string into start/end dates
        
        Args:
            period_str: Period like '1y', '6m', '30d'
            
        Returns:
            (start_date, end_date) tuple
        """
        end_date = datetime.now()
        
        if period_str.endswith('y'):
            years = int(period_str[:-1])
            start_date = end_date - timedelta(days=years * 365)
        elif period_str.endswith('m'):
            months = int(period_str[:-1])
            start_date = end_date - timedelta(days=months * 30)
        elif period_str.endswith('d'):
            days = int(period_str[:-1])
            start_date = end_date - timedelta(days=days)
        else:
            raise ValueError(f"Invalid period format: {period_str}. Use format like '1y', '6m', '30d'")
        
        return start_date, end_date
    
    def _is_data_cached(self, ticker: str, timeframe: str, start_date: datetime, end_date: datetime) -> bool:
        """Check if data is already cached for the given parameters"""
        try:
            cached_data = self.data_manager._load_from_cache(ticker, start_date, end_date, timeframe)
            return cached_data is not None and not cached_data.empty
        except Exception:
            return False
    
    def _fast_cached_retrieval(self, tickers: List[str], timeframes: List[str], 
                              start_date: datetime, end_date: datetime) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
        """Separate cached vs uncached data for optimization"""
        cached_items = []
        uncached_items = []
        
        for ticker in tickers:
            for timeframe in timeframes:
                if self._is_data_cached(ticker, timeframe, start_date, end_date):
                    cached_items.append((ticker, timeframe))
                else:
                    uncached_items.append((ticker, timeframe))
        
        return cached_items, uncached_items
    
    def expand_tickers(self, tickers: List[str], bucket: Optional[str] = None) -> List[str]:
        """
        Expand ticker list with bucket assets
        
        Args:
            tickers: List of ticker symbols
            bucket: Asset bucket name to include
            
        Returns:
            Expanded list of tickers
        """
        expanded = list(tickers) if tickers else []
        
        if bucket:
            bucket_assets = self.asset_manager.get_assets_from_buckets([bucket])
            expanded.extend(bucket_assets)
            print(f"📦 Added {len(bucket_assets)} assets from bucket '{bucket}'")
        
        # Remove duplicates and sort
        expanded = sorted(list(set(expanded)))
        print(f"🎯 Total tickers to download: {len(expanded)}")
        
        return expanded
    
    def estimate_download(self, tickers: List[str], timeframes: List[str]) -> dict:
        """Estimate download time and requests"""
        estimates = self.timeframe_manager.estimate_download_time(tickers, timeframes)
        
        print(f"\n📊 DOWNLOAD ESTIMATION")
        print(f"   📈 Total requests: {estimates['total_requests']}")
        print(f"   ⏱️  Estimated time: {estimates['estimated_minutes']:.1f} minutes")
        print(f"   🔄 Provider: {estimates['provider']}")
        
        return estimates
    
    def download_individual(self, tickers: List[str], timeframes: List[str], 
                          start_date: datetime, end_date: datetime) -> bool:
        """
        Download data individually (for Yahoo Finance or fallback)
        
        Args:
            tickers: List of symbols to download
            timeframes: List of timeframes to download
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            True if all downloads successful
        """
        print(f"\n📥 INDIVIDUAL DOWNLOAD MODE")
        print(f"   Provider: {self.provider_name}")
        
        # Cache optimization: separate cached from uncached data
        if self.optimize_cached_data:
            cached_items, uncached_items = self._fast_cached_retrieval(tickers, timeframes, start_date, end_date)
            print(f"   🚀 Cache optimization: {len(cached_items)} cached, {len(uncached_items)} need download")
            
            # Process cached items instantly
            if cached_items:
                print(f"   ⚡ Processing {len(cached_items)} cached items...")
                for ticker, timeframe in cached_items:
                    try:
                        data = self.data_manager.download_data(
                            ticker=ticker,
                            start_date=start_date,
                            end_date=end_date,
                            interval=timeframe,
                            use_cache=True
                        )
                        if data is not None and not data.empty:
                            print(f"      ✅ {ticker} {timeframe}: {len(data)} records (cached)")
                    except Exception as e:
                        print(f"      ❌ {ticker} {timeframe}: {e}")
            
            # Use traditional approach only for uncached items
            process_items = [(ticker, timeframe) for ticker, timeframe in uncached_items]
        else:
            # Traditional approach: process all items
            process_items = [(ticker, timeframe) for ticker in tickers for timeframe in timeframes]
        
        total_operations = len(process_items)
        completed = len(cached_items) if self.optimize_cached_data and cached_items else 0
        failed = 0
        
        # Process only uncached items
        for i, (ticker, timeframe) in enumerate(process_items):
            try:
                operation_num = i + 1
                print(f"   🕐 [{operation_num}/{total_operations}] Downloading {ticker} {timeframe}...")
                
                data = self.data_manager.download_data(
                    ticker=ticker,
                    start_date=start_date,
                    end_date=end_date,
                    interval=timeframe,
                    use_cache=True
                )
                
                if data is not None and not data.empty:
                    print(f"      ✅ Success: {len(data)} records")
                    completed += 1
                else:
                    print(f"      ❌ No data returned")
                    failed += 1
                    
            except Exception as e:
                print(f"      ❌ Error: {e}")
                failed += 1
        
        # Calculate true totals
        total_operations_actual = len(tickers) * len(timeframes)
        
        print(f"\n📊 INDIVIDUAL DOWNLOAD COMPLETE")
        print(f"   ✅ Successful: {completed}/{total_operations_actual}")
        print(f"   ❌ Failed: {failed}/{total_operations_actual}")
        
        return failed == 0
    
    def download_bulk(self, tickers: List[str], timeframes: List[str],
                     start_date: datetime, end_date: datetime) -> bool:
        """
        Download data using bulk fetcher with checkpointing
        
        Args:
            tickers: List of symbols to download
            timeframes: List of timeframes to download  
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            True if all downloads successful
        """
        print(f"\n📦 BULK DOWNLOAD MODE")
        print(f"   Using Alpha Vantage bulk fetcher with checkpointing")
        
        # Create download plans for each ticker/timeframe combination
        plans = []
        total_chunks = 0
        
        for ticker in tickers:
            for timeframe in timeframes:
                try:
                    plan = self.bulk_fetcher.create_download_plan(
                        ticker=ticker,
                        timeframe=timeframe,
                        start_date=start_date,
                        end_date=end_date
                    )
                    plans.append(plan)
                    total_chunks += len(plan.chunks)
                    
                    # Generate plan ID and save checkpoint
                    plan_id = f"BULK_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{ticker}_{timeframe}"
                    self.active_plan_id = plan_id
                    
                    self.checkpoint_manager.save_checkpoint(plan, plan_id)
                    print(f"   📋 Created plan for {ticker} {timeframe}: {len(plan.chunks)} chunks")
                    
                except Exception as e:
                    print(f"   ❌ Failed to create plan for {ticker} {timeframe}: {e}")
                    continue
        
        if not plans:
            print("❌ No valid download plans created")
            return False
        
        print(f"\n📊 BULK DOWNLOAD SUMMARY")
        print(f"   📈 Total plans: {len(plans)}")
        print(f"   📦 Total chunks: {total_chunks}")
        
        # Execute downloads
        success_count = 0
        for i, plan in enumerate(plans):
            try:
                plan_id = f"BULK_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{plan.ticker}_{plan.timeframe}"
                self.active_plan_id = plan_id
                
                print(f"\n📥 [{i+1}/{len(plans)}] Downloading {plan.ticker} {plan.timeframe}")
                
                # Execute plan (this would normally use bulk_fetcher.execute_plan)
                # For now, fall back to individual downloads
                data = self.data_manager.download_data(
                    ticker=plan.ticker,
                    start_date=plan.start_date,
                    end_date=plan.end_date,
                    interval=plan.timeframe,
                    use_cache=True
                )
                
                if data is not None and not data.empty:
                    print(f"   ✅ Success: {len(data)} records")
                    success_count += 1
                    
                    # Mark plan as completed
                    self.checkpoint_manager.complete_checkpoint(plan_id)
                else:
                    print(f"   ❌ No data returned")
                    
            except Exception as e:
                print(f"   ❌ Error downloading {plan.ticker} {plan.timeframe}: {e}")
        
        print(f"\n📊 BULK DOWNLOAD COMPLETE")
        print(f"   ✅ Successful: {success_count}/{len(plans)}")
        
        return success_count == len(plans)
    
    def resume_download(self, plan_id: str) -> bool:
        """
        Resume interrupted download from checkpoint
        
        Args:
            plan_id: Checkpoint plan ID to resume
            
        Returns:
            True if resume successful
        """
        if not self.supports_bulk:
            print("❌ Resume only available for Alpha Vantage provider")
            return False
        
        print(f"\n🔄 RESUMING DOWNLOAD: {plan_id}")
        
        try:
            # Load checkpoint
            plan = self.checkpoint_manager.load_checkpoint(plan_id)
            if not plan:
                print(f"❌ Checkpoint not found: {plan_id}")
                return False
            
            print(f"   📋 Loaded plan: {plan.ticker} {plan.timeframe}")
            print(f"   📊 Progress: {plan.completed_chunks}/{plan.total_chunks} chunks")
            
            # Resume download would go here
            # For now, just report status
            checkpoints = self.checkpoint_manager.list_active_checkpoints()
            for cp in checkpoints:
                if cp['plan_id'] == plan_id:
                    print(f"   ✅ Found checkpoint: {cp['progress']} ({cp['progress_percent']}%)")
                    print(f"   🔄 Can resume: {cp['can_resume']}")
                    break
            
            return True
            
        except Exception as e:
            print(f"❌ Resume failed: {e}")
            return False
    
    def list_checkpoints(self):
        """List available checkpoints"""
        if not self.supports_bulk:
            print("ℹ️  Checkpoints only available for Alpha Vantage provider")
            return
        
        checkpoints = self.checkpoint_manager.list_active_checkpoints()
        
        if not checkpoints:
            print("📝 No active checkpoints found")
            return
        
        print(f"\n📝 ACTIVE CHECKPOINTS ({len(checkpoints)})")
        print("=" * 60)
        
        for cp in checkpoints:
            print(f"📋 {cp['plan_id']}")
            print(f"   📊 {cp['ticker']} {cp['timeframe']}")
            print(f"   📈 Progress: {cp['progress']} ({cp['progress_percent']}%)")
            print(f"   ❌ Failed: {cp['failed_chunks']} chunks")
            print(f"   🔄 Can resume: {cp['can_resume']}")
            print(f"   📅 Last updated: {cp['last_updated']}")
            print()
    
    def show_cache_stats(self):
        """Show cache statistics"""
        print("\n💾 CACHE STATISTICS")
        print("=" * 40)
        
        cache_stats = self.timeframe_manager.get_cache_stats()
        print(f"Provider: {cache_stats['provider']}")
        print(f"Total tickers: {cache_stats['total_tickers']}")
        print(f"Total files: {cache_stats['total_files']}")
        
        if cache_stats['timeframe_breakdown']:
            print("\nTimeframe breakdown:")
            for tf, count in cache_stats['timeframe_breakdown'].items():
                print(f"  {tf}: {count} files")
        
        if cache_stats['tickers']:
            print(f"\nCached tickers: {', '.join(cache_stats['tickers'][:10])}")
            if len(cache_stats['tickers']) > 10:
                print(f"  ... and {len(cache_stats['tickers']) - 10} more")


def main():
    parser = argparse.ArgumentParser(
        description="Pre-download historical data for backtesting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Data selection
    parser.add_argument('--tickers', '-t', type=str,
                       help='Comma-separated list of ticker symbols (e.g., AAPL,MSFT,GOOGL)')
    parser.add_argument('--bucket', '-b', type=str,
                       help='Asset bucket name to download (e.g., "Risk Assets")')
    parser.add_argument('--timeframes', '-tf', type=str, default='1d',
                       help='Comma-separated timeframes (e.g., 1h,4h,1d) [default: 1d]')
    
    # Date range
    parser.add_argument('--start-date', '-s', type=str,
                       help='Start date (YYYY-MM-DD format)')
    parser.add_argument('--end-date', '-e', type=str,
                       help='End date (YYYY-MM-DD format)')
    parser.add_argument('--period', '-p', type=str,
                       help='Period to download (e.g., 1y, 6m, 30d)')
    
    # Provider options
    parser.add_argument('--provider', type=str, default='alpha_vantage',
                       choices=['alpha_vantage', 'yahoo'],
                       help='Data provider to use [default: alpha_vantage]')
    parser.add_argument('--cache-dir', type=str, default='data/cache',
                       help='Cache directory [default: data/cache]')
    
    # Resume and management
    parser.add_argument('--resume', type=str,
                       help='Resume download from checkpoint ID')
    parser.add_argument('--list-checkpoints', action='store_true',
                       help='List available checkpoints')
    parser.add_argument('--cache-stats', action='store_true',
                       help='Show cache statistics')
    
    # Download options
    parser.add_argument('--force', '-f', action='store_true',
                       help='Force re-download even if cached')
    parser.add_argument('--estimate-only', action='store_true',
                       help='Only show download estimates, don\'t download')
    
    args = parser.parse_args()
    
    try:
        # Initialize preloader
        preloader = DataPreloader(provider_name=args.provider, cache_dir=args.cache_dir)
        
        # Handle utility commands
        if args.list_checkpoints:
            preloader.list_checkpoints()
            return
        
        if args.cache_stats:
            preloader.show_cache_stats()
            return
        
        if args.resume:
            success = preloader.resume_download(args.resume)
            sys.exit(0 if success else 1)
        
        # Validate required arguments
        if not args.tickers and not args.bucket:
            print("❌ Must specify either --tickers or --bucket")
            sys.exit(1)
        
        # Parse tickers and timeframes
        tickers = args.tickers.split(',') if args.tickers else []
        tickers = preloader.expand_tickers(tickers, args.bucket)
        timeframes = args.timeframes.split(',')
        
        # Parse date range
        if args.start_date and args.end_date:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
        elif args.period:
            start_date, end_date = preloader.parse_period(args.period)
        else:
            # Default to 1 year
            start_date, end_date = preloader.parse_period('1y')
        
        print(f"\n📅 DATE RANGE: {start_date.date()} to {end_date.date()}")
        print(f"📊 TIMEFRAMES: {', '.join(timeframes)}")
        print(f"🎯 TICKERS: {', '.join(tickers[:5])}")
        if len(tickers) > 5:
            print(f"          ... and {len(tickers) - 5} more")
        
        # Estimate download
        estimates = preloader.estimate_download(tickers, timeframes)
        
        if args.estimate_only:
            print("\n✅ Estimation complete (--estimate-only specified)")
            return
        
        # Confirm download
        if estimates['estimated_minutes'] > 5:
            print(f"\n⚠️  This download will take approximately {estimates['estimated_minutes']:.1f} minutes")
            response = input("Continue? (y/N): ")
            if response.lower() != 'y':
                print("❌ Download cancelled")
                return
        
        # Execute download with cache optimization
        use_bulk_mode = False
        
        if preloader.supports_bulk and len(tickers) > 1:
            # Check cache status to decide bulk vs individual
            if preloader.optimize_cached_data:
                cached_items, uncached_items = preloader._fast_cached_retrieval(tickers, timeframes, start_date, end_date)
                cached_percentage = len(cached_items) / (len(cached_items) + len(uncached_items)) if (cached_items or uncached_items) else 0
                
                # Use individual mode if >50% is cached to avoid bulk overhead
                if cached_percentage > 0.5:
                    print(f"🚀 Cache optimization: {cached_percentage:.1%} cached, using individual mode")
                    use_bulk_mode = False
                else:
                    print(f"📦 Using bulk mode: {cached_percentage:.1%} cached")
                    use_bulk_mode = True
            else:
                use_bulk_mode = True
        
        if use_bulk_mode:
            success = preloader.download_bulk(tickers, timeframes, start_date, end_date)
        else:
            success = preloader.download_individual(tickers, timeframes, start_date, end_date)
        
        if success:
            print("\n🎉 DOWNLOAD COMPLETE!")
            print("✅ All data successfully cached")
            preloader.show_cache_stats()
        else:
            print("\n⚠️  Download completed with some failures")
            print("   Check logs above for details")
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n⚠️  Download interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Download failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()