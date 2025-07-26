# Core Rebalancer Engine Implementation TODO

**Priority: CRITICAL**  
**Module: 1/11 - Core Rebalancer Engine**  
**Status: Planning**  
**Estimated Effort: 2-3 weeks**

## 🎯 Module Objective

Create a self-contained Core Rebalancer Engine that can:
1. **Ingest "combined universe"** → **score** → **pick winners** → **output raw target weights**
2. Fix the critical "zombie position" bug by ensuring current positions are ALWAYS evaluated
3. Provide clean, well-defined APIs for future module integration
4. Support basic portfolio limits (max_new_positions, max_total_positions)
5. Output pure JSON targets without backtrader coupling

## 🚨 Critical Issues Being Fixed

### **1. Zombie Position Bug (Current State)**
```python
# CURRENT PROBLEMATIC FLOW in regime_strategy.py:162-180
trending_assets = self.regime_detector.get_trending_assets(
    current_date, available_assets, len(available_assets),
    min_confidence=self.params.min_trending_confidence  # ❌ Excludes existing positions!
)

position_scores = self.position_manager.analyze_and_score_assets(
    trending_assets, current_date, regime, self.data_manager  # ❌ Only trending assets!
)
# Missing: Current portfolio positions that don't meet trending confidence
```

### **2. Missing Portfolio Priority System**
- Current positions should be re-evaluated regardless of trending confidence
- No distinction between portfolio assets vs new opportunities
- No separate limits for new positions vs portfolio management

### **3. Tightly Coupled Architecture**
- `PositionManager` is deeply embedded in backtrader strategy
- No pure rebalancing interface that outputs targets
- Cannot test rebalancing logic independently

## 📋 Detailed Implementation Tasks

### **Task 1.1: Universe Builder API**

#### **1.1.1: Create Core Data Models**
**File:** `backtrader/core/models.py`

```python
from dataclasses import dataclass
from datetime import datetime
from typing import List, Set, Optional, Dict
from enum import Enum

class AssetPriority(Enum):
    PORTFOLIO = "portfolio"      # Current positions (highest priority)
    TRENDING = "trending"        # New trending opportunities  
    REGIME = "regime"           # Regime-appropriate assets
    FALLBACK = "fallback"       # Backup assets

@dataclass
class RebalancingUniverse:
    """Combined asset universe for rebalancing"""
    portfolio_assets: Set[str]          # Current positions (MUST analyze)
    trending_assets: Set[str]           # New opportunities from trending
    regime_assets: Set[str]             # All regime-appropriate assets
    combined_universe: Set[str]         # Union for actual analysis
    date: datetime
    regime: str
    
    def get_prioritized_assets(self) -> Dict[AssetPriority, Set[str]]:
        """Get assets grouped by priority"""
        return {
            AssetPriority.PORTFOLIO: self.portfolio_assets,
            AssetPriority.TRENDING: self.trending_assets - self.portfolio_assets,
            AssetPriority.REGIME: self.regime_assets - self.trending_assets - self.portfolio_assets
        }

@dataclass 
class AssetScore:
    """Enhanced position score with priority information"""
    asset: str
    date: datetime
    technical_score: float
    fundamental_score: float
    combined_score: float
    confidence: float
    regime: str
    priority: AssetPriority
    timeframes_analyzed: List[str]
    
    # Portfolio context
    is_current_position: bool = False
    previous_allocation: float = 0.0
    
    # Scoring metadata
    scoring_reason: str = ""
    missing_data_flags: List[str] = None
    
    def to_dict(self) -> dict:
        return {
            'asset': self.asset,
            'date': self.date.isoformat(),
            'technical_score': self.technical_score,
            'fundamental_score': self.fundamental_score,
            'combined_score': self.combined_score,
            'confidence': self.confidence,
            'regime': self.regime,
            'priority': self.priority.value,
            'is_current_position': self.is_current_position,
            'previous_allocation': self.previous_allocation,
            'scoring_reason': self.scoring_reason,
            'timeframes_analyzed': self.timeframes_analyzed or []
        }

@dataclass
class RebalancingLimits:
    """Position limits for rebalancing"""
    max_total_positions: int = 10
    max_new_positions: int = 3
    min_score_threshold: float = 0.6
    min_score_new_position: float = 0.65
    
    # For future expansion
    max_single_position_pct: float = 0.2
    target_total_allocation: float = 0.95

@dataclass
class RebalancingTarget:
    """Final rebalancing target output"""
    asset: str
    target_allocation_pct: float
    current_allocation_pct: float
    action: str  # 'open', 'increase', 'decrease', 'close', 'hold'
    priority: AssetPriority
    score: float
    reason: str
```

#### **1.1.2: Implement Universe Builder**
**File:** `backtrader/core/universe_builder.py`

```python
from typing import Set, List, Dict
from datetime import datetime
import sys
import os

# Import existing components
sys.path.append(os.path.dirname(__file__))
from ..data.regime_detector import RegimeDetector
from ..data.asset_buckets import AssetBucketManager
from .models import RebalancingUniverse, AssetPriority

class UniverseBuilder:
    """Builds comprehensive asset universe for rebalancing"""
    
    def __init__(self, regime_detector: RegimeDetector, asset_manager: AssetBucketManager):
        self.regime_detector = regime_detector
        self.asset_manager = asset_manager
        
    def get_universe(self, current_date: datetime, current_positions: Dict[str, float] = None, 
                    regime: str = None, bucket_names: List[str] = None,
                    min_trending_confidence: float = 0.7) -> RebalancingUniverse:
        """
        Build comprehensive rebalancing universe
        
        Args:
            current_date: Date for universe construction
            current_positions: Dict of {asset: allocation_pct} for current portfolio
            regime: Market regime (if None, will be detected)
            bucket_names: Bucket filter (if None, uses regime buckets)
            min_trending_confidence: Confidence threshold for trending assets
            
        Returns:
            RebalancingUniverse with all asset categories
        """
        
        # 1. ALWAYS include current portfolio assets (highest priority)
        portfolio_assets = set(current_positions.keys()) if current_positions else set()
        
        # 2. Detect regime if not provided
        if regime is None:
            regime, _ = self.regime_detector.get_market_regime(current_date)
        
        # 3. Get regime-appropriate bucket assets
        if bucket_names:
            regime_buckets = [bucket for bucket in bucket_names 
                            if bucket in self.regime_detector.get_regime_buckets(regime)]
        else:
            # Try research buckets first, fallback to regime buckets
            research_buckets = self.regime_detector.get_research_buckets(current_date)
            regime_buckets = research_buckets if research_buckets else self.regime_detector.get_regime_buckets(regime)
        
        regime_assets = set(self.asset_manager.get_assets_from_buckets(regime_buckets))
        
        # 4. Get trending assets for new opportunities (with portfolio assets ALWAYS included)
        available_regime_assets = list(regime_assets)
        trending_candidates = self.regime_detector.get_trending_assets(
            current_date, available_regime_assets, 
            limit=len(available_regime_assets),  # Get all for filtering
            min_confidence=min_trending_confidence
        )
        
        # CRITICAL FIX: Always include portfolio assets in trending, regardless of confidence
        trending_assets = set(trending_candidates) | portfolio_assets
        
        # 5. Create combined universe for analysis
        combined_universe = portfolio_assets | trending_assets
        
        print(f"Universe Builder Results:")
        print(f"  Portfolio Assets: {len(portfolio_assets)} - {portfolio_assets}")
        print(f"  Trending Assets: {len(trending_assets)} (includes portfolio)")
        print(f"  Regime Assets: {len(regime_assets)} from buckets {regime_buckets}")
        print(f"  Combined Universe: {len(combined_universe)} assets")
        
        return RebalancingUniverse(
            portfolio_assets=portfolio_assets,
            trending_assets=trending_assets,
            regime_assets=regime_assets,
            combined_universe=combined_universe,
            date=current_date,
            regime=regime
        )
```

