# Module 11: CLI & Config Management - Implementation Plan

**Implementation Date:** January 15, 2024  
**Status:** 📋 PLANNING  
**Priority:** HIGH - Foundation for all other modules  
**Estimated Effort:** 3-4 days  

## Overview

Module 11 implements a comprehensive configuration management system that centralizes, organizes, and validates all 50+ parameters across the entire backtesting framework. This module provides professional-grade configuration management with parameter tiering, validation, presets, and interactive tools.

## 🎯 Objectives

### **Primary Goals**
1. **Centralize Configuration Management** - Unified system for all 50+ parameters
2. **Parameter Tiering** - Organize by complexity (Basic → Expert)
3. **Module Integration** - Seamless integration across all modules
4. **Professional Validation** - Comprehensive constraints and dependency checking
5. **Configuration Presets** - Industry-standard strategy templates
6. **Import/Export System** - Save/load configurations from files
7. **Interactive Tools** - CLI builders and configuration helpers

### **Strategic Benefits**
- **Reduced Complexity** - Organized parameter hierarchy
- **Better UX** - Tiered complexity for different user levels
- **Consistency** - Centralized validation and defaults
- **Productivity** - Presets and templates for common strategies
- **Maintainability** - Single source of truth for all configuration

## 📊 Current Parameter Inventory

### **Module 1: Core Rebalancer Engine (10 parameters)**
```python
# Basic portfolio management
max_total_positions: int = 10
max_new_positions: int = 3
min_score_threshold: float = 0.6
min_score_new_position: float = 0.65
max_single_position_pct: float = 0.2
target_total_allocation: float = 0.95

# Analysis configuration
enable_technical_analysis: bool = True
enable_fundamental_analysis: bool = True
technical_weight: float = 0.6
fundamental_weight: float = 0.4
```

### **Module 2: Bucket Diversification (6 parameters)**
```python
enable_bucket_diversification: bool = False
max_positions_per_bucket: int = 4
max_allocation_per_bucket: float = 0.4
min_buckets_represented: int = 2
allow_bucket_overflow: bool = False
correlation_limit: float = 0.8
```

### **Module 3: Dynamic Position Sizing (8 parameters)**
```python
enable_dynamic_sizing: bool = True
sizing_mode: str = 'adaptive'
max_single_position: float = 0.15
min_position_size: float = 0.02
residual_strategy: str = 'safe_top_slice'
max_residual_per_asset: float = 0.05
max_residual_multiple: float = 0.5
enable_two_stage_sizing: bool = True
```

### **Module 4: Grace & Holding Period Management (12 parameters)**
```python
enable_grace_periods: bool = True
grace_period_days: int = 5
grace_decay_rate: float = 0.8
min_decay_factor: float = 0.1

min_holding_period_days: int = 3
max_holding_period_days: int = 90
enable_regime_overrides: bool = True
regime_override_cooldown_days: int = 30
regime_severity_threshold: str = 'high'

enable_whipsaw_protection: bool = True
max_cycles_per_protection_period: int = 1
whipsaw_protection_days: int = 14
min_position_duration_hours: int = 4
```

### **Module 5: Core Asset Management (8 parameters)**
```python
enable_core_asset_management: bool = True
core_asset_override_threshold: float = 0.95
core_asset_expiry_days: int = 90
core_asset_underperformance_threshold: float = 0.15
core_asset_underperformance_period: int = 30
max_core_assets: int = 3
core_asset_extension_limit: int = 2
core_asset_performance_check_frequency: int = 7
```

### **Base System Parameters (9 parameters)**
```python
buckets: List[str] = []
start_date: str = '2021-01-01'
end_date: Optional[str] = None
cash: float = 100000
commission: float = 0.001
rebalance_frequency: str = 'monthly'
min_trending_confidence: float = 0.7
timeframes: List[str] = ['1d', '4h', '1h']
plot_results: bool = False
```

### **Future Modules (Estimated 15+ parameters)**
```python
# Module 6: Regime Context Provider
regime_detection_sensitivity: float = 0.8
regime_confirmation_period: int = 5

# Module 7: Advanced Whipsaw Protection  
advanced_whipsaw_algorithms: bool = False
sector_whipsaw_correlation: float = 0.7

# Module 8: Protection System Orchestrator
protection_priority_mode: str = 'hierarchical'
conflict_resolution_strategy: str = 'conservative'

# Module 9: Monitoring & Alerts
enable_performance_alerts: bool = True
alert_thresholds: Dict = {}

# Module 10: Testing & QA Harness
stress_test_scenarios: List[str] = []
monte_carlo_iterations: int = 1000
```

## 🏗️ Architecture Design

### **Core Components**

#### **1. Configuration Hierarchy**
```python
@dataclass
class ParameterTier:
    name: str
    description: str
    target_user: str  # 'beginner', 'intermediate', 'advanced', 'expert'
    complexity_level: int  # 1-5
    parameters: List[str]

class ConfigurationTiers:
    BASIC = ParameterTier(
        name="Basic Portfolio Management",
        description="Essential parameters for basic backtesting",
        target_user="beginner",
        complexity_level=1,
        parameters=[
            'buckets', 'start_date', 'end_date', 'cash', 
            'max_total_positions', 'min_score_threshold'
        ]
    )
    
    INTERMEDIATE = ParameterTier(
        name="Strategy Configuration", 
        description="Enhanced strategy controls and analysis",
        target_user="intermediate",
        complexity_level=2,
        parameters=[
            'enable_technical_analysis', 'technical_weight',
            'enable_bucket_diversification', 'max_positions_per_bucket',
            'sizing_mode', 'target_total_allocation'
        ]
    )
    
    ADVANCED = ParameterTier(
        name="Risk Management",
        description="Sophisticated risk controls and lifecycle management", 
        target_user="advanced",
        complexity_level=3,
        parameters=[
            'enable_grace_periods', 'grace_period_days',
            'min_holding_period_days', 'enable_whipsaw_protection',
            'max_single_position', 'residual_strategy'
        ]
    )
    
    EXPERT = ParameterTier(
        name="Professional Features",
        description="Institutional-grade features and overrides",
        target_user="expert", 
        complexity_level=4,
        parameters=[
            'enable_core_asset_management', 'core_asset_override_threshold',
            'regime_override_cooldown_days', 'protection_priority_mode',
            'advanced_whipsaw_algorithms'
        ]
    )
```

