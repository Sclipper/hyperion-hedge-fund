#!/usr/bin/env python3

"""
Protection Orchestrator System Tests

Comprehensive tests for the unified protection system including:
- Protection decision hierarchy
- Override logic and regime integration
- Integration with rebalancer engine
- Performance and error handling
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
import time

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from core.protection_orchestrator import ProtectionOrchestrator
from core.protection_models import ProtectionRequest, ProtectionDecision, ProtectionResult
from core.protection_aware_rebalancer import ProtectionAwareRebalancerEngine
from core.models import RebalancingTarget, AssetPriority
from monitoring.event_store import EventStore
from monitoring.event_writer import EventWriter


class TestProtectionModels(unittest.TestCase):
    """Test protection request and decision models"""
    
    def test_protection_request_creation(self):
        """Test creating protection requests"""
        request = ProtectionRequest(
            asset='AAPL',
            action='open',
            current_date=datetime.now(),
            current_size=0.0,
            target_size=0.10,
            current_score=0.85,
            reason='High scoring opportunity'
        )
        
        self.assertEqual(request.asset, 'AAPL')
        self.assertEqual(request.action, 'open')
        self.assertTrue(request.validate())
    
    def test_protection_request_validation(self):
        """Test protection request validation"""
        # Valid request
        valid_request = ProtectionRequest(
            asset='AAPL',
            action='open',
            current_date=datetime.now()
        )
        self.assertTrue(valid_request.validate())
        
        # Invalid request - missing required fields
        invalid_request = ProtectionRequest(
            asset='AAPL',
            action='open',
            current_date=None  # Missing required field
        )
        self.assertFalse(invalid_request.validate())
    
    def test_protection_decision_to_dict(self):
        """Test protection decision serialization"""
        decision = ProtectionDecision(
            approved=True,
            reason='All checks passed',
            blocking_systems=[],
            override_applied=False,
            decision_time_ms=1.5
        )
        
        result_dict = decision.to_dict()
        
        self.assertEqual(result_dict['approved'], True)
        self.assertEqual(result_dict['reason'], 'All checks passed')
        self.assertEqual(result_dict['blocking_systems'], [])
        self.assertEqual(result_dict['decision_time_ms'], 1.5)


class TestProtectionOrchestrator(unittest.TestCase):
    """Test protection orchestrator functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database for event logging
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Create event store and writer
        self.event_store = EventStore(self.temp_db.name)
        self.event_writer = EventWriter(self.event_store)
        
        # Create mock protection managers
        self.mock_core_asset_manager = Mock()
        self.mock_grace_period_manager = Mock()
        self.mock_holding_period_manager = Mock()
        self.mock_whipsaw_protection_manager = Mock()
        self.mock_regime_context_provider = Mock()
        
        # Create orchestrator
        self.orchestrator = ProtectionOrchestrator(
            core_asset_manager=self.mock_core_asset_manager,
            grace_period_manager=self.mock_grace_period_manager,
            holding_period_manager=self.mock_holding_period_manager,
            whipsaw_protection_manager=self.mock_whipsaw_protection_manager,
            regime_context_provider=self.mock_regime_context_provider,
            event_writer=self.event_writer
        )
    
    def tearDown(self):
        """Clean up test environment"""
        self.event_store.close_all_connections()
        os.unlink(self.temp_db.name)
    
    def test_orchestrator_initialization(self):
        """Test orchestrator initialization"""
        self.assertEqual(self.orchestrator.decisions_processed, 0)
        self.assertEqual(self.orchestrator.decisions_approved, 0)
        self.assertEqual(self.orchestrator.decisions_denied, 0)
        self.assertEqual(len(self.orchestrator.priority_hierarchy), 5)
        
        # Check that initialization was logged
        init_events = self.event_store.query_events(
            self.event_store.query_events.__defaults__[0].__class__(
                event_type='protection_orchestrator_init'
            )
        )
        self.assertGreater(len(init_events), 0)
    
    def test_core_asset_immunity_blocks_action(self):
        """Test core asset immunity blocking actions"""
        # Mock core asset manager to return True for is_core_asset
        self.mock_core_asset_manager.is_core_asset.return_value = True
        
        request = ProtectionRequest(
            asset='CORE_ASSET',
            action='close',
            current_date=datetime.now(),
            reason='Test core asset closure'
        )
        
        decision = self.orchestrator.can_execute_action(request)
        
        self.assertFalse(decision.approved)
        self.assertIn('core_asset_immunity', decision.blocking_systems)
        self.assertEqual(self.orchestrator.decisions_denied, 1)
    
    def test_core_asset_immunity_allows_action(self):
        """Test core asset immunity allowing non-blocking actions"""
        # Mock core asset manager to return True for is_core_asset
        self.mock_core_asset_manager.is_core_asset.return_value = True
        
        request = ProtectionRequest(
            asset='CORE_ASSET',
            action='open',  # Opening should be allowed
            current_date=datetime.now(),
            reason='Test core asset opening'
        )
        
        # Mock other managers to not block
        self.mock_grace_period_manager.is_in_grace_period.return_value = False
        self.mock_whipsaw_protection_manager.can_open_position.return_value = (True, "No whipsaw block")
        
        decision = self.orchestrator.can_execute_action(request)
        
        self.assertTrue(decision.approved)
        self.assertEqual(len(decision.blocking_systems), 0)
    
    def test_protection_hierarchy_order(self):
        """Test that protection checks follow correct priority order"""
        # Mock non-core asset
        self.mock_core_asset_manager.is_core_asset.return_value = False
        
        # Mock grace period to block
        self.mock_grace_period_manager.is_in_grace_period.return_value = True
        grace_position = Mock()
        grace_position.grace_end_date = datetime.now() + timedelta(days=2)
        grace_position.current_decay_factor = 0.8
        self.mock_grace_period_manager.get_grace_position.return_value = grace_position
        
        request = ProtectionRequest(
            asset='TEST_ASSET',
            action='close',
            current_date=datetime.now(),
            reason='Test protection hierarchy'
        )
        
        decision = self.orchestrator.can_execute_action(request)
        
        self.assertFalse(decision.approved)
        self.assertIn('grace_period', decision.blocking_systems)
        
        # Verify decision hierarchy has results in priority order
        system_names = [result.system_name for result in decision.decision_hierarchy]
        expected_order = ['core_asset_immunity', 'grace_period']
        self.assertEqual(system_names[:2], expected_order)
    
    def test_regime_override_functionality(self):
        """Test regime override bypassing protection systems"""
        # Mock non-core asset
        self.mock_core_asset_manager.is_core_asset.return_value = False
        
        # Mock grace period to block
        self.mock_grace_period_manager.is_in_grace_period.return_value = True
        grace_position = Mock()
        grace_position.grace_end_date = datetime.now() + timedelta(days=2)
        grace_position.current_decay_factor = 0.8
        self.mock_grace_period_manager.get_grace_position.return_value = grace_position
        
        # Mock regime context to allow override
        regime_context = {
            'regime_changed': True,
            'regime_severity': 'critical',
            'new_regime': 'Crisis',
            'old_regime': 'Goldilocks'
        }
        self.mock_regime_context_provider.get_regime_context.return_value = regime_context
        
        request = ProtectionRequest(
            asset='TEST_ASSET',
            action='close',
            current_date=datetime.now(),
            reason='Test regime override'
        )
        
        decision = self.orchestrator.can_execute_action(request)
        
        self.assertTrue(decision.approved)
        self.assertTrue(decision.override_applied)
        self.assertIn('regime override bypassed grace_period', decision.override_reason)
    
    def test_multiple_protection_systems_blocking(self):
        """Test behavior when multiple protection systems block"""
        # Mock non-core asset
        self.mock_core_asset_manager.is_core_asset.return_value = False
        
        # Mock grace period to allow
        self.mock_grace_period_manager.is_in_grace_period.return_value = False
        
        # Mock holding period to block
        self.mock_holding_period_manager.can_adjust_position.return_value = (False, "Minimum holding period not met")
        
        # Mock whipsaw protection to block
        self.mock_whipsaw_protection_manager.can_open_position.return_value = (False, "Too many recent cycles")
        
        # Mock no regime override
        self.mock_regime_context_provider.get_regime_context.return_value = {
            'regime_changed': False,
            'regime_severity': 'normal'
        }
        
        request = ProtectionRequest(
            asset='TEST_ASSET',
            action='close',
            current_date=datetime.now(),
            position_entry_date=datetime.now() - timedelta(hours=1),  # Recent entry
            reason='Test multiple blocks'
        )
        
        decision = self.orchestrator.can_execute_action(request)
        
        self.assertFalse(decision.approved)
        self.assertIn('holding_period', decision.blocking_systems)
    
    def test_performance_tracking(self):
        """Test performance metrics tracking"""
        # Mock non-core asset that passes all checks
        self.mock_core_asset_manager.is_core_asset.return_value = False
        self.mock_grace_period_manager.is_in_grace_period.return_value = False
        self.mock_whipsaw_protection_manager.can_open_position.return_value = (True, "No whipsaw block")
        
        request = ProtectionRequest(
            asset='TEST_ASSET',
            action='open',
            current_date=datetime.now(),
            reason='Performance test'
        )
        
        initial_processed = self.orchestrator.decisions_processed
        
        decision = self.orchestrator.can_execute_action(request)
        
        self.assertEqual(self.orchestrator.decisions_processed, initial_processed + 1)
        self.assertIsNotNone(decision.decision_time_ms)
        self.assertGreater(decision.decision_time_ms, 0)
        
        # Test metrics getter
        metrics = self.orchestrator.get_performance_metrics()
        self.assertIn('decisions_processed', metrics)
        self.assertIn('approval_rate', metrics)
    
    def test_error_handling(self):
        """Test error handling in protection decisions"""
        # Mock core asset manager to throw exception
        self.mock_core_asset_manager.is_core_asset.side_effect = Exception("Core asset check failed")
        
        request = ProtectionRequest(
            asset='ERROR_ASSET',
            action='open',
            current_date=datetime.now(),
            reason='Test error handling'
        )
        
        decision = self.orchestrator.can_execute_action(request)
        
        # Should return conservative decision (deny)
        self.assertFalse(decision.approved)
        self.assertIn('error', decision.blocking_systems)
    
    def test_protection_status_reporting(self):
        """Test protection status reporting for assets"""
        # Mock various protection states
        self.mock_core_asset_manager.is_core_asset.return_value = True
        self.mock_grace_period_manager.is_in_grace_period.return_value = False
        self.mock_whipsaw_protection_manager.can_open_position.return_value = (True, None)
        
        status = self.orchestrator.get_protection_status('TEST_ASSET', datetime.now())
        
        self.assertEqual(status['asset'], 'TEST_ASSET')
        self.assertIn('protections', status)
        self.assertIn('core_asset', status['protections'])
        self.assertTrue(status['protections']['core_asset']['is_core'])


