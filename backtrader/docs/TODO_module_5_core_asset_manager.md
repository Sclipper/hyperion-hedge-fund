# Module 5: Override & Core-Asset Manager Implementation Plan

**Status**: Planning  
**Priority**: High  
**Dependencies**: Modules 1-4 (Core Rebalancer Engine, Bucket Diversification, Dynamic Sizing, Grace & Holding Period Manager)  
**Estimated Effort**: 3-4 days  

## 🎯 **Module Overview**

### **Purpose**
Implement sophisticated asset override systems that allow exceptional high-alpha assets to bypass normal diversification constraints while maintaining risk management discipline through lifecycle tracking and performance monitoring.

### **Key Features**
- **Core Asset Designation**: Mark high-scoring assets as "core" with special immunity privileges
- **Lifecycle Management**: Automatic expiry and performance-based revocation of core status
- **Grace Period Exemption**: Core assets immune to grace period decay
- **Bucket Override Integration**: Assets granted bucket overrides automatically become core
- **Performance Monitoring**: Continuous tracking vs bucket performance with auto-revocation
- **Manual Override Controls**: Portfolio manager controls for extending/revoking core status

### **Professional Benefits**
- **Alpha Preservation**: Ensures exceptional opportunities aren't lost to mechanical rules
- **Risk Discipline**: Prevents indefinite rule-breaking through lifecycle management
- **Institutional Quality**: Provides sophisticated override controls expected by professional managers
- **Audit Trail**: Complete tracking of all override decisions and outcomes

## 🏗️ **Architecture Overview**

### **Core Components**

```python
# Data Models
@dataclass
class CoreAssetInfo:
    asset: str
    designation_date: datetime
    expiry_date: datetime
    reason: str
    bucket: str
    extension_count: int = 0
    performance_warnings: List[str] = field(default_factory=list)

# Main Manager
class CoreAssetManager:
    - mark_as_core()          # Grant core status
    - is_core_asset()         # Check current core status  
    - revoke_core_status()    # Manual revocation
    - extend_core_status()    # Extend expiry
    - get_core_status_report()# Generate status reports
    - _auto_revoke_lifecycle_check() # Automatic lifecycle management

# Integration Enhancements
class EnhancedGracePeriodManager(GracePeriodManager):
    - should_apply_grace_period() # Exempt core assets

class EnhancedSmartDiversificationManager:
    - grant_bucket_override()  # Auto-mark bucket overrides as core
```

### **Integration Points**
- **RebalancingLimits**: Add core asset configuration parameters
- **SelectionService**: Integrate core asset immunity checks
- **CoreRebalancerEngine**: Initialize and orchestrate core asset lifecycle
- **BucketLimitsEnforcer**: Allow core asset bucket override exemptions
- **CLI**: Expose all core asset configuration parameters

## 📋 **Implementation Phases**

### **Phase 1: Core Data Models & Basic Manager** (Day 1)

#### **Deliverables**
1. `CoreAssetInfo` dataclass with comprehensive tracking
2. `CoreAssetManager` class with core functionality
3. Basic lifecycle management (expiry, manual controls)
4. Unit tests for core functionality

#### **Implementation Steps**

**1.1 Create Core Asset Data Models**
```python
# In backtrader/core/models.py - Add to existing file

@dataclass
class CoreAssetInfo:
    asset: str
    designation_date: datetime
    expiry_date: datetime
    reason: str
    bucket: str
    extension_count: int = 0
    performance_warnings: List[str] = field(default_factory=list)
    last_performance_check: Optional[datetime] = None
    designation_score: Optional[float] = None
    bucket_average_at_designation: Optional[float] = None

# Add to RebalancingLimits
@dataclass
class RebalancingLimits:
    # ... existing fields ...
    
    # Core Asset Management (Module 5)
    enable_core_asset_management: bool = True
    core_asset_override_threshold: float = 0.95
    core_asset_expiry_days: int = 90
    core_asset_underperformance_threshold: float = 0.15
    core_asset_underperformance_period: int = 30
    max_core_assets: int = 3
    core_asset_extension_limit: int = 2
    core_asset_performance_check_frequency: int = 7  # Days between checks
```

