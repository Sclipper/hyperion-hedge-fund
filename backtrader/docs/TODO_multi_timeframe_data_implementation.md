# Multi-Timeframe Data Implementation Design Document

## Executive Summary

This document outlines the implementation plan for adding true multi-timeframe data support to the backtrader hedge fund system. Currently, the system assumes multi-timeframe data availability but only provides daily data via Yahoo Finance. This creates a significant gap between intended functionality and actual capabilities.

## Current State Analysis

### Data Infrastructure Assessment

**Current Implementation:**
- Uses `yfinance` library exclusively for data downloads
- `DataManager.download_data()` hardcoded to `interval="1d"` (daily only)
- Cache system designed around daily data only
- No actual multi-timeframe data retrieval

**Components Assuming Multi-Timeframe Data:**
1. **TechnicalAnalyzer** (`position/technical_analyzer.py`):
   - Expects `timeframe_data: Dict[str, pd.DataFrame]` with keys like `'1h'`, `'4h'`, `'1d'`
   - Has timeframe weights: `{'1d': 0.5, '4h': 0.3, '1h': 0.2}`
   - Method `analyze_multi_timeframe()` designed for multiple timeframes

2. **PositionManager** (`position/position_manager.py`):
   - Method `_get_timeframe_data()` currently returns daily data for all timeframes
   - Contains warnings: "CRITICAL: Multi-timeframe analysis requires real hourly data"
   - Prints mock data warnings for 1h and 4h data

3. **RegimeStrategy** (`strategies/regime_strategy.py`):
   - Parameter `timeframes=['1d', '4h', '1h']` suggests multi-timeframe support
   - TechnicalAnalyzer initialized with timeframe weights

4. **EnhancedAssetScanner** (`core/enhanced_asset_scanner.py`):
   - TODO comment: "Add multi-timeframe support when intraday data sources available"
   - Currently defaults to daily only: `'1d': 1.0`

5. **RegimeDetector** (`data/regime_detector.py`):
   - Method `get_price_data()` accepts timeframe parameter but ignores it
   - Warning message: "Only daily data available. Requested timeframe {timeframe} not supported."

### Yahoo Finance Limitations

**yfinance Library Constraints:**
- **Intraday Data Limitation**: Only last 60 days for intervals < 1d
- **1-Hour Data Issues**: 
  - Timestamps at :30 minute mark instead of :00
  - Version-specific timestamp bugs
  - Only covers last 60 days
- **4-Hour Data**: Not directly supported (closest is 90m intervals)
- **Historical Intraday**: Cannot retrieve 1h or 4h data for periods before last 60 days

## Alternative Data Sources Research

### Free Options Supporting Multi-Timeframe Historical Data

1. **Alpha Vantage** ⭐ **RECOMMENDED**
   - **Pros**: 2+ years of intraday data, reliable 1h/4h support, JSON API
   - **Cons**: 25 API calls/day free tier, rate limiting
   - **Timeframes**: 1min, 5min, 15min, 30min, 60min, daily, weekly, monthly

2. **EODHD (End of Day Historical Data)**
   - **Pros**: 150,000+ tickers, historical data from inception, CSV/JSON
   - **Cons**: Primarily end-of-day focused, limited free intraday
   - **Free Tier**: 100,000 requests/day

3. **Finnhub**
   - **Pros**: Real-time and historical data, good API documentation
   - **Cons**: Limited free tier for historical intraday data
   - **Timeframes**: 1min, 5min, 15min, 30min, 60min, daily

4. **IEX Cloud**
   - **Pros**: Reliable infrastructure, good free tier
   - **Cons**: US markets only, limited historical intraday in free tier
   - **Timeframes**: 1min, 5min, 15min, 30min, 60min, daily

5. **Twelve Data**
   - **Pros**: 800 API calls/day free, multi-market coverage
   - **Cons**: Rate limiting, registration required
   - **Timeframes**: 1min, 5min, 15min, 30min, 45min, 1h, 2h, 4h, 1day

### Hybrid Approach (Recommended)

**Primary Strategy**: Use multiple data sources with fallback hierarchy:
1. **Alpha Vantage**: Primary source for 1h/4h historical data (up to 2021)
2. **yfinance**: Fallback for daily data and recent periods
3. **EODHD**: Backup for daily historical data

## Implementation Plan

### Phase 1: Enhanced Data Manager (2-3 days)

**1.1 Create Multi-Source Data Manager**
```python
# New file: backtrader/data/multi_source_data_manager.py
class MultiSourceDataManager:
    def __init__(self, primary_source='alpha_vantage', cache_dir='data/cache'):
        self.sources = {
            'alpha_vantage': AlphaVantageConnector(),
            'yfinance': YFinanceConnector(), 
            'eodhd': EODHDConnector()
        }
        self.primary_source = primary_source
        self.fallback_order = ['alpha_vantage', 'yfinance', 'eodhd']
    
    def get_multi_timeframe_data(self, ticker: str, start_date: datetime, 
                                end_date: datetime, timeframes: List[str]) -> Dict[str, pd.DataFrame]:
        """Get data for multiple timeframes from appropriate sources"""
        pass
```

