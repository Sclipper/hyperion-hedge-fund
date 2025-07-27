# Module 9: Monitoring & Alerts - Implementation Plan

**Implementation Date:** TBD  
**Status:** 📋 PLANNING  
**Priority:** HIGH - Critical Operational Intelligence Module  
**Estimated Effort:** 2-3 days (comprehensive audit system)  
**Dependencies:** Modules 1-7, 11 ✅ (All completed)

---

## 📋 Module Overview

Module 9 implements a comprehensive monitoring and audit system that captures all portfolio management decisions, regime changes, protection system activations, and edge cases in a unified event journal. This provides complete operational transparency and enables sophisticated analysis of strategy performance.

### **Strategic Importance:**
- **Complete Audit Trail**: Every decision tracked with full context
- **Performance Analysis**: Deep insights into strategy effectiveness
- **Debugging Capability**: Trace any issue from event to root cause
- **Compliance Ready**: Institutional-grade audit trail
- **Real-time Monitoring**: Live system health and performance tracking

---

## 🎯 Technical Architecture

### **Design Philosophy: Single-Table Event Journal**

**Core Principle**: All events go into one table with standardized structure but flexible JSON metadata. This enables:
- **Simple Queries**: No complex joins needed for investigation
- **Unified Timeline**: Complete chronological event sequence
- **Flexible Schema**: JSON metadata adapts to any event type
- **Trace Capability**: Unique trace IDs link related events
- **Fast Performance**: Single table optimized for time-series queries

### **Event Journal Schema**

```sql
CREATE TABLE portfolio_events (
    -- Primary identification
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    
    -- Event classification
    event_type VARCHAR(50) NOT NULL,        -- 'position_change', 'regime_transition', 'protection_block', etc.
    event_category VARCHAR(30) NOT NULL,    -- 'portfolio', 'regime', 'protection', 'scoring', 'diversification'
    
    -- Tracing and context
    trace_id VARCHAR(36) NOT NULL,          -- UUID for tracking related events
    session_id VARCHAR(36) NOT NULL,       -- Rebalancing session identifier
    
    -- Core identifiers
    asset VARCHAR(20),                      -- Asset symbol (NULL for system-wide events)
    regime VARCHAR(20),                     -- Current regime
    
    -- Event details
    action VARCHAR(30),                     -- 'open', 'close', 'block', 'override', 'transition', etc.
    reason TEXT NOT NULL,                   -- Human-readable reason
    
    -- Quantitative data
    score_before DECIMAL(5,3),              -- Asset score before action
    score_after DECIMAL(5,3),               -- Asset score after action
    size_before DECIMAL(6,4),               -- Position size before (as % of portfolio)
    size_after DECIMAL(6,4),                -- Position size after
    
    -- System state
    portfolio_allocation DECIMAL(5,3),      -- Total portfolio allocation at time
    active_positions INTEGER,               -- Number of active positions
    
    -- Flexible metadata (JSON)
    metadata TEXT,                          -- JSON with event-specific data
    
    -- Performance tracking
    execution_time_ms DECIMAL(8,2),         -- Time taken to process
    
    -- Indexing for performance
    INDEX idx_timestamp (timestamp),
    INDEX idx_event_type (event_type),
    INDEX idx_trace_id (trace_id),
    INDEX idx_asset (asset),
    INDEX idx_session (session_id)
);
```

### **Event Categories & Types**

#### **Portfolio Events**
```python
PORTFOLIO_EVENTS = {
    'position_open': 'New position opened',
    'position_close': 'Position closed',
    'position_adjust': 'Position size adjusted',
    'position_decay': 'Position size decayed during grace period',
    'portfolio_rebalance_start': 'Rebalancing session initiated',
    'portfolio_rebalance_complete': 'Rebalancing session completed'
}
```

#### **Regime Events**
```python
REGIME_EVENTS = {
    'regime_transition': 'Market regime changed',
    'regime_detection': 'Regime analysis performed',
    'regime_override_granted': 'Regime override authorized',
    'regime_confidence_low': 'Regime confidence below threshold'
}
```

