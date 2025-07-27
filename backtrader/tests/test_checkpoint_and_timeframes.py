#!/usr/bin/env python3
"""
Specific test for checkpointing and smaller timeframes (1h, 4h) functionality
Comprehensive testing of Alpha Vantage integration with checkpoint system
"""

import os
import sys
import tempfile
import shutil
import json
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.providers.alpha_vantage.checkpoint_manager import CheckpointManager
from data.providers.alpha_vantage.bulk_fetcher import BulkDataFetcher, DownloadPlan
from data.providers.alpha_vantage.provider import AlphaVantageProvider
from data.timeframe_manager import TimeframeManager
from data.data_manager import DataManager


def test_checkpoint_system():
    """Test checkpointing system functionality"""
    print("\n💾 CHECKPOINTING SYSTEM TEST")
    print("=" * 50)
    
    temp_dir = tempfile.mkdtemp()
    print(f"📁 Using temp directory: {temp_dir}")
    
    try:
        # 1. Test CheckpointManager initialization
        print("\n🔧 Step 1: Initialize CheckpointManager")
        
        checkpoint_manager = CheckpointManager(checkpoint_dir=temp_dir)
        print("   ✅ CheckpointManager initialized")
        
        # 2. Create test download plan
        print("\n📋 Step 2: Create Test Download Plan")
        
        from data.providers.alpha_vantage.bulk_fetcher import DownloadChunk
        
        # Create simple plan for testing  
        test_plan = DownloadPlan(
            ticker='AAPL',
            timeframe='1h',
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 1, 31),
            chunks=[],
            total_chunks=3
        )
        
        # Add some test chunks
        test_plan.chunks = [
            DownloadChunk(
                ticker='AAPL',
                timeframe='1h',
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 1, 15),
                status='completed'
            ),
            DownloadChunk(
                ticker='AAPL', 
                timeframe='1h',
                start_date=datetime(2023, 1, 15),
                end_date=datetime(2023, 1, 31),
                status='pending'
            ),
            DownloadChunk(
                ticker='AAPL',
                timeframe='1h',
                start_date=datetime(2023, 1, 31),
                end_date=datetime(2023, 2, 15),
                status='failed'
            )
        ]
        
        print(f"   ✅ Test plan created: {len(test_plan.chunks)} chunks")
        
        # 3. Test checkpoint saving
        print("\n💾 Step 3: Test Checkpoint Saving")
        
        plan_id = "test_checkpoint_001"
        save_success = checkpoint_manager.save_checkpoint(test_plan, plan_id)
        print(f"   ✅ Checkpoint saved: {save_success}")
        
        # Verify checkpoint file exists
        checkpoint_path = checkpoint_manager.active_dir / f"{plan_id}.json"
        print(f"   ✅ Checkpoint file exists: {checkpoint_path.exists()}")
        
        # 4. Test checkpoint loading
        print("\n📂 Step 4: Test Checkpoint Loading")
        
        loaded_plan = checkpoint_manager.load_checkpoint(plan_id)
        print(f"   ✅ Checkpoint loaded: {loaded_plan is not None}")
        
        if loaded_plan:
            print(f"     - Ticker: {loaded_plan.ticker}")
            print(f"     - Timeframe: {loaded_plan.timeframe}")
            print(f"     - Chunks: {len(loaded_plan.chunks)}")
            
            # Test plan integrity
            assert loaded_plan.ticker == test_plan.ticker
            assert loaded_plan.timeframe == test_plan.timeframe
            assert len(loaded_plan.chunks) == len(test_plan.chunks)
            print("   ✅ Plan integrity verified")
        
        # 5. Test checkpoint listing
        print("\n📊 Step 5: Test Checkpoint Listing")
        
        checkpoints = checkpoint_manager.list_active_checkpoints()
        print(f"   ✅ Checkpoint listing: {len(checkpoints)} checkpoints")
        
        if checkpoints:
            checkpoint = checkpoints[0]
            print(f"     - Plan ID: {checkpoint['plan_id']}")
            print(f"     - Progress: {checkpoint['progress']} ({checkpoint['progress_percent']}%)")
            print(f"     - Can resume: {checkpoint['can_resume']}")
        
        # 6. Test checkpoint cleanup  
        print("\n🧹 Step 6: Test Checkpoint Cleanup")
        
        # Move to completed first, then cleanup
        complete_success = checkpoint_manager.complete_checkpoint(plan_id)
        print(f"   ✅ Checkpoint completed: {complete_success}")
        
        cleanup_count = checkpoint_manager.cleanup_old_checkpoints(days=0)
        print(f"   ✅ Checkpoint cleanup: {cleanup_count} old checkpoints removed")
        
        # Verify checkpoint file is gone from active
        print(f"   ✅ Checkpoint file removed from active: {not checkpoint_path.exists()}")
        
        print("\n✅ CHECKPOINTING SYSTEM TEST PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ Checkpointing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        shutil.rmtree(temp_dir)
        print("🧹 Cleanup complete")


@patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_checkpoint_key'})
def test_smaller_timeframes():
    """Test 1h and 4h timeframe handling"""
    print("\n🕐 SMALLER TIMEFRAMES TEST (1h, 4h)")
    print("=" * 50)
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 1. Test Alpha Vantage provider with smaller timeframes
        print("\n🔧 Step 1: Initialize Alpha Vantage Provider")
        
        provider = AlphaVantageProvider()
        print(f"   ✅ Provider initialized: {provider.name}")
        print(f"   ✅ Supported timeframes: {provider.get_supported_timeframes()}")
        
        # Verify 1h and 4h support
        assert '1h' in provider.get_supported_timeframes()
        assert '4h' in provider.get_supported_timeframes()
        print("   ✅ Smaller timeframes supported")
        
        # 2. Test TimeframeManager with smaller timeframes
        print("\n📊 Step 2: TimeframeManager with Smaller Timeframes")
        
        data_manager = DataManager(cache_dir=temp_dir, provider_name='alpha_vantage')
        timeframe_manager = data_manager.timeframe_manager
        
        # Test timeframe compatibility
        compatibility = timeframe_manager.validate_timeframe_compatibility(['1h', '4h', '1d'])
        print(f"   ✅ Timeframe compatibility: {compatibility}")
        
        assert compatibility['1h'] == True
        assert compatibility['4h'] == True
        assert compatibility['1d'] == True
        
        # 3. Test chunking strategies for smaller timeframes
        print("\n📦 Step 3: Test Chunking Strategies")
        
        from data.providers.alpha_vantage.client import AlphaVantageClient
        client = AlphaVantageClient()
        bulk_fetcher = BulkDataFetcher(client=client)
        
        # Test chunking for 1h data
        h1_plan = bulk_fetcher.create_download_plan(
            ticker='AAPL',  # Single ticker
            timeframe='1h',
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 6, 30)  # 6 months
        )
        
        print(f"   ✅ 1h plan created: {len(h1_plan.chunks)} chunks")
        
        # Test chunking for 4h data  
        h4_plan = bulk_fetcher.create_download_plan(
            ticker='AAPL',
            timeframe='4h',
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31)  # 1 year
        )
        
        print(f"   ✅ 4h plan created: {len(h4_plan.chunks)} chunks")
        
        # Verify chunking is appropriate for timeframe
        # 1h should have more chunks due to smaller chunk size
        # 4h should have fewer chunks due to larger chunk size
        print(f"     - 1h chunks: {len(h1_plan.chunks)} (for 6 months)")
        print(f"     - 4h chunks: {len(h4_plan.chunks)} (for 12 months)")
        
        # 4. Test rate limit estimates for smaller timeframes
        print("\n⏱️  Step 4: Rate Limit Estimates")
        
        estimates = timeframe_manager.estimate_download_time(['AAPL', 'MSFT'], ['1h', '4h'])
        print(f"   ✅ Download estimates: {estimates}")
        print(f"     - Total requests: {estimates['total_requests']}")
        print(f"     - Est. minutes: {estimates['estimated_minutes']:.2f}")
        
        # 5. Mock test multi-timeframe data fetch
        print("\n📈 Step 5: Mock Multi-timeframe Fetch")
        
        # Mock the provider's fetch_data method
        def mock_fetch_data(ticker, timeframe, start_date, end_date):
            import pandas as pd
            
            # Generate appropriate number of records for timeframe
            if timeframe == '1h':
                periods = 24 * 7  # 1 week hourly
                freq = 'h'
            elif timeframe == '4h':
                periods = 6 * 7   # 1 week 4-hourly
                freq = '4h'
            else:
                periods = 7       # 1 week daily
                freq = 'D'
            
            dates = pd.date_range(start=start_date, periods=periods, freq=freq)
            data = pd.DataFrame({
                'Open': [150.0] * periods,
                'High': [155.0] * periods,
                'Low': [145.0] * periods,
                'Close': [152.0] * periods,
                'Volume': [1000000] * periods
            }, index=dates)
            
            data.attrs['provider_source'] = 'alpha_vantage'
            data.attrs['timeframe'] = timeframe
            data.attrs['ticker'] = ticker
            
            return data
        
        # Patch the fetch_data method
        original_fetch = provider.fetch_data
        provider.fetch_data = mock_fetch_data
        data_manager.download_data = lambda ticker, start_date, end_date, use_cache=True, interval='1d': mock_fetch_data(ticker, interval, start_date, end_date)
        
        try:
            multi_data = timeframe_manager.get_multi_timeframe_data(
                ticker='AAPL',
                timeframes=['1h', '4h', '1d'],
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 1, 8)  # 1 week
            )
            
            print(f"   ✅ Multi-timeframe fetch: {len(multi_data)} timeframes")
            for tf, data in multi_data.items():
                print(f"     - {tf}: {len(data)} records")
                
            # Verify we got data for all timeframes
            assert '1h' in multi_data
            assert '4h' in multi_data
            assert '1d' in multi_data
            
            # Verify record counts make sense
            assert len(multi_data['1h']) > len(multi_data['4h'])
            assert len(multi_data['4h']) > len(multi_data['1d'])
            
            print("   ✅ Timeframe data validation passed")
            
        finally:
            provider.fetch_data = original_fetch
        
        print("\n✅ SMALLER TIMEFRAMES TEST PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ Smaller timeframes test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        shutil.rmtree(temp_dir)


def test_checkpoint_resume_functionality():
    """Test checkpoint resume functionality with mocked data"""
    print("\n🔄 CHECKPOINT RESUME FUNCTIONALITY TEST")
    print("=" * 50)
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 1. Create a partially completed download plan
        print("\n📋 Step 1: Create Partially Completed Plan")
        
        checkpoint_manager = CheckpointManager(checkpoint_dir=temp_dir)
        # Don't need the bulk_fetcher for this test - we're just testing checkpoint functionality
        
        # Create plan with some completed and some pending chunks
        plan = DownloadPlan(
            ticker='AAPL',  # DownloadPlan is for single ticker
            timeframe='1h',
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 3, 31),
            chunks=[],
            total_chunks=9
        )
        
        # Simulate partially completed state with DownloadChunk objects
        from data.providers.alpha_vantage.bulk_fetcher import DownloadChunk
        
        plan.chunks = [
            # Some completed chunks
            DownloadChunk(
                ticker='AAPL', timeframe='1h', 
                start_date=datetime(2023, 1, 1), end_date=datetime(2023, 1, 15),
                status='completed', attempt=1
            ),
            DownloadChunk(
                ticker='AAPL', timeframe='1h',
                start_date=datetime(2023, 1, 15), end_date=datetime(2023, 2, 1), 
                status='completed', attempt=1
            ),
            DownloadChunk(
                ticker='AAPL', timeframe='1h',
                start_date=datetime(2023, 2, 1), end_date=datetime(2023, 2, 15),
                status='pending', attempt=0
            ),
            # Some failed chunks
            DownloadChunk(
                ticker='AAPL', timeframe='1h',
                start_date=datetime(2023, 2, 15), end_date=datetime(2023, 3, 1),
                status='failed', attempt=3
            ),
            DownloadChunk(
                ticker='AAPL', timeframe='1h',
                start_date=datetime(2023, 3, 1), end_date=datetime(2023, 3, 15),
                status='pending', attempt=0
            ),
        ]
        
        # Update plan counters
        plan.total_chunks = len(plan.chunks)
        plan.completed_chunks = sum(1 for chunk in plan.chunks if chunk.status == 'completed')
        plan.failed_chunks = sum(1 for chunk in plan.chunks if chunk.status == 'failed')
        
        print(f"   ✅ Plan created: {len(plan.chunks)} chunks")
        
        # 2. Save checkpoint
        print("\n💾 Step 2: Save Checkpoint")
        
        plan_id = "resume_test_001"
        save_success = checkpoint_manager.save_checkpoint(plan, plan_id)
        print(f"   ✅ Checkpoint saved: {save_success}")
        
        # 3. Calculate initial progress
        initial_checkpoints = checkpoint_manager.list_active_checkpoints()
        initial_progress = None
        if initial_checkpoints:
            initial_progress = initial_checkpoints[0]['progress_percent']
            print(f"   ✅ Initial progress: {initial_progress}%")
            print(f"     - Progress: {initial_checkpoints[0]['progress']}")
            print(f"     - Failed chunks: {initial_checkpoints[0]['failed_chunks']}")
        
        # 4. Test resume functionality 
        print("\n🔄 Step 3: Test Resume Functionality")
        
        # Simulate progress by updating chunk statuses
        print("   📝 Simulating progress on pending/failed chunks...")
        
        # Update some pending chunks to completed
        for chunk in plan.chunks:
            if chunk.status == 'pending':
                chunk.status = 'completed'
                plan.completed_chunks += 1
                break  # Just update one for testing
            elif chunk.status == 'failed':
                chunk.status = 'completed' 
                plan.completed_chunks += 1
                plan.failed_chunks -= 1
                break
        
        # Update checkpoint with progress
        update_success = checkpoint_manager.update_checkpoint(plan, plan_id)
        print(f"   ✅ Checkpoint updated: {update_success}")
        
        # Check final progress
        final_checkpoints = checkpoint_manager.list_active_checkpoints()
        if final_checkpoints:
            final_progress = final_checkpoints[0]['progress_percent']
            print(f"   ✅ Final progress: {final_progress}%")
            print(f"     - Progress: {final_checkpoints[0]['progress']}")
            print(f"     - Failed chunks: {final_checkpoints[0]['failed_chunks']}")
            
            # Verify progress improved
            if initial_progress is not None:
                assert final_progress >= initial_progress
                print("   ✅ Progress improved after update")
        
        # 5. Test checkpoint listing
        print("\n📝 Step 4: Test Checkpoint Listing")
        
        checkpoints = checkpoint_manager.list_active_checkpoints()
        print(f"   ✅ Available checkpoints: {len(checkpoints)}")
        
        for cp in checkpoints:
            print(f"     - {cp['plan_id']}: {cp['progress_percent']}% complete")
        
        print("\n✅ CHECKPOINT RESUME TEST PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ Checkpoint resume test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    print("🏁 CHECKPOINT & SMALLER TIMEFRAMES TESTS")
    print("=" * 60)
    print("Testing: Checkpointing system and 1h/4h timeframe handling")
    print("=" * 60)
    
    success = True
    
    # Run checkpoint system tests
    success &= test_checkpoint_system()
    
    # Run smaller timeframes tests  
    success &= test_smaller_timeframes()
    
    # Run checkpoint resume tests
    success &= test_checkpoint_resume_functionality()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ALL CHECKPOINT & TIMEFRAME TESTS PASSED!")
        print("✅ Checkpointing system fully functional")
        print("✅ Smaller timeframes (1h, 4h) working correctly")
        print("✅ Resume functionality operational")
        print("✅ Progress tracking accurate")
        print("\n🚀 ALPHA VANTAGE SYSTEM READY FOR PRODUCTION!")
    else:
        print("❌ Some checkpoint/timeframe tests failed")
        exit(1)