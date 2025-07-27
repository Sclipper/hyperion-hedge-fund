# TODO: Module 12 - Enhanced Asset Scanner Implementation

## 🎯 **Module Overview**

Module 12 implements a sophisticated asset-level market condition scanner that determines whether individual assets are trending, ranging, breaking out, or breaking down. This is fundamentally different from macro regime detection (Module 6) and operates at the individual asset level using multi-timeframe technical analysis.

**CRITICAL DISTINCTION**: 
- **Module 6 (Regime Detection)**: Macro economic regimes (Goldilocks, Deflation, Inflation, Reflation)
- **Module 12 (Asset Scanner)**: Asset-level market conditions (Trending, Ranging, Breakout, Breakdown)

---

## 🏗️ **Database Schema Reference**

```prisma
model scanner_historical {
  id         Int      @id @default(autoincrement())
  ticker     String
  market     Market   // Enum: trending, ranging, breakout, breakdown
  confidence Float    // 0.0 - 1.0
  timeframe  String   // '1d', '4h', '1h'
  date       DateTime // Historical date this data represents
  created_at DateTime @default(now())
  updated_at DateTime @updatedAt

  @@unique([ticker, timeframe, date])
  @@index([ticker])
  @@index([date])
  @@index([market])
}

enum Market {
  trending
  ranging
  breakout
  breakdown
}
```

---

## 📋 **Implementation Phases**

### **Phase 1: Enhanced Asset Scanner Core (Week 1)**

#### **1.1 Core Scanner Architecture**
```python
# File: core/enhanced_asset_scanner.py

class EnhancedAssetScanner:
    """
    Multi-timeframe asset market condition scanner with fallback technical analysis
    
    Key Features:
    - Database-first approach with technical analysis fallback
    - Multi-timeframe analysis (1d, 4h, 1h)
    - Configurable confidence thresholds
    - Asset-level market condition detection
    - Complete independence from macro regime detection
    """
    
    def __init__(self, 
                 enable_database=True,
                 timeframes=['1d', '4h', '1h'],
                 fallback_enabled=True,
                 confidence_weights=None):
        self.enable_database = enable_database
        self.timeframes = timeframes
        self.fallback_enabled = fallback_enabled
        self.confidence_weights = confidence_weights or {
            '1d': 0.5,    # Daily primary weight
            '4h': 0.3,    # 4-hour intermediate
            '1h': 0.2     # Hourly short-term
        }
```

#### **1.2 Database Integration Layer**
```python
def scan_from_database(self, tickers: List[str], date: datetime, 
                      min_confidence: float = 0.7) -> Dict[str, AssetCondition]:
    """
    Primary scanner method - attempts database first
    
    Returns:
        Dict mapping ticker to AssetCondition with:
        - market: MarketCondition enum
        - confidence: float
        - timeframe_breakdown: Dict[str, float]
        - source: 'database' | 'fallback'
    """
```

#### **1.3 Technical Analysis Fallback**
```python
def scan_from_technical_analysis(self, tickers: List[str], date: datetime,
                                data_manager) -> Dict[str, AssetCondition]:
    """
    Fallback scanner using multi-timeframe technical analysis
    
    Technical Indicators:
    - Trend: ADX, MA alignment, MACD
    - Range: Bollinger Band position, RSI oscillation
    - Breakout: Volume surge, volatility expansion
    - Breakdown: Support breaks, momentum divergence
    """
```

---

### **Phase 2: Multi-Timeframe Technical Analysis Engine (Week 2)**

#### **2.1 Trending Condition Detection**
```python
def _detect_trending_condition(self, price_data: pd.DataFrame, 
                              timeframe: str) -> Tuple[float, Dict]:
    """
    Detect trending market condition using multiple indicators
    
    Primary Indicators:
    - ADX > 25 (strong trend)
    - MA alignment (5 > 10 > 20 > 50)
    - MACD histogram expansion
    - Price above/below key MAs consistently
    
    Confidence Scoring:
    - 0.9+: All indicators aligned, strong momentum
    - 0.7-0.9: Most indicators aligned
    - 0.5-0.7: Mixed signals, weak trend
    - <0.5: No clear trend
    """
```

#### **2.2 Ranging Condition Detection**
```python
def _detect_ranging_condition(self, price_data: pd.DataFrame,
                             timeframe: str) -> Tuple[float, Dict]:
    """
    Detect ranging/sideways market condition
    
    Primary Indicators:
    - ADX < 20 (weak trend)
    - Bollinger Band squeeze
    - RSI oscillating between 30-70
    - Price oscillating between support/resistance
    - Low volatility relative to recent history
    
    Confidence Scoring:
    - High confidence: Tight range, low ADX, mean reversion signals
    - Medium confidence: Loose range, some directional bias
    - Low confidence: Unclear range boundaries
    """
```

