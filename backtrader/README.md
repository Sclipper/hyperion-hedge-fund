# Backtrader Regime-Based Backtesting System

A comprehensive backtesting framework built on the backtrader library, designed to test dynamic trading strategies that adapt to market regimes using asset buckets and trending data.

## Features

- **Regime-Based Asset Selection**: Dynamically selects assets based on market regimes detected from macro research
- **Asset Bucket Management**: Organizes assets into themed buckets (Risk Assets, Defensives, etc.)
- **Database Integration**: Connects to your hedge fund database for macro research and trending asset data
- **Dynamic Rebalancing**: Automatically rebalances portfolio when market regimes change
- **Multi-Asset Support**: Test strategies across multiple asset classes simultaneously
- **Data Caching**: Intelligent caching system to avoid repeated API calls
- **Performance Analytics**: Comprehensive analysis including Sharpe ratio, drawdown, win rate
- **Flexible Strategy Framework**: Easy-to-extend regime-aware strategy classes
- **Results Export**: JSON and CSV export for further analysis
- **3-Year Backtests**: Default 3-year lookback period for robust testing

## Quick Start

### Regime-Based Backtesting (Recommended)
```bash
# Install dependencies
pip install -r requirements.txt

# Run regime-based backtest with Risk Assets and Defensives
python main.py regime --buckets "Risk Assets,Defensive Assets" --start-date 2021-01-01

# Run with daily rebalancing and high score threshold
python main.py regime --buckets "Growth,Value,Cyclicals" --rebalance-freq daily --min-score 0.7

# Test crypto and high-beta assets with custom timeframes
python main.py regime --buckets "High Beta,Gold" --timeframes "1d,4h" --max-assets 3
```

### Static Backtesting (Original Functionality)
```bash
# Run traditional static backtest
python main.py static --tickers AAPL,MSFT,NVDA --start-date 2021-01-01

# Plot results
python main.py static --tickers AAPL --start-date 2021-01-01 --plot
```

### Compare Backtest Results
```bash
# Compare multiple result files
python main.py compare --files "backtest_result1.json,backtest_result2.json"

# Compare and save to CSV
python main.py compare --files "result1.json,result2.json" --output comparison.csv
```

## Directory Structure

```
backtrader/
├── main.py                    # Main execution script with regime and static modes
├── strategies/                # Trading strategy implementations
│   ├── base_strategy.py      # Original static strategy class with SMA/RSI logic
│   ├── regime_strategy.py    # Dynamic regime-aware strategy
│   └── __init__.py
├── data/                     # Data management and regime detection
│   ├── data_manager.py       # Yahoo Finance data fetching with caching
│   ├── regime_detector.py    # Market regime detection from database
│   ├── asset_buckets.py      # Asset bucket management system
│   ├── database_integration.py # Database connection for macro research
│   ├── cache/                # Cached data files
│   └── __init__.py
├── utils/                    # Utilities and analysis
│   ├── config.py            # Configuration classes
│   ├── analyzers.py         # Performance analysis tools
│   ├── results.py           # Results saving and comparison
│   └── __init__.py
├── results/                  # Backtest results (JSON/CSV)
└── requirements.txt          # Python dependencies
```

## Regime Strategy with Position Manager

The advanced regime-aware strategy combines:
- **Dynamic Asset Selection**: Chooses assets based on current market regime from database
- **Bucket-Based Universe**: Selects from predefined asset buckets (Risk Assets, Defensives, etc.)
- **Trending Asset Filter**: Uses database scanner data to identify trending assets
- **Multi-Timeframe Technical Analysis**: Analyzes 1d, 4h, 1h timeframes using 20+ indicators (ta library)
- **Fundamental Analysis**: Balance sheet, profitability, valuation, and regime-fit scoring
- **Position Manager**: Sophisticated scoring system that tracks position changes over time
- **Dynamic Position Sizing**: Deterministic position sizing based on combined technical/fundamental scores
- **Position Score Tracking**: Saves and compares position scores to trigger rebalancing
- **Configurable Rebalancing**: Daily, weekly, or monthly rebalancing frequency
- **Risk Management**: 5% stop loss, 15% take profit on all positions

## Available Asset Buckets

- **Risk Assets**: Large cap stocks, growth names, tech leaders
- **Defensive Assets**: Bonds, utilities, defensive sectors
- **High Beta**: Volatile stocks, crypto assets, high-beta ETFs
- **Low Beta**: Low volatility ETFs, stable dividend stocks
- **Cyclicals**: Industrial, financial, consumer cyclical sectors
- **Growth/Value**: Style-based ETFs and factor tilts
- **International**: Developed and emerging market ETFs
- **Commodities**: Gold, energy, industrial, agricultural commodities
- **Fixed Income**: Treasuries, corporate bonds, high yield

## Command Line Options