#### **Protection Events**
```python
PROTECTION_EVENTS = {
    'whipsaw_block': 'Action blocked by whipsaw protection',
    'grace_period_start': 'Asset entered grace period',
    'grace_period_end': 'Asset exited grace period',
    'holding_period_block': 'Action blocked by holding period',
    'core_asset_immunity': 'Core asset protection activated',
    'override_applied': 'Protection system override applied'
}
```

#### **Scoring Events**
```python
SCORING_EVENTS = {
    'asset_scored': 'Asset analysis and scoring completed',
    'threshold_breach': 'Score crossed threshold',
    'trending_analysis': 'Trending confidence analysis',
    'correlation_check': 'Asset correlation analysis'
}
```

#### **Diversification Events**
```python
DIVERSIFICATION_EVENTS = {
    'bucket_limit_enforced': 'Bucket position limit enforced',
    'bucket_override_granted': 'High-alpha bucket override granted',
    'correlation_block': 'Position blocked by correlation limit',
    'allocation_limit_hit': 'Bucket allocation limit reached'
}
```

---

## 🏗️ Implementation Strategy

### **Phase 1: Core Event Journal System**
**Duration:** 6-8 hours  
**Components:** SQLite Event Store, Event Writer, Basic Querying

#### **Objectives:**
1. **Event Store Infrastructure**: SQLite database with optimized schema
2. **Event Writer Service**: High-performance event logging system
3. **Event Models**: Standardized event data structures
4. **Basic Querying**: Essential query capabilities for investigation

#### **Deliverables:**
1. **`EventStore`** - SQLite-backed event storage with connection pooling
2. **`EventWriter`** - Centralized event logging with trace management
3. **`EventModels`** - Dataclasses for all event types
4. **`EventQueryManager`** - Optimized querying interface
5. **Database schema and migration scripts**

### **Phase 2: Module Integration & Instrumentation**  
**Duration:** 8-10 hours  
**Components:** Portfolio Manager Integration, Protection System Events, Regime Events

#### **Objectives:**
1. **Portfolio Manager Events**: Complete position lifecycle tracking
2. **Protection System Integration**: All protection decisions logged
3. **Regime System Integration**: Regime transitions and overrides tracked
4. **Trace Management**: Related events linked with trace IDs

#### **Deliverables:**
1. **Portfolio Event Integration** - All position changes tracked
2. **Protection Event Integration** - Whipsaw, grace period, holding period events
3. **Regime Event Integration** - Transitions, overrides, confidence changes
4. **Trace ID Management** - Session and transaction tracking
5. **Performance monitoring** - Event logging performance optimization

### **Phase 3: Analytics & Monitoring Dashboard**
**Duration:** 6-8 hours  
**Components:** Query Interface, Real-time Monitoring, Alert System

#### **Objectives:**
1. **Advanced Analytics**: Sophisticated event analysis capabilities
2. **Real-time Monitoring**: Live system health and performance tracking
3. **Alert System**: Automated alerts for critical events
4. **Investigation Tools**: Debug and trace capabilities

#### **Deliverables:**
1. **`EventAnalyzer`** - Advanced event analysis and reporting
2. **`MonitoringDashboard`** - Real-time system monitoring
3. **`AlertManager`** - Configurable alert system
4. **Investigation utilities** - Debug and trace tools
5. **Performance analytics** - System performance insights

---

## 🔧 Technical Specifications

### **1. EventStore - SQLite Event Storage**

