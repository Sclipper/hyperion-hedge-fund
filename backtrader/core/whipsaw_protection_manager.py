"""
Whipsaw Protection Manager for preventing rapid position cycling.

This module implements professional-grade whipsaw protection that prevents
rapid opening and closing of positions, reducing transaction costs and
improving trading discipline through quantified protection rules.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from collections import defaultdict


@dataclass
class PositionEvent:
    """Record of a position open/close event"""
    event_type: str  # 'open', 'close'
    date: datetime
    size: float
    reason: str = ""
    price: Optional[float] = None


@dataclass
class WhipsawCycle:
    """Complete whipsaw cycle (open + close)"""
    asset: str
    open_event: PositionEvent
    close_event: PositionEvent
    cycle_duration_hours: float
    size_traded: float
    
    @property
    def cycle_duration_days(self) -> float:
        """Get cycle duration in days."""
        return self.cycle_duration_hours / 24


class WhipsawProtectionManager:
    """
    Quantified whipsaw protection to prevent rapid position cycling.
    
    Implements professional-grade protection against rapid trading:
    - Quantified cycle limits (max cycles per protection period)
    - Minimum position duration enforcement
    - Complete position event tracking and history
    - Cycle analysis and pattern detection
    - Comprehensive whipsaw reporting and alerts
    
    Key Features:
    - Configurable cycle limits (default: 1 cycle per 14 days)
    - Minimum position duration (default: 4 hours)
    - Complete event history with metadata
    - Cycle pattern analysis and detection
    - Protection status reporting for all assets
    - Automatic cleanup of expired events
    """
    
    def __init__(self, 
                 max_cycles_per_period: int = 1, 
                 protection_period_days: int = 14,
                 min_position_duration_hours: int = 4):
        """
        Initialize whipsaw protection manager.
        
        Args:
            max_cycles_per_period: Maximum complete cycles allowed per protection period
            protection_period_days: Protection period length in days
            min_position_duration_hours: Minimum hours position must be held before closure
        """
        self.max_cycles_per_period = max_cycles_per_period
        self.protection_period_days = protection_period_days
        self.min_position_duration_hours = min_position_duration_hours
        self.position_history: Dict[str, List[PositionEvent]] = defaultdict(list)
        self.active_positions: Dict[str, PositionEvent] = {}  # Track currently open positions
        
        # Validation
        if not (1 <= max_cycles_per_period <= 10):
            raise ValueError(f"max_cycles_per_period must be 1-10, got {max_cycles_per_period}")
        if not (1 <= protection_period_days <= 365):
            raise ValueError(f"protection_period_days must be 1-365, got {protection_period_days}")
        if not (1 <= min_position_duration_hours <= 168):  # Max 1 week
            raise ValueError(f"min_position_duration_hours must be 1-168, got {min_position_duration_hours}")
    
    def can_open_position(self, asset: str, current_date: datetime) -> Tuple[bool, str]:
        """
        Check if opening position would violate whipsaw protection.
        
        Args:
            asset: Asset symbol
            current_date: Current date/time
            
        Returns:
            Tuple of (can_open: bool, reason: str)
        """
        # Check if position is already open
        if asset in self.active_positions:
            return False, f"Position already open since {self.active_positions[asset].date}"
        
        # Count recent cycles to check limits
        recent_cycles = self._count_recent_cycles(asset, current_date)
        
        if recent_cycles >= self.max_cycles_per_period:
            last_cycle = self._get_last_complete_cycle(asset, current_date)
            if last_cycle:
                days_until_reset = self._days_until_protection_reset(asset, current_date)
                return False, (f"WHIPSAW PROTECTION: {recent_cycles} cycles in last "
                             f"{self.protection_period_days} days (limit: {self.max_cycles_per_period}). "
                             f"Protection resets in {days_until_reset} days.")
            else:
                return False, f"WHIPSAW PROTECTION: Cycle limit reached ({recent_cycles}/{self.max_cycles_per_period})"
        
        return True, f"Can open position ({recent_cycles}/{self.max_cycles_per_period} recent cycles)"
    
    def can_close_position(self, 
                          asset: str, 
                          open_date: datetime, 
                          current_date: datetime) -> Tuple[bool, str]:
        """
        Check if closing position would create whipsaw (too quick).
        
        Args:
            asset: Asset symbol
            open_date: Date when position was opened
            current_date: Current date/time
            
        Returns:
            Tuple of (can_close: bool, reason: str)
        """
        # Check if position is actually open
        if asset not in self.active_positions:
            return True, "Position not tracked as open, closure allowed"
        
        # Calculate position duration
        position_duration = current_date - open_date
        min_duration = timedelta(hours=self.min_position_duration_hours)
        
        if position_duration < min_duration:
            hours_held = position_duration.total_seconds() / 3600
            hours_required = self.min_position_duration_hours
            return False, (f"WHIPSAW PROTECTION: Position duration {hours_held:.1f}h "
                          f"< minimum {hours_required}h")
        
        return True, f"Minimum duration met ({position_duration})"
    
    def record_position_event(self, 
                            asset: str, 
                            event_type: str, 
                            event_date: datetime, 
                            position_size: float = 0.0,
                            reason: str = "",
                            price: Optional[float] = None):
        """
        Record position open/close events for tracking.
        
        Args:
            asset: Asset symbol
            event_type: 'open' or 'close'
            event_date: Date/time of event
            position_size: Size of position
            reason: Reason for the event
            price: Optional price information
        """
        event = PositionEvent(
            event_type=event_type.lower(),
            date=event_date,
            size=position_size,
            reason=reason,
            price=price
        )
        
        self.position_history[asset].append(event)
        
        # Update active position tracking
        if event_type.lower() == 'open':
            self.active_positions[asset] = event
            print(f"📈 Position opened: {asset} (size: {position_size:.3f}, reason: {reason})")
        elif event_type.lower() == 'close':
            if asset in self.active_positions:
                open_event = self.active_positions[asset]
                duration = event_date - open_event.date
                del self.active_positions[asset]
                print(f"📉 Position closed: {asset} after {duration} "
                      f"(size: {position_size:.3f}, reason: {reason})")
            else:
                print(f"⚠️ Closing untracked position: {asset}")
        
        # Clean old events periodically
        self._clean_old_events(asset, event_date)
    
    def _count_recent_cycles(self, asset: str, current_date: datetime) -> int:
        """
        Count complete open+close cycles in recent protection period.
        
        Args:
            asset: Asset symbol
            current_date: Current date
            
        Returns:
            Number of complete cycles
        """
        cutoff_date = current_date - timedelta(days=self.protection_period_days)
        recent_events = [
            event for event in self.position_history[asset] 
            if event.date > cutoff_date
        ]
        
        # Count complete cycles (open followed by close)
        cycles = 0
        expecting_open = True
        
        for event in sorted(recent_events, key=lambda x: x.date):
            if event.event_type == 'open' and expecting_open:
                expecting_open = False
            elif event.event_type == 'close' and not expecting_open:
                cycles += 1
                expecting_open = True
        
        return cycles
    
    def _get_last_complete_cycle(self, asset: str, current_date: datetime) -> Optional[WhipsawCycle]:
        """Get the most recent complete cycle for an asset."""
        cutoff_date = current_date - timedelta(days=self.protection_period_days * 2)  # Look back further
        events = [
            event for event in self.position_history[asset]
            if event.date > cutoff_date
        ]
        
        if len(events) < 2:
            return None
        
        # Find the most recent complete cycle
        sorted_events = sorted(events, key=lambda x: x.date, reverse=True)
        
        open_event = None
        for event in sorted_events:
            if event.event_type == 'close' and open_event is None:
                close_event = event
            elif event.event_type == 'open' and 'close_event' in locals():
                open_event = event
                # Found complete cycle
                duration_hours = (close_event.date - open_event.date).total_seconds() / 3600
                return WhipsawCycle(
                    asset=asset,
                    open_event=open_event,
                    close_event=close_event,
                    cycle_duration_hours=duration_hours,
                    size_traded=max(open_event.size, close_event.size)
                )
        
        return None
    
    def get_whipsaw_report(self, assets: List[str], current_date: datetime) -> Dict:
        """
        Generate whipsaw protection status report.
        
        Args:
            assets: List of assets to report on
            current_date: Current date
            
        Returns:
            Comprehensive whipsaw protection report
        """
        report = {
            'timestamp': current_date,
            'protection_settings': {
                'max_cycles_per_period': self.max_cycles_per_period,
                'protection_period_days': self.protection_period_days,
                'min_position_duration_hours': self.min_position_duration_hours
            },
            'asset_status': {},
            'summary': {
                'total_assets': len(assets),
                'active_positions': len(self.active_positions),
                'protected_assets': 0,
                'assets_at_cycle_limit': 0
            }
        }
        
        protected_count = 0
        at_limit_count = 0
        
        for asset in assets:
            recent_cycles = self._count_recent_cycles(asset, current_date)
            can_trade = recent_cycles < self.max_cycles_per_period
            
            if not can_trade:
                protected_count += 1
                if recent_cycles >= self.max_cycles_per_period:
                    at_limit_count += 1
            
            asset_status = {
                'recent_cycles': recent_cycles,
                'can_open_new_position': can_trade,
                'protection_active': not can_trade,
                'days_until_reset': self._days_until_protection_reset(asset, current_date),
                'is_currently_open': asset in self.active_positions,
                'total_events': len(self.position_history[asset])
            }
            
            # Add current position info if open
            if asset in self.active_positions:
                open_event = self.active_positions[asset]
                duration = current_date - open_event.date
                can_close, close_reason = self.can_close_position(asset, open_event.date, current_date)
                
                asset_status.update({
                    'current_position': {
                        'opened': open_event.date,
                        'duration': str(duration),
                        'duration_hours': duration.total_seconds() / 3600,
                        'size': open_event.size,
                        'can_close': can_close,
                        'close_reason': close_reason
                    }
                })
            
            # Add last cycle info if available
            last_cycle = self._get_last_complete_cycle(asset, current_date)
            if last_cycle:
                asset_status['last_cycle'] = {
                    'duration_hours': last_cycle.cycle_duration_hours,
                    'duration_days': last_cycle.cycle_duration_days,
                    'size_traded': last_cycle.size_traded,
                    'open_date': last_cycle.open_event.date,
                    'close_date': last_cycle.close_event.date
                }
            
            report['asset_status'][asset] = asset_status
        
        # Update summary
        report['summary'].update({
            'protected_assets': protected_count,
            'assets_at_cycle_limit': at_limit_count,
            'protection_active_pct': (protected_count / len(assets) * 100) if assets else 0
        })
        
        return report
    
    def _days_until_protection_reset(self, asset: str, current_date: datetime) -> int:
        """
        Calculate days until whipsaw protection resets for an asset.
        
        Args:
            asset: Asset symbol
            current_date: Current date
            
        Returns:
            Days until protection resets (0 if not protected)
        """
        if asset not in self.position_history or not self.position_history[asset]:
            return 0
        
        cutoff_date = current_date - timedelta(days=self.protection_period_days)
        relevant_events = [
            event for event in self.position_history[asset]
            if event.date > cutoff_date
        ]
        
        if not relevant_events:
            return 0
        
        # Find oldest relevant event that's contributing to the cycle count
        oldest_relevant_event = min(relevant_events, key=lambda x: x.date)
        reset_date = oldest_relevant_event.date + timedelta(days=self.protection_period_days)
        
        return max(0, (reset_date - current_date).days)
    
    def _clean_old_events(self, asset: str, current_date: datetime):
        """Clean up old events beyond the tracking period."""
        if asset not in self.position_history:
            return
        
        # Keep events for 2x protection period for analysis
        cutoff_date = current_date - timedelta(days=self.protection_period_days * 2)
        
        self.position_history[asset] = [
            event for event in self.position_history[asset]
            if event.date > cutoff_date
        ]
    
    def get_cycle_analysis(self, asset: str, current_date: datetime) -> Dict:
        """
        Get detailed cycle analysis for an asset.
        
        Args:
            asset: Asset symbol
            current_date: Current date
            
        Returns:
            Detailed cycle analysis
        """
        if asset not in self.position_history:
            return {'message': f'No history available for {asset}'}
        
        # Get all cycles in extended lookback period
        cutoff_date = current_date - timedelta(days=self.protection_period_days * 3)
        events = [
            event for event in self.position_history[asset]
            if event.date > cutoff_date
        ]
        
        cycles = []
        sorted_events = sorted(events, key=lambda x: x.date)
        
        # Find all complete cycles
        i = 0
        while i < len(sorted_events) - 1:
            if sorted_events[i].event_type == 'open':
                # Look for corresponding close
                for j in range(i + 1, len(sorted_events)):
                    if sorted_events[j].event_type == 'close':
                        duration_hours = (sorted_events[j].date - sorted_events[i].date).total_seconds() / 3600
                        cycles.append(WhipsawCycle(
                            asset=asset,
                            open_event=sorted_events[i],
                            close_event=sorted_events[j],
                            cycle_duration_hours=duration_hours,
                            size_traded=max(sorted_events[i].size, sorted_events[j].size)
                        ))
                        i = j + 1
                        break
                else:
                    i += 1
            else:
                i += 1
        
        if not cycles:
            return {
                'asset': asset,
                'total_cycles': 0,
                'message': 'No complete cycles found'
            }
        
        # Calculate statistics
        cycle_durations = [cycle.cycle_duration_hours for cycle in cycles]
        cycle_sizes = [cycle.size_traded for cycle in cycles]
        
        return {
            'asset': asset,
            'analysis_period_days': self.protection_period_days * 3,
            'total_cycles': len(cycles),
            'cycle_statistics': {
                'avg_duration_hours': sum(cycle_durations) / len(cycle_durations),
                'min_duration_hours': min(cycle_durations),
                'max_duration_hours': max(cycle_durations),
                'avg_size_traded': sum(cycle_sizes) / len(cycle_sizes),
                'total_size_traded': sum(cycle_sizes)
            },
            'recent_cycles': [
                {
                    'open_date': cycle.open_event.date,
                    'close_date': cycle.close_event.date,
                    'duration_hours': cycle.cycle_duration_hours,
                    'size_traded': cycle.size_traded,
                    'open_reason': cycle.open_event.reason,
                    'close_reason': cycle.close_event.reason
                }
                for cycle in cycles[-5:]  # Last 5 cycles
            ]
        }
    
    def clean_expired_events(self, current_date: datetime) -> int:
        """
        Clean up expired events from all assets.
        
        Args:
            current_date: Current date
            
        Returns:
            Number of expired events removed
        """
        total_removed = 0
        cutoff_date = current_date - timedelta(days=self.protection_period_days * 2)
        
        for asset in list(self.position_history.keys()):
            original_count = len(self.position_history[asset])
            self.position_history[asset] = [
                event for event in self.position_history[asset]
                if event.date > cutoff_date
            ]
            removed_count = original_count - len(self.position_history[asset])
            total_removed += removed_count
            
            # Remove empty histories
            if not self.position_history[asset]:
                del self.position_history[asset]
        
        return total_removed
    
    def get_configuration_summary(self) -> Dict:
        """
        Get current whipsaw protection configuration.
        
        Returns:
            Dict with configuration parameters and current state
        """
        return {
            'protection_settings': {
                'max_cycles_per_period': self.max_cycles_per_period,
                'protection_period_days': self.protection_period_days,
                'min_position_duration_hours': self.min_position_duration_hours
            },
            'current_state': {
                'tracked_assets': len(self.position_history),
                'active_positions': len(self.active_positions),
                'total_events': sum(len(events) for events in self.position_history.values())
            },
            'protection_rules': {
                'cycle_definition': 'Complete open + close sequence',
                'protection_trigger': f'{self.max_cycles_per_period} cycles per {self.protection_period_days} days',
                'minimum_duration': f'{self.min_position_duration_hours} hours',
                'event_retention': f'{self.protection_period_days * 2} days'
            }
        } 