"""
Module 12: Enhanced Asset Scanner - Data Models

Asset-level market condition models for trending, ranging, breakout, and breakdown detection.
This is fundamentally different from macro regime detection (Module 6).
"""

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Dict, Optional, Any


class MarketCondition(Enum):
    """Asset-level market conditions (NOT macro regimes)"""
    TRENDING = "trending"
    RANGING = "ranging"
    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"


class ScannerSource(Enum):
    """Source of scanner data"""
    DATABASE = "database"
    FALLBACK = "fallback"
    MIXED = "mixed"


@dataclass
class AssetCondition:
    """
    Individual asset market condition result
    
    Represents the market condition of a single asset at a specific point in time,
    completely independent of macro economic regime.
    """
    ticker: str
    market: MarketCondition
    confidence: float  # 0.0 - 1.0
    timeframe_breakdown: Dict[str, float] = field(default_factory=dict)
    source: ScannerSource = ScannerSource.DATABASE
    scan_date: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate confidence range"""
        self.confidence = max(0.0, min(1.0, self.confidence))
    
    def is_confident(self, threshold: float = 0.7) -> bool:
        """Check if confidence meets threshold"""
        return self.confidence >= threshold
    
    def is_trending(self) -> bool:
        """Check if asset is in trending condition"""
        return self.market == MarketCondition.TRENDING
    
    def is_ranging(self) -> bool:
        """Check if asset is in ranging condition"""
        return self.market == MarketCondition.RANGING
    
    def is_breakout(self) -> bool:
        """Check if asset is in breakout condition"""
        return self.market == MarketCondition.BREAKOUT
    
    def is_breakdown(self) -> bool:
        """Check if asset is in breakdown condition"""
        return self.market == MarketCondition.BREAKDOWN
    
    def get_dominant_timeframe(self) -> Optional[str]:
        """Get timeframe with highest confidence"""
        if not self.timeframe_breakdown:
            return None
        return max(self.timeframe_breakdown.items(), key=lambda x: x[1])[0]


@dataclass
class ScannerResults:
    """
    Complete scanner results for multiple assets
    """
    asset_conditions: Dict[str, AssetCondition]
    scan_date: datetime
    total_assets_scanned: int
    database_assets: int = 0
    fallback_assets: int = 0
    average_confidence: float = 0.0
    
    def __post_init__(self):
        """Calculate derived metrics"""
        if self.asset_conditions:
            confidences = [ac.confidence for ac in self.asset_conditions.values()]
            self.average_confidence = sum(confidences) / len(confidences)
            
            self.database_assets = sum(1 for ac in self.asset_conditions.values() 
                                     if ac.source == ScannerSource.DATABASE)
            self.fallback_assets = sum(1 for ac in self.asset_conditions.values() 
                                     if ac.source == ScannerSource.FALLBACK)
    
    def get_assets_by_condition(self, condition: MarketCondition, 
                               min_confidence: float = 0.0) -> Dict[str, AssetCondition]:
        """Get assets filtered by market condition and confidence"""
        return {
            ticker: asset_condition
            for ticker, asset_condition in self.asset_conditions.items()
            if (asset_condition.market == condition and 
                asset_condition.confidence >= min_confidence)
        }
    
    def get_trending_assets(self, min_confidence: float = 0.7) -> Dict[str, AssetCondition]:
        """Get trending assets above confidence threshold"""
        return self.get_assets_by_condition(MarketCondition.TRENDING, min_confidence)
    
    def get_ranging_assets(self, min_confidence: float = 0.7) -> Dict[str, AssetCondition]:
        """Get ranging assets above confidence threshold"""
        return self.get_assets_by_condition(MarketCondition.RANGING, min_confidence)
    
    def get_breakout_assets(self, min_confidence: float = 0.8) -> Dict[str, AssetCondition]:
        """Get breakout assets above confidence threshold (higher threshold for breakouts)"""
        return self.get_assets_by_condition(MarketCondition.BREAKOUT, min_confidence)
    
    def get_breakdown_assets(self, min_confidence: float = 0.8) -> Dict[str, AssetCondition]:
        """Get breakdown assets above confidence threshold (higher threshold for breakdowns)"""
        return self.get_assets_by_condition(MarketCondition.BREAKDOWN, min_confidence)
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics for scanner results"""
        stats = {
            'total_assets': self.total_assets_scanned,
            'database_coverage': self.database_assets / self.total_assets_scanned if self.total_assets_scanned > 0 else 0,
            'average_confidence': self.average_confidence,
            'conditions': {}
        }
        
        for condition in MarketCondition:
            condition_assets = self.get_assets_by_condition(condition)
            stats['conditions'][condition.value] = {
                'count': len(condition_assets),
                'percentage': len(condition_assets) / self.total_assets_scanned if self.total_assets_scanned > 0 else 0,
                'avg_confidence': sum(ac.confidence for ac in condition_assets.values()) / len(condition_assets) if condition_assets else 0
            }
        
        return stats


