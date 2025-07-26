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
--sector-concentration-limit 0.3         # Max allocation per sector (30%)
--correlation-limit 0.8                  # Max correlation between positions
--correlation-window 60                  # Days for correlation calculation
--sector-classification dynamic          # dynamic|api|hardcoded|hybrid
--correlation-update-frequency daily     # daily|weekly|monthly
--regime-aware-correlation true          # Adjust correlations by market regime
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

## 🏗️ Dynamic Sector Classification & Correlation System

### **The Challenge: Static vs Dynamic Classification**

**Hardcoded Approach Problems:**
```python
# Static mapping - becomes stale quickly
SECTOR_MAPPING = {
    'AAPL': 'Technology',
    'TSLA': 'Automotive',  # But is it really? Or Technology? Or Energy?
    'SQ': 'Fintech',       # New category not in traditional sectors
    'SHOP': 'E-commerce'   # Again, traditional sectors miss this
}
```

**Dynamic Approach Benefits:**
- Adapts to changing business models
- Captures cross-sector companies accurately
- Handles new instruments automatically
- Reflects current market behavior vs historical classification

### **Recommended: Hybrid Multi-Source System**

#### **1. Multi-Source Sector Classification**
```python
class DynamicSectorClassifier:
    def __init__(self, classification_mode='hybrid'):
        self.classification_mode = classification_mode
        self.api_cache = {}
        self.behavior_cache = {}
        self.manual_overrides = {}
        
    def get_asset_sector(self, asset: str, current_date: datetime) -> str:
        """
        Get sector using multi-source approach
        """
        if self.classification_mode == 'hybrid':
            return self._hybrid_classification(asset, current_date)
        elif self.classification_mode == 'api':
            return self._api_classification(asset)
        elif self.classification_mode == 'dynamic':
            return self._behavioral_classification(asset, current_date)
        else:  # hardcoded
            return self._hardcoded_classification(asset)
    
    def _hybrid_classification(self, asset: str, current_date: datetime) -> str:
        """
        Hybrid approach: API + Behavioral + Manual overrides
        """
        
        # 1. Check manual overrides first (for edge cases)
        if asset in self.manual_overrides:
            return self.manual_overrides[asset]
        
        # 2. Get API sector as base
        api_sector = self._api_classification(asset)
        
        # 3. Get behavioral sector
        behavioral_sector = self._behavioral_classification(asset, current_date)
        
        # 4. Decide which to use based on confidence and recency
        if api_sector and behavioral_sector:
            # If they agree, use API sector
            if self._sectors_similar(api_sector, behavioral_sector):
                return api_sector
            else:
                # If they disagree, use behavioral (more current)
                return behavioral_sector
        elif api_sector:
            return api_sector
        elif behavioral_sector:
            return behavioral_sector
        else:
            return 'Unknown'
    
    def _api_classification(self, asset: str) -> Optional[str]:
        """
        Get sector from financial APIs (Yahoo Finance, Alpha Vantage, etc.)
        """
        if asset in self.api_cache:
            return self.api_cache[asset]
        
        try:
            # This would integrate with your existing financial data APIs
            # Example with yfinance (if available)
            import yfinance as yf
            ticker = yf.Ticker(asset)
            info = ticker.info
            
            sector = info.get('sector', None)
            if sector:
                self.api_cache[asset] = sector
                return sector
                
        except Exception as e:
            print(f"Could not get API sector for {asset}: {e}")
        
        return None
    
    def _behavioral_classification(self, asset: str, current_date: datetime) -> Optional[str]:
        """
        Classify based on price behavior and correlations with known sector ETFs
        """
        try:
            # Get price data for asset
            asset_data = self._get_price_data(asset, current_date, lookback_days=90)
            
            # Calculate correlations with sector ETFs
            sector_etfs = {
                'Technology': 'XLK',
                'Healthcare': 'XLV', 
                'Financials': 'XLF',
                'Consumer Discretionary': 'XLY',
                'Energy': 'XLE',
                'Industrials': 'XLI',
                'Utilities': 'XLU',
                'Materials': 'XLB',
                'Real Estate': 'XLRE',
                'Consumer Staples': 'XLP',
                'Communication': 'XLC'
            }
            
            correlations = {}
            for sector, etf in sector_etfs.items():
                etf_data = self._get_price_data(etf, current_date, lookback_days=90)
                if asset_data is not None and etf_data is not None:
                    correlation = self._calculate_correlation(asset_data, etf_data)
                    correlations[sector] = correlation
            
            # Return sector with highest correlation (if above threshold)
            if correlations:
                best_sector = max(correlations, key=correlations.get)
                best_correlation = correlations[best_sector]
                
                if best_correlation > 0.7:  # High correlation threshold
                    self.behavior_cache[asset] = best_sector
                    return best_sector
                    
        except Exception as e:
            print(f"Behavioral classification failed for {asset}: {e}")
        
        return None
    
    def _hardcoded_classification(self, asset: str) -> str:
        """
        Fallback hardcoded mapping for known assets
        """
        STATIC_MAPPING = {
            # Technology
            'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology', 
            'NVDA': 'Technology', 'META': 'Technology', 'TSLA': 'Technology',
            
            # Financials  
            'JPM': 'Financials', 'BAC': 'Financials', 'WFC': 'Financials',
            'GS': 'Financials', 'MS': 'Financials',
            
            # Healthcare
            'JNJ': 'Healthcare', 'PFE': 'Healthcare', 'UNH': 'Healthcare',
            
            # Energy
            'XOM': 'Energy', 'CVX': 'Energy', 'COP': 'Energy',
            
            # Consumer
            'AMZN': 'Consumer Discretionary', 'HD': 'Consumer Discretionary',
            'WMT': 'Consumer Staples', 'PG': 'Consumer Staples',
        }
        
        return STATIC_MAPPING.get(asset, 'Unknown')
```

