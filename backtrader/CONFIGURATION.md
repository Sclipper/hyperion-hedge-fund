# Configuration Guide - Hedge Fund Backtesting Framework

This comprehensive guide explains all configuration options, settings hierarchy, and provides templates for running the backtesting system.

## 🚀 Quick Start

### **Basic Backtest Run**
```bash
# Simplest configuration - uses built-in defaults
python main.py basic --start-date 2021-01-01 --cash 100000

# With asset buckets (regime-based selection)
python main.py basic --start-date 2021-01-01 --cash 100000 \
  --buckets "Risk Assets,Defensive Assets"
```

### **Intermediate Backtest**
```bash
# Enhanced strategy features
python main.py intermediate --start-date 2021-01-01 --cash 500000 \
  --max-total-positions 8 --rebalance-frequency weekly \
  --enable-bucket-diversification
```

### **Advanced Professional Setup**
```bash
# Full protection systems and risk management
python main.py advanced --start-date 2021-01-01 --cash 1000000 \
  --enable-core-assets --enable-grace-periods \
  --enable-whipsaw-protection --max-total-positions 12
```

---

## 📋 Configuration Hierarchy

The system uses multiple configuration layers with the following priority (highest to lowest):

### **1. Command Line Arguments (Highest Priority)**
Direct CLI parameters override all other settings:
```bash
python main.py advanced --cash 1000000 --max-total-positions 15
```

### **2. Configuration Files (.yaml/.json)**
Structured configuration files for complex setups:
```bash
# Export current CLI setup to file
python -m config.cli_parser --tier advanced --export-config my_strategy.yaml

# Run with configuration file
python main.py config --file my_strategy.yaml
```

### **3. Strategy Presets**
Built-in professional configurations:
```bash
python main.py preset --preset-name institutional --start-date 2021-01-01
```

### **4. Environment Variables (.env)**
Database connections and API keys:
```bash
# Database configuration
DATABASE_URL='postgresql://user:password@localhost:5432/hedge_fund'

# Alternative individual components
DB_HOST='localhost'
DB_PORT='5432'
DB_NAME='hedge_fund'
DB_USER='postgres'
DB_PASSWORD='your_password'
```

### **5. System Defaults (Lowest Priority)**
Built-in fallback values for all parameters.

---

## 🎯 Asset Bucket System

**Important**: Asset buckets are NOT specified manually - they are **dynamically selected based on market regime detection**. The `--buckets` parameter defines which bucket categories the system can choose from.

### **How Regime-Based Selection Works**
```python
# The system automatically detects market regime
current_regime = 'Goldilocks'  # Detected automatically

# Then selects appropriate buckets for that regime
if current_regime == 'Goldilocks':
    active_buckets = ['Risk Assets', 'Growth Assets']
elif current_regime == 'Deflation':
    active_buckets = ['Defensive Assets', 'Treasuries', 'Gold']
elif current_regime == 'Inflation':
    active_buckets = ['Commodities', 'Energy', 'Value Assets']
```

### **Available Asset Bucket Categories**

**Core Equity**
- `Risk Assets`: Large cap growth, tech leaders, high-momentum stocks
- `Defensive Assets`: Utilities, consumer staples, dividend aristocrats  
- `Value Assets`: Deep value stocks, contrarian opportunities
- `Growth Assets`: High-growth companies, emerging technologies

**Style & Factor**
- `High Beta`: Volatile stocks, leverage plays, high-beta ETFs
- `Low Beta`: Low volatility ETFs, stable dividend stocks
- `Cyclicals`: Industrial, financial, consumer cyclical sectors
- `Quality`: High ROE, low debt, stable earnings companies

**Geographic & Thematic**
- `International`: Developed markets, emerging markets, regional ETFs
- `Commodities`: Gold, energy, industrial metals, agriculture
- `Fixed Income`: Treasuries, corporate bonds, high yield
- `Alternatives`: REITs, infrastructure, commodity producers

