import os
import logging
import time
from typing import Dict, List
from datetime import datetime, timedelta
import pandas as pd
import requests

from ..base import DataProvider

logger = logging.getLogger(__name__)


class AlphaVantageProvider(DataProvider):
    """
    Alpha Vantage data provider with rate limiting and multi-timeframe support
    
    Features:
    - 75 requests/minute rate limiting
    - Support for 1h, 4h, 1d timeframes
    - Automatic retry with exponential backoff
    """
    
    def __init__(self):
        self.api_key = os.getenv('ALPHA_VANTAGE_API_KEY') or os.getenv('ALPHA_VINTAGE_KEY')
        if not self.api_key:
            raise ValueError("ALPHA_VANTAGE_API_KEY environment variable is required")
            
        self.base_url = "https://www.alphavantage.co/query"
        self.last_request_time = 0
        self.min_request_interval = 60 / 75  # 75 requests per minute
        
        # Request session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BacktraderHedgeFund/1.0'
        })
        
        # Initialize asset bucket manager for crypto detection
        # Import here to avoid circular imports
        from ...asset_buckets import AssetBucketManager
        self.asset_manager = AssetBucketManager()
        
        logger.info("AlphaVantageProvider initialized with rate limit: 75 req/min")
    
    @property
    def name(self) -> str:
        return "alpha_vantage"
    
    def get_supported_timeframes(self) -> List[str]:
        """Return supported timeframes"""
        return ['1h', '4h', '1d']
    
    def _is_crypto_symbol(self, ticker: str) -> bool:
        """Check if ticker is a cryptocurrency using AssetBucketManager"""
        ticker_upper = ticker.upper()
        
        # Check direct match first
        crypto_assets = self.asset_manager.filter_assets_by_type([ticker_upper], 'crypto')
        if len(crypto_assets) > 0:
            return True
        
        # Check if it's a USD pair (e.g., BTCUSD -> BTC)
        if ticker_upper.endswith('USD') and len(ticker_upper) > 3:
            base_symbol = ticker_upper[:-3]  # Remove 'USD'
            crypto_base = self.asset_manager.filter_assets_by_type([base_symbol], 'crypto')
            return len(crypto_base) > 0
            
        return False
    
    def get_rate_limit(self) -> Dict[str, int]:
        """Return rate limit configuration"""
        return {
            'requests_per_minute': 75,
            'requests_per_hour': 4500,
            'requests_per_day': 108000
        }
    
    def validate_ticker(self, ticker: str) -> bool:
        """Basic ticker validation"""
        if not ticker or not isinstance(ticker, str):
            return False
        return len(ticker) >= 1 and len(ticker) <= 10
    
    def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def _make_request(self, params: Dict, max_retries: int = 3) -> Dict:
        """Make API request with rate limiting and retries"""
        self._rate_limit()
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(self.base_url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                # Check for API errors
                if 'Error Message' in data:
                    raise Exception(f"Alpha Vantage API Error: {data['Error Message']}")
                
                if 'Note' in data:
                    if 'call frequency' in data['Note']:
                        logger.warning("Alpha Vantage rate limit hit, waiting...")
                        time.sleep(60)  # Wait 1 minute
                        continue
                    else:
                        logger.warning(f"Alpha Vantage Note: {data['Note']}")
                
                return data
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    time.sleep(wait_time)
                else:
                    raise
                    
        raise Exception("Max retries exceeded")
    
    def _convert_timeframe(self, timeframe: str) -> str:
        """Convert our timeframe format to Alpha Vantage format"""
        mapping = {
            '1h': '60min',
            '4h': '240min',  # We'll construct this from 60min data
            '1d': 'daily'
        }
        return mapping.get(timeframe, 'daily')
    
    def fetch_data(self, ticker: str, timeframe: str, 
                  start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Fetch data from Alpha Vantage"""
        
        if not self.validate_ticker(ticker):
            logger.error(f"Invalid ticker: {ticker}")
            return pd.DataFrame()
        
        if timeframe not in self.get_supported_timeframes():
            logger.error(f"Unsupported timeframe: {timeframe}")
            return pd.DataFrame()
        
        try:
            if self._is_crypto_symbol(ticker):
                if timeframe == '1d':
                    return self._fetch_crypto_daily_data(ticker, start_date, end_date)
                else:
                    return self._fetch_crypto_intraday_data(ticker, timeframe, start_date, end_date)
            else:
                if timeframe == '1d':
                    return self._fetch_daily_data(ticker, start_date, end_date)
                else:
                    return self._fetch_intraday_data(ticker, timeframe, start_date, end_date)
                
        except Exception as e:
            logger.error(f"Error fetching {ticker} data: {e}")
            return pd.DataFrame()
    
    def _fetch_daily_data(self, ticker: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Fetch daily data"""
        params = {
            'function': 'TIME_SERIES_DAILY',
            'symbol': ticker,
            'apikey': self.api_key,
            'outputsize': 'full'
        }
        
        data = self._make_request(params)
        
        if 'Time Series (Daily)' not in data:
            logger.warning(f"No daily data found for {ticker}")
            return pd.DataFrame()
        
        time_series = data['Time Series (Daily)']
        df = pd.DataFrame.from_dict(time_series, orient='index')
        
        # Clean up column names and data types
        df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        df.index = pd.to_datetime(df.index)
        df = df.astype(float)
        
        # Filter by date range
        df = df[(df.index >= start_date) & (df.index <= end_date)]
        df = df.sort_index()
        
        # Add provider attribution
        df.attrs['provider_source'] = self.name
        df.attrs['timeframe'] = '1d'
        df.attrs['ticker'] = ticker
        df.attrs['asset_type'] = 'stock'
        
        logger.info(f"Fetched {len(df)} daily records for {ticker}")
        return df
    
    def _fetch_intraday_data(self, ticker: str, timeframe: str, 
                           start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Fetch intraday data (1h, 4h)"""
        
        if timeframe == '4h':
            # For 4h data, we'll fetch 1h data and resample
            base_timeframe = '1h'
        else:
            base_timeframe = timeframe
            
        av_interval = self._convert_timeframe(base_timeframe)
        
        params = {
            'function': 'TIME_SERIES_INTRADAY',
            'symbol': ticker,
            'interval': av_interval,
            'apikey': self.api_key,
            'outputsize': 'full'
        }
        
        data = self._make_request(params)
        
        time_series_key = f'Time Series ({av_interval})'
        if time_series_key not in data:
            logger.warning(f"No intraday data found for {ticker} ({av_interval})")
            return pd.DataFrame()
        
        time_series = data[time_series_key]
        df = pd.DataFrame.from_dict(time_series, orient='index')
        
        # Clean up column names and data types
        df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        df.index = pd.to_datetime(df.index)
        df = df.astype(float)
        df = df.sort_index()
        
        # Filter by date range
        df = df[(df.index >= start_date) & (df.index <= end_date)]
        
        # Resample to 4h if needed
        if timeframe == '4h' and not df.empty:
            df = self._resample_to_4h(df)
        
        # Add provider attribution
        df.attrs['provider_source'] = self.name
        df.attrs['timeframe'] = timeframe
        df.attrs['ticker'] = ticker
        df.attrs['asset_type'] = 'stock'
        
        logger.info(f"Fetched {len(df)} {timeframe} records for {ticker}")
        return df
    
    def _resample_to_4h(self, df: pd.DataFrame) -> pd.DataFrame:
        """Resample 1h data to 4h"""
        if df.empty:
            return df
            
        # Resample to 4-hour periods starting at market open (9:30 AM ET)
        resampled = df.resample('4H', origin='09:30').agg({
            'Open': 'first',
            'High': 'max', 
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
        
        return resampled
    
    def _fetch_crypto_daily_data(self, ticker: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Fetch daily crypto data using crypto-specific API"""
        # Parse crypto symbol
        if 'USD' in ticker:
            symbol = ticker.replace('USD', '')
            market = 'USD'
        else:
            symbol = ticker
            market = 'USD'
        
        params = {
            'function': 'DIGITAL_CURRENCY_DAILY',
            'symbol': symbol,
            'market': market,
            'apikey': self.api_key
        }
        
        data = self._make_request(params)
        
        if 'Time Series (Digital Currency Daily)' not in data:
            logger.warning(f"No crypto daily data found for {ticker}")
            return pd.DataFrame()
        
        time_series = data['Time Series (Digital Currency Daily)']
        df = pd.DataFrame.from_dict(time_series, orient='index')
        
        # Clean up column names for crypto data
        df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        df.index = pd.to_datetime(df.index)
        df = df.astype(float)
        
        # Filter by date range
        df = df[(df.index >= start_date) & (df.index <= end_date)]
        df = df.sort_index()
        
        # Add provider attribution
        df.attrs['provider_source'] = self.name
        df.attrs['timeframe'] = '1d'
        df.attrs['ticker'] = ticker
        df.attrs['asset_type'] = 'crypto'
        
        logger.info(f"Fetched {len(df)} crypto daily records for {ticker}")
        return df
    
    def _fetch_crypto_intraday_data(self, ticker: str, timeframe: str, 
                                  start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Fetch intraday crypto data using crypto-specific API"""
        # Parse crypto symbol
        if 'USD' in ticker:
            symbol = ticker.replace('USD', '')
            market = 'USD'
        else:
            symbol = ticker
            market = 'USD'
        
        # Convert timeframe for crypto API
        av_interval = self._convert_timeframe(timeframe if timeframe != '4h' else '1h')
        
        params = {
            'function': 'CRYPTO_INTRADAY',
            'symbol': symbol,
            'market': market,
            'interval': av_interval,
            'apikey': self.api_key
        }
        
        data = self._make_request(params)
        
        time_series_key = f'Time Series Crypto ({av_interval})'
        if time_series_key not in data:
            logger.warning(f"No crypto intraday data found for {ticker} ({av_interval})")
            return pd.DataFrame()
        
        time_series = data[time_series_key]
        df = pd.DataFrame.from_dict(time_series, orient='index')
        
        # Clean up column names and data types
        df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        df.index = pd.to_datetime(df.index)
        df = df.astype(float)
        df = df.sort_index()
        
        # Filter by date range
        df = df[(df.index >= start_date) & (df.index <= end_date)]
        
        # Resample to 4h if needed
        if timeframe == '4h' and not df.empty:
            df = self._resample_to_4h(df)
        
        # Add provider attribution
        df.attrs['provider_source'] = self.name
        df.attrs['timeframe'] = timeframe
        df.attrs['ticker'] = ticker
        df.attrs['asset_type'] = 'crypto'
        
        logger.info(f"Fetched {len(df)} crypto {timeframe} records for {ticker}")
        return df