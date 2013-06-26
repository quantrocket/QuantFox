import matplotlib.pyplot as plt
import numpy as np
import statsmodels.api as sm
from datetime import datetime
import pytz
import operator
import pandas as pd

from zipline.algorithm import TradingAlgorithm
from zipline.transforms import batch_transform
from zipline.utils.factory import create_returns_from_list, load_from_yahoo
from zipline.finance import performance, slippage, risk, trading
from zipline.finance.risk import RiskMetricsBase
from zipline.finance.performance import PerformanceTracker, PerformancePeriod

index = 'SPY'
sym_list = ['XLY','XLP','XLE','XLF','XLB','XLK','XLV','XLI','XLU']
feed = ['SPY','XLY','XLP','XLE','XLF','XLB','XLK','XLV','XLI','XLU']


class sector_rs(TradingAlgorithm):  # inherit from TradingAlgorithm
    def initialize(self):
        self.dates = []
        self.prices = {sym:[] for sym in feed}
        self.rs_list = {sym:0 for sym in sym_list}
        
    def get_rs(self,data):
        spy_start = self.prices[index][-250]
        spy_now = data[index].price
        spy_change = (spy_start-spy_now)/spy_start
        for sym in sym_list:
            etf_start = self.prices[sym][-250]
            etf_now = data[sym].price
            etf_change = (etf_start-etf_now)/etf_start
            rs = etf_change / spy_change
            self.rs_list[sym] = rs
            
    def short(self,data,sym):
        price = data[sym].price
        q = 1000/price
        self.order(sym,-q)
        
    def long(self,data,sym):
        price = data[sym].price
        q = 1000/price
        self.order(sym,q)
        
    def handle_data(self, data):  # overload handle_data() method
        
        month = int(str(TradingAlgorithm.get_datetime(self))[5:7])
        
        spy_price = data[index].price
        self.prices[index].append(spy_price)
        
        for sym in sym_list:
            sym_price = data[sym].price
            self.prices[sym].append(sym_price)
        
        if len(self.dates) < 250:
            pass
        else:
            if month != self.dates[-1]:
                # Exit existing positions
                for sym in sym_list:
                    if self.portfolio.positions[sym].amount != 0:
                        q = self.portfolio.positions[sym].amount
                        self.order(sym,-q)
                # Enter new position
                self.get_rs(data)
                sorted_rs = sorted(self.rs_list.iteritems(), key=operator.itemgetter(1))
                #print 'SHORT: ', sorted_rs[0][0], sorted_rs[1][0], sorted_rs[2][0]
                #print 'LONG: ', sorted_rs[-3][0], sorted_rs[-2][0], sorted_rs[-1][0]
                self.short(data,sorted_rs[0][0])
                self.short(data,sorted_rs[1][0])
                self.short(data,sorted_rs[2][0])
                self.long(data,sorted_rs[-1][0])
                self.long(data,sorted_rs[-2][0])
                self.long(data,sorted_rs[-3][0])
            else:
                pass
        self.dates.append(month)

if __name__ == '__main__':
    start = datetime(2010, 1, 1, 0, 0, 0, 0, pytz.utc)
    end = datetime(2013, 01, 01, 0, 0, 0, 0, pytz.utc)
    data = load_from_yahoo(stocks=feed, indexes={}, start=start, end=end)
    simple_algo = sector_rs()
    results = simple_algo.run(data)

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



    ax1 = plt.subplot(211)
    results.portfolio_value.plot(ax=ax1)
    ax2 = plt.subplot(212, sharex=ax1)
    data.SPY.plot(ax=ax2)
    plt.gcf().set_size_inches(18, 8)
    plt.show()