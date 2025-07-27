# Data Pre-download Scripts

This directory contains standalone scripts for pre-downloading historical data for the hedge fund backtesting system.

## Scripts

### `preload_data.py` - Main Data Pre-download Script

A comprehensive script for bulk downloading historical data with support for:
- Multiple data providers (Alpha Vantage, Yahoo Finance)
- Multi-timeframe downloads (1h, 4h, 1d)
- Intelligent chunking and rate limiting
- Checkpointing for resumable downloads
- Asset bucket integration
- Progress tracking and estimation

#### Quick Start

```bash
# Download daily data for major assets (1 year)
python scripts/preload_data.py --tickers AAPL,MSFT,GOOGL --period 1y

# Multi-timeframe download with Alpha Vantage
python scripts/preload_data.py --tickers AAPL --timeframes 1h,4h,1d --period 6m --provider alpha_vantage

# Download all risk assets
python scripts/preload_data.py --bucket "Risk Assets" --period 1y

# Show help
python scripts/preload_data.py --help
```

#### Key Features

**Data Selection:**
- `--tickers`: Specify individual ticker symbols
- `--bucket`: Download entire asset buckets (Risk Assets, Defensive Assets, etc.)
- `--timeframes`: Multiple timeframes in one command (1h, 4h, 1d)

**Date Ranges:**
- `--period`: Simple period format (1y, 6m, 30d)
- `--start-date` / `--end-date`: Exact date ranges

**Provider Management:**
- `--provider`: Choose between alpha_vantage and yahoo
- Automatic fallback when API keys unavailable
- Provider-specific optimizations

**Progress & Recovery:**
- `--estimate-only`: Preview download time and requests
- `--resume`: Resume interrupted downloads from checkpoints
- `--list-checkpoints`: View resumable downloads
- Graceful interruption handling (Ctrl+C saves checkpoint)

**Cache Management:**
- `--cache-stats`: View cached data statistics
- Provider-isolated caching
- Automatic cache validation

#### Usage Examples

```bash
# Basic Usage
python scripts/preload_data.py --tickers AAPL,MSFT --period 1y

# High-frequency Trading Data
python scripts/preload_data.py --tickers SPY,QQQ --timeframes 1h,4h --period 3m --provider alpha_vantage

# Cryptocurrency Data
python scripts/preload_data.py --tickers BTC,ETH --period 6m --provider alpha_vantage

# Specific Date Range
python scripts/preload_data.py --tickers AAPL --timeframes 1h,4h,1d --start-date 2023-01-01 --end-date 2023-12-31

# Bulk Asset Download
python scripts/preload_data.py --bucket "Risk Assets" --timeframes 1d --period 2y

# Estimation Only
python scripts/preload_data.py --tickers AAPL,MSFT,GOOGL --timeframes 1h,4h,1d --period 1y --estimate-only

# Resume Interrupted Download
python scripts/preload_data.py --resume BULK_20240101_120000_AAPL_1h

# Cache Management
python scripts/preload_data.py --cache-stats
python scripts/preload_data.py --list-checkpoints
```

#### Error Handling

The script includes comprehensive error handling:
- **Network Issues**: Automatic retry with exponential backoff
- **Rate Limiting**: Intelligent request spacing based on provider limits
- **Interruptions**: Saves checkpoints on Ctrl+C for resumability
- **API Errors**: Graceful degradation and detailed error reporting
- **Data Validation**: Checks data integrity before caching

#### Performance Considerations

**Alpha Vantage (75 req/min plan):**
- Optimal chunking for each timeframe
- Bulk download mode with checkpointing
- ~1 minute per 75 ticker/timeframe combinations

**Yahoo Finance:**
- No rate limits for reasonable usage
- Individual download mode
- Very fast for daily data

#### Directory Structure

After running downloads, your cache directory will be organized as:

```
data/cache/
├── alpha_vantage/
│   ├── AAPL/
│   │   ├── 1h/
│   │   ├── 4h/
│   │   └── 1d/
│   └── MSFT/
└── yahoo/
    ├── AAPL/
    │   └── 1d/
    └── MSFT/
```

### `examples/` Directory

Contains example scripts and usage patterns:
- `preload_examples.sh`: Comprehensive usage examples
- Common download patterns for different strategies
- Management command examples

## Integration

The pre-download script integrates seamlessly with the existing hedge fund system:

1. **Provider Abstraction**: Uses the same provider system as the main backtester
2. **Cache Compatibility**: Data downloaded here is immediately available to backtests
3. **Asset Buckets**: Full integration with the asset bucket system
4. **Timeframe Support**: Supports all timeframes available in the main system

## Best Practices

1. **Start with Estimation**: Always use `--estimate-only` first for large downloads
2. **Use Checkpoints**: For downloads >10 minutes, interruptions are saved automatically
3. **Provider Selection**: Use Alpha Vantage for multi-timeframe, Yahoo for daily-only
4. **Batch Downloads**: Download multiple assets/timeframes together for efficiency
5. **Cache Management**: Check `--cache-stats` periodically to monitor storage usage

## Troubleshooting

**"No API key" errors:**
- Set `ALPHA_VANTAGE_API_KEY` environment variable
- Script will automatically fall back to Yahoo Finance

**Rate limit errors:**
- Alpha Vantage: Reduce concurrent downloads or upgrade plan
- Yahoo Finance: Generally no limits for reasonable usage

**Checkpoint issues:**
- Checkpoints stored in `data/checkpoints/`
- Use `--list-checkpoints` to see resumable downloads

**Cache issues:**
- Provider-specific cache directories prevent conflicts
- Use `--cache-stats` to verify cached data
- Clear cache by deleting provider directories in `data/cache/`