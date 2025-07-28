"""
Enhanced Data Export Functions

Provides comprehensive CSV export capabilities for portfolio analysis:
- Portfolio timeline with daily metrics
- Position changes with trading decisions
- Asset composition over time
- Regime analysis data
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import sys
import os

# Add monitoring module to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
try:
    from monitoring.event_store import EventStore
    from monitoring.event_models import EventQuery
    EVENT_SYSTEM_AVAILABLE = True
except ImportError:
    EVENT_SYSTEM_AVAILABLE = False
    # Create dummy classes for type hints when event system is not available
    class EventStore:
        pass


class PortfolioDataExporter:
    """Main class for exporting portfolio data to various CSV formats"""
    
    def __init__(self, output_dir: str = "results"):
        """
        Initialize exporter
        
        Args:
            output_dir: Base directory to save CSV files (will create dated subdirectories)
        """
        self.base_output_dir = Path(output_dir)
        self.base_output_dir.mkdir(exist_ok=True)
        self.output_dir = None  # Will be set when creating export package
    
    def export_portfolio_timeline(self, 
                                strategy, 
                                filename_prefix: str,
                                benchmark_data: Optional[pd.DataFrame] = None) -> str:
        """
        Export portfolio timeline CSV with daily metrics
        
        Args:
            strategy: Backtrader strategy with analyzers
            filename_prefix: Prefix for output filename
            benchmark_data: Optional benchmark data for comparison
            
        Returns:
            Path to saved CSV file
        """
        # Get portfolio timeline from custom analyzer
        portfolio_tracker = strategy.analyzers.portfolio_tracker.get_analysis()
        timeline_data = portfolio_tracker.get('portfolio_timeline', [])
        
        if not timeline_data:
            raise ValueError("No portfolio timeline data available")
        
        # Convert to DataFrame
        df = pd.DataFrame(timeline_data)
        df['date'] = pd.to_datetime(df['date'])
        
        # Calculate additional metrics
        df = self._calculate_timeline_metrics(df, benchmark_data)
        
        # Select and order columns for CSV
        columns = [
            'date', 'portfolio_value', 'cash', 'total_positions',
            'daily_return', 'cumulative_return', 'drawdown_pct',
            'sharpe_30d', 'regime', 'regime_confidence'
        ]
        
        # Add benchmark columns if available
        if benchmark_data is not None:
            columns.extend(['benchmark_value', 'benchmark_return', 'excess_return'])
        
        # Filter to available columns
        available_columns = [col for col in columns if col in df.columns]
        export_df = df[available_columns].copy()
        
        # Format for CSV export
        export_df = self._format_for_csv(export_df)
        
        # Save to CSV
        filename = f"{filename_prefix}_portfolio_timeline.csv"
        filepath = self.output_dir / filename
        export_df.to_csv(filepath, index=False)
        
        return str(filepath)
    
    def export_position_changes(self, 
                              strategy,
                              filename_prefix: str) -> str:
        """
        Export position changes CSV with all trading decisions
        
        Args:
            strategy: Backtrader strategy with analyzers
            filename_prefix: Prefix for output filename
            
        Returns:
            Path to saved CSV file
        """
        # Get position changes from custom analyzer
        position_tracker = strategy.analyzers.position_tracker.get_analysis()
        changes_data = position_tracker.get('position_changes', [])
        
        if not changes_data:
            # Create empty structure if no changes
            changes_data = []
        
        # Convert to DataFrame
        df = pd.DataFrame(changes_data)
        
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            
            # Select and order columns for CSV
            columns = [
                'date', 'asset', 'action', 'quantity', 'price', 'value',
                'reason', 'score_before', 'score_after', 'bucket', 'regime'
            ]
            
            # Filter to available columns
            available_columns = [col for col in columns if col in df.columns]
            export_df = df[available_columns].copy()
            
            # Format for CSV export
            export_df = self._format_for_csv(export_df)
        else:
            # Create empty DataFrame with expected columns
            export_df = pd.DataFrame(columns=[
                'date', 'asset', 'action', 'quantity', 'price', 'value',
                'reason', 'score_before', 'score_after', 'bucket', 'regime'
            ])
        
        # Save to CSV
        filename = f"{filename_prefix}_position_changes.csv"
        filepath = self.output_dir / filename
        export_df.to_csv(filepath, index=False)
        
        return str(filepath)
    
    def export_asset_composition(self, 
                               strategy,
                               filename_prefix: str) -> str:
        """
        Export asset composition CSV with daily holdings and weights
        
        Args:
            strategy: Backtrader strategy with analyzers
            filename_prefix: Prefix for output filename
            
        Returns:
            Path to saved CSV file
        """
        # Get portfolio timeline data
        portfolio_tracker = strategy.analyzers.portfolio_tracker.get_analysis()
        timeline_data = portfolio_tracker.get('portfolio_timeline', [])
        
        if not timeline_data:
            raise ValueError("No portfolio timeline data available")
        
        # Extract position details for each date
        composition_records = []
        
        for day_data in timeline_data:
            date = day_data['date']
            total_value = day_data['portfolio_value']
            position_details = day_data.get('position_details', {})
            
            for asset, details in position_details.items():
                size = details.get('size', 0)
                price = details.get('price', 0)
                market_value = details.get('value', size * price)
                weight_pct = (market_value / total_value * 100) if total_value > 0 else 0
                
                # Calculate days held (simplified - would need position tracking for accuracy)
                days_held = 1  # Placeholder
                
                # Get additional info (these would come from strategy context)
                score = getattr(strategy, f'{asset}_current_score', 0.0)
                bucket = getattr(strategy, f'{asset}_bucket', 'Unknown')
                is_core_asset = getattr(strategy, f'{asset}_is_core', False)
                
                composition_records.append({
                    'date': date,
                    'asset': asset,
                    'shares': abs(size),
                    'price': price,
                    'market_value': market_value,
                    'weight_pct': weight_pct,
                    'score': score,
                    'bucket': bucket,
                    'days_held': days_held,
                    'is_core_asset': is_core_asset
                })
        
        # Convert to DataFrame
        df = pd.DataFrame(composition_records)
        
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            
            # Format for CSV export
            df = self._format_for_csv(df)
        else:
            # Create empty DataFrame with expected columns
            df = pd.DataFrame(columns=[
                'date', 'asset', 'shares', 'price', 'market_value', 'weight_pct',
                'score', 'bucket', 'days_held', 'is_core_asset'
            ])
        
        # Save to CSV
        filename = f"{filename_prefix}_asset_composition.csv"
        filepath = self.output_dir / filename
        df.to_csv(filepath, index=False)
        
        return str(filepath)
    
    def export_regime_analysis(self, 
                             strategy,
                             filename_prefix: str) -> str:
        """
        Export regime analysis CSV with regime transitions and performance
        
        Args:
            strategy: Backtrader strategy with analyzers
            filename_prefix: Prefix for output filename
            
        Returns:
            Path to saved CSV file
        """
        # Get portfolio timeline data
        portfolio_tracker = strategy.analyzers.portfolio_tracker.get_analysis()
        timeline_data = portfolio_tracker.get('portfolio_timeline', [])
        
        if not timeline_data:
            raise ValueError("No portfolio timeline data available")
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(timeline_data)
        df['date'] = pd.to_datetime(df['date'])
        
        # Calculate daily returns
        df['daily_return'] = df['portfolio_value'].pct_change().fillna(0)
        
        # Identify regime changes and calculate regime-specific metrics
        regime_records = []
        current_regime = None
        regime_start_date = None
        regime_start_value = None
        
        for idx, row in df.iterrows():
            regime = row['regime']
            
            # Check for regime change
            if regime != current_regime:
                # Save previous regime data if exists
                if current_regime is not None and regime_start_date is not None:
                    end_date = row['date']
                    end_value = df.iloc[idx-1]['portfolio_value'] if idx > 0 else regime_start_value
                    duration_days = (end_date - regime_start_date).days
                    
                    # Calculate return during regime
                    regime_return = ((end_value - regime_start_value) / regime_start_value * 100) if regime_start_value > 0 else 0
                    
                    # Get regime metadata (would come from strategy)
                    confidence = df.iloc[idx-1]['regime_confidence'] if idx > 0 else 0.0
                    stability = getattr(strategy, f'{current_regime}_stability', 0.0)
                    active_buckets = getattr(strategy, f'{current_regime}_buckets', 'Unknown')
                    
                    regime_records.append({
                        'date': regime_start_date,
                        'regime': current_regime,
                        'confidence': confidence,
                        'stability': stability,
                        'duration_days': duration_days,
                        'active_buckets': active_buckets,
                        'portfolio_return_in_regime': regime_return
                    })
                
                # Start new regime tracking
                current_regime = regime
                regime_start_date = row['date']
                regime_start_value = row['portfolio_value']
        
        # Handle last regime
        if current_regime is not None and regime_start_date is not None:
            end_date = df.iloc[-1]['date']
            end_value = df.iloc[-1]['portfolio_value']
            duration_days = (end_date - regime_start_date).days
            
            regime_return = ((end_value - regime_start_value) / regime_start_value * 100) if regime_start_value > 0 else 0
            confidence = df.iloc[-1]['regime_confidence']
            stability = getattr(strategy, f'{current_regime}_stability', 0.0)
            active_buckets = getattr(strategy, f'{current_regime}_buckets', 'Unknown')
            
            regime_records.append({
                'date': regime_start_date,
                'regime': current_regime,
                'confidence': confidence,
                'stability': stability,
                'duration_days': duration_days,
                'active_buckets': active_buckets,
                'portfolio_return_in_regime': regime_return
            })
        
        # Convert to DataFrame
        regime_df = pd.DataFrame(regime_records)
        
        if not regime_df.empty:
            # Format for CSV export
            regime_df = self._format_for_csv(regime_df)
        else:
            # Create empty DataFrame with expected columns
            regime_df = pd.DataFrame(columns=[
                'date', 'regime', 'confidence', 'stability', 'duration_days',
                'active_buckets', 'portfolio_return_in_regime'
            ])
        
        # Save to CSV
        filename = f"{filename_prefix}_regime_analysis.csv"
        filepath = self.output_dir / filename
        regime_df.to_csv(filepath, index=False)
        
        return str(filepath)
    
    def create_enhanced_export_package(self, 
                                     strategy,
                                     tickers: List[str], 
                                     start_date: datetime, 
                                     end_date: datetime,
                                     benchmark_data: Optional[pd.DataFrame] = None,
                                     enable_event_integration: bool = True) -> Dict[str, str]:
        """
        Create complete enhanced export package with all CSV files
        
        Args:
            strategy: Backtrader strategy with analyzers
            tickers: List of tickers (for filename)
            start_date: Backtest start date
            end_date: Backtest end date
            benchmark_data: Optional benchmark data
            enable_event_integration: Whether to integrate with event system
            
        Returns:
            Dictionary mapping export type to file path
        """
        # Create date-based folder structure
        run_date = datetime.now().strftime('%Y%m%d_%H%M%S')
        start_str = start_date.strftime('%Y%m%d')
        end_str = end_date.strftime('%Y%m%d')
        
        # Create folder name: run_YYYYMMDD_HHMMSS_from_YYYYMMDD_to_YYYYMMDD
        folder_name = f"run_{run_date}_from_{start_str}_to_{end_str}"
        self.output_dir = self.base_output_dir / folder_name
        self.output_dir.mkdir(exist_ok=True)
        
        # Create filename prefix with same structure
        # Create clean filename prefix without ticker names
        filename_prefix = f"backtest_{run_date}_from_{start_str}_to_{end_str}"
        
        export_files = {}
        
        # Phase 4: Event system integration
        event_store = None
        session_id = None
        if enable_event_integration and EVENT_SYSTEM_AVAILABLE:
            try:
                event_store = EventStore()
                session_id = get_session_id_from_strategy(strategy)
                if session_id:
                    print(f"Event integration enabled for session: {session_id}")
                else:
                    print("Event integration available but no session ID found")
            except Exception as e:
                print(f"Warning: Could not initialize event store: {e}")
        
        try:
            # Export portfolio timeline (with event correlation if available)
            if event_store and session_id:
                # Use event-enhanced timeline
                enhanced_timeline = correlate_events_with_portfolio_timeline(
                    strategy, event_store, session_id
                )
                if not enhanced_timeline.empty:
                    # Export enhanced timeline to CSV
                    timeline_filename = f"{filename_prefix}_portfolio_timeline_enhanced.csv"
                    timeline_filepath = self.output_dir / timeline_filename
                    enhanced_timeline.to_csv(timeline_filepath, index=False)
                    export_files['portfolio_timeline_enhanced'] = str(timeline_filepath)
            
            # Standard portfolio timeline export
            timeline_file = self.export_portfolio_timeline(
                strategy, filename_prefix, benchmark_data
            )
            export_files['portfolio_timeline'] = timeline_file
            
            # Export position changes (with event data if available)
            if event_store and session_id:
                # Try to get enhanced position data from events
                event_positions = extract_trading_decisions_from_events(session_id, event_store)
                if not event_positions.empty:
                    # Export event-based position data
                    events_filename = f"{filename_prefix}_position_changes_from_events.csv"
                    events_filepath = self.output_dir / events_filename
                    event_positions.to_csv(events_filepath, index=False)
                    export_files['position_changes_from_events'] = str(events_filepath)
            
            # Standard position changes export
            changes_file = self.export_position_changes(
                strategy, filename_prefix
            )
            export_files['position_changes'] = changes_file
            
            # Export asset composition
            composition_file = self.export_asset_composition(
                strategy, filename_prefix
            )
            export_files['asset_composition'] = composition_file
            
            # Export regime analysis
            regime_file = self.export_regime_analysis(
                strategy, filename_prefix
            )
            export_files['regime_analysis'] = regime_file
            
        except Exception as e:
            print(f"Warning: Error during enhanced export: {e}")
        
        return export_files
    
    def _calculate_timeline_metrics(self, 
                                   df: pd.DataFrame,
                                   benchmark_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Calculate additional metrics for portfolio timeline"""
        
        # Calculate daily returns
        df['daily_return'] = df['portfolio_value'].pct_change().fillna(0)
        
        # Calculate cumulative returns
        df['cumulative_return'] = (1 + df['daily_return']).cumprod() - 1
        
        # Calculate drawdown
        df['running_max'] = df['portfolio_value'].expanding().max()
        df['drawdown_pct'] = ((df['portfolio_value'] - df['running_max']) / df['running_max'] * 100).fillna(0)
        
        # Calculate rolling 30-day Sharpe ratio
        df['sharpe_30d'] = (
            df['daily_return'].rolling(30).mean() / 
            df['daily_return'].rolling(30).std() * 
            np.sqrt(252)
        ).fillna(0)
        
        # Add benchmark metrics if provided
        if benchmark_data is not None:
            benchmark_data = benchmark_data.copy()
            benchmark_data['date'] = pd.to_datetime(benchmark_data['date'])
            
            # Merge with portfolio data
            df = df.merge(benchmark_data, on='date', how='left', suffixes=('', '_benchmark'))
            
            # Calculate benchmark returns and excess returns
            if 'value' in benchmark_data.columns:
                df['benchmark_value'] = df['value']
                df['benchmark_return'] = df['benchmark_value'].pct_change().fillna(0)
                df['excess_return'] = df['daily_return'] - df['benchmark_return']
        
        return df
    
    def _format_for_csv(self, df: pd.DataFrame) -> pd.DataFrame:
        """Format DataFrame for clean CSV export"""
        df = df.copy()
        
        # Format date columns
        date_columns = ['date']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col]).dt.strftime('%Y-%m-%d')
        
        # Round numeric columns
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            if 'pct' in col or 'return' in col or 'ratio' in col:
                df[col] = df[col].round(4)
            elif 'value' in col or 'price' in col:
                df[col] = df[col].round(2)
            elif 'score' in col or 'confidence' in col:
                df[col] = df[col].round(3)
            else:
                df[col] = df[col].round(6)
        
        # Handle boolean columns
        bool_columns = df.select_dtypes(include=[bool]).columns
        for col in bool_columns:
            df[col] = df[col].astype(str).str.lower()
        
        return df


