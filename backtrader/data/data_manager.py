import yfinance as yf
import backtrader as bt
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any
import pickle
import os
import logging
from datetime import datetime, timedelta

from .providers.registry import ProviderRegistry
from .providers.yahoo_finance.provider import YahooFinanceProvider
from .providers.alpha_vantage.provider import AlphaVantageProvider
from .timeframe_manager import TimeframeManager

logger = logging.getLogger(__name__)


class DataManager:
    def __init__(self, cache_dir: str = "data/cache", provider_name: str = None):
        # Initialize provider registry and set up providers
        self.registry = ProviderRegistry()
        
        # Register available providers
        self.registry.register('yahoo', YahooFinanceProvider())
        
        # Register Alpha Vantage provider if API key is available
        try:
            self.registry.register('alpha_vantage', AlphaVantageProvider())
        except ValueError as e:
            logger.warning(f"Alpha Vantage provider not available: {e}")
        
        # Set active provider from parameter, environment, or default
        provider = provider_name or os.getenv('DATA_PROVIDER', 'yahoo')
        
        try:
            self.registry.set_active(provider)
            logger.info(f"Using data provider: {provider}")
        except ValueError as e:
            logger.warning(f"Failed to set provider {provider}: {e}. Falling back to yahoo.")
            self.registry.set_active('yahoo')
        
        # Initialize caching with provider-specific directories
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.data_cache: Dict[str, Any] = {}
        
        # Initialize TimeframeManager for multi-timeframe operations
        self.timeframe_manager = TimeframeManager(data_manager=self, cache_dir=str(self.cache_dir), provider_name=provider)
    
    def _get_cache_filename(self, ticker: str, start_date: datetime, end_date: datetime, 
                           timeframe: str = '1d') -> Path:
        """Get provider-specific cache filename"""
        provider_name = self.registry.get_active_name()
        start_str = start_date.strftime('%Y%m%d')
        end_str = end_date.strftime('%Y%m%d')
        
        # Create provider-specific cache directory
        provider_cache_dir = self.cache_dir / provider_name / ticker / timeframe
        provider_cache_dir.mkdir(parents=True, exist_ok=True)
        
        return provider_cache_dir / f"{ticker}_{timeframe}_{start_str}_{end_str}.pkl"
    
    def _load_from_cache(self, ticker: str, start_date: datetime, end_date: datetime, 
                        timeframe: str = '1d') -> Optional[pd.DataFrame]:
        """Load data from provider-specific cache with smart matching"""
        # First try exact match
        cache_file = self._get_cache_filename(ticker, start_date, end_date, timeframe)
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                    
                # Verify provider attribution
                provider_name = self.registry.get_active_name()
                if hasattr(data, 'attrs') and 'provider_source' in data.attrs:
                    if data.attrs['provider_source'] != provider_name:
                        logger.warning(f"Cache provider mismatch for {ticker}. Expected {provider_name}, "
                                     f"found {data.attrs['provider_source']}. Ignoring cache.")
                        return None
                        
                print(f"Loaded {ticker} from {provider_name} cache (exact match)")
                return data
            except Exception as e:
                logger.error(f"Error loading exact cache for {ticker}: {e}")
        
        # Try smart matching - find cached files that contain the requested range
        return self._load_from_cache_smart_match(ticker, start_date, end_date, timeframe)
    
    def _load_from_cache_smart_match(self, ticker: str, start_date: datetime, end_date: datetime, 
                                   timeframe: str = '1d') -> Optional[pd.DataFrame]:
        """Smart cache matching - find cached files that contain the requested range"""
        provider_name = self.registry.get_active_name()
        cache_base_dir = Path(self.cache_dir) / provider_name / ticker / timeframe
        
        if not cache_base_dir.exists():
            return None
        
        # Look for cached files that might contain our date range
        for cache_file in cache_base_dir.glob(f"{ticker}_{timeframe}_*.pkl"):
            try:
                # Parse filename to extract date range
                filename = cache_file.stem
                parts = filename.split('_')
                if len(parts) >= 4:
                    cached_start_str = parts[-2]
                    cached_end_str = parts[-1]
                    
                    # Parse cached date range
                    cached_start = datetime.strptime(cached_start_str, '%Y%m%d')
                    cached_end = datetime.strptime(cached_end_str, '%Y%m%d')
                    
                    # Check if cached range contains our requested range
                    if cached_start <= start_date and cached_end >= end_date:
                        # Load and filter the cached data
                        with open(cache_file, 'rb') as f:
                            data = pickle.load(f)
                        
                        # Verify provider attribution
                        if hasattr(data, 'attrs') and 'provider_source' in data.attrs:
                            if data.attrs['provider_source'] != provider_name:
                                continue
                        
                        # Filter to requested date range
                        filtered_data = data[(data.index >= pd.Timestamp(start_date)) & 
                                           (data.index <= pd.Timestamp(end_date))]
                        
                        if not filtered_data.empty:
                            print(f"Loaded {ticker} from {provider_name} cache (smart match: {cached_start_str}-{cached_end_str})")
                            return filtered_data
                        
            except Exception as e:
                logger.debug(f"Error parsing cache file {cache_file}: {e}")
                continue
        
        return None
    
    def _save_to_cache(self, ticker: str, start_date: datetime, end_date: datetime, 
                      data: pd.DataFrame, timeframe: str = '1d'):
        """Save data to provider-specific cache with attribution"""
        # Add provider metadata to dataframe
        provider_name = self.registry.get_active_name()
        data.attrs['provider_source'] = provider_name
        data.attrs['cache_timestamp'] = datetime.now().isoformat()
        data.attrs['timeframe'] = timeframe
        data.attrs['ticker'] = ticker
        
        cache_file = self._get_cache_filename(ticker, start_date, end_date, timeframe)
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
            logger.debug(f"Saved {ticker} to {provider_name} cache")
        except Exception as e:
            logger.error(f"Error saving cache for {ticker}: {e}")
    
    def download_data(self, ticker: str, start_date: datetime, end_date: datetime, 
                     use_cache: bool = True, interval: str = '1d') -> Optional[pd.DataFrame]:
        """
        Download data using the active provider. Maintains backward compatibility.
        """
        provider = self.registry.get_active()
        
        # Check if provider supports requested timeframe
        if interval not in provider.get_supported_timeframes():
            logger.warning(
                f"Provider {provider.name} doesn't support {interval}. "
                f"Available: {provider.get_supported_timeframes()}. Using daily data."
            )
            interval = '1d'
        
        if use_cache:
            cached_data = self._load_from_cache(ticker, start_date, end_date, interval)
            if cached_data is not None:
                print(f"Loaded {ticker} from {provider.name} cache")
                return cached_data
        
        try:
            # Handle both datetime and date objects
            start_str = start_date.date() if hasattr(start_date, 'date') else start_date
            end_str = end_date.date() if hasattr(end_date, 'date') else end_date
            print(f"Downloading {ticker} data from {start_str} to {end_str} "
                  f"using {provider.name} provider (timeframe: {interval})")
            
            # Use provider to fetch data
            data = provider.fetch_data(ticker, interval, start_date, end_date + timedelta(days=1))
            
            if data is None or data.empty:
                print(f"No data found for {ticker}")
                return None
            
            data = data.dropna()
            
            if use_cache:
                self._save_to_cache(ticker, start_date, end_date, data, interval)
            
            return data
            
        except Exception as e:
            logger.error(f"Error downloading data for {ticker}: {e}")
            print(f"Error downloading data for {ticker}: {e}")
            return None
    
    def get_data(self, ticker: str, start_date: datetime, end_date: datetime, 
                use_cache: bool = True) -> Optional[bt.feeds.PandasData]:
        
        df = self.download_data(ticker, start_date, end_date, use_cache)
        
        if df is None or df.empty:
            return None
        
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        
        data = bt.feeds.PandasData(
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
        
        return data
    
    def get_multiple_data(self, tickers: list, start_date: datetime, end_date: datetime,
                         use_cache: bool = True) -> Dict[str, bt.feeds.PandasData]:
        
        data_feeds = {}
        
        for ticker in tickers:
            data = self.get_data(ticker, start_date, end_date, use_cache)
            if data is not None:
                data_feeds[ticker] = data
            else:
                print(f"Failed to load data for {ticker}")
        
        return data_feeds
    
    def clear_cache(self, ticker: str = None, provider: str = None):
        """Clear cache files for specific ticker/provider or all"""
        provider_name = provider or self.registry.get_active_name()
        provider_cache_dir = self.cache_dir / provider_name
        
        if not provider_cache_dir.exists():
            print(f"No cache directory found for provider {provider_name}")
            return
            
        if ticker:
            # Clear cache for specific ticker
            ticker_cache_dir = provider_cache_dir / ticker
            if ticker_cache_dir.exists():
                cache_files = list(ticker_cache_dir.rglob("*.pkl"))
            else:
                cache_files = []
        else:
            # Clear all cache for the provider
            cache_files = list(provider_cache_dir.rglob("*.pkl"))
        
        for cache_file in cache_files:
            try:
                cache_file.unlink()
                print(f"Deleted cache file: {cache_file}")
            except Exception as e:
                print(f"Error deleting {cache_file}: {e}")
                
        # Clean up empty directories
        if ticker:
            ticker_cache_dir = provider_cache_dir / ticker
            if ticker_cache_dir.exists() and not any(ticker_cache_dir.iterdir()):
                ticker_cache_dir.rmdir()
    
    def list_cached_data(self) -> Dict[str, Dict[str, list]]:
        """List cached data organized by provider and ticker"""
        cache_info = {}
        
        for provider_dir in self.cache_dir.iterdir():
            if provider_dir.is_dir():
                provider_name = provider_dir.name
                cache_info[provider_name] = {}
                
                for ticker_dir in provider_dir.iterdir():
                    if ticker_dir.is_dir():
                        ticker = ticker_dir.name
                        cache_info[provider_name][ticker] = []
                        
                        for timeframe_dir in ticker_dir.iterdir():
                            if timeframe_dir.is_dir():
                                timeframe = timeframe_dir.name
                                
                                for cache_file in timeframe_dir.glob("*.pkl"):
                                    cache_info[provider_name][ticker].append({
                                        'timeframe': timeframe,
                                        'file': cache_file.name,
                                        'file_size': cache_file.stat().st_size,
                                        'modified': datetime.fromtimestamp(cache_file.stat().st_mtime)
                                    })
        
        return cache_info
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about current provider configuration"""
        provider = self.registry.get_active()
        return {
            'active_provider': self.registry.get_active_name(),
            'supported_timeframes': provider.get_supported_timeframes(),
            'rate_limits': provider.get_rate_limit(),
            'cache_directory': str(self.cache_dir / self.registry.get_active_name())
        }