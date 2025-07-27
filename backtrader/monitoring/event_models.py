import json
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum


class EventCategory(Enum):
    PORTFOLIO = "portfolio"
    REGIME = "regime" 
    PROTECTION = "protection"
    SCORING = "scoring"
    DIVERSIFICATION = "diversification"
    SYSTEM = "system"
    ERROR = "error"


class ActionType(Enum):
    OPEN = "open"
    CLOSE = "close"
    INCREASE = "increase"
    DECREASE = "decrease"
    HOLD = "hold"
    BLOCK = "block"
    OVERRIDE = "override"
    TRANSITION = "transition"
    START = "start"
    END = "end"
    ERROR = "error"


PORTFOLIO_EVENT_TYPES = {
    'position_open': 'New position opened',
    'position_close': 'Position closed', 
    'position_adjust': 'Position size adjusted',
    'position_decay': 'Position size decayed during grace period',
    'portfolio_rebalance_start': 'Rebalancing session initiated',
    'portfolio_rebalance_complete': 'Rebalancing session completed'
}

REGIME_EVENT_TYPES = {
    'regime_transition': 'Market regime changed',
    'regime_detection': 'Regime analysis performed',
    'regime_override_granted': 'Regime override authorized',
    'regime_confidence_low': 'Regime confidence below threshold'
}

PROTECTION_EVENT_TYPES = {
    'whipsaw_block': 'Action blocked by whipsaw protection',
    'grace_period_start': 'Asset entered grace period',
    'grace_period_end': 'Asset exited grace period',
    'holding_period_block': 'Action blocked by holding period',
    'core_asset_immunity': 'Core asset protection activated',
    'override_applied': 'Protection system override applied'
}

SCORING_EVENT_TYPES = {
    'asset_scored': 'Asset analysis and scoring completed',
    'threshold_breach': 'Score crossed threshold',
    'trending_analysis': 'Trending confidence analysis',
    'correlation_check': 'Asset correlation analysis'
}

DIVERSIFICATION_EVENT_TYPES = {
    'bucket_limit_enforced': 'Bucket position limit enforced',
    'bucket_override_granted': 'High-alpha bucket override granted',
    'correlation_block': 'Position blocked by correlation limit',
    'allocation_limit_hit': 'Bucket allocation limit reached'
}


@dataclass
class PortfolioEvent:
    """Standardized portfolio event with complete context"""
    timestamp: datetime
    event_type: str
    event_category: str
    trace_id: str
    session_id: str
    action: str
    reason: str
    
    # Optional fields
    asset: Optional[str] = None
    regime: Optional[str] = None
    score_before: Optional[float] = None
    score_after: Optional[float] = None
    size_before: Optional[float] = None
    size_after: Optional[float] = None
    portfolio_allocation: Optional[float] = None
    active_positions: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: Optional[float] = None
    
    def to_db_tuple(self) -> tuple:
        """Convert to database insert tuple"""
        return (
            self.timestamp.isoformat(),
            self.event_type,
            self.event_category,
            self.trace_id,
            self.session_id,
            self.asset,
            self.regime,
            self.action,
            self.reason,
            self.score_before,
            self.score_after,
            self.size_before,
            self.size_after,
            self.portfolio_allocation,
            self.active_positions,
            json.dumps(self.metadata) if self.metadata else None,
            self.execution_time_ms
        )
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'PortfolioEvent':
        """Create event from database row"""
        metadata = {}
        if row['metadata']:
            try:
                metadata = json.loads(row['metadata'])
            except json.JSONDecodeError:
                metadata = {'raw_metadata': row['metadata']}
        
        return cls(
            timestamp=datetime.fromisoformat(row['timestamp']),
            event_type=row['event_type'],
            event_category=row['event_category'],
            trace_id=row['trace_id'],
            session_id=row['session_id'],
            asset=row['asset'],
            regime=row['regime'],
            action=row['action'],
            reason=row['reason'],
            score_before=row['score_before'],
            score_after=row['score_after'],
            size_before=row['size_before'],
            size_after=row['size_after'],
            portfolio_allocation=row['portfolio_allocation'],
            active_positions=row['active_positions'],
            metadata=metadata,
            execution_time_ms=row['execution_time_ms']
        )