### **Bucket Selection Examples**
```bash
# Conservative regime-aware portfolio
python main.py basic --buckets "Risk Assets,Defensive Assets,International"

# Aggressive growth focus
python main.py intermediate --buckets "Risk Assets,Growth Assets,High Beta"

# Balanced institutional approach
python main.py advanced --buckets "Risk Assets,Defensive Assets,International,Commodities"

# All-weather portfolio
python main.py expert --buckets "Risk Assets,Defensive Assets,International,Commodities,Alternatives"
```

---

## ⚙️ Complexity Tiers

The system provides tiered access to parameters based on user experience:

### **Tier 1: Basic (10 parameters)**
Essential parameters for beginners:
```bash
python main.py basic \
  --start-date 2021-01-01 \
  --cash 100000 \
  --max-total-positions 5 \
  --buckets "Risk Assets,Defensive Assets"
```

**Key Parameters:**
- `--start-date`: Backtest start date
- `--cash`: Initial capital amount
- `--max-total-positions`: Maximum number of positions
- `--buckets`: Asset bucket categories to use
- `--rebalance-frequency`: daily/weekly/monthly

### **Tier 2: Intermediate (25 parameters)**
Enhanced strategy features:
```bash
python main.py intermediate \
  --enable-bucket-diversification \
  --technical-weight 0.7 \
  --fundamental-weight 0.3 \
  --min-score-threshold 0.65
```

**Additional Parameters:**
- `--enable-bucket-diversification`: Enable bucket-based diversification
- `--technical-weight`: Weight for technical analysis (0.0-1.0)
- `--fundamental-weight`: Weight for fundamental analysis (0.0-1.0)
- `--min-score-threshold`: Minimum score for position entry
- `--max-single-position-pct`: Maximum individual position size

### **Tier 3: Advanced (40+ parameters)**
Risk management and lifecycle features:
```bash
python main.py advanced \
  --enable-grace-periods \
  --grace-period-days 5 \
  --enable-whipsaw-protection \
  --min-holding-period-days 3
```

**Additional Parameters:**
- `--enable-grace-periods`: Enable grace period protection
- `--grace-period-days`: Number of grace period days
- `--enable-whipsaw-protection`: Enable whipsaw protection
- `--whipsaw-protection-days`: Protection period length
- `--min-holding-period-days`: Minimum position holding period

### **Tier 4: Expert (50+ parameters)**
Professional institutional features:
```bash
python main.py expert \
  --enable-core-assets \
  --core-override-threshold 0.95 \
  --smart-diversification-overrides 2 \
  --enable-regime-overrides
```

**Additional Parameters:**
- `--enable-core-assets`: Enable core asset management
- `--core-override-threshold`: Score threshold for core asset designation
- `--smart-diversification-overrides`: Maximum bucket override allowances
- `--enable-regime-overrides`: Allow regime-based protection overrides

---

## 📄 Configuration File Templates

### **Conservative Strategy Template**
```yaml
# conservative_strategy.yaml
name: "Conservative Diversified Strategy"
tier_level: 2

system_config:
  buckets: ["Risk Assets", "Defensive Assets", "International"]
  cash: 100000
  commission: 0.001
  rebalance_frequency: 'monthly'
  start_date: '2021-01-01'

core_config:
  max_total_positions: 8
  max_new_positions: 2
  min_score_threshold: 0.65
  max_single_position_pct: 0.15
  target_total_allocation: 0.90
  technical_weight: 0.4
  fundamental_weight: 0.6

bucket_config:
  enable_bucket_diversification: true
  max_positions_per_bucket: 3
  max_allocation_per_bucket: 0.35
  allow_bucket_overflow: false

sizing_config:
  enable_dynamic_sizing: false
  sizing_mode: 'equal_weight'
  max_single_position: 0.12

lifecycle_config:
  enable_grace_periods: true
  grace_period_days: 7
  min_holding_period_days: 5
  enable_whipsaw_protection: true
  whipsaw_protection_days: 21

core_asset_config:
  enable_core_asset_management: false
```

