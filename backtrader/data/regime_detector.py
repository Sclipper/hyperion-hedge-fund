import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))
try:
    from app.backend.database.connection import SessionLocal
except ImportError:
    SessionLocal = None
    print("Warning: Database connection not available. Using mock regime data.")


class RegimeDetector:
    def __init__(self, use_database=True):
        self.use_database = use_database and SessionLocal is not None
        self.cache = {}
        
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
        
        db = SessionLocal()
        try:
            result = db.execute(text("""
                SELECT regime, buckets, created_at FROM research 
                WHERE created_at <= :date
                AND regime IS NOT NULL
                ORDER BY created_at DESC 
                LIMIT 1
            """), {"date": date_str})
            
            research_data = [dict(row._mapping) for row in result]
            
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
                
        except Exception as e:
            print(f"ERROR: Could not fetch regime data from database: {e}")
            print("CRITICAL: No regime data available - cannot proceed with regime-based strategy")
            self.cache[date_str] = (None, 0.0)
            return None, 0.0
        finally:
            db.close()
    
    def get_research_buckets(self, date: datetime) -> Optional[List[str]]:
        """Get buckets directly from research table if available"""
        date_str = date.strftime('%Y-%m-%d')
        
        if not self.use_database:
            return None
        
        db = SessionLocal()
        try:
            result = db.execute(text("""
                SELECT buckets FROM research 
                WHERE created_at <= :date
                AND buckets IS NOT NULL
                ORDER BY created_at DESC 
                LIMIT 1
            """), {"date": date_str})
            
            research_data = [dict(row._mapping) for row in result]
            
            if research_data and research_data[0].get('buckets'):
                return research_data[0]['buckets']
            
            return None
                
        except Exception as e:
            print(f"Warning: Could not fetch bucket data from database: {e}")
            return None
        finally:
            db.close()
    
    
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
    
    def get_trending_assets(self, date: datetime, asset_universe: List[str], 
                           limit: int = 10, min_confidence: float = 0.7) -> List[str]:
        if not self.use_database:
            return asset_universe[:limit]
        
        db = SessionLocal()
        try:
            date_str = date.strftime('%Y-%m-%d')
            result = db.execute(text("""
                SELECT * FROM scanner_historical
                WHERE ticker = ANY(:tickers)
                AND confidence >= :min_confidence
                AND market = 'trending'
                AND date <= :date
                ORDER BY confidence DESC, date DESC
                LIMIT :limit
            """), {"tickers": asset_universe, "date": date_str, "limit": limit, "min_confidence": min_confidence})
            
            trending_assets = [dict(row._mapping) for row in result]
            trending_tickers = [asset['ticker'] for asset in trending_assets]
            
            # Log trending asset filtering results
            print(f"Trending Assets Filter: Found {len(trending_tickers)} assets with confidence >= {min_confidence:.1%}")
            if trending_assets:
                avg_confidence = sum(asset['confidence'] for asset in trending_assets) / len(trending_assets)
                print(f"Average trending confidence: {avg_confidence:.2f}")
            
            if trending_tickers:
                return trending_tickers
            else:
                print(f"No trending assets found with confidence >= {min_confidence:.1%}, using all available assets")
                return asset_universe[:limit]
                
        except Exception as e:
            print(f"Warning: Could not fetch trending assets: {e}")
            return asset_universe[:limit]
        finally:
            db.close()
    
    def should_rebalance(self, current_date: datetime, last_rebalance: datetime, 
                        current_regime: str, last_regime: str) -> bool:
        days_since_rebalance = (current_date - last_rebalance).days
        
        if days_since_rebalance >= 30:  # Monthly rebalancing
            return True
        
        if current_regime != last_regime:  # Regime change
            return True
        
        return False