class TestProtectionAwareRebalancer(unittest.TestCase):
    """Test protection-aware rebalancer integration"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database for event logging
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Create event store and writer
        self.event_store = EventStore(self.temp_db.name)
        self.event_writer = EventWriter(self.event_store)
        
        # Create mock dependencies
        self.mock_regime_detector = Mock()
        self.mock_asset_manager = Mock()
        self.mock_protection_orchestrator = Mock()
        
        # Create protection-aware rebalancer
        self.rebalancer = ProtectionAwareRebalancerEngine(
            regime_detector=self.mock_regime_detector,
            asset_manager=self.mock_asset_manager,
            event_writer=self.event_writer,
            protection_orchestrator=self.mock_protection_orchestrator
        )
    
    def tearDown(self):
        """Clean up test environment"""
        self.event_store.close_all_connections()
        os.unlink(self.temp_db.name)
    
    @patch('core.protection_aware_rebalancer.EnhancedCoreRebalancerEngine.rebalance')
    def test_target_validation_approval(self, mock_parent_rebalance):
        """Test validation of rebalancing targets - approval case"""
        # Mock parent rebalancer to return targets
        mock_targets = [
            RebalancingTarget(
                asset='AAPL',
                target_allocation_pct=0.10,
                current_allocation_pct=0.05,
                action='increase',
                priority=AssetPriority.TRENDING,
                score=0.85,
                reason='High momentum score'
            ),
            RebalancingTarget(
                asset='MSFT',
                target_allocation_pct=0.08,
                current_allocation_pct=0.0,
                action='open',
                priority=AssetPriority.REGIME,
                score=0.78,
                reason='Regime-appropriate asset'
            )
        ]
        mock_parent_rebalance.return_value = mock_targets
        
        # Mock protection orchestrator to approve all targets
        approved_decision = ProtectionDecision(
            approved=True,
            reason='All protection checks passed',
            blocking_systems=[],
            override_applied=False
        )
        self.mock_protection_orchestrator.can_execute_action.return_value = approved_decision
        
        # Execute rebalancing
        current_positions = {'AAPL': 0.05}
        validated_targets = self.rebalancer.rebalance(
            rebalance_date=datetime.now(),
            current_positions=current_positions
        )
        
        # Should return all targets since all were approved
        self.assertEqual(len(validated_targets), 2)
        self.assertEqual(self.rebalancer.targets_approved, 2)
        self.assertEqual(self.rebalancer.targets_denied, 0)
        
        # Verify protection orchestrator was called for each target
        self.assertEqual(self.mock_protection_orchestrator.can_execute_action.call_count, 2)
    
    @patch('core.protection_aware_rebalancer.EnhancedCoreRebalancerEngine.rebalance')
    def test_target_validation_denial(self, mock_parent_rebalance):
        """Test validation of rebalancing targets - denial case"""
        # Mock parent rebalancer to return targets
        mock_targets = [
            RebalancingTarget(
                asset='AAPL',
                target_allocation_pct=0.0,
                current_allocation_pct=0.10,
                action='close',
                priority=AssetPriority.PORTFOLIO,
                score=0.45,
                reason='Low score, close position'
            )
        ]
        mock_parent_rebalance.return_value = mock_targets
        
        # Mock protection orchestrator to deny target
        denied_decision = ProtectionDecision(
            approved=False,
            reason='Grace period protection active',
            blocking_systems=['grace_period'],
            override_applied=False
        )
        self.mock_protection_orchestrator.can_execute_action.return_value = denied_decision
        
        # Execute rebalancing
        current_positions = {'AAPL': 0.10}
        validated_targets = self.rebalancer.rebalance(
            rebalance_date=datetime.now(),
            current_positions=current_positions
        )
        
        # Should return no targets since the target was denied
        self.assertEqual(len(validated_targets), 0)
        self.assertEqual(self.rebalancer.targets_approved, 0)
        self.assertEqual(self.rebalancer.targets_denied, 1)
    
    @patch('core.protection_aware_rebalancer.EnhancedCoreRebalancerEngine.rebalance')
    def test_hold_actions_skip_validation(self, mock_parent_rebalance):
        """Test that 'hold' actions skip protection validation"""
        # Mock parent rebalancer to return hold target
        mock_targets = [
            RebalancingTarget(
                asset='AAPL',
                target_allocation_pct=0.10,
                current_allocation_pct=0.10,
                action='hold',
                priority=AssetPriority.PORTFOLIO,
                score=0.75,
                reason='Maintain current position'
            )
        ]
        mock_parent_rebalance.return_value = mock_targets
        
        # Execute rebalancing
        validated_targets = self.rebalancer.rebalance(
            rebalance_date=datetime.now(),
            current_positions={'AAPL': 0.10}
        )
        
        # Should return the hold target without validation
        self.assertEqual(len(validated_targets), 1)
        self.assertEqual(validated_targets[0].action, 'hold')
        
        # Protection orchestrator should not have been called
        self.mock_protection_orchestrator.can_execute_action.assert_not_called()
    
    def test_validation_statistics(self):
        """Test validation statistics tracking"""
        initial_stats = self.rebalancer.get_protection_validation_stats()
        
        self.assertEqual(initial_stats['targets_validated'], 0)
        self.assertEqual(initial_stats['targets_approved'], 0)
        self.assertEqual(initial_stats['targets_denied'], 0)
        self.assertEqual(initial_stats['approval_rate'], 0.0)
        
        # Reset stats
        self.rebalancer.reset_validation_stats()
        
        # Verify stats were reset and logged
        stats_after_reset = self.rebalancer.get_protection_validation_stats()
        self.assertEqual(stats_after_reset['targets_validated'], 0)


class TestPerformanceAndStress(unittest.TestCase):
    """Test performance characteristics of protection system"""
    
    def setUp(self):
        """Set up performance test environment"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Create event store and writer
        self.event_store = EventStore(self.temp_db.name)
        self.event_writer = EventWriter(self.event_store)
        
        # Create orchestrator with mock managers (fast)
        self.orchestrator = ProtectionOrchestrator(
            core_asset_manager=Mock(),
            grace_period_manager=Mock(),
            holding_period_manager=Mock(),
            whipsaw_protection_manager=Mock(),
            regime_context_provider=Mock(),
            event_writer=self.event_writer
        )
        
        # Configure mocks for fast execution
        self.orchestrator.core_asset_manager.is_core_asset.return_value = False
        self.orchestrator.grace_period_manager.is_in_grace_period.return_value = False
        self.orchestrator.whipsaw_protection_manager.can_open_position.return_value = (True, "No block")
        self.orchestrator.regime_context_provider.get_regime_context.return_value = {
            'regime_changed': False,
            'regime_severity': 'normal'
        }
    
    def tearDown(self):
        """Clean up"""
        self.event_store.close_all_connections()
        os.unlink(self.temp_db.name)
    
    def test_decision_performance(self):
        """Test decision making performance"""
        print("\n=== Protection Decision Performance Test ===")
        
        # Create test requests
        requests = []
        for i in range(100):
            request = ProtectionRequest(
                asset=f'ASSET_{i:03d}',
                action='open',
                current_date=datetime.now(),
                current_score=0.5 + (i * 0.005),
                reason=f'Performance test {i}'
            )
            requests.append(request)
        
        # Time the decisions
        start_time = time.time()
        decisions = []
        
        for request in requests:
            decision = self.orchestrator.can_execute_action(request)
            decisions.append(decision)
        
        total_time = (time.time() - start_time) * 1000
        avg_time = total_time / len(requests)
        
        print(f"Total decisions: {len(decisions)}")
        print(f"Total time: {total_time:.2f}ms")
        print(f"Average decision time: {avg_time:.3f}ms")
        print(f"Decisions per second: {len(decisions) / (total_time / 1000):.1f}")
        
        # All decisions should be approved (mocked to pass)
        approved_count = sum(1 for d in decisions if d.approved)
        self.assertEqual(approved_count, len(decisions))
        
        # Average decision time should be reasonable (< 5ms)
        self.assertLess(avg_time, 5.0)
        
        # All decisions should have timing information
        for decision in decisions:
            self.assertIsNotNone(decision.decision_time_ms)
            self.assertGreater(decision.decision_time_ms, 0)


def run_protection_tests():
    """Run protection orchestrator tests"""
    print("=" * 80)
    print("PROTECTION ORCHESTRATOR SYSTEM TESTS")
    print("=" * 80)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestProtectionModels,
        TestProtectionOrchestrator,
        TestProtectionAwareRebalancer,
        TestPerformanceAndStress
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
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
        print("\n🎉 ALL PROTECTION ORCHESTRATOR TESTS PASSED! 🎉")
    else:
        print("\n❌ Some tests failed")
    
    return success


if __name__ == '__main__':
    success = run_protection_tests()
    sys.exit(0 if success else 1)