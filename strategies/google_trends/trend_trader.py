import google_trends as gt
import matplotlib.pyplot as plt
import numpy as np
import statsmodels.api as sm
from datetime import datetime
import pytz
import operator
import pandas as pd
from scipy.stats import zscore

from zipline.algorithm import TradingAlgorithm
from zipline.transforms import batch_transform
from zipline.utils.factory import create_returns_from_list, load_from_yahoo
from zipline.finance import performance, slippage, risk, trading
from zipline.finance.risk import RiskMetricsBase
from zipline.finance.performance import PerformanceTracker, PerformancePeriod

sym_list = ['AAPL','GOOG']
start = datetime(2010, 1, 1, 0, 0, 0, 0, pytz.utc)
end = datetime(2013, 01, 01, 0, 0, 0, 0, pytz.utc)
window = 14

class trend_trader(TradingAlgorithm):  # inherit from TradingAlgorithm
    def initialize(self):
        self.trend_df = self.get_trends()
        self.set_slippage(slippage.FixedSlippage())
        self.dates = []
        self.trends = {sym:[] for sym in sym_list}
        self.zscores = {sym:[] for sym in sym_list}
        self.prices = {sym:[] for sym in sym_list}
        self.day_count = 0
        self.last_order = 0
      
    def get_trends(self):
        trend_df = gt.run(sym_list)
        print trend_df
        return trend_df
            
    def trend_zscore(self,sym,date):
        slice = self.trends[sym][-window:]
        z = zscore(slice)[-1]
        return z
                    
    def get_rs(self,sym):
        window_price = self.prices[sym][-window]
        current_price = self.prices[sym][-window]
        rs = (current_price - window_price)/window_price
        return rs
        
    def short(self,data,sym):
        price = data[sym].price
        q = 10000/price
        self.order(sym,-q)
        
    def long(self,data,sym):
        size = (self.portfolio.cash)/2
        slice = self.trend_df[sym][-window:]
        q = 10000/price
        self.order(sym,q)
    
    def handle_data(self, data):  # overload handle_data() method
        print self.day_count
        date = TradingAlgorithm.get_datetime(self)
        self.dates.append(str(date)[0:10])
        print str(date)[0:10]
        if self.day_count >= window:
            # Get price and trend data
            for sym in sym_list:
                # Price
                sym_price = data[sym].price
                self.prices[sym].append(sym_price)
                # Trend
                trend = self.trend_df[sym][self.dates[-1]]
                self.trends[sym].append(trend)
                
                
            # Get RS and zscore
                rs = self.get_rs
                zscore = trend_zscore(sym,date)
                # Execute trades
                if zscore > 1:
                    long(data,sym)
        self.day_count += 1

if __name__ == '__main__':
    data = load_from_yahoo(stocks=sym_list, indexes={}, start=start, end=end)
    simple_algo = trend_trader()
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
    data.XLY.plot(ax=ax2)
    data.XLP.plot(ax=ax2)
    data.XLE.plot(ax=ax2)
    data.XLF.plot(ax=ax2)
    data.XLB.plot(ax=ax2)
    data.XLK.plot(ax=ax2)
    data.XLV.plot(ax=ax2)
    data.XLI.plot(ax=ax2)
    data.XLU.plot(ax=ax2)
    
    
    
    
    plt.gcf().set_size_inches(18, 8)
    plt.show()