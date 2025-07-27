from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from enum import Enum
import json
import time

from ..monitoring.event_writer import EventWriter, log_portfolio_event, get_event_writer
from .position_manager import PositionManager, PositionScore, PositionChange, PositionSizeCategory


class EnhancedPositionManager(PositionManager):
    """Position Manager with comprehensive event logging and monitoring"""
    
    def __init__(self, 
                 technical_analyzer=None,
                 fundamental_analyzer=None,
                 asset_manager=None,
                 rebalance_frequency='monthly',
                 max_positions=10,
                 position_sizing_method='kelly',
                 min_score_threshold=0.6,
                 timeframes=['1d', '4h', '1h'],
                 enable_technical_analysis=True,
                 enable_fundamental_analysis=True,
                 technical_weight=0.6,
                 fundamental_weight=0.4,
                 event_writer: EventWriter = None):
        
        super().__init__(
            technical_analyzer=technical_analyzer,
            fundamental_analyzer=fundamental_analyzer,
            asset_manager=asset_manager,
            rebalance_frequency=rebalance_frequency,
            max_positions=max_positions,
            position_sizing_method=position_sizing_method,
            min_score_threshold=min_score_threshold,
            timeframes=timeframes,
            enable_technical_analysis=enable_technical_analysis,
            enable_fundamental_analysis=enable_fundamental_analysis,
            technical_weight=technical_weight,
            fundamental_weight=fundamental_weight
        )
        
        # Event logging
        self.event_writer = event_writer or get_event_writer()
        self._current_trace_id = None
        
        # Log initialization
        self.event_writer.log_event(
            event_type='position_manager_init',
            event_category='system',
            action='init',
            reason='Enhanced position manager initialized',
            metadata={
                'max_positions': max_positions,
                'min_score_threshold': min_score_threshold,
                'rebalance_frequency': rebalance_frequency,
                'technical_enabled': enable_technical_analysis,
                'fundamental_enabled': enable_fundamental_analysis,
                'technical_weight': technical_weight,
                'fundamental_weight': fundamental_weight
            }
        )
    
    @log_portfolio_event('rebalance_check', 'portfolio')
    def should_rebalance(self, current_date: datetime) -> bool:
        """Determine if we should rebalance based on configured frequency"""
        should_rebalance = super().should_rebalance(current_date)
        
        # Log rebalance decision
        days_since = (current_date - self.last_rebalance_date).days if self.last_rebalance_date else 0
        
        self.event_writer.log_event(
            event_type='rebalance_check',
            event_category='portfolio', 
            action='check',
            reason=f'Rebalance {"required" if should_rebalance else "not required"}',
            metadata={
                'should_rebalance': should_rebalance,
                'days_since_last': days_since,
                'frequency': self.rebalance_frequency,
                'last_rebalance_date': self.last_rebalance_date.isoformat() if self.last_rebalance_date else None
            }
        )
        
        return should_rebalance
    
    def analyze_and_score_assets(self, 
                                assets: List[str], 
                                current_date: datetime,
                                regime: str,
                                data_manager) -> List[PositionScore]:
        """Analyze assets and generate position scores with event logging"""
        
        trace_id = self.event_writer.start_trace(f'asset_scoring_batch_{len(assets)}_assets')
        self._current_trace_id = trace_id
        
        start_time = time.time()
        
        try:
            self.event_writer.log_event(
                event_type='asset_scoring_start',
                event_category='scoring',
                action='start',
                reason=f'Starting analysis of {len(assets)} assets',
                regime=regime,
                metadata={
                    'asset_count': len(assets),
                    'assets': assets,
                    'min_score_threshold': self.min_score_threshold,
                    'regime': regime
                }
            )
            
            scores = []
            successful_scores = 0
            failed_scores = 0
            
            for asset in assets:
                try:
                    score = self._score_single_asset_with_logging(asset, current_date, regime, data_manager)
                    if score and score.combined_score >= self.min_score_threshold:
                        scores.append(score)
                        successful_scores += 1
                        
                        # Log individual asset scoring
                        self.event_writer.log_event(
                            event_type='asset_scored',
                            event_category='scoring',
                            action='score',
                            reason=f'Asset scored: {score.combined_score:.3f}',
                            asset=asset,
                            regime=regime,
                            score_after=score.combined_score,
                            size_after=score.position_size_percentage,
                            metadata={
                                'technical_score': score.technical_score,
                                'fundamental_score': score.fundamental_score,
                                'confidence': score.confidence,
                                'position_category': score.position_size_category.name,
                                'timeframes': score.timeframes_analyzed
                            }
                        )
                    elif score:
                        # Asset scored but below threshold
                        self.event_writer.log_event(
                            event_type='threshold_breach',
                            event_category='scoring',
                            action='reject',
                            reason=f'Score {score.combined_score:.3f} below threshold {self.min_score_threshold}',
                            asset=asset,
                            regime=regime,
                            score_after=score.combined_score,
                            metadata={
                                'threshold': self.min_score_threshold,
                                'technical_score': score.technical_score,
                                'fundamental_score': score.fundamental_score
                            }
                        )
                        failed_scores += 1
                except Exception as e:
                    failed_scores += 1
                    self.event_writer.log_error(
                        error_type='asset_scoring',
                        error_message=f'Error scoring {asset}: {str(e)}',
                        asset=asset,
                        metadata={
                            'regime': regime,
                            'error_type': type(e).__name__
                        }
                    )
                    continue
            
            # Sort by combined score descending
            scores.sort(key=lambda x: x.combined_score, reverse=True)
            
            # Limit to max positions
            selected_scores = scores[:self.max_positions]
            
            execution_time = (time.time() - start_time) * 1000
            
            # Log completion
            self.event_writer.log_event(
                event_type='asset_scoring_complete',
                event_category='scoring',
                action='complete',
                reason=f'Scored {successful_scores} assets, {len(selected_scores)} selected',
                regime=regime,
                execution_time_ms=execution_time,
                metadata={
                    'total_processed': len(assets),
                    'successful_scores': successful_scores,
                    'failed_scores': failed_scores,
                    'selected_count': len(selected_scores),
                    'max_positions': self.max_positions,
                    'average_score': np.mean([s.combined_score for s in selected_scores]) if selected_scores else 0
                }
            )
            
            return selected_scores
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            self.event_writer.log_error(
                error_type='asset_scoring_batch',
                error_message=f'Batch scoring failed: {str(e)}',
                metadata={
                    'asset_count': len(assets),
                    'execution_time_ms': execution_time,
                    'error_type': type(e).__name__
                }
            )
            raise
        finally:
            self.event_writer.end_trace(trace_id, success=True)
            self._current_trace_id = None
    
    def _score_single_asset_with_logging(self, 
                                       asset: str, 
                                       current_date: datetime,
                                       regime: str,
                                       data_manager) -> Optional[PositionScore]:
        """Score a single asset with detailed event logging"""
        
        asset_start_time = time.time()
        
        try:
            # Use parent class scoring logic
            score = self._score_single_asset(asset, current_date, regime, data_manager)
            
            asset_execution_time = (time.time() - asset_start_time) * 1000
            
            if score:
                # Log successful asset analysis
                self.event_writer.log_event(
                    event_type='asset_analysis_complete',
                    event_category='scoring',
                    action='analyze',
                    reason=f'Asset analysis completed successfully',
                    asset=asset,
                    regime=regime,
                    score_after=score.combined_score,
                    execution_time_ms=asset_execution_time,
                    metadata={
                        'technical_score': score.technical_score,
                        'fundamental_score': score.fundamental_score,
                        'confidence': score.confidence,
                        'timeframes_count': len(score.timeframes_analyzed),
                        'technical_enabled': self.enable_technical_analysis,
                        'fundamental_enabled': self.enable_fundamental_analysis
                    }
                )
            
            return score
            
        except Exception as e:
            asset_execution_time = (time.time() - asset_start_time) * 1000
            self.event_writer.log_error(
                error_type='asset_analysis',
                error_message=f'Asset analysis failed: {str(e)}',
                asset=asset,
                metadata={
                    'regime': regime,
                    'execution_time_ms': asset_execution_time,
                    'error_type': type(e).__name__
                }
            )
            raise
    
    def calculate_position_changes(self, 
                                 new_scores: List[PositionScore],
                                 current_date: datetime,
                                 regime_changed: bool = False,
                                 valid_buckets: List[str] = None) -> List[PositionChange]:
        """Calculate position changes with comprehensive event logging"""
        
        trace_id = self.event_writer.start_trace('position_change_calculation')
        
        start_time = time.time()
        
        try:
            self.event_writer.log_event(
                event_type='position_change_start',
                event_category='portfolio',
                action='start',
                reason='Starting position change calculation',
                metadata={
                    'current_positions_count': len(self.current_positions),
                    'new_scores_count': len(new_scores),
                    'regime_changed': regime_changed,
                    'valid_buckets': valid_buckets
                }
            )
            
            changes = super().calculate_position_changes(new_scores, current_date, regime_changed, valid_buckets)
            
            # Log each position change
            for change in changes:
                self._log_position_change(change, regime_changed)
            
            execution_time = (time.time() - start_time) * 1000
            
            # Summary logging
            action_counts = {}
            for change in changes:
                action_counts[change.action] = action_counts.get(change.action, 0) + 1
            
            self.event_writer.log_event(
                event_type='position_change_complete',
                event_category='portfolio',
                action='complete',
                reason=f'Position change calculation completed: {len(changes)} changes',
                execution_time_ms=execution_time,
                metadata={
                    'total_changes': len(changes),
                    'action_summary': action_counts,
                    'regime_changed': regime_changed
                }
            )
            
            return changes
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            self.event_writer.log_error(
                error_type='position_change_calculation',
                error_message=f'Position change calculation failed: {str(e)}',
                metadata={
                    'execution_time_ms': execution_time,
                    'current_positions': len(self.current_positions),
                    'new_scores': len(new_scores)
                }
            )
            raise
        finally:
            self.event_writer.end_trace(trace_id)
    
    def _log_position_change(self, change: PositionChange, regime_changed: bool = False):
        """Log individual position change event"""
        
        # Determine event type based on action
        if change.action == 'open':
            event_type = 'position_open'
        elif change.action == 'close':
            event_type = 'position_close'
        elif change.action in ['increase', 'decrease']:
            event_type = 'position_adjust'
        else:
            event_type = 'position_hold'
        
        # Get scores
        score_before = change.previous_score.combined_score if change.previous_score else None
        score_after = change.current_score.combined_score if change.current_score else None
        size_before = change.previous_score.position_size_percentage if change.previous_score else 0.0
        size_after = change.current_score.position_size_percentage if change.current_score else 0.0
        
        # Build metadata
        metadata = {
            'action': change.action,
            'size_change': change.size_change,
            'regime_changed': regime_changed
        }
        
        if change.current_score:
            metadata.update({
                'position_category': change.current_score.position_size_category.name,
                'confidence': change.current_score.confidence,
                'regime': change.current_score.regime
            })
        
        if change.previous_score:
            metadata['previous_category'] = change.previous_score.position_size_category.name
        
        self.event_writer.log_position_event(
            event_type=event_type,
            asset=change.asset,
            action=change.action,
            reason=change.reason,
            score_before=score_before,
            score_after=score_after,
            size_before=size_before,
            size_after=size_after,
            regime=change.current_score.regime if change.current_score else None,
            metadata=metadata
        )
    
    @log_portfolio_event('portfolio_update', 'portfolio')
    def update_positions(self, new_scores: List[PositionScore], current_date: datetime):
        """Update current positions and history with event logging"""
        
        trace_id = self.event_writer.start_trace('portfolio_update')
        
        try:
            # Track changes before update
            previous_allocation = sum(pos.position_size_percentage for pos in self.current_positions.values())
            previous_count = len(self.current_positions)
            
            # Update positions using parent logic
            super().update_positions(new_scores, current_date)
            
            # Calculate new allocation and stats
            new_allocation = sum(pos.position_size_percentage for pos in self.current_positions.values())
            new_count = len(self.current_positions)
            avg_score = np.mean([pos.combined_score for pos in self.current_positions.values()]) if self.current_positions else 0
            
            # Log portfolio update
            self.event_writer.log_event(
                event_type='portfolio_update',
                event_category='portfolio',
                action='update',
                reason=f'Portfolio updated: {new_count} positions, {new_allocation:.1%} allocated',
                portfolio_allocation=new_allocation,
                active_positions=new_count,
                metadata={
                    'previous_allocation': previous_allocation,
                    'previous_count': previous_count,
                    'allocation_change': new_allocation - previous_allocation,
                    'position_count_change': new_count - previous_count,
                    'average_score': avg_score,
                    'assets': list(self.current_positions.keys())
                }
            )
            
            # Log individual position updates
            for asset, position in self.current_positions.items():
                self.event_writer.log_event(
                    event_type='position_update',
                    event_category='portfolio',
                    action='update',
                    reason=f'Position updated in portfolio',
                    asset=asset,
                    score_after=position.combined_score,
                    size_after=position.position_size_percentage,
                    regime=position.regime,
                    metadata={
                        'technical_score': position.technical_score,
                        'fundamental_score': position.fundamental_score,
                        'confidence': position.confidence,
                        'position_category': position.position_size_category.name
                    }
                )
            
        except Exception as e:
            self.event_writer.log_error(
                error_type='portfolio_update',
                error_message=f'Portfolio update failed: {str(e)}',
                metadata={
                    'new_positions_count': len(new_scores),
                    'error_type': type(e).__name__
                }
            )
            raise
        finally:
            self.event_writer.end_trace(trace_id)
    
    def get_position_summary_with_events(self) -> Dict:
        """Get position summary with event logging"""
        
        summary = super().get_position_summary()
        
        # Log summary request
        self.event_writer.log_event(
            event_type='portfolio_summary',
            event_category='portfolio',
            action='summary',
            reason='Portfolio summary requested',
            portfolio_allocation=summary['total_allocation'],
            active_positions=summary['total_positions'],
            metadata={
                'average_score': summary['average_score'],
                'positions_summary': summary['positions']
            }
        )
        
        return summary
    
    def export_position_history_with_events(self, filepath: str):
        """Export position history with event logging"""
        
        try:
            super().export_position_history(filepath)
            
            total_records = sum(len(scores) for scores in self.position_history.values())
            
            self.event_writer.log_event(
                event_type='data_export',
                event_category='system',
                action='export',
                reason=f'Position history exported to {filepath}',
                metadata={
                    'filepath': filepath,
                    'total_records': total_records,
                    'assets_count': len(self.position_history),
                    'export_type': 'position_history'
                }
            )
            
        except Exception as e:
            self.event_writer.log_error(
                error_type='data_export',
                error_message=f'Position history export failed: {str(e)}',
                metadata={
                    'filepath': filepath,
                    'export_type': 'position_history'
                }
            )
            raise