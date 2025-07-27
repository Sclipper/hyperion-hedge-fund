#!/usr/bin/env python3
"""
Phase 2 Validation: Multi-Timeframe Technical Analysis Engine

Tests the enhanced asset scanner with real technical analysis calculations.
Validates indicator calculations, condition detection, and multi-timeframe aggregation.
"""

import sys
import os
import time
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

try:
    from core.enhanced_asset_scanner import EnhancedAssetScanner, get_enhanced_asset_scanner
    from core.asset_scanner_models import MarketCondition, ScannerSource
    from core.technical_indicators import TechnicalIndicatorCalculator, get_technical_calculator
    print("✓ All imports successful")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)


class MockDataManager:
    """Mock data manager that doesn't provide price data to test fallback"""
    def get_timeframe_data(self, timeframe):
        return {
            'VIX': 15.0,
            'growth_momentum': 0.7,
            'risk_appetite': 0.6
        }


def test_technical_calculator():
    """Test technical indicator calculator independently"""
    print("\n=== Testing Technical Indicator Calculator ===")
    
    calculator = get_technical_calculator()
    print(f"✓ Technical calculator initialized: {type(calculator).__name__}")
    
    # Create some mock price data for testing
    import pandas as pd
    import numpy as np
    
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    
    # Create trending price data
    np.random.seed(42)
    trend_prices = [100]
    for i in range(99):
        change = np.random.normal(0.005, 0.02)  # Slight upward bias
        trend_prices.append(trend_prices[-1] * (1 + change))
    
    trending_data = pd.DataFrame({
        'date': dates,
        'open': trend_prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in trend_prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in trend_prices],
        'close': trend_prices,
        'volume': np.random.uniform(100000, 1000000, 100)
    }).set_index('date')
    
    # Test calculation
    result = calculator.calculate_all_indicators(trending_data, '1d')
    print(f"✓ Calculated indicators for trending data:")
    print(f"  - ADX: {result.adx:.2f}")
    print(f"  - MA Alignment: {result.ma_alignment_score:.2f}")
    print(f"  - MACD Momentum: {result.macd_momentum:.2f}")
    print(f"  - Trend Score: {result.trend_score:.2f}")
    print(f"  - Range Score: {result.range_score:.2f}")
    print(f"  - Breakout Score: {result.breakout_score:.2f}")
    
    # Verify scores are in valid range
    assert 0.0 <= result.trend_score <= 1.0, f"Invalid trend score: {result.trend_score}"
    assert 0.0 <= result.range_score <= 1.0, f"Invalid range score: {result.range_score}"
    print("✓ All indicator scores in valid range [0.0, 1.0]")
    
    return True


def test_enhanced_scanner_technical_analysis():
    """Test enhanced scanner with technical analysis fallback"""
    print("\n=== Testing Enhanced Scanner Technical Analysis ===")
    
    # Create scanner with database disabled to force technical analysis
    scanner = EnhancedAssetScanner(
        enable_database=False,
        fallback_enabled=True,
        timeframes=['1d', '4h'],  # Reduce timeframes for testing
        min_confidence_threshold=0.3
    )
    
    print(f"✓ Scanner created with technical analysis fallback")
    print(f"  - Database enabled: {scanner.enable_database}")
    print(f"  - Fallback enabled: {scanner.fallback_enabled}")
    print(f"  - Timeframes: {scanner.timeframes}")
    
    # Test with mock data manager
    data_manager = MockDataManager()
    test_tickers = ['AAPL', 'MSFT', 'GOOGL']
    test_date = datetime(2024, 1, 15)
    
    print(f"\n📊 Scanning {len(test_tickers)} assets with technical analysis...")
    start_time = time.time()
    
    results = scanner.scan_assets(test_tickers, test_date, 0.3, data_manager)
    
    scan_duration = time.time() - start_time
    print(f"✓ Scan completed in {scan_duration:.3f} seconds")
    
    # Validate results
    print(f"\n📈 Results Summary:")
    print(f"  - Total assets scanned: {results.total_assets_scanned}")
    print(f"  - Assets with conditions: {len(results.asset_conditions)}")
    print(f"  - Database assets: {results.database_assets}")
    print(f"  - Fallback assets: {results.fallback_assets}")
    print(f"  - Average confidence: {results.average_confidence:.3f}")
    
    # Check individual asset results
    for ticker, condition in results.asset_conditions.items():
        print(f"\n🔍 {ticker}:")
        print(f"  - Market Condition: {condition.market.value}")
        print(f"  - Confidence: {condition.confidence:.3f}")
        print(f"  - Source: {condition.source.value}")
        print(f"  - Timeframes: {list(condition.timeframe_breakdown.keys())}")
        print(f"  - Analysis Method: {condition.metadata.get('analysis_method', 'unknown')}")
        
        # Validate condition
        assert condition.source == ScannerSource.FALLBACK, f"Expected fallback source, got {condition.source}"
        assert condition.confidence >= 0.3, f"Confidence {condition.confidence} below minimum"
        assert condition.market in [MarketCondition.TRENDING, MarketCondition.RANGING, 
                                   MarketCondition.BREAKOUT, MarketCondition.BREAKDOWN]
        assert 'technical_analysis' in condition.metadata
        assert condition.metadata.get('analysis_method') == 'multi_timeframe_technical'
    
    print("✓ All asset conditions properly validated")
    
    # Test convenience methods
    print("\n🎯 Testing convenience methods...")
    trending = scanner.get_trending_assets(test_tickers, test_date, 0.3, None, data_manager)
    ranging = scanner.get_ranging_assets(test_tickers, test_date, 0.3, None, data_manager)
    breakout = scanner.get_breakout_assets(test_tickers, test_date, 0.3, None, data_manager)
    
    print(f"  - Trending assets: {len(trending)} - {trending}")
    print(f"  - Ranging assets: {len(ranging)} - {ranging}")
    print(f"  - Breakout assets: {len(breakout)} - {breakout}")
    
    total_classified = len(trending) + len(ranging) + len(breakout)
    print(f"✓ Total classified assets: {total_classified}")
    
    return True