@dataclass
class EventQuery:
    """Flexible event query builder"""
    event_type: Optional[str] = None
    event_category: Optional[str] = None
    asset: Optional[str] = None
    regime: Optional[str] = None
    trace_id: Optional[str] = None
    session_id: Optional[str] = None
    since: Optional[datetime] = None
    until: Optional[datetime] = None
    action: Optional[str] = None
    limit: Optional[int] = None
    order_by_field: str = 'timestamp'
    order_direction: str = 'DESC'
    
    def order_by(self, field: str, direction: str = 'DESC') -> 'EventQuery':
        """Set ordering for query"""
        self.order_by_field = field
        self.order_direction = direction
        return self
    
    def to_sql(self) -> Tuple[str, List[Any]]:
        """Convert to SQL query with parameters"""
        conditions = []
        params = []
        
        if self.event_type:
            conditions.append("event_type = ?")
            params.append(self.event_type)
        
        if self.event_category:
            conditions.append("event_category = ?")
            params.append(self.event_category)
        
        if self.asset:
            conditions.append("asset = ?")
            params.append(self.asset)
        
        if self.regime:
            conditions.append("regime = ?")
            params.append(self.regime)
        
        if self.trace_id:
            conditions.append("trace_id = ?")
            params.append(self.trace_id)
        
        if self.session_id:
            conditions.append("session_id = ?")
            params.append(self.session_id)
        
        if self.since:
            conditions.append("timestamp >= ?")
            params.append(self.since.isoformat())
        
        if self.until:
            conditions.append("timestamp <= ?")
            params.append(self.until.isoformat())
        
        if self.action:
            conditions.append("action = ?")
            params.append(self.action)
        
        # Build SQL
        sql = "SELECT * FROM portfolio_events"
        
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        
        sql += f" ORDER BY {self.order_by_field} {self.order_direction}"
        
        if self.limit:
            sql += f" LIMIT {self.limit}"
        
        return sql, params


@dataclass
class EventStatistics:
    """Event statistics for monitoring dashboard"""
    total_events: int
    events_by_category: Dict[str, int]
    events_by_type: Dict[str, int]
    recent_events_count: int
    average_execution_time_ms: float
    error_count: int
    protection_blocks_count: int
    regime_transitions_count: int
    
    @classmethod
    def from_events(cls, events: List[Dict[str, Any]]) -> 'EventStatistics':
        """Create statistics from list of events"""
        total_events = len(events)
        events_by_category = {}
        events_by_type = {}
        execution_times = []
        error_count = 0
        protection_blocks = 0
        regime_transitions = 0
        
        for event in events:
            # Count by category
            category = event.get('event_category', 'unknown')
            events_by_category[category] = events_by_category.get(category, 0) + 1
            
            # Count by type
            event_type = event.get('event_type', 'unknown')
            events_by_type[event_type] = events_by_type.get(event_type, 0) + 1
            
            # Track execution times
            if event.get('execution_time_ms'):
                execution_times.append(event['execution_time_ms'])
            
            # Count special event types
            if category == 'error':
                error_count += 1
            elif 'block' in event_type:
                protection_blocks += 1
            elif event_type == 'regime_transition':
                regime_transitions += 1
        
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0.0
        
        return cls(
            total_events=total_events,
            events_by_category=events_by_category,
            events_by_type=events_by_type,
            recent_events_count=total_events,  # Assume all events are "recent" in this context
            average_execution_time_ms=avg_execution_time,
            error_count=error_count,
            protection_blocks_count=protection_blocks,
            regime_transitions_count=regime_transitions
        )


def create_portfolio_event(event_type: str, action: str, reason: str, 
                         trace_id: str = None, session_id: str = None,
                         asset: str = None, regime: str = None,
                         score_before: float = None, score_after: float = None,
                         size_before: float = None, size_after: float = None,
                         portfolio_allocation: float = None, active_positions: int = None,
                         metadata: Dict[str, Any] = None, execution_time_ms: float = None) -> PortfolioEvent:
    """Helper function to create portfolio events"""
    
    # Determine event category from event type
    if event_type in PORTFOLIO_EVENT_TYPES:
        category = EventCategory.PORTFOLIO.value
    elif event_type in REGIME_EVENT_TYPES:
        category = EventCategory.REGIME.value
    elif event_type in PROTECTION_EVENT_TYPES:
        category = EventCategory.PROTECTION.value
    elif event_type in SCORING_EVENT_TYPES:
        category = EventCategory.SCORING.value
    elif event_type in DIVERSIFICATION_EVENT_TYPES:
        category = EventCategory.DIVERSIFICATION.value
    elif 'error' in event_type:
        category = EventCategory.ERROR.value
    else:
        category = EventCategory.SYSTEM.value
    
    # Generate IDs if not provided
    if trace_id is None:
        trace_id = str(uuid.uuid4())
    if session_id is None:
        session_id = 'no_session'
    
    return PortfolioEvent(
        timestamp=datetime.now(),
        event_type=event_type,
        event_category=category,
        trace_id=trace_id,
        session_id=session_id,
        asset=asset,
        regime=regime,
        action=action,
        reason=reason,
        score_before=score_before,
        score_after=score_after,
        size_before=size_before,
        size_after=size_after,
        portfolio_allocation=portfolio_allocation,
        active_positions=active_positions,
        metadata=metadata or {},
        execution_time_ms=execution_time_ms
    )