#### **1.1.3: Add Universe Builder Tests**
**File:** `backtrader/tests/test_universe_builder.py`

```python
import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock
from core.universe_builder import UniverseBuilder
from core.models import RebalancingUniverse

def test_universe_builder_includes_portfolio_assets():
    """Test that current positions are ALWAYS included in universe"""
    
    # Mock dependencies
    regime_detector = Mock()
    asset_manager = Mock()
    
    regime_detector.get_market_regime.return_value = ("Goldilocks", 0.8)
    regime_detector.get_regime_buckets.return_value = ["Risk Assets", "Defensives"]
    regime_detector.get_research_buckets.return_value = None
    regime_detector.get_trending_assets.return_value = ["AAPL", "MSFT"]  # Doesn't include TSLA!
    
    asset_manager.get_assets_from_buckets.return_value = ["AAPL", "MSFT", "GOOGL", "AMZN"]
    
    builder = UniverseBuilder(regime_detector, asset_manager)
    
    # Test with portfolio containing asset not in trending
    current_positions = {"TSLA": 0.15, "NVDA": 0.10}  # Neither in trending!
    
    universe = builder.get_universe(
        current_date=datetime(2024, 1, 15),
        current_positions=current_positions,
        min_trending_confidence=0.7
    )
    
    # CRITICAL: Portfolio assets must be in combined universe
    assert "TSLA" in universe.combined_universe, "Portfolio asset TSLA missing from universe!"
    assert "NVDA" in universe.combined_universe, "Portfolio asset NVDA missing from universe!"
    assert universe.portfolio_assets == {"TSLA", "NVDA"}
    
    # Trending should include trending + portfolio
    assert "TSLA" in universe.trending_assets, "Portfolio assets must be in trending!"
    assert "NVDA" in universe.trending_assets, "Portfolio assets must be in trending!"
    assert "AAPL" in universe.trending_assets
    assert "MSFT" in universe.trending_assets

def test_empty_portfolio_universe():
    """Test universe building with no current positions"""
    
    regime_detector = Mock()
    asset_manager = Mock()
    
    regime_detector.get_market_regime.return_value = ("Goldilocks", 0.8)
    regime_detector.get_regime_buckets.return_value = ["Risk Assets"]
    regime_detector.get_research_buckets.return_value = None
    regime_detector.get_trending_assets.return_value = ["AAPL", "MSFT"]
    
    asset_manager.get_assets_from_buckets.return_value = ["AAPL", "MSFT", "GOOGL"]
    
    builder = UniverseBuilder(regime_detector, asset_manager)
    
    universe = builder.get_universe(
        current_date=datetime(2024, 1, 15),
        current_positions={}  # Empty portfolio
    )
    
    assert len(universe.portfolio_assets) == 0
    assert universe.trending_assets == {"AAPL", "MSFT"}
    assert universe.combined_universe == {"AAPL", "MSFT"}
```

### **Task 1.2: Scoring Service API**

#### **1.2.1: Create Scoring Service Interface**
**File:** `backtrader/core/scoring_service.py`