#### **2. Unified Configuration Manager**
```python
class UnifiedConfigurationManager:
    """
    Central configuration management for the entire backtesting framework
    """
    
    def __init__(self):
        self.parameters = self._load_parameter_definitions()
        self.validators = self._load_parameter_validators()
        self.presets = self._load_configuration_presets()
        self.dependencies = self._load_parameter_dependencies()
    
    def create_configuration(self, tier_level: int = 1, 
                           preset: Optional[str] = None) -> StrategyConfiguration:
        """Create configuration for specific tier level or preset"""
        pass
    
    def validate_configuration(self, config: StrategyConfiguration) -> ValidationResult:
        """Comprehensive validation with dependency checking"""
        pass
    
    def export_configuration(self, config: StrategyConfiguration, 
                           format: str = 'yaml') -> str:
        """Export configuration to file format"""
        pass
    
    def import_configuration(self, file_path: str) -> StrategyConfiguration:
        """Import configuration from file"""
        pass
    
    def get_parameter_info(self, parameter_name: str) -> ParameterInfo:
        """Get detailed parameter information and help"""
        pass
```

#### **3. Strategy Configuration Data Model**
```python
@dataclass
class StrategyConfiguration:
    """Unified configuration for all strategy parameters"""
    
    # Metadata
    name: str
    description: str
    tier_level: int
    created_date: datetime
    last_modified: datetime
    
    # Module 1: Core Rebalancer
    core_config: CoreRebalancerConfig
    
    # Module 2: Bucket Diversification
    bucket_config: BucketDiversificationConfig
    
    # Module 3: Dynamic Sizing
    sizing_config: DynamicSizingConfig
    
    # Module 4: Lifecycle Management
    lifecycle_config: LifecycleManagementConfig
    
    # Module 5: Core Asset Management
    core_asset_config: CoreAssetManagementConfig
    
    # Base System
    system_config: SystemConfig
    
    def to_rebalancing_limits(self) -> RebalancingLimits:
        """Convert to RebalancingLimits for backward compatibility"""
        pass
    
    def to_cli_args(self) -> List[str]:
        """Convert to CLI argument list"""
        pass
    
    def validate(self) -> ValidationResult:
        """Self-validation using built-in constraints"""
        pass

@dataclass
class CoreRebalancerConfig:
    max_total_positions: int = 10
    max_new_positions: int = 3
    min_score_threshold: float = 0.6
    min_score_new_position: float = 0.65
    max_single_position_pct: float = 0.2
    target_total_allocation: float = 0.95
    enable_technical_analysis: bool = True
    enable_fundamental_analysis: bool = True
    technical_weight: float = 0.6
    fundamental_weight: float = 0.4

@dataclass
class BucketDiversificationConfig:
    enable_bucket_diversification: bool = False
    max_positions_per_bucket: int = 4
    max_allocation_per_bucket: float = 0.4
    min_buckets_represented: int = 2
    allow_bucket_overflow: bool = False
    correlation_limit: float = 0.8

# ... additional config dataclasses for each module
```

## 🎛️ Implementation Phases

### **Phase 1: Core Configuration Framework (Day 1)**

#### **1.1 Create Parameter Registry**
```python
class ParameterRegistry:
    """Registry of all parameters with metadata and validation rules"""
    
    def __init__(self):
        self.parameters = {}
        self._register_all_parameters()
    
    def register_parameter(self, param: ParameterDefinition):
        """Register a parameter with metadata"""
        self.parameters[param.name] = param
    
    def get_parameter(self, name: str) -> ParameterDefinition:
        """Get parameter definition"""
        return self.parameters.get(name)
    
    def get_parameters_by_tier(self, tier: int) -> List[ParameterDefinition]:
        """Get all parameters for a tier level"""
        return [p for p in self.parameters.values() if p.tier_level <= tier]

@dataclass
class ParameterDefinition:
    name: str
    type: Type
    default_value: Any
    description: str
    tier_level: int  # 1=Basic, 2=Intermediate, 3=Advanced, 4=Expert
    module: str  # Which module owns this parameter
    cli_name: str  # CLI argument name
    validation_rules: List[ValidationRule]
    dependencies: List[str]  # Other parameters this depends on
    mutually_exclusive: List[str]  # Parameters that can't be used together
    help_text: str
    examples: List[str]
```

