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
        
        # Components will be initialized on demand
        self._bulk_fetcher = None
        self._data_validator = None
        self._error_handler = None
        
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
    
    def _make_request(self, params: Dict, ticker: str = "unknown", timeframe: str = "unknown") -> Dict:
        """Make API request with advanced error handling"""
        self._rate_limit()
        
        def _execute_request():
            response = self.session.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors
            if 'Error Message' in data:
                error_msg = data['Error Message']
                if 'Invalid API call' in error_msg and 'TIME_SERIES_INTRADAY' in error_msg:
                    # Specific handling for invalid symbol errors
                    logger.error(f"Symbol {ticker} not supported for intraday data: {error_msg}")
                    raise Exception(f"Symbol not supported: {error_msg}")
                else:
                    raise Exception(f"Alpha Vantage API Error: {error_msg}")
            
            if 'Note' in data:
                if 'call frequency' in data['Note']:
                    # This will be handled by error handler as rate limit
                    raise Exception(f"Rate limit hit: {data['Note']}")
                else:
                    logger.warning(f"Alpha Vantage Note: {data['Note']}")
            
            return data
        
        # Use error handler for intelligent retry
        return self.get_error_handler().execute_with_retry(
            _execute_request, ticker, timeframe
        )
    
    def _convert_timeframe(self, timeframe: str) -> str:
        """Convert our timeframe format to Alpha Vantage format"""
        mapping = {
            '1h': '60min',
            '4h': '240min',  # We'll construct this from 60min data
            '1d': 'daily'
        }
        return mapping.get(timeframe, 'daily')
    
    def _resolve_native_timeframe(self, requested_timeframe: str) -> dict:
        """Determine optimal native timeframe and resampling strategy"""
        
        # Alpha Vantage native intraday intervals
        native_supported = ['1min', '5min', '15min', '30min', '60min']
        
        # Smart mapping strategy - fetch lowest native timeframe and resample up
        mapping = {
            '1h': {'native': '60min', 'resample': None},          # Direct mapping
            '4h': {'native': '60min', 'resample': '4H'},          # Resample from 1h
            '2h': {'native': '60min', 'resample': '2H'},          # Future: 2-hour 
            '8h': {'native': '60min', 'resample': '8H'},          # Future: 8-hour
            '12h': {'native': '60min', 'resample': '12H'},        # Future: 12-hour
            '15min': {'native': '15min', 'resample': None},       # Direct mapping
            '30min': {'native': '30min', 'resample': None},       # Direct mapping
            '1d': {'native': 'daily', 'resample': None}           # Daily data
        }
        
        resolution = mapping.get(requested_timeframe)
        if resolution is None:
            # Default fallback: use 60min and try to resample
            logger.warning(f"Unknown timeframe {requested_timeframe}, using 60min with custom resampling")
            resolution = {'native': '60min', 'resample': requested_timeframe}
            
        return resolution
    
    def _should_use_historical_method(self, start_date: datetime, end_date: datetime) -> bool:
        """Determine if we need historical fetching methods"""
        days_from_now = (datetime.now() - end_date).days
        return days_from_now > 30
    
    def _select_historical_method(self, start_date: datetime, end_date: datetime) -> str:
        """Choose optimal historical fetching method"""
        
        total_days = (end_date - start_date).days
        months_needed = total_days / 30
        
        if months_needed <= 3:
            return 'month_by_month'  # Precise, fewer API calls
        elif months_needed <= 25:  # Allow up to 25 months for extended slices (2+ years)
            return 'extended_slices'  # Bulk fetching
        else:
            return 'hybrid'  # Combination approach
    
    def _resample_timeframe(self, df: pd.DataFrame, target_timeframe: str) -> pd.DataFrame:
        """Universal resampling for any target timeframe"""
        
        if df.empty:
            return df
            
        # Parse target timeframe
        if target_timeframe.endswith('H'):
            # Handle pandas-style resampling rules like '4H', '2H', etc.
            resample_rule = target_timeframe
        elif target_timeframe.endswith('h'):
            # Handle our format like '4h', '2h', etc.
            hours = int(target_timeframe[:-1])
            resample_rule = f"{hours}H"
        elif target_timeframe.endswith('min'):
            minutes = int(target_timeframe[:-3])
            resample_rule = f"{minutes}T"
        else:
            raise ValueError(f"Unsupported timeframe format: {target_timeframe}")
        
        # Market-aware resampling (9:30 AM ET origin for stock market)
        try:
            resampled = df.resample(resample_rule, origin='09:30').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
            
            logger.info(f"Resampled {len(df)} records to {len(resampled)} {target_timeframe} records")
            return resampled
            
        except Exception as e:
            logger.error(f"Error resampling to {target_timeframe}: {e}")
            return df
    
    def fetch_data(self, ticker: str, timeframe: str, 
                  start_date: datetime, end_date: datetime, 
                  validate_data: bool = True) -> pd.DataFrame:
        """Enhanced fetch data with smart date-aware fetching and universal timeframe support"""
        
        if not self.validate_ticker(ticker):
            logger.error(f"Invalid ticker: {ticker}")
            return pd.DataFrame()
        
        # Check if symbol is likely supported by Alpha Vantage
        if not self._is_symbol_likely_supported(ticker):
            logger.warning(f"Symbol {ticker} may not be supported by Alpha Vantage")
            # Still try to fetch but expect potential failures
        
        if timeframe not in self.get_supported_timeframes():
            logger.error(f"Unsupported timeframe: {timeframe}")
            return pd.DataFrame()
        
        try:
            # Resolve timeframe strategy
            timeframe_resolution = self._resolve_native_timeframe(timeframe)
            native_timeframe = timeframe_resolution['native']
            needs_resampling = timeframe_resolution['resample'] is not None
            
            logger.info(f"Fetching {ticker} {timeframe}: native={native_timeframe}, resample={timeframe_resolution['resample']}")
            
            # Fetch native data using enhanced logic
            if native_timeframe == 'daily':
                # Daily data - use existing method
                if self._is_crypto_symbol(ticker):
                    df = self._fetch_crypto_daily_data(ticker, start_date, end_date)
                else:
                    df = self._fetch_daily_data(ticker, start_date, end_date)
            else:
                # Intraday data - use enhanced smart fetching
                if self._is_crypto_symbol(ticker):
                    df = self._fetch_crypto_intraday_enhanced(ticker, native_timeframe, start_date, end_date)
                else:
                    df = self._fetch_intraday_enhanced(ticker, native_timeframe, start_date, end_date)
            
            # Apply resampling if needed
            if needs_resampling and not df.empty:
                target_resample = timeframe_resolution['resample']
                logger.info(f"Resampling {ticker} from {native_timeframe} to {target_resample}")
                df = self._resample_timeframe(df, target_resample)
                
                # Update metadata to reflect final timeframe
                if hasattr(df, 'attrs'):
                    df.attrs['timeframe'] = timeframe
                    df.attrs['resampled_from'] = native_timeframe
            
            # Validate data if requested and data exists
            if validate_data and not df.empty:
                asset_type = 'crypto' if self._is_crypto_symbol(ticker) else 'stock'
                validation_result = self.get_data_validator().validate_dataframe(
                    df, ticker, timeframe, asset_type
                )
                
                if not validation_result.is_valid:
                    logger.warning(f"Data validation failed for {ticker} {timeframe}: "
                                 f"{len(validation_result.errors)} errors")
                    # Attempt repair
                    df = self.get_data_validator().repair_data(df, validation_result)
                    logger.info(f"Applied data repairs for {ticker} {timeframe}")
                
                # Add validation metadata
                df.attrs['validation_passed'] = validation_result.is_valid
                df.attrs['validation_errors'] = len(validation_result.errors)
                df.attrs['validation_warnings'] = len(validation_result.warnings)
            
            return df
                
        except Exception as e:
            logger.error(f"Error fetching {ticker} data: {e}")
            return pd.DataFrame()
    
    def _fetch_daily_data(self, ticker: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Fetch daily data"""
        # Sanitize symbol for API call
        api_symbol = self._sanitize_symbol_for_api(ticker)
        if api_symbol != ticker:
            logger.info(f"Sanitized symbol {ticker} -> {api_symbol} for Alpha Vantage API")
        
        params = {
            'function': 'TIME_SERIES_DAILY',
            'symbol': api_symbol,  # Use sanitized symbol
            'apikey': self.api_key,
            'outputsize': 'full'
        }
        
        data = self._make_request(params, ticker, 'daily')
        
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
        df = df[(df.index >= pd.Timestamp(start_date)) & (df.index <= pd.Timestamp(end_date))]
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
        
        # Sanitize symbol for API call
        api_symbol = self._sanitize_symbol_for_api(ticker)
        if api_symbol != ticker:
            logger.info(f"Sanitized symbol {ticker} -> {api_symbol} for Alpha Vantage API")
        
        params = {
            'function': 'TIME_SERIES_INTRADAY',
            'symbol': api_symbol,  # Use sanitized symbol
            'interval': av_interval,
            'apikey': self.api_key,
            'outputsize': 'full'
        }
        
        data = self._make_request(params, ticker, base_timeframe)
        
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
        df = df[(df.index >= pd.Timestamp(start_date)) & (df.index <= pd.Timestamp(end_date))]
        
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
        
        data = self._make_request(params, ticker, 'daily')
        
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
        df = df[(df.index >= pd.Timestamp(start_date)) & (df.index <= pd.Timestamp(end_date))]
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
        
        data = self._make_request(params, ticker, timeframe)
        
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
        df = df[(df.index >= pd.Timestamp(start_date)) & (df.index <= pd.Timestamp(end_date))]
        
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
    
    def _fetch_intraday_enhanced(self, ticker: str, native_timeframe: str, 
                                start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Enhanced intraday fetching with smart date-aware logic"""
        
        # Determine if we need historical method
        if self._should_use_historical_method(start_date, end_date):
            logger.info(f"Using historical method for {ticker} {native_timeframe} (data > 30 days old)")
            return self._fetch_intraday_historical(ticker, native_timeframe, start_date, end_date)
        else:
            logger.info(f"Using recent method for {ticker} {native_timeframe} (data within 30 days)")
            return self._fetch_intraday_recent(ticker, native_timeframe, start_date, end_date)
    
    def _fetch_crypto_intraday_enhanced(self, ticker: str, native_timeframe: str,
                                       start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Enhanced crypto intraday fetching with smart date-aware logic"""
        
        # For now, use existing crypto method (can be enhanced later)
        # Convert native_timeframe back to our format for compatibility
        timeframe_map = {'60min': '1h', '240min': '4h', '15min': '15min', '30min': '30min'}
        our_timeframe = timeframe_map.get(native_timeframe, '1h')
        
        return self._fetch_crypto_intraday_data(ticker, our_timeframe, start_date, end_date)
    
    def _fetch_intraday_recent(self, ticker: str, native_timeframe: str,
                              start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Fetch recent intraday data (within 30 days) using standard endpoint"""
        
        av_interval = native_timeframe  # Use native timeframe directly
        
        # Sanitize symbol for API call
        api_symbol = self._sanitize_symbol_for_api(ticker)
        if api_symbol != ticker:
            logger.info(f"Sanitized symbol {ticker} -> {api_symbol} for Alpha Vantage API")
        
        params = {
            'function': 'TIME_SERIES_INTRADAY',
            'symbol': api_symbol,  # Use sanitized symbol
            'interval': av_interval,
            'apikey': self.api_key,
            'outputsize': 'full'  # Gets last 30 days
        }
        
        data = self._make_request(params, ticker, native_timeframe)
        
        time_series_key = f'Time Series ({av_interval})'
        if time_series_key not in data:
            logger.warning(f"No recent intraday data found for {ticker} ({av_interval})")
            return pd.DataFrame()
        
        time_series = data[time_series_key]
        df = pd.DataFrame.from_dict(time_series, orient='index')
        
        # Clean up column names and data types
        df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        df.index = pd.to_datetime(df.index)
        df = df.astype(float)
        df = df.sort_index()
        
        # Filter by date range
        df = df[(df.index >= pd.Timestamp(start_date)) & (df.index <= pd.Timestamp(end_date))]
        
        # Add provider attribution
        df.attrs['provider_source'] = self.name
        df.attrs['timeframe'] = native_timeframe
        df.attrs['ticker'] = ticker
        df.attrs['asset_type'] = 'stock'
        df.attrs['fetch_method'] = 'recent'
        
        logger.info(f"Fetched {len(df)} recent {native_timeframe} records for {ticker}")
        return df
    
    def _fetch_intraday_historical(self, ticker: str, native_timeframe: str,
                                  start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Fetch historical intraday data using month-by-month or extended slices"""
        
        method = self._select_historical_method(start_date, end_date)
        
        if method == 'month_by_month':
            return self._fetch_intraday_monthly(ticker, native_timeframe, start_date, end_date)
        elif method == 'extended_slices':
            return self._fetch_intraday_slices(ticker, native_timeframe, start_date, end_date)
        else:  # hybrid
            # For now, use month_by_month as it's more precise
            logger.info(f"Using month_by_month method for hybrid approach")
            return self._fetch_intraday_monthly(ticker, native_timeframe, start_date, end_date)
    
    def _sanitize_symbol_for_api(self, ticker: str) -> str:
        """Sanitize ticker symbol for Alpha Vantage API calls"""
        # Alpha Vantage doesn't handle dots in symbols for intraday data
        # Convert BRK.B to BRK-B format
        sanitized = ticker.replace('.', '-')
        
        # Additional sanitization for other problematic characters
        # Remove any special characters that might cause issues
        import re
        sanitized = re.sub(r'[^A-Za-z0-9\-]', '', sanitized)
        
        return sanitized.upper()  # Ensure uppercase for consistency
    
    def _is_symbol_likely_supported(self, ticker: str) -> bool:
        """Check if symbol is likely supported by Alpha Vantage"""
        # Basic validation for symbol format
        if not ticker or len(ticker) < 1 or len(ticker) > 10:
            return False
        
        # Check for known problematic patterns
        problematic_patterns = [
            r'^[0-9]+$',  # Pure numeric symbols
            r'.*\s.*',    # Symbols with spaces
            r'.*[^A-Za-z0-9.\-].*'  # Symbols with special chars (except . and -)
        ]
        
        import re
        for pattern in problematic_patterns:
            if re.match(pattern, ticker):
                return False
        
        return True
    
    def _fetch_intraday_monthly(self, ticker: str, native_timeframe: str,
                               start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Fetch historical intraday data month by month"""
        
        all_data = []
        current_date = start_date.replace(day=1)  # Start of month
        
        # Sanitize symbol for API call
        api_symbol = self._sanitize_symbol_for_api(ticker)
        if api_symbol != ticker:
            logger.info(f"Sanitized symbol {ticker} -> {api_symbol} for Alpha Vantage API")
        
        while current_date <= end_date:
            month_str = current_date.strftime('%Y-%m')
            
            # Check if this month intersects with our date range
            month_start = current_date
            if current_date.month == 12:
                month_end = current_date.replace(year=current_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = current_date.replace(month=current_date.month + 1, day=1) - timedelta(days=1)
            
            # Skip if month is entirely outside our range
            if month_end < start_date or month_start > end_date:
                current_date = month_end + timedelta(days=1)
                continue
            
            logger.info(f"Fetching historical data for {ticker} {native_timeframe} month {month_str}")
            
            params = {
                'function': 'TIME_SERIES_INTRADAY',
                'symbol': api_symbol,  # Use sanitized symbol
                'interval': native_timeframe,
                'month': month_str,  # Key parameter for historical data
                'outputsize': 'full',
                'apikey': self.api_key
            }
            
            try:
                data = self._make_request(params, ticker, f"{native_timeframe}-{month_str}")
                
                time_series_key = f'Time Series ({native_timeframe})'
                if time_series_key in data:
                    time_series = data[time_series_key]
                    month_df = pd.DataFrame.from_dict(time_series, orient='index')
                    
                    if not month_df.empty:
                        # Clean up data
                        month_df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                        month_df.index = pd.to_datetime(month_df.index)
                        month_df = month_df.astype(float)
                        all_data.append(month_df)
                        logger.info(f"Fetched {len(month_df)} records for {month_str}")
                    else:
                        logger.warning(f"Empty data for {ticker} {month_str}")
                else:
                    logger.warning(f"No data key found for {ticker} {month_str}")
                    
            except Exception as e:
                logger.error(f"Error fetching {ticker} data for {month_str}: {e}")
                # Continue with other months
            
            # Move to next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        # Combine all monthly data
        if not all_data:
            logger.warning(f"No historical data found for {ticker} {native_timeframe}")
            return pd.DataFrame()
        
        combined_df = pd.concat(all_data)
        combined_df = combined_df.sort_index()
        
        # Filter by exact date range
        combined_df = combined_df[(combined_df.index >= pd.Timestamp(start_date)) & 
                                 (combined_df.index <= pd.Timestamp(end_date))]
        
        # Add provider attribution
        combined_df.attrs['provider_source'] = self.name
        combined_df.attrs['timeframe'] = native_timeframe
        combined_df.attrs['ticker'] = ticker
        combined_df.attrs['asset_type'] = 'stock'
        combined_df.attrs['fetch_method'] = 'monthly'
        
        logger.info(f"Combined {len(combined_df)} historical {native_timeframe} records for {ticker}")
        return combined_df
    
    def _fetch_intraday_slices(self, ticker: str, native_timeframe: str,
                              start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Fetch historical intraday data using extended slices (up to 2 years)"""
        
        # For now, implement as a placeholder that falls back to monthly
        # Extended slices can be implemented in a future enhancement
        logger.info(f"Extended slices not yet implemented, falling back to monthly method")
        return self._fetch_intraday_monthly(ticker, native_timeframe, start_date, end_date)
    
    def get_bulk_fetcher(self):
        """Get bulk fetcher instance (lazy initialization)"""
        if self._bulk_fetcher is None:
            from .client import AlphaVantageClient
            from .bulk_fetcher import BulkDataFetcher
            
            client = AlphaVantageClient()
            self._bulk_fetcher = BulkDataFetcher(client)
        
        return self._bulk_fetcher
    
    def get_data_validator(self):
        """Get data validator instance (lazy initialization)"""
        if self._data_validator is None:
            from .data_validator import DataValidator
            self._data_validator = DataValidator()
        
        return self._data_validator
    
    def get_error_handler(self):
        """Get error handler instance (lazy initialization)"""
        if self._error_handler is None:
            from .error_handler import ErrorRecoveryStrategy
            self._error_handler = ErrorRecoveryStrategy(max_retries=3)
        
        return self._error_handler
    
