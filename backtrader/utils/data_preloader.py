"""
Data pre-loader utility for optimized backtesting
Pre-loads all required timeframes with sufficient lookback to avoid cache misses
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import backtrader as bt

logger = logging.getLogger(__name__)


class DataPreloader:
    """
    Pre-loads all required data for backtesting to avoid runtime downloads
    """
    
    def __init__(self, data_manager, lookback_days: int = 90):
        """
        Initialize data preloader
        
        Args:
            data_manager: DataManager instance
            lookback_days: Extra days to load before start_date for technical analysis
        """
        self.data_manager = data_manager
        self.lookback_days = lookback_days
        self.preloaded_data = {}
        
    def preload_all_timeframes(
        self,
        assets: List[str],
        timeframes: List[str],
        start_date: datetime,
        end_date: datetime,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Pre-load all timeframes for all assets with lookback buffer
        
        Args:
            assets: List of asset symbols
            timeframes: List of timeframes (e.g., ['1d', '4h', '1h'])
            start_date: Backtest start date
            end_date: Backtest end date
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dict mapping assets to their multi-timeframe data
        """
        # Extend start date by lookback period
        extended_start = start_date - timedelta(days=self.lookback_days)
        
        logger.info(f"Pre-loading {len(assets)} assets with {len(timeframes)} timeframes")
        logger.info(f"Date range: {extended_start.date()} to {end_date.date()} "
                   f"(includes {self.lookback_days}-day lookback)")
        
        total_operations = len(assets) * len(timeframes)
        completed = 0
        
        for asset in assets:
            self.preloaded_data[asset] = {}
            
            if hasattr(self.data_manager, 'timeframe_manager'):
                # Use TimeframeManager for efficient multi-timeframe loading
                try:
                    logger.info(f"Pre-loading {asset} with TimeframeManager...")
                    
                    multi_tf_data = self.data_manager.timeframe_manager.get_multi_timeframe_data(
                        ticker=asset,
                        timeframes=timeframes,
                        start_date=extended_start,
                        end_date=end_date
                    )
                    
                    self.preloaded_data[asset] = multi_tf_data
                    completed += len(timeframes)
                    
                    if progress_callback:
                        progress_callback(f"Loaded {asset}", int((completed / total_operations) * 100))
                        
                except Exception as e:
                    logger.error(f"Failed to pre-load {asset}: {e}")
                    # Try individual timeframe loading as fallback
                    self._load_individual_timeframes(
                        asset, timeframes, extended_start, end_date, 
                        progress_callback, completed, total_operations
                    )
            else:
                # Fallback to individual timeframe loading
                self._load_individual_timeframes(
                    asset, timeframes, extended_start, end_date,
                    progress_callback, completed, total_operations
                )
        
        logger.info(f"Pre-loading complete: {len(self.preloaded_data)} assets loaded")
        return self.preloaded_data
    
    def _load_individual_timeframes(
        self, asset: str, timeframes: List[str], 
        start_date: datetime, end_date: datetime,
        progress_callback: Optional[callable],
        completed: int, total_operations: int
    ):
        """Load timeframes individually as fallback"""
        for tf in timeframes:
            try:
                data = self.data_manager.download_data(
                    asset, start_date, end_date, interval=tf
                )
                if data is not None and not data.empty:
                    self.preloaded_data[asset][tf] = data
                    
                completed += 1
                if progress_callback:
                    progress_callback(
                        f"Loaded {asset} {tf}", 
                        int((completed / total_operations) * 100)
                    )
                    
            except Exception as e:
                logger.error(f"Failed to load {asset} {tf}: {e}")
                completed += 1
    
    def get_data_for_analysis(
        self, asset: str, current_date: datetime, 
        lookback_days: int = 90, timeframes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get pre-loaded data for analysis, filtered to specific date range
        
        Args:
            asset: Asset symbol
            current_date: Current date in backtest
            lookback_days: Days to look back from current date
            timeframes: Specific timeframes to return (None = all)
            
        Returns:
            Dict of timeframe -> filtered DataFrame
        """
        if asset not in self.preloaded_data:
            logger.warning(f"Asset {asset} not in pre-loaded data")
            return {}
        
        start_date = current_date - timedelta(days=lookback_days)
        result = {}
        
        asset_data = self.preloaded_data[asset]
        target_timeframes = timeframes or list(asset_data.keys())
        
        for tf in target_timeframes:
            if tf in asset_data:
                df = asset_data[tf]
                if not df.empty:
                    # Convert dates to pandas timestamps for comparison
                    import pandas as pd
                    
                    # Handle both datetime and date objects
                    if hasattr(start_date, 'date'):
                        start_ts = pd.Timestamp(start_date)
                    else:
                        start_ts = pd.Timestamp(start_date)
                        
                    if hasattr(current_date, 'date'):
                        current_ts = pd.Timestamp(current_date)
                    else:
                        current_ts = pd.Timestamp(current_date)
                    
                    # Filter to requested date range
                    try:
                        filtered = df[(df.index >= start_ts) & (df.index <= current_ts)]
                    except Exception as e:
                        logger.error(f"Date filtering failed for {asset} {tf}: {e}")
                        logger.error(f"  df.index type: {type(df.index[0])}")
                        logger.error(f"  start_ts type: {type(start_ts)}")
                        logger.error(f"  current_ts type: {type(current_ts)}")
                        continue
                    if not filtered.empty:
                        result[tf] = filtered
        
        return result
    
    def create_backtrader_feeds(
        self, cerebro: bt.Cerebro, 
        assets: List[str],
        start_date: datetime,
        end_date: datetime,
        primary_timeframe: str = '1d'
    ) -> Dict[str, bt.feeds.PandasData]:
        """
        Create backtrader data feeds from pre-loaded data
        
        Args:
            cerebro: Backtrader Cerebro instance
            assets: List of assets to add
            start_date: Backtest start date
            end_date: Backtest end date
            primary_timeframe: Primary timeframe for backtesting
            
        Returns:
            Dict of asset -> data feed
        """
        feeds = {}
        
        for asset in assets:
            if asset in self.preloaded_data and primary_timeframe in self.preloaded_data[asset]:
                df = self.preloaded_data[asset][primary_timeframe]
                
                if not df.empty:
                    # Create backtrader feed
                    data_feed = bt.feeds.PandasData(
                        dataname=df,
                        datetime=None,
                        open='Open',
                        high='High',
                        low='Low',
                        close='Close',
                        volume='Volume',
                        openinterest=None,
                        fromdate=start_date,
                        todate=end_date
                    )
                    
                    cerebro.adddata(data_feed, name=asset)
                    feeds[asset] = data_feed
                    
                    logger.info(f"Added {asset} to cerebro with {len(df)} {primary_timeframe} records")
                else:
                    logger.warning(f"Empty data for {asset} {primary_timeframe}")
            else:
                logger.warning(f"No pre-loaded data for {asset} {primary_timeframe}")
        
        return feeds
    
    def get_memory_usage(self) -> Dict[str, float]:
        """
        Estimate memory usage of pre-loaded data
        
        Returns:
            Dict with memory statistics in MB
        """
        import sys
        
        total_size = 0
        asset_sizes = {}
        
        for asset, timeframes in self.preloaded_data.items():
            asset_size = 0
            for tf, df in timeframes.items():
                if hasattr(df, 'memory_usage'):
                    size_bytes = df.memory_usage(deep=True).sum()
                    asset_size += size_bytes
            
            asset_sizes[asset] = asset_size / 1024 / 1024  # Convert to MB
            total_size += asset_size
        
        return {
            'total_mb': total_size / 1024 / 1024,
            'assets': asset_sizes,
            'num_assets': len(self.preloaded_data),
            'avg_per_asset_mb': (total_size / len(self.preloaded_data) / 1024 / 1024) 
                                if self.preloaded_data else 0
        }