# Phase 4: Event System Integration Functions
def extract_trading_decisions_from_events(session_id: str, event_store: Optional[EventStore] = None) -> pd.DataFrame:
    """
    Extract position decisions from event log for enhanced CSV export
    
    Args:
        session_id: Session ID to query events for
        event_store: EventStore instance (creates new one if None)
        
    Returns:
        DataFrame with trading decisions from event logs
    """
    if not EVENT_SYSTEM_AVAILABLE:
        print("Warning: Event system not available, returning empty DataFrame")
        return pd.DataFrame(columns=['date', 'asset', 'action', 'reason', 'score_before', 'score_after'])
    
    if event_store is None:
        event_store = EventStore()
    
    try:
        # Get all events for this session
        session_events = event_store.get_session_events(session_id)
        
        if not session_events:
            return pd.DataFrame(columns=['date', 'asset', 'action', 'reason', 'score_before', 'score_after'])
        
        # Filter for position-related events
        position_events = [
            event for event in session_events 
            if event.get('event_category') == 'position' and event.get('action') in ['BUY', 'SELL', 'HOLD']
        ]
        
        if not position_events:
            return pd.DataFrame(columns=['date', 'asset', 'action', 'reason', 'score_before', 'score_after'])
        
        # Convert to DataFrame
        decisions_data = []
        for event in position_events:
            decisions_data.append({
                'date': event.get('timestamp'),
                'asset': event.get('asset', 'Unknown'),
                'action': event.get('action', 'Unknown'),
                'reason': event.get('reason', 'No reason provided'),
                'score_before': event.get('score_before', 0.0),
                'score_after': event.get('score_after', 0.0),
                'size_before': event.get('size_before', 0.0),
                'size_after': event.get('size_after', 0.0),
                'regime': event.get('regime', 'Unknown'),
                'trace_id': event.get('trace_id', ''),
                'portfolio_allocation': event.get('portfolio_allocation', 0.0)
            })
        
        df = pd.DataFrame(decisions_data)
        df['date'] = pd.to_datetime(df['date'])
        
        return df
        
    except Exception as e:
        print(f"Warning: Failed to extract trading decisions from events: {e}")
        return pd.DataFrame(columns=['date', 'asset', 'action', 'reason', 'score_before', 'score_after'])


