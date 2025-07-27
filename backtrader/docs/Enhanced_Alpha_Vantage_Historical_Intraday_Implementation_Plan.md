# Enhanced Alpha Vantage Historical Intraday Implementation Plan

## 🎯 **Objective**

Enhance the Alpha Vantage provider to support historical intraday data beyond the 30-day limitation while maintaining all current functionality, abstractions, and performance characteristics.

## 📊 **Current State Analysis**

### **Existing Implementation Issues**
- ✅ **Daily data**: Works perfectly (no limitations)
- ❌ **1h/4h data**: Limited to last 30 days via `TIME_SERIES_INTRADAY` 
- ❌ **Historical backtests**: Fail when requesting intraday data older than 30 days
- ❌ **200-day lookback**: TimeframeManager uses 200-day lookback but only gets 30 days

### **Alpha Vantage Native Support**
- **Intraday intervals**: `1min`, `5min`, `15min`, `30min`, `60min`
- **Daily**: `daily`, `weekly`, `monthly`
- **Historical intraday**: 
  - Month-by-month: `month=YYYY-MM` parameter
  - Extended slices: `TIME_SERIES_INTRADAY_EXTENDED` with `slice` parameter

### **Current Timeframe Requirements**
- **Primary**: `1h`, `4h` 
- **Future scalability**: `12h`, `8h`, `2h`, etc.
- **Resampling strategy**: Fetch lowest available native timeframe and resample up

## 🏗️ **Implementation Strategy**

### **Phase 1: Smart Date-Aware Fetching**

#### **1.1 Enhanced Provider Logic**
```python
def fetch_data(self, ticker: str, timeframe: str, start_date: datetime, end_date: datetime):
    """Enhanced fetch with automatic historical detection"""
    
    if timeframe == '1d':
        return self._fetch_daily_data(ticker, start_date, end_date)
    
    # Intraday logic
    days_from_now = (datetime.now() - end_date).days
    
    if days_from_now <= 30:
        # Recent data: use standard endpoint
        return self._fetch_intraday_recent(ticker, timeframe, start_date, end_date)
    else:
        # Historical data: use enhanced historical fetching
        return self._fetch_intraday_historical(ticker, timeframe, start_date, end_date)
```

#### **1.2 Timeframe Resolution Strategy**
```python
def _resolve_native_timeframe(self, requested_timeframe: str) -> dict:
    """Determine optimal native timeframe and resampling strategy"""
    
    native_supported = ['1min', '5min', '15min', '30min', '60min']
    
    # Mapping strategy
    mapping = {
        '1h': {'native': '60min', 'resample': None},
        '4h': {'native': '60min', 'resample': '4H'},
        '2h': {'native': '60min', 'resample': '2H'},
        '8h': {'native': '60min', 'resample': '8H'},
        '12h': {'native': '60min', 'resample': '12H'},
        '15min': {'native': '15min', 'resample': None},
        '30min': {'native': '30min', 'resample': None}
    }
    
    return mapping.get(requested_timeframe, {'native': '60min', 'resample': requested_timeframe})
```

### **Phase 2: Historical Data Fetching**

#### **2.1 Month-by-Month Strategy**
- **Use case**: Backtests requiring specific historical periods
- **Method**: `TIME_SERIES_INTRADAY` with `month=YYYY-MM` parameter
- **Advantage**: Precise date control, efficient for sparse date ranges

#### **2.2 Extended Slices Strategy** 
- **Use case**: Deep historical analysis (up to 2 years)
- **Method**: `TIME_SERIES_INTRADAY_EXTENDED` with slice parameters
- **Advantage**: Bulk fetching for comprehensive historical data

#### **2.3 Intelligent Method Selection**
```python
def _select_historical_method(self, start_date: datetime, end_date: datetime) -> str:
    """Choose optimal historical fetching method"""
    
    total_days = (end_date - start_date).days
    months_needed = total_days / 30
    
    if months_needed <= 3:
        return 'month_by_month'  # Precise, fewer API calls
    elif months_needed <= 24:
        return 'extended_slices'  # Bulk fetching
    else:
        return 'hybrid'  # Combination approach
```

### **Phase 3: Enhanced Caching Strategy**

#### **3.1 Multi-Level Cache Architecture**
```
cache/
├── alpha_vantage/
│   ├── {ticker}/
│   │   ├── 1h/
│   │   │   ├── recent/          # Last 30 days cache
│   │   │   ├── monthly/         # Month-by-month cache
│   │   │   └── slices/          # Extended slices cache
│   │   ├── 4h/
│   │   └── 1d/
```

#### **3.2 Cache Key Strategy**
```python
def _get_enhanced_cache_key(self, ticker: str, timeframe: str, 
                           start_date: datetime, end_date: datetime) -> str:
    """Generate cache key based on data type and date range"""
    
    if timeframe == '1d':
        return f"{ticker}_{timeframe}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pkl"
    
    days_from_now = (datetime.now() - end_date).days
    
    if days_from_now <= 30:
        # Recent cache
        return f"{ticker}_{timeframe}_recent_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pkl"
    else:
        # Historical monthly cache
        month_str = start_date.strftime('%Y-%m')
        return f"{ticker}_{timeframe}_monthly_{month_str}.pkl"
```

