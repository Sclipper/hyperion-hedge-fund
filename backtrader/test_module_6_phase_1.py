#!/usr/bin/env python3
"""
Module 6 Phase 1 Testing: Enhanced Regime Detection Framework

This script tests the enhanced regime detection capabilities including:
- Enhanced data models functionality
- Multi-timeframe regime analysis
- Confidence and stability calculations
- Integration with existing regime detector
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple

# Add the project root to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))


class MockRegimeDetector:
    """Mock regime detector for testing when real one isn't available"""
    
    def __init__(self, use_database=False):
        self.use_database = False
        self.cache = {}
        self.regime_mappings = {
            'Goldilocks': ['Risk Assets', 'Growth', 'Large Caps', 'High Beta'],
            'Deflation': ['Treasurys', 'Long Rates', 'Defensive Assets', 'Gold'],
            'Inflation': ['Industrial Commodities', 'Energy Commodities', 'Gold', 'Value'],
            'Reflation': ['Cyclicals', 'Value', 'International', 'SMID Caps']
        }
    
    def get_market_regime(self, date: datetime) -> Tuple[str, float]:
        """Mock regime detection"""
        return ("Goldilocks", 0.8)
    
    def get_regime_buckets(self, regime: str):
        return self.regime_mappings.get(regime, ['Risk Assets'])


try:
    # Import core components
    from core.regime_models import (
        RegimeState, RegimeTransition, TransitionSeverity, RegimeConfidence,
        RegimeStability, RegimeStrength, RegimeContext, RegimeAnalytics
    )
    from core.enhanced_regime_detector import EnhancedRegimeDetector
    
    # Try to import the real regime detector, fall back to mock if needed
    try:
        from data.regime_detector import RegimeDetector
    except ImportError:
        print("⚠️ Using mock RegimeDetector due to missing dependencies")
        RegimeDetector = MockRegimeDetector
    
    print("✅ Successfully imported Module 6 Phase 1 components")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure you're running from the backtrader directory")
    sys.exit(1)


class MockDataManager:
    """Mock data manager for testing timeframe analysis"""
    
    def __init__(self):
        self.market_data = {
            'VIX': 18.5,
            'growth_momentum': 0.65,
            'inflation_pressure': 0.3,
            'risk_appetite': 0.6,
            'trend_strength': 0.7,
            'safe_haven_demand': 0.4,
            'growth_weakness': 0.2,
            'deflation_signals': 0.25,
            'commodity_strength': 0.55,
            'real_asset_strength': 0.5,
            'rate_environment': 0.45,
            'policy_support': 0.6,
            'growth_recovery': 0.65,
            'cyclical_strength': 0.6
        }
    
    def get_timeframe_data(self, timeframe: str, current_date: datetime) -> Dict[str, Any]:
        """Return mock timeframe data"""
        # Add some timeframe-specific variation
        variation = {
            '1d': 0.0,
            '4h': 0.05,
            '1h': 0.1
        }.get(timeframe, 0.0)
        
        adjusted_data = {}
        for key, value in self.market_data.items():
            adjusted_data[key] = min(1.0, max(0.0, value + variation))
        
        return adjusted_data
    
    def get_current_market_data(self, current_date: datetime) -> Dict[str, Any]:
        """Return current market data"""
        return self.market_data.copy()


def test_regime_data_models():
    """Test the enhanced regime data models"""
    print("\n🧪 Testing Regime Data Models...")
    
    # Test RegimeState
    current_date = datetime.now()
    regime_state = RegimeState(
        regime="Goldilocks",
        confidence=0.85,
        stability=0.7,
        strength=0.75,
        timeframe_analysis={'1d': 0.8, '4h': 0.85, '1h': 0.9},
        detection_date=current_date - timedelta(days=10),
        duration_days=10
    )
    
    assert regime_state.is_confident(0.8), "RegimeState should be confident"
    assert regime_state.is_stable(0.65), "RegimeState should be stable"
    assert regime_state.is_strong(0.7), "RegimeState should be strong"
    print("  ✅ RegimeState validation passed")
    
    # Test RegimeTransition
    transition = RegimeTransition(
        from_regime="Goldilocks",
        to_regime="Inflation",
        transition_date=current_date,
        severity=TransitionSeverity.HIGH,
        confidence=0.82,
        momentum=0.65,
        trigger_indicators=['commodity_surge', 'inflation_pressure']
    )
    
    assert transition.is_high_impact(), "Transition should be high impact"
    assert transition.can_override_protection('grace_period'), "Should allow grace period override"
    assert not transition.can_override_protection('whipsaw_protection'), "Should not allow whipsaw override"
    print("  ✅ RegimeTransition validation passed")
    
    # Test TransitionSeverity
    critical_transition = RegimeTransition(
        from_regime="Goldilocks",
        to_regime="Deflation",
        transition_date=current_date,
        severity=TransitionSeverity.CRITICAL,
        confidence=0.9,
        momentum=0.8,
        trigger_indicators=['deflationary_pressure', 'safe_haven_demand']
    )
    
    assert critical_transition.is_critical(), "Transition should be critical"
    assert critical_transition.can_override_protection('whipsaw_protection'), "Critical should allow whipsaw override"
    print("  ✅ TransitionSeverity validation passed")
    
    print("✅ All regime data model tests passed!")


