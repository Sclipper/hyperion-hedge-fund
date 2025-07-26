from typing import Dict, List, Set, Optional, Any
from collections import defaultdict
from dataclasses import dataclass
import sys
import os

# Import models only to avoid dependency issues during testing
from .models import AssetScore, AssetPriority

@dataclass
class BucketAllocation:
    """Bucket allocation constraints"""
    max_positions: int = 4
    max_weight: float = 0.4
    current_positions: int = 0
    current_weight: float = 0.0
    priority: int = 1  # 1 = highest priority

@dataclass  
class BucketStatistics:
    """Comprehensive bucket statistics"""
    bucket_name: str
    asset_count: int
    total_allocation: float
    assets: List[str]
    avg_score: float
    max_score: float
    min_score: float

class BucketManager:
    """Enhanced bucket manager with diversification capabilities"""
    
    def __init__(self, asset_manager: Any = None):
        self.asset_manager = asset_manager
        self.bucket_mappings = self._load_bucket_mappings()
        
    def _load_bucket_mappings(self) -> Dict[str, List[str]]:
        """
        Load bucket mappings from existing asset manager or create default
        """
        if self.asset_manager and hasattr(self.asset_manager, 'buckets'):
            return self.asset_manager.buckets
        elif self.asset_manager and hasattr(self.asset_manager, 'get_all_buckets'):
            try:
                return self.asset_manager.get_all_buckets()
            except:
                pass
        
        # Fallback to basic mappings for testing
        return {
            'Risk Assets': ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA', 'META'],
            'Defensive Assets': ['JNJ', 'PG', 'KO', 'WMT', 'XOM'],
            'International': ['EFA', 'EEM', 'VGK', 'FXI'],
            'Commodities': ['GLD', 'SLV', 'DBA', 'USO']
        }
    
    def get_asset_bucket(self, asset: str) -> str:
        """
        Get bucket for an asset
        
        Args:
            asset: Asset symbol
            
        Returns:
            Bucket name or 'Unknown' if not found
        """
        for bucket_name, assets in self.bucket_mappings.items():
            if asset in assets:
                return bucket_name
        
        return 'Unknown'
    
    def get_bucket_assets(self, bucket_name: str) -> List[str]:
        """
        Get all assets in a bucket
        
        Args:
            bucket_name: Name of the bucket
            
        Returns:
            List of asset symbols in the bucket
        """
        return self.bucket_mappings.get(bucket_name, [])
    
    def get_all_buckets(self) -> List[str]:
        """Get list of all available bucket names"""
        return list(self.bucket_mappings.keys())
    
    def group_assets_by_bucket(self, asset_scores: List[AssetScore]) -> Dict[str, List[AssetScore]]:
        """
        Group asset scores by their bucket
        
        Args:
            asset_scores: List of scored assets
            
        Returns:
            Dict mapping bucket names to lists of asset scores
        """
        bucket_groups = defaultdict(list)
        
        for asset_score in asset_scores:
            bucket = self.get_asset_bucket(asset_score.asset)
            bucket_groups[bucket].append(asset_score)
        
        # Sort each bucket by score (highest first)
        for bucket in bucket_groups:
            bucket_groups[bucket].sort(key=lambda x: x.combined_score, reverse=True)
        
        return dict(bucket_groups)
    
    def calculate_bucket_statistics(self, asset_scores: List[AssetScore]) -> Dict[str, BucketStatistics]:
        """
        Calculate comprehensive statistics for each bucket
        
        Args:
            asset_scores: List of scored assets
            
        Returns:
            Dict mapping bucket names to statistics
        """
        bucket_groups = self.group_assets_by_bucket(asset_scores)
        statistics = {}
        
        for bucket_name, scores in bucket_groups.items():
            if not scores:
                continue
                
            assets = [score.asset for score in scores]
            score_values = [score.combined_score for score in scores]
            total_allocation = sum(getattr(score, 'position_size_percentage', 0.0) for score in scores)
            
            statistics[bucket_name] = BucketStatistics(
                bucket_name=bucket_name,
                asset_count=len(scores),
                total_allocation=total_allocation,
                assets=assets,
                avg_score=sum(score_values) / len(score_values),
                max_score=max(score_values),
                min_score=min(score_values)
            )
        
        return statistics
    
    def get_bucket_allocation_status(self, asset_scores: List[AssetScore], 
                                   max_positions_per_bucket: int = 4,
                                   max_allocation_per_bucket: float = 0.4) -> Dict[str, BucketAllocation]:
        """
        Get current allocation status for all buckets
        
        Args:
            asset_scores: List of scored assets (with position sizes)
            max_positions_per_bucket: Maximum positions allowed per bucket
            max_allocation_per_bucket: Maximum allocation percentage per bucket
            
        Returns:
            Dict mapping bucket names to allocation status
        """
        bucket_groups = self.group_assets_by_bucket(asset_scores)
        allocations = {}
        
        for bucket_name in self.get_all_buckets():
            scores = bucket_groups.get(bucket_name, [])
            
            current_positions = len(scores)
            current_weight = sum(getattr(score, 'position_size_percentage', 0.0) for score in scores)
            
            allocations[bucket_name] = BucketAllocation(
                max_positions=max_positions_per_bucket,
                max_weight=max_allocation_per_bucket,
                current_positions=current_positions,
                current_weight=current_weight,
                priority=1  # Equal priority for now
            )
        
        return allocations
    
    def validate_bucket_constraints(self, asset_scores: List[AssetScore],
                                  max_positions_per_bucket: int = 4,
                                  max_allocation_per_bucket: float = 0.4,
                                  min_buckets_represented: int = 2) -> Dict[str, Any]:
        """
        Validate portfolio against bucket constraints
        
        Args:
            asset_scores: List of scored assets
            max_positions_per_bucket: Maximum positions per bucket
            max_allocation_per_bucket: Maximum allocation per bucket
            min_buckets_represented: Minimum number of buckets required
            
        Returns:
            Validation results with violations and recommendations
        """
        bucket_stats = self.calculate_bucket_statistics(asset_scores)
        violations = []
        recommendations = []
        
        # Check position limits per bucket
        for bucket_name, stats in bucket_stats.items():
            if stats.asset_count > max_positions_per_bucket:
                violations.append(f"Bucket '{bucket_name}' has {stats.asset_count} positions (limit: {max_positions_per_bucket})")
                recommendations.append(f"Reduce positions in '{bucket_name}' bucket")
        
        # Check allocation limits per bucket
        for bucket_name, stats in bucket_stats.items():
            if stats.total_allocation > max_allocation_per_bucket:
                violations.append(f"Bucket '{bucket_name}' has {stats.total_allocation:.1%} allocation (limit: {max_allocation_per_bucket:.1%})")
                recommendations.append(f"Reduce allocation to '{bucket_name}' bucket")
        
        # Check minimum bucket representation
        buckets_with_positions = len([stats for stats in bucket_stats.values() if stats.asset_count > 0])
        if buckets_with_positions < min_buckets_represented:
            violations.append(f"Only {buckets_with_positions} buckets represented (minimum: {min_buckets_represented})")
            recommendations.append("Add positions from underrepresented buckets")
        
        return {
            'is_valid': len(violations) == 0,
            'violations': violations,
            'recommendations': recommendations,
            'bucket_statistics': bucket_stats,
            'buckets_represented': buckets_with_positions
        } 