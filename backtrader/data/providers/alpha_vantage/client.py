import logging
from typing import Optional
from datetime import datetime
import pandas as pd

from .provider import AlphaVantageProvider

logger = logging.getLogger(__name__)


class AlphaVantageClient:
    """
    High-level client interface for Alpha Vantage data fetching
    Provides a consistent interface for both provider and bulk fetcher
    """
    
    def __init__(self):
        self.provider = AlphaVantageProvider()
        logger.info("AlphaVantageClient initialized")
    
    def fetch_data(self, ticker: str, timeframe: str, 
                   start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """
        Fetch data using the Alpha Vantage provider
        
        Args:
            ticker: Symbol to fetch
            timeframe: Data timeframe (1h, 4h, 1d)
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        try:
            return self.provider.fetch_data(ticker, timeframe, start_date, end_date)
        except Exception as e:
            logger.error(f"Client fetch failed for {ticker} {timeframe}: {e}")
            return None
    
    def validate_ticker(self, ticker: str) -> bool:
        """Validate ticker symbol"""
        return self.provider.validate_ticker(ticker)
    
    def get_supported_timeframes(self) -> list:
        """Get supported timeframes"""
        return self.provider.get_supported_timeframes()
    
    def get_rate_limit(self) -> dict:
        """Get rate limit information"""
        return self.provider.get_rate_limit()