### **Aggressive Growth Template**
```yaml
# aggressive_strategy.yaml
name: "Aggressive Growth Strategy"
tier_level: 3

system_config:
  buckets: ["Risk Assets", "Growth Assets", "High Beta"]
  cash: 100000
  commission: 0.001
  rebalance_frequency: 'weekly'
  start_date: '2021-01-01'

core_config:
  max_total_positions: 12
  max_new_positions: 5
  min_score_threshold: 0.55
  max_single_position_pct: 0.25
  target_total_allocation: 0.98
  technical_weight: 0.7
  fundamental_weight: 0.3

bucket_config:
  enable_bucket_diversification: true
  max_positions_per_bucket: 6
  max_allocation_per_bucket: 0.6
  allow_bucket_overflow: true

sizing_config:
  enable_dynamic_sizing: true
  sizing_mode: 'score_weighted'
  max_single_position: 0.20
  enable_two_stage_sizing: true

lifecycle_config:
  enable_grace_periods: true
  grace_period_days: 3
  min_holding_period_days: 1
  enable_regime_overrides: true
  enable_whipsaw_protection: true
  whipsaw_protection_days: 7

core_asset_config:
  enable_core_asset_management: true
  max_core_assets: 2
  core_asset_override_threshold: 0.92
```

### **Institutional Professional Template**
```yaml
# institutional_strategy.yaml
name: "Professional Institutional Strategy"
tier_level: 4

system_config:
  buckets: ["Risk Assets", "Defensive Assets", "International", "Alternatives"]
  cash: 1000000
  commission: 0.001
  rebalance_frequency: 'weekly'
  start_date: '2021-01-01'
  timeframes: ['1d', '4h', '1h']

core_config:
  max_total_positions: 15
  max_new_positions: 4
  min_score_threshold: 0.62
  max_single_position_pct: 0.20
  target_total_allocation: 0.96
  technical_weight: 0.55
  fundamental_weight: 0.45

bucket_config:
  enable_bucket_diversification: true
  max_positions_per_bucket: 5
  max_allocation_per_bucket: 0.35
  min_buckets_represented: 4
  allow_bucket_overflow: true
  correlation_limit: 0.75

sizing_config:
  enable_dynamic_sizing: true
  sizing_mode: 'adaptive'
  max_single_position: 0.16
  enable_two_stage_sizing: true
  residual_strategy: 'safe_top_slice'

lifecycle_config:
  enable_grace_periods: true
  grace_period_days: 4
  min_holding_period_days: 3
  enable_regime_overrides: true
  regime_override_cooldown_days: 28
  enable_whipsaw_protection: true
  whipsaw_protection_days: 10

core_asset_config:
  enable_core_asset_management: true
  max_core_assets: 3
  core_asset_override_threshold: 0.96
  core_asset_expiry_days: 75
  smart_diversification_overrides: 2
```

---

## 🗄️ Database Configuration

### **PostgreSQL Setup (Recommended)**
```bash
# Set environment variables
export DATABASE_URL='postgresql://user:password@localhost:5432/hedge_fund'

# Or use individual components
export DB_HOST='localhost'
export DB_PORT='5432'
export DB_NAME='hedge_fund'
export DB_USER='postgres'
export DB_PASSWORD='your_password'

# Test connection
python utils/database_test.py
```

### **Required Database Tables**
```sql
-- Market regime detection data
CREATE TABLE research (
    id SERIAL PRIMARY KEY,
    regime VARCHAR(50),           -- 'Goldilocks', 'Deflation', 'Inflation', 'Reflation'
    buckets TEXT[],              -- Asset buckets for current regime
    created_at DATE,             -- Date this regime data applies to
    confidence DECIMAL(5,3),     -- Regime confidence score (0.0-1.0)
    metadata JSONB               -- Additional regime metadata
);

-- Asset scanner historical data
CREATE TABLE scanner_historical (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    market VARCHAR(20) NOT NULL, -- 'trending', 'ranging', 'breakout', 'breakdown'
    confidence DECIMAL(5,3) NOT NULL, -- 0.0-1.0 confidence score
    timeframe VARCHAR(5) DEFAULT '1d',
    date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### **Database Modes**
```bash
# Full functionality with database
python main.py advanced --enable-database=true

