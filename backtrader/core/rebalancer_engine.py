import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from .universe_builder import UniverseBuilder
from .scoring_service import ScoringService
from .selection_service import SelectionService
from .bucket_manager import BucketManager
from .bucket_limits_enforcer import BucketLimitsEnforcer, BucketLimitsConfig
from .models import RebalancingLimits, RebalancingTarget

class CoreRebalancerEngine:
    """Main engine for portfolio rebalancing"""
    
    def __init__(self, regime_detector: Any, asset_manager: Any, 
                 technical_analyzer: Any = None, fundamental_analyzer: Any = None,
                 data_manager: Any = None):
        
        self.universe_builder = UniverseBuilder(regime_detector, asset_manager)
        self.scoring_service = ScoringService(
            technical_analyzer=technical_analyzer,
            fundamental_analyzer=fundamental_analyzer
        )
        self.selection_service = SelectionService()
        self.data_manager = data_manager
        
        # Optional bucket diversification components
        self.bucket_manager = BucketManager(asset_manager)
        self.bucket_enforcer = BucketLimitsEnforcer(self.bucket_manager)
        
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
        
        # Step 3: Apply bucket diversification (if enabled)
        if limits.enable_bucket_diversification:
            print(f"\n🏛️ Step 3: Applying Bucket Diversification")
            bucket_config = BucketLimitsConfig(
                max_positions_per_bucket=limits.max_positions_per_bucket,
                max_allocation_per_bucket=limits.max_allocation_per_bucket,
                min_buckets_represented=limits.min_buckets_represented,
                allow_bucket_overflow=limits.allow_bucket_overflow
            )
            
            bucket_result = self.bucket_enforcer.apply_bucket_limits(scored_assets, bucket_config)
            scored_assets = bucket_result.selected_assets
            
            print(f"   Bucket enforcement: {len(bucket_result.selected_assets)} selected, "
                  f"{len(bucket_result.rejected_assets)} rejected")
            print(f"   Buckets represented: {len(bucket_result.bucket_statistics)}")
        
        # Step 4: Select assets by score and limits
        print(f"\n🎯 Step {'4' if limits.enable_bucket_diversification else '3'}: Selecting Portfolio")
        selected_assets = self.selection_service.select_by_score(
            scored_assets=scored_assets,
            limits=limits,
            current_positions=current_positions
        )
        
        # Step 4/5: Create final targets with dynamic sizing
        print(f"\n⚖️  Step {'5' if limits.enable_bucket_diversification else '4'}: Creating Rebalancing Targets")
        targets = self.selection_service.create_rebalancing_targets(
            selected_assets=selected_assets,
            current_positions=current_positions,
            target_allocation=limits.target_total_allocation,
            limits=limits  # Pass limits for dynamic sizing configuration
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