#!/usr/bin/env python3
"""
Phase 4 Validation: Real Data Integration

Tests the complete integration of Module 12 Enhanced Asset Scanner with real data sources.
Verifies that no mock data is used and all technical analysis uses real Yahoo Finance data.
"""

import sys
import os
import time
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

try:
    from data.regime_detector import RegimeDetector
    from core.enhanced_asset_scanner import get_enhanced_asset_scanner
    from data.data_manager import DataManager
    print("✓ Core imports successful")
    
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)


def test_real_data_manager_integration():
    """Test that data manager provides real Yahoo Finance data"""
    print("\n=== Testing Real Data Manager Integration ===")
    
    data_manager = DataManager()
    test_ticker = 'AAPL'
    end_date = datetime.now()
    start_date = end_date - timedelta(days=100)
    
    print(f"🔍 Testing data download for {test_ticker}...")
    
    # Test direct data download
    price_data = data_manager.download_data(test_ticker, start_date, end_date)
    
    if price_data is None:
        print(f"✗ No data returned for {test_ticker}")
        return False
    
    print(f"✓ Data downloaded: {len(price_data)} periods")
    print(f"  - Columns: {list(price_data.columns)}")
    print(f"  - Date range: {price_data.index[0]} to {price_data.index[-1]}")
    
    # Verify data structure
    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    missing_cols = [col for col in required_cols if col not in price_data.columns]
    
    if missing_cols:
        print(f"✗ Missing required columns: {missing_cols}")
        return False
    
    # Verify data quality
    for col in required_cols[:-1]:  # Skip Volume as it can be 0
        if price_data[col].isna().all():
            print(f"✗ Column {col} is all NaN")
            return False
        
        if (price_data[col] <= 0).any():
            print(f"✗ Column {col} has zero or negative values")
            return False
    
    print("✓ Data structure and quality validated")
    return True


def test_regime_detector_real_data_interface():
    """Test regime detector provides real data interface"""
    print("\n=== Testing Regime Detector Real Data Interface ===")
    
    regime_detector = RegimeDetector(use_enhanced_scanner=True)
    test_ticker = 'MSFT'
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)
    
    print(f"🔍 Testing regime detector data interface for {test_ticker}...")
    
    # Test the new get_price_data method
    price_data = regime_detector.get_price_data(test_ticker, start_date, end_date)
    
    if price_data is None:
        print(f"✗ No data returned from regime detector for {test_ticker}")
        return False
    
    print(f"✓ Data received: {len(price_data)} periods")
    print(f"  - Columns: {list(price_data.columns)}")
    
    # Verify columns are lowercase (standardized)
    expected_cols = ['open', 'high', 'low', 'close']
    missing_cols = [col for col in expected_cols if col not in price_data.columns]
    
    if missing_cols:
        print(f"✗ Missing standardized columns: {missing_cols}")
        return False
    
    print("✓ Regime detector provides properly formatted real data")
    return True


def test_enhanced_scanner_no_mock_data():
    """Test that enhanced scanner uses only real data (no mock generation)"""
    print("\n=== Testing Enhanced Scanner Real Data Only ===")
    
    # Create scanner with database disabled to force fallback to technical analysis
    scanner = get_enhanced_asset_scanner(
        enable_database=False,
        fallback_enabled=True
    )
    
    regime_detector = RegimeDetector(use_enhanced_scanner=True)
    
    test_tickers = ['AAPL', 'GOOGL']
    test_date = datetime.now() - timedelta(days=1)  # Use yesterday to ensure data exists
    
    print(f"🔍 Testing scanner with real data for {len(test_tickers)} assets...")
    
    # Scan assets using real data manager
    start_time = time.time()
    results = scanner.scan_assets(
        tickers=test_tickers,
        date=test_date,
        min_confidence=0.3,  # Lower threshold for testing
        data_manager=regime_detector
    )
    scan_duration = time.time() - start_time
    
    print(f"✓ Scan completed in {scan_duration:.2f}s")
    print(f"  - Total assets scanned: {results.total_assets_scanned}")
    print(f"  - Database assets: {results.database_assets}")
    print(f"  - Fallback assets: {results.fallback_assets}")
    print(f"  - Average confidence: {results.average_confidence:.3f}")
    
    # Verify we got real technical analysis results
    if results.fallback_assets == 0:
        print("✗ No fallback assets processed - technical analysis may not be working")
        return False
    
    # Check individual asset conditions
    asset_conditions = results.asset_conditions
    
    for ticker in test_tickers:
        if ticker in asset_conditions:
            condition = asset_conditions[ticker]
            print(f"  - {ticker}: {condition.market.value} (confidence: {condition.confidence:.3f})")
            
            # Verify it's from technical analysis (not database)
            if condition.source.value != 'fallback':
                print(f"✗ {ticker} not using fallback technical analysis: {condition.source.value}")
                return False
            
            # Verify metadata indicates real technical analysis
            if not condition.metadata.get('technical_analysis', False):
                print(f"✗ {ticker} metadata doesn't indicate technical analysis")
                return False
        else:
            print(f"  - {ticker}: No condition (insufficient data or low confidence)")
    
    print("✓ Enhanced scanner using real data and technical analysis only")
    return True


