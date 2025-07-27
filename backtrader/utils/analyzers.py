import backtrader as bt
from datetime import datetime
from collections import defaultdict


class CustomPortfolioTracker(bt.Analyzer):
    """Track daily portfolio value, composition, and metrics for enhanced visualization and export"""
    
    def create_analysis(self):
        self.rets = {}
        self.portfolio_timeline = []
        
    def start(self):
        # We'll set start_date in the first next() call when data is available
        self.start_date = None
        
    def next(self):
        current_date = self.strategy.datetime.date()
        
        # Set start_date on first call
        if self.start_date is None:
            self.start_date = current_date
            
        portfolio_value = self.strategy.broker.getvalue()
        cash = self.strategy.broker.getcash()
        
        # Count current positions
        total_positions = 0
        position_details = {}
        
        for data in self.strategy.datas:
            position = self.strategy.getposition(data)
            if position.size != 0:
                total_positions += 1
                position_details[data._name] = {
                    'size': position.size,
                    'price': position.price,
                    'value': position.size * data.close[0]
                }
        
        # Try to get regime information if available (from strategy)
        regime = getattr(self.strategy, 'current_regime', 'Unknown')
        regime_confidence = getattr(self.strategy, 'regime_confidence', 0.0)
        
        daily_data = {
            'date': current_date,
            'portfolio_value': portfolio_value,
            'cash': cash,
            'total_positions': total_positions,
            'regime': regime,
            'regime_confidence': regime_confidence,
            'position_details': position_details.copy()
        }
        
        self.portfolio_timeline.append(daily_data)
        
    def get_analysis(self):
        return {
            'portfolio_timeline': self.portfolio_timeline,
            'start_date': self.start_date if hasattr(self, 'start_date') else None
        }


class CustomPositionTracker(bt.Analyzer):
    """Track all position changes with detailed context for trading decisions export"""
    
    def create_analysis(self):
        self.position_changes = []
        self.previous_positions = {}
        
    def start(self):
        # Initialize previous positions tracking
        for data in self.strategy.datas:
            self.previous_positions[data._name] = 0
            
    def next(self):
        current_date = self.strategy.datetime.date()
        
        # Check each asset for position changes
        for data in self.strategy.datas:
            asset_name = data._name
            current_position = self.strategy.getposition(data)
            current_size = current_position.size
            previous_size = self.previous_positions.get(asset_name, 0)
            
            # Determine action type
            action = 'HOLD'
            if current_size > previous_size:
                action = 'BUY'
            elif current_size < previous_size:
                action = 'SELL'
            elif current_size == 0 and previous_size == 0:
                continue  # Skip if no position and no change
                
            # Get additional context from strategy if available
            regime = getattr(self.strategy, 'current_regime', 'Unknown')
            score_before = getattr(self.strategy, f'{asset_name}_score_before', 0.0)
            score_after = getattr(self.strategy, f'{asset_name}_score_after', 0.0)
            bucket = getattr(self.strategy, f'{asset_name}_bucket', 'Unknown')
            reason = getattr(self.strategy, f'{asset_name}_reason', 'Position update')
            
            # Calculate quantity and value
            quantity_change = abs(current_size - previous_size)
            price = data.close[0]
            value = quantity_change * price
            
            position_data = {
                'date': current_date,
                'asset': asset_name,
                'action': action,
                'quantity': quantity_change if action != 'HOLD' else abs(current_size),
                'price': price,
                'value': value if action != 'HOLD' else abs(current_size) * price,
                'reason': reason,
                'score_before': score_before,
                'score_after': score_after,
                'bucket': bucket,
                'regime': regime
            }
            
            self.position_changes.append(position_data)
            self.previous_positions[asset_name] = current_size
            
    def get_analysis(self):
        return {
            'position_changes': self.position_changes
        }


def setup_analyzers(cerebro):
    # Existing built-in analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Days, annualize=True)
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
    cerebro.addanalyzer(bt.analyzers.VWR, _name='vwr')
    cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='timereturn')
    cerebro.addanalyzer(bt.analyzers.PositionsValue, _name='positions')
    
    # New custom analyzers for enhanced data collection
    cerebro.addanalyzer(CustomPortfolioTracker, _name='portfolio_tracker')
    cerebro.addanalyzer(CustomPositionTracker, _name='position_tracker')


def print_analysis(strategy):
    print('\n--- PERFORMANCE ANALYSIS ---')
    
    sharpe = strategy.analyzers.sharpe.get_analysis()
    returns = strategy.analyzers.returns.get_analysis()
    drawdown = strategy.analyzers.drawdown.get_analysis()
    trades = strategy.analyzers.trades.get_analysis()
    sqn = strategy.analyzers.sqn.get_analysis()
    vwr = strategy.analyzers.vwr.get_analysis()
    
    sharpe_ratio = sharpe.get("sharperatio", 0) if sharpe else 0
    print(f'Sharpe Ratio: {sharpe_ratio:.3f}' if sharpe_ratio is not None else 'Sharpe Ratio: N/A')
    
    print(f'Total Return: {returns.get("rtot", 0) * 100:.2f}%')
    print(f'Average Return: {returns.get("ravg", 0) * 100:.3f}%')
    
    print(f'Max Drawdown: {drawdown.get("max", {}).get("drawdown", 0):.2f}%')
    print(f'Max Drawdown Duration: {drawdown.get("max", {}).get("len", 0)} days')
    
    if 'total' in trades:
        total_trades = trades['total']['total']
        won_trades = trades['won']['total'] if 'won' in trades else 0
        lost_trades = trades['lost']['total'] if 'lost' in trades else 0
        
        print(f'Total Trades: {total_trades}')
        print(f'Won Trades: {won_trades} ({won_trades/total_trades*100:.1f}%)' if total_trades > 0 else 'Won Trades: 0')
        print(f'Lost Trades: {lost_trades} ({lost_trades/total_trades*100:.1f}%)' if total_trades > 0 else 'Lost Trades: 0')
        
        if 'won' in trades and 'pnl' in trades['won']:
            avg_win = trades['won']['pnl']['average']
            print(f'Average Win: ${avg_win:.2f}')
        
        if 'lost' in trades and 'pnl' in trades['lost']:
            avg_loss = trades['lost']['pnl']['average']
            print(f'Average Loss: ${avg_loss:.2f}')
    
    print(f'SQN (System Quality Number): {sqn.get("sqn", 0):.3f}')
    print(f'VWR (Variability-Weighted Return): {vwr.get("vwr", 0):.3f}')
    
    print('--- END ANALYSIS ---\n')