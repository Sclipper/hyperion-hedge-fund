"""
Module 6: Regime Context Provider - Core Data Models

This module defines the enhanced data models for sophisticated regime detection,
transition analysis, and context provision across the trading framework.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum


class TransitionSeverity(Enum):
    """Severity levels for regime transitions"""
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RegimeState:
    """Enhanced regime state with confidence and stability metrics"""
    regime: str                           # 'Goldilocks', 'Deflation', 'Inflation', 'Reflation'
    confidence: float                     # 0.0-1.0 confidence in regime classification
    stability: float                      # 0.0-1.0 likelihood regime will persist
    strength: float                       # 0.0-1.0 strength of regime characteristics
    timeframe_analysis: Dict[str, float]  # Per-timeframe confidence levels
    detection_date: datetime              # When regime was first detected
    duration_days: int                    # Days since regime started
    
    def __post_init__(self):
        """Validate field values"""
        self.confidence = max(0.0, min(1.0, self.confidence))
        self.stability = max(0.0, min(1.0, self.stability))
        self.strength = max(0.0, min(1.0, self.strength))
        self.duration_days = max(0, self.duration_days)
    
    def is_stable(self, threshold: float = 0.7) -> bool:
        """Check if regime is considered stable"""
        return self.stability >= threshold
    
    def is_confident(self, threshold: float = 0.8) -> bool:
        """Check if regime detection is confident"""
        return self.confidence >= threshold
    
    def is_strong(self, threshold: float = 0.6) -> bool:
        """Check if regime characteristics are strong"""
        return self.strength >= threshold


@dataclass
class RegimeTransition:
    """Regime transition event with severity assessment"""
    from_regime: str
    to_regime: str
    transition_date: datetime
    severity: TransitionSeverity          # Severity level
    confidence: float                     # Confidence in the transition
    momentum: float                       # Speed/strength of transition
    trigger_indicators: List[str]         # What triggered the transition
    expected_duration: Optional[int] = None  # Predicted regime duration in days
    validation_score: float = 0.0        # Internal validation score
    
    def __post_init__(self):
        """Validate field values"""
        self.confidence = max(0.0, min(1.0, self.confidence))
        self.momentum = max(0.0, min(1.0, self.momentum))
        self.validation_score = max(0.0, min(1.0, self.validation_score))
        
        # Convert string severity to enum if needed
        if isinstance(self.severity, str):
            self.severity = TransitionSeverity(self.severity.lower())
    
    @property
    def severity_str(self) -> str:
        """Get severity as string"""
        return self.severity.value
    
    def is_critical(self) -> bool:
        """Check if transition is critical"""
        return self.severity == TransitionSeverity.CRITICAL
    
    def is_high_impact(self) -> bool:
        """Check if transition is high impact or critical"""
        return self.severity in [TransitionSeverity.HIGH, TransitionSeverity.CRITICAL]
    
    def can_override_protection(self, protection_type: str) -> bool:
        """Check if this transition can override specific protection types"""
        override_rules = {
            TransitionSeverity.CRITICAL: [
                'grace_period', 'holding_period', 'whipsaw_protection', 'position_limits'
            ],
            TransitionSeverity.HIGH: [
                'grace_period', 'holding_period', 'position_limits'
            ],
            TransitionSeverity.NORMAL: []
        }
        
        return protection_type in override_rules.get(self.severity, [])


@dataclass
class RegimeConfidence:
    """Detailed confidence metrics for regime detection"""
    overall: float                        # Overall confidence (0.0-1.0)
    timeframe_breakdown: Dict[str, float] # Per-timeframe confidence
    indicator_confidence: Dict[str, float] # Per-indicator confidence
    historical_consistency: float        # Consistency with recent history
    market_data_quality: float          # Quality of underlying market data
    
    def __post_init__(self):
        """Validate and normalize confidence values"""
        self.overall = max(0.0, min(1.0, self.overall))
        self.historical_consistency = max(0.0, min(1.0, self.historical_consistency))
        self.market_data_quality = max(0.0, min(1.0, self.market_data_quality))
        
        # Normalize timeframe and indicator confidence
        for key in self.timeframe_breakdown:
            self.timeframe_breakdown[key] = max(0.0, min(1.0, self.timeframe_breakdown[key]))
        
        for key in self.indicator_confidence:
            self.indicator_confidence[key] = max(0.0, min(1.0, self.indicator_confidence[key]))


@dataclass
class RegimeStability:
    """Detailed stability metrics for regime persistence"""
    overall: float                        # Overall stability (0.0-1.0)
    consistency_score: float             # Recent regime consistency
    duration_factor: float               # Regime duration contribution
    strength_factor: float               # Regime strength contribution
    transition_risk: float               # Risk of near-term transition
    
    def __post_init__(self):
        """Validate stability values"""
        self.overall = max(0.0, min(1.0, self.overall))
        self.consistency_score = max(0.0, min(1.0, self.consistency_score))
        self.duration_factor = max(0.0, min(1.0, self.duration_factor))
        self.strength_factor = max(0.0, min(1.0, self.strength_factor))
        self.transition_risk = max(0.0, min(1.0, self.transition_risk))


@dataclass
class RegimeStrength:
    """Detailed strength metrics for regime characteristics"""
    overall: float                        # Overall regime strength (0.0-1.0)
    regime_specific_indicators: Dict[str, float]  # Regime-specific indicator strength
    market_alignment: float              # How well market aligns with regime
    volatility_consistency: float        # Volatility consistent with regime
    trend_strength: float                # Strength of trending behavior
    
    def __post_init__(self):
        """Validate strength values"""
        self.overall = max(0.0, min(1.0, self.overall))
        self.market_alignment = max(0.0, min(1.0, self.market_alignment))
        self.volatility_consistency = max(0.0, min(1.0, self.volatility_consistency))
        self.trend_strength = max(0.0, min(1.0, self.trend_strength))
        
        # Normalize regime-specific indicators
        for key in self.regime_specific_indicators:
            self.regime_specific_indicators[key] = max(0.0, min(1.0, self.regime_specific_indicators[key]))


@dataclass
class RegimeChangeEvent:
    """Comprehensive regime change event record"""
    transition: RegimeTransition
    detection_timestamp: datetime
    validation_period_end: Optional[datetime] = None
    confirmed: bool = False
    override_decisions: Dict[str, bool] = field(default_factory=dict)
    impact_metrics: Dict[str, float] = field(default_factory=dict)
    
    def is_validated(self) -> bool:
        """Check if transition has been validated"""
        return self.confirmed and self.validation_period_end is not None
    
    def can_authorize_override(self, protection_type: str) -> bool:
        """Check if this event can authorize protection overrides"""
        return (self.is_validated() and 
                self.transition.can_override_protection(protection_type))


@dataclass
class RegimeContext:
    """Comprehensive regime context for module consumption"""
    current_regime: RegimeState
    recent_transition: Optional[RegimeTransition]
    historical_context: Dict[str, Any]
    override_permissions: Dict[str, bool]
    parameter_adjustments: Dict[str, Any]
    module_specific_context: Dict[str, Any]
    context_timestamp: datetime = field(default_factory=datetime.now)
    
    def has_recent_transition(self, days_threshold: int = 7) -> bool:
        """Check if there's been a recent transition"""
        if not self.recent_transition:
            return False
        
        days_since = (self.context_timestamp - self.recent_transition.transition_date).days
        return days_since <= days_threshold
    
    def can_override(self, protection_type: str) -> bool:
        """Check if protection can be overridden"""
        return self.override_permissions.get(protection_type, False)
    
    def get_module_context(self, module_name: str) -> Dict[str, Any]:
        """Get context for specific module"""
        return self.module_specific_context.get(module_name, {})


