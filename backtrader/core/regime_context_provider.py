"""
Module 6: Regime Context Provider - Regime Context Provider

This module implements centralized regime context management with module-specific APIs,
override decision authority, and efficient context caching for the entire framework.
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

from .regime_models import (
    RegimeState, RegimeTransition, RegimeContext, TransitionSeverity
)
from .enhanced_regime_detector import EnhancedRegimeDetector
from .regime_change_analyzer import RegimeChangeAnalyzer


class RegimeContextProvider:
    """
    Centralized regime context provider with module-specific APIs and override authority
    """
    
    def __init__(self, enhanced_detector: EnhancedRegimeDetector,
                 change_analyzer: RegimeChangeAnalyzer,
                 parameter_mapper=None,
                 cache_duration_hours=1):
        """
        Initialize regime context provider
        
        Args:
            enhanced_detector: Enhanced regime detector instance
            change_analyzer: Regime change analyzer instance
            parameter_mapper: Regime parameter mapper (optional, will create default)
            cache_duration_hours: How long to cache context objects
        """
        self.detector = enhanced_detector
        self.analyzer = change_analyzer
        self.parameter_mapper = parameter_mapper
        self.cache_duration = timedelta(hours=cache_duration_hours)
        
        # Context caching
        self.context_cache: Dict[str, RegimeContext] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
        
        # Recent transition tracking
        self.recent_transitions: List[RegimeTransition] = []
        self.transition_window_days = 7  # Consider transitions "recent" for 7 days
        
        # Module-specific context customization
        self.module_context_configs = {
            'core_rebalancer': {
                'needs_position_limits': True,
                'needs_score_adjustments': True,
                'needs_regime_change_info': True,
                'override_types': ['position_limits']
            },
            'bucket_diversification': {
                'needs_bucket_preferences': True,
                'needs_allocation_adjustments': True,
                'needs_override_permissions': True,
                'override_types': ['bucket_limits']
            },
            'dynamic_sizing': {
                'needs_sizing_mode_override': True,
                'needs_risk_scaling': True,
                'needs_volatility_adjustment': True,
                'override_types': []
            },
            'lifecycle_management': {
                'needs_grace_period_override': True,
                'needs_holding_period_override': True,
                'needs_regime_change_context': True,
                'override_types': ['grace_period', 'holding_period']
            },
            'core_asset_management': {
                'needs_designation_adjustments': True,
                'needs_favored_assets': True,
                'needs_transition_opportunities': True,
                'override_types': ['core_asset_designation']
            }
        }
        
        # Performance tracking
        self.performance_stats = {
            'context_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'override_decisions': 0,
            'module_requests': defaultdict(int)
        }
    
    def get_current_context(self, current_date: datetime,
                          data_manager=None) -> RegimeContext:
        """
        Get comprehensive regime context for current date
        
        Args:
            current_date: Current date for context
            data_manager: Data manager for regime detection
            
        Returns:
            Complete RegimeContext object
        """
        self.performance_stats['context_requests'] += 1
        
        # Check cache first
        cache_key = current_date.strftime('%Y-%m-%d-%H')
        if self._is_cache_valid(cache_key, current_date):
            self.performance_stats['cache_hits'] += 1
            return self.context_cache[cache_key]
        
        self.performance_stats['cache_misses'] += 1
        
        # Detect current regime
        current_regime = self.detector.detect_current_regime(current_date, data_manager)
        
        # Check for recent transitions
        recent_transition = self._get_recent_transition(current_date)
        
        # If no recent transition, check for new transition
        if not recent_transition:
            recent_transition = self._check_for_new_transition(current_date)
        
        # Build historical context
        historical_context = self._build_historical_context(current_date)
        
        # Calculate override permissions
        override_permissions = self._calculate_override_permissions(
            current_regime, recent_transition
        )
        
        # Get parameter adjustments
        parameter_adjustments = self._get_parameter_adjustments(
            current_regime, recent_transition
        )
        
        # Build module-specific context
        module_specific_context = self._build_module_context(
            current_regime, recent_transition, parameter_adjustments
        )
        
        # Create comprehensive context
        context = RegimeContext(
            current_regime=current_regime,
            recent_transition=recent_transition,
            historical_context=historical_context,
            override_permissions=override_permissions,
            parameter_adjustments=parameter_adjustments,
            module_specific_context=module_specific_context,
            context_timestamp=current_date
        )
        
        # Cache and return
        self._cache_context(cache_key, context, current_date)
        return context
    
    def get_module_context(self, module_name: str, current_date: datetime,
                          data_manager=None) -> Dict[str, Any]:
        """
        Get regime context tailored for specific module
        
        Args:
            module_name: Name of requesting module
            current_date: Current date
            data_manager: Data manager for regime detection
            
        Returns:
            Module-specific context dictionary
        """
        self.performance_stats['module_requests'][module_name] += 1
        
        full_context = self.get_current_context(current_date, data_manager)
        module_context = full_context.get_module_context(module_name)
        
        # Add module-specific metadata
        module_context['request_timestamp'] = current_date
        module_context['context_age_minutes'] = (
            current_date - full_context.context_timestamp
        ).total_seconds() / 60
        
        return module_context
    
    def can_override_protection(self, protection_type: str, current_date: datetime,
                              data_manager=None) -> Tuple[bool, str]:
        """
        Authoritative decision on regime-based protection overrides
        
        Args:
            protection_type: Type of protection ('grace_period', 'holding_period', etc.)
            current_date: Current date
            data_manager: Data manager for regime detection
            
        Returns:
            Tuple of (can_override: bool, reason: str)
        """
        self.performance_stats['override_decisions'] += 1
        
        context = self.get_current_context(current_date, data_manager)
        
        # Check if recent transition allows override
        if context.recent_transition:
            severity = context.recent_transition.severity
            transition_desc = f"{context.recent_transition.from_regime} → {context.recent_transition.to_regime}"
            
            # Override rules based on transition severity
            if severity == TransitionSeverity.CRITICAL:
                # Critical transitions can override most protections
                override_allowed = protection_type in [
                    'grace_period', 'holding_period', 'whipsaw_protection', 'position_limits'
                ]
                reason = f"Critical regime transition: {transition_desc}"
                
            elif severity == TransitionSeverity.HIGH:
                # High severity can override some protections
                override_allowed = protection_type in ['grace_period', 'holding_period', 'position_limits']
                reason = f"High-severity regime transition: {transition_desc}"
                
            else:
                # Normal transitions generally don't override
                override_allowed = False
                reason = f"Normal regime transition ({transition_desc}) - insufficient severity for {protection_type} override"
        else:
            override_allowed = False
            reason = "No recent regime transition"
        
        # Log override decision
        if override_allowed:
            print(f"🔓 Override GRANTED for {protection_type}: {reason}")
        else:
            print(f"🔒 Override DENIED for {protection_type}: {reason}")
        
        return override_allowed, reason
    
    def _is_cache_valid(self, cache_key: str, current_date: datetime) -> bool:
        """
        Check if cached context is still valid
        
        Args:
            cache_key: Cache key to check
            current_date: Current date
            
        Returns:
            True if cache is valid, False otherwise
        """
        if cache_key not in self.context_cache:
            return False
        
        cache_time = self.cache_timestamps.get(cache_key)
        if not cache_time:
            return False
        
        age = current_date - cache_time
        return age <= self.cache_duration
    
    def _cache_context(self, cache_key: str, context: RegimeContext, 
                      current_date: datetime):
        """
        Cache context object with timestamp
        
        Args:
            cache_key: Key for caching
            context: Context to cache
            current_date: Current date
        """
        self.context_cache[cache_key] = context
        self.cache_timestamps[cache_key] = current_date
        
        # Clean old cache entries
        self._clean_old_cache_entries(current_date)
    
    def _clean_old_cache_entries(self, current_date: datetime):
        """
        Remove old cache entries to prevent memory bloat
        
        Args:
            current_date: Current date for age calculation
        """
        cutoff_time = current_date - self.cache_duration * 2  # Keep double duration for safety
        
        keys_to_remove = []
        for cache_key, cache_time in self.cache_timestamps.items():
            if cache_time < cutoff_time:
                keys_to_remove.append(cache_key)
        
        for key in keys_to_remove:
            self.context_cache.pop(key, None)
            self.cache_timestamps.pop(key, None)
    
    def _get_recent_transition(self, current_date: datetime) -> Optional[RegimeTransition]:
        """
        Get most recent transition within window
        
        Args:
            current_date: Current date
            
        Returns:
            Most recent transition or None
        """
        cutoff_date = current_date - timedelta(days=self.transition_window_days)
        
        # Check confirmed transitions from analyzer
        confirmed_transitions = self.analyzer.get_recent_transitions(
            days=self.transition_window_days
        )
        
        if confirmed_transitions:
            return confirmed_transitions[0]  # Most recent
        
        # Check pending transitions
        for transition in self.analyzer.pending_transitions:
            if transition.transition_date >= cutoff_date:
                return transition
        
        return None
    
    def _check_for_new_transition(self, current_date: datetime) -> Optional[RegimeTransition]:
        """
        Check if there's a new transition to detect
        
        Args:
            current_date: Current date
            
        Returns:
            New transition if detected, None otherwise
        """
        # Get regime history for comparison
        history = self.detector.get_regime_history(days=2)
        
        if len(history) >= 2:
            previous_regime = history[-2]
            current_regime = history[-1]
            
            # Check for transition with analyzer
            transition = self.analyzer.analyze_potential_transition(
                previous_regime, current_regime, current_date
            )
            
            if transition:
                # Add to recent transitions tracking
                self.recent_transitions.append(transition)
                return transition
        
        return None
    
    def _build_historical_context(self, current_date: datetime) -> Dict[str, Any]:
        """
        Build historical context for regime analysis
        
        Args:
            current_date: Current date
            
        Returns:
            Historical context dictionary
        """
        # Get regime history
        regime_history = self.detector.get_regime_history(days=30)
        
        # Get transition statistics
        transition_stats = self.analyzer.get_transition_statistics()
        
        # Calculate regime stability trends
        stability_trends = self._calculate_stability_trends(regime_history)
        
        # Recent regime distribution
        recent_regimes = [r.regime for r in regime_history[-14:]]  # Last 2 weeks
        regime_distribution = {
            regime: recent_regimes.count(regime) / len(recent_regimes)
            for regime in set(recent_regimes)
        } if recent_regimes else {}
        
        return {
            'regime_history_length': len(regime_history),
            'transition_statistics': transition_stats,
            'stability_trends': stability_trends,
            'recent_regime_distribution': regime_distribution,
            'last_transition_date': (
                transition_stats.get('last_transition_date') if transition_stats else None
            ),
            'regime_volatility_score': self._calculate_regime_volatility(regime_history)
        }
    
    def _calculate_stability_trends(self, regime_history: List[RegimeState]) -> Dict[str, str]:
        """
        Calculate stability trends for each regime
        
        Args:
            regime_history: List of regime states
            
        Returns:
            Dictionary mapping regime to trend direction
        """
        trends = {}
        
        # Group by regime
        regime_groups = defaultdict(list)
        for state in regime_history:
            regime_groups[state.regime].append(state.stability)
        
        # Calculate trends
        for regime, stabilities in regime_groups.items():
            if len(stabilities) < 3:
                trends[regime] = 'insufficient_data'
                continue
            
            # Simple trend analysis
            recent_avg = sum(stabilities[-3:]) / 3
            earlier_avg = sum(stabilities[:-3]) / max(1, len(stabilities) - 3)
            
            if recent_avg > earlier_avg * 1.1:
                trends[regime] = 'improving'
            elif recent_avg < earlier_avg * 0.9:
                trends[regime] = 'declining'
            else:
                trends[regime] = 'stable'
        
        return trends
    
    def _calculate_regime_volatility(self, regime_history: List[RegimeState]) -> float:
        """
        Calculate regime volatility score
        
        Args:
            regime_history: List of regime states
            
        Returns:
            Volatility score (0.0-1.0)
        """
        if len(regime_history) < 5:
            return 0.5  # Neutral volatility with insufficient data
        
        # Count regime changes
        regime_changes = 0
        for i in range(1, len(regime_history)):
            if regime_history[i].regime != regime_history[i-1].regime:
                regime_changes += 1
        
        # Calculate change frequency
        change_frequency = regime_changes / (len(regime_history) - 1)
        
        # Normalize to 0-1 (assuming max reasonable frequency is 0.5)
        volatility = min(change_frequency / 0.5, 1.0)
        
        return volatility
    
    def _calculate_override_permissions(self, current_regime: RegimeState,
                                      recent_transition: Optional[RegimeTransition]) -> Dict[str, bool]:
        """
        Calculate which protection systems can be overridden
        
        Args:
            current_regime: Current regime state
            recent_transition: Recent transition if any
            
        Returns:
            Dictionary of override permissions
        """
        permissions = {
            'grace_period': False,
            'holding_period': False,
            'whipsaw_protection': False,
            'bucket_limits': False,
            'position_limits': False,
            'core_asset_designation': False
        }
        
        if recent_transition:
            if recent_transition.severity == TransitionSeverity.CRITICAL:
                permissions.update({
                    'grace_period': True,
                    'holding_period': True,
                    'whipsaw_protection': True,
                    'position_limits': True,
                    'bucket_limits': True
                })
            elif recent_transition.severity == TransitionSeverity.HIGH:
                permissions.update({
                    'grace_period': True,
                    'holding_period': True,
                    'position_limits': True,
                    'core_asset_designation': True
                })
        
        return permissions
    
    def _get_parameter_adjustments(self, current_regime: RegimeState,
                                 recent_transition: Optional[RegimeTransition]) -> Dict[str, Any]:
        """
        Get parameter adjustments for current regime and transition context
        
        Args:
            current_regime: Current regime state
            recent_transition: Recent transition if any
            
        Returns:
            Dictionary of parameter adjustments
        """
        if self.parameter_mapper:
            return self.parameter_mapper.get_regime_adjustments(
                current_regime, recent_transition
            )
        
        # Default parameter adjustments if no mapper
        return self._get_default_parameter_adjustments(current_regime, recent_transition)
    
    def _get_default_parameter_adjustments(self, current_regime: RegimeState,
                                         recent_transition: Optional[RegimeTransition]) -> Dict[str, Any]:
        """
        Get default parameter adjustments when no parameter mapper is available
        
        Args:
            current_regime: Current regime state
            recent_transition: Recent transition if any
            
        Returns:
            Default parameter adjustments
        """
        regime_defaults = {
            'Goldilocks': {
                'position_limit_multiplier': 1.1,
                'score_threshold_adjustment': -0.02,
                'risk_scaling_factor': 1.0,
                'sizing_mode_override': None
            },
            'Deflation': {
                'position_limit_multiplier': 0.8,
                'score_threshold_adjustment': 0.05,
                'risk_scaling_factor': 0.7,
                'sizing_mode_override': 'equal_weight'
            },
            'Inflation': {
                'position_limit_multiplier': 0.9,
                'score_threshold_adjustment': 0.0,
                'risk_scaling_factor': 0.85,
                'sizing_mode_override': None
            },
            'Reflation': {
                'position_limit_multiplier': 1.2,
                'score_threshold_adjustment': -0.03,
                'risk_scaling_factor': 1.1,
                'sizing_mode_override': 'score_weighted'
            }
        }
        
        base_adjustments = regime_defaults.get(current_regime.regime, regime_defaults['Goldilocks'])
        
        # Apply transition-based modifications
        if recent_transition:
            if recent_transition.severity == TransitionSeverity.CRITICAL:
                base_adjustments['position_limit_multiplier'] *= 1.3
                base_adjustments['score_threshold_adjustment'] -= 0.03
            elif recent_transition.severity == TransitionSeverity.HIGH:
                base_adjustments['position_limit_multiplier'] *= 1.1
                base_adjustments['score_threshold_adjustment'] -= 0.01
        
        return base_adjustments
    
    def _build_module_context(self, current_regime: RegimeState,
                            recent_transition: Optional[RegimeTransition],
                            parameter_adjustments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build context tailored for each module
        
        Args:
            current_regime: Current regime state
            recent_transition: Recent transition if any
            parameter_adjustments: Parameter adjustments
            
        Returns:
            Module-specific context dictionary
        """
        module_contexts = {}
        
        for module_name, config in self.module_context_configs.items():
            context = {
                'regime_state': current_regime,
                'regime_changed': recent_transition is not None,
                'transition_severity': recent_transition.severity_str if recent_transition else 'none'
            }
            
            # Add module-specific context based on config
            if config.get('needs_position_limits'):
                context['position_limit_multiplier'] = parameter_adjustments.get('position_limit_multiplier', 1.0)
            
            if config.get('needs_score_adjustments'):
                context['score_threshold_adjustment'] = parameter_adjustments.get('score_threshold_adjustment', 0.0)
            
            if config.get('needs_regime_change_info') or config.get('needs_regime_change_context'):
                context['regime_change_context'] = {
                    'changed': recent_transition is not None,
                    'severity': recent_transition.severity_str if recent_transition else 'none',
                    'from_regime': recent_transition.from_regime if recent_transition else None,
                    'to_regime': recent_transition.to_regime if recent_transition else None,
                    'confidence': recent_transition.confidence if recent_transition else None,
                    'momentum': recent_transition.momentum if recent_transition else None
                }
            
            if config.get('needs_bucket_preferences'):
                context['preferred_buckets'] = self._get_regime_preferred_buckets(current_regime.regime)
                context['bucket_allocation_adjustments'] = parameter_adjustments.get('bucket_adjustments', {})
            
            if config.get('needs_override_permissions'):
                context['override_allowed'] = recent_transition and recent_transition.severity in [
                    TransitionSeverity.HIGH, TransitionSeverity.CRITICAL
                ]
            
            if config.get('needs_sizing_mode_override'):
                context['sizing_mode_override'] = parameter_adjustments.get('sizing_mode_override')
                context['risk_scaling_factor'] = parameter_adjustments.get('risk_scaling_factor', 1.0)
            
            if config.get('needs_volatility_adjustment'):
                context['volatility_adjustment'] = self._calculate_volatility_adjustment(current_regime)
            
            if config.get('needs_grace_period_override'):
                context['grace_period_override'] = (
                    recent_transition and recent_transition.severity != TransitionSeverity.NORMAL
                )
            
            if config.get('needs_holding_period_override'):
                context['holding_period_override'] = (
                    recent_transition and recent_transition.severity in [
                        TransitionSeverity.HIGH, TransitionSeverity.CRITICAL
                    ]
                )
            
            if config.get('needs_designation_adjustments'):
                context['designation_threshold_adjustment'] = parameter_adjustments.get(
                    'core_asset_threshold_adj', 0.0
                )
            
            if config.get('needs_favored_assets'):
                context['regime_favored_assets'] = self._get_regime_favored_assets(current_regime.regime)
            
            if config.get('needs_transition_opportunities'):
                context['transition_opportunity'] = (
                    recent_transition and recent_transition.severity in [
                        TransitionSeverity.HIGH, TransitionSeverity.CRITICAL
                    ]
                )
            
            module_contexts[module_name] = context
        
        return module_contexts
    
    def _get_regime_preferred_buckets(self, regime: str) -> Dict[str, float]:
        """
        Get regime-specific bucket preferences
        
        Args:
            regime: Regime name
            
        Returns:
            Dictionary mapping bucket to preference weight
        """
        preferences = {
            'Goldilocks': {
                'Risk Assets': 0.45,
                'Defensive Assets': 0.25,
                'International': 0.20,
                'Commodities': 0.10
            },
            'Deflation': {
                'Risk Assets': 0.20,
                'Defensive Assets': 0.45,
                'International': 0.15,
                'Commodities': 0.20
            },
            'Inflation': {
                'Risk Assets': 0.30,
                'Defensive Assets': 0.20,
                'International': 0.25,
                'Commodities': 0.25
            },
            'Reflation': {
                'Risk Assets': 0.50,
                'Defensive Assets': 0.15,
                'International': 0.25,
                'Commodities': 0.10
            }
        }
        
        return preferences.get(regime, preferences['Goldilocks'])
    
    def _get_regime_favored_assets(self, regime: str) -> List[str]:
        """
        Get regime-favored asset categories
        
        Args:
            regime: Regime name
            
        Returns:
            List of favored asset categories
        """
        favored = {
            'Goldilocks': ['technology', 'growth', 'large_cap'],
            'Deflation': ['treasuries', 'utilities', 'consumer_staples'],
            'Inflation': ['commodities', 'energy', 'real_estate'],
            'Reflation': ['financials', 'industrials', 'small_cap']
        }
        
        return favored.get(regime, [])
    
    def _calculate_volatility_adjustment(self, regime_state: RegimeState) -> float:
        """
        Calculate volatility adjustment factor for sizing
        
        Args:
            regime_state: Current regime state
            
        Returns:
            Volatility adjustment factor
        """
        base_adjustments = {
            'Goldilocks': 1.0,   # Normal volatility
            'Deflation': 0.7,    # Reduce for high volatility
            'Inflation': 0.85,   # Moderate reduction
            'Reflation': 1.1     # Slight increase for stable recovery
        }
        
        base_adjustment = base_adjustments.get(regime_state.regime, 1.0)
        
        # Adjust based on regime strength and stability
        strength_factor = 0.8 + (regime_state.strength * 0.4)  # 0.8-1.2 range
        stability_factor = 0.9 + (regime_state.stability * 0.2)  # 0.9-1.1 range
        
        return base_adjustment * strength_factor * stability_factor
    
    def get_performance_statistics(self) -> Dict[str, Any]:
        """
        Get performance statistics for the context provider
        
        Returns:
            Performance statistics dictionary
        """
        stats = self.performance_stats.copy()
        
        # Calculate cache efficiency
        total_requests = stats['cache_hits'] + stats['cache_misses']
        if total_requests > 0:
            stats['cache_hit_rate'] = stats['cache_hits'] / total_requests
        else:
            stats['cache_hit_rate'] = 0.0
        
        # Add cache status
        stats['cache_size'] = len(self.context_cache)
        stats['module_request_distribution'] = dict(stats['module_requests'])
        
        return stats
    
    def clear_cache(self):
        """Clear all cached contexts"""
        self.context_cache.clear()
        self.cache_timestamps.clear()
    
    def reset_performance_stats(self):
        """Reset performance statistics"""
        self.performance_stats = {
            'context_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'override_decisions': 0,
            'module_requests': defaultdict(int)
        } 