#### **1.2 Create Configuration Validation Framework**
```python
class ConfigurationValidator:
    """Comprehensive validation with dependency checking"""
    
    def __init__(self, parameter_registry: ParameterRegistry):
        self.registry = parameter_registry
        self.validators = self._load_validators()
    
    def validate(self, config: StrategyConfiguration) -> ValidationResult:
        """Run all validation checks"""
        result = ValidationResult()
        
        # 1. Type validation
        result.merge(self._validate_types(config))
        
        # 2. Range validation
        result.merge(self._validate_ranges(config))
        
        # 3. Dependency validation
        result.merge(self._validate_dependencies(config))
        
        # 4. Mutual exclusion validation
        result.merge(self._validate_mutual_exclusions(config))
        
        # 5. Business logic validation
        result.merge(self._validate_business_logic(config))
        
        return result
    
    def _validate_business_logic(self, config: StrategyConfiguration) -> ValidationResult:
        """Advanced business logic validation"""
        result = ValidationResult()
        
        # Example: Max new positions must be <= max total positions
        if config.core_config.max_new_positions > config.core_config.max_total_positions:
            result.add_error("max_new_positions cannot exceed max_total_positions")
        
        # Example: Technical + fundamental weights should sum to 1.0
        total_weight = config.core_config.technical_weight + config.core_config.fundamental_weight
        if abs(total_weight - 1.0) > 0.01:
            result.add_warning(f"Analysis weights sum to {total_weight:.2f}, will be normalized")
        
        # Example: Core asset threshold should be high if enabled
        if (config.core_asset_config.enable_core_asset_management and 
            config.core_asset_config.core_asset_override_threshold < 0.85):
            result.add_warning("Core asset threshold below 0.85 may cause frequent overrides")
        
        return result
```

#### **1.3 Create Configuration Builder**
```python
class ConfigurationBuilder:
    """Interactive configuration builder for different user levels"""
    
    def __init__(self, registry: ParameterRegistry, validator: ConfigurationValidator):
        self.registry = registry
        self.validator = validator
    
    def build_interactive(self, tier_level: int = 1) -> StrategyConfiguration:
        """Interactive CLI-based configuration builder"""
        print(f"🎛️  Building {self._get_tier_name(tier_level)} Configuration")
        print("="*60)
        
        config = StrategyConfiguration()
        
        # Get parameters for this tier
        parameters = self.registry.get_parameters_by_tier(tier_level)
        
        for param in parameters:
            value = self._prompt_for_parameter(param)
            self._set_parameter_value(config, param.name, value)
        
        # Validate and get feedback
        validation = self.validator.validate(config)
        if not validation.is_valid():
            self._handle_validation_errors(validation, config)
        
        return config
    
    def build_from_preset(self, preset_name: str) -> StrategyConfiguration:
        """Build configuration from a preset template"""
        preset = self._load_preset(preset_name)
        config = preset.to_configuration()
        
        # Validate preset
        validation = self.validator.validate(config)
        if not validation.is_valid():
            raise ValueError(f"Invalid preset '{preset_name}': {validation.errors}")
        
        return config
```

### **Phase 2: CLI Integration Framework (Day 1-2)**

#### **2.1 Enhanced CLI Parser**
```python
class TieredArgumentParser:
    """Multi-tiered CLI argument parser with progressive disclosure"""
    
    def __init__(self, registry: ParameterRegistry):
        self.registry = registry
        self.parser = argparse.ArgumentParser(description="Hedge Fund Backtesting Framework")
        self._setup_base_commands()
    
    def _setup_base_commands(self):
        """Setup base command structure"""
        subparsers = self.parser.add_subparsers(dest='mode', help='Execution mode')
        
        # Basic mode (Tier 1 parameters only)
        basic_parser = subparsers.add_parser('basic', 
                                           help='Basic backtesting (Tier 1 parameters)')
        self._add_tier_arguments(basic_parser, tier_level=1)
        
        # Advanced mode (Tier 1-3 parameters)
        advanced_parser = subparsers.add_parser('advanced',
                                              help='Advanced backtesting (Tier 1-3 parameters)')
        self._add_tier_arguments(advanced_parser, tier_level=3)
        
        # Expert mode (All parameters)
        expert_parser = subparsers.add_parser('expert',
                                            help='Expert mode (All parameters)')
        self._add_tier_arguments(expert_parser, tier_level=4)
        
        # Preset mode
        preset_parser = subparsers.add_parser('preset',
                                            help='Run with predefined strategy preset')
        preset_parser.add_argument('--preset-name', required=True,
                                 choices=self._get_available_presets(),
                                 help='Strategy preset to use')
        
        # Configuration management commands
        config_parser = subparsers.add_parser('config', help='Configuration management')
        config_subparsers = config_parser.add_subparsers(dest='config_action')
        
        # Config build command
        build_parser = config_subparsers.add_parser('build', help='Interactive configuration builder')
        build_parser.add_argument('--tier', type=int, choices=[1,2,3,4], default=1,
                                help='Configuration complexity tier')
        
        # Config export/import commands  
        export_parser = config_subparsers.add_parser('export', help='Export configuration')
        export_parser.add_argument('--output', required=True, help='Output file path')
        export_parser.add_argument('--format', choices=['yaml', 'json'], default='yaml')
        
        import_parser = config_subparsers.add_parser('import', help='Import configuration')
        import_parser.add_argument('--file', required=True, help='Configuration file path')
        
        # Config validate command
        validate_parser = config_subparsers.add_parser('validate', help='Validate configuration')
        validate_parser.add_argument('--file', required=True, help='Configuration file to validate')
    
    def _add_tier_arguments(self, parser: argparse.ArgumentParser, tier_level: int):
        """Add arguments for specific tier level"""
        parameters = self.registry.get_parameters_by_tier(tier_level)
        
        # Group parameters by module for better organization
        module_groups = {}
        for param in parameters:
            if param.module not in module_groups:
                module_groups[param.module] = []
            module_groups[param.module].append(param)
        
        # Add argument groups for each module
        for module_name, module_params in module_groups.items():
            group = parser.add_argument_group(module_name)
            
            for param in module_params:
                self._add_parameter_argument(group, param)
    
    def _add_parameter_argument(self, group: argparse._ArgumentGroup, param: ParameterDefinition):
        """Add a single parameter as CLI argument"""
        kwargs = {
            'help': param.help_text,
            'default': param.default_value
        }
        
        # Handle different parameter types
        if param.type == bool:
            if param.default_value:
                # For boolean True defaults, add --no-X flag
                group.add_argument(f'--no-{param.cli_name}', action='store_false',
                                 dest=param.name.replace('-', '_'), **kwargs)
            else:
                # For boolean False defaults, add --X flag
                group.add_argument(f'--{param.cli_name}', action='store_true',
                                 dest=param.name.replace('-', '_'), **kwargs)
        else:
            kwargs['type'] = param.type
            group.add_argument(f'--{param.cli_name}', 
                             dest=param.name.replace('-', '_'), **kwargs)
```

