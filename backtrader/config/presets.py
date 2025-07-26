"""
Strategy Presets for Configuration Management

Provides professionally-designed strategy configurations for:
- Conservative/institutional strategies
- Aggressive growth strategies
- Adaptive/balanced strategies
- Institutional-grade configurations
"""

from typing import Dict
from .data_models import (
    StrategyConfiguration,
    CoreRebalancerConfig,
    BucketDiversificationConfig, 
    DynamicSizingConfig,
    LifecycleManagementConfig,
    CoreAssetManagementConfig,
    SystemConfig
)


class StrategyPresets:
    """Library of predefined strategy configurations"""
    
    @staticmethod
    def conservative() -> StrategyConfiguration:
        """Conservative diversified strategy preset
        
        Designed for: Risk-averse investors, institutional mandates
        Risk Level: Low
        Complexity: Tier 2 (Intermediate)
        Features: Strict diversification, lower position limits, equal weighting
        """
        return StrategyConfiguration(
            name="Conservative Diversified",
            description="Risk-averse strategy with strict diversification and conservative position sizing",
            tier_level=2,
            
            system_config=SystemConfig(
                buckets=["Risk Assets", "Defensive Assets", "International"],
                cash=100000,
                commission=0.001,
                rebalance_frequency='monthly',
                min_trending_confidence=0.75,  # Higher confidence requirement
                plot_results=False
            ),
            
            core_config=CoreRebalancerConfig(
                max_total_positions=8,           # Lower diversification
                max_new_positions=2,             # Conservative new position rate
                min_score_threshold=0.65,        # Higher quality threshold
                min_score_new_position=0.7,      # Even higher for new positions
                max_single_position_pct=0.15,    # Conservative max position size
                target_total_allocation=0.90,    # Leave more cash buffer
                technical_weight=0.4,            # Favor fundamentals
                fundamental_weight=0.6
            ),
            
            bucket_config=BucketDiversificationConfig(
                enable_bucket_diversification=True,
                max_positions_per_bucket=3,      # Strict bucket limits
                max_allocation_per_bucket=0.35,  # Conservative bucket allocation
                min_buckets_represented=3,       # Force diversification
                allow_bucket_overflow=False,     # No exceptions
                correlation_limit=0.7            # Strict correlation limits
            ),
            
            sizing_config=DynamicSizingConfig(
                enable_dynamic_sizing=False,     # Use equal weighting
                sizing_mode='equal_weight',
                max_single_position=0.12,        # Conservative individual sizing
                min_position_size=0.03           # Higher minimum to avoid dust
            ),
            
            lifecycle_config=LifecycleManagementConfig(
                enable_grace_periods=True,
                grace_period_days=7,             # Longer grace period
                grace_decay_rate=0.85,           # Slower decay
                min_holding_period_days=5,       # Longer minimum holding
                max_holding_period_days=120,     # Longer maximum holding
                enable_regime_overrides=False,   # No aggressive regime moves
                enable_whipsaw_protection=True,
                whipsaw_protection_days=21       # Longer whipsaw protection
            ),
            
            core_asset_config=CoreAssetManagementConfig(
                enable_core_asset_management=False  # Disabled for conservative strategy
            )
        )
    
    @staticmethod
    def aggressive() -> StrategyConfiguration:
        """Aggressive growth strategy preset
        
        Designed for: Growth-oriented investors, high-risk tolerance
        Risk Level: High
        Complexity: Tier 3 (Advanced)
        Features: Higher position limits, score-weighted sizing, shorter holding periods
        """
        return StrategyConfiguration(
            name="Aggressive Growth",
            description="High-risk, high-reward growth strategy with dynamic sizing",
            tier_level=3,
            
            system_config=SystemConfig(
                buckets=["Risk Assets", "Growth", "High Beta"],
                cash=100000,
                commission=0.001,
                rebalance_frequency='weekly',     # More frequent rebalancing
                min_trending_confidence=0.65,     # Lower confidence threshold
                plot_results=False
            ),
            
            core_config=CoreRebalancerConfig(
                max_total_positions=12,           # Higher diversification
                max_new_positions=5,              # Aggressive new position rate
                min_score_threshold=0.55,         # Lower threshold for opportunities
                min_score_new_position=0.6,       # Still selective for new positions
                max_single_position_pct=0.25,     # Larger individual positions
                target_total_allocation=0.98,     # Almost fully invested
                technical_weight=0.7,             # Favor technical analysis
                fundamental_weight=0.3
            ),
            
            bucket_config=BucketDiversificationConfig(
                enable_bucket_diversification=True,
                max_positions_per_bucket=6,       # More flexible bucket limits
                max_allocation_per_bucket=0.6,    # Allow concentration
                min_buckets_represented=2,        # Minimum diversification
                allow_bucket_overflow=True,       # Allow exceptions
                correlation_limit=0.85            # More lenient correlation
            ),
            
            sizing_config=DynamicSizingConfig(
                enable_dynamic_sizing=True,
                sizing_mode='score_weighted',      # Favor higher scoring assets
                max_single_position=0.20,         # Allow larger positions
                min_position_size=0.02,           # Standard minimum
                enable_two_stage_sizing=True,
                residual_strategy='safe_top_slice' # Allocate residual to top positions
            ),
            
            lifecycle_config=LifecycleManagementConfig(
                enable_grace_periods=True,
                grace_period_days=3,              # Shorter grace period
                grace_decay_rate=0.75,            # Faster decay
                min_holding_period_days=1,        # Very short minimum holding
                max_holding_period_days=60,       # Shorter maximum holding
                enable_regime_overrides=True,     # Allow aggressive regime moves
                regime_override_cooldown_days=14, # Shorter cooldown
                enable_whipsaw_protection=True,
                whipsaw_protection_days=7         # Shorter whipsaw protection
            ),
            
            core_asset_config=CoreAssetManagementConfig(
                enable_core_asset_management=True,
                max_core_assets=2,                # Limited core assets
                core_asset_override_threshold=0.92, # Lower threshold for designation
                core_asset_expiry_days=60         # Shorter expiry
            )
        )
    
    @staticmethod
    def adaptive() -> StrategyConfiguration:
        """Regime-adaptive balanced strategy preset
        
        Designed for: Balanced investors, regime-aware strategies
        Risk Level: Medium
        Complexity: Tier 3 (Advanced)
        Features: Regime adaptation, balanced approach, moderate risk controls
        """
        return StrategyConfiguration(
            name="Regime Adaptive",
            description="Balanced strategy that adapts to market regimes with moderate risk controls",
            tier_level=3,
            
            system_config=SystemConfig(
                buckets=["Risk Assets", "Defensive Assets", "Commodities", "International"],
                cash=100000,
                commission=0.001,
                rebalance_frequency='monthly',
                min_trending_confidence=0.7,      # Balanced confidence
                plot_results=False
            ),
            
            core_config=CoreRebalancerConfig(
                max_total_positions=10,           # Balanced diversification
                max_new_positions=3,              # Moderate new position rate
                min_score_threshold=0.6,          # Balanced threshold
                min_score_new_position=0.65,      # Slightly higher for new
                max_single_position_pct=0.18,     # Moderate max position size
                target_total_allocation=0.95,     # Standard allocation
                technical_weight=0.5,             # Balanced analysis
                fundamental_weight=0.5
            ),
            
            bucket_config=BucketDiversificationConfig(
                enable_bucket_diversification=True,
                max_positions_per_bucket=4,       # Balanced bucket limits
                max_allocation_per_bucket=0.4,    # Balanced bucket allocation
                min_buckets_represented=3,        # Good diversification
                allow_bucket_overflow=False,      # Maintain discipline
                correlation_limit=0.8             # Standard correlation limit
            ),
            
            sizing_config=DynamicSizingConfig(
                enable_dynamic_sizing=True,
                sizing_mode='adaptive',           # Intelligent adaptive sizing
                max_single_position=0.15,         # Balanced individual sizing
                min_position_size=0.02,           # Standard minimum
                enable_two_stage_sizing=True,
                residual_strategy='proportional'  # Proportional residual allocation
            ),
            
            lifecycle_config=LifecycleManagementConfig(
                enable_grace_periods=True,
                grace_period_days=5,              # Standard grace period
                grace_decay_rate=0.8,             # Standard decay
                min_holding_period_days=3,        # Standard minimum holding
                max_holding_period_days=90,       # Standard maximum holding
                enable_regime_overrides=True,     # Allow regime adaptation
                regime_override_cooldown_days=21, # Balanced cooldown
                regime_severity_threshold='high', # Only for significant changes
                enable_whipsaw_protection=True,
                whipsaw_protection_days=14        # Standard whipsaw protection
            ),
            
            core_asset_config=CoreAssetManagementConfig(
                enable_core_asset_management=True,
                max_core_assets=2,                # Limited core assets
                core_asset_override_threshold=0.95, # Standard threshold
                core_asset_expiry_days=90,        # Standard expiry
                core_asset_underperformance_threshold=0.15,
                core_asset_underperformance_period=30
            )
        )
    
    @staticmethod
    def institutional() -> StrategyConfiguration:
        """Professional institutional-grade strategy preset
        
        Designed for: Hedge funds, institutional investors, professional managers
        Risk Level: Medium-High
        Complexity: Tier 4 (Expert)
        Features: All professional features, sophisticated risk management
        """
        return StrategyConfiguration(
            name="Professional Institutional",
            description="Institutional-grade strategy with all professional features and sophisticated risk management",
            tier_level=4,
            
            system_config=SystemConfig(
                buckets=["Risk Assets", "Defensive Assets", "International", "Alternatives"],
                cash=100000,
                commission=0.001,
                rebalance_frequency='weekly',      # Professional frequency
                min_trending_confidence=0.72,      # Institutional confidence
                timeframes=['1d', '4h', '1h', '15m'], # Multiple timeframes
                plot_results=False
            ),
            
            core_config=CoreRebalancerConfig(
                max_total_positions=15,            # Institutional diversification
                max_new_positions=4,               # Professional new position rate
                min_score_threshold=0.62,          # Professional threshold
                min_score_new_position=0.68,       # Higher standard for new positions
                max_single_position_pct=0.2,       # Professional max position size
                target_total_allocation=0.96,      # Institutional allocation target
                technical_weight=0.55,             # Slightly favor technical
                fundamental_weight=0.45
            ),
            
            bucket_config=BucketDiversificationConfig(
                enable_bucket_diversification=True,
                max_positions_per_bucket=5,        # Professional bucket limits
                max_allocation_per_bucket=0.35,    # Institutional allocation limits
                min_buckets_represented=4,         # Comprehensive diversification
                allow_bucket_overflow=True,        # Allow professional overrides
                correlation_limit=0.75,            # Strict correlation control
                correlation_window=60              # Professional correlation window
            ),
            
            sizing_config=DynamicSizingConfig(
                enable_dynamic_sizing=True,
                sizing_mode='adaptive',            # Sophisticated adaptive sizing
                max_single_position=0.16,          # Professional individual sizing
                min_position_size=0.015,           # Lower minimum for flexibility
                enable_two_stage_sizing=True,
                residual_strategy='safe_top_slice', # Professional residual management
                max_residual_per_asset=0.04,       # Conservative residual limits
                max_residual_multiple=0.5
            ),
            
            lifecycle_config=LifecycleManagementConfig(
                enable_grace_periods=True,
                grace_period_days=4,               # Professional grace period
                grace_decay_rate=0.85,             # Conservative decay
                min_decay_factor=0.1,              # Professional minimum
                min_holding_period_days=3,         # Professional minimum holding
                max_holding_period_days=60,        # Dynamic maximum holding
                enable_regime_overrides=True,      # Allow professional overrides
                regime_override_cooldown_days=28,  # Professional cooldown
                regime_severity_threshold='high',  # Conservative override threshold
                enable_whipsaw_protection=True,
                max_cycles_per_protection_period=1, # Strict whipsaw control
                whipsaw_protection_days=10,        # Professional protection period
                min_position_duration_hours=2      # Professional minimum duration
            ),
            
            core_asset_config=CoreAssetManagementConfig(
                enable_core_asset_management=True,
                max_core_assets=3,                 # Professional core asset limit
                core_asset_override_threshold=0.96, # High professional threshold
                core_asset_expiry_days=75,         # Professional expiry period
                core_asset_underperformance_threshold=0.12, # Strict underperformance
                core_asset_underperformance_period=30,
                core_asset_extension_limit=2,      # Limited extensions
                core_asset_performance_check_frequency=5, # Frequent monitoring
                smart_diversification_overrides=2  # Professional override limit
            )
        )
    
    @classmethod
    def get_all_presets(cls) -> Dict[str, StrategyConfiguration]:
        """Get all available presets as a dictionary"""
        return {
            'conservative': cls.conservative(),
            'aggressive': cls.aggressive(),
            'adaptive': cls.adaptive(),
            'institutional': cls.institutional()
        }
    
    @classmethod
    def get_preset_info(cls) -> Dict[str, Dict[str, str]]:
        """Get information about all presets"""
        return {
            'conservative': {
                'name': 'Conservative Diversified',
                'risk_level': 'Low',
                'complexity': 'Tier 2 (Intermediate)',
                'target_user': 'Risk-averse investors, institutional mandates',
                'key_features': 'Strict diversification, equal weighting, longer holding periods',
                'max_positions': '8',
                'rebalance_frequency': 'Monthly'
            },
            'aggressive': {
                'name': 'Aggressive Growth',
                'risk_level': 'High', 
                'complexity': 'Tier 3 (Advanced)',
                'target_user': 'Growth-oriented investors, high-risk tolerance',
                'key_features': 'Score-weighted sizing, shorter holding periods, regime adaptation',
                'max_positions': '12',
                'rebalance_frequency': 'Weekly'
            },
            'adaptive': {
                'name': 'Regime Adaptive',
                'risk_level': 'Medium',
                'complexity': 'Tier 3 (Advanced)',
                'target_user': 'Balanced investors, regime-aware strategies',
                'key_features': 'Regime adaptation, balanced approach, moderate risk controls',
                'max_positions': '10',
                'rebalance_frequency': 'Monthly'
            },
            'institutional': {
                'name': 'Professional Institutional',
                'risk_level': 'Medium-High',
                'complexity': 'Tier 4 (Expert)',
                'target_user': 'Hedge funds, institutional investors, professional managers',
                'key_features': 'All professional features, sophisticated risk management, core assets',
                'max_positions': '15',
                'rebalance_frequency': 'Weekly'
            }
        }
    
    @classmethod
    def validate_all_presets(cls) -> Dict[str, bool]:
        """Validate all presets and return results"""
        from .validator import ConfigurationValidator
        
        validator = ConfigurationValidator()
        results = {}
        
        for name, config in cls.get_all_presets().items():
            validation = validator.validate(config)
            results[name] = validation.is_valid
            
            if not validation.is_valid:
                print(f"⚠️  Preset '{name}' has validation issues:")
                for error in validation.errors[:2]:  # Show first 2 errors
                    print(f"   • {error.parameter}: {error.message}")
        
        return results
    
    @classmethod
    def get_preset_by_risk_level(cls, risk_level: str) -> StrategyConfiguration:
        """Get preset by risk level"""
        risk_mapping = {
            'low': cls.conservative(),
            'medium': cls.adaptive(),
            'high': cls.aggressive(),
            'institutional': cls.institutional()
        }
        
        return risk_mapping.get(risk_level.lower(), cls.adaptive())
    
    @classmethod
    def get_preset_by_complexity(cls, tier_level: int) -> StrategyConfiguration:
        """Get preset by complexity tier"""
        tier_mapping = {
            1: cls.conservative(),  # Basic -> Conservative
            2: cls.conservative(),  # Intermediate -> Conservative
            3: cls.adaptive(),      # Advanced -> Adaptive  
            4: cls.institutional()  # Expert -> Institutional
        }
        
        return tier_mapping.get(tier_level, cls.adaptive()) 