**1.2 Implement CoreAssetManager Basic Functionality**
```python
# Create backtrader/core/core_asset_manager.py

class CoreAssetManager:
    def __init__(self, bucket_manager=None):
        self.core_assets: Dict[str, CoreAssetInfo] = {}
        self.bucket_manager = bucket_manager
        self.config = None  # Will be updated from RebalancingLimits
        
    def mark_as_core(self, asset: str, current_date: datetime, 
                    reason: str, designation_score: float = None) -> bool:
        """Mark asset as core with comprehensive tracking"""
        
    def is_core_asset(self, asset: str, current_date: datetime = None) -> bool:
        """Check if asset is currently core (with lifecycle validation)"""
        
    def revoke_core_status(self, asset: str, reason: str = "Manual revocation") -> bool:
        """Manually revoke core status"""
        
    def extend_core_status(self, asset: str, additional_days: int, 
                          current_date: datetime, reason: str = "Manual extension") -> bool:
        """Extend core status expiry date"""
        
    def should_exempt_from_grace(self, asset: str, current_date: datetime) -> bool:
        """Check if asset should be exempt from grace periods"""
        
    def get_core_assets_list(self) -> List[str]:
        """Get list of currently active core assets"""
        
    def update_config(self, limits: RebalancingLimits):
        """Update configuration from RebalancingLimits"""
```

**1.3 Unit Tests for Phase 1**
```python
# Create backtrader/test_core_asset_manager.py

class TestCoreAssetManager:
    def test_mark_as_core()
    def test_is_core_asset()
    def test_manual_revocation()
    def test_manual_extension()
    def test_grace_period_exemption()
    def test_config_updates()
    def test_core_asset_limits()
```

### **Phase 2: Performance Monitoring & Auto-Revocation** (Day 1-2)

#### **Deliverables**
1. Bucket performance comparison logic
2. Automatic revocation based on underperformance
3. Performance warning system
4. Enhanced lifecycle management

#### **Implementation Steps**

**2.1 Implement Performance Monitoring**
```python
# Enhance CoreAssetManager with performance tracking

class CoreAssetManager:
    def _check_underperformance(self, asset: str, current_date: datetime) -> Tuple[bool, float]:
        """Check if core asset is underperforming its bucket significantly"""
        
    def _calculate_asset_return(self, asset: str, start_date: datetime, 
                               end_date: datetime) -> Optional[float]:
        """Calculate asset return over period"""
        
    def _calculate_bucket_average_return(self, bucket: str, start_date: datetime,
                                        end_date: datetime, exclude_asset: str = None) -> Optional[float]:
        """Calculate bucket average return excluding specified asset"""
        
    def _should_auto_revoke(self, asset: str, current_date: datetime) -> Tuple[bool, str]:
        """Comprehensive auto-revocation check with detailed reason"""
        
    def _auto_revoke_core_status(self, asset: str, current_date: datetime, reason: str):
        """Automatically revoke core status with audit trail"""
        
    def perform_lifecycle_check(self, current_date: datetime) -> Dict[str, str]:
        """Perform lifecycle check on all core assets"""
```

**2.2 Implement Warning System**
```python
def _issue_performance_warning(self, asset: str, underperformance: float, 
                              current_date: datetime):
    """Issue warning for underperforming core asset"""
    
def get_performance_warnings(self) -> Dict[str, List[str]]:
    """Get all current performance warnings"""
    
def clear_performance_warnings(self, asset: str = None):
    """Clear warnings for specific asset or all assets"""
```

**2.3 Unit Tests for Phase 2**
```python
def test_performance_monitoring()
def test_auto_revocation_expiry()
def test_auto_revocation_underperformance()
def test_performance_warnings()
def test_lifecycle_check()
def test_bucket_return_calculation()
```

### **Phase 3: Integration with Existing Systems** (Day 2-3)

#### **Deliverables**
1. Enhanced GracePeriodManager with core asset exemptions
2. Enhanced BucketLimitsEnforcer with core asset overrides
3. Integration with SelectionService
4. Enhanced SmartDiversificationManager

#### **Implementation Steps**

