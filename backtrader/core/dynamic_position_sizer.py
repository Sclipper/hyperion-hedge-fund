from typing import List, Dict, Any, Tuple
from enum import Enum
import sys
import os

# Import models
from .models import AssetScore, AssetPriority

class SizingMode(Enum):
    """Available position sizing modes"""
    ADAPTIVE = "adaptive"           # Score-aware + portfolio context (default)
    EQUAL_WEIGHT = "equal_weight"   # Simple equal allocation
    SCORE_WEIGHTED = "score_weighted"  # Pure score-based allocation

class PositionSizeCategory(Enum):
    """Position size categories for adaptive mode"""
    MAX = "max"           # Large positions (high score)
    STANDARD = "standard" # Standard positions 
    HALF = "half"         # Smaller positions
    LIGHT = "light"       # Minimal positions
    NO_POSITION = "none"  # No position

class DynamicPositionSizer:
    """Intelligent position sizing with multiple modes and portfolio context awareness"""
    
    def __init__(self, sizing_mode: str = 'adaptive', 
                 max_single_position: float = 0.15,
                 target_allocation: float = 0.95,
                 min_position_size: float = 0.02):
        
        self.sizing_mode = SizingMode(sizing_mode)
        self.max_single_position = max_single_position
        self.target_allocation = target_allocation
        self.min_position_size = min_position_size
        
        print(f"Dynamic Position Sizer initialized:")
        print(f"  Mode: {self.sizing_mode.value}")
        print(f"  Max single position: {self.max_single_position:.1%}")
        print(f"  Target allocation: {self.target_allocation:.1%}")
        print(f"  Min position size: {self.min_position_size:.1%}")
    
    def calculate_position_sizes(self, scored_assets: List[AssetScore]) -> List[AssetScore]:
        """
        Calculate position sizes using selected sizing mode
        
        Args:
            scored_assets: List of assets to size
            
        Returns:
            List of AssetScore with position_size_percentage populated
        """
        
        if not scored_assets:
            return []
        
        print(f"\n📏 Dynamic Position Sizing ({self.sizing_mode.value})")
        print(f"   Input: {len(scored_assets)} assets to size")
        
        # Apply sizing based on selected mode
        if self.sizing_mode == SizingMode.ADAPTIVE:
            sized_assets = self._adaptive_sizing(scored_assets)
        elif self.sizing_mode == SizingMode.EQUAL_WEIGHT:
            sized_assets = self._equal_weight_sizing(scored_assets)
        elif self.sizing_mode == SizingMode.SCORE_WEIGHTED:
            sized_assets = self._score_weighted_sizing(scored_assets)
        else:
            raise ValueError(f"Unknown sizing mode: {self.sizing_mode}")
        
        # Apply constraints to all modes
        constrained_assets = self._apply_size_constraints(sized_assets)
        
        # Log results
        if constrained_assets:
            total_allocation = sum(asset.position_size_percentage for asset in constrained_assets)
            max_position = max(asset.position_size_percentage for asset in constrained_assets)
            min_position = min(asset.position_size_percentage for asset in constrained_assets)
            
            print(f"   Results: Total allocation {total_allocation:.1%}, "
                  f"Range {min_position:.1%}-{max_position:.1%}")
        else:
            print(f"   Results: No assets selected (all filtered out)")
        
        return constrained_assets
    
    def _adaptive_sizing(self, assets: List[AssetScore]) -> List[AssetScore]:
        """
        Adaptive sizing: Score-aware with portfolio context
        """
        n_positions = len(assets)
        
        # Base size per position (equal weight starting point)
        base_size = self.target_allocation / n_positions
        
        # Calculate score-based multipliers
        for asset in assets:
            category, multiplier = self._get_score_multiplier(asset.combined_score)
            
            # Calculate raw size with portfolio context
            raw_size = base_size * multiplier
            
            # Portfolio priority boost for existing positions
            if hasattr(asset, 'is_current_position') and asset.is_current_position:
                raw_size *= 1.02  # Small bias toward existing positions
                asset.sizing_reason = f"Adaptive: {category.value} ({multiplier:.1f}x) + portfolio bias"
            else:
                asset.sizing_reason = f"Adaptive: {category.value} ({multiplier:.1f}x)"
            
            asset.position_size_percentage = raw_size
            asset.size_category = category
        
        # Normalize to target allocation while preserving relative differences
        self._normalize_to_target(assets)
        
        return assets
    
    def _equal_weight_sizing(self, assets: List[AssetScore]) -> List[AssetScore]:
        """
        Equal weight sizing: Simple equal allocation (backward compatibility)
        """
        n_positions = len(assets)
        equal_size = self.target_allocation / n_positions
        
        for asset in assets:
            asset.position_size_percentage = equal_size
            asset.sizing_reason = f"Equal weight: {equal_size:.1%}"
            asset.size_category = PositionSizeCategory.STANDARD
        
        return assets
    
    def _score_weighted_sizing(self, assets: List[AssetScore]) -> List[AssetScore]:
        """
        Score weighted sizing: Pure score-based allocation
        """
        # Calculate total score
        total_score = sum(asset.combined_score for asset in assets)
        
        if total_score == 0:
            # Fallback to equal weight if no scores
            return self._equal_weight_sizing(assets)
        
        # Allocate proportionally to scores
        for asset in assets:
            score_weight = asset.combined_score / total_score
            raw_size = self.target_allocation * score_weight
            
            asset.position_size_percentage = raw_size
            asset.sizing_reason = f"Score weighted: {score_weight:.1%} of portfolio"
            
            # Assign category based on final size
            if raw_size >= self.target_allocation * 0.15:  # >15% of target
                asset.size_category = PositionSizeCategory.MAX
            elif raw_size >= self.target_allocation * 0.10:  # >10% of target
                asset.size_category = PositionSizeCategory.STANDARD
            elif raw_size >= self.target_allocation * 0.05:  # >5% of target
                asset.size_category = PositionSizeCategory.HALF
            else:
                asset.size_category = PositionSizeCategory.LIGHT
        
        return assets
    
    def _get_score_multiplier(self, combined_score: float) -> Tuple[PositionSizeCategory, float]:
        """
        Get size multiplier and category based on combined score
        
        Args:
            combined_score: Asset's combined score (0.0-1.0)
            
        Returns:
            Tuple of (category, multiplier)
        """
        
        if combined_score >= 0.9:
            return PositionSizeCategory.MAX, 1.5      # 50% larger than base
        elif combined_score >= 0.8:
            return PositionSizeCategory.STANDARD, 1.2  # 20% larger than base
        elif combined_score >= 0.7:
            return PositionSizeCategory.HALF, 1.0      # Base size
        elif combined_score >= 0.6:
            return PositionSizeCategory.LIGHT, 0.8     # 20% smaller than base
        else:
            return PositionSizeCategory.NO_POSITION, 0.0  # No position
    
    def _normalize_to_target(self, assets: List[AssetScore]) -> None:
        """
        Normalize position sizes to target allocation while preserving relative differences
        """
        current_total = sum(asset.position_size_percentage for asset in assets)
        
        if current_total > 0:
            scale_factor = self.target_allocation / current_total
            
            for asset in assets:
                asset.position_size_percentage *= scale_factor
                if hasattr(asset, 'sizing_reason'):
                    asset.sizing_reason += f" (normalized {scale_factor:.3f}x)"
    
    def _apply_size_constraints(self, assets: List[AssetScore]) -> List[AssetScore]:
        """
        Apply min/max position size constraints
        """
        constrained_assets = []
        
        for asset in assets:
            original_size = asset.position_size_percentage
            
            # Apply maximum constraint
            if original_size > self.max_single_position:
                asset.position_size_percentage = self.max_single_position
                asset.was_capped = True
                asset.cap_reason = f"Capped from {original_size:.1%} to {self.max_single_position:.1%}"
            
            # Apply minimum constraint
            elif original_size > 0 and original_size < self.min_position_size:
                asset.position_size_percentage = self.min_position_size
                asset.was_boosted = True
                asset.boost_reason = f"Boosted from {original_size:.1%} to {self.min_position_size:.1%}"
            
            # Skip positions that are too small
            elif original_size <= 0:
                continue
            
            constrained_assets.append(asset)
        
        # Always re-normalize to hit target allocation exactly
        total_after_constraints = sum(asset.position_size_percentage for asset in constrained_assets)
        if total_after_constraints > 0:
            scale_factor = self.target_allocation / total_after_constraints
            
            # Apply scaling but re-check max constraints
            for asset in constrained_assets:
                new_size = asset.position_size_percentage * scale_factor
                
                # Re-check max constraint after scaling
                if new_size > self.max_single_position:
                    asset.position_size_percentage = self.max_single_position
                    asset.was_capped = True
                    asset.cap_reason = f"Re-capped after normalization to {self.max_single_position:.1%}"
                else:
                    asset.position_size_percentage = new_size
                
                if hasattr(asset, 'sizing_reason'):
                    asset.sizing_reason += f" (constraint normalized {scale_factor:.3f}x)"
        
        return constrained_assets
    
    def get_sizing_summary(self, sized_assets: List[AssetScore]) -> Dict[str, Any]:
        """
        Generate summary of sizing decisions
        """
        if not sized_assets:
            return {
                'total_assets': 0,
                'total_allocation': 0.0,
                'sizing_mode': self.sizing_mode.value
            }
        
        # Calculate statistics
        allocations = [asset.position_size_percentage for asset in sized_assets]
        total_allocation = sum(allocations)
        
        # Count by category
        category_counts = {}
        for asset in sized_assets:
            category = getattr(asset, 'size_category', PositionSizeCategory.STANDARD)
            category_counts[category.value] = category_counts.get(category.value, 0) + 1
        
        # Count constraints applied
        capped_count = len([a for a in sized_assets if getattr(a, 'was_capped', False)])
        boosted_count = len([a for a in sized_assets if getattr(a, 'was_boosted', False)])
        
        return {
            'total_assets': len(sized_assets),
            'total_allocation': total_allocation,
            'min_allocation': min(allocations),
            'max_allocation': max(allocations),
            'avg_allocation': total_allocation / len(sized_assets),
            'sizing_mode': self.sizing_mode.value,
            'category_counts': category_counts,
            'constraints_applied': {
                'capped': capped_count,
                'boosted': boosted_count
            },
            'target_allocation': self.target_allocation,
            'allocation_efficiency': total_allocation / self.target_allocation
        } 