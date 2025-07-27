# Multi-Timeframe Data Implementation with Alpha Vantage (75 req/min)

## Executive Summary

This document outlines the architecture for implementing multi-timeframe data support using Alpha Vantage API with 75 requests/minute rate limit. The design focuses on efficient data collection, intelligent caching, resumable downloads, and seamless integration with the existing backtrader hedge fund system.

## Key Requirements

- **API Rate Limit**: 75 requests/minute (4,500/hour, 108,000/day)
- **Data Coverage**: Up to 5 years of historical intraday data
- **Timeframes**: 1h, 4h, 1d (configurable)
- **Features**: Caching, checkpointing, error handling, bulk downloads
- **Integration**: Seamless plug-in with existing system components

## Architecture Overview

### Data Provider Abstraction

The system uses a single active data provider at any time, selected via configuration. This allows clean switching between Yahoo Finance, Alpha Vantage, or future providers without code changes.

### Core Components

```
data/
├── providers/
│   ├── __init__.py
│   ├── base.py                # Abstract base provider interface
│   ├── alpha_vantage/
│   │   ├── __init__.py
│   │   ├── client.py          # Rate-limited API client
│   │   ├── data_fetcher.py    # Bulk data fetching with checkpointing
│   │   └── provider.py        # AlphaVantageProvider implementation
│   ├── yahoo_finance/
│   │   ├── __init__.py
│   │   └── provider.py        # YahooFinanceProvider (legacy)
│   └── registry.py            # Provider registration and factory
├── cache_manager.py           # Unified caching system
├── timeframe_manager.py       # Provider-agnostic orchestration
└── data_manager.py            # Updated to use provider abstraction
```

## Detailed Design

### 0. Provider Abstraction Layer

The system uses a provider abstraction that allows switching between data sources without changing business logic. Only one provider is active at any time.

```python
# data/providers/base.py
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import pandas as pd

class DataProvider(ABC):
    """
    Abstract base class for all data providers
    """
    
    @abstractmethod
    def get_supported_timeframes(self) -> List[str]:
        """Return list of supported timeframes (e.g., ['1h', '4h', '1d'])"""
        pass
    
    @abstractmethod
    def fetch_data(
        self, 
        ticker: str, 
        timeframe: str,
        start_date: datetime, 
        end_date: datetime
    ) -> pd.DataFrame:
        """Fetch data for single ticker/timeframe combination"""
        pass
    
    @abstractmethod
    def get_rate_limit(self) -> Dict[str, int]:
        """Return rate limit configuration"""
        pass
    
    @abstractmethod
    def validate_ticker(self, ticker: str) -> bool:
        """Check if ticker is valid for this provider"""
        pass
```

#### Provider Registry
```python
# data/providers/registry.py
class ProviderRegistry:
    """
    Manages data provider registration and selection
    """
    
    def __init__(self):
        self._providers = {}
        self._active_provider = None
        
    def register(self, name: str, provider: DataProvider):
        """Register a new data provider"""
        self._providers[name] = provider
        
    def set_active(self, name: str):
        """Set the active data provider"""
        if name not in self._providers:
            raise ValueError(f"Unknown provider: {name}")
        self._active_provider = self._providers[name]
        
    def get_active(self) -> DataProvider:
        """Get the currently active provider"""
        if not self._active_provider:
            raise RuntimeError("No active data provider set")
        return self._active_provider
```

#### Yahoo Finance Deprecation Strategy
```python
# data/providers/yahoo_finance/provider.py
class YahooFinanceProvider(DataProvider):
    """
    Legacy Yahoo Finance provider (to be deprecated)
    
    Limitations:
    - Only daily data for historical periods
    - Intraday data limited to last 60 days
    - No reliable 4h data support
    """
    
    def __init__(self):
        self._show_deprecation_warning()
        
    def _show_deprecation_warning(self):
        warnings.warn(
            "YahooFinanceProvider is deprecated. Limited to daily data only. "
            "Consider switching to AlphaVantageProvider for multi-timeframe support.",
            DeprecationWarning,
            stacklevel=2
        )
    
    def get_supported_timeframes(self) -> List[str]:
        # Only return what YF can reliably provide
        return ['1d']  # Daily only for historical data
    
    def fetch_data(self, ticker: str, timeframe: str, 
                  start_date: datetime, end_date: datetime) -> pd.DataFrame:
        if timeframe != '1d':
            logger.warning(f"YahooFinance doesn't support {timeframe} for historical data. Using daily.")
            timeframe = '1d'
            
        # Use existing yfinance implementation
        import yfinance as yf
        return yf.download(ticker, start=start_date, end=end_date, interval=timeframe)
```

