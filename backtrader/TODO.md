# Backtrader Enhancement TODOs

## Add Analysis Disable Functionality

**Priority: High**  
**Status: Pending**  
**Estimated Effort: Medium**

### Objective
Add functionality to the Position Manager to allow disabling technical analysis, fundamental analysis, or both components independently. This will provide flexibility for different trading strategies and use cases.

### Current State Analysis
- Position Manager currently always attempts to use both technical and fundamental analyzers
- Fixed weights: `technical_weight = 0.6`, `fundamental_weight = 0.4`
- Scoring logic in `_score_single_asset()` method always combines both scores
- No configuration options to disable either component

### Required Changes

#### 1. Position Manager Configuration (`position/position_manager.py`)
- Add initialization parameters:
  - `enable_technical_analysis: bool = True`
  - `enable_fundamental_analysis: bool = True`
- Update constructor to accept these parameters
- Add validation to ensure at least one analysis type is enabled

#### 2. Scoring Logic Updates (`_score_single_asset()` method)
- **Both Enabled (Default)**: Current behavior with configurable weights
- **Technical Only**: `combined_score = technical_score`, skip fundamental analysis
- **Fundamental Only**: `combined_score = fundamental_score`, skip technical analysis  
- **Both Disabled**: Raise configuration error or return neutral score (0.5)

#### 3. Weight Adjustment Logic
- When fundamental is disabled: `effective_technical_weight = 1.0`
- When technical is disabled: `effective_fundamental_weight = 1.0`
- Maintain current fallback behavior for missing data

#### 4. Strategy Integration (`strategies/regime_strategy.py`)
- Add parameters to strategy constructor to pass through to Position Manager
- Update command line argument parsing in `main.py`

#### 5. Command Line Interface (`main.py`)
- Add CLI arguments:
  - `--disable-technical`: Disable technical analysis
  - `--disable-fundamental`: Disable fundamental analysis
  - `--analysis-weights`: Allow custom technical/fundamental weights

#### 6. Configuration Validation
- Prevent both being disabled simultaneously
- Warn users about crypto assets when fundamental analysis is enabled (limited data)
- Provide helpful error messages for invalid configurations

### Implementation Steps
1. Update Position Manager constructor and add validation
2. Modify `_score_single_asset()` method scoring logic
3. Add command line arguments to main.py
4. Update regime strategy to pass through configuration
5. Add tests for different configuration combinations
6. Update documentation and examples

### Benefits
- **Flexibility**: Support pure technical or fundamental strategies
- **Performance**: Skip expensive analysis when not needed  
- **Crypto Compatibility**: Better support for crypto assets (technical-only)
- **Testing**: Easier to isolate and test individual components
- **User Choice**: Match user's analysis preferences/expertise

### Use Cases
- **Technical Traders**: Disable fundamental analysis for pure chart-based strategies
- **Value Investors**: Disable technical analysis for pure fundamental strategies  
- **Crypto Focus**: Disable fundamental analysis for crypto-heavy portfolios
- **Performance Testing**: Compare technical vs fundamental effectiveness
- **Data Limitations**: Graceful fallback when one data source is unavailable

### Notes
- Maintain backward compatibility with existing configurations
- Ensure proper error handling and user feedback
- Consider adding analysis type indicators to output/logs
- May want to add weight validation (sum to 1.0) in future iterations 