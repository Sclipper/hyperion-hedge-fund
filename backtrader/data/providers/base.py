from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd


class DataProvider(ABC):
    """
    Abstract base class for all data providers
    """
    
    @abstractmethod
    def get_supported_timeframes(self) -> List[str]:
        """Return list of supported timeframes (e.g., ['1h', '4h', '1d'])"""
        pass
    
    @abstractmethod
    def fetch_data(
        self, 
        ticker: str, 
        timeframe: str,
        start_date: datetime, 
        end_date: datetime
    ) -> pd.DataFrame:
        """Fetch data for single ticker/timeframe combination"""
        pass
    
    @abstractmethod
    def get_rate_limit(self) -> Dict[str, int]:
        """Return rate limit configuration"""
        pass
    
    @abstractmethod
    def validate_ticker(self, ticker: str) -> bool:
        """Check if ticker is valid for this provider"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return provider name"""
        pass