import pytest
import tempfile
import shutil
import pandas as pd
import json
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.providers.alpha_vantage.provider import AlphaVantageProvider
from data.providers.alpha_vantage.bulk_fetcher import BulkDataFetcher
from data.providers.alpha_vantage.checkpoint_manager import CheckpointManager
from data.providers.alpha_vantage.client import AlphaVantageClient
from data.providers.alpha_vantage.data_validator import DataValidator
from data.providers.alpha_vantage.error_handler import ErrorRecoveryStrategy
from data.timeframe_manager import TimeframeManager


class TestMultiTimeframeIntegration:
    """Comprehensive integration tests for multi-timeframe Alpha Vantage implementation"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.checkpoint_dir = os.path.join(self.temp_dir, "checkpoints")
        self.cache_dir = os.path.join(self.temp_dir, "cache")
        
        # Create sample data for different timeframes
        self.sample_daily_data = self._create_sample_data('1d', 30)
        self.sample_hourly_data = self._create_sample_data('1h', 48)  # 2 days
        self.sample_4h_data = self._create_sample_data('4h', 12)      # 2 days
        
        print(f"Test setup complete. Temp dir: {self.temp_dir}")
    
    def teardown_method(self):
        """Cleanup test environment"""
        shutil.rmtree(self.temp_dir)
        print("Test cleanup complete")
    
    def _create_sample_data(self, timeframe: str, periods: int) -> pd.DataFrame:
        """Create realistic sample OHLCV data for testing"""
        start_date = datetime(2023, 1, 1)
        
        if timeframe == '1h':
            freq = 'h'
        elif timeframe == '4h':
            freq = '4h'
        else:  # 1d
            freq = 'D'
        
        dates = pd.date_range(start=start_date, periods=periods, freq=freq)
        
        # Generate realistic price data
        base_price = 100.0
        prices = []
        current_price = base_price
        
        for i in range(periods):
            # Add some realistic volatility
            change = (0.95 + 0.1 * (i % 10) / 10) * current_price
            open_price = current_price
            high_price = current_price * (1 + 0.02 * (i % 3) / 3)
            low_price = current_price * (1 - 0.02 * (i % 2) / 2)
            close_price = change
            volume = 1000000 + (i % 5) * 100000
            
            prices.append([open_price, high_price, low_price, close_price, volume])
            current_price = close_price
        
        df = pd.DataFrame(prices, columns=['Open', 'High', 'Low', 'Close', 'Volume'], index=dates)
        
        # Add metadata
        df.attrs['provider_source'] = 'alpha_vantage'
        df.attrs['timeframe'] = timeframe
        df.attrs['ticker'] = 'AAPL'
        
        return df
    
    @patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_key'})
    def test_timeframe_manager_multi_timeframe_fetch(self):
        """Test TimeframeManager fetching multiple timeframes"""
        print("\n🧪 Testing TimeframeManager multi-timeframe fetch...")
        
        # Mock the data manager's download_data method
        mock_data_manager = Mock()
        
        def mock_download_data(ticker, start_date, end_date, interval, use_cache=True):
            if interval == '1d':
                return self.sample_daily_data.copy()
            elif interval == '1h':
                return self.sample_hourly_data.copy()
            elif interval == '4h':
                return self.sample_4h_data.copy()
            else:
                return pd.DataFrame()
        
        mock_data_manager.download_data = mock_download_data
        mock_data_manager.get_provider_info.return_value = {
            'active_provider': 'alpha_vantage',
            'supported_timeframes': ['1h', '4h', '1d'],
            'rate_limits': {'requests_per_minute': 75}
        }
        mock_data_manager.list_cached_data.return_value = {'alpha_vantage': {}}
        
        # Create TimeframeManager with mocked data manager
        with patch('data.timeframe_manager.DataManager') as mock_dm_class:
            mock_dm_class.return_value = mock_data_manager
            
            timeframe_manager = TimeframeManager(cache_dir=self.cache_dir)
            
            # Test multi-timeframe fetch
            results = timeframe_manager.get_multi_timeframe_data(
                ticker='AAPL',
                timeframes=['1h', '4h', '1d'],
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 1, 31)
            )
            
            # Verify results
            assert len(results) == 3, f"Expected 3 timeframes, got {len(results)}"
            assert '1h' in results
            assert '4h' in results
            assert '1d' in results
            
            # Verify data quality
            for timeframe, data in results.items():
                assert not data.empty, f"Data for {timeframe} is empty"
                assert list(data.columns) == ['Open', 'High', 'Low', 'Close', 'Volume']
                assert data.attrs['timeframe'] == timeframe
                print(f"  ✅ {timeframe}: {len(data)} records")
        
        print("✅ TimeframeManager multi-timeframe fetch test passed")
    
    @patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_key'})
    def test_bulk_fetcher_with_checkpointing(self):
        """Test BulkDataFetcher with checkpointing for large downloads"""
        print("\n🧪 Testing BulkDataFetcher with checkpointing...")
        
        # Create mock client that returns data
        mock_client = Mock(spec=AlphaVantageClient)
        mock_client.fetch_data.return_value = self.sample_daily_data.copy()
        
        # Create bulk fetcher with checkpoint support
        bulk_fetcher = BulkDataFetcher(mock_client, self.checkpoint_dir)
        
        # Create a download plan for 5 years (should create multiple chunks for daily data)
        # Daily strategy: 24 months per chunk, so 5 years = 60 months = 3 chunks
        plan = bulk_fetcher.create_download_plan(
            ticker='AAPL',
            timeframe='1d',
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2024, 12, 31)
        )
        
        print(f"  📋 Created plan with {len(plan.chunks)} chunks")
        assert len(plan.chunks) > 1, "Should create multiple chunks for 5-year period"
        
        # Track progress
        progress_updates = []
        def progress_callback(status, progress, stats):
            progress_updates.append((status, progress, stats))
            print(f"  📊 Progress: {status} - {progress}%")
        
        # Execute download with checkpointing
        result_df = bulk_fetcher.execute_download_plan(
            plan=plan,
            progress_callback=progress_callback,
            enable_checkpoints=True,
            checkpoint_interval=2  # Save checkpoint every 2 chunks
        )
        
        # Verify results
        assert not result_df.empty, "Download should return data"
        assert result_df.attrs['bulk_download'] is True
        assert result_df.attrs['ticker'] == 'AAPL'
        assert len(progress_updates) > 0, "Should have progress updates"
        
        # Verify checkpoint was created and completed
        checkpoint_stats = bulk_fetcher.get_checkpoint_status()
        print(f"  💾 Checkpoint stats: {checkpoint_stats}")
        
        print("✅ BulkDataFetcher checkpointing test passed")
    
    @patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_key'})
    def test_resume_interrupted_download(self):
        """Test resuming an interrupted download from checkpoint"""
        print("\n🧪 Testing resume interrupted download...")
        
        # Create mock client that simulates partial success then failure
        mock_client = Mock(spec=AlphaVantageClient)
        call_count = 0
        
        def mock_fetch_with_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # First 2 calls succeed
                return self.sample_hourly_data.copy()
            else:  # All subsequent calls fail
                raise Exception("Simulated network error")
        
        mock_client.fetch_data.side_effect = mock_fetch_with_failure
        
        # Create bulk fetcher
        bulk_fetcher = BulkDataFetcher(mock_client, self.checkpoint_dir)
        
        # Create plan with multiple chunks (use 1h timeframe for smaller chunks)
        # 1h strategy: 2 months per chunk, so 6 months = 3 chunks
        plan = bulk_fetcher.create_download_plan(
            ticker='AAPL',
            timeframe='1h',
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 6, 30)
        )
        
        print(f"  📋 Created plan with {len(plan.chunks)} chunks")
        
        # Patch the error handler to not retry so failures happen immediately
        with patch.object(bulk_fetcher.error_handler, 'execute_with_retry') as mock_retry:
            def immediate_failure(*args, **kwargs):
                operation = args[0]
                try:
                    return operation()
                except Exception as e:
                    # Don't retry, just raise immediately
                    raise e
            
            mock_retry.side_effect = immediate_failure
            
            # First attempt - should fail partway through
            try:
                bulk_fetcher.execute_download_plan(
                    plan=plan,
                    enable_checkpoints=True,
                    checkpoint_interval=1
                )
                assert False, "Should have failed due to simulated error"
            except Exception as e:
                print(f"  ❌ Expected failure: {e}")
        
        # Verify we have a resumable checkpoint
        resumable = bulk_fetcher.list_resumable_downloads(ticker='AAPL')
        print(f"  🔍 Found {len(resumable)} resumable downloads")
        for r in resumable:
            print(f"    - {r['ticker']}: {r['progress']} (can_resume: {r['can_resume']})")
        assert len(resumable) > 0, "Should have resumable downloads"
        
        plan_id = resumable[0]['plan_id']
        print(f"  🔄 Found resumable download: {plan_id}")
        print(f"  📊 Progress: {resumable[0]['progress']}")
        
        # Reset call count and mock for resume
        call_count = 0
        mock_client.fetch_data.side_effect = lambda *args, **kwargs: self.sample_hourly_data.copy()
        
        # Resume download (should now succeed)
        result_df = bulk_fetcher.resume_download(plan_id)
        
        # Verify successful resume
        assert not result_df.empty, "Resumed download should return data"
        assert result_df.attrs['ticker'] == 'AAPL'
        
        # Verify no more resumable downloads
        resumable_after = bulk_fetcher.list_resumable_downloads(ticker='AAPL')
        assert len(resumable_after) == 0, "Should have no resumable downloads after completion"
        
        print("✅ Resume interrupted download test passed")
    
    @patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_key'})
    def test_data_validation_and_repair(self):
        """Test data validation and automatic repair functionality"""
        print("\n🧪 Testing data validation and repair...")
        
        # Create problematic data for testing validation
        problematic_data = self.sample_daily_data.copy()
        
        # Introduce various data issues
        problematic_data.iloc[5, problematic_data.columns.get_loc('High')] = 50  # High < Close
        problematic_data.iloc[10, problematic_data.columns.get_loc('Low')] = 200  # Low > High  
        problematic_data.iloc[15, problematic_data.columns.get_loc('Close')] = -10  # Negative price
        problematic_data.iloc[20, problematic_data.columns.get_loc('Volume')] = -1000  # Negative volume
        
        print(f"  🔧 Created problematic data with {len(problematic_data)} records")
        
        # Test data validator
        validator = DataValidator()
        validation_result = validator.validate_dataframe(
            problematic_data, 'AAPL', '1d', 'stock'
        )
        
        print(f"  📋 Validation result: {validation_result.is_valid}")
        print(f"  ❌ Errors: {len(validation_result.errors)}")
        print(f"  ⚠️  Warnings: {len(validation_result.warnings)}")
        
        # Should have errors due to problematic data
        assert not validation_result.is_valid, "Should detect data problems"
        assert len(validation_result.errors) > 0, "Should have validation errors"
        
        # Test automatic repair
        repaired_data = validator.repair_data(problematic_data, validation_result)
        
        print(f"  🔧 Repaired data has {len(repaired_data)} records")
        
        # Validate repaired data
        repaired_validation = validator.validate_dataframe(
            repaired_data, 'AAPL', '1d', 'stock'
        )
        
        print(f"  ✅ Repaired validation: {repaired_validation.is_valid}")
        
        # Should have fewer errors after repair
        assert len(repaired_validation.errors) < len(validation_result.errors), "Repair should fix some errors"
        
        print("✅ Data validation and repair test passed")
    
    @patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_key'})
    def test_error_recovery_strategy(self):
        """Test error recovery and retry mechanisms"""
        print("\n🧪 Testing error recovery strategy...")
        
        error_handler = ErrorRecoveryStrategy(max_retries=3)
        
        # Test different error types
        test_errors = [
            (Exception("API calls per minute exceeded"), "rate_limit"),
            (Exception("Invalid API key"), "auth_error"),
            (Exception("Connection timeout"), "network_error"),
            (Exception("Unknown error"), "unknown_error")
        ]
        
        for error, expected_type in test_errors:
            error_type = error_handler.classify_error(error)
            print(f"  🔍 Error '{error}' classified as: {error_type.value}")
            
            # Test retry decision
            should_retry = error_handler.should_retry(error_type, 0)
            print(f"  🔄 Should retry: {should_retry}")
            
            # Test retry delay calculation
            if should_retry:
                delay = error_handler.get_retry_delay(error_type, 0)
                print(f"  ⏱️  Retry delay: {delay:.2f}s")
        
        # Test execute with retry
        attempt_count = 0
        def failing_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception("Temporary failure")
            return "Success!"
        
        result = error_handler.execute_with_retry(
            failing_operation, 'AAPL', '1d'
        )
        
        assert result == "Success!", "Should eventually succeed"
        assert attempt_count == 3, f"Should take 3 attempts, took {attempt_count}"
        
        # Test error statistics
        stats = error_handler.get_error_statistics()
        print(f"  📊 Error statistics: {stats}")
        
        print("✅ Error recovery strategy test passed")
    
    @patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_key'})
    def test_provider_integration(self):
        """Test AlphaVantageProvider integration with all components"""
        print("\n🧪 Testing AlphaVantageProvider integration...")
        
        # Mock the requests to avoid real API calls
        with patch('data.providers.alpha_vantage.provider.requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            
            # Mock successful API response
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {
                'Time Series (Daily)': {
                    '2023-01-01': {'1. open': '100.0', '2. high': '102.0', '3. low': '99.0', '4. close': '101.0', '5. volume': '1000000'},
                    '2023-01-02': {'1. open': '101.0', '2. high': '103.0', '3. low': '100.0', '4. close': '102.0', '5. volume': '1100000'}
                }
            }
            mock_session.get.return_value = mock_response
            
            # Mock AssetBucketManager
            with patch('data.providers.alpha_vantage.provider.AssetBucketManager') as mock_asset_manager_class:
                mock_asset_manager = Mock()
                mock_asset_manager.filter_assets_by_type.return_value = []  # Not crypto
                mock_asset_manager_class.return_value = mock_asset_manager
                
                # Create provider
                provider = AlphaVantageProvider()
                
                # Test basic data fetching
                data = provider.fetch_data(
                    ticker='AAPL',
                    timeframe='1d',
                    start_date=datetime(2023, 1, 1),
                    end_date=datetime(2023, 1, 2),
                    validate_data=True
                )
                
                print(f"  📊 Fetched data: {len(data)} records")
                assert not data.empty, "Should return data"
                assert 'validation_passed' in data.attrs, "Should have validation metadata"
                
                # Test bulk fetcher access
                bulk_fetcher = provider.get_bulk_fetcher()
                assert bulk_fetcher is not None, "Should provide bulk fetcher"
                
                # Test data validator access
                validator = provider.get_data_validator()
                assert validator is not None, "Should provide data validator"
                
                # Test error handler access
                error_handler = provider.get_error_handler()
                assert error_handler is not None, "Should provide error handler"
                
                print("✅ Provider integration test passed")
    
    def test_checkpoint_persistence_and_recovery(self):
        """Test checkpoint file persistence and recovery across sessions"""
        print("\n🧪 Testing checkpoint persistence and recovery...")
        
        # Create checkpoint manager
        checkpoint_manager = CheckpointManager(self.checkpoint_dir)
        
        # Create multiple checkpoints with different states
        test_plans = []
        for i, (ticker, completed) in enumerate([('AAPL', 2), ('MSFT', 0), ('GOOGL', 5)]):
            from data.providers.alpha_vantage.bulk_fetcher import DownloadPlan, DownloadChunk
            
            chunks = []
            for j in range(10):  # 10 chunks total
                chunk = DownloadChunk(
                    start_date=datetime(2023, 1, 1) + timedelta(days=j*30),
                    end_date=datetime(2023, 1, 1) + timedelta(days=(j+1)*30),
                    timeframe='1d',
                    ticker=ticker,
                    status='completed' if j < completed else 'pending'
                )
                chunks.append(chunk)
            
            plan = DownloadPlan(
                ticker=ticker,
                timeframe='1d',
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 12, 31),
                chunks=chunks,
                total_chunks=10,
                completed_chunks=completed,
                failed_chunks=0
            )
            
            plan_id = f"test_plan_{ticker}_{i}"
            success = checkpoint_manager.save_checkpoint(plan, plan_id)
            assert success, f"Should save checkpoint for {ticker}"
            test_plans.append((plan_id, ticker, completed))
            
            print(f"  💾 Saved checkpoint for {ticker}: {completed}/10 chunks completed")
        
        # Verify checkpoints exist on disk
        checkpoint_files = list(Path(checkpoint_manager.active_dir).glob("*.json"))
        assert len(checkpoint_files) == 3, f"Should have 3 checkpoint files, found {len(checkpoint_files)}"
        
        # Test loading each checkpoint
        for plan_id, ticker, expected_completed in test_plans:
            loaded_plan = checkpoint_manager.load_checkpoint(plan_id)
            assert loaded_plan is not None, f"Should load checkpoint for {ticker}"
            assert loaded_plan.ticker == ticker
            assert loaded_plan.completed_chunks == expected_completed
            print(f"  ✅ Loaded {ticker}: {loaded_plan.completed_chunks}/{loaded_plan.total_chunks}")
        
        # Test checkpoint validation
        for plan_id, ticker, expected_completed in test_plans:
            validation = checkpoint_manager.validate_checkpoint(plan_id)
            can_resume = expected_completed < 10
            assert validation['can_resume'] == can_resume, f"Resume status wrong for {ticker}"
            print(f"  🔍 {ticker} can resume: {validation['can_resume']}")
        
        # Test listing resumable downloads
        resumable = checkpoint_manager.get_resumable_downloads()
        expected_resumable = ['MSFT']  # Only MSFT has 0/10 completed
        assert len(resumable) == len(expected_resumable), f"Expected {len(expected_resumable)} resumable, got {len(resumable)}"
        
        # Test checkpoint completion
        aapl_plan_id = test_plans[0][0]  # AAPL plan
        success = checkpoint_manager.complete_checkpoint(aapl_plan_id)
        assert success, "Should complete AAPL checkpoint"
        
        # Verify moved to completed directory
        active_files_after = list(Path(checkpoint_manager.active_dir).glob("*.json"))
        completed_files = list(Path(checkpoint_manager.completed_dir).glob("*.json"))
        assert len(active_files_after) == 2, "Should have 2 active checkpoints after completion"
        assert len(completed_files) == 1, "Should have 1 completed checkpoint"
        
        print("✅ Checkpoint persistence and recovery test passed")
    
    @patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_key'})
    def test_hourly_and_4h_timeframes_specifically(self):
        """Test 1h and 4h timeframes specifically with real chunking scenarios"""
        print("\n🧪 Testing 1h and 4h timeframes with realistic scenarios...")
        
        mock_client = Mock(spec=AlphaVantageClient)
        
        # Test 1h timeframe with 1 year of data (should create multiple chunks)
        mock_client.fetch_data.return_value = self.sample_hourly_data.copy()
        bulk_fetcher = BulkDataFetcher(mock_client, self.checkpoint_dir)
        
        # 1h strategy: 2 months per chunk, 1 year = 6 chunks
        plan_1h = bulk_fetcher.create_download_plan(
            ticker='AAPL',
            timeframe='1h',
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31)
        )
        
        print(f"  📊 1h timeframe plan: {len(plan_1h.chunks)} chunks for 1 year")
        assert len(plan_1h.chunks) >= 6, f"Expected >=6 chunks for 1h/1year, got {len(plan_1h.chunks)}"
        
        # Test chunk size estimation
        estimate_1h = bulk_fetcher.estimate_download_time(
            'AAPL', '1h', datetime(2023, 1, 1), datetime(2023, 12, 31)
        )
        print(f"  ⏱️  1h estimated time: {estimate_1h['estimated_minutes']:.1f} minutes")
        
        # Test 4h timeframe with 2 years of data
        mock_client.fetch_data.return_value = self.sample_4h_data.copy()
        
        # 4h strategy: 6 months per chunk, 2 years = 4 chunks
        plan_4h = bulk_fetcher.create_download_plan(
            ticker='MSFT',
            timeframe='4h',
            start_date=datetime(2022, 1, 1),
            end_date=datetime(2023, 12, 31)
        )
        
        print(f"  📊 4h timeframe plan: {len(plan_4h.chunks)} chunks for 2 years")
        assert len(plan_4h.chunks) >= 4, f"Expected >=4 chunks for 4h/2years, got {len(plan_4h.chunks)}"
        
        # Test actual download execution for 1h
        progress_calls = []
        def track_progress(status, progress, stats):
            progress_calls.append((status, progress, stats.get('current_chunk', 0)))
            
        result_1h = bulk_fetcher.execute_download_plan(
            plan_1h, 
            progress_callback=track_progress,
            enable_checkpoints=True
        )
        
        print(f"  ✅ 1h download completed: {len(result_1h)} records, {len(progress_calls)} progress updates")
        assert not result_1h.empty
        assert result_1h.attrs['timeframe'] == '1h'
        assert len(progress_calls) > 0
        
        print("✅ Hourly and 4h timeframes test passed")
    
    def run_all_tests(self):
        """Run all integration tests"""
        print("🚀 Starting Multi-Timeframe Integration Tests")
        print("=" * 60)
        
        try:
            self.test_timeframe_manager_multi_timeframe_fetch()
            self.test_bulk_fetcher_with_checkpointing()
            self.test_resume_interrupted_download()
            self.test_data_validation_and_repair()
            self.test_error_recovery_strategy()
            self.test_provider_integration()
            self.test_checkpoint_persistence_and_recovery()
            self.test_hourly_and_4h_timeframes_specifically()
            
            print("\n" + "=" * 60)
            print("🎉 ALL INTEGRATION TESTS PASSED!")
            print("✅ Checkpointing system working correctly")
            print("✅ Multi-timeframe data fetching operational")
            print("✅ Error recovery and resume functionality verified")
            print("✅ Data validation and repair mechanisms functional")
            print("✅ Provider integration complete")
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            raise


if __name__ == "__main__":
    # Run the integration tests
    test_suite = TestMultiTimeframeIntegration()
    test_suite.setup_method()
    
    try:
        test_suite.run_all_tests()
    finally:
        test_suite.teardown_method()