"""
Module 8: Protection System Orchestrator

Unified protection system orchestrator with priority hierarchy that coordinates
all protection mechanisms (grace periods, holding periods, whipsaw protection,
regime overrides, and core asset immunity) with clear priority hierarchy and
centralized decision-making.
"""

import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime

try:
    from .protection_models import ProtectionRequest, ProtectionDecision, ProtectionResult
    from .enhanced_whipsaw_protection_manager import EnhancedWhipsawProtectionManager
    from .enhanced_grace_period_manager import EnhancedGracePeriodManager
    from .holding_period_manager import HoldingPeriodManager
    from .core_asset_manager import CoreAssetManager
    from .regime_context_provider import RegimeContextProvider
    from ..monitoring.event_writer import EventWriter, get_event_writer
except ImportError:
    # Fallback for testing - use absolute imports
    from core.protection_models import ProtectionRequest, ProtectionDecision, ProtectionResult
    from monitoring.event_writer import EventWriter, get_event_writer


class ProtectionOrchestrator:
    """
    Unified protection system orchestrator with priority hierarchy.
    
    Coordinates all protection mechanisms:
    - Core asset immunity (priority 1)
    - Regime overrides (priority 2) 
    - Grace periods (priority 3)
    - Holding periods (priority 4)
    - Whipsaw protection (priority 5)
    """
    
    def __init__(self, 
                 core_asset_manager: CoreAssetManager = None,
                 grace_period_manager: EnhancedGracePeriodManager = None,
                 holding_period_manager: HoldingPeriodManager = None,
                 whipsaw_protection_manager: EnhancedWhipsawProtectionManager = None,
                 regime_context_provider: RegimeContextProvider = None,
                 event_writer: EventWriter = None):
        """
        Initialize protection orchestrator with all protection systems.
        
        Args:
            core_asset_manager: Core asset management system
            grace_period_manager: Grace period protection
            holding_period_manager: Holding period enforcement
            whipsaw_protection_manager: Whipsaw cycle prevention
            regime_context_provider: Regime change context
            event_writer: Event logging system
        """
        self.core_asset_manager = core_asset_manager
        self.grace_period_manager = grace_period_manager
        self.holding_period_manager = holding_period_manager
        self.whipsaw_protection_manager = whipsaw_protection_manager
        self.regime_context_provider = regime_context_provider
        self.event_writer = event_writer or get_event_writer()
        
        # Priority hierarchy
        self.priority_hierarchy = {
            1: 'core_asset_immunity',
            2: 'regime_override', 
            3: 'grace_period',
            4: 'holding_period',
            5: 'whipsaw_protection'
        }
        
        # Performance tracking
        self.decisions_processed = 0
        self.decisions_approved = 0
        self.decisions_denied = 0
        self.override_count = 0
        
        # Log orchestrator initialization
        self.event_writer.log_event(
            event_type='protection_orchestrator_init',
            event_category='protection',
            action='init',
            reason='Protection orchestrator initialized',
            metadata={
                'priority_hierarchy': self.priority_hierarchy,
                'managers_enabled': {
                    'core_asset': core_asset_manager is not None,
                    'grace_period': grace_period_manager is not None,
                    'holding_period': holding_period_manager is not None,
                    'whipsaw_protection': whipsaw_protection_manager is not None,
                    'regime_context': regime_context_provider is not None
                }
            }
        )
    
    def can_execute_action(self, request: ProtectionRequest) -> ProtectionDecision:
        """
        Central decision authority for all position actions.
        
        Args:
            request: Protection request with action details
            
        Returns:
            ProtectionDecision with approval/denial and detailed reasoning
        """
        self.decisions_processed += 1
        decision_start_time = time.time()
        
        try:
            # Generate decision trace ID
            decision_trace_id = self.event_writer.start_trace(
                f'protection_decision_{request.asset}_{request.action}'
            )
            
            # Log decision request
            self.event_writer.log_event(
                event_type='protection_decision_start',
                event_category='protection',
                action='start',
                reason=f'Protection decision requested: {request.action} {request.asset}',
                asset=request.asset,
                trace_id=decision_trace_id,
                metadata={
                    'action': request.action,
                    'current_size': request.current_size,
                    'target_size': request.target_size,
                    'current_score': request.current_score,
                    'reason': request.reason
                }
            )
            
            # Apply protection hierarchy
            decision = self._apply_protection_hierarchy(request, decision_trace_id)
            
            # Update statistics
            if decision.approved:
                self.decisions_approved += 1
            else:
                self.decisions_denied += 1
            
            if decision.override_applied:
                self.override_count += 1
            
            decision_time = (time.time() - decision_start_time) * 1000
            decision.decision_time_ms = decision_time
            
            # Log final decision
            self.event_writer.log_event(
                event_type='protection_decision_complete',
                event_category='protection',
                action='approve' if decision.approved else 'deny',
                reason=decision.reason,
                asset=request.asset,
                trace_id=decision_trace_id,
                execution_time_ms=decision_time,
                metadata={
                    'approved': decision.approved,
                    'blocking_systems': decision.blocking_systems,
                    'override_applied': decision.override_applied,
                    'override_reason': decision.override_reason,
                    'decision_hierarchy': [r.system_name for r in decision.decision_hierarchy],
                    'performance_stats': {
                        'decisions_processed': self.decisions_processed,
                        'approval_rate': self.decisions_approved / self.decisions_processed,
                        'override_rate': self.override_count / self.decisions_processed
                    }
                }
            )
            
            self.event_writer.end_trace(decision_trace_id, success=True)
            
            return decision
            
        except Exception as e:
            decision_time = (time.time() - decision_start_time) * 1000
            
            # Log decision error
            self.event_writer.log_error(
                error_type='protection_decision',
                error_message=f'Protection decision failed: {str(e)}',
                asset=request.asset,
                metadata={
                    'action': request.action,
                    'execution_time_ms': decision_time,
                    'error_type': type(e).__name__
                }
            )
            
            # Return conservative decision (deny on error)
            return ProtectionDecision(
                approved=False,
                reason=f'Protection decision failed: {str(e)}',
                blocking_systems=['error'],
                override_applied=False
            )
    
    def _apply_protection_hierarchy(self, request: ProtectionRequest, 
                                  trace_id: str) -> ProtectionDecision:
        """
        Apply protection hierarchy with override logic.
        
        Args:
            request: Protection request
            trace_id: Trace ID for event logging
            
        Returns:
            ProtectionDecision with detailed reasoning
        """
        
        # Initialize decision tracking
        protection_results = []
        blocking_systems = []
        override_applied = False
        override_reason = None
        
        # Get regime context for override decisions
        regime_context = None
        if self.regime_context_provider:
            try:
                regime_context = self.regime_context_provider.get_regime_context(request.current_date)
            except Exception as e:
                self.event_writer.log_error(
                    'regime_context_fetch',
                    f'Failed to get regime context: {str(e)}',
                    request.asset
                )
        
        # Priority 1: Core Asset Immunity (highest priority)
        core_result = self._check_core_asset_immunity(request, trace_id)
        protection_results.append(core_result)
        
        if core_result.blocks_action:
            return ProtectionDecision(
                approved=False,
                reason=core_result.reason,
                blocking_systems=[core_result.system_name],
                override_applied=False,
                decision_hierarchy=protection_results
            )
        
        # Priority 2: Regime Override Check
        regime_override_available = self._check_regime_override_availability(
            request, regime_context, trace_id
        )
        
        # Priority 3-5: Standard Protection Chain
        protection_checks = [
            ('grace_period', self._check_grace_period_protection),
            ('holding_period', self._check_holding_period_protection),
            ('whipsaw_protection', self._check_whipsaw_protection)
        ]
        
        for system_name, check_function in protection_checks:
            result = check_function(request, trace_id)
            protection_results.append(result)
            
            if result.blocks_action:
                # Check if regime override can bypass this protection
                if (regime_override_available and 
                    self._can_regime_override_system(system_name, regime_context)):
                    
                    # Apply regime override
                    override_applied = True
                    regime_severity = regime_context.get('regime_severity', 'unknown') if regime_context else 'unknown'
                    new_regime = regime_context.get('new_regime', 'unknown') if regime_context else 'unknown'
                    override_reason = f"Regime override bypassed {system_name}: {regime_severity} severity {new_regime} transition"
                    
                    # Log override application
                    self.event_writer.log_event(
                        event_type='protection_override_applied',
                        event_category='protection',
                        action='override',
                        reason=override_reason,
                        asset=request.asset,
                        trace_id=trace_id,
                        regime=regime_context.get('new_regime') if regime_context else None,
                        metadata={
                            'overridden_system': system_name,
                            'regime_severity': regime_severity,
                            'original_block_reason': result.reason
                        }
                    )
                    
                    # Continue to next protection check
                    continue
                else:
                    # Cannot override, action is blocked
                    blocking_systems.append(system_name)
        
        # Determine final decision
        if blocking_systems:
            # Action blocked by non-overrideable systems
            return ProtectionDecision(
                approved=False,
                reason=f"Action blocked by: {', '.join(blocking_systems)}",
                blocking_systems=blocking_systems,
                override_applied=override_applied,
                override_reason=override_reason,
                decision_hierarchy=protection_results
            )
        else:
            # Action approved
            approval_reason = "All protection checks passed"
            if override_applied:
                approval_reason += f" (with regime override: {override_reason})"
            
            return ProtectionDecision(
                approved=True,
                reason=approval_reason,
                blocking_systems=[],
                override_applied=override_applied,
                override_reason=override_reason,
                decision_hierarchy=protection_results
            )
    
    def _check_core_asset_immunity(self, request: ProtectionRequest, 
                                 trace_id: str) -> ProtectionResult:
        """Check core asset immunity (highest priority)."""
        start_time = time.time()
        
        if not self.core_asset_manager:
            return ProtectionResult(
                system_name='core_asset_immunity',
                blocks_action=False,
                reason='Core asset manager not available',
                priority=1,
                check_time_ms=(time.time() - start_time) * 1000
            )
        
        try:
            is_core = self.core_asset_manager.is_core_asset(request.asset)
            
            if is_core and request.action in ['close', 'decrease']:
                return ProtectionResult(
                    system_name='core_asset_immunity',
                    blocks_action=True,
                    reason=f'Core asset {request.asset} protected from {request.action}',
                    priority=1,
                    check_time_ms=(time.time() - start_time) * 1000,
                    metadata={'core_asset': True}
                )
            
            return ProtectionResult(
                system_name='core_asset_immunity',
                blocks_action=False,
                reason='Core asset check passed' if is_core else 'Not a core asset',
                priority=1,
                check_time_ms=(time.time() - start_time) * 1000,
                metadata={'core_asset': is_core}
            )
            
        except Exception as e:
            return ProtectionResult(
                system_name='core_asset_immunity',
                blocks_action=False,
                reason=f'Core asset check failed: {str(e)}',
                priority=1,
                check_time_ms=(time.time() - start_time) * 1000,
                metadata={'error': str(e)}
            )
    
    def _check_grace_period_protection(self, request: ProtectionRequest, 
                                     trace_id: str) -> ProtectionResult:
        """Check grace period protection."""
        start_time = time.time()
        
        if not self.grace_period_manager:
            return ProtectionResult(
                system_name='grace_period',
                blocks_action=False,
                reason='Grace period manager not available',
                priority=3,
                check_time_ms=(time.time() - start_time) * 1000
            )
        
        try:
            in_grace = self.grace_period_manager.is_in_grace_period(request.asset, request.current_date)
            
            if in_grace and request.action == 'close':
                grace_position = self.grace_period_manager.get_grace_position(request.asset)
                return ProtectionResult(
                    system_name='grace_period',
                    blocks_action=True,
                    reason=f'Asset {request.asset} in grace period until {grace_position.grace_end_date}',
                    priority=3,
                    check_time_ms=(time.time() - start_time) * 1000,
                    metadata={
                        'grace_end_date': grace_position.grace_end_date.isoformat() if grace_position else None,
                        'current_decay_factor': grace_position.current_decay_factor if grace_position else None
                    }
                )
            
            return ProtectionResult(
                system_name='grace_period',
                blocks_action=False,
                reason='Grace period check passed',
                priority=3,
                check_time_ms=(time.time() - start_time) * 1000,
                metadata={'in_grace_period': in_grace}
            )
            
        except Exception as e:
            return ProtectionResult(
                system_name='grace_period',
                blocks_action=False,
                reason=f'Grace period check failed: {str(e)}',
                priority=3,
                check_time_ms=(time.time() - start_time) * 1000,
                metadata={'error': str(e)}
            )
    
    def _check_holding_period_protection(self, request: ProtectionRequest, 
                                       trace_id: str) -> ProtectionResult:
        """Check holding period protection."""
        start_time = time.time()
        
        if not self.holding_period_manager:
            return ProtectionResult(
                system_name='holding_period',
                blocks_action=False,
                reason='Holding period manager not available',
                priority=4,
                check_time_ms=(time.time() - start_time) * 1000
            )
        
        try:
            if request.action in ['close', 'decrease'] and request.position_entry_date:
                can_adjust, reason = self.holding_period_manager.can_adjust_position(
                    request.asset,
                    request.position_entry_date,
                    request.current_date,
                    request.action
                )
                
                if not can_adjust:
                    return ProtectionResult(
                        system_name='holding_period',
                        blocks_action=True,
                        reason=reason,
                        priority=4,
                        check_time_ms=(time.time() - start_time) * 1000,
                        metadata={
                            'position_entry_date': request.position_entry_date.isoformat(),
                            'adjustment_type': request.action
                        }
                    )
            
            return ProtectionResult(
                system_name='holding_period',
                blocks_action=False,
                reason='Holding period check passed',
                priority=4,
                check_time_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            return ProtectionResult(
                system_name='holding_period',
                blocks_action=False,
                reason=f'Holding period check failed: {str(e)}',
                priority=4,
                check_time_ms=(time.time() - start_time) * 1000,
                metadata={'error': str(e)}
            )
    
    def _check_whipsaw_protection(self, request: ProtectionRequest, 
                                trace_id: str) -> ProtectionResult:
        """Check whipsaw protection."""
        start_time = time.time()
        
        if not self.whipsaw_protection_manager:
            return ProtectionResult(
                system_name='whipsaw_protection',
                blocks_action=False,
                reason='Whipsaw protection manager not available',
                priority=5,
                check_time_ms=(time.time() - start_time) * 1000
            )
        
        try:
            if request.action == 'open':
                can_open, reason = self.whipsaw_protection_manager.can_open_position(
                    request.asset, request.current_date
                )
                
                if not can_open:
                    return ProtectionResult(
                        system_name='whipsaw_protection',
                        blocks_action=True,
                        reason=reason,
                        priority=5,
                        check_time_ms=(time.time() - start_time) * 1000,
                        metadata={'action': 'open'}
                    )
            
            return ProtectionResult(
                system_name='whipsaw_protection',
                blocks_action=False,
                reason='Whipsaw protection check passed',
                priority=5,
                check_time_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            return ProtectionResult(
                system_name='whipsaw_protection',
                blocks_action=False,
                reason=f'Whipsaw protection check failed: {str(e)}',
                priority=5,
                check_time_ms=(time.time() - start_time) * 1000,
                metadata={'error': str(e)}
            )
    
    def _check_regime_override_availability(self, request: ProtectionRequest,
                                          regime_context: Dict, trace_id: str) -> bool:
        """Check if regime override is available for current conditions."""
        if not regime_context or not self.regime_context_provider:
            return False
        
        # Override is available if there's been a significant regime change
        regime_changed = regime_context.get('regime_changed', False)
        regime_severity = regime_context.get('regime_severity', 'normal')
        
        return regime_changed and regime_severity in ['high', 'critical']
    
    def _can_regime_override_system(self, system_name: str, regime_context: Dict) -> bool:
        """Determine if regime can override specific protection system."""
        if not regime_context:
            return False
        
        regime_severity = regime_context.get('regime_severity', 'normal')
        
        # High severity can override grace period and holding period
        if regime_severity == 'high':
            return system_name in ['grace_period', 'holding_period']
        
        # Critical severity can override grace period, holding period, and whipsaw
        if regime_severity == 'critical':
            return system_name in ['grace_period', 'holding_period', 'whipsaw_protection']
        
        return False
    
    def get_protection_status(self, asset: str, current_date: datetime) -> Dict[str, any]:
        """Get comprehensive protection status for an asset."""
        status = {
            'asset': asset,
            'timestamp': current_date.isoformat(),
            'protections': {}
        }
        
        # Check each protection system
        if self.core_asset_manager:
            status['protections']['core_asset'] = {
                'is_core': self.core_asset_manager.is_core_asset(asset),
                'immune_to_closure': self.core_asset_manager.is_core_asset(asset)
            }
        
        if self.grace_period_manager:
            in_grace = self.grace_period_manager.is_in_grace_period(asset, current_date)
            status['protections']['grace_period'] = {
                'in_grace_period': in_grace,
                'blocks_closure': in_grace
            }
        
        if self.whipsaw_protection_manager:
            can_open, reason = self.whipsaw_protection_manager.can_open_position(asset, current_date)
            status['protections']['whipsaw'] = {
                'can_open_position': can_open,
                'block_reason': reason if not can_open else None
            }
        
        return status
    
    def get_performance_metrics(self) -> Dict[str, any]:
        """Get orchestrator performance metrics."""
        return {
            'decisions_processed': self.decisions_processed,
            'decisions_approved': self.decisions_approved,
            'decisions_denied': self.decisions_denied,
            'approval_rate': self.decisions_approved / max(self.decisions_processed, 1),
            'override_count': self.override_count,
            'override_rate': self.override_count / max(self.decisions_processed, 1),
            'active_managers': {
                'core_asset': self.core_asset_manager is not None,
                'grace_period': self.grace_period_manager is not None,
                'holding_period': self.holding_period_manager is not None,
                'whipsaw_protection': self.whipsaw_protection_manager is not None,
                'regime_context': self.regime_context_provider is not None
            }
        }