# Technical analysis only (no database required)
python main.py advanced --enable-database=false
```

---

## 🎛️ Complete Parameter Reference

### **System Parameters**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--start-date` | date | Required | Backtest start date (YYYY-MM-DD) |
| `--end-date` | date | yesterday | Backtest end date (YYYY-MM-DD) |
| `--cash` | float | 100000 | Starting capital amount |
| `--commission` | float | 0.001 | Transaction cost (0.1% default) |
| `--rebalance-frequency` | str | monthly | daily/weekly/monthly |
| `--buckets` | str | Auto | Comma-separated bucket list |

### **Portfolio Management**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--max-total-positions` | int | 10 | Maximum portfolio positions |
| `--max-new-positions` | int | 3 | Max new positions per rebalance |
| `--min-score-threshold` | float | 0.6 | Minimum position score threshold |
| `--max-single-position-pct` | float | 0.2 | Maximum individual position size |
| `--target-total-allocation` | float | 0.95 | Target portfolio allocation |

### **Analysis Weights**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--technical-weight` | float | 0.6 | Technical analysis weight (0.0-1.0) |
| `--fundamental-weight` | float | 0.4 | Fundamental analysis weight (0.0-1.0) |

### **Bucket Diversification**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--enable-bucket-diversification` | bool | false | Enable bucket-based diversification |
| `--max-positions-per-bucket` | int | 4 | Maximum positions per bucket |
| `--max-allocation-per-bucket` | float | 0.4 | Maximum allocation per bucket |
| `--allow-bucket-overflow` | bool | false | Allow bucket limit overrides |

### **Dynamic Sizing**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--enable-dynamic-sizing` | bool | false | Enable dynamic position sizing |
| `--sizing-mode` | str | equal_weight | equal_weight/score_weighted/adaptive |
| `--enable-two-stage-sizing` | bool | false | Enable two-stage sizing system |

### **Grace Periods**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--enable-grace-periods` | bool | false | Enable grace period protection |
| `--grace-period-days` | int | 5 | Number of grace period days |
| `--grace-decay-rate` | float | 0.8 | Daily decay rate (0.0-1.0) |

### **Holding Periods**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--min-holding-period-days` | int | 3 | Minimum position holding period |
| `--max-holding-period-days` | int | 90 | Maximum position holding period |

### **Whipsaw Protection**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--enable-whipsaw-protection` | bool | false | Enable whipsaw protection |
| `--whipsaw-protection-days` | int | 14 | Protection period length |
| `--max-cycles-per-period` | int | 1 | Max cycles per protection period |

### **Core Asset Management**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--enable-core-assets` | bool | false | Enable core asset management |
| `--max-core-assets` | int | 3 | Maximum core asset positions |
| `--core-override-threshold` | float | 0.95 | Score threshold for core designation |
| `--core-expiry-days` | int | 90 | Core asset status expiry period |

### **Regime Management**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--enable-regime-overrides` | bool | false | Allow regime-based overrides |
| `--regime-override-cooldown-days` | int | 21 | Cooldown between overrides |

---

## 🏃‍♂️ Usage Examples

### **Basic Beginner Setup**
```bash
# Simple start with minimum parameters
python main.py basic \
  --start-date 2022-01-01 \
  --cash 50000 \
  --max-total-positions 5
```

### **Intermediate Strategy Testing**
```bash
# Enhanced features with diversification
python main.py intermediate \
  --start-date 2021-01-01 \
  --cash 200000 \
  --enable-bucket-diversification \
  --technical-weight 0.7 \
  --rebalance-frequency weekly
```

### **Advanced Risk Management**
```bash
# Full protection systems
python main.py advanced \
  --start-date 2020-01-01 \
  --cash 500000 \
  --enable-grace-periods \
  --enable-whipsaw-protection \
  --enable-core-assets \
  --max-total-positions 12
```

### **Professional Institutional**
```bash
# Complete professional setup
python main.py expert \
  --start-date 2019-01-01 \
  --cash 2000000 \
  --buckets "Risk Assets,Defensive Assets,International,Commodities" \
  --max-total-positions 20 \
  --enable-core-assets \
  --enable-regime-overrides \
  --core-override-threshold 0.96 \
  --rebalance-frequency daily
```

