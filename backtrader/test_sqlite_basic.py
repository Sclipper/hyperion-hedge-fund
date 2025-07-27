#!/usr/bin/env python3

"""
Basic SQLite test for monitoring system.

This test verifies:
- SQLite database creation and schema
- Event storage and retrieval
- Basic performance characteristics
- Data integrity
"""

import os
import sys
import sqlite3
import json
import tempfile
import time
from datetime import datetime, timedelta

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

try:
    from monitoring.event_models import PortfolioEvent, EventQuery, create_portfolio_event
    from monitoring.event_store import EventStore
    from monitoring.event_writer import EventWriter
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the backtrader directory")
    sys.exit(1)


def test_basic_sqlite_functionality():
    """Test basic SQLite functionality for event storage"""
    
    print("="*60)
    print("BASIC SQLITE MONITORING SYSTEM TEST")
    print("="*60)
    
    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='_test.db')
    temp_db.close()
    
    try:
        print(f"\n1. Database Setup")
        print(f"   Database path: {temp_db.name}")
        
        # Initialize event store
        event_store = EventStore(temp_db.name)
        print(f"   ✓ Event store initialized")
        
        # Verify database schema
        with sqlite3.connect(temp_db.name) as conn:
            cursor = conn.cursor()
            
            # Check table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='portfolio_events'
            """)
            result = cursor.fetchone()
            assert result is not None, "portfolio_events table not found"
            print(f"   ✓ Table 'portfolio_events' exists")
            
            # Check indices
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name LIKE 'idx_%'
            """)
            indices = cursor.fetchall()
            assert len(indices) >= 5, f"Expected at least 5 indices, found {len(indices)}"
            print(f"   ✓ Found {len(indices)} indices")
        
        print(f"\n2. Event Creation and Storage")
        
        # Create test events
        test_events = []
        
        # Portfolio events
        for i in range(5):
            event = create_portfolio_event(
                event_type='position_open',
                action='open',
                reason=f'Test position {i+1}',
                asset=f'STOCK_{i+1}',
                score_after=0.7 + (i * 0.05),
                size_after=0.1 + (i * 0.02),
                portfolio_allocation=0.85 + (i * 0.02),
                active_positions=i + 1,
                metadata={
                    'test_id': i + 1,
                    'strategy': 'test_strategy',
                    'market_cap': 'large' if i < 3 else 'mid'
                }
            )
            test_events.append(event)
        
        # Protection events
        for i in range(3):
            event = create_portfolio_event(
                event_type='whipsaw_block',
                action='block',
                reason=f'Whipsaw protection activated for STOCK_{i+1}',
                asset=f'STOCK_{i+1}',
                metadata={
                    'protection_type': 'whipsaw',
                    'cycles_recent': 1,
                    'protection_period_days': 7
                }
            )
            test_events.append(event)
        
        # Regime events
        event = create_portfolio_event(
            event_type='regime_transition',
            action='transition',
            reason='Market regime changed from Goldilocks to Inflation',
            regime='Inflation',
            metadata={
                'previous_regime': 'Goldilocks',
                'confidence': 0.82,
                'vix': 22.5,
                'yield_curve': 0.8
            }
        )
        test_events.append(event)
        
        print(f"   Created {len(test_events)} test events")
        
        # Single event write test
        print(f"\n3. Single Event Write Test")
        start_time = time.time()
        
        for event in test_events[:3]:
            event_id = event_store.write_event(event)
            assert event_id > 0, "Event ID should be positive"
        
        single_write_time = (time.time() - start_time) * 1000
        print(f"   ✓ Wrote 3 events individually in {single_write_time:.2f}ms")
        print(f"   ✓ Average single write: {single_write_time/3:.2f}ms")
        
        # Batch write test
        print(f"\n4. Batch Write Test")
        start_time = time.time()
        
        batch_events = test_events[3:]  # Remaining events
        event_ids = event_store.write_events_batch(batch_events)
        
        batch_write_time = (time.time() - start_time) * 1000
        print(f"   ✓ Batch wrote {len(batch_events)} events in {batch_write_time:.2f}ms")
        print(f"   ✓ Average batch write: {batch_write_time/len(batch_events):.2f}ms per event")
        
        assert len(event_ids) == len(batch_events), "Batch write ID count mismatch"
        print(f"   ✓ All batch events received IDs")
        
        print(f"\n5. Data Retrieval Tests")
        
        # Query all events
        all_events = event_store.query_events(EventQuery())
        print(f"   ✓ Total events in database: {len(all_events)}")
        assert len(all_events) == len(test_events), f"Expected {len(test_events)} events, found {len(all_events)}"
        
        # Query by event type
        position_events = event_store.query_events(EventQuery(event_type='position_open'))
        print(f"   ✓ Position open events: {len(position_events)}")
        assert len(position_events) == 5
        
        # Query by category
        portfolio_events = event_store.query_events(EventQuery(event_category='portfolio'))
        protection_events = event_store.query_events(EventQuery(event_category='protection'))
        regime_events = event_store.query_events(EventQuery(event_category='regime'))
        
        print(f"   ✓ Portfolio events: {len(portfolio_events)}")
        print(f"   ✓ Protection events: {len(protection_events)}")
        print(f"   ✓ Regime events: {len(regime_events)}")
        
        # Query by asset
        stock1_events = event_store.query_events(EventQuery(asset='STOCK_1'))
        print(f"   ✓ STOCK_1 events: {len(stock1_events)}")
        assert len(stock1_events) >= 1
        
        # Query with time range
        recent_events = event_store.query_events(EventQuery(
            since=datetime.now() - timedelta(minutes=1)
        ))
        print(f"   ✓ Recent events (last minute): {len(recent_events)}")
        assert len(recent_events) == len(test_events)  # All events should be recent
        
        print(f"\n6. Data Integrity Tests")
        
        # Check event content integrity
        sample_event = position_events[0]
        print(f"   Sample event type: {sample_event['event_type']}")
        print(f"   Sample event asset: {sample_event['asset']}")
        print(f"   Sample event timestamp: {sample_event['timestamp']}")
        
        # Check metadata parsing
        if sample_event['metadata']:
            metadata = json.loads(sample_event['metadata'])
            print(f"   Sample metadata keys: {list(metadata.keys())}")
            assert 'test_id' in metadata, "Metadata should contain test_id"
        
        # Check numerical data
        assert sample_event['score_after'] is not None, "Score should not be None"
        assert sample_event['size_after'] is not None, "Size should not be None"
        assert sample_event['portfolio_allocation'] is not None, "Allocation should not be None"
        
        print(f"   ✓ Event data integrity verified")
        
        print(f"\n7. Database Statistics")
        
        stats = event_store.get_event_statistics(days=1)
        print(f"   Total events: {stats['total_events']}")
        print(f"   Events by category: {stats['events_by_category']}")
        print(f"   Events by type: {stats['events_by_type']}")
        print(f"   Average execution time: {stats['average_execution_time_ms']:.2f}ms")
        print(f"   Error count: {stats['error_count']}")
        
        print(f"\n8. Performance Stress Test")
        
        # Generate larger dataset for performance testing
        large_batch = []
        for i in range(100):
            event = create_portfolio_event(
                event_type='performance_test',
                action='test',
                reason=f'Performance test event {i}',
                asset=f'PERF_{i:03d}',
                score_after=0.5 + (i * 0.005),
                execution_time_ms=i * 0.1
            )
            large_batch.append(event)
        
        # Time the large batch write
        start_time = time.time()
        large_batch_ids = event_store.write_events_batch(large_batch)
        large_batch_time = (time.time() - start_time) * 1000
        
        print(f"   ✓ Large batch (100 events): {large_batch_time:.2f}ms")
        print(f"   ✓ Rate: {large_batch_time/100:.3f}ms per event")
        
        # Time a complex query
        start_time = time.time()
        complex_query_events = event_store.query_events(EventQuery(
            event_category='portfolio',
            since=datetime.now() - timedelta(hours=1),
            limit=50
        ))
        query_time = (time.time() - start_time) * 1000
        
        print(f"   ✓ Complex query: {query_time:.2f}ms ({len(complex_query_events)} results)")
        
        # Database size
        db_size = os.path.getsize(temp_db.name)
        total_events_final = len(event_store.query_events(EventQuery()))
        print(f"   ✓ Database size: {db_size} bytes ({total_events_final} events)")
        print(f"   ✓ Bytes per event: {db_size/total_events_final:.1f}")
        
        print(f"\n9. EventWriter Integration Test")
        
        # Test EventWriter with the same database
        event_writer = EventWriter(event_store)
        
        # Test session management
        session_id = event_writer.start_session("test_session")
        print(f"   ✓ Started session: {session_id}")
        
        # Test convenience methods
        event_writer.log_position_event(
            'position_adjust', 'TEST_ASSET', 'adjust', 'Test position adjustment',
            score_before=0.75, score_after=0.82, size_before=0.10, size_after=0.12
        )
        
        event_writer.log_protection_event(
            'grace_period', 'TEST_ASSET', 'start', 'Grace period started',
            metadata={'grace_days': 3, 'decay_rate': 0.8}
        )
        
        event_writer.log_regime_event(
            'regime_detection', 'Goldilocks', 'detect', 'Regime detection completed',
            metadata={'confidence': 0.85, 'indicators': {'vix': 18.0}}
        )
        
        event_writer.log_error(
            'test_error', 'This is a test error message', 'ERROR_ASSET',
            metadata={'severity': 'low', 'recoverable': True}
        )
        
        # End session
        event_writer.end_session({'events_logged': 4, 'success': True})
        print(f"   ✓ Session ended successfully")
        
        # Verify EventWriter events
        session_events = event_store.query_events(EventQuery(session_id=session_id))
        print(f"   ✓ Session events logged: {len(session_events)}")
        
        # Get final statistics
        final_stats = event_writer.get_performance_stats()
        print(f"   ✓ EventWriter performance:")
        print(f"     - Events written: {final_stats['events_written']}")
        print(f"     - Average write time: {final_stats['average_write_time_ms']:.3f}ms")
        
        print(f"\n" + "="*60)
        print("ALL TESTS PASSED SUCCESSFULLY! ✓")
        print("="*60)
        
        final_event_count = len(event_store.query_events(EventQuery()))
        final_db_size = os.path.getsize(temp_db.name)
        
        print(f"Final Statistics:")
        print(f"  Database file: {temp_db.name}")
        print(f"  Total events: {final_event_count}")
        print(f"  Database size: {final_db_size} bytes")
        print(f"  Average bytes per event: {final_db_size/final_event_count:.1f}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Clean up
        try:
            event_store.close_all_connections()
        except:
            pass
        
        # Ask user whether to keep the database
        keep_db = input(f"\nKeep test database for inspection? (y/N): ").lower().startswith('y')
        if not keep_db:
            try:
                os.unlink(temp_db.name)
                print(f"Test database cleaned up")
            except Exception as e:
                print(f"Could not clean up database: {e}")
        else:
            print(f"Test database preserved: {temp_db.name}")
            print(f"You can inspect it with any SQLite browser or:")
            print(f"  sqlite3 {temp_db.name}")
            print(f"  .tables")
            print(f"  .schema portfolio_events")
            print(f"  SELECT * FROM portfolio_events LIMIT 5;")


if __name__ == '__main__':
    success = test_basic_sqlite_functionality()
    sys.exit(0 if success else 1)