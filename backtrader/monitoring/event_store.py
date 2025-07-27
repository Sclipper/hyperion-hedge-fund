import sqlite3
import threading
from contextlib import contextmanager
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from .event_models import PortfolioEvent, EventQuery


class EventStore:
    """High-performance SQLite event storage with connection pooling"""
    
    def __init__(self, db_path: str = "portfolio_events.db", pool_size: int = 5):
        self.db_path = db_path
        self.pool_size = pool_size
        self._connections = []
        self._lock = threading.Lock()
        self._local = threading.local()
        
        self._initialize_schema()
    
    def _initialize_schema(self):
        """Initialize database schema"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_events (
                    -- Primary identification
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    
                    -- Event classification
                    event_type VARCHAR(50) NOT NULL,
                    event_category VARCHAR(30) NOT NULL,
                    
                    -- Tracing and context
                    trace_id VARCHAR(36) NOT NULL,
                    session_id VARCHAR(36) NOT NULL,
                    
                    -- Core identifiers
                    asset VARCHAR(20),
                    regime VARCHAR(20),
                    
                    -- Event details
                    action VARCHAR(30),
                    reason TEXT NOT NULL,
                    
                    -- Quantitative data
                    score_before DECIMAL(5,3),
                    score_after DECIMAL(5,3),
                    size_before DECIMAL(6,4),
                    size_after DECIMAL(6,4),
                    
                    -- System state
                    portfolio_allocation DECIMAL(5,3),
                    active_positions INTEGER,
                    
                    -- Flexible metadata (JSON)
                    metadata TEXT,
                    
                    -- Performance tracking
                    execution_time_ms DECIMAL(8,2)
                )
            """)
            
            # Create indices for performance
            indices = [
                "CREATE INDEX IF NOT EXISTS idx_timestamp ON portfolio_events(timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_event_type ON portfolio_events(event_type)",
                "CREATE INDEX IF NOT EXISTS idx_trace_id ON portfolio_events(trace_id)",
                "CREATE INDEX IF NOT EXISTS idx_asset ON portfolio_events(asset)",
                "CREATE INDEX IF NOT EXISTS idx_session ON portfolio_events(session_id)",
                "CREATE INDEX IF NOT EXISTS idx_category ON portfolio_events(event_category)",
                "CREATE INDEX IF NOT EXISTS idx_action ON portfolio_events(action)"
            ]
            
            for index_sql in indices:
                cursor.execute(index_sql)
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with automatic cleanup"""
        conn = None
        try:
            # Try to get existing connection for this thread
            if hasattr(self._local, 'connection'):
                conn = self._local.connection
            else:
                conn = sqlite3.connect(self.db_path, timeout=30.0)
                conn.row_factory = sqlite3.Row  # Enable dict-like access
                self._local.connection = conn
            
            yield conn
            
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            # Don't close connection - keep it for thread reuse
            pass
    
    def write_event(self, event: PortfolioEvent) -> int:
        """Write event to database with performance optimization"""
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
        """Batch write for high-performance bulk operations"""
        if not events:
            return []
        
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
            
            # Get generated IDs - handle case where lastrowid might be None
            last_id = cursor.lastrowid
            if last_id is None:
                # Fallback: query for the IDs
                cursor.execute("SELECT seq FROM sqlite_sequence WHERE name='portfolio_events'")
                result = cursor.fetchone()
                if result:
                    last_id = result[0]
                    event_ids = list(range(last_id - len(events) + 1, last_id + 1))
                else:
                    # If we can't get IDs, return dummy IDs
                    event_ids = list(range(1, len(events) + 1))
            else:
                first_id = last_id - len(events) + 1
                event_ids = list(range(first_id, last_id + 1))
            
            conn.commit()
            return event_ids
    
    def query_events(self, query: EventQuery) -> List[Dict[str, Any]]:
        """Query events with optimized filters"""
        sql, params = query.to_sql()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_trace_events(self, trace_id: str) -> List[Dict[str, Any]]:
        """Get all events for a specific trace ID (transaction)"""
        return self.query_events(EventQuery(trace_id=trace_id))
    
    def get_asset_timeline(self, asset: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get chronological timeline for specific asset"""
        return self.query_events(
            EventQuery(
                asset=asset,
                since=datetime.now() - timedelta(days=days)
            ).order_by('timestamp')
        )
    
    def get_session_events(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all events for a rebalancing session"""
        return self.query_events(
            EventQuery(session_id=session_id).order_by('timestamp')
        )
    
    def get_recent_events(self, hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent events for monitoring dashboard"""
        return self.query_events(
            EventQuery(
                since=datetime.now() - timedelta(hours=hours),
                limit=limit
            )
        )
    
    def get_error_events(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get all error events for investigation"""
        return self.query_events(
            EventQuery(
                event_category='error',
                since=datetime.now() - timedelta(days=days)
            )
        )
    
    def get_protection_events(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get all protection system events"""
        return self.query_events(
            EventQuery(
                event_category='protection',
                since=datetime.now() - timedelta(days=days)
            )
        )
    
    def get_regime_transitions(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get regime transition events"""
        return self.query_events(
            EventQuery(
                event_type='regime_transition',
                since=datetime.now() - timedelta(days=days)
            )
        )
    
    def get_event_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get event statistics for monitoring"""
        since = datetime.now() - timedelta(days=days)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Total events
            cursor.execute("""
                SELECT COUNT(*) as total FROM portfolio_events 
                WHERE timestamp >= ?
            """, (since.isoformat(),))
            total_events = cursor.fetchone()[0]
            
            # Events by category
            cursor.execute("""
                SELECT event_category, COUNT(*) as count 
                FROM portfolio_events 
                WHERE timestamp >= ?
                GROUP BY event_category
            """, (since.isoformat(),))
            events_by_category = dict(cursor.fetchall())
            
            # Events by type
            cursor.execute("""
                SELECT event_type, COUNT(*) as count 
                FROM portfolio_events 
                WHERE timestamp >= ?
                GROUP BY event_type
                ORDER BY count DESC
                LIMIT 10
            """, (since.isoformat(),))
            events_by_type = dict(cursor.fetchall())
            
            # Average execution time
            cursor.execute("""
                SELECT AVG(execution_time_ms) as avg_time 
                FROM portfolio_events 
                WHERE timestamp >= ? AND execution_time_ms IS NOT NULL
            """, (since.isoformat(),))
            avg_execution_time = cursor.fetchone()[0] or 0.0
            
            # Error count
            cursor.execute("""
                SELECT COUNT(*) as errors FROM portfolio_events 
                WHERE timestamp >= ? AND event_category = 'error'
            """, (since.isoformat(),))
            error_count = cursor.fetchone()[0]
            
            # Protection blocks
            cursor.execute("""
                SELECT COUNT(*) as blocks FROM portfolio_events 
                WHERE timestamp >= ? AND action = 'block'
            """, (since.isoformat(),))
            protection_blocks = cursor.fetchone()[0]
            
            return {
                'total_events': total_events,
                'events_by_category': events_by_category,
                'events_by_type': events_by_type,
                'average_execution_time_ms': avg_execution_time,
                'error_count': error_count,
                'protection_blocks_count': protection_blocks,
                'period_days': days
            }
    
    def cleanup_old_events(self, days_to_keep: int = 365):
        """Clean up old events to manage database size"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM portfolio_events 
                WHERE timestamp < ?
            """, (cutoff_date.isoformat(),))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            # Vacuum to reclaim space
            cursor.execute("VACUUM")
            
            return deleted_count
    
    def close_all_connections(self):
        """Close all database connections"""
        with self._lock:
            if hasattr(self._local, 'connection'):
                self._local.connection.close()
                delattr(self._local, 'connection')