#### Updated DataManager Integration
```python
# data/data_manager.py
class DataManager:
    """
    Updated to use provider abstraction
    """
    
    def __init__(self, provider_name: str = None, cache_dir: str = "data/cache"):
        self.registry = ProviderRegistry()
        
        # Register all available providers
        self.registry.register('yahoo', YahooFinanceProvider())
        self.registry.register('alpha_vantage', AlphaVantageProvider())
        
        # Set active provider from config or parameter
        provider = provider_name or os.getenv('DATA_PROVIDER', 'alpha_vantage')
        self.registry.set_active(provider)
        
        # Provider-agnostic components
        self.cache_manager = UnifiedCacheManager(cache_dir)
        self.validator = DataValidator()
        
    def download_data(self, ticker: str, start_date: datetime, 
                     end_date: datetime, interval: str = '1d') -> pd.DataFrame:
        """
        Backward compatible method using active provider
        """
        provider = self.registry.get_active()
        
        # Check if provider supports requested timeframe
        if interval not in provider.get_supported_timeframes():
            logger.warning(
                f"Provider {provider.__class__.__name__} doesn't support {interval}. "
                f"Available: {provider.get_supported_timeframes()}"
            )
            # Fallback to daily
            interval = '1d'
            
        return provider.fetch_data(ticker, interval, start_date, end_date)
```

### 1. Rate-Limited API Client

```python
# data/alpha_vantage/client.py
class AlphaVantageClient:
    """
    Thread-safe, rate-limited client for Alpha Vantage API
    
    Features:
    - Automatic rate limiting (75 req/min)
    - Request queuing and batching
    - Retry logic with exponential backoff
    - Connection pooling for efficiency
    """
    
    def __init__(self):
        self.rate_limiter = RateLimiter(
            max_requests=75,
            time_window=60,  # seconds
            burst_capacity=10  # Allow short bursts
        )
        self.session = self._create_session()
        self.request_queue = PriorityQueue()
        self.worker_pool = ThreadPoolExecutor(max_workers=5)
```

### 2. Bulk Data Fetching Strategy

#### 2.1 Alpha Vantage Data Limits
- **TIME_SERIES_INTRADAY_EXTENDED**: Returns up to 2 years of data per request
- **Max data points per request**: ~5,000-10,000 depending on timeframe
- **CSV format**: More efficient than JSON for bulk data

#### 2.2 Chunking Strategy
```python
# data/alpha_vantage/data_fetcher.py
class BulkDataFetcher:
    """
    Efficient bulk data fetching with checkpointing
    """
    
    CHUNK_SIZES = {
        '60min': {'months': 2, 'max_years': 2},    # ~1,460 data points
        '240min': {'months': 6, 'max_years': 2},   # ~730 data points  
        'daily': {'months': 12, 'max_years': 20}   # ~252 data points
    }
    
    def fetch_historical_data(self, ticker: str, timeframe: str, 
                            start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Fetch data in chunks with checkpointing
        
        Algorithm:
        1. Calculate optimal chunk size based on timeframe
        2. Create download plan with checkpoint markers
        3. Download chunks in parallel (respecting rate limits)
        4. Merge and validate data
        5. Save checkpoints after each successful chunk
        """
```

### 3. Checkpoint System

```python
# data/alpha_vantage/checkpoint_manager.py
class CheckpointManager:
    """
    Manages download checkpoints for resumable operations
    
    Checkpoint Structure:
    {
        'ticker': 'AAPL',
        'timeframe': '60min',
        'total_chunks': 30,
        'completed_chunks': [
            {'start': '2023-01-01', 'end': '2023-03-01', 'status': 'completed'},
            {'start': '2023-03-01', 'end': '2023-05-01', 'status': 'completed'},
            {'start': '2023-05-01', 'end': '2023-07-01', 'status': 'pending'}
        ],
        'last_updated': '2024-01-15T10:30:00',
        'data_hash': 'sha256_hash_of_completed_data'
    }
    """
    
    def save_checkpoint(self, download_state: Dict) -> None:
        checkpoint_file = self._get_checkpoint_path(
            download_state['ticker'],
            download_state['timeframe']
        )
        # Atomic write to prevent corruption
        temp_file = checkpoint_file.with_suffix('.tmp')
        json.dump(download_state, temp_file)
        temp_file.replace(checkpoint_file)
```

