#!/usr/bin/env python3

"""
Comprehensive tests for the monitoring and event logging system.

Tests:
- SQLite event storage and retrieval
- Event writer functionality
- Enhanced protection managers
- Event querying and statistics
- Database performance
- Error handling
"""

import os
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import sqlite3
import time

# Import monitoring system components
from monitoring.event_models import (
    PortfolioEvent, EventQuery, create_portfolio_event, 
    EventStatistics, PORTFOLIO_EVENT_TYPES
)
from monitoring.event_store import EventStore
from monitoring.event_writer import EventWriter, EventManager
from core.enhanced_whipsaw_protection_manager import EnhancedWhipsawProtectionManager
from core.enhanced_grace_period_manager import EnhancedGracePeriodManager


class TestEventModels(unittest.TestCase):
    """Test event models and data structures"""
    
    def test_portfolio_event_creation(self):
        """Test creating and serializing portfolio events"""
        event = create_portfolio_event(
            event_type='position_open',
            action='open',
            reason='Test position opening',
            asset='AAPL',
            score_after=0.85,
            size_after=0.12,
            metadata={'test': 'data'}
        )
        
        self.assertIsInstance(event, PortfolioEvent)
        self.assertEqual(event.event_type, 'position_open')
        self.assertEqual(event.event_category, 'portfolio')
        self.assertEqual(event.asset, 'AAPL')
        self.assertEqual(event.score_after, 0.85)
        self.assertEqual(event.metadata['test'], 'data')
        
        # Test serialization
        db_tuple = event.to_db_tuple()
        self.assertEqual(len(db_tuple), 16)
        self.assertIn('position_open', db_tuple)
        self.assertIn('AAPL', db_tuple)
    
    def test_event_query_builder(self):
        """Test event query builder functionality"""
        query = EventQuery(
            event_type='position_open',
            asset='AAPL',
            since=datetime(2024, 1, 1),
            limit=10
        )
        
        sql, params = query.to_sql()
        
        self.assertIn('SELECT * FROM portfolio_events', sql)
        self.assertIn('WHERE', sql)
        self.assertIn('event_type = ?', sql)
        self.assertIn('asset = ?', sql)
        self.assertIn('timestamp >= ?', sql)
        self.assertIn('LIMIT 10', sql)
        
        self.assertEqual(len(params), 3)
        self.assertIn('position_open', params)
        self.assertIn('AAPL', params)
    
    def test_event_statistics(self):
        """Test event statistics calculation"""
        events = [
            {'event_category': 'portfolio', 'event_type': 'position_open', 'execution_time_ms': 10.0},
            {'event_category': 'portfolio', 'event_type': 'position_close', 'execution_time_ms': 15.0},
            {'event_category': 'protection', 'event_type': 'whipsaw_block', 'execution_time_ms': 5.0},
            {'event_category': 'error', 'event_type': 'scoring_error', 'execution_time_ms': 20.0}
        ]
        
        stats = EventStatistics.from_events(events)
        
        self.assertEqual(stats.total_events, 4)
        self.assertEqual(stats.events_by_category['portfolio'], 2)
        self.assertEqual(stats.events_by_category['protection'], 1)
        self.assertEqual(stats.error_count, 1)
        self.assertEqual(stats.average_execution_time_ms, 12.5)