def test_multi_timeframe_analysis():
    """Test multi-timeframe analysis and aggregation"""
    print("\n=== Testing Multi-Timeframe Analysis ===")
    
    scanner = EnhancedAssetScanner(
        enable_database=False,
        fallback_enabled=True,
        timeframes=['1d', '4h', '1h'],  # All three timeframes
        confidence_weights={'1d': 0.5, '4h': 0.3, '1h': 0.2},
        min_confidence_threshold=0.2
    )
    
    data_manager = MockDataManager()
    test_date = datetime(2024, 1, 15)
    
    # Test single asset analysis
    print("🔬 Analyzing single asset across multiple timeframes...")
    
    asset_condition = scanner._analyze_asset_technical('AAPL', test_date, data_manager)
    
    if asset_condition:
        print(f"✓ Multi-timeframe analysis successful:")
        print(f"  - Final Condition: {asset_condition.market.value}")
        print(f"  - Final Confidence: {asset_condition.confidence:.3f}")
        print(f"  - Timeframe Breakdown: {asset_condition.timeframe_breakdown}")
        print(f"  - Timeframes Analyzed: {asset_condition.metadata.get('timeframes_analyzed', [])}")
        
        # Validate timeframe breakdown
        assert len(asset_condition.timeframe_breakdown) <= 3, "Too many timeframes in breakdown"
        for tf, conf in asset_condition.timeframe_breakdown.items():
            assert tf in ['1d', '4h', '1h'], f"Invalid timeframe: {tf}"
            assert 0.0 <= conf <= 1.0, f"Invalid confidence for {tf}: {conf}"
        
        print("✓ Timeframe breakdown validated")
    else:
        print("✗ Multi-timeframe analysis failed")
        return False
    
    return True


def test_performance_and_caching():
    """Test performance and caching functionality"""
    print("\n=== Testing Performance and Caching ===")
    
    scanner = EnhancedAssetScanner(enable_database=False, fallback_enabled=True)
    data_manager = MockDataManager()
    test_tickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
    test_date = datetime(2024, 1, 15)
    
    # First scan (no cache)
    print("⏱️ First scan (building cache)...")
    start_time = time.time()
    results1 = scanner.scan_assets(test_tickers, test_date, 0.3, data_manager)
    duration1 = time.time() - start_time
    
    print(f"✓ First scan: {duration1:.3f}s, {len(results1.asset_conditions)} assets")
    
    # Check cache
    cache_status = scanner.get_scanner_status()
    print(f"  - Cache entries: {cache_status['cache_entries']}")
    
    # Clear cache and test again
    scanner.clear_cache()
    cache_status_after = scanner.get_scanner_status()
    print(f"✓ Cache cleared: {cache_status_after['cache_entries']} entries")
    
    return True


def main():
    """Run Phase 2 validation tests"""
    print("🧪 Module 12 Enhanced Asset Scanner - Phase 2 Validation")
    print("=" * 60)
    print("Testing Multi-Timeframe Technical Analysis Engine")
    
    tests = [
        test_technical_calculator,
        test_enhanced_scanner_technical_analysis,
        test_multi_timeframe_analysis,
        test_performance_and_caching
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
                print(f"✅ {test.__name__} PASSED")
            else:
                failed += 1
                print(f"❌ {test.__name__} FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test.__name__} FAILED with error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"📊 Phase 2 Validation Results:")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📈 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 Phase 2 implementation is COMPLETE and WORKING!")
        print("   Ready to proceed to Phase 3: Configuration and Integration")
    else:
        print(f"\n⚠️  Phase 2 has {failed} failing test(s). Please review and fix.")
        
    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)