#### **2.2 Configuration File Support**
```python
class ConfigurationFileManager:
    """Manage configuration import/export in multiple formats"""
    
    def __init__(self, validator: ConfigurationValidator):
        self.validator = validator
    
    def export_yaml(self, config: StrategyConfiguration, file_path: str):
        """Export configuration to YAML format"""
        config_dict = self._config_to_dict(config)
        
        with open(file_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)
    
    def export_json(self, config: StrategyConfiguration, file_path: str):
        """Export configuration to JSON format"""
        config_dict = self._config_to_dict(config)
        
        with open(file_path, 'w') as f:
            json.dump(config_dict, f, indent=2, default=str)
    
    def import_yaml(self, file_path: str) -> StrategyConfiguration:
        """Import configuration from YAML format"""
        with open(file_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        
        config = self._dict_to_config(config_dict)
        
        # Validate imported configuration
        validation = self.validator.validate(config)
        if not validation.is_valid():
            raise ValueError(f"Invalid configuration file: {validation.errors}")
        
        return config
    
    def import_json(self, file_path: str) -> StrategyConfiguration:
        """Import configuration from JSON format"""
        with open(file_path, 'r') as f:
            config_dict = json.load(f)
        
        config = self._dict_to_config(config_dict)
        
        # Validate imported configuration
        validation = self.validator.validate(config)
        if not validation.is_valid():
            raise ValueError(f"Invalid configuration file: {validation.errors}")
        
        return config
```

### **Phase 3: Configuration Presets Library (Day 2)**

#### **3.1 Strategy Preset Templates**
```python
class StrategyPresets:
    """Library of predefined strategy configurations"""
    
    @staticmethod
    def conservative_diversified() -> StrategyConfiguration:
        """Conservative diversified strategy preset"""
        return StrategyConfiguration(
            name="Conservative Diversified",
            description="Risk-averse strategy with strict diversification",
            tier_level=2,
            
            core_config=CoreRebalancerConfig(
                max_total_positions=8,
                max_new_positions=2,
                min_score_threshold=0.65,
                min_score_new_position=0.7,
                max_single_position_pct=0.15,
                target_total_allocation=0.90,
                technical_weight=0.4,
                fundamental_weight=0.6
            ),
            
            bucket_config=BucketDiversificationConfig(
                enable_bucket_diversification=True,
                max_positions_per_bucket=3,
                max_allocation_per_bucket=0.35,
                min_buckets_represented=3,
                correlation_limit=0.7
            ),
            
            sizing_config=DynamicSizingConfig(
                sizing_mode='equal_weight',
                max_single_position=0.12,
                residual_strategy='cash_bucket'
            ),
            
            lifecycle_config=LifecycleManagementConfig(
                enable_grace_periods=True,
                grace_period_days=7,
                min_holding_period_days=5,
                enable_whipsaw_protection=True
            ),
            
            core_asset_config=CoreAssetManagementConfig(
                enable_core_asset_management=False
            )
        )
    
    @staticmethod
    def aggressive_growth() -> StrategyConfiguration:
        """Aggressive growth strategy preset"""
        return StrategyConfiguration(
            name="Aggressive Growth",
            description="High-risk, high-reward growth strategy",
            tier_level=3,
            
            core_config=CoreRebalancerConfig(
                max_total_positions=12,
                max_new_positions=5,
                min_score_threshold=0.55,
                min_score_new_position=0.6,
                max_single_position_pct=0.25,
                target_total_allocation=0.98,
                technical_weight=0.7,
                fundamental_weight=0.3
            ),
            
            bucket_config=BucketDiversificationConfig(
                enable_bucket_diversification=True,
                max_positions_per_bucket=6,
                max_allocation_per_bucket=0.6,
                min_buckets_represented=2,
                correlation_limit=0.85
            ),
            
            sizing_config=DynamicSizingConfig(
                sizing_mode='score_weighted',
                max_single_position=0.20,
                residual_strategy='safe_top_slice'
            ),
            
            lifecycle_config=LifecycleManagementConfig(
                enable_grace_periods=True,
                grace_period_days=3,
                min_holding_period_days=1,
                enable_regime_overrides=True
            ),
            
            core_asset_config=CoreAssetManagementConfig(
                enable_core_asset_management=True,
                core_asset_override_threshold=0.92,
                max_core_assets=2
            )
        )
    
    @staticmethod
    def regime_adaptive() -> StrategyConfiguration:
        """Regime-adaptive balanced strategy preset"""
        return StrategyConfiguration(
            name="Regime Adaptive",
            description="Balanced strategy that adapts to market regimes",
            tier_level=3,
            
            core_config=CoreRebalancerConfig(
                max_total_positions=10,
                max_new_positions=3,
                min_score_threshold=0.6,
                min_score_new_position=0.65,
                max_single_position_pct=0.18,
                target_total_allocation=0.95,
                technical_weight=0.5,
                fundamental_weight=0.5
            ),
            
            bucket_config=BucketDiversificationConfig(
                enable_bucket_diversification=True,
                max_positions_per_bucket=4,
                max_allocation_per_bucket=0.4,
                min_buckets_represented=3,
                correlation_limit=0.8
            ),
            
            sizing_config=DynamicSizingConfig(
                sizing_mode='adaptive',
                max_single_position=0.15,
                residual_strategy='proportional'
            ),
            
            lifecycle_config=LifecycleManagementConfig(
                enable_grace_periods=True,
                grace_period_days=5,
                min_holding_period_days=3,
                enable_regime_overrides=True,
                regime_override_cooldown_days=21
            ),
            
            core_asset_config=CoreAssetManagementConfig(
                enable_core_asset_management=True,
                core_asset_override_threshold=0.95,
                max_core_assets=2
            )
        )
    
    @staticmethod
    def professional_institutional() -> StrategyConfiguration:
        """Professional institutional-grade strategy preset"""
        return StrategyConfiguration(
            name="Professional Institutional",
            description="Institutional-grade strategy with all features enabled",
            tier_level=4,
            
            core_config=CoreRebalancerConfig(
                max_total_positions=15,
                max_new_positions=4,
                min_score_threshold=0.62,
                min_score_new_position=0.68,
                max_single_position_pct=0.2,
                target_total_allocation=0.96,
                technical_weight=0.55,
                fundamental_weight=0.45
            ),
            
            bucket_config=BucketDiversificationConfig(
                enable_bucket_diversification=True,
                max_positions_per_bucket=5,
                max_allocation_per_bucket=0.35,
                min_buckets_represented=4,
                correlation_limit=0.75
            ),
            
            sizing_config=DynamicSizingConfig(
                sizing_mode='adaptive',
                max_single_position=0.16,
                residual_strategy='safe_top_slice',
                max_residual_per_asset=0.04
            ),
            
            lifecycle_config=LifecycleManagementConfig(
                enable_grace_periods=True,
                grace_period_days=4,
                grace_decay_rate=0.85,
                min_holding_period_days=3,
                max_holding_period_days=60,
                enable_regime_overrides=True,
                regime_override_cooldown_days=28,
                enable_whipsaw_protection=True,
                max_cycles_per_protection_period=1,
                whipsaw_protection_days=10
            ),
            
            core_asset_config=CoreAssetManagementConfig(
                enable_core_asset_management=True,
                core_asset_override_threshold=0.96,
                core_asset_expiry_days=75,
                core_asset_underperformance_threshold=0.12,
                max_core_assets=3,
                core_asset_performance_check_frequency=5
            )
        )

    @classmethod
    def get_all_presets(cls) -> Dict[str, StrategyConfiguration]:
        """Get all available presets"""
        return {
            'conservative': cls.conservative_diversified(),
            'aggressive': cls.aggressive_growth(),
            'adaptive': cls.regime_adaptive(),
            'institutional': cls.professional_institutional()
        }
```