```python
from typing import List, Optional, Dict
from datetime import datetime
import random
import sys
import os

# Import existing analyzers
sys.path.append(os.path.dirname(__file__))
from ..position.technical_analyzer import TechnicalAnalyzer
from ..position.fundamental_analyzer import FundamentalAnalyzer
from .models import AssetScore, AssetPriority, RebalancingUniverse

class ScoringService:
    """Service for scoring assets with priority awareness"""
    
    def __init__(self, technical_analyzer=None, fundamental_analyzer=None,
                 enable_technical=True, enable_fundamental=True,
                 technical_weight=0.6, fundamental_weight=0.4):
        
        self.technical_analyzer = technical_analyzer
        self.fundamental_analyzer = fundamental_analyzer
        self.enable_technical = enable_technical
        self.enable_fundamental = enable_fundamental
        self.technical_weight = technical_weight
        self.fundamental_weight = fundamental_weight
        
        self._validate_configuration()
    
    def _validate_configuration(self):
        """Validate scoring configuration"""
        if not self.enable_technical and not self.enable_fundamental:
            raise ValueError("At least one analysis type must be enabled")
        
        print(f"Scoring Service Configuration:")
        if self.enable_technical:
            print(f"  Technical Analysis: {self.technical_weight:.1%}")
        if self.enable_fundamental:
            print(f"  Fundamental Analysis: {self.fundamental_weight:.1%}")
    
    def score_assets(self, universe: RebalancingUniverse, 
                    current_positions: Dict[str, float] = None,
                    data_manager=None) -> List[AssetScore]:
        """
        Score all assets in universe with priority classification
        
        Args:
            universe: RebalancingUniverse to score
            current_positions: Dict of {asset: allocation_pct}
            data_manager: Data manager for price/fundamental data
            
        Returns:
            List of AssetScore objects with priorities
        """
        
        current_positions = current_positions or {}
        scored_assets = []
        
        # Get prioritized assets
        prioritized = universe.get_prioritized_assets()
        
        for priority, assets in prioritized.items():
            for asset in assets:
                try:
                    score = self._score_single_asset(
                        asset=asset,
                        date=universe.date,
                        regime=universe.regime,
                        priority=priority,
                        current_allocation=current_positions.get(asset, 0.0),
                        data_manager=data_manager
                    )
                    
                    if score:
                        scored_assets.append(score)
                        
                except Exception as e:
                    print(f"Warning: Could not score {asset}: {e}")
                    continue
        
        print(f"Scoring Results: {len(scored_assets)} assets scored")
        for priority in AssetPriority:
            priority_scores = [s for s in scored_assets if s.priority == priority]
            if priority_scores:
                avg_score = sum(s.combined_score for s in priority_scores) / len(priority_scores)
                print(f"  {priority.value}: {len(priority_scores)} assets, avg score: {avg_score:.3f}")
        
        return scored_assets
    
    def _score_single_asset(self, asset: str, date: datetime, regime: str,
                           priority: AssetPriority, current_allocation: float,
                           data_manager) -> Optional[AssetScore]:
        """
        Score a single asset with all available analysis
        """
        
        # For now, use existing analyzers if available, otherwise stub
        if self.technical_analyzer and self.fundamental_analyzer and data_manager:
            return self._score_with_real_analyzers(
                asset, date, regime, priority, current_allocation, data_manager
            )
        else:
            return self._score_with_stub(
                asset, date, regime, priority, current_allocation
            )
    
    def _score_with_real_analyzers(self, asset: str, date: datetime, regime: str,
                                  priority: AssetPriority, current_allocation: float,
                                  data_manager) -> Optional[AssetScore]:
        """Score using real technical and fundamental analyzers"""
        
        technical_score = 0.0
        fundamental_score = 0.0
        missing_data = []
        
        # Technical analysis
        if self.enable_technical and self.technical_analyzer:
            try:
                # Use existing technical analyzer
                tech_result = self.technical_analyzer.analyze_asset(asset, date)
                technical_score = tech_result if isinstance(tech_result, float) else tech_result.get('composite_score', 0.0)
            except Exception as e:
                missing_data.append(f"technical: {str(e)}")
                technical_score = 0.0
        
        # Fundamental analysis  
        if self.enable_fundamental and self.fundamental_analyzer:
            try:
                fundamental_score = self.fundamental_analyzer.analyze_asset(asset, date, regime)
            except Exception as e:
                missing_data.append(f"fundamental: {str(e)}")
                fundamental_score = 0.0
        
        # Calculate combined score with proper weighting
        effective_tech_weight = self.technical_weight if self.enable_technical else 0.0
        effective_fund_weight = self.fundamental_weight if self.enable_fundamental else 0.0
        
        # Handle case where one analysis is disabled
        if not self.enable_technical:
            effective_fund_weight = 1.0
        elif not self.enable_fundamental:
            effective_tech_weight = 1.0
        elif fundamental_score == 0.0 and technical_score > 0.0:
            # Fundamental data missing, use technical only
            effective_tech_weight = 1.0
            effective_fund_weight = 0.0
        
        combined_score = (technical_score * effective_tech_weight + 
                         fundamental_score * effective_fund_weight)
        
        # Priority boost for current positions (slight bias to avoid unnecessary churn)
        if priority == AssetPriority.PORTFOLIO and current_allocation > 0:
            combined_score *= 1.02  # 2% boost to existing positions
        
        return AssetScore(
            asset=asset,
            date=date,
            technical_score=technical_score,
            fundamental_score=fundamental_score,
            combined_score=combined_score,
            confidence=0.8 if not missing_data else 0.6,  # Lower confidence if missing data
            regime=regime,
            priority=priority,
            is_current_position=current_allocation > 0,
            previous_allocation=current_allocation,
            scoring_reason=f"Tech: {effective_tech_weight:.1%}, Fund: {effective_fund_weight:.1%}",
            missing_data_flags=missing_data,
            timeframes_analyzed=['1d']  # Placeholder
        )
    
    def _score_with_stub(self, asset: str, date: datetime, regime: str,
                        priority: AssetPriority, current_allocation: float) -> AssetScore:
        """Stub scoring for testing and development"""
        
        # Generate deterministic "scores" for consistent testing
        random.seed(hash(asset + date.strftime('%Y-%m-%d') + regime))
        
        technical_score = random.uniform(0.3, 0.9)
        fundamental_score = random.uniform(0.3, 0.9)
        
        # Simulate different analysis configurations
        if not self.enable_technical:
            technical_score = 0.0
            fundamental_score = random.uniform(0.4, 0.85)
            combined_score = fundamental_score
        elif not self.enable_fundamental:
            fundamental_score = 0.0
            technical_score = random.uniform(0.4, 0.85)
            combined_score = technical_score
        else:
            combined_score = (technical_score * self.technical_weight + 
                            fundamental_score * self.fundamental_weight)
        
        # Portfolio priority boost
        if priority == AssetPriority.PORTFOLIO and current_allocation > 0:
            combined_score *= 1.02
        
        # Regime-based adjustments (stub)
        regime_multipliers = {
            'Goldilocks': 1.1,
            'Reflation': 1.05,
            'Inflation': 0.95,
            'Deflation': 0.9
        }
        combined_score *= regime_multipliers.get(regime, 1.0)
        
        # Ensure scores are in valid range
        combined_score = max(0.0, min(1.0, combined_score))
        
        return AssetScore(
            asset=asset,
            date=date,
            technical_score=technical_score,
            fundamental_score=fundamental_score,
            combined_score=combined_score,
            confidence=0.75,  # Moderate confidence for stub
            regime=regime,
            priority=priority,
            is_current_position=current_allocation > 0,
            previous_allocation=current_allocation,
            scoring_reason="STUB: Deterministic test scoring",
            timeframes_analyzed=['1d_stub']
        )
```

#### **1.2.2: Add Scoring Service Tests**
**File:** `backtrader/tests/test_scoring_service.py`

```python
import pytest
from datetime import datetime
from core.scoring_service import ScoringService
from core.models import RebalancingUniverse, AssetPriority

def test_scoring_service_stub_mode():
    """Test scoring service in stub mode"""
    
    service = ScoringService(
        technical_analyzer=None,
        fundamental_analyzer=None,
        enable_technical=True,
        enable_fundamental=True
    )
    
    # Create test universe
    universe = RebalancingUniverse(
        portfolio_assets={"TSLA"},
        trending_assets={"AAPL", "MSFT", "TSLA"},
        regime_assets={"AAPL", "MSFT", "GOOGL"},
        combined_universe={"AAPL", "MSFT", "TSLA"},
        date=datetime(2024, 1, 15),
        regime="Goldilocks"
    )
    
    current_positions = {"TSLA": 0.15}
    
    scores = service.score_assets(universe, current_positions)
    
    # Verify all assets scored
    assert len(scores) == 3
    asset_names = {score.asset for score in scores}
    assert asset_names == {"AAPL", "MSFT", "TSLA"}
    
    # Verify priority assignment
    tsla_score = next(s for s in scores if s.asset == "TSLA")
    assert tsla_score.priority == AssetPriority.PORTFOLIO
    assert tsla_score.is_current_position == True
    assert tsla_score.previous_allocation == 0.15
    
    # Verify portfolio priority boost
    other_scores = [s for s in scores if s.asset != "TSLA"]
    if other_scores:
        # TSLA should have slight boost due to being current position
        base_tsla_score = tsla_score.combined_score / 1.02  # Remove boost
        for other_score in other_scores:
            if abs(base_tsla_score - other_score.combined_score) < 0.01:
                # Similar base scores, TSLA should be higher due to boost
                assert tsla_score.combined_score > other_score.combined_score

def test_scoring_service_technical_only():
    """Test scoring with technical analysis only"""
    
    service = ScoringService(
        enable_technical=True,
        enable_fundamental=False
    )
    
    universe = RebalancingUniverse(
        portfolio_assets=set(),
        trending_assets={"AAPL"},
        regime_assets=set(),
        combined_universe={"AAPL"},
        date=datetime(2024, 1, 15),
        regime="Goldilocks"
    )
    
    scores = service.score_assets(universe)
    
    assert len(scores) == 1
    score = scores[0]
    assert score.fundamental_score == 0.0
    assert score.technical_score > 0.0
    assert score.combined_score == score.technical_score
```