**1.2 Individual Data Source Connectors**
```python
# backtrader/data/connectors/alpha_vantage_connector.py
class AlphaVantageConnector:
    def get_intraday_data(self, ticker: str, interval: str, 
                         start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Fetch 1h/4h data from Alpha Vantage with proper date filtering"""
        pass

# backtrader/data/connectors/yfinance_connector.py  
class YFinanceConnector:
    def get_data(self, ticker: str, interval: str, 
                start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Enhanced yfinance wrapper with better error handling"""
        pass
```

**1.3 Enhanced Caching System**
```python
# Enhance existing cache to support multiple timeframes
def _get_cache_filename(self, ticker: str, start_date: datetime, 
                       end_date: datetime, timeframe: str) -> Path:
    start_str = start_date.strftime('%Y%m%d')
    end_str = end_date.strftime('%Y%m%d')
    return self.cache_dir / f"{ticker}_{timeframe}_{start_str}_{end_str}.pkl"
```

### Phase 2: Data Manager Integration (1-2 days)

**2.1 Update DataManager Interface**
```python
# Modify backtrader/data/data_manager.py
class DataManager:
    def __init__(self, enable_multi_timeframe=True, cache_dir="data/cache"):
        self.multi_source_manager = MultiSourceDataManager() if enable_multi_timeframe else None
        
    def get_timeframe_data(self, ticker: str, start_date: datetime, 
                          end_date: datetime, timeframe: str) -> pd.DataFrame:
        """New method to get specific timeframe data"""
        if self.multi_source_manager and timeframe != '1d':
            return self.multi_source_manager.get_data(ticker, start_date, end_date, timeframe)
        else:
            return self.download_data(ticker, start_date, end_date)  # Daily fallback
```

**2.2 Update Position Manager**
```python
# Modify backtrader/position/position_manager.py
def _get_timeframe_data(self, asset: str, current_date: datetime, 
                       timeframe: str, data_manager) -> Optional[pd.DataFrame]:
    """Enhanced to use real timeframe data"""
    if hasattr(data_manager, 'get_timeframe_data'):
        return data_manager.get_timeframe_data(asset, 
                                              current_date - timedelta(days=365), 
                                              current_date, timeframe)
    # Remove mock data warnings and resampling
```

### Phase 3: Configuration & Environment Setup (1 day)

**3.1 Environment Variables**
```bash
# Add to .env file
ALPHA_VANTAGE_API_KEY=your_key_here
EODHD_API_KEY=your_key_here
ENABLE_MULTI_TIMEFRAME=true
MULTI_TIMEFRAME_PRIMARY_SOURCE=alpha_vantage
```

**3.2 Configuration Parameters**
```python
# Add to backtrader/config/parameter_registry.py
'data_source_config': {
    'type': 'dict',
    'default': {
        'primary_source': 'alpha_vantage',
        'fallback_sources': ['yfinance', 'eodhd'],
        'api_rate_limits': {
            'alpha_vantage': {'calls_per_day': 25, 'calls_per_minute': 5},
            'eodhd': {'calls_per_day': 100000}
        }
    }
}
```

### Phase 4: Strategy & Component Updates (2-3 days)

**4.1 Update RegimeDetector**
```python
# Modify backtrader/data/regime_detector.py
def get_price_data(self, ticker: str, start_date: datetime, 
                  end_date: datetime, timeframe: str = '1d'):
    """Remove timeframe limitation and use multi-source data"""
    if hasattr(self.data_manager, 'get_timeframe_data'):
        return self.data_manager.get_timeframe_data(ticker, start_date, end_date, timeframe)
    else:
        return self.data_manager.download_data(ticker, start_date, end_date)
```

**4.2 Update Enhanced Asset Scanner**
```python
# Modify backtrader/core/enhanced_asset_scanner.py
def __init__(self):
    # Remove TODO comment and enable real multi-timeframe weights
    self.timeframe_weights = {
        '1d': 0.5,   # Daily trend
        '4h': 0.3,   # 4-hour momentum  
        '1h': 0.2    # Hourly timing
    }
```

**4.3 Update Main Entry Point**
```python
# Modify backtrader/main.py
def run_regime_backtest(..., enable_multi_timeframe=True, data_sources_config=None):
    # Pass multi-timeframe configuration to DataManager
    data_manager = DataManager(
        enable_multi_timeframe=enable_multi_timeframe,
        sources_config=data_sources_config
    )
```

### Phase 5: Testing Strategy (2-3 days)

**5.1 Unit Tests**
```python
# tests/test_multi_timeframe_data.py
class TestMultiTimeframeData:
    def test_alpha_vantage_connector(self):
        """Test Alpha Vantage 1h/4h data retrieval"""
        pass
        
    def test_data_source_fallback(self):
        """Test fallback from Alpha Vantage to yfinance"""
        pass
        
    def test_cache_with_timeframes(self):
        """Test caching works with multiple timeframes"""
        pass
        
    def test_real_vs_mock_timeframe_analysis(self):
        """Compare analysis results with real vs daily-only data"""
        pass
```

