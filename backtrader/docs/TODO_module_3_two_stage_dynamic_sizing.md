# Module 3: Two-Stage Dynamic Sizing Module - Implementation Plan

**Priority: HIGH**  
**Status: PLANNED**  
**Estimated Effort: 1 Week**  
**Dependencies: Module 1 (Core Rebalancer Engine), Module 2 (Bucket Diversification)**

## 🎯 Module Objective

Implement intelligent two-stage position sizing to replace simple equal-weight allocation, providing score-aware, portfolio-context adaptive sizing with professional residual allocation management.

**Key Goals:**
- Replace equal-weight sizing with intelligent score-based sizing
- Implement two-stage process: cap individual positions first, then normalize remainder
- Handle residual allocation intelligently to avoid cash drift
- Support multiple sizing modes (adaptive, equal_weight, score_weighted)
- Ensure no single position exceeds maximum size limits
- Maintain 100% backward compatibility with existing system

## 🏗️ Architecture Strategy

### **Design Principles**
1. **Two-Stage Safety**: Cap individual positions before normalization to prevent over-concentration
2. **Score-Aware Sizing**: Higher scoring assets get larger allocations within constraints
3. **Portfolio Context**: Sizing adapts to portfolio size and target allocation
4. **Residual Management**: Intelligent handling of leftover allocation
5. **Flexible Modes**: Support for different sizing strategies
6. **Integration**: Seamless integration with Core Rebalancer and Bucket Diversification

### **Component Architecture**
```
Core Rebalancer Engine
├── Universe Builder (existing)
├── Scoring Service (existing)  
├── Bucket Manager (existing)
├── Bucket Limits Enforcer (existing)
├── Dynamic Position Sizer (NEW)     ← Two-stage sizing logic
├── Residual Allocator (NEW)         ← Handle leftover allocation
├── Selection Service (enhanced)      ← Integrate dynamic sizing
└── Rebalancer Engine (enhanced)     ← Optional sizing mode selection
```

## 📋 Detailed Implementation Plan

### **Phase 1: Dynamic Position Sizer Core (Days 1-2)**

#### **Component: `DynamicPositionSizer`**
```python
class DynamicPositionSizer:
    """Intelligent position sizing with two-stage safety"""
    
    def __init__(self, sizing_mode='adaptive', max_single_position=0.15, 
                 target_allocation=0.95, min_position_size=0.02):
        self.sizing_mode = sizing_mode  # 'adaptive', 'equal_weight', 'score_weighted'
        self.max_single_position = max_single_position
        self.target_allocation = target_allocation
        self.min_position_size = min_position_size
    
    def calculate_position_sizes(self, scored_assets: List[AssetScore]) -> List[AssetScore]:
        """
        Calculate position sizes using selected sizing mode
        
        Returns:
            List of AssetScore with position_size_percentage populated
        """
```

**Sizing Modes:**

1. **Adaptive Mode** (Default - Smart):
   ```python
   def _adaptive_sizing(self, assets: List[AssetScore]) -> List[AssetScore]:
       # Base size = target_allocation / num_positions
       # Score multiplier for higher scoring assets
       # Portfolio context awareness
   ```

2. **Equal Weight Mode** (Current Behavior):
   ```python
   def _equal_weight_sizing(self, assets: List[AssetScore]) -> List[AssetScore]:
       # Simple: target_allocation / num_positions for all
   ```

3. **Score Weighted Mode** (Pure Score-Based):
   ```python
   def _score_weighted_sizing(self, assets: List[AssetScore]) -> List[AssetScore]:
       # Size proportional to combined_score
       # Higher scores = larger positions
   ```

**Key Features:**
- **Portfolio Context Awareness**: Sizing adapts to number of positions and target allocation
- **Score Integration**: Higher scoring assets get preference within constraints
- **Constraint Enforcement**: Respects min/max position size limits
- **Mode Flexibility**: Easy switching between sizing strategies

#### **Testing Strategy**
- Sizing mode correctness (adaptive, equal_weight, score_weighted)
- Constraint enforcement (min/max position sizes)
- Portfolio context adaptation (different portfolio sizes)
- Score-based differentiation validation
- Edge cases (empty portfolio, single asset, extreme scores)

### **Phase 2: Two-Stage Sizing Engine (Days 3-4)**

