from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, date
import pandas as pd
import numpy as np
from enum import Enum
import json


class PositionSizeCategory(Enum):
    NO_POSITION = 0.0
    LIGHT = 0.25
    HALF = 0.5
    STANDARD = 0.75
    MAX = 1.0


@dataclass
class PositionScore:
    asset: str
    date: datetime
    technical_score: float
    fundamental_score: float
    combined_score: float
    position_size_category: PositionSizeCategory
    position_size_percentage: float
    confidence: float
    regime: str
    timeframes_analyzed: List[str]
    
    def to_dict(self):
        return {
            'asset': self.asset,
            'date': self.date.isoformat(),
            'technical_score': self.technical_score,
            'fundamental_score': self.fundamental_score,
            'combined_score': self.combined_score,
            'position_size_category': self.position_size_category.name,
            'position_size_percentage': self.position_size_percentage,
            'confidence': self.confidence,
            'regime': self.regime,
            'timeframes_analyzed': self.timeframes_analyzed
        }


@dataclass
class PositionChange:
    asset: str
    previous_score: Optional[PositionScore]
    current_score: PositionScore
    action: str  # 'open', 'increase', 'decrease', 'close', 'hold'
    size_change: float
    reason: str


class PositionManager:
    def __init__(self, 
                 technical_analyzer=None,
                 fundamental_analyzer=None,
                 asset_manager=None,
                 rebalance_frequency='monthly',  # 'daily', 'weekly', 'monthly'
                 max_positions=10,
                 position_sizing_method='kelly',  # 'equal', 'kelly', 'risk_parity'
                 min_score_threshold=0.6,
                 timeframes=['1d', '4h', '1h'],
                 enable_technical_analysis=True,
                 enable_fundamental_analysis=True,
                 technical_weight=0.6,
                 fundamental_weight=0.4):
        
        self.technical_analyzer = technical_analyzer
        self.fundamental_analyzer = fundamental_analyzer
        self.asset_manager = asset_manager
        self.rebalance_frequency = rebalance_frequency
        self.max_positions = max_positions
        self.position_sizing_method = position_sizing_method
        self.min_score_threshold = min_score_threshold
        self.timeframes = timeframes
        
        # Analysis enable/disable flags
        self.enable_technical_analysis = enable_technical_analysis
        self.enable_fundamental_analysis = enable_fundamental_analysis
        
        # Position sizing weights (will be adjusted based on enabled analysis)
        self.technical_weight = technical_weight
        self.fundamental_weight = fundamental_weight
        
        # Validate configuration
        self._validate_analysis_configuration()
        
        # Track position scores over time
        self.position_history: Dict[str, List[PositionScore]] = {}
        self.current_positions: Dict[str, PositionScore] = {}
        self.last_rebalance_date: Optional[datetime] = None
        
        # Risk management parameters
        self.max_position_size = 0.2  # 20% max per position
        self.min_position_size = 0.01  # 1% min per position
    
    def _validate_analysis_configuration(self):
        """Validate analysis configuration to ensure at least one type is enabled"""
        if not self.enable_technical_analysis and not self.enable_fundamental_analysis:
            raise ValueError(
                "At least one analysis type must be enabled. "
                "Cannot disable both technical and fundamental analysis."
            )
        
        # Warn about analyzer availability
        if self.enable_technical_analysis and self.technical_analyzer is None:
            print("WARNING: Technical analysis enabled but no technical analyzer provided")
        
        if self.enable_fundamental_analysis and self.fundamental_analyzer is None:
            print("WARNING: Fundamental analysis enabled but no fundamental analyzer provided")
        
        # Log configuration
        analysis_types = []
        if self.enable_technical_analysis:
            analysis_types.append(f"Technical ({self.technical_weight:.1%})")
        if self.enable_fundamental_analysis:
            analysis_types.append(f"Fundamental ({self.fundamental_weight:.1%})")
        
        print(f"Position Manager Analysis Configuration: {', '.join(analysis_types)}")
        
    def should_rebalance(self, current_date: datetime) -> bool:
        """Determine if we should rebalance based on configured frequency"""
        if self.last_rebalance_date is None:
            return True
        
        days_since_rebalance = (current_date - self.last_rebalance_date).days
        
        if self.rebalance_frequency == 'daily':
            return days_since_rebalance >= 1
        elif self.rebalance_frequency == 'weekly':
            return days_since_rebalance >= 7
        elif self.rebalance_frequency == 'monthly':
            return days_since_rebalance >= 30
        else:
            return days_since_rebalance >= 30  # Default to monthly
    
    def analyze_and_score_assets(self, 
                                assets: List[str], 
                                current_date: datetime,
                                regime: str,
                                data_manager) -> List[PositionScore]:
        """Analyze assets and generate position scores"""
        scores = []
        
        for asset in assets:
            try:
                score = self._score_single_asset(asset, current_date, regime, data_manager)
                if score and score.combined_score >= self.min_score_threshold:
                    scores.append(score)
            except Exception as e:
                print(f"Error scoring {asset}: {e}")
                continue
        
        # Sort by combined score descending
        scores.sort(key=lambda x: x.combined_score, reverse=True)
        
        # Limit to max positions
        return scores[:self.max_positions]
    
    def _score_single_asset(self, 
                           asset: str, 
                           current_date: datetime,
                           regime: str,
                           data_manager) -> Optional[PositionScore]:
        """Score a single asset using technical and fundamental analysis"""
        
        # Get multi-timeframe data using new provider system
        timeframe_data = {}
        
        # Check if data_manager supports multi-timeframe fetching
        if hasattr(data_manager, 'timeframe_manager'):
            # Use new TimeframeManager for multi-timeframe data
            try:
                # Convert date to datetime if needed
                if isinstance(current_date, date):
                    current_date = datetime.combine(current_date, datetime.min.time())
                
                # Calculate date range for analysis (typically last 100 trading days)
                end_date = current_date
                start_date = current_date - timedelta(days=200)  # ~100 trading days
                
                timeframe_data = data_manager.timeframe_manager.get_multi_timeframe_data(
                    ticker=asset,
                    timeframes=self.timeframes,
                    start_date=start_date,
                    end_date=end_date
                )
                
                # Filter out empty datasets
                timeframe_data = {tf: data for tf, data in timeframe_data.items() 
                                if data is not None and not data.empty}
                
            except Exception as e:
                print(f"Error fetching multi-timeframe data for {asset}: {e}")
                # Fallback to legacy method
                for timeframe in self.timeframes:
                    data = self._get_timeframe_data(asset, current_date, timeframe, data_manager)
                    if data is not None and not data.empty:
                        timeframe_data[timeframe] = data
        else:
            # Legacy single-timeframe approach
            for timeframe in self.timeframes:
                data = self._get_timeframe_data(asset, current_date, timeframe, data_manager)
                if data is not None and not data.empty:
                    timeframe_data[timeframe] = data
        
        if not timeframe_data:
            return None
        
        # Technical analysis across timeframes
        technical_score = 0.0
        if self.enable_technical_analysis and self.technical_analyzer and timeframe_data:
            try:
                technical_score = self.technical_analyzer.analyze_multi_timeframe(
                    timeframe_data, asset, current_date
                )
            except Exception as e:
                print(f"Technical analysis failed for {asset}: {e}")
                technical_score = 0.5  # Default to neutral if technical analysis fails
        elif self.enable_technical_analysis and not timeframe_data:
            technical_score = 0.5  # Neutral score if no data available
        
        # Fundamental analysis
        fundamental_score = 0.0
        if self.enable_fundamental_analysis and self.fundamental_analyzer:
            fundamental_score = self.fundamental_analyzer.analyze_asset(
                asset, current_date, regime
            )
        
        # Determine effective weights based on configuration and data availability
        if not self.enable_technical_analysis:
            # Fundamental only
            effective_technical_weight = 0.0
            effective_fundamental_weight = 1.0
            combined_score = fundamental_score
        elif not self.enable_fundamental_analysis:
            # Technical only
            effective_technical_weight = 1.0
            effective_fundamental_weight = 0.0
            combined_score = technical_score
        else:
            # Both enabled - handle missing data gracefully
            if fundamental_score == 0.0:
                # If no fundamental score available, use technical only
                effective_technical_weight = 1.0
                effective_fundamental_weight = 0.0
                combined_score = technical_score
            else:
                # Both scores available, use configured weights
                effective_technical_weight = self.technical_weight
                effective_fundamental_weight = self.fundamental_weight
                # Normalize weights to sum to 1.0
                total_weight = effective_technical_weight + effective_fundamental_weight
                if total_weight > 0:
                    effective_technical_weight /= total_weight
                    effective_fundamental_weight /= total_weight
        
        combined_score = (
            technical_score * effective_technical_weight + 
            fundamental_score * effective_fundamental_weight
        )
        
        # Determine position size
        position_size_category, position_size_percentage = self._determine_position_size(
            combined_score, technical_score, fundamental_score
        )
        
        # Calculate confidence based on score consistency
        confidence = self._calculate_confidence(technical_score, fundamental_score)
        
        return PositionScore(
            asset=asset,
            date=current_date,
            technical_score=technical_score,
            fundamental_score=fundamental_score,
            combined_score=combined_score,
            position_size_category=position_size_category,
            position_size_percentage=position_size_percentage,
            confidence=confidence,
            regime=regime,
            timeframes_analyzed=list(timeframe_data.keys())
        )
    
    def _get_timeframe_data(self, 
                           asset: str, 
                           current_date: datetime, 
                           timeframe: str, 
                           data_manager) -> Optional[pd.DataFrame]:
        """Get data for specific timeframe"""
        try:
            # Convert date to datetime if needed
            if isinstance(current_date, date):
                current_date = datetime.combine(current_date, datetime.min.time())
            
            # Calculate appropriate lookback period based on timeframe
            if timeframe == '1h':
                lookback_days = 30  # 30 days of hourly data
            elif timeframe == '4h':
                lookback_days = 90  # 90 days of 4h data
            else:  # '1d'
                lookback_days = 365  # 1 year of daily data
            
            start_date = current_date - timedelta(days=lookback_days)
            
            # For now, we'll use daily data and resample for other timeframes
            # In production, you'd want to fetch actual timeframe data
            daily_data = data_manager.download_data(asset, start_date, current_date)
            
            if daily_data is None or daily_data.empty:
                return None
            
            # Resample for different timeframes
            if timeframe == '1h':
                # For demo purposes, create hourly data by resampling daily
                # In production, fetch actual hourly data
                return self._resample_to_hourly(daily_data)
            elif timeframe == '4h':
                return self._resample_to_4h(daily_data)
            else:  # '1d'
                return daily_data
                
        except Exception as e:
            print(f"Error getting {timeframe} data for {asset}: {e}")
            return None
    
    def _resample_to_hourly(self, daily_data: pd.DataFrame) -> pd.DataFrame:
        """Get hourly data - REQUIRES REAL DATA SOURCE"""
        print(f"ERROR: No real hourly data source configured")
        print("CRITICAL: Multi-timeframe analysis requires real hourly data")
        # Return None to indicate no data available
        return None
    
    def _resample_to_4h(self, daily_data: pd.DataFrame) -> pd.DataFrame:
        """Get 4-hour data - REQUIRES REAL DATA SOURCE"""
        print(f"ERROR: No real 4-hour data source configured")
        print("CRITICAL: Multi-timeframe analysis requires real 4-hour data")
        # Return None to indicate no data available
        return None
    
    def _determine_position_size(self, 
                                combined_score: float, 
                                technical_score: float, 
                                fundamental_score: float) -> Tuple[PositionSizeCategory, float]:
        """Determine position size based on scores"""
        
        if combined_score >= 0.9:
            return PositionSizeCategory.MAX, self.max_position_size
        elif combined_score >= 0.8:
            return PositionSizeCategory.STANDARD, self.max_position_size * 0.75
        elif combined_score >= 0.7:
            return PositionSizeCategory.HALF, self.max_position_size * 0.5
        elif combined_score >= 0.6:
            return PositionSizeCategory.LIGHT, self.max_position_size * 0.25
        elif combined_score >= 0.5:
            return PositionSizeCategory.LIGHT, self.max_position_size * 0.15
        elif combined_score >= 0.4:
            return PositionSizeCategory.LIGHT, self.max_position_size * 0.1
        elif combined_score >= self.min_score_threshold:
            return PositionSizeCategory.LIGHT, self.max_position_size * 0.05
        else:
            return PositionSizeCategory.NO_POSITION, 0.0
    
    def _calculate_confidence(self, technical_score: float, fundamental_score: float) -> float:
        """Calculate confidence based on score agreement"""
        # Higher confidence when technical and fundamental scores agree
        score_difference = abs(technical_score - fundamental_score)
        max_confidence = 1.0
        min_confidence = 0.5
        
        # Confidence decreases as scores diverge
        confidence = max_confidence - (score_difference * 0.5)
        return max(min_confidence, min(max_confidence, confidence))
    
    def calculate_position_changes(self, 
                                 new_scores: List[PositionScore],
                                 current_date: datetime,
                                 regime_changed: bool = False,
                                 valid_buckets: List[str] = None) -> List[PositionChange]:
        """Calculate what position changes need to be made"""
        changes = []
        
        # Create lookup for new scores
        new_scores_dict = {score.asset: score for score in new_scores}
        
        # Check existing positions for changes
        for asset, current_position in self.current_positions.items():
            should_close_position = False
            close_reason = ""
            
            # Check if asset is still in valid buckets (regime change scenario)
            if regime_changed and valid_buckets is not None:
                asset_buckets = self._get_asset_buckets(asset)
                if not any(bucket in valid_buckets for bucket in asset_buckets):
                    should_close_position = True
                    close_reason = f'Regime change: asset bucket no longer valid'
            
            # Check if asset is no longer in new scores
            if asset not in new_scores_dict:
                should_close_position = True
                if not close_reason:
                    close_reason = 'Asset no longer in selection'
            
            if should_close_position:
                changes.append(PositionChange(
                    asset=asset,
                    previous_score=current_position,
                    current_score=None,
                    action='close',
                    size_change=-current_position.position_size_percentage,
                    reason=close_reason
                ))
            elif asset in new_scores_dict:
                # Asset still valid, check for score changes
                new_score = new_scores_dict[asset]
                change = self._compare_positions(current_position, new_score)
                if change:
                    changes.append(change)
        
        # Check for new positions
        for asset, new_score in new_scores_dict.items():
            if asset not in self.current_positions:
                changes.append(PositionChange(
                    asset=asset,
                    previous_score=None,
                    current_score=new_score,
                    action='open',
                    size_change=new_score.position_size_percentage,
                    reason='New position'
                ))
        
        return changes
    
    def _get_asset_buckets(self, asset: str) -> List[str]:
        """Get which buckets an asset belongs to"""
        if self.asset_manager:
            return self.asset_manager.get_bucket_for_asset(asset)
        return []
    
    def _compare_positions(self, 
                          previous: PositionScore, 
                          current: PositionScore) -> Optional[PositionChange]:
        """Compare previous and current position scores"""
        
        size_change = current.position_size_percentage - previous.position_size_percentage
        
        if abs(size_change) < 0.01:  # Less than 1% change
            return PositionChange(
                asset=current.asset,
                previous_score=previous,
                current_score=current,
                action='hold',
                size_change=0.0,
                reason='No significant change'
            )
        
        if size_change > 0:
            action = 'increase'
            reason = f'Score improved: {previous.combined_score:.3f} -> {current.combined_score:.3f}'
        else:
            action = 'decrease'
            reason = f'Score declined: {previous.combined_score:.3f} -> {current.combined_score:.3f}'
        
        return PositionChange(
            asset=current.asset,
            previous_score=previous,
            current_score=current,
            action=action,
            size_change=size_change,
            reason=reason
        )
    
    def update_positions(self, new_scores: List[PositionScore], current_date: datetime):
        """Update current positions and history"""
        
        # Update current positions
        self.current_positions = {score.asset: score for score in new_scores}
        
        # Update history
        for score in new_scores:
            if score.asset not in self.position_history:
                self.position_history[score.asset] = []
            self.position_history[score.asset].append(score)
        
        # Update last rebalance date
        self.last_rebalance_date = current_date
    
    def get_position_summary(self) -> Dict:
        """Get summary of current positions"""
        total_allocation = sum(pos.position_size_percentage for pos in self.current_positions.values())
        
        return {
            'total_positions': len(self.current_positions),
            'total_allocation': total_allocation,
            'average_score': np.mean([pos.combined_score for pos in self.current_positions.values()]) if self.current_positions else 0,
            'positions': [pos.to_dict() for pos in self.current_positions.values()]
        }
    
    def export_position_history(self, filepath: str):
        """Export position history to JSON"""
        history_data = {}
        for asset, scores in self.position_history.items():
            history_data[asset] = [score.to_dict() for score in scores]
        
        with open(filepath, 'w') as f:
            json.dump(history_data, f, indent=2)
    
    def get_configuration_summary(self) -> Dict:
        """Get summary of current position manager configuration"""
        return {
            'analysis_configuration': {
                'technical_enabled': self.enable_technical_analysis,
                'fundamental_enabled': self.enable_fundamental_analysis,
                'technical_weight': self.technical_weight,
                'fundamental_weight': self.fundamental_weight
            },
            'position_settings': {
                'rebalance_frequency': self.rebalance_frequency,
                'max_positions': self.max_positions,
                'min_score_threshold': self.min_score_threshold,
                'max_position_size': self.max_position_size,
                'min_position_size': self.min_position_size
            },
            'technical_settings': {
                'timeframes': self.timeframes,
                'analyzer_available': self.technical_analyzer is not None
            },
            'fundamental_settings': {
                'analyzer_available': self.fundamental_analyzer is not None
            }
        }