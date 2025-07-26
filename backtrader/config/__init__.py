"""
Configuration Management Module for Hedge Fund Backtesting Framework

This module provides comprehensive configuration management with:
- Parameter registry and validation
- Tiered complexity management  
- Strategy presets and templates
- Import/export functionality
- Interactive configuration tools
"""

from .parameter_registry import ParameterRegistry, ParameterDefinition, ValidationRule
from .data_models import (
    StrategyConfiguration,
    CoreRebalancerConfig,
    BucketDiversificationConfig, 
    DynamicSizingConfig,
    LifecycleManagementConfig,
    CoreAssetManagementConfig,
    SystemConfig,
    ConfigurationTiers,
    create_basic_configuration,
    create_intermediate_configuration,
    create_advanced_configuration,
    create_expert_configuration
)
from .validator import ConfigurationValidator, ValidationResult, ValidationError
from .cli_parser import TieredArgumentParser, create_cli_parser
from .file_manager import ConfigurationFileManager
from .presets import StrategyPresets

__all__ = [
    # Core Registry
    'ParameterRegistry',
    'ParameterDefinition', 
    'ValidationRule',
    
    # Data Models
    'StrategyConfiguration',
    'CoreRebalancerConfig',
    'BucketDiversificationConfig',
    'DynamicSizingConfig', 
    'LifecycleManagementConfig',
    'CoreAssetManagementConfig',
    'SystemConfig',
    'ConfigurationTiers',
    
    # Factory Functions
    'create_basic_configuration',
    'create_intermediate_configuration',
    'create_advanced_configuration',
    'create_expert_configuration',
    
    # Validation
    'ConfigurationValidator',
    'ValidationResult',
    'ValidationError',
    
    # CLI and File Management
    'TieredArgumentParser',
    'create_cli_parser',
    'ConfigurationFileManager',
    
    # Strategy Presets
    'StrategyPresets'
] 