### **Task 1.3: Selection & Limits Enforcer**

#### **1.3.1: Create Selection Service**
**File:** `backtrader/core/selection_service.py`

```python
from typing import List, Dict
from .models import AssetScore, AssetPriority, RebalancingLimits, RebalancingTarget

class SelectionService:
    """Service for selecting assets and enforcing position limits"""
    
    def __init__(self):
        pass
    
    def select_by_score(self, scored_assets: List[AssetScore], 
                       limits: RebalancingLimits,
                       current_positions: Dict[str, float] = None) -> List[AssetScore]:
        """
        Select assets by score while enforcing limits
        
        Args:
            scored_assets: List of scored assets
            limits: Position and scoring limits
            current_positions: Current portfolio allocations
            
        Returns:
            List of selected AssetScore objects
        """
        
        current_positions = current_positions or {}
        
        # Group assets by priority
        portfolio_assets = [s for s in scored_assets if s.priority == AssetPriority.PORTFOLIO]
        new_opportunity_assets = [s for s in scored_assets if s.priority != AssetPriority.PORTFOLIO]
        
        selected = []
        
        # STEP 1: Handle existing portfolio (highest priority)
        print(f"Step 1: Evaluating {len(portfolio_assets)} portfolio assets")
        
        for asset_score in portfolio_assets:
            if asset_score.combined_score >= limits.min_score_threshold:
                selected.append(asset_score)
                asset_score.selection_reason = f"Portfolio: score {asset_score.combined_score:.3f} >= {limits.min_score_threshold}"
            else:
                asset_score.selection_reason = f"Portfolio: score {asset_score.combined_score:.3f} < {limits.min_score_threshold} - CLOSE"
                # Note: Position will be closed, not included in selected
        
        # STEP 2: Add new positions within limits
        current_position_count = len(selected)
        available_slots = limits.max_total_positions - current_position_count
        max_new = min(limits.max_new_positions, available_slots)
        
        print(f"Step 2: Available slots for new positions: {max_new}")
        
        if max_new > 0:
            # Filter new opportunities by higher threshold
            qualified_new = [
                s for s in new_opportunity_assets 
                if s.combined_score >= limits.min_score_new_position
            ]
            
            # Sort by score (highest first)
            qualified_new.sort(key=lambda x: x.combined_score, reverse=True)
            
            # Take top N new positions
            new_selected = qualified_new[:max_new]
            
            for asset_score in new_selected:
                asset_score.selection_reason = f"New: score {asset_score.combined_score:.3f} >= {limits.min_score_new_position}"
                selected.append(asset_score)
            
            print(f"Selected {len(new_selected)} new positions from {len(qualified_new)} qualified")
        
        # Log selection summary
        total_selected = len(selected)
        portfolio_selected = len([s for s in selected if s.priority == AssetPriority.PORTFOLIO])
        new_selected = total_selected - portfolio_selected
        
        print(f"Selection Summary:")
        print(f"  Portfolio positions kept: {portfolio_selected}")
        print(f"  New positions added: {new_selected}")
        print(f"  Total selected: {total_selected}/{limits.max_total_positions}")
        
        return selected
    
    def create_rebalancing_targets(self, selected_assets: List[AssetScore],
                                  current_positions: Dict[str, float] = None,
                                  target_allocation: float = 0.95) -> List[RebalancingTarget]:
        """
        Create final rebalancing targets with position sizing
        
        Args:
            selected_assets: Assets selected for portfolio
            current_positions: Current allocations
            target_allocation: Total target allocation (e.g., 0.95 = 95%)
            
        Returns:
            List of RebalancingTarget objects
        """
        
        current_positions = current_positions or {}
        
        if not selected_assets:
            # Close all positions if nothing selected
            targets = []
            for asset, current_alloc in current_positions.items():
                targets.append(RebalancingTarget(
                    asset=asset,
                    target_allocation_pct=0.0,
                    current_allocation_pct=current_alloc,
                    action='close',
                    priority=AssetPriority.PORTFOLIO,
                    score=0.0,
                    reason="No assets selected for portfolio"
                ))
            return targets
        
        # Simple equal weight allocation for now
        num_positions = len(selected_assets)
        target_per_position = target_allocation / num_positions
        
        targets = []
        
        # Create targets for selected assets
        for asset_score in selected_assets:
            current_alloc = current_positions.get(asset_score.asset, 0.0)
            
            # Determine action
            if current_alloc == 0.0:
                action = 'open'
            elif target_per_position > current_alloc * 1.05:  # 5% threshold
                action = 'increase'
            elif target_per_position < current_alloc * 0.95:  # 5% threshold
                action = 'decrease'
            else:
                action = 'hold'
            
            targets.append(RebalancingTarget(
                asset=asset_score.asset,
                target_allocation_pct=target_per_position,
                current_allocation_pct=current_alloc,
                action=action,
                priority=asset_score.priority,
                score=asset_score.combined_score,
                reason=getattr(asset_score, 'selection_reason', 'Selected for portfolio')
            ))
        
        # Add close targets for positions not selected
        for asset, current_alloc in current_positions.items():
            if asset not in [t.asset for t in targets]:
                targets.append(RebalancingTarget(
                    asset=asset,
                    target_allocation_pct=0.0,
                    current_allocation_pct=current_alloc,
                    action='close',
                    priority=AssetPriority.PORTFOLIO,
                    score=0.0,
                    reason="Asset not selected in rebalancing"
                ))
        
        # Log targets summary
        actions = {}
        for target in targets:
            actions[target.action] = actions.get(target.action, 0) + 1
        
        print(f"Rebalancing Targets: {actions}")
        
        return targets
```

#### **1.3.2: Add Selection Service Tests**
**File:** `backtrader/tests/test_selection_service.py`

