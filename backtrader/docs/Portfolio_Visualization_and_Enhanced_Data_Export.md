# Portfolio Visualization and Enhanced Data Export Implementation

This document outlines the implementation plan for adding comprehensive portfolio visualization and enhanced data export capabilities to the hedge fund backtesting framework.

## 🎯 Overview

### Current State Analysis
After examining the existing codebase, the current data export functionality includes:

**Existing Export Capabilities:**
- `utils/results.py`: Exports JSON summary and basic CSV trades data
- `utils/analyzers.py`: Backtrader analyzers for performance metrics
- `monitoring/event_store.py`: Detailed SQLite event logging for audit trails
- Basic performance metrics: Sharpe ratio, returns, drawdown, trade statistics

**Current Data Flow:**
```
Backtest Run → Analyzers → results.py → JSON + Basic CSV
                        ↘ monitoring → SQLite Event Log
```

### Proposed Enhancements

**New Capabilities:**
1. **Portfolio Value Visualization**: Time-series charts of portfolio performance
2. **Enhanced CSV Export**: Comprehensive trading decisions dataset  
3. **Visual Dashboard**: Multi-panel performance visualization
4. **Extended Data Export**: Portfolio composition, asset weights, regime data
5. **Comparative Analysis**: Multi-backtest comparison visualizations

---

## 📈 Portfolio Visualization Features

### 1. Core Portfolio Value Chart
**Primary Visualization:**
- **X-axis**: Time (daily granularity)
- **Y-axis**: Portfolio value ($)
- **Main Line**: Total portfolio value over time
- **Benchmark**: Optional benchmark comparison (SPY, etc.)
- **Drawdown Shading**: Red shaded areas for drawdown periods

### 2. Secondary Visualizations
**Panel 2 - Asset Allocation Over Time:**
- **Type**: Stacked area chart
- **Shows**: Portfolio composition by asset over time
- **Colors**: Distinct colors per asset
- **Tooltip**: Asset name, allocation %, dollar value

**Panel 3 - Performance Metrics:**
- **Type**: Multiple subplot panels
- **Metrics**: 
  - Rolling Sharpe ratio (30-day window)
  - Cumulative returns vs benchmark
  - Rolling volatility
  - Regime indicators (background coloring)

**Panel 4 - Trading Activity:**
- **Type**: Scatter plot overlay
- **Green Dots**: Buy signals
- **Red Dots**: Sell signals
- **Size**: Proportional to trade size
- **Hover**: Asset, date, action, amount

### 3. Interactive Features
- **Zoom**: Time range selection
- **Crosshair**: Exact values on hover
- **Toggle**: Show/hide individual assets
- **Export**: Save chart as PNG/SVG

---

## 📊 Enhanced Data Export Specification

### 1. Portfolio Timeline CSV
**Filename Format:** `portfolio_timeline_{timestamp}.csv`
**Columns:**
```csv
date,portfolio_value,cash,total_positions,regime,regime_confidence,benchmark_value,daily_return,cumulative_return,drawdown_pct,sharpe_30d
2024-01-01,100000.00,5000.00,8,Goldilocks,0.85,100000.00,0.0000,0.0000,0.00,0.000
2024-01-02,101250.00,4800.00,8,Goldilocks,0.87,100150.00,0.0125,0.0125,-0.12,0.045
```

### 2. Position Changes CSV
**Filename Format:** `position_changes_{timestamp}.csv`
**Columns:**
```csv
date,asset,action,quantity,price,value,reason,score_before,score_after,bucket,regime
2024-01-02,AAPL,BUY,100,150.25,15025.00,High score asset: 0.857 > 0.65 threshold,0.000,0.857,Risk Assets,Goldilocks
2024-01-15,MSFT,SELL,50,420.50,21025.00,Grace period expired,0.582,0.000,Risk Assets,Goldilocks
2024-01-20,GOOGL,HOLD,75,140.75,10556.25,Position maintained,0.724,0.731,Risk Assets,Goldilocks
```

### 3. Asset Composition CSV
**Filename Format:** `asset_composition_{timestamp}.csv`
**Columns:**
```csv
date,asset,shares,price,market_value,weight_pct,score,bucket,days_held,is_core_asset
2024-01-02,AAPL,100,150.25,15025.00,14.85,0.857,Risk Assets,1,false
2024-01-02,MSFT,45,420.50,18922.50,18.71,0.743,Risk Assets,15,true
```

