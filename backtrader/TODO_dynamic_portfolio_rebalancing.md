# Dynamic Portfolio Rebalancing Enhancement TODO

**Priority: CRITICAL**  
**Status: Planning**  
**Estimated Effort: High**  
**Functionality Name: Dynamic Portfolio Rebalancing**

## 🚨 Critical Issues Identified

### Current Bug (FIXED)
The trending confidence filter excludes existing positions from re-evaluation during rebalancing, causing:
- **Zombie Positions**: Existing positions that don't meet trending confidence get auto-closed without proper scoring
- **Missing Re-evaluation**: Current positions bypassed if they fall below trending threshold
- **Forced Closures**: Positions closed with reason "Asset no longer in selection" instead of score-based decisions

### Professional Hedge Fund Manager Feedback (NEW ISSUES)

#### 1. **Zombie Position "Closure" vs. Review**
**Issue**: Low-score legacy positions still get automatic exits, just with better scoring. Creates whipsaw trading.
**Risk**: Frequent churning of positions around the threshold, high transaction costs, missing rebounds.

#### 2. **Min/Max Holding Periods vs. Dynamic Sizing Frequency** 
**Issue**: `min_holding_period=3` days with daily rebalancing creates "phantom" undersized adjustments.
**Risk**: Attempting to adjust positions that shouldn't be touched, inconsistent position management.

#### 3. **Dynamic Sizer "Normalization" Ambiguity**
**Issue**: `_normalize_allocations()` could override `max_single_position_size` caps indirectly.
**Risk**: Positions growing beyond intended limits through normalization scaling.

#### 4. **Forced Diversification vs. Score Meritocracy**
**Issue**: Strict bucket limits might force rejection of very high-alpha assets (score > 0.95).
**Risk**: Missing exceptional opportunities for the sake of mechanical diversification rules.

### Current Problematic Flow
```python
# 1. Get trending assets (filtered by confidence)
trending_assets = get_trending_assets(min_confidence=0.7)  # ❌ May exclude current positions

# 2. Score ONLY trending assets
position_scores = analyze_and_score_assets(trending_assets)  # ❌ Missing current positions

# 3. Close positions not in trending assets
if asset not in new_scores_dict:
    close_position(reason='Asset no longer in selection')  # ❌ Auto-close without scoring
```

## 🎯 Objectives

### 1. **Portfolio Priority System (ENHANCED)**
- Current positions ALWAYS get re-evaluated regardless of trending confidence
- **Grace Period Management**: Positions below threshold get grace period with size decay vs immediate closure
- **Holding Period Awareness**: Position adjustments respect min/max holding periods
- Separate limits for new positions vs portfolio management
- Dynamic behavior based on market conditions and regime changes

### 2. **Flexible Position Limits & Intelligent Sizing**
- `max_new_positions`: Limit on new positions to open
- `max_total_positions`: Overall portfolio size limit
- `regime_change_multiplier`: Aggressive rebalancing during regime shifts
- **Two-Stage Dynamic Sizing**: Cap individual positions FIRST, then normalize remainder
- **Holding Period Synchronization**: Align sizing adjustments with holding period constraints
- **Target Portfolio Allocation**: Automatically scale positions to fit desired portfolio size

### 3. **Enhanced Asset Selection & Smart Diversification**
- **Portfolio Assets**: Always included (current positions)
- **Trending Assets**: Filtered by confidence for new opportunities
- **Combined Universe**: Merge both for comprehensive analysis
- **Bucket Diversification with Override**: Ensure distribution but allow high-alpha asset exceptions
- **Concentration Limits**: Prevent over-allocation to any single bucket or sector
- **Score-Based Diversification Bypass**: Ultra-high scoring assets can override bucket limits

## 🎛️ Complete Parameter Configurability

### **All Parameters Must Be CLI Configurable**
Every aspect of the strategy behavior should be configurable for backtesting optimization:

#### **Portfolio Management Parameters**
```bash
--max-new-positions 3                    # Max new positions per rebalance
--max-total-positions 10                 # Overall portfolio size limit  
--max-positions-per-bucket 4             # Max positions from any single bucket
--min-buckets-represented 2              # Minimum buckets that must be represented
--max-bucket-allocation 0.4              # Max % of portfolio in any bucket (40%)
--regime-change-aggression 2.0           # Position limit multiplier during regime changes
--portfolio-concentration-limit 0.7      # Force diversification threshold
```

#### **Position Sizing Parameters**
```bash
--base-position-size 0.1                 # Base position size (10% of portfolio)
--position-size-scaling dynamic          # dynamic|fixed - how to scale positions
--max-single-position-size 0.2           # Maximum size for any single position (20%)
--min-position-size 0.02                 # Minimum viable position size (2%)
--size-adjustment-factor 0.8             # Factor to adjust sizes when opening more positions
```

#### **Scoring & Selection Parameters**
```bash
--min-score-threshold 0.6                # Minimum score to maintain position
--min-score-new-position 0.65            # Higher threshold for new positions
--score-decay-factor 0.95                # Daily decay for aging positions
--trending-confidence-new 0.7            # Trending confidence for new positions
--trending-confidence-existing 0.0       # Trending confidence for existing (always evaluate)
```

#### **Diversification Parameters**
```bash
--diversification-mode strict            # strict|balanced|aggressive
--max-bucket-allocation 0.4              # Max allocation per bucket (40%)
--min-buckets-represented 2              # Minimum buckets that must be represented
--correlation-limit 0.8                  # Max correlation between positions within bucket
--correlation-window 60                  # Days for correlation calculation
--force-bucket-distribution true         # Force distribution across buckets
--bucket-balance-tolerance 0.2           # Tolerance for bucket imbalance
```

#### **Risk Management Parameters**
```bash
--position-holding-period-min 3          # Min days to hold before considering closure
--position-holding-period-max 90         # Max days before forced review
--volatility-position-scaling true       # Scale positions based on volatility
--drawdown-position-reduction 0.8        # Reduce sizes during portfolio drawdown
--grace-period-days 5                    # Days to decay position before forced closure
--grace-period-decay-rate 0.8            # Daily decay rate during grace period
--bucket-override-threshold 0.95         # Score threshold to bypass bucket limits
--whipsaw-protection true                # Prevent rapid position cycling
```

## 🎯 Bucket Diversification Strategy

### **Current Problem: Bucket Concentration Risk**
Without diversification controls, all top-scoring assets might come from one bucket:
```python
# Problem: All positions from "Risk Assets" bucket
portfolio = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN"]  # All tech/risk assets
# Missing: Defensives, International, Commodities, etc.
```

### **Proposed Solution: Multi-Layered Diversification**

#### **1. Bucket-Level Diversification**
```python
class BucketDiversificationManager:
    def __init__(self, max_per_bucket=4, min_buckets=2, max_bucket_allocation=0.4):
        self.max_positions_per_bucket = max_per_bucket
        self.min_buckets_represented = min_buckets  
        self.max_bucket_allocation = max_bucket_allocation
    
    def enforce_bucket_limits(self, scored_assets: List[PositionScore], 
                            current_buckets: Dict[str, List[str]]) -> List[PositionScore]:
        """
        Enforce bucket diversification constraints
        """
        selected = []
        bucket_counts = defaultdict(int)
        bucket_allocations = defaultdict(float)
        
        # Sort by score but select with bucket constraints
        for asset_score in sorted(scored_assets, key=lambda x: x.combined_score, reverse=True):
            asset_bucket = self._get_asset_bucket(asset_score.asset)
            
            # Check bucket constraints
            if (bucket_counts[asset_bucket] < self.max_positions_per_bucket and
                bucket_allocations[asset_bucket] + asset_score.position_size_percentage <= self.max_bucket_allocation):
                
                selected.append(asset_score)
                bucket_counts[asset_bucket] += 1
                bucket_allocations[asset_bucket] += asset_score.position_size_percentage
        
        # Ensure minimum bucket representation
        self._ensure_min_bucket_representation(selected, scored_assets, bucket_counts)
        
        return selected
```

#### **2. Intelligent Bucket Selection**
```python
def select_diversified_portfolio(self, scores: PrioritizedScores, 
                               limits: RebalancingLimits) -> DiversifiedSelection:
    """
    Select portfolio with bucket diversification constraints
    """
    
    # Step 1: Group assets by bucket
    bucket_groups = self._group_assets_by_bucket(scores.all_scores)
    
    # Step 2: Allocate positions across buckets
    bucket_allocations = self._calculate_bucket_allocations(
        bucket_groups, limits.max_total_positions
    )
    
    # Step 3: Select best assets from each bucket within allocation
    selected_positions = []
    for bucket, allocation in bucket_allocations.items():
        bucket_assets = bucket_groups[bucket]
        bucket_best = sorted(bucket_assets, key=lambda x: x.combined_score, reverse=True)
        selected_positions.extend(bucket_best[:allocation.max_positions])
    
    return DiversifiedSelection(
        selected_positions=selected_positions,
        bucket_distribution=bucket_allocations,
        diversification_score=self._calculate_diversification_score(selected_positions)
    )
```

#### **3. Dynamic Bucket Allocation**
```python
def calculate_bucket_allocations(self, available_buckets: List[str], 
                               total_positions: int, 
                               regime: str) -> Dict[str, BucketAllocation]:
    """
    Dynamically allocate positions across buckets based on regime and constraints
    """
    
    # Base allocation: Equal distribution
    base_allocation = total_positions // len(available_buckets)
    remainder = total_positions % len(available_buckets)
    
    allocations = {}
    for bucket in available_buckets:
        # Base equal allocation
        allocation = base_allocation
        
        # Regime-based bias
        if self._is_regime_favored_bucket(bucket, regime):
            allocation += 1  # Give extra slot to regime-favored buckets
        
        # Apply constraints
        allocation = min(allocation, self.max_positions_per_bucket)
        allocation = max(allocation, 1 if len(available_buckets) <= total_positions else 0)
        
        allocations[bucket] = BucketAllocation(
            max_positions=allocation,
            max_weight=self.max_bucket_allocation,
            priority=self._get_bucket_priority(bucket, regime)
        )
    
    return allocations
```

## ⚖️ Dynamic Position Sizing Strategy

### **Current Problem: Fixed Sizing in Variable Portfolios**
Current deterministic sizing doesn't adapt to portfolio size:
```python
# Current: Fixed categories regardless of portfolio size
if combined_score >= 0.9:
    return PositionSizeCategory.MAX, 0.2      # 20% always
elif combined_score >= 0.8:
    return PositionSizeCategory.STANDARD, 0.15  # 15% always
# Problem: With 8 positions, we'd need 8 × 15% = 120% allocation!
```

### **Proposed Solution: Adaptive Position Sizing**

