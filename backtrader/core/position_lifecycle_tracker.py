"""
Position Lifecycle Tracker for comprehensive position state management.

This module implements professional-grade position lifecycle tracking that maintains
complete audit trails, health assessments, and recommendations for all positions
throughout their lifecycle from entry to closure.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
from enum import Enum


class LifecycleStage(Enum):
    """Position lifecycle stages"""
    ACTIVE = "active"
    GRACE = "grace"
    WARNING = "warning"
    FORCED_REVIEW = "forced_review"
    CLOSING = "closing"


class HealthStatus(Enum):
    """Position health status"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class PositionState:
    """Current state of a position in the lifecycle"""
    asset: str
    current_stage: str  # LifecycleStage value
    entry_date: datetime
    current_size: float
    current_score: float
    days_held: int
    grace_days_remaining: int
    can_adjust: bool
    last_adjustment: Optional[datetime]
    bucket: str
    lifecycle_events_count: int
    health_status: str = "healthy"
    
    # Additional tracking fields
    original_entry_size: float = 0.0
    peak_size: float = 0.0
    total_size_changes: float = 0.0
    score_trend: str = "stable"  # "improving", "declining", "stable"
    consecutive_low_scores: int = 0


@dataclass
class LifecycleEvent:
    """Record of a position lifecycle event"""
    date: datetime
    event_type: str  # 'entry', 'adjustment', 'grace_start', 'grace_decay', 'closure', 'regime_override'
    previous_size: float
    new_size: float
    previous_score: float
    new_score: float
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Additional event details
    stage_change: Optional[str] = None
    health_change: Optional[str] = None
    triggered_by: str = "system"  # "system", "regime", "grace", "forced"


@dataclass
class PositionSummary:
    """Comprehensive position summary with lifecycle information"""
    asset: str
    state: PositionState
    recent_events: List[LifecycleEvent]
    health_status: str
    recommendations: List[str]
    
    # Performance metrics
    total_return: Optional[float] = None
    days_in_current_stage: int = 0
    avg_score: float = 0.0
    score_volatility: float = 0.0
    
    # Risk indicators
    risk_flags: List[str] = field(default_factory=list)
    priority_level: str = "normal"  # "low", "normal", "high", "critical"


