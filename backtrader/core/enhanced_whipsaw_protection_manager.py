"""
Enhanced Whipsaw Protection Manager with comprehensive event logging.

Extends the base WhipsawProtectionManager with detailed event tracking for:
- All protection decisions (allow/block)
- Position lifecycle events (open/close)
- Cycle detection and analysis
- Protection status changes
- Performance metrics
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import time

from .whipsaw_protection_manager import WhipsawProtectionManager, PositionEvent, WhipsawCycle
from ..monitoring.event_writer import EventWriter, get_event_writer


class EnhancedWhipsawProtectionManager(WhipsawProtectionManager):
    """
    Enhanced whipsaw protection manager with comprehensive event logging.
    
    Extends base functionality with:
    - Detailed event logging for all protection decisions
    - Complete audit trail of position lifecycle events
    - Cycle detection and analysis with event tracking
    - Protection status monitoring and alerts
    - Performance metrics and reporting
    """
    
    def __init__(self, 
                 max_cycles_per_period: int = 1, 
                 protection_period_days: int = 14,
                 min_position_duration_hours: int = 4,
                 event_writer: EventWriter = None):
        """
        Initialize enhanced whipsaw protection manager.
        
        Args:
            max_cycles_per_period: Maximum complete cycles allowed per protection period
            protection_period_days: Protection period length in days
            min_position_duration_hours: Minimum hours position must be held before closure
            event_writer: Event writer for logging (optional, will use global if not provided)
        """
        super().__init__(max_cycles_per_period, protection_period_days, min_position_duration_hours)
        
        # Event logging
        self.event_writer = event_writer or get_event_writer()
        
        # Performance tracking
        self.protection_checks_count = 0
        self.positions_blocked = 0
        self.positions_allowed = 0
        
        # Log initialization
        self.event_writer.log_event(
            event_type='whipsaw_protection_init',
            event_category='protection',
            action='init',
            reason='Enhanced whipsaw protection manager initialized',
            metadata={
                'max_cycles_per_period': max_cycles_per_period,
                'protection_period_days': protection_period_days,
                'min_position_duration_hours': min_position_duration_hours,
                'protection_type': 'whipsaw'
            }
        )
    
    def can_open_position(self, asset: str, current_date: datetime) -> Tuple[bool, str]:
        """
        Check if opening position would violate whipsaw protection with event logging.
        
        Args:
            asset: Asset symbol
            current_date: Current date/time
            
        Returns:
            Tuple of (can_open: bool, reason: str)
        """
        self.protection_checks_count += 1
        check_start_time = time.time()
        
        try:
            # Use parent logic for actual check
            can_open, reason = super().can_open_position(asset, current_date)
            
            check_execution_time = (time.time() - check_start_time) * 1000
            
            # Count statistics
            if can_open:
                self.positions_allowed += 1
                action = 'allow'
                event_reason = f'Position opening allowed: {reason}'
            else:
                self.positions_blocked += 1
                action = 'block'
                event_reason = f'Position opening blocked: {reason}'
            
            # Get cycle statistics for metadata
            recent_cycles = self._count_recent_cycles(asset, current_date)
            days_until_reset = self._days_until_protection_reset(asset, current_date)
            
            # Log protection decision
            self.event_writer.log_protection_event(
                protection_type='whipsaw',
                asset=asset,
                action=action,
                reason=event_reason,
                metadata={
                    'can_open': can_open,
                    'recent_cycles': recent_cycles,
                    'max_cycles': self.max_cycles_per_period,
                    'protection_period_days': self.protection_period_days,
                    'days_until_reset': days_until_reset,
                    'position_already_open': asset in self.active_positions,
                    'execution_time_ms': check_execution_time,
                    'total_checks': self.protection_checks_count
                }
            )
            
            return can_open, reason
            
        except Exception as e:
            check_execution_time = (time.time() - check_start_time) * 1000
            
            # Log error
            self.event_writer.log_error(
                error_type='whipsaw_protection_check',
                error_message=f'Whipsaw protection check failed for {asset}: {str(e)}',
                asset=asset,
                metadata={
                    'execution_time_ms': check_execution_time,
                    'current_date': current_date.isoformat(),
                    'error_type': type(e).__name__
                }
            )
            
            # Default to blocking on error (conservative approach)
            return False, f"Protection check failed: {str(e)}"
    
    def can_close_position(self, asset: str, open_date: datetime, 
                          current_date: datetime) -> Tuple[bool, str]:
        """
        Check if closing position would create whipsaw with event logging.
        
        Args:
            asset: Asset symbol
            open_date: When position was opened
            current_date: Current date/time
            
        Returns:
            Tuple of (can_close: bool, reason: str)
        """
        self.protection_checks_count += 1
        check_start_time = time.time()
        
        try:
            # Use parent logic for actual check
            can_close, reason = super().can_close_position(asset, open_date, current_date)
            
            check_execution_time = (time.time() - check_start_time) * 1000
            
            # Calculate position duration
            position_duration = current_date - open_date
            position_duration_hours = position_duration.total_seconds() / 3600
            
            # Determine action
            if can_close:
                action = 'allow'
                event_reason = f'Position closing allowed: {reason}'
            else:
                action = 'block'
                event_reason = f'Position closing blocked: {reason}'
                self.positions_blocked += 1
            
            # Log protection decision
            self.event_writer.log_protection_event(
                protection_type='whipsaw',
                asset=asset,
                action=action,
                reason=event_reason,
                metadata={
                    'can_close': can_close,
                    'position_duration_hours': position_duration_hours,
                    'min_duration_hours': self.min_position_duration_hours,
                    'open_date': open_date.isoformat(),
                    'duration_check_passed': position_duration_hours >= self.min_position_duration_hours,
                    'execution_time_ms': check_execution_time,
                    'total_checks': self.protection_checks_count
                }
            )
            
            return can_close, reason
            
        except Exception as e:
            check_execution_time = (time.time() - check_start_time) * 1000
            
            # Log error
            self.event_writer.log_error(
                error_type='whipsaw_protection_check',
                error_message=f'Whipsaw position close check failed for {asset}: {str(e)}',
                asset=asset,
                metadata={
                    'execution_time_ms': check_execution_time,
                    'open_date': open_date.isoformat(),
                    'current_date': current_date.isoformat(),
                    'error_type': type(e).__name__
                }
            )
            
            # Default to blocking on error
            return False, f"Protection check failed: {str(e)}"
    
    def record_position_event(self, asset: str, event_type: str, 
                            event_date: datetime, position_size: float = 0.0,
                            reason: str = "", price: float = None):
        """
        Record position open/close events with comprehensive logging.
        
        Args:
            asset: Asset symbol
            event_type: 'open' or 'close'
            event_date: When the event occurred
            position_size: Size of the position
            reason: Reason for the action
            price: Price at which position was opened/closed (optional)
        """
        record_start_time = time.time()
        
        try:
            # Use parent logic for actual recording
            super().record_position_event(asset, event_type, event_date, position_size, reason)
            
            record_execution_time = (time.time() - record_start_time) * 1000
            
            # Log the position event
            self.event_writer.log_event(
                event_type=f'whipsaw_position_{event_type}',
                event_category='protection',
                action=event_type,
                reason=f'Whipsaw protection recorded position {event_type}: {reason}',
                asset=asset,
                size_after=position_size if event_type == 'open' else 0.0,
                size_before=position_size if event_type == 'close' else 0.0,
                execution_time_ms=record_execution_time,
                metadata={
                    'event_type': event_type,
                    'position_size': position_size,
                    'price': price,
                    'reason': reason,
                    'event_date': event_date.isoformat(),
                    'active_positions_count': len(self.active_positions),
                    'total_events_for_asset': len(self.position_history[asset])
                }
            )
            
            # Check for cycle completion and log if cycle detected
            if event_type == 'close':
                self._check_and_log_cycle_completion(asset, event_date)
            
        except Exception as e:
            record_execution_time = (time.time() - record_start_time) * 1000
            
            self.event_writer.log_error(
                error_type='whipsaw_event_recording',
                error_message=f'Failed to record whipsaw event for {asset}: {str(e)}',
                asset=asset,
                metadata={
                    'event_type': event_type,
                    'execution_time_ms': record_execution_time,
                    'position_size': position_size,
                    'error_type': type(e).__name__
                }
            )
            raise
    
    def _check_and_log_cycle_completion(self, asset: str, close_date: datetime):
        """Check if a whipsaw cycle was completed and log it"""
        
        # Find the most recent open event for this asset
        asset_events = self.position_history[asset]
        if len(asset_events) < 2:
            return
        
        # Look for the matching open event (working backwards)
        close_event = None
        open_event = None
        
        for event in reversed(asset_events):
            if event.event_type == 'close' and close_event is None:
                close_event = event
            elif event.event_type == 'open' and close_event is not None:
                open_event = event
                break
        
        if open_event and close_event:
            # Calculate cycle duration
            cycle_duration = close_date - open_event.date
            cycle_duration_hours = cycle_duration.total_seconds() / 3600
            
            # Create cycle object
            cycle = WhipsawCycle(
                asset=asset,
                open_event=open_event,
                close_event=close_event,
                cycle_duration_hours=cycle_duration_hours,
                size_traded=open_event.size
            )
            
            # Log cycle completion
            self.event_writer.log_event(
                event_type='whipsaw_cycle_complete',
                event_category='protection',
                action='cycle_complete',
                reason=f'Whipsaw cycle completed for {asset}',
                asset=asset,
                metadata={
                    'cycle_duration_hours': cycle_duration_hours,
                    'cycle_duration_days': cycle.cycle_duration_days,
                    'size_traded': cycle.size_traded,
                    'open_date': open_event.date.isoformat(),
                    'close_date': close_event.date.isoformat(),
                    'open_reason': open_event.reason,
                    'close_reason': close_event.reason,
                    'is_rapid_cycle': cycle_duration_hours < 24,  # Flag rapid cycles
                    'recent_cycles_count': self._count_recent_cycles(asset, close_date)
                }
            )
    
    def get_whipsaw_report(self, assets: List[str], current_date: datetime) -> Dict:
        """
        Generate comprehensive whipsaw protection status report with event logging.
        
        Args:
            assets: List of assets to report on
            current_date: Current date for analysis
            
        Returns:
            Dictionary containing whipsaw protection status for all assets
        """
        report_start_time = time.time()
        
        try:
            # Use parent logic for actual report generation
            report = super().get_whipsaw_report(assets, current_date)
            
            report_execution_time = (time.time() - report_start_time) * 1000
            
            # Enhance report with performance statistics
            enhanced_report = {
                **report,
                'performance_stats': {
                    'total_protection_checks': self.protection_checks_count,
                    'positions_blocked': self.positions_blocked,
                    'positions_allowed': self.positions_allowed,
                    'block_rate': self.positions_blocked / max(self.protection_checks_count, 1),
                    'allow_rate': self.positions_allowed / max(self.protection_checks_count, 1)
                },
                'configuration': {
                    'max_cycles_per_period': self.max_cycles_per_period,
                    'protection_period_days': self.protection_period_days,
                    'min_position_duration_hours': self.min_position_duration_hours
                }
            }
            
            # Calculate summary statistics
            protected_assets = sum(1 for asset_data in report.values() 
                                 if isinstance(asset_data, dict) and not asset_data.get('can_trade', True))
            
            # Log report generation
            self.event_writer.log_event(
                event_type='whipsaw_report_generated',
                event_category='protection',
                action='report',
                reason=f'Whipsaw protection report generated for {len(assets)} assets',
                execution_time_ms=report_execution_time,
                metadata={
                    'assets_count': len(assets),
                    'protected_assets_count': protected_assets,
                    'total_active_positions': len(self.active_positions),
                    'report_execution_time_ms': report_execution_time,
                    'performance_stats': enhanced_report['performance_stats']
                }
            )
            
            return enhanced_report
            
        except Exception as e:
            report_execution_time = (time.time() - report_start_time) * 1000
            
            self.event_writer.log_error(
                error_type='whipsaw_report_generation',
                error_message=f'Whipsaw report generation failed: {str(e)}',
                metadata={
                    'assets_count': len(assets),
                    'execution_time_ms': report_execution_time,
                    'error_type': type(e).__name__
                }
            )
            raise
    
    def cleanup_old_events(self, current_date: datetime, cleanup_days: int = None) -> int:
        """
        Clean up old position events with logging.
        
        Args:
            current_date: Current date
            cleanup_days: Days of history to keep (defaults to 2x protection period)
            
        Returns:
            Number of events cleaned up
        """
        cleanup_start_time = time.time()
        
        try:
            if cleanup_days is None:
                cleanup_days = self.protection_period_days * 2
            
            cutoff_date = current_date - timedelta(days=cleanup_days)
            total_cleaned = 0
            
            for asset in list(self.position_history.keys()):
                initial_count = len(self.position_history[asset])
                
                # Keep only events after cutoff date
                self.position_history[asset] = [
                    event for event in self.position_history[asset]
                    if event.date > cutoff_date
                ]
                
                cleaned_count = initial_count - len(self.position_history[asset])
                total_cleaned += cleaned_count
                
                # Remove empty lists
                if not self.position_history[asset]:
                    del self.position_history[asset]
            
            cleanup_execution_time = (time.time() - cleanup_start_time) * 1000
            
            # Log cleanup activity
            self.event_writer.log_event(
                event_type='whipsaw_cleanup',
                event_category='protection',
                action='cleanup',
                reason=f'Whipsaw protection cleanup completed: {total_cleaned} events removed',
                execution_time_ms=cleanup_execution_time,
                metadata={
                    'events_cleaned': total_cleaned,
                    'cleanup_days': cleanup_days,
                    'cutoff_date': cutoff_date.isoformat(),
                    'assets_remaining': len(self.position_history),
                    'cleanup_execution_time_ms': cleanup_execution_time
                }
            )
            
            return total_cleaned
            
        except Exception as e:
            cleanup_execution_time = (time.time() - cleanup_start_time) * 1000
            
            self.event_writer.log_error(
                error_type='whipsaw_cleanup',
                error_message=f'Whipsaw cleanup failed: {str(e)}',
                metadata={
                    'cleanup_days': cleanup_days,
                    'execution_time_ms': cleanup_execution_time,
                    'error_type': type(e).__name__
                }
            )
            raise
    
    def get_performance_statistics(self) -> Dict:
        """Get performance statistics for whipsaw protection"""
        
        return {
            'total_checks': self.protection_checks_count,
            'positions_blocked': self.positions_blocked,
            'positions_allowed': self.positions_allowed,
            'block_rate': self.positions_blocked / max(self.protection_checks_count, 1),
            'allow_rate': self.positions_allowed / max(self.protection_checks_count, 1),
            'active_positions': len(self.active_positions),
            'tracked_assets': len(self.position_history),
            'configuration': {
                'max_cycles_per_period': self.max_cycles_per_period,
                'protection_period_days': self.protection_period_days,
                'min_position_duration_hours': self.min_position_duration_hours
            }
        }