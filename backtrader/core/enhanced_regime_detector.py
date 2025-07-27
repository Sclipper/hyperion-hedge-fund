"""
Module 6: Regime Context Provider - Enhanced Regime Detector

This module implements sophisticated regime detection with multi-timeframe analysis,
confidence quantification, and stability assessment capabilities.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, deque

from .regime_models import (
    RegimeState, RegimeTransition, RegimeConfidence, RegimeStability, 
    RegimeStrength, TransitionSeverity
)


class EnhancedRegimeDetector:
    """
    Enhanced regime detector with multi-timeframe analysis and confidence metrics
    """
    
    def __init__(self, base_detector, timeframes=['1d', '4h', '1h'], 
                 history_length=50, confidence_weights=None):
        """
        Initialize enhanced regime detector
        
        Args:
            base_detector: Existing RegimeDetector instance
            timeframes: List of timeframes to analyze
            history_length: Number of historical observations to maintain
            confidence_weights: Weights for timeframe confidence calculation
        """
        self.base_detector = base_detector
        self.timeframes = timeframes
        self.history_length = history_length
        
        # Default confidence weights (sum to 1.0)
        self.confidence_weights = confidence_weights or {
            '1d': 0.5,    # Daily carries most weight
            '4h': 0.3,    # 4-hour for intermediate trends  
            '1h': 0.2     # Hourly for short-term confirmation
        }
        
        # Historical tracking
        self.regime_history: deque = deque(maxlen=history_length)
        self.transition_history: List[RegimeTransition] = []
        self.current_regime: Optional[RegimeState] = None
        self.last_detection_date: Optional[datetime] = None
        
        # Regime start tracking
        self.regime_start_dates: Dict[str, datetime] = {}
        
        # Performance caching
        self._confidence_cache: Dict[str, float] = {}
        self._stability_cache: Dict[str, float] = {}
        
    def detect_current_regime(self, current_date: datetime, 
                            data_manager=None) -> RegimeState:
        """
        Enhanced regime detection with multi-timeframe analysis
        
        Args:
            current_date: Current date for detection
            data_manager: Data manager for timeframe analysis
            
        Returns:
            RegimeState with enhanced metrics
        """
        # Get base regime from existing detector
        base_regime_result = self.base_detector.get_market_regime(current_date)
        
        if base_regime_result is None or base_regime_result[0] is None:
            # Fallback regime state for missing data
            return self._create_fallback_regime_state(current_date)
        
        base_regime, base_confidence = base_regime_result
        
        # Analyze across multiple timeframes
        timeframe_analysis = self._analyze_multiple_timeframes(
            base_regime, current_date, data_manager
        )
        
        # Calculate overall confidence
        overall_confidence = self._calculate_overall_confidence(
            base_confidence, timeframe_analysis
        )
        
        # Calculate stability based on recent history
        stability = self._calculate_regime_stability(base_regime, current_date)
        
        # Calculate regime strength
        strength = self._calculate_regime_strength(
            base_regime, current_date, data_manager
        )
        
        # Get or set regime start date
        detection_date = self._get_regime_start_date(base_regime, current_date)
        duration_days = self._calculate_regime_duration(base_regime, current_date)
        
        # Create enhanced regime state
        regime_state = RegimeState(
            regime=base_regime,
            confidence=overall_confidence,
            stability=stability,
            strength=strength,
            timeframe_analysis=timeframe_analysis,
            detection_date=detection_date,
            duration_days=duration_days
        )
        
        # Update history and tracking
        self._update_regime_history(regime_state, current_date)
        self.current_regime = regime_state
        self.last_detection_date = current_date
        
        return regime_state
    
    def _create_fallback_regime_state(self, current_date: datetime) -> RegimeState:
        """Create a fallback regime state when base detector fails"""
        fallback_regime = "Goldilocks"  # Conservative fallback
        
        return RegimeState(
            regime=fallback_regime,
            confidence=0.3,  # Low confidence due to missing data
            stability=0.5,   # Neutral stability
            strength=0.4,    # Weak strength
            timeframe_analysis={'1d': 0.3, '4h': 0.3, '1h': 0.3},
            detection_date=current_date,
            duration_days=0
        )
    
    def _analyze_multiple_timeframes(self, base_regime: str, current_date: datetime,
                                   data_manager) -> Dict[str, float]:
        """
        Analyze regime indicators across multiple timeframes
        
        Args:
            base_regime: Base regime from primary detector
            current_date: Current analysis date
            data_manager: Data manager for timeframe data
            
        Returns:
            Dict mapping timeframe to confidence level
        """
        timeframe_analysis = {}
        
        for timeframe in self.timeframes:
            try:
                tf_confidence = self._analyze_timeframe_regime(
                    base_regime, current_date, timeframe, data_manager
                )
                timeframe_analysis[timeframe] = tf_confidence
            except Exception as e:
                print(f"⚠️ Error analyzing {timeframe} for {base_regime}: {e}")
                timeframe_analysis[timeframe] = 0.5  # Neutral confidence on error
        
        return timeframe_analysis
    
    def _analyze_timeframe_regime(self, base_regime: str, current_date: datetime,
                                timeframe: str, data_manager) -> float:
        """
        Analyze regime indicators for specific timeframe
        
        Args:
            base_regime: Current regime
            current_date: Analysis date
            timeframe: Timeframe to analyze ('1d', '4h', '1h')
            data_manager: Data manager instance
            
        Returns:
            Confidence level for this timeframe (0.0-1.0)
        """
        if data_manager is None:
            # Without data manager, use base confidence adjusted by timeframe
            return self._get_timeframe_base_confidence(base_regime, timeframe)
        
        try:
            # Get timeframe-specific data if available
            tf_data = self._get_timeframe_data(timeframe, current_date, data_manager)
            
            if tf_data is None:
                return self._get_timeframe_base_confidence(base_regime, timeframe)
            
            # Analyze regime-specific indicators for this timeframe
            if base_regime == 'Goldilocks':
                return self._analyze_goldilocks_indicators(tf_data, timeframe)
            elif base_regime == 'Deflation':
                return self._analyze_deflation_indicators(tf_data, timeframe)
            elif base_regime == 'Inflation':
                return self._analyze_inflation_indicators(tf_data, timeframe)
            elif base_regime == 'Reflation':
                return self._analyze_reflation_indicators(tf_data, timeframe)
            else:
                return 0.5  # Neutral confidence for unknown regime
                
        except Exception as e:
            print(f"⚠️ Error analyzing {timeframe} indicators: {e}")
            return self._get_timeframe_base_confidence(base_regime, timeframe)
    
    def _get_timeframe_base_confidence(self, regime: str, timeframe: str) -> float:
        """Get base confidence for regime/timeframe combination without data"""
        # Regime-specific base confidence levels
        base_confidences = {
            'Goldilocks': {'1d': 0.7, '4h': 0.65, '1h': 0.6},
            'Deflation': {'1d': 0.75, '4h': 0.7, '1h': 0.65},
            'Inflation': {'1d': 0.7, '4h': 0.65, '1h': 0.6},
            'Reflation': {'1d': 0.68, '4h': 0.63, '1h': 0.58}
        }
        
        return base_confidences.get(regime, {}).get(timeframe, 0.6)
    
    def _get_timeframe_data(self, timeframe: str, current_date: datetime, 
                          data_manager) -> Optional[Dict]:
        """Get timeframe-specific market data"""
        try:
            # Try to get data from data manager
            if hasattr(data_manager, 'get_timeframe_data'):
                return data_manager.get_timeframe_data(timeframe, current_date)
            elif hasattr(data_manager, 'get_current_market_data'):
                return data_manager.get_current_market_data(current_date)
            else:
                return None
        except Exception:
            return None
    
    def _analyze_goldilocks_indicators(self, tf_data: Dict, timeframe: str) -> float:
        """Analyze Goldilocks regime indicators for specific timeframe"""
        confidence = 0.6  # Base confidence
        
        # Goldilocks: Low volatility, steady growth, moderate risk appetite
        try:
            # Volatility indicators (lower is better for Goldilocks)
            vix = tf_data.get('VIX', 20)
            if vix < 15:
                confidence += 0.2
            elif vix < 20:
                confidence += 0.1
            elif vix > 30:
                confidence -= 0.2
            
            # Growth momentum indicators
            growth_momentum = tf_data.get('growth_momentum', 0.5)
            confidence += (growth_momentum - 0.5) * 0.3
            
            # Risk appetite (moderate levels preferred)
            risk_appetite = tf_data.get('risk_appetite', 0.5)
            if 0.4 <= risk_appetite <= 0.7:
                confidence += 0.1
            
            # Timeframe-specific adjustments
            if timeframe == '1d':
                # Daily trend confirmation
                trend_strength = tf_data.get('trend_strength', 0.5)
                if trend_strength > 0.6:
                    confidence += 0.1
            
        except Exception as e:
            print(f"⚠️ Error in Goldilocks analysis: {e}")
        
        return max(0.0, min(1.0, confidence))
    
    def _analyze_deflation_indicators(self, tf_data: Dict, timeframe: str) -> float:
        """Analyze Deflation regime indicators for specific timeframe"""
        confidence = 0.6  # Base confidence
        
        # Deflation: Risk-off, safe haven demand, falling prices
        try:
            # Safe haven demand indicators
            safe_haven_demand = tf_data.get('safe_haven_demand', 0.5)
            confidence += (safe_haven_demand - 0.5) * 0.4
            
            # Volatility (higher volatility supports deflation)
            vix = tf_data.get('VIX', 20)
            if vix > 25:
                confidence += 0.2
            elif vix > 20:
                confidence += 0.1
            
            # Growth weakness indicators
            growth_weakness = tf_data.get('growth_weakness', 0.5)
            confidence += (growth_weakness - 0.5) * 0.3
            
            # Deflationary pressure
            deflation_signals = tf_data.get('deflation_signals', 0.5)
            confidence += (deflation_signals - 0.5) * 0.3
            
        except Exception as e:
            print(f"⚠️ Error in Deflation analysis: {e}")
        
        return max(0.0, min(1.0, confidence))
    
    def _analyze_inflation_indicators(self, tf_data: Dict, timeframe: str) -> float:
        """Analyze Inflation regime indicators for specific timeframe"""
        confidence = 0.6  # Base confidence
        
        # Inflation: Rising prices, commodity strength, real asset preference
        try:
            # Inflationary pressure indicators
            inflation_pressure = tf_data.get('inflation_pressure', 0.5)
            confidence += (inflation_pressure - 0.5) * 0.4
            
            # Commodity strength
            commodity_strength = tf_data.get('commodity_strength', 0.5)
            confidence += (commodity_strength - 0.5) * 0.3
            
            # Real asset performance
            real_asset_strength = tf_data.get('real_asset_strength', 0.5)
            confidence += (real_asset_strength - 0.5) * 0.2
            
            # Interest rate environment
            rate_environment = tf_data.get('rate_environment', 0.5)
            if rate_environment > 0.6:  # Rising rates support inflation regime
                confidence += 0.1
            
        except Exception as e:
            print(f"⚠️ Error in Inflation analysis: {e}")
        
        return max(0.0, min(1.0, confidence))
    
    def _analyze_reflation_indicators(self, tf_data: Dict, timeframe: str) -> float:
        """Analyze Reflation regime indicators for specific timeframe"""
        confidence = 0.6  # Base confidence
        
        # Reflation: Policy support, growth recovery, risk-on sentiment
        try:
            # Policy support indicators
            policy_support = tf_data.get('policy_support', 0.5)
            confidence += (policy_support - 0.5) * 0.3
            
            # Growth recovery signals
            growth_recovery = tf_data.get('growth_recovery', 0.5)
            confidence += (growth_recovery - 0.5) * 0.3
            
            # Risk appetite (higher is better for reflation)
            risk_appetite = tf_data.get('risk_appetite', 0.5)
            confidence += (risk_appetite - 0.5) * 0.2
            
            # Cyclical asset strength
            cyclical_strength = tf_data.get('cyclical_strength', 0.5)
            confidence += (cyclical_strength - 0.5) * 0.2
            
        except Exception as e:
            print(f"⚠️ Error in Reflation analysis: {e}")
        
        return max(0.0, min(1.0, confidence))
    
    def _calculate_overall_confidence(self, base_confidence: float, 
                                    timeframe_analysis: Dict[str, float]) -> float:
        """
        Calculate overall confidence combining base and timeframe analysis
        
        Args:
            base_confidence: Base confidence from primary detector
            timeframe_analysis: Per-timeframe confidence levels
            
        Returns:
            Overall confidence level (0.0-1.0)
        """
        # Weight base confidence
        base_weight = 0.4
        timeframe_weight = 0.6
        
        # Calculate weighted timeframe confidence
        timeframe_confidence = 0.0
        total_weight = 0.0
        
        for tf, confidence in timeframe_analysis.items():
            weight = self.confidence_weights.get(tf, 0.2)
            timeframe_confidence += confidence * weight
            total_weight += weight
        
        if total_weight > 0:
            timeframe_confidence /= total_weight
        else:
            timeframe_confidence = 0.5  # Neutral fallback
        
        # Combine base and timeframe confidence
        overall_confidence = (base_confidence * base_weight + 
                            timeframe_confidence * timeframe_weight)
        
        return max(0.0, min(1.0, overall_confidence))
    
    def _calculate_regime_stability(self, current_regime: str, 
                                  current_date: datetime) -> float:
        """
        Calculate likelihood that current regime will persist
        
        Args:
            current_regime: Current regime name
            current_date: Current date
            
        Returns:
            Stability score (0.0-1.0)
        """
        if not self.regime_history:
            return 0.5  # Neutral stability for new regime
        
        # Look at recent regime consistency (last 10 observations)
        recent_regimes = [state.regime for state in list(self.regime_history)[-10:]]
        consistency = recent_regimes.count(current_regime) / len(recent_regimes)
        
        # Factor in regime duration (longer regimes more stable)
        duration = self._calculate_regime_duration(current_regime, current_date)
        duration_factor = min(duration / 30, 1.0)  # Normalize to 30 days max
        
        # Factor in historical regime duration patterns
        historical_factor = self._get_historical_stability_factor(current_regime)
        
        # Combine factors with weights
        stability = (consistency * 0.5 + 
                    duration_factor * 0.3 + 
                    historical_factor * 0.2)
        
        return max(0.0, min(1.0, stability))
    
    def _get_historical_stability_factor(self, regime: str) -> float:
        """Get historical stability factor for a regime"""
        # Regime-specific historical stability (based on typical durations)
        historical_stability = {
            'Goldilocks': 0.7,  # Typically stable periods
            'Deflation': 0.6,   # Can be persistent
            'Inflation': 0.5,   # Variable duration
            'Reflation': 0.4    # Often transitional
        }
        
        return historical_stability.get(regime, 0.5)
    
    def _calculate_regime_strength(self, regime: str, current_date: datetime,
                                 data_manager) -> float:
        """
        Calculate strength of regime characteristics
        
        Args:
            regime: Current regime name
            current_date: Current date
            data_manager: Data manager for market data
            
        Returns:
            Strength score (0.0-1.0)
        """
        try:
            # Get current market data if available
            if data_manager and hasattr(data_manager, 'get_current_market_data'):
                market_data = data_manager.get_current_market_data(current_date)
            else:
                market_data = {}
            
            # Regime-specific strength calculations
            if regime == 'Goldilocks':
                return self._calculate_goldilocks_strength(market_data)
            elif regime == 'Deflation':
                return self._calculate_deflation_strength(market_data)
            elif regime == 'Inflation':
                return self._calculate_inflation_strength(market_data)
            elif regime == 'Reflation':
                return self._calculate_reflation_strength(market_data)
            else:
                return 0.5  # Default moderate strength
                
        except Exception as e:
            print(f"⚠️ Error calculating regime strength: {e}")
            return 0.5
    
    def _calculate_goldilocks_strength(self, market_data: Dict) -> float:
        """Calculate Goldilocks regime strength"""
        # Strong Goldilocks: Low volatility, steady growth, low inflation
        vix = market_data.get('VIX', 20)
        growth_momentum = market_data.get('growth_momentum', 0.5)
        inflation_pressure = market_data.get('inflation_pressure', 0.5)
        
        strength = (
            (1.0 - min(vix / 30, 1.0)) * 0.4 +  # Lower VIX = stronger
            growth_momentum * 0.4 +
            (1.0 - inflation_pressure) * 0.2
        )
        
        return max(0.0, min(1.0, strength))
    
    def _calculate_deflation_strength(self, market_data: Dict) -> float:
        """Calculate Deflation regime strength"""
        # Strong Deflation: Falling prices, weak growth, high safe haven demand
        deflation_signals = market_data.get('deflation_signals', 0.5)
        safe_haven_demand = market_data.get('safe_haven_demand', 0.5)
        growth_weakness = market_data.get('growth_weakness', 0.5)
        
        strength = (deflation_signals * 0.4 + 
                   safe_haven_demand * 0.3 + 
                   growth_weakness * 0.3)
        
        return max(0.0, min(1.0, strength))
    
    def _calculate_inflation_strength(self, market_data: Dict) -> float:
        """Calculate Inflation regime strength"""
        # Strong Inflation: Rising prices, commodity strength, rate pressure
        inflation_pressure = market_data.get('inflation_pressure', 0.5)
        commodity_strength = market_data.get('commodity_strength', 0.5)
        rate_pressure = market_data.get('rate_pressure', 0.5)
        
        strength = (inflation_pressure * 0.4 + 
                   commodity_strength * 0.3 + 
                   rate_pressure * 0.3)
        
        return max(0.0, min(1.0, strength))
    
    def _calculate_reflation_strength(self, market_data: Dict) -> float:
        """Calculate Reflation regime strength"""
        # Strong Reflation: Policy support, growth recovery, risk appetite
        policy_support = market_data.get('policy_support', 0.5)
        growth_recovery = market_data.get('growth_recovery', 0.5)
        risk_appetite = market_data.get('risk_appetite', 0.5)
        
        strength = (policy_support * 0.4 + 
                   growth_recovery * 0.3 + 
                   risk_appetite * 0.3)
        
        return max(0.0, min(1.0, strength))
    
    def _get_regime_start_date(self, regime: str, current_date: datetime) -> datetime:
        """Get or set the start date for current regime"""
        if regime not in self.regime_start_dates:
            self.regime_start_dates[regime] = current_date
        
        return self.regime_start_dates[regime]
    
    def _calculate_regime_duration(self, regime: str, current_date: datetime) -> int:
        """Calculate days since regime started"""
        start_date = self.regime_start_dates.get(regime, current_date)
        return (current_date - start_date).days
    
    def _update_regime_history(self, regime_state: RegimeState, current_date: datetime):
        """Update regime history and handle regime changes"""
        # Add to history
        self.regime_history.append(regime_state)
        
        # Check for regime change
        if (self.current_regime and 
            self.current_regime.regime != regime_state.regime):
            
            # Reset start date for new regime
            self.regime_start_dates[regime_state.regime] = current_date
            
            print(f"🔄 Regime change detected: {self.current_regime.regime} → {regime_state.regime}")
    
    def get_regime_history(self, days: int = 30) -> List[RegimeState]:
        """Get recent regime history"""
        if days <= 0:
            return list(self.regime_history)
        
        return list(self.regime_history)[-days:]
    
    def get_current_regime_info(self) -> Optional[Dict[str, Any]]:
        """Get comprehensive current regime information"""
        if not self.current_regime:
            return None
        
        return {
            'regime': self.current_regime.regime,
            'confidence': self.current_regime.confidence,
            'stability': self.current_regime.stability,
            'strength': self.current_regime.strength,
            'duration_days': self.current_regime.duration_days,
            'timeframe_analysis': self.current_regime.timeframe_analysis,
            'detection_date': self.current_regime.detection_date.isoformat(),
            'is_stable': self.current_regime.is_stable(),
            'is_confident': self.current_regime.is_confident(),
            'is_strong': self.current_regime.is_strong()
        }
    
    def clear_cache(self):
        """Clear performance caches"""
        self._confidence_cache.clear()
        self._stability_cache.clear()
    
    def reset_history(self):
        """Reset all historical tracking"""
        self.regime_history.clear()
        self.transition_history.clear()
        self.regime_start_dates.clear()
        self.current_regime = None
        self.last_detection_date = None
        self.clear_cache() 