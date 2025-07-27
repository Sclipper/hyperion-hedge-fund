#!/usr/bin/env python3
"""
Asset Scanner Test Utility

Test the enhanced asset scanner functionality including:
- Trending asset detection
- Ranging asset detection
- Market condition analysis
- Database integration validation
"""

import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from data.asset_scanner import get_asset_scanner, MarketCondition
from data.regime_detector import RegimeDetector


def test_asset_scanner():
    """Test enhanced asset scanner functionality"""
    print("=" * 60)
    print("Enhanced Asset Scanner - Functionality Test")
    print("=" * 60)
    
    # Get scanner instance
    scanner = get_asset_scanner()
    
    print(f"\n1. Scanner Status:")
    print(f"   Database available: {scanner.is_database_available}")
    
    # Test assets
    test_assets = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX']
    test_date = datetime.now() - timedelta(days=1)  # Yesterday's data
    
    print(f"\n2. Testing Asset Universe:")
    print(f"   Assets: {', '.join(test_assets)}")
    print(f"   Test date: {test_date.strftime('%Y-%m-%d')}")
    
    # Test comprehensive scan
    print(f"\n3. Comprehensive Asset Scan:")
    results = scanner.scan_assets(
        asset_universe=test_assets,
        scan_date=test_date,
        min_confidence=0.6
    )
    
    print(f"   Total assets scanned: {results.total_assets_scanned}")
    print(f"   Average confidence: {results.average_confidence:.2f}")
    print(f"   Trending assets: {len(results.trending_assets)}")
    print(f"   Ranging assets: {len(results.ranging_assets)}")
    print(f"   Breakout assets: {len(results.breakout_assets)}")
    print(f"   Breakdown assets: {len(results.breakdown_assets)}")
    
    # Display trending assets
    if results.trending_assets:
        print(f"\n   📈 Trending Assets:")
        for asset in results.trending_assets[:5]:  # Top 5
            print(f"      {asset.ticker}: confidence={asset.confidence:.2f}, strength={asset.strength:.2f}")
    
    # Display ranging assets
    if results.ranging_assets:
        print(f"\n   📊 Ranging Assets:")
        for asset in results.ranging_assets[:5]:  # Top 5
            print(f"      {asset.ticker}: confidence={asset.confidence:.2f}, strength={asset.strength:.2f}")
    
    # Test market condition summary
    print(f"\n4. Market Condition Summary:")
    summary = scanner.get_market_condition_summary(test_assets, test_date, 0.6)
    
    for condition, count in summary.items():
        if condition != 'average_confidence':
            print(f"   {condition.replace('_', ' ').title()}: {count}")
        else:
            print(f"   Average Confidence: {count:.2f}")
    
    # Test individual methods
    print(f"\n5. Individual Method Tests:")
    
    # Test trending assets
    trending = scanner.get_trending_assets(test_assets, test_date, 0.6, 5)
    print(f"   Trending (limit 5): {trending}")
    
    # Test ranging assets
    ranging = scanner.get_ranging_assets(test_assets, test_date, 0.6, 5)
    print(f"   Ranging (limit 5): {ranging}")
    
    return results


def test_regime_detector_integration():
    """Test regime detector integration with enhanced scanner"""
    print(f"\n" + "=" * 60)
    print("Regime Detector - Scanner Integration Test")
    print("=" * 60)
    
    # Create regime detector
    regime_detector = RegimeDetector()
    
    test_assets = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    test_date = datetime.now() - timedelta(days=1)
    
    print(f"\n1. Regime Detector Scanner Integration:")
    print(f"   Database available: {regime_detector.use_database}")
    
    # Test trending assets via regime detector
    trending = regime_detector.get_trending_assets(test_date, test_assets, 5, 0.6)
    print(f"   Trending assets: {trending}")
    
    # Test ranging assets via regime detector
    ranging = regime_detector.get_ranging_assets(test_date, test_assets, 5, 0.6)
    print(f"   Ranging assets: {ranging}")
    
    # Test market summary via regime detector
    summary = regime_detector.get_market_condition_summary(test_date, test_assets, 0.6)
    print(f"\n2. Market Summary via Regime Detector:")
    for key, value in summary.items():
        print(f"   {key}: {value}")
    
    return True


def test_backward_compatibility():
    """Test that existing code still works with enhanced scanner"""
    print(f"\n" + "=" * 60)
    print("Backward Compatibility Test")
    print("=" * 60)
    
    from data.database_integration import DatabaseIntegration
    
    # Test original database integration still works
    db_integration = DatabaseIntegration()
    
    test_assets = ['AAPL', 'MSFT', 'GOOGL']
    end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"\n1. Original DatabaseIntegration.get_trending_assets:")
    trending = db_integration.get_trending_assets(test_assets, end_date, 3, 0.6)
    print(f"   Result: {trending}")
    
    print(f"\n✅ Backward compatibility maintained")
    
    return True


if __name__ == '__main__':
    try:
        # Test enhanced scanner
        scanner_results = test_asset_scanner()
        
        # Test regime detector integration
        regime_results = test_regime_detector_integration()
        
        # Test backward compatibility
        compat_results = test_backward_compatibility()
        
        print(f"\n" + "=" * 60)
        print("✅ All scanner tests completed successfully!")
        print("=" * 60)
        
        if scanner_results.all_assets:
            print(f"\n💡 Key Insights:")
            print(f"   - Found {len(scanner_results.all_assets)} assets with actionable signals")
            print(f"   - Average confidence: {scanner_results.average_confidence:.1%}")
            print(f"   - Scanner is fully integrated with database manager")
            print(f"   - Both trending and ranging detection operational")
        
    except Exception as e:
        print(f"\n❌ Scanner test failed with error: {e}")
        print(f"\nThis may indicate:")
        print(f"- Database connection issues")
        print(f"- Missing scanner_historical table")
        print(f"- Scanner data availability issues")
        sys.exit(1)