### 4. Provider-Specific Cache System

```python
# data/cache_manager.py
class UnifiedCacheManager:
    """
    Provider-aware caching system that maintains data isolation
    
    Key Features:
    - Provider-specific namespacing prevents data mixing
    - Metadata tracking for data provenance
    - Automatic cache invalidation on provider switch
    """
    
    CACHE_STRUCTURE = {
        'path': 'data/cache/{provider}/{ticker}/{timeframe}/',
        'format': 'parquet',
        'compression': 'snappy',
        'metadata_file': 'data/cache/{provider}/.metadata.json'
    }
    
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = Path(cache_dir)
        self.memory_cache = {}  # Provider-namespaced LRU cache
        
    def get_cache_key(self, provider: str, ticker: str, 
                     timeframe: str, date_range: Tuple[datetime, datetime]) -> str:
        """Generate provider-specific cache key"""
        start_str = date_range[0].strftime('%Y%m%d')
        end_str = date_range[1].strftime('%Y%m%d')
        return f"{provider}:{ticker}:{timeframe}:{start_str}:{end_str}"
        
    def get_data(self, provider: str, ticker: str, timeframe: str,
                start: datetime, end: datetime) -> Optional[pd.DataFrame]:
        """
        Provider-aware cache retrieval
        
        IMPORTANT: Only returns data from the specified provider's cache
        """
        cache_path = self._get_cache_path(provider, ticker, timeframe)
        if not cache_path.exists():
            return None
            
        # Verify provider metadata matches
        metadata = self._load_metadata(provider)
        if metadata.get('provider') != provider:
            logger.warning(f"Cache provider mismatch: expected {provider}, found {metadata.get('provider')}")
            return None
            
        # Load with provider verification
        df = pd.read_parquet(cache_path)
        
        # Double-check data has provider attribution
        if 'provider_source' in df.attrs:
            if df.attrs['provider_source'] != provider:
                logger.error(f"Data provider mismatch in cache: {df.attrs['provider_source']} != {provider}")
                return None
                
        return self._filter_date_range(df, start, end)
        
    def save_data(self, provider: str, ticker: str, timeframe: str,
                 data: pd.DataFrame, metadata: Dict[str, Any] = None):
        """Save data with provider attribution"""
        # Add provider metadata to dataframe
        data.attrs['provider_source'] = provider
        data.attrs['cache_timestamp'] = datetime.now().isoformat()
        data.attrs['api_version'] = metadata.get('api_version', 'unknown')
        
        cache_path = self._get_cache_path(provider, ticker, timeframe)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save with provider metadata
        data.to_parquet(cache_path, compression='snappy')
        
        # Update provider metadata file
        self._update_metadata(provider, ticker, timeframe, metadata)
```

#### Cache Isolation Example
```python
# Running with Yahoo Finance
data_manager = DataManager(provider_name='yahoo')
yahoo_data = data_manager.download_data('AAPL', start, end)
# Saves to: data/cache/yahoo/AAPL/1d/

# Later, running with Alpha Vantage
data_manager = DataManager(provider_name='alpha_vantage')
av_data = data_manager.download_data('AAPL', start, end, interval='1h')
# Saves to: data/cache/alpha_vantage/AAPL/1h/
# Does NOT use Yahoo's cached daily data!
```

### 5. Data Validation & Quality

```python
# data/alpha_vantage/validator.py
class DataValidator:
    """
    Ensures data quality and consistency
    
    Validation Rules:
    1. No gaps larger than expected (weekends/holidays)
    2. Price sanity checks (no 50%+ single-bar moves)
    3. Volume consistency
    4. Timestamp alignment
    5. OHLC relationship validation (H >= L, etc.)
    """
    
    def validate_timeframe_data(self, df: pd.DataFrame, 
                               timeframe: str) -> ValidationResult:
        checks = [
            self._check_gaps(df, timeframe),
            self._check_price_sanity(df),
            self._check_ohlc_consistency(df),
            self._check_volume_anomalies(df),
            self._check_timestamp_alignment(df, timeframe)
        ]
        return ValidationResult(checks)
```

### 6. Integration Layer

