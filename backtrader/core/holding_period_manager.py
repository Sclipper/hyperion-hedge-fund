"""
Holding Period Manager for position lifecycle constraints.

This module implements professional-grade holding period management that enforces
minimum and maximum holding periods for positions, with intelligent regime override
capability for critical market changes.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List, Any
from enum import Enum


class AdjustmentType(Enum):
    """Types of position adjustments"""
    CLOSE = "close"
    REDUCE = "reduce"
    INCREASE = "increase"
    ANY = "any"


@dataclass
class PositionAge:
    """Metadata for tracking position age and adjustments"""
    asset: str
    entry_date: datetime
    entry_size: float
    entry_reason: str
    last_adjustment_date: Optional[datetime] = None
    adjustment_count: int = 0


@dataclass
class RegimeContext:
    """Context information for regime changes and overrides"""
    regime_changed: bool
    new_regime: str
    old_regime: str
    regime_severity: str  # 'normal', 'high', 'critical'
    change_date: datetime


class HoldingPeriodManager:
    """
    Minimum and maximum holding period enforcement for positions.
    
    Ensures positions respect timing constraints:
    - Minimum holding periods prevent premature adjustments
    - Maximum holding periods force periodic review
    - Different rules for different adjustment types (close vs reduce)
    - Complete position lifecycle tracking
    
    Key Features:
    - Configurable min/max holding periods (default: 3-90 days)
    - Adjustment type awareness (close, reduce, increase)
    - Position age tracking with entry metadata
    - Forced review triggers for max holding period
    - Complete audit trail of position adjustments
    """
    
    def __init__(self, 
                 min_holding_days: int = 3, 
                 max_holding_days: int = 90):
        """
        Initialize holding period manager.
        
        Args:
            min_holding_days: Minimum days before position can be adjusted
            max_holding_days: Maximum days before position must be reviewed
        """
        self.min_holding_days = min_holding_days
        self.max_holding_days = max_holding_days
        self.position_ages: Dict[str, PositionAge] = {}
        
        # Validation
        if not (1 <= min_holding_days <= 365):
            raise ValueError(f"min_holding_days must be 1-365, got {min_holding_days}")
        if not (min_holding_days <= max_holding_days <= 365):
            raise ValueError(f"max_holding_days must be >= min_holding_days and <= 365, got {max_holding_days}")
    
    def can_adjust_position(self, 
                          asset: str, 
                          current_date: datetime, 
                          adjustment_type: str = 'any') -> Tuple[bool, str]:
        """
        Check if position can be adjusted based on holding period.
        
        Args:
            asset: Asset symbol
            current_date: Current date
            adjustment_type: Type of adjustment ('close', 'reduce', 'increase', 'any')
            
        Returns:
            Tuple of (can_adjust: bool, reason: str)
        """
        if asset not in self.position_ages:
            return True, "New position, no holding period constraints"
        
        position_age = self.position_ages[asset]
        days_held = (current_date - position_age.entry_date).days
        
        # Check minimum holding period
        if days_held < self.min_holding_days:
            # Different rules for different adjustment types
            if adjustment_type.lower() in ['close', 'reduce']:
                return False, (f"Min holding period not met: {days_held}/{self.min_holding_days} days "
                             f"(entry: {position_age.entry_date.strftime('%Y-%m-%d')})")
            elif adjustment_type.lower() == 'increase':
                # Can always increase positions regardless of holding period
                return True, f"Position increase allowed (held {days_held} days)"
        
        # Check maximum holding period
        if days_held >= self.max_holding_days:
            return True, f"Max holding period reached: {days_held} days, forced review required"
        
        return True, f"Within holding period: {days_held} days (min: {self.min_holding_days}, max: {self.max_holding_days})"
    
    def record_position_entry(self, 
                            asset: str, 
                            entry_date: datetime, 
                            entry_size: float, 
                            entry_reason: str):
        """
        Record position entry for holding period tracking.
        
        Args:
            asset: Asset symbol
            entry_date: Date position was entered
            entry_size: Initial position size
            entry_reason: Reason for position entry
        """
        position_age = PositionAge(
            asset=asset,
            entry_date=entry_date,
            entry_size=entry_size,
            entry_reason=entry_reason,
            last_adjustment_date=None,
            adjustment_count=0
        )
        
        self.position_ages[asset] = position_age
        print(f"📅 Recorded position entry: {asset} on {entry_date.strftime('%Y-%m-%d')} "
              f"(size: {entry_size:.3f}, reason: {entry_reason})")
    
    def record_position_adjustment(self, 
                                 asset: str, 
                                 adjustment_date: datetime, 
                                 adjustment_type: str, 
                                 adjustment_reason: str):
        """
        Record position adjustment for tracking.
        
        Args:
            asset: Asset symbol
            adjustment_date: Date of adjustment
            adjustment_type: Type of adjustment
            adjustment_reason: Reason for adjustment
        """
        if asset in self.position_ages:
            position_age = self.position_ages[asset]
            position_age.last_adjustment_date = adjustment_date
            position_age.adjustment_count += 1
            print(f"📝 Recorded position adjustment: {asset} - {adjustment_type} "
                  f"(#{position_age.adjustment_count}, reason: {adjustment_reason})")
    
    def record_position_closure(self, asset: str, closure_date: datetime, closure_reason: str):
        """
        Record position closure and remove from tracking.
        
        Args:
            asset: Asset symbol
            closure_date: Date of closure
            closure_reason: Reason for closure
        """
        if asset in self.position_ages:
            position_age = self.position_ages[asset]
            days_held = (closure_date - position_age.entry_date).days
            print(f"🗑️ Position closed: {asset} after {days_held} days "
                  f"(entry: {position_age.entry_date.strftime('%Y-%m-%d')}, "
                  f"closure: {closure_date.strftime('%Y-%m-%d')}, "
                  f"reason: {closure_reason})")
            del self.position_ages[asset]
    
    def get_position_age(self, asset: str, current_date: datetime) -> int:
        """
        Get position age in days.
        
        Args:
            asset: Asset symbol
            current_date: Current date
            
        Returns:
            Age in days, or 0 if position not tracked
        """
        if asset not in self.position_ages:
            return 0
        
        position_age = self.position_ages[asset]
        return (current_date - position_age.entry_date).days
    
    def get_eligible_positions_for_adjustment(self, 
                                            portfolio_assets: List[str], 
                                            current_date: datetime,
                                            adjustment_type: str = 'any') -> List[str]:
        """
        Get list of positions that can be adjusted today.
        
        Args:
            portfolio_assets: List of current portfolio assets
            current_date: Current date
            adjustment_type: Type of adjustment to check
            
        Returns:
            List of assets eligible for adjustment
        """
        eligible = []
        
        for asset in portfolio_assets:
            can_adjust, reason = self.can_adjust_position(asset, current_date, adjustment_type)
            if can_adjust:
                eligible.append(asset)
            else:
                print(f"⏳ {asset} not eligible for {adjustment_type}: {reason}")
        
        return eligible
    
    def should_force_review(self, asset: str, current_date: datetime) -> bool:
        """
        Check if position has reached max holding period and needs review.
        
        Args:
            asset: Asset symbol
            current_date: Current date
            
        Returns:
            True if position needs forced review due to max holding period
        """
        if asset not in self.position_ages:
            return False
        
        position_age = self.position_ages[asset]
        days_held = (current_date - position_age.entry_date).days
        
        return days_held >= self.max_holding_days
    
    def get_holding_status(self, asset: str, current_date: datetime) -> Optional[Dict]:
        """
        Get comprehensive holding period status for an asset.
        
        Args:
            asset: Asset symbol
            current_date: Current date
            
        Returns:
            Dict with holding period status details, or None if not tracked
        """
        if asset not in self.position_ages:
            return None
        
        position_age = self.position_ages[asset]
        days_held = (current_date - position_age.entry_date).days
        
        return {
            'asset': asset,
            'entry_date': position_age.entry_date,
            'days_held': days_held,
            'min_holding_days': self.min_holding_days,
            'max_holding_days': self.max_holding_days,
            'days_until_min_met': max(0, self.min_holding_days - days_held),
            'days_until_forced_review': max(0, self.max_holding_days - days_held),
            'can_close': days_held >= self.min_holding_days,
            'needs_forced_review': days_held >= self.max_holding_days,
            'entry_size': position_age.entry_size,
            'entry_reason': position_age.entry_reason,
            'last_adjustment_date': position_age.last_adjustment_date,
            'adjustment_count': position_age.adjustment_count
        }
    
    def get_all_holding_status(self, current_date: datetime) -> Dict[str, Dict]:
        """
        Get holding period status for all tracked positions.
        
        Args:
            current_date: Current date
            
        Returns:
            Dict mapping asset symbols to their holding period status
        """
        return {
            asset: self.get_holding_status(asset, current_date)
            for asset in self.position_ages.keys()
        }
    
    def get_configuration_summary(self) -> Dict:
        """
        Get current holding period manager configuration.
        
        Returns:
            Dict with configuration parameters
        """
        return {
            'min_holding_days': self.min_holding_days,
            'max_holding_days': self.max_holding_days,
            'tracked_positions': len(self.position_ages),
            'adjustment_types_supported': ['close', 'reduce', 'increase', 'any'],
            'holding_window': f'{self.min_holding_days}-{self.max_holding_days} days'
        }


class RegimeAwareHoldingPeriodManager(HoldingPeriodManager):
    """
    Enhanced holding period manager with regime override capability.
    
    Extends base holding period management with intelligent regime awareness:
    - Normal holding periods apply during stable markets
    - Critical regime changes can override minimum holding periods
    - Cooldown periods prevent override abuse
    - Regime severity assessment (normal/high/critical)
    - Complete audit trail of regime overrides
    
    Key Features:
    - Regime severity-based override rules
    - Per-asset override cooldown tracking
    - Override eligibility assessment
    - Enhanced logging and audit trail
    - Integration with regime detection systems
    """
    
    def __init__(self, 
                 min_holding_days: int = 3, 
                 max_holding_days: int = 90,
                 regime_override_cooldown: int = 30):
        """
        Initialize regime-aware holding period manager.
        
        Args:
            min_holding_days: Minimum days before position can be adjusted
            max_holding_days: Maximum days before position must be reviewed
            regime_override_cooldown: Days between regime overrides per asset
        """
        super().__init__(min_holding_days, max_holding_days)
        self.regime_override_cooldown = regime_override_cooldown
        self.last_regime_override: Dict[str, datetime] = {}
        
        # Validation
        if not (1 <= regime_override_cooldown <= 180):
            raise ValueError(f"regime_override_cooldown must be 1-180 days, got {regime_override_cooldown}")
    
    def can_adjust_position(self, 
                          asset: str, 
                          current_date: datetime,
                          regime_context: Optional[Dict] = None,
                          adjustment_type: str = 'any') -> Tuple[bool, str]:
        """
        Enhanced holding period check with regime override capability.
        
        Args:
            asset: Asset symbol
            current_date: Current date
            regime_context: Optional regime context for override decisions
            adjustment_type: Type of adjustment
            
        Returns:
            Tuple of (can_adjust: bool, reason: str)
        """
        # Normal holding period check first
        normal_check, normal_reason = super().can_adjust_position(asset, current_date, adjustment_type)
        
        if normal_check:
            return True, normal_reason
        
        # Check for regime override eligibility
        if regime_context and regime_context.get('regime_changed', False):
            can_override, override_reason = self._can_use_regime_override(asset, current_date, regime_context)
            if can_override:
                # Record the override
                self.last_regime_override[asset] = current_date
                return True, f"REGIME OVERRIDE: {override_reason}"
        
        return False, normal_reason
    
    def _can_use_regime_override(self, 
                               asset: str, 
                               current_date: datetime, 
                               regime_context: Dict) -> Tuple[bool, str]:
        """
        Check if regime change justifies holding period override.
        
        Args:
            asset: Asset symbol
            current_date: Current date
            regime_context: Regime change context
            
        Returns:
            Tuple of (can_override: bool, reason: str)
        """
        # Check cooldown period - prevent regime override abuse
        if asset in self.last_regime_override:
            last_override = self.last_regime_override[asset]
            days_since_override = (current_date - last_override).days
            
            if days_since_override < self.regime_override_cooldown:
                return False, (f"Regime override cooldown active: {days_since_override}/"
                             f"{self.regime_override_cooldown} days since last override")
        
        # Check regime severity - only allow for significant regime changes
        regime_severity = regime_context.get('regime_severity', 'normal')
        
        if regime_severity == 'normal':
            return False, "Regime change not significant enough for override (severity: normal)"
        
        # Check how close we are to meeting minimum holding period
        if asset in self.position_ages:
            position_age = self.position_ages[asset]
            days_held = (current_date - position_age.entry_date).days
            days_remaining = self.min_holding_days - days_held
            
            # Only allow override if we're close to meeting minimum (within 2 days)
            if days_remaining > 2:
                return False, (f"Too far from min holding period: {days_remaining} days remaining "
                             f"(override only allowed within 2 days of minimum)")
        
        # Grant override
        new_regime = regime_context.get('new_regime', 'Unknown')
        old_regime = regime_context.get('old_regime', 'Unknown')
        
        return True, (f"Critical regime change {old_regime} → {new_regime} "
                     f"(severity: {regime_severity}) overrides holding period")
    
    def get_regime_override_status(self, asset: str, current_date: datetime) -> Dict:
        """
        Get regime override status for an asset.
        
        Args:
            asset: Asset symbol
            current_date: Current date
            
        Returns:
            Dict with override status details
        """
        status = {
            'asset': asset,
            'has_used_override': asset in self.last_regime_override,
            'cooldown_active': False,
            'days_since_override': None,
            'days_until_cooldown_expires': None
        }
        
        if asset in self.last_regime_override:
            last_override = self.last_regime_override[asset]
            days_since = (current_date - last_override).days
            days_until_expiry = max(0, self.regime_override_cooldown - days_since)
            
            status.update({
                'last_override_date': last_override,
                'days_since_override': days_since,
                'cooldown_active': days_since < self.regime_override_cooldown,
                'days_until_cooldown_expires': days_until_expiry
            })
        
        return status
    
    def can_use_regime_override(self, 
                              asset: str, 
                              current_date: datetime, 
                              regime_context: Dict) -> bool:
        """
        Public method to check regime override eligibility.
        
        Args:
            asset: Asset symbol
            current_date: Current date
            regime_context: Regime context
            
        Returns:
            True if regime override can be used
        """
        can_override, _ = self._can_use_regime_override(asset, current_date, regime_context)
        return can_override
    
    def get_all_regime_override_status(self, current_date: datetime) -> Dict[str, Dict]:
        """
        Get regime override status for all assets.
        
        Args:
            current_date: Current date
            
        Returns:
            Dict mapping assets to their override status
        """
        all_assets = set(self.position_ages.keys()) | set(self.last_regime_override.keys())
        
        return {
            asset: self.get_regime_override_status(asset, current_date)
            for asset in all_assets
        }
    
    def clean_expired_overrides(self, current_date: datetime) -> int:
        """
        Clean up expired regime overrides from tracking.
        
        Args:
            current_date: Current date
            
        Returns:
            Number of expired overrides removed
        """
        expired_assets = []
        
        for asset, override_date in self.last_regime_override.items():
            days_since = (current_date - override_date).days
            if days_since >= self.regime_override_cooldown * 2:  # Keep for 2x cooldown period
                expired_assets.append(asset)
        
        for asset in expired_assets:
            del self.last_regime_override[asset]
        
        return len(expired_assets)
    
    def get_enhanced_configuration_summary(self) -> Dict:
        """
        Get enhanced configuration summary including regime override settings.
        
        Returns:
            Dict with enhanced configuration parameters
        """
        base_config = super().get_configuration_summary()
        
        regime_config = {
            'regime_override_enabled': True,
            'regime_override_cooldown_days': self.regime_override_cooldown,
            'regime_override_severity_threshold': 'high or critical',
            'regime_override_proximity_threshold': '2 days from min holding',
            'active_regime_overrides': len(self.last_regime_override),
            'regime_override_types_supported': ['high', 'critical']
        }
        
        return {**base_config, **regime_config} 