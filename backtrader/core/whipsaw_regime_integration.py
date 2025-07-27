"""
Module 7: Advanced Whipsaw Protection - Regime Integration & Override Authority

This module implements regime-aware override capabilities for whipsaw protection,
integrating with Module 6's regime intelligence for smart protection decisions.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

from .whipsaw_protection import OverrideReason, ProtectionDecision


class OverrideAuthority(Enum):
    """Override authority levels"""
    NONE = "none"
    EMERGENCY = "emergency"
    REGIME = "regime"
    MANUAL = "manual"
    SYSTEM = "system"


class EmergencyCondition(Enum):
    """Emergency condition types"""
    HIGH_VOLATILITY = "high_volatility"
    REGIME_CHANGE = "regime_change"
    MARKET_STRESS = "market_stress"
    LIQUIDITY_CRISIS = "liquidity_crisis"


@dataclass
class OverrideDecision:
    """Override decision record"""
    asset: str
    action: str
    authority: OverrideAuthority
    reason: str
    condition: str
    decision_date: datetime
    expires_date: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EmergencyScenario:
    """Emergency scenario definition"""
    condition: EmergencyCondition
    threshold: float
    duration_minutes: int
    authority_level: OverrideAuthority
    description: str


class RegimeOverrideManager:
    """
    Manages regime-based overrides of whipsaw protection using Module 6 integration
    """
    
    def __init__(self, regime_context_provider, override_cooldown_hours=24):
        """
        Initialize regime override manager
        
        Args:
            regime_context_provider: Module 6 regime context provider
            override_cooldown_hours: Hours between overrides per asset
        """
        self.regime_context_provider = regime_context_provider
        self.override_cooldown_hours = override_cooldown_hours
        self.override_history: Dict[str, List[OverrideDecision]] = defaultdict(list)
        self.active_overrides: Dict[str, OverrideDecision] = {}
        
        # Emergency scenarios configuration
        self.emergency_scenarios = self._initialize_emergency_scenarios()
        
        # Override statistics
        self.override_stats = {
            'total_override_requests': 0,
            'overrides_granted': 0,
            'overrides_denied': 0,
            'regime_overrides': 0,
            'emergency_overrides': 0,
            'manual_overrides': 0
        }
        
        print(f"🔗 Regime Override Manager initialized with {override_cooldown_hours}h cooldown")
    
    def can_override_protection(self, asset: str, action: str, 
                              current_date: datetime,
                              context: Optional[Dict] = None) -> Tuple[bool, OverrideAuthority, str]:
        """
        Determine if regime context allows override of whipsaw protection
        
        Args:
            asset: Asset symbol
            action: Action type (open/close)
            current_date: Current date
            context: Optional additional context
            
        Returns:
            Tuple of (can_override: bool, authority: OverrideAuthority, reason: str)
        """
        self.override_stats['total_override_requests'] += 1
        
        # Check cooldown period
        if self._is_override_cooling_down(asset, current_date):
            self.override_stats['overrides_denied'] += 1
            return False, OverrideAuthority.NONE, "Override cooldown period active"
        
        # Check for emergency conditions first (highest priority)
        emergency_override = self._check_emergency_override(asset, action, current_date, context)
        if emergency_override[0]:
            self.override_stats['overrides_granted'] += 1
            self.override_stats['emergency_overrides'] += 1
            return emergency_override
        
        # Check for regime-based override
        regime_override = self._check_regime_override(asset, action, current_date, context)
        if regime_override[0]:
            self.override_stats['overrides_granted'] += 1
            self.override_stats['regime_overrides'] += 1
            return regime_override
        
        # Check for manual override (if authorized)
        manual_override = self._check_manual_override(asset, action, current_date, context)
        if manual_override[0]:
            self.override_stats['overrides_granted'] += 1
            self.override_stats['manual_overrides'] += 1
            return manual_override
        
        self.override_stats['overrides_denied'] += 1
        return False, OverrideAuthority.NONE, "No override conditions met"
    
    def apply_regime_override(self, asset: str, action: str, current_date: datetime,
                            authority: OverrideAuthority, reason: str,
                            duration_hours: int = 24) -> str:
        """
        Apply and record regime-based override
        
        Args:
            asset: Asset symbol
            action: Action type
            current_date: Current date
            authority: Override authority level
            reason: Override reason
            duration_hours: How long override is valid
            
        Returns:
            Override ID
        """
        expires_date = current_date + timedelta(hours=duration_hours)
        
        override_decision = OverrideDecision(
            asset=asset,
            action=action,
            authority=authority,
            reason=reason,
            condition=self._extract_condition_from_reason(reason),
            decision_date=current_date,
            expires_date=expires_date
        )
        
        # Record override
        override_id = f"override_{asset}_{action}_{current_date.strftime('%Y%m%d_%H%M%S')}"
        self.override_history[asset].append(override_decision)
        self.active_overrides[f"{asset}_{action}"] = override_decision
        
        print(f"🔓 OVERRIDE APPLIED: {asset} {action} - {reason} (expires: {expires_date.strftime('%Y-%m-%d %H:%M')})")
        
        return override_id
    
    def is_override_cooling_down(self, asset: str, 
                                current_date: datetime) -> Tuple[bool, Optional[datetime]]:
        """
        Check if asset is in override cooldown period
        
        Args:
            asset: Asset to check
            current_date: Current date
            
        Returns:
            Tuple of (is_cooling: bool, cooldown_expires: datetime)
        """
        if asset not in self.override_history:
            return False, None
        
        # Get most recent override
        recent_overrides = [
            override for override in self.override_history[asset]
            if override.decision_date > current_date - timedelta(hours=self.override_cooldown_hours)
        ]
        
        if not recent_overrides:
            return False, None
        
        most_recent = max(recent_overrides, key=lambda x: x.decision_date)
        cooldown_expires = most_recent.decision_date + timedelta(hours=self.override_cooldown_hours)
        
        is_cooling = current_date < cooldown_expires
        return is_cooling, cooldown_expires if is_cooling else None
    
    def get_override_eligibility(self, assets: List[str], 
                               current_date: datetime) -> Dict[str, Dict]:
        """
        Get override eligibility status for multiple assets
        
        Args:
            assets: Assets to check
            current_date: Current date
            
        Returns:
            Override eligibility status for each asset
        """
        eligibility = {}
        
        for asset in assets:
            # Check cooldown
            is_cooling, cooldown_expires = self.is_override_cooling_down(asset, current_date)
            
            # Check active overrides
            active_override = self.active_overrides.get(f"{asset}_open") or self.active_overrides.get(f"{asset}_close")
            
            # Get current regime context
            regime_context = None
            regime_eligible = False
            try:
                regime_context = self.regime_context_provider.get_current_context(current_date)
                regime_eligible = self._is_regime_override_eligible(regime_context)
            except Exception as e:
                print(f"⚠️ Error getting regime context for {asset}: {e}")
            
            eligibility[asset] = {
                'cooling_down': is_cooling,
                'cooldown_expires': cooldown_expires.isoformat() if cooldown_expires else None,
                'active_override': {
                    'action': active_override.action if active_override else None,
                    'authority': active_override.authority.value if active_override else None,
                    'expires': active_override.expires_date.isoformat() if active_override else None
                } if active_override else None,
                'regime_eligible': regime_eligible,
                'current_regime': regime_context.current_regime.regime if regime_context else None,
                'regime_transition': bool(regime_context.recent_transition) if regime_context else False,
                'emergency_conditions': self._check_emergency_conditions(current_date)
            }
        
        return eligibility
    
    def _initialize_emergency_scenarios(self) -> List[EmergencyScenario]:
        """
        Initialize emergency scenario definitions
        
        Returns:
            List of emergency scenarios
        """
        return [
            EmergencyScenario(
                condition=EmergencyCondition.HIGH_VOLATILITY,
                threshold=0.05,  # 5% volatility
                duration_minutes=60,
                authority_level=OverrideAuthority.EMERGENCY,
                description="Market volatility exceeds 5% threshold"
            ),
            EmergencyScenario(
                condition=EmergencyCondition.REGIME_CHANGE,
                threshold=0.8,  # High confidence regime change
                duration_minutes=120,
                authority_level=OverrideAuthority.REGIME,
                description="High-confidence regime change detected"
            ),
            EmergencyScenario(
                condition=EmergencyCondition.MARKET_STRESS,
                threshold=0.7,  # Market stress indicator
                duration_minutes=180,
                authority_level=OverrideAuthority.EMERGENCY,
                description="Market stress indicators elevated"
            )
        ]
    
    def _check_emergency_override(self, asset: str, action: str, 
                                current_date: datetime,
                                context: Optional[Dict]) -> Tuple[bool, OverrideAuthority, str]:
        """
        Check for emergency condition overrides
        
        Args:
            asset: Asset symbol
            action: Action type
            current_date: Current date
            context: Additional context
            
        Returns:
            Tuple of (eligible: bool, authority: OverrideAuthority, reason: str)
        """
        # Check each emergency scenario
        for scenario in self.emergency_scenarios:
            if self._is_emergency_condition_met(scenario, current_date, context):
                return (
                    True,
                    scenario.authority_level,
                    f"Emergency override: {scenario.description}"
                )
        
        return False, OverrideAuthority.NONE, "No emergency conditions detected"
    
    def _check_regime_override(self, asset: str, action: str, 
                             current_date: datetime,
                             context: Optional[Dict]) -> Tuple[bool, OverrideAuthority, str]:
        """
        Check for regime-based override eligibility
        
        Args:
            asset: Asset symbol
            action: Action type
            current_date: Current date
            context: Additional context
            
        Returns:
            Tuple of (eligible: bool, authority: OverrideAuthority, reason: str)
        """
        try:
            # Get current regime context from Module 6
            regime_context = self.regime_context_provider.get_current_context(current_date)
            
            # Check for recent regime transition
            if regime_context.recent_transition:
                severity = regime_context.recent_transition.severity
                
                # Critical regime changes allow overrides
                if severity.value == 'critical':
                    transition_desc = f"{regime_context.recent_transition.from_regime} → {regime_context.recent_transition.to_regime}"
                    return (
                        True,
                        OverrideAuthority.REGIME,
                        f"Critical regime transition: {transition_desc}"
                    )
                
                # High severity regime changes allow overrides for certain actions
                elif severity.value == 'high' and action in ['open', 'close']:
                    transition_desc = f"{regime_context.recent_transition.from_regime} → {regime_context.recent_transition.to_regime}"
                    return (
                        True,
                        OverrideAuthority.REGIME,
                        f"High-severity regime transition: {transition_desc}"
                    )
            
            # Check for low regime confidence (unstable period)
            if regime_context.current_regime.confidence < 0.4:
                return (
                    True,
                    OverrideAuthority.REGIME,
                    f"Low regime confidence: {regime_context.current_regime.confidence:.3f} < 0.4"
                )
            
            return False, OverrideAuthority.NONE, "No regime override conditions met"
            
        except Exception as e:
            print(f"⚠️ Error checking regime override: {e}")
            return False, OverrideAuthority.NONE, f"Regime check failed: {e}"
    
    def _check_manual_override(self, asset: str, action: str, 
                             current_date: datetime,
                             context: Optional[Dict]) -> Tuple[bool, OverrideAuthority, str]:
        """
        Check for manual override authorization
        
        Args:
            asset: Asset symbol
            action: Action type
            current_date: Current date
            context: Additional context
            
        Returns:
            Tuple of (eligible: bool, authority: OverrideAuthority, reason: str)
        """
        # Check if manual override is requested and authorized
        if context and context.get('manual_override_requested'):
            auth_level = context.get('authorization_level', 'none')
            
            # Simple authorization check (in production, this would be more sophisticated)
            authorized_levels = ['admin', 'manager', 'senior_trader']
            
            if auth_level in authorized_levels:
                override_reason = context.get('override_reason', 'Manual override requested')
                return (
                    True,
                    OverrideAuthority.MANUAL,
                    f"Manual override authorized by {auth_level}: {override_reason}"
                )
        
        return False, OverrideAuthority.NONE, "No manual override authorization"
    
    def _is_override_cooling_down(self, asset: str, current_date: datetime) -> bool:
        """
        Internal check for override cooldown
        
        Args:
            asset: Asset to check
            current_date: Current date
            
        Returns:
            True if in cooldown period
        """
        is_cooling, _ = self.is_override_cooling_down(asset, current_date)
        return is_cooling
    
    def _is_regime_override_eligible(self, regime_context) -> bool:
        """
        Check if current regime context is eligible for overrides
        
        Args:
            regime_context: Regime context from Module 6
            
        Returns:
            True if eligible for regime overrides
        """
        if not regime_context:
            return False
        
        # Recent transition makes override eligible
        if regime_context.recent_transition:
            return True
        
        # Low confidence makes override eligible
        if regime_context.current_regime.confidence < 0.5:
            return True
        
        return False
    
    def _check_emergency_conditions(self, current_date: datetime) -> List[str]:
        """
        Check for current emergency conditions
        
        Args:
            current_date: Current date
            
        Returns:
            List of active emergency conditions
        """
        active_conditions = []
        
        # This would integrate with market data in production
        # For now, return basic checks
        
        try:
            # Check regime transition (emergency condition)
            regime_context = self.regime_context_provider.get_current_context(current_date)
            if regime_context.recent_transition:
                if regime_context.recent_transition.severity.value in ['high', 'critical']:
                    active_conditions.append('regime_change')
        except:
            pass
        
        return active_conditions
    
    def _is_emergency_condition_met(self, scenario: EmergencyScenario, 
                                  current_date: datetime,
                                  context: Optional[Dict]) -> bool:
        """
        Check if specific emergency scenario is met
        
        Args:
            scenario: Emergency scenario to check
            current_date: Current date
            context: Additional context
            
        Returns:
            True if scenario conditions are met
        """
        if scenario.condition == EmergencyCondition.REGIME_CHANGE:
            try:
                regime_context = self.regime_context_provider.get_current_context(current_date)
                if regime_context.recent_transition:
                    return regime_context.recent_transition.confidence >= scenario.threshold
            except:
                pass
        
        elif scenario.condition == EmergencyCondition.HIGH_VOLATILITY:
            if context and 'volatility' in context:
                return context['volatility'] >= scenario.threshold
        
        elif scenario.condition == EmergencyCondition.MARKET_STRESS:
            if context and 'market_stress' in context:
                return context['market_stress'] >= scenario.threshold
        
        return False
    
    def _extract_condition_from_reason(self, reason: str) -> str:
        """
        Extract condition type from override reason
        
        Args:
            reason: Override reason string
            
        Returns:
            Condition type
        """
        reason_lower = reason.lower()
        
        if 'regime' in reason_lower:
            return 'regime_change'
        elif 'emergency' in reason_lower:
            return 'emergency'
        elif 'volatility' in reason_lower:
            return 'high_volatility'
        elif 'manual' in reason_lower:
            return 'manual'
        else:
            return 'other'
    
    def get_override_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get override usage statistics
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Override statistics
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Count recent overrides by type
        recent_overrides = []
        for asset_overrides in self.override_history.values():
            recent_overrides.extend([
                override for override in asset_overrides
                if override.decision_date > cutoff_date
            ])
        
        override_by_authority = defaultdict(int)
        override_by_condition = defaultdict(int)
        
        for override in recent_overrides:
            override_by_authority[override.authority.value] += 1
            override_by_condition[override.condition] += 1
        
        total_requests = self.override_stats['total_override_requests']
        
        return {
            'period_days': days,
            'total_override_requests': total_requests,
            'overrides_granted': self.override_stats['overrides_granted'],
            'overrides_denied': self.override_stats['overrides_denied'],
            'grant_rate': self.override_stats['overrides_granted'] / max(total_requests, 1),
            'recent_overrides_count': len(recent_overrides),
            'overrides_by_authority': dict(override_by_authority),
            'overrides_by_condition': dict(override_by_condition),
            'regime_overrides': self.override_stats['regime_overrides'],
            'emergency_overrides': self.override_stats['emergency_overrides'],
            'manual_overrides': self.override_stats['manual_overrides'],
            'active_overrides_count': len(self.active_overrides),
            'cooldown_hours': self.override_cooldown_hours
        }
    
    def cleanup_expired_overrides(self, current_date: datetime):
        """
        Clean up expired overrides
        
        Args:
            current_date: Current date for expiry check
        """
        expired_keys = []
        
        for key, override in self.active_overrides.items():
            if current_date > override.expires_date:
                expired_keys.append(key)
        
        for key in expired_keys:
            expired_override = self.active_overrides.pop(key)
            print(f"⏰ Override expired: {expired_override.asset} {expired_override.action}")
        
        if expired_keys:
            print(f"🧹 Cleaned up {len(expired_keys)} expired overrides")


class SimpleOverrideAuditTrail:
    """
    Simple audit trail for override decisions and usage
    """
    
    def __init__(self, max_audit_days=365):
        """
        Initialize audit trail
        
        Args:
            max_audit_days: Maximum days to retain audit records
        """
        self.max_audit_days = max_audit_days
        self.audit_records: List[Dict[str, Any]] = []
    
    def record_override_request(self, asset: str, action: str, current_date: datetime,
                              granted: bool, authority: OverrideAuthority, reason: str,
                              **metadata):
        """
        Record override request and decision
        
        Args:
            asset: Asset symbol
            action: Action type
            current_date: Request date
            granted: Whether override was granted
            authority: Authority level
            reason: Override reason
            **metadata: Additional metadata
        """
        record = {
            'timestamp': current_date.isoformat(),
            'asset': asset,
            'action': action,
            'granted': granted,
            'authority': authority.value,
            'reason': reason,
            'metadata': metadata
        }
        
        self.audit_records.append(record)
        
        # Clean old records periodically
        if len(self.audit_records) % 100 == 0:
            self._clean_old_records(current_date)
    
    def get_audit_report(self, asset: Optional[str] = None, 
                        days: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get audit report for override activities
        
        Args:
            asset: Filter by asset (None for all)
            days: Number of days to look back
            
        Returns:
            List of audit records
        """
        records = self.audit_records.copy()
        
        if asset:
            records = [r for r in records if r['asset'] == asset]
        
        if days:
            cutoff_date = datetime.now() - timedelta(days=days)
            records = [
                r for r in records
                if datetime.fromisoformat(r['timestamp']) > cutoff_date
            ]
        
        return records
    
    def _clean_old_records(self, current_date: datetime):
        """
        Clean old audit records
        
        Args:
            current_date: Current date for age calculation
        """
        cutoff_date = current_date - timedelta(days=self.max_audit_days)
        
        old_count = len(self.audit_records)
        self.audit_records = [
            record for record in self.audit_records
            if datetime.fromisoformat(record['timestamp']) > cutoff_date
        ]
        
        cleaned_count = old_count - len(self.audit_records)
        if cleaned_count > 0:
            print(f"🧹 Cleaned {cleaned_count} old audit records") 