def correlate_events_with_portfolio_timeline(strategy, event_store: Optional[EventStore] = None, session_id: Optional[str] = None) -> pd.DataFrame:
    """
    Merge portfolio value data with event context for enhanced analysis
    
    Args:
        strategy: Backtrader strategy with analyzers
        event_store: EventStore instance (creates new one if None)
        session_id: Session ID to correlate events with
        
    Returns:
        Enhanced portfolio timeline DataFrame with event context
    """
    # Get base portfolio timeline from analyzers
    portfolio_tracker = strategy.analyzers.portfolio_tracker.get_analysis()
    timeline_data = portfolio_tracker.get('portfolio_timeline', [])
    
    if not timeline_data:
        return pd.DataFrame()
    
    # Convert to DataFrame
    df = pd.DataFrame(timeline_data)
    df['date'] = pd.to_datetime(df['date'])
    
    # Add event context if available
    if EVENT_SYSTEM_AVAILABLE and event_store is not None and session_id:
        try:
            # Get events for this session
            session_events = event_store.get_session_events(session_id)
            
            if session_events:
                # Group events by date
                events_by_date = {}
                for event in session_events:
                    event_date = pd.to_datetime(event['timestamp']).date()
                    if event_date not in events_by_date:
                        events_by_date[event_date] = []
                    events_by_date[event_date].append(event)
                
                # Add event context to each timeline entry
                event_context_data = []
                for _, row in df.iterrows():
                    date_key = row['date'].date()
                    events_on_date = events_by_date.get(date_key, [])
                    
                    # Aggregate event information for this date
                    position_events = [e for e in events_on_date if e.get('event_category') == 'position']
                    regime_events = [e for e in events_on_date if e.get('event_category') == 'regime']
                    protection_events = [e for e in events_on_date if e.get('event_category') == 'protection']
                    
                    event_context_data.append({
                        'date': row['date'],
                        'position_events_count': len(position_events),
                        'regime_events_count': len(regime_events),
                        'protection_events_count': len(protection_events),
                        'total_events': len(events_on_date),
                        'primary_regime': regime_events[0].get('regime') if regime_events else 'Unknown',
                        'protection_triggers': len([e for e in protection_events if 'blocked' in e.get('reason', '').lower()])
                    })
                
                # Merge with portfolio data
                event_df = pd.DataFrame(event_context_data)
                df = df.merge(event_df, on='date', how='left')
                
                # Fill NaN values for dates without events
                event_columns = ['position_events_count', 'regime_events_count', 'protection_events_count', 'total_events', 'protection_triggers']
                for col in event_columns:
                    if col in df.columns:
                        df[col] = df[col].fillna(0).astype(int)
                
                if 'primary_regime' in df.columns:
                    df['primary_regime'] = df['primary_regime'].fillna('Unknown')
                    
        except Exception as e:
            print(f"Warning: Failed to correlate events with portfolio timeline: {e}")
    
    return df


