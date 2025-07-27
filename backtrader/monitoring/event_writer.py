import time
import uuid
import functools
from typing import Dict, List, Optional, Any
from datetime import datetime
from .event_store import EventStore
from .event_models import PortfolioEvent, create_portfolio_event


class EventWriter:
    """Centralized event logging with trace management and performance optimization"""
    
    def __init__(self, event_store: EventStore = None, enable_batch_mode: bool = False):
        self.event_store = event_store or EventStore()
        self.enable_batch_mode = enable_batch_mode
        self.batch_events: List[PortfolioEvent] = []
        self.batch_size = 100
        self.current_session_id = None
        self.trace_stack: List[str] = []  # For nested operations
        
        # Performance tracking
        self.events_written = 0
        self.total_write_time = 0.0
        self._enabled = True
    
    def enable(self):
        """Enable event logging"""
        self._enabled = True
    
    def disable(self):
        """Disable event logging (for testing or performance)"""
        self._enabled = False
    
    def start_session(self, session_type: str = "rebalancing") -> str:
        """Start new session and return session ID"""
        if not self._enabled:
            return "disabled"
        
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
        """End current session with statistics"""
        if not self._enabled or not self.current_session_id:
            return
        
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
        """Start new trace for related operations"""
        if not self._enabled:
            return "disabled"
        
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
        """End trace with success status and statistics"""
        if not self._enabled:
            return
        
        if trace_id is None and self.trace_stack:
            trace_id = self.trace_stack.pop()
        elif trace_id in self.trace_stack:
            self.trace_stack.remove(trace_id)
        
        if trace_id and trace_id != "disabled":
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
                  portfolio_allocation: float = None, active_positions: int = None,
                  metadata: Dict[str, Any] = None, execution_time_ms: float = None) -> int:
        """Log single event with automatic trace and session management"""
        
        if not self._enabled:
            return 0
        
        # Use current trace if none specified
        if trace_id is None and self.trace_stack:
            trace_id = self.trace_stack[-1]
        elif trace_id is None:
            trace_id = str(uuid.uuid4())  # Generate new trace for standalone events
        
        event = create_portfolio_event(
            event_type=event_type,
            action=action,
            reason=reason,
            trace_id=trace_id,
            session_id=self.current_session_id or 'no_session',
            asset=asset,
            regime=regime,
            score_before=score_before,
            score_after=score_after,
            size_before=size_before,
            size_after=size_after,
            portfolio_allocation=portfolio_allocation,
            active_positions=active_positions,
            metadata=metadata,
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
    
    def log_position_event(self, event_type: str, asset: str, action: str, reason: str,
                          score_before: float = None, score_after: float = None,
                          size_before: float = None, size_after: float = None,
                          regime: str = None, metadata: Dict[str, Any] = None):
        """Convenience method for position events"""
        return self.log_event(
            event_type=event_type,
            event_category='portfolio',
            action=action,
            reason=reason,
            asset=asset,
            regime=regime,
            score_before=score_before,
            score_after=score_after,
            size_before=size_before,
            size_after=size_after,
            metadata=metadata
        )
    
    def log_protection_event(self, protection_type: str, asset: str, action: str, reason: str,
                           metadata: Dict[str, Any] = None):
        """Convenience method for protection system events"""
        return self.log_event(
            event_type=f'{protection_type}_block' if action == 'block' else f'{protection_type}_{action}',
            event_category='protection',
            action=action,
            reason=reason,
            asset=asset,
            metadata=metadata
        )
    
    def log_regime_event(self, event_type: str, regime: str, action: str, reason: str,
                        metadata: Dict[str, Any] = None):
        """Convenience method for regime events"""
        return self.log_event(
            event_type=event_type,
            event_category='regime',
            action=action,
            reason=reason,
            regime=regime,
            metadata=metadata
        )
    
    def log_error(self, error_type: str, error_message: str, asset: str = None,
                 metadata: Dict[str, Any] = None):
        """Convenience method for error logging"""
        return self.log_event(
            event_type=f'{error_type}_error',
            event_category='error',
            action='error',
            reason=error_message,
            asset=asset,
            metadata=metadata
        )
    
    def flush_batch(self):
        """Flush all batched events to storage"""
        if not self._enabled or not self.batch_events:
            return
        
        start_time = time.time()
        self.event_store.write_events_batch(self.batch_events)
        write_time = (time.time() - start_time) * 1000
        
        self.events_written += len(self.batch_events)
        self.total_write_time += write_time
        
        print(f"Flushed {len(self.batch_events)} events in {write_time:.2f}ms")
        self.batch_events = []
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get event writing performance statistics"""
        avg_time = self.total_write_time / max(self.events_written, 1)
        
        return {
            'events_written': self.events_written,
            'total_write_time_ms': self.total_write_time,
            'average_write_time_ms': avg_time,
            'batch_mode': self.enable_batch_mode,
            'pending_batch_events': len(self.batch_events),
            'enabled': self._enabled
        }
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        if self.enable_batch_mode:
            self.flush_batch()


def log_portfolio_event(event_type: str, event_category: str = 'portfolio'):
    """Decorator to automatically log portfolio events"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Check if the object has an event_writer
            if not hasattr(self, 'event_writer') or not self.event_writer._enabled:
                return func(self, *args, **kwargs)
            
            # Extract context
            asset = kwargs.get('asset') or (args[0] if args and isinstance(args[0], str) else None)
            trace_id = getattr(self, '_current_trace_id', None)
            
            start_time = time.time()
            
            try:
                # Execute function
                result = func(self, *args, **kwargs)
                
                execution_time = (time.time() - start_time) * 1000
                
                # Log successful event
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


class EventManager:
    """Singleton event manager for application-wide event logging"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.event_writer = EventWriter()
            self._initialized = True
    
    @property
    def writer(self) -> EventWriter:
        """Get the event writer instance"""
        return self.event_writer
    
    def configure(self, db_path: str = None, enable_batch_mode: bool = False):
        """Configure the event system"""
        if db_path:
            self.event_writer.event_store = EventStore(db_path)
        self.event_writer.enable_batch_mode = enable_batch_mode
    
    def shutdown(self):
        """Shutdown event system and cleanup"""
        if self.event_writer.enable_batch_mode:
            self.event_writer.flush_batch()
        self.event_writer.event_store.close_all_connections()


# Global event manager instance
event_manager = EventManager()


def get_event_writer() -> EventWriter:
    """Get the global event writer instance"""
    return event_manager.writer