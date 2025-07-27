#!/bin/bash
# Data Pre-download Examples for Hedge Fund System

echo "📊 DATA PRE-DOWNLOAD EXAMPLES"
echo "=" * 50

# Example 1: Download daily data for major assets (1 year)
echo "📈 Example 1: Major assets daily data (1 year)"
echo "python scripts/preload_data.py --tickers AAPL,MSFT,GOOGL,NVDA,TSLA --timeframes 1d --period 1y"
echo

# Example 2: Multi-timeframe download with Alpha Vantage
echo "🕐 Example 2: Multi-timeframe data for analysis"
echo "python scripts/preload_data.py --tickers AAPL,MSFT --timeframes 1h,4h,1d --start-date 2023-01-01 --end-date 2024-01-01 --provider alpha_vantage"
echo

# Example 3: Bulk download all risk assets
echo "📦 Example 3: All risk assets (2 years daily)"
echo "python scripts/preload_data.py --bucket 'Risk Assets' --timeframes 1d --period 2y"
echo

# Example 4: Crypto data download
echo "🪙 Example 4: Cryptocurrency data"
echo "python scripts/preload_data.py --tickers BTC,ETH,BTCUSD --timeframes 1d --period 6m --provider alpha_vantage"
echo

# Example 5: High-frequency data for day trading strategy
echo "⚡ Example 5: High-frequency data for day trading"
echo "python scripts/preload_data.py --tickers SPY,QQQ,IWM --timeframes 1h,4h --period 3m --provider alpha_vantage"
echo

# Example 6: Specific date range download
echo "📅 Example 6: Specific date range"
echo "python scripts/preload_data.py --tickers AAPL --timeframes 1h,4h,1d --start-date 2023-06-01 --end-date 2023-12-31"
echo

# Management examples
echo "🔧 MANAGEMENT EXAMPLES"
echo "=" * 30

echo "📝 List active checkpoints:"
echo "python scripts/preload_data.py --list-checkpoints"
echo

echo "🔄 Resume interrupted download:"
echo "python scripts/preload_data.py --resume BULK_20240101_120000_AAPL_1h"
echo

echo "💾 Show cache statistics:"
echo "python scripts/preload_data.py --cache-stats"
echo

echo "📊 Estimate download time only:"
echo "python scripts/preload_data.py --tickers AAPL,MSFT,GOOGL --timeframes 1h,4h,1d --period 1y --estimate-only"
echo

# Quick start commands
echo "🚀 QUICK START COMMANDS"
echo "=" * 30

echo "# Basic usage (Yahoo Finance):"
echo "python scripts/preload_data.py --tickers AAPL,MSFT --period 1y"
echo

echo "# Alpha Vantage multi-timeframe:"
echo "python scripts/preload_data.py --tickers AAPL --timeframes 1h,4h,1d --period 6m --provider alpha_vantage"
echo

echo "# Bulk asset bucket download:"
echo "python scripts/preload_data.py --bucket 'Risk Assets' --period 1y"
echo