```python
class EventStore:
    """
    High-performance SQLite event storage with connection pooling
    """
    
    def __init__(self, db_path: str = "portfolio_events.db", pool_size: int = 5):
        self.db_path = db_path
        self.connection_pool = self._create_connection_pool(pool_size)
        self._initialize_schema()
    
    def write_event(self, event: PortfolioEvent) -> int:
        """
        Write event to database with performance optimization
        
        Returns:
            Event ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO portfolio_events (
                    timestamp, event_type, event_category, trace_id, session_id,
                    asset, regime, action, reason, score_before, score_after,
                    size_before, size_after, portfolio_allocation, active_positions,
                    metadata, execution_time_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, event.to_db_tuple())
            
            event_id = cursor.lastrowid
            conn.commit()
            return event_id
    
    def write_events_batch(self, events: List[PortfolioEvent]) -> List[int]:
        """
        Batch write for high-performance bulk operations
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT INTO portfolio_events (
                    timestamp, event_type, event_category, trace_id, session_id,
                    asset, regime, action, reason, score_before, score_after,
                    size_before, size_after, portfolio_allocation, active_positions,
                    metadata, execution_time_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [event.to_db_tuple() for event in events])
            
            # Get generated IDs
            first_id = cursor.lastrowid - len(events) + 1
            event_ids = list(range(first_id, cursor.lastrowid + 1))
            
            conn.commit()
            return event_ids
    
    def query_events(self, query: EventQuery) -> List[Dict[str, Any]]:
        """
        Query events with optimized filters
        """
        sql, params = query.to_sql()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_trace_events(self, trace_id: str) -> List[Dict[str, Any]]:
        """
        Get all events for a specific trace ID (transaction)
        """
        return self.query_events(EventQuery(trace_id=trace_id))
    
    def get_asset_timeline(self, asset: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get chronological timeline for specific asset
        """
        return self.query_events(
            EventQuery(
                asset=asset,
                since=datetime.now() - timedelta(days=days)
            ).order_by('timestamp')
        )
```

### **2. EventWriter - Centralized Event Logging**

```python
class EventWriter:
    """
    Centralized event logging with trace management and performance optimization
    """
    
    def __init__(self, event_store: EventStore, enable_batch_mode: bool = False):
        self.event_store = event_store
        self.enable_batch_mode = enable_batch_mode
        self.batch_events: List[PortfolioEvent] = []
        self.batch_size = 100
        self.current_session_id = None
        self.trace_stack: List[str] = []  # For nested operations
        
        # Performance tracking
        self.events_written = 0
        self.total_write_time = 0.0
    
    def start_session(self, session_type: str = "rebalancing") -> str:
        """
        Start new session and return session ID
        """
        self.current_session_id = str(uuid.uuid4())
        
        self.log_event(
            event_type='session_start',
            event_category='system',
            action='start',
            reason=f'{session_type} session initiated',
            metadata={'session_type': session_type}
        )
        
        return self.current_session_id
    
    def end_session(self, session_stats: Dict[str, Any] = None):
        """
        End current session with statistics
        """
        if self.current_session_id:
            self.log_event(
                event_type='session_end',
                event_category='system',
                action='end',
                reason='Session completed',
                metadata=session_stats or {}
            )
            
            if self.enable_batch_mode:
                self.flush_batch()
            
            self.current_session_id = None
    
    def start_trace(self, operation: str) -> str:
        """
        Start new trace for related operations
        """
        trace_id = str(uuid.uuid4())
        self.trace_stack.append(trace_id)
        
        self.log_event(
            event_type='trace_start',
            event_category='system',
            action='start',
            reason=f'Starting {operation}',
            trace_id=trace_id,
            metadata={'operation': operation}
        )
        
        return trace_id
    
    def end_trace(self, trace_id: str = None, success: bool = True, stats: Dict = None):
        """
        End trace with success status and statistics
        """
        if trace_id is None and self.trace_stack:
            trace_id = self.trace_stack.pop()
        elif trace_id in self.trace_stack:
            self.trace_stack.remove(trace_id)
        
        if trace_id:
            self.log_event(
                event_type='trace_end',
                event_category='system',
                action='end',
                reason=f'Trace completed - {"success" if success else "failure"}',
                trace_id=trace_id,
                metadata={'success': success, 'stats': stats or {}}
            )
    
    def log_event(self, event_type: str, event_category: str, action: str, reason: str,
                  asset: str = None, regime: str = None, trace_id: str = None,
                  score_before: float = None, score_after: float = None,
                  size_before: float = None, size_after: float = None,
                  metadata: Dict[str, Any] = None, execution_time_ms: float = None) -> int:
        """
        Log single event with automatic trace and session management
        """
        # Use current trace if none specified
        if trace_id is None and self.trace_stack:
            trace_id = self.trace_stack[-1]
        elif trace_id is None:
            trace_id = str(uuid.uuid4())  # Generate new trace for standalone events
        
        event = PortfolioEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            event_category=event_category,
            trace_id=trace_id,
            session_id=self.current_session_id or 'no_session',
            asset=asset,
            regime=regime,
            action=action,
            reason=reason,
            score_before=score_before,
            score_after=score_after,
            size_before=size_before,
            size_after=size_after,
            metadata=metadata or {},
            execution_time_ms=execution_time_ms
        )
        
        if self.enable_batch_mode:
            self.batch_events.append(event)
            if len(self.batch_events) >= self.batch_size:
                self.flush_batch()
            return 0  # Batch mode doesn't return immediate ID
        else:
            start_time = time.time()
            event_id = self.event_store.write_event(event)
            write_time = (time.time() - start_time) * 1000
            
            # Track performance
            self.events_written += 1
            self.total_write_time += write_time
            
            return event_id
    
    def flush_batch(self):
        """
        Flush all batched events to storage
        """
        if self.batch_events:
            start_time = time.time()
            self.event_store.write_events_batch(self.batch_events)
            write_time = (time.time() - start_time) * 1000
            
            self.events_written += len(self.batch_events)
            self.total_write_time += write_time
            
            print(f"Flushed {len(self.batch_events)} events in {write_time:.2f}ms")
            self.batch_events = []
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get event writing performance statistics
        """
        avg_time = self.total_write_time / max(self.events_written, 1)
        
        return {
            'events_written': self.events_written,
            'total_write_time_ms': self.total_write_time,
            'average_write_time_ms': avg_time,
            'batch_mode': self.enable_batch_mode,
            'pending_batch_events': len(self.batch_events)
        }
```