@dataclass
class TechnicalIndicators:
    """
    Technical analysis indicators for fallback scanner
    """
    # Trend indicators
    adx: float = 0.0
    ma_alignment_score: float = 0.0
    macd_momentum: float = 0.0
    trend_consistency: float = 0.0
    
    # Range indicators
    bb_squeeze: float = 0.0
    support_resistance_strength: float = 0.0
    oscillator_range: float = 0.0
    volatility_compression: float = 0.0
    
    # Breakout indicators
    volume_surge: float = 0.0
    volatility_expansion: float = 0.0
    momentum_acceleration: float = 0.0
    level_break_quality: float = 0.0
    
    # Derived scores
    trend_score: float = 0.0
    range_score: float = 0.0
    breakout_score: float = 0.0
    breakdown_score: float = 0.0
    
    def calculate_derived_scores(self):
        """Calculate derived condition scores from individual indicators"""
        # Trend score: combination of trend indicators
        self.trend_score = (
            (self.adx / 100) * 0.4 +  # ADX normalized to 0-1
            self.ma_alignment_score * 0.3 +
            self.macd_momentum * 0.2 +
            self.trend_consistency * 0.1
        )
        
        # Range score: combination of range indicators
        self.range_score = (
            self.bb_squeeze * 0.3 +
            self.support_resistance_strength * 0.3 +
            self.oscillator_range * 0.2 +
            self.volatility_compression * 0.2
        )
        
        # Breakout score: combination of breakout indicators
        self.breakout_score = (
            self.volume_surge * 0.4 +
            self.volatility_expansion * 0.3 +
            self.momentum_acceleration * 0.2 +
            self.level_break_quality * 0.1
        )
        
        # Breakdown score: similar to breakout but for downside
        self.breakdown_score = (
            self.volume_surge * 0.3 +  # Volume less critical for breakdowns
            self.volatility_expansion * 0.3 +
            (1.0 - self.momentum_acceleration) * 0.3 +  # Negative momentum
            self.level_break_quality * 0.1
        )
        
        # Ensure all scores are in valid range
        self.trend_score = max(0.0, min(1.0, self.trend_score))
        self.range_score = max(0.0, min(1.0, self.range_score))
        self.breakout_score = max(0.0, min(1.0, self.breakout_score))
        self.breakdown_score = max(0.0, min(1.0, self.breakdown_score))
    
    def get_dominant_condition(self) -> tuple[MarketCondition, float]:
        """Get the market condition with highest score"""
        scores = {
            MarketCondition.TRENDING: self.trend_score,
            MarketCondition.RANGING: self.range_score,
            MarketCondition.BREAKOUT: self.breakout_score,
            MarketCondition.BREAKDOWN: self.breakdown_score
        }
        
        dominant_condition = max(scores.items(), key=lambda x: x[1])
        return dominant_condition[0], dominant_condition[1]