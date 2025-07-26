"""
Parameter Registry for Configuration Management

Centralized registry of all backtesting framework parameters with:
- Parameter definitions and metadata
- Validation rules and constraints
- Tier-based complexity organization
- Dependency tracking
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Type, Optional, Union, Callable
from datetime import datetime
from enum import Enum


class ParameterTier(Enum):
    """Parameter complexity tiers"""
    BASIC = 1        # Beginner - Essential parameters only
    INTERMEDIATE = 2 # Intermediate - Enhanced features
    ADVANCED = 3     # Advanced - Risk management
    EXPERT = 4       # Expert - Professional features


class ParameterType(Enum):
    """Parameter data types"""
    INTEGER = int
    FLOAT = float
    BOOLEAN = bool
    STRING = str
    LIST = list
    DICT = dict


@dataclass
class ValidationRule:
    """Parameter validation rule"""
    name: str
    description: str
    validator: Callable[[Any], bool]
    error_message: str


@dataclass
class ParameterDefinition:
    """Complete parameter definition with metadata"""
    name: str                           # Internal parameter name
    type: Type                          # Parameter data type
    default_value: Any                  # Default value
    description: str                    # Short description
    tier_level: ParameterTier          # Complexity tier
    module: str                        # Owning module
    cli_name: str                      # CLI argument name
    help_text: str                     # Detailed help text
    
    # Validation and constraints
    validation_rules: List[ValidationRule] = field(default_factory=list)
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    choices: Optional[List[Any]] = None
    
    # Dependencies and relationships
    dependencies: List[str] = field(default_factory=list)
    mutually_exclusive: List[str] = field(default_factory=list)
    enables: List[str] = field(default_factory=list)  # Parameters this enables
    
    # Documentation
    examples: List[str] = field(default_factory=list)
    use_cases: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class ParameterRegistry:
    """Central registry of all framework parameters"""
    
    def __init__(self):
        self.parameters: Dict[str, ParameterDefinition] = {}
        self._register_all_parameters()
    
    def register_parameter(self, param: ParameterDefinition):
        """Register a parameter with the registry"""
        self.parameters[param.name] = param
    
    def get_parameter(self, name: str) -> Optional[ParameterDefinition]:
        """Get parameter definition by name"""
        return self.parameters.get(name)
    
    def get_parameters_by_tier(self, tier_level: int) -> List[ParameterDefinition]:
        """Get all parameters for a tier level and below"""
        return [
            param for param in self.parameters.values()
            if param.tier_level.value <= tier_level
        ]
    
    def get_parameters_by_module(self, module: str) -> List[ParameterDefinition]:
        """Get all parameters for a specific module"""
        return [
            param for param in self.parameters.values()
            if param.module == module
        ]
    
    def get_cli_parameters(self, tier_level: int = 4) -> Dict[str, ParameterDefinition]:
        """Get parameters as CLI argument mapping"""
        params = self.get_parameters_by_tier(tier_level)
        return {param.cli_name: param for param in params}
    
    def _register_all_parameters(self):
        """Register all framework parameters"""
        # Module 1: Core Rebalancer Engine
        self._register_core_rebalancer_parameters()
        
        # Module 2: Bucket Diversification  
        self._register_bucket_diversification_parameters()
        
        # Module 3: Dynamic Position Sizing
        self._register_dynamic_sizing_parameters()
        
        # Module 4: Grace & Holding Period Management
        self._register_lifecycle_management_parameters()
        
        # Module 5: Core Asset Management
        self._register_core_asset_management_parameters()
        
        # Base System Parameters
        self._register_system_parameters()
    
    def _register_core_rebalancer_parameters(self):
        """Register Module 1: Core Rebalancer Engine parameters"""
        
        # Basic portfolio management (Tier 1)
        self.register_parameter(ParameterDefinition(
            name='max_total_positions',
            type=int,
            default_value=10,
            description='Maximum total positions in portfolio',
            tier_level=ParameterTier.BASIC,
            module='Core Rebalancer Engine',
            cli_name='max-total-positions',
            help_text='Sets the maximum number of positions the portfolio can hold at any time. Higher values allow more diversification but may dilute returns.',
            validation_rules=[
                ValidationRule(
                    name='positive_integer',
                    description='Must be positive integer',
                    validator=lambda x: isinstance(x, int) and x > 0,
                    error_message='max_total_positions must be a positive integer'
                ),
                ValidationRule(
                    name='reasonable_range',
                    description='Should be between 1 and 50',
                    validator=lambda x: 1 <= x <= 50,
                    error_message='max_total_positions should be between 1 and 50 for practical portfolio management'
                )
            ],
            min_value=1,
            max_value=50,
            examples=['5 (concentrated)', '10 (balanced)', '20 (diversified)'],
            use_cases=['Conservative: 5-8', 'Balanced: 8-15', 'Diversified: 15-25'],
            warnings=['Values >25 may lead to over-diversification and diluted returns']
        ))
        
        self.register_parameter(ParameterDefinition(
            name='max_new_positions',
            type=int,
            default_value=3,
            description='Maximum new positions per rebalancing period',
            tier_level=ParameterTier.BASIC,
            module='Core Rebalancer Engine',
            cli_name='max-new-positions',
            help_text='Limits how many new positions can be opened in a single rebalancing period. Helps control portfolio turnover and transaction costs.',
            validation_rules=[
                ValidationRule(
                    name='positive_integer',
                    description='Must be positive integer',
                    validator=lambda x: isinstance(x, int) and x > 0,
                    error_message='max_new_positions must be a positive integer'
                )
            ],
            min_value=1,
            max_value=20,
            dependencies=['max_total_positions'],
            examples=['1 (conservative)', '3 (balanced)', '5 (aggressive)'],
            use_cases=['Low turnover: 1-2', 'Moderate: 2-4', 'High turnover: 4+'],
            warnings=['Should not exceed max_total_positions']
        ))
        
        self.register_parameter(ParameterDefinition(
            name='min_score_threshold',
            type=float,
            default_value=0.6,
            description='Minimum score to maintain existing positions',
            tier_level=ParameterTier.BASIC,
            module='Core Rebalancer Engine',
            cli_name='min-score-threshold',
            help_text='Assets with scores below this threshold will be closed. Lower values keep more positions but may reduce quality.',
            validation_rules=[
                ValidationRule(
                    name='valid_range',
                    description='Must be between 0.0 and 1.0',
                    validator=lambda x: isinstance(x, (int, float)) and 0.0 <= x <= 1.0,
                    error_message='min_score_threshold must be between 0.0 and 1.0'
                )
            ],
            min_value=0.0,
            max_value=1.0,
            examples=['0.5 (lenient)', '0.6 (balanced)', '0.7 (strict)'],
            use_cases=['Bear market: 0.7+', 'Bull market: 0.5-0.6', 'Neutral: 0.6'],
            warnings=['Values >0.8 may cause excessive turnover']
        ))
        
        self.register_parameter(ParameterDefinition(
            name='min_score_new_position',
            type=float,
            default_value=0.65,
            description='Minimum score required for new positions',
            tier_level=ParameterTier.INTERMEDIATE,
            module='Core Rebalancer Engine',
            cli_name='min-score-new-position',
            help_text='New positions require higher scores than existing ones to prevent low-quality additions.',
            validation_rules=[
                ValidationRule(
                    name='valid_range',
                    description='Must be between 0.0 and 1.0',
                    validator=lambda x: isinstance(x, (int, float)) and 0.0 <= x <= 1.0,
                    error_message='min_score_new_position must be between 0.0 and 1.0'
                )
            ],
            min_value=0.0,
            max_value=1.0,
            dependencies=['min_score_threshold'],
            examples=['0.65 (balanced)', '0.7 (conservative)', '0.75 (strict)'],
            warnings=['Should typically be >= min_score_threshold']
        ))
        
        # Analysis configuration (Tier 2)
        self.register_parameter(ParameterDefinition(
            name='enable_technical_analysis',
            type=bool,
            default_value=True,
            description='Enable technical analysis in scoring',
            tier_level=ParameterTier.INTERMEDIATE,
            module='Core Rebalancer Engine',
            cli_name='enable-technical-analysis',
            help_text='When enabled, includes technical indicators in asset scoring. Disable for fundamental-only strategies.',
            mutually_exclusive=[],  # Can't disable both technical and fundamental
            examples=['True (default)', 'False (fundamental only)'],
            use_cases=['Trend following: True', 'Value investing: False', 'Balanced: True']
        ))
        
        self.register_parameter(ParameterDefinition(
            name='enable_fundamental_analysis',
            type=bool,
            default_value=True,
            description='Enable fundamental analysis in scoring',
            tier_level=ParameterTier.INTERMEDIATE,
            module='Core Rebalancer Engine',
            cli_name='enable-fundamental-analysis',
            help_text='When enabled, includes fundamental metrics in asset scoring. Disable for technical-only strategies.',
            examples=['True (default)', 'False (technical only)'],
            use_cases=['Value investing: True', 'Day trading: False', 'Balanced: True']
        ))
        
        self.register_parameter(ParameterDefinition(
            name='technical_weight',
            type=float,
            default_value=0.6,
            description='Weight for technical analysis in scoring',
            tier_level=ParameterTier.INTERMEDIATE,
            module='Core Rebalancer Engine',
            cli_name='technical-weight',
            help_text='Relative weight given to technical analysis. Higher values favor trend-following strategies.',
            validation_rules=[
                ValidationRule(
                    name='valid_weight',
                    description='Must be between 0.0 and 1.0',
                    validator=lambda x: isinstance(x, (int, float)) and 0.0 <= x <= 1.0,
                    error_message='technical_weight must be between 0.0 and 1.0'
                )
            ],
            min_value=0.0,
            max_value=1.0,
            dependencies=['enable_technical_analysis'],
            examples=['0.3 (value focus)', '0.6 (balanced)', '0.8 (trend focus)'],
            warnings=['Should sum with fundamental_weight to ~1.0']
        ))
        
        self.register_parameter(ParameterDefinition(
            name='fundamental_weight',
            type=float,
            default_value=0.4,
            description='Weight for fundamental analysis in scoring',
            tier_level=ParameterTier.INTERMEDIATE,
            module='Core Rebalancer Engine',
            cli_name='fundamental-weight',
            help_text='Relative weight given to fundamental analysis. Higher values favor value-based strategies.',
            validation_rules=[
                ValidationRule(
                    name='valid_weight',
                    description='Must be between 0.0 and 1.0',
                    validator=lambda x: isinstance(x, (int, float)) and 0.0 <= x <= 1.0,
                    error_message='fundamental_weight must be between 0.0 and 1.0'
                )
            ],
            min_value=0.0,
            max_value=1.0,
            dependencies=['enable_fundamental_analysis'],
            examples=['0.2 (trend focus)', '0.4 (balanced)', '0.7 (value focus)'],
            warnings=['Should sum with technical_weight to ~1.0']
        ))
        
        # Position sizing (Tier 2)
        self.register_parameter(ParameterDefinition(
            name='max_single_position_pct',
            type=float,
            default_value=0.2,
            description='Maximum allocation to any single position',
            tier_level=ParameterTier.INTERMEDIATE,
            module='Core Rebalancer Engine',
            cli_name='max-single-position-pct',
            help_text='Prevents over-concentration in any single asset. 0.2 = 20% maximum per position.',
            validation_rules=[
                ValidationRule(
                    name='valid_percentage',
                    description='Must be between 0.01 and 1.0',
                    validator=lambda x: isinstance(x, (int, float)) and 0.01 <= x <= 1.0,
                    error_message='max_single_position_pct must be between 0.01 and 1.0'
                )
            ],
            min_value=0.01,
            max_value=1.0,
            examples=['0.1 (10% - conservative)', '0.2 (20% - balanced)', '0.3 (30% - aggressive)'],
            use_cases=['Diversified: 0.05-0.15', 'Balanced: 0.15-0.25', 'Concentrated: 0.25-0.5'],
            warnings=['Values >0.3 may create concentration risk']
        ))
        
        self.register_parameter(ParameterDefinition(
            name='target_total_allocation',
            type=float,
            default_value=0.95,
            description='Target total portfolio allocation percentage',
            tier_level=ParameterTier.INTERMEDIATE,
            module='Core Rebalancer Engine',
            cli_name='target-total-allocation',
            help_text='Target percentage of portfolio to allocate to positions. Remainder stays in cash.',
            validation_rules=[
                ValidationRule(
                    name='valid_allocation',
                    description='Must be between 0.5 and 1.0',
                    validator=lambda x: isinstance(x, (int, float)) and 0.5 <= x <= 1.0,
                    error_message='target_total_allocation must be between 0.5 and 1.0'
                )
            ],
            min_value=0.5,
            max_value=1.0,
            examples=['0.9 (90% - conservative)', '0.95 (95% - balanced)', '0.98 (98% - aggressive)'],
            use_cases=['Bear market: 0.8-0.9', 'Bull market: 0.95-0.98', 'Uncertain: 0.85-0.92'],
            warnings=['Values >0.98 leave very little cash buffer']
        ))
    
    def _register_bucket_diversification_parameters(self):
        """Register Module 2: Bucket Diversification parameters"""
        
        self.register_parameter(ParameterDefinition(
            name='enable_bucket_diversification',
            type=bool,
            default_value=False,
            description='Enable bucket-based diversification constraints',
            tier_level=ParameterTier.INTERMEDIATE,
            module='Bucket Diversification',
            cli_name='enable-bucket-diversification',
            help_text='When enabled, enforces diversification rules across asset buckets (Risk Assets, Defensives, etc.)',
            enables=['max_positions_per_bucket', 'max_allocation_per_bucket', 'min_buckets_represented'],
            examples=['True (diversified strategy)', 'False (concentration allowed)'],
            use_cases=['Institutional: True', 'Concentrated: False', 'Balanced: True']
        ))
        
        self.register_parameter(ParameterDefinition(
            name='max_positions_per_bucket',
            type=int,
            default_value=4,
            description='Maximum positions from any single bucket',
            tier_level=ParameterTier.INTERMEDIATE,
            module='Bucket Diversification',
            cli_name='max-positions-per-bucket',
            help_text='Prevents over-concentration in any single asset bucket. Ensures diversification across different asset types.',
            validation_rules=[
                ValidationRule(
                    name='positive_integer',
                    description='Must be positive integer',
                    validator=lambda x: isinstance(x, int) and x > 0,
                    error_message='max_positions_per_bucket must be positive'
                )
            ],
            min_value=1,
            max_value=20,
            dependencies=['enable_bucket_diversification'],
            examples=['3 (strict)', '4 (balanced)', '6 (flexible)'],
            warnings=['Should allow room for adequate diversification']
        ))
        
        self.register_parameter(ParameterDefinition(
            name='max_allocation_per_bucket',
            type=float,
            default_value=0.4,
            description='Maximum allocation percentage to any bucket',
            tier_level=ParameterTier.INTERMEDIATE,
            module='Bucket Diversification',
            cli_name='max-allocation-per-bucket',
            help_text='Limits total allocation to any single bucket. 0.4 = maximum 40% in Risk Assets, for example.',
            validation_rules=[
                ValidationRule(
                    name='valid_percentage',
                    description='Must be between 0.1 and 1.0',
                    validator=lambda x: isinstance(x, (int, float)) and 0.1 <= x <= 1.0,
                    error_message='max_allocation_per_bucket must be between 0.1 and 1.0'
                )
            ],
            min_value=0.1,
            max_value=1.0,
            dependencies=['enable_bucket_diversification'],
            examples=['0.3 (30% - strict)', '0.4 (40% - balanced)', '0.6 (60% - flexible)'],
            warnings=['Values <0.2 may be too restrictive for most strategies']
        ))
        
        self.register_parameter(ParameterDefinition(
            name='min_buckets_represented',
            type=int,
            default_value=2,
            description='Minimum number of buckets that must be represented',
            tier_level=ParameterTier.INTERMEDIATE,
            module='Bucket Diversification',
            cli_name='min-buckets-represented',
            help_text='Forces portfolio to hold positions from at least this many different buckets.',
            validation_rules=[
                ValidationRule(
                    name='positive_integer',
                    description='Must be positive integer',
                    validator=lambda x: isinstance(x, int) and x > 0,
                    error_message='min_buckets_represented must be positive'
                )
            ],
            min_value=1,
            max_value=10,
            dependencies=['enable_bucket_diversification'],
            examples=['2 (basic)', '3 (diversified)', '4 (highly diversified)'],
            warnings=['Higher values may force suboptimal selections']
        ))
        
        self.register_parameter(ParameterDefinition(
            name='allow_bucket_overflow',
            type=bool,
            default_value=False,
            description='Allow positions to exceed bucket limits in special cases',
            tier_level=ParameterTier.ADVANCED,
            module='Bucket Diversification',
            cli_name='allow-bucket-overflow',
            help_text='When enabled, very high-scoring assets can override bucket limits.',
            dependencies=['enable_bucket_diversification'],
            examples=['False (strict limits)', 'True (flexible for high-alpha)'],
            use_cases=['Institutional: False', 'Alpha-focused: True']
        ))
        
        self.register_parameter(ParameterDefinition(
            name='correlation_limit',
            type=float,
            default_value=0.8,
            description='Maximum correlation between assets in same bucket',
            tier_level=ParameterTier.ADVANCED,
            module='Bucket Diversification',
            cli_name='correlation-limit',
            help_text='Prevents selecting highly correlated assets within the same bucket.',
            validation_rules=[
                ValidationRule(
                    name='valid_correlation',
                    description='Must be between 0.0 and 1.0',
                    validator=lambda x: isinstance(x, (int, float)) and 0.0 <= x <= 1.0,
                    error_message='correlation_limit must be between 0.0 and 1.0'
                )
            ],
            min_value=0.0,
            max_value=1.0,
            dependencies=['enable_bucket_diversification'],
            examples=['0.7 (strict)', '0.8 (balanced)', '0.9 (flexible)'],
            warnings=['Values <0.5 may be too restrictive']
        ))
    
    def _register_dynamic_sizing_parameters(self):
        """Register Module 3: Dynamic Position Sizing parameters"""
        
        self.register_parameter(ParameterDefinition(
            name='enable_dynamic_sizing',
            type=bool,
            default_value=True,
            description='Enable dynamic position sizing based on scores',
            tier_level=ParameterTier.INTERMEDIATE,
            module='Dynamic Position Sizing',
            cli_name='enable-dynamic-sizing',
            help_text='When enabled, position sizes adapt based on asset scores and portfolio context.',
            enables=['sizing_mode', 'max_single_position', 'residual_strategy'],
            examples=['True (adaptive)', 'False (fixed sizing)'],
            use_cases=['Professional: True', 'Simple strategies: False']
        ))
        
        self.register_parameter(ParameterDefinition(
            name='sizing_mode',
            type=str,
            default_value='adaptive',
            description='Position sizing algorithm to use',
            tier_level=ParameterTier.INTERMEDIATE,
            module='Dynamic Position Sizing',
            cli_name='sizing-mode',
            help_text='Algorithm for determining position sizes: adaptive (score-based), equal_weight, or score_weighted.',
            choices=['adaptive', 'equal_weight', 'score_weighted'],
            dependencies=['enable_dynamic_sizing'],
            examples=['adaptive (score-based)', 'equal_weight (balanced)', 'score_weighted (simple)'],
            use_cases=['Professional: adaptive', 'Conservative: equal_weight', 'Growth: score_weighted']
        ))
        
        self.register_parameter(ParameterDefinition(
            name='max_single_position',
            type=float,
            default_value=0.15,
            description='Maximum single position size for two-stage sizing',
            tier_level=ParameterTier.ADVANCED,
            module='Dynamic Position Sizing',
            cli_name='max-single-position',
            help_text='Two-stage sizing first caps positions at this level, then normalizes remainder.',
            validation_rules=[
                ValidationRule(
                    name='valid_percentage',
                    description='Must be between 0.01 and 0.5',
                    validator=lambda x: isinstance(x, (int, float)) and 0.01 <= x <= 0.5,
                    error_message='max_single_position must be between 0.01 and 0.5'
                )
            ],
            min_value=0.01,
            max_value=0.5,
            dependencies=['enable_dynamic_sizing'],
            examples=['0.1 (10% - conservative)', '0.15 (15% - balanced)', '0.2 (20% - aggressive)'],
            warnings=['Should be <= max_single_position_pct']
        ))
        
        self.register_parameter(ParameterDefinition(
            name='min_position_size',
            type=float,
            default_value=0.02,
            description='Minimum viable position size',
            tier_level=ParameterTier.ADVANCED,
            module='Dynamic Position Sizing',
            cli_name='min-position-size',
            help_text='Positions smaller than this will not be created. Prevents dust positions.',
            validation_rules=[
                ValidationRule(
                    name='valid_percentage',
                    description='Must be between 0.001 and 0.1',
                    validator=lambda x: isinstance(x, (int, float)) and 0.001 <= x <= 0.1,
                    error_message='min_position_size must be between 0.001 and 0.1'
                )
            ],
            min_value=0.001,
            max_value=0.1,
            dependencies=['enable_dynamic_sizing'],
            examples=['0.01 (1% - lenient)', '0.02 (2% - balanced)', '0.05 (5% - strict)'],
            warnings=['Higher values may prevent small but meaningful positions']
        ))
        
        # Continue with additional sizing parameters...
        
    def _register_lifecycle_management_parameters(self):
        """Register Module 4: Grace & Holding Period Management parameters"""
        # Implementation continues...
        pass
    
    def _register_core_asset_management_parameters(self):
        """Register Module 5: Core Asset Management parameters"""  
        # Implementation continues...
        pass
    
    def _register_system_parameters(self):
        """Register base system parameters"""
        # Implementation continues...
        pass 