def test_enhanced_regime_detector():
    """Test the enhanced regime detector functionality"""
    print("\n🧪 Testing Enhanced Regime Detector...")
    
    # Create base detector and enhanced detector
    base_detector = RegimeDetector(use_database=False)  # Use mock mode
    enhanced_detector = EnhancedRegimeDetector(
        base_detector=base_detector,
        timeframes=['1d', '4h', '1h']
    )
    
    # Create mock data manager
    data_manager = MockDataManager()
    
    # Mock the base detector to return a regime
    def mock_get_market_regime(date):
        return ("Goldilocks", 0.8)
    
    base_detector.get_market_regime = mock_get_market_regime
    
    current_date = datetime.now()
    
    print("  🔍 Testing regime detection...")
    regime_state = enhanced_detector.detect_current_regime(current_date, data_manager)
    
    assert regime_state.regime == "Goldilocks", f"Expected Goldilocks, got {regime_state.regime}"
    assert 0.0 <= regime_state.confidence <= 1.0, "Confidence should be between 0 and 1"
    assert 0.0 <= regime_state.stability <= 1.0, "Stability should be between 0 and 1"
    assert 0.0 <= regime_state.strength <= 1.0, "Strength should be between 0 and 1"
    assert len(regime_state.timeframe_analysis) == 3, "Should have 3 timeframe analyses"
    
    print(f"    📊 Regime: {regime_state.regime}")
    print(f"    📊 Confidence: {regime_state.confidence:.3f}")
    print(f"    📊 Stability: {regime_state.stability:.3f}")
    print(f"    📊 Strength: {regime_state.strength:.3f}")
    print(f"    📊 Timeframe Analysis: {regime_state.timeframe_analysis}")
    
    print("  ✅ Basic regime detection working")
    
    # Test multiple detections to build history
    print("  🔍 Testing regime history building...")
    for i in range(5):
        test_date = current_date + timedelta(days=i)
        regime_state = enhanced_detector.detect_current_regime(test_date, data_manager)
        
    history = enhanced_detector.get_regime_history(days=10)
    assert len(history) >= 5, "Should have at least 5 historical entries"
    print(f"    📊 History length: {len(history)}")
    print("  ✅ Regime history building working")
    
    # Test regime info
    print("  🔍 Testing regime info retrieval...")
    info = enhanced_detector.get_current_regime_info()
    assert info is not None, "Should return regime info"
    assert 'regime' in info, "Info should contain regime"
    assert 'confidence' in info, "Info should contain confidence"
    
    print(f"    📊 Current regime info: {info['regime']} (confidence: {info['confidence']:.3f})")
    print("  ✅ Regime info retrieval working")
    
    print("✅ Enhanced regime detector tests passed!")


