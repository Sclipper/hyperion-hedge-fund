from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import sys
import os

# Import models and dynamic sizer
from .models import AssetScore
from .dynamic_position_sizer import DynamicPositionSizer

@dataclass
class TwoStageSizingResult:
    """Result of two-stage sizing process"""
    sized_assets: List[AssetScore]
    stage1_capped_count: int
    stage2_capped_count: int
    total_allocated: float
    residual_unallocated: float
    residual_strategy_applied: str
    sizing_metadata: Dict[str, Any]

class ResidualStrategy(Enum):
    """Available residual allocation strategies"""
    SAFE_TOP_SLICE = "safe_top_slice"     # Add to top-scoring uncapped positions (default)
    PROPORTIONAL = "proportional"         # Distribute proportionally to all positions
    CASH_BUCKET = "cash_bucket"           # Allocate to cash/treasury position

class TwoStagePositionSizer:
    """Two-stage position sizing with residual allocation management"""
    
    def __init__(self, max_single_position: float = 0.15,
                 target_allocation: float = 0.95,
                 residual_strategy: str = 'safe_top_slice'):
        
        self.max_single_position = max_single_position
        self.target_allocation = target_allocation
        self.residual_strategy = ResidualStrategy(residual_strategy)
        
        print(f"Two-Stage Position Sizer initialized:")
        print(f"  Max single position: {self.max_single_position:.1%}")
        print(f"  Target allocation: {self.target_allocation:.1%}")
        print(f"  Residual strategy: {self.residual_strategy.value}")
    
    def apply_two_stage_sizing(self, sized_assets: List[AssetScore]) -> TwoStageSizingResult:
        """
        Apply two-stage sizing process
        
        Stage 1: Cap individual positions at max_single_position
        Stage 2: Normalize remaining allocation among uncapped positions
        Stage 3: Handle residual allocation
        
        Args:
            sized_assets: Assets with initial position sizes from DynamicPositionSizer
            
        Returns:
            TwoStageSizingResult with final allocations and metadata
        """
        
        if not sized_assets:
            return TwoStageSizingResult(
                sized_assets=[], stage1_capped_count=0, stage2_capped_count=0,
                total_allocated=0.0, residual_unallocated=0.0,
                residual_strategy_applied='none', sizing_metadata={}
            )
        
        print(f"\n⚖️  Two-Stage Position Sizing")
        print(f"   Input: {len(sized_assets)} assets to process")
        
        # Stage 1: Apply individual position caps
        capped_assets, uncapped_assets = self._stage1_apply_caps(sized_assets)
        stage1_capped_count = len(capped_assets)
        
        print(f"   Stage 1: {stage1_capped_count} assets capped at {self.max_single_position:.1%}")
        
        # Stage 2: Distribute remaining allocation among uncapped positions
        remaining_unallocated = self._stage2_distribute_remaining(capped_assets, uncapped_assets)
        
        # Count assets that became capped in stage 2
        stage2_capped_count = len([a for a in uncapped_assets if getattr(a, 'stage2_capped', False)])
        
        print(f"   Stage 2: {stage2_capped_count} additional assets capped, {remaining_unallocated:.1%} unallocated")
        
        # Combine all assets
        all_assets = capped_assets + uncapped_assets
        
        # Stage 3: Handle residual allocation
        residual_strategy_applied = 'none'
        if remaining_unallocated > 0.01:  # Only if >1% unallocated
            residual_strategy_applied = self.residual_strategy.value
            remaining_unallocated = self._stage3_handle_residual(all_assets, remaining_unallocated)
            print(f"   Stage 3: Applied {residual_strategy_applied}, {remaining_unallocated:.1%} final unallocated")
        
        # Calculate final statistics
        total_allocated = sum(asset.position_size_percentage for asset in all_assets)
        
        # Prepare metadata
        sizing_metadata = {
            'stage1_caps_applied': stage1_capped_count,
            'stage2_caps_applied': stage2_capped_count,
            'residual_strategy_used': residual_strategy_applied,
            'target_allocation': self.target_allocation,
            'allocation_efficiency': total_allocated / self.target_allocation if self.target_allocation > 0 else 0
        }
        
        print(f"   Final: {total_allocated:.1%} allocated, efficiency {sizing_metadata['allocation_efficiency']:.1%}")
        
        return TwoStageSizingResult(
            sized_assets=all_assets,
            stage1_capped_count=stage1_capped_count,
            stage2_capped_count=stage2_capped_count,
            total_allocated=total_allocated,
            residual_unallocated=remaining_unallocated,
            residual_strategy_applied=residual_strategy_applied,
            sizing_metadata=sizing_metadata
        )
    
    def _stage1_apply_caps(self, assets: List[AssetScore]) -> Tuple[List[AssetScore], List[AssetScore]]:
        """
        Stage 1: Cap individual positions at max_single_position
        
        Returns:
            Tuple of (capped_assets, uncapped_assets)
        """
        capped_assets = []
        uncapped_assets = []
        
        for asset in assets:
            original_size = asset.position_size_percentage
            
            if original_size > self.max_single_position:
                # Cap this position
                asset.position_size_percentage = self.max_single_position
                asset.stage1_capped = True
                asset.stage1_original_size = original_size
                asset.stage1_cap_reason = f"Stage 1: Capped from {original_size:.1%} to {self.max_single_position:.1%}"
                capped_assets.append(asset)
            else:
                # This position can still grow
                asset.stage1_capped = False
                uncapped_assets.append(asset)
        
        return capped_assets, uncapped_assets
    
    def _stage2_distribute_remaining(self, capped_assets: List[AssetScore], 
                                   uncapped_assets: List[AssetScore]) -> float:
        """
        Stage 2: Distribute remaining allocation among uncapped positions
        
        Returns:
            remaining_unallocated: Cash that couldn't be allocated
        """
        if not uncapped_assets:
            # All assets were capped in stage 1
            total_capped = sum(asset.position_size_percentage for asset in capped_assets)
            return max(0, self.target_allocation - total_capped)
        
        # Calculate remaining allocation to distribute
        total_capped = sum(asset.position_size_percentage for asset in capped_assets)
        remaining_allocation = max(0, self.target_allocation - total_capped)
        
        if remaining_allocation <= 0:
            return 0.0
        
        # Calculate current uncapped total
        total_uncapped = sum(asset.position_size_percentage for asset in uncapped_assets)
        
        if total_uncapped > 0:
            # Scale uncapped positions to fill remaining allocation
            scale_factor = remaining_allocation / total_uncapped
            
            for asset in uncapped_assets:
                new_size = asset.position_size_percentage * scale_factor
                
                # Re-check cap after scaling
                if new_size > self.max_single_position:
                    asset.position_size_percentage = self.max_single_position
                    asset.stage2_capped = True
                    asset.stage2_cap_reason = f"Stage 2: Capped at {self.max_single_position:.1%} after scaling"
                else:
                    asset.position_size_percentage = new_size
                    asset.stage2_capped = False
                
                # Add sizing reason
                if hasattr(asset, 'sizing_reason'):
                    asset.sizing_reason += f" (stage 2 scaled {scale_factor:.3f}x)"
        
        # Calculate final unallocated amount
        final_total = sum(asset.position_size_percentage for asset in capped_assets + uncapped_assets)
        return max(0, self.target_allocation - final_total)
    
    def _stage3_handle_residual(self, assets: List[AssetScore], residual_amount: float) -> float:
        """
        Stage 3: Handle residual allocation using specified strategy
        
        Returns:
            remaining_unallocated: Cash still unallocated after residual handling
        """
        if residual_amount <= 0.01:  # Less than 1% residual
            return residual_amount
        
        if self.residual_strategy == ResidualStrategy.SAFE_TOP_SLICE:
            return self._apply_safe_top_slice(assets, residual_amount)
        elif self.residual_strategy == ResidualStrategy.PROPORTIONAL:
            return self._apply_proportional_residual(assets, residual_amount)
        elif self.residual_strategy == ResidualStrategy.CASH_BUCKET:
            return self._apply_cash_bucket_residual(assets, residual_amount)
        else:
            return residual_amount  # No strategy applied
    
    def _apply_safe_top_slice(self, assets: List[AssetScore], residual: float) -> float:
        """
        Safe top slice: Add residual to top-scoring uncapped positions with safety limits
        """
        # Find positions that weren't capped in either stage
        uncapped_positions = [a for a in assets 
                            if not getattr(a, 'stage1_capped', False) 
                            and not getattr(a, 'stage2_capped', False)]
        
        if not uncapped_positions:
            # All positions were capped, use cash bucket strategy
            return self._apply_cash_bucket_residual(assets, residual)
        
        # Sort by combined score (highest first)
        uncapped_positions.sort(key=lambda x: x.combined_score, reverse=True)
        
        # Take top 3 positions for residual allocation
        top_positions = uncapped_positions[:min(3, len(uncapped_positions))]
        residual_per_position = residual / len(top_positions)
        
        allocated_residual = 0.0
        
        for position in top_positions:
            # Check if adding residual would exceed max position size
            current_size = position.position_size_percentage
            max_additional = self.max_single_position - current_size
            
            # Apply safety limit: max 5% of portfolio as residual per asset
            max_residual_per_asset = 0.05
            safe_additional = min(residual_per_position, max_additional, max_residual_per_asset)
            
            if safe_additional > 0.001:  # Minimum 0.1% to avoid tiny allocations
                position.position_size_percentage += safe_additional
                position.residual_added = safe_additional
                position.residual_reason = f"Top slice residual: +{safe_additional:.1%}"
                allocated_residual += safe_additional
        
        return residual - allocated_residual
    
    def _apply_proportional_residual(self, assets: List[AssetScore], residual: float) -> float:
        """
        Proportional: Distribute residual proportionally to all positions
        """
        if not assets:
            return residual
        
        current_total = sum(asset.position_size_percentage for asset in assets)
        if current_total <= 0:
            return residual
        
        allocated_residual = 0.0
        
        for asset in assets:
            # Proportional share of residual
            proportion = asset.position_size_percentage / current_total
            proportional_share = residual * proportion
            
            # Check max constraint
            current_size = asset.position_size_percentage
            max_additional = self.max_single_position - current_size
            
            safe_additional = min(proportional_share, max_additional)
            
            if safe_additional > 0.001:  # Minimum 0.1%
                asset.position_size_percentage += safe_additional
                asset.residual_added = safe_additional
                asset.residual_reason = f"Proportional residual: +{safe_additional:.1%}"
                allocated_residual += safe_additional
        
        return residual - allocated_residual
    
    def _apply_cash_bucket_residual(self, assets: List[AssetScore], residual: float) -> float:
        """
        Cash bucket: Create a synthetic cash position for unallocated residual
        """
        # Create synthetic cash position
        from .models import AssetPriority
        
        cash_asset = AssetScore(
            asset='CASH_EQUIVALENT',
            date=assets[0].date if assets else None,
            technical_score=0.0,
            fundamental_score=0.0,
            combined_score=0.0,
            confidence=1.0,  # Cash is always certain
            regime='N/A',
            priority=AssetPriority.REGIME,  # Cash has neutral priority
            timeframes_analyzed=[]
        )
        
        # Set position size and metadata after creation
        cash_asset.position_size_percentage = residual
        cash_asset.is_cash_residual = True
        cash_asset.residual_reason = f"Cash bucket residual: {residual:.1%}"
        cash_asset.sizing_reason = "Cash equivalent for unallocated residual"
        
        assets.append(cash_asset)
        
        return 0.0  # All residual allocated to cash
    
    def get_two_stage_summary(self, result: TwoStageSizingResult) -> Dict[str, Any]:
        """
        Generate comprehensive summary of two-stage sizing
        """
        if not result.sized_assets:
            return {
                'total_assets': 0,
                'two_stage_efficiency': 0.0,
                'stages_summary': 'No assets to size'
            }
        
        # Calculate statistics by stage
        stage1_capped = [a for a in result.sized_assets if getattr(a, 'stage1_capped', False)]
        stage2_capped = [a for a in result.sized_assets if getattr(a, 'stage2_capped', False)]
        residual_modified = [a for a in result.sized_assets if hasattr(a, 'residual_added')]
        cash_positions = [a for a in result.sized_assets if getattr(a, 'is_cash_residual', False)]
        
        # Efficiency metrics
        allocation_efficiency = result.total_allocated / result.sizing_metadata['target_allocation']
        residual_efficiency = 1.0 - (result.residual_unallocated / result.sizing_metadata['target_allocation'])
        
        return {
            'total_assets': len(result.sized_assets),
            'total_allocated': result.total_allocated,
            'target_allocation': result.sizing_metadata['target_allocation'],
            'allocation_efficiency': allocation_efficiency,
            'residual_efficiency': residual_efficiency,
            'two_stage_efficiency': allocation_efficiency * residual_efficiency,
            
            'stage_breakdown': {
                'stage1_capped': len(stage1_capped),
                'stage2_capped': len(stage2_capped),
                'residual_modified': len(residual_modified),
                'cash_positions': len(cash_positions)
            },
            
            'residual_management': {
                'strategy_used': result.residual_strategy_applied,
                'residual_allocated': result.sizing_metadata['target_allocation'] - result.total_allocated - result.residual_unallocated,
                'residual_remaining': result.residual_unallocated
            },
            
            'constraint_compliance': {
                'max_single_position': self.max_single_position,
                'violations': len([a for a in result.sized_assets 
                                if a.position_size_percentage > self.max_single_position + 0.001])
            }
        } 