#### **2. Dynamic Correlation Management**
```python
class DynamicCorrelationManager:
    def __init__(self, window_days=60, update_frequency='daily', 
                 regime_aware=True):
        self.window_days = window_days
        self.update_frequency = update_frequency
        self.regime_aware = regime_aware
        self.correlation_matrix = {}
        self.last_update = None
        
    def get_correlation(self, asset1: str, asset2: str, 
                       current_date: datetime) -> float:
        """
        Get correlation between two assets with dynamic updates
        """
        if self._needs_update(current_date):
            self._update_correlations(current_date)
        
        pair_key = tuple(sorted([asset1, asset2]))
        return self.correlation_matrix.get(pair_key, 0.0)
    
    def _update_correlations(self, current_date: datetime):
        """
        Update correlation matrix with recent data
        """
        try:
            # Get all current portfolio assets + candidates
            all_assets = self._get_all_relevant_assets()
            
            # Calculate correlations for all pairs
            for i, asset1 in enumerate(all_assets):
                for asset2 in all_assets[i+1:]:
                    correlation = self._calculate_pair_correlation(
                        asset1, asset2, current_date
                    )
                    
                    pair_key = tuple(sorted([asset1, asset2]))
                    self.correlation_matrix[pair_key] = correlation
            
            self.last_update = current_date
            
        except Exception as e:
            print(f"Correlation update failed: {e}")
    
    def _calculate_pair_correlation(self, asset1: str, asset2: str, 
                                  current_date: datetime) -> float:
        """
        Calculate correlation between two assets
        """
        try:
            # Get price data for both assets
            data1 = self._get_price_data(asset1, current_date, self.window_days)
            data2 = self._get_price_data(asset2, current_date, self.window_days)
            
            if data1 is None or data2 is None:
                return 0.0
            
            # Calculate returns
            returns1 = data1.pct_change().dropna()
            returns2 = data2.pct_change().dropna()
            
            # Align dates
            common_dates = returns1.index.intersection(returns2.index)
            if len(common_dates) < 30:  # Need minimum data points
                return 0.0
            
            aligned_returns1 = returns1.loc[common_dates]
            aligned_returns2 = returns2.loc[common_dates]
            
            # Calculate correlation
            correlation = aligned_returns1.corr(aligned_returns2)
            
            # Handle regime-aware correlation if enabled
            if self.regime_aware:
                correlation = self._adjust_for_regime(correlation, current_date)
            
            return correlation if not pd.isna(correlation) else 0.0
            
        except Exception as e:
            print(f"Correlation calculation failed for {asset1}-{asset2}: {e}")
            return 0.0
    
    def _adjust_for_regime(self, correlation: float, current_date: datetime) -> float:
        """
        Adjust correlation based on current market regime
        """
        # During stress periods, correlations tend to increase
        # This is a simplified approach - could be more sophisticated
        
        try:
            # Get current regime (you'd integrate with your regime detector)
            current_regime = self._get_current_regime(current_date)
            
            if current_regime in ['Deflation', 'Crisis']:
                # Correlations tend to spike during crisis
                return min(0.95, correlation * 1.3)
            elif current_regime == 'Goldilocks':
                # Correlations tend to be lower in calm periods
                return max(-0.95, correlation * 0.8)
            else:
                return correlation
                
        except Exception:
            return correlation
```