class TestEventStore(unittest.TestCase):
    """Test SQLite event storage functionality"""
    
    def setUp(self):
        """Set up temporary database for testing"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.event_store = EventStore(self.temp_db.name)
    
    def tearDown(self):
        """Clean up temporary database"""
        self.event_store.close_all_connections()
        os.unlink(self.temp_db.name)
    
    def test_database_initialization(self):
        """Test database schema creation"""
        # Check if table exists
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='portfolio_events'
            """)
            result = cursor.fetchone()
            self.assertIsNotNone(result)
            
            # Check if indices exist
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name LIKE 'idx_%'
            """)
            indices = cursor.fetchall()
            self.assertGreater(len(indices), 5)  # Should have multiple indices
    
    def test_single_event_write_and_read(self):
        """Test writing and reading a single event"""
        event = create_portfolio_event(
            event_type='position_open',
            action='open',
            reason='Test position',
            asset='AAPL',
            score_after=0.85,
            size_after=0.12,
            portfolio_allocation=0.95,
            active_positions=5,
            metadata={'test': 'value', 'number': 42}
        )
        
        # Write event
        event_id = self.event_store.write_event(event)
        self.assertIsInstance(event_id, int)
        self.assertGreater(event_id, 0)
        
        # Read event back
        query = EventQuery(event_type='position_open', asset='AAPL')
        events = self.event_store.query_events(query)
        
        self.assertEqual(len(events), 1)
        retrieved_event = events[0]
        
        self.assertEqual(retrieved_event['event_type'], 'position_open')
        self.assertEqual(retrieved_event['asset'], 'AAPL')
        self.assertEqual(retrieved_event['score_after'], 0.85)
        self.assertEqual(retrieved_event['portfolio_allocation'], 0.95)
        
        # Check metadata parsing
        import json
        metadata = json.loads(retrieved_event['metadata'])
        self.assertEqual(metadata['test'], 'value')
        self.assertEqual(metadata['number'], 42)
    
    def test_batch_event_write(self):
        """Test batch writing of events"""
        events = []
        for i in range(100):
            event = create_portfolio_event(
                event_type='asset_scored',
                action='score',
                reason=f'Test asset {i}',
                asset=f'ASSET_{i:03d}',
                score_after=0.5 + (i * 0.005),
                execution_time_ms=i * 0.1
            )
            events.append(event)
        
        # Batch write
        start_time = time.time()
        event_ids = self.event_store.write_events_batch(events)
        write_time = time.time() - start_time
        
        self.assertEqual(len(event_ids), 100)
        self.assertTrue(all(isinstance(eid, int) for eid in event_ids))
        print(f"Batch write of 100 events took {write_time*1000:.2f}ms")
        
        # Verify all events were written
        query = EventQuery(event_type='asset_scored')
        retrieved_events = self.event_store.query_events(query)
        self.assertEqual(len(retrieved_events), 100)
    
    def test_event_querying(self):
        """Test various event querying scenarios"""
        # Create test events with different characteristics
        test_events = [
            create_portfolio_event('position_open', 'open', 'Test 1', asset='AAPL'),
            create_portfolio_event('position_close', 'close', 'Test 2', asset='AAPL'),
            create_portfolio_event('position_open', 'open', 'Test 3', asset='MSFT'),
            create_portfolio_event('whipsaw_block', 'block', 'Test 4', asset='TSLA'),
        ]
        
        # Write all events
        for event in test_events:
            self.event_store.write_event(event)
        
        # Test asset-specific query
        aapl_events = self.event_store.query_events(EventQuery(asset='AAPL'))
        self.assertEqual(len(aapl_events), 2)
        
        # Test event type query
        position_events = self.event_store.query_events(EventQuery(event_type='position_open'))
        self.assertEqual(len(position_events), 2)
        
        # Test category query
        protection_events = self.event_store.query_events(EventQuery(event_category='protection'))
        self.assertEqual(len(protection_events), 1)
        
        # Test date range query
        recent_events = self.event_store.query_events(EventQuery(
            since=datetime.now() - timedelta(minutes=1)
        ))
        self.assertEqual(len(recent_events), 4)
    
    def test_event_statistics(self):
        """Test event statistics generation"""
        # Create diverse events for statistics
        events = [
            create_portfolio_event('position_open', 'open', 'Test', execution_time_ms=10.0),
            create_portfolio_event('position_close', 'close', 'Test', execution_time_ms=15.0),
            create_portfolio_event('whipsaw_block', 'block', 'Test', execution_time_ms=5.0),
            create_portfolio_event('scoring_error', 'error', 'Test', execution_time_ms=20.0),
        ]
        
        for event in events:
            self.event_store.write_event(event)
        
        stats = self.event_store.get_event_statistics(days=1)
        
        self.assertEqual(stats['total_events'], 4)
        self.assertIn('portfolio', stats['events_by_category'])
        self.assertIn('protection', stats['events_by_category'])
        self.assertEqual(stats['error_count'], 1)
        self.assertGreater(stats['average_execution_time_ms'], 0)
    
    def test_database_performance(self):
        """Test database performance with larger datasets"""
        print("\n=== Database Performance Test ===")
        
        # Test single writes
        single_write_times = []
        for i in range(100):
            event = create_portfolio_event(
                'performance_test', 'test', f'Performance test {i}',
                asset=f'PERF_{i}', score_after=i * 0.01
            )
            
            start_time = time.time()
            self.event_store.write_event(event)
            write_time = (time.time() - start_time) * 1000
            single_write_times.append(write_time)
        
        avg_single_write = sum(single_write_times) / len(single_write_times)
        print(f"Average single write time: {avg_single_write:.3f}ms")
        
        # Test batch writes
        batch_events = []
        for i in range(1000):
            event = create_portfolio_event(
                'batch_test', 'test', f'Batch test {i}',
                asset=f'BATCH_{i}', score_after=i * 0.001
            )
            batch_events.append(event)
        
        start_time = time.time()
        self.event_store.write_events_batch(batch_events)
        batch_write_time = (time.time() - start_time) * 1000
        print(f"Batch write 1000 events: {batch_write_time:.2f}ms ({batch_write_time/1000:.3f}ms per event)")
        
        # Test query performance
        start_time = time.time()
        all_events = self.event_store.query_events(EventQuery(limit=500))
        query_time = (time.time() - start_time) * 1000
        print(f"Query 500 events: {query_time:.2f}ms")
        
        # Verify data integrity
        total_events = self.event_store.query_events(EventQuery())
        print(f"Total events in database: {len(total_events)}")
        self.assertGreater(len(total_events), 1000)


class TestEventWriter(unittest.TestCase):
    """Test event writer functionality"""
    
    def setUp(self):
        """Set up event writer with temporary database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.event_store = EventStore(self.temp_db.name)
        self.event_writer = EventWriter(self.event_store)
    
    def tearDown(self):
        """Clean up"""
        self.event_store.close_all_connections()
        os.unlink(self.temp_db.name)
    
    def test_session_management(self):
        """Test session lifecycle management"""
        # Start session
        session_id = self.event_writer.start_session("test_session")
        self.assertIsNotNone(session_id)
        self.assertEqual(self.event_writer.current_session_id, session_id)
        
        # Log some events during session
        self.event_writer.log_event(
            'test_event', 'system', 'test', 'Test event during session'
        )
        
        # End session
        self.event_writer.end_session({'test': 'stats'})
        self.assertIsNone(self.event_writer.current_session_id)
        
        # Verify session events were logged
        session_events = self.event_store.query_events(EventQuery(session_id=session_id))
        session_start_events = [e for e in session_events if e['event_type'] == 'session_start']
        session_end_events = [e for e in session_events if e['event_type'] == 'session_end']
        
        self.assertEqual(len(session_start_events), 1)
        self.assertEqual(len(session_end_events), 1)
    
    def test_trace_management(self):
        """Test trace management for related operations"""
        # Start trace
        trace_id = self.event_writer.start_trace("test_operation")
        self.assertIsNotNone(trace_id)
        self.assertIn(trace_id, self.event_writer.trace_stack)
        
        # Log events with automatic trace
        self.event_writer.log_event(
            'test_event_1', 'system', 'test', 'First test event'
        )
        self.event_writer.log_event(
            'test_event_2', 'system', 'test', 'Second test event'
        )
        
        # End trace
        self.event_writer.end_trace(trace_id, success=True, stats={'operations': 2})
        self.assertNotIn(trace_id, self.event_writer.trace_stack)
        
        # Verify all events have same trace ID
        trace_events = self.event_store.query_events(EventQuery(trace_id=trace_id))
        self.assertGreaterEqual(len(trace_events), 4)  # start, 2 events, end
        
        for event in trace_events:
            self.assertEqual(event['trace_id'], trace_id)
    
    def test_convenience_methods(self):
        """Test convenience logging methods"""
        # Test position event logging
        self.event_writer.log_position_event(
            'position_open', 'AAPL', 'open', 'Position opened',
            score_after=0.85, size_after=0.12
        )
        
        # Test protection event logging
        self.event_writer.log_protection_event(
            'whipsaw', 'TSLA', 'block', 'Position blocked by whipsaw protection'
        )
        
        # Test regime event logging
        self.event_writer.log_regime_event(
            'regime_transition', 'Goldilocks', 'transition', 'Regime changed'
        )
        
        # Test error logging
        self.event_writer.log_error(
            'scoring', 'Test error message', asset='MSFT'
        )
        
        # Verify all events were logged correctly
        portfolio_events = self.event_store.query_events(EventQuery(event_category='portfolio'))
        protection_events = self.event_store.query_events(EventQuery(event_category='protection'))
        regime_events = self.event_store.query_events(EventQuery(event_category='regime'))
        error_events = self.event_store.query_events(EventQuery(event_category='error'))
        
        self.assertEqual(len(portfolio_events), 1)
        self.assertEqual(len(protection_events), 1)
        self.assertEqual(len(regime_events), 1)
        self.assertEqual(len(error_events), 1)
    
    def test_batch_mode(self):
        """Test batch mode functionality"""
        # Create event writer in batch mode
        batch_writer = EventWriter(self.event_store, enable_batch_mode=True)
        
        # Log multiple events
        for i in range(50):
            batch_writer.log_event(
                'batch_test', 'system', 'test', f'Batch event {i}'
            )
        
        # Events should be batched, not immediately written
        all_events = self.event_store.query_events(EventQuery(event_type='batch_test'))
        self.assertEqual(len(all_events), 0)  # Not flushed yet
        
        # Flush batch
        batch_writer.flush_batch()
        
        # Now events should be in database
        all_events = self.event_store.query_events(EventQuery(event_type='batch_test'))
        self.assertEqual(len(all_events), 50)
    
    def test_performance_tracking(self):
        """Test performance statistics tracking"""
        # Log some events
        for i in range(10):
            self.event_writer.log_event(
                'perf_test', 'system', 'test', f'Performance test {i}'
            )
        
        # Get performance stats
        stats = self.event_writer.get_performance_stats()
        
        self.assertEqual(stats['events_written'], 10)
        self.assertGreater(stats['total_write_time_ms'], 0)
        self.assertGreater(stats['average_write_time_ms'], 0)
        self.assertFalse(stats['batch_mode'])
        self.assertTrue(stats['enabled'])