#### **1. Dynamic Size Calculator**
```python
class DynamicPositionSizer:
    def __init__(self, base_position_size=0.1, max_single_size=0.2, 
                 sizing_mode='adaptive'):
        self.base_position_size = base_position_size
        self.max_single_position_size = max_single_size
        self.sizing_mode = sizing_mode
    
    def calculate_position_sizes(self, scored_positions: List[PositionScore], 
                               target_total_allocation=0.95) -> List[PositionScore]:
        """
        Calculate adaptive position sizes based on portfolio composition
        """
        
        if self.sizing_mode == 'adaptive':
            return self._adaptive_sizing(scored_positions, target_total_allocation)
        elif self.sizing_mode == 'equal_weight':
            return self._equal_weight_sizing(scored_positions, target_total_allocation)
        elif self.sizing_mode == 'score_weighted':
            return self._score_weighted_sizing(scored_positions, target_total_allocation)
        else:
            return self._fixed_category_sizing(scored_positions)
    
    def _adaptive_sizing(self, positions: List[PositionScore], 
                        target_allocation: float) -> List[PositionScore]:
        """
        Adaptive sizing based on number of positions and scores
        """
        n_positions = len(positions)
        
        # Calculate base size per position
        base_size_per_position = target_allocation / n_positions
        
        # Adjust based on scores (higher scores get larger allocations)
        total_score = sum(pos.combined_score for pos in positions)
        
        for position in positions:
            # Score-weighted allocation
            score_weight = position.combined_score / total_score
            raw_size = base_size_per_position * (1 + score_weight)
            
            # Apply constraints
            position.position_size_percentage = min(
                raw_size, 
                self.max_single_position_size
            )
        
        # Normalize to target allocation
        self._normalize_allocations(positions, target_allocation)
        
        return positions
```

#### **2. Portfolio-Aware Sizing**
```python
def determine_dynamic_position_size(self, combined_score: float, 
                                  portfolio_context: PortfolioContext) -> Tuple[PositionSizeCategory, float]:
    """
    Determine position size based on score AND portfolio context
    """
    
    # Base size calculation
    base_size = portfolio_context.target_allocation / portfolio_context.target_positions
    
    # Score multiplier
    if combined_score >= 0.9:
        multiplier = 1.5  # 50% larger than base
        category = PositionSizeCategory.MAX
    elif combined_score >= 0.8:
        multiplier = 1.2  # 20% larger than base
        category = PositionSizeCategory.STANDARD
    elif combined_score >= 0.7:
        multiplier = 1.0  # Base size
        category = PositionSizeCategory.HALF
    elif combined_score >= 0.6:
        multiplier = 0.8  # 20% smaller than base
        category = PositionSizeCategory.LIGHT
    else:
        multiplier = 0.0
        category = PositionSizeCategory.NO_POSITION
    
    # Calculate final size
    raw_size = base_size * multiplier
    
    # Apply constraints
    final_size = min(raw_size, self.max_single_position_size)
    final_size = max(final_size, self.min_position_size if multiplier > 0 else 0)
    
    return category, final_size
```

#### **3. Allocation Overflow Handling**
```python
def handle_allocation_overflow(self, positions: List[PositionScore], 
                              max_allocation: float = 0.95) -> List[PositionScore]:
    """
    Handle cases where total allocation exceeds maximum
    """
    total_allocation = sum(pos.position_size_percentage for pos in positions)
    
    if total_allocation > max_allocation:
        # Strategy 1: Proportional scaling
        scale_factor = max_allocation / total_allocation
        for pos in positions:
            pos.position_size_percentage *= scale_factor
    
         return positions
```

## 🛡️ Professional Risk Mitigation Solutions

### **Solution 1: Grace Period with Size Decay**
```python
class GracePeriodManager:
    def __init__(self, grace_period_days=5, decay_rate=0.8):
        self.grace_period_days = grace_period_days
        self.decay_rate = decay_rate
        self.grace_positions: Dict[str, GracePosition] = {}
    
    def handle_underperforming_position(self, asset: str, current_score: float, 
                                      current_size: float, min_threshold: float) -> PositionAction:
        """
        Handle positions that fall below threshold with grace period
        """
        if current_score < min_threshold:
            if asset not in self.grace_positions:
                # Start grace period
                self.grace_positions[asset] = GracePosition(
                    asset=asset,
                    start_date=datetime.now(),
                    original_size=current_size,
                    current_size=current_size,
                    original_score=current_score
                )
                return PositionAction(action='grace_start', reason='Score below threshold, starting grace period')
            else:
                # Continue grace period with decay
                grace_pos = self.grace_positions[asset]
                days_in_grace = (datetime.now() - grace_pos.start_date).days
                
                if days_in_grace >= self.grace_period_days:
                    # Grace period expired, force close
                    del self.grace_positions[asset]
                    return PositionAction(action='force_close', reason=f'Grace period expired after {days_in_grace} days')
                else:
                    # Apply decay
                    decay_factor = self.decay_rate ** days_in_grace
                    new_size = grace_pos.original_size * decay_factor
                    grace_pos.current_size = new_size
                    
                    return PositionAction(
                        action='decay_size', 
                        new_size=new_size,
                        reason=f'Grace period day {days_in_grace}, size decaying to {new_size:.3f}'
                    )
        else:
            # Score recovered, remove from grace period
            if asset in self.grace_positions:
                del self.grace_positions[asset]
                return PositionAction(action='grace_recovery', reason='Score recovered above threshold')
        
        return PositionAction(action='hold', reason='Normal scoring')
```

### **Solution 2: Holding Period Synchronization**
```python
class HoldingPeriodManager:
    def __init__(self, min_holding_days=3, max_holding_days=90):
        self.min_holding_days = min_holding_days
        self.max_holding_days = max_holding_days
        self.position_ages: Dict[str, datetime] = {}
    
    def can_adjust_position(self, asset: str, current_date: datetime) -> Tuple[bool, str]:
        """
        Check if position can be adjusted based on holding period
        """
        if asset not in self.position_ages:
            return True, "New position, can adjust"
        
        entry_date = self.position_ages[asset]
        days_held = (current_date - entry_date).days
        
        if days_held < self.min_holding_days:
            return False, f"Min holding period not met: {days_held}/{self.min_holding_days} days"
        
        if days_held >= self.max_holding_days:
            return True, f"Max holding period reached: {days_held} days, forced review"
        
        return True, f"Within holding period: {days_held} days"
    
    def get_eligible_positions_for_adjustment(self, portfolio_assets: List[str], 
                                            current_date: datetime) -> List[str]:
        """
        Get list of positions that can be adjusted today
        """
        eligible = []
        for asset in portfolio_assets:
            can_adjust, reason = self.can_adjust_position(asset, current_date)
            if can_adjust:
                eligible.append(asset)
        
        return eligible
```

### **Solution 3: Two-Stage Position Sizing**
```python
class TwoStagePositionSizer:
    def __init__(self, max_single_size=0.2, target_allocation=0.95):
        self.max_single_position_size = max_single_size
        self.target_total_allocation = target_allocation
    
    def calculate_safe_position_sizes(self, scored_positions: List[PositionScore]) -> List[PositionScore]:
        """
        Two-stage sizing: Cap first, then normalize remainder
        """
        # STAGE 1: Cap individual positions at max_single_size
        total_capped_allocation = 0.0
        capped_positions = []
        uncapped_positions = []
        
        for position in scored_positions:
            raw_size = self._calculate_raw_size(position)
            
            if raw_size > self.max_single_position_size:
                # Cap this position
                position.position_size_percentage = self.max_single_position_size
                position.is_capped = True
                total_capped_allocation += self.max_single_position_size
                capped_positions.append(position)
            else:
                # This position can grow
                position.position_size_percentage = raw_size
                position.is_capped = False
                uncapped_positions.append(position)
        
        # STAGE 2: Distribute remaining allocation among uncapped positions
        remaining_allocation = max(0, self.target_total_allocation - total_capped_allocation)
        
        if uncapped_positions and remaining_allocation > 0:
            # Calculate total uncapped allocation
            total_uncapped = sum(pos.position_size_percentage for pos in uncapped_positions)
            
            if total_uncapped > 0:
                # Scale uncapped positions to fill remaining allocation
                scale_factor = remaining_allocation / total_uncapped
                
                for position in uncapped_positions:
                    position.position_size_percentage *= scale_factor
                    # Re-check cap after scaling
                    if position.position_size_percentage > self.max_single_position_size:
                        position.position_size_percentage = self.max_single_position_size
                        position.is_capped = True
        
        return scored_positions
```

### **Solution 4: High-Alpha Bucket Override**
```python
class SmartDiversificationManager:
    def __init__(self, bucket_override_threshold=0.95, max_overrides=2):
        self.bucket_override_threshold = bucket_override_threshold
        self.max_overrides_per_rebalance = max_overrides
    
    def apply_diversification_with_override(self, scored_assets: List[PositionScore], 
                                          bucket_limits: Dict[str, int]) -> List[PositionScore]:
        """
        Apply bucket diversification but allow high-alpha overrides
        """
        selected = []
        bucket_counts = defaultdict(int)
        override_count = 0
        
        # Sort by score (highest first)
        sorted_assets = sorted(scored_assets, key=lambda x: x.combined_score, reverse=True)
        
        for asset_score in sorted_assets:
            asset_bucket = self._get_asset_bucket(asset_score.asset)
            bucket_limit = bucket_limits.get(asset_bucket, 999)
            
            # Check if we can add this asset
            can_add_normal = bucket_counts[asset_bucket] < bucket_limit
            
            # Check for override eligibility
            can_override = (
                asset_score.combined_score >= self.bucket_override_threshold and
                override_count < self.max_overrides_per_rebalance and
                not can_add_normal  # Only override when normal rules prevent selection
            )
            
            if can_add_normal:
                # Normal selection
                selected.append(asset_score)
                bucket_counts[asset_bucket] += 1
                asset_score.selection_reason = f"Normal selection (bucket {asset_bucket})"
                
            elif can_override:
                # Override bucket limits for exceptional asset
                selected.append(asset_score)
                bucket_counts[asset_bucket] += 1  # Still count towards bucket
                override_count += 1
                asset_score.selection_reason = f"BUCKET OVERRIDE: Score {asset_score.combined_score:.3f} > {self.bucket_override_threshold}"
                asset_score.is_bucket_override = True
                
            else:
                # Rejected by bucket limits
                asset_score.selection_reason = f"Rejected: Bucket {asset_bucket} limit ({bucket_limit}) reached"
        
                 return selected
```

## 🏗️ Simplified Bucket-Based Diversification System

### **Design Approach: Buckets Handle Everything**

Since we don't have financial data APIs for sector classification, we'll use **buckets as our primary diversification mechanism**. This is much cleaner and more practical.

**Buckets serve dual purposes:**
1. **Strategic/Regime allocation** (Risk Assets, Defensives, International)
2. **Diversification constraints** (position limits, allocation limits, correlation management)

### **Bucket-Only Diversification System**