### **Phase 4: Resampling Engine**

#### **4.1 Universal Resampling Logic**
```python
def _resample_timeframe(self, df: pd.DataFrame, target_timeframe: str) -> pd.DataFrame:
    """Universal resampling for any target timeframe"""
    
    # Parse target timeframe
    if target_timeframe.endswith('h'):
        hours = int(target_timeframe[:-1])
        resample_rule = f"{hours}H"
    elif target_timeframe.endswith('min'):
        minutes = int(target_timeframe[:-3])
        resample_rule = f"{minutes}T"
    else:
        raise ValueError(f"Unsupported timeframe format: {target_timeframe}")
    
    # Market-aware resampling (9:30 AM ET origin)
    resampled = df.resample(resample_rule, origin='09:30').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min', 
        'Close': 'last',
        'Volume': 'sum'
    }).dropna()
    
    return resampled
```

## 🧪 **Testing Strategy**

### **Test Phase 1: Unit Tests**
- ✅ Date range detection logic
- ✅ Timeframe resolution mapping
- ✅ Cache key generation
- ✅ Resampling accuracy

### **Test Phase 2: Integration Tests**
- ✅ Recent data fetching (last 30 days)
- ✅ Historical data fetching (month-by-month)
- ✅ Extended slices fetching
- ✅ Cache invalidation and retrieval
- ✅ Provider interface compatibility

### **Test Phase 3: Regression Tests**  
- ✅ Existing functionality preservation
- ✅ TimeframeManager compatibility
- ✅ Position Manager integration
- ✅ Backtest scenarios (recent vs historical)

### **Test Phase 4: Performance Tests**
- ✅ API rate limiting compliance
- ✅ Cache hit ratios
- ✅ Memory usage with large datasets
- ✅ Concurrent request handling

## 📋 **Implementation Checklist**

### **Deliverable 1: Enhanced Provider Foundation**
- [ ] Smart date-aware fetching logic
- [ ] Timeframe resolution engine
- [ ] Enhanced cache strategy
- [ ] Unit tests for core logic
- [ ] Integration test with existing cached data

### **Deliverable 2: Historical Data Fetching**
- [ ] Month-by-month implementation
- [ ] Extended slices implementation  
- [ ] Intelligent method selection
- [ ] Historical cache management
- [ ] Integration tests with real API calls

### **Deliverable 3: Universal Resampling**
- [ ] Scalable resampling engine
- [ ] Support for arbitrary timeframes (2h, 8h, 12h)
- [ ] Market-aware resampling (trading hours)
- [ ] Resampling accuracy tests
- [ ] Performance optimization

### **Deliverable 4: Complete Integration**
- [ ] Full backward compatibility verification
- [ ] TimeframeManager integration
- [ ] Position Manager compatibility
- [ ] End-to-end backtest validation
- [ ] Documentation updates

## 🎯 **Success Criteria**

### **Functional Requirements**
- ✅ Historical intraday data beyond 30 days
- ✅ Support for 1h, 4h timeframes (primary)
- ✅ Scalable architecture for future timeframes (2h, 8h, 12h)
- ✅ Zero breaking changes to existing interfaces
- ✅ Maintained performance characteristics

### **Non-Functional Requirements**
- ✅ API rate limit compliance (75 req/min)
- ✅ Efficient caching (>90% cache hit for historical data)
- ✅ Memory efficiency (<500MB for typical operations)
- ✅ Error resilience (retry logic, fallback mechanisms)

### **Integration Requirements**
- ✅ TimeframeManager compatibility
- ✅ Provider abstraction preservation
- ✅ Cache system compatibility
- ✅ Position Manager integration
- ✅ Technical Analyzer compatibility

## 🚨 **Risk Mitigation**

### **API Rate Limiting**
- Intelligent batching of month-by-month requests
- Progressive backoff for extended slice requests
- Cache-first approach to minimize API calls

### **Data Quality**
- Validation of historical data completeness
- Gap detection and handling
- Resampling accuracy verification

### **Backward Compatibility**
- Comprehensive regression test suite
- Gradual rollout with feature flags
- Fallback to existing logic if enhanced logic fails

## 📊 **Performance Expectations**

### **Cache Hit Ratios**
- **Recent data**: 95% (frequently accessed)
- **Historical data**: 98% (mostly static once fetched)
- **Resampled data**: 90% (cached after first computation)

### **API Call Reduction**
- **Current**: 1 call per timeframe per asset per date range
- **Enhanced**: 1 call per month per timeframe (for historical)
- **Expected reduction**: 60-80% for typical backtest scenarios

### **Memory Usage**
- **Target**: <500MB for 100 assets × 3 timeframes × 1 year
- **Strategy**: Lazy loading, intelligent cache eviction
- **Monitoring**: Memory profiling in integration tests

---

## 🎯 **Next Steps**

1. **Review and approve this plan**
2. **Begin Deliverable 1**: Enhanced Provider Foundation
3. **Run comprehensive tests after each deliverable**
4. **Iterate based on test results and performance metrics**

This plan ensures a robust, scalable solution while maintaining all existing functionality and performance characteristics.