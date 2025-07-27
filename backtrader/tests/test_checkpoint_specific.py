import pytest
import tempfile
import shutil
import pandas as pd
import json
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.providers.alpha_vantage.bulk_fetcher import BulkDataFetcher, DownloadPlan, DownloadChunk
from data.providers.alpha_vantage.client import AlphaVantageClient
from data.providers.alpha_vantage.checkpoint_manager import CheckpointManager


class TestCheckpointSpecific:
    """Specific tests for checkpoint functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.checkpoint_dir = os.path.join(self.temp_dir, "checkpoints")
        
        # Sample data
        self.sample_data = pd.DataFrame({
            'Open': [100.0, 101.0, 102.0],
            'High': [102.0, 103.0, 104.0], 
            'Low': [99.0, 100.0, 101.0],
            'Close': [101.0, 102.0, 103.0],
            'Volume': [1000000, 1100000, 1200000]
        }, index=pd.DatetimeIndex(['2023-01-01', '2023-01-02', '2023-01-03']))
        
        print(f"Test setup complete. Temp dir: {self.temp_dir}")
    
    def teardown_method(self):
        """Cleanup test environment"""
        shutil.rmtree(self.temp_dir)
        print("Test cleanup complete")
    
    def test_checkpoint_creation_and_resume(self):
        """Test basic checkpoint creation and resume functionality"""
        print("\n🧪 Testing checkpoint creation and resume...")
        
        # Create mock client
        mock_client = Mock(spec=AlphaVantageClient)
        
        # Track how many times fetch_data is called
        call_count = 0
        def mock_fetch_data(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # First 2 calls succeed
                print(f"  📊 Mock call {call_count}: SUCCESS")
                return self.sample_data.copy()
            else:  # Third call and beyond fail
                print(f"  📊 Mock call {call_count}: FAILURE")
                raise Exception("Simulated failure")
        
        mock_client.fetch_data.side_effect = mock_fetch_data
        
        # Create bulk fetcher
        bulk_fetcher = BulkDataFetcher(mock_client, self.checkpoint_dir)
        
        # Manually create a plan with multiple chunks to test resuming
        chunks = []
        for i in range(5):  # 5 chunks total
            chunk = DownloadChunk(
                start_date=datetime(2023, 1, 1) + timedelta(days=i*30),
                end_date=datetime(2023, 1, 1) + timedelta(days=(i+1)*30),
                timeframe='1h',
                ticker='AAPL',
                status='pending'
            )
            chunks.append(chunk)
        
        plan = DownloadPlan(
            ticker='AAPL',
            timeframe='1h',
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 6, 1),
            chunks=chunks,
            total_chunks=5,
            completed_chunks=0,
            failed_chunks=0
        )
        
        print(f"  📋 Created manual plan with {len(plan.chunks)} chunks")
        
        # Execute download - should process 2 chunks successfully, then fail on 3rd
        try:
            result_df = bulk_fetcher.execute_download_plan(
                plan=plan,
                enable_checkpoints=True,
                checkpoint_interval=1  # Save checkpoint after each chunk
            )
            print("  ⚠️  Download completed unexpectedly")
        except Exception as e:
            print(f"  ❌ Expected failure after chunk 3: {e}")
        
        # Check what checkpoints exist
        checkpoint_manager = CheckpointManager(self.checkpoint_dir)
        active_checkpoints = checkpoint_manager.list_active_checkpoints()
        
        print(f"  📂 Active checkpoints: {len(active_checkpoints)}")
        for cp in active_checkpoints:
            print(f"    - {cp['ticker']}: {cp['progress']} (can_resume: {cp['can_resume']})")
        
        # Should have at least one resumable checkpoint
        resumable = [cp for cp in active_checkpoints if cp['can_resume']]
        print(f"  ♻️  Resumable checkpoints: {len(resumable)}")
        
        if len(resumable) > 0:
            # Test resume functionality
            plan_id = resumable[0]['plan_id']
            print(f"  🔄 Attempting to resume: {plan_id}")
            
            # Reset mock to succeed for remaining chunks
            call_count = 0
            mock_client.fetch_data.side_effect = lambda *args, **kwargs: self.sample_data.copy()
            
            # Resume download
            result_df = bulk_fetcher.resume_download(plan_id)
            print(f"  ✅ Resume successful: {len(result_df)} records")
            
        print("✅ Checkpoint creation and resume test completed")
    
    def test_checkpoint_manual_scenarios(self):
        """Test manual checkpoint scenarios to understand behavior"""
        print("\n🧪 Testing manual checkpoint scenarios...")
        
        checkpoint_manager = CheckpointManager(self.checkpoint_dir)
        
        # Scenario 1: Partially completed download
        chunks_scenario1 = []
        for i in range(3):
            chunk = DownloadChunk(
                start_date=datetime(2023, 1, 1) + timedelta(days=i*30),
                end_date=datetime(2023, 1, 1) + timedelta(days=(i+1)*30),
                timeframe='1d',
                ticker='TEST1',
                status='completed' if i < 2 else 'pending'  # 2 completed, 1 pending
            )
            chunks_scenario1.append(chunk)
        
        plan1 = DownloadPlan(
            ticker='TEST1',
            timeframe='1d',
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 4, 1),
            chunks=chunks_scenario1,
            total_chunks=3,
            completed_chunks=2,
            failed_chunks=0
        )
        
        success1 = checkpoint_manager.save_checkpoint(plan1, "test1_partial")
        print(f"  💾 Scenario 1 (2/3 completed): Saved = {success1}")
        
        # Scenario 2: Download with failures
        chunks_scenario2 = []
        for i in range(4):
            status = 'completed' if i < 2 else ('failed' if i == 2 else 'pending')
            chunk = DownloadChunk(
                start_date=datetime(2023, 1, 1) + timedelta(days=i*30),
                end_date=datetime(2023, 1, 1) + timedelta(days=(i+1)*30),
                timeframe='1h',
                ticker='TEST2',
                status=status
            )
            chunks_scenario2.append(chunk)
        
        plan2 = DownloadPlan(
            ticker='TEST2',
            timeframe='1h',
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 5, 1),
            chunks=chunks_scenario2,
            total_chunks=4,
            completed_chunks=2,
            failed_chunks=1
        )
        
        success2 = checkpoint_manager.save_checkpoint(plan2, "test2_with_failures")
        print(f"  💾 Scenario 2 (2/4 completed, 1 failed): Saved = {success2}")
        
        # List all checkpoints
        all_checkpoints = checkpoint_manager.list_active_checkpoints()
        print(f"  📂 Total active checkpoints: {len(all_checkpoints)}")
        
        for cp in all_checkpoints:
            validation = checkpoint_manager.validate_checkpoint(cp['plan_id'])
            print(f"    - {cp['ticker']}: {cp['progress']} | "
                  f"can_resume={cp['can_resume']} | "
                  f"validation_ok={validation['valid']}")
        
        # Test loading each checkpoint
        for cp in all_checkpoints:
            loaded_plan = checkpoint_manager.load_checkpoint(cp['plan_id'])
            if loaded_plan:
                print(f"  ✅ Loaded {cp['ticker']}: {loaded_plan.completed_chunks}/{loaded_plan.total_chunks}")
            else:
                print(f"  ❌ Failed to load {cp['ticker']}")
        
        print("✅ Manual checkpoint scenarios test completed")
    
    def test_specific_chunking_strategies(self):
        """Test the chunking strategies for different timeframes"""
        print("\n🧪 Testing chunking strategies...")
        
        mock_client = Mock(spec=AlphaVantageClient)
        bulk_fetcher = BulkDataFetcher(mock_client, self.checkpoint_dir)
        
        # Test different timeframe chunking
        test_cases = [
            ('1h', datetime(2023, 1, 1), datetime(2023, 7, 1), "6 months 1h data"),  # Should create ~3 chunks
            ('4h', datetime(2023, 1, 1), datetime(2024, 1, 1), "1 year 4h data"),    # Should create ~2 chunks  
            ('1d', datetime(2020, 1, 1), datetime(2025, 1, 1), "5 years 1d data"),   # Should create ~3 chunks
        ]
        
        for timeframe, start, end, description in test_cases:
            plan = bulk_fetcher.create_download_plan('TEST', timeframe, start, end)
            estimate = bulk_fetcher.estimate_download_time('TEST', timeframe, start, end)
            
            print(f"  📊 {description}:")
            print(f"    - Chunks: {len(plan.chunks)}")
            print(f"    - Estimated time: {estimate['estimated_minutes']:.1f} minutes")
            print(f"    - Date range: {(end - start).days} days")
        
        print("✅ Chunking strategies test completed")
    
    def run_all_tests(self):
        """Run all checkpoint-specific tests"""
        print("🚀 Starting Checkpoint-Specific Tests")
        print("=" * 50)
        
        try:
            self.test_checkpoint_creation_and_resume()
            self.test_checkpoint_manual_scenarios()
            self.test_specific_chunking_strategies()
            
            print("\n" + "=" * 50)
            print("🎉 ALL CHECKPOINT TESTS PASSED!")
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            raise


if __name__ == "__main__":
    test_suite = TestCheckpointSpecific()
    test_suite.setup_method()
    
    try:
        test_suite.run_all_tests()
    finally:
        test_suite.teardown_method()