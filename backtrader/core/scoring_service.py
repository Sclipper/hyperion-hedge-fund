from typing import List, Optional, Dict, Any
from datetime import datetime
import random
import sys
import os

# Import models only to avoid dependency issues during testing
from .models import AssetScore, AssetPriority, RebalancingUniverse

class ScoringService:
    """Service for scoring assets with priority awareness"""
    
    def __init__(self, technical_analyzer: Any = None, fundamental_analyzer: Any = None,
                 enable_technical: bool = True, enable_fundamental: bool = True,
                 technical_weight: float = 0.6, fundamental_weight: float = 0.4):
        
        self.technical_analyzer = technical_analyzer
        self.fundamental_analyzer = fundamental_analyzer
        self.enable_technical = enable_technical
        self.enable_fundamental = enable_fundamental
        self.technical_weight = technical_weight
        self.fundamental_weight = fundamental_weight
        
        self._validate_configuration()
    
    def _validate_configuration(self):
        """Validate scoring configuration"""
        if not self.enable_technical and not self.enable_fundamental:
            raise ValueError("At least one analysis type must be enabled")
        
        print(f"Scoring Service Configuration:")
        if self.enable_technical:
            print(f"  Technical Analysis: {self.technical_weight:.1%}")
        if self.enable_fundamental:
            print(f"  Fundamental Analysis: {self.fundamental_weight:.1%}")
    
    def score_assets(self, universe: RebalancingUniverse, 
                    current_positions: Dict[str, float] = None,
                    data_manager: Any = None) -> List[AssetScore]:
        """
        Score all assets in universe with priority classification
        
        Args:
            universe: RebalancingUniverse to score
            current_positions: Dict of {asset: allocation_pct}
            data_manager: Data manager for price/fundamental data
            
        Returns:
            List of AssetScore objects with priorities
        """
        
        current_positions = current_positions or {}
        scored_assets = []
        
        # Get prioritized assets
        prioritized = universe.get_prioritized_assets()
        
        for priority, assets in prioritized.items():
            for asset in assets:
                try:
                    score = self._score_single_asset(
                        asset=asset,
                        date=universe.date,
                        regime=universe.regime,
                        priority=priority,
                        current_allocation=current_positions.get(asset, 0.0),
                        data_manager=data_manager
                    )
                    
                    if score:
                        scored_assets.append(score)
                        
                except Exception as e:
                    print(f"Warning: Could not score {asset}: {e}")
                    continue
        
        print(f"Scoring Results: {len(scored_assets)} assets scored")
        for priority in AssetPriority:
            priority_scores = [s for s in scored_assets if s.priority == priority]
            if priority_scores:
                avg_score = sum(s.combined_score for s in priority_scores) / len(priority_scores)
                print(f"  {priority.value}: {len(priority_scores)} assets, avg score: {avg_score:.3f}")
        
        return scored_assets
    
    def _score_single_asset(self, asset: str, date: datetime, regime: str,
                           priority: AssetPriority, current_allocation: float,
                           data_manager: Any = None) -> Optional[AssetScore]:
        """
        Score a single asset with all available analysis
        """
        
        # Check if we have real analyzers and data manager
        if (self.technical_analyzer and self.fundamental_analyzer and 
            data_manager and hasattr(data_manager, 'get_data')):
            return self._score_with_real_analyzers(
                asset, date, regime, priority, current_allocation, data_manager
            )
        else:
            return self._score_with_stub(
                asset, date, regime, priority, current_allocation
            )
    
    def _score_with_real_analyzers(self, asset: str, date: datetime, regime: str,
                                  priority: AssetPriority, current_allocation: float,
                                  data_manager: Any) -> Optional[AssetScore]:
        """Score using real technical and fundamental analyzers"""
        
        technical_score = 0.0
        fundamental_score = 0.0
        missing_data = []
        
        # Technical analysis
        if self.enable_technical and self.technical_analyzer:
            try:
                # Use existing technical analyzer
                tech_result = self.technical_analyzer.analyze_asset(asset, date)
                technical_score = tech_result if isinstance(tech_result, float) else tech_result.get('composite_score', 0.0)
            except Exception as e:
                missing_data.append(f"technical: {str(e)}")
                technical_score = 0.0
        
        # Fundamental analysis  
        if self.enable_fundamental and self.fundamental_analyzer:
            try:
                fundamental_score = self.fundamental_analyzer.analyze_asset(asset, date, regime)
            except Exception as e:
                missing_data.append(f"fundamental: {str(e)}")
                fundamental_score = 0.0
        
        # Calculate combined score with proper weighting
        effective_tech_weight = self.technical_weight if self.enable_technical else 0.0
        effective_fund_weight = self.fundamental_weight if self.enable_fundamental else 0.0
        
        # Handle case where one analysis is disabled
        if not self.enable_technical:
            effective_fund_weight = 1.0
        elif not self.enable_fundamental:
            effective_tech_weight = 1.0
        elif fundamental_score == 0.0 and technical_score > 0.0:
            # Fundamental data missing, use technical only
            effective_tech_weight = 1.0
            effective_fund_weight = 0.0
        
        combined_score = (technical_score * effective_tech_weight + 
                         fundamental_score * effective_fund_weight)
        
        # Priority boost for current positions (slight bias to avoid unnecessary churn)
        if priority == AssetPriority.PORTFOLIO and current_allocation > 0:
            combined_score *= 1.02  # 2% boost to existing positions
        
        return AssetScore(
            asset=asset,
            date=date,
            technical_score=technical_score,
            fundamental_score=fundamental_score,
            combined_score=combined_score,
            confidence=0.8 if not missing_data else 0.6,  # Lower confidence if missing data
            regime=regime,
            priority=priority,
            is_current_position=current_allocation > 0,
            previous_allocation=current_allocation,
            scoring_reason=f"Tech: {effective_tech_weight:.1%}, Fund: {effective_fund_weight:.1%}",
            missing_data_flags=missing_data,
            timeframes_analyzed=['1d']  # Placeholder
        )
    
    def _score_with_stub(self, asset: str, date: datetime, regime: str,
                        priority: AssetPriority, current_allocation: float) -> AssetScore:
        """Stub scoring for testing and development"""
        
        # Generate deterministic "scores" for consistent testing
        random.seed(hash(asset + date.strftime('%Y-%m-%d') + regime))
        
        technical_score = random.uniform(0.3, 0.9)
        fundamental_score = random.uniform(0.3, 0.9)
        
        # Simulate different analysis configurations
        if not self.enable_technical:
            technical_score = 0.0
            fundamental_score = random.uniform(0.4, 0.85)
            combined_score = fundamental_score
        elif not self.enable_fundamental:
            fundamental_score = 0.0
            technical_score = random.uniform(0.4, 0.85)
            combined_score = technical_score
        else:
            combined_score = (technical_score * self.technical_weight + 
                            fundamental_score * self.fundamental_weight)
        
        # Portfolio priority boost
        if priority == AssetPriority.PORTFOLIO and current_allocation > 0:
            combined_score *= 1.02
        
        # Regime-based adjustments (stub)
        regime_multipliers = {
            'Goldilocks': 1.1,
            'Reflation': 1.05,
            'Inflation': 0.95,
            'Deflation': 0.9
        }
        combined_score *= regime_multipliers.get(regime, 1.0)
        
        # Ensure scores are in valid range
        combined_score = max(0.0, min(1.0, combined_score))
        
        return AssetScore(
            asset=asset,
            date=date,
            technical_score=technical_score,
            fundamental_score=fundamental_score,
            combined_score=combined_score,
            confidence=0.75,  # Moderate confidence for stub
            regime=regime,
            priority=priority,
            is_current_position=current_allocation > 0,
            previous_allocation=current_allocation,
            scoring_reason="STUB: Deterministic test scoring",
            timeframes_analyzed=['1d_stub']
        ) 