**5.2 Integration Tests**
```python
# tests/test_integration_multi_timeframe.py
class TestMultiTimeframeIntegration:
    def test_end_to_end_with_real_data(self):
        """Test complete backtest with real 1h/4h data"""
        pass
        
    def test_position_manager_with_real_timeframes(self):
        """Test position scoring with actual multi-timeframe data"""
        pass
        
    def test_technical_analyzer_accuracy(self):
        """Compare technical analysis accuracy with real timeframe data"""
        pass
```

**5.3 Performance Tests**
```python
# tests/test_performance_multi_timeframe.py
def test_api_rate_limiting():
    """Ensure API rate limits are respected"""
    pass
    
def test_cache_performance():
    """Test cache hit rates and performance with multiple timeframes"""
    pass
    
def test_memory_usage():
    """Monitor memory usage with multi-timeframe data"""
    pass
```

**5.4 Data Quality Tests**
```python
# tests/test_data_quality.py
def test_timeframe_data_consistency():
    """Ensure 1h/4h data aggregates properly to daily"""
    pass
    
def test_missing_data_handling():
    """Test graceful degradation when intraday data unavailable"""
    pass
    
def test_timestamp_alignment():
    """Verify proper timestamp alignment across timeframes"""
    pass
```

## Implementation Timeline

| Phase | Duration | Dependencies | Deliverables |
|-------|----------|--------------|--------------|
| Phase 1 | 2-3 days | API key setup | Multi-source data manager, connectors |
| Phase 2 | 1-2 days | Phase 1 | Updated DataManager, PositionManager |
| Phase 3 | 1 day | - | Configuration system, environment setup |
| Phase 4 | 2-3 days | Phases 1-3 | Updated strategy components |
| Phase 5 | 2-3 days | Phases 1-4 | Comprehensive testing suite |
| **Total** | **8-12 days** | - | Production-ready multi-timeframe system |

## Risk Assessment & Mitigation

### High Risk Items

1. **API Rate Limiting**
   - **Risk**: Hitting Alpha Vantage 25 calls/day limit
   - **Mitigation**: Implement intelligent caching, request queuing, multiple API keys rotation

2. **Data Quality Issues**
   - **Risk**: Inconsistent data between sources, missing periods
   - **Mitigation**: Data validation pipeline, fallback hierarchy, quality monitoring

3. **Performance Impact**
   - **Risk**: 3x data volume (1h + 4h + daily) affecting memory/speed
   - **Mitigation**: Lazy loading, selective timeframe loading, memory optimization

### Medium Risk Items

1. **API Key Management**
   - **Risk**: API keys exposure, key exhaustion
   - **Mitigation**: Environment variable management, key rotation system

2. **Backward Compatibility**
   - **Risk**: Breaking existing daily-only workflows
   - **Mitigation**: Feature flags, graceful degradation to daily data

## Configuration Management

### Environment Variables Required
```bash
# Primary data source configuration
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
EODHD_API_KEY=your_eodhd_key

# Feature flags
ENABLE_MULTI_TIMEFRAME=true
MULTI_TIMEFRAME_PRIMARY_SOURCE=alpha_vantage

# Performance tuning
MAX_CONCURRENT_API_CALLS=3
CACHE_TTL_HOURS=24
ENABLE_AGGRESSIVE_CACHING=true
```

### CLI Parameters
```bash
# New command line options
python main.py regime --enable-multi-timeframe \
  --timeframes 1h,4h,1d \
  --data-source alpha_vantage \
  --cache-policy aggressive
```

## Success Metrics

### Functional Metrics
- [ ] All 41 files expecting multi-timeframe data receive real data
- [ ] TechnicalAnalyzer produces differentiated scores across timeframes
- [ ] PositionManager eliminates "CRITICAL" warning messages
- [ ] RegimeDetector supports all requested timeframes

### Performance Metrics
- [ ] API calls stay within daily limits (< 25/day Alpha Vantage)
- [ ] Cache hit rate > 80% for repeated requests
- [ ] Memory usage increase < 50% vs daily-only mode
- [ ] Backtest execution time increase < 100%

### Quality Metrics
- [ ] Data consistency validation across timeframes
- [ ] Zero data gaps for available periods
- [ ] Proper timestamp alignment validation
- [ ] Graceful degradation when APIs unavailable

## Conclusion

This implementation plan addresses the fundamental gap between the system's multi-timeframe expectations and current daily-only data reality. The phased approach ensures minimal disruption while delivering production-ready multi-timeframe capabilities.

The recommended Alpha Vantage + fallback approach provides the best balance of data quality, historical coverage, and cost-effectiveness for historical data up to 2021. The comprehensive testing strategy ensures reliability and data quality across all timeframes.

Upon completion, the system will truly support the multi-timeframe technical analysis it was designed for, significantly improving the accuracy of technical indicators and trading decisions.