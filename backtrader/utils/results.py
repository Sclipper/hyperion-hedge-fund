import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from .analyzers import print_analysis


def save_results(strategy, tickers, start_date, end_date, results_dir="results"):
    results_path = Path(results_dir)
    results_path.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    tickers_str = '_'.join(tickers)
    filename = f"backtest_{tickers_str}_{timestamp}"
    
    results_data = extract_results(strategy, tickers, start_date, end_date)
    
    json_file = results_path / f"{filename}.json"
    with open(json_file, 'w') as f:
        json.dump(results_data, f, indent=2, default=str)
    
    csv_file = results_path / f"{filename}_trades.csv"
    if results_data['trades']['details']:
        trades_df = pd.DataFrame(results_data['trades']['details'])
        trades_df.to_csv(csv_file, index=False)
    
    print_analysis(strategy)
    
    print(f"Results saved to:")
    print(f"  JSON: {json_file}")
    print(f"  CSV: {csv_file}")
    
    return results_data


def extract_results(strategy, tickers, start_date, end_date) -> Dict[str, Any]:
    sharpe = strategy.analyzers.sharpe.get_analysis()
    returns = strategy.analyzers.returns.get_analysis()
    drawdown = strategy.analyzers.drawdown.get_analysis()
    trades = strategy.analyzers.trades.get_analysis()
    sqn = strategy.analyzers.sqn.get_analysis()
    vwr = strategy.analyzers.vwr.get_analysis()
    
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
        }
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