#### **1. Enhanced Bucket Diversification Manager**
```python
class BucketDiversificationManager:
    def __init__(self, max_per_bucket=4, min_buckets=2, max_bucket_allocation=0.4):
        self.max_positions_per_bucket = max_per_bucket
        self.min_buckets_represented = min_buckets  
        self.max_bucket_allocation = max_bucket_allocation
        self.correlation_limit = 0.8
        self.correlation_window = 60
        
    def apply_bucket_diversification(self, scored_assets: List[PositionScore], 
                                   current_date: datetime) -> List[PositionScore]:
        """
        Apply all diversification constraints using buckets only
        """
        
        # Step 1: Group assets by bucket
        bucket_groups = self._group_assets_by_bucket(scored_assets)
        
        # Step 2: Apply position limits per bucket
        position_limited = self._apply_position_limits(bucket_groups)
        
        # Step 3: Apply allocation limits per bucket
        allocation_limited = self._apply_allocation_limits(position_limited)
        
        # Step 4: Apply correlation limits within buckets
        correlation_filtered = self._apply_correlation_limits(allocation_limited, current_date)
        
        # Step 5: Ensure minimum bucket representation
        final_portfolio = self._ensure_min_bucket_representation(correlation_filtered, bucket_groups)
        
        return final_portfolio
    
    def _group_assets_by_bucket(self, scored_assets: List[PositionScore]) -> Dict[str, List[PositionScore]]:
        """
        Group assets by their bucket classification
        """
        bucket_groups = defaultdict(list)
        
        for asset_score in scored_assets:
            # Get asset bucket from asset manager
            asset_bucket = self._get_asset_bucket(asset_score.asset)
            bucket_groups[asset_bucket].append(asset_score)
        
        # Sort each bucket by score (highest first)
        for bucket in bucket_groups:
            bucket_groups[bucket].sort(key=lambda x: x.combined_score, reverse=True)
        
        return bucket_groups
    
    def _apply_position_limits(self, bucket_groups: Dict[str, List[PositionScore]]) -> List[PositionScore]:
        """
        Apply max_positions_per_bucket constraint
        """
        selected = []
        
        for bucket, assets in bucket_groups.items():
            # Take top N assets from this bucket
            bucket_selected = assets[:self.max_positions_per_bucket]
            selected.extend(bucket_selected)
            
            print(f"Bucket {bucket}: Selected {len(bucket_selected)}/{len(assets)} assets")
        
        return selected
    
    def _apply_allocation_limits(self, assets: List[PositionScore]) -> List[PositionScore]:
        """
        Apply max_bucket_allocation constraint
        """
        # Calculate current bucket allocations
        bucket_allocations = defaultdict(float)
        
        for asset in assets:
            bucket = self._get_asset_bucket(asset.asset)
            bucket_allocations[bucket] += asset.position_size_percentage
        
        # Scale down over-allocated buckets
        for asset in assets:
            bucket = self._get_asset_bucket(asset.asset)
            current_allocation = bucket_allocations[bucket]
            
            if current_allocation > self.max_bucket_allocation:
                # Scale down proportionally
                scale_factor = self.max_bucket_allocation / current_allocation
                asset.position_size_percentage *= scale_factor
                asset.bucket_scaled = True
                asset.scale_factor = scale_factor
                
        return assets
    
    def _apply_correlation_limits(self, assets: List[PositionScore], 
                                current_date: datetime) -> List[PositionScore]:
        """
        Apply correlation limits within each bucket
        """
        # Group by bucket again (after previous filtering)
        bucket_groups = self._group_assets_by_bucket(assets)
        final_assets = []
        
        for bucket, bucket_assets in bucket_groups.items():
            # Apply correlation filtering within this bucket
            filtered_bucket = self._filter_bucket_correlations(bucket_assets, current_date)
            final_assets.extend(filtered_bucket)
        
        return final_assets
    
    def _filter_bucket_correlations(self, bucket_assets: List[PositionScore], 
                                  current_date: datetime) -> List[PositionScore]:
        """
        Remove highly correlated assets within a bucket
        """
        if len(bucket_assets) <= 1:
            return bucket_assets
        
        selected = [bucket_assets[0]]  # Start with highest scoring asset
        
        for candidate in bucket_assets[1:]:
            # Check correlation with already selected assets
            max_correlation = 0.0
            
            for selected_asset in selected:
                correlation = self._calculate_correlation(
                    candidate.asset, selected_asset.asset, current_date
                )
                max_correlation = max(max_correlation, abs(correlation))
            
            # Add if correlation is below limit
            if max_correlation < self.correlation_limit:
                selected.append(candidate)
                candidate.correlation_reason = f"Max correlation: {max_correlation:.2f}"
            else:
                candidate.correlation_reason = f"Rejected: correlation {max_correlation:.2f} > {self.correlation_limit}"
        
        return selected
    
    def _calculate_correlation(self, asset1: str, asset2: str, current_date: datetime) -> float:
        """
        Calculate correlation between two assets using available price data
        """
        try:
            # Get price data for both assets (use data manager)
            end_date = current_date
            start_date = current_date - timedelta(days=self.correlation_window)
            
            data1 = self._get_price_data(asset1, start_date, end_date)
            data2 = self._get_price_data(asset2, start_date, end_date)
            
            if data1 is None or data2 is None or len(data1) < 30 or len(data2) < 30:
                return 0.0  # Not enough data
            
            # Calculate returns
            returns1 = data1['Close'].pct_change().dropna()
            returns2 = data2['Close'].pct_change().dropna()
            
            # Align dates and calculate correlation
            common_dates = returns1.index.intersection(returns2.index)
            if len(common_dates) < 20:
                return 0.0
            
            aligned_returns1 = returns1.loc[common_dates]
            aligned_returns2 = returns2.loc[common_dates]
            
            correlation = aligned_returns1.corr(aligned_returns2)
            return correlation if not pd.isna(correlation) else 0.0
            
        except Exception as e:
            print(f"Correlation calculation failed for {asset1}-{asset2}: {e}")
            return 0.0
    
    def _ensure_min_bucket_representation(self, assets: List[PositionScore], 
                                        original_bucket_groups: Dict[str, List[PositionScore]]) -> List[PositionScore]:
        """
        Ensure minimum number of buckets are represented
        """
        current_buckets = set(self._get_asset_bucket(asset.asset) for asset in assets)
        
        if len(current_buckets) >= self.min_buckets_represented:
            return assets
        
        # Need to add assets from underrepresented buckets
        needed_buckets = self.min_buckets_represented - len(current_buckets)
        
        # Find buckets not currently represented
        all_buckets = set(original_bucket_groups.keys())
        missing_buckets = all_buckets - current_buckets
        
        # Add top asset from missing buckets
        for bucket in list(missing_buckets)[:needed_buckets]:
            if bucket in original_bucket_groups and original_bucket_groups[bucket]:
                top_asset = original_bucket_groups[bucket][0]
                top_asset.forced_for_diversification = True
                assets.append(top_asset)
        
        return assets
```

#### **2. Simplified Asset Manager Integration**
```python
class EnhancedAssetBucketManager:
    def __init__(self):
        self.bucket_mappings = self._load_bucket_mappings()
    
    def get_asset_bucket(self, asset: str) -> str:
        """
        Get bucket for an asset using existing asset bucket mappings
        """
        # Use existing bucket mappings from asset_buckets.py
        for bucket_name, assets in self.bucket_mappings.items():
            if asset in assets:
                return bucket_name
        
        return 'Unknown'  # Fallback for unmapped assets
    
    def get_bucket_statistics(self, portfolio: List[PositionScore]) -> Dict:
        """
        Get comprehensive bucket statistics for portfolio
        """
        bucket_stats = defaultdict(lambda: {
            'count': 0, 
            'allocation': 0.0, 
            'assets': [], 
            'avg_score': 0.0
        })
        
        for position in portfolio:
            bucket = self.get_asset_bucket(position.asset)
            bucket_stats[bucket]['count'] += 1
            bucket_stats[bucket]['allocation'] += position.position_size_percentage
            bucket_stats[bucket]['assets'].append(position.asset)
            bucket_stats[bucket]['avg_score'] += position.combined_score
        
        # Calculate averages
        for bucket in bucket_stats:
            if bucket_stats[bucket]['count'] > 0:
                bucket_stats[bucket]['avg_score'] /= bucket_stats[bucket]['count']
        
        return dict(bucket_stats)
```

### **Simplified Configuration**

#### **Bucket-Only Parameters:**
```bash
# Portfolio Management
--max-positions-per-bucket 4          # Max positions from any single bucket  
--max-bucket-allocation 0.4           # Max 40% allocation to any bucket
--min-buckets-represented 2           # Must have assets from at least 2 buckets

# Correlation Management (within buckets)
--correlation-limit 0.8               # Max correlation between assets in same bucket
--correlation-window 60               # Days for correlation calculation

# Diversification Mode
--diversification-mode balanced       # strict|balanced|aggressive
--force-bucket-distribution           # Force distribution across buckets
--bucket-balance-tolerance 0.2        # Tolerance for bucket imbalance
```

#### **Real-World Example:**
```python
# Goldilocks regime → "Risk Assets" bucket favored
available_assets = {
    'Risk Assets': ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL', 'META'],
    'Defensive Assets': ['JNJ', 'PG', 'KO', 'WMT'],
    'International': ['EFA', 'EEM', 'VGK']
}

# Step 1: Position limits (max 4 per bucket)
position_limited = {
    'Risk Assets': ['AAPL', 'MSFT', 'NVDA', 'TSLA'],  # Top 4 by score
    'Defensive Assets': ['JNJ', 'PG'],                 # Top 2 by score  
    'International': ['EFA']                           # Top 1 by score
}

# Step 2: Allocation limits (max 40% per bucket)
# Risk Assets: 4 assets × 10% = 40% (at limit)
# Defensive: 2 assets × 10% = 20% (OK)
# International: 1 asset × 10% = 10% (OK)

# Step 3: Correlation filtering (within Risk Assets bucket)
correlations = {
    ('AAPL', 'MSFT'): 0.65,  # OK
    ('AAPL', 'NVDA'): 0.72,  # OK  
    ('AAPL', 'TSLA'): 0.83   # Too high! Remove TSLA
}

final_portfolio = ['AAPL', 'MSFT', 'NVDA', 'JNJ', 'PG', 'EFA']
```

This **simplified bucket-only approach** is much more practical and maintainable while still providing robust diversification control!

## 🔧 **Advanced Risk Management: Edge Case Solutions**

### **Critical Issue Resolution from Professional Review**

The following section addresses sophisticated edge cases and logical inconsistencies identified through institutional-level review:

#### **Issue 1: Grace-Period vs. Override Logic Clash**

**Problem**: High-alpha assets (>0.95 score) with bucket overrides could still enter grace period logic if their score dips temporarily, creating a contradiction.

**Solution**: Implement "Core Asset" immunity system:

