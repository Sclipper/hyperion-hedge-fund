"""
Grace Period Manager for intelligent position lifecycle management.

This module implements professional-grade grace period management that prevents
whipsaw trading by allowing underperforming positions to decay gradually 
rather than being closed immediately.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional
import math


@dataclass
class GracePosition:
    """Metadata for a position in grace period"""
    asset: str
    start_date: datetime
    original_size: float
    original_score: float
    current_size: float
    decay_applied: float
    reason: str


@dataclass  
class GraceAction:
    """Action to take for a position based on grace period analysis"""
    action: str  # 'grace_start', 'grace_decay', 'grace_recovery', 'force_close', 'hold'
    new_size: float = 0.0
    reason: str = ""
    days_in_grace: int = 0
    recovery_detected: bool = False
    force_close_triggered: bool = False


class GracePeriodManager:
    """
    Intelligent grace period management for underperforming positions.
    
    Prevents whipsaw trading by allowing positions below threshold to decay
    gradually over a configurable grace period rather than immediate closure.
    
    Key Features:
    - Configurable grace period length (default: 5 days)
    - Exponential decay with configurable rate (default: 0.8 daily)
    - Minimum decay factor to prevent positions going to zero
    - Score recovery detection for grace period exit
    - Complete audit trail of grace period decisions
    """
    
    def __init__(self, 
                 grace_period_days: int = 5, 
                 decay_rate: float = 0.8, 
                 min_decay_factor: float = 0.1):
        """
        Initialize grace period manager.
        
        Args:
            grace_period_days: Maximum days a position can remain in grace period
            decay_rate: Daily decay rate for position size (0.8 = 20% decay per day)
            min_decay_factor: Minimum size factor (0.1 = position can't go below 10% of original)
        """
        self.grace_period_days = grace_period_days
        self.decay_rate = decay_rate
        self.min_decay_factor = min_decay_factor
        self.grace_positions: Dict[str, GracePosition] = {}
        
        # Validation
        if not (1 <= grace_period_days <= 30):
            raise ValueError(f"grace_period_days must be 1-30, got {grace_period_days}")
        if not (0.1 <= decay_rate <= 1.0):
            raise ValueError(f"decay_rate must be 0.1-1.0, got {decay_rate}")
        if not (0.01 <= min_decay_factor <= 0.5):
            raise ValueError(f"min_decay_factor must be 0.01-0.5, got {min_decay_factor}")
    
    def handle_underperforming_position(self, 
                                      asset: str, 
                                      current_score: float, 
                                      current_size: float, 
                                      min_threshold: float,
                                      current_date: datetime) -> GraceAction:
        """
        Handle positions that fall below threshold with grace period logic.
        
        Args:
            asset: Asset symbol
            current_score: Current combined score
            current_size: Current position size (as percentage)
            min_threshold: Minimum score threshold
            current_date: Current date for calculations
            
        Returns:
            GraceAction: Action to take based on grace period analysis
        """
        # Check if score is above threshold (no grace period needed)
        if current_score >= min_threshold:
            if asset in self.grace_positions:
                # Score recovered - exit grace period
                return self._handle_score_recovery(asset, current_score, current_size, current_date)
            else:
                # Normal position, no action needed
                return GraceAction(
                    action='hold',
                    new_size=current_size,
                    reason=f'Score above threshold: {current_score:.3f} >= {min_threshold:.3f}'
                )
        
        # Score is below threshold - grace period logic
        if asset not in self.grace_positions:
            # Start new grace period
            return self._start_grace_period(asset, current_score, current_size, 
                                          min_threshold, current_date)
        else:
            # Continue existing grace period
            return self._continue_grace_period(asset, current_score, current_size, 
                                             min_threshold, current_date)
    
    def _start_grace_period(self, 
                           asset: str, 
                           current_score: float, 
                           current_size: float,
                           min_threshold: float, 
                           current_date: datetime) -> GraceAction:
        """Start a new grace period for an underperforming position."""
        grace_position = GracePosition(
            asset=asset,
            start_date=current_date,
            original_size=current_size,
            original_score=current_score,
            current_size=current_size,
            decay_applied=0.0,
            reason=f'Score below threshold: {current_score:.3f} < {min_threshold:.3f}'
        )
        
        self.grace_positions[asset] = grace_position
        
        return GraceAction(
            action='grace_start',
            new_size=current_size,
            reason=f'Starting grace period: score {current_score:.3f} < threshold {min_threshold:.3f}',
            days_in_grace=0
        )
    
    def _continue_grace_period(self, 
                              asset: str, 
                              current_score: float, 
                              current_size: float,
                              min_threshold: float, 
                              current_date: datetime) -> GraceAction:
        """Continue existing grace period with decay or closure."""
        grace_pos = self.grace_positions[asset]
        days_in_grace = (current_date - grace_pos.start_date).days
        
        # Check if grace period has expired
        if days_in_grace >= self.grace_period_days:
            return self._force_close_position(asset, current_score, days_in_grace, current_date)
        
        # Apply decay to position size
        new_size = self._calculate_decayed_size(grace_pos, days_in_grace)
        
        # Update grace position
        grace_pos.current_size = new_size
        grace_pos.decay_applied = grace_pos.original_size - new_size
        
        return GraceAction(
            action='grace_decay',
            new_size=new_size,
            reason=f'Grace period day {days_in_grace}/{self.grace_period_days}: '
                   f'size decaying to {new_size:.3f} (decay rate: {self.decay_rate})',
            days_in_grace=days_in_grace
        )
    
    def _handle_score_recovery(self, 
                              asset: str, 
                              current_score: float, 
                              current_size: float,
                              current_date: datetime) -> GraceAction:
        """Handle position recovery during grace period."""
        grace_pos = self.grace_positions[asset]
        days_in_grace = (current_date - grace_pos.start_date).days
        
        # Remove from grace period
        del self.grace_positions[asset]
        
        return GraceAction(
            action='grace_recovery',
            new_size=current_size,  # Keep current size, don't restore to original
            reason=f'Score recovered above threshold after {days_in_grace} days in grace period',
            days_in_grace=days_in_grace,
            recovery_detected=True
        )
    
    def _force_close_position(self, 
                             asset: str, 
                             current_score: float, 
                             days_in_grace: int,
                             current_date: datetime) -> GraceAction:
        """Force close position after grace period expiry."""
        # Remove from grace period tracking
        del self.grace_positions[asset]
        
        return GraceAction(
            action='force_close',
            new_size=0.0,
            reason=f'Grace period expired after {days_in_grace} days, forcing closure '
                   f'(score still {current_score:.3f})',
            days_in_grace=days_in_grace,
            force_close_triggered=True
        )
    
    def _calculate_decayed_size(self, grace_pos: GracePosition, days_in_grace: int) -> float:
        """
        Calculate decayed position size using exponential decay.
        
        Formula: new_size = original_size * (decay_rate ^ days_in_grace)
        With minimum floor to prevent position going to zero.
        """
        # Exponential decay: size * (decay_rate ^ days)
        decay_factor = self.decay_rate ** days_in_grace
        
        # Apply minimum decay factor floor
        decay_factor = max(decay_factor, self.min_decay_factor)
        
        decayed_size = grace_pos.original_size * decay_factor
        
        return round(decayed_size, 6)  # Round to avoid floating point precision issues
    
    def apply_grace_decay(self, asset: str, current_date: datetime) -> Optional[float]:
        """
        Apply daily decay to position size during grace period.
        
        Args:
            asset: Asset symbol
            current_date: Current date
            
        Returns:
            New position size after decay, or None if not in grace period
        """
        if asset not in self.grace_positions:
            return None
        
        grace_pos = self.grace_positions[asset]
        days_in_grace = (current_date - grace_pos.start_date).days
        
        new_size = self._calculate_decayed_size(grace_pos, days_in_grace)
        grace_pos.current_size = new_size
        grace_pos.decay_applied = grace_pos.original_size - new_size
        
        return new_size
    
    def is_in_grace_period(self, asset: str, current_date: datetime = None) -> bool:
        """
        Check if asset is currently in grace period.
        
        Args:
            asset: Asset symbol
            current_date: Current date (optional, for expiry checking)
            
        Returns:
            True if asset is in grace period and not expired
        """
        if asset not in self.grace_positions:
            return False
        
        if current_date:
            grace_pos = self.grace_positions[asset]
            days_in_grace = (current_date - grace_pos.start_date).days
            
            # Check if grace period has expired
            if days_in_grace >= self.grace_period_days:
                return False
        
        return True
    
    def should_force_close(self, asset: str, current_date: datetime) -> bool:
        """
        Check if grace period has expired and position should be closed.
        
        Args:
            asset: Asset symbol
            current_date: Current date
            
        Returns:
            True if position should be force closed due to grace period expiry
        """
        if asset not in self.grace_positions:
            return False
        
        grace_pos = self.grace_positions[asset]
        days_in_grace = (current_date - grace_pos.start_date).days
        
        return days_in_grace >= self.grace_period_days
    
    def get_grace_status(self, asset: str, current_date: datetime) -> Optional[Dict]:
        """
        Get comprehensive grace period status for an asset.
        
        Args:
            asset: Asset symbol
            current_date: Current date
            
        Returns:
            Dict with grace period status details, or None if not in grace period
        """
        if asset not in self.grace_positions:
            return None
        
        grace_pos = self.grace_positions[asset]
        days_in_grace = (current_date - grace_pos.start_date).days
        days_remaining = max(0, self.grace_period_days - days_in_grace)
        
        return {
            'asset': asset,
            'in_grace_period': True,
            'start_date': grace_pos.start_date,
            'days_in_grace': days_in_grace,
            'days_remaining': days_remaining,
            'original_size': grace_pos.original_size,
            'current_size': grace_pos.current_size,
            'decay_applied': grace_pos.decay_applied,
            'decay_percentage': (grace_pos.decay_applied / grace_pos.original_size) * 100,
            'original_score': grace_pos.original_score,
            'reason': grace_pos.reason,
            'will_expire_today': days_remaining == 0
        }
    
    def get_all_grace_positions(self, current_date: datetime) -> Dict[str, Dict]:
        """
        Get status of all positions currently in grace period.
        
        Args:
            current_date: Current date
            
        Returns:
            Dict mapping asset symbols to their grace period status
        """
        return {
            asset: self.get_grace_status(asset, current_date)
            for asset in self.grace_positions.keys()
        }
    
    def clean_expired_positions(self, current_date: datetime) -> int:
        """
        Remove expired grace positions from tracking.
        
        Args:
            current_date: Current date
            
        Returns:
            Number of expired positions removed
        """
        expired_assets = []
        
        for asset, grace_pos in self.grace_positions.items():
            days_in_grace = (current_date - grace_pos.start_date).days
            if days_in_grace >= self.grace_period_days:
                expired_assets.append(asset)
        
        for asset in expired_assets:
            del self.grace_positions[asset]
        
        return len(expired_assets)
    
    def get_configuration_summary(self) -> Dict:
        """
        Get current grace period manager configuration.
        
        Returns:
            Dict with configuration parameters
        """
        return {
            'grace_period_days': self.grace_period_days,
            'decay_rate': self.decay_rate,
            'min_decay_factor': self.min_decay_factor,
            'active_grace_positions': len(self.grace_positions),
            'decay_formula': f'size * ({self.decay_rate} ^ days_in_grace)',
            'minimum_size_floor': f'{self.min_decay_factor * 100}% of original size'
        } 