```python
# data/timeframe_manager.py
class TimeframeManager:
    """
    High-level interface for multi-timeframe data access
    Integrates with existing DataManager
    """
    
    def __init__(self, cache_dir: str = "data/cache"):
        self.av_client = AlphaVantageClient()
        self.fetcher = BulkDataFetcher(self.av_client)
        self.cache = TimeframeCacheManager(cache_dir)
        self.checkpoint_mgr = CheckpointManager(cache_dir)
        
    def get_multi_timeframe_data(
        self, 
        ticker: str, 
        timeframes: List[str],
        start_date: datetime,
        end_date: datetime,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Get data for multiple timeframes with optimal fetching
        
        Strategy:
        1. Check cache for each timeframe
        2. Identify missing data ranges
        3. Create optimized download plan
        4. Fetch missing data with progress tracking
        5. Merge and return complete datasets
        """
```

### 7. Error Handling & Recovery

```python
# data/alpha_vantage/error_handler.py
class ErrorHandler:
    """
    Comprehensive error handling with recovery strategies
    """
    
    ERROR_STRATEGIES = {
        'RateLimitError': {
            'strategy': 'exponential_backoff',
            'initial_delay': 1,
            'max_delay': 60,
            'max_retries': 5
        },
        'NetworkError': {
            'strategy': 'immediate_retry',
            'max_retries': 3
        },
        'DataError': {
            'strategy': 'skip_and_log',
            'fallback': 'use_cached_if_available'
        },
        'APIKeyError': {
            'strategy': 'fail_fast',
            'message': 'Invalid API key configuration'
        }
    }
```

## Cache Management & Provider Switching

### Cache Directory Structure
```
data/cache/
├── yahoo/                      # Yahoo Finance cache
│   ├── AAPL/
│   │   └── 1d/                # Daily data only
│   │       └── 2024_data.parquet
│   └── .metadata.json         # Provider metadata
├── alpha_vantage/             # Alpha Vantage cache
│   ├── AAPL/
│   │   ├── 1h/               # Hourly data
│   │   ├── 4h/               # 4-hour data
│   │   └── 1d/               # Daily data
│   └── .metadata.json
└── cache_config.json          # Global cache configuration
```

### Provider Switching Behavior

```python
# data/providers/manager.py
class ProviderManager:
    """
    Manages provider switching and cache validation
    """
    
    def validate_cache_on_switch(self, old_provider: str, new_provider: str):
        """
        Ensures cache isolation when switching providers
        """
        logger.info(f"Switching data provider: {old_provider} → {new_provider}")
        
        # Log cache statistics for transparency
        old_cache_size = self._get_cache_size(old_provider)
        new_cache_size = self._get_cache_size(new_provider)
        
        logger.info(f"Cache sizes - {old_provider}: {old_cache_size}MB, "
                   f"{new_provider}: {new_cache_size}MB")
        
        # Verify no cross-contamination
        if self._detect_cache_mixing(old_provider, new_provider):
            raise CacheIntegrityError(
                f"Detected mixed cache data between {old_provider} and {new_provider}"
            )
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get current provider configuration and cache status"""
        return {
            'active_provider': self.active_provider,
            'cache_locations': {
                provider: str(self.cache_dir / provider)
                for provider in self.registry.list_providers()
            },
            'cache_sizes': {
                provider: self._get_cache_size(provider)
                for provider in self.registry.list_providers()
            }
        }
```

### Cache Validation Rules

1. **Provider Attribution**: Every cached file includes provider metadata
2. **Timestamp Validation**: Cache files older than provider switch are marked
3. **Data Integrity**: Checksums verify data hasn't been corrupted
4. **No Cross-Reading**: Provider A never reads Provider B's cache

### Example: Safe Provider Switching

```python
# First run with Yahoo
python main.py regime --data-provider yahoo --ticker AAPL
# Creates: data/cache/yahoo/AAPL/1d/

# Switch to Alpha Vantage
python main.py regime --data-provider alpha_vantage --ticker AAPL --timeframes 1h,4h,1d
# Creates: data/cache/alpha_vantage/AAPL/1h/
#         data/cache/alpha_vantage/AAPL/4h/
#         data/cache/alpha_vantage/AAPL/1d/
# Does NOT read from data/cache/yahoo/!

# Verify cache isolation
python utils/verify_cache_isolation.py
# Output: ✓ Cache isolation verified. No cross-provider data detected.
```

## Implementation Plan

### Phase 1: Core Infrastructure (Days 1-2)
1. Implement rate-limited API client
2. Create basic data models and schemas
3. Set up error handling framework
4. Write unit tests for core components

### Phase 2: Fetching & Caching (Days 3-4)
1. Implement bulk data fetcher with chunking
2. Create checkpoint system
3. Build intelligent cache manager
4. Add data validation layer

