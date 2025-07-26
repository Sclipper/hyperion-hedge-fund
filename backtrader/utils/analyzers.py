import backtrader as bt


def setup_analyzers(cerebro):
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Days, annualize=True)
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
    cerebro.addanalyzer(bt.analyzers.VWR, _name='vwr')
    cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='timereturn')
    cerebro.addanalyzer(bt.analyzers.PositionsValue, _name='positions')


def print_analysis(strategy):
    print('\n--- PERFORMANCE ANALYSIS ---')
    
    sharpe = strategy.analyzers.sharpe.get_analysis()
    returns = strategy.analyzers.returns.get_analysis()
    drawdown = strategy.analyzers.drawdown.get_analysis()
    trades = strategy.analyzers.trades.get_analysis()
    sqn = strategy.analyzers.sqn.get_analysis()
    vwr = strategy.analyzers.vwr.get_analysis()
    
    print(f'Sharpe Ratio: {sharpe.get("sharperatio", 0):.3f}')
    
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