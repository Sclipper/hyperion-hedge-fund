"""
Dedicated crypto provider for Alpha Vantage API
Handles cryptocurrency-specific data fetching with proper error handling
"""

import logging
import os
import time
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
import pandas as pd
import requests

logger = logging.getLogger(__name__)


class AlphaVantageCryptoProvider:
    """
    Specialized provider for Alpha Vantage cryptocurrency data
    
    Features:
    - CRYPTO_INTRADAY endpoint for intraday data
    - DIGITAL_CURRENCY_DAILY for daily data
    - Automatic symbol validation against supported list
    - Proper error handling for unsupported symbols
    """
    
    # Supported crypto symbols from Alpha Vantage (as of 2024)
    # This is a subset - we'll fetch the full list dynamically
    KNOWN_SUPPORTED_CRYPTOS = {
        'BTC', 'ETH', 'ADA', 'ALGO', 'ATOM', 'AVAX', 'BCH', 'BNB', 'BSV',
        'BUSD', 'COMP', 'CRO', 'DAI', 'DASH', 'DOGE', 'DOT', 'EOS', 'ETC',
        'FIL', 'LINK', 'LTC', 'MATIC', 'SOL', 'TRX', 'UNI', 'USDC', 'USDT',
        'VET', 'XLM', 'XMR', 'XRP', 'ZEC'
    }
    
    def __init__(self):
        self.api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        if not self.api_key:
            raise ValueError("ALPHA_VANTAGE_API_KEY environment variable is required")
        
        self.base_url = "https://www.alphavantage.co/query"
        self.crypto_list_url = "https://www.alphavantage.co/digital_currency_list/"
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BacktraderHedgeFund/1.0'
        })
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 60 / 75  # 75 requests per minute
        
        # Cache supported cryptos
        self._supported_cryptos: Optional[Set[str]] = None
        self._last_crypto_list_fetch = None
        
        logger.info("AlphaVantageCryptoProvider initialized")
    
    def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def get_supported_cryptos(self, force_refresh: bool = False) -> Set[str]:
        """
        Get set of supported cryptocurrency symbols
        
        Args:
            force_refresh: Force refresh from API even if cached
            
        Returns:
            Set of supported crypto symbols
        """
        # Use cache if available and not forcing refresh
        if (self._supported_cryptos is not None and 
            not force_refresh and
            self._last_crypto_list_fetch and
            (datetime.now() - self._last_crypto_list_fetch).days < 7):
            return self._supported_cryptos
        
        try:
            logger.info("Fetching supported crypto list from Alpha Vantage")
            response = self.session.get(self.crypto_list_url, timeout=10)
            response.raise_for_status()
            
            # Parse CSV response
            lines = response.text.strip().split('\n')
            if len(lines) > 1:
                # Skip header
                cryptos = set()
                for line in lines[1:]:
                    parts = line.split(',')
                    if len(parts) >= 2:
                        symbol = parts[0].strip().upper()
                        if symbol:
                            cryptos.add(symbol)
                
                self._supported_cryptos = cryptos
                self._last_crypto_list_fetch = datetime.now()
                logger.info(f"Loaded {len(cryptos)} supported cryptocurrencies")
                return cryptos
            else:
                logger.warning("Empty crypto list response")
                return self.KNOWN_SUPPORTED_CRYPTOS
                
        except Exception as e:
            logger.error(f"Failed to fetch crypto list: {e}")
            # Fall back to known list
            if self._supported_cryptos:
                return self._supported_cryptos
            return self.KNOWN_SUPPORTED_CRYPTOS
    
    def is_crypto_supported(self, symbol: str) -> bool:
        """
        Check if a cryptocurrency symbol is supported
        
        Args:
            symbol: Crypto symbol (e.g., 'BTC', 'ETH')
            
        Returns:
            True if supported, False otherwise
        """
        # Remove USD suffix if present
        if symbol.upper().endswith('USD'):
            symbol = symbol[:-3]
        
        supported_cryptos = self.get_supported_cryptos()
        return symbol.upper() in supported_cryptos
    
    def fetch_crypto_intraday(self, symbol: str, interval: str, 
                             start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Fetch intraday crypto data using CRYPTO_INTRADAY endpoint
        
        Args:
            symbol: Crypto symbol (e.g., 'BTC', 'ETH')
            interval: Time interval ('1min', '5min', '15min', '30min', '60min')
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            DataFrame with OHLCV data or empty DataFrame if not available
        """
        # Validate symbol
        if not self.is_crypto_supported(symbol):
            logger.warning(f"Cryptocurrency {symbol} is not supported by Alpha Vantage")
            return pd.DataFrame()
        
        # Clean symbol
        if symbol.upper().endswith('USD'):
            symbol = symbol[:-3]
        
        symbol = symbol.upper()
        
        # Validate interval
        valid_intervals = ['1min', '5min', '15min', '30min', '60min']
        if interval not in valid_intervals:
            logger.error(f"Invalid interval {interval}. Must be one of: {valid_intervals}")
            return pd.DataFrame()
        
        params = {
            'function': 'CRYPTO_INTRADAY',
            'symbol': symbol,
            'market': 'USD',
            'interval': interval,
            'outputsize': 'full',
            'apikey': self.api_key
        }
        
        try:
            self._rate_limit()
            
            logger.info(f"Fetching crypto intraday data for {symbol} ({interval})")
            response = self.session.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors
            if 'Error Message' in data:
                logger.error(f"API Error for {symbol}: {data['Error Message']}")
                return pd.DataFrame()
            
            if 'Note' in data:
                logger.warning(f"API Note: {data['Note']}")
                # API limit reached
                return pd.DataFrame()
            
            # Find time series key
            time_series_key = None
            for key in data.keys():
                if 'time series' in key.lower():
                    time_series_key = key
                    break
            
            if not time_series_key:
                logger.error(f"No time series data found for {symbol}. Keys: {list(data.keys())}")
                return pd.DataFrame()
            
            # Parse time series data
            time_series = data[time_series_key]
            df = pd.DataFrame.from_dict(time_series, orient='index')
            
            if df.empty:
                return pd.DataFrame()
            
            # Standardize column names
            df.columns = [col.split('. ')[-1].title() for col in df.columns]
            
            # Ensure we have standard OHLCV columns
            expected_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            df = df[[col for col in expected_cols if col in df.columns]]
            
            # Convert to numeric and datetime index
            df = df.astype(float)
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            
            # Filter by date range
            mask = (df.index >= pd.Timestamp(start_date)) & (df.index <= pd.Timestamp(end_date))
            df = df[mask]
            
            # Add metadata
            df.attrs['symbol'] = symbol
            df.attrs['interval'] = interval
            df.attrs['source'] = 'alpha_vantage_crypto'
            
            logger.info(f"Fetched {len(df)} records for {symbol} ({interval})")
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch crypto intraday data for {symbol}: {e}")
            return pd.DataFrame()
    
    def fetch_crypto_daily(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Fetch daily crypto data using DIGITAL_CURRENCY_DAILY endpoint
        
        Args:
            symbol: Crypto symbol (e.g., 'BTC', 'ETH')
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            DataFrame with OHLCV data or empty DataFrame if not available
        """
        # Validate symbol
        if not self.is_crypto_supported(symbol):
            logger.warning(f"Cryptocurrency {symbol} is not supported by Alpha Vantage")
            return pd.DataFrame()
        
        # Clean symbol
        if symbol.upper().endswith('USD'):
            symbol = symbol[:-3]
        
        symbol = symbol.upper()
        
        params = {
            'function': 'DIGITAL_CURRENCY_DAILY',
            'symbol': symbol,
            'market': 'USD',
            'apikey': self.api_key
        }
        
        try:
            self._rate_limit()
            
            logger.info(f"Fetching crypto daily data for {symbol}")
            response = self.session.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors
            if 'Error Message' in data:
                logger.error(f"API Error for {symbol}: {data['Error Message']}")
                return pd.DataFrame()
            
            if 'Note' in data:
                logger.warning(f"API Note: {data['Note']}")
                return pd.DataFrame()
            
            # Find time series key
            time_series_key = 'Time Series (Digital Currency Daily)'
            if time_series_key not in data:
                logger.error(f"No daily data found for {symbol}")
                return pd.DataFrame()
            
            # Parse time series data
            time_series = data[time_series_key]
            rows = []
            
            for date_str, values in time_series.items():
                # Extract values - Alpha Vantage uses simple numeric keys for crypto daily
                row = {
                    'Date': date_str,
                    'Open': float(values.get('1. open', values.get('1a. open (USD)', 0))),
                    'High': float(values.get('2. high', values.get('2a. high (USD)', 0))),
                    'Low': float(values.get('3. low', values.get('3a. low (USD)', 0))),
                    'Close': float(values.get('4. close', values.get('4a. close (USD)', 0))),
                    'Volume': float(values.get('5. volume', 0))
                }
                rows.append(row)
            
            df = pd.DataFrame(rows)
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            df = df.sort_index()
            
            # Filter by date range
            mask = (df.index >= pd.Timestamp(start_date)) & (df.index <= pd.Timestamp(end_date))
            df = df[mask]
            
            # Add metadata
            df.attrs['symbol'] = symbol
            df.attrs['interval'] = '1d'
            df.attrs['source'] = 'alpha_vantage_crypto'
            
            logger.info(f"Fetched {len(df)} daily records for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch crypto daily data for {symbol}: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def resample_to_timeframe(self, df: pd.DataFrame, target_timeframe: str) -> pd.DataFrame:
        """
        Universal resampling to any target timeframe
        
        Args:
            df: Source DataFrame with OHLCV data
            target_timeframe: Target timeframe (e.g., '4h', '2h', '15min', '6h', '8h', '12h')
            
        Returns:
            Resampled DataFrame
        """
        if df.empty:
            return df
        
        # Convert target timeframe to pandas resample rule
        rule = self._convert_to_pandas_rule(target_timeframe)
        if not rule:
            logger.error(f"Cannot convert timeframe '{target_timeframe}' to pandas rule")
            return df
        
        try:
            # Resample OHLCV data
            resampled = df.resample(rule).agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
            
            # Preserve metadata
            resampled.attrs = df.attrs.copy()
            resampled.attrs['resampled_from'] = df.attrs.get('interval', 'unknown')
            resampled.attrs['interval'] = target_timeframe
            
            logger.info(f"Resampled {len(df)} records to {len(resampled)} records ({target_timeframe})")
            return resampled
            
        except Exception as e:
            logger.error(f"Failed to resample to {target_timeframe}: {e}")
            return df
    
    def _convert_to_pandas_rule(self, timeframe: str) -> str:
        """
        Convert any timeframe string to pandas resample rule
        
        Supports:
        - Minutes: '1min', '5min', '15min', '30min', '45min', etc.
        - Hours: '1h', '2h', '4h', '6h', '8h', '12h', etc.
        - Days: '1d', '2d', '3d', etc.
        - Weeks: '1w', '2w', etc.
        
        Returns:
            Pandas resample rule string or empty string if invalid
        """
        timeframe = timeframe.lower()
        
        # Minutes
        if timeframe.endswith('min'):
            try:
                minutes = int(timeframe[:-3])
                return f"{minutes}min"
            except ValueError:
                return ""
        
        # Hours
        elif timeframe.endswith('h'):
            try:
                hours = int(timeframe[:-1])
                return f"{hours}h"
            except ValueError:
                return ""
        
        # Days
        elif timeframe.endswith('d'):
            try:
                days = int(timeframe[:-1])
                return f"{days}D"
            except ValueError:
                return ""
        
        # Weeks
        elif timeframe.endswith('w'):
            try:
                weeks = int(timeframe[:-1])
                return f"{weeks}W"
            except ValueError:
                return ""
        
        # Legacy pandas format (already a valid rule)
        elif any(timeframe.endswith(suffix) for suffix in ['T', 'H', 'D', 'W']):
            # Convert old format to new (T->min, H->h)
            return timeframe.replace('T', 'min').replace('H', 'h')
        
        return ""