### Phase 3: Integration (Days 5-6)
1. Create TimeframeManager interface
2. Update existing DataManager
3. Modify PositionManager and TechnicalAnalyzer
4. Update configuration system

### Phase 4: Testing & Optimization (Days 7-8)
1. Integration testing with real data
2. Performance optimization
3. Load testing with concurrent requests
4. Documentation and examples

## Usage Examples

### Basic Usage
```python
# Initialize the system
tf_manager = TimeframeManager()

# Fetch 2 years of data for multiple timeframes
data = tf_manager.get_multi_timeframe_data(
    ticker='AAPL',
    timeframes=['1h', '4h', '1d'],
    start_date=datetime(2022, 1, 1),
    end_date=datetime(2024, 1, 1),
    progress_callback=lambda p: print(f"Progress: {p}%")
)

# Access specific timeframe
hourly_data = data['1h']
daily_data = data['1d']
```

### Advanced Usage with Checkpointing
```python
# Resume interrupted download
tf_manager = TimeframeManager()

# This will automatically resume from last checkpoint
data = tf_manager.resume_download(
    ticker='MSFT',
    timeframes=['1h', '4h'],
    original_request_id='msft_2024_01_15_1234'
)
```

### Batch Operations
```python
# Download data for multiple tickers efficiently
tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']
timeframes = ['1h', '4h', '1d']

# Optimized batch download (uses all 75 req/min efficiently)
all_data = tf_manager.batch_download(
    tickers=tickers,
    timeframes=timeframes,
    start_date=datetime(2020, 1, 1),
    end_date=datetime(2024, 1, 1),
    max_parallel=5  # Process 5 ticker-timeframe combinations at once
)
```

## Performance Characteristics

### Download Speed Estimates
- **1h data**: ~2-3 months per request × 75 req/min = ~150-225 months/min
- **4h data**: ~6-8 months per request × 75 req/min = ~450-600 months/min  
- **Daily data**: ~2 years per request × 75 req/min = ~150 years/min

### Cache Performance
- **Memory cache hit**: < 1ms
- **Disk cache hit**: < 10ms
- **Network fetch**: 200-500ms per request

### Storage Requirements
- **1h data**: ~50MB per ticker per year (compressed)
- **4h data**: ~15MB per ticker per year (compressed)
- **Daily data**: ~3MB per ticker per year (compressed)

## Configuration

### Environment Variables
```bash
# Data Provider Selection
DATA_PROVIDER=alpha_vantage  # Options: yahoo, alpha_vantage

# Required for Alpha Vantage
ALPHA_VANTAGE_API_KEY=your_75_req_min_key

# Optional performance tuning
AV_MAX_PARALLEL_REQUESTS=5
AV_CACHE_SIZE_GB=10
AV_ENABLE_COMPRESSION=true
AV_REQUEST_TIMEOUT=30
AV_MAX_RETRIES=3
```

### Configuration File
```yaml
# config/data_providers.yaml
data_config:
  # Active provider selection
  active_provider: alpha_vantage  # or yahoo
  
  # Provider-specific configurations
  providers:
    alpha_vantage:
      rate_limit:
        requests_per_minute: 75
        burst_capacity: 10
        
      fetching:
        chunk_strategy: "adaptive"  # or "fixed"
        max_parallel_chunks: 5
        enable_checkpointing: true
        
      caching:
        memory_cache_size_mb: 1024
        disk_cache_size_gb: 50
        cache_ttl_days: 30
        compression: "snappy"
        
      validation:
        enable_validation: true
        max_gap_tolerance_hours: 72
        price_change_threshold: 0.5
    
    yahoo:
      # Minimal config for legacy provider
      cache_ttl_days: 7
      enable_warnings: true
```

## Migration Path from Yahoo Finance

### Phase 1: Parallel Testing (Week 1)
1. Deploy provider abstraction with Yahoo as default
2. Add feature flag for Alpha Vantage testing
3. Run comparison tests between providers
4. Validate data consistency

### Phase 2: Gradual Rollout (Week 2-3)
```bash
# Start with Yahoo Finance (existing behavior)
python main.py regime --data-provider yahoo

# Test with Alpha Vantage
python main.py regime --data-provider alpha_vantage --timeframes 1h,4h,1d

# Compare results
python utils/compare_providers.py --providers yahoo,alpha_vantage --ticker AAPL
```

### Phase 3: Default Switch (Week 4)
1. Change default provider to Alpha Vantage
2. Keep Yahoo available via explicit flag
3. Update documentation
4. Monitor for issues