#### **2.3 Breakout Condition Detection**
```python
def _detect_breakout_condition(self, price_data: pd.DataFrame,
                              timeframe: str) -> Tuple[float, Dict]:
    """
    Detect breakout from consolidation/range
    
    Primary Indicators:
    - Volume surge (2x+ average)
    - Volatility expansion (ATR increase)
    - Break above resistance with momentum
    - RSI breaking above/below key levels
    - MACD signal line cross with histogram acceleration
    
    Confidence Scoring:
    - Volume confirmation critical for high confidence
    - Multiple timeframe alignment increases confidence
    """
```

#### **2.4 Breakdown Condition Detection**
```python
def _detect_breakdown_condition(self, price_data: pd.DataFrame,
                               timeframe: str) -> Tuple[float, Dict]:
    """
    Detect breakdown/support failure
    
    Primary Indicators:
    - Support level break with volume
    - Momentum divergence signals
    - RSI failure swings
    - MACD bearish cross below zero
    - Volatility spike on downside
    """
```

---

### **Phase 3: Configuration and Integration (Week 3)**

#### **3.1 Configuration Parameters**
```python
# Add to config/parameter_registry.py

# Module 12: Enhanced Asset Scanner
self.register_parameter(ParameterDefinition(
    name='enable_asset_scanner_database',
    type=bool,
    default_value=True,
    description='Enable database lookup for asset scanner',
    tier_level=ParameterTier.INTERMEDIATE,
    module='Enhanced Asset Scanner',
    cli_name='enable-scanner-database',
    help_text='When disabled, scanner relies entirely on technical analysis fallback'
))

self.register_parameter(ParameterDefinition(
    name='asset_scanner_timeframes',
    type=list,
    default_value=['1d', '4h', '1h'],
    description='Timeframes for multi-timeframe asset analysis',
    tier_level=ParameterTier.ADVANCED,
    module='Enhanced Asset Scanner',
    cli_name='scanner-timeframes',
    help_text='List of timeframes to analyze. More timeframes = higher accuracy but slower processing'
))

self.register_parameter(ParameterDefinition(
    name='asset_scanner_confidence_threshold',
    type=float,
    default_value=0.6,
    description='Minimum confidence threshold for asset scanner results',
    tier_level=ParameterTier.INTERMEDIATE,
    module='Enhanced Asset Scanner',
    cli_name='scanner-confidence-threshold',
    help_text='Assets below this confidence are excluded from scanner results'
))
```

#### **3.2 Integration with Regime Detector**
```python
# Update data/regime_detector.py

class RegimeDetector:
    def __init__(self, use_database=True, use_enhanced_scanner=True):
        # IMPORTANT: Keep macro regime detection separate
        self.macro_regime_detector = DatabaseIntegration()  # For macro regimes
        self.asset_scanner = EnhancedAssetScanner() if use_enhanced_scanner else None
        
    def get_trending_assets(self, date: datetime, asset_universe: List[str]) -> List[str]:
        """
        Get assets in trending condition (ASSET-LEVEL, not macro regime)
        
        Flow:
        1. Use enhanced asset scanner for asset-level trending detection
        2. This is independent of macro regime (Goldilocks/Deflation/etc)
        3. Trending assets can exist in any macro regime
        """
        if self.asset_scanner:
            return self.asset_scanner.get_trending_assets(asset_universe, date)
        else:
            # Fallback to simple database query
            return self._fallback_trending_assets(asset_universe, date)
```

#### **3.3 Clear Separation of Concerns**
```python
# CORRECT DECISION FLOW:

# Step 1: Determine Macro Regime (Module 6)
macro_regime = regime_detector.get_market_regime(current_date)  # -> 'Goldilocks'

# Step 2: Get Asset Universe for Macro Regime (Module 6)
regime_buckets = regime_detector.get_regime_buckets(macro_regime)  # -> ['Risk Assets', 'Growth']
asset_universe = asset_manager.get_assets_from_buckets(regime_buckets)

# Step 3: Scan Individual Assets for Market Conditions (Module 12)
asset_conditions = enhanced_scanner.scan_assets(asset_universe, current_date)
trending_assets = [a.ticker for a in asset_conditions if a.market == MarketCondition.TRENDING]

# Step 4: Apply Position Management (Existing Modules)
# ... existing position scoring and selection logic
```