def test_multi_timeframe_analysis():
    """Test multi-timeframe analysis capabilities"""
    print("\n🧪 Testing Multi-timeframe Analysis...")
    
    base_detector = RegimeDetector(use_database=False)
    enhanced_detector = EnhancedRegimeDetector(
        base_detector=base_detector,
        timeframes=['1d', '4h', '1h'],
        confidence_weights={'1d': 0.5, '4h': 0.3, '1h': 0.2}
    )
    
    # Mock different regimes for testing
    test_regimes = ["Goldilocks", "Deflation", "Inflation", "Reflation"]
    
    for regime in test_regimes:
        print(f"  🔍 Testing {regime} regime analysis...")
        
        # Mock the base detector
        def mock_get_market_regime(date):
            return (regime, 0.75)
        
        base_detector.get_market_regime = mock_get_market_regime
        
        # Create regime-specific mock data
        data_manager = MockDataManager()
        if regime == "Deflation":
            data_manager.market_data.update({
                'VIX': 28,
                'safe_haven_demand': 0.8,
                'growth_weakness': 0.7,
                'deflation_signals': 0.75
            })
        elif regime == "Inflation":
            data_manager.market_data.update({
                'inflation_pressure': 0.8,
                'commodity_strength': 0.85,
                'rate_environment': 0.7
            })
        elif regime == "Reflation":
            data_manager.market_data.update({
                'policy_support': 0.8,
                'growth_recovery': 0.75,
                'risk_appetite': 0.8
            })
        
        current_date = datetime.now()
        regime_state = enhanced_detector.detect_current_regime(current_date, data_manager)
        
        assert regime_state.regime == regime, f"Expected {regime}, got {regime_state.regime}"
        
        # Check timeframe analysis
        for timeframe in ['1d', '4h', '1h']:
            assert timeframe in regime_state.timeframe_analysis, f"Missing {timeframe} analysis"
            tf_confidence = regime_state.timeframe_analysis[timeframe]
            assert 0.0 <= tf_confidence <= 1.0, f"{timeframe} confidence out of range: {tf_confidence}"
        
        print(f"    📊 {regime} confidence: {regime_state.confidence:.3f}")
        print(f"    📊 Timeframes: {regime_state.timeframe_analysis}")
    
    print("✅ Multi-timeframe analysis tests passed!")


def test_confidence_and_stability():
    """Test confidence and stability calculations"""
    print("\n🧪 Testing Confidence and Stability Calculations...")
    
    base_detector = RegimeDetector(use_database=False)
    enhanced_detector = EnhancedRegimeDetector(base_detector=base_detector)
    
    def mock_get_market_regime(date):
        return ("Goldilocks", 0.85)
    
    base_detector.get_market_regime = mock_get_market_regime
    data_manager = MockDataManager()
    
    # Build some history for stability calculation
    current_date = datetime.now()
    for i in range(15):
        test_date = current_date + timedelta(days=i)
        enhanced_detector.detect_current_regime(test_date, data_manager)
    
    # Get final regime state
    final_state = enhanced_detector.detect_current_regime(current_date + timedelta(days=15), data_manager)
    
    print(f"  📊 Final confidence: {final_state.confidence:.3f}")
    print(f"  📊 Final stability: {final_state.stability:.3f}")
    print(f"  📊 Final strength: {final_state.strength:.3f}")
    print(f"  📊 Duration: {final_state.duration_days} days")
    
    # Test stability improvement over time
    assert final_state.stability > 0.5, "Stability should improve with consistent regime"
    
    # Test regime change impact on stability
    print("  🔍 Testing regime change impact...")
    
    def mock_regime_change(date):
        return ("Deflation", 0.8)  # Change to deflation
    
    base_detector.get_market_regime = mock_regime_change
    
    change_state = enhanced_detector.detect_current_regime(current_date + timedelta(days=16), data_manager)
    
    print(f"  📊 After change - regime: {change_state.regime}")
    print(f"  📊 After change - stability: {change_state.stability:.3f}")
    
    assert change_state.regime == "Deflation", "Regime should have changed"
    
    print("✅ Confidence and stability calculation tests passed!")


def test_fallback_behavior():
    """Test fallback behavior when base detector fails"""
    print("\n🧪 Testing Fallback Behavior...")
    
    base_detector = RegimeDetector(use_database=False)
    enhanced_detector = EnhancedRegimeDetector(base_detector=base_detector)
    
    # Mock base detector failure
    def mock_failed_detection(date):
        return (None, 0.0)  # Simulate failure
    
    base_detector.get_market_regime = mock_failed_detection
    
    current_date = datetime.now()
    regime_state = enhanced_detector.detect_current_regime(current_date, None)
    
    # Should return fallback regime
    assert regime_state.regime == "Goldilocks", "Should fallback to Goldilocks"
    assert regime_state.confidence == 0.3, "Should have low confidence"
    
    print(f"  📊 Fallback regime: {regime_state.regime}")
    print(f"  📊 Fallback confidence: {regime_state.confidence}")
    
    print("✅ Fallback behavior tests passed!")


def run_comprehensive_test():
    """Run comprehensive test suite for Phase 1"""
    print("🚀 Starting Module 6 Phase 1 Comprehensive Test Suite")
    print("=" * 60)
    
    try:
        # Run all test components
        test_regime_data_models()
        test_enhanced_regime_detector()
        test_multi_timeframe_analysis()
        test_confidence_and_stability()
        test_fallback_behavior()
        
        print("\n" + "=" * 60)
        print("🎉 All Module 6 Phase 1 tests PASSED!")
        print("✅ Enhanced Regime Detection Framework is working correctly")
        print("🔄 Ready to proceed to Phase 2: Regime Change Analysis")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1) 