@dataclass
class RegimeAnalytics:
    """Analytics data for regime performance and behavior"""
    regime_durations: Dict[str, List[int]]  # Historical durations by regime
    transition_frequencies: Dict[tuple, int]  # Transition pair frequencies
    average_confidences: Dict[str, float]   # Average confidence by regime
    stability_trends: Dict[str, List[float]]  # Stability trends by regime
    performance_correlations: Dict[str, Dict[str, float]]  # Performance by regime
    
    def get_average_duration(self, regime: str) -> float:
        """Get average duration for a regime"""
        durations = self.regime_durations.get(regime, [])
        return sum(durations) / len(durations) if durations else 0.0
    
    def get_transition_probability(self, from_regime: str, to_regime: str) -> float:
        """Get probability of specific transition"""
        transition_key = (from_regime, to_regime)
        total_transitions = sum(self.transition_frequencies.values())
        
        if total_transitions == 0:
            return 0.0
        
        return self.transition_frequencies.get(transition_key, 0) / total_transitions
    
    def get_regime_stability_trend(self, regime: str) -> str:
        """Get stability trend direction for a regime"""
        trends = self.stability_trends.get(regime, [])
        
        if len(trends) < 2:
            return "insufficient_data"
        
        recent_avg = sum(trends[-5:]) / min(5, len(trends))
        historical_avg = sum(trends[:-5]) / max(1, len(trends) - 5)
        
        if recent_avg > historical_avg * 1.1:
            return "improving"
        elif recent_avg < historical_avg * 0.9:
            return "declining"
        else:
            return "stable"


# Type aliases for convenience
RegimeTimeframeAnalysis = Dict[str, float]
RegimeIndicatorStrength = Dict[str, float]
RegimeBucketPreferences = Dict[str, float]
RegimeParameterAdjustments = Dict[str, Any] 