#!/usr/bin/env python3

"""
Integration test for monitoring system with real backtrader components.

This test demonstrates:
- Event logging integration with existing components
- SQLite database creation and usage
- Real portfolio rebalancing with event tracking
- Protection system event logging
- Performance measurement
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

# Import monitoring components
from monitoring.event_store import EventStore
from monitoring.event_writer import EventWriter, EventManager
from monitoring.event_models import EventQuery

# Import enhanced components
from core.enhanced_whipsaw_protection_manager import EnhancedWhipsawProtectionManager
from core.enhanced_grace_period_manager import EnhancedGracePeriodManager

# Import existing backtrader components
from data.regime_detector import RegimeDetector
from data.asset_buckets import AssetBucketManager


def test_event_logging_integration():
    """Test event logging integration with existing components"""
    
    print("="*60)
    print("MONITORING SYSTEM INTEGRATION TEST")
    print("="*60)
    
    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='_test_events.db')
    temp_db.close()
    
    try:
        # Initialize event system
        print(f"\n1. Initializing event system...")
        event_store = EventStore(temp_db.name)
        event_writer = EventWriter(event_store)
        
        print(f"   Database created: {temp_db.name}")
        print(f"   Event store initialized successfully")
        
        # Test session management
        print(f"\n2. Testing session management...")
        session_id = event_writer.start_session("integration_test")
        print(f"   Session started: {session_id}")
        
        # Test basic event logging
        print(f"\n3. Testing basic event logging...")
        
        event_writer.log_event(
            event_type='integration_test_start',
            event_category='system',
            action='start',
            reason='Integration test started',
            metadata={
                'test_type': 'integration',
                'components': ['event_store', 'event_writer', 'protection_managers']
            }
        )
        
        # Test position events
        test_assets = ['AAPL', 'MSFT', 'NVDA', 'TSLA']
        for i, asset in enumerate(test_assets):
            event_writer.log_position_event(
                event_type='position_open',
                asset=asset,
                action='open',
                reason=f'Test position {i+1}',
                score_after=0.7 + (i * 0.05),
                size_after=0.1 + (i * 0.02)
            )
        
        print(f"   Logged {len(test_assets)} position events")
        
        # Initialize protection managers with event logging
        print(f"\n4. Testing protection managers with event logging...")
        
        whipsaw_manager = EnhancedWhipsawProtectionManager(
            max_cycles_per_period=1,
            protection_period_days=7,
            min_position_duration_hours=4,
            event_writer=event_writer
        )
        
        grace_manager = EnhancedGracePeriodManager(
            grace_period_days=3,
            decay_rate=0.8,
            event_writer=event_writer
        )
        
        print(f"   Protection managers initialized")
        
        # Test whipsaw protection
        current_date = datetime.now()
        
        for asset in test_assets:
            can_open, reason = whipsaw_manager.can_open_position(asset, current_date)
            print(f"   Whipsaw check {asset}: {'ALLOW' if can_open else 'BLOCK'} - {reason}")
            
            if can_open:
                whipsaw_manager.record_position_event(
                    asset, 'open', current_date, 0.15, f'Test position for {asset}'
                )
        
        # Test grace period management
        print(f"\n5. Testing grace period management...")
        
        for i, asset in enumerate(test_assets[:2]):  # Test on 2 assets
            low_score = 0.55 + (i * 0.02)
            
            should_apply, reason = grace_manager.should_apply_grace_period(
                asset, low_score, 0.6, current_date
            )
            
            print(f"   Grace period check {asset}: {'APPLY' if should_apply else 'SKIP'} - {reason}")
            
            if should_apply:
                grace_manager.start_grace_period(
                    asset, low_score, 0.12, current_date, 'Score below threshold'
                )
                
                # Apply decay
                new_size, decay_reason = grace_manager.apply_decay(
                    asset, current_date + timedelta(days=1)
                )
                print(f"   Grace decay {asset}: {0.12:.3f} -> {new_size:.3f} ({decay_reason})")
        
        # Test regime events
        print(f"\n6. Testing regime event logging...")
        
        try:
            regime_detector = RegimeDetector()
            
            event_writer.log_regime_event(
                event_type='regime_detection',
                regime='Goldilocks',
                action='detect',
                reason='Regime detection completed',
                metadata={
                    'vix': 18.5,
                    'yield_curve': 1.2,
                    'confidence': 0.82
                }
            )
            
            print(f"   Regime event logged")
            
        except Exception as e:
            print(f"   Regime detector not available: {e}")
        
        # Test error logging
        print(f"\n7. Testing error logging...")
        
        event_writer.log_error(
            error_type='integration_test',
            error_message='This is a test error for integration testing',
            asset='TEST_ASSET',
            metadata={
                'error_severity': 'low',
                'test_context': 'integration_test'
            }
        )
        
        print(f"   Error event logged")
        
        # End session
        event_writer.end_session({
            'total_test_events': len(test_assets) + 6,
            'protection_tests': len(test_assets),
            'success': True
        })
        
        print(f"   Session ended: {session_id}")
        
        # Query and analyze events
        print(f"\n8. Querying and analyzing events...")
        
        # Get all events
        all_events = event_store.query_events(EventQuery())
        print(f"   Total events in database: {len(all_events)}")
        
        # Get events by category
        categories = ['portfolio', 'protection', 'regime', 'system', 'error']
        for category in categories:
            category_events = event_store.query_events(EventQuery(event_category=category))
            print(f"   {category.capitalize()} events: {len(category_events)}")
        
        # Get session events
        session_events = event_store.query_events(EventQuery(session_id=session_id))
        print(f"   Session events: {len(session_events)}")
        
        # Get asset-specific events
        for asset in test_assets[:2]:
            asset_events = event_store.query_events(EventQuery(asset=asset))
            print(f"   {asset} events: {len(asset_events)}")
        
        # Test database statistics
        print(f"\n9. Database statistics...")
        
        stats = event_store.get_event_statistics(days=1)
        print(f"   Events by category: {stats['events_by_category']}")
        print(f"   Average execution time: {stats['average_execution_time_ms']:.2f}ms")
        print(f"   Error count: {stats['error_count']}")
        
        # Test performance metrics
        print(f"\n10. Performance metrics...")
        
        writer_stats = event_writer.get_performance_stats()
        print(f"   Events written: {writer_stats['events_written']}")
        print(f"   Total write time: {writer_stats['total_write_time_ms']:.2f}ms")
        print(f"   Average write time: {writer_stats['average_write_time_ms']:.3f}ms")
        
        whipsaw_stats = whipsaw_manager.get_performance_statistics()
        grace_stats = grace_manager.get_performance_statistics()
        
        print(f"   Whipsaw protection checks: {whipsaw_stats['total_checks']}")
        print(f"   Grace period checks: {grace_stats['total_checks']}")
        
        # Demonstrate event querying capabilities
        print(f"\n11. Advanced querying examples...")
        
        # Recent events
        recent_events = event_store.get_recent_events(hours=1, limit=10)
        print(f"   Recent events (last hour): {len(recent_events)}")
        
        # Protection events
        protection_events = event_store.get_protection_events(days=1)
        print(f"   Protection events: {len(protection_events)}")
        
        # Error events
        error_events = event_store.get_error_events(days=1)
        print(f"   Error events: {len(error_events)}")
        
        # Show sample events
        print(f"\n12. Sample events...")
        
        if len(all_events) >= 3:
            print(f"   Sample portfolio event:")
            portfolio_event = next((e for e in all_events if e['event_category'] == 'portfolio'), None)
            if portfolio_event:
                print(f"      Type: {portfolio_event['event_type']}")
                print(f"      Asset: {portfolio_event['asset']}")
                print(f"      Action: {portfolio_event['action']}")
                print(f"      Reason: {portfolio_event['reason']}")
                print(f"      Timestamp: {portfolio_event['timestamp']}")
            
            print(f"   Sample protection event:")
            protection_event = next((e for e in all_events if e['event_category'] == 'protection'), None)
            if protection_event:
                print(f"      Type: {protection_event['event_type']}")
                print(f"      Asset: {protection_event['asset']}")
                print(f"      Action: {protection_event['action']}")
                print(f"      Reason: {protection_event['reason']}")
        
        print(f"\n" + "="*60)
        print("INTEGRATION TEST COMPLETED SUCCESSFULLY")
        print("="*60)
        print(f"Database file: {temp_db.name}")
        print(f"Total events logged: {len(all_events)}")
        print(f"Database size: {os.path.getsize(temp_db.name)} bytes")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Clean up
        try:
            event_store.close_all_connections()
        except:
            pass
        
        # Optionally keep database for inspection
        keep_db = input(f"\nKeep test database for inspection? (y/N): ").lower().startswith('y')
        if not keep_db:
            try:
                os.unlink(temp_db.name)
                print(f"Test database cleaned up")
            except:
                print(f"Could not clean up database: {temp_db.name}")
        else:
            print(f"Test database preserved: {temp_db.name}")


def test_database_inspection():
    """Simple database inspection utility"""
    
    db_path = input("Enter database path to inspect (or press Enter to skip): ").strip()
    if not db_path or not os.path.exists(db_path):
        print("No valid database path provided or file doesn't exist")
        return
    
    try:
        print(f"\n" + "="*60)
        print(f"DATABASE INSPECTION: {db_path}")
        print("="*60)
        
        event_store = EventStore(db_path)
        
        # Basic statistics
        stats = event_store.get_event_statistics(days=30)
        print(f"Total events (last 30 days): {stats['total_events']}")
        print(f"Events by category: {stats['events_by_category']}")
        print(f"Average execution time: {stats['average_execution_time_ms']:.2f}ms")
        
        # Recent events
        recent = event_store.get_recent_events(hours=24, limit=5)
        print(f"\nRecent events (last 24 hours): {len(recent)}")
        for event in recent[:3]:
            print(f"  - {event['timestamp']} | {event['event_type']} | {event.get('asset', 'N/A')} | {event['reason'][:50]}...")
        
        # Event types
        all_events = event_store.query_events(EventQuery(limit=1000))
        event_types = {}
        for event in all_events:
            event_types[event['event_type']] = event_types.get(event['event_type'], 0) + 1
        
        print(f"\nTop event types:")
        for event_type, count in sorted(event_types.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  - {event_type}: {count}")
        
        event_store.close_all_connections()
        
    except Exception as e:
        print(f"Database inspection failed: {e}")


if __name__ == '__main__':
    print("Monitoring System Integration Test")
    print("1. Run integration test")
    print("2. Inspect existing database")
    
    choice = input("\nSelect option (1-2): ").strip()
    
    if choice == '1':
        success = test_event_logging_integration()
        sys.exit(0 if success else 1)
    elif choice == '2':
        test_database_inspection()
    else:
        print("Invalid choice")
        sys.exit(1)