### **Phase 4: Integration & Migration (Day 3)**

#### **4.1 Enhanced Main CLI**
```python
class EnhancedMainCLI:
    """Enhanced main CLI with full configuration management"""
    
    def __init__(self):
        self.registry = ParameterRegistry()
        self.validator = ConfigurationValidator(self.registry)
        self.builder = ConfigurationBuilder(self.registry, self.validator)
        self.file_manager = ConfigurationFileManager(self.validator)
        self.parser = TieredArgumentParser(self.registry)
    
    def run(self):
        """Main entry point for enhanced CLI"""
        args = self.parser.parser.parse_args()
        
        if args.mode == 'config':
            self._handle_config_commands(args)
        elif args.mode == 'preset':
            self._handle_preset_mode(args)
        elif args.mode in ['basic', 'advanced', 'expert']:
            self._handle_tiered_mode(args)
        else:
            self.parser.parser.print_help()
    
    def _handle_config_commands(self, args):
        """Handle configuration management commands"""
        if args.config_action == 'build':
            config = self.builder.build_interactive(tier_level=args.tier)
            print(f"\n✅ Configuration built successfully!")
            print(f"📊 Tier Level: {args.tier}")
            print(f"📋 Parameters: {len(config.get_all_parameters())}")
            
            # Offer to save configuration
            save_choice = input("\n💾 Save configuration to file? (y/n): ")
            if save_choice.lower() == 'y':
                file_path = input("📁 Enter file path (e.g., my_strategy.yaml): ")
                self.file_manager.export_yaml(config, file_path)
                print(f"✅ Configuration saved to {file_path}")
        
        elif args.config_action == 'export':
            # Export current CLI args to file
            config = self._args_to_config(args)
            if args.format == 'yaml':
                self.file_manager.export_yaml(config, args.output)
            else:
                self.file_manager.export_json(config, args.output)
            print(f"✅ Configuration exported to {args.output}")
        
        elif args.config_action == 'import':
            config = self.file_manager.import_yaml(args.file)
            print(f"✅ Configuration imported from {args.file}")
            print(f"📊 Strategy: {config.name}")
            print(f"📋 Description: {config.description}")
            
            # Convert to CLI args and run backtest
            cli_args = config.to_cli_args()
            self._run_backtest_with_config(config)
        
        elif args.config_action == 'validate':
            config = self.file_manager.import_yaml(args.file)
            validation = self.validator.validate(config)
            
            if validation.is_valid():
                print(f"✅ Configuration is valid!")
            else:
                print(f"❌ Configuration validation failed:")
                for error in validation.errors:
                    print(f"   • {error}")
                for warning in validation.warnings:
                    print(f"   ⚠️  {warning}")
    
    def _handle_preset_mode(self, args):
        """Handle preset mode execution"""
        presets = StrategyPresets.get_all_presets()
        
        if args.preset_name not in presets:
            print(f"❌ Unknown preset: {args.preset_name}")
            print(f"📋 Available presets: {list(presets.keys())}")
            return
        
        config = presets[args.preset_name]
        print(f"🚀 Running with preset: {config.name}")
        print(f"📋 Description: {config.description}")
        print(f"📊 Tier Level: {config.tier_level}")
        
        self._run_backtest_with_config(config)
    
    def _handle_tiered_mode(self, args):
        """Handle tiered mode execution (basic/advanced/expert)"""
        tier_map = {'basic': 1, 'advanced': 3, 'expert': 4}
        tier_level = tier_map[args.mode]
        
        print(f"🎛️  Running in {args.mode.upper()} mode (Tier {tier_level})")
        
        # Convert args to configuration
        config = self._args_to_config(args, tier_level)
        
        # Validate configuration
        validation = self.validator.validate(config)
        if not validation.is_valid():
            print(f"❌ Configuration validation failed:")
            for error in validation.errors:
                print(f"   • {error}")
            return
        
        if validation.warnings:
            print(f"⚠️  Configuration warnings:")
            for warning in validation.warnings:
                print(f"   • {warning}")
        
        self._run_backtest_with_config(config)
```