### Regime Mode
```bash
--buckets "Risk Assets,Defensives"  # Comma-separated bucket names
--start-date 2021-01-01            # Start date (YYYY-MM-DD)
--end-date 2024-01-01              # End date (defaults to yesterday)
--max-assets 5                     # Maximum assets per rebalance period
--cash 100000                      # Starting cash amount
--commission 0.001                 # Commission rate (0.1% default)
--rebalance-freq daily             # Rebalancing frequency: daily, weekly, monthly
--min-score 0.6                    # Minimum position score threshold
--timeframes 1d,4h,1h              # Timeframes for technical analysis
```

### Static Mode  
```bash
--tickers AAPL,MSFT,NVDA          # Comma-separated list of tickers
--start-date 2021-01-01           # Start date (YYYY-MM-DD)
--end-date 2024-01-01             # End date (defaults to yesterday)
--cash 100000                     # Starting cash amount
--commission 0.001                # Commission rate (0.1% default)
--plot                            # Generate plots
```

## Performance Metrics

The system tracks:
- **Sharpe Ratio**: Risk-adjusted returns
- **Total/Average Returns**: Absolute and average performance
- **Maximum Drawdown**: Worst peak-to-trough decline
- **Win Rate**: Percentage of profitable trades
- **Profit Factor**: Ratio of average win to average loss
- **SQN**: System Quality Number
- **Trade Statistics**: Total trades, average win/loss

## Adding New Assets

The data manager supports any ticker available on Yahoo Finance. Simply add tickers to the command line:

```bash
python main.py --tickers AAPL,MSFT,NVDA,TSLA,GOOGL,AMZN,META
```

Data is automatically cached to avoid repeated downloads.

## ⚠️ CRITICAL: Required Real Data Sources

**NO MOCK DATA IS USED IN THIS SYSTEM** - All data sources must be real and properly configured:

### **1. Database Requirements (PostgreSQL)**
The system requires your existing hedge fund database with these tables populated:

#### **`research` table:**
- **`regime`**: Must contain real regime data (`Goldilocks`, `Deflation`, `Inflation`, `Reflation`)
- **`buckets`**: JSON array of asset buckets for each regime
- **`created_at`**: Timestamp for historical regime lookup
- **Status**: ✅ Connected to your existing database

#### **`scanner_historical` table:**
- **`ticker`**: Asset symbol
- **`market`**: Market type (`trending`, `ranging`)
- **`confidence`**: Confidence score for trending/ranging classification
- **`date`**: Historical date for the scan data
- **Status**: ✅ Connected to your existing database

### **2. Financial Data APIs (NOT IMPLEMENTED)**
The fundamental analyzer requires real financial data sources:

#### **Required Data:**
- Balance sheet data (debt, equity, assets, liabilities)
- Income statement data (revenue, net income, operating margins)
- Cash flow data (free cash flow, operating cash flow)
- Market data (market cap, price performance, volatility)

#### **Integration Points:**
- `position/fundamental_analyzer.py:87-97` - Financial data integration
- `position/fundamental_analyzer.py:110-118` - Market data integration
- **Status**: ❌ **REQUIRES IMPLEMENTATION** - Currently returns empty data

#### **Recommended Sources:**
- Your existing `src/tools/api.py` financial APIs
- Alpha Vantage, Yahoo Finance, or similar financial data providers
- Real-time market data feeds

### **3. Multi-Timeframe Price Data (NOT IMPLEMENTED)**
Technical analysis requires real multi-timeframe data:

#### **Required Timeframes:**
- **1-hour data**: For short-term technical analysis
- **4-hour data**: For medium-term momentum analysis  
- **Daily data**: ✅ Available via Yahoo Finance

#### **Integration Points:**
- `position/position_manager.py:225-236` - Hourly/4h data fetching
- **Status**: ❌ **REQUIRES IMPLEMENTATION** - Currently returns None

#### **Recommended Sources:**
- Your existing price data APIs
- Professional market data feeds (Bloomberg, Refinitiv)
- Cryptocurrency exchanges for crypto assets
- Forex brokers for FX data

### **4. Data Validation**
The system will **FAIL GRACEFULLY** when real data is not available:
- **Regime data missing**: Strategy cannot proceed (returns None regime)
- **Financial data missing**: Fundamental score defaults to 0.5
- **Multi-timeframe data missing**: Technical analysis uses only daily data
- **Trending data missing**: Uses all available assets instead of filtered trending

### **5. Implementation Status Summary**
| Data Source | Status | Impact |
|-------------|--------|---------|
| Database (regime/buckets) | ✅ Connected | Strategy works |
| Database (trending assets) | ✅ Connected | Asset filtering works |
| Financial APIs | ❌ Missing | Fundamental analysis disabled |
| Multi-timeframe data | ❌ Missing | Technical analysis limited |
| Daily price data | ✅ Yahoo Finance | Basic strategy works |

**NEXT STEPS:** Implement missing data sources or accept limited functionality without fundamental analysis and multi-timeframe technical analysis.