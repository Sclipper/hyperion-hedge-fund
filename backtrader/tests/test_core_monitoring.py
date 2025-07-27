#!/usr/bin/env python3

"""
Core monitoring system tests focused on event storage and writing.

Tests the fundamental components:
- Event models and creation
- SQLite event storage
- Event writer functionality
- Query performance
- Error handling
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
import time
import json

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from monitoring.event_models import (
    PortfolioEvent, EventQuery, create_portfolio_event, 
    EventStatistics, PORTFOLIO_EVENT_TYPES
)
from monitoring.event_store import EventStore
from monitoring.event_writer import EventWriter, EventManager


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
        self.assertEqual(len(db_tuple), 17)  # Updated to match actual tuple size
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
        import sqlite3
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
        metadata = json.loads(retrieved_event['metadata'])
        self.assertEqual(metadata['test'], 'value')
        self.assertEqual(metadata['number'], 42)
    
    def test_batch_event_write(self):
        """Test batch writing of events"""
        events = []
        for i in range(50):
            event = create_portfolio_event(
                event_type='asset_scored',
                action='score',
                reason=f'Test asset {i}',
                asset=f'ASSET_{i:03d}',
                score_after=0.5 + (i * 0.01),
                execution_time_ms=i * 0.1
            )
            events.append(event)
        
        # Batch write
        start_time = time.time()
        event_ids = self.event_store.write_events_batch(events)
        write_time = time.time() - start_time
        
        self.assertEqual(len(event_ids), 50)
        self.assertTrue(all(isinstance(eid, int) for eid in event_ids))
        print(f"Batch write of 50 events took {write_time*1000:.2f}ms")
        
        # Verify all events were written
        query = EventQuery(event_type='asset_scored')
        retrieved_events = self.event_store.query_events(query)
        self.assertEqual(len(retrieved_events), 50)
    
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


class TestPerformance(unittest.TestCase):
    """Test performance characteristics"""
    
    def setUp(self):
        """Set up for performance testing"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.event_store = EventStore(self.temp_db.name)
        self.event_writer = EventWriter(self.event_store)
    
    def tearDown(self):
        """Clean up"""
        self.event_store.close_all_connections()
        os.unlink(self.temp_db.name)
    
    def test_write_performance(self):
        """Test write performance under load"""
        print("\n=== Write Performance Test ===")
        
        # Test single writes
        events = []
        for i in range(100):
            event = create_portfolio_event(
                'performance_test', 'test', f'Performance test {i}',
                asset=f'PERF_{i}', score_after=i * 0.01
            )
            events.append(event)
        
        # Single writes
        start_time = time.time()
        for event in events[:50]:
            self.event_store.write_event(event)
        single_write_time = (time.time() - start_time) * 1000
        
        # Batch writes
        start_time = time.time()
        self.event_store.write_events_batch(events[50:])
        batch_write_time = (time.time() - start_time) * 1000
        
        print(f"Single writes (50 events): {single_write_time:.2f}ms ({single_write_time/50:.3f}ms each)")
        print(f"Batch write (50 events): {batch_write_time:.2f}ms ({batch_write_time/50:.3f}ms each)")
        
        # Batch should be faster per event
        self.assertLess(batch_write_time/50, single_write_time/50 * 1.5)  # Allow some tolerance
    
    def test_query_performance(self):
        """Test query performance"""
        print("\n=== Query Performance Test ===")
        
        # Create larger dataset
        events = []
        for i in range(500):
            event = create_portfolio_event(
                'query_test', 'test', f'Query test {i}',
                asset=f'QUERY_{i % 20}',  # 20 different assets
                score_after=i * 0.002,
                execution_time_ms=i * 0.1
            )
            events.append(event)
        
        # Write all events
        self.event_store.write_events_batch(events)
        
        # Test different query types
        queries = [
            ("All events", EventQuery()),
            ("By event type", EventQuery(event_type='query_test')),
            ("By asset", EventQuery(asset='QUERY_5')),
            ("Recent events", EventQuery(since=datetime.now() - timedelta(minutes=1))),
            ("Limited results", EventQuery(limit=50)),
        ]
        
        for description, query in queries:
            start_time = time.time()
            results = self.event_store.query_events(query)
            query_time = (time.time() - start_time) * 1000
            
            print(f"{description}: {len(results)} results in {query_time:.2f}ms")
            
            # All queries should complete quickly
            self.assertLess(query_time, 100)  # Less than 100ms


def run_core_tests():
    """Run core monitoring system tests"""
    print("="*80)
    print("CORE MONITORING SYSTEM TESTS")
    print("="*80)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestEventModels,
        TestEventStore,
        TestEventWriter,
        TestPerformance
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
    
    if result.testsRun > 0:
        success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100)
        print(f"Success rate: {success_rate:.1f}%")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}")
            print(f"  {traceback}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}")
            print(f"  {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    
    if success:
        print("\n🎉 ALL CORE TESTS PASSED! 🎉")
    else:
        print("\n❌ Some tests failed")
    
    return success


if __name__ == '__main__':
    success = run_core_tests()
    sys.exit(0 if success else 1)