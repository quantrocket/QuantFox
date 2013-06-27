import matplotlib.pyplot as plt
import numpy as np
import statsmodels.api as sm
from datetime import datetime
import pytz
import operator
import pandas as pd
import talib
import vratio
import csv
from scipy import stats

from zipline.algorithm import TradingAlgorithm
from zipline.transforms import batch_transform
from zipline.utils.factory import create_returns_from_list, load_from_yahoo
from zipline.finance import performance, slippage, risk, trading
from zipline.finance.risk import RiskMetricsBase
from zipline.finance.performance import PerformanceTracker, PerformancePeriod

symReader = csv.reader(open('sp500.csv', "rb"), delimiter = ",")
sym_list = [symbol for line in symReader for symbol in line]
window = 5
feed = sym_list


class sector_rs(TradingAlgorithm):  # inherit from TradingAlgorithm
    def initialize(self):
        self.set_slippage(slippage.FixedSlippage())
        self.dates = []
        self.prices = {sym:np.array([]) for sym in feed}
        self.vratio_plot = {sym:np.array([]) for sym in feed}
        self.buy_plot = {sym:[] for sym in feed}
        self.sell_plot = {sym:[] for sym in feed}
        self.day_count = 0
        
    def get_rsi(self,sym):
        #print sym
        rsi = talib.RSI(self.prices[sym],window)
        return rsi
    
    def get_rs(self,sym):
        rs = self.prices[sym][-5] - self.prices[sym][1]
        return rs
        
    def get_vratio(self,sym):
        v = vratio.vratio(self.prices[sym], cor = 'het')
        self.vratio_plot[sym] = np.append(self.vratio_plot[sym],v[2])
        if v[2] < 0.05:
            trending = True
        else:
            trending = False
        return trending
        
    def get_ttest(self,sym):
        array = stats.ttest_1samp(self.prices[sym][-30:], np.mean(self.prices[sym][-30]))
        t = abs(array[0])
        p = array[1]
        if t > 2 and p < 0.05:
            return True
        else:
            return False    

    def short(self,data,sym):
        price = data[sym].price
        q = 10000/price
        self.order(sym,-q)
        
    def long(self,data,sym):
        price = data[sym].price
        q = 10000/price
        self.order(sym,q)
    
    def handle_data(self, data):  # overload handle_data() method
        day = TradingAlgorithm.get_datetime(self)
        self.dates.append(day)
        #print self.day_count
        #print self.portfolio
        # Get price data
        for sym in sym_list:
            sym_price = data[sym].price
            self.prices[sym] = np.append(self.prices[sym],sym_price)
        # Execute trades
        for sym in sym_list:
            if self.day_count >=  30:
                rsi = self.get_rsi(sym)[-1]
                trending = self.get_vratio(sym)
                t = self.get_ttest(sym)
                rs = self.get_rs(sym)
                #
                if self.portfolio.positions[sym].amount == 0:
                    if trending == True and t == True and rs > 0 and rsi < 70:
                        print day,' Long ',sym
                        self.long(data,sym)
                        self.buy_plot[sym].append(self.day_count)
                    elif trending == True and t == True and rs < 0 and rsi > 30:
                        print day,' Short ',sym
                        self.short(data,sym)
                        self.sell_plot[sym].append(self.day_count)
                    else:
                        pass
                elif self.portfolio.positions[sym].amount > 0 and rsi >70:
                    print day,' Exit Long ',sym
                    q = self.portfolio.positions[sym].amount
                    self.order(sym,-q)
                    self.sell_plot[sym].append(self.day_count)
                elif self.portfolio.positions[sym].amount < 0 and rsi < 30:
                    print day,' Exit Short ',sym
                    q = self.portfolio.positions[sym].amount
                    self.order(sym,-q)
                    self.buy_plot[sym].append(self.day_count)
            else:
                self.vratio_plot[sym] = np.append(self.vratio_plot[sym],0)
        self.day_count += 1

if __name__ == '__main__':
    start = datetime(2010, 1, 1, 0, 0, 0, 0, pytz.utc)
    end = datetime(2013, 01, 01, 0, 0, 0, 0, pytz.utc)
    data = load_from_yahoo(stocks=feed, indexes={}, start=start, end=end)
    sector_rs = sector_rs()
    results = sector_rs.run(data)

    ###########################################################################
    # Generate metrics
    print 'Generating Risk Report...........'
    print 'Using S&P500 as benchmark........'

    start = results.first_valid_index().replace(tzinfo=pytz.utc)
    end = results.last_valid_index().replace(tzinfo=pytz.utc)
    env = trading.SimulationParameters(start, end)
    returns_risk = create_returns_from_list(results.returns, env)
    
    algo_returns = RiskMetricsBase(start, end, returns_risk).algorithm_period_returns
    benchmark_returns = RiskMetricsBase(start, end, returns_risk).benchmark_period_returns
    excess_return = RiskMetricsBase(start, end, returns_risk).excess_return
    algo_volatility = RiskMetricsBase(start, end, returns_risk).algorithm_volatility
    benchmark_volatility = RiskMetricsBase(start, end, returns_risk).benchmark_volatility
    sharpe = RiskMetricsBase(start, end, returns_risk).sharpe
    sortino = RiskMetricsBase(start, end, returns_risk).sortino
    information = RiskMetricsBase(start, end, returns_risk).information
    beta = RiskMetricsBase(start, end, returns_risk).beta
    alpha = RiskMetricsBase(start, end, returns_risk).alpha
    max_drawdown = RiskMetricsBase(start, end, returns_risk).max_drawdown
    load
    print '---------Risk Metrics---------'
    print 'Algorithm Returns: ' + str(round(algo_returns * 100,4)) + '%'
    print 'Benchmark Returns: ' + str(round(benchmark_returns * 100,4)) + '%'
    print 'Excess Return: ' + str(excess_return * 100) + '%'
    print '------------------------------'
    print 'Algorithm Volatility: ' + str(round(algo_volatility,4))
    print 'Benchmark Volatility: ' + str(round(benchmark_volatility,4))
    print '------------------------------'
    print 'Sharpe Ratio: ' + str(round(sharpe,4))
    print 'Sortino Ratio: ' + str(round(sortino,4))
    print 'Information Ratio: ' + str(round(information,4))
    print '------------------------------'
    print 'Beta: ' + str(round(beta,4))
    print 'Alpha: ' + str(round(alpha,4))
    print 'Max Drawdown: ' + str(round(max_drawdown*100,4)) + '%'
    print '------------------------------'
    sym = 'AAPL'
    print len(sector_rs.dates)
    print len(sector_rs.vratio_plot[sym])
    
    sym = 'ADM'
    ax1 = plt.subplot(311)
    data.ADM.plot(ax=ax1)
    #ax1.plot(sector_rs.buy_plot[sym], sector_rs.prices[sym],'^', markersize=10, color='g' )
    #ax1.plot(sector_rs.sell_plot[sym], sector_rs.prices[sym],'v', markersize=10, color='r')
    ax2 = plt.subplot(312)
    ax2.plot(sector_rs.dates, sector_rs.vratio_plot[sym])
    ax2.plot(sector_rs.dates, [0.05]*len(sector_rs.dates))
    #
    ax3 = plt.subplot(313)
    results.portfolio_value.plot(ax=ax3)
    plt.legend(loc=0)
    plt.show()