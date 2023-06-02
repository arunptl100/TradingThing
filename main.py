import backtrader as bt
import yfinance as yf


START_DATE = '2021-01-01'
END_DATE = '2022-12-31'
STOCK_TICKER = 'AAPL'

class MyStrategy(bt.Strategy):
    def __init__(self):
        self.sma_fast = bt.indicators.SimpleMovingAverage(self.data.close, period=14)
        self.sma_slow = bt.indicators.SimpleMovingAverage(self.data.close, period=50)
        self.rsi = bt.indicators.RSI_SMA(self.data.close, period=14)
        self.dataclose = self.datas[0].close

        # To keep track of pending orders
        self.order = None

    def log(self, txt, dt=None):
        """ Logging function for this strategy"""
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))
            elif order.issell():
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Write down: no pending order
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        # Check if we are in the market
        if not self.position:
            # We are not in the market, if RSI < 30 then buy
            if self.rsi[0] < 30:
                self.log('BUY CREATE, %.2f' % self.data.close[0])
                self.order = self.buy()

        else:
            # We are in the market, if RSI > 70 then sell
            if self.rsi[0] > 70:
                self.log('SELL CREATE, %.2f' % self.data.close[0])
                self.order = self.sell()

        self.log('Close, %.2f' % self.data.close[0])


# Download data
data = yf.download(STOCK_TICKER, START_DATE, END_DATE)

# Create a data feed
data_feed = bt.feeds.PandasData(dataname=data)

# Create a Cerebro entity
cerebro = bt.Cerebro()

# Add a strategy
cerebro.addstrategy(MyStrategy)

# Add the data to Cerebro
cerebro.adddata(data_feed)

# Set our desired cash start
cerebro.broker.setcash(100000.0)

cerebro.broker.setcommission(commission=0.001)

# Add analyzers
cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='tradeanalyzer')
cerebro.addanalyzer(bt.analyzers.Transactions, _name='transactions')
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')

# Print out the starting conditions
print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

# Run over everything
results = cerebro.run()

# Print out the final result
print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

# Print analysis
trade_analysis = results[0].analyzers.tradeanalyzer.get_analysis()
transaction_analysis = results[0].analyzers.transactions.get_analysis()
sharpe_ratio = results[0].analyzers.sharpe.get_analysis()

total_trades = trade_analysis.total.closed
profitable_trades = trade_analysis.won.total
unprofitable_trades = trade_analysis.lost.total
total_net_profit = trade_analysis.pnl.net.total

average_profit_per_trade = (trade_analysis.pnl.net.total / total_trades) if total_trades != 0 else 0
average_trade_length = (trade_analysis.len.total / total_trades) if total_trades != 0 else 0

print('Total Trades:', total_trades)
print('Profitable Trades:', profitable_trades)
print('Unprofitable Trades:', unprofitable_trades)
print('Average Profit per Trade: $' + format(average_profit_per_trade, '.2f'))
print('Average Trade Length: ' + format(average_trade_length, '.2f') + ' periods')
print('Total Net Profit: $' + format(total_net_profit, '.2f'))

