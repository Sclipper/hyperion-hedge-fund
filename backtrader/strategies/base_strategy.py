import backtrader as bt


class BaseStrategy(bt.Strategy):
    params = (
        ('sma_period', 20),
        ('rsi_period', 14),
        ('rsi_lower', 30),
        ('rsi_upper', 70),
        ('stop_loss', 0.05),
        ('take_profit', 0.15),
    )
    
    def __init__(self):
        self.sma = {}
        self.rsi = {}
        self.order = None
        self.buy_price = None
        self.buy_comm = None
        
        for data in self.datas:
            self.sma[data._name] = bt.indicators.SimpleMovingAverage(
                data.close, period=self.params.sma_period
            )
            self.rsi[data._name] = bt.indicators.RSI(
                data.close, period=self.params.rsi_period
            )
    
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}, {txt}')
    
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED: {order.data._name}, Price: {order.executed.price:.2f}, '
                        f'Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
                self.buy_price = order.executed.price
                self.buy_comm = order.executed.comm
            else:
                self.log(f'SELL EXECUTED: {order.data._name}, Price: {order.executed.price:.2f}, '
                        f'Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order {order.data._name} Canceled/Margin/Rejected')
        
        self.order = None
    
    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        
        self.log(f'OPERATION PROFIT: {trade.data._name}, GROSS: {trade.pnl:.2f}, NET: {trade.pnlcomm:.2f}')
    
    def next(self):
        if self.order:
            return
        
        for data in self.datas:
            ticker = data._name
            position = self.getposition(data)
            
            if not position:
                if (data.close[0] > self.sma[ticker][0] and 
                    self.rsi[ticker][0] < self.params.rsi_upper):
                    
                    size = int(self.broker.getcash() / len(self.datas) / data.close[0])
                    if size > 0:
                        self.log(f'BUY CREATE: {ticker}, Price: {data.close[0]:.2f}, Size: {size}')
                        self.order = self.buy(data=data, size=size)
            
            else:
                current_price = data.close[0]
                entry_price = position.price
                
                stop_loss_price = entry_price * (1 - self.params.stop_loss)
                take_profit_price = entry_price * (1 + self.params.take_profit)
                
                if (current_price <= stop_loss_price or 
                    current_price >= take_profit_price or
                    (data.close[0] < self.sma[ticker][0] and 
                     self.rsi[ticker][0] > self.params.rsi_lower)):
                    
                    self.log(f'SELL CREATE: {ticker}, Price: {current_price:.2f}')
                    self.order = self.sell(data=data, size=position.size)