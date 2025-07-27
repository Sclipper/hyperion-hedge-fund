# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a sophisticated institutional-grade hedge fund backtesting and trading framework built on backtrader. It features 11 integrated modules providing professional portfolio management with regime-aware trading, advanced risk protection systems, dynamic position sizing, and comprehensive audit trails.

## Tech Stack

- **Backend**: Python 3.9+ with backtrader framework
- **Dependencies**: pandas, numpy, yfinance, SQLAlchemy, matplotlib, seaborn, ta, psycopg2-binary
- **Database**: SQLite (event logging), PostgreSQL (regime detection) 
- **Testing**: pytest for unit tests

## Development Commands

### Core Operations
```bash
# Install dependencies
pip install -r requirements.txt

# Basic regime-based backtesting (recommended approach)
python main.py regime --buckets "Risk Assets,Defensive Assets" --start-date 2021-01-01

# Static backtesting (legacy approach)
python main.py static --tickers AAPL,MSFT,NVDA

# Advanced configuration with all protection systems
python main.py regime --buckets "Risk Assets,Defensive Assets,International" \
  --start-date 2021-01-01 --enable-core-assets --max-assets 8 \
  --min-score 0.65 --rebalance-freq daily

# Configuration management (Module 11)
python -m config.cli_parser --tier intermediate --export-config strategy.yaml
python main.py regime --config strategy.yaml
```

### Testing
```bash
# Run all tests
pytest

# Run specific test modules
pytest tests/test_core_monitoring.py
pytest tests/test_protection_orchestrator.py

# Run tests with verbose output
pytest -v tests/

# Test database connection
python utils/database_test.py

# Test asset scanner functionality
python utils/scanner_test.py
```

### Event Monitoring and Analysis
```bash
# Monitor event database
python -c "
from monitoring.event_store import EventStore
store = EventStore()
events = store.query_recent_events(hours=24)
print(f'Recent events: {len(events)}')
"

# View protection system status
python -c "
from core.protection_orchestrator import ProtectionOrchestrator
orchestrator = ProtectionOrchestrator()
status = orchestrator.get_protection_status('AAPL', datetime.now())
print(status)
"
```

## Architecture Overview

### Multi-Module System (11 Modules)
- **Module 3**: Two-Stage Dynamic Position Sizing (`core/two_stage_position_sizer.py`)
- **Module 4**: Grace & Holding Period Management (`core/enhanced_grace_period_manager.py`, `core/holding_period_manager.py`)
- **Module 5**: Core Asset Management (`core/core_asset_manager.py`)
- **Module 6**: Regime Context Provider (`core/regime_context_provider.py`)
- **Module 7**: Advanced Whipsaw Protection (`core/enhanced_whipsaw_protection_manager.py`)
- **Module 8**: Protection System Orchestrator (`core/protection_orchestrator.py`)
- **Module 9**: Monitoring & Event Logging (`monitoring/`)
- **Module 11**: CLI & Configuration Management (`config/`)

### Key Components

**Core Trading Engine**
- `core/enhanced_rebalancer_engine.py`: Main orchestrator with event logging
- `core/protection_aware_rebalancer.py`: Protection-integrated rebalancer
- `strategies/regime_strategy.py`: Advanced regime-aware trading strategy

**Data Management**
- `data/database_manager.py`: PostgreSQL connection manager with pooling and error handling
- `data/asset_scanner.py`: Enhanced asset scanner for trending/ranging/breakout/breakdown detection
- `data/regime_detector.py`: Market regime detection system with integrated scanner
- `data/asset_buckets.py`: Asset bucket management (Risk Assets, Defensives, etc.)
- `data/data_manager.py`: Yahoo Finance integration
- `data/database_integration.py`: Database queries for research and scanner data

**Position Management**
- `position/position_manager.py`: Core position lifecycle management
- `position/technical_analyzer.py`: Multi-timeframe technical analysis (20+ indicators)
- `position/fundamental_analyzer.py`: Balance sheet and valuation analysis

**Protection Systems (Priority Hierarchy)**
1. **Core Asset Immunity**: High-alpha assets (>0.95 score) protected from forced closure
2. **Regime Override**: Critical regime changes can bypass protection systems
3. **Grace Periods**: 3-5 day grace periods with 20% daily decay instead of immediate closure
4. **Holding Periods**: Minimum position duration enforcement (3+ days)
5. **Whipsaw Protection**: Maximum 1 complete cycle per 14-day period

**Event System**
- `monitoring/event_store.py`: SQLite-based event storage with sub-millisecond logging
- `monitoring/event_writer.py`: Centralized event logging with trace IDs
- `portfolio_events.db`: Complete audit trail database

## Database Configuration

The system requires PostgreSQL for regime detection and trending asset data:

### Environment Variables
```bash
# Option 1: Full connection string
export DATABASE_URL='postgresql://user:password@host:port/dbname'

# Option 2: Individual components
export DB_HOST='localhost'
export DB_PORT='5432'
export DB_NAME='hedge_fund'
export DB_USER='postgres'
export DB_PASSWORD='your_password'
```

