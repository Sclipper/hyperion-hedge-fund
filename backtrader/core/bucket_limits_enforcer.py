from typing import List, Dict, Set, Optional, Any
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
import sys
import os

# Import models and bucket manager
from .models import AssetScore, AssetPriority
from .bucket_manager import BucketManager, BucketAllocation

@dataclass
class BucketLimitsConfig:
    """Configuration for bucket limits enforcement"""
    max_positions_per_bucket: int = 4
    max_allocation_per_bucket: float = 0.4
    min_buckets_represented: int = 2
    enforce_position_limits: bool = True
    enforce_allocation_limits: bool = True
    enforce_min_buckets: bool = True
    allow_bucket_overflow: bool = False  # Allow temporary overflow for portfolio assets

@dataclass
class BucketEnforcementResult:
    """Result of bucket limits enforcement"""
    selected_assets: List[AssetScore]
    rejected_assets: List[AssetScore]
    bucket_statistics: Dict[str, Any]
    enforcement_actions: List[str]
    violations_fixed: List[str]

class BucketLimitsEnforcer:
    """Enforces bucket-based portfolio diversification constraints"""
    
    def __init__(self, bucket_manager: BucketManager = None):
        self.bucket_manager = bucket_manager or BucketManager()
    
    def apply_bucket_limits(self, scored_assets: List[AssetScore], 
                          config: BucketLimitsConfig) -> BucketEnforcementResult:
        """
        Apply bucket limits to a list of scored assets
        
        Args:
            scored_assets: List of asset scores to filter
            config: Bucket limits configuration
            
        Returns:
            BucketEnforcementResult with selected/rejected assets and metadata
        """
        
        if not scored_assets:
            return BucketEnforcementResult(
                selected_assets=[],
                rejected_assets=[],
                bucket_statistics={},
                enforcement_actions=["No assets to process"],
                violations_fixed=[]
            )
        
        print(f"\n🏛️ Applying Bucket Limits")
        print(f"   Config: max_positions={config.max_positions_per_bucket}, "
              f"max_allocation={config.max_allocation_per_bucket:.1%}, "
              f"min_buckets={config.min_buckets_represented}")
        
        enforcement_actions = []
        violations_fixed = []
        
        # Step 1: Group assets by bucket and priority
        bucket_groups = self._group_by_bucket_and_priority(scored_assets)
        
        # Step 2: Apply position limits per bucket
        if config.enforce_position_limits:
            bucket_groups, actions, violations = self._apply_position_limits(
                bucket_groups, config.max_positions_per_bucket, config.allow_bucket_overflow
            )
            enforcement_actions.extend(actions)
            violations_fixed.extend(violations)
        
        # Step 3: Apply allocation limits per bucket  
        if config.enforce_allocation_limits:
            bucket_groups, actions, violations = self._apply_allocation_limits(
                bucket_groups, config.max_allocation_per_bucket
            )
            enforcement_actions.extend(actions)
            violations_fixed.extend(violations)
        
        # Step 4: Ensure minimum bucket representation
        if config.enforce_min_buckets:
            bucket_groups, actions, violations = self._ensure_min_bucket_representation(
                bucket_groups, scored_assets, config.min_buckets_represented
            )
            enforcement_actions.extend(actions)
            violations_fixed.extend(violations)
        
        # Compile results
        selected_assets = []
        rejected_assets = []
        
        for bucket_name, asset_list in bucket_groups.items():
            for asset_score in asset_list:
                if getattr(asset_score, '_bucket_selected', True):
                    selected_assets.append(asset_score)
                else:
                    rejected_assets.append(asset_score)
        
        # Add any assets that weren't processed
        processed_assets = {asset.asset for asset in selected_assets + rejected_assets}
        for asset_score in scored_assets:
            if asset_score.asset not in processed_assets:
                rejected_assets.append(asset_score)
                asset_score.bucket_rejection_reason = "Not processed in bucket enforcement"
        
        # Calculate final statistics
        bucket_statistics = self.bucket_manager.calculate_bucket_statistics(selected_assets)
        
        print(f"   Results: {len(selected_assets)} selected, {len(rejected_assets)} rejected")
        print(f"   Buckets represented: {len(bucket_statistics)}")
        
        return BucketEnforcementResult(
            selected_assets=selected_assets,
            rejected_assets=rejected_assets,
            bucket_statistics=bucket_statistics,
            enforcement_actions=enforcement_actions,
            violations_fixed=violations_fixed
        )
    
    def _group_by_bucket_and_priority(self, scored_assets: List[AssetScore]) -> Dict[str, List[AssetScore]]:
        """
        Group assets by bucket with priority awareness
        """
        bucket_groups = defaultdict(list)
        
        for asset_score in scored_assets:
            bucket = self.bucket_manager.get_asset_bucket(asset_score.asset)
            bucket_groups[bucket].append(asset_score)
        
        # Sort each bucket by priority first, then score
        for bucket in bucket_groups:
            bucket_groups[bucket].sort(key=lambda x: (
                0 if x.priority == AssetPriority.PORTFOLIO else 1,  # Portfolio assets first
                -x.combined_score  # Then by score (highest first)
            ))
        
        return dict(bucket_groups)
    
    def _apply_position_limits(self, bucket_groups: Dict[str, List[AssetScore]], 
                             max_positions: int, allow_overflow: bool = False) -> tuple:
        """
        Apply maximum positions per bucket constraint
        """
        actions = []
        violations = []
        
        for bucket_name, assets in bucket_groups.items():
            if len(assets) <= max_positions:
                # Within limit
                for asset in assets:
                    asset._bucket_selected = True
                continue
            
            # Over limit - need to select top assets
            portfolio_assets = [a for a in assets if a.priority == AssetPriority.PORTFOLIO]
            other_assets = [a for a in assets if a.priority != AssetPriority.PORTFOLIO]
            
            selected_count = 0
            
            # Always include portfolio assets if allow_overflow is True
            if allow_overflow:
                for asset in portfolio_assets:
                    asset._bucket_selected = True
                    asset.bucket_selection_reason = f"Portfolio asset (overflow allowed)"
                    selected_count += 1
                
                if selected_count > max_positions:
                    actions.append(f"Bucket '{bucket_name}': Allowed {selected_count} portfolio assets (overflow)")
            else:
                # Strict enforcement - portfolio assets compete for slots
                all_assets_by_priority = portfolio_assets + other_assets
                selected_assets = all_assets_by_priority[:max_positions]
                
                for asset in selected_assets:
                    asset._bucket_selected = True
                    asset.bucket_selection_reason = f"Top {max_positions} in bucket '{bucket_name}'"
                    selected_count += 1
            
            # Handle remaining slots for non-portfolio assets
            remaining_slots = max(0, max_positions - (len(portfolio_assets) if allow_overflow else selected_count))
            
            if remaining_slots > 0 and other_assets:
                additional_selected = other_assets[:remaining_slots]
                for asset in additional_selected:
                    asset._bucket_selected = True
                    asset.bucket_selection_reason = f"Additional slot in bucket '{bucket_name}'"
                    selected_count += 1
            
            # Mark rejected assets
            all_assets = portfolio_assets + other_assets
            for asset in all_assets:
                if not getattr(asset, '_bucket_selected', False):
                    asset._bucket_selected = False
                    asset.bucket_rejection_reason = f"Exceeded max positions for bucket '{bucket_name}' ({max_positions})"
            
            rejected_count = len(assets) - selected_count
            actions.append(f"Bucket '{bucket_name}': Selected {selected_count}/{len(assets)} assets (limit: {max_positions})")
            
            if rejected_count > 0:
                violations.append(f"Bucket '{bucket_name}': Rejected {rejected_count} assets due to position limit")
        
        return bucket_groups, actions, violations
    
    def _apply_allocation_limits(self, bucket_groups: Dict[str, List[AssetScore]], 
                               max_allocation: float) -> tuple:
        """
        Apply maximum allocation per bucket constraint
        """
        actions = []
        violations = []
        
        for bucket_name, assets in bucket_groups.items():
            # Only consider assets that passed position limits
            selected_assets = [a for a in assets if getattr(a, '_bucket_selected', True)]
            
            if not selected_assets:
                continue
            
            # Calculate current allocation
            current_allocation = sum(getattr(a, 'position_size_percentage', 0.0) for a in selected_assets)
            
            if current_allocation <= max_allocation:
                # Within limit
                continue
            
            # Over allocation limit - need to scale down
            scale_factor = max_allocation / current_allocation
            
            for asset in selected_assets:
                original_size = getattr(asset, 'position_size_percentage', 0.0)
                if original_size > 0:
                    asset.position_size_percentage = original_size * scale_factor
                    asset.bucket_scaling_applied = True
                    asset.bucket_scale_factor = scale_factor
            
            actions.append(f"Bucket '{bucket_name}': Scaled allocation from {current_allocation:.1%} to {max_allocation:.1%}")
            violations.append(f"Bucket '{bucket_name}': Applied {scale_factor:.3f} scaling due to allocation limit")
        
        return bucket_groups, actions, violations
    
    def _ensure_min_bucket_representation(self, bucket_groups: Dict[str, List[AssetScore]], 
                                        all_scored_assets: List[AssetScore],
                                        min_buckets: int) -> tuple:
        """
        Ensure minimum number of buckets are represented
        """
        actions = []
        violations = []
        
        # Count buckets with selected assets
        buckets_with_selections = []
        for bucket_name, assets in bucket_groups.items():
            selected_assets = [a for a in assets if getattr(a, '_bucket_selected', True)]
            if selected_assets:
                buckets_with_selections.append(bucket_name)
        
        if len(buckets_with_selections) >= min_buckets:
            actions.append(f"Minimum bucket representation satisfied: {len(buckets_with_selections)} >= {min_buckets}")
            return bucket_groups, actions, violations
        
        # Need to add assets from underrepresented buckets
        needed_buckets = min_buckets - len(buckets_with_selections)
        
        # Find buckets without selections from processed assets
        empty_buckets = []
        for bucket_name, assets in bucket_groups.items():
            selected_assets = [a for a in assets if getattr(a, '_bucket_selected', True)]
            if not selected_assets and assets:  # Has assets but none selected
                empty_buckets.append((bucket_name, assets))
        
        # If we still need more buckets, create synthetic assets from unrepresented buckets
        if len(empty_buckets) < needed_buckets:
            all_available_buckets = self.bucket_manager.get_all_buckets()
            represented_buckets = set(bucket_groups.keys())
            
            for bucket_name in all_available_buckets:
                if bucket_name not in represented_buckets:
                    # Create a minimal asset score for this bucket
                    bucket_assets = self.bucket_manager.get_bucket_assets(bucket_name)
                    if bucket_assets:
                        # Use first asset from bucket as representative
                        synthetic_asset = AssetScore(
                            asset=bucket_assets[0],
                            date=all_scored_assets[0].date if all_scored_assets else datetime.now(),
                            technical_score=0.5,
                            fundamental_score=0.5,
                            combined_score=0.5,
                            confidence=0.5,
                            regime=all_scored_assets[0].regime if all_scored_assets else "Unknown",
                            priority=AssetPriority.REGIME,
                            timeframes_analyzed=['synthetic']
                        )
                        synthetic_asset.position_size_percentage = 0.05  # Small allocation
                        empty_buckets.append((bucket_name, [synthetic_asset]))
        
        # Sort empty buckets by best asset score
        empty_buckets.sort(key=lambda x: max(a.combined_score for a in x[1]), reverse=True)
        
        # Add top asset from best empty buckets
        added_count = 0
        for bucket_name, assets in empty_buckets:
            if added_count >= needed_buckets:
                break
                
            best_asset = max(assets, key=lambda a: a.combined_score)
            best_asset._bucket_selected = True
            best_asset.bucket_selection_reason = f"Added for minimum bucket representation"
            best_asset.forced_for_diversification = True
            
            # Add to bucket_groups if not already there
            if bucket_name not in bucket_groups:
                bucket_groups[bucket_name] = [best_asset]
            
            actions.append(f"Added {best_asset.asset} from bucket '{bucket_name}' for minimum representation")
            violations.append(f"Forced selection from bucket '{bucket_name}' to meet minimum {min_buckets} buckets")
            added_count += 1
        
        return bucket_groups, actions, violations
    
    def get_enforcement_summary(self, result: BucketEnforcementResult) -> Dict[str, Any]:
        """
        Generate a summary of enforcement actions taken
        """
        selected_by_bucket = defaultdict(list)
        for asset in result.selected_assets:
            bucket = self.bucket_manager.get_asset_bucket(asset.asset)
            selected_by_bucket[bucket].append(asset.asset)
        
        return {
            'total_selected': len(result.selected_assets),
            'total_rejected': len(result.rejected_assets),
            'buckets_represented': len(result.bucket_statistics),
            'selected_by_bucket': dict(selected_by_bucket),
            'enforcement_actions_count': len(result.enforcement_actions),
            'violations_fixed_count': len(result.violations_fixed),
            'bucket_statistics': {
                bucket: {
                    'asset_count': stats.asset_count,
                    'total_allocation': stats.total_allocation,
                    'avg_score': stats.avg_score
                }
                for bucket, stats in result.bucket_statistics.items()
            }
        } 