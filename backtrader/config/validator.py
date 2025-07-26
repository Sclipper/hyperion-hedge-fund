"""
Configuration Validator for Strategy Configuration

Provides comprehensive validation with:
- Type and range validation
- Parameter dependency checking
- Business logic constraints
- Cross-module validation
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from .data_models import StrategyConfiguration
from .parameter_registry import ParameterRegistry


@dataclass
class ValidationError:
    """Single validation error"""
    parameter: str
    message: str
    severity: str = 'error'  # 'error', 'warning', 'info'
    category: str = 'validation'  # 'validation', 'dependency', 'business_logic'


@dataclass 
class ValidationResult:
    """Complete validation result"""
    is_valid: bool = True
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    infos: List[ValidationError] = field(default_factory=list)
    
    def add_error(self, parameter: str, message: str, category: str = 'validation'):
        """Add validation error"""
        self.errors.append(ValidationError(parameter, message, 'error', category))
        self.is_valid = False
    
    def add_warning(self, parameter: str, message: str, category: str = 'validation'):
        """Add validation warning"""
        self.warnings.append(ValidationError(parameter, message, 'warning', category))
    
    def add_info(self, parameter: str, message: str, category: str = 'validation'):
        """Add validation info"""
        self.infos.append(ValidationError(parameter, message, 'info', category))
    
    def merge(self, other: 'ValidationResult'):
        """Merge another validation result"""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.infos.extend(other.infos)
        if not other.is_valid:
            self.is_valid = False
    
    def get_all_messages(self) -> List[str]:
        """Get all validation messages"""
        messages = []
        for error in self.errors:
            messages.append(f"ERROR: {error.parameter}: {error.message}")
        for warning in self.warnings:
            messages.append(f"WARNING: {warning.parameter}: {warning.message}")
        for info in self.infos:
            messages.append(f"INFO: {info.parameter}: {info.message}")
        return messages
    
    def has_errors(self) -> bool:
        """Check if there are any errors"""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if there are any warnings"""
        return len(self.warnings) > 0