def get_session_id_from_strategy(strategy) -> Optional[str]:
    """
    Extract session ID from strategy if available
    
    Args:
        strategy: Backtrader strategy instance
        
    Returns:
        Session ID string or None if not available
    """
    # Try to get session ID from various possible sources
    if hasattr(strategy, 'session_id'):
        return strategy.session_id
    
    if hasattr(strategy, '_session_id'):
        return strategy._session_id
        
    if hasattr(strategy, 'rebalancer') and hasattr(strategy.rebalancer, 'session_id'):
        return strategy.rebalancer.session_id
        
    if hasattr(strategy, 'params') and hasattr(strategy.params, 'session_id'):
        return strategy.params.session_id
    
    return None


# Convenience functions for backward compatibility
def export_portfolio_timeline(strategy, output_dir: str = "results") -> str:
    """Convenience function to export portfolio timeline"""
    exporter = PortfolioDataExporter(output_dir)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return exporter.export_portfolio_timeline(strategy, f"portfolio_{timestamp}")


def export_position_changes(strategy, output_dir: str = "results") -> str:
    """Convenience function to export position changes"""
    exporter = PortfolioDataExporter(output_dir)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return exporter.export_position_changes(strategy, f"positions_{timestamp}")


def export_asset_composition(strategy, output_dir: str = "results") -> str:
    """Convenience function to export asset composition"""
    exporter = PortfolioDataExporter(output_dir)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return exporter.export_asset_composition(strategy, f"composition_{timestamp}")


def export_regime_analysis(strategy, output_dir: str = "results") -> str:
    """Convenience function to export regime analysis"""
    exporter = PortfolioDataExporter(output_dir)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M_S')
    return exporter.export_regime_analysis(strategy, f"regime_{timestamp}")


def create_enhanced_export_package(strategy, 
                                 tickers: List[str], 
                                 start_date: datetime, 
                                 end_date: datetime, 
                                 output_dir: str = "results") -> Dict[str, str]:
    """Convenience function to create complete export package"""
    exporter = PortfolioDataExporter(output_dir)
    return exporter.create_enhanced_export_package(strategy, tickers, start_date, end_date)