```python
class CoreAssetManager:
    def __init__(self, core_expiry_days=90, underperformance_threshold=0.15, 
                 underperformance_period=30):
        self.core_assets = {}  # asset -> CoreAssetInfo
        self.core_expiry_days = core_expiry_days
        self.underperformance_threshold = underperformance_threshold
        self.underperformance_period = underperformance_period
    
    def mark_as_core(self, asset: str, current_date: datetime, 
                    reason: str = "High-alpha bucket override"):
        """
        Mark asset as core with lifecycle tracking
        """
        core_info = CoreAssetInfo(
            asset=asset,
            designation_date=current_date,
            expiry_date=current_date + timedelta(days=self.core_expiry_days),
            reason=reason,
            bucket=self._get_asset_bucket(asset)
        )
        
        self.core_assets[asset] = core_info
        print(f"Asset {asset} marked as CORE: {reason} (expires: {core_info.expiry_date.strftime('%Y-%m-%d')})")
    
    def is_core_asset(self, asset: str, current_date: datetime = None) -> bool:
        """
        Check if asset is currently core (with lifecycle checks)
        """
        if asset not in self.core_assets:
            return False
        
        if current_date:
            # Check for automatic expiry or underperformance
            if self._should_auto_revoke(asset, current_date):
                self._auto_revoke_core_status(asset, current_date)
                return False
        
        return True
    
    def _should_auto_revoke(self, asset: str, current_date: datetime) -> bool:
        """
        Check if core status should be automatically revoked
        """
        core_info = self.core_assets[asset]
        
        # Check expiry date
        if current_date > core_info.expiry_date:
            return True
        
        # Check underperformance vs bucket
        if self._check_underperformance(asset, current_date):
            return True
        
        return False
    
    def _check_underperformance(self, asset: str, current_date: datetime) -> bool:
        """
        Check if core asset is underperforming its bucket significantly
        """
        try:
            core_info = self.core_assets[asset]
            
            # Get asset performance over underperformance_period
            start_date = current_date - timedelta(days=self.underperformance_period)
            asset_return = self._calculate_return(asset, start_date, current_date)
            
            # Get bucket average performance
            bucket_assets = self._get_bucket_assets(core_info.bucket)
            bucket_returns = []
            
            for bucket_asset in bucket_assets:
                if bucket_asset != asset:  # Exclude the core asset itself
                    try:
                        bucket_asset_return = self._calculate_return(bucket_asset, start_date, current_date)
                        if bucket_asset_return is not None:
                            bucket_returns.append(bucket_asset_return)
                    except:
                        continue
            
            if not bucket_returns:
                return False  # Can't compare if no bucket data
            
            bucket_avg_return = sum(bucket_returns) / len(bucket_returns)
            underperformance = bucket_avg_return - asset_return
            
            return underperformance > self.underperformance_threshold
            
        except Exception as e:
            print(f"Error checking underperformance for {asset}: {e}")
            return False
    
    def _auto_revoke_core_status(self, asset: str, current_date: datetime):
        """
        Automatically revoke core status with detailed logging
        """
        core_info = self.core_assets[asset]
        
        if current_date > core_info.expiry_date:
            reason = f"Automatic expiry after {self.core_expiry_days} days"
        else:
            reason = f"Underperformed bucket by >{self.underperformance_threshold:.1%} over {self.underperformance_period} days"
        
        print(f"AUTO-REVOKED core status for {asset}: {reason}")
        del self.core_assets[asset]
    
    def revoke_core_status(self, asset: str, reason: str = "Manual revocation"):
        """
        Manually revoke core status (conscious decision)
        """
        if asset in self.core_assets:
            del self.core_assets[asset]
            print(f"MANUALLY REVOKED core status for {asset}: {reason}")
    
    def extend_core_status(self, asset: str, additional_days: int, 
                          current_date: datetime, reason: str = "Manual extension"):
        """
        Extend core status expiry date
        """
        if asset in self.core_assets:
            old_expiry = self.core_assets[asset].expiry_date
            new_expiry = current_date + timedelta(days=additional_days)
            self.core_assets[asset].expiry_date = new_expiry
            print(f"Extended core status for {asset}: {old_expiry} -> {new_expiry} ({reason})")
    
    def should_exempt_from_grace(self, asset: str, current_date: datetime) -> bool:
        """
        Check if asset should be exempt from grace periods (with lifecycle)
        """
        return self.is_core_asset(asset, current_date)

@dataclass
class CoreAssetInfo:
    asset: str
    designation_date: datetime
    expiry_date: datetime
    reason: str
    bucket: str
    extension_count: int = 0

# Integration with GracePeriodManager
class EnhancedGracePeriodManager(GracePeriodManager):
    def __init__(self, grace_days=3, min_decay_factor=0.1, core_asset_manager=None):
        super().__init__(grace_days, min_decay_factor)
        self.core_asset_manager = core_asset_manager or CoreAssetManager()
    
    def should_apply_grace_period(self, asset: str, current_score: float, 
                                 threshold: float) -> bool:
        """
        Apply grace period ONLY if not a core asset
        """
        # Core assets are NEVER subject to grace periods
        if self.core_asset_manager.should_exempt_from_grace(asset):
            return False
        
        # Normal grace period logic for non-core assets
        return current_score < threshold

# Update SmartDiversificationManager to mark overrides as core
class EnhancedSmartDiversificationManager:
    def __init__(self, override_threshold=0.95, max_overrides=2, core_asset_manager=None):
        self.override_threshold = override_threshold
        self.max_overrides = max_overrides
        self.core_asset_manager = core_asset_manager or CoreAssetManager()
    
    def grant_bucket_override(self, asset: str, score: float):
        """
        Grant bucket override AND mark as core asset
        """
        # Grant override
        # ... existing override logic ...
        
        # CRITICAL: Mark as core asset (immune to grace periods)
        self.core_asset_manager.mark_as_core(
            asset, f"High-alpha bucket override: {score:.3f} > {self.override_threshold}"
        )
```

#### **Issue 2: Holding-Period vs. Regime Aggression Tension**

**Problem**: Regime changes want aggressive rebalancing, but minimum holding periods may prevent immediate action.

**Solution**: Implement regime-aware holding period override:

```python
class RegimeAwareHoldingPeriodManager(HoldingPeriodManager):
    def __init__(self, min_holding_days=3, regime_override_cooldown=30):
        super().__init__(min_holding_days)
        self.regime_override_cooldown = regime_override_cooldown
        self.last_regime_override = {}  # Per-asset cooldown tracking
    
    def can_adjust_position(self, asset: str, current_date: datetime, 
                          regime_context: Dict = None) -> bool:
        """
        Enhanced holding period check with regime override capability
        """
        # Normal holding period check
        normal_check = super().can_adjust_position(asset, current_date)
        
        if normal_check:
            return True  # Normal rules allow adjustment
        
        # Check for regime override eligibility
        if regime_context and regime_context.get('regime_changed', False):
            return self._can_use_regime_override(asset, current_date, regime_context)
        
        return False  # No adjustment allowed
    
    def _can_use_regime_override(self, asset: str, current_date: datetime, 
                               regime_context: Dict) -> bool:
        """
        Check if regime change justifies holding period override
        """
        # Prevent regime override abuse - max once per cooldown period
        last_override = self.last_regime_override.get(asset)
        if last_override:
            days_since_override = (current_date - last_override).days
            if days_since_override < self.regime_override_cooldown:
                return False
        
        # Regime severity check - only allow for significant regime changes
        regime_severity = regime_context.get('regime_severity', 'normal')
        if regime_severity not in ['high', 'critical']:
            return False
        
        # Grant override
        self.last_regime_override[asset] = current_date
        print(f"REGIME OVERRIDE: Allowing {asset} adjustment despite holding period "
              f"(regime: {regime_context.get('new_regime')}, "
              f"severity: {regime_severity})")
        
        return True

# Integration with main position management
class RegimeContextProvider:
    def __init__(self, regime_detector):
        self.regime_detector = regime_detector
        self.last_regime = None
        self.regime_change_date = None
    
    def get_regime_context(self, current_date: datetime) -> Dict:
        """
        Provide regime context for position management decisions
        """
        current_regime = self.regime_detector.get_current_regime(current_date)
        
        regime_changed = False
        regime_severity = 'normal'
        
        if self.last_regime and self.last_regime != current_regime:
            regime_changed = True
            self.regime_change_date = current_date
            
            # Determine severity based on regime transition
            severity_map = {
                ('Goldilocks', 'Deflation'): 'critical',
                ('Goldilocks', 'Inflation'): 'high', 
                ('Deflation', 'Inflation'): 'critical',
                ('Reflation', 'Deflation'): 'critical'
            }
            
            transition = (self.last_regime, current_regime)
            regime_severity = severity_map.get(transition, 'normal')
        
        self.last_regime = current_regime
        
        return {
            'current_regime': current_regime,
            'regime_changed': regime_changed,
            'regime_severity': regime_severity,
            'change_date': self.regime_change_date
        }
```

#### **Issue 3: Two-Stage Sizing & Target Allocation Drift**

**Problem**: When many positions hit single-position cap in stage 1, stage 2 normalization may leave too much cash unallocated.

**Solution**: Implement residual allocation management:

```python
class TwoStagePositionSizerWithResidual(TwoStagePositionSizer):
    def __init__(self, max_single_position=0.15, target_total_allocation=0.95,
                 residual_strategy='top_slice'):
        super().__init__(max_single_position)
        self.target_total_allocation = target_total_allocation
        self.residual_strategy = residual_strategy  # 'top_slice' | 'cash_bucket' | 'proportional'
    
    def size_positions(self, scored_positions: List[PositionScore]) -> List[PositionScore]:
        """
        Two-stage sizing with residual allocation management
        """
        if not scored_positions:
            return []
        
        # Stage 1: Cap individual positions
        stage1_positions = self._apply_individual_caps(scored_positions)
        
        # Stage 2: Normalize to target allocation
        stage2_positions = self._normalize_allocations(stage1_positions)
        
        # Stage 3: Handle residual allocation
        final_positions = self._handle_residual_allocation(stage2_positions)
        
        return final_positions
    
    def _handle_residual_allocation(self, positions: List[PositionScore]) -> List[PositionScore]:
        """
        Allocate any remaining cash to avoid drift
        """
        current_allocation = sum(p.position_size_percentage for p in positions)
        unallocated = self.target_total_allocation - current_allocation
        
        if unallocated < 0.01:  # Less than 1% unallocated
            return positions
        
        print(f"Unallocated cash: {unallocated:.2%} - Applying {self.residual_strategy} strategy")
        
        if self.residual_strategy == 'top_slice':
            return self._top_slice_residual(positions, unallocated)
        elif self.residual_strategy == 'proportional':
            return self._proportional_residual(positions, unallocated)
        elif self.residual_strategy == 'cash_bucket':
            return self._cash_bucket_residual(positions, unallocated)
        else:
            return positions
    
    def _top_slice_residual(self, positions: List[PositionScore], 
                          residual: float) -> List[PositionScore]:
        """
        Add residual to top-scoring uncapped positions
        """
        # Find positions that weren't capped in stage 1
        uncapped_positions = [p for p in positions if not getattr(p, 'was_capped', False)]
        
        if not uncapped_positions:
            return positions  # All were capped, can't allocate more
        
        # Sort by score and allocate residual to top positions
        uncapped_positions.sort(key=lambda x: x.combined_score, reverse=True)
        
        # Distribute residual among top N positions (e.g., top 3)
        top_positions = uncapped_positions[:min(3, len(uncapped_positions))]
        residual_per_position = residual / len(top_positions)
        
        for position in top_positions:
            # Check if adding residual would exceed single position cap
            new_size = position.position_size_percentage + residual_per_position
            if new_size <= self.max_single_position:
                position.position_size_percentage = new_size
                position.residual_added = residual_per_position
            else:
                # Add only what's allowed
                allowed_add = self.max_single_position - position.position_size_percentage
                position.position_size_percentage = self.max_single_position
                position.residual_added = allowed_add
        
        return positions
    
    def _proportional_residual(self, positions: List[PositionScore], 
                             residual: float) -> List[PositionScore]:
        """
        Add residual proportionally to all positions
        """
        current_total = sum(p.position_size_percentage for p in positions)
        
        for position in positions:
            proportion = position.position_size_percentage / current_total
            additional = residual * proportion
            
            # Check single position cap
            new_size = position.position_size_percentage + additional
            if new_size <= self.max_single_position:
                position.position_size_percentage = new_size
                position.residual_added = additional
            else:
                position.position_size_percentage = self.max_single_position
                position.residual_added = self.max_single_position - position.position_size_percentage
        
        return positions
    
    def _cash_bucket_residual(self, positions: List[PositionScore], 
                            residual: float) -> List[PositionScore]:
        """
        Allocate residual to low-beta/cash equivalent bucket
        """
        # Create a synthetic cash position
        cash_position = PositionScore(
            asset='CASH_EQUIVALENT',  # Or treasury ETF like SHY
            combined_score=0.0,
            position_size_percentage=residual,
            is_cash_residual=True
        )
        
        positions.append(cash_position)
        return positions
```