#### **4.2 Backward Compatibility Layer**
```python
class BackwardCompatibilityAdapter:
    """Ensures existing code continues to work with new configuration system"""
    
    @staticmethod
    def config_to_rebalancing_limits(config: StrategyConfiguration) -> RebalancingLimits:
        """Convert new configuration to legacy RebalancingLimits"""
        return RebalancingLimits(
            # Core parameters
            max_total_positions=config.core_config.max_total_positions,
            max_new_positions=config.core_config.max_new_positions,
            min_score_threshold=config.core_config.min_score_threshold,
            min_score_new_position=config.core_config.min_score_new_position,
            max_single_position_pct=config.core_config.max_single_position_pct,
            target_total_allocation=config.core_config.target_total_allocation,
            
            # Bucket diversification
            enable_bucket_diversification=config.bucket_config.enable_bucket_diversification,
            max_positions_per_bucket=config.bucket_config.max_positions_per_bucket,
            max_allocation_per_bucket=config.bucket_config.max_allocation_per_bucket,
            min_buckets_represented=config.bucket_config.min_buckets_represented,
            allow_bucket_overflow=config.bucket_config.allow_bucket_overflow,
            
            # Dynamic sizing
            enable_dynamic_sizing=config.sizing_config.enable_dynamic_sizing,
            sizing_mode=config.sizing_config.sizing_mode,
            max_single_position=config.sizing_config.max_single_position,
            min_position_size=config.sizing_config.min_position_size,
            residual_strategy=config.sizing_config.residual_strategy,
            
            # Lifecycle management
            enable_grace_periods=config.lifecycle_config.enable_grace_periods,
            grace_period_days=config.lifecycle_config.grace_period_days,
            grace_decay_rate=config.lifecycle_config.grace_decay_rate,
            min_decay_factor=config.lifecycle_config.min_decay_factor,
            min_holding_period_days=config.lifecycle_config.min_holding_period_days,
            max_holding_period_days=config.lifecycle_config.max_holding_period_days,
            enable_regime_overrides=config.lifecycle_config.enable_regime_overrides,
            regime_override_cooldown_days=config.lifecycle_config.regime_override_cooldown_days,
            enable_whipsaw_protection=config.lifecycle_config.enable_whipsaw_protection,
            max_cycles_per_protection_period=config.lifecycle_config.max_cycles_per_protection_period,
            whipsaw_protection_days=config.lifecycle_config.whipsaw_protection_days,
            min_position_duration_hours=config.lifecycle_config.min_position_duration_hours,
            
            # Core asset management
            enable_core_asset_management=config.core_asset_config.enable_core_asset_management,
            core_asset_override_threshold=config.core_asset_config.core_asset_override_threshold,
            core_asset_expiry_days=config.core_asset_config.core_asset_expiry_days,
            core_asset_underperformance_threshold=config.core_asset_config.core_asset_underperformance_threshold,
            core_asset_underperformance_period=config.core_asset_config.core_asset_underperformance_period,
            max_core_assets=config.core_asset_config.max_core_assets,
            core_asset_extension_limit=config.core_asset_config.core_asset_extension_limit,
            core_asset_performance_check_frequency=config.core_asset_config.core_asset_performance_check_frequency
        )
    
    @staticmethod
    def rebalancing_limits_to_config(limits: RebalancingLimits) -> StrategyConfiguration:
        """Convert legacy RebalancingLimits to new configuration"""
        return StrategyConfiguration(
            name="Legacy Configuration",
            description="Converted from RebalancingLimits",
            tier_level=3,  # Assume advanced since all parameters present
            
            core_config=CoreRebalancerConfig(
                max_total_positions=limits.max_total_positions,
                max_new_positions=limits.max_new_positions,
                min_score_threshold=limits.min_score_threshold,
                min_score_new_position=limits.min_score_new_position,
                max_single_position_pct=limits.max_single_position_pct,
                target_total_allocation=limits.target_total_allocation
            ),
            
            bucket_config=BucketDiversificationConfig(
                enable_bucket_diversification=limits.enable_bucket_diversification,
                max_positions_per_bucket=limits.max_positions_per_bucket,
                max_allocation_per_bucket=limits.max_allocation_per_bucket,
                min_buckets_represented=limits.min_buckets_represented,
                allow_bucket_overflow=limits.allow_bucket_overflow
            ),
            
            # ... continue for all config sections
        )
```

### **Phase 5: Interactive Tools & Documentation (Day 3-4)**