**3.1 Enhance Grace Period Manager Integration**
```python
# Enhance backtrader/core/grace_period_manager.py

class EnhancedGracePeriodManager(GracePeriodManager):
    def __init__(self, grace_period_days=5, decay_rate=0.8, min_decay_factor=0.1,
                 core_asset_manager=None):
        super().__init__(grace_period_days, decay_rate, min_decay_factor)
        self.core_asset_manager = core_asset_manager
    
    def should_apply_grace_period(self, asset: str, current_score: float, 
                                 threshold: float, current_date: datetime) -> Tuple[bool, str]:
        """Enhanced grace period check with core asset exemption"""
        
    def handle_underperforming_position(self, asset: str, current_score: float,
                                       current_size: float, min_threshold: float,
                                       current_date: datetime) -> GraceAction:
        """Enhanced with core asset immunity"""
```

**3.2 Enhance Bucket Limits Enforcer**
```python
# Enhance backtrader/core/bucket_limits_enforcer.py

class EnhancedBucketLimitsEnforcer(BucketLimitsEnforcer):
    def __init__(self, bucket_manager, core_asset_manager=None):
        super().__init__(bucket_manager)
        self.core_asset_manager = core_asset_manager
    
    def apply_bucket_limits(self, assets: List[AssetScore], limits: RebalancingLimits,
                           current_date: datetime = None) -> BucketEnforcementResult:
        """Enhanced bucket limits with core asset override capability"""
        
    def _can_override_bucket_limit(self, asset: str, current_score: float,
                                  limits: RebalancingLimits, current_date: datetime) -> Tuple[bool, str]:
        """Check if asset qualifies for bucket override + core designation"""
```

**3.3 Enhance Smart Diversification Manager**
```python
# Create enhanced version or enhance existing

class EnhancedSmartDiversificationManager:
    def __init__(self, bucket_override_threshold=0.95, max_overrides=2, 
                 core_asset_manager=None):
        self.bucket_override_threshold = bucket_override_threshold
        self.max_overrides = max_overrides
        self.core_asset_manager = core_asset_manager
    
    def grant_bucket_override(self, asset: str, score: float, current_date: datetime,
                             bucket: str) -> bool:
        """Grant bucket override AND mark as core asset"""
```

**3.4 Integration Tests for Phase 3**
```python
# Create backtrader/test_core_asset_integration.py

def test_grace_period_core_exemption()
def test_bucket_override_core_designation() 
def test_core_asset_bucket_limit_override()
def test_selection_service_core_integration()
def test_smart_diversification_core_marking()
```

### **Phase 4: Core Rebalancer Engine Integration** (Day 3)

#### **Deliverables**
1. CoreAssetManager initialization in CoreRebalancerEngine
2. Lifecycle management integration in rebalancing flow
3. Core asset reporting in rebalancing results
4. Configuration updates throughout the pipeline

#### **Implementation Steps**

**4.1 Enhance CoreRebalancerEngine**
```python
# Enhance backtrader/core/rebalancer_engine.py

class CoreRebalancerEngine:
    def __init__(self, ...):
        # ... existing initialization ...
        self.core_asset_manager = CoreAssetManager(bucket_manager=self.bucket_manager)
        
        # Update other managers to use core asset manager
        self.grace_period_manager = EnhancedGracePeriodManager(
            core_asset_manager=self.core_asset_manager
        )
        
        self.bucket_limits_enforcer = EnhancedBucketLimitsEnforcer(
            bucket_manager=self.bucket_manager,
            core_asset_manager=self.core_asset_manager
        )
    
    def rebalance(self, rebalance_date: datetime, ...):
        # ... existing steps ...
        
        # NEW: Update core asset manager config
        self.core_asset_manager.update_config(limits)
        
        # NEW: Perform core asset lifecycle check
        lifecycle_report = self.core_asset_manager.perform_lifecycle_check(rebalance_date)
        
        # ... existing rebalancing logic ...
        
        # NEW: Generate core asset status report
        core_status_report = self._generate_core_asset_report(rebalance_date)
        
        return RebalancingResult(
            # ... existing fields ...
            core_asset_lifecycle_report=lifecycle_report,
            core_asset_status_report=core_status_report
        )
    
    def _generate_core_asset_report(self, current_date: datetime) -> Dict:
        """Generate comprehensive core asset status report"""
```

