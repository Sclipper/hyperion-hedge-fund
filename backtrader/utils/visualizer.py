"""
Portfolio Visualization Engine

Provides comprehensive portfolio visualization capabilities including:
- Portfolio value charts with benchmark comparison
- Asset allocation over time
- Performance metrics dashboard
- Trading activity visualization
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from pathlib import Path


class PortfolioVisualizer:
    """Main visualization engine for portfolio analysis"""
    
    def __init__(self, style: str = 'interactive'):
        """
        Initialize visualizer
        
        Args:
            style: 'interactive' for plotly charts, 'static' for matplotlib
        """
        self.style = style
        self.setup_styling()
    
    def setup_styling(self):
        """Setup default styling for charts"""
        if self.style == 'static':
            plt.style.use('seaborn-v0_8')
            sns.set_palette("husl")
        
        # Color palette for consistent styling
        self.colors = {
            'primary': '#2E86AB',
            'secondary': '#A23B72', 
            'success': '#F18F01',
            'danger': '#C73E1D',
            'background': '#F8F9FA',
            'text': '#343A40'
        }
    
    def create_portfolio_chart(self, 
                             portfolio_data: pd.DataFrame, 
                             benchmark_data: Optional[pd.DataFrame] = None,
                             title: str = "Portfolio Performance",
                             show_drawdown: bool = True) -> go.Figure:
        """
        Create primary portfolio value chart with optional benchmark comparison
        
        Args:
            portfolio_data: DataFrame with columns: date, portfolio_value, cash, etc.
            benchmark_data: Optional benchmark data with date, value columns
            title: Chart title
            show_drawdown: Whether to show drawdown shading
            
        Returns:
            Plotly figure object
        """
        if self.style == 'interactive':
            return self._create_interactive_portfolio_chart(
                portfolio_data, benchmark_data, title, show_drawdown
            )
        else:
            return self._create_static_portfolio_chart(
                portfolio_data, benchmark_data, title, show_drawdown
            )
    
    def _create_interactive_portfolio_chart(self, 
                                          portfolio_data: pd.DataFrame,
                                          benchmark_data: Optional[pd.DataFrame],
                                          title: str,
                                          show_drawdown: bool) -> go.Figure:
        """Create interactive plotly portfolio chart"""
        
        # Ensure date column is datetime
        portfolio_data['date'] = pd.to_datetime(portfolio_data['date'])
        
        # Calculate metrics
        portfolio_data = self._calculate_metrics(portfolio_data)
        
        # Create subplots
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=['Portfolio Value', 'Daily Returns', 'Drawdown'],
            vertical_spacing=0.08,
            row_heights=[0.6, 0.2, 0.2]
        )
        
        # Main portfolio line
        fig.add_trace(
            go.Scatter(
                x=portfolio_data['date'],
                y=portfolio_data['portfolio_value'],
                name='Portfolio',
                line=dict(color=self.colors['primary'], width=2),
                hovertemplate='<b>%{x}</b><br>Portfolio: $%{y:,.2f}<extra></extra>'
            ),
            row=1, col=1
        )
        
        # Benchmark comparison if provided
        if benchmark_data is not None:
            benchmark_data['date'] = pd.to_datetime(benchmark_data['date'])
            fig.add_trace(
                go.Scatter(
                    x=benchmark_data['date'],
                    y=benchmark_data['value'],
                    name='Benchmark',
                    line=dict(color=self.colors['secondary'], width=1, dash='dash'),
                    hovertemplate='<b>%{x}</b><br>Benchmark: $%{y:,.2f}<extra></extra>'
                ),
                row=1, col=1
            )
        
        # Daily returns
        fig.add_trace(
            go.Scatter(
                x=portfolio_data['date'],
                y=portfolio_data['daily_return'] * 100,
                name='Daily Returns',
                line=dict(color=self.colors['success'], width=1),
                hovertemplate='<b>%{x}</b><br>Return: %{y:.2f}%<extra></extra>'
            ),
            row=2, col=1
        )
        
        # Drawdown with shading
        if show_drawdown and 'drawdown' in portfolio_data.columns:
            fig.add_trace(
                go.Scatter(
                    x=portfolio_data['date'],
                    y=portfolio_data['drawdown'] * 100,
                    name='Drawdown',
                    fill='tonexty',
                    fillcolor='rgba(199, 62, 29, 0.3)',
                    line=dict(color=self.colors['danger'], width=1),
                    hovertemplate='<b>%{x}</b><br>Drawdown: %{y:.2f}%<extra></extra>'
                ),
                row=3, col=1
            )
        
        # Update layout
        fig.update_layout(
            title=title,
            height=800,
            showlegend=True,
            template='plotly_white',
            hovermode='x unified'
        )
        
        # Update axes
        fig.update_yaxes(title_text="Portfolio Value ($)", row=1, col=1)
        fig.update_yaxes(title_text="Daily Return (%)", row=2, col=1)
        fig.update_yaxes(title_text="Drawdown (%)", row=3, col=1)
        
        # Format X-axes with proper date formatting
        fig.update_xaxes(
            title_text="Date", 
            row=3, col=1,
            type='date',
            tickformat='%Y-%m-%d',
            dtick="D1" if len(portfolio_data) <= 30 else "M1"
        )
        fig.update_xaxes(
            type='date',
            tickformat='%Y-%m-%d',
            dtick="D1" if len(portfolio_data) <= 30 else "M1",
            row=1, col=1
        )
        fig.update_xaxes(
            type='date',
            tickformat='%Y-%m-%d', 
            dtick="D1" if len(portfolio_data) <= 30 else "M1",
            row=2, col=1
        )
        
        return fig
    
    def create_allocation_chart(self, composition_data: pd.DataFrame) -> go.Figure:
        """
        Create asset allocation over time stacked area chart
        
        Args:
            composition_data: DataFrame with date, asset, value, weight columns
            
        Returns:
            Plotly figure object
        """
        # Pivot data for stacked area chart
        pivot_data = composition_data.pivot_table(
            index='date', 
            columns='asset', 
            values='weight_pct', 
            fill_value=0
        )
        
        fig = go.Figure()
        
        # Add trace for each asset
        colors = px.colors.qualitative.Set3
        for i, asset in enumerate(pivot_data.columns):
            fig.add_trace(
                go.Scatter(
                    x=pivot_data.index,
                    y=pivot_data[asset],
                    mode='lines',
                    stackgroup='one',
                    name=asset,
                    line=dict(width=0.5),
                    fillcolor=colors[i % len(colors)],
                    hovertemplate=f'<b>{asset}</b><br>Date: %{{x}}<br>Weight: %{{y:.1f}}%<extra></extra>'
                )
            )
        
        fig.update_layout(
            title='Portfolio Allocation Over Time',
            xaxis_title='Date',
            yaxis_title='Allocation (%)',
            yaxis=dict(range=[0, 100]),
            hovermode='x unified',
            template='plotly_white'
        )
        
        return fig
    
    def create_performance_dashboard(self, all_data: Dict[str, pd.DataFrame]) -> go.Figure:
        """
        Create comprehensive performance dashboard with multiple metrics
        
        Args:
            all_data: Dictionary containing portfolio_timeline, position_changes, etc.
            
        Returns:
            Plotly figure with multiple subplots
        """
        portfolio_data = all_data['portfolio_timeline']
        portfolio_data['date'] = pd.to_datetime(portfolio_data['date'])
        portfolio_data = self._calculate_metrics(portfolio_data)
        
        # Create 2x2 subplot grid
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=[
                'Rolling Sharpe Ratio (30-day)',
                'Cumulative Returns',
                'Rolling Volatility (30-day)', 
                'Trade Distribution'
            ],
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"type": "bar"}]]
        )
        
        # Rolling Sharpe ratio
        rolling_sharpe = portfolio_data['daily_return'].rolling(30).mean() / portfolio_data['daily_return'].rolling(30).std() * np.sqrt(252)
        fig.add_trace(
            go.Scatter(
                x=portfolio_data['date'],
                y=rolling_sharpe,
                name='Rolling Sharpe',
                line=dict(color=self.colors['primary'])
            ),
            row=1, col=1
        )
        
        # Cumulative returns
        cum_returns = (1 + portfolio_data['daily_return']).cumprod() - 1
        fig.add_trace(
            go.Scatter(
                x=portfolio_data['date'],
                y=cum_returns * 100,
                name='Cumulative Returns',
                line=dict(color=self.colors['success'])
            ),
            row=1, col=2
        )
        
        # Rolling volatility
        rolling_vol = portfolio_data['daily_return'].rolling(30).std() * np.sqrt(252) * 100
        fig.add_trace(
            go.Scatter(
                x=portfolio_data['date'],
                y=rolling_vol,
                name='Rolling Volatility',
                line=dict(color=self.colors['danger'])
            ),
            row=2, col=1
        )
        
        # Trade distribution (if position changes available)
        if 'position_changes' in all_data:
            position_changes = all_data['position_changes']
            trade_counts = position_changes['action'].value_counts()
            fig.add_trace(
                go.Bar(
                    x=trade_counts.index,
                    y=trade_counts.values,
                    name='Trade Count',
                    marker_color=[self.colors['success'], self.colors['danger'], self.colors['primary']]
                ),
                row=2, col=2
            )
        
        # Update layout
        fig.update_layout(
            title='Performance Dashboard',
            height=600,
            showlegend=False,
            template='plotly_white'
        )
        
        # Update y-axis labels
        fig.update_yaxes(title_text="Sharpe Ratio", row=1, col=1)
        fig.update_yaxes(title_text="Cumulative Return (%)", row=1, col=2)
        fig.update_yaxes(title_text="Volatility (%)", row=2, col=1)
        fig.update_yaxes(title_text="Trade Count", row=2, col=2)
        
        return fig
    
    def create_trading_activity_chart(self, 
                                    portfolio_data: pd.DataFrame,
                                    position_changes: pd.DataFrame) -> go.Figure:
        """
        Create trading activity overlay on portfolio chart
        
        Args:
            portfolio_data: Portfolio timeline data
            position_changes: Position changes data
            
        Returns:
            Plotly figure with portfolio line and trading signals
        """
        portfolio_data['date'] = pd.to_datetime(portfolio_data['date'])
        position_changes['date'] = pd.to_datetime(position_changes['date'])
        
        fig = go.Figure()
        
        # Portfolio value line
        fig.add_trace(
            go.Scatter(
                x=portfolio_data['date'],
                y=portfolio_data['portfolio_value'],
                name='Portfolio Value',
                line=dict(color=self.colors['primary'], width=2)
            )
        )
        
        # Buy signals
        buy_signals = position_changes[position_changes['action'] == 'BUY']
        if not buy_signals.empty:
            # Match buy signals to portfolio values on those dates
            buy_dates = buy_signals['date'].unique()
            portfolio_values_on_buy_dates = portfolio_data[portfolio_data['date'].isin(buy_dates)]
            
            fig.add_trace(
                go.Scatter(
                    x=portfolio_values_on_buy_dates['date'],
                    y=portfolio_values_on_buy_dates['portfolio_value'],
                    mode='markers',
                    name='Buy Signals',
                    marker=dict(
                        color=self.colors['success'],
                        size=8,
                        symbol='triangle-up'
                    ),
                    hovertemplate='<b>BUY</b><br>Date: %{x}<br>Portfolio: $%{y:,.2f}<extra></extra>'
                )
            )
        
        # Sell signals
        sell_signals = position_changes[position_changes['action'] == 'SELL']
        if not sell_signals.empty:
            sell_dates = sell_signals['date'].unique()
            portfolio_values_on_sell_dates = portfolio_data[portfolio_data['date'].isin(sell_dates)]
            
            fig.add_trace(
                go.Scatter(
                    x=portfolio_values_on_sell_dates['date'],
                    y=portfolio_values_on_sell_dates['portfolio_value'],
                    mode='markers',
                    name='Sell Signals',
                    marker=dict(
                        color=self.colors['danger'],
                        size=8,
                        symbol='triangle-down'
                    ),
                    hovertemplate='<b>SELL</b><br>Date: %{x}<br>Portfolio: $%{y:,.2f}<extra></extra>'
                )
            )
        
        fig.update_layout(
            title='Portfolio Value with Trading Activity',
            xaxis_title='Date',
            yaxis_title='Portfolio Value ($)',
            template='plotly_white',
            hovermode='x unified'
        )
        
        return fig
    
    def create_performance_metrics_chart(self, performance_metrics: dict) -> go.Figure:
        """
        Create performance metrics visualization chart
        
        Args:
            performance_metrics: Dictionary with performance metrics
            
        Returns:
            Plotly figure with metrics visualization
        """
        # Prepare metrics for visualization
        metrics_data = {
            'Risk Metrics': {
                'Sharpe Ratio': performance_metrics.get('sharpe_ratio', 0),
                'Max Drawdown (%)': performance_metrics.get('max_drawdown_pct', 0),
                'Volatility (%)': performance_metrics.get('volatility_pct', 0)
            },
            'Return Metrics': {
                'Total Return (%)': performance_metrics.get('total_return_pct', 0),
                'Average Return (%)': performance_metrics.get('avg_return_pct', 0),
                'Win Rate (%)': performance_metrics.get('win_rate_pct', 0)
            },
            'Trade Metrics': {
                'Profit Factor': performance_metrics.get('profit_factor', 0),
                'Win/Loss Ratio': performance_metrics.get('win_loss_ratio', 0),
                'SQN': performance_metrics.get('sqn', 0),
                'VWR': performance_metrics.get('vwr', 0)
            }
        }
        
        # Create subplots for each category
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=list(metrics_data.keys()) + ['Key Performance Summary'],
            specs=[[{"type": "bar"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "indicator"}]]
        )
        
        colors = [self.colors['primary'], self.colors['success'], self.colors['danger']]
        
        # Add bar charts for each metric category
        for i, (category, metrics) in enumerate(metrics_data.items()):
            row = (i // 2) + 1
            col = (i % 2) + 1
            
            fig.add_trace(
                go.Bar(
                    x=list(metrics.keys()),
                    y=list(metrics.values()),
                    name=category,
                    marker_color=colors[i % len(colors)],
                    text=[f"{v:.3f}" for v in metrics.values()],
                    textposition='auto',
                    hovertemplate='<b>%{x}</b><br>Value: %{y:.3f}<extra></extra>'
                ),
                row=row, col=col
            )
        
        # Add summary indicators in the fourth subplot
        fig.add_trace(
            go.Indicator(
                mode="number+gauge+delta",
                value=performance_metrics.get('sharpe_ratio', 0),
                domain={'row': 1, 'column': 1},
                title={'text': "Sharpe Ratio"},
                gauge={
                    'axis': {'range': [-2, 3]},
                    'bar': {'color': self.colors['primary']},
                    'steps': [
                        {'range': [-2, 0], 'color': "lightgray"},
                        {'range': [0, 1], 'color': "yellow"},
                        {'range': [1, 2], 'color': "orange"},
                        {'range': [2, 3], 'color': "green"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 1.0
                    }
                }
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            title='Performance Metrics Dashboard',
            height=800,
            showlegend=False,
            template='plotly_white'
        )
        
        return fig
    
    def _calculate_metrics(self, portfolio_data: pd.DataFrame) -> pd.DataFrame:
        """Calculate additional metrics for portfolio data"""
        data = portfolio_data.copy()
        
        # Calculate daily returns
        data['daily_return'] = data['portfolio_value'].pct_change().fillna(0)
        
        # Calculate running maximum for drawdown calculation
        data['running_max'] = data['portfolio_value'].expanding().max()
        data['drawdown'] = (data['portfolio_value'] - data['running_max']) / data['running_max']
        
        return data
    
    def save_visualizations(self, 
                          charts: List[go.Figure], 
                          output_dir: str, 
                          filename_prefix: str) -> List[str]:
        """
        Save visualization charts to files
        
        Args:
            charts: List of plotly figures to save
            output_dir: Output directory path
            filename_prefix: Prefix for filenames
            
        Returns:
            List of saved file paths
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        saved_files = []
        
        chart_names = [
            'portfolio_performance',
            'asset_allocation', 
            'performance_dashboard',
            'trading_activity',
            'performance_metrics'
        ]
        
        for i, fig in enumerate(charts):
            if i < len(chart_names):
                chart_name = chart_names[i]
            else:
                chart_name = f'chart_{i+1}'
            
            # Save as interactive HTML
            html_file = output_path / f"{filename_prefix}_{chart_name}.html"
            fig.write_html(str(html_file))
            saved_files.append(str(html_file))
            
            # Save as static PNG
            try:
                png_file = output_path / f"{filename_prefix}_{chart_name}.png"
                fig.write_image(str(png_file), width=1200, height=800, scale=2)
                saved_files.append(str(png_file))
            except Exception as e:
                print(f"Warning: Could not save PNG for {chart_name}: {e}")
        
        return saved_files