### **3. EventModels - Standardized Event Data Structures**

```python
@dataclass
class PortfolioEvent:
    """
    Standardized portfolio event with complete context
    """
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
        """
        Convert to database insert tuple
        """
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
        """
        Create event from database row
        """
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


class EventQuery:
    """
    Flexible event query builder
    """
    
    def __init__(self, event_type: str = None, event_category: str = None,
                 asset: str = None, regime: str = None, trace_id: str = None,
                 session_id: str = None, since: datetime = None, until: datetime = None,
                 action: str = None, limit: int = None):
        self.event_type = event_type
        self.event_category = event_category
        self.asset = asset
        self.regime = regime
        self.trace_id = trace_id
        self.session_id = session_id
        self.since = since
        self.until = until
        self.action = action
        self.limit = limit
        self.order_by_field = 'timestamp'
        self.order_direction = 'DESC'
    
    def order_by(self, field: str, direction: str = 'DESC') -> 'EventQuery':
        """
        Set ordering for query
        """
        self.order_by_field = field
        self.order_direction = direction
        return self
    
    def to_sql(self) -> Tuple[str, List[Any]]:
        """
        Convert to SQL query with parameters
        """
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
```

### **4. Module Integration Decorators**

```python
def log_portfolio_event(event_type: str, event_category: str = 'portfolio'):
    """
    Decorator to automatically log portfolio events
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Extract context
            asset = kwargs.get('asset') or (args[0] if args else None)
            trace_id = getattr(self, '_current_trace_id', None)
            
            start_time = time.time()
            
            try:
                # Execute function
                result = func(self, *args, **kwargs)
                
                execution_time = (time.time() - start_time) * 1000
                
                # Log successful event
                if hasattr(self, 'event_writer'):
                    self.event_writer.log_event(
                        event_type=event_type,
                        event_category=event_category,
                        action=event_type.split('_')[-1],  # Extract action from event type
                        reason=f'{func.__name__} completed successfully',
                        asset=asset if isinstance(asset, str) else None,
                        trace_id=trace_id,
                        execution_time_ms=execution_time,
                        metadata={
                            'function': func.__name__,
                            'module': func.__module__,
                            'args_count': len(args),
                            'kwargs_keys': list(kwargs.keys())
                        }
                    )
                
                return result
                
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                
                # Log error event
                if hasattr(self, 'event_writer'):
                    self.event_writer.log_event(
                        event_type=f'{event_type}_error',
                        event_category='error',
                        action='error',
                        reason=f'{func.__name__} failed: {str(e)}',
                        asset=asset if isinstance(asset, str) else None,
                        trace_id=trace_id,
                        execution_time_ms=execution_time,
                        metadata={
                            'function': func.__name__,
                            'error_type': type(e).__name__,
                            'error_message': str(e)
                        }
                    )
                
                raise
        
        return wrapper
    return decorator
```