#### **5.1 Configuration Help System**
```python
class ConfigurationHelpSystem:
    """Interactive help and documentation system"""
    
    def __init__(self, registry: ParameterRegistry):
        self.registry = registry
    
    def show_parameter_help(self, parameter_name: str):
        """Show detailed help for a specific parameter"""
        param = self.registry.get_parameter(parameter_name)
        if not param:
            print(f"❌ Unknown parameter: {parameter_name}")
            return
        
        print(f"\n📋 Parameter: {param.name}")
        print(f"🏷️  Type: {param.type.__name__}")
        print(f"⚙️  Default: {param.default_value}")
        print(f"📊 Tier: {param.tier_level} ({self._get_tier_name(param.tier_level)})")
        print(f"🏗️  Module: {param.module}")
        print(f"📝 Description: {param.description}")
        print(f"💡 Help: {param.help_text}")
        
        if param.examples:
            print(f"\n💫 Examples:")
            for example in param.examples:
                print(f"   • {example}")
        
        if param.dependencies:
            print(f"\n🔗 Dependencies: {', '.join(param.dependencies)}")
        
        if param.mutually_exclusive:
            print(f"\n🚫 Mutually Exclusive: {', '.join(param.mutually_exclusive)}")
        
        print(f"\n🖥️  CLI Usage: --{param.cli_name} <value>")
    
    def show_tier_overview(self, tier_level: int):
        """Show overview of parameters in a tier"""
        tier_name = self._get_tier_name(tier_level)
        parameters = self.registry.get_parameters_by_tier(tier_level)
        
        print(f"\n🎛️  {tier_name} Configuration (Tier {tier_level})")
        print("="*60)
        
        # Group by module
        modules = {}
        for param in parameters:
            if param.module not in modules:
                modules[param.module] = []
            modules[param.module].append(param)
        
        for module_name, module_params in modules.items():
            print(f"\n🏗️  {module_name} ({len(module_params)} parameters)")
            for param in module_params:
                print(f"   • --{param.cli_name:<30} {param.description}")
    
    def show_preset_comparison(self):
        """Show comparison of all presets"""
        presets = StrategyPresets.get_all_presets()
        
        print(f"\n🎯 Strategy Preset Comparison")
        print("="*80)
        
        for name, config in presets.items():
            print(f"\n📋 {config.name}")
            print(f"   Tier Level: {config.tier_level}")
            print(f"   Description: {config.description}")
            print(f"   Max Positions: {config.core_config.max_total_positions}")
            print(f"   Risk Level: {self._assess_risk_level(config)}")
            print(f"   Diversification: {self._assess_diversification(config)}")
```

#### **5.2 Configuration Wizard**
```python
class ConfigurationWizard:
    """Step-by-step configuration wizard for beginners"""
    
    def __init__(self, registry: ParameterRegistry, validator: ConfigurationValidator):
        self.registry = registry
        self.validator = validator
    
    def run_wizard(self) -> StrategyConfiguration:
        """Run interactive configuration wizard"""
        print("🧙‍♂️ Configuration Wizard")
        print("="*40)
        print("This wizard will help you build a configuration step by step.")
        print("Answer the questions to create your strategy configuration.\n")
        
        # Step 1: Basic info
        name = input("📋 Strategy name: ")
        description = input("📝 Strategy description: ")
        
        # Step 2: Experience level
        print("\n🎯 What's your experience level?")
        print("1. Beginner - Basic parameters only")
        print("2. Intermediate - Enhanced features")
        print("3. Advanced - Risk management features")
        print("4. Expert - All professional features")
        
        while True:
            try:
                tier_choice = int(input("Choose (1-4): "))
                if 1 <= tier_choice <= 4:
                    break
                print("Please choose 1-4")
            except ValueError:
                print("Please enter a number")
        
        # Step 3: Strategy style
        print(f"\n🎨 Strategy Style (for tier {tier_choice}):")
        print("1. Conservative - Lower risk, steady returns")
        print("2. Balanced - Moderate risk and returns")
        print("3. Aggressive - Higher risk, higher potential returns")
        print("4. Custom - I'll configure parameters manually")
        
        while True:
            try:
                style_choice = int(input("Choose (1-4): "))
                if 1 <= style_choice <= 4:
                    break
                print("Please choose 1-4")
            except ValueError:
                print("Please enter a number")
        
        # Build configuration based on choices
        if style_choice <= 3:
            config = self._build_style_preset(name, description, tier_choice, style_choice)
        else:
            config = self._build_custom_config(name, description, tier_choice)
        
        # Final validation and summary
        validation = self.validator.validate(config)
        
        print(f"\n✅ Configuration Complete!")
        print(f"📋 Name: {config.name}")
        print(f"📊 Tier: {config.tier_level}")
        print(f"📈 Risk Level: {self._assess_risk_level(config)}")
        
        if validation.warnings:
            print(f"\n⚠️  Warnings:")
            for warning in validation.warnings:
                print(f"   • {warning}")
        
        return config
```

## 🧪 Testing Strategy

### **Test Categories**

#### **1. Unit Tests (Day 4)**
```python
class TestParameterRegistry(unittest.TestCase):
    def test_parameter_registration(self):
        """Test parameter registration and retrieval"""
        pass
    
    def test_tier_filtering(self):
        """Test parameter filtering by tier level"""
        pass

class TestConfigurationValidator(unittest.TestCase):
    def test_type_validation(self):
        """Test parameter type validation"""
        pass
    
    def test_dependency_validation(self):
        """Test parameter dependency checking"""
        pass
    
    def test_business_logic_validation(self):
        """Test complex business logic constraints"""
        pass

class TestConfigurationBuilder(unittest.TestCase):
    def test_preset_building(self):
        """Test building configuration from presets"""
        pass
    
    def test_tier_building(self):
        """Test building configuration for different tiers"""
        pass

class TestFileManager(unittest.TestCase):
    def test_yaml_export_import(self):
        """Test YAML export/import roundtrip"""
        pass
    
    def test_json_export_import(self):
        """Test JSON export/import roundtrip"""
        pass
```