class PositionLifecycleTracker:
    """
    Comprehensive position lifecycle and state management.
    
    Provides complete position tracking throughout lifecycle:
    - Position state management with stage transitions
    - Comprehensive event recording and history
    - Health status assessment and recommendations
    - Portfolio-wide lifecycle reporting and analytics
    - Risk flag identification and alerting
    
    Key Features:
    - Four-stage lifecycle (Active → Grace → Warning → Forced Review)
    - Health status classification (Healthy / Warning / Critical)
    - Complete event audit trail with metadata
    - Intelligent recommendation engine
    - Performance and risk analytics
    - Portfolio-wide health dashboard
    """
    
    def __init__(self):
        """Initialize position lifecycle tracker."""
        self.position_states: Dict[str, PositionState] = {}
        self.lifecycle_history: Dict[str, List[LifecycleEvent]] = defaultdict(list)
        
        # Configuration
        self.max_history_events = 100  # Limit history size per position
        self.score_trend_window = 5   # Days to analyze for score trend
        self.low_score_threshold = 0.6  # Score below which is considered "low"
    
    def track_position_entry(self, 
                           asset: str, 
                           entry_date: datetime, 
                           entry_size: float, 
                           entry_score: float, 
                           entry_reason: str, 
                           bucket: str):
        """
        Track new position entry with complete metadata.
        
        Args:
            asset: Asset symbol
            entry_date: Date position was entered
            entry_size: Initial position size
            entry_score: Initial position score
            entry_reason: Reason for position entry
            bucket: Asset bucket classification
        """
        # Create position state
        position_state = PositionState(
            asset=asset,
            current_stage=LifecycleStage.ACTIVE.value,
            entry_date=entry_date,
            current_size=entry_size,
            current_score=entry_score,
            days_held=0,
            grace_days_remaining=0,
            can_adjust=True,
            last_adjustment=None,
            bucket=bucket,
            lifecycle_events_count=0,
            health_status=HealthStatus.HEALTHY.value,
            original_entry_size=entry_size,
            peak_size=entry_size,
            total_size_changes=0.0,
            score_trend="stable",
            consecutive_low_scores=0 if entry_score >= self.low_score_threshold else 1
        )
        
        self.position_states[asset] = position_state
        
        # Record entry event
        entry_event = LifecycleEvent(
            date=entry_date,
            event_type='entry',
            previous_size=0.0,
            new_size=entry_size,
            previous_score=0.0,
            new_score=entry_score,
            reason=entry_reason,
            metadata={
                'bucket': bucket,
                'initial_stage': LifecycleStage.ACTIVE.value,
                'initial_health': HealthStatus.HEALTHY.value
            },
            stage_change=f"NEW → {LifecycleStage.ACTIVE.value}",
            health_change=f"NEW → {HealthStatus.HEALTHY.value}",
            triggered_by="system"
        )
        
        self.lifecycle_history[asset].append(entry_event)
        position_state.lifecycle_events_count = 1
        
        print(f"🎬 Position lifecycle started: {asset} in {bucket} "
              f"(size: {entry_size:.3f}, score: {entry_score:.3f}, reason: {entry_reason})")
    
    def update_position_state(self, 
                            asset: str, 
                            current_date: datetime,
                            new_score: float, 
                            new_size: float, 
                            action_taken: str, 
                            reason: str,
                            **kwargs):
        """
        Update position state and record lifecycle event.
        
        Args:
            asset: Asset symbol
            current_date: Current date
            new_score: Updated position score
            new_size: Updated position size
            action_taken: Action that was taken
            reason: Reason for the action
            **kwargs: Additional metadata
        """
        if asset not in self.position_states:
            print(f"⚠️ Cannot update unknown position: {asset}")
            return
        
        position_state = self.position_states[asset]
        
        # Store previous values
        previous_size = position_state.current_size
        previous_score = position_state.current_score
        previous_stage = position_state.current_stage
        previous_health = position_state.health_status
        
        # Update basic state
        position_state.current_size = new_size
        position_state.current_score = new_score
        position_state.days_held = (current_date - position_state.entry_date).days
        position_state.last_adjustment = current_date
        
        # Update derived metrics
        self._update_derived_metrics(position_state, previous_size, new_size, new_score)
        
        # Determine new stage and health
        new_stage = self._determine_lifecycle_stage(position_state, action_taken, kwargs)
        new_health = self._assess_health_status(position_state)
        
        # Update stage and health
        position_state.current_stage = new_stage
        position_state.health_status = new_health
        
        # Record lifecycle event
        event = LifecycleEvent(
            date=current_date,
            event_type=action_taken,
            previous_size=previous_size,
            new_size=new_size,
            previous_score=previous_score,
            new_score=new_score,
            reason=reason,
            metadata=kwargs,
            stage_change=f"{previous_stage} → {new_stage}" if previous_stage != new_stage else None,
            health_change=f"{previous_health} → {new_health}" if previous_health != new_health else None,
            triggered_by=kwargs.get('triggered_by', 'system')
        )
        
        self.lifecycle_history[asset].append(event)
        position_state.lifecycle_events_count += 1
        
        # Limit history size
        if len(self.lifecycle_history[asset]) > self.max_history_events:
            self.lifecycle_history[asset] = self.lifecycle_history[asset][-self.max_history_events:]
        
        print(f"📊 Position updated: {asset} - {action_taken} "
              f"(size: {previous_size:.3f}→{new_size:.3f}, "
              f"score: {previous_score:.3f}→{new_score:.3f}, "
              f"stage: {previous_stage}→{new_stage})")
    
    def _update_derived_metrics(self, 
                              position_state: PositionState, 
                              previous_size: float, 
                              new_size: float, 
                              new_score: float):
        """Update derived metrics based on new values."""
        # Update peak size
        if new_size > position_state.peak_size:
            position_state.peak_size = new_size
        
        # Update total size changes
        size_change = abs(new_size - previous_size)
        position_state.total_size_changes += size_change
        
        # Update consecutive low scores
        if new_score < self.low_score_threshold:
            position_state.consecutive_low_scores += 1
        else:
            position_state.consecutive_low_scores = 0
        
        # Update score trend (simplified)
        recent_events = self.lifecycle_history[position_state.asset][-self.score_trend_window:]
        if len(recent_events) >= 2:
            recent_scores = [event.new_score for event in recent_events]
            if len(recent_scores) >= 2:
                trend_slope = recent_scores[-1] - recent_scores[0]
                if trend_slope > 0.05:
                    position_state.score_trend = "improving"
                elif trend_slope < -0.05:
                    position_state.score_trend = "declining"
                else:
                    position_state.score_trend = "stable"
    
    def _determine_lifecycle_stage(self, 
                                 position_state: PositionState, 
                                 action_taken: str, 
                                 metadata: Dict) -> str:
        """Determine appropriate lifecycle stage based on current state."""
        # Check for specific stage transitions
        if action_taken == 'grace_start':
            return LifecycleStage.GRACE.value
        elif action_taken == 'grace_recovery':
            return LifecycleStage.ACTIVE.value
        elif action_taken == 'force_close':
            return LifecycleStage.CLOSING.value
        elif metadata.get('forced_review', False):
            return LifecycleStage.FORCED_REVIEW.value
        
        # Determine stage based on current conditions
        if position_state.consecutive_low_scores >= 5:
            return LifecycleStage.WARNING.value
        elif position_state.consecutive_low_scores >= 2:
            return LifecycleStage.GRACE.value
        else:
            return LifecycleStage.ACTIVE.value
    
    def _assess_health_status(self, position_state: PositionState) -> str:
        """Assess health status based on multiple factors."""
        risk_factors = 0
        
        # Score-based factors
        if position_state.current_score < 0.4:
            risk_factors += 3  # Very low score
        elif position_state.current_score < 0.6:
            risk_factors += 1  # Low score
        
        # Consecutive low scores
        if position_state.consecutive_low_scores >= 5:
            risk_factors += 2
        elif position_state.consecutive_low_scores >= 3:
            risk_factors += 1
        
        # Score trend
        if position_state.score_trend == "declining":
            risk_factors += 1
        
        # Size reduction
        size_reduction = (position_state.original_entry_size - position_state.current_size) / position_state.original_entry_size
        if size_reduction > 0.5:  # More than 50% size reduction
            risk_factors += 2
        elif size_reduction > 0.3:  # More than 30% size reduction
            risk_factors += 1
        
        # Determine health status
        if risk_factors >= 4:
            return HealthStatus.CRITICAL.value
        elif risk_factors >= 2:
            return HealthStatus.WARNING.value
        else:
            return HealthStatus.HEALTHY.value
    
    def record_position_closure(self, 
                              asset: str, 
                              closure_date: datetime, 
                              closure_reason: str,
                              final_score: float = 0.0):
        """
        Record position closure and finalize lifecycle.
        
        Args:
            asset: Asset symbol
            closure_date: Date of closure
            closure_reason: Reason for closure
            final_score: Final position score
        """
        if asset not in self.position_states:
            print(f"⚠️ Cannot close unknown position: {asset}")
            return
        
        position_state = self.position_states[asset]
        
        # Record closure event
        closure_event = LifecycleEvent(
            date=closure_date,
            event_type='closure',
            previous_size=position_state.current_size,
            new_size=0.0,
            previous_score=position_state.current_score,
            new_score=final_score,
            reason=closure_reason,
            metadata={
                'total_days_held': position_state.days_held,
                'final_stage': position_state.current_stage,
                'final_health': position_state.health_status,
                'total_events': position_state.lifecycle_events_count,
                'peak_size': position_state.peak_size,
                'total_size_changes': position_state.total_size_changes
            },
            stage_change=f"{position_state.current_stage} → CLOSED",
            health_change=f"{position_state.health_status} → CLOSED",
            triggered_by="system"
        )
        
        self.lifecycle_history[asset].append(closure_event)
        
        print(f"🏁 Position lifecycle ended: {asset} after {position_state.days_held} days "
              f"(final size: {position_state.current_size:.3f}, "
              f"final score: {final_score:.3f}, reason: {closure_reason})")
        
        # Remove from active tracking but keep history
        del self.position_states[asset]
    
    def get_position_summary(self, asset: str, current_date: datetime) -> Optional[PositionSummary]:
        """
        Get comprehensive position summary with lifecycle info.
        
        Args:
            asset: Asset symbol
            current_date: Current date
            
        Returns:
            PositionSummary with complete position information
        """
        if asset not in self.position_states:
            return None
        
        position_state = self.position_states[asset]
        
        # Get recent events (last 10)
        recent_events = self.lifecycle_history[asset][-10:]
        
        # Calculate additional metrics
        days_in_current_stage = self._calculate_days_in_stage(asset, current_date)
        avg_score = self._calculate_average_score(asset)
        score_volatility = self._calculate_score_volatility(asset)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(position_state)
        
        # Identify risk flags
        risk_flags = self._identify_risk_flags(position_state)
        
        # Determine priority level
        priority_level = self._determine_priority_level(position_state, risk_flags)
        
        return PositionSummary(
            asset=asset,
            state=position_state,
            recent_events=recent_events,
            health_status=position_state.health_status,
            recommendations=recommendations,
            days_in_current_stage=days_in_current_stage,
            avg_score=avg_score,
            score_volatility=score_volatility,
            risk_flags=risk_flags,
            priority_level=priority_level
        )
    
    def get_portfolio_lifecycle_report(self, current_date: datetime) -> Dict:
        """
        Generate portfolio-wide lifecycle report.
        
        Args:
            current_date: Current date
            
        Returns:
            Comprehensive portfolio lifecycle analytics
        """
        if not self.position_states:
            return {'message': 'No active positions to report'}
        
        # Aggregate statistics
        total_positions = len(self.position_states)
        stage_distribution = defaultdict(int)
        health_distribution = defaultdict(int)
        bucket_distribution = defaultdict(int)
        
        critical_positions = []
        warning_positions = []
        grace_positions = []
        
        total_size = 0.0
        total_events = 0
        
        for asset, state in self.position_states.items():
            stage_distribution[state.current_stage] += 1
            health_distribution[state.health_status] += 1
            bucket_distribution[state.bucket] += 1
            
            total_size += state.current_size
            total_events += state.lifecycle_events_count
            
            # Categorize positions needing attention
            if state.health_status == HealthStatus.CRITICAL.value:
                critical_positions.append(asset)
            elif state.health_status == HealthStatus.WARNING.value:
                warning_positions.append(asset)
            
            if state.current_stage == LifecycleStage.GRACE.value:
                grace_positions.append(asset)
        
        # Calculate average metrics
        avg_size = total_size / total_positions if total_positions > 0 else 0
        avg_events_per_position = total_events / total_positions if total_positions > 0 else 0
        
        # Generate portfolio health score
        health_score = self._calculate_portfolio_health_score(health_distribution, total_positions)
        
        return {
            'timestamp': current_date,
            'portfolio_summary': {
                'total_positions': total_positions,
                'total_portfolio_size': total_size,
                'average_position_size': avg_size,
                'average_events_per_position': avg_events_per_position,
                'portfolio_health_score': health_score
            },
            'stage_distribution': dict(stage_distribution),
            'health_distribution': dict(health_distribution),
            'bucket_distribution': dict(bucket_distribution),
            'positions_needing_attention': {
                'critical': critical_positions,
                'warning': warning_positions,
                'in_grace_period': grace_positions
            },
            'recommendations': self._generate_portfolio_recommendations(
                critical_positions, warning_positions, grace_positions
            )
        }
    
    def _calculate_days_in_stage(self, asset: str, current_date: datetime) -> int:
        """Calculate days spent in current lifecycle stage."""
        if asset not in self.position_states:
            return 0
        
        current_stage = self.position_states[asset].current_stage
        events = self.lifecycle_history[asset]
        
        # Find last stage change event
        for event in reversed(events):
            if event.stage_change and current_stage in event.stage_change:
                return (current_date - event.date).days
        
        # If no stage change found, use days since entry
        return self.position_states[asset].days_held
    
    def _calculate_average_score(self, asset: str) -> float:
        """Calculate average score over position lifecycle."""
        events = self.lifecycle_history[asset]
        if not events:
            return 0.0
        
        scores = [event.new_score for event in events if event.new_score > 0]
        return sum(scores) / len(scores) if scores else 0.0
    
    def _calculate_score_volatility(self, asset: str) -> float:
        """Calculate score volatility (standard deviation)."""
        events = self.lifecycle_history[asset]
        if len(events) < 2:
            return 0.0
        
        scores = [event.new_score for event in events if event.new_score > 0]
        if len(scores) < 2:
            return 0.0
        
        avg_score = sum(scores) / len(scores)
        variance = sum((score - avg_score) ** 2 for score in scores) / len(scores)
        return variance ** 0.5
    
    def _generate_recommendations(self, position_state: PositionState) -> List[str]:
        """Generate actionable recommendations for a position."""
        recommendations = []
        
        # Score-based recommendations
        if position_state.current_score < 0.4:
            recommendations.append("URGENT: Consider immediate closure due to very low score")
        elif position_state.current_score < 0.6:
            recommendations.append("Consider reducing position size or entering grace period")
        
        # Stage-based recommendations
        if position_state.current_stage == LifecycleStage.GRACE.value:
            recommendations.append("Monitor closely - position in grace period")
        elif position_state.current_stage == LifecycleStage.WARNING.value:
            recommendations.append("High priority review needed - extended poor performance")
        elif position_state.current_stage == LifecycleStage.FORCED_REVIEW.value:
            recommendations.append("REQUIRED: Forced review due to max holding period")
        
        # Trend-based recommendations
        if position_state.score_trend == "declining":
            recommendations.append("Declining score trend - consider exit strategy")
        elif position_state.score_trend == "improving":
            recommendations.append("Improving trend - consider maintaining or increasing")
        
        # Size-based recommendations
        size_reduction = (position_state.original_entry_size - position_state.current_size) / position_state.original_entry_size
        if size_reduction > 0.7:
            recommendations.append("Significant size reduction - evaluate remaining position viability")
        
        return recommendations
    
    def _identify_risk_flags(self, position_state: PositionState) -> List[str]:
        """Identify risk flags for a position."""
        flags = []
        
        if position_state.consecutive_low_scores >= 5:
            flags.append("EXTENDED_LOW_PERFORMANCE")
        
        if position_state.score_trend == "declining":
            flags.append("DECLINING_TREND")
        
        if position_state.current_score < 0.4:
            flags.append("VERY_LOW_SCORE")
        
        size_reduction = (position_state.original_entry_size - position_state.current_size) / position_state.original_entry_size
        if size_reduction > 0.5:
            flags.append("SIGNIFICANT_SIZE_REDUCTION")
        
        if position_state.days_held > 60:  # Configurable
            flags.append("LONG_HOLDING_PERIOD")
        
        return flags
    
    def _determine_priority_level(self, position_state: PositionState, risk_flags: List[str]) -> str:
        """Determine priority level based on health and risk flags."""
        if position_state.health_status == HealthStatus.CRITICAL.value:
            return "critical"
        elif position_state.health_status == HealthStatus.WARNING.value:
            return "high"
        elif any(flag in ["VERY_LOW_SCORE", "EXTENDED_LOW_PERFORMANCE"] for flag in risk_flags):
            return "high"
        elif risk_flags:
            return "normal"
        else:
            return "low"
    
    def _calculate_portfolio_health_score(self, health_distribution: Dict, total_positions: int) -> float:
        """Calculate overall portfolio health score (0-100)."""
        if total_positions == 0:
            return 100.0
        
        healthy_count = health_distribution.get(HealthStatus.HEALTHY.value, 0)
        warning_count = health_distribution.get(HealthStatus.WARNING.value, 0)
        critical_count = health_distribution.get(HealthStatus.CRITICAL.value, 0)
        
        # Weighted score: Healthy=100, Warning=50, Critical=0
        weighted_score = (healthy_count * 100 + warning_count * 50 + critical_count * 0) / total_positions
        
        return round(weighted_score, 1)
    
    def _generate_portfolio_recommendations(self, 
                                          critical_positions: List[str], 
                                          warning_positions: List[str], 
                                          grace_positions: List[str]) -> List[str]:
        """Generate portfolio-level recommendations."""
        recommendations = []
        
        if critical_positions:
            recommendations.append(f"URGENT: {len(critical_positions)} critical positions need immediate attention")
        
        if warning_positions:
            recommendations.append(f"Review {len(warning_positions)} positions with warning status")
        
        if grace_positions:
            recommendations.append(f"Monitor {len(grace_positions)} positions in grace period")
        
        total_at_risk = len(critical_positions) + len(warning_positions)
        if total_at_risk > 3:
            recommendations.append("Consider portfolio-wide risk assessment - multiple positions at risk")
        
        return recommendations
    
    def get_configuration_summary(self) -> Dict:
        """Get configuration summary."""
        return {
            'max_history_events': self.max_history_events,
            'score_trend_window': self.score_trend_window,
            'low_score_threshold': self.low_score_threshold,
            'active_positions': len(self.position_states),
            'total_tracked_assets': len(self.lifecycle_history),
            'lifecycle_stages': [stage.value for stage in LifecycleStage],
            'health_statuses': [status.value for status in HealthStatus]
        } 