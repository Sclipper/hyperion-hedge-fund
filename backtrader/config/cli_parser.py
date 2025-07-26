"""
Enhanced CLI Parser for Configuration Management

Provides tiered CLI interface with:
- Progressive complexity disclosure (Basic → Expert)
- Configuration management commands
- Organized parameter groups by module
- Built-in help and validation
"""

import argparse
from typing import Dict, List, Optional, Any
from .parameter_registry import ParameterRegistry, ParameterDefinition
from .data_models import StrategyConfiguration


class TieredArgumentParser:
    """Multi-tiered CLI argument parser with progressive disclosure"""
    
    def __init__(self, registry: ParameterRegistry):
        self.registry = registry
        self.parser = argparse.ArgumentParser(
            description="Hedge Fund Backtesting Framework - Enhanced Configuration Management",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=self._get_epilog_text()
        )
        self._setup_commands()
    
    def _get_epilog_text(self) -> str:
        """Get help epilog with usage examples"""
        return """
Examples:
  # Basic backtesting (Tier 1 - Beginner)
  python main.py basic --buckets "Risk Assets,Defensives" --max-total-positions 5
  
  # Advanced backtesting (Tier 3 - Advanced)  
  python main.py advanced --enable-bucket-diversification --enable-grace-periods
  
  # Expert mode (Tier 4 - Professional)
  python main.py expert --enable-core-assets --core-override-threshold 0.96
  
  # Use strategy preset
  python main.py preset --preset-name conservative
  
  # Configuration management
  python main.py config build --tier 2
  python main.py config import --file my_strategy.yaml
  python main.py config export --output current_setup.yaml

Tiers:
  Tier 1 (Basic):        Essential parameters for beginners
  Tier 2 (Intermediate): Enhanced strategy features  
  Tier 3 (Advanced):     Risk management and lifecycle
  Tier 4 (Expert):       Professional institutional features
        """
    
    def _setup_commands(self):
        """Setup all CLI commands and subcommands"""
        subparsers = self.parser.add_subparsers(dest='mode', help='Execution mode')
        
        # Tiered backtesting modes
        self._add_basic_mode(subparsers)
        self._add_intermediate_mode(subparsers)
        self._add_advanced_mode(subparsers)
        self._add_expert_mode(subparsers)
        
        # Preset mode
        self._add_preset_mode(subparsers)
        
        # Configuration management
        self._add_config_management(subparsers)
        
        # Legacy regime mode (backward compatibility)
        self._add_legacy_regime_mode(subparsers)
    
    def _add_basic_mode(self, subparsers):
        """Add basic mode (Tier 1) with essential parameters only"""
        basic_parser = subparsers.add_parser(
            'basic',
            help='Basic backtesting with essential parameters (Tier 1)',
            description='Basic mode provides a simplified interface with only the most essential parameters.'
        )
        
        self._add_tier_arguments(basic_parser, tier_level=1, mode_name="Basic")
    
    def _add_intermediate_mode(self, subparsers):
        """Add intermediate mode (Tier 2) with enhanced features"""
        intermediate_parser = subparsers.add_parser(
            'intermediate', 
            help='Enhanced backtesting with strategy features (Tier 2)',
            description='Intermediate mode adds strategy configuration and analysis options.'
        )
        
        self._add_tier_arguments(intermediate_parser, tier_level=2, mode_name="Intermediate")
    
    def _add_advanced_mode(self, subparsers):
        """Add advanced mode (Tier 3) with risk management"""
        advanced_parser = subparsers.add_parser(
            'advanced',
            help='Advanced backtesting with risk management (Tier 3)', 
            description='Advanced mode includes sophisticated risk management and lifecycle features.'
        )
        
        self._add_tier_arguments(advanced_parser, tier_level=3, mode_name="Advanced")
    
    def _add_expert_mode(self, subparsers):
        """Add expert mode (Tier 4) with all professional features"""
        expert_parser = subparsers.add_parser(
            'expert',
            help='Expert mode with all professional features (Tier 4)',
            description='Expert mode provides access to all institutional-grade features.'
        )
        
        self._add_tier_arguments(expert_parser, tier_level=4, mode_name="Expert")
    
    def _add_preset_mode(self, subparsers):
        """Add preset mode for predefined strategies"""
        preset_parser = subparsers.add_parser(
            'preset',
            help='Run with predefined strategy preset',
            description='Use predefined strategy configurations optimized for different use cases.'
        )
        
        preset_parser.add_argument(
            '--preset-name', 
            required=True,
            choices=['conservative', 'aggressive', 'adaptive', 'institutional'],
            help='Strategy preset to use'
        )
        
        # Allow override of key parameters
        preset_parser.add_argument('--buckets', help='Override buckets')
        preset_parser.add_argument('--start-date', help='Override start date')
        preset_parser.add_argument('--end-date', help='Override end date')
        preset_parser.add_argument('--cash', type=float, help='Override cash amount')
        preset_parser.add_argument('--plot', action='store_true', help='Plot results')
    
    def _add_config_management(self, subparsers):
        """Add configuration management commands"""
        config_parser = subparsers.add_parser(
            'config',
            help='Configuration management',
            description='Manage, validate, and share strategy configurations.'
        )
        
        config_subparsers = config_parser.add_subparsers(dest='config_action', help='Configuration action')
        
        # Build command
        build_parser = config_subparsers.add_parser(
            'build', 
            help='Interactive configuration builder',
            description='Build configuration interactively with step-by-step guidance.'
        )
        build_parser.add_argument('--tier', type=int, choices=[1,2,3,4], default=1,
                                help='Configuration complexity tier (1=Basic, 4=Expert)')
        build_parser.add_argument('--output', help='Save configuration to file')
        build_parser.add_argument('--format', choices=['yaml', 'json'], default='yaml',
                                help='Output file format')
        
        # Export command
        export_parser = config_subparsers.add_parser(
            'export',
            help='Export current configuration',
            description='Export current CLI configuration to a file.'
        )
        export_parser.add_argument('--output', required=True, help='Output file path')
        export_parser.add_argument('--format', choices=['yaml', 'json'], default='yaml',
                                 help='Output file format')
        export_parser.add_argument('--tier', type=int, choices=[1,2,3,4], default=3,
                                 help='Configuration tier level to export')
        
        # Import command
        import_parser = config_subparsers.add_parser(
            'import',
            help='Import and run configuration',
            description='Import configuration from file and run backtest.'
        )
        import_parser.add_argument('--file', required=True, help='Configuration file path')
        import_parser.add_argument('--validate-only', action='store_true',
                                 help='Only validate configuration, don\'t run')
        import_parser.add_argument('--plot', action='store_true', help='Plot results')
        
        # Validate command
        validate_parser = config_subparsers.add_parser(
            'validate',
            help='Validate configuration file',
            description='Validate configuration file without running backtest.'
        )
        validate_parser.add_argument('--file', required=True, help='Configuration file to validate')
        validate_parser.add_argument('--verbose', action='store_true', help='Show detailed validation results')
        
        # Info command
        info_parser = config_subparsers.add_parser(
            'info',
            help='Show configuration information',
            description='Show information about parameters, tiers, and presets.'
        )
        info_parser.add_argument('--parameter', help='Show detailed parameter information')
        info_parser.add_argument('--tier', type=int, choices=[1,2,3,4], help='Show tier information')
        info_parser.add_argument('--presets', action='store_true', help='Show available presets')
    
    def _add_legacy_regime_mode(self, subparsers):
        """Add legacy regime mode for backward compatibility"""
        regime_parser = subparsers.add_parser(
            'regime',
            help='Legacy regime-based backtest (backward compatibility)',
            description='Legacy interface - consider using tiered modes (basic/advanced/expert) instead.'
        )
        
        # Add all current parameters for full backward compatibility
        self._add_tier_arguments(regime_parser, tier_level=4, mode_name="Legacy")
        
        # Mark as legacy
        regime_parser.add_argument('--legacy-mode', action='store_true', default=True, 
                                 help=argparse.SUPPRESS)  # Hidden argument
    
    def _add_tier_arguments(self, parser: argparse.ArgumentParser, tier_level: int, mode_name: str):
        """Add arguments for specific tier level with organized groups"""
        
        # Get parameters for this tier
        parameters = self.registry.get_parameters_by_tier(tier_level)
        
        # Group parameters by module for better organization
        module_groups = self._group_parameters_by_module(parameters)
        
        # Add argument groups for each module
        for module_name, module_params in module_groups.items():
            if not module_params:  # Skip empty groups
                continue
                
            # Create argument group for this module
            group_title = f"{module_name} ({len(module_params)} parameters)"
            group = parser.add_argument_group(group_title)
            
            # Add parameters to group
            for param in module_params:
                self._add_parameter_argument(group, param)
        
        # Add common output arguments
        output_group = parser.add_argument_group("Output Options")
        output_group.add_argument('--plot', action='store_true', help='Plot backtest results')
        output_group.add_argument('--save-results', help='Save results to file')
        output_group.add_argument('--verbose', action='store_true', help='Verbose output')
    
    def _group_parameters_by_module(self, parameters: List[ParameterDefinition]) -> Dict[str, List[ParameterDefinition]]:
        """Group parameters by their module"""
        groups = {
            'System Configuration': [],
            'Core Rebalancer Engine': [],
            'Bucket Diversification': [],
            'Dynamic Position Sizing': [],
            'Lifecycle Management': [],
            'Core Asset Management': []
        }
        
        # Handle system parameters specially
        system_params = ['buckets', 'start_date', 'end_date', 'cash', 'commission', 
                        'rebalance_frequency', 'min_trending_confidence', 'timeframes', 'plot_results']
        
        for param in parameters:
            # Map to system configuration
            if param.name in system_params:
                groups['System Configuration'].append(param)
            else:
                # Use module from parameter definition
                module = param.module
                if module in groups:
                    groups[module].append(param)
                else:
                    # Default to Core Rebalancer Engine for unknown modules
                    groups['Core Rebalancer Engine'].append(param)
        
        # Remove empty groups
        return {k: v for k, v in groups.items() if v}
    
    def _add_parameter_argument(self, group: argparse._ArgumentGroup, param: ParameterDefinition):
        """Add a single parameter as CLI argument"""
        kwargs = {
            'help': self._format_help_text(param),
            'dest': param.name
        }
        
        # Set default value
        if param.default_value is not None:
            kwargs['default'] = param.default_value
        
        # Handle different parameter types
        if param.type == bool:
            if param.default_value:
                # For boolean True defaults, add --no-X flag to disable
                flag_name = f'--no-{param.cli_name}'
                kwargs['action'] = 'store_false'
            else:
                # For boolean False defaults, add --X flag to enable
                flag_name = f'--{param.cli_name}'
                kwargs['action'] = 'store_true'
            
            group.add_argument(flag_name, **kwargs)
            
        else:
            # For non-boolean parameters
            kwargs['type'] = param.type
            
            # Add choices if specified
            if param.choices:
                kwargs['choices'] = param.choices
            
            # Add metavar for better help formatting
            if param.type == int:
                kwargs['metavar'] = 'N'
            elif param.type == float:
                kwargs['metavar'] = 'X.X'
            elif param.type == str and param.choices:
                kwargs['metavar'] = f"{{{','.join(map(str, param.choices))}}}"
            elif param.type == str:
                kwargs['metavar'] = 'STR'
            
            group.add_argument(f'--{param.cli_name}', **kwargs)
    
    def _format_help_text(self, param: ParameterDefinition) -> str:
        """Format help text for parameter"""
        help_text = param.help_text or param.description
        
        # Add default value info
        if param.default_value is not None:
            if param.type == bool:
                default_text = "enabled" if param.default_value else "disabled" 
                help_text += f" (default: {default_text})"
            else:
                help_text += f" (default: {param.default_value})"
        
        # Add range info for numeric types
        if param.min_value is not None or param.max_value is not None:
            if param.min_value is not None and param.max_value is not None:
                help_text += f" [range: {param.min_value}-{param.max_value}]"
            elif param.min_value is not None:
                help_text += f" [min: {param.min_value}]"
            elif param.max_value is not None:
                help_text += f" [max: {param.max_value}]"
        
        # Add tier info
        tier_names = {1: "Basic", 2: "Intermediate", 3: "Advanced", 4: "Expert"}
        tier_name = tier_names.get(param.tier_level.value, "Unknown")
        help_text += f" [Tier {param.tier_level.value}: {tier_name}]"
        
        return help_text
    
    def parse_args(self, args=None) -> argparse.Namespace:
        """Parse arguments and return namespace"""
        return self.parser.parse_args(args)
    
    def print_help(self):
        """Print help message"""
        self.parser.print_help()
    
    def get_tier_help(self, tier_level: int) -> str:
        """Get help text for specific tier"""
        tier_names = {
            1: "Basic - Essential parameters for beginners",
            2: "Intermediate - Enhanced strategy features", 
            3: "Advanced - Risk management and lifecycle",
            4: "Expert - Professional institutional features"
        }
        
        params = self.registry.get_parameters_by_tier(tier_level)
        param_count = len(params)
        
        help_text = f"\nTier {tier_level}: {tier_names.get(tier_level, 'Unknown')}\n"
        help_text += f"Parameters: {param_count}\n\n"
        
        # Group by module
        module_groups = self._group_parameters_by_module(params)
        
        for module, module_params in module_groups.items():
            help_text += f"{module}:\n"
            for param in module_params[:5]:  # Show first 5 parameters
                help_text += f"  --{param.cli_name:<30} {param.description}\n"
            if len(module_params) > 5:
                help_text += f"  ... and {len(module_params) - 5} more\n"
            help_text += "\n"
        
        return help_text


def create_cli_parser() -> TieredArgumentParser:
    """Factory function to create configured CLI parser"""
    registry = ParameterRegistry()
    return TieredArgumentParser(registry) 