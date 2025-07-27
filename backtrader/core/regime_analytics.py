"""
Module 6: Regime Context Provider - Regime Analytics Engine

This module implements comprehensive regime analytics including performance analysis,
transition impact assessment, historical pattern recognition, and regime forecasting.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, Counter
from dataclasses import dataclass, field

from .regime_models import (
    RegimeState, RegimeTransition, RegimeAnalytics, TransitionSeverity
)


@dataclass
class RegimePerformanceMetrics:
    """Performance metrics for a specific regime"""
    regime: str
    total_days: int
    avg_confidence: float
    avg_stability: float
    avg_strength: float
    transition_count: int
    avg_duration: float
    confidence_trend: str
    stability_trend: str
    performance_score: float


@dataclass
class TransitionAnalysis:
    """Analysis of regime transitions"""
    transition_pair: Tuple[str, str]
    frequency: int
    avg_momentum: float
    avg_confidence: float
    success_rate: float
    avg_duration: int
    severity_distribution: Dict[str, int]
    common_triggers: List[str]


class RegimeAnalyticsEngine:
    """
    Comprehensive regime analytics and performance analysis engine
    """
    
    def __init__(self, analysis_window_days=90, min_data_points=10):
        """
        Initialize regime analytics engine
        
        Args:
            analysis_window_days: Default analysis window
            min_data_points: Minimum data points for reliable analysis
        """
        self.analysis_window_days = analysis_window_days
        self.min_data_points = min_data_points
        
        # Analytics storage
        self.regime_history: List[RegimeState] = []
        self.transition_history: List[RegimeTransition] = []
        self.performance_history: Dict[str, List[float]] = defaultdict(list)
        
        # Analysis cache
        self.analytics_cache: Dict[str, Any] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
        self.cache_duration = timedelta(hours=6)  # Cache for 6 hours
        
        # Patterns and insights
        self.detected_patterns: List[Dict[str, Any]] = []
        self.regime_correlations: Dict[str, Dict[str, float]] = {}
        
        # Performance tracking
        self.analysis_stats = {
            'total_analyses': 0,
            'cache_hits': 0,
            'patterns_detected': 0,
            'forecasts_generated': 0
        }
    
    def add_regime_observation(self, regime_state: RegimeState, 
                             performance_data: Optional[Dict[str, float]] = None):
        """
        Add regime observation to analytics
        
        Args:
            regime_state: Regime state observation
            performance_data: Optional performance data for the period
        """
        self.regime_history.append(regime_state)
        
        # Add performance data if provided
        if performance_data:
            for metric, value in performance_data.items():
                self.performance_history[metric].append(value)
        
        # Maintain history size
        max_history = self.analysis_window_days * 2  # Keep double window for analysis
        if len(self.regime_history) > max_history:
            self.regime_history.pop(0)
            
            # Trim performance history too
            for metric in self.performance_history:
                if len(self.performance_history[metric]) > max_history:
                    self.performance_history[metric].pop(0)
        
        # Clear cache when new data arrives
        self._clear_analysis_cache()
    
    def add_transition_observation(self, transition: RegimeTransition):
        """
        Add transition observation to analytics
        
        Args:
            transition: Regime transition observation
        """
        self.transition_history.append(transition)
        
        # Maintain transition history size
        max_transitions = 100
        if len(self.transition_history) > max_transitions:
            self.transition_history.pop(0)
        
        # Clear cache
        self._clear_analysis_cache()
    
    def analyze_regime_performance(self, regime: Optional[str] = None,
                                 analysis_period_days: Optional[int] = None) -> Dict[str, RegimePerformanceMetrics]:
        """
        Analyze performance metrics for regimes
        
        Args:
            regime: Specific regime to analyze (None for all)
            analysis_period_days: Analysis period (None for default)
            
        Returns:
            Dictionary mapping regime to performance metrics
        """
        self.analysis_stats['total_analyses'] += 1
        
        period = analysis_period_days or self.analysis_window_days
        cache_key = f"regime_performance_{regime}_{period}"
        
        # Check cache
        if self._is_cache_valid(cache_key):
            self.analysis_stats['cache_hits'] += 1
            return self.analytics_cache[cache_key]
        
        # Get recent regime history
        cutoff_date = datetime.now() - timedelta(days=period)
        recent_history = [
            r for r in self.regime_history
            if hasattr(r, 'detection_date') and r.detection_date >= cutoff_date
        ]
        
        if len(recent_history) < self.min_data_points:
            print(f"⚠️ Insufficient data for regime performance analysis: {len(recent_history)} < {self.min_data_points}")
            return {}
        
        # Group by regime
        regime_groups = defaultdict(list)
        for state in recent_history:
            regime_groups[state.regime].append(state)
        
        # Filter by specific regime if requested
        if regime:
            regime_groups = {regime: regime_groups.get(regime, [])}
        
        # Calculate performance metrics for each regime
        performance_metrics = {}
        for regime_name, states in regime_groups.items():
            if len(states) < 3:  # Need minimum observations
                continue
            
            metrics = self._calculate_regime_performance_metrics(regime_name, states)
            performance_metrics[regime_name] = metrics
        
        # Cache results
        self._cache_result(cache_key, performance_metrics)
        return performance_metrics
    
    def analyze_transition_patterns(self, analysis_period_days: Optional[int] = None) -> Dict[Tuple[str, str], TransitionAnalysis]:
        """
        Analyze regime transition patterns and characteristics
        
        Args:
            analysis_period_days: Analysis period (None for default)
            
        Returns:
            Dictionary mapping transition pairs to analysis
        """
        period = analysis_period_days or self.analysis_window_days
        cache_key = f"transition_patterns_{period}"
        
        # Check cache
        if self._is_cache_valid(cache_key):
            self.analysis_stats['cache_hits'] += 1
            return self.analytics_cache[cache_key]
        
        # Get recent transitions
        cutoff_date = datetime.now() - timedelta(days=period)
        recent_transitions = [
            t for t in self.transition_history
            if t.transition_date >= cutoff_date
        ]
        
        if len(recent_transitions) < 3:
            print(f"⚠️ Insufficient transition data: {len(recent_transitions)} < 3")
            return {}
        
        # Group by transition pair
        transition_groups = defaultdict(list)
        for transition in recent_transitions:
            key = (transition.from_regime, transition.to_regime)
            transition_groups[key].append(transition)
        
        # Analyze each transition pattern
        pattern_analysis = {}
        for transition_pair, transitions in transition_groups.items():
            analysis = self._analyze_transition_pattern(transition_pair, transitions)
            pattern_analysis[transition_pair] = analysis
        
        # Cache and return
        self._cache_result(cache_key, pattern_analysis)
        return pattern_analysis
    
    def detect_regime_patterns(self, pattern_window_days: int = 30) -> List[Dict[str, Any]]:
        """
        Detect patterns in regime behavior
        
        Args:
            pattern_window_days: Window for pattern detection
            
        Returns:
            List of detected patterns
        """
        cache_key = f"regime_patterns_{pattern_window_days}"
        
        if self._is_cache_valid(cache_key):
            return self.analytics_cache[cache_key]
        
        patterns = []
        
        # Pattern 1: Regime Stability Cycles
        stability_pattern = self._detect_stability_cycles(pattern_window_days)
        if stability_pattern:
            patterns.append(stability_pattern)
        
        # Pattern 2: Confidence Momentum
        confidence_pattern = self._detect_confidence_momentum(pattern_window_days)
        if confidence_pattern:
            patterns.append(confidence_pattern)
        
        # Pattern 3: Transition Clustering
        clustering_pattern = self._detect_transition_clustering(pattern_window_days)
        if clustering_pattern:
            patterns.append(clustering_pattern)
        
        # Pattern 4: Regime Duration Patterns
        duration_pattern = self._detect_duration_patterns(pattern_window_days)
        if duration_pattern:
            patterns.append(duration_pattern)
        
        self.detected_patterns.extend(patterns)
        self.analysis_stats['patterns_detected'] += len(patterns)
        
        # Cache and return
        self._cache_result(cache_key, patterns)
        return patterns
    
    def forecast_regime_probability(self, current_regime: RegimeState,
                                  forecast_days: int = 7) -> Dict[str, float]:
        """
        Forecast probability of regime transitions
        
        Args:
            current_regime: Current regime state
            forecast_days: Number of days to forecast
            
        Returns:
            Dictionary mapping regime to probability
        """
        self.analysis_stats['forecasts_generated'] += 1
        
        # Base probabilities from historical data
        base_probabilities = self._calculate_base_transition_probabilities(current_regime.regime)
        
        # Adjust based on current regime characteristics
        adjusted_probabilities = self._adjust_probabilities_for_state(
            base_probabilities, current_regime, forecast_days
        )
        
        # Apply pattern-based adjustments
        pattern_adjusted = self._apply_pattern_adjustments(
            adjusted_probabilities, current_regime
        )
        
        # Normalize to sum to 1.0
        total_prob = sum(pattern_adjusted.values())
        if total_prob > 0:
            normalized_probabilities = {
                regime: prob / total_prob
                for regime, prob in pattern_adjusted.items()
            }
        else:
            # Fallback to uniform distribution
            regimes = ['Goldilocks', 'Deflation', 'Inflation', 'Reflation']
            normalized_probabilities = {regime: 0.25 for regime in regimes}
        
        return normalized_probabilities
    
    def get_regime_correlation_matrix(self) -> Dict[str, Dict[str, float]]:
        """
        Calculate correlation matrix between regimes and market metrics
        
        Returns:
            Correlation matrix dictionary
        """
        cache_key = "regime_correlations"
        
        if self._is_cache_valid(cache_key):
            return self.analytics_cache[cache_key]
        
        correlations = {}
        regimes = ['Goldilocks', 'Deflation', 'Inflation', 'Reflation']
        
        # Calculate regime-to-regime correlations based on transition patterns
        for regime1 in regimes:
            correlations[regime1] = {}
            for regime2 in regimes:
                if regime1 == regime2:
                    correlations[regime1][regime2] = 1.0
                else:
                    correlation = self._calculate_regime_correlation(regime1, regime2)
                    correlations[regime1][regime2] = correlation
        
        # Add performance correlations if available
        if self.performance_history:
            for regime in regimes:
                for metric in self.performance_history:
                    correlation = self._calculate_regime_performance_correlation(regime, metric)
                    correlations[regime][f"performance_{metric}"] = correlation
        
        self._cache_result(cache_key, correlations)
        return correlations
    
    def generate_comprehensive_report(self, report_period_days: int = 30) -> Dict[str, Any]:
        """
        Generate comprehensive regime analytics report
        
        Args:
            report_period_days: Period for report analysis
            
        Returns:
            Comprehensive analytics report
        """
        report = {
            'analysis_period_days': report_period_days,
            'report_generated': datetime.now().isoformat(),
            'data_summary': self._get_data_summary(),
            'regime_performance': self.analyze_regime_performance(analysis_period_days=report_period_days),
            'transition_analysis': self.analyze_transition_patterns(analysis_period_days=report_period_days),
            'detected_patterns': self.detect_regime_patterns(pattern_window_days=report_period_days),
            'correlation_matrix': self.get_regime_correlation_matrix(),
            'statistics': self.get_analytics_statistics()
        }
        
        # Add current regime analysis if available
        if self.regime_history:
            current_regime = self.regime_history[-1]
            report['current_regime_analysis'] = {
                'regime': current_regime.regime,
                'confidence': current_regime.confidence,
                'stability': current_regime.stability,
                'strength': current_regime.strength,
                'duration_days': current_regime.duration_days,
                'forecast': self.forecast_regime_probability(current_regime)
            }
        
        return report
    
    def _calculate_regime_performance_metrics(self, regime: str, 
                                            states: List[RegimeState]) -> RegimePerformanceMetrics:
        """Calculate performance metrics for a regime"""
        confidences = [s.confidence for s in states]
        stabilities = [s.stability for s in states]
        strengths = [s.strength for s in states]
        durations = [s.duration_days for s in states]
        
        # Calculate trends
        confidence_trend = self._calculate_trend(confidences)
        stability_trend = self._calculate_trend(stabilities)
        
        # Count transitions involving this regime
        transition_count = len([
            t for t in self.transition_history
            if t.from_regime == regime or t.to_regime == regime
        ])
        
        # Calculate performance score
        performance_score = (
            np.mean(confidences) * 0.4 +
            np.mean(stabilities) * 0.3 +
            np.mean(strengths) * 0.3
        )
        
        return RegimePerformanceMetrics(
            regime=regime,
            total_days=len(states),
            avg_confidence=np.mean(confidences),
            avg_stability=np.mean(stabilities),
            avg_strength=np.mean(strengths),
            transition_count=transition_count,
            avg_duration=np.mean(durations),
            confidence_trend=confidence_trend,
            stability_trend=stability_trend,
            performance_score=performance_score
        )
    
    def _analyze_transition_pattern(self, transition_pair: Tuple[str, str],
                                  transitions: List[RegimeTransition]) -> TransitionAnalysis:
        """Analyze pattern for specific transition pair"""
        momenta = [t.momentum for t in transitions]
        confidences = [t.confidence for t in transitions]
        severities = [t.severity_str for t in transitions]
        
        # Calculate success rate (transitions with high validation scores)
        successful_transitions = [
            t for t in transitions
            if t.validation_score > 0.7
        ]
        success_rate = len(successful_transitions) / len(transitions)
        
        # Get common triggers
        all_triggers = []
        for t in transitions:
            all_triggers.extend(t.trigger_indicators)
        
        trigger_counter = Counter(all_triggers)
        common_triggers = [trigger for trigger, count in trigger_counter.most_common(5)]
        
        # Calculate average duration from expected_duration
        durations = [t.expected_duration for t in transitions if t.expected_duration]
        avg_duration = int(np.mean(durations)) if durations else 30
        
        return TransitionAnalysis(
            transition_pair=transition_pair,
            frequency=len(transitions),
            avg_momentum=np.mean(momenta),
            avg_confidence=np.mean(confidences),
            success_rate=success_rate,
            avg_duration=avg_duration,
            severity_distribution=dict(Counter(severities)),
            common_triggers=common_triggers
        )
    
    def _detect_stability_cycles(self, window_days: int) -> Optional[Dict[str, Any]]:
        """Detect cyclical patterns in regime stability"""
        if len(self.regime_history) < window_days:
            return None
        
        recent_states = self.regime_history[-window_days:]
        stabilities = [s.stability for s in recent_states]
        
        # Simple cycle detection - look for oscillation patterns
        if len(stabilities) < 10:
            return None
        
        # Calculate moving average and deviations
        window_size = 5
        moving_avg = []
        for i in range(window_size, len(stabilities)):
            avg = np.mean(stabilities[i-window_size:i])
            moving_avg.append(avg)
        
        if not moving_avg:
            return None
        
        # Look for oscillation around the moving average
        above_avg = [s > np.mean(moving_avg) for s in stabilities[-len(moving_avg):]]
        
        # Count sign changes (peaks and troughs)
        sign_changes = 0
        for i in range(1, len(above_avg)):
            if above_avg[i] != above_avg[i-1]:
                sign_changes += 1
        
        # If we have multiple oscillations, it's a pattern
        if sign_changes >= 4:
            return {
                'pattern_type': 'stability_cycle',
                'cycle_count': sign_changes // 2,
                'avg_stability': np.mean(stabilities),
                'stability_variance': np.var(stabilities),
                'confidence': min(sign_changes / 8, 1.0)  # Normalize confidence
            }
        
        return None
    
    def _detect_confidence_momentum(self, window_days: int) -> Optional[Dict[str, Any]]:
        """Detect momentum patterns in regime confidence"""
        if len(self.regime_history) < window_days:
            return None
        
        recent_states = self.regime_history[-window_days:]
        confidences = [s.confidence for s in recent_states]
        
        if len(confidences) < 5:
            return None
        
        # Calculate momentum (rate of change)
        momentum_values = []
        for i in range(1, len(confidences)):
            momentum = confidences[i] - confidences[i-1]
            momentum_values.append(momentum)
        
        avg_momentum = np.mean(momentum_values)
        momentum_consistency = 1.0 - np.std(momentum_values)  # Lower std = more consistent
        
        # Detect significant momentum patterns
        if abs(avg_momentum) > 0.02 and momentum_consistency > 0.7:
            direction = 'increasing' if avg_momentum > 0 else 'decreasing'
            return {
                'pattern_type': 'confidence_momentum',
                'direction': direction,
                'avg_momentum': avg_momentum,
                'consistency': momentum_consistency,
                'confidence': min(abs(avg_momentum) * 20, 1.0)
            }
        
        return None
    
    def _detect_transition_clustering(self, window_days: int) -> Optional[Dict[str, Any]]:
        """Detect clustering patterns in regime transitions"""
        cutoff_date = datetime.now() - timedelta(days=window_days)
        recent_transitions = [
            t for t in self.transition_history
            if t.transition_date >= cutoff_date
        ]
        
        if len(recent_transitions) < 3:
            return None
        
        # Calculate time gaps between transitions
        transition_dates = sorted([t.transition_date for t in recent_transitions])
        gaps = []
        for i in range(1, len(transition_dates)):
            gap = (transition_dates[i] - transition_dates[i-1]).days
            gaps.append(gap)
        
        avg_gap = np.mean(gaps)
        gap_std = np.std(gaps)
        
        # Clustering detected if gaps are consistently small
        if avg_gap < 7 and gap_std < 3:  # Transitions within a week, low variance
            return {
                'pattern_type': 'transition_clustering',
                'cluster_size': len(recent_transitions),
                'avg_gap_days': avg_gap,
                'gap_consistency': 1.0 - (gap_std / max(avg_gap, 1)),
                'confidence': min(len(recent_transitions) / 5, 1.0)
            }
        
        return None
    
    def _detect_duration_patterns(self, window_days: int) -> Optional[Dict[str, Any]]:
        """Detect patterns in regime durations"""
        if len(self.regime_history) < 10:
            return None
        
        recent_states = self.regime_history[-window_days:]
        
        # Group by regime and calculate duration patterns
        regime_durations = defaultdict(list)
        for state in recent_states:
            regime_durations[state.regime].append(state.duration_days)
        
        # Look for consistent duration patterns
        pattern_regimes = []
        for regime, durations in regime_durations.items():
            if len(durations) >= 3:
                avg_duration = np.mean(durations)
                duration_std = np.std(durations)
                consistency = 1.0 - (duration_std / max(avg_duration, 1))
                
                if consistency > 0.7:  # High consistency
                    pattern_regimes.append({
                        'regime': regime,
                        'avg_duration': avg_duration,
                        'consistency': consistency
                    })
        
        if pattern_regimes:
            return {
                'pattern_type': 'duration_consistency',
                'regime_patterns': pattern_regimes,
                'confidence': np.mean([p['consistency'] for p in pattern_regimes])
            }
        
        return None
    
    def _calculate_base_transition_probabilities(self, current_regime: str) -> Dict[str, float]:
        """Calculate base transition probabilities from historical data"""
        transitions_from_regime = [
            t for t in self.transition_history
            if t.from_regime == current_regime
        ]
        
        if not transitions_from_regime:
            # Uniform distribution if no historical data
            regimes = ['Goldilocks', 'Deflation', 'Inflation', 'Reflation']
            return {regime: 0.25 for regime in regimes}
        
        # Count transitions to each regime
        transition_counts = Counter([t.to_regime for t in transitions_from_regime])
        total_transitions = len(transitions_from_regime)
        
        # Convert to probabilities
        probabilities = {}
        for regime in ['Goldilocks', 'Deflation', 'Inflation', 'Reflation']:
            count = transition_counts.get(regime, 0)
            probabilities[regime] = count / total_transitions
        
        # Add probability of staying in current regime
        probabilities[current_regime] += 0.6  # Base persistence probability
        
        return probabilities
    
    def _adjust_probabilities_for_state(self, base_probs: Dict[str, float],
                                      regime_state: RegimeState,
                                      forecast_days: int) -> Dict[str, float]:
        """Adjust probabilities based on current regime state"""
        adjusted = base_probs.copy()
        
        # High stability regimes are less likely to transition
        stability_factor = regime_state.stability
        current_regime = regime_state.regime
        
        # Reduce transition probabilities for stable regimes
        for regime in adjusted:
            if regime != current_regime:
                adjusted[regime] *= (1.0 - stability_factor * 0.5)
        
        # Increase persistence probability for stable regimes
        adjusted[current_regime] *= (1.0 + stability_factor * 0.3)
        
        # Adjust based on regime strength
        strength_factor = regime_state.strength
        if strength_factor > 0.7:
            # Strong regimes are more persistent
            adjusted[current_regime] *= 1.2
            for regime in adjusted:
                if regime != current_regime:
                    adjusted[regime] *= 0.8
        
        # Adjust based on forecast horizon
        horizon_factor = min(forecast_days / 30, 1.0)  # 30 days = full effect
        for regime in adjusted:
            if regime != current_regime:
                adjusted[regime] *= (1.0 + horizon_factor * 0.5)
        
        return adjusted
    
    def _apply_pattern_adjustments(self, probabilities: Dict[str, float],
                                 current_regime: RegimeState) -> Dict[str, float]:
        """Apply pattern-based adjustments to probabilities"""
        adjusted = probabilities.copy()
        
        # Apply detected pattern influences
        for pattern in self.detected_patterns[-5:]:  # Last 5 patterns
            pattern_type = pattern.get('pattern_type')
            confidence = pattern.get('confidence', 0.5)
            
            if pattern_type == 'transition_clustering' and confidence > 0.7:
                # High clustering suggests more transitions likely
                for regime in adjusted:
                    if regime != current_regime.regime:
                        adjusted[regime] *= 1.2
                adjusted[current_regime.regime] *= 0.8
            
            elif pattern_type == 'stability_cycle' and confidence > 0.7:
                # Stability cycles suggest alternating periods
                if current_regime.stability > 0.7:
                    # Currently stable, might destabilize
                    for regime in adjusted:
                        if regime != current_regime.regime:
                            adjusted[regime] *= 1.1
            
        return adjusted
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction for a series of values"""
        if len(values) < 3:
            return 'insufficient_data'
        
        # Simple linear trend
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)[0]
        
        if slope > 0.01:
            return 'increasing'
        elif slope < -0.01:
            return 'decreasing'
        else:
            return 'stable'
    
    def _calculate_regime_correlation(self, regime1: str, regime2: str) -> float:
        """Calculate correlation between two regimes based on transition patterns"""
        # Find transitions between these regimes
        transitions_1_to_2 = len([
            t for t in self.transition_history
            if t.from_regime == regime1 and t.to_regime == regime2
        ])
        
        transitions_2_to_1 = len([
            t for t in self.transition_history
            if t.from_regime == regime2 and t.to_regime == regime1
        ])
        
        total_transitions = len(self.transition_history)
        
        if total_transitions == 0:
            return 0.0
        
        # Calculate bidirectional transition frequency
        bidirectional_frequency = (transitions_1_to_2 + transitions_2_to_1) / total_transitions
        
        # Normalize to correlation-like scale
        correlation = min(bidirectional_frequency * 10, 1.0)  # Scale to 0-1
        
        return correlation
    
    def _calculate_regime_performance_correlation(self, regime: str, metric: str) -> float:
        """Calculate correlation between regime and performance metric"""
        if metric not in self.performance_history:
            return 0.0
        
        # Get regime indicators and performance values
        regime_indicators = []
        performance_values = []
        
        min_length = min(len(self.regime_history), len(self.performance_history[metric]))
        
        for i in range(min_length):
            regime_state = self.regime_history[-(i+1)]
            perf_value = self.performance_history[metric][-(i+1)]
            
            # Convert regime to numeric indicator
            regime_indicator = 1.0 if regime_state.regime == regime else 0.0
            regime_indicators.append(regime_indicator)
            performance_values.append(perf_value)
        
        if len(regime_indicators) < 3:
            return 0.0
        
        # Calculate correlation
        correlation = np.corrcoef(regime_indicators, performance_values)[0, 1]
        
        return correlation if not np.isnan(correlation) else 0.0
    
    def _get_data_summary(self) -> Dict[str, Any]:
        """Get summary of available data"""
        return {
            'regime_observations': len(self.regime_history),
            'transition_observations': len(self.transition_history),
            'performance_metrics': list(self.performance_history.keys()),
            'analysis_window_days': self.analysis_window_days,
            'oldest_observation': (
                self.regime_history[0].detection_date.isoformat()
                if self.regime_history else None
            ),
            'newest_observation': (
                self.regime_history[-1].detection_date.isoformat()
                if self.regime_history else None
            )
        }
    
    def get_analytics_statistics(self) -> Dict[str, Any]:
        """Get analytics engine statistics"""
        stats = self.analysis_stats.copy()
        
        # Add cache statistics
        stats['cache_size'] = len(self.analytics_cache)
        stats['cache_hit_rate'] = (
            stats['cache_hits'] / max(stats['total_analyses'], 1)
        )
        
        # Add data statistics
        stats['data_summary'] = self._get_data_summary()
        
        return stats
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is valid"""
        if cache_key not in self.analytics_cache:
            return False
        
        timestamp = self.cache_timestamps.get(cache_key)
        if not timestamp:
            return False
        
        age = datetime.now() - timestamp
        return age <= self.cache_duration
    
    def _cache_result(self, cache_key: str, result: Any):
        """Cache analysis result"""
        self.analytics_cache[cache_key] = result
        self.cache_timestamps[cache_key] = datetime.now()
        
        # Clean old cache entries
        self._clean_old_cache()
    
    def _clean_old_cache(self):
        """Remove old cache entries"""
        cutoff_time = datetime.now() - self.cache_duration * 2
        
        keys_to_remove = [
            key for key, timestamp in self.cache_timestamps.items()
            if timestamp < cutoff_time
        ]
        
        for key in keys_to_remove:
            self.analytics_cache.pop(key, None)
            self.cache_timestamps.pop(key, None)
    
    def _clear_analysis_cache(self):
        """Clear all analysis cache"""
        self.analytics_cache.clear()
        self.cache_timestamps.clear()
    
    def reset_analytics(self):
        """Reset all analytics data and cache"""
        self.regime_history.clear()
        self.transition_history.clear()
        self.performance_history.clear()
        self.detected_patterns.clear()
        self.regime_correlations.clear()
        self._clear_analysis_cache()
        
        self.analysis_stats = {
            'total_analyses': 0,
            'cache_hits': 0,
            'patterns_detected': 0,
            'forecasts_generated': 0
        } 