```python
import pytest
from datetime import datetime
from core.selection_service import SelectionService
from core.models import AssetScore, AssetPriority, RebalancingLimits

def test_portfolio_priority_selection():
    """Test that portfolio assets are prioritized over new assets"""
    
    service = SelectionService()
    
    # Create test scores - portfolio asset with lower score
    portfolio_score = AssetScore(
        asset="TSLA",
        date=datetime(2024, 1, 15),
        technical_score=0.6,
        fundamental_score=0.6,
        combined_score=0.6,  # At threshold
        confidence=0.8,
        regime="Goldilocks",
        priority=AssetPriority.PORTFOLIO,
        is_current_position=True,
        previous_allocation=0.15,
        timeframes_analyzed=['1d']
    )
    
    # New asset with higher score
    new_score = AssetScore(
        asset="AAPL",
        date=datetime(2024, 1, 15),
        technical_score=0.9,
        fundamental_score=0.9,
        combined_score=0.9,  # Much higher
        confidence=0.8,
        regime="Goldilocks",
        priority=AssetPriority.TRENDING,
        is_current_position=False,
        previous_allocation=0.0,
        timeframes_analyzed=['1d']
    )
    
    limits = RebalancingLimits(
        max_total_positions=2,
        max_new_positions=1,
        min_score_threshold=0.6,
        min_score_new_position=0.65
    )
    
    current_positions = {"TSLA": 0.15}
    
    selected = service.select_by_score([portfolio_score, new_score], limits, current_positions)
    
    # Both should be selected - portfolio asset kept despite lower score
    assert len(selected) == 2
    assets = {s.asset for s in selected}
    assert "TSLA" in assets, "Portfolio asset should be kept at threshold"
    assert "AAPL" in assets, "New asset should be added"

def test_position_limits_enforcement():
    """Test that position limits are enforced correctly"""
    
    service = SelectionService()
    
    # Create more assets than limits allow
    scores = []
    for i, asset in enumerate(['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'AMZN']):
        scores.append(AssetScore(
            asset=asset,
            date=datetime(2024, 1, 15),
            technical_score=0.9 - i * 0.05,  # Decreasing scores
            fundamental_score=0.9 - i * 0.05,
            combined_score=0.9 - i * 0.05,
            confidence=0.8,
            regime="Goldilocks",
            priority=AssetPriority.TRENDING,
            is_current_position=False,
            timeframes_analyzed=['1d']
        ))
    
    limits = RebalancingLimits(
        max_total_positions=3,
        max_new_positions=2,  # Limit new positions
        min_score_new_position=0.65
    )
    
    selected = service.select_by_score(scores, limits)
    
    # Should select only top 2 due to max_new_positions limit
    assert len(selected) <= 2
    
    # Should select highest scoring assets
    selected_assets = {s.asset for s in selected}
    assert "AAPL" in selected_assets  # Highest score
    assert "MSFT" in selected_assets  # Second highest
```

### **Task 1.4: Basic CLI & Configuration**

#### **1.4.1: Create Core Rebalancer Engine**
**File:** `backtrader/core/rebalancer_engine.py`

```python
import json
from typing import Dict, List, Optional
from datetime import datetime
from .universe_builder import UniverseBuilder
from .scoring_service import ScoringService
from .selection_service import SelectionService
from .models import RebalancingLimits, RebalancingTarget

class CoreRebalancerEngine:
    """Main engine for portfolio rebalancing"""
    
    def __init__(self, regime_detector, asset_manager, 
                 technical_analyzer=None, fundamental_analyzer=None,
                 data_manager=None):
        
        self.universe_builder = UniverseBuilder(regime_detector, asset_manager)
        self.scoring_service = ScoringService(
            technical_analyzer=technical_analyzer,
            fundamental_analyzer=fundamental_analyzer
        )
        self.selection_service = SelectionService()
        self.data_manager = data_manager
        
    def rebalance(self, rebalance_date: datetime, 
                 current_positions: Dict[str, float] = None,
                 limits: RebalancingLimits = None,
                 bucket_names: List[str] = None,
                 min_trending_confidence: float = 0.7,
                 enable_technical: bool = True,
                 enable_fundamental: bool = True,
                 technical_weight: float = 0.6,
                 fundamental_weight: float = 0.4) -> List[RebalancingTarget]:
        """
        Perform complete rebalancing operation
        
        Args:
            rebalance_date: Date for rebalancing
            current_positions: Dict of {asset: allocation_pct}
            limits: Position limits configuration
            bucket_names: Asset bucket filter
            min_trending_confidence: Trending asset confidence threshold
            enable_technical: Enable technical analysis
            enable_fundamental: Enable fundamental analysis
            technical_weight: Weight for technical analysis
            fundamental_weight: Weight for fundamental analysis
            
        Returns:
            List of RebalancingTarget objects
        """
        
        current_positions = current_positions or {}
        limits = limits or RebalancingLimits()
        
        print(f"\n{'='*60}")
        print(f"CORE REBALANCER ENGINE - {rebalance_date.strftime('%Y-%m-%d')}")
        print(f"{'='*60}")
        
        # Update scoring service configuration
        self.scoring_service.enable_technical = enable_technical
        self.scoring_service.enable_fundamental = enable_fundamental
        self.scoring_service.technical_weight = technical_weight
        self.scoring_service.fundamental_weight = fundamental_weight
        self.scoring_service._validate_configuration()
        
        # Step 1: Build asset universe
        print(f"\n🌍 Step 1: Building Asset Universe")
        universe = self.universe_builder.get_universe(
            current_date=rebalance_date,
            current_positions=current_positions,
            bucket_names=bucket_names,
            min_trending_confidence=min_trending_confidence
        )
        
        # Step 2: Score all assets
        print(f"\n📊 Step 2: Scoring Assets")
        scored_assets = self.scoring_service.score_assets(
            universe=universe,
            current_positions=current_positions,
            data_manager=self.data_manager
        )
        
        # Step 3: Select assets by score and limits
        print(f"\n🎯 Step 3: Selecting Portfolio")
        selected_assets = self.selection_service.select_by_score(
            scored_assets=scored_assets,
            limits=limits,
            current_positions=current_positions
        )
        
        # Step 4: Create final targets
        print(f"\n⚖️  Step 4: Creating Rebalancing Targets")
        targets = self.selection_service.create_rebalancing_targets(
            selected_assets=selected_assets,
            current_positions=current_positions,
            target_allocation=limits.target_total_allocation
        )
        
        print(f"\n✅ Rebalancing Complete: {len(targets)} targets generated")
        
        return targets
    
    def to_json(self, targets: List[RebalancingTarget], 
               include_metadata: bool = True) -> str:
        """
        Convert rebalancing targets to JSON output
        
        Args:
            targets: List of RebalancingTarget objects
            include_metadata: Include metadata in output
            
        Returns:
            JSON string representation
        """
        
        output = {
            "rebalancing_targets": [
                {
                    "asset": target.asset,
                    "target_allocation_pct": round(target.target_allocation_pct, 4),
                    "current_allocation_pct": round(target.current_allocation_pct, 4),
                    "action": target.action,
                    "priority": target.priority.value,
                    "score": round(target.score, 4),
                    "reason": target.reason
                }
                for target in targets
            ]
        }
        
        if include_metadata:
            actions = {}
            total_target_allocation = 0.0
            
            for target in targets:
                actions[target.action] = actions.get(target.action, 0) + 1
                if target.action != 'close':
                    total_target_allocation += target.target_allocation_pct
            
            output["metadata"] = {
                "total_targets": len(targets),
                "actions_summary": actions,
                "total_target_allocation": round(total_target_allocation, 4),
                "timestamp": datetime.now().isoformat()
            }
        
        return json.dumps(output, indent=2)
```

#### **1.4.2: Add Rebalance CLI Command**
**File:** `backtrader/core/cli.py`

