#!/usr/bin/env python3
"""
Test script to demonstrate cache performance optimization.
Tests both old vs new approach for data loading.
"""

import time
from datetime import datetime, timedelta
from data.data_manager import DataManager

def test_cache_performance():
    """Test cache performance for multiple asset loading"""
    
    # Test parameters
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA', 'AMZN', 'META', 'BRK.B', 'JPM', 'JNJ']
    start_date = datetime(2025, 7, 20)
    end_date = datetime(2025, 7, 25)
    
    print("🧪 CACHE PERFORMANCE TEST")
    print("=" * 50)
    print(f"Testing {len(tickers)} tickers: {', '.join(tickers)}")
    print(f"Date range: {start_date.date()} to {end_date.date()}")
    print()
    
    # Initialize data manager
    data_manager = DataManager(provider_name='alpha_vantage')
    
    # Test 1: Individual loading (simulating old approach)
    print("🔧 Test 1: Individual ticker loading")
    start_time = time.time()
    
    individual_results = {}
    for ticker in tickers:
        data = data_manager.download_data(ticker, start_date, end_date, use_cache=True, interval='1d')
        if data is not None and not data.empty:
            individual_results[ticker] = len(data)
    
    individual_time = time.time() - start_time
    print(f"   ⏱️  Time: {individual_time:.3f} seconds")
    print(f"   ✅ Loaded: {len(individual_results)}/{len(tickers)} tickers")
    print()
    
    # Test 2: Optimized bulk loading
    print("🚀 Test 2: Optimized bulk loading")
    start_time = time.time()
    
    bulk_data_feeds = data_manager.get_multiple_data(tickers, start_date, end_date, use_cache=True)
    
    bulk_time = time.time() - start_time
    print(f"   ⏱️  Time: {bulk_time:.3f} seconds")
    print(f"   ✅ Loaded: {len(bulk_data_feeds)}/{len(tickers)} tickers")
    print()
    
    # Performance comparison
    if individual_time > 0:
        improvement = ((individual_time - bulk_time) / individual_time) * 100
        print("📊 PERFORMANCE COMPARISON")
        print("=" * 30)
        print(f"Individual loading: {individual_time:.3f}s")
        print(f"Optimized loading:  {bulk_time:.3f}s")
        print(f"Improvement:        {improvement:.1f}% faster")
        
        if improvement > 0:
            print(f"🎉 Optimization successful!")
        else:
            print(f"⚠️  No improvement detected")
    
    return individual_time, bulk_time, len(individual_results), len(bulk_data_feeds)

if __name__ == "__main__":
    try:
        test_cache_performance()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()