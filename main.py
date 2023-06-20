import backtrader as bt
import yfinance as yf

START_DATE = '2023-06-15'
END_DATE = '2023-06-16'
STOCK_TICKER = 'AAPL'


class VWAP(bt.Indicator):
    lines = ('vwap',)
    params = (('period', 20),)

    def __init__(self):
        self.addminperiod(self.params.period)

    def next(self):
        cum_sum = sum(self.data.close[i] * self.data.volume[i] for i in range(-self.params.period, 0))
        cum_vol = sum(self.data.volume[i] for i in range(-self.params.period, 0))
        self.lines.vwap[0] = cum_sum / cum_vol


class MomentumStrategy(bt.Strategy):
    params = (
        ("macd1", 12),
        ("macd2", 26),
        ("macdsig", 9),
        ("rsi_period", 14),
        ("rsi_overbought", 70),
        ("rsi_oversold", 30),
        ("bb_period", 20),
        ("bb_stddev", 2),
    )

    def __init__(self):
        # Indicators
        self.macd = bt.indicators.MACD(self.data.close,
                                       period_me1=self.params.macd1,
                                       period_me2=self.params.macd2,
                                       period_signal=self.params.macdsig,
                                       plot=False)
        self.rsi = bt.indicators.RelativeStrengthIndex(period=self.params.rsi_period)
        self.bollinger = bt.indicators.BollingerBands(self.data.close,
                                                      period=self.params.bb_period,
                                                      devfactor=self.params.bb_stddev,
                                                      plot=False)
        self.vwap = VWAP(self.data, plot=False)
        self.trades = 0
        self.winning_trades = 0
        self.losing_trades = 0

    def next(self):
        # Log the prices for this bar
        self.log(
            f'Open: {self.data.open[0]}, High: {self.data.high[0]}, Low: {self.data.low[0]}, Close: {self.data.close[0]}')
        # Compute the differences
        macd_diff = self.macd.macd[0] - self.macd.signal[0]
        rsi_diff = self.params.rsi_oversold - self.rsi[0]

        # Log the differences
        self.log('MACD difference: %.2f, RSI difference: %.2f' % (macd_diff, rsi_diff))

        if not self.position:
            if (self.macd.macd > self.macd.signal) and \
                    (self.rsi < self.params.rsi_oversold):
                # and \
                    # (self.data.close < self.bollinger.lines.bot) and \
                    # (self.data.close < self.vwap):
                self.buy()
        else:
            if (self.macd.macd < self.macd.signal) or \
                    (self.rsi > self.params.rsi_overbought):
                # or \
                    # (self.data.close > self.bollinger.lines.top) or \
                    # (self.data.close > self.vwap):
                self.sell()

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price, order.executed.value, order.executed.comm))
                self.trades += 1
            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price, order.executed.value, order.executed.comm))
                self.trades += 1

                # calculate the profit for the trade
                profit = self.broker.getvalue() - self.start_cash
                if profit > 0:
                    self.winning_trades += 1
                else:
                    self.losing_trades += 1

    def log(self, text):
        """ Logging function for the strategy"""
        dt = self.data.datetime.datetime()
        print(f'{dt}, {text}')

    def stop(self):
        self.log('Number of trades: %d' % self.trades)
        self.log('Number of winning trades: %d' % self.winning_trades)
        self.log('Number of losing trades: %d' % self.losing_trades)


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
    cerebro.broker.set_cash(10000.0)

    # Set broker commission
    cerebro.broker.setcommission(commission=0.001)

    # Print starting portfolio value
    print(f'Starting Portfolio Value: {cerebro.broker.getvalue()}')

    # Run the strategy
    cerebro.run()

    # Print final portfolio value
    print(f'Final Portfolio Value: {cerebro.broker.getvalue()}')
    cerebro.plot(style='candle', barup='green', bardown='red', fmt_x_data='%Y-%m-%d %H:%M:%S', volume=False)


