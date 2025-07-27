"""
Enhanced Grace Period Manager with comprehensive event logging.

Extends the base GracePeriodManager with detailed event tracking for:
- Grace period entries and exits
- Position size decay events
- Grace period decisions and overrides
- Protection status monitoring
- Core asset exemptions
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time

from .grace_period_manager import GracePeriodManager, GracePosition
from ..monitoring.event_writer import EventWriter, get_event_writer


class EnhancedGracePeriodManager(GracePeriodManager):
    """
    Enhanced grace period manager with comprehensive event logging.
    
    Extends base functionality with:
    - Detailed event logging for all grace period decisions
    - Complete audit trail of position size decay
    - Grace period lifecycle tracking
    - Core asset exemption logging
    - Performance metrics and monitoring
    """
    
    def __init__(self, grace_period_days: int = 3, decay_rate: float = 0.8, 
                 min_decay_factor: float = 0.1, core_asset_manager=None,
                 event_writer: EventWriter = None):
        """
        Initialize enhanced grace period manager.
        
        Args:
            grace_period_days: Number of days for grace period
            decay_rate: Daily decay rate for position size
            min_decay_factor: Minimum decay factor (position won't decay below this)
            core_asset_manager: Core asset manager for exemptions
            event_writer: Event writer for logging
        """
        super().__init__(grace_period_days, decay_rate, min_decay_factor, core_asset_manager)
        
        # Event logging
        self.event_writer = event_writer or get_event_writer()
        
        # Performance tracking
        self.grace_checks_count = 0
        self.grace_entries = 0
        self.grace_exits = 0
        self.decay_applications = 0
        self.core_asset_exemptions = 0
        
        # Log initialization
        self.event_writer.log_event(
            event_type='grace_period_manager_init',
            event_category='protection',
            action='init',
            reason='Enhanced grace period manager initialized',
            metadata={
                'grace_period_days': grace_period_days,
                'decay_rate': decay_rate,
                'min_decay_factor': min_decay_factor,
                'core_asset_manager_enabled': core_asset_manager is not None,
                'protection_type': 'grace_period'
            }
        )
    
    def should_apply_grace_period(self, asset: str, current_score: float, 
                                threshold: float, current_date: datetime) -> Tuple[bool, str]:
        """
        Determine if grace period should be applied with event logging.
        
        Args:
            asset: Asset symbol
            current_score: Current asset score
            threshold: Score threshold
            current_date: Current date
            
        Returns:
            Tuple of (should_apply: bool, reason: str)
        """
        self.grace_checks_count += 1
        check_start_time = time.time()
        
        try:
            # Check core asset exemption first
            is_core_exempt = False
            if self.core_asset_manager:
                is_core_exempt = self.core_asset_manager.should_exempt_from_grace(asset, current_date)
                if is_core_exempt:
                    self.core_asset_exemptions += 1
            
            # Use parent logic for actual grace period logic
            should_apply, reason = super().should_apply_grace_period(asset, current_score, threshold, current_date)
            
            check_execution_time = (time.time() - check_start_time) * 1000
            
            # Determine final decision accounting for core asset exemption
            if is_core_exempt and should_apply:
                final_should_apply = False
                final_reason = f"Core asset exemption: {reason}"
            else:
                final_should_apply = should_apply
                final_reason = reason
            
            # Log grace period decision
            self.event_writer.log_protection_event(
                protection_type='grace_period',
                asset=asset,
                action='check' if not final_should_apply else 'apply',
                reason=f'Grace period check: {final_reason}',
                metadata={
                    'should_apply_grace': final_should_apply,
                    'current_score': current_score,
                    'threshold': threshold,
                    'score_below_threshold': current_score < threshold,
                    'is_core_asset': is_core_exempt,
                    'already_in_grace': asset in self.grace_positions,
                    'execution_time_ms': check_execution_time,
                    'total_checks': self.grace_checks_count,
                    'reason': final_reason
                }
            )
            
            return final_should_apply, final_reason
            
        except Exception as e:
            check_execution_time = (time.time() - check_start_time) * 1000
            
            self.event_writer.log_error(
                error_type='grace_period_check',
                error_message=f'Grace period check failed for {asset}: {str(e)}',
                asset=asset,
                metadata={
                    'current_score': current_score,
                    'threshold': threshold,
                    'execution_time_ms': check_execution_time,
                    'error_type': type(e).__name__
                }
            )
            
            # Default to not applying grace period on error
            return False, f"Grace period check failed: {str(e)}"
    
    def start_grace_period(self, asset: str, current_score: float, current_size: float,
                          current_date: datetime, reason: str = "Score below threshold") -> bool:
        """
        Start grace period for an asset with event logging.
        
        Args:
            asset: Asset symbol
            current_score: Current asset score
            current_size: Current position size
            current_date: Current date
            reason: Reason for starting grace period
            
        Returns:
            True if grace period started, False if already in grace period
        """
        start_time = time.time()
        
        try:
            # Check if already in grace period
            if asset in self.grace_positions:
                self.event_writer.log_protection_event(
                    protection_type='grace_period',
                    asset=asset,
                    action='already_active',
                    reason=f'Grace period already active for {asset}',
                    metadata={
                        'current_score': current_score,
                        'current_size': current_size,
                        'existing_grace_start': self.grace_positions[asset].start_date.isoformat(),
                        'days_in_grace': (current_date - self.grace_positions[asset].start_date).days
                    }
                )
                return False
            
            # Start grace period using parent logic
            success = super().start_grace_period(asset, current_score, current_size, current_date, reason)
            
            execution_time = (time.time() - start_time) * 1000
            
            if success:
                self.grace_entries += 1
                
                # Log grace period start
                self.event_writer.log_event(
                    event_type='grace_period_start',
                    event_category='protection',
                    action='start',
                    reason=f'Grace period started for {asset}: {reason}',
                    asset=asset,
                    score_before=current_score,
                    size_before=current_size,
                    execution_time_ms=execution_time,
                    metadata={
                        'grace_period_days': self.grace_period_days,
                        'decay_rate': self.decay_rate,
                        'min_decay_factor': self.min_decay_factor,
                        'start_score': current_score,
                        'start_size': current_size,
                        'start_reason': reason,
                        'total_grace_entries': self.grace_entries,
                        'active_grace_positions': len(self.grace_positions)
                    }
                )
            
            return success
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            self.event_writer.log_error(
                error_type='grace_period_start',
                error_message=f'Failed to start grace period for {asset}: {str(e)}',
                asset=asset,
                metadata={
                    'current_score': current_score,
                    'current_size': current_size,
                    'execution_time_ms': execution_time,
                    'error_type': type(e).__name__
                }
            )
            return False
    
    def end_grace_period(self, asset: str, current_date: datetime, 
                        reason: str = "Grace period expired") -> bool:
        """
        End grace period for an asset with event logging.
        
        Args:
            asset: Asset symbol
            current_date: Current date
            reason: Reason for ending grace period
            
        Returns:
            True if grace period ended, False if asset wasn't in grace period
        """
        end_start_time = time.time()
        
        try:
            # Check if asset is in grace period
            if asset not in self.grace_positions:
                self.event_writer.log_protection_event(
                    protection_type='grace_period',
                    asset=asset,
                    action='not_active',
                    reason=f'Cannot end grace period - {asset} not in grace period',
                    metadata={'reason': reason}
                )
                return False
            
            # Get grace position info before ending
            grace_position = self.grace_positions[asset]
            days_in_grace = (current_date - grace_position.start_date).days
            final_size = grace_position.current_size
            original_size = grace_position.original_size
            total_decay = (original_size - final_size) / original_size if original_size > 0 else 0
            
            # End grace period using parent logic
            success = super().end_grace_period(asset, current_date, reason)
            
            execution_time = (time.time() - end_start_time) * 1000
            
            if success:
                self.grace_exits += 1
                
                # Log grace period end
                self.event_writer.log_event(
                    event_type='grace_period_end',
                    event_category='protection',
                    action='end',
                    reason=f'Grace period ended for {asset}: {reason}',
                    asset=asset,
                    size_before=final_size,
                    size_after=0.0,  # Position typically closed after grace period
                    execution_time_ms=execution_time,
                    metadata={
                        'days_in_grace': days_in_grace,
                        'original_size': original_size,
                        'final_size': final_size,
                        'total_decay_percentage': total_decay,
                        'end_reason': reason,
                        'grace_period_days': self.grace_period_days,
                        'total_grace_exits': self.grace_exits,
                        'remaining_grace_positions': len(self.grace_positions) - 1
                    }
                )
            
            return success
            
        except Exception as e:
            execution_time = (time.time() - end_start_time) * 1000
            
            self.event_writer.log_error(
                error_type='grace_period_end',
                error_message=f'Failed to end grace period for {asset}: {str(e)}',
                asset=asset,
                metadata={
                    'execution_time_ms': execution_time,
                    'reason': reason,
                    'error_type': type(e).__name__
                }
            )
            return False
    
    def apply_decay(self, asset: str, current_date: datetime) -> Tuple[float, str]:
        """
        Apply decay to grace period position with event logging.
        
        Args:
            asset: Asset symbol
            current_date: Current date
            
        Returns:
            Tuple of (new_size: float, reason: str)
        """
        decay_start_time = time.time()
        
        try:
            # Check if asset is in grace period
            if asset not in self.grace_positions:
                return 0.0, f"{asset} not in grace period"
            
            grace_position = self.grace_positions[asset]
            old_size = grace_position.current_size
            
            # Apply decay using parent logic
            new_size, reason = super().apply_decay(asset, current_date)
            
            execution_time = (time.time() - decay_start_time) * 1000
            
            # Calculate decay statistics
            decay_amount = old_size - new_size
            decay_percentage = decay_amount / old_size if old_size > 0 else 0
            days_in_grace = (current_date - grace_position.start_date).days
            
            if decay_amount > 0:
                self.decay_applications += 1
                
                # Log position decay
                self.event_writer.log_event(
                    event_type='position_decay',
                    event_category='portfolio',
                    action='decay',
                    reason=f'Grace period decay applied to {asset}: {reason}',
                    asset=asset,
                    size_before=old_size,
                    size_after=new_size,
                    execution_time_ms=execution_time,
                    metadata={
                        'days_in_grace': days_in_grace,
                        'decay_amount': decay_amount,
                        'decay_percentage': decay_percentage,
                        'decay_rate': self.decay_rate,
                        'original_size': grace_position.original_size,
                        'total_decay_applications': self.decay_applications,
                        'at_min_decay_factor': new_size <= (grace_position.original_size * self.min_decay_factor)
                    }
                )
            
            return new_size, reason
            
        except Exception as e:
            execution_time = (time.time() - decay_start_time) * 1000
            
            self.event_writer.log_error(
                error_type='grace_period_decay',
                error_message=f'Failed to apply decay for {asset}: {str(e)}',
                asset=asset,
                metadata={
                    'execution_time_ms': execution_time,
                    'error_type': type(e).__name__
                }
            )
            return 0.0, f"Decay failed: {str(e)}"
    
    def get_all_grace_positions(self, current_date: datetime) -> Dict[str, Dict]:
        """
        Get all grace positions with enhanced information and event logging.
        
        Args:
            current_date: Current date for calculations
            
        Returns:
            Dictionary of asset -> grace position info
        """
        report_start_time = time.time()
        
        try:
            # Use parent logic for basic grace positions
            grace_positions_info = super().get_all_grace_positions(current_date)
            
            execution_time = (time.time() - report_start_time) * 1000
            
            # Enhance with additional statistics
            enhanced_info = {}
            for asset, info in grace_positions_info.items():
                grace_position = self.grace_positions.get(asset)
                if grace_position:
                    enhanced_info[asset] = {
                        **info,
                        'total_decay_percentage': (grace_position.original_size - grace_position.current_size) / grace_position.original_size,
                        'decay_rate': self.decay_rate,
                        'min_decay_factor': self.min_decay_factor,
                        'is_at_min_decay': grace_position.current_size <= (grace_position.original_size * self.min_decay_factor)
                    }
            
            # Log grace positions report
            self.event_writer.log_event(
                event_type='grace_positions_report',
                event_category='protection',
                action='report',
                reason=f'Grace positions report generated: {len(enhanced_info)} positions',
                execution_time_ms=execution_time,
                metadata={
                    'active_grace_positions': len(enhanced_info),
                    'performance_stats': self.get_performance_statistics(),
                    'report_execution_time_ms': execution_time
                }
            )
            
            return enhanced_info
            
        except Exception as e:
            execution_time = (time.time() - report_start_time) * 1000
            
            self.event_writer.log_error(
                error_type='grace_positions_report',
                error_message=f'Failed to generate grace positions report: {str(e)}',
                metadata={
                    'execution_time_ms': execution_time,
                    'error_type': type(e).__name__
                }
            )
            return {}
    
    def cleanup_expired_positions(self, current_date: datetime) -> List[str]:
        """
        Clean up expired grace positions with event logging.
        
        Args:
            current_date: Current date
            
        Returns:
            List of assets that had expired grace periods cleaned up
        """
        cleanup_start_time = time.time()
        
        try:
            # Use parent logic for cleanup
            expired_assets = super().cleanup_expired_positions(current_date)
            
            execution_time = (time.time() - cleanup_start_time) * 1000
            
            # Log cleanup activity
            if expired_assets:
                self.event_writer.log_event(
                    event_type='grace_period_cleanup',
                    event_category='protection',
                    action='cleanup',
                    reason=f'Grace period cleanup completed: {len(expired_assets)} expired positions',
                    execution_time_ms=execution_time,
                    metadata={
                        'expired_assets': expired_assets,
                        'expired_count': len(expired_assets),
                        'remaining_grace_positions': len(self.grace_positions),
                        'cleanup_execution_time_ms': execution_time
                    }
                )
            
            return expired_assets
            
        except Exception as e:
            execution_time = (time.time() - cleanup_start_time) * 1000
            
            self.event_writer.log_error(
                error_type='grace_period_cleanup',
                error_message=f'Grace period cleanup failed: {str(e)}',
                metadata={
                    'execution_time_ms': execution_time,
                    'error_type': type(e).__name__
                }
            )
            return []
    
    def get_performance_statistics(self) -> Dict:
        """Get performance statistics for grace period management"""
        
        return {
            'total_checks': self.grace_checks_count,
            'grace_entries': self.grace_entries,
            'grace_exits': self.grace_exits,
            'decay_applications': self.decay_applications,
            'core_asset_exemptions': self.core_asset_exemptions,
            'active_grace_positions': len(self.grace_positions),
            'configuration': {
                'grace_period_days': self.grace_period_days,
                'decay_rate': self.decay_rate,
                'min_decay_factor': self.min_decay_factor
            }
        }