### Phase 4: Yahoo Deprecation (Month 2)
1. Add deprecation warnings to Yahoo provider
2. Remove Yahoo from CLI help (but keep functional)
3. Plan removal date

### Backward Compatibility

The system maintains full backward compatibility:

```python
# Old code continues to work
data_manager = DataManager()
df = data_manager.download_data('AAPL', start, end)  # Uses active provider

# New code can specify provider
data_manager = DataManager(provider_name='alpha_vantage')
df = data_manager.download_data('AAPL', start, end, interval='1h')  # Multi-timeframe!

# Or use environment variable
os.environ['DATA_PROVIDER'] = 'alpha_vantage'
data_manager = DataManager()  # Uses Alpha Vantage
```

## Monitoring & Observability

### Metrics to Track
1. **API Usage**: Requests/minute, daily quota usage
2. **Cache Performance**: Hit rate, size, evictions
3. **Download Progress**: Chunks completed, time remaining
4. **Data Quality**: Validation failures, gap statistics
5. **System Health**: Memory usage, disk I/O, network latency

### Logging Strategy
```python
# Structured logging for easy monitoring
logger.info("data_fetch_started", extra={
    "ticker": ticker,
    "timeframe": timeframe,
    "date_range": f"{start_date} to {end_date}",
    "estimated_requests": estimated_requests,
    "cache_hit_rate": cache_stats.hit_rate
})
```

## Future Enhancements

1. **Predictive Caching**: Pre-fetch likely-needed data during idle times
2. **Delta Updates**: Only fetch changed data for recent periods
3. **Multi-Provider Fallback**: Add IEX Cloud or Twelve Data as backups
4. **Data Streaming**: Real-time updates for current day
5. **Distributed Caching**: Redis for multi-instance deployments

## Key Design Decisions Summary

### 1. Single Provider Architecture
- **Decision**: Only one data provider active at a time
- **Rationale**: Simplifies data consistency, caching, and debugging
- **Implementation**: Provider abstraction with registry pattern

### 2. Provider-Isolated Caching
- **Decision**: Separate cache namespaces for each provider
- **Rationale**: Prevents data contamination between providers
- **Format**: Parquet files in provider-specific directories
- **Validation**: Provider attribution checked on every cache read

### 3. Graceful Yahoo Finance Deprecation
- **Decision**: Keep Yahoo functional during transition
- **Rationale**: Allows gradual migration without breaking changes
- **Timeline**: 2-month deprecation period

### 4. Checkpoint-Based Downloads
- **Decision**: All bulk downloads are resumable
- **Rationale**: 5 years × multiple timeframes = many requests
- **Implementation**: Atomic checkpoint files with progress tracking

### 5. Smart Rate Limiting
- **Decision**: Burst capacity with request queuing
- **Rationale**: Maximize 75 req/min while avoiding 429 errors
- **Implementation**: Token bucket algorithm with priority queue

## Implementation Checklist

- [ ] **Week 1**: Provider abstraction and base infrastructure
  - [ ] Create provider interface and registry
  - [ ] Implement Yahoo wrapper with deprecation warnings
  - [ ] Set up basic Alpha Vantage client
  - [ ] Add provider selection to CLI

- [ ] **Week 2**: Alpha Vantage implementation
  - [ ] Rate-limited client with burst capacity
  - [ ] Bulk fetching with optimal chunking
  - [ ] Checkpoint system for resumable downloads
  - [ ] Data validation pipeline

- [ ] **Week 3**: Integration and testing
  - [ ] Update DataManager with provider support
  - [ ] Modify PositionManager for real multi-timeframe
  - [ ] Create provider comparison tools
  - [ ] Performance and load testing

- [ ] **Week 4**: Migration and documentation
  - [ ] Deploy with Yahoo as default
  - [ ] Run parallel tests
  - [ ] Switch default to Alpha Vantage
  - [ ] Update all documentation

## Conclusion

This architecture provides a clean, maintainable solution for multi-timeframe data support while preserving backward compatibility. The provider abstraction allows easy addition of new data sources in the future, and the deprecation strategy ensures a smooth transition from Yahoo Finance.

Key benefits:
- **Single Source of Truth**: One provider active at a time eliminates data conflicts
- **Efficient**: Maximizes the 75 req/min Alpha Vantage limit with intelligent batching
- **Resilient**: Checkpointing and caching prevent data loss and reduce API calls
- **Backward Compatible**: Existing code continues to work without changes
- **Future-Proof**: Easy to add new providers or switch between them