def test_no_mock_data_generation():
    """Verify that no mock data generation methods are called"""
    print("\n=== Testing No Mock Data Generation ===")
    
    # This test ensures that the _create_mock_price_data method has been removed
    scanner = get_enhanced_asset_scanner()
    
    # Check that mock data method doesn't exist
    if hasattr(scanner, '_create_mock_price_data'):
        print("✗ Mock data generation method still exists in scanner")
        return False
    
    print("✓ No mock data generation methods found")
    
    # Test with invalid data manager to ensure graceful failure (not mock generation)
    test_ticker = 'INVALID_TICKER_12345'
    test_date = datetime.now()
    
    # Use None as data manager - should fail gracefully
    price_data = scanner._get_price_data(test_ticker, test_date, '1d', None)
    
    if price_data is not None:
        print("✗ Scanner returned data with None data manager (possible mock generation)")
        return False
    
    print("✓ Scanner correctly fails with invalid data (no mock generation)")
    return True


def test_daily_data_only_limitation():
    """Test that scanner correctly handles daily-only data limitation"""
    print("\n=== Testing Daily Data Only Limitation ===")
    
    scanner = get_enhanced_asset_scanner()
    
    # Verify timeframes are set to daily only
    if scanner.timeframes != ['1d']:
        print(f"✗ Scanner timeframes not limited to daily: {scanner.timeframes}")
        return False
    
    # Verify confidence weights are set for daily only
    if scanner.confidence_weights != {'1d': 1.0}:
        print(f"✗ Confidence weights not set for daily only: {scanner.confidence_weights}")
        return False
    
    print("✓ Scanner correctly configured for daily data only")
    
    # Test that regime detector warns about non-daily timeframes
    regime_detector = RegimeDetector()
    test_ticker = 'AAPL'
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Should return None for non-daily timeframes
    hourly_data = regime_detector.get_price_data(test_ticker, start_date, end_date, '1h')
    four_hour_data = regime_detector.get_price_data(test_ticker, start_date, end_date, '4h')
    
    if hourly_data is not None:
        print("✗ Regime detector returned data for 1h timeframe")
        return False
    
    if four_hour_data is not None:
        print("✗ Regime detector returned data for 4h timeframe")
        return False
    
    # Should return data for daily timeframe
    daily_data = regime_detector.get_price_data(test_ticker, start_date, end_date, '1d')
    
    if daily_data is None:
        print("✗ Regime detector failed to return daily data")
        return False
    
    print("✓ Regime detector correctly handles timeframe limitations")
    return True


def test_integration_performance():
    """Test performance of real data integration"""
    print("\n=== Testing Integration Performance ===")
    
    scanner = get_enhanced_asset_scanner(enable_database=False, fallback_enabled=True)
    regime_detector = RegimeDetector()
    
    test_tickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
    test_date = datetime.now() - timedelta(days=1)
    
    print(f"⚡ Testing performance with {len(test_tickers)} assets...")
    
    start_time = time.time()
    results = scanner.scan_assets(
        tickers=test_tickers,
        date=test_date,
        min_confidence=0.4,
        data_manager=regime_detector
    )
    duration = time.time() - start_time
    
    print(f"✓ Performance test completed in {duration:.2f}s")
    print(f"  - Assets per second: {len(test_tickers) / duration:.1f}")
    print(f"  - Assets processed: {results.fallback_assets}")
    
    # Performance should be reasonable (under 30 seconds for 5 assets)
    if duration > 30:
        print(f"⚠️ Performance slower than expected: {duration:.2f}s > 30s")
        return False
    
    print("✓ Performance within acceptable limits")
    return True


def main():
    """Run Phase 4 validation tests"""
    print("🧪 Module 12 Enhanced Asset Scanner - Phase 4 Validation")
    print("=" * 65)
    print("Testing Real Data Integration (No Mock Data)")
    
    tests = [
        test_real_data_manager_integration,
        test_regime_detector_real_data_interface,
        test_enhanced_scanner_no_mock_data,
        test_no_mock_data_generation,
        test_daily_data_only_limitation,
        test_integration_performance
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
    
    print("\n" + "=" * 65)
    print(f"📊 Phase 4 Validation Results:")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📈 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 Phase 4 Real Data Integration is COMPLETE and WORKING!")
        print("   ✓ No mock data generation")
        print("   ✓ Real Yahoo Finance data integration")
        print("   ✓ Proper data validation and error handling")
        print("   ✓ Performance within acceptable limits")
        print("   ✓ Daily-only data limitation properly handled")
    else:
        print(f"\n⚠️ Phase 4 has {failed} failing test(s). Please review and fix.")
        
    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)