class TestEnhancedProtectionManagers(unittest.TestCase):
    """Test enhanced protection managers with event logging"""
    
    def setUp(self):
        """Set up protection managers with event logging"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.event_store = EventStore(self.temp_db.name)
        self.event_writer = EventWriter(self.event_store)
        
        self.whipsaw_manager = EnhancedWhipsawProtectionManager(
            max_cycles_per_period=1,
            protection_period_days=7,
            min_position_duration_hours=4,
            event_writer=self.event_writer
        )
        
        self.grace_manager = EnhancedGracePeriodManager(
            grace_period_days=3,
            decay_rate=0.8,
            event_writer=self.event_writer
        )
    
    def tearDown(self):
        """Clean up"""
        self.event_store.close_all_connections()
        os.unlink(self.temp_db.name)
    
    def test_whipsaw_protection_logging(self):
        """Test whipsaw protection with event logging"""
        current_date = datetime.now()
        
        # Test position opening (should be allowed)
        can_open, reason = self.whipsaw_manager.can_open_position('AAPL', current_date)
        self.assertTrue(can_open)
        
        # Record position opening
        self.whipsaw_manager.record_position_event(
            'AAPL', 'open', current_date, 0.15, 'Test position'
        )
        
        # Try to open again (should be blocked - already open)
        can_open, reason = self.whipsaw_manager.can_open_position('AAPL', current_date)
        self.assertFalse(can_open)
        
        # Test position closing too quickly (should be blocked)
        can_close, reason = self.whipsaw_manager.can_close_position(
            'AAPL', current_date, current_date + timedelta(hours=2)
        )
        self.assertFalse(can_close)
        
        # Test position closing after sufficient time (should be allowed)
        can_close, reason = self.whipsaw_manager.can_close_position(
            'AAPL', current_date, current_date + timedelta(hours=6)
        )
        self.assertTrue(can_close)
        
        # Verify events were logged
        whipsaw_events = self.event_store.query_events(EventQuery(event_category='protection'))
        self.assertGreater(len(whipsaw_events), 0)
        
        # Check specific event types
        block_events = [e for e in whipsaw_events if 'block' in e['action']]
        allow_events = [e for e in whipsaw_events if 'allow' in e['action']]
        
        self.assertGreater(len(block_events), 0)
        self.assertGreater(len(allow_events), 0)
    
    def test_grace_period_logging(self):
        """Test grace period management with event logging"""
        current_date = datetime.now()
        
        # Start grace period
        success = self.grace_manager.start_grace_period(
            'AAPL', 0.55, 0.12, current_date, 'Score below threshold'
        )
        self.assertTrue(success)
        
        # Apply decay
        new_size, reason = self.grace_manager.apply_decay('AAPL', current_date + timedelta(days=1))
        self.assertLess(new_size, 0.12)
        self.assertGreater(new_size, 0)
        
        # End grace period
        success = self.grace_manager.end_grace_period('AAPL', current_date + timedelta(days=2))
        self.assertTrue(success)
        
        # Verify grace period events were logged
        grace_events = self.event_store.query_events(
            EventQuery(asset='AAPL', event_category='protection')
        )
        self.assertGreater(len(grace_events), 0)
        
        # Check for specific event types
        start_events = [e for e in grace_events if e['event_type'] == 'grace_period_start']
        end_events = [e for e in grace_events if e['event_type'] == 'grace_period_end']
        decay_events = self.event_store.query_events(
            EventQuery(asset='AAPL', event_type='position_decay')
        )
        
        self.assertEqual(len(start_events), 1)
        self.assertEqual(len(end_events), 1)
        self.assertGreater(len(decay_events), 0)
    
    def test_protection_performance_stats(self):
        """Test protection manager performance statistics"""
        current_date = datetime.now()
        
        # Generate some protection activity
        for i in range(5):
            asset = f'TEST_{i}'
            self.whipsaw_manager.can_open_position(asset, current_date)
            self.grace_manager.should_apply_grace_period(asset, 0.5, 0.6, current_date)
        
        # Get performance stats
        whipsaw_stats = self.whipsaw_manager.get_performance_statistics()
        grace_stats = self.grace_manager.get_performance_statistics()
        
        self.assertEqual(whipsaw_stats['total_checks'], 5)
        self.assertEqual(grace_stats['total_checks'], 5)
        self.assertIn('configuration', whipsaw_stats)
        self.assertIn('configuration', grace_stats)


class TestEventManagerSingleton(unittest.TestCase):
    """Test the global event manager singleton"""
    
    def test_singleton_behavior(self):
        """Test that EventManager is a singleton"""
        manager1 = EventManager()
        manager2 = EventManager()
        
        self.assertIs(manager1, manager2)
        self.assertIs(manager1.event_writer, manager2.event_writer)
    
    def test_configuration(self):
        """Test event manager configuration"""
        manager = EventManager()
        
        # Configure with temporary database
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        try:
            manager.configure(db_path=temp_db.name, enable_batch_mode=True)
            
            self.assertEqual(manager.event_writer.event_store.db_path, temp_db.name)
            self.assertTrue(manager.event_writer.enable_batch_mode)
        finally:
            os.unlink(temp_db.name)


def run_all_tests():
    """Run all monitoring system tests"""
    print("="*80)
    print("MONITORING SYSTEM COMPREHENSIVE TESTS")
    print("="*80)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestEventModels,
        TestEventStore,
        TestEventWriter,
        TestEnhancedProtectionManagers,
        TestEventManagerSingleton
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    # Set up path for imports
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    
    success = run_all_tests()
    sys.exit(0 if success else 1)