**4.2 Enhance SelectionService Integration**
```python
# Enhance backtrader/core/selection_service.py

class SelectionService:
    def __init__(self, ...):
        # ... existing initialization ...
        self.core_asset_manager = None  # Will be set by CoreRebalancerEngine
    
    def set_core_asset_manager(self, core_asset_manager: CoreAssetManager):
        """Set core asset manager reference"""
        
    def select_by_score(self, ...):
        # ... existing logic ...
        
        # NEW: Apply core asset protections before other lifecycle management
        if self.core_asset_manager:
            scored_assets = self._apply_core_asset_protections(
                scored_assets, limits, current_date
            )
        
        # ... existing lifecycle management ...
    
    def _apply_core_asset_protections(self, scored_assets: List[AssetScore],
                                     limits: RebalancingLimits, current_date: datetime) -> List[AssetScore]:
        """Apply core asset protections and exemptions"""
```

**4.3 Integration Tests for Phase 4**
```python
def test_core_rebalancer_engine_initialization()
def test_core_asset_lifecycle_in_rebalancing()
def test_core_asset_reporting()
def test_selection_service_core_protections()
def test_bucket_override_to_core_asset_flow()
```

### **Phase 5: CLI Integration & Configuration** (Day 3-4)

#### **Deliverables**
1. CLI parameters for all core asset features
2. Configuration validation
3. Example configurations and presets
4. Complete documentation

#### **Implementation Steps**

**5.1 Add CLI Parameters**
```python
# Enhance backtrader/main.py

def add_core_asset_arguments(parser):
    """Add core asset management arguments"""
    
    core_group = parser.add_argument_group('Core Asset Management')
    
    core_group.add_argument('--enable-core-asset-management', 
                           action='store_true', default=True,
                           help='Enable core asset management system')
    
    core_group.add_argument('--core-asset-override-threshold', 
                           type=float, default=0.95,
                           help='Score threshold for automatic core asset designation')
    
    core_group.add_argument('--core-asset-expiry-days', 
                           type=int, default=90,
                           help='Automatic expiry days for core assets')
    
    core_group.add_argument('--core-asset-underperformance-threshold', 
                           type=float, default=0.15,
                           help='Underperformance threshold for auto-revocation')
    
    core_group.add_argument('--core-asset-underperformance-period', 
                           type=int, default=30,
                           help='Days to measure underperformance')
    
    core_group.add_argument('--max-core-assets', 
                           type=int, default=3,
                           help='Maximum number of core assets')
    
    core_group.add_argument('--core-asset-extension-limit', 
                           type=int, default=2,
                           help='Maximum extensions per core asset')

def validate_core_asset_arguments(args):
    """Validate core asset configuration"""
```

**5.2 Configuration Integration**
```python
def run_regime_backtest(...):
    # ... existing parameters ...
    
    # NEW: Core asset parameters
    enable_core_asset_management=True,
    core_asset_override_threshold=0.95,
    core_asset_expiry_days=90,
    core_asset_underperformance_threshold=0.15,
    core_asset_underperformance_period=30,
    max_core_assets=3,
    core_asset_extension_limit=2
    
    # ... build RebalancingLimits with core asset params ...
```

**5.3 CLI Tests**
```python
def test_core_asset_cli_arguments()
def test_core_asset_configuration_validation()
def test_core_asset_config_integration()
```

### **Phase 6: Comprehensive Testing & Validation** (Day 4)

#### **Deliverables**
1. Full integration test suite
2. Edge case testing
3. Performance validation
4. Professional scenario testing

#### **Implementation Steps**

**6.1 Create Comprehensive Integration Tests**
```python
# Create backtrader/test_module5_integration.py

class TestModule5Integration:
    def test_full_core_asset_lifecycle()
    def test_bucket_override_to_core_designation()
    def test_grace_period_exemption_integration()
    def test_performance_based_auto_revocation()
    def test_core_asset_expiry_flow()
    def test_manual_override_controls()
    def test_core_asset_reporting()
    def test_configuration_parameter_effects()
    def test_edge_case_scenarios()
    def test_professional_use_cases()
```

**6.2 Professional Scenario Testing**
```python
def test_high_alpha_asset_preservation():
    """Test that exceptional assets are preserved through rule changes"""
    
def test_risk_discipline_maintenance():
    """Test that core assets don't become permanent rule-breakers"""
    
def test_institutional_override_controls():
    """Test manual controls meet professional standards"""
    
def test_audit_trail_completeness():
    """Test that all override decisions are fully documented"""
```