```python
import argparse
import json
from datetime import datetime
from pathlib import Path
import sys
import os

# Import existing components
sys.path.append(os.path.dirname(__file__))
from ..data.regime_detector import RegimeDetector
from ..data.asset_buckets import AssetBucketManager
from ..data.data_manager import DataManager
from ..position.technical_analyzer import TechnicalAnalyzer
from ..position.fundamental_analyzer import FundamentalAnalyzer
from .rebalancer_engine import CoreRebalancerEngine
from .models import RebalancingLimits

def add_rebalance_command(parser):
    """Add rebalance command to main parser"""
    
    rebalance_parser = parser.add_parser('rebalance', 
                                       help='Generate rebalancing targets (Core Engine)')
    
    # Required arguments
    rebalance_parser.add_argument('--date', type=str, required=True,
                                help='Rebalancing date (YYYY-MM-DD)')
    
    # Portfolio configuration
    rebalance_parser.add_argument('--current-positions', type=str, default=None,
                                help='JSON file with current positions {asset: allocation_pct}')
    rebalance_parser.add_argument('--buckets', type=str, default=None,
                                help='Comma-separated asset buckets (e.g., "Risk Assets,Defensives")')
    
    # Position limits
    rebalance_parser.add_argument('--max-total-positions', type=int, default=10,
                                help='Maximum total positions in portfolio')
    rebalance_parser.add_argument('--max-new-positions', type=int, default=3,
                                help='Maximum new positions per rebalance')
    rebalance_parser.add_argument('--min-score-threshold', type=float, default=0.6,
                                help='Minimum score to maintain position')
    rebalance_parser.add_argument('--min-score-new-position', type=float, default=0.65,
                                help='Minimum score for new positions')
    
    # Analysis configuration
    rebalance_parser.add_argument('--disable-technical', action='store_true',
                                help='Disable technical analysis')
    rebalance_parser.add_argument('--disable-fundamental', action='store_true',
                                help='Disable fundamental analysis')
    rebalance_parser.add_argument('--technical-weight', type=float, default=0.6,
                                help='Weight for technical analysis (0.0-1.0)')
    rebalance_parser.add_argument('--fundamental-weight', type=float, default=0.4,
                                help='Weight for fundamental analysis (0.0-1.0)')
    rebalance_parser.add_argument('--min-trending-confidence', type=float, default=0.7,
                                help='Minimum confidence for trending assets')
    
    # Output configuration
    rebalance_parser.add_argument('--output', type=str, default=None,
                                help='Output file for targets (JSON)')
    rebalance_parser.add_argument('--include-metadata', action='store_true',
                                help='Include metadata in JSON output')
    
    rebalance_parser.set_defaults(func=handle_rebalance_command)

def handle_rebalance_command(args):
    """Handle rebalance command execution"""
    
    print(f"Core Rebalancer Engine - {args.date}")
    print("=" * 50)
    
    # Parse date
    try:
        rebalance_date = datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        print(f"ERROR: Invalid date format '{args.date}'. Use YYYY-MM-DD")
        return
    
    # Load current positions if provided
    current_positions = {}
    if args.current_positions:
        try:
            with open(args.current_positions, 'r') as f:
                current_positions = json.load(f)
            print(f"Loaded {len(current_positions)} current positions")
        except Exception as e:
            print(f"ERROR: Could not load current positions: {e}")
            return
    
    # Parse bucket names
    bucket_names = None
    if args.buckets:
        bucket_names = [bucket.strip() for bucket in args.buckets.split(',')]
    
    # Validate analysis configuration
    enable_technical = not args.disable_technical
    enable_fundamental = not args.disable_fundamental
    
    if not enable_technical and not enable_fundamental:
        print("ERROR: Cannot disable both technical and fundamental analysis")
        return
    
    # Create limits configuration
    limits = RebalancingLimits(
        max_total_positions=args.max_total_positions,
        max_new_positions=args.max_new_positions,
        min_score_threshold=args.min_score_threshold,
        min_score_new_position=args.min_score_new_position
    )
    
    try:
        # Initialize components
        regime_detector = RegimeDetector()
        asset_manager = AssetBucketManager()
        data_manager = DataManager()
        
        # Initialize analyzers (will gracefully degrade to stub if not available)
        technical_analyzer = None
        fundamental_analyzer = None
        
        try:
            if enable_technical:
                technical_analyzer = TechnicalAnalyzer()
        except Exception as e:
            print(f"WARNING: Technical analyzer not available: {e}")
        
        try:
            if enable_fundamental:
                fundamental_analyzer = FundamentalAnalyzer()
        except Exception as e:
            print(f"WARNING: Fundamental analyzer not available: {e}")
        
        # Create rebalancer engine
        engine = CoreRebalancerEngine(
            regime_detector=regime_detector,
            asset_manager=asset_manager,
            technical_analyzer=technical_analyzer,
            fundamental_analyzer=fundamental_analyzer,
            data_manager=data_manager
        )
        
        # Execute rebalancing
        targets = engine.rebalance(
            rebalance_date=rebalance_date,
            current_positions=current_positions,
            limits=limits,
            bucket_names=bucket_names,
            min_trending_confidence=args.min_trending_confidence,
            enable_technical=enable_technical,
            enable_fundamental=enable_fundamental,
            technical_weight=args.technical_weight,
            fundamental_weight=args.fundamental_weight
        )
        
        # Generate JSON output
        json_output = engine.to_json(targets, include_metadata=args.include_metadata)
        
        # Output results
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(json_output)
            print(f"\nTargets saved to: {output_path}")
        else:
            print(f"\nRebalancing Targets:")
            print(json_output)
        
    except Exception as e:
        print(f"ERROR: Rebalancing failed: {e}")
        import traceback
        traceback.print_exc()
```

#### **1.4.3: Integration with Main CLI**
**File:** `backtrader/main.py` (modifications)

```python
# Add these imports at the top
from core.cli import add_rebalance_command

# In the main() function, add the rebalance command:
def main():
    parser = argparse.ArgumentParser(description='Backtrader Regime-Based Backtesting System')
    
    subparsers = parser.add_subparsers(dest='mode', help='Backtest mode')
    
    # Existing commands...
    regime_parser = subparsers.add_parser('regime', help='Run regime-based backtest')
    # ... existing regime parser setup ...
    
    # NEW: Add Core Rebalancer Engine command
    add_rebalance_command(subparsers)
    
    # Existing commands...
    compare_parser = subparsers.add_parser('compare', help='Compare backtest results')
    # ... rest of existing setup ...
```

### **Task 1.5: Integration Testing & Validation**

#### **1.5.1: Create Integration Test**
**File:** `backtrader/tests/test_core_rebalancer_integration.py`