#### **Component: `TwoStagePositionSizer`**
```python
class TwoStagePositionSizer:
    """Two-stage position sizing with residual allocation management"""
    
    def __init__(self, max_single_position=0.15, target_allocation=0.95,
                 residual_strategy='safe_top_slice'):
        self.max_single_position = max_single_position
        self.target_allocation = target_allocation
        self.residual_strategy = residual_strategy
    
    def apply_two_stage_sizing(self, sized_assets: List[AssetScore]) -> TwoStageSizingResult:
        """
        Apply two-stage sizing process
        
        Stage 1: Cap individual positions at max_single_position
        Stage 2: Normalize remaining allocation among uncapped positions
        Stage 3: Handle residual allocation
        """
```

**Two-Stage Process:**

**Stage 1: Individual Position Capping**
```python
def _stage1_apply_caps(self, assets: List[AssetScore]) -> Tuple[List[AssetScore], List[AssetScore]]:
    """
    Cap individual positions at max_single_position
    
    Returns:
        capped_assets: Assets that hit the cap
        uncapped_assets: Assets that can still grow
    """
    capped_assets = []
    uncapped_assets = []
    
    for asset in assets:
        if asset.position_size_percentage > self.max_single_position:
            asset.position_size_percentage = self.max_single_position
            asset.is_capped = True
            asset.cap_reason = f"Capped at {self.max_single_position:.1%}"
            capped_assets.append(asset)
        else:
            asset.is_capped = False
            uncapped_assets.append(asset)
    
    return capped_assets, uncapped_assets
```

**Stage 2: Remaining Allocation Distribution**
```python
def _stage2_distribute_remaining(self, capped_assets: List[AssetScore], 
                               uncapped_assets: List[AssetScore]) -> float:
    """
    Distribute remaining allocation among uncapped positions
    
    Returns:
        remaining_unallocated: Cash that couldn't be allocated
    """
    total_capped = sum(asset.position_size_percentage for asset in capped_assets)
    remaining_allocation = max(0, self.target_allocation - total_capped)
    
    if uncapped_assets and remaining_allocation > 0:
        # Distribute proportionally among uncapped positions
        total_uncapped = sum(asset.position_size_percentage for asset in uncapped_assets)
        
        if total_uncapped > 0:
            scale_factor = remaining_allocation / total_uncapped
            
            for asset in uncapped_assets:
                new_size = asset.position_size_percentage * scale_factor
                
                # Re-check cap after scaling
                if new_size > self.max_single_position:
                    asset.position_size_percentage = self.max_single_position
                    asset.is_capped = True
                    asset.cap_reason = f"Capped during Stage 2 scaling"
                else:
                    asset.position_size_percentage = new_size
    
    # Calculate final unallocated amount
    total_allocated = sum(asset.position_size_percentage for asset in capped_assets + uncapped_assets)
    return max(0, self.target_allocation - total_allocated)
```

**Data Models:**
```python
@dataclass
class TwoStageSizingResult:
    sized_assets: List[AssetScore]
    stage1_capped_count: int
    stage2_capped_count: int
    total_allocated: float
    residual_unallocated: float
    residual_strategy_applied: str
    sizing_metadata: Dict[str, Any]

@dataclass
class PositionSizeCategory(Enum):
    MAX = "max"           # Large positions (high score)
    STANDARD = "standard" # Standard positions 
    HALF = "half"         # Smaller positions
    LIGHT = "light"       # Minimal positions
    NO_POSITION = "none"  # No position
```

#### **Testing Strategy**
- Stage 1 capping correctness
- Stage 2 distribution accuracy  
- Multiple capping rounds handling
- Residual calculation accuracy
- Integration with different sizing modes

### **Phase 3: Residual Allocation Manager (Day 5)**

#### **Component: `ResidualAllocationManager`**
```python
class ResidualAllocationManager:
    """Manages intelligent allocation of residual cash"""
    
    def __init__(self, max_residual_per_asset=0.05, max_residual_multiple=0.5):
        self.max_residual_per_asset = max_residual_per_asset      # Max 5% of portfolio as residual
        self.max_residual_multiple = max_residual_multiple        # Max 50% of original size as residual
    
    def allocate_residual(self, assets: List[AssetScore], 
                         residual_amount: float, 
                         strategy: str = 'safe_top_slice') -> ResidualAllocationResult:
        """
        Allocate residual cash using specified strategy
        """
```

**Residual Allocation Strategies:**

1. **Safe Top Slice** (Default - Conservative):
   ```python
   def _safe_top_slice_allocation(self, assets: List[AssetScore], residual: float):
       # Add to top-scoring uncapped positions
       # Apply safety caps to prevent over-concentration
       # Roll leftover to cash bucket if needed
   ```

2. **Proportional Allocation** (Balanced):
   ```python
   def _proportional_allocation(self, assets: List[AssetScore], residual: float):
       # Distribute proportionally to all positions
       # Maintain relative position sizes
   ```