---

## 📋 Implementation Checklist

### **Phase 1: Core Event Journal System** ⏳
- [ ] `EventStore` SQLite database with optimized schema
- [ ] `EventWriter` centralized logging with trace management  
- [ ] `PortfolioEvent` and `EventQuery` data models
- [ ] Database schema creation and migration scripts
- [ ] Connection pooling and performance optimization
- [ ] Basic event querying capabilities
- [ ] Unit tests for core event system

### **Phase 2: Module Integration & Instrumentation** ⏳
- [ ] Portfolio Manager event integration
- [ ] Position lifecycle event tracking
- [ ] Whipsaw protection event logging
- [ ] Grace period and holding period events
- [ ] Regime transition and override events
- [ ] Diversification constraint events
- [ ] Trace ID management across modules
- [ ] Performance monitoring integration

### **Phase 3: Analytics & Monitoring Dashboard** ⏳
- [ ] `EventAnalyzer` for advanced analytics
- [ ] Real-time monitoring capabilities
- [ ] Alert system for critical events
- [ ] Investigation and debugging tools
- [ ] Performance analytics and reporting
- [ ] System health monitoring
- [ ] Integration testing across all modules

---

## 📊 Event Examples

### **Position Opening Event**
```json
{
  "timestamp": "2025-07-27T10:30:15.123456",
  "event_type": "position_open",
  "event_category": "portfolio",
  "trace_id": "rebal_20250727_103015_001",
  "session_id": "session_20250727_103000",
  "asset": "AAPL",
  "regime": "Goldilocks",
  "action": "open",
  "reason": "High score asset: 0.857 > 0.65 threshold",
  "score_before": null,
  "score_after": 0.857,
  "size_before": 0.0,
  "size_after": 0.12,
  "portfolio_allocation": 0.94,
  "active_positions": 8,
  "metadata": {
    "bucket": "Risk Assets",
    "trending_confidence": 0.78,
    "bucket_allocation_before": 0.32,
    "bucket_allocation_after": 0.44,
    "diversification_impact": "within_limits"
  },
  "execution_time_ms": 2.3
}
```

### **Whipsaw Protection Block Event**
```json
{
  "timestamp": "2025-07-27T10:32:45.678901",
  "event_type": "whipsaw_block",
  "event_category": "protection",
  "trace_id": "rebal_20250727_103015_001",
  "session_id": "session_20250727_103000",
  "asset": "TSLA",
  "regime": "Goldilocks",
  "action": "block",
  "reason": "Cycle limit exceeded: 1/1 in 7 days",
  "score_before": null,
  "score_after": 0.742,
  "metadata": {
    "protection_type": "whipsaw",
    "cycles_recent": 1,
    "cycles_limit": 1,
    "protection_period_days": 7,
    "last_cycle_date": "2025-07-25T14:20:30",
    "days_until_reset": 5
  },
  "execution_time_ms": 0.8
}
```

