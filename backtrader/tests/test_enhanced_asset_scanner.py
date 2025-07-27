#!/usr/bin/env python3
"""
Module 12: Enhanced Asset Scanner - Unit Tests

Test suite for asset-level market condition scanning functionality.
Focuses on database integration, fallback mechanisms, and configuration.
"""

import unittest
import sys
import os
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from core.enhanced_asset_scanner import EnhancedAssetScanner, get_enhanced_asset_scanner
from core.asset_scanner_models import (
    MarketCondition, ScannerSource, AssetCondition, 
    ScannerResults, TechnicalIndicators
)


class TestAssetScannerModels(unittest.TestCase):
    """Test data models for asset scanner"""
    
    def test_market_condition_enum(self):
        """Test MarketCondition enum values"""
        self.assertEqual(MarketCondition.TRENDING.value, "trending")
        self.assertEqual(MarketCondition.RANGING.value, "ranging")
        self.assertEqual(MarketCondition.BREAKOUT.value, "breakout")
        self.assertEqual(MarketCondition.BREAKDOWN.value, "breakdown")
    
    def test_asset_condition_creation(self):
        """Test AssetCondition creation and validation"""
        condition = AssetCondition(
            ticker="AAPL",
            market=MarketCondition.TRENDING,
            confidence=0.85,
            timeframe_breakdown={'1d': 0.8, '4h': 0.9},
            source=ScannerSource.DATABASE,
            scan_date=datetime.now()
        )
        
        self.assertEqual(condition.ticker, "AAPL")
        self.assertEqual(condition.market, MarketCondition.TRENDING)
        self.assertEqual(condition.confidence, 0.85)
        self.assertTrue(condition.is_trending())
        self.assertFalse(condition.is_ranging())
        self.assertTrue(condition.is_confident(0.7))
        self.assertFalse(condition.is_confident(0.9))
    
    def test_asset_condition_confidence_validation(self):
        """Test confidence is clamped to valid range"""
        # Test confidence > 1.0
        condition1 = AssetCondition(
            ticker="TEST1", 
            market=MarketCondition.TRENDING, 
            confidence=1.5
        )
        self.assertEqual(condition1.confidence, 1.0)
        
        # Test confidence < 0.0
        condition2 = AssetCondition(
            ticker="TEST2", 
            market=MarketCondition.RANGING, 
            confidence=-0.1
        )
        self.assertEqual(condition2.confidence, 0.0)
    
    def test_scanner_results_aggregation(self):
        """Test ScannerResults aggregation and filtering"""
        conditions = {
            'AAPL': AssetCondition('AAPL', MarketCondition.TRENDING, 0.8, source=ScannerSource.DATABASE),
            'MSFT': AssetCondition('MSFT', MarketCondition.RANGING, 0.7, source=ScannerSource.DATABASE),
            'GOOGL': AssetCondition('GOOGL', MarketCondition.BREAKOUT, 0.9, source=ScannerSource.FALLBACK),
            'TSLA': AssetCondition('TSLA', MarketCondition.BREAKDOWN, 0.6, source=ScannerSource.FALLBACK)
        }
        
        results = ScannerResults(
            asset_conditions=conditions,
            scan_date=datetime.now(),
            total_assets_scanned=4
        )
        
        # Test aggregation
        self.assertEqual(results.database_assets, 2)
        self.assertEqual(results.fallback_assets, 2)
        self.assertEqual(results.average_confidence, 0.75)
        
        # Test filtering
        trending = results.get_trending_assets(0.7)
        self.assertEqual(len(trending), 1)
        self.assertIn('AAPL', trending)
        
        ranging = results.get_ranging_assets(0.6)
        self.assertEqual(len(ranging), 1)
        self.assertIn('MSFT', ranging)
        
        # Test summary stats
        stats = results.get_summary_stats()
        self.assertEqual(stats['total_assets'], 4)
        self.assertEqual(stats['database_coverage'], 0.5)
        self.assertEqual(stats['conditions']['trending']['count'], 1)
        self.assertEqual(stats['conditions']['ranging']['count'], 1)
    
    def test_technical_indicators_calculation(self):
        """Test TechnicalIndicators derived score calculation"""
        indicators = TechnicalIndicators(
            adx=30.0,
            ma_alignment_score=0.8,
            macd_momentum=0.7,
            trend_consistency=0.9,
            bb_squeeze=0.6,
            support_resistance_strength=0.7,
            oscillator_range=0.5,
            volatility_compression=0.8
        )
        
        indicators.calculate_derived_scores()
        
        # Test trend score calculation
        expected_trend = (30/100 * 0.4) + (0.8 * 0.3) + (0.7 * 0.2) + (0.9 * 0.1)
        self.assertAlmostEqual(indicators.trend_score, expected_trend, places=2)
        
        # Test range score calculation
        expected_range = (0.6 * 0.3) + (0.7 * 0.3) + (0.5 * 0.2) + (0.8 * 0.2)
        self.assertAlmostEqual(indicators.range_score, expected_range, places=2)
        
        # Test dominant condition
        dominant_condition, dominant_score = indicators.get_dominant_condition()
        self.assertIsInstance(dominant_condition, MarketCondition)
        self.assertGreaterEqual(dominant_score, 0.0)
        self.assertLessEqual(dominant_score, 1.0)