### 4. Regime Analysis CSV
**Filename Format:** `regime_analysis_{timestamp}.csv`
**Columns:**
```csv
date,regime,confidence,stability,duration_days,active_buckets,portfolio_return_in_regime
2024-01-01,Goldilocks,0.85,0.78,45,"Risk Assets,Growth Assets",12.45
2024-02-15,Deflation,0.72,0.65,12,"Defensive Assets,Treasuries",-2.31
```

---

## 🏗️ Implementation Plan

### Phase 1: Data Collection Enhancement
**Target Files:** `utils/analyzers.py`, `utils/results.py`

**Changes Required:**

1. **Enhanced Analyzers (`utils/analyzers.py`):**
```python
# Add new analyzers to setup_analyzers()
cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='timereturn', timeframe=bt.TimeFrame.Days)
cerebro.addanalyzer(bt.analyzers.PositionsValue, _name='positions')
cerebro.addanalyzer(CustomPortfolioTracker, _name='portfolio_tracker')
cerebro.addanalyzer(CustomPositionTracker, _name='position_tracker')
```

2. **New Custom Analyzers:**
```python
class CustomPortfolioTracker(bt.Analyzer):
    """Track daily portfolio value, composition, and metrics"""
    
class CustomPositionTracker(bt.Analyzer):
    """Track all position changes with detailed context"""
```

**Testing:** Verify analyzers collect data without affecting backtest performance.

### Phase 2: Visualization Engine
**New File:** `utils/visualizer.py`

**Dependencies:** 
- `matplotlib` for static charts
- `plotly` for interactive visualizations
- `seaborn` for enhanced styling

**Core Functions:**
```python
def create_portfolio_chart(portfolio_data: pd.DataFrame, benchmark_data: pd.DataFrame = None) -> Figure
def create_allocation_chart(composition_data: pd.DataFrame) -> Figure  
def create_performance_dashboard(all_data: Dict[str, pd.DataFrame]) -> Figure
def save_visualizations(charts: List[Figure], output_dir: str, filename_prefix: str) -> List[str]
```

**Testing:** Generate charts with mock data to verify layout and functionality.

### Phase 3: Enhanced Data Export
**Target File:** `utils/results.py`

**New Functions:**
```python
def export_portfolio_timeline(strategy, output_dir: str) -> str
def export_position_changes(strategy, output_dir: str) -> str  
def export_asset_composition(strategy, output_dir: str) -> str
def export_regime_analysis(strategy, output_dir: str) -> str
def create_enhanced_export_package(strategy, tickers, start_date, end_date, output_dir="results") -> Dict[str, str]
```

**Enhanced `save_results()` function:**
```python
def save_results(strategy, tickers, start_date, end_date, results_dir="results", enable_visualization=True):
    # Existing JSON/CSV export
    results_data = extract_results(strategy, tickers, start_date, end_date)
    
    # New: Enhanced CSV exports
    csv_files = create_enhanced_export_package(strategy, tickers, start_date, end_date, results_dir)
    
    # New: Visualization generation
    if enable_visualization:
        chart_files = generate_portfolio_visualizations(strategy, results_dir)
        results_data['visualizations'] = chart_files
    
    results_data['data_exports'] = csv_files
    return results_data
```

**Testing:** Verify CSV files contain expected data and format correctly.

### Phase 4: Integration with Event System
**Target Files:** `monitoring/event_store.py`, `utils/results.py`

**Enhanced Event Data Extraction:**
```python
def extract_trading_decisions_from_events(session_id: str) -> pd.DataFrame:
    """Extract position decisions from event log for CSV export"""

def correlate_events_with_portfolio_timeline(strategy, event_store: EventStore) -> pd.DataFrame:
    """Merge portfolio value data with event context"""
```

**Testing:** Verify event data correctly supplements backtest analyzer data.

### Phase 5: CLI Integration
**Target File:** `main.py`

**New CLI Options:**
```bash
--enable-visualization     # Generate portfolio charts (default: true)
--export-format            # csv,json,charts,all (default: all)  
--chart-style              # static,interactive (default: interactive)
--benchmark                # Benchmark ticker for comparison (default: SPY)
```

**Integration Points:**
```python
def run_regime_backtest(..., enable_visualization=True, export_format='all', benchmark_ticker='SPY'):
    # Existing backtest logic
    results = cerebro.run()
    
    # Enhanced export with visualization
    save_results(results[0], all_possible_assets, start_date, end_date, 
                enable_visualization=enable_visualization,
                export_format=export_format,
                benchmark_ticker=benchmark_ticker)
```

**Testing:** Verify CLI options work correctly and maintain backward compatibility.

