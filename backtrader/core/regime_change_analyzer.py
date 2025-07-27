"""
Module 6: Regime Context Provider - Regime Change Analyzer

This module implements sophisticated regime transition detection with severity assessment,
validation logic, and momentum analysis for authoritative regime change identification.
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

from .regime_models import (
    RegimeState, RegimeTransition, TransitionSeverity, RegimeChangeEvent
)


class RegimeChangeAnalyzer:
    """
    Sophisticated regime change analyzer with validation and severity assessment
    """
    
    def __init__(self, sensitivity_threshold=0.3, validation_period_days=2,
                 momentum_threshold=0.4):
        """
        Initialize regime change analyzer
        
        Args:
            sensitivity_threshold: Minimum confidence change to consider transition
            validation_period_days: Days to validate transition persistence  
            momentum_threshold: Minimum momentum to confirm transition
        """
        self.sensitivity_threshold = sensitivity_threshold
        self.validation_period_days = validation_period_days
        self.momentum_threshold = momentum_threshold
        
        # Transition tracking
        self.pending_transitions: List[RegimeTransition] = []
        self.confirmed_transitions: List[RegimeTransition] = []
        self.transition_history: Dict[str, List[RegimeTransition]] = defaultdict(list)
        
        # Critical transition pairs (highest severity)
        self.critical_transitions = {
            ('Goldilocks', 'Deflation'),    # Growth to recession
            ('Goldilocks', 'Inflation'),    # Low inflation to high inflation
            ('Deflation', 'Inflation'),     # Deflationary to inflationary
            ('Inflation', 'Deflation'),     # Inflationary to deflationary
            ('Reflation', 'Deflation')      # Recovery to recession
        }
        
        # High-impact transition pairs
        self.high_impact_transitions = {
            ('Goldilocks', 'Reflation'),    # Stable growth to policy-driven growth
            ('Reflation', 'Inflation'),     # Policy support to inflation pressure
            ('Deflation', 'Reflation'),     # Recession to recovery
            ('Inflation', 'Goldilocks')     # High inflation to stability
        }
        
        # Validation metrics
        self.validation_stats = {
            'total_analyzed': 0,
            'transitions_detected': 0,
            'transitions_confirmed': 0,
            'false_positives_filtered': 0
        }
    
    def analyze_potential_transition(self, previous_regime: RegimeState,
                                   current_regime: RegimeState,
                                   current_date: datetime) -> Optional[RegimeTransition]:
        """
        Analyze if a genuine regime transition has occurred
        
        Args:
            previous_regime: Previous regime state
            current_regime: Current regime state  
            current_date: Current analysis date
            
        Returns:
            RegimeTransition if valid transition detected, None otherwise
        """
        self.validation_stats['total_analyzed'] += 1
        
        # Check for regime change
        if previous_regime.regime == current_regime.regime:
            return None  # No regime change
        
        # Calculate transition characteristics
        confidence_change = current_regime.confidence - previous_regime.confidence
        stability_drop = previous_regime.stability - current_regime.stability
        
        # Assess transition validity
        is_valid_transition = self._validate_transition(
            previous_regime, current_regime, confidence_change
        )
        
        if not is_valid_transition:
            self.validation_stats['false_positives_filtered'] += 1
            return None
        
        # Calculate transition momentum
        momentum = self._calculate_transition_momentum(
            previous_regime, current_regime
        )
        
        # Validate momentum threshold
        if momentum < self.momentum_threshold:
            print(f"⚠️ Transition {previous_regime.regime} → {current_regime.regime} "
                  f"filtered: momentum {momentum:.3f} < {self.momentum_threshold}")
            self.validation_stats['false_positives_filtered'] += 1
            return None
        
        # Calculate transition severity
        severity = self._assess_transition_severity(
            previous_regime.regime, current_regime.regime,
            confidence_change, stability_drop, momentum
        )
        
        # Identify transition triggers
        triggers = self._identify_transition_triggers(
            previous_regime, current_regime
        )
        
        # Estimate regime duration
        expected_duration = self._estimate_regime_duration(
            current_regime.regime, severity, momentum
        )
        
        # Create transition event
        transition = RegimeTransition(
            from_regime=previous_regime.regime,
            to_regime=current_regime.regime,
            transition_date=current_date,
            severity=severity,
            confidence=current_regime.confidence,
            momentum=momentum,
            trigger_indicators=triggers,
            expected_duration=expected_duration,
            validation_score=self._calculate_validation_score(
                previous_regime, current_regime, momentum
            )
        )
        
        self.validation_stats['transitions_detected'] += 1
        
        # Add to tracking
        self._track_transition(transition)
        
        return transition
    
    def _validate_transition(self, previous_regime: RegimeState, 
                           current_regime: RegimeState,
                           confidence_change: float) -> bool:
        """
        Validate if regime transition is genuine vs noise
        
        Args:
            previous_regime: Previous regime state
            current_regime: Current regime state
            confidence_change: Change in confidence level
            
        Returns:
            True if transition is valid, False if likely noise
        """
        # Minimum confidence requirements
        if current_regime.confidence < 0.5:
            return False  # New regime not confident enough
        
        # Minimum confidence change requirement
        if abs(confidence_change) < self.sensitivity_threshold:
            return False  # Insufficient confidence change
        
        # Stability considerations
        if previous_regime.stability > 0.8 and current_regime.confidence < 0.7:
            return False  # Very stable regime shouldn't change to low-confidence regime
        
        # Duration considerations (very short regimes are suspicious)
        if previous_regime.duration_days < 2:
            return False  # Previous regime too short to be genuine
        
        # Timeframe consensus check
        tf_consensus = self._check_timeframe_consensus(current_regime)
        if not tf_consensus:
            return False  # Timeframes don't agree on new regime
        
        return True
    
    def _check_timeframe_consensus(self, regime_state: RegimeState) -> bool:
        """
        Check if timeframes agree on the regime change
        
        Args:
            regime_state: Current regime state with timeframe analysis
            
        Returns:
            True if timeframes show consensus, False otherwise
        """
        timeframe_confidences = list(regime_state.timeframe_analysis.values())
        
        if len(timeframe_confidences) < 2:
            return True  # Can't check consensus with less than 2 timeframes
        
        # Check if majority of timeframes are confident
        confident_timeframes = sum(1 for conf in timeframe_confidences if conf > 0.6)
        consensus_threshold = len(timeframe_confidences) * 0.6  # 60% consensus required
        
        return confident_timeframes >= consensus_threshold
    
    def _assess_transition_severity(self, from_regime: str, to_regime: str,
                                  confidence_change: float, stability_drop: float,
                                  momentum: float) -> TransitionSeverity:
        """
        Assess severity of regime transition
        
        Args:
            from_regime: Source regime
            to_regime: Target regime
            confidence_change: Change in confidence
            stability_drop: Drop in stability
            momentum: Transition momentum
            
        Returns:
            TransitionSeverity level
        """
        transition_pair = (from_regime, to_regime)
        
        # Base severity from transition type
        if transition_pair in self.critical_transitions:
            base_severity = TransitionSeverity.CRITICAL
        elif transition_pair in self.high_impact_transitions:
            base_severity = TransitionSeverity.HIGH
        else:
            base_severity = TransitionSeverity.NORMAL
        
        # Severity amplifiers
        severity_score = 0
        
        # Large confidence changes indicate strong transitions
        if confidence_change > 0.6:
            severity_score += 2
        elif confidence_change > 0.4:
            severity_score += 1
        
        # Large stability drops indicate sudden transitions
        if stability_drop > 0.5:
            severity_score += 2
        elif stability_drop > 0.3:
            severity_score += 1
        
        # High momentum indicates forceful transitions
        if momentum > 0.8:
            severity_score += 2
        elif momentum > 0.6:
            severity_score += 1
        
        # Adjust severity based on score
        if base_severity == TransitionSeverity.NORMAL and severity_score >= 3:
            return TransitionSeverity.HIGH
        elif base_severity == TransitionSeverity.HIGH and severity_score >= 4:
            return TransitionSeverity.CRITICAL
        elif base_severity == TransitionSeverity.CRITICAL and severity_score < 2:
            return TransitionSeverity.HIGH  # Downgrade if weak signals
        
        return base_severity
    
    def _calculate_transition_momentum(self, previous_regime: RegimeState,
                                     current_regime: RegimeState) -> float:
        """
        Calculate speed and strength of regime transition
        
        Args:
            previous_regime: Previous regime state
            current_regime: Current regime state
            
        Returns:
            Momentum score (0.0-1.0)
        """
        # Core momentum factors
        confidence_jump = max(0, current_regime.confidence - previous_regime.confidence)
        strength_increase = max(0, current_regime.strength - previous_regime.strength)
        stability_context = 1.0 - previous_regime.stability  # Less stable = higher momentum potential
        
        # Timeframe momentum (how much timeframes shifted)
        timeframe_momentum = self._calculate_timeframe_momentum(
            previous_regime.timeframe_analysis,
            current_regime.timeframe_analysis
        )
        
        # Regime duration factor (longer previous regime = more significant change)
        duration_factor = min(previous_regime.duration_days / 30, 1.0)
        
        # Combine factors with weights
        momentum = (
            confidence_jump * 0.3 +
            strength_increase * 0.25 +
            stability_context * 0.2 +
            timeframe_momentum * 0.15 +
            duration_factor * 0.1
        )
        
        return max(0.0, min(1.0, momentum))
    
    def _calculate_timeframe_momentum(self, prev_tf_analysis: Dict[str, float],
                                    curr_tf_analysis: Dict[str, float]) -> float:
        """
        Calculate momentum from timeframe analysis changes
        
        Args:
            prev_tf_analysis: Previous timeframe analysis
            curr_tf_analysis: Current timeframe analysis
            
        Returns:
            Timeframe momentum (0.0-1.0)
        """
        if not prev_tf_analysis or not curr_tf_analysis:
            return 0.5  # Neutral momentum if missing data
        
        total_change = 0.0
        timeframe_count = 0
        
        for timeframe in curr_tf_analysis:
            if timeframe in prev_tf_analysis:
                change = abs(curr_tf_analysis[timeframe] - prev_tf_analysis[timeframe])
                total_change += change
                timeframe_count += 1
        
        if timeframe_count == 0:
            return 0.5
        
        # Average change across timeframes
        avg_change = total_change / timeframe_count
        
        # Normalize to 0-1 range (assuming max reasonable change is 0.8)
        momentum = min(avg_change / 0.8, 1.0)
        
        return momentum
    
    def _identify_transition_triggers(self, previous_regime: RegimeState,
                                    current_regime: RegimeState) -> List[str]:
        """
        Identify what triggered the regime transition
        
        Args:
            previous_regime: Previous regime state
            current_regime: Current regime state
            
        Returns:
            List of trigger indicators
        """
        triggers = []
        
        # Analyze timeframe-specific triggers
        for timeframe, confidence in current_regime.timeframe_analysis.items():
            prev_confidence = previous_regime.timeframe_analysis.get(timeframe, 0.5)
            if confidence - prev_confidence > 0.3:
                triggers.append(f"{timeframe}_momentum")
            elif confidence - prev_confidence < -0.3:
                triggers.append(f"{timeframe}_reversal")
        
        # Regime-specific triggers
        if current_regime.regime == 'Deflation':
            triggers.extend(['deflationary_pressure', 'safe_haven_demand', 'growth_weakness'])
        elif current_regime.regime == 'Inflation':
            triggers.extend(['inflationary_pressure', 'commodity_surge', 'rate_pressure'])
        elif current_regime.regime == 'Goldilocks':
            triggers.extend(['growth_stabilization', 'volatility_decline', 'policy_normalization'])
        elif current_regime.regime == 'Reflation':
            triggers.extend(['policy_stimulus', 'growth_recovery', 'risk_appetite_return'])
        
        # Confidence and stability triggers
        confidence_change = current_regime.confidence - previous_regime.confidence
        if confidence_change > 0.4:
            triggers.append('high_confidence_shift')
        elif confidence_change < -0.4:
            triggers.append('confidence_collapse')
        
        stability_change = current_regime.stability - previous_regime.stability
        if stability_change < -0.4:
            triggers.append('stability_breakdown')
        
        # Strength triggers
        strength_change = current_regime.strength - previous_regime.strength
        if strength_change > 0.3:
            triggers.append('regime_strength_buildup')
        elif strength_change < -0.3:
            triggers.append('regime_weakness')
        
        return list(set(triggers))  # Remove duplicates
    
    def _estimate_regime_duration(self, regime: str, severity: TransitionSeverity,
                                momentum: float) -> int:
        """
        Estimate expected duration of new regime
        
        Args:
            regime: New regime name
            severity: Transition severity
            momentum: Transition momentum
            
        Returns:
            Expected duration in days
        """
        # Base durations by regime (historical averages)
        base_durations = {
            'Goldilocks': 60,   # Typically stable periods
            'Deflation': 45,    # Can be persistent but volatile
            'Inflation': 35,    # Usually shorter-lived
            'Reflation': 25     # Often transitional
        }
        
        base_duration = base_durations.get(regime, 40)
        
        # Adjust based on transition characteristics
        if severity == TransitionSeverity.CRITICAL:
            duration_multiplier = 1.3  # Critical transitions tend to last longer
        elif severity == TransitionSeverity.HIGH:
            duration_multiplier = 1.1
        else:
            duration_multiplier = 0.9  # Normal transitions might be shorter
        
        # High momentum transitions might be more durable
        momentum_adjustment = 1.0 + (momentum - 0.5) * 0.4
        
        estimated_duration = int(base_duration * duration_multiplier * momentum_adjustment)
        
        return max(10, min(estimated_duration, 120))  # Clamp between 10-120 days
    
    def _calculate_validation_score(self, previous_regime: RegimeState,
                                  current_regime: RegimeState, momentum: float) -> float:
        """
        Calculate internal validation score for transition quality
        
        Args:
            previous_regime: Previous regime state
            current_regime: Current regime state
            momentum: Transition momentum
            
        Returns:
            Validation score (0.0-1.0)
        """
        score = 0.0
        
        # Confidence factors (40% weight)
        if current_regime.confidence > 0.7:
            score += 0.4 * (current_regime.confidence - 0.5) / 0.5
        
        # Momentum factors (30% weight)
        score += 0.3 * momentum
        
        # Timeframe consensus (20% weight)
        tf_confidences = list(current_regime.timeframe_analysis.values())
        if tf_confidences:
            avg_tf_confidence = sum(tf_confidences) / len(tf_confidences)
            score += 0.2 * avg_tf_confidence
        
        # Duration validity (10% weight)
        if previous_regime.duration_days >= 3:
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def _track_transition(self, transition: RegimeTransition):
        """
        Track transition in history and statistics
        
        Args:
            transition: Regime transition to track
        """
        # Add to transition history
        key = f"{transition.from_regime}_{transition.to_regime}"
        self.transition_history[key].append(transition)
        
        # Track in pending transitions for validation
        self.pending_transitions.append(transition)
        
        # Log transition detection
        print(f"🔄 Regime transition detected: {transition.from_regime} → {transition.to_regime}")
        print(f"   📊 Severity: {transition.severity_str}")
        print(f"   📊 Confidence: {transition.confidence:.3f}")
        print(f"   📊 Momentum: {transition.momentum:.3f}")
        print(f"   📊 Triggers: {', '.join(transition.trigger_indicators[:3])}")
    
    def validate_pending_transitions(self, current_date: datetime) -> List[RegimeTransition]:
        """
        Validate pending transitions that have been observed long enough
        
        Args:
            current_date: Current date for validation
            
        Returns:
            List of confirmed transitions
        """
        confirmed = []
        still_pending = []
        
        for transition in self.pending_transitions:
            days_since = (current_date - transition.transition_date).days
            
            if days_since >= self.validation_period_days:
                # Consider transition confirmed
                confirmed.append(transition)
                self.confirmed_transitions.append(transition)
                self.validation_stats['transitions_confirmed'] += 1
                
                print(f"✅ Transition confirmed: {transition.from_regime} → {transition.to_regime} "
                      f"(after {days_since} days)")
            else:
                still_pending.append(transition)
        
        # Update pending list
        self.pending_transitions = still_pending
        
        return confirmed
    
    def get_transition_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive transition analysis statistics
        
        Returns:
            Dictionary with transition statistics
        """
        stats = self.validation_stats.copy()
        
        # Calculate success rates
        if stats['transitions_detected'] > 0:
            stats['confirmation_rate'] = stats['transitions_confirmed'] / stats['transitions_detected']
            stats['false_positive_rate'] = stats['false_positives_filtered'] / stats['total_analyzed']
        
        # Transition frequency by type
        transition_frequencies = {}
        for key, transitions in self.transition_history.items():
            transition_frequencies[key] = len(transitions)
        
        stats['transition_frequencies'] = transition_frequencies
        
        # Severity distribution
        severity_counts = defaultdict(int)
        for transitions in self.transition_history.values():
            for transition in transitions:
                severity_counts[transition.severity_str] += 1
        
        stats['severity_distribution'] = dict(severity_counts)
        
        # Recent activity
        stats['pending_transitions'] = len(self.pending_transitions)
        stats['total_confirmed'] = len(self.confirmed_transitions)
        
        return stats
    
    def get_recent_transitions(self, days: int = 30) -> List[RegimeTransition]:
        """
        Get recent confirmed transitions
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of recent transitions
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        recent = [
            t for t in self.confirmed_transitions
            if t.transition_date >= cutoff_date
        ]
        
        return sorted(recent, key=lambda x: x.transition_date, reverse=True)
    
    def reset_statistics(self):
        """Reset all statistics and tracking"""
        self.pending_transitions.clear()
        self.confirmed_transitions.clear()
        self.transition_history.clear()
        self.validation_stats = {
            'total_analyzed': 0,
            'transitions_detected': 0,
            'transitions_confirmed': 0,
            'false_positives_filtered': 0
        } 