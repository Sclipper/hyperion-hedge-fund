"""
Configuration Data Models for Strategy Configuration

Provides structured data models for organizing all strategy parameters:
- Module-specific configuration classes
- Unified StrategyConfiguration 
- Configuration tier definitions
- Conversion utilities
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

# Import the core RebalancingLimits for compatibility
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.models import RebalancingLimits


class ConfigurationTier:
    """Configuration complexity tier definitions"""
    
    @dataclass
    class TierInfo:
        name: str
        description: str
        target_user: str
        complexity_level: int
        max_parameters: int
        
    BASIC = TierInfo(
        name="Basic Portfolio Management",
        description="Essential parameters for basic backtesting",
        target_user="beginner",
        complexity_level=1,
        max_parameters=10
    )
    
    INTERMEDIATE = TierInfo(
        name="Strategy Configuration", 
        description="Enhanced strategy controls and analysis",
        target_user="intermediate",
        complexity_level=2,
        max_parameters=25
    )
    
    ADVANCED = TierInfo(
        name="Risk Management",
        description="Sophisticated risk controls and lifecycle management", 
        target_user="advanced",
        complexity_level=3,
        max_parameters=45
    )
    
    EXPERT = TierInfo(
        name="Professional Features",
        description="Institutional-grade features and overrides",
        target_user="expert", 
        complexity_level=4,
        max_parameters=100
    )


class ConfigurationTiers:
    """Container for all tier definitions"""
    BASIC = ConfigurationTier.BASIC
    INTERMEDIATE = ConfigurationTier.INTERMEDIATE
    ADVANCED = ConfigurationTier.ADVANCED
    EXPERT = ConfigurationTier.EXPERT
    
    @classmethod
    def get_tier_by_level(cls, level: int):
        """Get tier info by level number"""
        tier_map = {1: cls.BASIC, 2: cls.INTERMEDIATE, 3: cls.ADVANCED, 4: cls.EXPERT}
        return tier_map.get(level, cls.EXPERT)


@dataclass
class CoreRebalancerConfig:
    """Core rebalancer engine configuration (Module 1)"""
    
    # Basic portfolio management (Tier 1)
    max_total_positions: int = 10
    max_new_positions: int = 3
    min_score_threshold: float = 0.6
    
    # Enhanced settings (Tier 2)
    min_score_new_position: float = 0.65
    max_single_position_pct: float = 0.2
    target_total_allocation: float = 0.95
    
    # Analysis configuration (Tier 2)
    enable_technical_analysis: bool = True
    enable_fundamental_analysis: bool = True
    technical_weight: float = 0.6
    fundamental_weight: float = 0.4
    
    def validate(self) -> List[str]:
        """Validate configuration and return any errors"""
        errors = []
        
        if self.max_new_positions > self.max_total_positions:
            errors.append("max_new_positions cannot exceed max_total_positions")
        
        if abs((self.technical_weight + self.fundamental_weight) - 1.0) > 0.01:
            errors.append("technical_weight + fundamental_weight should equal 1.0")
        
        if not self.enable_technical_analysis and not self.enable_fundamental_analysis:
            errors.append("At least one analysis type must be enabled")
        
        return errors


@dataclass
class BucketDiversificationConfig:
    """Bucket diversification configuration (Module 2)"""
    
    # Basic diversification (Tier 2)
    enable_bucket_diversification: bool = False
    max_positions_per_bucket: int = 4
    max_allocation_per_bucket: float = 0.4
    min_buckets_represented: int = 2
    
    # Advanced settings (Tier 3)
    allow_bucket_overflow: bool = False
    correlation_limit: float = 0.8
    correlation_window: int = 60
    
    def validate(self) -> List[str]:
        """Validate configuration and return any errors"""
        errors = []
        
        if self.max_allocation_per_bucket < 0.1:
            errors.append("max_allocation_per_bucket should be at least 0.1 (10%)")
        
        if self.min_buckets_represented < 1:
            errors.append("min_buckets_represented must be at least 1")
        
        return errors


@dataclass
class DynamicSizingConfig:
    """Dynamic position sizing configuration (Module 3)"""
    
    # Basic sizing (Tier 2)
    enable_dynamic_sizing: bool = True
    sizing_mode: str = 'adaptive'  # 'adaptive', 'equal_weight', 'score_weighted'
    
    # Advanced sizing (Tier 3)
    max_single_position: float = 0.15
    min_position_size: float = 0.02
    enable_two_stage_sizing: bool = True
    
    # Residual allocation (Tier 3)
    residual_strategy: str = 'safe_top_slice'  # 'safe_top_slice', 'proportional', 'cash_bucket'
    max_residual_per_asset: float = 0.05
    max_residual_multiple: float = 0.5
    
    def validate(self) -> List[str]:
        """Validate configuration and return any errors"""
        errors = []
        
        valid_modes = ['adaptive', 'equal_weight', 'score_weighted']
        if self.sizing_mode not in valid_modes:
            errors.append(f"sizing_mode must be one of {valid_modes}")
        
        if self.max_single_position <= self.min_position_size:
            errors.append("max_single_position must be greater than min_position_size")
        
        valid_strategies = ['safe_top_slice', 'proportional', 'cash_bucket']
        if self.residual_strategy not in valid_strategies:
            errors.append(f"residual_strategy must be one of {valid_strategies}")
        
        return errors


@dataclass
class LifecycleManagementConfig:
    """Lifecycle management configuration (Module 4)"""
    
    # Grace period management (Tier 3)
    enable_grace_periods: bool = True
    grace_period_days: int = 5
    grace_decay_rate: float = 0.8
    min_decay_factor: float = 0.1
    
    # Holding period management (Tier 3)
    min_holding_period_days: int = 3
    max_holding_period_days: int = 90
    enable_regime_overrides: bool = True
    regime_override_cooldown_days: int = 30
    regime_severity_threshold: str = 'high'  # 'normal', 'high', 'critical'
    
    # Whipsaw protection (Tier 3)
    enable_whipsaw_protection: bool = True
    max_cycles_per_protection_period: int = 1
    whipsaw_protection_days: int = 14
    min_position_duration_hours: int = 4
    
    def validate(self) -> List[str]:
        """Validate configuration and return any errors"""
        errors = []
        
        if self.grace_period_days < 1:
            errors.append("grace_period_days must be at least 1")
        
        if self.min_holding_period_days >= self.max_holding_period_days:
            errors.append("min_holding_period_days must be less than max_holding_period_days")
        
        valid_severities = ['normal', 'high', 'critical']
        if self.regime_severity_threshold not in valid_severities:
            errors.append(f"regime_severity_threshold must be one of {valid_severities}")
        
        return errors


@dataclass
class CoreAssetManagementConfig:
    """Core asset management configuration (Module 5)"""
    
    # Basic core asset management (Tier 4)
    enable_core_asset_management: bool = False
    max_core_assets: int = 3
    core_asset_override_threshold: float = 0.95
    core_asset_expiry_days: int = 90
    
    # Performance monitoring (Tier 4)
    core_asset_underperformance_threshold: float = 0.15
    core_asset_underperformance_period: int = 30
    core_asset_extension_limit: int = 2
    core_asset_performance_check_frequency: int = 7
    
    # Smart diversification (Tier 4)
    smart_diversification_overrides: int = 2
    
    def validate(self) -> List[str]:
        """Validate configuration and return any errors"""
        errors = []
        
        if self.core_asset_override_threshold < 0.8:
            errors.append("core_asset_override_threshold should be at least 0.8 for meaningful overrides")
        
        if self.max_core_assets < 1:
            errors.append("max_core_assets must be at least 1 if enabled")
        
        return errors


@dataclass
class SystemConfig:
    """Base system configuration"""
    
    # Basic system settings (Tier 1)
    buckets: List[str] = field(default_factory=lambda: ["Risk Assets", "Defensive Assets"])
    start_date: str = '2021-01-01'
    end_date: Optional[str] = None
    cash: float = 100000
    commission: float = 0.001
    
    # Strategy settings (Tier 1)
    rebalance_frequency: str = 'monthly'  # 'daily', 'weekly', 'monthly'
    min_trending_confidence: float = 0.7
    
    # Analysis settings (Tier 2)
    timeframes: List[str] = field(default_factory=lambda: ['1d', '4h', '1h'])
    
    # Output settings (Tier 1)
    plot_results: bool = False
    
    def validate(self) -> List[str]:
        """Validate configuration and return any errors"""
        errors = []
        
        valid_frequencies = ['daily', 'weekly', 'monthly']
        if self.rebalance_frequency not in valid_frequencies:
            errors.append(f"rebalance_frequency must be one of {valid_frequencies}")
        
        if self.cash < 1000:
            errors.append("cash should be at least 1000 for meaningful backtesting")
        
        if not self.buckets:
            errors.append("At least one bucket must be specified")
        
        return errors


@dataclass
class StrategyConfiguration:
    """Unified configuration for complete strategy setup"""
    
    # Metadata
    name: str = "Default Strategy"
    description: str = "Auto-generated configuration"
    tier_level: int = 1
    created_date: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)
    version: str = "1.0.0"
    
    # Module configurations
    core_config: CoreRebalancerConfig = field(default_factory=CoreRebalancerConfig)
    bucket_config: BucketDiversificationConfig = field(default_factory=BucketDiversificationConfig)
    sizing_config: DynamicSizingConfig = field(default_factory=DynamicSizingConfig)
    lifecycle_config: LifecycleManagementConfig = field(default_factory=LifecycleManagementConfig)
    core_asset_config: CoreAssetManagementConfig = field(default_factory=CoreAssetManagementConfig)
    system_config: SystemConfig = field(default_factory=SystemConfig)
    
    def validate(self) -> List[str]:
        """Validate entire configuration and return all errors"""
        all_errors = []
        
        # Validate each module configuration
        all_errors.extend(self.core_config.validate())
        all_errors.extend(self.bucket_config.validate())
        all_errors.extend(self.sizing_config.validate())
        all_errors.extend(self.lifecycle_config.validate())
        all_errors.extend(self.core_asset_config.validate())
        all_errors.extend(self.system_config.validate())
        
        # Cross-module validation
        all_errors.extend(self._validate_cross_module())
        
        return all_errors
    
    def _validate_cross_module(self) -> List[str]:
        """Validate relationships between modules"""
        errors = []
        
        # Core asset management requires bucket diversification for overrides
        if (self.core_asset_config.enable_core_asset_management and 
            not self.bucket_config.enable_bucket_diversification):
            errors.append("Core asset management requires bucket diversification to be enabled")
        
        # Two-stage sizing max should be <= core max position
        if (self.sizing_config.enable_two_stage_sizing and
            self.sizing_config.max_single_position > self.core_config.max_single_position_pct):
            errors.append("max_single_position should not exceed max_single_position_pct")
        
        return errors
    
    def to_rebalancing_limits(self) -> RebalancingLimits:
        """Convert to RebalancingLimits for backward compatibility"""
        return RebalancingLimits(
            # Core parameters
            max_total_positions=self.core_config.max_total_positions,
            max_new_positions=self.core_config.max_new_positions,
            min_score_threshold=self.core_config.min_score_threshold,
            min_score_new_position=self.core_config.min_score_new_position,
            max_single_position_pct=self.core_config.max_single_position_pct,
            target_total_allocation=self.core_config.target_total_allocation,
            
            # Bucket diversification
            enable_bucket_diversification=self.bucket_config.enable_bucket_diversification,
            max_positions_per_bucket=self.bucket_config.max_positions_per_bucket,
            max_allocation_per_bucket=self.bucket_config.max_allocation_per_bucket,
            min_buckets_represented=self.bucket_config.min_buckets_represented,
            allow_bucket_overflow=self.bucket_config.allow_bucket_overflow,
            
            # Dynamic sizing
            enable_dynamic_sizing=self.sizing_config.enable_dynamic_sizing,
            sizing_mode=self.sizing_config.sizing_mode,
            max_single_position=self.sizing_config.max_single_position,
            min_position_size=self.sizing_config.min_position_size,
            residual_strategy=self.sizing_config.residual_strategy,
            max_residual_per_asset=self.sizing_config.max_residual_per_asset,
            max_residual_multiple=self.sizing_config.max_residual_multiple,
            
            # Lifecycle management
            enable_grace_periods=self.lifecycle_config.enable_grace_periods,
            grace_period_days=self.lifecycle_config.grace_period_days,
            grace_decay_rate=self.lifecycle_config.grace_decay_rate,
            min_decay_factor=self.lifecycle_config.min_decay_factor,
            min_holding_period_days=self.lifecycle_config.min_holding_period_days,
            max_holding_period_days=self.lifecycle_config.max_holding_period_days,
            enable_regime_overrides=self.lifecycle_config.enable_regime_overrides,
            regime_override_cooldown_days=self.lifecycle_config.regime_override_cooldown_days,
            enable_whipsaw_protection=self.lifecycle_config.enable_whipsaw_protection,
            max_cycles_per_protection_period=self.lifecycle_config.max_cycles_per_protection_period,
            whipsaw_protection_days=self.lifecycle_config.whipsaw_protection_days,
            min_position_duration_hours=self.lifecycle_config.min_position_duration_hours,
            
            # Core asset management  
            enable_core_asset_management=self.core_asset_config.enable_core_asset_management,
            core_asset_override_threshold=self.core_asset_config.core_asset_override_threshold,
            core_asset_expiry_days=self.core_asset_config.core_asset_expiry_days,
            core_asset_underperformance_threshold=self.core_asset_config.core_asset_underperformance_threshold,
            core_asset_underperformance_period=self.core_asset_config.core_asset_underperformance_period,
            max_core_assets=self.core_asset_config.max_core_assets,
            core_asset_extension_limit=self.core_asset_config.core_asset_extension_limit,
            core_asset_performance_check_frequency=self.core_asset_config.core_asset_performance_check_frequency
        )
    
    def to_cli_args(self) -> List[str]:
        """Convert configuration to CLI argument list"""
        args = []
        
        # System parameters
        args.extend(['--buckets', ','.join(self.system_config.buckets)])
        args.extend(['--start-date', self.system_config.start_date])
        if self.system_config.end_date:
            args.extend(['--end-date', self.system_config.end_date])
        args.extend(['--cash', str(self.system_config.cash)])
        args.extend(['--commission', str(self.system_config.commission)])
        args.extend(['--rebalance-freq', self.system_config.rebalance_frequency])
        args.extend(['--min-trending-confidence', str(self.system_config.min_trending_confidence)])
        
        # Core rebalancer
        args.extend(['--max-total-positions', str(self.core_config.max_total_positions)])
        args.extend(['--max-new-positions', str(self.core_config.max_new_positions)])
        args.extend(['--min-score', str(self.core_config.min_score_threshold)])
        args.extend(['--technical-weight', str(self.core_config.technical_weight)])
        args.extend(['--fundamental-weight', str(self.core_config.fundamental_weight)])
        
        if not self.core_config.enable_technical_analysis:
            args.append('--disable-technical')
        if not self.core_config.enable_fundamental_analysis:
            args.append('--disable-fundamental')
        
        # Bucket diversification
        if self.bucket_config.enable_bucket_diversification:
            args.append('--enable-bucket-diversification')
            args.extend(['--max-positions-per-bucket', str(self.bucket_config.max_positions_per_bucket)])
            args.extend(['--max-allocation-per-bucket', str(self.bucket_config.max_allocation_per_bucket)])
            args.extend(['--min-buckets-represented', str(self.bucket_config.min_buckets_represented)])
        
        # Core asset management
        if self.core_asset_config.enable_core_asset_management:
            args.append('--enable-core-assets')
            args.extend(['--max-core-assets', str(self.core_asset_config.max_core_assets)])
            args.extend(['--core-override-threshold', str(self.core_asset_config.core_asset_override_threshold)])
            args.extend(['--core-expiry-days', str(self.core_asset_config.core_asset_expiry_days)])
        
        # Output options
        if self.system_config.plot_results:
            args.append('--plot')
        
        return args
    
    def get_parameter_count(self) -> int:
        """Get total number of configured parameters"""
        # This would count non-default parameters
        # Implementation depends on specific counting logic
        return len([attr for attr in dir(self) if not attr.startswith('_')])
    
    def get_tier_info(self) -> ConfigurationTier.TierInfo:
        """Get tier information for this configuration"""
        return ConfigurationTiers.get_tier_by_level(self.tier_level)
    
    def update_metadata(self):
        """Update last modified timestamp"""
        self.last_modified = datetime.now()


# Factory functions for creating configurations
def create_basic_configuration(name: str = "Basic Strategy") -> StrategyConfiguration:
    """Create a basic Tier 1 configuration"""
    return StrategyConfiguration(
        name=name,
        description="Basic configuration with essential parameters only",
        tier_level=1,
        core_config=CoreRebalancerConfig(
            max_total_positions=8,
            max_new_positions=2,
            min_score_threshold=0.65
        ),
        bucket_config=BucketDiversificationConfig(
            enable_bucket_diversification=False
        ),
        sizing_config=DynamicSizingConfig(
            enable_dynamic_sizing=False,
            sizing_mode='equal_weight'
        ),
        lifecycle_config=LifecycleManagementConfig(
            enable_grace_periods=False,
            enable_whipsaw_protection=False
        ),
        core_asset_config=CoreAssetManagementConfig(
            enable_core_asset_management=False
        )
    )


def create_intermediate_configuration(name: str = "Intermediate Strategy") -> StrategyConfiguration:
    """Create an intermediate Tier 2 configuration"""
    return StrategyConfiguration(
        name=name,
        description="Intermediate configuration with enhanced features",
        tier_level=2,
        core_config=CoreRebalancerConfig(
            max_total_positions=10,
            max_new_positions=3,
            min_score_threshold=0.6,
            technical_weight=0.6,
            fundamental_weight=0.4
        ),
        bucket_config=BucketDiversificationConfig(
            enable_bucket_diversification=True,
            max_positions_per_bucket=4,
            min_buckets_represented=2
        ),
        sizing_config=DynamicSizingConfig(
            enable_dynamic_sizing=True,
            sizing_mode='adaptive'
        ),
        lifecycle_config=LifecycleManagementConfig(
            enable_grace_periods=False,
            enable_whipsaw_protection=False
        ),
        core_asset_config=CoreAssetManagementConfig(
            enable_core_asset_management=False
        )
    )


def create_advanced_configuration(name: str = "Advanced Strategy") -> StrategyConfiguration:
    """Create an advanced Tier 3 configuration"""
    return StrategyConfiguration(
        name=name,
        description="Advanced configuration with risk management features",
        tier_level=3,
        bucket_config=BucketDiversificationConfig(
            enable_bucket_diversification=True,
            max_positions_per_bucket=4,
            min_buckets_represented=2,
            correlation_limit=0.8
        ),
        sizing_config=DynamicSizingConfig(
            enable_dynamic_sizing=True,
            sizing_mode='adaptive',
            enable_two_stage_sizing=True
        ),
        lifecycle_config=LifecycleManagementConfig(
            enable_grace_periods=True,
            grace_period_days=5,
            min_holding_period_days=3,
            enable_whipsaw_protection=True
        ),
        core_asset_config=CoreAssetManagementConfig(
            enable_core_asset_management=False
        )
    )


def create_expert_configuration(name: str = "Expert Strategy") -> StrategyConfiguration:
    """Create an expert Tier 4 configuration"""
    return StrategyConfiguration(
        name=name,
        description="Expert configuration with all professional features",
        tier_level=4,
        bucket_config=BucketDiversificationConfig(
            enable_bucket_diversification=True,
            max_positions_per_bucket=5,
            min_buckets_represented=3,
            allow_bucket_overflow=True,
            correlation_limit=0.75
        ),
        sizing_config=DynamicSizingConfig(
            enable_dynamic_sizing=True,
            sizing_mode='adaptive',
            enable_two_stage_sizing=True,
            residual_strategy='safe_top_slice'
        ),
        lifecycle_config=LifecycleManagementConfig(
            enable_grace_periods=True,
            grace_period_days=4,
            min_holding_period_days=3,
            enable_regime_overrides=True,
            enable_whipsaw_protection=True
        ),
        core_asset_config=CoreAssetManagementConfig(
            enable_core_asset_management=True,
            max_core_assets=3,
            core_asset_override_threshold=0.95
        )
    ) 