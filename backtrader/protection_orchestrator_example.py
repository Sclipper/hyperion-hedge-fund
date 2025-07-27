#!/usr/bin/env python3

"""
Protection Orchestrator Example - Module 8 Demo

Demonstrates the unified protection system orchestrator functionality
with mock protection managers for testing and demonstration.
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from core.protection_models import ProtectionRequest, ProtectionDecision, ProtectionResult
from monitoring.event_store import EventStore
from monitoring.event_writer import EventWriter


class MockProtectionOrchestrator:
    """
    Simplified protection orchestrator for demonstration without complex dependencies.
    
    This shows the core decision-making logic of the protection system.
    """
    
    def __init__(self, event_writer=None):
        self.event_writer = event_writer
        
        # Priority hierarchy
        self.priority_hierarchy = {
            1: 'core_asset_immunity',
            2: 'regime_override', 
            3: 'grace_period',
            4: 'holding_period',
            5: 'whipsaw_protection'
        }
        
        # Mock protection states
        self.core_assets = {'AAPL', 'MSFT'}  # Core assets that are protected
        self.grace_period_assets = {'TSLA'}  # Assets in grace period
        self.whipsaw_blocked_assets = {'NVDA'}  # Assets blocked by whipsaw
        self.recent_positions = {'GOOGL': datetime.now() - timedelta(hours=2)}  # Recent positions
        
        # Statistics
        self.decisions_processed = 0
        self.decisions_approved = 0
        self.decisions_denied = 0
        self.override_count = 0
        
        if self.event_writer:
            self.event_writer.log_event(
                event_type='mock_orchestrator_init',
                event_category='protection',
                action='init',
                reason='Mock protection orchestrator initialized for demo'
            )
    
    def can_execute_action(self, request: ProtectionRequest) -> ProtectionDecision:
        """
        Mock implementation of protection decision logic.
        """
        self.decisions_processed += 1
        start_time = datetime.now()
        
        if self.event_writer:
            self.event_writer.log_event(
                event_type='protection_decision_start',
                event_category='protection',
                action='start',
                reason=f'Protection decision requested: {request.action} {request.asset}',
                asset=request.asset,
                metadata={
                    'action': request.action,
                    'current_size': request.current_size,
                    'target_size': request.target_size
                }
            )
        
        # Apply protection hierarchy
        protection_results = []
        blocking_systems = []
        
        # Priority 1: Core Asset Immunity
        if request.asset in self.core_assets and request.action in ['close', 'decrease']:
            result = ProtectionResult(
                system_name='core_asset_immunity',
                blocks_action=True,
                reason=f'Core asset {request.asset} protected from {request.action}',
                priority=1,
                check_time_ms=0.2
            )
            protection_results.append(result)
            blocking_systems.append('core_asset_immunity')
        else:
            result = ProtectionResult(
                system_name='core_asset_immunity',
                blocks_action=False,
                reason='Core asset check passed' if request.asset in self.core_assets else 'Not a core asset',
                priority=1,
                check_time_ms=0.2
            )
            protection_results.append(result)
        
        # If core asset blocks, return immediately (highest priority)
        if blocking_systems:
            decision = ProtectionDecision(
                approved=False,
                reason=f"Action blocked by: {', '.join(blocking_systems)}",
                blocking_systems=blocking_systems,
                override_applied=False,
                decision_hierarchy=protection_results
            )
            self.decisions_denied += 1
            return self._finalize_decision(decision, request, start_time)
        
        # Priority 3: Grace Period Protection
        if request.asset in self.grace_period_assets and request.action == 'close':
            result = ProtectionResult(
                system_name='grace_period',
                blocks_action=True,
                reason=f'Asset {request.asset} in grace period - cannot close',
                priority=3,
                check_time_ms=0.3
            )
            protection_results.append(result)
            blocking_systems.append('grace_period')
        else:
            result = ProtectionResult(
                system_name='grace_period',
                blocks_action=False,
                reason='Grace period check passed',
                priority=3,
                check_time_ms=0.3
            )
            protection_results.append(result)
        
        # Priority 4: Holding Period Protection
        if (request.asset in self.recent_positions and 
            request.action in ['close', 'decrease'] and
            datetime.now() - self.recent_positions[request.asset] < timedelta(hours=24)):
            
            result = ProtectionResult(
                system_name='holding_period',
                blocks_action=True,
                reason=f'Minimum holding period not met for {request.asset}',
                priority=4,
                check_time_ms=0.4
            )
            protection_results.append(result)
            blocking_systems.append('holding_period')
        else:
            result = ProtectionResult(
                system_name='holding_period',
                blocks_action=False,
                reason='Holding period check passed',
                priority=4,
                check_time_ms=0.4
            )
            protection_results.append(result)
        
        # Priority 5: Whipsaw Protection
        if request.asset in self.whipsaw_blocked_assets and request.action == 'open':
            result = ProtectionResult(
                system_name='whipsaw_protection',
                blocks_action=True,
                reason=f'Whipsaw protection blocks opening {request.asset}',
                priority=5,
                check_time_ms=0.5
            )
            protection_results.append(result)
            blocking_systems.append('whipsaw_protection')
        else:
            result = ProtectionResult(
                system_name='whipsaw_protection',
                blocks_action=False,
                reason='Whipsaw protection check passed',
                priority=5,
                check_time_ms=0.5
            )
            protection_results.append(result)
        
        # Final decision
        if blocking_systems:
            decision = ProtectionDecision(
                approved=False,
                reason=f"Action blocked by: {', '.join(blocking_systems)}",
                blocking_systems=blocking_systems,
                override_applied=False,
                decision_hierarchy=protection_results
            )
            self.decisions_denied += 1
        else:
            decision = ProtectionDecision(
                approved=True,
                reason="All protection checks passed",
                blocking_systems=[],
                override_applied=False,
                decision_hierarchy=protection_results
            )
            self.decisions_approved += 1
        
        return self._finalize_decision(decision, request, start_time)
    
    def _finalize_decision(self, decision, request, start_time):
        """Finalize decision with timing and logging."""
        decision_time = (datetime.now() - start_time).total_seconds() * 1000
        decision.decision_time_ms = decision_time
        
        if self.event_writer:
            self.event_writer.log_event(
                event_type='protection_decision_complete',
                event_category='protection',
                action='approve' if decision.approved else 'deny',
                reason=decision.reason,
                asset=request.asset,
                execution_time_ms=decision_time,
                metadata={
                    'approved': decision.approved,
                    'blocking_systems': decision.blocking_systems,
                    'protection_checks': len(decision.decision_hierarchy)
                }
            )
        
        return decision
    
    def get_performance_metrics(self):
        """Get orchestrator performance metrics."""
        return {
            'decisions_processed': self.decisions_processed,
            'decisions_approved': self.decisions_approved,
            'decisions_denied': self.decisions_denied,
            'approval_rate': self.decisions_approved / max(self.decisions_processed, 1),
            'denial_rate': self.decisions_denied / max(self.decisions_processed, 1)
        }


def demonstrate_protection_orchestrator():
    """Demonstrate protection orchestrator functionality."""
    print("=" * 80)
    print("PROTECTION ORCHESTRATOR DEMONSTRATION")
    print("=" * 80)
    
    # Create temporary database for event logging
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='_demo.db')
    temp_db.close()
    
    try:
        # Create event logging system
        event_store = EventStore(temp_db.name)
        event_writer = EventWriter(event_store)
        
        print(f"\n1. Setting up protection orchestrator with event logging")
        print(f"   Database: {temp_db.name}")
        
        # Create orchestrator
        orchestrator = MockProtectionOrchestrator(event_writer)
        
        print(f"   ✓ Orchestrator initialized")
        print(f"   ✓ Core assets: {orchestrator.core_assets}")
        print(f"   ✓ Grace period assets: {orchestrator.grace_period_assets}")
        print(f"   ✓ Whipsaw blocked assets: {orchestrator.whipsaw_blocked_assets}")
        
        print(f"\n2. Testing protection decisions")
        
        # Test scenarios
        test_scenarios = [
            {
                'name': 'Open new position (should pass)',
                'request': ProtectionRequest(
                    asset='META',
                    action='open',
                    current_date=datetime.now(),
                    current_size=0.0,
                    target_size=0.08,
                    current_score=0.82,
                    reason='High momentum signal'
                )
            },
            {
                'name': 'Close core asset (should be blocked)',
                'request': ProtectionRequest(
                    asset='AAPL',  # Core asset
                    action='close',
                    current_date=datetime.now(),
                    current_size=0.15,
                    target_size=0.0,
                    current_score=0.45,
                    reason='Score below threshold'
                )
            },
            {
                'name': 'Close asset in grace period (should be blocked)',
                'request': ProtectionRequest(
                    asset='TSLA',  # In grace period
                    action='close',
                    current_date=datetime.now(),
                    current_size=0.12,
                    target_size=0.0,
                    current_score=0.38,
                    reason='Poor performance'
                )
            },
            {
                'name': 'Open whipsaw-blocked asset (should be blocked)',
                'request': ProtectionRequest(
                    asset='NVDA',  # Whipsaw blocked
                    action='open',
                    current_date=datetime.now(),
                    current_size=0.0,
                    target_size=0.10,
                    current_score=0.75,
                    reason='Strong technical signal'
                )
            },
            {
                'name': 'Close recent position (should be blocked)',
                'request': ProtectionRequest(
                    asset='GOOGL',  # Recent position
                    action='close',
                    current_date=datetime.now(),
                    current_size=0.09,
                    target_size=0.0,
                    current_score=0.42,
                    reason='Score degradation'
                )
            },
            {
                'name': 'Increase core asset position (should pass)',
                'request': ProtectionRequest(
                    asset='MSFT',  # Core asset but increasing is allowed
                    action='increase',
                    current_date=datetime.now(),
                    current_size=0.10,
                    target_size=0.15,
                    current_score=0.88,
                    reason='Strong fundamentals'
                )
            }
        ]
        
        # Process each scenario
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n   Scenario {i}: {scenario['name']}")
            
            decision = orchestrator.can_execute_action(scenario['request'])
            
            status = "✓ APPROVED" if decision.approved else "✗ DENIED"
            print(f"   {status}: {decision.reason}")
            
            if decision.blocking_systems:
                print(f"   Blocking systems: {', '.join(decision.blocking_systems)}")
            
            print(f"   Decision time: {decision.decision_time_ms:.2f}ms")
            print(f"   Protection checks: {len(decision.decision_hierarchy)}")
            
            # Show protection hierarchy results
            for result in decision.decision_hierarchy:
                block_status = "BLOCKS" if result.blocks_action else "ALLOWS"
                print(f"     - {result.system_name} ({result.priority}): {block_status} - {result.reason}")
        
        print(f"\n3. Performance metrics")
        metrics = orchestrator.get_performance_metrics()
        print(f"   Decisions processed: {metrics['decisions_processed']}")
        print(f"   Decisions approved: {metrics['decisions_approved']}")
        print(f"   Decisions denied: {metrics['decisions_denied']}")
        print(f"   Approval rate: {metrics['approval_rate']:.1%}")
        print(f"   Denial rate: {metrics['denial_rate']:.1%}")
        
        print(f"\n4. Event logging verification")
        
        # Query events from database
        from monitoring.event_models import EventQuery
        
        all_events = event_store.query_events(EventQuery())
        protection_events = event_store.query_events(EventQuery(event_category='protection'))
        decision_events = event_store.query_events(EventQuery(event_type='protection_decision_complete'))
        
        print(f"   Total events logged: {len(all_events)}")
        print(f"   Protection events: {len(protection_events)}")
        print(f"   Decision events: {len(decision_events)}")
        
        # Show recent decision events
        print(f"\n   Recent decision events:")
        for event in decision_events[-3:]:  # Last 3 decisions
            asset = event.get('asset', 'N/A')
            action = event.get('action', 'N/A')
            reason = event.get('reason', 'N/A')
            exec_time = event.get('execution_time_ms', 0)
            print(f"     - {asset} {action}: {reason} ({exec_time:.2f}ms)")
        
        print(f"\n5. Database statistics")
        
        stats = event_store.get_event_statistics(days=1)
        print(f"   Events by category: {stats['events_by_category']}")
        print(f"   Average execution time: {stats['average_execution_time_ms']:.2f}ms")
        print(f"   Error count: {stats['error_count']}")
        
        print(f"\n" + "=" * 80)
        print("DEMONSTRATION COMPLETE ✓")
        print("=" * 80)
        
        print(f"\nKey takeaways:")
        print(f"✓ Protection orchestrator successfully coordinates multiple protection systems")
        print(f"✓ Priority hierarchy ensures core assets have highest protection")
        print(f"✓ Comprehensive event logging captures all protection decisions")
        print(f"✓ Performance metrics enable monitoring and optimization")
        print(f"✓ Flexible architecture supports complex protection scenarios")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Clean up
        try:
            event_store.close_all_connections()
        except:
            pass
        
        # Clean up database automatically for demo
        try:
            os.unlink(temp_db.name)
            print(f"\nDatabase cleaned up automatically")
        except:
            print(f"Could not clean up database: {temp_db.name}")


if __name__ == '__main__':
    success = demonstrate_protection_orchestrator()
    sys.exit(0 if success else 1)