3. **Cash Bucket** (Ultra-Safe):
   ```python
   def _cash_bucket_allocation(self, assets: List[AssetScore], residual: float):
       # Create synthetic cash/treasury position
       # Prevent any concentration risk
   ```

**Safety Features:**
- **Concentration Prevention**: Max residual per asset limits
- **Over-Allocation Protection**: Cap residual to percentage of original position
- **Rollover Logic**: Unallocatable residual goes to cash bucket
- **Transparency**: Detailed logging of allocation decisions

**Data Models:**
```python
@dataclass
class ResidualAllocationResult:
    modified_assets: List[AssetScore]
    residual_allocated: float
    residual_remaining: float
    strategy_used: str
    allocation_actions: List[str]
    cash_bucket_amount: float = 0.0

@dataclass
class ResidualAllocationConfig:
    strategy: str = 'safe_top_slice'  # 'safe_top_slice', 'proportional', 'cash_bucket'
    max_residual_per_asset: float = 0.05
    max_residual_multiple: float = 0.5
    rollover_threshold: float = 0.01  # 1% threshold for cash bucket
```

#### **Testing Strategy**
- Residual allocation strategy correctness
- Safety cap enforcement
- Rollover logic validation
- Concentration prevention testing
- Strategy comparison and selection

### **Phase 4: Integration & Enhancement (Days 6-7)**

#### **Enhanced `SelectionService`**
```python
class SelectionService:
    def __init__(self, enable_dynamic_sizing=True, sizing_config=None):
        self.enable_dynamic_sizing = enable_dynamic_sizing
        self.sizing_config = sizing_config or DynamicSizingConfig()
        
        # Initialize sizing components
        self.position_sizer = DynamicPositionSizer(
            sizing_mode=self.sizing_config.sizing_mode,
            max_single_position=self.sizing_config.max_single_position,
            target_allocation=self.sizing_config.target_allocation
        )
        self.two_stage_sizer = TwoStagePositionSizer(
            max_single_position=self.sizing_config.max_single_position,
            target_allocation=self.sizing_config.target_allocation,
            residual_strategy=self.sizing_config.residual_strategy
        )
        self.residual_allocator = ResidualAllocationManager(
            max_residual_per_asset=self.sizing_config.max_residual_per_asset,
            max_residual_multiple=self.sizing_config.max_residual_multiple
        )
    
    def create_rebalancing_targets(self, selected_assets: List[AssetScore], 
                                 current_positions: Dict[str, float] = None,
                                 target_allocation: float = 0.95) -> List[RebalancingTarget]:
        """
        Enhanced target creation with dynamic sizing
        """
        if not self.enable_dynamic_sizing:
            # Fallback to original equal-weight behavior
            return self._create_equal_weight_targets(selected_assets, current_positions, target_allocation)
        
        # Apply dynamic two-stage sizing
        return self._create_dynamic_targets(selected_assets, current_positions)
```

#### **Enhanced `RebalancingLimits`**
```python
@dataclass
class RebalancingLimits:
    # Existing limits...
    max_total_positions: int = 10
    max_new_positions: int = 3
    min_score_threshold: float = 0.6
    
    # Bucket diversification (existing)
    enable_bucket_diversification: bool = False
    max_positions_per_bucket: int = 4
    max_allocation_per_bucket: float = 0.4
    min_buckets_represented: int = 2
    allow_bucket_overflow: bool = False
    
    # NEW: Dynamic sizing configuration
    enable_dynamic_sizing: bool = True
    sizing_mode: str = 'adaptive'  # 'adaptive', 'equal_weight', 'score_weighted'
    max_single_position: float = 0.15
    target_total_allocation: float = 0.95
    min_position_size: float = 0.02
    residual_strategy: str = 'safe_top_slice'
    max_residual_per_asset: float = 0.05
    max_residual_multiple: float = 0.5
```

#### **Enhanced `CoreRebalancerEngine`**
Integration point in the rebalancing flow:
```python
def rebalance(self, **kwargs) -> List[RebalancingTarget]:
    # Steps 1-4: Existing flow (universe, scoring, bucket diversification, selection)
    
    # Step 5: Create targets with dynamic sizing
    print(f"\n⚖️  Step 5: Creating Rebalancing Targets (Dynamic Sizing)")
    targets = self.selection_service.create_rebalancing_targets(
        selected_assets=selected_assets,
        current_positions=current_positions,
        target_allocation=limits.target_total_allocation
    )
```