### **Configuration File Usage**
```bash
# Export current settings
python -m config.cli_parser --tier expert --export-config my_strategy.yaml

# Import and validate
python -m config.cli_parser --import my_strategy.yaml --validate

# Run with configuration file
python main.py config --file my_strategy.yaml
```

### **Strategy Preset Usage**
```bash
# Use built-in presets
python main.py preset --preset-name conservative --start-date 2021-01-01
python main.py preset --preset-name aggressive --start-date 2021-01-01
python main.py preset --preset-name institutional --start-date 2021-01-01

# List available presets
python -m config.cli_parser --list-presets
```

---

## 🔧 Configuration Management Commands

### **Export Current Configuration**
```bash
# Export basic tier configuration
python -m config.cli_parser --tier basic --export-config basic_setup.yaml

# Export advanced configuration with validation
python -m config.cli_parser --tier advanced --export-config advanced_setup.yaml --validate
```

### **Import and Validate Configuration**
```bash
# Validate configuration file
python -m config.cli_parser --import my_strategy.yaml --validate

# Import with tier verification
python -m config.cli_parser --import my_strategy.yaml --tier 3 --validate
```

### **Configuration Information**
```bash
# List all available presets with details
python -m config.cli_parser --list-presets --detailed

# Show parameter registry for specific tier
python -m config.cli_parser --show-params --tier advanced

# Validate all built-in presets
python -m config.cli_parser --validate-presets
```

---

## 📊 Performance and Monitoring

### **Event Monitoring**
```bash
# View recent events
python -c "
from monitoring.event_store import EventStore
store = EventStore()
events = store.query_recent_events(hours=24)
print(f'Recent events: {len(events)}')
"

# Monitor protection system status
python -c "
from core.protection_orchestrator import ProtectionOrchestrator
orchestrator = ProtectionOrchestrator()
status = orchestrator.get_system_health()
print(f'Protection systems active: {status}')
"
```

### **Database Monitoring**
```bash
# Test database connection and performance
python utils/database_test.py

# Test asset scanner with database integration
python utils/scanner_test.py
```

---

## 🚨 Common Configuration Issues

### **Asset Bucket Confusion**
❌ **Wrong**: Manually specifying individual stocks
```bash
python main.py basic --buckets "AAPL,MSFT,GOOGL"  # Don't do this
```

✅ **Correct**: Specifying bucket categories
```bash
python main.py basic --buckets "Risk Assets,Defensive Assets"  # Do this
```

### **Database Configuration**
❌ **Wrong**: Missing database setup
```bash
# Running without DATABASE_URL when using database features
python main.py advanced --enable-database=true  # Will fail
```

✅ **Correct**: Proper database setup
```bash
export DATABASE_URL='postgresql://user:password@localhost:5432/hedge_fund'
python main.py advanced --enable-database=true  # Will work
```

### **Parameter Validation**
❌ **Wrong**: Conflicting parameters
```bash
python main.py basic --technical-weight 0.8 --fundamental-weight 0.8  # Sums > 1.0
```

✅ **Correct**: Balanced parameters
```bash
python main.py basic --technical-weight 0.6 --fundamental-weight 0.4  # Sums = 1.0
```

---

## 📈 Performance Optimization

### **For Speed**
```bash
# Reduce position count and rebalance frequency
python main.py basic \
  --max-total-positions 5 \
  --rebalance-frequency monthly \
  --enable-database=false
```

### **For Accuracy**
```bash
# Enable all analysis features with database
python main.py expert \
  --enable-database=true \
  --technical-weight 0.5 \
  --fundamental-weight 0.5 \
  --rebalance-frequency daily
```

### **For Risk Management**
```bash
# Enable all protection systems
python main.py advanced \
  --enable-grace-periods \
  --enable-whipsaw-protection \
  --enable-core-assets \
  --enable-regime-overrides
```

---

This configuration guide provides comprehensive coverage of all system parameters, templates, and usage patterns. The regime-based asset selection system automatically chooses appropriate assets based on market conditions, eliminating the need for manual asset specification.