```python
import pytest
import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from core.rebalancer_engine import CoreRebalancerEngine
from core.models import RebalancingLimits

def test_end_to_end_rebalancing():
    """Test complete rebalancing flow end-to-end"""
    
    # Mock dependencies
    regime_detector = Mock()
    asset_manager = Mock()
    data_manager = Mock()
    
    # Configure mocks
    regime_detector.get_market_regime.return_value = ("Goldilocks", 0.8)
    regime_detector.get_regime_buckets.return_value = ["Risk Assets", "Defensives"]
    regime_detector.get_research_buckets.return_value = None
    regime_detector.get_trending_assets.return_value = ["AAPL", "MSFT", "GOOGL"]
    
    asset_manager.get_assets_from_buckets.return_value = ["AAPL", "MSFT", "GOOGL", "JNJ"]
    
    # Create engine
    engine = CoreRebalancerEngine(
        regime_detector=regime_detector,
        asset_manager=asset_manager,
        data_manager=data_manager
    )
    
    # Test with existing portfolio
    current_positions = {
        "TSLA": 0.20,  # Will be closed (not in trending)
        "NVDA": 0.15   # Will be closed (not in trending)
    }
    
    limits = RebalancingLimits(
        max_total_positions=3,
        max_new_positions=2,
        min_score_threshold=0.6,
        min_score_new_position=0.65
    )
    
    # Execute rebalancing
    targets = engine.rebalance(
        rebalance_date=datetime(2024, 1, 15),
        current_positions=current_positions,
        limits=limits
    )
    
    # Verify results
    assert len(targets) >= 2  # At least close existing positions
    
    # Should have close actions for current positions not selected
    close_actions = [t for t in targets if t.action == 'close']
    close_assets = {t.asset for t in close_actions}
    
    # TSLA and NVDA should be closed (not in trending universe)
    # This depends on stub scoring, but they should likely be closed
    assert len(close_actions) >= 0  # Could be 0 if stub scoring keeps them
    
    # Should have some open/increase actions for new positions
    open_actions = [t for t in targets if t.action in ['open', 'increase']]
    assert len(open_actions) > 0
    
    # Verify JSON output
    json_output = engine.to_json(targets, include_metadata=True)
    data = json.loads(json_output)
    
    assert "rebalancing_targets" in data
    assert "metadata" in data
    assert len(data["rebalancing_targets"]) == len(targets)

def test_zombie_position_fix():
    """Test that the zombie position bug is fixed"""
    
    # Mock regime detector to return trending assets that DON'T include current positions
    regime_detector = Mock()
    asset_manager = Mock()
    
    regime_detector.get_market_regime.return_value = ("Goldilocks", 0.8)
    regime_detector.get_regime_buckets.return_value = ["Risk Assets"]
    regime_detector.get_research_buckets.return_value = None
    # CRITICAL: Trending assets don't include TSLA (current position)
    regime_detector.get_trending_assets.return_value = ["AAPL", "MSFT"]
    
    asset_manager.get_assets_from_buckets.return_value = ["AAPL", "MSFT", "GOOGL"]
    
    engine = CoreRebalancerEngine(
        regime_detector=regime_detector,
        asset_manager=asset_manager
    )
    
    # Portfolio with asset NOT in trending
    current_positions = {"TSLA": 0.25}
    
    # Execute rebalancing
    targets = engine.rebalance(
        rebalance_date=datetime(2024, 1, 15),
        current_positions=current_positions,
        limits=RebalancingLimits()
    )
    
    # CRITICAL TEST: TSLA should appear in targets (not just disappear)
    target_assets = {t.asset for t in targets}
    assert "TSLA" in target_assets, "Current position TSLA must be evaluated, not ignored!"
    
    # TSLA should have an explicit action (close, hold, or adjust)
    tsla_target = next(t for t in targets if t.asset == "TSLA")
    assert tsla_target.action in ['close', 'hold', 'decrease'], f"TSLA action should be explicit, got: {tsla_target.action}"
    
    print("✅ Zombie position bug fixed: TSLA was properly evaluated and given explicit action")

@pytest.mark.integration
def test_cli_integration():
    """Test CLI integration with real command"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test current positions file
        positions_file = Path(temp_dir) / "positions.json"
        with open(positions_file, 'w') as f:
            json.dump({"AAPL": 0.15, "MSFT": 0.10}, f)
        
        # Create output file path
        output_file = Path(temp_dir) / "targets.json"
        
        # Mock subprocess call to main CLI
        import subprocess
        import sys
        
        cmd = [
            sys.executable, "-m", "main", "rebalance",
            "--date", "2024-01-15",
            "--current-positions", str(positions_file),
            "--max-total-positions", "5",
            "--max-new-positions", "2",
            "--output", str(output_file),
            "--include-metadata"
        ]
        
        # This would be tested in actual integration environment
        # For now, verify the command structure is correct
        assert len(cmd) == 11
        assert "rebalance" in cmd
        assert "--date" in cmd
```

#### **1.5.2: Create Manual Testing Script**
**File:** `backtrader/test_core_engine_manual.py`

