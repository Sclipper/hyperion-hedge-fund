import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from .analyzers import print_analysis
from .data_exporters import PortfolioDataExporter
from .visualizer import PortfolioVisualizer


def extract_performance_metrics(strategy) -> dict:
    """Extract performance metrics from strategy analyzers for JSON export and visualization"""
    try:
        sharpe = strategy.analyzers.sharpe.get_analysis()
        returns = strategy.analyzers.returns.get_analysis()
        drawdown = strategy.analyzers.drawdown.get_analysis()
        trades = strategy.analyzers.trades.get_analysis()
        sqn = strategy.analyzers.sqn.get_analysis()
        vwr = strategy.analyzers.vwr.get_analysis()
        
        # Extract basic metrics
        metrics = {
            'sharpe_ratio': sharpe.get("sharperatio", 0) if sharpe else 0,
            'total_return_pct': returns.get("rtot", 0) * 100 if returns else 0,
            'avg_return_pct': returns.get("ravg", 0) * 100 if returns else 0,
            'max_drawdown_pct': drawdown.get("max", {}).get("drawdown", 0) if drawdown else 0,
            'max_drawdown_duration': drawdown.get("max", {}).get("len", 0) if drawdown else 0,
            'sqn': sqn.get("sqn", 0) if sqn else 0,
            'vwr': vwr.get("vwr", 0) if vwr else 0,
        }
        
        # Extract trade metrics
        if 'total' in trades:
            total_trades = trades['total']['total']
            won_trades = trades['won']['total'] if 'won' in trades else 0
            lost_trades = trades['lost']['total'] if 'lost' in trades else 0
            
            metrics.update({
                'total_trades': total_trades,
                'won_trades': won_trades,
                'lost_trades': lost_trades,
                'win_rate_pct': (won_trades / total_trades * 100) if total_trades > 0 else 0,
            })
            
            # Average win/loss
            if 'won' in trades and 'pnl' in trades['won']:
                metrics['avg_win'] = trades['won']['pnl']['average']
            
            if 'lost' in trades and 'pnl' in trades['lost']:
                metrics['avg_loss'] = trades['lost']['pnl']['average']
            
            # Profit factor and win/loss ratio
            if 'won' in trades and 'lost' in trades and 'pnl' in trades['won'] and 'pnl' in trades['lost']:
                total_wins = trades['won']['pnl']['total'] if trades['won']['pnl']['total'] > 0 else 0
                total_losses = abs(trades['lost']['pnl']['total']) if trades['lost']['pnl']['total'] < 0 else 0
                metrics['profit_factor'] = total_wins / total_losses if total_losses > 0 else float('inf') if total_wins > 0 else 0
                
                avg_win = trades['won']['pnl']['average'] if trades['won']['pnl']['average'] > 0 else 0
                avg_loss = abs(trades['lost']['pnl']['average']) if trades['lost']['pnl']['average'] < 0 else 1
                metrics['win_loss_ratio'] = avg_win / avg_loss if avg_loss > 0 else 0
        
        # Calculate volatility if we have returns data
        if returns and 'ravg' in returns and 'rstd' in returns:
            metrics['volatility_pct'] = returns.get('rstd', 0) * 100
        
        return metrics
        
    except Exception as e:
        print(f"Warning: Could not extract performance metrics: {e}")
        return {}


def save_results(strategy, tickers, start_date, end_date, results_dir="results", enable_enhanced_export=True, 
                enable_visualization=True, export_format='all', chart_style='interactive', benchmark_ticker='SPY'):
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
    enhanced_files = {}
    if enable_enhanced_export and export_format in ['csv', 'all']:
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
    
    # Position history export (strategy-specific data)
    if hasattr(strategy, 'position_manager'):
        try:
            position_history_file = results_path / f"{filename}_position_history.json"
            strategy.position_manager.export_position_history(str(position_history_file))
            print(f"  position_history: {position_history_file.name}")
            saved_files.append(str(position_history_file))
        except Exception as e:
            print(f"Warning: Position history export failed: {e}")
    
    # Portfolio visualizations (new functionality) 
    visualization_files = {}
    if enable_visualization and export_format in ['charts', 'all']:
        try:
            # Create portfolio visualization data
            portfolio_data = None
            position_changes = None
            
            # Extract data from enhanced exports or analyzers
            if enhanced_files:
                # Try to load the generated CSV files for visualization
                timeline_file = enhanced_files.get('portfolio_timeline')
                changes_file = enhanced_files.get('position_changes')
                
                if timeline_file and Path(timeline_file).exists():
                    portfolio_data = pd.read_csv(timeline_file)
                    portfolio_data['date'] = pd.to_datetime(portfolio_data['date'])
                
                if changes_file and Path(changes_file).exists():
                    position_changes = pd.read_csv(changes_file)
                    position_changes['date'] = pd.to_datetime(position_changes['date'])
            
            if portfolio_data is not None and not portfolio_data.empty:
                # Initialize visualizer
                visualizer = PortfolioVisualizer(style=chart_style)
                
                # Create charts
                charts = []
                
                # Portfolio performance chart
                portfolio_chart = visualizer.create_portfolio_chart(
                    portfolio_data, 
                    title=f"Portfolio Performance: {', '.join(tickers)}"
                )
                charts.append(portfolio_chart)
                
                # Trading activity chart (if position changes available)
                if position_changes is not None and not position_changes.empty:
                    trading_chart = visualizer.create_trading_activity_chart(
                        portfolio_data, position_changes
                    )
                    charts.append(trading_chart)
                
                # Performance dashboard
                dashboard_data = {'portfolio_timeline': portfolio_data}
                if position_changes is not None:
                    dashboard_data['position_changes'] = position_changes
                    
                dashboard_chart = visualizer.create_performance_dashboard(dashboard_data)
                charts.append(dashboard_chart)
                
                # Performance metrics visualization (if strategy has analyzers)
                if hasattr(strategy, 'analyzers'):
                    performance_metrics = extract_performance_metrics(strategy)
                    if performance_metrics:
                        # Export metrics to JSON
                        metrics_json_file = results_path / f"{filename}_performance_metrics.json"
                        with open(metrics_json_file, 'w') as f:
                            json.dump(performance_metrics, f, indent=2)
                        print(f"  performance_metrics: {metrics_json_file.name}")
                        saved_files.append(str(metrics_json_file))
                        
                        # Create metrics visualization chart
                        metrics_chart = visualizer.create_performance_metrics_chart(performance_metrics)
                        charts.append(metrics_chart)
                
                # Save all charts
                chart_files = visualizer.save_visualizations(
                    charts, results_path, filename
                )
                
                print(f"\nVisualization charts generated:")
                for chart_file in chart_files:
                    print(f"  {Path(chart_file).name}")
                    saved_files.append(chart_file)
                    
                visualization_files['charts'] = chart_files
                
            else:
                print("Warning: No portfolio data available for visualization")
                
        except Exception as e:
            print(f"Warning: Visualization generation failed: {e}")
            import traceback
            traceback.print_exc()
    
    print_analysis(strategy)
    
    print(f"\nCore results saved in folder: {folder_name}")
    print(f"  JSON: {Path(json_file).name}")
    print(f"  Trades CSV: {Path(csv_file).name}")
    print(f"  Location: {results_path}")
    
    # Add visualization and export info to results
    results_data['enhanced_exports'] = enhanced_files
    results_data['visualizations'] = visualization_files
    results_data['export_format'] = export_format
    results_data['chart_style'] = chart_style
    
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