def create_portfolio_chart(portfolio_data: pd.DataFrame, 
                         benchmark_data: pd.DataFrame = None,
                         style: str = 'interactive') -> go.Figure:
    """
    Convenience function to create portfolio chart
    
    Args:
        portfolio_data: Portfolio timeline data
        benchmark_data: Optional benchmark data 
        style: 'interactive' or 'static'
        
    Returns:
        Chart figure
    """
    visualizer = PortfolioVisualizer(style=style)
    return visualizer.create_portfolio_chart(portfolio_data, benchmark_data)


def create_allocation_chart(composition_data: pd.DataFrame,
                          style: str = 'interactive') -> go.Figure:
    """
    Convenience function to create allocation chart
    
    Args:
        composition_data: Asset composition data
        style: 'interactive' or 'static'
        
    Returns:
        Chart figure
    """
    visualizer = PortfolioVisualizer(style=style)
    return visualizer.create_allocation_chart(composition_data)


def create_performance_dashboard(all_data: Dict[str, pd.DataFrame],
                               style: str = 'interactive') -> go.Figure:
    """
    Convenience function to create performance dashboard
    
    Args:
        all_data: Dictionary with portfolio and position data
        style: 'interactive' or 'static'
        
    Returns:
        Dashboard figure
    """
    visualizer = PortfolioVisualizer(style=style)
    return visualizer.create_performance_dashboard(all_data)