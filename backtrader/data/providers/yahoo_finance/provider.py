import warnings
import logging
from typing import Dict, List
from datetime import datetime
import pandas as pd
import yfinance as yf

from ..base import DataProvider

logger = logging.getLogger(__name__)


class YahooFinanceProvider(DataProvider):
    """
    Legacy Yahoo Finance provider (to be deprecated)
    
    Limitations:
    - Only daily data for historical periods
    - Intraday data limited to last 60 days
    - No reliable 4h data support
    """
    
    def __init__(self):
        self._show_deprecation_warning()
        
    def _show_deprecation_warning(self):
        warnings.warn(
            "YahooFinanceProvider has limitations. Only daily data available for historical periods. "
            "Consider using AlphaVantageProvider for multi-timeframe support.",
            UserWarning,
            stacklevel=3
        )
    
    @property
    def name(self) -> str:
        return "yahoo_finance"
    
    def get_supported_timeframes(self) -> List[str]:
        """Only return what YF can reliably provide for historical data"""
        return ['1d']  # Daily only for historical data
    
    def fetch_data(self, ticker: str, timeframe: str, 
                  start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Fetch data using yfinance"""
        if timeframe != '1d':
            logger.warning(f"YahooFinance doesn't support {timeframe} for historical data. Using daily.")
            timeframe = '1d'
            
        try:
            # Use existing yfinance implementation
            ticker_obj = yf.Ticker(ticker)
            data = ticker_obj.history(start=start_date, end=end_date, interval=timeframe)
            
            if data.empty:
                logger.warning(f"No data returned for {ticker} from {start_date} to {end_date}")
                return pd.DataFrame()
                
            # Ensure consistent column names (uppercase)
            data.columns = [col.title() for col in data.columns]
            
            # Add provider attribution
            data.attrs['provider_source'] = self.name
            data.attrs['timeframe'] = timeframe
            data.attrs['ticker'] = ticker
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {str(e)}")
            return pd.DataFrame()
    
    def get_rate_limit(self) -> Dict[str, int]:
        """Return rate limit configuration for Yahoo Finance"""
        return {
            'requests_per_minute': 2000,  # Very generous, rarely hit
            'requests_per_hour': 48000,
            'requests_per_day': 2000000
        }
    
    def validate_ticker(self, ticker: str) -> bool:
        """Basic ticker validation for Yahoo Finance"""
        if not ticker or not isinstance(ticker, str):
            return False
        
        # Basic format check
        if len(ticker) < 1 or len(ticker) > 10:
            return False
            
        # Yahoo Finance accepts various formats, so we're lenient
        return True