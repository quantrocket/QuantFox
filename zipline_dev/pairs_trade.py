
import matplotlib.pyplot as plt
import numpy as np
import statsmodels.api as sm
from datetime import datetime
import pytz

from zipline.algorithm import TradingAlgorithm
from zipline.transforms import batch_transform
from zipline.utils.factory import load_from_yahoo

sym_list = {'SEE':'XLB','BEAM':'XLP'}
etf_list = {'XLB','XLP'}

def build_feed():
    feed = []
    for sym in sym_list:
        feed.append(sym)
    for etf in etf_list:
        feed.append(etf)
    return feed 
    
@batch_transform
def ols_transform(data, sid1, sid2):
    """
    Computes regression coefficient (slope and intercept)
    via Ordinary Least Squares between two instruments.
    """
    p0 = data.price[sid1]
    p1 = sm.add_constant(data.price[sid2], prepend=True)
    slope, intercept = sm.OLS(p0, p1).fit().params
    return slope, intercept

class Pairtrade(TradingAlgorithm):
    
    def initialize(self, window_length=100):
        self.spreads = {sym:[] for sym in sym_list}
        self.invested = {sym:[0,0] for sym in sym_list}
        self.window_length = window_length
        self.ols_transform = ols_transform(refresh_period=self.window_length,
                                           window_length=self.window_length)

    def handle_data(self, data):
        for sym in sym_list:
            etf = sym_list[sym]
            ################################################################
            # 1. Compute regression coefficients between the two instruments
            params = self.ols_transform.handle_data(data, sym, etf)
            if params is None:
                return
            intercept, slope = params
            ################################################################
            # 2. Compute spread and z-score
            zscore = self.compute_zscore(data, sym, etf, slope, intercept)
            self.record(zscores=zscore)
            ################################################################
            # 3. Place orders
            self.place_orders(data, sym, etf, zscore)

    def compute_zscore(self, data, sym, etf, slope, intercept):
        ####################################################################
        # 1. Compute the spread given slope and intercept.
        # 2. z-score the spread.
        spread = (data[sym].price - (slope * data[etf].price + intercept))
        self.spreads[sym].append(spread)
        spread_wind = self.spreads[sym][-self.window_length:]
        zscore = (spread - np.mean(spread_wind)) / np.std(spread_wind)
        return zscore

    def place_orders(self, data, sym, etf, zscore):
        ####################################################################
        # Buy spread if z-score is > 2, sell if z-score < .5.
        if zscore >= 2.0 and self.invested[sym][0] == 0:
            sym_quantity = int(100 / data[sym].price)
            etf_quantity = int(100 / data[etf].price)
            self.order(sym, sym_quantity)
            self.order(etf, -etf_quantity)
            self.invested[sym] = [sym_quantity,-etf_quantity]
        elif zscore <= -2.0 and self.invested[sym][0] == 0:
            sym_quantity = int(100 / data[sym].price)
            etf_quantity = int(100 / data[etf].price)
            self.order(etf, etf_quantity)
            self.order(sym, sym_quantity)
            self.invested[sym] = [-sym_quantity,etf_quantity]
        elif abs(zscore) < .5 and self.invested[sym][0] != 0:
            self.sell_spread(sym, etf)
            self.invested[sym] = [0,0]

    def sell_spread(self, sym, etf):
        #####################################################################
        # decrease exposure, regardless of position long/short.
        # buy for a short position, sell for a long.
        etf_amount = self.invested[sym][0]
        self.order(etf, -1 * etf_amount)
        sym_amount = self.portfolio.positions[sym].amount
        self.order(sym, -1 * sym_amount)

if __name__ == '__main__':
    start = datetime(2010, 1, 1, 0, 0, 0, 0, pytz.utc)
    end = datetime(2012, 12, 31, 0, 0, 0, 0, pytz.utc)
    feed = build_feed()
    data = load_from_yahoo(stocks=feed, indexes={},
                           start=start, end=end)
    
    pairtrade = Pairtrade()
    results = pairtrade.run(data)
    print results.portfolio_value[-1]
    data['spreads'] = np.nan

    for sym in sym_list:
        etf = sym_list[sym]
        ax1 = plt.subplot(211)
        data[[sym, etf]].plot(ax=ax1)
        plt.ylabel('Price')
        plt.setp(ax1.get_xticklabels(), visible=False)
    
        ax2 = plt.subplot(212, sharex=ax1)
        results.zscores.plot(ax=ax2, color='r')
        plt.ylabel('z-scored spread')
    
        plt.gcf().set_size_inches(18, 8)
        plt.savefig(str(sym)+":"+str(etf), format='pdf')