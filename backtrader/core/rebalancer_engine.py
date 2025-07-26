import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from .universe_builder import UniverseBuilder
from .scoring_service import ScoringService
from .selection_service import SelectionService
from .bucket_manager import BucketManager
from .bucket_limits_enforcer import BucketLimitsEnforcer, BucketLimitsConfig
from .grace_period_manager import GracePeriodManager
from .holding_period_manager import RegimeAwareHoldingPeriodManager
from .position_lifecycle_tracker import PositionLifecycleTracker
from .whipsaw_protection_manager import WhipsawProtectionManager
from .models import RebalancingLimits, RebalancingTarget

class CoreRebalancerEngine:
    """
    Enhanced main engine for portfolio rebalancing with comprehensive lifecycle management.
    
    Integrates all Module 1-4 components:
    - Universe building and asset scoring (Module 1)
    - Bucket diversification (Module 2) 
    - Dynamic position sizing (Module 3)
    - Grace periods, holding periods, lifecycle tracking, and whipsaw protection (Module 4)
    """
    
    def __init__(self, regime_detector: Any, asset_manager: Any, 
                 technical_analyzer: Any = None, fundamental_analyzer: Any = None,
                 data_manager: Any = None):
        
        self.regime_detector = regime_detector  # Store for regime context generation
        self.universe_builder = UniverseBuilder(regime_detector, asset_manager)
        self.scoring_service = ScoringService(
            technical_analyzer=technical_analyzer,
            fundamental_analyzer=fundamental_analyzer
        )
        self.data_manager = data_manager
        
        # Module 2: Bucket diversification components
        self.bucket_manager = BucketManager(asset_manager)
        self.bucket_enforcer = BucketLimitsEnforcer(self.bucket_manager)
        
        # Module 4: Initialize lifecycle management components
        self.grace_period_manager = GracePeriodManager()
        self.holding_period_manager = RegimeAwareHoldingPeriodManager()
        self.lifecycle_tracker = PositionLifecycleTracker()
        self.whipsaw_protection = WhipsawProtectionManager()
        
        # Module 1: Enhanced selection service with lifecycle management
        self.selection_service = SelectionService(
            enable_dynamic_sizing=True,
            grace_period_manager=self.grace_period_manager,
            holding_period_manager=self.holding_period_manager,
            lifecycle_tracker=self.lifecycle_tracker,
            whipsaw_protection=self.whipsaw_protection
        )
        
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
        
        # Initialize lifecycle managers with current limits
        self._update_lifecycle_manager_configs(limits)
        
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
        
        # Step 3.5: Generate regime context for lifecycle management
        print(f"\n🌡️ Step 3.5: Generating Regime Context")
        regime_context = self._get_regime_context(rebalance_date)
        
        # Step 4: Select assets with lifecycle management
        print(f"\n🎯 Step {'4' if limits.enable_bucket_diversification else '3'}: Selecting Portfolio (with Lifecycle Management)")
        selected_assets = self.selection_service.select_by_score(
            scored_assets=scored_assets,
            limits=limits,
            current_positions=current_positions,
            current_date=rebalance_date,
            regime_context=regime_context
        )
        
        # Step 4/5: Create final targets with dynamic sizing
        print(f"\n⚖️  Step {'5' if limits.enable_bucket_diversification else '4'}: Creating Rebalancing Targets")
        targets = self.selection_service.create_rebalancing_targets(
            selected_assets=selected_assets,
            current_positions=current_positions,
            target_allocation=limits.target_total_allocation,
            limits=limits  # Pass limits for dynamic sizing configuration
        )
        
        # Step 6: Update lifecycle tracking for position changes
        print(f"\n📊 Step 6: Updating Position Lifecycle Tracking")
        self._update_position_lifecycle_tracking(targets, rebalance_date)
        
        # Step 7: Generate lifecycle management report
        print(f"\n📋 Step 7: Generating Lifecycle Report")
        lifecycle_report = self._generate_lifecycle_report(rebalance_date)
        
        print(f"\n✅ Rebalancing Complete: {len(targets)} targets generated")
        print(f"📊 Lifecycle Report: {lifecycle_report.get('summary', {}).get('active_positions', 0)} active positions tracked")
        
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
    
    def _update_lifecycle_manager_configs(self, limits: RebalancingLimits):
        """Update lifecycle manager configurations from limits."""
        if limits.enable_grace_periods and self.grace_period_manager:
            # Recreate with new config if parameters changed
            if (self.grace_period_manager.grace_period_days != limits.grace_period_days or
                self.grace_period_manager.decay_rate != limits.grace_decay_rate or
                self.grace_period_manager.min_decay_factor != limits.min_decay_factor):
                
                self.grace_period_manager = GracePeriodManager(
                    grace_period_days=limits.grace_period_days,
                    decay_rate=limits.grace_decay_rate,
                    min_decay_factor=limits.min_decay_factor
                )
        
        if self.holding_period_manager:
            # Recreate with new config if parameters changed
            if (self.holding_period_manager.min_holding_days != limits.min_holding_period_days or
                self.holding_period_manager.max_holding_days != limits.max_holding_period_days or
                self.holding_period_manager.regime_override_cooldown != limits.regime_override_cooldown_days):
                
                self.holding_period_manager = RegimeAwareHoldingPeriodManager(
                    min_holding_days=limits.min_holding_period_days,
                    max_holding_days=limits.max_holding_period_days,
                    regime_override_cooldown=limits.regime_override_cooldown_days
                )
        
        if limits.enable_whipsaw_protection and self.whipsaw_protection:
            # Recreate with new config if parameters changed
            if (self.whipsaw_protection.max_cycles_per_period != limits.max_cycles_per_protection_period or
                self.whipsaw_protection.protection_period_days != limits.whipsaw_protection_days or
                self.whipsaw_protection.min_position_duration_hours != limits.min_position_duration_hours):
                
                self.whipsaw_protection = WhipsawProtectionManager(
                    max_cycles_per_period=limits.max_cycles_per_protection_period,
                    protection_period_days=limits.whipsaw_protection_days,
                    min_position_duration_hours=limits.min_position_duration_hours
                )
        
        # Update selection service with new managers
        self.selection_service.grace_period_manager = self.grace_period_manager
        self.selection_service.holding_period_manager = self.holding_period_manager
        self.selection_service.whipsaw_protection = self.whipsaw_protection
    
    def _get_regime_context(self, current_date: datetime) -> Dict:
        """Generate regime context for holding period override decisions."""
        try:
            current_regime = None
            regime_changed = False
            regime_severity = 'normal'
            
            # Try to get current regime if regime detector has the method
            if hasattr(self.regime_detector, 'get_current_regime'):
                current_regime = self.regime_detector.get_current_regime(current_date)
            elif hasattr(self.regime_detector, 'get_market_regime'):
                current_regime = self.regime_detector.get_market_regime(current_date)
            
            # For now, we'll assume no regime change (this could be enhanced)
            # In a real implementation, this would track regime changes over time
            
            return {
                'current_regime': current_regime,
                'regime_changed': regime_changed,
                'regime_severity': regime_severity,
                'change_date': current_date,
                'old_regime': None,
                'new_regime': current_regime
            }
        except Exception as e:
            print(f"⚠️ Could not generate regime context: {e}")
            return {
                'current_regime': 'Unknown',
                'regime_changed': False,
                'regime_severity': 'normal',
                'change_date': current_date
            }
    
    def _update_position_lifecycle_tracking(self, targets: List[RebalancingTarget], current_date: datetime):
        """Update position lifecycle tracking based on rebalancing targets."""
        if not self.lifecycle_tracker:
            return
        
        for target in targets:
            if target.action == 'open':
                # Track new position entry
                self.lifecycle_tracker.track_position_entry(
                    asset=target.asset,
                    entry_date=current_date,
                    entry_size=target.target_allocation_pct,
                    entry_score=target.score,
                    entry_reason=target.reason,
                    bucket=self._get_asset_bucket(target.asset)
                )
                
                # Record in holding period manager
                if self.holding_period_manager:
                    self.holding_period_manager.record_position_entry(
                        asset=target.asset,
                        entry_date=current_date,
                        entry_size=target.target_allocation_pct,
                        entry_reason=target.reason
                    )
                
                # Record in whipsaw protection
                if self.whipsaw_protection:
                    self.whipsaw_protection.record_position_event(
                        asset=target.asset,
                        event_type='open',
                        event_date=current_date,
                        position_size=target.target_allocation_pct,
                        reason=target.reason
                    )
            
            elif target.action == 'close':
                # Record position closure
                self.lifecycle_tracker.record_position_closure(
                    asset=target.asset,
                    closure_date=current_date,
                    closure_reason=target.reason,
                    final_score=target.score
                )
                
                # Record in holding period manager
                if self.holding_period_manager:
                    self.holding_period_manager.record_position_closure(
                        asset=target.asset,
                        closure_date=current_date,
                        closure_reason=target.reason
                    )
                
                # Record in whipsaw protection
                if self.whipsaw_protection:
                    self.whipsaw_protection.record_position_event(
                        asset=target.asset,
                        event_type='close',
                        event_date=current_date,
                        position_size=target.current_allocation_pct,
                        reason=target.reason
                    )
            
            elif target.action in ['increase', 'decrease', 'hold']:
                # Record position adjustment
                if self.holding_period_manager:
                    self.holding_period_manager.record_position_adjustment(
                        asset=target.asset,
                        adjustment_date=current_date,
                        adjustment_type=target.action,
                        adjustment_reason=target.reason
                    )
    
    def _get_asset_bucket(self, asset: str) -> str:
        """Get bucket for an asset (helper method)."""
        try:
            return self.bucket_manager.get_asset_bucket(asset)
        except:
            return 'Unknown'
    
    def _generate_lifecycle_report(self, current_date: datetime) -> Dict:
        """Generate comprehensive lifecycle management report."""
        report = {
            'timestamp': current_date,
            'summary': {
                'active_positions': 0,
                'grace_positions': 0,
                'whipsaw_protected': 0,
                'portfolio_health_score': 100.0
            }
        }
        
        try:
            # Get portfolio lifecycle report
            if self.lifecycle_tracker:
                portfolio_report = self.lifecycle_tracker.get_portfolio_lifecycle_report(current_date)
                report.update(portfolio_report)
            
            # Get grace period status
            if self.grace_period_manager:
                grace_positions = self.grace_period_manager.get_all_grace_positions(current_date)
                report['grace_period_status'] = grace_positions
                report['summary']['grace_positions'] = len(grace_positions)
            
            # Get whipsaw protection status
            if self.whipsaw_protection:
                # Get list of tracked assets for whipsaw report
                tracked_assets = list(self.whipsaw_protection.position_history.keys())
                if tracked_assets:
                    whipsaw_report = self.whipsaw_protection.get_whipsaw_report(tracked_assets, current_date)
                    report['whipsaw_protection_status'] = whipsaw_report
                    report['summary']['whipsaw_protected'] = whipsaw_report['summary']['protected_assets']
            
            # Get holding period status
            if self.holding_period_manager:
                holding_status = self.holding_period_manager.get_all_holding_status(current_date)
                report['holding_period_status'] = holding_status
            
        except Exception as e:
            print(f"⚠️ Error generating lifecycle report: {e}")
        
        return report 