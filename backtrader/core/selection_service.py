from typing import List, Dict, Optional
from datetime import datetime
from .models import AssetScore, AssetPriority, RebalancingLimits, RebalancingTarget
from .dynamic_position_sizer import DynamicPositionSizer
from .two_stage_position_sizer import TwoStagePositionSizer
from .grace_period_manager import GracePeriodManager
from .holding_period_manager import RegimeAwareHoldingPeriodManager
from .position_lifecycle_tracker import PositionLifecycleTracker
from .whipsaw_protection_manager import WhipsawProtectionManager

class SelectionService:
    """
    Enhanced service for selecting assets with comprehensive lifecycle management.
    
    Integrates:
    - Grace period management for underperforming positions
    - Holding period constraints with regime override capability
    - Position lifecycle tracking with health assessment
    - Whipsaw protection against rapid cycling
    - Dynamic position sizing with two-stage safety
    """
    
    def __init__(self, 
                 enable_dynamic_sizing: bool = True,
                 grace_period_manager: Optional[GracePeriodManager] = None,
                 holding_period_manager: Optional[RegimeAwareHoldingPeriodManager] = None,
                 lifecycle_tracker: Optional[PositionLifecycleTracker] = None,
                 whipsaw_protection: Optional[WhipsawProtectionManager] = None):
        self.enable_dynamic_sizing = enable_dynamic_sizing
        self.dynamic_sizer = None
        self.two_stage_sizer = None
        
        # Lifecycle management components
        self.grace_period_manager = grace_period_manager
        self.holding_period_manager = holding_period_manager
        self.lifecycle_tracker = lifecycle_tracker
        self.whipsaw_protection = whipsaw_protection
    
    def select_by_score(self, 
                       scored_assets: List[AssetScore], 
                       limits: RebalancingLimits,
                       current_positions: Dict[str, float] = None,
                       current_date: Optional[datetime] = None,
                       regime_context: Optional[Dict] = None) -> List[AssetScore]:
        """
        Enhanced selection with comprehensive lifecycle management.
        
        Args:
            scored_assets: List of scored assets
            limits: Position and scoring limits
            current_positions: Current portfolio allocations
            current_date: Current date for lifecycle calculations
            regime_context: Optional regime context for override decisions
            
        Returns:
            List of selected AssetScore objects with lifecycle management applied
        """
        
        current_positions = current_positions or {}
        
        # STEP 0: Apply lifecycle management if enabled and managers available
        if limits.enable_grace_periods or limits.enable_whipsaw_protection or limits.min_holding_period_days > 0:
            scored_assets = self._apply_lifecycle_management(
                scored_assets, limits, current_positions, current_date, regime_context
            )
        
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
                                  target_allocation: float = 0.95,
                                  limits: RebalancingLimits = None) -> List[RebalancingTarget]:
        """
        Create final rebalancing targets with dynamic position sizing
        
        Args:
            selected_assets: Assets selected for portfolio
            current_positions: Current allocations
            target_allocation: Total target allocation (e.g., 0.95 = 95%)
            limits: Rebalancing limits including dynamic sizing config
            
        Returns:
            List of RebalancingTarget objects
        """
        
        current_positions = current_positions or {}
        limits = limits or RebalancingLimits()
        
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
        
        # Apply dynamic sizing if enabled
        sized_assets = self._apply_dynamic_sizing(selected_assets, limits, target_allocation)
        
        targets = []
        
        # Create targets for sized assets
        for asset_score in sized_assets:
            if getattr(asset_score, 'is_cash_residual', False):
                # Handle cash positions specially
                targets.append(RebalancingTarget(
                    asset=asset_score.asset,
                    target_allocation_pct=asset_score.position_size_percentage,
                    current_allocation_pct=0.0,
                    action='open',
                    priority=AssetPriority.REGIME,
                    score=0.0,
                    reason=getattr(asset_score, 'residual_reason', 'Cash residual allocation')
                ))
                continue
            
            current_alloc = current_positions.get(asset_score.asset, 0.0)
            target_alloc = asset_score.position_size_percentage
            
            # Determine action
            if current_alloc == 0.0:
                action = 'open'
            elif target_alloc > current_alloc * 1.05:  # 5% threshold
                action = 'increase'
            elif target_alloc < current_alloc * 0.95:  # 5% threshold
                action = 'decrease'
            else:
                action = 'hold'
            
            # Enhanced reason with sizing info
            sizing_info = getattr(asset_score, 'sizing_reason', 'Dynamic sizing')
            base_reason = getattr(asset_score, 'selection_reason', 'Selected for portfolio')
            combined_reason = f"{base_reason} | {sizing_info}"
            
            targets.append(RebalancingTarget(
                asset=asset_score.asset,
                target_allocation_pct=target_alloc,
                current_allocation_pct=current_alloc,
                action=action,
                priority=asset_score.priority,
                score=asset_score.combined_score,
                reason=combined_reason
            ))
        
        # Add close targets for positions not selected
        selected_asset_names = [a.asset for a in sized_assets]
        for asset, current_alloc in current_positions.items():
            if asset not in selected_asset_names:
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
        total_target_allocation = 0.0
        for target in targets:
            actions[target.action] = actions.get(target.action, 0) + 1
            total_target_allocation += target.target_allocation_pct
        
        print(f"Rebalancing Targets: {actions}, Total Target: {total_target_allocation:.1%}")
        
        return targets
    
    def _apply_dynamic_sizing(self, selected_assets: List[AssetScore], 
                            limits: RebalancingLimits, 
                            target_allocation: float) -> List[AssetScore]:
        """
        Apply dynamic sizing to selected assets
        """
        if not self.enable_dynamic_sizing or not limits.enable_dynamic_sizing:
            # Fallback to equal weight
            return self._apply_equal_weight_sizing(selected_assets, target_allocation)
        
        # Initialize dynamic sizers if needed
        if not self.dynamic_sizer:
            self.dynamic_sizer = DynamicPositionSizer(
                sizing_mode=limits.sizing_mode,
                max_single_position=limits.max_single_position_pct,  # Use the higher limit for initial sizing
                target_allocation=target_allocation,
                min_position_size=limits.min_position_size
            )
        
        if not self.two_stage_sizer:
            self.two_stage_sizer = TwoStagePositionSizer(
                max_single_position=limits.max_single_position,  # Use the stricter limit for final constraints
                target_allocation=target_allocation,
                residual_strategy=limits.residual_strategy
            )
        
        print(f"\n🎯 Dynamic Position Sizing Pipeline")
        print(f"   Mode: {limits.sizing_mode}")
        print(f"   Initial max position: {limits.max_single_position_pct:.1%}")
        print(f"   Final max position: {limits.max_single_position:.1%}")
        print(f"   Residual strategy: {limits.residual_strategy}")
        
        # Step 1: Dynamic sizing (score-aware, portfolio-context)
        dynamically_sized = self.dynamic_sizer.calculate_position_sizes(selected_assets)
        
        # Step 2: Two-stage sizing (safety constraints, residual management)
        two_stage_result = self.two_stage_sizer.apply_two_stage_sizing(dynamically_sized)
        
        # Log summary
        summary = self.two_stage_sizer.get_two_stage_summary(two_stage_result)
        print(f"   Final efficiency: {summary['two_stage_efficiency']:.1%}")
        print(f"   Stage breakdown: {summary['stage_breakdown']}")
        
        return two_stage_result.sized_assets
    
    def _apply_equal_weight_sizing(self, selected_assets: List[AssetScore], 
                                 target_allocation: float) -> List[AssetScore]:
        """
        Fallback to simple equal weight sizing
        """
        num_positions = len(selected_assets)
        target_per_position = target_allocation / num_positions
        
        for asset in selected_assets:
            asset.position_size_percentage = target_per_position
            asset.sizing_reason = f"Equal weight: {target_per_position:.1%}"
        
        return selected_assets
    
    def _apply_lifecycle_management(self, 
                                  scored_assets: List[AssetScore], 
                                  limits: RebalancingLimits,
                                  current_positions: Dict[str, float],
                                  current_date: Optional[datetime],
                                  regime_context: Optional[Dict]) -> List[AssetScore]:
        """
        Apply comprehensive lifecycle management to asset selection.
        
        Pipeline:
        1. Grace period management for underperforming positions
        2. Holding period constraints (with regime override capability)
        3. Whipsaw protection against rapid cycling
        4. Position lifecycle tracking and health assessment
        """
        if not current_date:
            # If no current date provided, skip lifecycle management
            return scored_assets
        
        print(f"\n🔄 Applying Lifecycle Management Pipeline")
        
        # Step 1: Apply grace period logic to underperforming positions
        grace_managed_assets = self._apply_grace_period_management(
            scored_assets, limits, current_date
        )
        
        # Step 2: Filter by holding period constraints
        holding_period_filtered = self._apply_holding_period_constraints(
            grace_managed_assets, limits, current_date, regime_context
        )
        
        # Step 3: Apply whipsaw protection
        whipsaw_protected = self._apply_whipsaw_protection(
            holding_period_filtered, limits, current_date
        )
        
        # Step 4: Update lifecycle tracking
        self._update_lifecycle_tracking(
            whipsaw_protected, current_positions, current_date
        )
        
        print(f"Lifecycle Management: {len(scored_assets)} → {len(whipsaw_protected)} assets")
        
        return whipsaw_protected
    
    def _apply_grace_period_management(self, 
                                     scored_assets: List[AssetScore],
                                     limits: RebalancingLimits,
                                     current_date: datetime) -> List[AssetScore]:
        """Apply grace period logic to underperforming positions."""
        if not limits.enable_grace_periods or not self.grace_period_manager:
            return scored_assets
        
        print(f"  📉 Applying Grace Period Management")
        
        modified_assets = []
        grace_actions_taken = 0
        
        for asset_score in scored_assets:
            # Only apply grace period to portfolio assets (existing positions)
            if asset_score.priority == AssetPriority.PORTFOLIO:
                grace_action = self.grace_period_manager.handle_underperforming_position(
                    asset=asset_score.asset,
                    current_score=asset_score.combined_score,
                    current_size=asset_score.position_size_percentage or 0.1,  # Default if not set
                    min_threshold=limits.min_score_threshold,
                    current_date=current_date
                )
                
                if grace_action.action in ['grace_start', 'grace_decay', 'grace_recovery']:
                    grace_actions_taken += 1
                    asset_score.position_size_percentage = grace_action.new_size
                    asset_score.selection_reason = f"Grace: {grace_action.reason}"
                    
                    # If grace period expired (force close), don't include in selection
                    if grace_action.action == 'force_close':
                        asset_score.selection_reason = f"Force Close: {grace_action.reason}"
                        continue  # Skip adding to modified_assets
                
                modified_assets.append(asset_score)
            else:
                # Non-portfolio assets pass through unchanged
                modified_assets.append(asset_score)
        
        if grace_actions_taken > 0:
            print(f"    Grace actions applied to {grace_actions_taken} positions")
        
        return modified_assets
    
    def _apply_holding_period_constraints(self, 
                                        scored_assets: List[AssetScore],
                                        limits: RebalancingLimits,
                                        current_date: datetime,
                                        regime_context: Optional[Dict]) -> List[AssetScore]:
        """Apply holding period constraints to position adjustments."""
        if not self.holding_period_manager or limits.min_holding_period_days <= 0:
            return scored_assets
        
        print(f"  ⏳ Applying Holding Period Constraints")
        
        filtered_assets = []
        blocked_adjustments = 0
        regime_overrides = 0
        
        for asset_score in scored_assets:
            # Only apply holding period constraints to portfolio assets
            if asset_score.priority == AssetPriority.PORTFOLIO:
                # Determine adjustment type based on score threshold
                if asset_score.combined_score < limits.min_score_threshold:
                    adjustment_type = 'close'
                else:
                    adjustment_type = 'any'  # Could be increase/decrease based on sizing
                
                can_adjust, reason = self.holding_period_manager.can_adjust_position(
                    asset=asset_score.asset,
                    current_date=current_date,
                    regime_context=regime_context,
                    adjustment_type=adjustment_type
                )
                
                if can_adjust:
                    if "REGIME OVERRIDE" in reason:
                        regime_overrides += 1
                        asset_score.selection_reason = f"Holding: {reason}"
                    filtered_assets.append(asset_score)
                else:
                    blocked_adjustments += 1
                    # Don't include assets that can't be adjusted due to holding period
                    print(f"    Blocked {asset_score.asset}: {reason}")
            else:
                # New positions are not subject to holding period constraints
                filtered_assets.append(asset_score)
        
        if blocked_adjustments > 0:
            print(f"    Blocked {blocked_adjustments} adjustments due to holding periods")
        if regime_overrides > 0:
            print(f"    Applied {regime_overrides} regime overrides")
        
        return filtered_assets
    
    def _apply_whipsaw_protection(self, 
                                scored_assets: List[AssetScore],
                                limits: RebalancingLimits,
                                current_date: datetime) -> List[AssetScore]:
        """Apply whipsaw protection to prevent rapid cycling."""
        if not limits.enable_whipsaw_protection or not self.whipsaw_protection:
            return scored_assets
        
        print(f"  🛡️ Applying Whipsaw Protection")
        
        protected_assets = []
        blocked_opens = 0
        
        for asset_score in scored_assets:
            # Apply whipsaw protection primarily to new positions
            if asset_score.priority != AssetPriority.PORTFOLIO:
                can_open, reason = self.whipsaw_protection.can_open_position(
                    asset=asset_score.asset,
                    current_date=current_date
                )
                
                if can_open:
                    protected_assets.append(asset_score)
                else:
                    blocked_opens += 1
                    print(f"    Blocked {asset_score.asset}: {reason}")
            else:
                # Portfolio assets pass through (whipsaw applies more to rapid open/close)
                protected_assets.append(asset_score)
        
        if blocked_opens > 0:
            print(f"    Blocked {blocked_opens} new positions due to whipsaw protection")
        
        return protected_assets
    
    def _update_lifecycle_tracking(self, 
                                 scored_assets: List[AssetScore],
                                 current_positions: Dict[str, float],
                                 current_date: datetime):
        """Update position lifecycle tracking."""
        if not self.lifecycle_tracker:
            return
        
        print(f"  📊 Updating Lifecycle Tracking")
        
        # Update existing positions
        for asset_score in scored_assets:
            if asset_score.priority == AssetPriority.PORTFOLIO:
                self.lifecycle_tracker.update_position_state(
                    asset=asset_score.asset,
                    current_date=current_date,
                    new_score=asset_score.combined_score,
                    new_size=asset_score.position_size_percentage or 0.0,
                    action_taken='score_update',
                    reason=f"Score updated to {asset_score.combined_score:.3f}"
                )
        
        # Track new position entries
        for asset_score in scored_assets:
            if asset_score.priority != AssetPriority.PORTFOLIO:
                # This will be a new position entry if selected
                # Note: Actual entry tracking happens in the rebalancer engine when positions are opened
                pass 