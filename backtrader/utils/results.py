import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from .analyzers import print_analysis
from .data_exporters import PortfolioDataExporter


def save_results(strategy, tickers, start_date, end_date, results_dir="results", enable_enhanced_export=True):
    # Create date-based folder structure
    base_results_path = Path(results_dir)
    base_results_path.mkdir(exist_ok=True)
    
    run_date = datetime.now().strftime('%Y%m%d_%H%M%S')
    start_str = start_date.strftime('%Y%m%d')
    end_str = end_date.strftime('%Y%m%d')
    
    # Create folder name: run_YYYYMMDD_HHMMSS_from_YYYYMMDD_to_YYYYMMDD
    folder_name = f"run_{run_date}_from_{start_str}_to_{end_str}"
    results_path = base_results_path / folder_name
    results_path.mkdir(exist_ok=True)
    
    # Create filename with same structure
    tickers_str = '_'.join(tickers[:3])  # Limit to first 3 tickers for filename
    if len(tickers) > 3:
        tickers_str += f'_plus{len(tickers)-3}'
    filename = f"backtest_{tickers_str}_{run_date}_from_{start_str}_to_{end_str}"
    
    results_data = extract_results(strategy, tickers, start_date, end_date)
    
    # Original JSON export
    json_file = results_path / f"{filename}.json"
    with open(json_file, 'w') as f:
        json.dump(results_data, f, indent=2, default=str)
    
    # Original trades CSV export
    csv_file = results_path / f"{filename}_trades.csv"
    if results_data['trades']['details']:
        trades_df = pd.DataFrame(results_data['trades']['details'])
        trades_df.to_csv(csv_file, index=False)
    
    saved_files = [str(json_file), str(csv_file)]
    
    # Enhanced CSV exports (new functionality)
    if enable_enhanced_export and False:  # Temporarily disabled for testing
        try:
            exporter = PortfolioDataExporter(results_dir)
            enhanced_files = exporter.create_enhanced_export_package(
                strategy, tickers, start_date, end_date
            )
            
            print(f"\nEnhanced CSV exports in folder: {folder_name}")
            for export_type, filepath in enhanced_files.items():
                print(f"  {export_type}: {Path(filepath).name}")
                saved_files.append(filepath)
                
        except Exception as e:
            print(f"Warning: Enhanced export failed: {e}")
    
    print_analysis(strategy)
    
    print(f"\nCore results saved in folder: {folder_name}")
    print(f"  JSON: {Path(json_file).name}")
    print(f"  Trades CSV: {Path(csv_file).name}")
    print(f"  Location: {results_path}")
    
    return results_data


def extract_results(strategy, tickers, start_date, end_date) -> Dict[str, Any]:
    sharpe = strategy.analyzers.sharpe.get_analysis()
    returns = strategy.analyzers.returns.get_analysis()
    drawdown = strategy.analyzers.drawdown.get_analysis()
    trades = strategy.analyzers.trades.get_analysis()
    sqn = strategy.analyzers.sqn.get_analysis()
    vwr = strategy.analyzers.vwr.get_analysis()
    
    # Get data from our new custom analyzers
    portfolio_tracker = strategy.analyzers.portfolio_tracker.get_analysis()
    position_tracker = strategy.analyzers.position_tracker.get_analysis()
    
    results = {
        'metadata': {
            'tickers': tickers,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'strategy': strategy.__class__.__name__,
            'parameters': {param: getattr(strategy.params, param) for param in strategy.params._getkeys()},
            'generated_at': datetime.now().isoformat()
        },
        'performance': {
            'sharpe_ratio': sharpe.get('sharperatio', 0),
            'total_return': returns.get('rtot', 0),
            'average_return': returns.get('ravg', 0),
            'max_drawdown': drawdown.get('max', {}).get('drawdown', 0),
            'max_drawdown_duration': drawdown.get('max', {}).get('len', 0),
            'sqn': sqn.get('sqn', 0),
            'vwr': vwr.get('vwr', 0)
        },
        'trades': {
            'total': trades.get('total', {}).get('total', 0),
            'won': trades.get('won', {}).get('total', 0),
            'lost': trades.get('lost', {}).get('total', 0),
            'win_rate': 0,
            'average_win': 0,
            'average_loss': 0,
            'profit_factor': 0,
            'details': []
        },
        'portfolio_timeline': portfolio_tracker.get('portfolio_timeline', []),
        'position_changes': position_tracker.get('position_changes', [])
    }
    
    if results['trades']['total'] > 0:
        results['trades']['win_rate'] = results['trades']['won'] / results['trades']['total']
    
    if 'won' in trades and 'pnl' in trades['won']:
        results['trades']['average_win'] = trades['won']['pnl']['average']
    
    if 'lost' in trades and 'pnl' in trades['lost']:
        results['trades']['average_loss'] = trades['lost']['pnl']['average']
    
    if (results['trades']['average_loss'] != 0 and 
        results['trades']['average_win'] > 0):
        results['trades']['profit_factor'] = abs(results['trades']['average_win'] / results['trades']['average_loss'])
    
    return results


def load_results(filename: str, results_dir: str = "results") -> Dict[str, Any]:
    results_path = Path(results_dir) / filename
    
    if not results_path.exists():
        raise FileNotFoundError(f"Results file not found: {results_path}")
    
    with open(results_path, 'r') as f:
        return json.load(f)


def compare_results(result_files: list, results_dir: str = "results") -> pd.DataFrame:
    comparison_data = []
    
    for filename in result_files:
        try:
            results = load_results(filename, results_dir)
            
            comparison_data.append({
                'file': filename,
                'strategy': results['metadata']['strategy'],
                'tickers': ', '.join(results['metadata']['tickers']),
                'start_date': results['metadata']['start_date'],
                'end_date': results['metadata']['end_date'],
                'total_return': results['performance']['total_return'],
                'sharpe_ratio': results['performance']['sharpe_ratio'],
                'max_drawdown': results['performance']['max_drawdown'],
                'total_trades': results['trades']['total'],
                'win_rate': results['trades']['win_rate'],
                'profit_factor': results['trades']['profit_factor']
            })
        except Exception as e:
            print(f"Error loading {filename}: {e}")
    
    return pd.DataFrame(comparison_data)