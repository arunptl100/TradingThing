import backtrader as bt
import yfinance as yf

START_DATE = '2023-06-15'
END_DATE = '2023-06-16'
STOCK_TICKER = 'AAPL'


class VWAP(bt.Indicator):
    lines = ('vwap',)
    params = (('period', 5),)

    def __init__(self):
        self.addminperiod(self.params.period)

    def next(self):
        cum_sum = sum(self.data.close[i] * self.data.volume[i] for i in range(-self.params.period, 0))
        cum_vol = sum(self.data.volume[i] for i in range(-self.params.period, 0))
        self.lines.vwap[0] = cum_sum / cum_vol


class MomentumStrategy(bt.Strategy):
    params = (
        ("macd1", 8),
        ("macd2", 17),
        ("macdsig", 9),
        ("rsi_period", 9),
        ("rsi_overbought", 70),
        ("rsi_oversold", 30),
        ("bb_period", 20),
        ("bb_stddev", 2),
    )

    def __init__(self):
        self.rsi = bt.indicators.RelativeStrengthIndex(period=self.params.rsi_period)
        self.vwap = VWAP(self.data, plot=True)
        # To keep track of pending orders
        self.order = None

    def next(self):
        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        # Log the prices for this bar
        self.log(
            f'Open: {self.data.open[0]}, High: {self.data.high[0]}, Low: {self.data.low[0]}, Close: {self.data.close[0]}')

        if not self.position:
            if (self.rsi[0] < self.params.rsi_oversold) and \
                    (self.data.close[0] < self.vwap):
                self.log('BUY CREATE, %.2f' % self.data.close[0])
                self.log(f'Buy condition met: RSI {self.rsi[0]} < {self.params.rsi_oversold}')
                self.log(f'Buy condition met: Close price {self.data.close[0]} < VWAP {self.vwap[0]}')
                self.order = self.buy()
        else:
            if (self.rsi[0] > self.params.rsi_overbought) and \
                    (self.data.close[0] > self.vwap):
                self.log('SELL CREATE, %.2f' % self.data.close[0])
                self.log(f'Sell condition met: RSI {self.rsi[0]} > {self.params.rsi_overbought}')
                self.log(f'Sell condition met: Close price {self.data.close[0]} > VWAP {self.vwap[0]}')
                self.order = self.sell()

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

    def log(self, text):
        """ Logging function for the strategy"""
        dt = self.data.datetime.datetime()
        print(f'{dt}, {text}')


if __name__ == "__main__":
    # Download data
    data = yf.download(STOCK_TICKER, START_DATE, END_DATE, interval='1m')

    # Create a data feed
    data_feed = bt.feeds.PandasData(dataname=data)

    # Create a Cerebro entity
    cerebro = bt.Cerebro()

    # Add strategy
    cerebro.addstrategy(MomentumStrategy)

    # Add the data to Cerebro
    cerebro.adddata(data_feed)

    # Set initial cash
    # Set our desired cash start
    cerebro.broker.setcash(1000.0)

    # Set broker commission
    cerebro.broker.setcommission(commission=0.001)

    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='tradeanalyzer')

    # Print starting portfolio value
    print(f'Starting Portfolio Value: {cerebro.broker.getvalue()}')

    # Run the strategy
    results = cerebro.run()

    # Print final portfolio value
    print(f'Final Portfolio Value: {cerebro.broker.getvalue()}')

    trade_analysis = results[0].analyzers.tradeanalyzer.get_analysis()
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
    cerebro.plot(style='candle', barup='green', bardown='red', fmt_x_data='%Y-%m-%d %H:%M:%S', volume=False)