#### **Issue 4: Whipsaw Protection Quantification**

**Problem**: "Rapid cycling" protection was ambiguous and not quantified.

**Solution**: Implement precise whipsaw detection and protection:

```python
class WhipsawProtectionManager:
    def __init__(self, max_cycles_per_period=1, protection_period_days=14, 
                 min_position_duration_hours=4):
        self.max_cycles_per_period = max_cycles_per_period
        self.protection_period_days = protection_period_days
        self.min_position_duration_hours = min_position_duration_hours
        self.position_history = defaultdict(list)  # Track open/close events
    
    def can_open_position(self, asset: str, current_date: datetime) -> bool:
        """
        Check if opening position would violate whipsaw protection
        """
        recent_cycles = self._count_recent_cycles(asset, current_date)
        
        if recent_cycles >= self.max_cycles_per_period:
            print(f"WHIPSAW PROTECTION: Blocked {asset} - {recent_cycles} cycles "
                  f"in last {self.protection_period_days} days (limit: {self.max_cycles_per_period})")
            return False
        
        return True
    
    def can_close_position(self, asset: str, open_date: datetime, 
                          current_date: datetime) -> bool:
        """
        Check if closing position would create whipsaw (too quick)
        """
        position_duration = current_date - open_date
        min_duration = timedelta(hours=self.min_position_duration_hours)
        
        if position_duration < min_duration:
            print(f"WHIPSAW PROTECTION: Blocked {asset} close - position duration "
                  f"{position_duration} < minimum {min_duration}")
            return False
        
        return True
    
    def record_position_event(self, asset: str, event_type: str, 
                            event_date: datetime, position_size: float = 0.0):
        """
        Record position open/close events for tracking
        """
        event = {
            'type': event_type,  # 'open' | 'close'
            'date': event_date,
            'size': position_size
        }
        
        self.position_history[asset].append(event)
        
        # Clean old events
        cutoff_date = event_date - timedelta(days=self.protection_period_days * 2)
        self.position_history[asset] = [
            e for e in self.position_history[asset] 
            if e['date'] > cutoff_date
        ]
    
    def _count_recent_cycles(self, asset: str, current_date: datetime) -> int:
        """
        Count complete open+close cycles in recent period
        """
        cutoff_date = current_date - timedelta(days=self.protection_period_days)
        recent_events = [
            e for e in self.position_history[asset] 
            if e['date'] > cutoff_date
        ]
        
        # Count complete cycles (open followed by close)
        cycles = 0
        expecting_open = True
        
        for event in sorted(recent_events, key=lambda x: x['date']):
            if event['type'] == 'open' and expecting_open:
                expecting_open = False
            elif event['type'] == 'close' and not expecting_open:
                cycles += 1
                expecting_open = True
        
        return cycles
    
    def get_whipsaw_report(self, assets: List[str], current_date: datetime) -> Dict:
        """
        Generate whipsaw protection status report
        """
        report = {}
        
        for asset in assets:
            recent_cycles = self._count_recent_cycles(asset, current_date)
            can_trade = recent_cycles < self.max_cycles_per_period
            
            report[asset] = {
                'recent_cycles': recent_cycles,
                'can_trade': can_trade,
                'protection_active': not can_trade,
                'days_until_reset': self._days_until_protection_reset(asset, current_date)
            }
        
        return report
    
    def _days_until_protection_reset(self, asset: str, current_date: datetime) -> int:
        """
        Calculate days until whipsaw protection resets for an asset
        """
        if asset not in self.position_history:
            return 0
        
        recent_events = [
            e for e in self.position_history[asset]
            if e['date'] > current_date - timedelta(days=self.protection_period_days)
        ]
        
        if not recent_events:
            return 0
        
        oldest_relevant_event = min(recent_events, key=lambda x: x['date'])
        reset_date = oldest_relevant_event['date'] + timedelta(days=self.protection_period_days)
        
        return max(0, (reset_date - current_date).days)

# Integration with main position management
class WhipsawAwarePositionManager:
    def __init__(self, position_manager, whipsaw_protection):
        self.position_manager = position_manager
        self.whipsaw_protection = whipsaw_protection
    
    def execute_position_changes(self, changes: List[PositionChange], 
                               current_date: datetime) -> List[PositionChange]:
        """
        Execute position changes with whipsaw protection
        """
        approved_changes = []
        
        for change in changes:
            if change.action == 'open':
                if self.whipsaw_protection.can_open_position(change.asset, current_date):
                    approved_changes.append(change)
                    self.whipsaw_protection.record_position_event(
                        change.asset, 'open', current_date, change.size
                    )
                else:
                    change.blocked_reason = "Whipsaw protection"
                    
            elif change.action == 'close':
                if self.whipsaw_protection.can_close_position(
                    change.asset, change.open_date, current_date
                ):
                    approved_changes.append(change)
                    self.whipsaw_protection.record_position_event(
                        change.asset, 'close', current_date, change.size
                    )
                else:
                    change.blocked_reason = "Whipsaw protection - too quick"
        
        return approved_changes
```

### **Configuration for Edge Case Management**

```bash
# Core Asset Lifecycle Management
--core-asset-override-threshold 0.95     # Score threshold for core asset status
--core-asset-expiry-days 90              # Automatic expiry after N days
--core-asset-underperformance-threshold 0.15  # 15% underperformance vs bucket triggers revocation
--core-asset-underperformance-period 30  # Days to measure underperformance

# Protection System Priority Hierarchy
--enable-protection-orchestrator        # Enable centralized conflict resolution
--regime-override-grace-periods         # Allow regime to override grace periods  
--regime-override-whipsaw-critical      # Allow critical regime changes to override whipsaw
--protection-system-reporting           # Generate detailed protection status reports

# Regime-Aware Holding Periods
--regime-override-enabled               # Allow regime to override holding periods
--regime-override-cooldown 30           # Days between regime overrides per asset
--regime-severity-threshold high        # Minimum severity for override (normal|high|critical)

# Enhanced Residual Allocation (Safe)
--target-total-allocation 0.95          # Target portfolio allocation (5% cash)
--residual-strategy safe_top_slice      # safe_top_slice|proportional|cash_bucket
--max-residual-per-asset-pct 0.05      # Max 5% of portfolio as residual per asset
--max-residual-position-multiple 0.5    # Max 50% of original position size as residual
--residual-leftover-threshold 0.01      # Threshold for cash bucket rollover (1%)

# Whipsaw Protection (Quantified)
--whipsaw-max-cycles 1                  # Max cycles per protection period
--whipsaw-protection-days 7            # Protection period in days
--whipsaw-min-duration 4                # Minimum position duration in hours
--whipsaw-reporting-enabled             # Generate whipsaw protection reports
```

## 🔄 **Priority Hierarchy & Conflict Resolution**

### **Critical Issue: Overlapping Protection Systems**

**Problem**: What happens when multiple protection systems conflict? (e.g., regime change during grace period or whipsaw window)

**Solution**: Define explicit priority hierarchy with clear exception rules:

