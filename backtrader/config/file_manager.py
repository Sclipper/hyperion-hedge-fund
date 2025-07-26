"""
Configuration File Manager for Import/Export

Provides file-based configuration management with:
- YAML and JSON format support
- Validation during import
- Metadata preservation
- Error handling and recovery
"""

import yaml
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from .data_models import StrategyConfiguration
from .validator import ConfigurationValidator, ValidationResult


class ConfigurationFileManager:
    """Manage configuration import/export in multiple formats"""
    
    def __init__(self, validator: Optional[ConfigurationValidator] = None):
        self.validator = validator or ConfigurationValidator()
    
    def export_yaml(self, config: StrategyConfiguration, file_path: str, 
                   include_metadata: bool = True) -> bool:
        """Export configuration to YAML format"""
        try:
            config_dict = self._config_to_dict(config, include_metadata)
            
            # Ensure directory exists
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2, 
                         sort_keys=False, allow_unicode=True)
            
            print(f"✅ Configuration exported to {file_path}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to export YAML: {e}")
            return False
    
    def export_json(self, config: StrategyConfiguration, file_path: str,
                   include_metadata: bool = True) -> bool:
        """Export configuration to JSON format"""
        try:
            config_dict = self._config_to_dict(config, include_metadata)
            
            # Ensure directory exists
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w') as f:
                json.dump(config_dict, f, indent=2, default=self._json_serializer)
            
            print(f"✅ Configuration exported to {file_path}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to export JSON: {e}")
            return False
    
    def import_yaml(self, file_path: str, validate: bool = True) -> Optional[StrategyConfiguration]:
        """Import configuration from YAML format"""
        try:
            if not os.path.exists(file_path):
                print(f"❌ File not found: {file_path}")
                return None
            
            with open(file_path, 'r') as f:
                config_dict = yaml.safe_load(f)
            
            config = self._dict_to_config(config_dict)
            
            if validate:
                validation = self.validator.validate(config)
                self._handle_validation_result(validation, file_path)
                
                if not validation.is_valid:
                    print(f"❌ Configuration validation failed for {file_path}")
                    return None
            
            print(f"✅ Configuration imported from {file_path}")
            return config
            
        except Exception as e:
            print(f"❌ Failed to import YAML: {e}")
            return None
    
    def import_json(self, file_path: str, validate: bool = True) -> Optional[StrategyConfiguration]:
        """Import configuration from JSON format"""
        try:
            if not os.path.exists(file_path):
                print(f"❌ File not found: {file_path}")
                return None
            
            with open(file_path, 'r') as f:
                config_dict = json.load(f)
            
            config = self._dict_to_config(config_dict)
            
            if validate:
                validation = self.validator.validate(config)
                self._handle_validation_result(validation, file_path)
                
                if not validation.is_valid:
                    print(f"❌ Configuration validation failed for {file_path}")
                    return None
            
            print(f"✅ Configuration imported from {file_path}")
            return config
            
        except Exception as e:
            print(f"❌ Failed to import JSON: {e}")
            return None
    
    def validate_file(self, file_path: str, verbose: bool = False) -> ValidationResult:
        """Validate configuration file without importing"""
        try:
            # Determine format from extension
            if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                config = self.import_yaml(file_path, validate=False)
            elif file_path.endswith('.json'):
                config = self.import_json(file_path, validate=False)
            else:
                print(f"❌ Unsupported file format: {file_path}")
                result = ValidationResult()
                result.add_error('file_format', 'Unsupported file format. Use .yaml, .yml, or .json')
                return result
            
            if config is None:
                result = ValidationResult()
                result.add_error('file_parsing', 'Failed to parse configuration file')
                return result
            
            # Validate configuration
            validation = self.validator.validate(config)
            
            if verbose:
                self._print_validation_details(validation, file_path)
            else:
                self._print_validation_summary(validation, file_path)
            
            return validation
            
        except Exception as e:
            print(f"❌ Validation failed: {e}")
            result = ValidationResult()
            result.add_error('validation_error', str(e))
            return result
    
    def _config_to_dict(self, config: StrategyConfiguration, include_metadata: bool = True) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization"""
        config_dict = {}
        
        # Metadata
        if include_metadata:
            config_dict['metadata'] = {
                'name': config.name,
                'description': config.description,
                'tier_level': config.tier_level,
                'version': config.version,
                'created_date': config.created_date.isoformat(),
                'last_modified': config.last_modified.isoformat(),
                'exported_by': 'Configuration File Manager',
                'export_date': datetime.now().isoformat()
            }
        
        # System configuration
        config_dict['system'] = {
            'buckets': config.system_config.buckets,
            'start_date': config.system_config.start_date,
            'end_date': config.system_config.end_date,
            'cash': config.system_config.cash,
            'commission': config.system_config.commission,
            'rebalance_frequency': config.system_config.rebalance_frequency,
            'min_trending_confidence': config.system_config.min_trending_confidence,
            'timeframes': config.system_config.timeframes,
            'plot_results': config.system_config.plot_results
        }
        
        # Core rebalancer configuration
        config_dict['core_rebalancer'] = {
            'max_total_positions': config.core_config.max_total_positions,
            'max_new_positions': config.core_config.max_new_positions,
            'min_score_threshold': config.core_config.min_score_threshold,
            'min_score_new_position': config.core_config.min_score_new_position,
            'max_single_position_pct': config.core_config.max_single_position_pct,
            'target_total_allocation': config.core_config.target_total_allocation,
            'enable_technical_analysis': config.core_config.enable_technical_analysis,
            'enable_fundamental_analysis': config.core_config.enable_fundamental_analysis,
            'technical_weight': config.core_config.technical_weight,
            'fundamental_weight': config.core_config.fundamental_weight
        }
        
        # Bucket diversification configuration
        config_dict['bucket_diversification'] = {
            'enable_bucket_diversification': config.bucket_config.enable_bucket_diversification,
            'max_positions_per_bucket': config.bucket_config.max_positions_per_bucket,
            'max_allocation_per_bucket': config.bucket_config.max_allocation_per_bucket,
            'min_buckets_represented': config.bucket_config.min_buckets_represented,
            'allow_bucket_overflow': config.bucket_config.allow_bucket_overflow,
            'correlation_limit': config.bucket_config.correlation_limit,
            'correlation_window': config.bucket_config.correlation_window
        }
        
        # Dynamic sizing configuration
        config_dict['dynamic_sizing'] = {
            'enable_dynamic_sizing': config.sizing_config.enable_dynamic_sizing,
            'sizing_mode': config.sizing_config.sizing_mode,
            'max_single_position': config.sizing_config.max_single_position,
            'min_position_size': config.sizing_config.min_position_size,
            'enable_two_stage_sizing': config.sizing_config.enable_two_stage_sizing,
            'residual_strategy': config.sizing_config.residual_strategy,
            'max_residual_per_asset': config.sizing_config.max_residual_per_asset,
            'max_residual_multiple': config.sizing_config.max_residual_multiple
        }
        
        # Lifecycle management configuration
        config_dict['lifecycle_management'] = {
            'enable_grace_periods': config.lifecycle_config.enable_grace_periods,
            'grace_period_days': config.lifecycle_config.grace_period_days,
            'grace_decay_rate': config.lifecycle_config.grace_decay_rate,
            'min_decay_factor': config.lifecycle_config.min_decay_factor,
            'min_holding_period_days': config.lifecycle_config.min_holding_period_days,
            'max_holding_period_days': config.lifecycle_config.max_holding_period_days,
            'enable_regime_overrides': config.lifecycle_config.enable_regime_overrides,
            'regime_override_cooldown_days': config.lifecycle_config.regime_override_cooldown_days,
            'regime_severity_threshold': config.lifecycle_config.regime_severity_threshold,
            'enable_whipsaw_protection': config.lifecycle_config.enable_whipsaw_protection,
            'max_cycles_per_protection_period': config.lifecycle_config.max_cycles_per_protection_period,
            'whipsaw_protection_days': config.lifecycle_config.whipsaw_protection_days,
            'min_position_duration_hours': config.lifecycle_config.min_position_duration_hours
        }
        
        # Core asset management configuration
        config_dict['core_asset_management'] = {
            'enable_core_asset_management': config.core_asset_config.enable_core_asset_management,
            'max_core_assets': config.core_asset_config.max_core_assets,
            'core_asset_override_threshold': config.core_asset_config.core_asset_override_threshold,
            'core_asset_expiry_days': config.core_asset_config.core_asset_expiry_days,
            'core_asset_underperformance_threshold': config.core_asset_config.core_asset_underperformance_threshold,
            'core_asset_underperformance_period': config.core_asset_config.core_asset_underperformance_period,
            'core_asset_extension_limit': config.core_asset_config.core_asset_extension_limit,
            'core_asset_performance_check_frequency': config.core_asset_config.core_asset_performance_check_frequency,
            'smart_diversification_overrides': config.core_asset_config.smart_diversification_overrides
        }
        
        return config_dict
    
    def _dict_to_config(self, config_dict: Dict[str, Any]) -> StrategyConfiguration:
        """Convert dictionary to configuration object"""
        from .data_models import (
            CoreRebalancerConfig, BucketDiversificationConfig, DynamicSizingConfig,
            LifecycleManagementConfig, CoreAssetManagementConfig, SystemConfig
        )
        
        # Extract metadata
        metadata = config_dict.get('metadata', {})
        name = metadata.get('name', 'Imported Configuration')
        description = metadata.get('description', 'Configuration imported from file')
        tier_level = metadata.get('tier_level', 1)
        version = metadata.get('version', '1.0.0')
        
        # Parse dates
        try:
            created_date = datetime.fromisoformat(metadata.get('created_date', datetime.now().isoformat()))
            last_modified = datetime.fromisoformat(metadata.get('last_modified', datetime.now().isoformat()))
        except:
            created_date = datetime.now()
            last_modified = datetime.now()
        
        # Extract configurations
        system_dict = config_dict.get('system', {})
        core_dict = config_dict.get('core_rebalancer', {})
        bucket_dict = config_dict.get('bucket_diversification', {})
        sizing_dict = config_dict.get('dynamic_sizing', {})
        lifecycle_dict = config_dict.get('lifecycle_management', {})
        core_asset_dict = config_dict.get('core_asset_management', {})
        
        # Create configuration objects
        system_config = SystemConfig(
            buckets=system_dict.get('buckets', ['Risk Assets', 'Defensive Assets']),
            start_date=system_dict.get('start_date', '2021-01-01'),
            end_date=system_dict.get('end_date'),
            cash=system_dict.get('cash', 100000),
            commission=system_dict.get('commission', 0.001),
            rebalance_frequency=system_dict.get('rebalance_frequency', 'monthly'),
            min_trending_confidence=system_dict.get('min_trending_confidence', 0.7),
            timeframes=system_dict.get('timeframes', ['1d', '4h', '1h']),
            plot_results=system_dict.get('plot_results', False)
        )
        
        core_config = CoreRebalancerConfig(
            max_total_positions=core_dict.get('max_total_positions', 10),
            max_new_positions=core_dict.get('max_new_positions', 3),
            min_score_threshold=core_dict.get('min_score_threshold', 0.6),
            min_score_new_position=core_dict.get('min_score_new_position', 0.65),
            max_single_position_pct=core_dict.get('max_single_position_pct', 0.2),
            target_total_allocation=core_dict.get('target_total_allocation', 0.95),
            enable_technical_analysis=core_dict.get('enable_technical_analysis', True),
            enable_fundamental_analysis=core_dict.get('enable_fundamental_analysis', True),
            technical_weight=core_dict.get('technical_weight', 0.6),
            fundamental_weight=core_dict.get('fundamental_weight', 0.4)
        )
        
        bucket_config = BucketDiversificationConfig(
            enable_bucket_diversification=bucket_dict.get('enable_bucket_diversification', False),
            max_positions_per_bucket=bucket_dict.get('max_positions_per_bucket', 4),
            max_allocation_per_bucket=bucket_dict.get('max_allocation_per_bucket', 0.4),
            min_buckets_represented=bucket_dict.get('min_buckets_represented', 2),
            allow_bucket_overflow=bucket_dict.get('allow_bucket_overflow', False),
            correlation_limit=bucket_dict.get('correlation_limit', 0.8),
            correlation_window=bucket_dict.get('correlation_window', 60)
        )
        
        sizing_config = DynamicSizingConfig(
            enable_dynamic_sizing=sizing_dict.get('enable_dynamic_sizing', True),
            sizing_mode=sizing_dict.get('sizing_mode', 'adaptive'),
            max_single_position=sizing_dict.get('max_single_position', 0.15),
            min_position_size=sizing_dict.get('min_position_size', 0.02),
            enable_two_stage_sizing=sizing_dict.get('enable_two_stage_sizing', True),
            residual_strategy=sizing_dict.get('residual_strategy', 'safe_top_slice'),
            max_residual_per_asset=sizing_dict.get('max_residual_per_asset', 0.05),
            max_residual_multiple=sizing_dict.get('max_residual_multiple', 0.5)
        )
        
        lifecycle_config = LifecycleManagementConfig(
            enable_grace_periods=lifecycle_dict.get('enable_grace_periods', True),
            grace_period_days=lifecycle_dict.get('grace_period_days', 5),
            grace_decay_rate=lifecycle_dict.get('grace_decay_rate', 0.8),
            min_decay_factor=lifecycle_dict.get('min_decay_factor', 0.1),
            min_holding_period_days=lifecycle_dict.get('min_holding_period_days', 3),
            max_holding_period_days=lifecycle_dict.get('max_holding_period_days', 90),
            enable_regime_overrides=lifecycle_dict.get('enable_regime_overrides', True),
            regime_override_cooldown_days=lifecycle_dict.get('regime_override_cooldown_days', 30),
            regime_severity_threshold=lifecycle_dict.get('regime_severity_threshold', 'high'),
            enable_whipsaw_protection=lifecycle_dict.get('enable_whipsaw_protection', True),
            max_cycles_per_protection_period=lifecycle_dict.get('max_cycles_per_protection_period', 1),
            whipsaw_protection_days=lifecycle_dict.get('whipsaw_protection_days', 14),
            min_position_duration_hours=lifecycle_dict.get('min_position_duration_hours', 4)
        )
        
        core_asset_config = CoreAssetManagementConfig(
            enable_core_asset_management=core_asset_dict.get('enable_core_asset_management', False),
            max_core_assets=core_asset_dict.get('max_core_assets', 3),
            core_asset_override_threshold=core_asset_dict.get('core_asset_override_threshold', 0.95),
            core_asset_expiry_days=core_asset_dict.get('core_asset_expiry_days', 90),
            core_asset_underperformance_threshold=core_asset_dict.get('core_asset_underperformance_threshold', 0.15),
            core_asset_underperformance_period=core_asset_dict.get('core_asset_underperformance_period', 30),
            core_asset_extension_limit=core_asset_dict.get('core_asset_extension_limit', 2),
            core_asset_performance_check_frequency=core_asset_dict.get('core_asset_performance_check_frequency', 7),
            smart_diversification_overrides=core_asset_dict.get('smart_diversification_overrides', 2)
        )
        
        # Create and return strategy configuration
        return StrategyConfiguration(
            name=name,
            description=description,
            tier_level=tier_level,
            created_date=created_date,
            last_modified=last_modified,
            version=version,
            core_config=core_config,
            bucket_config=bucket_config,
            sizing_config=sizing_config,
            lifecycle_config=lifecycle_config,
            core_asset_config=core_asset_config,
            system_config=system_config
        )
    
    def _json_serializer(self, obj):
        """JSON serializer for datetime objects"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object {obj} is not JSON serializable")
    
    def _handle_validation_result(self, validation: ValidationResult, file_path: str):
        """Handle validation result with appropriate messaging"""
        if validation.is_valid:
            if validation.warnings:
                print(f"⚠️  Configuration valid with {len(validation.warnings)} warnings:")
                for warning in validation.warnings[:3]:  # Show first 3 warnings
                    print(f"   • {warning.parameter}: {warning.message}")
                if len(validation.warnings) > 3:
                    print(f"   ... and {len(validation.warnings) - 3} more warnings")
        else:
            print(f"❌ Configuration validation failed with {len(validation.errors)} errors:")
            for error in validation.errors[:3]:  # Show first 3 errors
                print(f"   • {error.parameter}: {error.message}")
            if len(validation.errors) > 3:
                print(f"   ... and {len(validation.errors) - 3} more errors")
    
    def _print_validation_summary(self, validation: ValidationResult, file_path: str):
        """Print validation summary"""
        if validation.is_valid:
            print(f"✅ {file_path}: Configuration is valid")
            if validation.warnings:
                print(f"   ⚠️  {len(validation.warnings)} warnings")
        else:
            print(f"❌ {file_path}: Configuration has errors")
            print(f"   ❌ {len(validation.errors)} errors")
            if validation.warnings:
                print(f"   ⚠️  {len(validation.warnings)} warnings")
    
    def _print_validation_details(self, validation: ValidationResult, file_path: str):
        """Print detailed validation results"""
        print(f"\n📋 Validation Results for {file_path}")
        print("="*60)
        
        if validation.is_valid:
            print("✅ Configuration is VALID")
        else:
            print("❌ Configuration has ERRORS")
        
        if validation.errors:
            print(f"\n❌ Errors ({len(validation.errors)}):")
            for i, error in enumerate(validation.errors, 1):
                print(f"  {i}. {error.parameter}: {error.message}")
                print(f"     Category: {error.category}")
        
        if validation.warnings:
            print(f"\n⚠️  Warnings ({len(validation.warnings)}):")
            for i, warning in enumerate(validation.warnings, 1):
                print(f"  {i}. {warning.parameter}: {warning.message}")
                print(f"     Category: {warning.category}")
        
        if validation.infos:
            print(f"\nℹ️  Information ({len(validation.infos)}):")
            for i, info in enumerate(validation.infos, 1):
                print(f"  {i}. {info.parameter}: {info.message}")
                print(f"     Category: {info.category}")
        
        print("\n" + "="*60) 