---

## 📁 File Structure Changes

### New Files to Create:
```
utils/
├── visualizer.py              # Portfolio visualization engine
├── data_exporters.py          # Enhanced CSV export functions
└── chart_templates.py         # Reusable chart configurations

docs/
└── Portfolio_Visualization_and_Enhanced_Data_Export.md  # This document

config/
└── visualization_config.py    # Chart styling and layout configurations
```

### Modified Files:
```
utils/
├── analyzers.py               # Add custom analyzers
├── results.py                 # Enhanced export functions
└── requirements.txt           # Add matplotlib, plotly, seaborn

main.py                        # CLI integration for visualization options
```

### Output Directory Structure:
```
results/
├── backtest_assets_20240127_143022/
│   ├── summary.json                    # Existing summary
│   ├── portfolio_timeline.csv         # New: Daily portfolio values
│   ├── position_changes.csv           # New: All trading decisions  
│   ├── asset_composition.csv          # New: Daily holdings
│   ├── regime_analysis.csv            # New: Regime transition data
│   ├── portfolio_performance.html     # New: Interactive dashboard
│   ├── portfolio_chart.png           # New: Static portfolio chart
│   └── allocation_evolution.png       # New: Asset allocation over time
```

---

## 🧪 Testing Strategy

### Phase-by-Phase Testing:

**Phase 1 Testing:**
```bash
# Verify new analyzers don't break existing functionality
python main.py basic --start-date 2023-01-01 --cash 100000
# Check that results.json still generates correctly
```

**Phase 2 Testing:**
```bash  
# Test visualization with mock data
python -c "from utils.visualizer import create_portfolio_chart; create_portfolio_chart(mock_data)"
```

**Phase 3 Testing:**
```bash
# Verify enhanced CSV exports
python main.py intermediate --start-date 2023-01-01 --export-format csv
# Validate CSV file formats and data completeness
```

**Phase 4 Testing:**
```bash
# Test event system integration
python main.py advanced --start-date 2023-01-01 --enable-grace-periods
# Verify event data correlates with trading decisions CSV
```

**Phase 5 Testing:**
```bash
# Full integration test
python main.py expert --start-date 2023-01-01 --enable-visualization --benchmark SPY
# Verify all output files generate correctly
```

### Incremental Functionality Validation:
- Each phase maintains existing functionality
- New features are opt-in via CLI flags
- Backward compatibility with existing results format
- Performance impact monitoring (visualization should not slow backtests)

---

## 📋 Data Requirements & Dependencies

### New Python Dependencies:
```requirements.txt
matplotlib>=3.7.0          # Static chart generation
plotly>=5.17.0            # Interactive visualizations  
seaborn>=0.12.0           # Enhanced chart styling
kaleido>=0.2.1            # Static export for plotly charts
```

### Data Sources Integration:
- **Backtrader Analyzers**: Portfolio value, trade data, performance metrics
- **Event Store**: Detailed trading decisions, regime transitions, protection system actions
- **Strategy Parameters**: Asset buckets, configuration settings, protection thresholds
- **Market Data**: Benchmark comparison data (SPY, etc.)

### Performance Considerations:
- **Visualization Generation**: Optional via CLI flag (default: enabled)
- **Memory Usage**: Stream large datasets to CSV rather than loading in memory
- **Chart Rendering**: Use efficient plotting libraries with caching
- **File Size Management**: Compress large datasets, optional high-resolution charts

---

## 🚀 Expected Benefits

### For Users:
1. **Visual Portfolio Analysis**: Immediately see portfolio performance trends
2. **Detailed Trade Review**: CSV data for external analysis (Excel, Python, R)
3. **Regime Impact Visualization**: See how market regimes affect strategy performance
4. **Comparative Analysis**: Easily compare multiple backtest runs
5. **Professional Reporting**: Export-ready charts for presentations

### For Development:
1. **Enhanced Debugging**: Visual correlation between events and performance
2. **Strategy Validation**: Comprehensive data export for strategy research
3. **Performance Monitoring**: Visual indicators of protection system effectiveness
4. **Regime Analysis**: Data-driven regime detection validation

### Data Export Summary:
- **Portfolio Timeline**: Daily portfolio values and metrics
- **Position Changes**: Complete trading decision history
- **Asset Composition**: Daily holdings and weights
- **Regime Analysis**: Market regime transitions and performance impact
- **Visualizations**: Interactive and static charts for analysis

This implementation provides comprehensive portfolio analysis capabilities while maintaining the system's existing functionality and performance characteristics.