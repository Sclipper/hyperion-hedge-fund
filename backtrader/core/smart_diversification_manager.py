"""
Smart Diversification Manager - Module 5 Phase 3

Manages bucket diversification with smart override capabilities. Automatically
marks high-alpha assets as core when they override bucket limits.
"""

from typing import List, Optional, Set
from datetime import datetime
import logging

from .models import AssetScore, RebalancingLimits

logger = logging.getLogger(__name__)


class SmartDiversificationManager:
    """
    Smart diversification manager with core asset integration (Phase 3)
    
    Manages bucket diversification while automatically promoting exceptional
    assets to core status when they override normal bucket limits.
    """
    
    def __init__(self, 
                 bucket_override_threshold: float = 0.95,
                 max_overrides_per_rebalance: int = 2,
                 core_asset_manager=None):
        """
        Initialize smart diversification manager
        
        Args:
            bucket_override_threshold: Score threshold for bucket overrides
            max_overrides_per_rebalance: Max bucket overrides per rebalancing cycle
            core_asset_manager: CoreAssetManager instance for auto-designation
        """
        self.bucket_override_threshold = bucket_override_threshold
        self.max_overrides_per_rebalance = max_overrides_per_rebalance
        self.core_asset_manager = core_asset_manager
        
        # Tracking for current rebalancing cycle
        self.overrides_granted_this_cycle = 0
        self.current_rebalance_date = None
    
    def apply_smart_diversification(self, 
                                  scored_assets: List[AssetScore],
                                  bucket_limits: dict,
                                  current_date: datetime) -> List[AssetScore]:
        """
        Apply smart diversification with automatic core asset designation
        
        Args:
            scored_assets: List of asset scores to evaluate
            bucket_limits: Dictionary of bucket -> max_positions
            current_date: Current date for core asset designation
            
        Returns:
            List[AssetScore]: Selected assets with bucket override handling
        """
        # Reset override tracking for new rebalancing cycle
        if self.current_rebalance_date != current_date:
            self.overrides_granted_this_cycle = 0
            self.current_rebalance_date = current_date
        
        selected_assets = []
        bucket_counts = {}
        
        # Sort assets by score (highest first)
        sorted_assets = sorted(scored_assets, key=lambda x: x.combined_score, reverse=True)
        
        logger.info(f"🎯 Smart Diversification: Processing {len(sorted_assets)} assets")
        logger.info(f"   Override threshold: {self.bucket_override_threshold:.1%}")
        logger.info(f"   Max overrides: {self.max_overrides_per_rebalance}")
        
        for asset_score in sorted_assets:
            asset_bucket = self._get_asset_bucket(asset_score.asset)
            bucket_limit = bucket_limits.get(asset_bucket, 999)
            current_bucket_count = bucket_counts.get(asset_bucket, 0)
            
            # Check if we can add this asset normally
            can_add_normally = current_bucket_count < bucket_limit
            
            # Check for bucket override eligibility
            can_override = self._can_grant_bucket_override(
                asset_score, asset_bucket, bucket_limit, current_bucket_count
            )
            
            if can_add_normally:
                # Normal selection within bucket limits
                selected_assets.append(asset_score)
                bucket_counts[asset_bucket] = current_bucket_count + 1
                asset_score.selection_reason = f"Normal selection (bucket: {asset_bucket})"
                
            elif can_override:
                # Grant bucket override and mark as core asset
                success = self._grant_bucket_override(asset_score, current_date, asset_bucket)
                
                if success:
                    selected_assets.append(asset_score)
                    bucket_counts[asset_bucket] = current_bucket_count + 1
                    self.overrides_granted_this_cycle += 1
                    
                    logger.info(f"🌟 BUCKET OVERRIDE GRANTED: {asset_score.asset} "
                               f"(score: {asset_score.combined_score:.3f}, bucket: {asset_bucket})")
                else:
                    asset_score.selection_reason = f"Override failed: Core asset designation failed"
                    
            else:
                # Rejected by bucket limits and not eligible for override
                asset_score.selection_reason = (f"Rejected: Bucket '{asset_bucket}' limit ({bucket_limit}) "
                                               f"reached, override not available")
        
        logger.info(f"✅ Smart Diversification Complete: {len(selected_assets)} selected, "
                   f"{self.overrides_granted_this_cycle} overrides granted")
        
        return selected_assets
    
    def _can_grant_bucket_override(self, 
                                 asset_score: AssetScore, 
                                 asset_bucket: str, 
                                 bucket_limit: int, 
                                 current_count: int) -> bool:
        """
        Check if asset qualifies for bucket override
        
        Args:
            asset_score: Asset score to evaluate
            asset_bucket: Asset's bucket
            bucket_limit: Bucket position limit
            current_count: Current positions in bucket
            
        Returns:
            bool: True if override can be granted
        """
        # Must exceed bucket limit to need override
        if current_count < bucket_limit:
            return False
        
        # Must meet score threshold
        if asset_score.combined_score < self.bucket_override_threshold:
            return False
        
        # Must not exceed override limit for this cycle
        if self.overrides_granted_this_cycle >= self.max_overrides_per_rebalance:
            return False
        
        # Must have core asset manager available
        if not self.core_asset_manager:
            return False
        
        return True
    
    def _grant_bucket_override(self, 
                             asset_score: AssetScore, 
                             current_date: datetime, 
                             asset_bucket: str) -> bool:
        """
        Grant bucket override and mark asset as core
        
        Args:
            asset_score: Asset to grant override
            current_date: Current date
            asset_bucket: Asset's bucket
            
        Returns:
            bool: True if override was successfully granted
        """
        if not self.core_asset_manager:
            return False
        
        # Mark as core asset with bucket override reason
        reason = f"High-alpha bucket override: {asset_score.combined_score:.3f} > {self.bucket_override_threshold:.3f}"
        
        success = self.core_asset_manager.mark_as_core(
            asset=asset_score.asset,
            current_date=current_date,
            reason=reason,
            designation_score=asset_score.combined_score
        )
        
        if success:
            # Update asset score with override information
            asset_score.selection_reason = f"BUCKET OVERRIDE + CORE DESIGNATION: {reason}"
            asset_score.is_bucket_override = True
            asset_score.bucket_override_reason = reason
            
            logger.info(f"🌟 Core asset designated: {asset_score.asset} "
                       f"(bucket: {asset_bucket}, score: {asset_score.combined_score:.3f})")
            
            return True
        else:
            logger.warning(f"Failed to mark {asset_score.asset} as core asset for bucket override")
            return False
    
    def _get_asset_bucket(self, asset: str) -> str:
        """
        Get bucket for asset (placeholder implementation)
        
        Args:
            asset: Asset symbol
            
        Returns:
            str: Asset bucket name
        """
        # This would integrate with the bucket manager
        # For now, use a simple mapping for testing
        bucket_mappings = {
            "AAPL": "Risk Assets",
            "MSFT": "Risk Assets", 
            "GOOGL": "Risk Assets",
            "NVDA": "Risk Assets",
            "TSLA": "Risk Assets",
            "JNJ": "Defensive Assets",
            "PG": "Defensive Assets",
            "KO": "Defensive Assets",
            "WMT": "Defensive Assets",
            "EFA": "International",
            "EEM": "International",
            "VGK": "International",
            "GLD": "Commodities",
            "SLV": "Commodities"
        }
        
        return bucket_mappings.get(asset, "Unknown")
    
    def get_override_statistics(self, current_date: datetime) -> dict:
        """
        Get statistics about bucket overrides
        
        Args:
            current_date: Current date
            
        Returns:
            dict: Override statistics
        """
        stats = {
            'overrides_this_cycle': self.overrides_granted_this_cycle,
            'max_overrides_allowed': self.max_overrides_per_rebalance,
            'override_threshold': self.bucket_override_threshold,
            'overrides_remaining': max(0, self.max_overrides_per_rebalance - self.overrides_granted_this_cycle),
            'current_rebalance_date': self.current_rebalance_date.strftime('%Y-%m-%d') if self.current_rebalance_date else None,
            'core_asset_manager_available': self.core_asset_manager is not None
        }
        
        # Add core asset statistics if available
        if self.core_asset_manager:
            core_assets = self.core_asset_manager.get_core_assets_list()
            stats['total_core_assets'] = len(core_assets)
            stats['core_assets'] = core_assets
        
        return stats
    
    def reset_override_cycle(self):
        """Reset override tracking for new rebalancing cycle"""
        self.overrides_granted_this_cycle = 0
        self.current_rebalance_date = None
        logger.info("🔄 Override cycle reset") 