---

### **Phase 4: Technical Analysis Implementation (Week 4)**

#### **4.1 Core Technical Indicators**
```python
class TechnicalAnalysisEngine:
    """
    Multi-timeframe technical analysis for asset scanner fallback
    """
    
    def calculate_trend_strength(self, data: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate trend strength using multiple indicators
        
        Returns:
        {
            'adx': float,           # Average Directional Index
            'ma_alignment': float,  # Moving Average alignment score
            'macd_momentum': float, # MACD momentum score
            'trend_consistency': float, # Trend consistency over period
            'overall_strength': float  # Combined trend strength
        }
        """
    
    def calculate_range_characteristics(self, data: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate ranging market characteristics
        
        Returns:
        {
            'bb_squeeze': float,      # Bollinger Band squeeze intensity
            'support_resistance': float, # S/R level strength
            'oscillator_range': float,   # RSI/Stoch range behavior
            'volatility_compression': float, # Volatility compression level
            'range_quality': float       # Overall range quality
        }
        """
    
    def detect_breakout_signals(self, data: pd.DataFrame) -> Dict[str, float]:
        """
        Detect breakout/breakdown signals
        
        Returns:
        {
            'volume_surge': float,     # Volume confirmation
            'volatility_expansion': float, # Volatility breakout
            'momentum_acceleration': float, # Momentum signals
            'level_break_quality': float,  # Quality of level break
            'breakout_probability': float  # Overall breakout probability
        }
        """
```

#### **4.2 Multi-Timeframe Analysis**
```python
def analyze_asset_across_timeframes(self, ticker: str, date: datetime,
                                   data_manager) -> AssetCondition:
    """
    Analyze single asset across multiple timeframes
    
    Process:
    1. Get price data for each timeframe
    2. Calculate technical indicators per timeframe
    3. Weight timeframe analysis by importance
    4. Determine overall market condition
    5. Calculate confidence based on timeframe agreement
    
    Confidence Logic:
    - All timeframes agree: 0.8-0.95 confidence
    - 2/3 timeframes agree: 0.6-0.8 confidence  
    - Split signals: 0.3-0.6 confidence
    - No clear signals: 0.2-0.4 confidence
    """
```

---

### **Phase 5: Testing and Validation (Week 5)**

#### **5.1 Unit Tests**
```python
# tests/test_enhanced_asset_scanner.py

class TestEnhancedAssetScanner(unittest.TestCase):
    
    def test_database_integration(self):
        """Test database lookup functionality"""
        scanner = EnhancedAssetScanner(enable_database=True)
        results = scanner.scan_from_database(['AAPL'], datetime.now())
        self.assertIsInstance(results, dict)
    
    def test_technical_analysis_fallback(self):
        """Test fallback technical analysis when database disabled"""
        scanner = EnhancedAssetScanner(enable_database=False, fallback_enabled=True)
        mock_data_manager = MockDataManager()
        results = scanner.scan_from_technical_analysis(['AAPL'], datetime.now(), mock_data_manager)
        self.assertEqual(results['AAPL'].source, 'fallback')
    
    def test_trending_detection(self):
        """Test trending condition detection accuracy"""
        # Test with known trending data
        trending_data = self.create_trending_price_data()
        condition, confidence = scanner._detect_trending_condition(trending_data, '1d')
        self.assertGreater(confidence, 0.7)
    
    def test_ranging_detection(self):
        """Test ranging condition detection accuracy"""
        # Test with known ranging data
        ranging_data = self.create_ranging_price_data()
        condition, confidence = scanner._detect_ranging_condition(ranging_data, '1d')
        self.assertGreater(confidence, 0.7)
```

#### **5.2 Integration Tests**
```python
# tests/test_scanner_integration.py

class TestScannerIntegration(unittest.TestCase):
    
    def test_regime_detector_integration(self):
        """Test that enhanced scanner integrates correctly with regime detector"""
        regime_detector = RegimeDetector(use_enhanced_scanner=True)
        
        # Test macro regime detection (should be independent)
        macro_regime = regime_detector.get_market_regime(datetime.now())
        self.assertIn(macro_regime[0], ['Goldilocks', 'Deflation', 'Inflation', 'Reflation'])
        
        # Test asset-level scanning (should be independent)
        trending_assets = regime_detector.get_trending_assets(datetime.now(), ['AAPL', 'MSFT'])
        self.assertIsInstance(trending_assets, list)
    
    def test_decision_flow_separation(self):
        """Test that macro regime and asset scanning remain separate"""
        # Simulate Deflation macro regime with trending assets
        # This should be possible - macro deflation doesn't mean no trending assets
        pass
```

