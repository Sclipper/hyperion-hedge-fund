import logging
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Results from data validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]
    corrected_data: Optional[pd.DataFrame] = None


class DataValidator:
    """
    Comprehensive data validation for Alpha Vantage market data
    
    Features:
    - OHLCV data integrity checks
    - Market hours validation
    - Price reasonableness checks
    - Volume validation
    - Gap detection and analysis
    - Data completeness assessment
    """
    
    def __init__(self):
        # Market hours for validation (Eastern Time)
        self.market_hours = {
            'stock': {
                'open': '09:30',
                'close': '16:00',
                'pre_market_start': '04:00',
                'after_hours_end': '20:00'
            },
            'crypto': {
                'open': '00:00',  # 24/7 trading
                'close': '23:59'
            }
        }
        
        # Price validation thresholds
        self.price_limits = {
            'min_price': 0.01,
            'max_price': 100000.0,
            'max_daily_change': 0.50,  # 50% max daily change
            'max_intraday_gap': 0.20   # 20% max gap between periods
        }
        
        # Volume validation
        self.volume_limits = {
            'min_volume': 0,
            'max_volume': 1e12,
            'max_volume_spike': 10.0  # 10x average volume
        }
        
        logger.info("DataValidator initialized with market validation rules")
    
    def validate_dataframe(self, df: pd.DataFrame, ticker: str, 
                          timeframe: str, asset_type: str = 'stock') -> ValidationResult:
        """
        Comprehensive validation of OHLCV DataFrame
        
        Args:
            df: DataFrame to validate
            ticker: Symbol being validated
            timeframe: Data timeframe
            asset_type: 'stock' or 'crypto'
            
        Returns:
            ValidationResult with validation details
        """
        errors = []
        warnings = []
        metadata = {
            'ticker': ticker,
            'timeframe': timeframe,
            'asset_type': asset_type,
            'original_rows': len(df),
            'validation_timestamp': datetime.now().isoformat()
        }
        
        if df.empty:
            errors.append("DataFrame is empty")
            return ValidationResult(False, errors, warnings, metadata)
        
        # 1. Schema validation
        schema_errors = self._validate_schema(df)
        errors.extend(schema_errors)
        
        # 2. OHLC relationship validation
        ohlc_errors, ohlc_warnings = self._validate_ohlc_relationships(df)
        errors.extend(ohlc_errors)
        warnings.extend(ohlc_warnings)
        
        # 3. Price reasonableness
        price_errors, price_warnings = self._validate_prices(df, ticker)
        errors.extend(price_errors)
        warnings.extend(price_warnings)
        
        # 4. Volume validation
        volume_errors, volume_warnings = self._validate_volume(df)
        errors.extend(volume_errors)
        warnings.extend(volume_warnings)
        
        # 5. Time series validation
        time_errors, time_warnings = self._validate_time_series(df, timeframe, asset_type)
        errors.extend(time_errors)
        warnings.extend(time_warnings)
        
        # 6. Gap detection
        gap_warnings = self._detect_gaps(df, timeframe, asset_type)
        warnings.extend(gap_warnings)
        
        # 7. Data completeness
        completeness_warnings = self._validate_completeness(df, timeframe)
        warnings.extend(completeness_warnings)
        
        # Update metadata with validation stats
        metadata.update({
            'total_errors': len(errors),
            'total_warnings': len(warnings),
            'date_range': f"{df.index.min()} to {df.index.max()}",
            'trading_days': len(df),
            'has_nulls': df.isnull().any().any(),
            'null_count': df.isnull().sum().sum()
        })
        
        is_valid = len(errors) == 0
        
        logger.info(f"Validation complete for {ticker} {timeframe}: "
                   f"{'PASSED' if is_valid else 'FAILED'} "
                   f"({len(errors)} errors, {len(warnings)} warnings)")
        
        return ValidationResult(is_valid, errors, warnings, metadata)
    
    def _validate_schema(self, df: pd.DataFrame) -> List[str]:
        """Validate DataFrame schema"""
        errors = []
        
        expected_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        missing_columns = [col for col in expected_columns if col not in df.columns]
        
        if missing_columns:
            errors.append(f"Missing required columns: {missing_columns}")
        
        # Check data types
        for col in expected_columns:
            if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
                errors.append(f"Column {col} is not numeric")
        
        # Check index is datetime
        if not isinstance(df.index, pd.DatetimeIndex):
            errors.append("Index is not DatetimeIndex")
        
        return errors
    
    def _validate_ohlc_relationships(self, df: pd.DataFrame) -> Tuple[List[str], List[str]]:
        """Validate OHLC price relationships"""
        errors = []
        warnings = []
        
        if not all(col in df.columns for col in ['Open', 'High', 'Low', 'Close']):
            return errors, warnings
        
        # High should be >= Open, Close, Low
        high_violations = (
            (df['High'] < df['Open']) |
            (df['High'] < df['Close']) |
            (df['High'] < df['Low'])
        ).sum()
        
        if high_violations > 0:
            errors.append(f"{high_violations} rows have High < Open/Close/Low")
        
        # Low should be <= Open, Close, High
        low_violations = (
            (df['Low'] > df['Open']) |
            (df['Low'] > df['Close']) |
            (df['Low'] > df['High'])
        ).sum()
        
        if low_violations > 0:
            errors.append(f"{low_violations} rows have Low > Open/Close/High")
        
        # Warn about unusual OHLC patterns
        equal_ohlc = (
            (df['Open'] == df['High']) &
            (df['High'] == df['Low']) &
            (df['Low'] == df['Close'])
        ).sum()
        
        if equal_ohlc > len(df) * 0.1:  # More than 10% of data
            warnings.append(f"{equal_ohlc} rows have identical OHLC (possible data issue)")
        
        return errors, warnings
    
    def _validate_prices(self, df: pd.DataFrame, ticker: str) -> Tuple[List[str], List[str]]:
        """Validate price reasonableness"""
        errors = []
        warnings = []
        
        price_columns = ['Open', 'High', 'Low', 'Close']
        available_columns = [col for col in price_columns if col in df.columns]
        
        if not available_columns:
            return errors, warnings
        
        # Check for negative or zero prices
        for col in available_columns:
            negative_prices = (df[col] <= 0).sum()
            if negative_prices > 0:
                errors.append(f"{negative_prices} rows have non-positive {col} prices")
        
        # Check for unreasonably high prices
        for col in available_columns:
            high_prices = (df[col] > self.price_limits['max_price']).sum()
            if high_prices > 0:
                warnings.append(f"{high_prices} rows have {col} > ${self.price_limits['max_price']}")
        
        # Check for unreasonably low prices  
        for col in available_columns:
            low_prices = (df[col] < self.price_limits['min_price']).sum()
            if low_prices > 0:
                warnings.append(f"{low_prices} rows have {col} < ${self.price_limits['min_price']}")
        
        # Check for extreme daily changes
        if 'Close' in df.columns and len(df) > 1:
            daily_returns = df['Close'].pct_change().abs()
            extreme_changes = (daily_returns > self.price_limits['max_daily_change']).sum()
            
            if extreme_changes > 0:
                max_change = daily_returns.max()
                warnings.append(f"{extreme_changes} periods have >50% price changes (max: {max_change:.1%})")
        
        return errors, warnings
    
    def _validate_volume(self, df: pd.DataFrame) -> Tuple[List[str], List[str]]:
        """Validate volume data"""
        errors = []
        warnings = []
        
        if 'Volume' not in df.columns:
            return errors, warnings
        
        # Check for negative volume
        negative_volume = (df['Volume'] < 0).sum()
        if negative_volume > 0:
            errors.append(f"{negative_volume} rows have negative volume")
        
        # Check for unreasonably high volume
        high_volume = (df['Volume'] > self.volume_limits['max_volume']).sum()
        if high_volume > 0:
            warnings.append(f"{high_volume} rows have volume > {self.volume_limits['max_volume']:,}")
        
        # Check for volume spikes
        if len(df) > 10:
            volume_median = df['Volume'].rolling(10).median()
            volume_spikes = (df['Volume'] > volume_median * self.volume_limits['max_volume_spike']).sum()
            
            if volume_spikes > 0:
                warnings.append(f"{volume_spikes} rows have volume spikes >10x median")
        
        # Check for too many zero volume periods
        zero_volume = (df['Volume'] == 0).sum()
        if zero_volume > len(df) * 0.2:  # More than 20%
            warnings.append(f"{zero_volume} rows have zero volume ({zero_volume/len(df):.1%} of data)")
        
        return errors, warnings
    
    def _validate_time_series(self, df: pd.DataFrame, timeframe: str, 
                             asset_type: str) -> Tuple[List[str], List[str]]:
        """Validate time series properties"""
        errors = []
        warnings = []
        
        if len(df) < 2:
            return errors, warnings
        
        # Check for duplicate timestamps
        duplicates = df.index.duplicated().sum()
        if duplicates > 0:
            errors.append(f"{duplicates} duplicate timestamps found")
        
        # Check for proper sorting
        if not df.index.is_monotonic_increasing:
            warnings.append("Index is not sorted chronologically")
        
        # Check for reasonable time intervals
        time_diffs = df.index.to_series().diff().dropna()
        
        if timeframe == '1h':
            expected_diff = timedelta(hours=1)
            tolerance = timedelta(minutes=10)
        elif timeframe == '4h':
            expected_diff = timedelta(hours=4)
            tolerance = timedelta(minutes=30)
        elif timeframe == '1d':
            expected_diff = timedelta(days=1)
            tolerance = timedelta(hours=6)
        else:
            expected_diff = None
            tolerance = None
        
        if expected_diff and tolerance:
            irregular_intervals = (
                (time_diffs < expected_diff - tolerance) |
                (time_diffs > expected_diff + tolerance)
            ).sum()
            
            if irregular_intervals > len(df) * 0.1:  # More than 10%
                warnings.append(f"{irregular_intervals} irregular time intervals for {timeframe} data")
        
        return errors, warnings
    
    def _detect_gaps(self, df: pd.DataFrame, timeframe: str, asset_type: str) -> List[str]:
        """Detect significant data gaps"""
        warnings = []
        
        if len(df) < 2:
            return warnings
        
        time_diffs = df.index.to_series().diff().dropna()
        
        # Define what constitutes a gap based on timeframe
        if timeframe == '1h':
            gap_threshold = timedelta(hours=6)  # Missing 6+ hours
        elif timeframe == '4h':
            gap_threshold = timedelta(days=1)   # Missing 1+ day
        elif timeframe == '1d':
            gap_threshold = timedelta(days=7)   # Missing 1+ week
        else:
            gap_threshold = timedelta(days=1)
        
        gaps = time_diffs[time_diffs > gap_threshold]
        
        if len(gaps) > 0:
            max_gap = gaps.max()
            gap_dates = [str(date.date()) for date in gaps.index[:5]]  # Show first 5
            warnings.append(f"{len(gaps)} data gaps detected (max: {max_gap}, dates: {gap_dates})")
        
        return warnings
    
    def _validate_completeness(self, df: pd.DataFrame, timeframe: str) -> List[str]:
        """Validate data completeness"""
        warnings = []
        
        # Check for null values
        null_counts = df.isnull().sum()
        total_nulls = null_counts.sum()
        
        if total_nulls > 0:
            null_cols = null_counts[null_counts > 0].to_dict()
            warnings.append(f"{total_nulls} null values found: {null_cols}")
        
        # Check expected data density based on timeframe
        if len(df) > 0:
            date_range = df.index.max() - df.index.min()
            
            if timeframe == '1h':
                # Expect ~6.5 hours/day trading * 5 days/week = 32.5 hours/week
                expected_points = (date_range.days / 7) * 32.5
            elif timeframe == '4h':
                # Expect ~1.6 periods/day * 5 days/week = 8 periods/week
                expected_points = (date_range.days / 7) * 8
            elif timeframe == '1d':
                # Expect ~5 trading days/week
                expected_points = (date_range.days / 7) * 5
            else:
                expected_points = None
            
            if expected_points:
                completeness = len(df) / expected_points
                if completeness < 0.8:  # Less than 80% complete
                    warnings.append(f"Data completeness: {completeness:.1%} "
                                  f"({len(df)} of ~{expected_points:.0f} expected points)")
        
        return warnings
    
    def repair_data(self, df: pd.DataFrame, validation_result: ValidationResult) -> pd.DataFrame:
        """
        Attempt to repair common data issues
        
        Args:
            df: Original DataFrame
            validation_result: Validation results
            
        Returns:
            Repaired DataFrame
        """
        if validation_result.is_valid:
            return df.copy()
        
        repaired_df = df.copy()
        repairs_made = []
        
        # 1. Remove duplicate timestamps
        if repaired_df.index.duplicated().any():
            repaired_df = repaired_df[~repaired_df.index.duplicated(keep='last')]
            repairs_made.append("Removed duplicate timestamps")
        
        # 2. Sort by timestamp
        if not repaired_df.index.is_monotonic_increasing:
            repaired_df = repaired_df.sort_index()
            repairs_made.append("Sorted by timestamp")
        
        # 3. Remove rows with negative/zero prices
        price_cols = ['Open', 'High', 'Low', 'Close']
        available_price_cols = [col for col in price_cols if col in repaired_df.columns]
        
        for col in available_price_cols:
            before_count = len(repaired_df)
            repaired_df = repaired_df[repaired_df[col] > 0]
            after_count = len(repaired_df)
            
            if before_count != after_count:
                repairs_made.append(f"Removed {before_count - after_count} rows with non-positive {col}")
        
        # 4. Remove rows with negative volume
        if 'Volume' in repaired_df.columns:
            before_count = len(repaired_df)
            repaired_df = repaired_df[repaired_df['Volume'] >= 0]
            after_count = len(repaired_df)
            
            if before_count != after_count:
                repairs_made.append(f"Removed {before_count - after_count} rows with negative volume")
        
        # 5. Cap extreme prices
        for col in available_price_cols:
            extreme_high = repaired_df[col] > self.price_limits['max_price']
            if extreme_high.any():
                repaired_df.loc[extreme_high, col] = self.price_limits['max_price']
                repairs_made.append(f"Capped {extreme_high.sum()} extreme high {col} values")
        
        if repairs_made:
            logger.info(f"Data repairs applied: {repairs_made}")
        
        return repaired_df
    
    def get_validation_summary(self, validation_result: ValidationResult) -> str:
        """Generate human-readable validation summary"""
        summary = []
        
        if validation_result.is_valid:
            summary.append("✅ Data validation PASSED")
        else:
            summary.append("❌ Data validation FAILED")
        
        summary.append(f"Ticker: {validation_result.metadata['ticker']}")
        summary.append(f"Timeframe: {validation_result.metadata['timeframe']}")
        summary.append(f"Rows: {validation_result.metadata['original_rows']}")
        summary.append(f"Date Range: {validation_result.metadata.get('date_range', 'N/A')}")
        
        if validation_result.errors:
            summary.append(f"\n🚨 Errors ({len(validation_result.errors)}):")
            for error in validation_result.errors:
                summary.append(f"  • {error}")
        
        if validation_result.warnings:
            summary.append(f"\n⚠️ Warnings ({len(validation_result.warnings)}):")
            for warning in validation_result.warnings[:5]:  # Show first 5
                summary.append(f"  • {warning}")
            if len(validation_result.warnings) > 5:
                summary.append(f"  ... and {len(validation_result.warnings) - 5} more")
        
        return "\n".join(summary)