import sys
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.orm import Session
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

try:
    from app.backend.database.connection import SessionLocal
    DATABASE_AVAILABLE = True
except ImportError:
    SessionLocal = None
    DATABASE_AVAILABLE = False
    print("Warning: Database connection not available. Using mock data.")


class DatabaseIntegration:
    def __init__(self):
        self.database_available = DATABASE_AVAILABLE
        self.cache = {}
    
    def get_macro_research_data(self, end_date: str) -> Dict:
        if not self.database_available:
            print("ERROR: Database connection not available - cannot get macro research data")
            return {
                'research_data': [],
                'regime': None,
                'buckets': [],
                'has_data': False
            }
        
        cache_key = f"macro_{end_date}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        db = SessionLocal()
        try:
            result = db.execute(text("""
                SELECT title, regime, buckets, created_at
                FROM research 
                WHERE created_at <= :end_date
                AND regime IS NOT NULL
                ORDER BY created_at DESC 
                LIMIT 1
            """), {"end_date": end_date})
            
            research_data = [dict(row._mapping) for row in result]
            
            if research_data:
                regime = research_data[0].get('regime')
                buckets = research_data[0].get('buckets', [])
                result_data = {
                    'research_data': research_data,
                    'regime': regime,
                    'buckets': buckets,
                    'has_data': True
                }
            else:
                print(f"ERROR: No macro research data available for {end_date}")
                result_data = {
                    'research_data': [],
                    'regime': None,
                    'buckets': [],
                    'has_data': False
                }
            
            self.cache[cache_key] = result_data
            return result_data
                
        except Exception as e:
            print(f"ERROR: Could not fetch macro data: {e}")
            return {
                'research_data': [],
                'regime': None,
                'buckets': [],
                'has_data': False
            }
        finally:
            db.close()
    
    def get_trending_assets(self, tickers: List[str], end_date: str, limit: int = 10, min_confidence: float = 0.7) -> List[str]:
        if not self.database_available:
            return tickers[:limit]
        
        cache_key = f"trending_{end_date}_{len(tickers)}_{limit}_{min_confidence}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        db = SessionLocal()
        try:
            result = db.execute(text("""
                SELECT * FROM scanner_historical
                WHERE ticker = ANY(:tickers)
                AND confidence >= :min_confidence
                AND market = 'trending'
                AND date <= :end_date
                ORDER BY confidence DESC, date DESC
                LIMIT :limit
            """), {"tickers": tickers, "end_date": end_date, "limit": limit, "min_confidence": min_confidence})
            
            trending_data = [dict(row._mapping) for row in result]
            trending_tickers = [item['ticker'] for item in trending_data]
            
            if trending_tickers:
                result_tickers = trending_tickers
            else:
                result_tickers = tickers[:limit]
            
            self.cache[cache_key] = result_tickers
            return result_tickers
                
        except Exception as e:
            print(f"Warning: Could not fetch trending assets: {e}")
            return tickers[:limit]
        finally:
            db.close()
    
    def get_market_sentiment_data(self, date: str) -> Dict:
        if not self.database_available:
            print("ERROR: Database connection not available - cannot get sentiment data")
            return {
                'sentiment_score': 0.5,
                'research_count': 0,
                'date': date
            }
        
        cache_key = f"sentiment_{date}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        db = SessionLocal()
        try:
            # Look for research data around the given date
            result = db.execute(text("""
                SELECT plain_text, created_at
                FROM research 
                WHERE created_at <= :date
                ORDER BY created_at DESC 
                LIMIT 3
            """), {"date": date})
            
            research_entries = [dict(row._mapping) for row in result]
            
            sentiment_score = self._analyze_sentiment_from_research(research_entries)
            
            result_data = {
                'sentiment_score': sentiment_score,
                'research_count': len(research_entries),
                'date': date
            }
            
            self.cache[cache_key] = result_data
            return result_data
                
        except Exception as e:
            print(f"ERROR: Could not fetch sentiment data: {e}")
            return {
                'sentiment_score': 0.5,
                'research_count': 0,
                'date': date
            }
        finally:
            db.close()
    
    def get_regime_change_history(self, start_date: str, end_date: str) -> pd.DataFrame:
        dates = pd.date_range(start_date, end_date, freq='W')  # Weekly sampling
        regime_history = []
        
        for date in dates:
            date_str = date.strftime('%Y-%m-%d')
            macro_data = self.get_macro_research_data(date_str)
            
            regime_history.append({
                'date': date,
                'regime': macro_data.get('regime', 'Goldilocks'),
                'buckets': macro_data.get('buckets', []),
                'has_data': macro_data['has_data']
            })
        
        return pd.DataFrame(regime_history)
    
    def _extract_top_markets(self, text: str) -> List[str]:
        import re
        
        if not text:
            return []
        
        clean = re.sub(r'\s+', ' ', text).strip()
        pattern = r'considerations.*?are:(.*?)(?:\.|$)'
        match = re.search(pattern, clean, re.IGNORECASE)
        
        if not match:
            return []
        
        body = match.group(1).strip()
        parts = re.split(r',\s*(?:and\s*)?', body, flags=re.IGNORECASE)
        
        winners = []
        for part in parts:
            idx = part.find('>')
            if idx == -1:
                continue
            winner = part[:idx].rstrip('.,').strip()
            if winner:
                winners.append(winner)
        
        return winners
    
    def _analyze_sentiment_from_research(self, research_entries: List[Dict]) -> float:
        if not research_entries:
            return 0.5  # Neutral
        
        sentiment_indicators = {
            'positive': ['bullish', 'optimistic', 'growth', 'expansion', 'strong', 'positive'],
            'negative': ['bearish', 'pessimistic', 'recession', 'contraction', 'weak', 'negative', 'decline']
        }
        
        total_score = 0
        total_entries = 0
        
        for entry in research_entries:
            if not entry.get('plain_text'):
                continue
            
            text_lower = entry['plain_text'].lower()
            positive_count = sum(1 for indicator in sentiment_indicators['positive'] if indicator in text_lower)
            negative_count = sum(1 for indicator in sentiment_indicators['negative'] if indicator in text_lower)
            
            if positive_count + negative_count > 0:
                entry_score = positive_count / (positive_count + negative_count)
                total_score += entry_score
                total_entries += 1
        
        return total_score / total_entries if total_entries > 0 else 0.5
    
    def _determine_regime_from_macro(self, top_markets: List[str]) -> str:
        if not top_markets:
            return 'Risk On'  # Default
        
        risk_indicators = ['Risk Assets', 'High Beta', 'Growth']
        defensive_indicators = ['Defensive Assets', 'Treasurys', 'Gold']
        
        risk_score = sum(1 for market in top_markets if market in risk_indicators)
        defensive_score = sum(1 for market in top_markets if market in defensive_indicators)
        
        if risk_score > defensive_score:
            return 'Risk On'
        elif defensive_score > risk_score:
            return 'Risk Off'
        else:
            return 'Rotation'
    
    def _determine_regime_from_sentiment(self, sentiment_score: float) -> str:
        if sentiment_score > 0.7:
            return 'Risk On'
        elif sentiment_score < 0.3:
            return 'Risk Off'
        else:
            return 'Rotation'
    