#### **Integration Features**
- **Optional Enhancement**: Dynamic sizing enabled by default but configurable
- **Backward Compatibility**: Falls back to equal-weight when disabled
- **Configuration Flexibility**: All sizing parameters configurable
- **Mode Selection**: Easy switching between sizing strategies
- **Comprehensive Logging**: Detailed sizing decisions and residual allocation

#### **Testing Strategy**
- Integration with Core Rebalancer Engine
- Backward compatibility validation (equal-weight fallback)
- Multi-mode testing (adaptive, equal_weight, score_weighted)
- Bucket diversification + dynamic sizing interaction
- Configuration parameter validation
- End-to-end rebalancing with dynamic sizing

## 🧪 Comprehensive Testing Strategy

### **Unit Tests**
```
test_dynamic_position_sizer.py
├── test_adaptive_sizing()
├── test_equal_weight_sizing()
├── test_score_weighted_sizing()
├── test_portfolio_context_adaptation()
├── test_constraint_enforcement()
└── test_edge_cases()

test_two_stage_position_sizer.py
├── test_stage1_capping()
├── test_stage2_distribution()
├── test_residual_calculation()
├── test_multiple_capping_rounds()
├── test_allocation_accuracy()
└── test_edge_cases()

test_residual_allocation_manager.py
├── test_safe_top_slice_strategy()
├── test_proportional_strategy()
├── test_cash_bucket_strategy()
├── test_safety_caps()
├── test_rollover_logic()
└── test_concentration_prevention()
```

### **Integration Tests**
```
test_dynamic_sizing_integration.py
├── test_without_dynamic_sizing()
├── test_with_dynamic_sizing_adaptive()
├── test_with_dynamic_sizing_score_weighted()
├── test_bucket_diversification_integration()
├── test_residual_allocation_scenarios()
├── test_configuration_variations()
└── test_backward_compatibility()
```

### **Test Scenarios**
1. **Small Portfolio (3 positions)**
   - Target 95% allocation
   - Max 15% single position
   - Adaptive sizing with score differentiation

2. **Large Portfolio (10+ positions)**
   - Equal weight vs adaptive sizing comparison
   - Residual allocation testing
   - Multiple capping rounds

3. **High-Score Concentration**
   - Multiple assets with >90% scores
   - Two-stage capping effectiveness
   - Residual allocation with caps

4. **Bucket Diversification + Dynamic Sizing**
   - Combined constraint enforcement
   - Sizing within bucket limits
   - Priority preservation

## 📊 Expected Outcomes

### **Functional Outcomes**
- ✅ **Intelligent Sizing**: Position sizes reflect scores and portfolio context
- ✅ **Concentration Prevention**: No single position exceeds max_single_position
- ✅ **Allocation Efficiency**: Minimal cash drift through residual management
- ✅ **Mode Flexibility**: Support for adaptive, equal_weight, and score_weighted modes
- ✅ **Backward Compatibility**: System works unchanged when disabled

### **Technical Outcomes**
- ✅ **Two-Stage Safety**: Individual caps applied before normalization
- ✅ **Residual Management**: Intelligent allocation of leftover cash
- ✅ **Configuration Flexibility**: All sizing parameters configurable
- ✅ **Integration**: Seamless integration with existing Core Rebalancer Engine
- ✅ **Testing**: 100% test coverage with comprehensive scenarios

### **Business Outcomes**
- ✅ **Risk Management**: Prevents over-concentration in single positions
- ✅ **Performance Optimization**: Higher scoring assets get larger allocations
- ✅ **Capital Efficiency**: Minimizes cash drag through residual management
- ✅ **Flexibility**: Supports different investment strategies and risk profiles
- ✅ **Transparency**: Clear reasoning for all sizing decisions

## 🎛️ Configuration Examples

### **Adaptive Sizing (Default - Recommended)**
```python
limits = RebalancingLimits(
    enable_dynamic_sizing=True,
    sizing_mode='adaptive',
    max_single_position=0.15,
    target_total_allocation=0.95,
    residual_strategy='safe_top_slice'
)
```

### **Conservative Equal Weight**
```python
limits = RebalancingLimits(
    enable_dynamic_sizing=True,
    sizing_mode='equal_weight',
    max_single_position=0.12,  # Lower concentration
    target_total_allocation=0.90,  # More cash
    residual_strategy='cash_bucket'
)
```

### **Aggressive Score-Weighted**
```python
limits = RebalancingLimits(
    enable_dynamic_sizing=True,
    sizing_mode='score_weighted',
    max_single_position=0.20,  # Higher concentration allowed
    target_total_allocation=0.98,  # Minimal cash
    residual_strategy='safe_top_slice',
    max_residual_per_asset=0.08
)
```