```python
class ProtectionSystemOrchestrator:
    """
    Manages conflicts between multiple protection systems with clear priority hierarchy
    """
    
    def __init__(self, core_asset_manager, grace_period_manager, 
                 holding_period_manager, whipsaw_protection_manager):
        self.core_asset_manager = core_asset_manager
        self.grace_period_manager = grace_period_manager
        self.holding_period_manager = holding_period_manager
        self.whipsaw_protection_manager = whipsaw_protection_manager
        
        # Define priority hierarchy (1 = highest priority)
        self.priority_hierarchy = {
            'core_asset_immunity': 1,      # Core assets always protected
            'regime_override': 2,          # Regime changes can override other systems
            'grace_period': 3,             # Grace periods for failing assets
            'holding_period': 4,           # Minimum holding periods
            'whipsaw_protection': 5        # Prevent rapid cycling
        }
    
    def can_execute_action(self, asset: str, action: str, current_date: datetime,
                          regime_context: Dict = None) -> tuple[bool, str]:
        """
        Determine if action can be executed considering all protection systems
        
        Returns: (can_execute: bool, decision_reason: str)
        """
        
        # Priority 1: Core Asset Immunity (highest priority)
        if self.core_asset_manager.is_core_asset(asset, current_date):
            if action in ['close', 'reduce']:
                return False, "BLOCKED: Core asset immunity - cannot close/reduce core assets"
            elif action in ['open', 'increase']:
                return True, "ALLOWED: Core asset immunity - can always increase core positions"
        
        # Priority 2: Regime Override (can override lower-priority systems)
        regime_override_allowed = False
        if regime_context and regime_context.get('regime_changed', False):
            severity = regime_context.get('regime_severity', 'normal')
            if severity in ['high', 'critical']:
                # Check if regime override is valid for this asset
                if self.holding_period_manager.can_use_regime_override(asset, current_date, regime_context):
                    regime_override_allowed = True
                    
        # Check each protection system in priority order
        protection_results = []
        
        # Priority 3: Grace Period
        if hasattr(self.grace_period_manager, 'is_in_grace_period'):
            in_grace = self.grace_period_manager.is_in_grace_period(asset, current_date)
            if in_grace and action in ['close', 'reduce']:
                if regime_override_allowed:
                    protection_results.append(('grace_period', False, 'OVERRIDDEN: Regime change overrides grace period'))
                else:
                    protection_results.append(('grace_period', True, 'BLOCKED: Asset in grace period'))
            else:
                protection_results.append(('grace_period', False, 'Grace period allows action'))
        
        # Priority 4: Holding Period
        holding_period_ok = self.holding_period_manager.can_adjust_position(asset, current_date, regime_context)
        if not holding_period_ok:
            if regime_override_allowed:
                protection_results.append(('holding_period', False, 'OVERRIDDEN: Regime change overrides holding period'))
            else:
                protection_results.append(('holding_period', True, 'BLOCKED: Minimum holding period not met'))
        else:
            protection_results.append(('holding_period', False, 'Holding period allows action'))
        
        # Priority 5: Whipsaw Protection (lowest priority)
        whipsaw_blocked = False
        if action == 'open':
            whipsaw_blocked = not self.whipsaw_protection_manager.can_open_position(asset, current_date)
        elif action in ['close', 'reduce']:
            # Need position open date for this check - would need to be passed in
            # For now, assume we have it available
            open_date = self._get_position_open_date(asset)  # Implementation needed
            if open_date:
                whipsaw_blocked = not self.whipsaw_protection_manager.can_close_position(asset, open_date, current_date)
        
        if whipsaw_blocked:
            if regime_override_allowed:
                protection_results.append(('whipsaw_protection', False, 'OVERRIDDEN: Regime change overrides whipsaw protection'))
            else:
                protection_results.append(('whipsaw_protection', True, 'BLOCKED: Whipsaw protection active'))
        else:
            protection_results.append(('whipsaw_protection', False, 'Whipsaw protection allows action'))
        
        # Determine final decision based on priority hierarchy
        blocking_systems = [result for result in protection_results if result[1] == True]
        
        if blocking_systems:
            # Find highest priority blocking system
            highest_priority_block = min(blocking_systems, 
                                       key=lambda x: self.priority_hierarchy.get(x[0], 999))
            return False, highest_priority_block[2]
        else:
            # No blocking systems
            allowing_reasons = [result[2] for result in protection_results if not result[1]]
            return True, f"ALLOWED: {'; '.join(allowing_reasons)}"
    
    def get_protection_status_report(self, assets: List[str], current_date: datetime,
                                   regime_context: Dict = None) -> Dict:
        """
        Generate comprehensive protection status for all assets
        """
        report = {}
        
        for asset in assets:
            status = {}
            
            # Core asset status
            status['is_core'] = self.core_asset_manager.is_core_asset(asset, current_date)
            
            # Grace period status
            if hasattr(self.grace_period_manager, 'is_in_grace_period'):
                status['in_grace_period'] = self.grace_period_manager.is_in_grace_period(asset, current_date)
            
            # Holding period status
            status['holding_period_ok'] = self.holding_period_manager.can_adjust_position(asset, current_date)
            
            # Whipsaw status
            whipsaw_report = self.whipsaw_protection_manager.get_whipsaw_report([asset], current_date)
            status['whipsaw_status'] = whipsaw_report.get(asset, {})
            
            # Regime override eligibility
            if regime_context and regime_context.get('regime_changed', False):
                status['regime_override_eligible'] = self.holding_period_manager.can_use_regime_override(
                    asset, current_date, regime_context
                )
            else:
                status['regime_override_eligible'] = False
            
            # Overall action permissions
            for action in ['open', 'close', 'increase', 'reduce']:
                can_execute, reason = self.can_execute_action(asset, action, current_date, regime_context)
                status[f'can_{action}'] = {'allowed': can_execute, 'reason': reason}
            
            report[asset] = status
        
        return report
    
    def resolve_conflicts_on_regime_change(self, assets: List[str], new_regime: str,
                                         regime_severity: str, current_date: datetime) -> Dict:
        """
        Special handling for regime changes - resolve all conflicts systematically
        """
        regime_context = {
            'regime_changed': True,
            'new_regime': new_regime,
            'regime_severity': regime_severity,
            'change_date': current_date
        }
        
        conflict_resolutions = {}
        
        for asset in assets:
            # Check what would normally be blocked
            normal_restrictions = []
            
            # Check grace period
            if hasattr(self.grace_period_manager, 'is_in_grace_period'):
                if self.grace_period_manager.is_in_grace_period(asset, current_date):
                    normal_restrictions.append('grace_period')
            
            # Check holding period
            if not self.holding_period_manager.can_adjust_position(asset, current_date):
                normal_restrictions.append('holding_period')
            
            # Check whipsaw
            if not self.whipsaw_protection_manager.can_open_position(asset, current_date):
                normal_restrictions.append('whipsaw_protection')
            
            # Determine what regime override can accomplish
            overrides_granted = []
            if regime_severity in ['high', 'critical']:
                if 'holding_period' in normal_restrictions:
                    if self.holding_period_manager.can_use_regime_override(asset, current_date, regime_context):
                        overrides_granted.append('holding_period')
                
                # Regime can also override whipsaw for critical changes
                if regime_severity == 'critical' and 'whipsaw_protection' in normal_restrictions:
                    overrides_granted.append('whipsaw_protection')
                    
                # Grace periods are overridden for high severity regime changes
                if 'grace_period' in normal_restrictions:
                    overrides_granted.append('grace_period')
            
            conflict_resolutions[asset] = {
                'normal_restrictions': normal_restrictions,
                'regime_overrides_granted': overrides_granted,
                'final_restrictions': [r for r in normal_restrictions if r not in overrides_granted],
                'regime_context': regime_context
            }
        
        return conflict_resolutions
```

## 💰 **Enhanced Residual Allocation with Safety Caps**

### **Critical Issue: Top-Slice Over-Concentration**

**Problem**: In "top_slice" mode with few uncapped positions, residual allocation could over-concentrate into one asset.

**Solution**: Implement progressive safety caps and rollover logic:

```python
class SafeResidualAllocationManager:
    """
    Enhanced residual allocation with concentration safeguards
    """
    
    def __init__(self, max_residual_per_asset_pct=0.05, max_residual_as_position_multiple=0.5):
        self.max_residual_per_asset_pct = max_residual_per_asset_pct  # Max 5% of portfolio as residual
        self.max_residual_as_position_multiple = max_residual_as_position_multiple  # Max 50% of original position size
    
    def _top_slice_residual_safe(self, positions: List[PositionScore], 
                               residual: float) -> List[PositionScore]:
        """
        Enhanced top-slice with concentration safeguards and rollover
        """
        uncapped_positions = [p for p in positions if not getattr(p, 'was_capped', False)]
        
        if not uncapped_positions:
            # All positions were capped - roll to cash bucket
            return self._cash_bucket_residual(positions, residual)
        
        # Sort by score (highest first)
        uncapped_positions.sort(key=lambda x: x.combined_score, reverse=True)
        
        total_allocated_residual = 0.0
        positions_modified = []
        
        # Progressive allocation with safety caps
        for position in uncapped_positions:
            if total_allocated_residual >= residual:
                break
            
            remaining_residual = residual - total_allocated_residual
            
            # Calculate maximum safe allocation for this position
            max_by_portfolio_pct = self.max_residual_per_asset_pct  # 5% of total portfolio
            max_by_position_multiple = position.position_size_percentage * self.max_residual_as_position_multiple
            max_by_single_position_cap = self.max_single_position - position.position_size_percentage
            
            # Take the most restrictive limit
            max_safe_addition = min(
                remaining_residual,
                max_by_portfolio_pct,
                max_by_position_multiple,
                max_by_single_position_cap
            )
            
            if max_safe_addition > 0.001:  # Minimum 0.1% to avoid tiny allocations
                position.position_size_percentage += max_safe_addition
                position.residual_added = max_safe_addition
                position.residual_cap_reason = self._get_cap_reason(
                    max_safe_addition, max_by_portfolio_pct, 
                    max_by_position_multiple, max_by_single_position_cap
                )
                total_allocated_residual += max_safe_addition
                positions_modified.append(position.asset)
            
        # Handle leftover residual if safety caps prevented full allocation
        leftover = residual - total_allocated_residual
        
        if leftover > 0.01:  # More than 1% leftover
            print(f"Residual allocation safety caps left {leftover:.2%} unallocated")
            print(f"Modified positions: {positions_modified}")
            
            # Options for leftover:
            # 1. Cash bucket (safest)
            # 2. Proportional to all positions (more aggressive)
            # 3. Second-tier top slice (moderate)
            
            return self._handle_leftover_residual(positions, leftover, "safety_caps")
        
        return positions
    
    def _get_cap_reason(self, allocated: float, max_pct: float, max_multiple: float, 
                       max_single: float) -> str:
        """
        Determine which constraint was binding
        """
        if allocated == max_pct:
            return f"Portfolio percentage cap ({max_pct:.1%})"
        elif allocated == max_multiple:
            return f"Position multiple cap ({self.max_residual_as_position_multiple:.0%} of original)"
        elif allocated == max_single:
            return "Single position size cap"
        else:
            return "Residual exhausted"
    
    def _handle_leftover_residual(self, positions: List[PositionScore], 
                                leftover: float, reason: str) -> List[PositionScore]:
        """
        Handle residual that couldn't be allocated due to safety constraints
        """
        print(f"Handling {leftover:.2%} leftover residual (reason: {reason})")
        
        # Strategy 1: Try proportional allocation to all positions (with caps)
        proportional_success, updated_positions = self._try_proportional_leftover(positions, leftover)
        
        if proportional_success:
            return updated_positions
        
        # Strategy 2: Cash bucket fallback
        print(f"Proportional allocation failed, using cash bucket for {leftover:.2%}")
        return self._cash_bucket_residual(positions, leftover)
    
    def _try_proportional_leftover(self, positions: List[PositionScore], 
                                 leftover: float) -> tuple[bool, List[PositionScore]]:
        """
        Try to allocate leftover proportionally with safety caps
        """
        current_total = sum(p.position_size_percentage for p in positions)
        allocated_leftover = 0.0
        
        for position in positions:
            if allocated_leftover >= leftover:
                break
            
            # Proportional share of leftover
            proportion = position.position_size_percentage / current_total
            proportional_share = leftover * proportion
            
            # Apply safety caps
            max_additional = min(
                proportional_share,
                self.max_residual_per_asset_pct - getattr(position, 'residual_added', 0),
                self.max_single_position - position.position_size_percentage
            )
            
            if max_additional > 0.001:
                position.position_size_percentage += max_additional
                position.leftover_residual_added = max_additional
                allocated_leftover += max_additional
        
        # Consider it successful if we allocated >80% of leftover
        success_threshold = 0.8
        success = (allocated_leftover / leftover) >= success_threshold
        
        return success, positions

# Integration with TwoStagePositionSizer
class EnhancedTwoStagePositionSizer(TwoStagePositionSizerWithResidual):
    def __init__(self, max_single_position=0.15, target_total_allocation=0.95,
                 residual_strategy='safe_top_slice', max_residual_per_asset=0.05):
        super().__init__(max_single_position, target_total_allocation, residual_strategy)
        self.residual_manager = SafeResidualAllocationManager(
            max_residual_per_asset_pct=max_residual_per_asset,
            max_residual_as_position_multiple=0.5
        )
    
    def _top_slice_residual(self, positions: List[PositionScore], 
                          residual: float) -> List[PositionScore]:
        """
        Use enhanced safe top-slice allocation
        """
        return self.residual_manager._top_slice_residual_safe(positions, residual)
```