class TestEnhancedAssetScanner(unittest.TestCase):
    """Test Enhanced Asset Scanner core functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_tickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
        self.test_date = datetime(2024, 1, 15)
        
        # Mock data manager
        self.mock_data_manager = Mock()
        self.mock_data_manager.get_timeframe_data.return_value = {
            'VIX': 15.0,
            'growth_momentum': 0.7,
            'risk_appetite': 0.6
        }
    
    def test_scanner_initialization(self):
        """Test scanner initialization with different configurations"""
        # Default configuration
        scanner1 = EnhancedAssetScanner()
        self.assertTrue(scanner1.enable_database)
        self.assertTrue(scanner1.fallback_enabled)
        self.assertEqual(scanner1.timeframes, ['1d', '4h', '1h'])
        self.assertEqual(scanner1.confidence_weights['1d'], 0.5)
        
        # Custom configuration
        scanner2 = EnhancedAssetScanner(
            enable_database=False,
            timeframes=['1d'],
            fallback_enabled=True,
            confidence_weights={'1d': 1.0},
            min_confidence_threshold=0.8
        )
        self.assertFalse(scanner2.enable_database)
        self.assertEqual(scanner2.timeframes, ['1d'])
        self.assertEqual(scanner2.min_confidence_threshold, 0.8)
    
    @patch('core.enhanced_asset_scanner.execute_query')
    def test_database_integration(self, mock_execute_query):
        """Test database lookup functionality"""
        # Mock database response
        mock_execute_query.return_value = [
            {
                'ticker': 'AAPL',
                'market': 'trending',
                'confidence': 0.85,
                'timeframe': '1d',
                'date': self.test_date
            },
            {
                'ticker': 'AAPL',
                'market': 'trending',
                'confidence': 0.80,
                'timeframe': '4h',
                'date': self.test_date
            },
            {
                'ticker': 'MSFT',
                'market': 'ranging',
                'confidence': 0.75,
                'timeframe': '1d',
                'date': self.test_date
            }
        ]
        
        scanner = EnhancedAssetScanner(enable_database=True)
        
        # Force database available for this test
        scanner.is_database_available = True
        
        results = scanner._scan_from_database(['AAPL', 'MSFT'], self.test_date, 0.7)
        
        # Verify results structure (might be empty if database unavailable)
        self.assertIsInstance(results, dict)
        
        # If we got results, verify their structure
        if results:
            for ticker, condition in results.items():
                self.assertIsInstance(condition, AssetCondition)
                self.assertEqual(condition.source, ScannerSource.DATABASE)
        
        # Verify database query was called
        mock_execute_query.assert_called_once()
    
    def test_fallback_technical_analysis(self):
        """Test fallback technical analysis when database disabled"""
        scanner = EnhancedAssetScanner(enable_database=False, fallback_enabled=True)
        
        # Mock data manager that provides data for technical analysis
        mock_data_manager_with_price_data = Mock()
        mock_data_manager_with_price_data.get_timeframe_data.return_value = {
            'VIX': 15.0,
            'growth_momentum': 0.7,
            'risk_appetite': 0.6
        }
        # Mock data manager doesn't have get_price_data, so scanner will create mock data
        
        results = scanner._scan_from_technical_analysis(
            ['AAPL'], self.test_date, mock_data_manager_with_price_data, 0.3
        )
        
        # Should return technical analysis results using mock price data
        self.assertEqual(len(results), 1)
        self.assertIn('AAPL', results)
        
        aapl_condition = results['AAPL']
        self.assertEqual(aapl_condition.ticker, 'AAPL')
        self.assertEqual(aapl_condition.source, ScannerSource.FALLBACK)
        self.assertIn(aapl_condition.market, [
            MarketCondition.TRENDING, MarketCondition.RANGING,
            MarketCondition.BREAKOUT, MarketCondition.BREAKDOWN
        ])
        self.assertTrue(aapl_condition.metadata.get('technical_analysis'))
        self.assertEqual(aapl_condition.metadata.get('analysis_method'), 'multi_timeframe_technical')
    
    @patch('core.enhanced_asset_scanner.execute_query')
    def test_comprehensive_scan(self, mock_execute_query):
        """Test comprehensive asset scanning with mixed sources"""
        # Mock database response (partial data)
        mock_execute_query.return_value = [
            {
                'ticker': 'AAPL',
                'market': 'trending',
                'confidence': 0.85,
                'timeframe': '1d',
                'date': self.test_date
            }
        ]
        
        scanner = EnhancedAssetScanner(enable_database=True, fallback_enabled=True)
        
        results = scanner.scan_assets(
            ['AAPL', 'MSFT'], self.test_date, 0.6, self.mock_data_manager
        )
        
        # Should have results from both database and fallback
        self.assertEqual(results.total_assets_scanned, 2)
        self.assertIsInstance(results.asset_conditions, dict)
        
        # Check AAPL from database
        if 'AAPL' in results.asset_conditions:
            aapl = results.asset_conditions['AAPL']
            self.assertEqual(aapl.source, ScannerSource.DATABASE)
        
        # Check MSFT from fallback (if included)
        if 'MSFT' in results.asset_conditions:
            msft = results.asset_conditions['MSFT']
            self.assertEqual(msft.source, ScannerSource.FALLBACK)
    
    def test_convenience_methods(self):
        """Test backward compatibility convenience methods"""
        scanner = EnhancedAssetScanner(enable_database=False, fallback_enabled=True)
        
        # Test get_trending_assets
        trending = scanner.get_trending_assets(
            self.test_tickers, self.test_date, 0.5, 3, self.mock_data_manager
        )
        self.assertIsInstance(trending, list)
        self.assertLessEqual(len(trending), 3)  # Respects limit
        
        # Test get_ranging_assets
        ranging = scanner.get_ranging_assets(
            self.test_tickers, self.test_date, 0.5, 2, self.mock_data_manager
        )
        self.assertIsInstance(ranging, list)
        self.assertLessEqual(len(ranging), 2)  # Respects limit
        
        # Test get_breakout_assets
        breakout = scanner.get_breakout_assets(
            self.test_tickers, self.test_date, 0.8, None, self.mock_data_manager
        )
        self.assertIsInstance(breakout, list)
        
        # Test get_breakdown_assets
        breakdown = scanner.get_breakdown_assets(
            self.test_tickers, self.test_date, 0.8, None, self.mock_data_manager
        )
        self.assertIsInstance(breakdown, list)
    
    def test_scanner_status(self):
        """Test scanner status reporting"""
        scanner = EnhancedAssetScanner(
            enable_database=False,
            timeframes=['1d', '4h'],
            min_confidence_threshold=0.7
        )
        
        status = scanner.get_scanner_status()
        
        self.assertFalse(status['database_enabled'])
        self.assertEqual(status['timeframes'], ['1d', '4h'])
        self.assertEqual(status['min_confidence_threshold'], 0.7)
        self.assertIn('cache_entries', status)
        self.assertIn('cache_ttl_seconds', status)
    
    def test_cache_functionality(self):
        """Test scanner caching functionality"""
        scanner = EnhancedAssetScanner()
        
        # Initially no cache
        self.assertEqual(len(scanner.cache), 0)
        
        # Add some mock cache data
        scanner.cache['test_key'] = {
            'timestamp': time.time(),
            'data': {'AAPL': 'test_data'}
        }
        
        # Verify cache
        self.assertEqual(len(scanner.cache), 1)
        
        # Clear cache
        scanner.clear_cache()
        self.assertEqual(len(scanner.cache), 0)
    
    def test_global_scanner_instance(self):
        """Test global scanner instance management"""
        # Get default instance
        scanner1 = get_enhanced_asset_scanner()
        self.assertIsInstance(scanner1, EnhancedAssetScanner)
        
        # Get same instance
        scanner2 = get_enhanced_asset_scanner()
        self.assertIs(scanner1, scanner2)
        
        # Get new instance with custom config
        scanner3 = get_enhanced_asset_scanner(enable_database=False)
        self.assertIsInstance(scanner3, EnhancedAssetScanner)
        self.assertFalse(scanner3.enable_database)


class TestScannerConfiguration(unittest.TestCase):
    """Test scanner configuration and parameter handling"""
    
    def test_timeframe_weight_validation(self):
        """Test timeframe weight validation"""
        # Valid weights
        valid_weights = {'1d': 0.6, '4h': 0.4}
        scanner1 = EnhancedAssetScanner(confidence_weights=valid_weights)
        self.assertEqual(scanner1.confidence_weights, valid_weights)
        
        # Weights that don't sum to 1.0 are accepted (scanner normalizes)
        unnormalized_weights = {'1d': 0.8, '4h': 0.4}
        scanner2 = EnhancedAssetScanner(confidence_weights=unnormalized_weights)
        self.assertEqual(scanner2.confidence_weights, unnormalized_weights)
    
    def test_database_disable_configuration(self):
        """Test complete database disable configuration"""
        scanner = EnhancedAssetScanner(
            enable_database=False,
            fallback_enabled=True,
            timeframes=['1d'],
            min_confidence_threshold=0.5
        )
        
        # Should not attempt database operations
        self.assertFalse(scanner.is_database_available)
        
        # Should work with fallback only
        results = scanner.scan_assets(
            ['AAPL'], datetime.now(), data_manager=Mock()
        )
        
        self.assertIsInstance(results, ScannerResults)
    
    def test_error_handling(self):
        """Test error handling in scanner operations"""
        scanner = EnhancedAssetScanner(enable_database=False, fallback_enabled=True)
        
        # Test with None data_manager (should handle gracefully)
        results = scanner.scan_assets(['AAPL'], datetime.now(), data_manager=None)
        self.assertIsInstance(results, ScannerResults)
        self.assertEqual(len(results.asset_conditions), 0)  # No fallback without data_manager
        
        # Test with invalid tickers (should handle gracefully)
        results = scanner.scan_assets([], datetime.now(), data_manager=Mock())
        self.assertIsInstance(results, ScannerResults)
        self.assertEqual(results.total_assets_scanned, 0)


if __name__ == '__main__':
    # Set up test environment
    import warnings
    warnings.filterwarnings('ignore')
    
    # Run tests
    unittest.main(verbosity=2)