### **Backward Compatibility Mode**
```python
limits = RebalancingLimits(
    enable_dynamic_sizing=False  # Fallback to original equal-weight
)
```

## 🔗 Integration Points

### **Input Dependencies**
- **Selected Assets**: Output from SelectionService with scores and priorities
- **Current Positions**: Portfolio context for sizing decisions
- **Bucket Constraints**: Integration with bucket diversification limits
- **Rebalancing Limits**: Configuration for sizing behavior

### **Output Integration**
- **Rebalancing Targets**: Enhanced targets with intelligent position sizes
- **Sizing Metadata**: Detailed information about sizing decisions
- **Residual Allocation**: Transparent reporting of cash management
- **JSON Output**: Enhanced metadata with sizing information

### **Backward Compatibility**
- **Default Enabled**: `enable_dynamic_sizing=True` by default for new value
- **Graceful Fallback**: Falls back to equal-weight when disabled
- **Configuration Migration**: Existing configurations work unchanged

## 📈 Success Metrics

### **Functional Metrics**
1. **Sizing Accuracy**: Position sizes correlate with scores and constraints
2. **Concentration Control**: 100% compliance with max_single_position limits
3. **Allocation Efficiency**: <1% cash drift through residual management
4. **Mode Differentiation**: Clear differences between sizing modes

### **Technical Metrics**
1. **Backward Compatibility**: 100% of existing configurations work
2. **Performance**: <50ms additional overhead for dynamic sizing
3. **Test Coverage**: 100% unit and integration test coverage
4. **Configuration Options**: 8+ new sizing configuration parameters

### **Integration Metrics**
1. **Bucket Compatibility**: Seamless integration with bucket diversification
2. **API Stability**: No breaking changes to existing interfaces
3. **Logging Quality**: Detailed sizing decisions and residual allocation
4. **Error Handling**: Graceful degradation for edge cases

## 🚀 Future Enhancements

### **Module 4+ Compatibility**
Dynamic sizing designed to work seamlessly with future modules:
- **Grace & Holding Period Management**: Size adjustments respect timing constraints
- **Core Asset Management**: High-alpha assets can get preferential sizing
- **Risk Management**: Volatility-adjusted position sizing
- **Regime Awareness**: Sizing mode selection based on market regime

### **Advanced Features (Future Modules)**
- **Volatility-Adjusted Sizing**: Position sizes inversely correlated with volatility
- **Correlation-Aware Sizing**: Reduce sizes for highly correlated positions
- **Risk Parity Sizing**: Equal risk contribution rather than equal dollar amounts
- **Kelly Criterion Sizing**: Optimal sizing based on expected returns and volatility

## 📋 Implementation Checklist

### **Phase 1: Dynamic Position Sizer Core** ⏳
- [ ] `DynamicPositionSizer` class implementation
- [ ] Adaptive sizing algorithm
- [ ] Equal weight sizing (backward compatibility)
- [ ] Score weighted sizing
- [ ] Portfolio context integration
- [ ] Constraint enforcement logic
- [ ] Unit tests and edge cases

### **Phase 2: Two-Stage Sizing Engine** ⏳
- [ ] `TwoStagePositionSizer` class implementation
- [ ] Stage 1: Individual position capping
- [ ] Stage 2: Remaining allocation distribution
- [ ] Multiple capping rounds handling
- [ ] Residual calculation accuracy
- [ ] Comprehensive unit tests

### **Phase 3: Residual Allocation Manager** ⏳
- [ ] `ResidualAllocationManager` class implementation
- [ ] Safe top slice strategy
- [ ] Proportional allocation strategy
- [ ] Cash bucket strategy
- [ ] Safety caps and concentration prevention
- [ ] Rollover logic and transparency

### **Phase 4: Integration & Enhancement** ⏳
- [ ] Enhanced `SelectionService` integration
- [ ] Enhanced `RebalancingLimits` data model
- [ ] `CoreRebalancerEngine` integration
- [ ] Backward compatibility preservation
- [ ] Configuration flexibility
- [ ] Integration tests and validation

### **Module 3 Completion** ⏳
- [ ] All components implemented and tested
- [ ] Integration validated with Core Rebalancer Engine
- [ ] Bucket diversification compatibility confirmed
- [ ] Backward compatibility verified
- [ ] Documentation and examples created
- [ ] Ready for Module 4 development

---

**Module 3 Status: PLANNED** ⏳  
**Next Module: Grace & Holding Period Management** 🚀  
**System Status: Ready for Advanced Sizing** ✅ 