These solutions address the sophisticated edge cases and ensure the system behaves predictably under institutional-level scrutiny.

## 🎛️ Configuration Strategy Examples

### **Strategy Preset 1: Conservative Diversified**
```bash
python main.py regime --buckets "Risk Assets,Defensive Assets,International" \
  --max-total-positions 8 \
  --max-new-positions 2 \
  --max-positions-per-bucket 3 \
  --min-buckets-represented 3 \
  --max-bucket-allocation 0.35 \
  --position-size-scaling equal_weight \
  --base-position-size 0.12 \
  --diversification-mode strict \
  --min-score-threshold 0.65 \
  --min-score-new-position 0.7
```

### **Strategy Preset 2: Aggressive Growth**
```bash
python main.py regime --buckets "Risk Assets,Growth,High Beta" \
  --max-total-positions 12 \
  --max-new-positions 5 \
  --max-positions-per-bucket 6 \
  --max-bucket-allocation 0.6 \
  --position-size-scaling score_weighted \
  --max-single-position-size 0.25 \
  --regime-change-aggression 3.0 \
  --diversification-mode aggressive \
  --min-score-threshold 0.55 \
  --trending-confidence-new 0.8
```

### **Strategy Preset 3: Regime-Adaptive Balanced**
```bash
python main.py regime --buckets "Risk Assets,Defensive Assets,Commodities,International" \
  --max-total-positions 10 \
  --max-new-positions 3 \
  --max-positions-per-bucket 4 \
  --min-buckets-represented 2 \
  --max-bucket-allocation 0.4 \
  --position-size-scaling adaptive \
  --regime-change-aggression 2.5 \
  --diversification-mode balanced \
  --volatility-position-scaling \
  --bucket-balance-tolerance 0.15
```

### **Strategy Preset 4: Momentum Focus**
```bash
python main.py regime --buckets "Risk Assets,Growth" \
  --max-total-positions 6 \
  --max-new-positions 4 \
  --max-positions-per-bucket 5 \
  --position-size-scaling score_weighted \
  --max-single-position-size 0.3 \
  --trending-confidence-new 0.85 \
  --min-score-new-position 0.75 \
  --position-holding-period-min 7 \
  --score-decay-factor 0.98
```

### **Strategy Preset 5: Crisis/Defensive Mode**
```bash
python main.py regime --buckets "Defensive Assets,Gold,Treasurys" \
  --max-total-positions 5 \
  --max-new-positions 1 \
  --max-positions-per-bucket 2 \
  --min-buckets-represented 3 \
  --position-size-scaling equal_weight \
  --base-position-size 0.18 \
  --diversification-mode strict \
  --min-score-threshold 0.7 \
  --drawdown-position-reduction 0.6
```

## 📊 Parameter Validation & Constraints

### **Constraint Rules**
```python
# Portfolio Management Constraints
assert max_new_positions <= max_total_positions
assert max_positions_per_bucket <= max_total_positions
assert min_buckets_represented >= 1
assert 0.1 <= max_bucket_allocation <= 1.0

# Position Sizing Constraints  
assert 0.01 <= base_position_size <= 0.5
assert min_position_size <= base_position_size <= max_single_position_size
assert 0.8 <= target_portfolio_allocation <= 1.0

# Scoring Constraints
assert 0.0 <= min_score_threshold <= 1.0
assert min_score_threshold <= min_score_new_position
assert 0.5 <= score_decay_factor <= 1.0

# Diversification Constraints
assert diversification_mode in ['strict', 'balanced', 'aggressive']
assert 0.1 <= sector_concentration_limit <= 1.0
assert 0.0 <= bucket_balance_tolerance <= 0.5
```

### **Parameter Dependencies**
```python
# If strict diversification, enforce stricter limits
if diversification_mode == 'strict':
    max_bucket_allocation = min(max_bucket_allocation, 0.35)
    min_buckets_represented = max(min_buckets_represented, 2)

# If aggressive mode, relax some constraints
if diversification_mode == 'aggressive':
    max_bucket_allocation = min(max_bucket_allocation, 0.7)
    bucket_balance_tolerance = max(bucket_balance_tolerance, 0.3)

# Dynamic sizing requires specific parameters
if position_size_scaling == 'adaptive':
    assert base_position_size is not None
    assert size_adjustment_factor is not None
```

## 📋 Detailed Implementation Plan

### Phase 1: Portfolio State Tracking

#### 1.1 Enhanced Position Manager State
```python
class PositionManager:
    def __init__(self, ...):
        # Current implementation
        self.current_positions: Dict[str, PositionScore] = {}
        
        # NEW: Enhanced portfolio tracking
        self.portfolio_assets: Set[str] = set()  # Track all current assets
        self.position_metadata: Dict[str, PositionMetadata] = {}
        
        # NEW: Dynamic limits
        self.max_new_positions = 3  # Max new positions per rebalance
        self.max_total_positions = 10  # Overall portfolio limit
        self.regime_change_multiplier = 2.0  # Increase limits during regime change
```

#### 1.2 Position Metadata Tracking
```python
@dataclass
class PositionMetadata:
    asset: str
    entry_date: datetime
    entry_regime: str
    days_held: int
    regime_changes_while_held: int
    last_trending_confidence: Optional[float]
    is_core_holding: bool  # For positions that should have extra priority
```

### Phase 2: Intelligent Asset Universe Construction

#### 2.1 Multi-Source Asset Selection
```python
def get_rebalancing_universe(self, current_date, regime, bucket_assets) -> RebalancingUniverse:
    """
    Construct comprehensive asset universe for rebalancing
    """
    
    # 1. ALWAYS include current portfolio assets (highest priority)
    portfolio_assets = set(self.current_positions.keys())
    
    # 2. Get trending assets for new opportunities
    trending_assets = self.regime_detector.get_trending_assets(
        current_date, bucket_assets, 
        min_confidence=self.min_trending_confidence
    )
    
    # 3. Get regime-appropriate assets (broader universe)
    regime_assets = self.asset_manager.get_assets_from_buckets(regime_buckets)
    
    return RebalancingUniverse(
        portfolio_assets=portfolio_assets,      # MUST analyze
        trending_assets=set(trending_assets),   # New opportunities
        regime_assets=set(regime_assets),       # Regime-appropriate
        combined_universe=portfolio_assets | set(trending_assets)
    )
```

#### 2.2 Priority-Based Scoring
```python
def analyze_rebalancing_universe(self, universe: RebalancingUniverse, 
                               current_date, regime) -> PrioritizedScores:
    """
    Score assets with priority classification
    """
    all_scores = []
    
    for asset in universe.combined_universe:
        score = self._score_single_asset(asset, current_date, regime, self.data_manager)
        
        # Classify asset priority
        priority = self._classify_asset_priority(asset, universe)
        score.priority = priority
        
        all_scores.append(score)
    
    return PrioritizedScores(
        portfolio_scores=[s for s in all_scores if s.priority == Priority.PORTFOLIO],
        trending_scores=[s for s in all_scores if s.priority == Priority.TRENDING],
        regime_scores=[s for s in all_scores if s.priority == Priority.REGIME]
    )
```

### Phase 3: Dynamic Position Limits

#### 3.1 Context-Aware Limits
```python
class DynamicLimits:
    def __init__(self, base_limits: Dict):
        self.max_new_positions = base_limits['max_new_positions']
        self.max_total_positions = base_limits['max_total_positions']
    
    def get_rebalancing_limits(self, context: RebalancingContext) -> RebalancingLimits:
        """
        Calculate dynamic limits based on context
        """
        
        # Base limits
        max_new = self.max_new_positions
        max_total = self.max_total_positions
        
        # Regime change: More aggressive rebalancing
        if context.regime_changed:
            max_new = int(max_new * context.regime_change_multiplier)
            max_total = int(max_total * 1.2)  # Allow temporary overage
        
        # Market volatility: More conservative
        if context.volatility_regime == 'HIGH':
            max_new = max(1, int(max_new * 0.5))
        
        # Portfolio concentration: Force diversification
        if context.portfolio_concentration > 0.7:
            max_new = max(2, max_new)  # Force some diversification
        
        return RebalancingLimits(
            max_new_positions=max_new,
            max_total_positions=max_total,
            force_diversification=context.portfolio_concentration > 0.7
        )
```

#### 3.2 Priority-Based Position Selection
```python
def select_optimal_portfolio(self, scores: PrioritizedScores, 
                           limits: RebalancingLimits) -> PortfolioSelection:
    """
    Select optimal portfolio respecting priorities and limits
    """
    
    selected_positions = []
    
    # STEP 1: Handle existing portfolio (highest priority)
    portfolio_candidates = sorted(scores.portfolio_scores, 
                                key=lambda x: x.combined_score, reverse=True)
    
    for score in portfolio_candidates:
        if score.combined_score >= self.min_score_threshold:
            selected_positions.append(score)
        # Note: Below-threshold positions will be closed
    
    # STEP 2: Add new positions within limits
    new_position_slots = min(
        limits.max_new_positions,
        limits.max_total_positions - len(selected_positions)
    )
    
    if new_position_slots > 0:
        new_candidates = [s for s in scores.trending_scores 
                         if s.asset not in [sp.asset for sp in selected_positions]]
        new_candidates.sort(key=lambda x: x.combined_score, reverse=True)
        
        selected_positions.extend(new_candidates[:new_position_slots])
    
    return PortfolioSelection(
        selected_positions=selected_positions,
        positions_to_close=[s for s in scores.portfolio_scores 
                          if s.combined_score < self.min_score_threshold],
        new_positions=[s for s in selected_positions 
                      if s.asset not in scores.portfolio_assets]
    )
```

### Phase 4: Enhanced Position Change Calculation

#### 4.1 Context-Aware Position Changes
```python
def calculate_dynamic_position_changes(self, selection: PortfolioSelection,
                                     context: RebalancingContext) -> List[PositionChange]:
    """
    Calculate position changes with enhanced context awareness
    """
    changes = []
    
    # CLOSURES: Handle positions to close
    for score in selection.positions_to_close:
        # Enhanced closure reasons
        if score.combined_score < self.min_score_threshold:
            reason = f'Score below threshold: {score.combined_score:.3f} < {self.min_score_threshold}'
        elif context.regime_changed and not self._asset_fits_new_regime(score.asset):
            reason = f'Regime change: {context.old_regime} -> {context.new_regime}'
        else:
            reason = 'Portfolio optimization'
        
        changes.append(PositionChange(
            asset=score.asset,
            action='close',
            reason=reason,
            priority='HIGH' if context.regime_changed else 'NORMAL'
        ))
    
    # ADJUSTMENTS: Handle existing positions
    for score in selection.selected_positions:
        if score.asset in self.current_positions:
            change = self._calculate_position_adjustment(score, context)
            if change:
                changes.append(change)
    
    # NEW POSITIONS: Handle new openings
    for score in selection.new_positions:
        changes.append(PositionChange(
            asset=score.asset,
            action='open',
            size_change=score.position_size_percentage,
            reason=f'New opportunity: score {score.combined_score:.3f}',
            priority='NORMAL'
        ))
    
    return changes
```

