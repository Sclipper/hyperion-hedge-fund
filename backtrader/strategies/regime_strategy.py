import backtrader as bt
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
from position.position_manager import PositionManager
from position.position_manager_optimized import PositionManagerOptimized
from position.technical_analyzer import TechnicalAnalyzer
from position.fundamental_analyzer import FundamentalAnalyzer


class RegimeStrategy(bt.Strategy):
    params = (
        ('rebalance_frequency', 'monthly'),  # 'daily', 'weekly', 'monthly'
        ('max_assets_per_period', 5),  # Maximum assets to hold
        ('sma_period', 20),
        ('rsi_period', 14),
        ('rsi_lower', 30),
        ('rsi_upper', 70),
        ('momentum_period', 10),
        ('stop_loss', 0.05),
        ('take_profit', 0.15),
        ('min_regime_confidence', 0.6),
        ('bucket_names', None),
        ('position_min_score', 0.6),  # Minimum position score threshold
        ('timeframes', ['1d', '4h', '1h']),  # Timeframes for technical analysis
        ('enable_technical_analysis', True),  # Enable/disable technical analysis
        ('enable_fundamental_analysis', True),  # Enable/disable fundamental analysis
        ('technical_weight', 0.6),  # Weight for technical analysis
        ('fundamental_weight', 0.4),  # Weight for fundamental analysis
        ('min_trending_confidence', 0.7),  # Minimum confidence for trending assets
        
        # External dependencies (passed from main.py)
        ('regime_detector', None),  # RegimeDetector instance
        ('asset_manager', None),    # AssetBucketManager instance
        ('data_manager', None),     # DataManager instance
        ('data_preloader', None),   # DataPreloader instance for optimized performance
        
        # Core Asset Management Parameters (Module 5)
        ('enable_core_assets', False),
        ('max_core_assets', 3),
        ('core_override_threshold', 0.95),
        ('core_expiry_days', 90),
        ('core_underperformance_threshold', 0.15),
        ('core_underperformance_period', 30),
        ('core_extension_limit', 2),
        ('core_performance_check_frequency', 7),
        ('smart_diversification_overrides', 2),
        ('enable_take_profit_stop_loss', False),  # Enable/disable take-profit and stop-loss
    )
    
    def __init__(self):
        self.regime_detector = self.p.regime_detector
        self.asset_manager = self.p.asset_manager
        self.data_manager = self.p.data_manager
        self.data_preloader = self.p.data_preloader
        
        # Initialize position management system
        try:
            self.technical_analyzer = TechnicalAnalyzer(
                timeframe_weights={'1d': 0.5, '4h': 0.3, '1h': 0.2}
            )
        except ImportError:
            print("Warning: Technical analyzer not available. Using simplified scoring.")
            self.technical_analyzer = None
        
        # Initialize fundamental analyzer only if enabled
        if self.params.enable_fundamental_analysis:
            self.fundamental_analyzer = FundamentalAnalyzer()
        else:
            self.fundamental_analyzer = None
        
        # Use optimized position manager if data_preloader is provided
        if self.data_preloader:
            self.position_manager = PositionManagerOptimized(
                data_preloader=self.data_preloader,
                technical_analyzer=self.technical_analyzer,
                fundamental_analyzer=self.fundamental_analyzer,
                asset_manager=self.asset_manager,
                rebalance_frequency=self.params.rebalance_frequency,
                max_positions=self.params.max_assets_per_period,
                min_score_threshold=self.params.position_min_score,
                timeframes=self.params.timeframes,
                enable_technical_analysis=self.params.enable_technical_analysis,
                enable_fundamental_analysis=self.params.enable_fundamental_analysis,
                technical_weight=self.params.technical_weight,
                fundamental_weight=self.params.fundamental_weight
            )
        else:
            self.position_manager = PositionManager(
                technical_analyzer=self.technical_analyzer,
                fundamental_analyzer=self.fundamental_analyzer,
                asset_manager=self.asset_manager,
                rebalance_frequency=self.params.rebalance_frequency,
                max_positions=self.params.max_assets_per_period,
                min_score_threshold=self.params.position_min_score,
                timeframes=self.params.timeframes,
                enable_technical_analysis=self.params.enable_technical_analysis,
                enable_fundamental_analysis=self.params.enable_fundamental_analysis,
                technical_weight=self.params.technical_weight,
                fundamental_weight=self.params.fundamental_weight
            )
        
        self.current_regime = None
        self.current_regime_confidence = 0.0
        self.regime_history = []
        
        # Track orders and positions
        self.orders = {}
        self.buy_prices = {}
        self.position_scores = {}  # Track current position scores
        self.asset_bucket_mapping = {}  # Maps assets to their buckets for analytics
        
        # Track PnL for visualization and metrics
        self.unrealized_pnl_history = []  # List of (date, unrealized_pnl) tuples
        self.realized_pnl_history = []    # List of (date, realized_pnl, asset) tuples
        self.total_realized_pnl = 0.0     # Running total of realized PnL
        
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}, {txt}')
    
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        ticker = order.data._name
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED: {ticker}, Price: {order.executed.price:.2f}, '
                        f'Size: {order.executed.size}, Cost: {order.executed.value:.2f}')
                self.buy_prices[ticker] = order.executed.price
            else:
                self.log(f'SELL EXECUTED: {ticker}, Price: {order.executed.price:.2f}, '
                        f'Size: {order.executed.size}, Cost: {order.executed.value:.2f}')
                if ticker in self.buy_prices:
                    del self.buy_prices[ticker]
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order {ticker} Canceled/Margin/Rejected')
        
        # Reset order tracking
        self.orders[ticker] = None
    
    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        
        asset_name = trade.data._name
        realized_pnl = trade.pnlcomm  # Net PnL after commissions
        current_date = self.datas[0].datetime.date(0)
        
        # Track realized PnL
        self.realized_pnl_history.append((current_date, realized_pnl, asset_name))
        self.total_realized_pnl += realized_pnl
        
        self.log(f'TRADE PROFIT: {asset_name}, GROSS: {trade.pnl:.2f}, NET: {realized_pnl:.2f}')
    
    def next(self):
        current_date = self.datas[0].datetime.date(0)
        
        # Check for regime change first (higher priority than time-based rebalancing)
        if self._should_rebalance_regime_change(current_date):
            self._rebalance_portfolio(current_date)
        # Otherwise check if we need to rebalance using position manager
        elif self.position_manager.should_rebalance(current_date):
            self._rebalance_portfolio(current_date)
        
        # Apply risk management to existing positions
        self._apply_risk_management()
        
        # Calculate and track unrealized PnL
        self._track_unrealized_pnl(current_date)
    
    def _should_rebalance_regime_change(self, current_date: datetime) -> bool:
        """Check for regime change separately from position manager rebalancing"""
        new_regime, confidence = self.regime_detector.get_market_regime(current_date)
        if (new_regime != self.current_regime and 
            confidence >= self.params.min_regime_confidence):
            self.log(f'REGIME CHANGE: {self.current_regime} -> {new_regime} (confidence: {confidence:.2f})')
            return True
        
        return False
    
    def _rebalance_portfolio(self, current_date: datetime):
        self.log(f'REBALANCING PORTFOLIO on {current_date}')
        
        # Get current market regime
        regime, confidence = self.regime_detector.get_market_regime(current_date)
        self.current_regime = regime
        self.current_regime_confidence = confidence
        
        self.log(f'Current regime: {regime} (confidence: {confidence:.2f})')
        
        # Try to get buckets directly from research data first
        research_buckets = self.regime_detector.get_research_buckets(current_date)
        
        if research_buckets:
            # Use buckets from research table
            regime_buckets = research_buckets
            self.log(f'Using research buckets: {regime_buckets}')
        else:
            # Fall back to regime-mapped buckets
            regime_buckets = self.regime_detector.get_regime_buckets(regime)
            self.log(f'Using regime-mapped buckets: {regime_buckets}')
        
        # Filter buckets based on strategy parameters
        if self.params.bucket_names:
            regime_buckets = [bucket for bucket in regime_buckets if bucket in self.params.bucket_names]
        
        # Get assets from regime buckets and create bucket mapping
        candidate_assets = self.asset_manager.get_assets_from_buckets(regime_buckets)
        
        # Create asset to bucket mapping for analytics
        self.asset_bucket_mapping = {}
        for bucket in regime_buckets:
            bucket_assets = self.asset_manager.get_bucket_assets(bucket)
            for asset in bucket_assets:
                if asset in candidate_assets:
                    self.asset_bucket_mapping[asset] = bucket
        
        # Filter to assets we have data for
        available_assets = [asset for asset in candidate_assets 
                          if any(data._name == asset for data in self.datas)]
        
        if not available_assets:
            self.log(f'No available assets for regime {regime}')
            return
        
        # Get trending assets from database if available
        trending_assets = self.regime_detector.get_trending_assets(
            current_date, available_assets, len(available_assets),  # Get all for scoring
            min_confidence=self.params.min_trending_confidence
        )
        
        # Use position manager to analyze and score assets
        self.log(f'Analyzing {len(trending_assets)} trending assets with position manager...')
        position_scores = self.position_manager.analyze_and_score_assets(
            trending_assets, current_date, regime, self.data_manager
        )
        
        self.log(f'Generated {len(position_scores)} position scores')
        
        # Check if regime changed
        regime_changed = (self.current_regime is not None and 
                         regime != self.current_regime)
        
        # Calculate position changes (including regime-based closures)
        position_changes = self.position_manager.calculate_position_changes(
            position_scores, 
            current_date,
            regime_changed=regime_changed,
            valid_buckets=regime_buckets
        )
        
        self.log(f'Calculated {len(position_changes)} position changes')
        
        # Execute position changes through backtrader
        self._execute_position_changes(position_changes)
        
        # Update position manager state
        self.position_manager.update_positions(position_scores, current_date)
        
        # Update our internal tracking
        self.position_scores = {score.asset: score for score in position_scores}
        
        # Set regime bucket information for analytics export
        regime_bucket_list = ','.join(regime_buckets) if regime_buckets else 'Unknown'
        setattr(self, f'{regime}_buckets', regime_bucket_list)
        
        # Record regime and position data
        self.regime_history.append({
            'date': current_date,
            'regime': regime,
            'confidence': confidence,
            'position_scores': [score.to_dict() for score in position_scores]
        })
        
        # Log portfolio summary
        summary = self.position_manager.get_position_summary()
        self.log(f'Portfolio: {summary["total_positions"]} positions, '
                f'{summary["total_allocation"]:.1%} allocated, '
                f'avg score: {summary["average_score"]:.3f}')
    
    def _execute_position_changes(self, position_changes):
        """Execute the position changes calculated by position manager"""
        
        for change in position_changes:
            asset = change.asset
            action = change.action
            size_change = change.size_change
            
            self.log(f'POSITION CHANGE: {asset} - {action} - size change: {size_change:.3f} - {change.reason}')
            
            # Set analytics attributes for the analyzer to access
            bucket = self.asset_bucket_mapping.get(asset, 'Unknown')
            setattr(self, f'{asset}_bucket', bucket)
            setattr(self, f'{asset}_reason', change.reason)
            if change.previous_score:
                setattr(self, f'{asset}_score_before', change.previous_score.combined_score)
            else:
                setattr(self, f'{asset}_score_before', 0.0)
            if change.current_score:
                setattr(self, f'{asset}_score_after', change.current_score.combined_score)
            else:
                setattr(self, f'{asset}_score_after', 0.0)
            
            # Find the data feed for this asset
            data_feed = None
            for data in self.datas:
                if data._name == asset:
                    data_feed = data
                    break
            
            if data_feed is None:
                self.log(f'Warning: No data feed found for {asset}')
                continue
            
            position = self.getposition(data_feed)
            
            if action == 'close':
                if position.size > 0:
                    if asset not in self.orders or self.orders[asset] is None:
                        self.log(f'CLOSING POSITION: {asset}')
                        self.orders[asset] = self.sell(data=data_feed, size=position.size)
            
            elif action == 'open':
                if position.size == 0:
                    # Calculate position size based on change.current_score.position_size_percentage
                    target_allocation = change.current_score.position_size_percentage
                    cash_to_allocate = self.broker.getcash() * target_allocation
                    size = int(cash_to_allocate / data_feed.close[0])
                    
                    if size > 0 and (asset not in self.orders or self.orders[asset] is None):
                        self.log(f'OPENING POSITION: {asset}, Size: {size}, Allocation: {target_allocation:.1%}')
                        self.orders[asset] = self.buy(data=data_feed, size=size)
            
            elif action in ['increase', 'decrease']:
                # Calculate new target size
                target_allocation = change.current_score.position_size_percentage
                total_portfolio_value = self.broker.getvalue()
                target_value = total_portfolio_value * target_allocation
                target_size = int(target_value / data_feed.close[0])
                
                size_diff = target_size - position.size
                
                if abs(size_diff) > 0 and (asset not in self.orders or self.orders[asset] is None):
                    if size_diff > 0:
                        self.log(f'INCREASING POSITION: {asset}, Additional size: {size_diff}')
                        self.orders[asset] = self.buy(data=data_feed, size=size_diff)
                    else:
                        self.log(f'DECREASING POSITION: {asset}, Reducing size: {abs(size_diff)}')
                        self.orders[asset] = self.sell(data=data_feed, size=abs(size_diff))
    
    
    def _apply_risk_management(self):
        for data in self.datas:
            ticker = data._name
            position = self.getposition(data)
            
            if position.size > 0 and ticker in self.buy_prices:
                current_price = data.close[0]
                entry_price = self.buy_prices[ticker]
                
                pct_change = (current_price - entry_price) / entry_price
                
                # Stop loss and take profit (only if enabled)
                if self.params.enable_take_profit_stop_loss:
                    # Stop loss
                    if pct_change <= -self.params.stop_loss:
                        if ticker not in self.orders or self.orders[ticker] is None:
                            self.log(f'STOP LOSS: {ticker}, Loss: {pct_change:.2%}')
                            self.orders[ticker] = self.sell(data=data, size=position.size)
                    
                    # Take profit
                    elif pct_change >= self.params.take_profit:
                        if ticker not in self.orders or self.orders[ticker] is None:
                            self.log(f'TAKE PROFIT: {ticker}, Gain: {pct_change:.2%}')
                            self.orders[ticker] = self.sell(data=data, size=position.size)
    
    def _track_unrealized_pnl(self, current_date):
        """Calculate and track unrealized PnL for open positions"""
        total_unrealized_pnl = 0.0
        
        for data in self.datas:
            ticker = data._name
            position = self.getposition(data)
            
            if position.size != 0 and ticker in self.buy_prices:
                current_price = data.close[0]
                entry_price = self.buy_prices[ticker]
                position_value = position.size * current_price
                cost_basis = position.size * entry_price
                unrealized_pnl = position_value - cost_basis
                total_unrealized_pnl += unrealized_pnl
        
        # Store the unrealized PnL for this date
        self.unrealized_pnl_history.append((current_date, total_unrealized_pnl))
    
    def stop(self):
        self.log(f'Final Portfolio Value: {self.broker.getvalue():.2f}')
        self.log(f'Total Regime Changes: {len(self.regime_history)}')
        
        if self.regime_history:
            regimes_used = set(entry['regime'] for entry in self.regime_history)
            self.log(f'Regimes Used: {list(regimes_used)}')
        
        
        # Position history export is now handled by save_results() function
        # to ensure it goes to the correct run folder with proper naming