import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from .database_manager import get_database_manager, execute_query

# Import the enhanced asset scanner from Module 12
try:
    from ..core.enhanced_asset_scanner import get_enhanced_asset_scanner
except ImportError:
    # Fallback for relative import issues
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
    from core.enhanced_asset_scanner import get_enhanced_asset_scanner


class RegimeDetector:
    def __init__(self, use_database=True, use_enhanced_scanner=True):
        self.db_manager = get_database_manager()
        self.use_database = use_database and self.db_manager.is_connected
        self.cache = {}
        self.use_enhanced_scanner = use_enhanced_scanner
        
        # Initialize the enhanced asset scanner from Module 12
        if use_enhanced_scanner:
            self.asset_scanner = get_enhanced_asset_scanner(
                enable_database=use_database,
                fallback_enabled=True
            )
        else:
            # Fallback to old scanner for backward compatibility
            from .asset_scanner import get_asset_scanner
            self.asset_scanner = get_asset_scanner()
        
        if not self.db_manager.is_connected and use_database:
            print("Warning: Database connection not available. Using mock regime data.")
        
        # Updated regime mappings based on your 4 regime system
        self.regime_mappings = {
            'Goldilocks': ['Risk Assets', 'Growth', 'Large Caps', 'High Beta'],
            'Deflation': ['Treasurys', 'Long Rates', 'Defensive Assets', 'Gold'],
            'Inflation': ['Industrial Commodities', 'Energy Commodities', 'Gold', 'Value'],
            'Reflation': ['Cyclicals', 'Value', 'International', 'SMID Caps']
        }
    
    def get_market_regime(self, date: datetime) -> Tuple[str, float]:
        if self.use_database:
            return self._get_regime_from_database(date)
        else:
            print("ERROR: Database connection not available - cannot get regime data")
            return None, 0.0
    
    def _get_regime_from_database(self, date: datetime) -> Tuple[str, float]:
        date_str = date.strftime('%Y-%m-%d')
        
        if date_str in self.cache:
            return self.cache[date_str]
        
        research_data = execute_query("""
            SELECT regime, buckets, created_at FROM research 
            WHERE created_at <= :date
            AND regime IS NOT NULL
            ORDER BY created_at DESC 
            LIMIT 1
        """, {"date": date_str})
        
        if research_data and research_data[0].get('regime'):
            regime = research_data[0]['regime']
            # High confidence since this is directly from research
            confidence = 0.9
            self.cache[date_str] = (regime, confidence)
            return regime, confidence
        else:
            # NO REGIME DATA AVAILABLE - FAIL GRACEFULLY
            print(f"ERROR: No regime data available for {date_str}")
            self.cache[date_str] = (None, 0.0)
            return None, 0.0
    
    def get_research_buckets(self, date: datetime) -> Optional[List[str]]:
        """Get buckets directly from research table if available"""
        date_str = date.strftime('%Y-%m-%d')
        
        if not self.use_database:
            return None
        
        research_data = execute_query("""
            SELECT buckets FROM research 
            WHERE created_at <= :date
            AND buckets IS NOT NULL
            ORDER BY created_at DESC 
            LIMIT 1
        """, {"date": date_str})
        
        if research_data and research_data[0].get('buckets'):
            return research_data[0]['buckets']
        
        return None
    
    
    def get_regime_buckets(self, regime: str) -> List[str]:
        return self.regime_mappings.get(regime, ['Risk Assets'])
    
    def get_regime_history(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        dates = pd.date_range(start_date, end_date, freq='D')
        regime_data = []
        
        for date in dates:
            regime, confidence = self.get_market_regime(date)
            regime_data.append({
                'date': date,
                'regime': regime,
                'confidence': confidence,
                'buckets': self.get_regime_buckets(regime)
            })
        
        return pd.DataFrame(regime_data)
    
    def get_price_data(self, ticker: str, start_date: datetime, end_date: datetime, timeframe: str = '1d'):
        """
        Get price data for technical analysis - interface for enhanced asset scanner
        
        Args:
            ticker: Asset ticker
            start_date: Start date for data
            end_date: End date for data  
            timeframe: Data timeframe ('1d', '4h', '1h')
            
        Returns:
            DataFrame with OHLCV data or None if unavailable
        """
        # Import data manager to get real price data
        from .data_manager import DataManager
        
        try:
            data_manager = DataManager()
            
            # For now, we only support daily data from Yahoo Finance
            # Multi-timeframe support would require additional data sources
            if timeframe != '1d':
                print(f"Warning: Only daily data available. Requested timeframe {timeframe} not supported.")
                return None
            
            # Get pandas DataFrame with OHLCV data
            df = data_manager.download_data(ticker, start_date, end_date)
            
            if df is None or df.empty:
                return None
            
            # Ensure consistent column names (Yahoo Finance uses title case)
            df.columns = [col.lower() for col in df.columns]
            
            return df
            
        except Exception as e:
            print(f"Error getting price data for {ticker}: {e}")
            return None
    
    def get_trending_assets(self, date: datetime, asset_universe: List[str], 
                           limit: int = 10, min_confidence: float = 0.7) -> List[str]:
        """
        Get trending assets using the enhanced asset scanner.
        Maintains backward compatibility while leveraging improved scanner capabilities.
        """
        if not asset_universe:
            return []
        
        if self.use_enhanced_scanner:
            # Use the Module 12 enhanced asset scanner with technical analysis
            trending_tickers = self.asset_scanner.get_trending_assets(
                tickers=asset_universe, 
                date=date, 
                min_confidence=min_confidence, 
                limit=limit,
                data_manager=self  # Pass self as data manager for timeframe data
            )
        else:
            # Use old scanner API for backward compatibility
            trending_tickers = self.asset_scanner.get_trending_assets(
                asset_universe, date, min_confidence, limit
            )
        
        if trending_tickers:
            return trending_tickers
        else:
            print(f"No trending assets found with confidence >= {min_confidence:.1%}, using all available assets")
            return asset_universe[:limit]
    
    def get_ranging_assets(self, date: datetime, asset_universe: List[str], 
                          limit: int = 10, min_confidence: float = 0.7) -> List[str]:
        """
        Get ranging/mean-reverting assets using the enhanced asset scanner.
        Useful for mean reversion strategies or defensive positioning.
        """
        if not asset_universe:
            return []
        
        if self.use_enhanced_scanner:
            # Use the Module 12 enhanced asset scanner with technical analysis
            ranging_tickers = self.asset_scanner.get_ranging_assets(
                tickers=asset_universe, 
                date=date, 
                min_confidence=min_confidence, 
                limit=limit,
                data_manager=self  # Pass self as data manager for timeframe data
            )
        else:
            # Use old scanner API for backward compatibility
            ranging_tickers = self.asset_scanner.get_ranging_assets(
                asset_universe, date, min_confidence, limit
            )
        
        return ranging_tickers
    
    def get_market_condition_summary(self, date: datetime, asset_universe: List[str],
                                   min_confidence: float = 0.7) -> Dict:
        """
        Get comprehensive market condition summary for asset universe.
        
        Returns:
            Dictionary with counts and percentages for each market condition
        """
        if not self.use_database:
            return {
                'trending': 0, 'ranging': 0, 'breakout': 0, 'breakdown': 0,
                'total_scanned': len(asset_universe), 'average_confidence': 0.0
            }
        
        return self.asset_scanner.get_market_condition_summary(
            asset_universe, date, min_confidence
        )
    
    def should_rebalance(self, current_date: datetime, last_rebalance: datetime, 
                        current_regime: str, last_regime: str) -> bool:
        days_since_rebalance = (current_date - last_rebalance).days
        
        if days_since_rebalance >= 30:  # Monthly rebalancing
            return True
        
        if current_regime != last_regime:  # Regime change
            return True
        
        return False