### Phase 5: Configuration Parameters

#### 5.1 Complete Strategy Parameters
```python
# Add to RegimeStrategy params - Portfolio Management
('max_new_positions_per_rebalance', 3),
('max_total_positions', 10),
('max_positions_per_bucket', 4),
('min_buckets_represented', 2),
('max_bucket_allocation', 0.4),
('regime_change_aggression', 2.0),
('portfolio_concentration_limit', 0.7),

# Position Sizing
('base_position_size', 0.1),
('position_size_scaling', 'dynamic'),  # 'dynamic'|'fixed'|'equal_weight'|'score_weighted'
('max_single_position_size', 0.2),
('min_position_size', 0.02),
('size_adjustment_factor', 0.8),
('target_portfolio_allocation', 0.95),

# Scoring & Selection
('min_score_threshold', 0.6),
('min_score_new_position', 0.65),
('score_decay_factor', 0.95),
('trending_confidence_new', 0.7),
('trending_confidence_existing', 0.0),

# Diversification (Bucket-Only)
('diversification_mode', 'balanced'),  # 'strict'|'balanced'|'aggressive'
('correlation_limit', 0.8),
('correlation_window', 60),
('force_bucket_distribution', True),
('bucket_balance_tolerance', 0.2),

# Risk Management & Grace Period
('position_holding_period_min', 3),
('position_holding_period_max', 90),
('volatility_position_scaling', True),
('drawdown_position_reduction', 0.8),
('grace_period_days', 5),
('grace_period_decay_rate', 0.8),
('bucket_override_threshold', 0.95),
('max_bucket_overrides', 2),
('whipsaw_protection', True),
```

#### 5.2 Complete CLI Arguments
```bash
# Portfolio Management
--max-new-positions 3
--max-total-positions 10
--max-positions-per-bucket 4
--min-buckets-represented 2
--max-bucket-allocation 0.4
--regime-change-aggression 2.0
--portfolio-concentration-limit 0.7

# Position Sizing
--base-position-size 0.1
--position-size-scaling dynamic
--max-single-position-size 0.2
--min-position-size 0.02
--size-adjustment-factor 0.8
--target-portfolio-allocation 0.95

# Scoring & Selection  
--min-score-threshold 0.6
--min-score-new-position 0.65
--score-decay-factor 0.95
--trending-confidence-new 0.7
--trending-confidence-existing 0.0

# Diversification (Bucket-Only)
--diversification-mode balanced
--correlation-limit 0.8
--correlation-window 60
--force-bucket-distribution
--bucket-balance-tolerance 0.2

# Risk Management & Grace Period
--position-holding-period-min 3
--position-holding-period-max 90
--volatility-position-scaling
--drawdown-position-reduction 0.8
--grace-period-days 5
--grace-period-decay-rate 0.8
--bucket-override-threshold 0.95
--max-bucket-overrides 2
--whipsaw-protection
```

## 🔄 Implementation Steps

### Step 1: Portfolio State Enhancement (Week 1)
1. Add portfolio tracking to PositionManager
2. Implement PositionMetadata tracking with bucket information
3. Add portfolio asset set management
4. Create portfolio state persistence
5. **NEW**: Add bucket tracking per position
6. **NEW**: Implement position age and regime change tracking

### Step 2: Asset Universe Construction (Week 1-2)
1. Implement RebalancingUniverse class
2. Create multi-source asset selection logic
3. Add priority classification system
4. Test asset universe construction
5. **NEW**: Implement bucket-aware asset selection
6. **NEW**: Add portfolio vs new asset separation

### Step 3: Dynamic Limits & Diversification System (Week 2)
1. Implement DynamicLimits class
2. Add context-aware limit calculation
3. Create RebalancingContext data structure
4. Add volatility and concentration detection
5. **NEW**: Implement BucketDiversificationManager
6. **NEW**: Add bucket allocation algorithms
7. **NEW**: Create diversification constraint enforcement

### Step 4: Professional-Grade Risk Management (Week 2)
1. **NEW**: Implement GracePeriodManager for position decay vs immediate closure
2. **NEW**: Create HoldingPeriodManager for adjustment synchronization
3. **NEW**: Add whipsaw protection to prevent rapid position cycling
4. **NEW**: Implement position age tracking and eligibility checking

### Step 5: Two-Stage Dynamic Position Sizing (Week 2-3)
1. **NEW**: Implement TwoStagePositionSizer class
2. **NEW**: Stage 1: Cap individual positions at max_single_size
3. **NEW**: Stage 2: Normalize remaining allocation among uncapped positions
4. **NEW**: Add adaptive sizing based on portfolio count
5. **NEW**: Create position sizing modes (adaptive, equal_weight, score_weighted)
6. **NEW**: Implement allocation overflow handling with proper capping

### Step 6: Smart Portfolio Selection with Overrides (Week 2-3)
1. Implement priority-based selection
2. Add new position limiting with bucket constraints
3. Create portfolio optimization algorithm
4. Test selection under various scenarios
5. **NEW**: Implement SmartDiversificationManager with bucket overrides
6. **NEW**: Add high-alpha asset exception handling
7. **NEW**: Integrate diversification constraints with override logic

### Step 7: Enhanced Position Change Management (Week 3)
1. Enhance position change calculation with grace period integration
2. Add contextual closure reasons with holding period awareness
3. Implement priority-based execution with timing constraints
4. Add position adjustment logic respecting min holding periods
5. **NEW**: Add bucket-aware position changes with override tracking
6. **NEW**: Implement two-stage dynamic sizing in position changes
7. **NEW**: Add grace period status tracking in position changes

### Step 8: Complete CLI Configuration (Week 3)
1. **NEW**: Add all 30+ new CLI parameters (including grace period & override params)
2. **NEW**: Group parameters logically in CLI help
3. Update configuration validation for all parameters
4. Add comprehensive logging for all decisions
5. Create configuration presets for common strategies
6. **NEW**: Add parameter validation and constraints
7. **NEW**: Add professional parameter validation rules

### Step 9: Enhanced Backtesting Features (Week 3-4)
1. **NEW**: Add configuration logging to backtest results
2. **NEW**: Create diversification metrics tracking
3. **NEW**: Add bucket allocation history with override tracking
4. **NEW**: Implement position sizing analytics with two-stage metrics
5. **NEW**: Add correlation and concentration monitoring
6. **NEW**: Track grace period usage and effectiveness
7. **NEW**: Monitor holding period constraint impacts

### Step 10: Professional Testing and Validation (Week 4)
1. Create comprehensive test suite for all scenarios
2. Test regime change scenarios with new limits
3. Test concentration limits and bucket constraints with overrides
4. Validate existing position priority and grace period handling
5. **NEW**: Test all position sizing modes and two-stage capping
6. **NEW**: Validate bucket diversification enforcement with overrides
7. **NEW**: Test parameter boundary conditions and edge cases
8. **NEW**: Test grace period decay scenarios
9. **NEW**: Validate holding period synchronization
10. **NEW**: Test whipsaw protection effectiveness

### Step 11: Documentation and Professional Examples (Week 4)
1. **NEW**: Create parameter configuration guide with professional rationale
2. **NEW**: Add example configurations for different strategies
3. **NEW**: Document bucket diversification strategies with override examples
4. **NEW**: Create troubleshooting guide for common issues
5. Update usage documentation with all new features
6. **NEW**: Add professional risk management documentation
7. **NEW**: Create grace period and holding period guides

## 🎯 Expected Outcomes

### Immediate Fixes
- ✅ Existing positions always re-evaluated
- ✅ No more forced closures without proper scoring
- ✅ Trending confidence only affects NEW position selection

### Enhanced Features
- ✅ Dynamic position limits based on market conditions
- ✅ Priority-based portfolio management
- ✅ Intelligent regime change handling
- ✅ Portfolio concentration management

### Strategic Benefits
- **Risk Management**: Better control over portfolio construction
- **Performance**: More intelligent position selection and sizing
- **Flexibility**: Adaptable to different market regimes and conditions
- **Transparency**: Clear reasoning for all position changes

## 📈 Enhanced Backtesting Metrics

### **Diversification Tracking**
```python
diversification_metrics = {
    'bucket_distribution': {
        'Risk Assets': 0.35,      # 35% of portfolio
        'Defensive Assets': 0.30, # 30% of portfolio  
        'International': 0.20,    # 20% of portfolio
        'Commodities': 0.15       # 15% of portfolio
    },
    'bucket_concentration_max': 0.35,  # No bucket > 35%
    'herfindahl_index': 0.28,          # Diversification index
    'active_buckets_count': 4,         # Number of buckets represented
    'bucket_balance_score': 0.85       # How well balanced across buckets
}
```

### **Position Sizing Analytics**
```python
position_sizing_metrics = {
    'total_allocation': 0.94,           # 94% of portfolio allocated
    'average_position_size': 0.094,     # Average 9.4% per position
    'position_size_variance': 0.003,    # Low variance = well balanced
    'largest_position': 0.18,           # Largest single position 18%
    'smallest_position': 0.06,          # Smallest position 6%
    'sizing_efficiency': 0.92           # How well did sizing work
}
```

### **Dynamic Behavior Validation**
```python
dynamic_behavior_metrics = {
    'regime_change_responses': 12,      # Times limits increased during regime change
    'new_position_rejections': 8,       # Times hit max_new_positions limit
    'bucket_limit_enforcements': 15,    # Times bucket limits prevented over-concentration
    'existing_position_reevals': 156,   # All existing positions re-evaluated
    'diversification_corrections': 7    # Times forced diversification
}
```

## 🚨 Critical Success Metrics

1. **No Zombie Positions**: 100% of existing positions must be re-evaluated
2. **Prioritized Selection**: Portfolio assets scored regardless of trending confidence  
3. **Dynamic Behavior**: Different limits during regime changes vs normal periods
4. **Clear Reasoning**: Every position change has contextual explanation
5. **Backward Compatibility**: Existing configurations continue to work
6. **NEW: Bucket Diversification**: Portfolio maintains target bucket distribution
7. **NEW: Position Sizing Efficiency**: Two-stage sizing prevents allocation overflow
8. **NEW: Parameter Sensitivity**: All parameters demonstrably affect behavior
9. **NEW: Configuration Validation**: Invalid parameter combinations rejected
10. **NEW: Performance Tracking**: All new metrics logged and exportable
11. **NEW: Professional Grace Period**: No whipsaw trading around score thresholds
12. **NEW: Holding Period Compliance**: Position adjustments respect timing constraints
13. **NEW: High-Alpha Preservation**: Exceptional assets can override diversification limits
14. **NEW: Risk Manager Approval**: All professional concerns addressed with solutions

## 📋 Risk Mitigation

### Technical Risks
- **Complexity**: Comprehensive testing of all scenarios
- **Performance**: Efficient asset universe construction
- **State Management**: Robust portfolio state tracking

### Market Risks
- **Over-Optimization**: Balance between sophistication and simplicity
- **Parameter Sensitivity**: Extensive backtesting of dynamic limits
- **Regime Detection**: Robust handling of regime detection failures 