### **Regime Transition Event**
```json
{
  "timestamp": "2025-07-27T10:35:12.345678",
  "event_type": "regime_transition",
  "event_category": "regime",
  "trace_id": "regime_check_20250727_103500",
  "session_id": "session_20250727_103000",
  "regime": "Inflation",
  "action": "transition",
  "reason": "Regime changed: Goldilocks → Inflation (confidence: 0.82)",
  "metadata": {
    "previous_regime": "Goldilocks",
    "new_regime": "Inflation",
    "transition_confidence": 0.82,
    "transition_severity": "high",
    "regime_indicators": {
      "vix": 18.5,
      "yield_curve": 1.2,
      "growth_momentum": 0.65
    },
    "override_authorizations": {
      "holding_period": true,
      "grace_period": true
    }
  },
  "execution_time_ms": 15.2
}
```

---

## 🔍 Essential Queries

### **Investigation Queries**

```sql
-- 1. Trace complete rebalancing session
SELECT * FROM portfolio_events 
WHERE session_id = 'session_20250727_103000' 
ORDER BY timestamp;

-- 2. Asset lifecycle for AAPL last 30 days
SELECT * FROM portfolio_events 
WHERE asset = 'AAPL' 
  AND timestamp >= datetime('now', '-30 days')
ORDER BY timestamp;

-- 3. All whipsaw blocks last week
SELECT asset, reason, timestamp, json_extract(metadata, '$.cycles_recent') as cycles
FROM portfolio_events 
WHERE event_type = 'whipsaw_block' 
  AND timestamp >= datetime('now', '-7 days')
ORDER BY timestamp DESC;

-- 4. Regime transitions with override impacts
SELECT regime, json_extract(metadata, '$.previous_regime') as prev_regime,
       json_extract(metadata, '$.transition_severity') as severity,
       timestamp
FROM portfolio_events 
WHERE event_type = 'regime_transition'
ORDER BY timestamp DESC;

-- 5. Protection system effectiveness
SELECT event_type, COUNT(*) as count, 
       AVG(execution_time_ms) as avg_time
FROM portfolio_events 
WHERE event_category = 'protection'
  AND timestamp >= datetime('now', '-7 days')
GROUP BY event_type;
```

### **Performance Analysis Queries**

```sql
-- Portfolio allocation over time
SELECT date(timestamp) as date,
       AVG(portfolio_allocation) as avg_allocation,
       AVG(active_positions) as avg_positions
FROM portfolio_events 
WHERE portfolio_allocation IS NOT NULL
GROUP BY date(timestamp)
ORDER BY date DESC;

-- Score threshold breaches
SELECT asset, COUNT(*) as breaches,
       AVG(score_before) as avg_score_before,
       AVG(score_after) as avg_score_after
FROM portfolio_events 
WHERE event_type = 'threshold_breach'
GROUP BY asset
ORDER BY breaches DESC;
```

---

## 🎯 Success Metrics

### **Operational Metrics**
- **Event Coverage**: 100% of all portfolio decisions logged
- **Performance Impact**: <1ms average logging overhead
- **Data Integrity**: Zero event loss, complete trace chains
- **Query Performance**: <100ms for typical investigation queries

### **Functional Metrics**
- **Audit Completeness**: Full reconstruction of any portfolio decision
- **Trace Accuracy**: 100% linkage of related events
- **Investigation Speed**: Find any issue root cause in <5 minutes
- **System Health**: Real-time monitoring of all protection systems

### **Integration Metrics**
- **Module Coverage**: All modules instrumented and logging
- **Event Consistency**: Standardized event format across all modules
- **Cross-Module Tracing**: Complete workflows traced across module boundaries
- **Alert Effectiveness**: Critical issues detected and alerted in real-time

---

## 🚀 Advanced Features (Future Enhancements)

### **Real-time Dashboard**
- Live portfolio state visualization
- Protection system status monitoring
- Performance metrics dashboard
- Alert management interface

### **Advanced Analytics**
- Pattern recognition in trading behavior
- Regime prediction based on event patterns
- Protection system optimization recommendations
- Performance attribution analysis

### **Integration Capabilities**
- Export to external monitoring systems
- API for real-time event streaming
- Integration with business intelligence tools
- Compliance reporting automation

---

**This comprehensive monitoring system will provide complete visibility into portfolio operations, enabling sophisticated analysis, debugging, and compliance while maintaining high performance and operational simplicity.** 🎯 