class ConfigurationValidator:
    """Comprehensive configuration validator"""
    
    def __init__(self, parameter_registry: Optional[ParameterRegistry] = None):
        self.registry = parameter_registry or ParameterRegistry()
        self.business_rules = self._load_business_rules()
    
    def validate(self, config: StrategyConfiguration) -> ValidationResult:
        """Run comprehensive validation on configuration"""
        result = ValidationResult()
        
        # 1. Built-in configuration validation
        result.merge(self._validate_built_in(config))
        
        # 2. Parameter registry validation
        result.merge(self._validate_against_registry(config))
        
        # 3. Dependency validation
        result.merge(self._validate_dependencies(config))
        
        # 4. Business logic validation
        result.merge(self._validate_business_logic(config))
        
        # 5. Cross-module validation
        result.merge(self._validate_cross_module(config))
        
        return result
    
    def _validate_built_in(self, config: StrategyConfiguration) -> ValidationResult:
        """Use built-in configuration validation methods"""
        result = ValidationResult()
        
        # Use each module's validate method
        for error_msg in config.validate():
            result.add_error('configuration', error_msg, 'built_in')
        
        return result
    
    def _validate_against_registry(self, config: StrategyConfiguration) -> ValidationResult:
        """Validate configuration against parameter registry"""
        result = ValidationResult()
        
        # Get all parameter values from config
        config_values = self._extract_config_values(config)
        
        for param_name, value in config_values.items():
            param_def = self.registry.get_parameter(param_name)
            if not param_def:
                continue  # Skip unknown parameters
            
            # Type validation
            if not isinstance(value, param_def.type):
                result.add_error(
                    param_name,
                    f"Expected {param_def.type.__name__}, got {type(value).__name__}",
                    'type'
                )
                continue
            
            # Range validation for numeric types
            if param_def.min_value is not None and value < param_def.min_value:
                result.add_error(
                    param_name,
                    f"Value {value} below minimum {param_def.min_value}",
                    'range'
                )
            
            if param_def.max_value is not None and value > param_def.max_value:
                result.add_error(
                    param_name,
                    f"Value {value} above maximum {param_def.max_value}",
                    'range'
                )
            
            # Choice validation
            if param_def.choices and value not in param_def.choices:
                result.add_error(
                    param_name,
                    f"Value {value} not in allowed choices: {param_def.choices}",
                    'choice'
                )
            
            # Custom validation rules
            for rule in param_def.validation_rules:
                if not rule.validator(value):
                    result.add_error(param_name, rule.error_message, 'custom')
        
        return result
    
    def _validate_dependencies(self, config: StrategyConfiguration) -> ValidationResult:
        """Validate parameter dependencies"""
        result = ValidationResult()
        
        config_values = self._extract_config_values(config)
        
        for param_name, value in config_values.items():
            param_def = self.registry.get_parameter(param_name)
            if not param_def:
                continue
            
            # Check dependencies
            for dep in param_def.dependencies:
                if dep not in config_values:
                    result.add_error(
                        param_name,
                        f"Depends on parameter '{dep}' which is not configured",
                        'dependency'
                    )
                else:
                    # Check if dependency is enabled/valid
                    dep_value = config_values[dep]
                    dep_def = self.registry.get_parameter(dep)
                    
                    # If dependency is boolean and False, warn about unused parameter
                    if dep_def and dep_def.type == bool and not dep_value:
                        result.add_warning(
                            param_name,
                            f"Parameter depends on '{dep}' which is disabled",
                            'dependency'
                        )
            
            # Check mutual exclusions
            for exclusive in param_def.mutually_exclusive:
                if exclusive in config_values:
                    exclusive_value = config_values[exclusive]
                    # Both are enabled (for boolean params)
                    if (isinstance(value, bool) and isinstance(exclusive_value, bool) 
                        and value and exclusive_value):
                        result.add_error(
                            param_name,
                            f"Cannot be enabled together with '{exclusive}'",
                            'mutual_exclusion'
                        )
        
        return result
    
    def _validate_business_logic(self, config: StrategyConfiguration) -> ValidationResult:
        """Validate business logic constraints"""
        result = ValidationResult()
        
        for rule_name, rule_func in self.business_rules.items():
            try:
                rule_result = rule_func(config)
                result.merge(rule_result)
            except Exception as e:
                result.add_error(
                    'business_logic',
                    f"Business rule '{rule_name}' failed: {str(e)}",
                    'business_logic'
                )
        
        return result
    
    def _validate_cross_module(self, config: StrategyConfiguration) -> ValidationResult:
        """Validate relationships between modules"""
        result = ValidationResult()
        
        # Analysis weights should sum to ~1.0
        total_weight = config.core_config.technical_weight + config.core_config.fundamental_weight
        if abs(total_weight - 1.0) > 0.05:  # Allow 5% tolerance
            result.add_warning(
                'analysis_weights',
                f"Technical + fundamental weights sum to {total_weight:.2f}, should be close to 1.0",
                'cross_module'
            )
        
        # Position limits consistency
        if config.core_config.max_new_positions > config.core_config.max_total_positions:
            result.add_error(
                'position_limits',
                "max_new_positions cannot exceed max_total_positions",
                'cross_module'
            )
        
        # Bucket diversification requires buckets
        if config.bucket_config.enable_bucket_diversification and len(config.system_config.buckets) < 2:
            result.add_warning(
                'bucket_diversification',
                "Bucket diversification enabled but only one bucket specified",
                'cross_module'
            )
        
        # Two-stage sizing constraints
        if (config.sizing_config.enable_two_stage_sizing and 
            config.sizing_config.max_single_position > config.core_config.max_single_position_pct):
            result.add_warning(
                'two_stage_sizing',
                "Two-stage max_single_position exceeds core max_single_position_pct",
                'cross_module'
            )
        
        # Core asset management requires bucket diversification for overrides
        if (config.core_asset_config.enable_core_asset_management and 
            not config.bucket_config.enable_bucket_diversification):
            result.add_warning(
                'core_asset_management',
                "Core asset bucket overrides require bucket diversification to be enabled",
                'cross_module'
            )
        
        # Grace period vs holding period interaction
        if (config.lifecycle_config.enable_grace_periods and 
            config.lifecycle_config.grace_period_days > config.lifecycle_config.min_holding_period_days):
            result.add_info(
                'lifecycle_interaction',
                "Grace period longer than min holding period - grace may complete before holding period",
                'cross_module'
            )
        
        return result
    
    def _extract_config_values(self, config: StrategyConfiguration) -> Dict[str, Any]:
        """Extract all parameter values from configuration"""
        values = {}
        
        # Core rebalancer config
        core_vars = vars(config.core_config)
        for key, value in core_vars.items():
            values[key] = value
        
        # Bucket diversification config
        bucket_vars = vars(config.bucket_config)
        for key, value in bucket_vars.items():
            values[key] = value
        
        # Dynamic sizing config
        sizing_vars = vars(config.sizing_config)
        for key, value in sizing_vars.items():
            values[key] = value
        
        # Lifecycle management config
        lifecycle_vars = vars(config.lifecycle_config)
        for key, value in lifecycle_vars.items():
            values[key] = value
        
        # Core asset management config
        core_asset_vars = vars(config.core_asset_config)
        for key, value in core_asset_vars.items():
            values[key] = value
        
        # System config
        system_vars = vars(config.system_config)
        for key, value in system_vars.items():
            values[key] = value
        
        return values
    
    def _load_business_rules(self) -> Dict[str, Callable]:
        """Load business logic validation rules"""
        return {
            'portfolio_sizing_logic': self._validate_portfolio_sizing,
            'diversification_logic': self._validate_diversification_logic,
            'risk_management_logic': self._validate_risk_management,
            'core_asset_logic': self._validate_core_asset_logic,
            'timing_constraints': self._validate_timing_constraints
        }
    
    def _validate_portfolio_sizing(self, config: StrategyConfiguration) -> ValidationResult:
        """Validate portfolio sizing business logic"""
        result = ValidationResult()
        
        # Check if portfolio can be reasonably sized
        max_positions = config.core_config.max_total_positions
        max_single_pct = config.core_config.max_single_position_pct
        target_allocation = config.core_config.target_total_allocation
        
        # Theoretical minimum allocation if all positions at max size
        theoretical_min = max_positions * max_single_pct
        
        if theoretical_min > target_allocation:
            result.add_error(
                'portfolio_sizing',
                f"Cannot fit {max_positions} positions at max {max_single_pct:.1%} each in {target_allocation:.1%} allocation",
                'business_logic'
            )
        
        # Warn if very little flexibility
        if theoretical_min > target_allocation * 0.8:
            result.add_warning(
                'portfolio_sizing',
                f"Limited sizing flexibility: positions will be near maximum size",
                'business_logic'
            )
        
        # Check bucket allocation vs position limits
        if config.bucket_config.enable_bucket_diversification:
            max_bucket_alloc = config.bucket_config.max_allocation_per_bucket
            max_bucket_positions = config.bucket_config.max_positions_per_bucket
            
            # Can we fit max positions per bucket within allocation limit?
            min_size_per_position = max_bucket_alloc / max_bucket_positions
            
            if min_size_per_position < config.sizing_config.min_position_size:
                result.add_warning(
                    'bucket_sizing',
                    f"Bucket allocation may create positions smaller than minimum size",
                    'business_logic'
                )
        
        return result
    
    def _validate_diversification_logic(self, config: StrategyConfiguration) -> ValidationResult:
        """Validate diversification business logic"""
        result = ValidationResult()
        
        if not config.bucket_config.enable_bucket_diversification:
            return result
        
        # Check if bucket requirements are achievable
        min_buckets = config.bucket_config.min_buckets_represented
        max_positions = config.core_config.max_total_positions
        max_per_bucket = config.bucket_config.max_positions_per_bucket
        
        # Can we satisfy min buckets requirement?
        theoretical_min_positions = min_buckets  # At least 1 per required bucket
        if theoretical_min_positions > max_positions:
            result.add_error(
                'diversification',
                f"Cannot represent {min_buckets} buckets with only {max_positions} total positions",
                'business_logic'
            )
        
        # Check allocation constraints
        max_allocation_per_bucket = config.bucket_config.max_allocation_per_bucket
        target_allocation = config.core_config.target_total_allocation
        
        # If we need min_buckets with max allocation each
        theoretical_min_allocation = min_buckets * max_allocation_per_bucket
        if theoretical_min_allocation > target_allocation:
            result.add_warning(
                'diversification',
                f"Bucket allocation limits may conflict with total allocation target",
                'business_logic'
            )
        
        return result
    
    def _validate_risk_management(self, config: StrategyConfiguration) -> ValidationResult:
        """Validate risk management business logic"""
        result = ValidationResult()
        
        # Grace period vs score threshold
        if config.lifecycle_config.enable_grace_periods:
            grace_days = config.lifecycle_config.grace_period_days
            decay_rate = config.lifecycle_config.grace_decay_rate
            min_threshold = config.core_config.min_score_threshold
            
            # Will grace period be effective?
            if decay_rate > 0.95:
                result.add_warning(
                    'grace_period',
                    f"High decay rate ({decay_rate}) may make grace period ineffective",
                    'business_logic'
                )
            
            if grace_days < 2:
                result.add_warning(
                    'grace_period',
                    f"Very short grace period ({grace_days} days) may not prevent whipsaw",
                    'business_logic'
                )
        
        # Whipsaw protection settings
        if config.lifecycle_config.enable_whipsaw_protection:
            protection_days = config.lifecycle_config.whipsaw_protection_days
            min_duration_hours = config.lifecycle_config.min_position_duration_hours
            
            # Check if settings are reasonable
            if min_duration_hours > 24:
                result.add_info(
                    'whipsaw_protection',
                    f"Minimum position duration of {min_duration_hours} hours may be restrictive",
                    'business_logic'
                )
            
            if protection_days < 7:
                result.add_warning(
                    'whipsaw_protection',
                    f"Short protection period ({protection_days} days) may allow frequent cycling",
                    'business_logic'
                )
        
        return result
    
    def _validate_core_asset_logic(self, config: StrategyConfiguration) -> ValidationResult:
        """Validate core asset management business logic"""
        result = ValidationResult()
        
        if not config.core_asset_config.enable_core_asset_management:
            return result
        
        # Core asset threshold vs scoring
        override_threshold = config.core_asset_config.core_asset_override_threshold
        min_score_new = config.core_config.min_score_new_position
        
        if override_threshold <= min_score_new:
            result.add_warning(
                'core_asset_threshold',
                f"Core asset threshold ({override_threshold}) not much higher than min score for new positions ({min_score_new})",
                'business_logic'
            )
        
        # Core asset count vs total positions
        max_core_assets = config.core_asset_config.max_core_assets
        max_total_positions = config.core_config.max_total_positions
        
        if max_core_assets > max_total_positions * 0.5:
            result.add_warning(
                'core_asset_count',
                f"High proportion of core assets ({max_core_assets}/{max_total_positions}) may reduce flexibility",
                'business_logic'
            )
        
        # Performance monitoring settings
        underperf_threshold = config.core_asset_config.core_asset_underperformance_threshold
        underperf_period = config.core_asset_config.core_asset_underperformance_period
        
        if underperf_threshold > 0.3:
            result.add_warning(
                'core_asset_performance',
                f"High underperformance threshold ({underperf_threshold:.1%}) may rarely trigger",
                'business_logic'
            )
        
        if underperf_period < 14:
            result.add_warning(
                'core_asset_performance',
                f"Short underperformance period ({underperf_period} days) may be too sensitive",
                'business_logic'
            )
        
        return result
    
    def _validate_timing_constraints(self, config: StrategyConfiguration) -> ValidationResult:
        """Validate timing-related constraints"""
        result = ValidationResult()
        
        # Rebalance frequency vs holding periods
        rebalance_freq = config.system_config.rebalance_frequency
        min_holding_days = config.lifecycle_config.min_holding_period_days
        
        freq_days = {'daily': 1, 'weekly': 7, 'monthly': 30}
        rebalance_interval = freq_days.get(rebalance_freq, 30)
        
        if min_holding_days < rebalance_interval:
            result.add_warning(
                'timing_constraints',
                f"Min holding period ({min_holding_days} days) shorter than rebalance frequency ({rebalance_freq})",
                'business_logic'
            )
        
        # Grace period vs rebalance frequency
        if config.lifecycle_config.enable_grace_periods:
            grace_days = config.lifecycle_config.grace_period_days
            if grace_days < rebalance_interval:
                result.add_warning(
                    'grace_timing',
                    f"Grace period ({grace_days} days) shorter than rebalance interval ({rebalance_freq})",
                    'business_logic'
                )
        
        return result 