#### **2. Integration Tests (Day 4)**
```python
class TestCLIIntegration(unittest.TestCase):
    def test_tiered_cli_parsing(self):
        """Test CLI parsing for different tiers"""
        pass
    
    def test_preset_mode(self):
        """Test preset mode execution"""
        pass
    
    def test_config_commands(self):
        """Test configuration management commands"""
        pass

class TestBackwardCompatibility(unittest.TestCase):
    def test_rebalancing_limits_conversion(self):
        """Test conversion to/from RebalancingLimits"""
        pass
    
    def test_existing_workflow(self):
        """Test that existing workflows still work"""
        pass
```

#### **3. End-to-End Tests (Day 4)**
```python
class TestEndToEndWorkflows(unittest.TestCase):
    def test_basic_user_workflow(self):
        """Test complete basic user workflow"""
        pass
    
    def test_expert_user_workflow(self):
        """Test complete expert user workflow"""
        pass
    
    def test_configuration_lifecycle(self):
        """Test full configuration lifecycle (create→export→import→validate→run)"""
        pass
```

## 📊 Success Metrics

### **Primary Metrics**
1. **✅ Centralized Management**: All 50+ parameters managed by single system
2. **✅ Tiered Complexity**: Clear progression from Basic (Tier 1) to Expert (Tier 4)
3. **✅ Validation Coverage**: 100% parameter validation with dependency checking
4. **✅ Preset Functionality**: 4+ working strategy presets
5. **✅ File Support**: YAML/JSON import/export working
6. **✅ CLI Enhancement**: Organized, tiered CLI with help system
7. **✅ Backward Compatibility**: Existing code continues to work
8. **✅ Interactive Tools**: Configuration wizard and help system

### **User Experience Metrics**
- **Beginner Friendly**: Basic tier has ≤10 parameters
- **Progressive Disclosure**: Each tier adds logical parameter groups
- **Help System**: Every parameter has comprehensive help
- **Validation Feedback**: Clear error messages with suggestions
- **Preset Quality**: Presets validate and produce reasonable results

### **Technical Metrics**
- **Performance**: Configuration loading/validation <100ms
- **Memory Usage**: <10MB additional memory for configuration system
- **Test Coverage**: >90% code coverage for configuration system
- **Error Handling**: Graceful handling of invalid configurations

## 🚨 Risk Mitigation

### **Technical Risks**
- **Complexity Explosion**: Mitigated by tiered approach and good organization
- **Performance Impact**: Mitigated by lazy loading and caching
- **Breaking Changes**: Mitigated by backward compatibility layer

### **User Experience Risks**  
- **Overwhelming Parameters**: Mitigated by tier system and presets
- **Configuration Errors**: Mitigated by comprehensive validation
- **Learning Curve**: Mitigated by wizard and help system

### **Integration Risks**
- **Module Coupling**: Mitigated by clear interfaces and adapters
- **Version Compatibility**: Mitigated by configuration versioning
- **Migration Issues**: Mitigated by automatic conversion tools

## 📋 Implementation Timeline

### **Day 1: Core Framework**
- ✅ Parameter Registry design and implementation
- ✅ Configuration data models (all config classes)
- ✅ Basic validation framework
- ✅ Unit tests for core components

### **Day 2: CLI Integration**
- ✅ Enhanced CLI parser with tiers
- ✅ Configuration file support (YAML/JSON)
- ✅ Strategy presets implementation
- ✅ Integration tests

### **Day 3: Advanced Features**
- ✅ Configuration wizard and help system
- ✅ Backward compatibility layer
- ✅ Enhanced main CLI with all modes
- ✅ End-to-end testing

### **Day 4: Polish & Documentation**
- ✅ Comprehensive testing and validation
- ✅ Documentation and help content
- ✅ Performance optimization
- ✅ Final integration testing

## 🎯 Expected Outcomes

### **Immediate Benefits**
- **Organized Parameters**: All 50+ parameters properly organized and accessible
- **Improved UX**: Tiered complexity suitable for different user levels
- **Better Validation**: Comprehensive parameter validation and constraints
- **Configuration Management**: Professional import/export and preset system

### **Long-term Benefits**
- **Scalability**: Easy to add new parameters and modules
- **Maintainability**: Centralized configuration reduces complexity
- **User Adoption**: Better onboarding for new users
- **Professional Quality**: Institutional-grade configuration management

### **Strategic Value**
- **Foundation for Growth**: Enables adding more modules without complexity explosion
- **User Segmentation**: Different tiers serve different user sophistication levels
- **Operational Efficiency**: Presets and templates speed up strategy development
- **Quality Assurance**: Validation prevents configuration errors

## 🏆 Module 11 Success Criteria

1. **✅ Complete Parameter Centralization**: All existing parameters managed by unified system
2. **✅ Four-Tier Organization**: Basic→Intermediate→Advanced→Expert progression
3. **✅ Professional Validation**: Comprehensive constraints and dependency checking
4. **✅ Strategy Presets**: 4+ working presets covering different strategy styles
5. **✅ File Integration**: Working YAML/JSON import/export with validation
6. **✅ Enhanced CLI**: Organized, tiered CLI with comprehensive help
7. **✅ Interactive Tools**: Configuration wizard and parameter help system
8. **✅ Backward Compatibility**: Existing workflows continue to work unchanged
9. **✅ Comprehensive Testing**: >90% test coverage with unit/integration/e2e tests
10. **✅ Professional Documentation**: Complete help system and usage examples

**Module 11 delivers the foundation for professional configuration management that scales to 100+ parameters across all future modules while maintaining excellent user experience.** 