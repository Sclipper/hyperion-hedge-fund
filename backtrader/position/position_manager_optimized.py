"""
Optimized PositionManager that uses pre-loaded data instead of downloading during execution
"""

from typing import Dict, List, Optional
from datetime import datetime
import logging

# Import original PositionManager
from .position_manager import PositionManager, PositionScore

logger = logging.getLogger(__name__)


class PositionManagerOptimized(PositionManager):
    """
    Optimized position manager that uses pre-loaded data
    """
    
    def __init__(self, data_preloader=None, **kwargs):
        """
        Initialize with data preloader
        
        Args:
            data_preloader: DataPreloader instance with pre-loaded data
            **kwargs: All other arguments for parent PositionManager
        """
        super().__init__(**kwargs)
        self.data_preloader = data_preloader
        
    def _score_single_asset(self, 
                           asset: str, 
                           current_date: datetime,
                           regime: str,
                           data_manager) -> Optional[PositionScore]:
        """
        Score a single asset using pre-loaded data (override parent method)
        """
        
        # Use pre-loaded data if available
        if self.data_preloader:
            # Get pre-loaded multi-timeframe data
            timeframe_data = self.data_preloader.get_data_for_analysis(
                asset=asset,
                current_date=current_date,
                lookback_days=90,  # Standard lookback for technical analysis
                timeframes=self.timeframes
            )
            
            if timeframe_data:
                logger.info(f"✓ Using pre-loaded data for {asset}: {list(timeframe_data.keys())}")
                # Log data shapes for debugging
                for tf, df in timeframe_data.items():
                    logger.debug(f"  {asset} {tf}: {len(df)} records, {df.index[0]} to {df.index[-1]}")
            else:
                logger.error(f"❌ No pre-loaded data for {asset}, checking preloader status...")
                logger.error(f"  Asset in preloader: {asset in self.data_preloader.preloaded_data}")
                if asset in self.data_preloader.preloaded_data:
                    available_tfs = list(self.data_preloader.preloaded_data[asset].keys())
                    logger.error(f"  Available timeframes: {available_tfs}")
                    logger.error(f"  Requested timeframes: {self.timeframes}")
                logger.error(f"  Current date: {current_date}")
                # Don't fall back - return None to highlight the issue
                return None
        else:
            # No preloader, use original method
            return super()._score_single_asset(asset, current_date, regime, data_manager)
        
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
                logger.error(f"Technical analysis failed for {asset}: {e}")
                technical_score = 0.5  # Default to neutral
        elif self.enable_technical_analysis and not timeframe_data:
            technical_score = 0.5  # Neutral score if no data
        
        # Fundamental analysis
        fundamental_score = 0.0
        if self.enable_fundamental_analysis and self.fundamental_analyzer:
            fundamental_score = self.fundamental_analyzer.analyze_asset(
                asset, current_date, regime
            )
        
        # Calculate combined score (same logic as parent)
        if not self.enable_technical_analysis:
            effective_technical_weight = 0.0
            effective_fundamental_weight = 1.0
            combined_score = fundamental_score
        elif not self.enable_fundamental_analysis:
            effective_technical_weight = 1.0
            effective_fundamental_weight = 0.0
            combined_score = technical_score
        else:
            if fundamental_score == 0.0:
                effective_technical_weight = 1.0
                effective_fundamental_weight = 0.0
                combined_score = technical_score
            else:
                effective_technical_weight = self.technical_weight
                effective_fundamental_weight = self.fundamental_weight
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
        
        # Calculate confidence
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
    
    def analyze_and_score_assets(self, 
                                assets: List[str], 
                                current_date: datetime,
                                regime: str,
                                data_manager) -> List[PositionScore]:
        """
        Analyze assets using pre-loaded data for much better performance
        """
        if self.data_preloader:
            logger.info(f"Analyzing {len(assets)} assets using pre-loaded data")
        
        return super().analyze_and_score_assets(assets, current_date, regime, data_manager)