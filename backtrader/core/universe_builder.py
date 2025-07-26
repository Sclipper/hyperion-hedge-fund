from typing import Set, List, Dict, Any
from datetime import datetime
import sys
import os

# Import models only, use Any for external dependencies to avoid import issues
from .models import RebalancingUniverse, AssetPriority

class UniverseBuilder:
    """Builds comprehensive asset universe for rebalancing"""
    
    def __init__(self, regime_detector: Any, asset_manager: Any):
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