#### **3. Sector Concentration with Dynamic Classification**
```python
class DynamicSectorManager:
    def __init__(self, sector_classifier, max_sector_allocation=0.3):
        self.sector_classifier = sector_classifier
        self.max_sector_allocation = max_sector_allocation
        
    def check_sector_concentration(self, proposed_portfolio: List[PositionScore],
                                 current_date: datetime) -> List[PositionScore]:
        """
        Enforce sector concentration limits with dynamic classification
        """
        # Classify all assets by sector
        sector_allocations = defaultdict(float)
        asset_sectors = {}
        
        for position in proposed_portfolio:
            sector = self.sector_classifier.get_asset_sector(
                position.asset, current_date
            )
            asset_sectors[position.asset] = sector
            sector_allocations[sector] += position.position_size_percentage
        
        # Check for violations
        violations = []
        for sector, allocation in sector_allocations.items():
            if allocation > self.max_sector_allocation:
                violations.append((sector, allocation))
        
        if not violations:
            return proposed_portfolio
        
        # Fix violations by reducing position sizes proportionally
        final_portfolio = []
        for position in proposed_portfolio:
            sector = asset_sectors[position.asset]
            
            # Check if this sector is over-allocated
            sector_violation = next(
                (v for v in violations if v[0] == sector), None
            )
            
            if sector_violation:
                # Scale down proportionally
                sector, over_allocation = sector_violation
                scale_factor = self.max_sector_allocation / over_allocation
                position.position_size_percentage *= scale_factor
                position.sector_scaled = True
                position.scale_factor = scale_factor
            
            final_portfolio.append(position)
        
        return final_portfolio
```

### **Implementation Recommendation: Hybrid Approach**

#### **Best Practice Configuration:**
```python
# Recommended hybrid setup
sector_classifier = DynamicSectorClassifier(classification_mode='hybrid')
correlation_manager = DynamicCorrelationManager(
    window_days=60,           # 3-month correlation window
    update_frequency='daily', # Update correlations daily
    regime_aware=True        # Adjust for market regime
)

# With fallback hierarchy:
# 1. Manual overrides (for special cases)
# 2. Behavioral classification (most current)
# 3. API classification (reliable baseline)
# 4. Hardcoded mapping (ultimate fallback)
```

