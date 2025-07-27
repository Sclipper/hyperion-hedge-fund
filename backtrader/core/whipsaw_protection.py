"""
Module 7: Advanced Whipsaw Protection - Core Protection Engine

This module implements sophisticated whipsaw protection to prevent rapid position cycling
and excessive transaction costs with regime-aware override capabilities.
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum


class ProtectionDecision(Enum):
    """Protection decision types"""
    ALLOW = "allow"
    BLOCK = "block"
    OVERRIDE = "override"


class OverrideReason(Enum):
    """Override reason types"""
    REGIME_CHANGE = "regime_change"
    EMERGENCY = "emergency"
    MANUAL = "manual"
    NONE = "none"


@dataclass
class PositionEvent:
    """Individual position event record"""
    asset: str
    event_type: str  # 'open', 'close', 'adjust'
    event_date: datetime
    position_size: float = 0.0
    event_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PositionCycle:
    """Complete position cycle (open -> close)"""
    asset: str
    open_event: PositionEvent
    close_event: PositionEvent
    cycle_duration: timedelta
    cycle_id: str = ""


@dataclass
class ProtectionDecisionRecord:
    """Record of protection decision"""
    asset: str
    action: str  # 'open', 'close', 'adjust'
    decision: ProtectionDecision
    reason: str
    override_reason: OverrideReason
    decision_date: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class PositionCycleTracker:
    """
    Precise tracking and counting of position open/close cycles
    """
    
    def __init__(self, protection_period_days=14):
        """
        Initialize cycle tracker
        
        Args:
            protection_period_days: Rolling window for cycle counting
        """
        self.protection_period_days = protection_period_days
        self.position_events: Dict[str, List[PositionEvent]] = defaultdict(list)
        self.completed_cycles: Dict[str, List[PositionCycle]] = defaultdict(list)
        self.cycle_cache: Dict[str, Tuple[int, datetime]] = {}  # asset -> (count, cache_time)
        self.cache_duration = timedelta(hours=1)  # Cache for 1 hour
    
    def add_position_event(self, asset: str, event_type: str, 
                          event_date: datetime, position_size: float = 0.0,
                          **metadata) -> str:
        """
        Add position event to tracking system
        
        Args:
            asset: Asset symbol
            event_type: 'open' | 'close' | 'adjust'
            event_date: When event occurred
            position_size: Size of position
            **metadata: Additional event information
            
        Returns:
            Event ID for tracking
        """
        event_id = f"{asset}_{event_type}_{event_date.strftime('%Y%m%d_%H%M%S')}"
        
        event = PositionEvent(
            asset=asset,
            event_type=event_type,
            event_date=event_date,
            position_size=position_size,
            event_id=event_id,
            metadata=metadata
        )
        
        self.position_events[asset].append(event)
        
        # Invalidate cache for this asset
        if asset in self.cycle_cache:
            del self.cycle_cache[asset]
        
        # Check for cycle completion
        if event_type == 'close':
            self._check_cycle_completion(asset, event)
        
        # Clean old events
        self._clean_old_events(asset, event_date)
        
        return event_id
    
    def count_recent_cycles(self, asset: str, current_date: datetime) -> int:
        """
        Count complete open->close cycles in recent protection period
        
        Args:
            asset: Asset to check
            current_date: Current date for calculation
            
        Returns:
            Number of complete cycles in protection period
        """
        # Check cache first
        if asset in self.cycle_cache:
            cached_count, cache_time = self.cycle_cache[asset]
            if current_date - cache_time < self.cache_duration:
                return cached_count
        
        cutoff_date = current_date - timedelta(days=self.protection_period_days)
        recent_cycles = [
            cycle for cycle in self.completed_cycles[asset]
            if cycle.close_event.event_date > cutoff_date
        ]
        
        cycle_count = len(recent_cycles)
        
        # Cache the result
        self.cycle_cache[asset] = (cycle_count, current_date)
        
        return cycle_count
    
    def get_last_position_event(self, asset: str, event_type: Optional[str] = None) -> Optional[PositionEvent]:
        """
        Get the most recent position event for an asset
        
        Args:
            asset: Asset to check
            event_type: Filter by event type (optional)
            
        Returns:
            Most recent event or None
        """
        if asset not in self.position_events:
            return None
        
        events = self.position_events[asset]
        if not events:
            return None
        
        if event_type:
            filtered_events = [e for e in events if e.event_type == event_type]
            if not filtered_events:
                return None
            return max(filtered_events, key=lambda x: x.event_date)
        
        return max(events, key=lambda x: x.event_date)
    
    def get_cycle_history(self, asset: str, days: Optional[int] = None) -> List[PositionCycle]:
        """
        Get detailed cycle history for analysis
        
        Args:
            asset: Asset to analyze
            days: Number of days to look back (None for all)
            
        Returns:
            List of completed cycles
        """
        cycles = self.completed_cycles.get(asset, [])
        
        if days is None:
            return cycles.copy()
        
        cutoff_date = datetime.now() - timedelta(days=days)
        return [cycle for cycle in cycles if cycle.close_event.event_date > cutoff_date]
    
    def estimate_next_cycle_completion(self, asset: str, current_date: datetime) -> Optional[datetime]:
        """
        Estimate when current incomplete cycle might complete
        
        Args:
            asset: Asset to analyze
            current_date: Current date
            
        Returns:
            Estimated completion date or None if no open position
        """
        last_open = self.get_last_position_event(asset, 'open')
        last_close = self.get_last_position_event(asset, 'close')
        
        # Check if we have an open position
        if not last_open:
            return None
        
        if last_close and last_close.event_date > last_open.event_date:
            return None  # Position is closed
        
        # Get historical cycle durations for estimation
        historical_cycles = self.get_cycle_history(asset, 90)  # Last 90 days
        
        if not historical_cycles:
            # No historical data, use default estimate
            estimated_duration = timedelta(days=7)
        else:
            # Use average duration from historical cycles
            avg_duration_seconds = np.mean([
                cycle.cycle_duration.total_seconds() 
                for cycle in historical_cycles
            ])
            estimated_duration = timedelta(seconds=avg_duration_seconds)
        
        return last_open.event_date + estimated_duration
    
    def _check_cycle_completion(self, asset: str, close_event: PositionEvent):
        """
        Check if close event completes a cycle and record it
        
        Args:
            asset: Asset symbol
            close_event: Close event to check
        """
        # Find the most recent open event before this close
        open_events = [
            e for e in self.position_events[asset]
            if e.event_type == 'open' and e.event_date < close_event.event_date
        ]
        
        if not open_events:
            return  # No open event to match
        
        # Get the most recent open event
        open_event = max(open_events, key=lambda x: x.event_date)
        
        # Check if this open event was already used in a cycle
        existing_cycles = [
            cycle for cycle in self.completed_cycles[asset]
            if cycle.open_event.event_id == open_event.event_id
        ]
        
        if existing_cycles:
            return  # Open event already used
        
        # Create new cycle
        cycle_duration = close_event.event_date - open_event.event_date
        cycle_id = f"{asset}_cycle_{open_event.event_date.strftime('%Y%m%d_%H%M%S')}"
        
        cycle = PositionCycle(
            asset=asset,
            open_event=open_event,
            close_event=close_event,
            cycle_duration=cycle_duration,
            cycle_id=cycle_id
        )
        
        self.completed_cycles[asset].append(cycle)
        
        print(f"📊 Cycle completed for {asset}: {cycle_duration.days} days "
              f"({open_event.event_date.strftime('%Y-%m-%d')} → {close_event.event_date.strftime('%Y-%m-%d')})")
    
    def _clean_old_events(self, asset: str, current_date: datetime):
        """
        Remove old events beyond retention period
        
        Args:
            asset: Asset to clean
            current_date: Current date for age calculation
        """
        # Keep events for double the protection period for analysis
        retention_days = self.protection_period_days * 2
        cutoff_date = current_date - timedelta(days=retention_days)
        
        # Clean position events
        if asset in self.position_events:
            self.position_events[asset] = [
                event for event in self.position_events[asset]
                if event.event_date > cutoff_date
            ]
        
        # Clean completed cycles
        if asset in self.completed_cycles:
            self.completed_cycles[asset] = [
                cycle for cycle in self.completed_cycles[asset]
                if cycle.close_event.event_date > cutoff_date
            ]


class PositionHistoryManager:
    """
    Comprehensive position event tracking and audit trail management
    """
    
    def __init__(self, max_history_days=365):
        """
        Initialize history manager
        
        Args:
            max_history_days: Maximum days to retain history
        """
        self.max_history_days = max_history_days
        self.event_history: List[PositionEvent] = []
        self.decision_history: List[ProtectionDecisionRecord] = []
        self.event_index: Dict[str, List[int]] = defaultdict(list)  # asset -> event indices
    
    def record_position_event(self, asset: str, event_type: str, 
                            event_date: datetime, position_size: float = 0.0,
                            **metadata) -> str:
        """
        Record position event in comprehensive history
        
        Args:
            asset: Asset symbol
            event_type: Type of event
            event_date: When event occurred
            position_size: Position size
            **metadata: Additional metadata
            
        Returns:
            Event ID
        """
        event_id = f"{asset}_{event_type}_{event_date.strftime('%Y%m%d_%H%M%S_%f')}"
        
        event = PositionEvent(
            asset=asset,
            event_type=event_type,
            event_date=event_date,
            position_size=position_size,
            event_id=event_id,
            metadata=metadata
        )
        
        # Add to history
        event_index = len(self.event_history)
        self.event_history.append(event)
        self.event_index[asset].append(event_index)
        
        # Clean old history periodically
        if len(self.event_history) % 100 == 0:  # Every 100 events
            self._clean_old_history(event_date)
        
        return event_id
    
    def record_protection_decision(self, asset: str, action: str,
                                 decision: ProtectionDecision, reason: str,
                                 override_reason: OverrideReason,
                                 decision_date: datetime, **metadata) -> str:
        """
        Record protection decision for audit trail
        
        Args:
            asset: Asset symbol
            action: Action being decided on
            decision: Protection decision
            reason: Reason for decision
            override_reason: Reason for any override
            decision_date: When decision was made
            **metadata: Additional metadata
            
        Returns:
            Decision record ID
        """
        decision_record = ProtectionDecisionRecord(
            asset=asset,
            action=action,
            decision=decision,
            reason=reason,
            override_reason=override_reason,
            decision_date=decision_date,
            metadata=metadata
        )
        
        self.decision_history.append(decision_record)
        
        return f"decision_{decision_date.strftime('%Y%m%d_%H%M%S_%f')}"
    
    def get_asset_event_history(self, asset: str, days: Optional[int] = None) -> List[PositionEvent]:
        """
        Get event history for specific asset
        
        Args:
            asset: Asset to query
            days: Number of days to look back
            
        Returns:
            List of events for asset
        """
        if asset not in self.event_index:
            return []
        
        asset_events = [self.event_history[i] for i in self.event_index[asset]]
        
        if days is None:
            return asset_events
        
        cutoff_date = datetime.now() - timedelta(days=days)
        return [event for event in asset_events if event.event_date > cutoff_date]
    
    def get_protection_decisions(self, asset: Optional[str] = None, 
                               days: Optional[int] = None) -> List[ProtectionDecisionRecord]:
        """
        Get protection decision history
        
        Args:
            asset: Filter by asset (None for all)
            days: Number of days to look back
            
        Returns:
            List of protection decisions
        """
        decisions = self.decision_history.copy()
        
        if asset:
            decisions = [d for d in decisions if d.asset == asset]
        
        if days:
            cutoff_date = datetime.now() - timedelta(days=days)
            decisions = [d for d in decisions if d.decision_date > cutoff_date]
        
        return decisions
    
    def _clean_old_history(self, current_date: datetime):
        """
        Clean old history beyond retention period
        
        Args:
            current_date: Current date for age calculation
        """
        cutoff_date = current_date - timedelta(days=self.max_history_days)
        
        # Clean event history
        old_count = len(self.event_history)
        valid_indices = []
        new_event_history = []
        
        for i, event in enumerate(self.event_history):
            if event.event_date > cutoff_date:
                valid_indices.append(i)
                new_event_history.append(event)
        
        self.event_history = new_event_history
        
        # Update event index
        for asset in self.event_index:
            self.event_index[asset] = [
                new_idx for new_idx, old_idx in enumerate(valid_indices)
                if old_idx in self.event_index[asset]
            ]
        
        # Clean decision history
        self.decision_history = [
            decision for decision in self.decision_history
            if decision.decision_date > cutoff_date
        ]
        
        cleaned_count = old_count - len(self.event_history)
        if cleaned_count > 0:
            print(f"🧹 Cleaned {cleaned_count} old events from history")


class BasicWhipsawMetrics:
    """
    Simple analytics for whipsaw protection effectiveness
    """
    
    def __init__(self):
        """Initialize metrics tracking"""
        self.protection_stats = {
            'total_decisions': 0,
            'blocked_opens': 0,
            'blocked_closes': 0,
            'allowed_opens': 0,
            'allowed_closes': 0,
            'overrides_used': 0,
            'cycles_prevented': 0
        }
        self.daily_stats: Dict[str, Dict] = defaultdict(lambda: {
            'decisions': 0,
            'blocks': 0,
            'allows': 0,
            'overrides': 0
        })
        self.asset_stats: Dict[str, Dict] = defaultdict(lambda: {
            'total_decisions': 0,
            'blocked_actions': 0,
            'allowed_actions': 0,
            'cycles_prevented': 0,
            'last_decision_date': None
        })
    
    def record_protection_decision(self, asset: str, action: str, 
                                 decision: ProtectionDecision, reason: str,
                                 current_date: datetime):
        """
        Record protection decision for analytics
        
        Args:
            asset: Asset symbol
            action: Action type (open/close)
            decision: Protection decision
            reason: Decision reason
            current_date: Current date
        """
        date_key = current_date.strftime('%Y-%m-%d')
        
        # Update overall stats
        self.protection_stats['total_decisions'] += 1
        
        # Update daily stats
        self.daily_stats[date_key]['decisions'] += 1
        
        # Update asset stats
        self.asset_stats[asset]['total_decisions'] += 1
        self.asset_stats[asset]['last_decision_date'] = current_date
        
        if decision == ProtectionDecision.BLOCK:
            self.protection_stats[f'blocked_{action}s'] += 1
            self.daily_stats[date_key]['blocks'] += 1
            self.asset_stats[asset]['blocked_actions'] += 1
            
            # Count cycles prevented (rough estimate)
            if action == 'open':
                self.protection_stats['cycles_prevented'] += 0.5  # Half a cycle
                self.asset_stats[asset]['cycles_prevented'] += 0.5
                
        elif decision == ProtectionDecision.ALLOW:
            self.protection_stats[f'allowed_{action}s'] += 1
            self.daily_stats[date_key]['allows'] += 1
            self.asset_stats[asset]['allowed_actions'] += 1
            
        elif decision == ProtectionDecision.OVERRIDE:
            self.protection_stats['overrides_used'] += 1
            self.daily_stats[date_key]['overrides'] += 1
    
    def get_protection_effectiveness(self, days: int = 30) -> Dict[str, Any]:
        """
        Get basic protection effectiveness metrics
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Protection effectiveness metrics
        """
        total_decisions = self.protection_stats['total_decisions']
        
        if total_decisions == 0:
            return {
                'total_decisions': 0,
                'protection_rate': 0.0,
                'override_rate': 0.0,
                'estimated_cycles_prevented': 0,
                'effectiveness_score': 0.0
            }
        
        blocked_decisions = (
            self.protection_stats['blocked_opens'] + 
            self.protection_stats['blocked_closes']
        )
        
        protection_rate = blocked_decisions / total_decisions
        override_rate = self.protection_stats['overrides_used'] / total_decisions
        
        # Simple effectiveness score (high protection with low overrides is good)
        effectiveness_score = protection_rate * (1.0 - override_rate * 0.5)
        
        return {
            'total_decisions': total_decisions,
            'protection_rate': protection_rate,
            'override_rate': override_rate,
            'estimated_cycles_prevented': self.protection_stats['cycles_prevented'],
            'effectiveness_score': effectiveness_score,
            'blocked_opens': self.protection_stats['blocked_opens'],
            'blocked_closes': self.protection_stats['blocked_closes'],
            'allowed_opens': self.protection_stats['allowed_opens'],
            'allowed_closes': self.protection_stats['allowed_closes']
        }
    
    def get_daily_summary(self, date: datetime) -> Dict[str, Any]:
        """
        Get protection summary for specific day
        
        Args:
            date: Date to analyze
            
        Returns:
            Daily protection summary
        """
        date_key = date.strftime('%Y-%m-%d')
        return self.daily_stats.get(date_key, {
            'decisions': 0,
            'blocks': 0,
            'allows': 0,
            'overrides': 0
        }).copy()
    
    def get_asset_statistics(self, asset: str) -> Dict[str, Any]:
        """
        Get protection statistics for specific asset
        
        Args:
            asset: Asset to analyze
            
        Returns:
            Asset-specific protection statistics
        """
        return self.asset_stats.get(asset, {
            'total_decisions': 0,
            'blocked_actions': 0,
            'allowed_actions': 0,
            'cycles_prevented': 0,
            'last_decision_date': None
        }).copy()
    
    def get_top_protected_assets(self, limit: int = 10) -> List[Tuple[str, Dict]]:
        """
        Get assets with most protection activity
        
        Args:
            limit: Number of top assets to return
            
        Returns:
            List of (asset, stats) tuples
        """
        asset_items = [
            (asset, stats) for asset, stats in self.asset_stats.items()
            if stats['total_decisions'] > 0
        ]
        
        # Sort by total decisions (most active first)
        asset_items.sort(key=lambda x: x[1]['total_decisions'], reverse=True)
        
        return asset_items[:limit]


class WhipsawProtectionEngine:
    """
    Core whipsaw protection engine with quantified rules and regime awareness
    """
    
    def __init__(self, max_cycles_per_period=1, protection_period_days=14,
                 min_position_duration_hours=4, regime_context_provider=None):
        """
        Initialize whipsaw protection engine
        
        Args:
            max_cycles_per_period: Maximum cycles allowed per protection period
            protection_period_days: Protection period in days
            min_position_duration_hours: Minimum position duration in hours
            regime_context_provider: Optional regime context provider for overrides
        """
        self.max_cycles_per_period = max_cycles_per_period
        self.protection_period_days = protection_period_days
        self.min_position_duration_hours = min_position_duration_hours
        self.regime_context_provider = regime_context_provider
        
        # Core components
        self.cycle_tracker = PositionCycleTracker(protection_period_days)
        self.history_manager = PositionHistoryManager()
        self.metrics = BasicWhipsawMetrics()
        
        # Protection state
        self.protected_assets: set = set()
        self.active_overrides: Dict[str, Dict] = {}
        
        print(f"🛡️ Whipsaw Protection Engine initialized:")
        print(f"   Max cycles per {protection_period_days} days: {max_cycles_per_period}")
        print(f"   Minimum position duration: {min_position_duration_hours} hours")
        print(f"   Regime integration: {'Enabled' if regime_context_provider else 'Disabled'}")
    
    def can_open_position(self, asset: str, current_date: datetime,
                         context: Optional[Dict] = None) -> Tuple[bool, str]:
        """
        Determine if position can be opened without violating whipsaw protection
        
        Args:
            asset: Asset symbol
            current_date: Current date
            context: Optional context for decision making
            
        Returns:
            Tuple of (can_open: bool, reason: str)
        """
        # Check cycle limits
        recent_cycles = self.cycle_tracker.count_recent_cycles(asset, current_date)
        
        if recent_cycles >= self.max_cycles_per_period:
            # Check for override eligibility
            override_eligible, override_reason = self._check_override_eligibility(
                asset, 'open', current_date, context
            )
            
            if override_eligible:
                decision = ProtectionDecision.OVERRIDE
                reason = f"Override granted: {override_reason} (cycles: {recent_cycles}/{self.max_cycles_per_period})"
                
                # Record override
                self._record_override(asset, 'open', current_date, override_reason)
            else:
                decision = ProtectionDecision.BLOCK
                reason = f"Cycle limit exceeded: {recent_cycles}/{self.max_cycles_per_period} in {self.protection_period_days} days"
        else:
            decision = ProtectionDecision.ALLOW
            reason = f"Within cycle limits: {recent_cycles}/{self.max_cycles_per_period}"
        
        # Record decision
        self.history_manager.record_protection_decision(
            asset=asset,
            action='open',
            decision=decision,
            reason=reason,
            override_reason=OverrideReason.NONE if decision != ProtectionDecision.OVERRIDE else OverrideReason.REGIME_CHANGE,
            decision_date=current_date
        )
        
        self.metrics.record_protection_decision(
            asset, 'open', decision, reason, current_date
        )
        
        can_open = decision in [ProtectionDecision.ALLOW, ProtectionDecision.OVERRIDE]
        
        if not can_open:
            print(f"🚫 WHIPSAW BLOCK: {asset} open blocked - {reason}")
        elif decision == ProtectionDecision.OVERRIDE:
            print(f"🔓 WHIPSAW OVERRIDE: {asset} open allowed - {reason}")
        
        return can_open, reason
    
    def can_close_position(self, asset: str, position_open_date: datetime,
                          current_date: datetime, context: Optional[Dict] = None) -> Tuple[bool, str]:
        """
        Determine if position can be closed without creating whipsaw
        
        Args:
            asset: Asset symbol
            position_open_date: When position was opened
            current_date: Current date
            context: Optional context for decision making
            
        Returns:
            Tuple of (can_close: bool, reason: str)
        """
        # Check minimum duration
        position_duration = current_date - position_open_date
        min_duration = timedelta(hours=self.min_position_duration_hours)
        
        if position_duration < min_duration:
            # Check for override eligibility
            override_eligible, override_reason = self._check_override_eligibility(
                asset, 'close', current_date, context
            )
            
            if override_eligible:
                decision = ProtectionDecision.OVERRIDE
                reason = f"Override granted: {override_reason} (duration: {position_duration} < {min_duration})"
                
                # Record override
                self._record_override(asset, 'close', current_date, override_reason)
            else:
                decision = ProtectionDecision.BLOCK
                reason = f"Minimum duration not met: {position_duration} < {min_duration}"
        else:
            decision = ProtectionDecision.ALLOW
            reason = f"Duration requirement met: {position_duration} >= {min_duration}"
        
        # Record decision
        self.history_manager.record_protection_decision(
            asset=asset,
            action='close',
            decision=decision,
            reason=reason,
            override_reason=OverrideReason.NONE if decision != ProtectionDecision.OVERRIDE else OverrideReason.REGIME_CHANGE,
            decision_date=current_date
        )
        
        self.metrics.record_protection_decision(
            asset, 'close', decision, reason, current_date
        )
        
        can_close = decision in [ProtectionDecision.ALLOW, ProtectionDecision.OVERRIDE]
        
        if not can_close:
            print(f"🚫 WHIPSAW BLOCK: {asset} close blocked - {reason}")
        elif decision == ProtectionDecision.OVERRIDE:
            print(f"🔓 WHIPSAW OVERRIDE: {asset} close allowed - {reason}")
        
        return can_close, reason
    
    def record_position_event(self, asset: str, event_type: str,
                            event_date: datetime, position_size: float = 0.0,
                            **kwargs):
        """
        Record position event in both cycle tracker and history manager
        
        Args:
            asset: Asset symbol
            event_type: Type of event
            event_date: When event occurred
            position_size: Position size
            **kwargs: Additional event data
        """
        # Record in cycle tracker
        event_id = self.cycle_tracker.add_position_event(
            asset, event_type, event_date, position_size, **kwargs
        )
        
        # Record in history manager
        self.history_manager.record_position_event(
            asset, event_type, event_date, position_size, event_id=event_id, **kwargs
        )
        
        print(f"📝 Position event recorded: {asset} {event_type} at {event_date.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def get_protection_status(self, assets: List[str], 
                            current_date: datetime) -> Dict[str, Any]:
        """
        Get comprehensive protection status for assets
        
        Args:
            assets: List of assets to check
            current_date: Current date
            
        Returns:
            Protection status for each asset
        """
        status = {}
        
        for asset in assets:
            recent_cycles = self.cycle_tracker.count_recent_cycles(asset, current_date)
            last_event = self.cycle_tracker.get_last_position_event(asset)
            
            asset_status = {
                'recent_cycles': recent_cycles,
                'max_cycles': self.max_cycles_per_period,
                'cycle_limit_reached': recent_cycles >= self.max_cycles_per_period,
                'last_event': {
                    'type': last_event.event_type if last_event else None,
                    'date': last_event.event_date.isoformat() if last_event else None,
                    'size': last_event.position_size if last_event else 0.0
                },
                'estimated_cycle_completion': None,
                'protection_active': asset in self.protected_assets,
                'active_overrides': self.active_overrides.get(asset, {})
            }
            
            # Estimate cycle completion if position is open
            if last_event and last_event.event_type == 'open':
                estimated_completion = self.cycle_tracker.estimate_next_cycle_completion(asset, current_date)
                if estimated_completion:
                    asset_status['estimated_cycle_completion'] = estimated_completion.isoformat()
            
            status[asset] = asset_status
        
        return status
    
    def _check_override_eligibility(self, asset: str, action: str, 
                                  current_date: datetime,
                                  context: Optional[Dict] = None) -> Tuple[bool, str]:
        """
        Check if protection can be overridden
        
        Args:
            asset: Asset symbol
            action: Action type
            current_date: Current date
            context: Decision context
            
        Returns:
            Tuple of (eligible: bool, reason: str)
        """
        # Check if regime context provider is available
        if not self.regime_context_provider:
            return False, "No regime context provider available"
        
        try:
            # Get regime context
            regime_context = self.regime_context_provider.get_current_context(current_date)
            
            # Check for recent regime transition
            if regime_context.recent_transition:
                severity = regime_context.recent_transition.severity
                if severity.value in ['high', 'critical']:  # Use .value to get string
                    return True, f"Regime transition: {regime_context.recent_transition.from_regime} → {regime_context.recent_transition.to_regime} ({severity.value})"
            
            # Check for emergency market conditions
            if context and context.get('emergency_conditions'):
                return True, "Emergency market conditions detected"
            
            return False, "No override conditions met"
            
        except Exception as e:
            print(f"⚠️ Error checking override eligibility: {e}")
            return False, f"Override check failed: {e}"
    
    def _record_override(self, asset: str, action: str, current_date: datetime, reason: str):
        """
        Record override usage
        
        Args:
            asset: Asset symbol
            action: Action type
            current_date: Current date
            reason: Override reason
        """
        if asset not in self.active_overrides:
            self.active_overrides[asset] = {}
        
        self.active_overrides[asset][action] = {
            'date': current_date,
            'reason': reason,
            'expires': current_date + timedelta(hours=24)  # Override expires in 24 hours
        }
    
    def get_analytics_summary(self, days: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive analytics summary
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Analytics summary
        """
        effectiveness = self.metrics.get_protection_effectiveness(days)
        top_assets = self.metrics.get_top_protected_assets(10)
        
        return {
            'protection_effectiveness': effectiveness,
            'top_protected_assets': top_assets,
            'total_events_tracked': len(self.history_manager.event_history),
            'total_decisions_made': len(self.history_manager.decision_history),
            'protection_period_days': self.protection_period_days,
            'max_cycles_per_period': self.max_cycles_per_period,
            'min_duration_hours': self.min_position_duration_hours
        } 