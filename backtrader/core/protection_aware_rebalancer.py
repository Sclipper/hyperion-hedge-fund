"""
Protection-Aware Rebalancer Engine - Module 8 Integration

Enhanced rebalancer engine that integrates with the Protection Orchestrator
to validate all position changes through the unified protection system.
"""

import time
from typing import Dict, List, Optional, Any
from datetime import datetime

from .enhanced_rebalancer_engine import EnhancedCoreRebalancerEngine
from .protection_orchestrator import ProtectionOrchestrator
from .protection_models import ProtectionRequest
from .models import RebalancingTarget, RebalancingLimits
from ..monitoring.event_writer import EventWriter, get_event_writer


class ProtectionAwareRebalancerEngine(EnhancedCoreRebalancerEngine):
    """
    Enhanced rebalancer engine with protection orchestrator integration.
    
    Validates all position changes through the unified protection system
    before execution, ensuring compliance with all protection mechanisms.
    """
    
    def __init__(self, regime_detector: Any, asset_manager: Any, 
                 technical_analyzer: Any = None, fundamental_analyzer: Any = None,
                 data_manager: Any = None, event_writer: EventWriter = None,
                 protection_orchestrator: ProtectionOrchestrator = None):
        
        super().__init__(
            regime_detector=regime_detector,
            asset_manager=asset_manager,
            technical_analyzer=technical_analyzer,
            fundamental_analyzer=fundamental_analyzer,
            data_manager=data_manager,
            event_writer=event_writer
        )
        
        # Protection orchestrator integration
        self.protection_orchestrator = protection_orchestrator
        
        # Protection validation metrics
        self.targets_validated = 0
        self.targets_approved = 0
        self.targets_denied = 0
        
        # Log protection-aware engine initialization
        self.event_writer.log_event(
            event_type='protection_aware_rebalancer_init',
            event_category='system',
            action='init',
            reason='Protection-aware rebalancer engine initialized',
            metadata={
                'protection_orchestrator_enabled': protection_orchestrator is not None,
                'base_engine': 'EnhancedCoreRebalancerEngine'
            }
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
        Perform complete rebalancing operation with protection validation.
        
        All position changes are validated through the protection orchestrator
        before being included in the final rebalancing targets.
        """
        
        # Start rebalancing session
        self._session_id = self.event_writer.start_session("protection_aware_rebalancing")
        
        # Log protection-aware rebalancing start
        self.event_writer.log_event(
            event_type='protection_aware_rebalance_start',
            event_category='portfolio',
            action='start',
            reason='Starting protection-aware rebalancing',
            metadata={
                'rebalance_date': rebalance_date.isoformat(),
                'current_positions_count': len(current_positions) if current_positions else 0,
                'protection_validation_enabled': self.protection_orchestrator is not None
            }
        )
        
        rebalance_start_time = time.time()
        
        try:
            # Get proposed targets from parent rebalancer
            proposed_targets = super().rebalance(
                rebalance_date=rebalance_date,
                current_positions=current_positions,
                limits=limits,
                bucket_names=bucket_names,
                min_trending_confidence=min_trending_confidence,
                enable_technical=enable_technical,
                enable_fundamental=enable_fundamental,
                technical_weight=technical_weight,
                fundamental_weight=fundamental_weight
            )
            
            # If protection orchestrator is not available, return original targets
            if not self.protection_orchestrator:
                self.event_writer.log_event(
                    event_type='protection_validation_skipped',
                    event_category='protection',
                    action='skip',
                    reason='Protection orchestrator not available - returning unvalidated targets',
                    metadata={'proposed_targets_count': len(proposed_targets)}
                )
                return proposed_targets
            
            # Validate targets through protection orchestrator
            validated_targets = self._validate_targets_with_protection(
                proposed_targets, current_positions or {}, rebalance_date
            )
            
            rebalance_time = (time.time() - rebalance_start_time) * 1000
            
            # Log protection-aware rebalancing completion
            self.event_writer.log_event(
                event_type='protection_aware_rebalance_complete',
                event_category='portfolio',
                action='complete',
                reason='Protection-aware rebalancing completed',
                execution_time_ms=rebalance_time,
                metadata={
                    'proposed_targets': len(proposed_targets),
                    'validated_targets': len(validated_targets),
                    'targets_filtered': len(proposed_targets) - len(validated_targets),
                    'validation_stats': {
                        'total_validated': self.targets_validated,
                        'total_approved': self.targets_approved,
                        'total_denied': self.targets_denied,
                        'approval_rate': self.targets_approved / max(self.targets_validated, 1)
                    }
                }
            )
            
            return validated_targets
            
        except Exception as e:
            rebalance_time = (time.time() - rebalance_start_time) * 1000
            
            # Log rebalancing error
            self.event_writer.log_error(
                error_type='protection_aware_rebalancing',
                error_message=f'Protection-aware rebalancing failed: {str(e)}',
                metadata={
                    'execution_time_ms': rebalance_time,
                    'error_type': type(e).__name__
                }
            )
            
            raise e
        
        finally:
            # End session
            self.event_writer.end_session({
                'targets_validated': self.targets_validated,
                'targets_approved': self.targets_approved,
                'targets_denied': self.targets_denied
            })
    
    def _validate_targets_with_protection(self, targets: List[RebalancingTarget],
                                        current_positions: Dict[str, float],
                                        current_date: datetime) -> List[RebalancingTarget]:
        """
        Validate all position changes through protection orchestrator.
        
        Args:
            targets: Proposed rebalancing targets
            current_positions: Current position allocations
            current_date: Current date
            
        Returns:
            Filtered list of approved targets
        """
        
        validation_trace_id = self.event_writer.start_trace('protection_validation_batch')
        
        try:
            approved_targets = []
            denied_targets = []
            
            for target in targets:
                self.targets_validated += 1
                
                # Skip 'hold' actions as they don't require protection validation
                if target.action == 'hold':
                    approved_targets.append(target)
                    continue
                
                # Get current position info
                current_size = current_positions.get(target.asset, 0.0)
                
                # Create protection request
                request = ProtectionRequest(
                    asset=target.asset,
                    action=target.action,
                    current_date=current_date,
                    current_size=current_size,
                    target_size=target.target_allocation_pct,
                    current_score=target.score,
                    reason=target.reason,
                    metadata={
                        'priority': target.priority.value,
                        'rebalancing_context': True,
                        'current_allocation_pct': target.current_allocation_pct,
                        'target_allocation_pct': target.target_allocation_pct
                    }
                )
                
                # Get protection decision
                decision = self.protection_orchestrator.can_execute_action(request)
                
                if decision.approved:
                    self.targets_approved += 1
                    approved_targets.append(target)
                    
                    # Update target with protection metadata
                    if not hasattr(target, 'metadata') or target.metadata is None:
                        target.metadata = {}
                    target.metadata['protection_decision'] = decision.to_dict()
                    
                    # Log approved target
                    self.event_writer.log_event(
                        event_type='rebalancing_target_approved',
                        event_category='protection',
                        action='approve',
                        reason=f'Target approved: {decision.reason}',
                        asset=target.asset,
                        trace_id=validation_trace_id,
                        metadata={
                            'action': target.action,
                            'target_allocation': target.target_allocation_pct,
                            'current_allocation': target.current_allocation_pct,
                            'score': target.score,
                            'priority': target.priority.value,
                            'decision': decision.to_dict()
                        }
                    )
                    
                else:
                    self.targets_denied += 1
                    denied_targets.append(target)
                    
                    # Log denied target
                    self.event_writer.log_event(
                        event_type='rebalancing_target_denied',
                        event_category='protection',
                        action='deny',
                        reason=f'Target denied by protection: {decision.reason}',
                        asset=target.asset,
                        trace_id=validation_trace_id,
                        metadata={
                            'original_action': target.action,
                            'target_allocation': target.target_allocation_pct,
                            'current_allocation': target.current_allocation_pct,
                            'blocking_systems': decision.blocking_systems,
                            'override_applied': decision.override_applied,
                            'decision': decision.to_dict()
                        }
                    )
            
            # Log validation summary
            self.event_writer.log_event(
                event_type='protection_validation_complete',
                event_category='protection',
                action='validate',
                reason=f'Protection validation: {len(approved_targets)} approved, {len(denied_targets)} denied',
                trace_id=validation_trace_id,
                metadata={
                    'total_targets': len(targets),
                    'approved_targets': len(approved_targets),
                    'denied_targets': len(denied_targets),
                    'approval_rate': len(approved_targets) / len(targets) if targets else 0,
                    'denied_targets_list': [
                        {
                            'asset': t.asset,
                            'action': t.action,
                            'reason': t.reason
                        } for t in denied_targets
                    ]
                }
            )
            
            return approved_targets
            
        finally:
            self.event_writer.end_trace(validation_trace_id)
    
    def get_protection_validation_stats(self) -> Dict[str, Any]:
        """Get protection validation statistics."""
        return {
            'targets_validated': self.targets_validated,
            'targets_approved': self.targets_approved,
            'targets_denied': self.targets_denied,
            'approval_rate': self.targets_approved / max(self.targets_validated, 1),
            'denial_rate': self.targets_denied / max(self.targets_validated, 1),
            'protection_orchestrator_enabled': self.protection_orchestrator is not None
        }
    
    def reset_validation_stats(self):
        """Reset protection validation statistics."""
        self.targets_validated = 0
        self.targets_approved = 0
        self.targets_denied = 0
        
        self.event_writer.log_event(
            event_type='protection_validation_stats_reset',
            event_category='system',
            action='reset',
            reason='Protection validation statistics reset'
        )