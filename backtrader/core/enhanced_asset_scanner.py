"""
Module 12: Enhanced Asset Scanner

Multi-timeframe asset market condition scanner with fallback technical analysis.
Determines whether individual assets are trending, ranging, breaking out, or breaking down.

CRITICAL: This is asset-level analysis, completely independent from macro regime detection (Module 6).
"""

import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

try:
    from .asset_scanner_models import (
        MarketCondition, ScannerSource, AssetCondition, 
        ScannerResults, TechnicalIndicators
    )
    from .technical_indicators import TechnicalIndicatorCalculator, get_technical_calculator
    from ..data.database_manager import get_database_manager, execute_query
except ImportError:
    # Fallback for standalone execution
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
    
    from core.asset_scanner_models import (
        MarketCondition, ScannerSource, AssetCondition, 
        ScannerResults, TechnicalIndicators
    )
    from core.technical_indicators import TechnicalIndicatorCalculator, get_technical_calculator
    from data.database_manager import get_database_manager, execute_query

# Optional event logging - simplified for testing
def get_simple_event_writer():
    """Simple event writer for testing purposes"""
    class SimpleEventWriter:
        def log_custom_event(self, **kwargs):
            pass  # Placeholder for testing
    return SimpleEventWriter()


class EnhancedAssetScanner:
    """
    Multi-timeframe asset market condition scanner with fallback technical analysis
    
    Key Features:
    - Database-first approach with technical analysis fallback
    - Multi-timeframe analysis (1d, 4h, 1h)
    - Configurable confidence thresholds
    - Asset-level market condition detection
    - Complete independence from macro regime detection
    """
    
    def __init__(self, 
                 enable_database: bool = True,
                 timeframes: List[str] = None,
                 fallback_enabled: bool = True,
                 confidence_weights: Dict[str, float] = None,
                 min_confidence_threshold: float = 0.6):
        """
        Initialize Enhanced Asset Scanner
        
        Args:
            enable_database: Enable database lookup (primary method)
            timeframes: List of timeframes to analyze
            fallback_enabled: Enable technical analysis fallback
            confidence_weights: Weights for timeframe confidence calculation
            min_confidence_threshold: Minimum confidence for results
        """
        self.enable_database = enable_database
        # For now, only daily data is available from Yahoo Finance
        # TODO: Add multi-timeframe support when intraday data sources available
        self.timeframes = ['1d']  # timeframes or ['1d', '4h', '1h']
        self.fallback_enabled = fallback_enabled
        self.min_confidence_threshold = min_confidence_threshold
        
        # Timeframe confidence weights (must sum to 1.0)
        # For now, only daily data available
        self.confidence_weights = confidence_weights or {
            '1d': 1.0     # Daily only until multi-timeframe data available
        }
        
        # Database manager
        self.db_manager = get_database_manager()
        self.is_database_available = self.db_manager.is_connected and self.enable_database
        
        # Technical analysis calculator
        self.technical_calculator = get_technical_calculator()
        
        # Event logging (simplified for testing)
        self.event_writer = get_simple_event_writer()
        
        # Caching for performance
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        # Initialize without database warning
        if not self.is_database_available and self.enable_database:
            print("Warning: Database not available for asset scanner. Using technical analysis fallback.")
    
    def scan_assets(self, 
                   tickers: List[str], 
                   date: datetime,
                   min_confidence: float = None,
                   data_manager = None) -> ScannerResults:
        """
        Primary scanner method - comprehensive asset market condition analysis
        
        Process:
        1. Attempt database lookup first (if enabled)
        2. Fall back to technical analysis for missing data
        3. Combine results with confidence weighting
        
        Args:
            tickers: List of asset tickers to scan
            date: Date for analysis
            min_confidence: Override minimum confidence threshold
            data_manager: Data manager for technical analysis fallback
            
        Returns:
            ScannerResults with comprehensive asset conditions
        """
        start_time = time.time()
        min_confidence = min_confidence or self.min_confidence_threshold
        
        # Log scan start
        self.event_writer.log_custom_event(
            event_type='asset_scan_start',
            event_category='scanner',
            action='scan',
            reason=f'Scanning {len(tickers)} assets for market conditions',
            metadata={
                'asset_count': len(tickers),
                'database_enabled': self.is_database_available,
                'fallback_enabled': self.fallback_enabled,
                'timeframes': self.timeframes
            }
        )
        
        asset_conditions = {}
        
        # Phase 1: Database lookup (if enabled)
        database_results = {}
        if self.is_database_available:
            database_results = self._scan_from_database(tickers, date, min_confidence)
            asset_conditions.update(database_results)
        
        # Phase 2: Technical analysis fallback for missing assets
        missing_tickers = [t for t in tickers if t not in asset_conditions]
        fallback_results = {}
        
        if missing_tickers and self.fallback_enabled and data_manager:
            fallback_results = self._scan_from_technical_analysis(
                missing_tickers, date, data_manager, min_confidence
            )
            asset_conditions.update(fallback_results)
        
        # Phase 3: Create results object
        results = ScannerResults(
            asset_conditions=asset_conditions,
            scan_date=date,
            total_assets_scanned=len(tickers)
        )
        
        # Log scan completion
        scan_duration = time.time() - start_time
        self.event_writer.log_custom_event(
            event_type='asset_scan_complete',
            event_category='scanner',
            action='scan',
            reason=f'Completed scan in {scan_duration:.2f}s',
            metadata={
                'scan_duration_ms': scan_duration * 1000,
                'database_assets': results.database_assets,
                'fallback_assets': results.fallback_assets,
                'average_confidence': results.average_confidence,
                'summary_stats': results.get_summary_stats()
            }
        )
        
        return results
    
    def _scan_from_database(self, 
                           tickers: List[str], 
                           date: datetime, 
                           min_confidence: float) -> Dict[str, AssetCondition]:
        """
        Primary scanner method - attempts database first
        
        Query database for pre-calculated asset market conditions across timeframes
        
        Args:
            tickers: List of tickers to scan
            date: Date for analysis
            min_confidence: Minimum confidence threshold
            
        Returns:
            Dict mapping ticker to AssetCondition
        """
        if not self.is_database_available:
            return {}
        
        # Check cache first
        cache_key = f"db_scan_{date.strftime('%Y%m%d')}_{len(tickers)}_{min_confidence}"
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if time.time() - cache_entry['timestamp'] < self.cache_ttl:
                # Filter for requested tickers
                return {t: ac for t, ac in cache_entry['data'].items() if t in tickers}
        
        # Query database
        date_str = date.strftime('%Y-%m-%d')
        
        scanner_data = execute_query("""
            SELECT ticker, market, confidence, timeframe, date
            FROM scanner_historical
            WHERE ticker = ANY(:tickers)
            AND confidence >= :min_confidence
            AND date <= :date
            ORDER BY ticker, timeframe, confidence DESC, date DESC
        """, {
            "tickers": tickers,
            "date": date_str,
            "min_confidence": min_confidence
        })
        
        if not scanner_data:
            return {}
        
        # Group by ticker and process
        ticker_data = defaultdict(list)
        for row in scanner_data:
            ticker_data[row['ticker']].append(row)
        
        asset_conditions = {}
        for ticker, rows in ticker_data.items():
            asset_condition = self._process_database_ticker_data(ticker, rows, date)
            if asset_condition and asset_condition.confidence >= min_confidence:
                asset_conditions[ticker] = asset_condition
        
        # Cache results
        self.cache[cache_key] = {
            'timestamp': time.time(),
            'data': asset_conditions
        }
        
        return asset_conditions
    
    def _process_database_ticker_data(self, 
                                     ticker: str, 
                                     rows: List[Dict], 
                                     date: datetime) -> Optional[AssetCondition]:
        """
        Process database rows for a single ticker into AssetCondition
        
        Combines multiple timeframe data using confidence weighting
        """
        if not rows:
            return None
        
        # Group by timeframe, take most recent/confident entry per timeframe
        timeframe_data = {}
        for row in rows:
            tf = row['timeframe']
            if tf not in timeframe_data or row['confidence'] > timeframe_data[tf]['confidence']:
                timeframe_data[tf] = row
        
        # Calculate weighted confidence and determine dominant condition
        condition_votes = defaultdict(float)
        timeframe_breakdown = {}
        total_weight = 0.0
        
        for tf, data in timeframe_data.items():
            weight = self.confidence_weights.get(tf, 0.1)
            confidence = data['confidence']
            market_condition = MarketCondition(data['market'])
            
            condition_votes[market_condition] += confidence * weight
            timeframe_breakdown[tf] = confidence
            total_weight += weight
        
        if not condition_votes:
            return None
        
        # Determine dominant condition
        dominant_condition = max(condition_votes.items(), key=lambda x: x[1])
        market_condition = dominant_condition[0]
        weighted_confidence = dominant_condition[1] / total_weight if total_weight > 0 else 0.0
        
        return AssetCondition(
            ticker=ticker,
            market=market_condition,
            confidence=weighted_confidence,
            timeframe_breakdown=timeframe_breakdown,
            source=ScannerSource.DATABASE,
            scan_date=date,
            metadata={
                'database_rows': len(rows),
                'timeframes_available': list(timeframe_data.keys()),
                'condition_votes': {c.value: v for c, v in condition_votes.items()}
            }
        )
    
    def _scan_from_technical_analysis(self, 
                                     tickers: List[str], 
                                     date: datetime,
                                     data_manager,
                                     min_confidence: float) -> Dict[str, AssetCondition]:
        """
        Fallback scanner using multi-timeframe technical analysis
        
        Used when database is unavailable or disabled, or for missing tickers
        
        Args:
            tickers: List of tickers to analyze
            date: Analysis date
            data_manager: Data manager for price data
            min_confidence: Minimum confidence threshold
            
        Returns:
            Dict mapping ticker to AssetCondition
        """
        if not self.fallback_enabled or not data_manager:
            return {}
        
        asset_conditions = {}
        
        for ticker in tickers:
            try:
                asset_condition = self._analyze_asset_technical(ticker, date, data_manager)
                if asset_condition and asset_condition.confidence >= min_confidence:
                    asset_conditions[ticker] = asset_condition
            except Exception as e:
                # Log error but continue with other assets
                self.event_writer.log_custom_event(
                    event_type='technical_analysis_error',
                    event_category='scanner',
                    action='analyze',
                    reason=f'Technical analysis failed for {ticker}: {e}',
                    metadata={'ticker': ticker, 'error': str(e)}
                )
        
        return asset_conditions
    
    def _analyze_asset_technical(self, 
                                ticker: str, 
                                date: datetime, 
                                data_manager) -> Optional[AssetCondition]:
        """
        Analyze single asset using technical analysis across multiple timeframes
        
        Implements real technical analysis using multi-timeframe indicator calculations
        """
        try:
            # Analyze each timeframe and collect results
            timeframe_results = {}
            timeframe_breakdown = {}
            
            for timeframe in self.timeframes:
                # Get price data for this timeframe
                price_data = self._get_price_data(ticker, date, timeframe, data_manager)
                
                if price_data is None or len(price_data) < 20:
                    continue
                
                # Ensure proper column names for technical analysis
                price_data = self._standardize_columns(price_data)
                
                # Calculate technical indicators
                tech_result = self.technical_calculator.calculate_all_indicators(price_data, timeframe)
                
                # Determine market condition and confidence
                condition, confidence = self._determine_market_condition(tech_result)
                
                timeframe_results[timeframe] = {
                    'condition': condition,
                    'confidence': confidence,
                    'technical_result': tech_result
                }
                timeframe_breakdown[timeframe] = confidence
            
            if not timeframe_results:
                return None
            
            # Aggregate results across timeframes using confidence weights
            final_condition, final_confidence = self._aggregate_timeframe_results(timeframe_results)
            
            # Create asset condition
            return AssetCondition(
                ticker=ticker,
                market=final_condition,
                confidence=final_confidence,
                timeframe_breakdown=timeframe_breakdown,
                source=ScannerSource.FALLBACK,
                scan_date=date,
                metadata={
                    'technical_analysis': True,
                    'timeframes_analyzed': list(timeframe_results.keys()),
                    'analysis_method': 'multi_timeframe_technical',
                    'indicators_used': [
                        'ADX', 'MA_alignment', 'MACD', 'Bollinger_Bands', 
                        'RSI', 'ATR', 'Volume_analysis'
                    ]
                }
            )
            
        except Exception as e:
            # Log error and return None
            self.event_writer.log_custom_event(
                event_type='technical_analysis_error',
                event_category='scanner',
                action='analyze',
                reason=f'Technical analysis failed for {ticker}: {e}',
                metadata={'ticker': ticker, 'error': str(e)}
            )
            return None
    
    def _get_price_data(self, 
                       ticker: str, 
                       date: datetime, 
                       timeframe: str, 
                       data_manager) -> Optional[pd.DataFrame]:
        """
        Get price data for technical analysis using real data manager
        
        Args:
            ticker: Asset ticker
            date: Analysis date (end date)
            timeframe: Timeframe ('1d', '4h', '1h')
            data_manager: Data manager for price data access
            
        Returns:
            DataFrame with OHLCV data or None if unavailable
        """
        if not data_manager:
            print(f"ERROR: No data manager provided for {ticker} price data")
            return None
        
        try:
            # Determine how much historical data we need for technical analysis
            periods_needed = {
                '1d': 100,   # 100 days for proper indicator calculation
                '4h': 400,   # More 4h periods for same historical depth
                '1h': 800    # More 1h periods for same historical depth
            }
            
            periods = periods_needed.get(timeframe, 100)
            
            # Calculate start date with sufficient lookback
            lookback_days = periods if timeframe == '1d' else periods // 6  # Assume ~6 bars per day for intraday
            start_date = date - timedelta(days=lookback_days)
            
            # Try to get data from data manager
            if hasattr(data_manager, 'get_price_data') and callable(getattr(data_manager, 'get_price_data')):
                try:
                    price_data = data_manager.get_price_data(
                        ticker=ticker,
                        start_date=start_date,
                        end_date=date,
                        timeframe=timeframe
                    )
                    
                    # Validate the data
                    if self._validate_price_data(price_data, ticker):
                        return price_data
                        
                except Exception as e:
                    print(f"Error getting price data for {ticker}: {e}")
            
            # No real data available
            print(f"ERROR: No real price data available for {ticker} timeframe {timeframe}")
            return None
            
        except Exception as e:
            print(f"Error in _get_price_data for {ticker}: {e}")
            return None
    
    def _validate_price_data(self, price_data: pd.DataFrame, ticker: str) -> bool:
        """
        Validate price data for technical analysis
        
        Args:
            price_data: DataFrame with price data
            ticker: Asset ticker for error messages
            
        Returns:
            True if data is valid, False otherwise
        """
        if price_data is None:
            return False
        
        # Check if it's a real DataFrame (not Mock object)
        if not hasattr(price_data, 'columns') or not hasattr(price_data, '__len__'):
            print(f"Invalid data type for {ticker}: {type(price_data)}")
            return False
        
        # Check minimum data length for technical analysis
        if len(price_data) < 20:
            print(f"Insufficient data for {ticker}: {len(price_data)} periods (minimum 20)")
            return False
        
        # Check required columns exist (case insensitive)
        columns_lower = [col.lower() for col in price_data.columns]
        required_cols = ['open', 'high', 'low', 'close']
        
        missing_cols = [col for col in required_cols if col not in columns_lower]
        if missing_cols:
            print(f"Missing required columns for {ticker}: {missing_cols}")
            return False
        
        # Check for excessive NaN values
        for col in required_cols:
            col_data = price_data[col] if col in price_data.columns else price_data[col.title()]
            nan_pct = col_data.isna().sum() / len(col_data)
            if nan_pct > 0.1:  # More than 10% NaN
                print(f"Too many NaN values in {col} for {ticker}: {nan_pct:.1%}")
                return False
        
        return True
    
    def _standardize_columns(self, price_data: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize column names for technical analysis
        
        Args:
            price_data: DataFrame with OHLCV data
            
        Returns:
            DataFrame with standardized column names
        """
        # Create a copy to avoid modifying original data
        df = price_data.copy()
        
        # Standard column mapping (from various sources to our expected format)
        column_mapping = {
            'Open': 'open',
            'High': 'high', 
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
            'Adj Close': 'adj_close'
        }
        
        # Apply column mapping
        df = df.rename(columns=column_mapping)
        
        # Ensure lowercase column names
        df.columns = [col.lower() for col in df.columns]
        
        return df
    
    def _determine_market_condition(self, tech_result) -> Tuple[MarketCondition, float]:
        """
        Determine market condition from technical analysis results
        
        Args:
            tech_result: TechnicalAnalysisResult with calculated indicators
            
        Returns:
            Tuple of (MarketCondition, confidence_score)
        """
        # Get derived scores
        scores = {
            MarketCondition.TRENDING: tech_result.trend_score,
            MarketCondition.RANGING: tech_result.range_score,
            MarketCondition.BREAKOUT: tech_result.breakout_score,
            MarketCondition.BREAKDOWN: tech_result.breakdown_score
        }
        
        # Find dominant condition
        dominant_condition = max(scores.items(), key=lambda x: x[1])
        condition = dominant_condition[0]
        confidence = dominant_condition[1]
        
        # Apply minimum confidence threshold
        if confidence < 0.3:
            # If all scores are low, default to ranging
            condition = MarketCondition.RANGING
            confidence = max(0.3, confidence)
        
        # Clamp confidence to valid range
        confidence = max(0.0, min(1.0, confidence))
        
        return condition, confidence
    
    def _aggregate_timeframe_results(self, timeframe_results: Dict) -> Tuple[MarketCondition, float]:
        """
        Aggregate market condition results across multiple timeframes
        
        Args:
            timeframe_results: Dict mapping timeframe to analysis results
            
        Returns:
            Tuple of (final_condition, final_confidence)
        """
        # Weight votes by timeframe importance and confidence
        condition_votes = defaultdict(float)
        total_weight = 0.0
        
        for timeframe, result in timeframe_results.items():
            weight = self.confidence_weights.get(timeframe, 0.1)
            confidence = result['confidence']
            condition = result['condition']
            
            # Vote strength = weight * confidence
            vote_strength = weight * confidence
            condition_votes[condition] += vote_strength
            total_weight += weight
        
        if not condition_votes:
            return MarketCondition.RANGING, 0.3
        
        # Find winning condition
        winning_condition = max(condition_votes.items(), key=lambda x: x[1])
        final_condition = winning_condition[0]
        
        # Calculate final confidence (normalized by total possible weight)
        final_confidence = winning_condition[1] / total_weight if total_weight > 0 else 0.3
        
        # Ensure minimum confidence
        final_confidence = max(0.3, min(1.0, final_confidence))
        
        return final_condition, final_confidence
    
    # Convenience methods for backward compatibility
    def get_trending_assets(self, 
                           tickers: List[str], 
                           date: datetime,
                           min_confidence: float = 0.7,
                           limit: Optional[int] = None,
                           data_manager = None) -> List[str]:
        """Get assets in trending condition (backward compatibility)"""
        results = self.scan_assets(tickers, date, min_confidence, data_manager)
        trending = results.get_trending_assets(min_confidence)
        
        trending_tickers = list(trending.keys())
        if limit:
            trending_tickers = trending_tickers[:limit]
        
        return trending_tickers
    
    def get_ranging_assets(self, 
                          tickers: List[str], 
                          date: datetime,
                          min_confidence: float = 0.7,
                          limit: Optional[int] = None,
                          data_manager = None) -> List[str]:
        """Get assets in ranging condition"""
        results = self.scan_assets(tickers, date, min_confidence, data_manager)
        ranging = results.get_ranging_assets(min_confidence)
        
        ranging_tickers = list(ranging.keys())
        if limit:
            ranging_tickers = ranging_tickers[:limit]
        
        return ranging_tickers
    
    def get_breakout_assets(self, 
                           tickers: List[str], 
                           date: datetime,
                           min_confidence: float = 0.8,
                           limit: Optional[int] = None,
                           data_manager = None) -> List[str]:
        """Get assets in breakout condition"""
        results = self.scan_assets(tickers, date, min_confidence, data_manager)
        breakout = results.get_breakout_assets(min_confidence)
        
        breakout_tickers = list(breakout.keys())
        if limit:
            breakout_tickers = breakout_tickers[:limit]
        
        return breakout_tickers
    
    def get_breakdown_assets(self, 
                            tickers: List[str], 
                            date: datetime,
                            min_confidence: float = 0.8,
                            limit: Optional[int] = None,
                            data_manager = None) -> List[str]:
        """Get assets in breakdown condition"""
        results = self.scan_assets(tickers, date, min_confidence, data_manager)
        breakdown = results.get_breakdown_assets(min_confidence)
        
        breakdown_tickers = list(breakdown.keys())
        if limit:
            breakdown_tickers = breakdown_tickers[:limit]
        
        return breakdown_tickers
    
    def clear_cache(self):
        """Clear performance cache"""
        self.cache.clear()
    
    def get_scanner_status(self) -> Dict[str, Any]:
        """Get comprehensive scanner status information"""
        return {
            'database_enabled': self.enable_database,
            'database_available': self.is_database_available,
            'fallback_enabled': self.fallback_enabled,
            'timeframes': self.timeframes,
            'confidence_weights': self.confidence_weights,
            'min_confidence_threshold': self.min_confidence_threshold,
            'cache_entries': len(self.cache),
            'cache_ttl_seconds': self.cache_ttl
        }


# Global scanner instance
_enhanced_asset_scanner = None


def get_enhanced_asset_scanner(**kwargs) -> EnhancedAssetScanner:
    """
    Get the global enhanced asset scanner instance
    
    Args:
        **kwargs: Configuration overrides for scanner initialization
        
    Returns:
        EnhancedAssetScanner instance
    """
    global _enhanced_asset_scanner
    if _enhanced_asset_scanner is None or kwargs:
        _enhanced_asset_scanner = EnhancedAssetScanner(**kwargs)
    return _enhanced_asset_scanner