import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

try:
    import ta
    TA_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False
    print("Warning: 'ta' package not available. Install with: pip install ta")


class TechnicalAnalyzer:
    def __init__(self, 
                 timeframe_weights: Dict[str, float] = None,
                 indicator_weights: Dict[str, float] = None):
        
        if not TA_AVAILABLE:
            raise ImportError("ta package is required for technical analysis. Install with: pip install ta")
        
        # Default timeframe weights (higher weight = more importance)
        self.timeframe_weights = timeframe_weights or {
            '1d': 0.5,   # Daily trend most important
            '4h': 0.3,   # 4h momentum
            '1h': 0.2    # Short-term entry timing
        }
        
        # Default indicator category weights
        self.indicator_weights = indicator_weights or {
            'trend': 0.35,       # Trend indicators (SMA, EMA, ADX)
            'momentum': 0.25,    # Momentum indicators (RSI, MACD, Stochastic)
            'volume': 0.15,      # Volume indicators (OBV, Volume SMA)
            'volatility': 0.15,  # Volatility indicators (Bollinger Bands, ATR)
            'others': 0.10       # Other indicators (Williams %R, etc.)
        }
        
        # Scoring thresholds
        self.strong_bullish_threshold = 0.8
        self.bullish_threshold = 0.6
        self.neutral_threshold = 0.4
        self.bearish_threshold = 0.2
    
    def analyze_multi_timeframe(self, 
                               timeframe_data: Dict[str, pd.DataFrame], 
                               asset: str, 
                               current_date: datetime) -> float:
        """Analyze asset across multiple timeframes and return combined score"""
        
        timeframe_scores = {}
        
        for timeframe, data in timeframe_data.items():
            if data is None or data.empty:
                continue
                
            score = self._analyze_single_timeframe(data, timeframe)
            timeframe_scores[timeframe] = score
        
        if not timeframe_scores:
            return 0.0
        
        # Weight and combine timeframe scores
        weighted_score = 0.0
        total_weight = 0.0
        
        for timeframe, score in timeframe_scores.items():
            weight = self.timeframe_weights.get(timeframe, 0.33)
            weighted_score += score * weight
            total_weight += weight
        
        # Normalize by total weight
        final_score = weighted_score / total_weight if total_weight > 0 else 0.0
        
        return max(0.0, min(1.0, final_score))
    
    def _analyze_single_timeframe(self, data: pd.DataFrame, timeframe: str) -> float:
        """Analyze single timeframe data and return technical score"""
        
        if data is None or len(data) < 20:
            return 0.0
        
        try:
            # Calculate all technical indicators
            indicators = self._calculate_indicators(data)
            
            # Score each indicator category
            category_scores = {
                'trend': self._score_trend_indicators(indicators, data),
                'momentum': self._score_momentum_indicators(indicators, data),
                'volume': self._score_volume_indicators(indicators, data),
                'volatility': self._score_volatility_indicators(indicators, data),
                'others': self._score_other_indicators(indicators, data)
            }
            
            # Weight and combine category scores
            final_score = 0.0
            for category, score in category_scores.items():
                weight = self.indicator_weights.get(category, 0.2)
                final_score += score * weight
            
            return max(0.0, min(1.0, final_score))
            
        except Exception as e:
            print(f"Error analyzing timeframe {timeframe}: {e}")
            return 0.0
    
    def _calculate_indicators(self, data: pd.DataFrame) -> Dict:
        """Calculate technical indicators using ta library"""
        indicators = {}
        
        try:
            # Trend indicators
            indicators['sma_20'] = ta.trend.sma_indicator(data['Close'], window=20)
            indicators['sma_50'] = ta.trend.sma_indicator(data['Close'], window=50)
            indicators['ema_12'] = ta.trend.ema_indicator(data['Close'], window=12)
            indicators['ema_26'] = ta.trend.ema_indicator(data['Close'], window=26)
            indicators['adx'] = ta.trend.adx(data['High'], data['Low'], data['Close'], window=14)
            
            # Momentum indicators
            indicators['rsi'] = ta.momentum.rsi(data['Close'], window=14)
            indicators['macd'] = ta.trend.macd_diff(data['Close'])
            indicators['stoch'] = ta.momentum.stoch(data['High'], data['Low'], data['Close'])
            indicators['williams_r'] = ta.momentum.williams_r(data['High'], data['Low'], data['Close'])
            
            # Volume indicators
            if 'Volume' in data.columns and not data['Volume'].isna().all():
                indicators['obv'] = ta.volume.on_balance_volume(data['Close'], data['Volume'])
                indicators['volume_sma'] = data['Volume'].rolling(window=20).mean()  # Simple volume SMA
            
            # Volatility indicators
            bb_bands = ta.volatility.BollingerBands(data['Close'])
            indicators['bb_upper'] = bb_bands.bollinger_hband()
            indicators['bb_lower'] = bb_bands.bollinger_lband()
            indicators['bb_middle'] = bb_bands.bollinger_mavg()
            indicators['atr'] = ta.volatility.average_true_range(data['High'], data['Low'], data['Close'])
            
            # Other indicators
            indicators['cci'] = ta.trend.cci(data['High'], data['Low'], data['Close'])
            
        except Exception as e:
            print(f"Error calculating indicators: {e}")
        
        return indicators
    
    def _score_trend_indicators(self, indicators: Dict, data: pd.DataFrame) -> float:
        """Score trend-based indicators"""
        scores = []
        current_price = data['Close'].iloc[-1]
        
        try:
            # SMA crossovers
            if 'sma_20' in indicators and 'sma_50' in indicators:
                sma_20 = indicators['sma_20'].iloc[-1]
                sma_50 = indicators['sma_50'].iloc[-1]
                
                if pd.notna(sma_20) and pd.notna(sma_50):
                    # Price above both SMAs = bullish
                    if current_price > sma_20 > sma_50:
                        scores.append(0.8)
                    elif current_price > sma_20:
                        scores.append(0.6)
                    elif current_price < sma_20 < sma_50:
                        scores.append(0.2)
                    else:
                        scores.append(0.4)
            
            # EMA trend
            if 'ema_12' in indicators and 'ema_26' in indicators:
                ema_12 = indicators['ema_12'].iloc[-1]
                ema_26 = indicators['ema_26'].iloc[-1]
                
                if pd.notna(ema_12) and pd.notna(ema_26):
                    if ema_12 > ema_26:
                        scores.append(0.7)
                    else:
                        scores.append(0.3)
            
            # ADX strength
            if 'adx' in indicators:
                adx = indicators['adx'].iloc[-1]
                if pd.notna(adx):
                    if adx > 25:
                        scores.append(0.7)  # Strong trend
                    elif adx > 15:
                        scores.append(0.5)  # Moderate trend
                    else:
                        scores.append(0.3)  # Weak trend
            
        except Exception as e:
            print(f"Error scoring trend indicators: {e}")
        
        return np.mean(scores) if scores else 0.5
    
    def _score_momentum_indicators(self, indicators: Dict, data: pd.DataFrame) -> float:
        """Score momentum-based indicators"""
        scores = []
        
        try:
            # RSI
            if 'rsi' in indicators:
                rsi = indicators['rsi'].iloc[-1]
                if pd.notna(rsi):
                    if 30 <= rsi <= 70:
                        scores.append(0.6)  # Neutral zone
                    elif rsi > 70:
                        scores.append(0.3)  # Overbought
                    elif rsi < 30:
                        scores.append(0.8)  # Oversold (potential bounce)
                    else:
                        scores.append(0.5)
            
            # MACD
            if 'macd' in indicators:
                macd = indicators['macd'].iloc[-1]
                if pd.notna(macd):
                    if macd > 0:
                        scores.append(0.7)
                    else:
                        scores.append(0.3)
            
            # Stochastic
            if 'stoch' in indicators:
                stoch = indicators['stoch'].iloc[-1]
                if pd.notna(stoch):
                    if 20 <= stoch <= 80:
                        scores.append(0.6)
                    elif stoch > 80:
                        scores.append(0.3)  # Overbought
                    else:
                        scores.append(0.8)  # Oversold
            
            # Williams %R
            if 'williams_r' in indicators:
                williams = indicators['williams_r'].iloc[-1]
                if pd.notna(williams):
                    if -80 <= williams <= -20:
                        scores.append(0.6)
                    elif williams > -20:
                        scores.append(0.3)  # Overbought
                    else:
                        scores.append(0.8)  # Oversold
            
        except Exception as e:
            print(f"Error scoring momentum indicators: {e}")
        
        return np.mean(scores) if scores else 0.5
    
    def _score_volume_indicators(self, indicators: Dict, data: pd.DataFrame) -> float:
        """Score volume-based indicators"""
        scores = []
        
        try:
            # On Balance Volume trend
            if 'obv' in indicators and len(indicators['obv']) > 5:
                obv_recent = indicators['obv'].iloc[-5:].values
                if len(obv_recent) > 1:
                    obv_trend = np.polyfit(range(len(obv_recent)), obv_recent, 1)[0]
                    if obv_trend > 0:
                        scores.append(0.7)  # Volume supporting uptrend
                    else:
                        scores.append(0.3)  # Volume not supporting
            
            # Volume compared to average
            if 'Volume' in data.columns and not data['Volume'].isna().all():
                recent_volume = data['Volume'].iloc[-1]
                avg_volume = data['Volume'].rolling(20).mean().iloc[-1]
                
                if pd.notna(recent_volume) and pd.notna(avg_volume) and avg_volume > 0:
                    volume_ratio = recent_volume / avg_volume
                    if volume_ratio > 1.5:
                        scores.append(0.7)  # High volume
                    elif volume_ratio > 1.0:
                        scores.append(0.6)  # Above average
                    else:
                        scores.append(0.4)  # Below average
            
        except Exception as e:
            print(f"Error scoring volume indicators: {e}")
        
        return np.mean(scores) if scores else 0.5
    
    def _score_volatility_indicators(self, indicators: Dict, data: pd.DataFrame) -> float:
        """Score volatility-based indicators"""
        scores = []
        current_price = data['Close'].iloc[-1]
        
        try:
            # Bollinger Bands position
            if all(k in indicators for k in ['bb_upper', 'bb_lower', 'bb_middle']):
                bb_upper = indicators['bb_upper'].iloc[-1]
                bb_lower = indicators['bb_lower'].iloc[-1]
                bb_middle = indicators['bb_middle'].iloc[-1]
                
                if all(pd.notna([bb_upper, bb_lower, bb_middle])):
                    if current_price > bb_upper:
                        scores.append(0.3)  # Above upper band (overbought)
                    elif current_price < bb_lower:
                        scores.append(0.8)  # Below lower band (oversold)
                    elif current_price > bb_middle:
                        scores.append(0.6)  # Above middle (bullish)
                    else:
                        scores.append(0.4)  # Below middle (bearish)
            
            # ATR for volatility assessment
            if 'atr' in indicators:
                atr = indicators['atr'].iloc[-1]
                if pd.notna(atr):
                    # Normalize ATR as percentage of price
                    atr_pct = (atr / current_price) * 100
                    if atr_pct < 2:
                        scores.append(0.6)  # Low volatility
                    elif atr_pct < 5:
                        scores.append(0.5)  # Moderate volatility
                    else:
                        scores.append(0.4)  # High volatility
            
        except Exception as e:
            print(f"Error scoring volatility indicators: {e}")
        
        return np.mean(scores) if scores else 0.5
    
    def _score_other_indicators(self, indicators: Dict, data: pd.DataFrame) -> float:
        """Score other technical indicators"""
        scores = []
        
        try:
            # Commodity Channel Index
            if 'cci' in indicators:
                cci = indicators['cci'].iloc[-1]
                if pd.notna(cci):
                    if -100 <= cci <= 100:
                        scores.append(0.5)  # Normal range
                    elif cci > 100:
                        scores.append(0.3)  # Overbought
                    else:
                        scores.append(0.7)  # Oversold
            
        except Exception as e:
            print(f"Error scoring other indicators: {e}")
        
        return np.mean(scores) if scores else 0.5
    
    def get_technical_summary(self, 
                             timeframe_data: Dict[str, pd.DataFrame], 
                             asset: str) -> Dict:
        """Get detailed technical analysis summary"""
        
        summary = {
            'asset': asset,
            'overall_score': self.analyze_multi_timeframe(timeframe_data, asset, datetime.now()),
            'timeframe_scores': {},
            'signal': 'NEUTRAL'
        }
        
        # Calculate individual timeframe scores
        for timeframe, data in timeframe_data.items():
            if data is not None and not data.empty:
                score = self._analyze_single_timeframe(data, timeframe)
                summary['timeframe_scores'][timeframe] = score
        
        # Determine overall signal
        overall_score = summary['overall_score']
        if overall_score >= self.strong_bullish_threshold:
            summary['signal'] = 'STRONG_BUY'
        elif overall_score >= self.bullish_threshold:
            summary['signal'] = 'BUY'
        elif overall_score >= self.neutral_threshold:
            summary['signal'] = 'NEUTRAL'
        elif overall_score >= self.bearish_threshold:
            summary['signal'] = 'SELL'
        else:
            summary['signal'] = 'STRONG_SELL'
        
        return summary