### Database Commands
```bash
# Test database connection
python utils/database_test.py

# Run with database enabled (default)
python main.py regime --buckets "Risk Assets,Defensive Assets" --enable-database

# Run without database (mock data)
python main.py regime --buckets "Risk Assets,Defensive Assets" --enable-database=false
```

### Required Tables
- `research`: Market regime data with regime classifications
- `scanner_historical`: Asset scanner results with market conditions (trending/ranging/breakout/breakdown) and confidence scores

## Configuration System (Module 11)

The system uses a sophisticated tiered configuration approach:

### Complexity Tiers
```bash
# Basic tier (10 essential parameters)
python -m config.cli_parser --tier basic

# Intermediate tier (25 parameters)  
python -m config.cli_parser --tier intermediate

# Advanced tier (40+ parameters)
python -m config.cli_parser --tier advanced

# Expert tier (all 50+ parameters)
python -m config.cli_parser --tier expert
```

### Built-in Strategy Presets
- **Conservative**: Low risk, stable returns focus
- **Aggressive**: High risk, maximum alpha pursuit
- **Adaptive**: Dynamic risk adjustment based on regime
- **Institutional**: Professional hedge fund configuration

## Asset Buckets

The system organizes assets into strategic buckets:

**Core Equity**: Risk Assets, Defensive Assets, Value Assets, Growth Assets
**Style & Factor**: High Beta, Low Beta, Cyclicals, Quality
**Geographic**: International, Commodities, Fixed Income, Alternatives

## Development Patterns

### Adding New Protection Systems
```python
# In core/protection_orchestrator.py
class CustomProtectionManager:
    def can_execute_action(self, request):
        return ProtectionResult(
            system_name='custom_protection',
            approved=True,
            reason='Custom logic approved'
        )

# Register with orchestrator
orchestrator.add_protection_manager('custom', CustomProtectionManager())
```

### Enhanced Asset Scanner Usage
```python
from data.asset_scanner import get_asset_scanner

scanner = get_asset_scanner()

# Comprehensive market condition scan
results = scanner.scan_assets(['AAPL', 'MSFT', 'GOOGL'], datetime.now())
trending_assets = [asset.ticker for asset in results.trending_assets]
ranging_assets = [asset.ticker for asset in results.ranging_assets]

# Get market condition summary
summary = scanner.get_market_condition_summary(['AAPL', 'MSFT'], datetime.now())
```

### Event Logging Integration
```python
from monitoring.event_writer import get_event_writer

event_writer = get_event_writer()
event_writer.log_position_event(
    'position_open', 'AAPL', 'open',
    reason='High score asset: 0.857 > 0.65 threshold',
    score_after=0.857, size_after=0.12,
    metadata={'bucket': 'Risk Assets'}
)
```

### Testing Patterns
- All protection system tests in `tests/test_protection_*.py`
- Event system tests in `tests/test_*_monitoring.py`
- Use `tempfile` for database tests to avoid state contamination
- Mock external data sources for consistent test results

## Performance Characteristics

- **Rebalancing Speed**: <5 seconds for 100+ asset universe
- **Protection Decisions**: <1ms per decision (sub-millisecond average)
- **Event Logging**: <0.5ms overhead per event
- **Memory Usage**: <500MB for full system operation

## Important Implementation Notes

- The system requires real PostgreSQL data for regime detection (graceful degradation to limited functionality without it)
- All protection systems use a unified priority hierarchy resolved by `ProtectionOrchestrator`
- Event logging is mandatory for all core operations - provides complete audit trail
- Configuration validation prevents dangerous parameter combinations
- Multi-timeframe technical analysis requires 1h, 4h data (defaults to daily if unavailable)

## Directory Structure

```
core/                     # Core trading engine and protection systems
├── enhanced_rebalancer_engine.py    # Main orchestrator with event logging
├── protection_orchestrator.py       # Module 8: Unified protection coordination
├── regime_context_provider.py       # Module 6: Regime intelligence
└── enhanced_*.py                     # Enhanced versions with monitoring integration

config/                   # Module 11: Configuration management
├── cli_parser.py         # Tiered CLI parser
├── parameter_registry.py # Central parameter registry
└── presets.py           # Strategy presets

monitoring/               # Module 9: Event logging system
├── event_store.py       # SQLite event storage
├── event_writer.py      # Centralized event logging
└── portfolio_events.db  # SQLite audit database

strategies/               # Trading strategies
├── regime_strategy.py   # Advanced regime-aware strategy (recommended)
└── base_strategy.py     # Original static strategy (legacy)

position/                 # Position management
├── position_manager.py  # Core position lifecycle
├── technical_analyzer.py # Multi-timeframe technical analysis
└── fundamental_analyzer.py # Balance sheet analysis

data/                     # Data management
├── regime_detector.py   # Market regime detection
├── asset_buckets.py     # Asset bucket management
└── data_manager.py      # Yahoo Finance integration
```