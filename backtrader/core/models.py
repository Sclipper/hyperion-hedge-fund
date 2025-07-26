from dataclasses import dataclass
from datetime import datetime
from typing import List, Set, Optional, Dict
from enum import Enum

class AssetPriority(Enum):
    PORTFOLIO = "portfolio"      # Current positions (highest priority)
    TRENDING = "trending"        # New trending opportunities  
    REGIME = "regime"           # Regime-appropriate assets
    FALLBACK = "fallback"       # Backup assets

@dataclass
class RebalancingUniverse:
    """Combined asset universe for rebalancing"""
    portfolio_assets: Set[str]          # Current positions (MUST analyze)
    trending_assets: Set[str]           # New opportunities from trending
    regime_assets: Set[str]             # All regime-appropriate assets
    combined_universe: Set[str]         # Union for actual analysis
    date: datetime
    regime: str
    
    def get_prioritized_assets(self) -> Dict[AssetPriority, Set[str]]:
        """Get assets grouped by priority"""
        return {
            AssetPriority.PORTFOLIO: self.portfolio_assets,
            AssetPriority.TRENDING: self.trending_assets - self.portfolio_assets,
            AssetPriority.REGIME: self.regime_assets - self.trending_assets - self.portfolio_assets
        }

@dataclass 
class AssetScore:
    """Enhanced position score with priority information"""
    asset: str
    date: datetime
    technical_score: float
    fundamental_score: float
    combined_score: float
    confidence: float
    regime: str
    priority: AssetPriority
    timeframes_analyzed: List[str]
    
    # Portfolio context
    is_current_position: bool = False
    previous_allocation: float = 0.0
    
    # Scoring metadata
    scoring_reason: str = ""
    missing_data_flags: List[str] = None
    
    def to_dict(self) -> dict:
        return {
            'asset': self.asset,
            'date': self.date.isoformat(),
            'technical_score': self.technical_score,
            'fundamental_score': self.fundamental_score,
            'combined_score': self.combined_score,
            'confidence': self.confidence,
            'regime': self.regime,
            'priority': self.priority.value,
            'is_current_position': self.is_current_position,
            'previous_allocation': self.previous_allocation,
            'scoring_reason': self.scoring_reason,
            'timeframes_analyzed': self.timeframes_analyzed or []
        }

@dataclass
class RebalancingLimits:
    """Position limits for rebalancing"""
    max_total_positions: int = 10
    max_new_positions: int = 3
    min_score_threshold: float = 0.6
    min_score_new_position: float = 0.65
    
    # Position sizing
    max_single_position_pct: float = 0.2
    target_total_allocation: float = 0.95
    
    # Bucket diversification (optional)
    enable_bucket_diversification: bool = False
    max_positions_per_bucket: int = 4
    max_allocation_per_bucket: float = 0.4
    min_buckets_represented: int = 2
    allow_bucket_overflow: bool = False
    
    # Dynamic sizing configuration (NEW)
    enable_dynamic_sizing: bool = True
    sizing_mode: str = 'adaptive'  # 'adaptive', 'equal_weight', 'score_weighted'
    max_single_position: float = 0.15  # For two-stage sizing (may be lower than max_single_position_pct)
    min_position_size: float = 0.02
    residual_strategy: str = 'safe_top_slice'  # 'safe_top_slice', 'proportional', 'cash_bucket'
    max_residual_per_asset: float = 0.05
    max_residual_multiple: float = 0.5
    
    # Grace & Holding Period Management (Module 4)
    enable_grace_periods: bool = True
    grace_period_days: int = 5
    grace_decay_rate: float = 0.8
    min_decay_factor: float = 0.1
    
    min_holding_period_days: int = 3
    max_holding_period_days: int = 90
    enable_regime_overrides: bool = True
    regime_override_cooldown_days: int = 30
    regime_severity_threshold: str = 'high'  # 'normal', 'high', 'critical'
    
    enable_whipsaw_protection: bool = True
    max_cycles_per_protection_period: int = 1
    whipsaw_protection_days: int = 14
    min_position_duration_hours: int = 4

@dataclass
class RebalancingTarget:
    """Final rebalancing target output"""
    asset: str
    target_allocation_pct: float
    current_allocation_pct: float
    action: str  # 'open', 'increase', 'decrease', 'close', 'hold'
    priority: AssetPriority
    score: float
    reason: str 