**6.3 Performance & Edge Case Testing**
```python
def test_core_asset_limit_enforcement()
def test_concurrent_core_designation_and_revocation()
def test_regime_change_with_core_assets()
def test_bucket_overflow_with_core_assets()
def test_grace_period_interaction_edge_cases()
```

## 🎛️ **Configuration Examples**

### **Conservative Institutional Setup**
```bash
python main.py regime \
  --enable-core-asset-management \
  --core-asset-override-threshold 0.97 \
  --core-asset-expiry-days 60 \
  --core-asset-underperformance-threshold 0.10 \
  --core-asset-underperformance-period 21 \
  --max-core-assets 2 \
  --core-asset-extension-limit 1
```

### **Aggressive Alpha Capture**
```bash
python main.py regime \
  --core-asset-override-threshold 0.92 \
  --core-asset-expiry-days 120 \
  --core-asset-underperformance-threshold 0.20 \
  --max-core-assets 4 \
  --core-asset-extension-limit 3
```

### **Balanced Professional**
```bash
python main.py regime \
  --core-asset-override-threshold 0.95 \
  --core-asset-expiry-days 90 \
  --core-asset-underperformance-threshold 0.15 \
  --core-asset-underperformance-period 30 \
  --max-core-assets 3 \
  --core-asset-extension-limit 2
```

## 📊 **Success Metrics**

### **Functional Requirements**
- ✅ High-alpha assets (>threshold) automatically designated as core
- ✅ Core assets exempt from grace period decay
- ✅ Core assets can override bucket diversification limits
- ✅ Automatic expiry after specified days
- ✅ Performance-based auto-revocation vs bucket average
- ✅ Manual controls for extension/revocation
- ✅ Complete audit trail of all override decisions

### **Professional Standards**
- ✅ Institutional-grade override controls
- ✅ Risk discipline through lifecycle management
- ✅ Transparent decision reasoning
- ✅ Configurable parameters for different risk tolerances
- ✅ Edge case handling for complex scenarios
- ✅ Performance monitoring and reporting

### **Integration Quality**
- ✅ Seamless integration with all existing modules
- ✅ Backward compatibility maintained
- ✅ No performance degradation
- ✅ All CLI parameters functional
- ✅ Comprehensive test coverage (>95%)

## 🚧 **Implementation Notes**

### **Critical Integration Points**
1. **CoreRebalancerEngine**: Central orchestration of core asset lifecycle
2. **GracePeriodManager**: Core assets must be exempt from grace periods
3. **BucketLimitsEnforcer**: Core assets can override bucket limits
4. **SelectionService**: Core asset protections applied before other rules
5. **CLI**: All parameters exposed and validated

### **Risk Mitigation**
1. **Performance Impact**: Efficient bucket return calculations
2. **State Management**: Robust core asset state persistence
3. **Edge Cases**: Comprehensive testing of concurrent operations
4. **Configuration**: Validation of parameter combinations

### **Professional Considerations**
1. **Audit Requirements**: Complete tracking of override decisions
2. **Risk Controls**: Automatic lifecycle management prevents abuse
3. **Flexibility**: Manual controls for portfolio manager intervention
4. **Transparency**: Clear reporting of core asset status and performance

## 📈 **Expected Outcomes**

### **Immediate Benefits**
- High-alpha assets preserved through diversification changes
- Professional-grade override controls available
- Reduced risk of losing exceptional opportunities to mechanical rules

### **Strategic Advantages**
- **Alpha Preservation**: Systematic protection of exceptional assets
- **Risk Discipline**: Lifecycle management prevents permanent rule-breaking
- **Institutional Quality**: Professional controls meet hedge fund standards
- **Audit Compliance**: Complete trail for regulatory/risk management review

### **Enhanced Capabilities**
- Dynamic asset treatment based on performance metrics
- Sophisticated override hierarchies
- Professional risk management controls
- Transparent decision-making processes

---

**Next Steps**: Upon approval, begin Phase 1 implementation with CoreAssetManager basic functionality and comprehensive unit testing. 