#### **Why Hybrid is Superior:**
1. **Adaptability**: Captures changing business models (e.g., Tesla's evolution)
2. **Reliability**: API data provides stable baseline
3. **Currency**: Behavioral analysis reflects current market perception
4. **Robustness**: Multiple fallback levels prevent system failures
5. **Accuracy**: Manual overrides handle edge cases

#### **Performance Considerations:**
- **Cache API results** to minimize external calls
- **Update correlations incrementally** rather than full recalculation
- **Parallel processing** for correlation matrix updates
- **Regime-aware caching** to avoid recalculation during stable periods

This hybrid approach gives you the **flexibility of dynamic classification** with the **reliability of established methods**, making it suitable for institutional-grade portfolio management while maintaining the configurability our system requires.

### **Integration with Existing Bucket System**

#### **Buckets vs Sectors: Complementary Diversification**
```python
# BUCKETS: Strategic/Regime-based classification
buckets = {
    'Risk Assets': ['AAPL', 'TSLA', 'NVDA'],      # Regime-driven grouping
    'Defensive Assets': ['JNJ', 'PG', 'KO'],      # Defensive characteristics
    'International': ['EFA', 'EEM', 'VGK']       # Geographic diversification
}

# SECTORS: Fundamental business classification  
sectors = {
    'Technology': ['AAPL', 'NVDA'],               # Business model similarity
    'Consumer Staples': ['PG', 'KO'],             # Industry classification
    'Healthcare': ['JNJ'],                        # Regulatory environment
}

# CORRELATION: Behavioral similarity (dynamic)
correlations = {
    ('AAPL', 'TSLA'): 0.73,                      # High tech correlation
    ('PG', 'KO'): 0.81,                          # Consumer staples correlation
    ('AAPL', 'JNJ'): 0.12                        # Low cross-sector correlation
}
```

#### **Multi-Layer Diversification Strategy**
```python
class MultilayerDiversificationManager:
    def __init__(self, bucket_manager, sector_manager, correlation_manager):
        self.bucket_manager = bucket_manager
        self.sector_manager = sector_manager
        self.correlation_manager = correlation_manager
    
    def apply_comprehensive_diversification(self, scored_assets, current_date):
        """
        Apply diversification constraints in order of priority
        """
        
        # LAYER 1: Bucket diversification (regime-based, highest priority)
        bucket_filtered = self.bucket_manager.apply_bucket_constraints(scored_assets)
        
        # LAYER 2: Sector diversification (fundamental business risk)
        sector_filtered = self.sector_manager.check_sector_concentration(
            bucket_filtered, current_date
        )
        
        # LAYER 3: Correlation diversification (behavioral risk)
        final_portfolio = self.correlation_manager.apply_correlation_limits(
            sector_filtered, current_date
        )
        
        return final_portfolio
    
    def get_diversification_report(self, portfolio, current_date):
        """
        Generate comprehensive diversification analysis
        """
        return {
            'bucket_distribution': self._analyze_bucket_distribution(portfolio),
            'sector_distribution': self._analyze_sector_distribution(portfolio, current_date),
            'correlation_matrix': self._analyze_correlations(portfolio, current_date),
            'diversification_score': self._calculate_overall_diversification_score(portfolio, current_date)
        }
```

#### **Configuration Hierarchy**
```bash
# Configuration priority (high to low):
--max-positions-per-bucket 4         # HIGHEST: Strategic regime allocation
--max-bucket-allocation 0.4          # 
--max-sector-allocation 0.3          # MIDDLE: Fundamental risk management
--correlation-limit 0.8              # LOWEST: Behavioral risk management

# Example conflict resolution:
# If bucket limits allow 5 tech stocks but sector limits allow only 3
# → Sector limit wins (more restrictive = safer)
```

#### **Real-World Example**
```python
# Scenario: Goldilocks regime favors "Risk Assets" bucket
regime_assets = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL', 'META', 'AMZN']

# Step 1: Bucket filter (max 4 from Risk Assets bucket)
bucket_selected = ['AAPL', 'MSFT', 'NVDA', 'TSLA']  # Top 4 by score

# Step 2: Sector filter (max 30% in Technology)
# AAPL, MSFT, NVDA all Technology → 3 * 10% = 30% (at limit)
# TSLA reclassified as Technology via behavioral analysis → Would exceed 30%
sector_adjusted = ['AAPL', 'MSFT', 'NVDA']  # TSLA removed for sector limit

# Step 3: Add back TSLA if correlation with others is low enough
correlation_check = check_correlations(['AAPL', 'MSFT', 'NVDA'], 'TSLA')
if max(correlation_check) < 0.8:
    final_portfolio = ['AAPL', 'MSFT', 'NVDA', 'TSLA']
else:
    final_portfolio = ['AAPL', 'MSFT', 'NVDA']  # Too correlated
```

#### **Performance Optimization**
```python
# Cache strategy for efficiency
class EfficientDiversificationManager:
    def __init__(self):
        self.sector_cache = TTLCache(maxsize=1000, ttl=86400)  # 24h cache
        self.correlation_cache = TTLCache(maxsize=10000, ttl=3600)  # 1h cache
        
    def get_cached_sector(self, asset, date):
        cache_key = f"{asset}_{date.strftime('%Y-%m-%d')}"
        return self.sector_cache.get(cache_key)
    
    def parallel_correlation_update(self, assets, date):
        """Update correlations in parallel for performance"""
        with ThreadPoolExecutor(max_workers=4) as executor:
            correlation_tasks = []
            for i, asset1 in enumerate(assets):
                for asset2 in assets[i+1:]:
                    task = executor.submit(
                        self._calculate_correlation, asset1, asset2, date
                    )
                    correlation_tasks.append((asset1, asset2, task))
            
            # Collect results
            for asset1, asset2, task in correlation_tasks:
                try:
                    correlation = task.result(timeout=30)
                    self._cache_correlation(asset1, asset2, correlation, date)
                except Exception as e:
                    print(f"Correlation calculation failed for {asset1}-{asset2}: {e}")
```

This **multi-layer approach** ensures robust diversification across:
1. **Strategic dimensions** (buckets/regimes)
2. **Fundamental dimensions** (sectors/industries)  
3. **Behavioral dimensions** (correlations/co-movements)

The dynamic classification makes it **adaptive to market evolution** while the hybrid approach ensures **reliability and performance** suitable for institutional use.

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

# Diversification
('diversification_mode', 'balanced'),  # 'strict'|'balanced'|'aggressive'
('sector_concentration_limit', 0.3),
('correlation_limit', 0.8),
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

# Diversification
--diversification-mode balanced
--sector-concentration-limit 0.3
--correlation-limit 0.8
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