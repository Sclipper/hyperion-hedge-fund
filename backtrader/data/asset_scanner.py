"""
Enhanced Asset Scanner for Hedge Fund System

Provides comprehensive asset scanning capabilities for:
- Trending assets (momentum-based opportunities)
- Ranging assets (mean reversion opportunities)
- Market condition analysis
- Confidence scoring and filtering
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from .database_manager import get_database_manager, execute_query


class MarketCondition(Enum):
    """Asset market condition types"""
    TRENDING = "trending"
    RANGING = "ranging"
    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"


@dataclass
class AssetScanResult:
    """Individual asset scan result"""
    ticker: str
    market_condition: MarketCondition
    confidence: float
    strength: float
    date: datetime
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ScannerResults:
    """Complete scanner results with statistics"""
    trending_assets: List[AssetScanResult]
    ranging_assets: List[AssetScanResult]
    breakout_assets: List[AssetScanResult]
    breakdown_assets: List[AssetScanResult]
    scan_date: datetime
    total_assets_scanned: int
    average_confidence: float
    
    @property
    def all_assets(self) -> List[AssetScanResult]:
        """Get all assets from all categories"""
        return (self.trending_assets + self.ranging_assets + 
                self.breakout_assets + self.breakdown_assets)
    
    def get_assets_by_condition(self, condition: MarketCondition) -> List[AssetScanResult]:
        """Get assets filtered by market condition"""
        condition_map = {
            MarketCondition.TRENDING: self.trending_assets,
            MarketCondition.RANGING: self.ranging_assets,
            MarketCondition.BREAKOUT: self.breakout_assets,
            MarketCondition.BREAKDOWN: self.breakdown_assets
        }
        return condition_map.get(condition, [])


class EnhancedAssetScanner:
    """
    Enhanced asset scanner with database integration.
    
    Provides sophisticated asset scanning capabilities including:
    - Multi-condition market analysis (trending/ranging/breakout/breakdown)
    - Historical scanner data integration
    - Confidence-based filtering
    - Asset universe filtering and selection
    """
    
    def __init__(self):
        self.db_manager = get_database_manager()
        self.is_database_available = self.db_manager.is_connected
        self.cache = {}
        
        if not self.is_database_available:
            print("Warning: Database not available. Asset scanner will use mock data.")
    
    def scan_assets(self, 
                   asset_universe: List[str], 
                   scan_date: datetime,
                   min_confidence: float = 0.7,
                   include_conditions: List[MarketCondition] = None) -> ScannerResults:
        """
        Comprehensive asset scan for multiple market conditions.
        
        Args:
            asset_universe: List of tickers to scan
            scan_date: Date for which to retrieve scanner data
            min_confidence: Minimum confidence threshold (0.0-1.0)
            include_conditions: Market conditions to include (default: all)
            
        Returns:
            ScannerResults with categorized assets
        """
        if include_conditions is None:
            include_conditions = list(MarketCondition)
        
        if not self.is_database_available:
            return self._mock_scan_results(asset_universe, scan_date, min_confidence)
        
        # Get scanner data from database
        scanner_data = self._fetch_scanner_data(asset_universe, scan_date, min_confidence)
        
        # Categorize results by market condition
        trending_assets = []
        ranging_assets = []
        breakout_assets = []
        breakdown_assets = []
        
        total_confidence = 0.0
        asset_count = 0
        
        for asset_data in scanner_data:
            result = AssetScanResult(
                ticker=asset_data['ticker'],
                market_condition=MarketCondition(asset_data['market']),
                confidence=asset_data['confidence'],
                strength=asset_data.get('strength', 0.0),
                date=asset_data['date'],
                metadata={
                    'volume_ratio': asset_data.get('volume_ratio'),
                    'price_change': asset_data.get('price_change'),
                    'volatility': asset_data.get('volatility')
                }
            )
            
            # Categorize by condition
            if result.market_condition == MarketCondition.TRENDING:
                trending_assets.append(result)
            elif result.market_condition == MarketCondition.RANGING:
                ranging_assets.append(result)
            elif result.market_condition == MarketCondition.BREAKOUT:
                breakout_assets.append(result)
            elif result.market_condition == MarketCondition.BREAKDOWN:
                breakdown_assets.append(result)
            
            total_confidence += result.confidence
            asset_count += 1
        
        average_confidence = total_confidence / asset_count if asset_count > 0 else 0.0
        
        return ScannerResults(
            trending_assets=trending_assets,
            ranging_assets=ranging_assets,
            breakout_assets=breakout_assets,
            breakdown_assets=breakdown_assets,
            scan_date=scan_date,
            total_assets_scanned=len(asset_universe),
            average_confidence=average_confidence
        )
    
    def get_trending_assets(self, 
                           asset_universe: List[str], 
                           scan_date: datetime,
                           min_confidence: float = 0.7,
                           limit: Optional[int] = None) -> List[str]:
        """
        Get trending assets (backward compatibility method).
        
        Args:
            asset_universe: List of tickers to scan
            scan_date: Date for scanner data
            min_confidence: Minimum confidence threshold
            limit: Maximum number of assets to return
            
        Returns:
            List of trending asset tickers
        """
        results = self.scan_assets(
            asset_universe, 
            scan_date, 
            min_confidence, 
            [MarketCondition.TRENDING]
        )
        
        trending_tickers = [asset.ticker for asset in results.trending_assets]
        
        if limit:
            trending_tickers = trending_tickers[:limit]
        
        if trending_tickers:
            print(f"Trending Assets Scanner: Found {len(trending_tickers)} assets "
                  f"with confidence >= {min_confidence:.1%}")
            avg_conf = sum(asset.confidence for asset in results.trending_assets) / len(results.trending_assets)
            print(f"Average trending confidence: {avg_conf:.2f}")
        else:
            print(f"No trending assets found with confidence >= {min_confidence:.1%}")
        
        return trending_tickers
    
    def get_ranging_assets(self, 
                          asset_universe: List[str], 
                          scan_date: datetime,
                          min_confidence: float = 0.7,
                          limit: Optional[int] = None) -> List[str]:
        """
        Get ranging/mean-reverting assets.
        
        Args:
            asset_universe: List of tickers to scan
            scan_date: Date for scanner data
            min_confidence: Minimum confidence threshold
            limit: Maximum number of assets to return
            
        Returns:
            List of ranging asset tickers
        """
        results = self.scan_assets(
            asset_universe, 
            scan_date, 
            min_confidence, 
            [MarketCondition.RANGING]
        )
        
        ranging_tickers = [asset.ticker for asset in results.ranging_assets]
        
        if limit:
            ranging_tickers = ranging_tickers[:limit]
        
        if ranging_tickers:
            print(f"Ranging Assets Scanner: Found {len(ranging_tickers)} assets "
                  f"with confidence >= {min_confidence:.1%}")
        
        return ranging_tickers
    
    def get_market_condition_summary(self, 
                                   asset_universe: List[str], 
                                   scan_date: datetime,
                                   min_confidence: float = 0.7) -> Dict[str, int]:
        """
        Get summary of market conditions across asset universe.
        
        Returns:
            Dictionary with counts for each market condition
        """
        results = self.scan_assets(asset_universe, scan_date, min_confidence)
        
        return {
            'trending': len(results.trending_assets),
            'ranging': len(results.ranging_assets),
            'breakout': len(results.breakout_assets),
            'breakdown': len(results.breakdown_assets),
            'total_scanned': results.total_assets_scanned,
            'average_confidence': results.average_confidence
        }
    
    def _fetch_scanner_data(self, 
                           asset_universe: List[str], 
                           scan_date: datetime,
                           min_confidence: float) -> List[Dict]:
        """Fetch scanner data from database"""
        date_str = scan_date.strftime('%Y-%m-%d')
        
        cache_key = f"scanner_{date_str}_{len(asset_universe)}_{min_confidence}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        scanner_data = execute_query("""
            SELECT ticker, market, confidence, strength, date, 
                   volume_ratio, price_change, volatility
            FROM scanner_historical
            WHERE ticker = ANY(:tickers)
            AND confidence >= :min_confidence
            AND date <= :date
            ORDER BY confidence DESC, date DESC
        """, {
            "tickers": asset_universe, 
            "date": date_str, 
            "min_confidence": min_confidence
        })
        
        if scanner_data is None:
            scanner_data = []
        
        self.cache[cache_key] = scanner_data
        return scanner_data
    
    def _mock_scan_results(self, 
                          asset_universe: List[str], 
                          scan_date: datetime,
                          min_confidence: float) -> ScannerResults:
        """Generate mock scanner results when database unavailable"""
        print("Warning: Using mock scanner data - database not available")
        
        # Simple mock logic: alternate between trending and ranging
        trending_assets = []
        ranging_assets = []
        
        for i, ticker in enumerate(asset_universe[:10]):  # Limit to 10 for mock
            if i % 2 == 0:
                trending_assets.append(AssetScanResult(
                    ticker=ticker,
                    market_condition=MarketCondition.TRENDING,
                    confidence=0.75 + (i * 0.02),  # Mock confidence
                    strength=0.6,
                    date=scan_date,
                    metadata={'mock': True}
                ))
            else:
                ranging_assets.append(AssetScanResult(
                    ticker=ticker,
                    market_condition=MarketCondition.RANGING,
                    confidence=0.72 + (i * 0.01),  # Mock confidence
                    strength=0.5,
                    date=scan_date,
                    metadata={'mock': True}
                ))
        
        return ScannerResults(
            trending_assets=trending_assets,
            ranging_assets=ranging_assets,
            breakout_assets=[],
            breakdown_assets=[],
            scan_date=scan_date,
            total_assets_scanned=len(asset_universe),
            average_confidence=0.75
        )


# Global scanner instance
_asset_scanner = None


def get_asset_scanner() -> EnhancedAssetScanner:
    """Get the global asset scanner instance"""
    global _asset_scanner
    if _asset_scanner is None:
        _asset_scanner = EnhancedAssetScanner()
    return _asset_scanner