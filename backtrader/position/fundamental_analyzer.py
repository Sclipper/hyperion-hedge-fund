import sys
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

try:
    from app.backend.database.connection import SessionLocal
    from sqlalchemy import text
    DATABASE_AVAILABLE = True
except ImportError:
    SessionLocal = None
    DATABASE_AVAILABLE = False
    print("Warning: Database connection not available for fundamental analysis.")


class FundamentalAnalyzer:
    def __init__(self):
        self.database_available = DATABASE_AVAILABLE
        self.cache = {}
        
        # Scoring weights for different fundamental factors
        self.factor_weights = {
            'financial_health': 0.3,    # Balance sheet strength
            'profitability': 0.25,      # Revenue, margins, growth
            'valuation': 0.2,           # P/E, P/B, market cap metrics  
            'momentum': 0.15,           # Recent financial trends
            'regime_fit': 0.1           # How well asset fits current regime
        }
        
        # Industry/sector scoring adjustments
        self.sector_adjustments = {
            'technology': {'growth_weight': 1.2, 'valuation_tolerance': 1.5},
            'utilities': {'dividend_weight': 1.3, 'stability_weight': 1.2},
            'financials': {'book_value_weight': 1.3, 'regulatory_weight': 0.9},
            'energy': {'commodity_correlation': 1.2, 'volatility_tolerance': 1.1},
            'healthcare': {'rd_weight': 1.2, 'regulatory_weight': 0.8},
            'consumer': {'brand_strength': 1.1, 'economic_sensitivity': 1.0}
        }
    
    def analyze_asset(self, asset: str, current_date: datetime, regime: str) -> float:
        """Analyze fundamental strength of an asset (stocks + crypto)"""
        
        try:
            # Detect asset type for appropriate analysis
            is_crypto = self._is_crypto_asset(asset)
            
            # Get data appropriate for asset type
            financial_data = self._get_financial_data(asset, current_date, is_crypto)
            market_data = self._get_market_data(asset, current_date, is_crypto)
            
            # Adjust factor weights based on asset type
            factor_weights = self._get_asset_type_weights(is_crypto)
            
            # Calculate component scores
            scores = {
                'financial_health': self._score_financial_health(financial_data, is_crypto),
                'profitability': self._score_profitability(financial_data, is_crypto),
                'valuation': self._score_valuation(financial_data, market_data, is_crypto),
                'momentum': self._score_momentum(financial_data, market_data, is_crypto),
                'regime_fit': self._score_regime_fit(asset, regime, market_data, is_crypto)
            }
            
            # Weight and combine scores with asset-specific weights
            final_score = 0.0
            valid_scores = 0
            for factor, score in scores.items():
                if score is not None:  # Only include valid scores
                    weight = factor_weights.get(factor, 0.2)
                    final_score += score * weight
                    valid_scores += 1
            
            # If no valid scores, return neutral
            if valid_scores == 0:
                return 0.5
            
            # Apply sector adjustments if needed
            final_score = self._apply_sector_adjustments(asset, final_score, scores, is_crypto)
            
            return max(0.0, min(1.0, final_score))
            
        except Exception as e:
            print(f"Error in fundamental analysis for {asset}: {e}")
            return 0.5

    def _is_crypto_asset(self, asset: str) -> bool:
        """Detect if asset is cryptocurrency using centralized asset bucket manager"""
        # Import here to avoid circular imports
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.append(parent_dir)
        
        from data.asset_buckets import AssetBucketManager
        
        # Use centralized crypto detection
        asset_manager = AssetBucketManager()
        crypto_assets = asset_manager.filter_assets_by_type([asset], 'crypto')
        return len(crypto_assets) > 0
    
    def _get_asset_type_weights(self, is_crypto: bool) -> Dict[str, float]:
        """Get factor weights appropriate for asset type"""
        if is_crypto:
            # Crypto assets: focus on momentum and regime fit, minimal fundamentals
            return {
                'financial_health': 0.05,    # Very low - no traditional financials
                'profitability': 0.05,       # Very low - no traditional profitability
                'valuation': 0.20,           # Medium - market cap, adoption metrics
                'momentum': 0.40,            # High - price action, volume trends
                'regime_fit': 0.30           # High - macro environment alignment
            }
        else:
            # Traditional stocks: standard fundamental analysis
            return self.factor_weights
    
    def _get_financial_data(self, asset: str, current_date: datetime, is_crypto: bool = False) -> Dict:
        """Get financial data from database or external sources"""
        
        cache_key = f"financial_{asset}_{current_date.strftime('%Y-%m-%d')}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Crypto assets don't have traditional financial statements
        if is_crypto:
            # For crypto, return empty financial data - rely on market data
            financial_data = {}
            self.cache[cache_key] = financial_data
            return financial_data
        
        # Try to get data from your existing tools/API integrations for stocks
        try:
            # This would integrate with your existing financial data tools
            # from src.tools.api import get_financial_metrics, search_line_items
            
            print(f"WARNING: No real financial data source configured for stock {asset}")
            print("CRITICAL: Stock fundamental analysis requires real financial data")
            
            # Return empty data instead of mock data
            financial_data = {}
            self.cache[cache_key] = financial_data
            return financial_data
            
        except Exception as e:
            print(f"ERROR: Could not fetch financial data for {asset}: {e}")
            return {}
    
    def _get_market_data(self, asset: str, current_date: datetime, is_crypto: bool = False) -> Dict:
        """Get market-related data for stocks and crypto"""
        
        cache_key = f"market_{asset}_{current_date.strftime('%Y-%m-%d')}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            if is_crypto:
                # For crypto, provide basic fallback data structure (empty but structured)
                market_data = self._get_crypto_market_fallback(asset, current_date)
                print(f"INFO: Using crypto market fallback for {asset} - real data integration recommended")
            else:
                print(f"WARNING: No real stock market data source configured for {asset}")
                print("CRITICAL: Stock market analysis requires real market data")
                market_data = {}
            
            self.cache[cache_key] = market_data
            return market_data
            
        except Exception as e:
            print(f"ERROR: Could not fetch market data for {asset}: {e}")
            return {}
    
    def _get_crypto_market_fallback(self, asset: str, current_date: datetime) -> Dict:
        """Provide basic crypto market data structure for fallback scoring"""
        
        # This provides empty but structured data for crypto assets
        # In production, you'd integrate with crypto APIs (CoinGecko, CoinMarketCap, etc.)
        fallback_data = {
            # Market metrics (would come from crypto APIs)
            'market_cap': None,
            'volume_24h': None,
            'price_change_24h': None,
            'price_change_7d': None,
            'price_change_30d': None,
            
            # Technical metrics (could be calculated from price data)
            'volatility_30d': None,
            'volume_to_market_cap_ratio': None,
            
            # Crypto-specific metrics
            'circulating_supply': None,
            'total_supply': None,
            
            # Metadata
            'data_source': 'fallback',
            'requires_real_integration': True
        }
        
        return fallback_data
    
    def _score_financial_health(self, financial_data: Dict, is_crypto: bool = False) -> float:
        """Score balance sheet strength and financial stability"""
        
        # Crypto assets don't have traditional balance sheets
        if is_crypto:
            return None  # Skip this scoring component for crypto
        
        if not financial_data:
            return 0.5
        
        scores = []
        
        try:
            # Debt-to-equity ratio
            if 'total_debt' in financial_data and 'shareholders_equity' in financial_data:
                debt = financial_data['total_debt']
                equity = financial_data['shareholders_equity']
                
                if equity > 0:
                    debt_to_equity = debt / equity
                    if debt_to_equity < 0.3:
                        scores.append(0.9)  # Very low leverage
                    elif debt_to_equity < 0.6:
                        scores.append(0.7)  # Moderate leverage
                    elif debt_to_equity < 1.0:
                        scores.append(0.5)  # High leverage
                    else:
                        scores.append(0.2)  # Very high leverage
            
            # Current ratio (liquidity)
            if 'current_assets' in financial_data and 'current_liabilities' in financial_data:
                current_assets = financial_data['current_assets']
                current_liabilities = financial_data['current_liabilities']
                
                if current_liabilities > 0:
                    current_ratio = current_assets / current_liabilities
                    if current_ratio > 2.0:
                        scores.append(0.8)
                    elif current_ratio > 1.5:
                        scores.append(0.7)
                    elif current_ratio > 1.0:
                        scores.append(0.5)
                    else:
                        scores.append(0.2)
            
            # Cash position
            if 'cash_and_equivalents' in financial_data and 'total_debt' in financial_data:
                cash = financial_data['cash_and_equivalents']
                debt = financial_data['total_debt']
                
                if debt > 0:
                    cash_to_debt = cash / debt
                    if cash_to_debt > 1.0:
                        scores.append(0.9)  # More cash than debt
                    elif cash_to_debt > 0.5:
                        scores.append(0.7)
                    elif cash_to_debt > 0.2:
                        scores.append(0.5)
                    else:
                        scores.append(0.3)
            
        except Exception as e:
            print(f"Error scoring financial health: {e}")
        
        return np.mean(scores) if scores else 0.5
    
    def _score_profitability(self, financial_data: Dict, is_crypto: bool = False) -> float:
        """Score profitability metrics and trends"""
        
        # Crypto assets don't have traditional profitability metrics
        if is_crypto:
            return None  # Skip this scoring component for crypto
        
        if not financial_data:
            return 0.5
        
        scores = []
        
        try:
            # Operating margin
            if 'operating_margin' in financial_data:
                margin = financial_data['operating_margin']
                if margin > 0.2:  # > 20%
                    scores.append(0.9)
                elif margin > 0.15:
                    scores.append(0.7)
                elif margin > 0.1:
                    scores.append(0.6)
                elif margin > 0.05:
                    scores.append(0.4)
                else:
                    scores.append(0.2)
            
            # Return on Equity
            if 'net_income' in financial_data and 'shareholders_equity' in financial_data:
                net_income = financial_data['net_income']
                equity = financial_data['shareholders_equity']
                
                if equity > 0:
                    roe = net_income / equity
                    if roe > 0.2:  # > 20%
                        scores.append(0.9)
                    elif roe > 0.15:
                        scores.append(0.7)
                    elif roe > 0.1:
                        scores.append(0.6)
                    elif roe > 0.05:
                        scores.append(0.4)
                    else:
                        scores.append(0.2)
            
            # Revenue growth (if historical data available)
            if 'revenue_growth' in financial_data:
                growth = financial_data['revenue_growth']
                if growth > 0.2:  # > 20%
                    scores.append(0.9)
                elif growth > 0.1:
                    scores.append(0.7)
                elif growth > 0.05:
                    scores.append(0.6)
                elif growth > 0:
                    scores.append(0.5)
                else:
                    scores.append(0.2)
            
        except Exception as e:
            print(f"Error scoring profitability: {e}")
        
        return np.mean(scores) if scores else 0.5
    
    def _score_valuation(self, financial_data: Dict, market_data: Dict, is_crypto: bool = False) -> float:
        """Score valuation metrics"""
        
        if not financial_data and not market_data:
            return 0.5
        
        scores = []
        
        try:
            # P/E ratio
            if 'market_cap' in market_data and 'net_income' in financial_data:
                market_cap = market_data['market_cap']
                net_income = financial_data['net_income']
                
                if net_income > 0:
                    pe_ratio = market_cap / net_income
                    if pe_ratio < 15:
                        scores.append(0.8)  # Undervalued
                    elif pe_ratio < 25:
                        scores.append(0.6)  # Fair value
                    elif pe_ratio < 40:
                        scores.append(0.4)  # Expensive
                    else:
                        scores.append(0.2)  # Very expensive
            
            # P/B ratio
            if 'market_cap' in market_data and 'shareholders_equity' in financial_data:
                market_cap = market_data['market_cap']
                book_value = financial_data['shareholders_equity']
                
                if book_value > 0:
                    pb_ratio = market_cap / book_value
                    if pb_ratio < 1.5:
                        scores.append(0.8)
                    elif pb_ratio < 3:
                        scores.append(0.6)
                    elif pb_ratio < 5:
                        scores.append(0.4)
                    else:
                        scores.append(0.2)
            
            # Price momentum (not strictly fundamental, but value-relevant)
            if 'price_change_1m' in market_data:
                change_1m = market_data['price_change_1m']
                if -0.1 <= change_1m <= 0.2:  # -10% to +20% range is healthy
                    scores.append(0.6)
                elif change_1m > 0.2:
                    scores.append(0.4)  # Too much momentum
                else:
                    scores.append(0.3)  # Poor momentum
            
        except Exception as e:
            print(f"Error scoring valuation: {e}")
        
        return np.mean(scores) if scores else 0.5
    
    def _score_momentum(self, financial_data: Dict, market_data: Dict, is_crypto: bool = False) -> float:
        """Score recent financial and market momentum"""
        
        scores = []
        
        try:
            # Earnings revision trends (if available)
            if 'earnings_revision_trend' in financial_data:
                trend = financial_data['earnings_revision_trend']
                if trend > 0.1:
                    scores.append(0.8)
                elif trend > 0:
                    scores.append(0.6)
                elif trend > -0.1:
                    scores.append(0.4)
                else:
                    scores.append(0.2)
            
            # Recent revenue growth acceleration
            if 'revenue_growth_acceleration' in financial_data:
                acceleration = financial_data['revenue_growth_acceleration']
                if acceleration > 0:
                    scores.append(0.7)
                else:
                    scores.append(0.3)
            
            # Market momentum vs sector
            if 'relative_performance' in market_data:
                rel_perf = market_data['relative_performance']
                if rel_perf > 0.05:  # Outperforming sector by 5%+
                    scores.append(0.8)
                elif rel_perf > 0:
                    scores.append(0.6)
                elif rel_perf > -0.05:
                    scores.append(0.4)
                else:
                    scores.append(0.2)
            
        except Exception as e:
            print(f"Error scoring momentum: {e}")
        
        return np.mean(scores) if scores else 0.5
    
    def _score_regime_fit(self, asset: str, regime: str, market_data: Dict, is_crypto: bool = False) -> float:
        """Score how well asset fits current market regime"""
        
        try:
            # Different regimes favor different asset characteristics
            regime_preferences = {
                'Goldilocks': {
                    'growth_stocks': 0.8,
                    'large_cap': 0.7,
                    'tech': 0.8,
                    'high_beta': 0.6,
                    'crypto': 0.7  # Moderate crypto preference in risk-on environment
                },
                'Reflation': {
                    'cyclicals': 0.8,
                    'value_stocks': 0.8,
                    'industrials': 0.7,
                    'materials': 0.7,
                    'crypto': 0.5  # Neutral crypto in reflation
                },
                'Inflation': {
                    'commodities': 0.9,
                    'real_assets': 0.8,
                    'energy': 0.8,
                    'value_stocks': 0.7,
                    'crypto': 0.8  # High crypto preference as inflation hedge
                },
                'Deflation': {
                    'defensives': 0.8,
                    'bonds': 0.9,
                    'utilities': 0.8,
                    'staples': 0.7,
                    'crypto': 0.3  # Low crypto preference in risk-off
                }
            }
            
            # Determine asset characteristics
            asset_score = 0.5  # Default neutral
            
            # Check if asset fits regime preferences
            if regime in regime_preferences:
                preferences = regime_preferences[regime]
                
                if is_crypto:
                    # Crypto assets get crypto-specific scoring
                    asset_score = preferences.get('crypto', 0.5)
                else:
                    # Stock-specific heuristics
                    asset_upper = asset.upper()
                    
                    if any(tech in asset_upper for tech in ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA']):
                        asset_score = preferences.get('tech', preferences.get('growth_stocks', 0.5))
                    elif any(def_asset in asset_upper for def_asset in ['XLU', 'PG', 'KO', 'JNJ']):
                        asset_score = preferences.get('defensives', 0.5)
                    elif any(energy in asset_upper for energy in ['XOM', 'CVX', 'XLE', 'USO']):
                        asset_score = preferences.get('energy', preferences.get('commodities', 0.5))
                    elif any(fin in asset_upper for fin in ['JPM', 'BAC', 'WFC', 'XLF']):
                        asset_score = preferences.get('cyclicals', 0.5)
            
            return asset_score
            
        except Exception as e:
            print(f"Error scoring regime fit: {e}")
            return 0.5
    
    def _apply_sector_adjustments(self, asset: str, base_score: float, component_scores: Dict, is_crypto: bool = False) -> float:
        """Apply sector-specific adjustments to the score"""
        
        if is_crypto:
            # For crypto, no sector adjustments needed
            return base_score
        
        # This is a simplified implementation
        # In practice, you'd have a more sophisticated sector classification
        
        return base_score  # No adjustments for now
    
    
    def get_fundamental_summary(self, asset: str, current_date: datetime, regime: str) -> Dict:
        """Get detailed fundamental analysis summary"""
        
        financial_data = self._get_financial_data(asset, current_date)
        market_data = self._get_market_data(asset, current_date)
        
        component_scores = {
            'financial_health': self._score_financial_health(financial_data),
            'profitability': self._score_profitability(financial_data),
            'valuation': self._score_valuation(financial_data, market_data),
            'momentum': self._score_momentum(financial_data, market_data),
            'regime_fit': self._score_regime_fit(asset, regime, market_data)
        }
        
        overall_score = sum(
            score * self.factor_weights.get(factor, 0.2) 
            for factor, score in component_scores.items()
        )
        
        return {
            'asset': asset,
            'overall_score': overall_score,
            'component_scores': component_scores,
            'regime': regime,
            'analysis_date': current_date.isoformat(),
            'recommendation': self._get_recommendation(overall_score)
        }
    
    def _get_recommendation(self, score: float) -> str:
        """Convert score to recommendation"""
        if score >= 0.8:
            return 'STRONG_BUY'
        elif score >= 0.65:
            return 'BUY'
        elif score >= 0.45:
            return 'HOLD'
        elif score >= 0.3:
            return 'SELL'
        else:
            return 'STRONG_SELL'