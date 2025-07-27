import pytest
import tempfile
import shutil
import pandas as pd
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.providers.alpha_vantage.checkpoint_manager import CheckpointManager
from data.providers.alpha_vantage.bulk_fetcher import BulkDataFetcher, DownloadPlan, DownloadChunk
from data.providers.alpha_vantage.client import AlphaVantageClient


class TestCheckpointSystem:
    """Test the checkpoint system for resumable downloads"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.checkpoint_manager = CheckpointManager(self.temp_dir)
        
        # Create mock client
        self.mock_client = Mock(spec=AlphaVantageClient)
        self.bulk_fetcher = BulkDataFetcher(self.mock_client, self.temp_dir)
    
    def teardown_method(self):
        """Cleanup test environment"""
        shutil.rmtree(self.temp_dir)
    
    def test_save_and_load_checkpoint(self):
        """Test basic checkpoint save/load functionality"""
        # Create a test download plan
        chunks = [
            DownloadChunk(
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 2, 1),
                timeframe='1d',
                ticker='AAPL',
                status='completed'
            ),
            DownloadChunk(
                start_date=datetime(2023, 2, 1),
                end_date=datetime(2023, 3, 1),
                timeframe='1d',
                ticker='AAPL',
                status='pending'
            )
        ]
        
        plan = DownloadPlan(
            ticker='AAPL',
            timeframe='1d',
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 3, 1),
            chunks=chunks,
            total_chunks=2,
            completed_chunks=1,
            failed_chunks=0
        )
        
        plan_id = "test_plan_123"
        
        # Save checkpoint
        result = self.checkpoint_manager.save_checkpoint(plan, plan_id)
        assert result is True
        
        # Load checkpoint
        loaded_plan = self.checkpoint_manager.load_checkpoint(plan_id)
        assert loaded_plan is not None
        assert loaded_plan.ticker == 'AAPL'
        assert loaded_plan.timeframe == '1d'
        assert loaded_plan.total_chunks == 2
        assert loaded_plan.completed_chunks == 1
        assert len(loaded_plan.chunks) == 2
        assert loaded_plan.chunks[0].status == 'completed'
        assert loaded_plan.chunks[1].status == 'pending'
    
    def test_checkpoint_validation(self):
        """Test checkpoint validation functionality"""
        # Create and save a checkpoint
        chunks = [
            DownloadChunk(
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 2, 1),
                timeframe='1d',
                ticker='AAPL',
                status='completed'
            ),
            DownloadChunk(
                start_date=datetime(2023, 2, 1),
                end_date=datetime(2023, 3, 1),
                timeframe='1d',
                ticker='AAPL',
                status='failed'
            )
        ]
        
        plan = DownloadPlan(
            ticker='AAPL',
            timeframe='1d',
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 3, 1),
            chunks=chunks,
            total_chunks=2,
            completed_chunks=1,
            failed_chunks=1
        )
        
        plan_id = "validation_test"
        self.checkpoint_manager.save_checkpoint(plan, plan_id)
        
        # Validate checkpoint
        validation = self.checkpoint_manager.validate_checkpoint(plan_id)
        
        assert validation['total_chunks'] == 2
        assert validation['completed_chunks'] == 1
        assert validation['failed_chunks'] == 1
        assert validation['can_resume'] is True
        assert len(validation['issues']) > 0  # Should have issues due to failed chunks
        assert "failed chunks" in validation['issues'][0]
    
    def test_list_resumable_downloads(self):
        """Test listing resumable downloads"""
        # Create multiple checkpoints with different completion states
        tickers = ['AAPL', 'MSFT', 'GOOGL']
        for i, ticker in enumerate(tickers):
            # For AAPL and MSFT, create completed downloads (not resumable)
            # For GOOGL, create incomplete download (resumable)
            if i < 2:  # AAPL, MSFT - completed
                chunks = [
                    DownloadChunk(
                        start_date=datetime(2023, 1, 1),
                        end_date=datetime(2023, 2, 1),
                        timeframe='1d',
                        ticker=ticker,
                        status='completed'
                    )
                ]
                completed_chunks = 1
            else:  # GOOGL - incomplete
                chunks = [
                    DownloadChunk(
                        start_date=datetime(2023, 1, 1),
                        end_date=datetime(2023, 2, 1),
                        timeframe='1d',
                        ticker=ticker,
                        status='pending'
                    )
                ]
                completed_chunks = 0
            
            plan = DownloadPlan(
                ticker=ticker,
                timeframe='1d',
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 2, 1),
                chunks=chunks,
                total_chunks=1,
                completed_chunks=completed_chunks,
                failed_chunks=0
            )
            
            self.checkpoint_manager.save_checkpoint(plan, f"test_{ticker}_{i}")
        
        # List all resumable downloads
        resumable = self.bulk_fetcher.list_resumable_downloads()
        
        # Debug: Print what we got
        print(f"Resumable downloads: {len(resumable)}")
        for r in resumable:
            print(f"  {r['ticker']}: {r['progress']} - can_resume={r['can_resume']}")
        
        # Only GOOGL should be resumable (not completed)
        assert len(resumable) == 1, f"Expected 1 resumable download, got {len(resumable)}: {[r['ticker'] for r in resumable]}"
        assert resumable[0]['ticker'] == 'GOOGL'
        
        # Test filtering by ticker
        googl_resumable = self.bulk_fetcher.list_resumable_downloads(ticker='GOOGL')
        assert len(googl_resumable) == 1
        
        # Test filtering by non-existent ticker
        none_resumable = self.bulk_fetcher.list_resumable_downloads(ticker='TSLA')
        assert len(none_resumable) == 0
    
    def test_checkpoint_completion(self):
        """Test checkpoint completion workflow"""
        # Create a completed download plan
        chunks = [
            DownloadChunk(
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 2, 1),
                timeframe='1d',
                ticker='AAPL',
                status='completed'
            )
        ]
        
        plan = DownloadPlan(
            ticker='AAPL',
            timeframe='1d',
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 2, 1),
            chunks=chunks,
            total_chunks=1,
            completed_chunks=1,
            failed_chunks=0
        )
        
        plan_id = "completion_test"
        self.checkpoint_manager.save_checkpoint(plan, plan_id)
        
        # Verify checkpoint exists in active directory
        active_checkpoints = self.checkpoint_manager.list_active_checkpoints()
        assert len(active_checkpoints) == 1
        
        # Complete the checkpoint
        result = self.checkpoint_manager.complete_checkpoint(plan_id)
        assert result is True
        
        # Verify checkpoint moved to completed directory
        active_checkpoints = self.checkpoint_manager.list_active_checkpoints()
        assert len(active_checkpoints) == 0
        
        # Should no longer be loadable from active
        loaded_plan = self.checkpoint_manager.load_checkpoint(plan_id)
        assert loaded_plan is None
    
    def test_checkpoint_statistics(self):
        """Test checkpoint statistics"""
        # Initially no checkpoints
        stats = self.checkpoint_manager.get_checkpoint_stats()
        assert stats['active_checkpoints'] == 0
        assert stats['completed_checkpoints'] == 0
        
        # Add some checkpoints
        for i in range(3):
            chunks = [DownloadChunk(
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 2, 1),
                timeframe='1d',
                ticker=f'TEST{i}',
                status='pending'
            )]
            
            plan = DownloadPlan(
                ticker=f'TEST{i}',
                timeframe='1d',
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 2, 1),
                chunks=chunks,
                total_chunks=1,
                completed_chunks=0,
                failed_chunks=0
            )
            
            self.checkpoint_manager.save_checkpoint(plan, f"test_{i}")
        
        # Complete one checkpoint
        self.checkpoint_manager.complete_checkpoint("test_0")
        
        # Check statistics
        stats = self.checkpoint_manager.get_checkpoint_stats()
        assert stats['active_checkpoints'] == 2
        assert stats['completed_checkpoints'] == 1
        assert stats['total_disk_usage_bytes'] > 0
    
    @patch('data.providers.alpha_vantage.bulk_fetcher.logger')
    def test_resume_download_integration(self, mock_logger):
        """Test the complete resume download workflow"""
        # Mock the client to return test data
        test_data = pd.DataFrame({
            'Open': [100.0, 101.0],
            'High': [102.0, 103.0], 
            'Low': [99.0, 100.0],
            'Close': [101.0, 102.0],
            'Volume': [1000000, 1100000]
        }, index=pd.DatetimeIndex(['2023-01-01', '2023-01-02']))
        
        self.mock_client.fetch_data.return_value = test_data
        
        # Create a partially completed plan
        chunks = [
            DownloadChunk(
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 2, 1),
                timeframe='1d',
                ticker='AAPL',
                status='completed'  # This chunk is already done
            ),
            DownloadChunk(
                start_date=datetime(2023, 2, 1),
                end_date=datetime(2023, 3, 1),
                timeframe='1d',
                ticker='AAPL',
                status='pending'   # This chunk needs to be downloaded
            )
        ]
        
        plan = DownloadPlan(
            ticker='AAPL',
            timeframe='1d',
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 3, 1),
            chunks=chunks,
            total_chunks=2,
            completed_chunks=1,
            failed_chunks=0
        )
        
        plan_id = "resume_test"
        self.checkpoint_manager.save_checkpoint(plan, plan_id)
        
        # Test resume functionality
        result_df = self.bulk_fetcher.resume_download(plan_id)
        
        # Verify the download was resumed successfully
        assert not result_df.empty
        assert 'provider_source' in result_df.attrs
        assert result_df.attrs['ticker'] == 'AAPL'
        
        # Verify that only the pending chunk was processed
        # (completed chunk should have been skipped)
        self.mock_client.fetch_data.assert_called_once()
    
    def test_nonexistent_checkpoint_resume(self):
        """Test resuming a non-existent checkpoint"""
        with pytest.raises(ValueError, match="Cannot resume: checkpoint .* not found"):
            self.bulk_fetcher.resume_download("nonexistent_plan_id")


if __name__ == "__main__":
    # Run a basic test
    test = TestCheckpointSystem()
    test.setup_method()
    
    try:
        test.test_save_and_load_checkpoint()
        print("✅ Checkpoint save/load test passed")
        
        test.test_checkpoint_validation()
        print("✅ Checkpoint validation test passed")
        
        test.test_list_resumable_downloads()
        print("✅ Resumable downloads list test passed")
        
        test.test_checkpoint_completion()
        print("✅ Checkpoint completion test passed")
        
        test.test_checkpoint_statistics()
        print("✅ Checkpoint statistics test passed")
        
        print("\n🎉 All checkpoint system tests passed!")
        
    finally:
        test.teardown_method()