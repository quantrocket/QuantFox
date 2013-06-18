import matplotlib.pyplot as plt
import numpy as np
import statsmodels.api as sm
from datetime import datetime
import pytz


from zipline.algorithm import TradingAlgorithm
from zipline.transforms import batch_transform
from zipline.utils.date_utils import days_since_epoch
from zipline.utils.factory import load_from_yahoo
from zipline.finance import performance

sym_list = {'SEE':'XLB'}#,'BEAM':'XLP'}
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
        #self.ratios = {sym:np.array([]) for sym in sym_list}
        self.ratios = {sym:np.array([]) for sym in sym_list}
        self.invested = {sym:[0,0] for sym in sym_list}            # invested[sym,etf]
        self.returns = {sym:[0,0,0] for sym in sym_list}         # returns[sym][enterSpread,currentSpread,tradeReturn]
        self.cumReturns = {sym:[] for sym in sym_list}
        self.zscores = {sym:np.array([0]*(window_length-1)) for sym in sym_list}
        self.dates = []
        self.window_length = window_length
        self.day_count = 0
        self.ols_transform = ols_transform(refresh_period=self.window_length,
                                           window_length=self.window_length)
        
    def trade_return(self, sym, ratio):
        if self.day_count == 1:
            tradeReturn = 0
        else:
            lastRatio = self.ratios[sym][-1]
            if self.invested[sym][0] > 0:
                tradeReturn = (ratio - lastRatio)/lastRatio
            elif self.invested[sym][0] < 0:
                tradeReturn = (lastRatio - ratio)/lastRatio
            else:
                tradeReturn = 0
        return tradeReturn

    def handle_data(self, data):
        print self.day_count
        self.day_count += 1
        self.dates = np.append(self.dates, TradingAlgorithm.get_datetime(self))
        
        for sym in sym_list:
            etf = sym_list[sym]
            ratio = data[sym].price / data[etf].price
            tradeReturn = self.trade_return(sym, ratio)
            self.ratios[sym] = np.append(self.ratios[sym], ratio)
            if self.day_count == 1:
                self.cumReturns[sym].append(0)
            else:
                self.cumReturns[sym].append(self.cumReturns[sym][-1] + tradeReturn)
        for sym in sym_list:
            ################################################################
            # 1. Compute regression coefficients between the two instruments
            params = self.ols_transform.handle_data(data, sym, etf)
            if params is None:
                return
            intercept, slope = params
            ################################################################
            # 2. Compute spread and z-score
            zscore = self.compute_zscore(data, sym, etf, slope, intercept)
            #self.record(zscores[sym]=zscore)
            ################################################################
            # 3. Place orders
            self.place_orders(data, sym, etf, zscore, ratio)

    def compute_zscore(self, data, sym, etf, slope, intercept):
        ####################################################################
        # 1. Compute the spread given slope and intercept.
        # 2. z-score the spread.
        spread = (data[sym].price - (slope * data[etf].price + intercept))
        self.spreads[sym].append(spread)
        spread_wind = self.spreads[sym][-self.window_length:]
        zscore = (spread - np.mean(spread_wind)) / np.std(spread_wind)
        self.zscores[sym] = np.append(self.zscores[sym], zscore)
        return zscore

    def place_orders(self, data, sym, etf, zscore, ratio):
        ####################################################################
        # Buy spread if z-score is > 2, sell if z-score < .5.
        if zscore >= 2.0 and self.invested[sym][0] == 0:
            sym_quantity = -int(100 / data[sym].price)
            etf_quantity = int(100 / data[etf].price)
            self.order(sym, sym_quantity)
            self.order(etf, etf_quantity)
            self.invested[sym] = [sym_quantity, etf_quantity]
            self.returns[sym][0] = ratio
        elif zscore <= -2.0 and self.invested[sym][0] == 0:
            sym_quantity = int(100 / data[sym].price)
            etf_quantity = -int(100 / data[etf].price)
            self.order(sym, sym_quantity)
            self.order(etf, etf_quantity)
            self.invested[sym] = [sym_quantity, etf_quantity]
            self.returns[sym][0] = ratio
        elif abs(zscore) < .5 and self.invested[sym][0] != 0:
            self.sell_spread(sym, etf)
            self.invested[sym] = [0,0]

    def sell_spread(self, sym, etf):
        #####################################################################
        # decrease exposure, regardless of position long/short.
        # buy for a short position, sell for a long.
        etf_amount = self.invested[sym][1]
        self.order(etf, -1 * etf_amount)
        sym_amount = self.portfolio.positions[sym].amount
        self.order(sym, -1 * sym_amount)

if __name__ == '__main__':
    start = datetime(2012, 1, 1, 0, 0, 0, 0, pytz.utc)
    end = datetime(2012, 12, 31, 0, 0, 0, 0, pytz.utc)
    feed = build_feed()
    data = load_from_yahoo(stocks=feed, indexes={},
                           start=start, end=end, adjusted=True)
    
    pairtrade = Pairtrade()
    results = pairtrade.run(data)
    print results.portfolio_value[-1]
    data['spreads'] = np.nan

    for sym in sym_list:
        etf = sym_list[sym]

        ax1 = plt.subplot(411, ylabel=(str(sym)+":"+str(etf))+' Adjusted Close')
        plt.plot(pairtrade.dates, pairtrade.ratios[sym])
        plt.setp(ax1.get_xticklabels(), visible=True)
        plt.xticks(rotation=45)
        plt.grid(b=True, which='major', color='k')
    
        ax2 = plt.subplot(412, ylabel='z-scored spread')
        plt.plot(pairtrade.dates, pairtrade.zscores[sym], color='r')
        plt.setp(ax2.get_xticklabels(), visible=True)
        plt.xticks(rotation=45)
        plt.grid(b=True, which='major', color='k')
        
        ax3 = plt.subplot(413, ylabel=(str(sym)+":"+str(etf))+' Return')
        plt.plot(pairtrade.dates, pairtrade.cumReturns[sym])
        plt.setp(ax3.get_xticklabels(), visible=True)
        plt.xticks(rotation=45)
        plt.grid(b=True, which='major', color='k')
        
        ax4 = plt.subplot(414, ylabel='portfolio value')
        results.portfolio_value.plot(ax=ax4)
        plt.setp(ax4.get_xticklabels(), visible=True)
        
        """
        results.portfolio_value.plot(ax=ax3)
        plt.setp(ax3.get_xticklabels(), visible=True)
        """
        plt.gcf().set_size_inches(30, 20)
        plt.savefig(str(sym)+":"+str(etf), format='pdf')
        #plt.show()
        plt.clf()