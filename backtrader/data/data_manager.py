import yfinance as yf
import backtrader as bt
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any
import pickle
from datetime import datetime, timedelta


class DataManager:
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.data_cache: Dict[str, Any] = {}
    
    def _get_cache_filename(self, ticker: str, start_date: datetime, end_date: datetime) -> Path:
        start_str = start_date.strftime('%Y%m%d')
        end_str = end_date.strftime('%Y%m%d')
        return self.cache_dir / f"{ticker}_{start_str}_{end_str}.pkl"
    
    def _load_from_cache(self, ticker: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        cache_file = self._get_cache_filename(ticker, start_date, end_date)
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"Error loading cache for {ticker}: {e}")
        return None
    
    def _save_to_cache(self, ticker: str, start_date: datetime, end_date: datetime, data: pd.DataFrame):
        cache_file = self._get_cache_filename(ticker, start_date, end_date)
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            print(f"Error saving cache for {ticker}: {e}")
    
    def download_data(self, ticker: str, start_date: datetime, end_date: datetime, 
                     use_cache: bool = True) -> Optional[pd.DataFrame]:
        
        if use_cache:
            cached_data = self._load_from_cache(ticker, start_date, end_date)
            if cached_data is not None:
                print(f"Loaded {ticker} from cache")
                return cached_data
        
        try:
            print(f"Downloading {ticker} data from {start_date.date()} to {end_date.date()}")
            
            stock = yf.Ticker(ticker)
            data = stock.history(
                start=start_date,
                end=end_date + timedelta(days=1),
                interval="1d"
            )
            
            if data.empty:
                print(f"No data found for {ticker}")
                return None
            
            data = data.dropna()
            
            if use_cache:
                self._save_to_cache(ticker, start_date, end_date, data)
            
            return data
            
        except Exception as e:
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
    
    def clear_cache(self, ticker: str = None):
        if ticker:
            cache_files = list(self.cache_dir.glob(f"{ticker}_*.pkl"))
        else:
            cache_files = list(self.cache_dir.glob("*.pkl"))
        
        for cache_file in cache_files:
            try:
                cache_file.unlink()
                print(f"Deleted cache file: {cache_file}")
            except Exception as e:
                print(f"Error deleting {cache_file}: {e}")
    
    def list_cached_data(self) -> Dict[str, list]:
        cache_info = {}
        for cache_file in self.cache_dir.glob("*.pkl"):
            parts = cache_file.stem.split('_')
            if len(parts) >= 3:
                ticker = '_'.join(parts[:-2])
                if ticker not in cache_info:
                    cache_info[ticker] = []
                cache_info[ticker].append({
                    'start_date': parts[-2],
                    'end_date': parts[-1],
                    'file_size': cache_file.stat().st_size,
                    'modified': datetime.fromtimestamp(cache_file.stat().st_mtime)
                })
        
        return cache_info