#### **5.3 Performance Tests**
```python
# tests/test_scanner_performance.py

class TestScannerPerformance(unittest.TestCase):
    
    def test_large_universe_scanning(self):
        """Test scanning performance with large asset universe"""
        large_universe = [f"STOCK_{i}" for i in range(500)]
        start_time = time.time()
        scanner.scan_assets(large_universe, datetime.now())
        duration = time.time() - start_time
        self.assertLess(duration, 30)  # Should complete within 30 seconds
    
    def test_fallback_performance(self):
        """Test that fallback technical analysis is reasonably fast"""
        scanner = EnhancedAssetScanner(enable_database=False)
        start_time = time.time()
        scanner.scan_from_technical_analysis(['AAPL'] * 50, datetime.now(), mock_data_manager)
        duration = time.time() - start_time
        self.assertLess(duration, 10)  # Should complete within 10 seconds
```

---

## 🔄 **Implementation Timeline**

### **Week 1: Core Architecture**
- [ ] Create `core/enhanced_asset_scanner.py` with main class structure
- [ ] Implement database integration layer
- [ ] Add configuration parameters to parameter registry
- [ ] Create basic unit tests for core functionality

### **Week 2: Technical Analysis Engine**
- [ ] Implement multi-timeframe data handling
- [ ] Create technical indicator calculations
- [ ] Build condition detection algorithms (trending/ranging/breakout/breakdown)
- [ ] Add confidence scoring methodology

### **Week 3: Integration and Configuration**
- [ ] Update `data/regime_detector.py` to use enhanced scanner
- [ ] Ensure clear separation between macro regime and asset scanning
- [ ] Add CLI parameters and configuration options
- [ ] Update database test utilities

### **Week 4: Fallback Implementation**
- [ ] Complete technical analysis fallback system
- [ ] Implement multi-timeframe analysis weighting
- [ ] Add graceful degradation when data unavailable
- [ ] Performance optimization and caching

### **Week 5: Testing and Validation**
- [ ] Comprehensive unit test suite
- [ ] Integration testing with existing modules
- [ ] Performance testing with large universes
- [ ] Documentation and CLAUDE.md updates

---

## ⚠️ **Critical Implementation Notes**

### **1. Separation of Concerns**
```python
# WRONG - Mixing macro regime with asset scanning
if macro_regime == 'Deflation':
    trending_assets = []  # Assume no trending in deflation

# CORRECT - Independent analysis
macro_regime = regime_detector.get_market_regime(date)  # Macro level
asset_conditions = enhanced_scanner.scan_assets(universe, date)  # Asset level
trending_assets = [a for a in asset_conditions if a.market == MarketCondition.TRENDING]
```

### **2. Database Schema Alignment**
- Use only fields that exist in actual schema: `id`, `ticker`, `market`, `confidence`, `timeframe`, `date`
- Do not assume additional fields like `strength`, `volume_ratio`, `price_change`
- Fallback technical analysis must calculate these derived metrics

### **3. Configuration Flexibility**
```python
# Must support full disable of database
scanner = EnhancedAssetScanner(
    enable_database=False,     # Force fallback mode
    fallback_enabled=True,     # Enable technical analysis
    timeframes=['1d'],         # Reduce timeframes for speed
    confidence_threshold=0.5   # Lower threshold for testing
)
```

### **4. Performance Considerations**
- Batch database queries where possible
- Cache technical analysis results
- Support partial universe analysis
- Graceful timeout handling for large universes

---

## 🎯 **Success Criteria**

1. **Functional**: Scanner accurately detects trending/ranging/breakout/breakdown conditions
2. **Configurable**: Complete database disable with technical analysis fallback works
3. **Independent**: Asset scanning operates independently from macro regime detection  
4. **Performance**: Can scan 100+ assets in under 10 seconds
5. **Robust**: Graceful degradation when data unavailable
6. **Tested**: >90% test coverage with integration tests

---

## 📚 **Related Modules**

- **Module 6**: Macro regime detection (independent but complementary)
- **Module 9**: Event logging for scanner decisions
- **Module 11**: Configuration management for scanner parameters
- **Existing**: `data/regime_detector.py` integration
- **Existing**: `position/technical_analyzer.py` shared indicators

---

**This implementation will provide a robust, configurable asset scanner that maintains clear separation between macro economic regime detection and individual asset market condition analysis.**