import logging
import os
from typing import Dict, List, Optional, Callable
from datetime import datetime
import pandas as pd

# Import at runtime to avoid circular imports

logger = logging.getLogger(__name__)


class TimeframeManager:
    """
    High-level interface for multi-timeframe data access
    Provides bulk downloading, progress tracking, and multi-timeframe orchestration
    """
    
    def __init__(self, data_manager=None, cache_dir: str = "data/cache", provider_name: str = None):
        if data_manager is not None:
            # Use provided data_manager (preferred to avoid circular imports)
            self.data_manager = data_manager
        else:
            # Create new data_manager (fallback)
            from .providers.registry import ProviderRegistry
            from .providers.yahoo_finance.provider import YahooFinanceProvider
            
            self.registry = ProviderRegistry()
            self.registry.register('yahoo', YahooFinanceProvider())
            
            try:
                from .providers.alpha_vantage.provider import AlphaVantageProvider
                self.registry.register('alpha_vantage', AlphaVantageProvider())
            except ValueError:
                pass
            
            provider = provider_name or 'yahoo'
            try:
                self.registry.set_active(provider)
            except ValueError:
                self.registry.set_active('yahoo')
            
            self.data_manager = None  # Will use registry directly
        
        # Get provider info for optimization
        if self.data_manager:
            self.provider_info = self.data_manager.get_provider_info()
            self.provider_name = self.provider_info['active_provider']
            self.supported_timeframes = self.provider_info['supported_timeframes']
        else:
            # Use registry directly
            active_provider = self.registry.get_active()
            self.provider_name = self.registry.get_active_name()
            self.supported_timeframes = active_provider.get_supported_timeframes()
            self.provider_info = {
                'active_provider': self.provider_name,
                'supported_timeframes': self.supported_timeframes,
                'rate_limits': active_provider.get_rate_limit()
            }
        
        logger.info(f"TimeframeManager initialized with {self.provider_name} provider")
        logger.info(f"Supported timeframes: {self.supported_timeframes}")
    
    def get_multi_timeframe_data(
        self, 
        ticker: str, 
        timeframes: List[str],
        start_date: datetime,
        end_date: datetime,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Get data for multiple timeframes with progress tracking
        
        Args:
            ticker: Symbol to fetch
            timeframes: List of timeframes to fetch
            start_date: Start date for data
            end_date: End date for data  
            progress_callback: Optional callback function(timeframe, progress_percent)
            
        Returns:
            Dict mapping timeframes to DataFrames
        """
        logger.info(f"Fetching multi-timeframe data for {ticker}: {timeframes}")
        
        # Validate timeframes
        unsupported = [tf for tf in timeframes if tf not in self.supported_timeframes]
        if unsupported:
            logger.warning(f"Unsupported timeframes for {self.provider_name}: {unsupported}")
            logger.warning(f"Will skip: {unsupported}")
            timeframes = [tf for tf in timeframes if tf in self.supported_timeframes]
        
        if not timeframes:
            logger.error("No supported timeframes to fetch")
            return {}
        
        results = {}
        total_timeframes = len(timeframes)
        
        for i, timeframe in enumerate(timeframes):
            try:
                if progress_callback:
                    progress_callback(f"Fetching {ticker} {timeframe}", 
                                    int((i / total_timeframes) * 100))
                
                logger.info(f"Fetching {ticker} data for timeframe: {timeframe}")
                if self.data_manager:
                    data = self.data_manager.download_data(
                        ticker=ticker,
                        start_date=start_date, 
                        end_date=end_date,
                        interval=timeframe,
                        use_cache=True
                    )
                else:
                    # Use provider directly
                    active_provider = self.registry.get_active()
                    data = active_provider.fetch_data(
                        ticker=ticker,
                        timeframe=timeframe,
                        start_date=start_date,
                        end_date=end_date
                    )
                
                if data is not None and not data.empty:
                    results[timeframe] = data
                    logger.info(f"Successfully fetched {len(data)} records for {ticker} {timeframe}")
                else:
                    logger.warning(f"No data returned for {ticker} {timeframe}")
                    
            except Exception as e:
                logger.error(f"Error fetching {ticker} {timeframe} data: {e}")
                continue
        
        if progress_callback:
            progress_callback("Complete", 100)
            
        logger.info(f"Multi-timeframe fetch complete. Retrieved {len(results)}/{total_timeframes} timeframes")
        return results
    
    def batch_download(
        self,
        tickers: List[str],
        timeframes: List[str], 
        start_date: datetime,
        end_date: datetime,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Download data for multiple tickers and timeframes efficiently
        
        Args:
            tickers: List of symbols to fetch
            timeframes: List of timeframes to fetch
            start_date: Start date for data
            end_date: End date for data
            progress_callback: Optional callback function(status, progress_percent)
            
        Returns:
            Dict mapping tickers to timeframe data: {ticker: {timeframe: DataFrame}}
        """
        logger.info(f"Starting batch download: {len(tickers)} tickers × {len(timeframes)} timeframes")
        
        results = {}
        total_operations = len(tickers) * len(timeframes)
        completed_operations = 0
        
        for ticker in tickers:
            try:
                if progress_callback:
                    progress_callback(f"Processing {ticker}", 
                                    int((completed_operations / total_operations) * 100))
                
                ticker_data = self.get_multi_timeframe_data(
                    ticker=ticker,
                    timeframes=timeframes,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if ticker_data:
                    results[ticker] = ticker_data
                    logger.info(f"Successfully downloaded {len(ticker_data)} timeframes for {ticker}")
                else:
                    logger.warning(f"No data retrieved for {ticker}")
                    
                completed_operations += len(timeframes)
                
            except Exception as e:
                logger.error(f"Error in batch download for {ticker}: {e}")
                completed_operations += len(timeframes)
                continue
        
        if progress_callback:
            progress_callback("Batch download complete", 100)
            
        logger.info(f"Batch download complete. Retrieved data for {len(results)}/{len(tickers)} tickers")
        return results
    
    def get_cached_timeframe_data(
        self,
        ticker: str,
        timeframes: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, pd.DataFrame]:
        """
        Get multi-timeframe data from cache only (no downloads)
        
        Returns:
            Dict mapping timeframes to cached DataFrames, empty dict if no cache
        """
        results = {}
        
        for timeframe in timeframes:
            try:
                if self.data_manager:
                    data = self.data_manager.download_data(
                        ticker=ticker,
                        start_date=start_date,
                        end_date=end_date, 
                        interval=timeframe,
                        use_cache=True
                    )
                else:
                    # Use provider directly
                    active_provider = self.registry.get_active()
                    data = active_provider.fetch_data(
                        ticker=ticker,
                        timeframe=timeframe,
                        start_date=start_date,
                        end_date=end_date
                    )
                
                # Check if data came from cache (has provider attribution)
                if (data is not None and not data.empty and 
                    hasattr(data, 'attrs') and 'provider_source' in data.attrs):
                    results[timeframe] = data
                    
            except Exception as e:
                logger.debug(f"No cached data for {ticker} {timeframe}: {e}")
                continue
                
        return results
    
    def clear_timeframe_cache(self, ticker: str = None, timeframes: List[str] = None):
        """
        Clear cache for specific ticker/timeframes or all data
        
        Args:
            ticker: Specific ticker to clear (None for all)
            timeframes: Specific timeframes to clear (None for all)
        """
        if ticker is None:
            # Clear entire provider cache
            if self.data_manager:
                self.data_manager.clear_cache()
            logger.info(f"Cleared entire {self.provider_name} cache")
        else:
            # Clear specific ticker cache
            if self.data_manager:
                self.data_manager.clear_cache(ticker=ticker)
            logger.info(f"Cleared cache for {ticker}")
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics for the current provider"""
        if self.data_manager:
            cache_info = self.data_manager.list_cached_data()
            provider_cache = cache_info.get(self.provider_name, {})
        else:
            provider_cache = {}
        
        stats = {
            'provider': self.provider_name,
            'total_tickers': len(provider_cache),
            'total_files': sum(len(files) for files in provider_cache.values()),
            'timeframe_breakdown': {},
            'tickers': list(provider_cache.keys())
        }
        
        # Count files by timeframe
        for ticker, files in provider_cache.items():
            for file_info in files:
                timeframe = file_info['timeframe']
                if timeframe not in stats['timeframe_breakdown']:
                    stats['timeframe_breakdown'][timeframe] = 0
                stats['timeframe_breakdown'][timeframe] += 1
        
        return stats
    
    def validate_timeframe_compatibility(self, timeframes: List[str]) -> Dict[str, bool]:
        """
        Validate which timeframes are supported by the current provider
        
        Returns:
            Dict mapping timeframes to support status
        """
        return {tf: tf in self.supported_timeframes for tf in timeframes}
    
    def estimate_download_time(self, tickers: List[str], timeframes: List[str]) -> Dict[str, float]:
        """
        Estimate download time based on provider rate limits
        
        Returns:
            Dict with time estimates in seconds
        """
        rate_limits = self.provider_info['rate_limits']
        requests_per_minute = rate_limits.get('requests_per_minute', 60)
        
        total_requests = len(tickers) * len(timeframes)
        
        # Add some overhead for processing time
        estimated_seconds = (total_requests / requests_per_minute) * 60 * 1.2
        
        return {
            'total_requests': total_requests,
            'requests_per_minute': requests_per_minute,
            'estimated_seconds': estimated_seconds,
            'estimated_minutes': estimated_seconds / 60,
            'provider': self.provider_name
        }
    
    def get_provider_info(self) -> Dict:
        """Get information about the current provider"""
        return self.provider_info