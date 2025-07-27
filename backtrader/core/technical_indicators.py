"""
Module 12: Enhanced Asset Scanner - Technical Indicators

Implements multi-timeframe technical analysis calculations for market condition detection.
Provides trending, ranging, breakout, and breakdown condition analysis.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass


@dataclass
class TechnicalAnalysisResult:
    """Results from technical analysis calculation"""
    adx: float
    ma_alignment_score: float
    macd_momentum: float
    trend_consistency: float
    bb_squeeze: float
    support_resistance_strength: float
    oscillator_range: float
    volatility_compression: float
    volume_surge_ratio: float
    atr_expansion: float
    
    # Derived scores
    trend_score: float = 0.0
    range_score: float = 0.0
    breakout_score: float = 0.0
    breakdown_score: float = 0.0


class TechnicalIndicatorCalculator:
    """
    Multi-timeframe technical indicator calculator for asset market condition detection
    
    Implements calculations for:
    - Trending condition detection (ADX, MA alignment, MACD)
    - Ranging condition detection (Bollinger Bands, RSI oscillation)
    - Breakout detection (Volume surge, volatility expansion)
    - Breakdown detection (Volume confirmation, momentum divergence)
    """
    
    def __init__(self):
        # Indicator parameters
        self.adx_period = 14
        self.ma_periods = [5, 10, 20, 50]
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.bb_period = 20
        self.bb_std = 2
        self.rsi_period = 14
        self.atr_period = 14
        self.volume_ma_period = 20
    
    def calculate_all_indicators(self, 
                               price_data: pd.DataFrame,
                               timeframe: str) -> TechnicalAnalysisResult:
        """
        Calculate all technical indicators for market condition detection
        
        Args:
            price_data: DataFrame with OHLCV data
            timeframe: Timeframe for analysis ('1d', '4h', '1h')
            
        Returns:
            TechnicalAnalysisResult with all calculated indicators
        """
        if len(price_data) < 50:  # Need sufficient data
            return self._create_default_result()
        
        # Core indicators
        adx = self._calculate_adx(price_data)
        ma_alignment = self._calculate_ma_alignment(price_data)
        macd_momentum = self._calculate_macd_momentum(price_data)
        trend_consistency = self._calculate_trend_consistency(price_data)
        
        # Range indicators
        bb_squeeze = self._calculate_bb_squeeze(price_data)
        sr_strength = self._calculate_support_resistance_strength(price_data)
        oscillator_range = self._calculate_oscillator_range(price_data)
        vol_compression = self._calculate_volatility_compression(price_data)
        
        # Breakout indicators
        volume_surge = self._calculate_volume_surge_ratio(price_data)
        atr_expansion = self._calculate_atr_expansion(price_data)
        
        result = TechnicalAnalysisResult(
            adx=adx,
            ma_alignment_score=ma_alignment,
            macd_momentum=macd_momentum,
            trend_consistency=trend_consistency,
            bb_squeeze=bb_squeeze,
            support_resistance_strength=sr_strength,
            oscillator_range=oscillator_range,
            volatility_compression=vol_compression,
            volume_surge_ratio=volume_surge,
            atr_expansion=atr_expansion
        )
        
        # Calculate derived scores
        self._calculate_derived_scores(result)
        
        return result
    
    def _calculate_adx(self, df: pd.DataFrame) -> float:
        """Calculate Average Directional Index (ADX)"""
        try:
            high = df['high']
            low = df['low']
            close = df['close']
            
            if len(df) < self.adx_period * 2:
                return 0.0
            
            # Calculate True Range
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # Calculate Directional Movement
            dm_plus = high - high.shift(1)
            dm_minus = low.shift(1) - low
            
            dm_plus = np.where((dm_plus > dm_minus) & (dm_plus > 0), dm_plus, 0)
            dm_minus = np.where((dm_minus > dm_plus) & (dm_minus > 0), dm_minus, 0)
            
            # Smooth using Wilder's moving average
            atr = tr.ewm(alpha=1/self.adx_period, adjust=False).mean()
            di_plus_raw = pd.Series(dm_plus).ewm(alpha=1/self.adx_period, adjust=False).mean() / atr
            di_minus_raw = pd.Series(dm_minus).ewm(alpha=1/self.adx_period, adjust=False).mean() / atr
            
            # Handle division by zero
            di_plus = 100 * di_plus_raw.fillna(0)
            di_minus = 100 * di_minus_raw.fillna(0)
            
            # Calculate DX and ADX with zero division protection
            di_sum = di_plus + di_minus
            dx = np.where(di_sum > 0, 100 * abs(di_plus - di_minus) / di_sum, 0)
            dx_series = pd.Series(dx, index=df.index)
            adx = dx_series.ewm(alpha=1/self.adx_period, adjust=False).mean()
            
            final_adx = float(adx.iloc[-1]) if not adx.empty and not np.isnan(adx.iloc[-1]) else 0.0
            return max(0.0, min(100.0, final_adx))  # Clamp to valid range
        except Exception as e:
            return 0.0
    
    def _calculate_ma_alignment(self, df: pd.DataFrame) -> float:
        """Calculate moving average alignment score (0-1)"""
        try:
            close = df['close']
            mas = {}
            
            for period in self.ma_periods:
                if len(close) >= period:
                    mas[period] = close.rolling(window=period).mean().iloc[-1]
            
            if len(mas) < 2:
                return 0.0
            
            # Check if MAs are in proper trend order
            ma_values = [mas[p] for p in sorted(self.ma_periods) if p in mas]
            
            # For uptrend: shorter MAs > longer MAs
            # For downtrend: shorter MAs < longer MAs
            uptrend_score = sum(1 for i in range(len(ma_values)-1) 
                              if ma_values[i] > ma_values[i+1]) / (len(ma_values) - 1)
            downtrend_score = sum(1 for i in range(len(ma_values)-1) 
                                if ma_values[i] < ma_values[i+1]) / (len(ma_values) - 1)
            
            # Return the stronger alignment
            return max(uptrend_score, downtrend_score)
        except:
            return 0.0
    
    def _calculate_macd_momentum(self, df: pd.DataFrame) -> float:
        """Calculate MACD momentum score"""
        try:
            close = df['close']
            
            # Calculate MACD
            exp1 = close.ewm(span=self.macd_fast).mean()
            exp2 = close.ewm(span=self.macd_slow).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=self.macd_signal).mean()
            histogram = macd - signal
            
            # Momentum score based on histogram direction and magnitude
            recent_hist = histogram.tail(5)
            if len(recent_hist) < 3:
                return 0.0
            
            # Check for consistent histogram expansion
            expanding = sum(1 for i in range(1, len(recent_hist)) 
                          if abs(recent_hist.iloc[i]) > abs(recent_hist.iloc[i-1]))
            
            momentum_score = expanding / (len(recent_hist) - 1)
            return momentum_score
        except:
            return 0.0
    
    def _calculate_trend_consistency(self, df: pd.DataFrame) -> float:
        """Calculate trend consistency over recent periods"""
        try:
            close = df['close']
            
            # Calculate price direction over last 10 periods
            price_changes = close.diff().tail(10)
            if len(price_changes) < 5:
                return 0.0
            
            positive_moves = (price_changes > 0).sum()
            negative_moves = (price_changes < 0).sum()
            total_moves = len(price_changes.dropna())
            
            if total_moves == 0:
                return 0.0
            
            # Consistency score (how many moves in same direction)
            consistency = max(positive_moves, negative_moves) / total_moves
            return consistency
        except:
            return 0.0
    
    def _calculate_bb_squeeze(self, df: pd.DataFrame) -> float:
        """Calculate Bollinger Band squeeze intensity"""
        try:
            close = df['close']
            
            # Calculate Bollinger Bands
            ma = close.rolling(window=self.bb_period).mean()
            std = close.rolling(window=self.bb_period).std()
            upper_bb = ma + (std * self.bb_std)
            lower_bb = ma - (std * self.bb_std)
            
            # Calculate band width
            bb_width = (upper_bb - lower_bb) / ma
            
            # Compare current width to recent average
            avg_width = bb_width.tail(20).mean()
            current_width = bb_width.iloc[-1]
            
            if avg_width == 0:
                return 0.0
            
            # Squeeze score (smaller width = higher squeeze)
            squeeze_score = max(0, 1 - (current_width / avg_width))
            return squeeze_score
        except:
            return 0.0
    
    def _calculate_support_resistance_strength(self, df: pd.DataFrame) -> float:
        """Calculate support/resistance level strength"""
        try:
            close = df['close']
            high = df['high']
            low = df['low']
            
            # Recent price levels
            recent_data = df.tail(20)
            current_price = close.iloc[-1]
            
            # Find potential support/resistance levels
            resistance_touches = 0
            support_touches = 0
            
            # Simple approach: check for price levels that acted as support/resistance
            for i in range(len(recent_data) - 2):
                price_range = (recent_data['high'].iloc[i] + recent_data['low'].iloc[i]) / 2
                tolerance = (recent_data['high'].iloc[i] - recent_data['low'].iloc[i]) * 0.1
                
                # Count touches near this level
                touches = sum(1 for j in range(len(recent_data))
                            if abs(recent_data['close'].iloc[j] - price_range) < tolerance)
                
                if touches >= 2:
                    if price_range > current_price:
                        resistance_touches += touches
                    else:
                        support_touches += touches
            
            # Normalize and return strength
            total_touches = resistance_touches + support_touches
            return min(1.0, total_touches / 10)  # Normalize to 0-1
        except:
            return 0.0
    
    def _calculate_oscillator_range(self, df: pd.DataFrame) -> float:
        """Calculate RSI range-bound behavior score"""
        try:
            close = df['close']
            
            # Calculate RSI
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            recent_rsi = rsi.tail(10)
            if len(recent_rsi) < 5:
                return 0.0
            
            # Check if RSI is oscillating in range (30-70)
            range_bound = sum(1 for r in recent_rsi if 30 <= r <= 70)
            range_score = range_bound / len(recent_rsi)
            
            return range_score
        except:
            return 0.0
    
    def _calculate_volatility_compression(self, df: pd.DataFrame) -> float:
        """Calculate volatility compression score"""
        try:
            close = df['close']
            
            # Calculate ATR
            high = df['high']
            low = df['low']
            
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=self.atr_period).mean()
            
            # Compare recent ATR to longer term average
            recent_atr = atr.tail(5).mean()
            longer_atr = atr.tail(20).mean()
            
            if longer_atr == 0:
                return 0.0
            
            # Compression score (lower recent volatility)
            compression = max(0, 1 - (recent_atr / longer_atr))
            return compression
        except:
            return 0.0
    
    def _calculate_volume_surge_ratio(self, df: pd.DataFrame) -> float:
        """Calculate volume surge ratio"""
        try:
            if 'volume' not in df.columns:
                return 0.0
            
            volume = df['volume']
            
            # Calculate volume moving average
            vol_ma = volume.rolling(window=self.volume_ma_period).mean()
            current_volume = volume.iloc[-1]
            avg_volume = vol_ma.iloc[-1]
            
            if avg_volume == 0:
                return 0.0
            
            # Surge ratio (current volume vs average)
            surge_ratio = current_volume / avg_volume
            
            # Normalize to 0-1 scale (2x volume = 0.5, 4x volume = 0.75, etc.)
            normalized_surge = min(1.0, (surge_ratio - 1) / 3)
            return max(0.0, normalized_surge)
        except:
            return 0.0
    
    def _calculate_atr_expansion(self, df: pd.DataFrame) -> float:
        """Calculate ATR expansion score"""
        try:
            high = df['high']
            low = df['low']
            close = df['close']
            
            # Calculate True Range and ATR
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=self.atr_period).mean()
            
            # Compare recent ATR to longer period
            recent_atr = atr.tail(5).mean()
            baseline_atr = atr.tail(20).mean()
            
            if baseline_atr == 0:
                return 0.0
            
            # Expansion ratio
            expansion_ratio = recent_atr / baseline_atr
            
            # Normalize (1.5x expansion = 0.5, 2x expansion = 0.75, etc.)
            normalized_expansion = min(1.0, (expansion_ratio - 1) / 1)
            return max(0.0, normalized_expansion)
        except:
            return 0.0
    
    def _calculate_derived_scores(self, result: TechnicalAnalysisResult):
        """Calculate derived condition scores from individual indicators"""
        
        # Handle NaN values in ADX
        adx_normalized = 0.0 if np.isnan(result.adx) else result.adx / 100
        
        # Trending Score (weighted combination)
        result.trend_score = (
            adx_normalized * 0.4 +                # ADX strength
            result.ma_alignment_score * 0.3 +     # MA alignment
            result.macd_momentum * 0.2 +          # MACD momentum
            result.trend_consistency * 0.1        # Trend consistency
        )
        
        # Ranging Score (weighted combination)
        result.range_score = (
            result.bb_squeeze * 0.3 +                    # BB squeeze
            result.support_resistance_strength * 0.3 +   # S/R strength
            result.oscillator_range * 0.2 +              # RSI range
            result.volatility_compression * 0.2          # Low volatility
        )
        
        # Breakout Score (volume + volatility expansion)
        result.breakout_score = (
            result.volume_surge_ratio * 0.6 +      # Volume surge
            result.atr_expansion * 0.4             # Volatility expansion
        )
        
        # Breakdown Score (similar to breakout but with trend reversal)
        # For Phase 2, using same calculation as breakout
        # Will be refined in later phases to detect negative momentum
        result.breakdown_score = result.breakout_score * (1 - result.trend_score)
    
    def _create_default_result(self) -> TechnicalAnalysisResult:
        """Create default result when insufficient data"""
        return TechnicalAnalysisResult(
            adx=0.0,
            ma_alignment_score=0.0,
            macd_momentum=0.0,
            trend_consistency=0.0,
            bb_squeeze=0.0,
            support_resistance_strength=0.0,
            oscillator_range=0.0,
            volatility_compression=0.0,
            volume_surge_ratio=0.0,
            atr_expansion=0.0,
            trend_score=0.0,
            range_score=0.0,
            breakout_score=0.0,
            breakdown_score=0.0
        )


def get_technical_calculator() -> TechnicalIndicatorCalculator:
    """Get global technical indicator calculator instance"""
    global _calculator
    if '_calculator' not in globals():
        _calculator = TechnicalIndicatorCalculator()
    return _calculator