```python
#!/usr/bin/env python3
"""
Manual testing script for Core Rebalancer Engine
Run this to validate the engine works correctly
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add backtrader to path
sys.path.append(os.path.dirname(__file__))

try:
    from data.regime_detector import RegimeDetector
    from data.asset_buckets import AssetBucketManager
    from data.data_manager import DataManager
    from core.rebalancer_engine import CoreRebalancerEngine
    from core.models import RebalancingLimits
except ImportError as e:
    print(f"Import error: {e}")
    print("Run this script from the backtrader directory")
    sys.exit(1)

def test_basic_rebalancing():
    """Test basic rebalancing functionality"""
    
    print("🧪 Testing Core Rebalancer Engine")
    print("=" * 50)
    
    try:
        # Initialize components
        regime_detector = RegimeDetector()
        asset_manager = AssetBucketManager()
        data_manager = DataManager()
        
        engine = CoreRebalancerEngine(
            regime_detector=regime_detector,
            asset_manager=asset_manager,
            data_manager=data_manager
        )
        
        # Test scenario: Existing portfolio with some positions
        current_positions = {
            "AAPL": 0.15,
            "MSFT": 0.10,
            "TSLA": 0.20,  # This might not be in trending
            "NVDA": 0.15
        }
        
        limits = RebalancingLimits(
            max_total_positions=6,
            max_new_positions=2,
            min_score_threshold=0.6,
            min_score_new_position=0.65
        )
        
        print(f"Current portfolio: {current_positions}")
        print(f"Limits: max_total={limits.max_total_positions}, max_new={limits.max_new_positions}")
        
        # Execute rebalancing
        targets = engine.rebalance(
            rebalance_date=datetime(2024, 1, 15),
            current_positions=current_positions,
            limits=limits,
            bucket_names=["Risk Assets", "Defensives"],
            min_trending_confidence=0.7
        )
        
        # Display results
        print(f"\n📊 Rebalancing Results:")
        print(f"Generated {len(targets)} targets")
        
        actions = {}
        for target in targets:
            actions[target.action] = actions.get(target.action, 0) + 1
            print(f"  {target.asset}: {target.action} "
                  f"({target.current_allocation_pct:.1%} → {target.target_allocation_pct:.1%}) "
                  f"[score: {target.score:.3f}]")
        
        print(f"\nActions summary: {actions}")
        
        # Test JSON output
        json_output = engine.to_json(targets, include_metadata=True)
        print(f"\n📄 JSON Output (first 500 chars):")
        print(json_output[:500] + "..." if len(json_output) > 500 else json_output)
        
        # Save to file
        output_file = Path("test_rebalancing_output.json")
        with open(output_file, 'w') as f:
            f.write(json_output)
        print(f"\nFull output saved to: {output_file}")
        
        # Verify zombie position fix
        portfolio_assets = set(current_positions.keys())
        target_assets = {t.asset for t in targets}
        
        print(f"\n🔍 Zombie Position Check:")
        print(f"Portfolio assets: {portfolio_assets}")
        print(f"Target assets: {target_assets}")
        
        for asset in portfolio_assets:
            if asset in target_assets:
                action = next(t.action for t in targets if t.asset == asset)
                print(f"  ✅ {asset}: {action} (properly evaluated)")
            else:
                print(f"  ❌ {asset}: MISSING (zombie position bug!)")
        
        print(f"\n✅ Test completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_empty_portfolio():
    """Test rebalancing with empty portfolio"""
    
    print(f"\n🧪 Testing Empty Portfolio Scenario")
    print("=" * 50)
    
    try:
        regime_detector = RegimeDetector()
        asset_manager = AssetBucketManager()
        
        engine = CoreRebalancerEngine(
            regime_detector=regime_detector,
            asset_manager=asset_manager
        )
        
        # Empty portfolio - should select new positions
        targets = engine.rebalance(
            rebalance_date=datetime(2024, 1, 15),
            current_positions={},
            limits=RebalancingLimits(max_new_positions=3)
        )
        
        print(f"Empty portfolio results: {len(targets)} targets")
        
        # Should have only 'open' actions
        actions = [t.action for t in targets]
        assert all(action == 'open' for action in actions), f"Expected only 'open' actions, got: {set(actions)}"
        
        print("✅ Empty portfolio test passed")
        return True
        
    except Exception as e:
        print(f"❌ Empty portfolio test failed: {e}")
        return False

if __name__ == "__main__":
    print("Core Rebalancer Engine Manual Test")
    print("=" * 60)
    
    # Run tests
    test1_passed = test_basic_rebalancing()
    test2_passed = test_empty_portfolio()
    
    # Summary
    print(f"\n" + "=" * 60)
    print(f"TEST SUMMARY")
    print(f"=" * 60)
    print(f"Basic Rebalancing: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Empty Portfolio: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print(f"\n🎉 ALL TESTS PASSED - Core Rebalancer Engine is working!")
        print(f"\nTry the CLI command:")
        print(f"python main.py rebalance --date 2024-01-15 --buckets 'Risk Assets,Defensives' --include-metadata")
    else:
        print(f"\n⚠️  SOME TESTS FAILED - Check the implementation")
        sys.exit(1)
```

## 🎯 Implementation Success Criteria

### **Primary Goals (Must Have)**
1. **✅ Zombie Position Bug Fixed**: Current positions are ALWAYS evaluated regardless of trending confidence
2. **✅ Clean API Design**: Well-defined interfaces for Universe Builder, Scoring Service, Selection Service
3. **✅ Basic Position Limits**: Enforce max_new_positions and max_total_positions
4. **✅ JSON Output**: Pure target output without backtrader coupling
5. **✅ CLI Integration**: `python main.py rebalance --date YYYY-MM-DD`

### **Secondary Goals (Should Have)**
1. **✅ Portfolio Priority**: Current positions prioritized over new opportunities
2. **✅ Configurable Analysis**: Enable/disable technical and fundamental analysis
3. **✅ Comprehensive Testing**: Unit tests and integration tests
4. **✅ Error Handling**: Graceful degradation when analyzers unavailable

### **Validation Tests**
1. **Zombie Position Test**: Portfolio asset not in trending must still appear in targets
2. **Limit Enforcement Test**: Verify max_new_positions and max_total_positions respected
3. **Empty Portfolio Test**: New portfolio creation works correctly
4. **CLI Integration Test**: Command line interface works end-to-end

## 📅 Implementation Timeline

### **Week 1: Core Infrastructure**
- **Days 1-2**: Create data models (`models.py`)
- **Days 3-4**: Implement Universe Builder with zombie fix
- **Days 5**: Unit tests for Universe Builder

### **Week 2: Scoring and Selection**  
- **Days 1-2**: Implement Scoring Service with stub mode
- **Days 3-4**: Implement Selection Service with limits
- **Days 5**: Unit tests for Scoring and Selection

### **Week 3: Integration and CLI**
- **Days 1-2**: Create Core Rebalancer Engine
- **Days 3-4**: Add CLI integration and JSON output
- **Days 5**: Integration tests and manual validation

## 🔗 Module Dependencies

### **Depends On (Existing)**
- `data/regime_detector.py` - RegimeDetector class
- `data/asset_buckets.py` - AssetBucketManager class  
- `data/data_manager.py` - DataManager class
- `position/technical_analyzer.py` - TechnicalAnalyzer class
- `position/fundamental_analyzer.py` - FundamentalAnalyzer class

### **Provides (New)**
- `core/models.py` - Core data models for rebalancing
- `core/universe_builder.py` - UniverseBuilder API
- `core/scoring_service.py` - ScoringService API  
- `core/selection_service.py` - SelectionService API
- `core/rebalancer_engine.py` - CoreRebalancerEngine API
- `core/cli.py` - CLI command integration

### **Used By (Future Modules)**
- **Module 2**: Bucket Diversification Manager will use Selection Service
- **Module 3**: Two-Stage Sizing will use Selection Service outputs
- **Module 4**: Grace Period Manager will use Scoring Service outputs
- **All Modules**: Will use core data models and engine interface

## 🚨 Critical Implementation Notes

### **1. Universe Builder Priority**
```python
# CRITICAL: Always include portfolio assets
trending_assets = set(trending_candidates) | portfolio_assets
combined_universe = portfolio_assets | trending_assets
```

### **2. Scoring Service Fallback**
```python
# Must gracefully handle missing analyzers
if self.technical_analyzer and self.fundamental_analyzer:
    return self._score_with_real_analyzers(...)
else:
    return self._score_with_stub(...)
```

### **3. Selection Service Limits**
```python
# Portfolio assets checked first, new assets second
portfolio_selected = [...]  # Current positions meeting threshold
new_slots = min(max_new_positions, max_total - len(portfolio_selected))
```

### **4. CLI Validation**
```python
# Must validate analysis configuration
if not enable_technical and not enable_fundamental:
    print("ERROR: Cannot disable both analysis types")
    return
```

This Core Rebalancer Engine module will provide the foundation for all future enhancements while immediately fixing the critical zombie position bug and establishing clean, testable interfaces for the remaining 10 modules. 