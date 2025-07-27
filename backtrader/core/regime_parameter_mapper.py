"""
Module 6: Regime Context Provider - Regime Parameter Mapper

This module implements sophisticated parameter mapping for different regimes with
dynamic adjustments, parameter interpolation, and configuration validation.
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from collections import defaultdict

from .regime_models import RegimeState, RegimeTransition, TransitionSeverity


@dataclass
class ParameterSet:
    """Complete parameter set for a regime"""
    regime: str
    parameters: Dict[str, Any]
    confidence_threshold: float = 0.7
    stability_threshold: float = 0.6
    interpolation_weight: float = 1.0
    
    def get_parameter(self, param_name: str, default: Any = None) -> Any:
        """Get parameter value with default fallback"""
        return self.parameters.get(param_name, default)
    
    def update_parameter(self, param_name: str, value: Any):
        """Update parameter value"""
        self.parameters[param_name] = value
    
    def is_applicable(self, regime_state: RegimeState) -> bool:
        """Check if parameter set is applicable to regime state"""
        return (regime_state.regime == self.regime and
                regime_state.confidence >= self.confidence_threshold and
                regime_state.stability >= self.stability_threshold)


class RegimeParameterMapper:
    """
    Sophisticated parameter mapping with regime-specific optimization
    """
    
    def __init__(self, enable_interpolation=True, interpolation_smoothing=0.3):
        """
        Initialize regime parameter mapper
        
        Args:
            enable_interpolation: Whether to use parameter interpolation
            interpolation_smoothing: Smoothing factor for parameter transitions
        """
        self.enable_interpolation = enable_interpolation
        self.interpolation_smoothing = interpolation_smoothing
        
        # Initialize regime-specific parameter sets
        self.parameter_sets = self._initialize_regime_parameters()
        
        # Transition-specific adjustments
        self.transition_adjustments = self._initialize_transition_adjustments()
        
        # Parameter validation rules
        self.validation_rules = self._initialize_validation_rules()
        
        # Parameter history for interpolation
        self.parameter_history: List[Dict[str, Any]] = []
        self.max_history_length = 10
        
        # Performance tracking
        self.adjustment_stats = {
            'total_adjustments': 0,
            'interpolations_applied': 0,
            'validation_errors': 0,
            'parameter_changes': defaultdict(int)
        }
    
    def _initialize_regime_parameters(self) -> Dict[str, ParameterSet]:
        """
        Initialize comprehensive parameter sets for each regime
        
        Returns:
            Dictionary mapping regime to parameter set
        """
        return {
            'Goldilocks': ParameterSet(
                regime='Goldilocks',
                parameters={
                    # Position Management
                    'position_limit_multiplier': 1.2,      # Slightly more aggressive
                    'max_new_positions_multiplier': 1.1,
                    'max_total_positions_multiplier': 1.0,
                    
                    # Scoring & Selection
                    'score_threshold_adjustment': -0.05,    # Lower thresholds (more opportunities)
                    'min_score_new_position_adj': -0.03,
                    'trending_confidence_adjustment': -0.1,
                    
                    # Bucket Allocation
                    'bucket_adjustments': {
                        'Risk Assets': 0.45,               # Higher allocation to risk assets
                        'Defensive Assets': 0.25,
                        'International': 0.20,
                        'Commodities': 0.10
                    },
                    'max_bucket_allocation_adj': 0.05,      # Allow slightly more concentration
                    'min_buckets_represented_adj': 0,
                    
                    # Position Sizing
                    'sizing_mode': 'score_weighted',        # Favor higher scoring assets
                    'base_position_size_adj': 0.01,
                    'max_single_position_adj': 0.02,
                    'risk_scaling_factor': 1.0,             # Normal risk scaling
                    
                    # Risk Management
                    'grace_period_days_adj': 0,             # Standard grace periods
                    'holding_period_min_adj': 0,
                    'whipsaw_protection_adj': 0,            # Standard whipsaw protection
                    'volatility_scaling_factor': 1.0,
                    
                    # Core Asset Management
                    'core_asset_threshold_adj': -0.02,     # Slightly easier core designation
                    'core_expiry_days_adj': 0,
                    'max_core_assets_adj': 0
                },
                confidence_threshold=0.7,
                stability_threshold=0.6
            ),
            
            'Deflation': ParameterSet(
                regime='Deflation',
                parameters={
                    # Position Management (Conservative)
                    'position_limit_multiplier': 0.8,       # More conservative
                    'max_new_positions_multiplier': 0.7,
                    'max_total_positions_multiplier': 0.9,
                    
                    # Scoring & Selection (Quality Focus)
                    'score_threshold_adjustment': 0.05,      # Higher thresholds (quality focus)
                    'min_score_new_position_adj': 0.08,
                    'trending_confidence_adjustment': 0.1,
                    
                    # Bucket Allocation (Defensive)
                    'bucket_adjustments': {
                        'Risk Assets': 0.20,                # Lower risk asset allocation
                        'Defensive Assets': 0.45,           # Higher defensive allocation
                        'International': 0.15,
                        'Commodities': 0.20                 # Some commodity protection
                    },
                    'max_bucket_allocation_adj': -0.05,     # Force more diversification
                    'min_buckets_represented_adj': 1,
                    
                    # Position Sizing (Conservative)
                    'sizing_mode': 'equal_weight',          # Conservative equal weighting
                    'base_position_size_adj': -0.02,
                    'max_single_position_adj': -0.05,
                    'risk_scaling_factor': 0.7,            # Reduced risk
                    
                    # Risk Management (Enhanced)
                    'grace_period_days_adj': 2,            # Longer grace periods
                    'holding_period_min_adj': 1,
                    'whipsaw_protection_adj': 3,           # More whipsaw protection
                    'volatility_scaling_factor': 0.6,
                    
                    # Core Asset Management (Restrictive)
                    'core_asset_threshold_adj': 0.03,      # Harder core designation
                    'core_expiry_days_adj': -10,
                    'max_core_assets_adj': -1
                },
                confidence_threshold=0.8,
                stability_threshold=0.7
            ),
            
            'Inflation': ParameterSet(
                regime='Inflation',
                parameters={
                    # Position Management (Moderate)
                    'position_limit_multiplier': 1.0,       # Standard positioning
                    'max_new_positions_multiplier': 0.9,
                    'max_total_positions_multiplier': 1.0,
                    
                    # Scoring & Selection (Balanced)
                    'score_threshold_adjustment': 0.0,      # Standard thresholds
                    'min_score_new_position_adj': 0.02,
                    'trending_confidence_adjustment': 0.0,
                    
                    # Bucket Allocation (Inflation Hedge)
                    'bucket_adjustments': {
                        'Risk Assets': 0.30,                # Moderate risk assets
                        'Defensive Assets': 0.20,
                        'International': 0.25,              # Higher international
                        'Commodities': 0.25                 # Inflation hedge
                    },
                    'max_bucket_allocation_adj': 0.0,
                    'min_buckets_represented_adj': 0,
                    
                    # Position Sizing (Adaptive)
                    'sizing_mode': 'adaptive',              # Adaptive to conditions
                    'base_position_size_adj': 0.0,
                    'max_single_position_adj': 0.0,
                    'risk_scaling_factor': 0.9,            # Slightly reduced risk
                    
                    # Risk Management (Moderate)
                    'grace_period_days_adj': 1,            # Slightly longer grace
                    'holding_period_min_adj': 0,
                    'whipsaw_protection_adj': 1,           # Slightly more protection
                    'volatility_scaling_factor': 0.85,
                    
                    # Core Asset Management (Standard)
                    'core_asset_threshold_adj': 0.0,       # Standard core designation
                    'core_expiry_days_adj': 0,
                    'max_core_assets_adj': 0
                },
                confidence_threshold=0.75,
                stability_threshold=0.65
            ),
            
            'Reflation': ParameterSet(
                regime='Reflation',
                parameters={
                    # Position Management (Aggressive)
                    'position_limit_multiplier': 1.3,       # More aggressive
                    'max_new_positions_multiplier': 1.2,
                    'max_total_positions_multiplier': 1.1,
                    
                    # Scoring & Selection (Opportunity Focus)
                    'score_threshold_adjustment': -0.03,    # Lower thresholds
                    'min_score_new_position_adj': -0.05,
                    'trending_confidence_adjustment': -0.05,
                    
                    # Bucket Allocation (Growth Focus)
                    'bucket_adjustments': {
                        'Risk Assets': 0.50,                # High risk asset allocation
                        'Defensive Assets': 0.15,
                        'International': 0.25,
                        'Commodities': 0.10
                    },
                    'max_bucket_allocation_adj': 0.1,       # Allow more concentration
                    'min_buckets_represented_adj': 0,
                    
                    # Position Sizing (Aggressive)
                    'sizing_mode': 'score_weighted',        # Favor high scores
                    'base_position_size_adj': 0.02,
                    'max_single_position_adj': 0.03,
                    'risk_scaling_factor': 1.1,            # Increased risk
                    
                    # Risk Management (Relaxed)
                    'grace_period_days_adj': -1,           # Shorter grace periods
                    'holding_period_min_adj': 0,
                    'whipsaw_protection_adj': -1,          # Less whipsaw protection
                    'volatility_scaling_factor': 1.15,
                    
                    # Core Asset Management (Easier)
                    'core_asset_threshold_adj': -0.01,     # Easier core designation
                    'core_expiry_days_adj': 5,
                    'max_core_assets_adj': 1
                },
                confidence_threshold=0.65,
                stability_threshold=0.55
            )
        }
    
    def _initialize_transition_adjustments(self) -> Dict[Tuple[str, str], Dict[str, Any]]:
        """
        Initialize transition-specific parameter adjustments
        
        Returns:
            Dictionary mapping transition pairs to adjustments
        """
        return {
            # Critical transitions - major adjustments
            ('Goldilocks', 'Deflation'): {
                'position_limit_multiplier': 0.6,          # Dramatic reduction
                'score_threshold_adjustment': 0.1,          # Much higher quality bar
                'risk_scaling_factor': 0.5,                # Major risk reduction
                'grace_period_days_adj': 3,                # Much longer grace
                'whipsaw_protection_adj': 5,               # Heavy protection
                'transition_duration_days': 14
            },
            
            ('Goldilocks', 'Inflation'): {
                'position_limit_multiplier': 0.8,          # Moderate reduction
                'score_threshold_adjustment': 0.05,         # Higher quality bar
                'risk_scaling_factor': 0.7,                # Risk reduction
                'bucket_allocation_shift': 0.15,           # Shift to commodities
                'transition_duration_days': 10
            },
            
            ('Deflation', 'Inflation'): {
                'position_limit_multiplier': 1.4,          # Aggressive increase
                'score_threshold_adjustment': -0.08,        # Lower thresholds
                'risk_scaling_factor': 1.3,                # Risk increase
                'bucket_allocation_shift': 0.2,            # Major bucket shift
                'transition_duration_days': 7
            },
            
            # High-impact transitions - moderate adjustments
            ('Goldilocks', 'Reflation'): {
                'position_limit_multiplier': 1.15,         # Moderate increase
                'score_threshold_adjustment': -0.02,        # Slightly lower thresholds
                'risk_scaling_factor': 1.05,               # Slight risk increase
                'transition_duration_days': 7
            },
            
            ('Reflation', 'Inflation'): {
                'position_limit_multiplier': 0.9,          # Slight reduction
                'score_threshold_adjustment': 0.03,         # Higher quality
                'risk_scaling_factor': 0.85,               # Risk reduction
                'transition_duration_days': 5
            },
            
            # Recovery transitions
            ('Deflation', 'Reflation'): {
                'position_limit_multiplier': 1.5,          # Strong increase
                'score_threshold_adjustment': -0.05,        # Lower thresholds
                'risk_scaling_factor': 1.4,                # Major risk increase
                'grace_period_days_adj': -2,               # Shorter grace
                'transition_duration_days': 10
            }
        }
    
    def _initialize_validation_rules(self) -> Dict[str, Dict[str, Any]]:
        """
        Initialize parameter validation rules
        
        Returns:
            Dictionary of validation rules by parameter
        """
        return {
            'position_limit_multiplier': {
                'min_value': 0.3,
                'max_value': 2.0,
                'type': float
            },
            'score_threshold_adjustment': {
                'min_value': -0.2,
                'max_value': 0.2,
                'type': float
            },
            'risk_scaling_factor': {
                'min_value': 0.3,
                'max_value': 2.0,
                'type': float
            },
            'grace_period_days_adj': {
                'min_value': -5,
                'max_value': 10,
                'type': int
            },
            'base_position_size_adj': {
                'min_value': -0.05,
                'max_value': 0.05,
                'type': float
            },
            'max_single_position_adj': {
                'min_value': -0.1,
                'max_value': 0.1,
                'type': float
            }
        }
    
    def get_regime_adjustments(self, current_regime: RegimeState,
                             recent_transition: Optional[RegimeTransition] = None) -> Dict[str, Any]:
        """
        Get comprehensive parameter adjustments for current regime and transition context
        
        Args:
            current_regime: Current regime state
            recent_transition: Recent transition if any
            
        Returns:
            Dictionary of parameter adjustments
        """
        self.adjustment_stats['total_adjustments'] += 1
        
        # Get base parameter set for regime
        base_params = self._get_base_parameters(current_regime)
        
        # Apply transition-specific adjustments
        if recent_transition:
            base_params = self._apply_transition_adjustments(
                base_params, recent_transition
            )
        
        # Apply confidence-based scaling
        confidence_scaled_params = self._apply_confidence_scaling(
            base_params, current_regime
        )
        
        # Apply interpolation if enabled
        if self.enable_interpolation:
            final_params = self._apply_parameter_interpolation(
                confidence_scaled_params, current_regime
            )
            self.adjustment_stats['interpolations_applied'] += 1
        else:
            final_params = confidence_scaled_params
        
        # Validate parameters
        validated_params = self._validate_parameters(final_params)
        
        # Track parameter changes
        self._track_parameter_changes(validated_params)
        
        # Update parameter history
        self._update_parameter_history(validated_params)
        
        return validated_params
    
    def _get_base_parameters(self, regime_state: RegimeState) -> Dict[str, Any]:
        """
        Get base parameters for regime
        
        Args:
            regime_state: Current regime state
            
        Returns:
            Base parameter dictionary
        """
        parameter_set = self.parameter_sets.get(regime_state.regime)
        
        if not parameter_set:
            print(f"⚠️ No parameter set for regime {regime_state.regime}, using Goldilocks default")
            parameter_set = self.parameter_sets['Goldilocks']
        
        # Check if parameter set is applicable
        if not parameter_set.is_applicable(regime_state):
            print(f"⚠️ Parameter set not fully applicable for {regime_state.regime} "
                  f"(confidence: {regime_state.confidence:.3f}, stability: {regime_state.stability:.3f})")
            # Still use it but with reduced weight
            parameter_set.interpolation_weight = 0.7
        
        return parameter_set.parameters.copy()
    
    def _apply_transition_adjustments(self, base_params: Dict[str, Any],
                                    transition: RegimeTransition) -> Dict[str, Any]:
        """
        Apply transition-specific parameter adjustments
        
        Args:
            base_params: Base parameter dictionary
            transition: Regime transition
            
        Returns:
            Adjusted parameters
        """
        transition_key = (transition.from_regime, transition.to_regime)
        adjustments = self.transition_adjustments.get(transition_key, {})
        
        if not adjustments:
            # Apply generic adjustments based on severity
            adjustments = self._get_generic_transition_adjustments(transition)
        
        adjusted_params = base_params.copy()
        
        # Apply transition adjustments with momentum weighting
        momentum_weight = transition.momentum
        
        for param, adjustment in adjustments.items():
            if param == 'transition_duration_days':
                continue  # Skip meta-parameter
            
            if param in adjusted_params:
                if isinstance(adjustment, (int, float)):
                    # Multiply adjustments for multiplicative parameters
                    if 'multiplier' in param or 'factor' in param:
                        adjusted_params[param] *= (1 + (adjustment - 1) * momentum_weight)
                    else:
                        # Add adjustments for additive parameters
                        adjusted_params[param] += adjustment * momentum_weight
                elif param == 'bucket_allocation_shift':
                    # Special handling for bucket allocation shifts
                    self._apply_bucket_allocation_shift(adjusted_params, adjustment, momentum_weight)
        
        return adjusted_params
    
    def _get_generic_transition_adjustments(self, transition: RegimeTransition) -> Dict[str, Any]:
        """
        Get generic transition adjustments based on severity
        
        Args:
            transition: Regime transition
            
        Returns:
            Generic adjustment dictionary
        """
        if transition.severity == TransitionSeverity.CRITICAL:
            return {
                'position_limit_multiplier': 0.7,
                'score_threshold_adjustment': 0.05,
                'risk_scaling_factor': 0.6,
                'grace_period_days_adj': 2,
                'whipsaw_protection_adj': 3
            }
        elif transition.severity == TransitionSeverity.HIGH:
            return {
                'position_limit_multiplier': 0.85,
                'score_threshold_adjustment': 0.02,
                'risk_scaling_factor': 0.8,
                'grace_period_days_adj': 1,
                'whipsaw_protection_adj': 1
            }
        else:
            return {
                'position_limit_multiplier': 0.95,
                'score_threshold_adjustment': 0.01,
                'risk_scaling_factor': 0.9
            }
    
    def _apply_bucket_allocation_shift(self, params: Dict[str, Any], 
                                     shift_amount: float, momentum_weight: float):
        """
        Apply bucket allocation shift during transitions
        
        Args:
            params: Parameter dictionary to modify
            shift_amount: Amount to shift allocations
            momentum_weight: Momentum-based weighting
        """
        if 'bucket_adjustments' not in params:
            return
        
        weighted_shift = shift_amount * momentum_weight
        bucket_adjustments = params['bucket_adjustments']
        
        # Example: Shift from risk assets to defensives during stress transitions
        if 'Risk Assets' in bucket_adjustments and 'Defensive Assets' in bucket_adjustments:
            risk_reduction = min(weighted_shift, bucket_adjustments['Risk Assets'] * 0.5)
            bucket_adjustments['Risk Assets'] -= risk_reduction
            bucket_adjustments['Defensive Assets'] += risk_reduction
    
    def _apply_confidence_scaling(self, params: Dict[str, Any],
                                regime_state: RegimeState) -> Dict[str, Any]:
        """
        Scale parameters based on regime confidence and stability
        
        Args:
            params: Parameter dictionary
            regime_state: Current regime state
            
        Returns:
            Confidence-scaled parameters
        """
        scaled_params = params.copy()
        
        # Confidence scaling factor (0.7-1.3 range)
        confidence_factor = 0.7 + (regime_state.confidence * 0.6)
        
        # Stability scaling factor (0.8-1.2 range)
        stability_factor = 0.8 + (regime_state.stability * 0.4)
        
        # Combined scaling
        combined_factor = (confidence_factor + stability_factor) / 2
        
        # Apply scaling to specific parameters
        scalable_params = [
            'position_limit_multiplier',
            'risk_scaling_factor',
            'max_single_position_adj',
            'base_position_size_adj'
        ]
        
        for param in scalable_params:
            if param in scaled_params:
                if 'multiplier' in param or 'factor' in param:
                    # Scale multiplicative parameters
                    scaled_params[param] *= combined_factor
                else:
                    # Scale additive adjustments
                    scaled_params[param] *= combined_factor
        
        return scaled_params
    
    def _apply_parameter_interpolation(self, params: Dict[str, Any],
                                     regime_state: RegimeState) -> Dict[str, Any]:
        """
        Apply parameter interpolation for smooth transitions
        
        Args:
            params: Current parameter dictionary
            regime_state: Current regime state
            
        Returns:
            Interpolated parameters
        """
        if not self.parameter_history:
            return params
        
        previous_params = self.parameter_history[-1]
        interpolated_params = params.copy()
        
        # Apply interpolation to numeric parameters
        for param_name, current_value in params.items():
            if param_name in previous_params:
                previous_value = previous_params[param_name]
                
                if isinstance(current_value, (int, float)) and isinstance(previous_value, (int, float)):
                    # Linear interpolation
                    interpolated_value = (
                        previous_value * self.interpolation_smoothing +
                        current_value * (1 - self.interpolation_smoothing)
                    )
                    interpolated_params[param_name] = interpolated_value
                
                elif isinstance(current_value, dict) and isinstance(previous_value, dict):
                    # Interpolate dictionary values (e.g., bucket_adjustments)
                    interpolated_dict = {}
                    all_keys = set(current_value.keys()) | set(previous_value.keys())
                    
                    for key in all_keys:
                        curr_val = current_value.get(key, 0.0)
                        prev_val = previous_value.get(key, 0.0)
                        
                        if isinstance(curr_val, (int, float)) and isinstance(prev_val, (int, float)):
                            interpolated_dict[key] = (
                                prev_val * self.interpolation_smoothing +
                                curr_val * (1 - self.interpolation_smoothing)
                            )
                        else:
                            interpolated_dict[key] = curr_val
                    
                    interpolated_params[param_name] = interpolated_dict
        
        return interpolated_params
    
    def _validate_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate parameters against rules and fix any violations
        
        Args:
            params: Parameter dictionary to validate
            
        Returns:
            Validated parameter dictionary
        """
        validated_params = params.copy()
        errors_fixed = 0
        
        for param_name, value in params.items():
            if param_name in self.validation_rules:
                rule = self.validation_rules[param_name]
                
                # Type validation
                expected_type = rule.get('type')
                if expected_type and not isinstance(value, expected_type):
                    try:
                        validated_params[param_name] = expected_type(value)
                        errors_fixed += 1
                    except (ValueError, TypeError):
                        print(f"⚠️ Type validation failed for {param_name}: {value}")
                        continue
                
                # Range validation
                if isinstance(value, (int, float)):
                    min_val = rule.get('min_value')
                    max_val = rule.get('max_value')
                    
                    if min_val is not None and value < min_val:
                        validated_params[param_name] = min_val
                        errors_fixed += 1
                    elif max_val is not None and value > max_val:
                        validated_params[param_name] = max_val
                        errors_fixed += 1
        
        if errors_fixed > 0:
            self.adjustment_stats['validation_errors'] += errors_fixed
            print(f"⚠️ Fixed {errors_fixed} parameter validation errors")
        
        return validated_params
    
    def _track_parameter_changes(self, params: Dict[str, Any]):
        """
        Track parameter changes for analytics
        
        Args:
            params: Current parameter dictionary
        """
        if not self.parameter_history:
            return
        
        previous_params = self.parameter_history[-1]
        
        for param_name, current_value in params.items():
            if param_name in previous_params:
                previous_value = previous_params[param_name]
                
                # Check for significant changes
                if isinstance(current_value, (int, float)) and isinstance(previous_value, (int, float)):
                    if abs(current_value - previous_value) > 0.01:  # 1% change threshold
                        self.adjustment_stats['parameter_changes'][param_name] += 1
    
    def _update_parameter_history(self, params: Dict[str, Any]):
        """
        Update parameter history for interpolation
        
        Args:
            params: Parameter dictionary to add to history
        """
        self.parameter_history.append(params.copy())
        
        # Trim history if too long
        if len(self.parameter_history) > self.max_history_length:
            self.parameter_history.pop(0)
    
    def get_parameter_set_info(self, regime: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a parameter set
        
        Args:
            regime: Regime name
            
        Returns:
            Parameter set information
        """
        parameter_set = self.parameter_sets.get(regime)
        if not parameter_set:
            return None
        
        return {
            'regime': parameter_set.regime,
            'parameter_count': len(parameter_set.parameters),
            'confidence_threshold': parameter_set.confidence_threshold,
            'stability_threshold': parameter_set.stability_threshold,
            'parameters': parameter_set.parameters.copy()
        }
    
    def get_transition_adjustment_info(self, from_regime: str, to_regime: str) -> Optional[Dict[str, Any]]:
        """
        Get information about transition adjustments
        
        Args:
            from_regime: Source regime
            to_regime: Target regime
            
        Returns:
            Transition adjustment information
        """
        transition_key = (from_regime, to_regime)
        adjustments = self.transition_adjustments.get(transition_key)
        
        if not adjustments:
            return None
        
        return {
            'transition': f"{from_regime} → {to_regime}",
            'adjustment_count': len(adjustments),
            'adjustments': adjustments.copy()
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get parameter mapping statistics
        
        Returns:
            Statistics dictionary
        """
        stats = self.adjustment_stats.copy()
        
        # Add configuration info
        stats['regime_count'] = len(self.parameter_sets)
        stats['transition_adjustment_count'] = len(self.transition_adjustments)
        stats['validation_rule_count'] = len(self.validation_rules)
        stats['parameter_history_length'] = len(self.parameter_history)
        stats['interpolation_enabled'] = self.enable_interpolation
        
        # Convert defaultdict to regular dict
        stats['parameter_changes'] = dict(stats['parameter_changes'])
        
        return stats
    
    def reset_statistics(self):
        """Reset all statistics"""
        self.adjustment_stats = {
            'total_adjustments': 0,
            'interpolations_applied': 0,
            'validation_errors': 0,
            'parameter_changes': defaultdict(int)
        }
    
    def clear_history(self):
        """Clear parameter history"""
        self.parameter_history.clear()
    
    def update_parameter_set(self, regime: str, parameter_updates: Dict[str, Any]):
        """
        Update parameters for a regime
        
        Args:
            regime: Regime to update
            parameter_updates: Parameters to update
        """
        if regime in self.parameter_sets:
            for param, value in parameter_updates.items():
                self.parameter_sets[regime].update_parameter(param, value)
        else:
            print(f"⚠️ Regime {regime} not found for parameter update")
    
    def add_validation_rule(self, parameter: str, rule: Dict[str, Any]):
        """
        Add validation rule for parameter
        
        Args:
            parameter: Parameter name
            rule: Validation rule dictionary
        """
        self.validation_rules[parameter] = rule 