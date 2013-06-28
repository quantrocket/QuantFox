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
import zipline.transforms.ta as ta
from zipline.utils.factory import create_returns_from_list, load_bars_from_yahoo
from zipline.finance import performance, slippage, risk, trading
from zipline.finance.risk import RiskMetricsBase
from zipline.protocol import BarData
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
        self.highs = {sym:np.array([]) for sym in feed}
        self.lows = {sym:np.array([]) for sym in feed}
        self.vratio_plot = {sym:np.array([]) for sym in feed}
        self.buy_plot = {sym:[] for sym in feed}
        self.stops = {sym:[0,0] for sym in feed}    #[take,stop]
        self.sell_plot = {sym:[] for sym in feed}
        self.day_count = 0
        
    def get_rsi(self,sym):
        #print sym
        rsi = talib.RSI(self.prices[sym],2)
        return rsi
    
    def get_macd(self,sym):
        macd, macdsignal, macdhist = talib.MACD(self.prices[sym],fastperiod=12,slowperiod=26,signalperiod=9)
        return macd, macdsignal, macdhist 
         
    def get_atr(self,sym):
        atr = talib.ATR(self.highs[sym], self.lows[sym], self.prices[sym], timeperiod=14)
        return atr
    
    def get_stoch(self,sym):
        slowk, slowd = talib.STOCH(self.highs[sym], self.lows[sym], self.prices[sym], fastk_period=5, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0)
        return slowk, slowd

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
            sym_high = data[sym].high
            sym_low = data[sym].low
            self.prices[sym] = np.append(self.prices[sym],sym_price)
            self.lows[sym] = np.append(self.prices[sym],sym_low)
            self.highs[sym] = np.append(self.prices[sym],sym_high)
            
        # Execute trades
        for sym in sym_list:
            if self.day_count >= 0:
                atr = self.get_atr(sym)[-1]
                rsi = self.get_rsi(sym)[-1]
                macd, macdsignal, macdhist = self.get_macd(sym)
                slowk, slowd = self.get_stoch(sym)
                #
                if self.portfolio.positions[sym].amount == 0:
                    if macd[-1] > 0 and rsi > 70 and 50 <= slowk[-1] <= 80:
                        print day,' Long ',sym
                        self.long(data,sym)
                        self.buy_plot[sym].append(self.day_count)
                        take = (atr*5)+sym_price
                        stop = -(atr*2)+sym_price
                        self.stops[sym] = [take,stop]
                    elif macd[-1] < 0 and rsi < 30 and 20 <= slowk[-1] <= 50:
                        print day,' Short ',sym
                        self.short(data,sym)
                        self.sell_plot[sym].append(self.day_count)
                        take = -(atr*5)+sym_price
                        stop = (atr*2)+sym_price
                        self.stops[sym] = [take,stop]
                    else:
                        pass
                elif self.portfolio.positions[sym].amount > 0:
                    if sym_price >= self.stops[sym][0] or sym_price <= self.stops[sym][1]:
                        print day,' Exit Long ',sym
                        q = self.portfolio.positions[sym].amount
                        self.order(sym,-q)
                        self.sell_plot[sym].append(self.day_count)
                elif self.portfolio.positions[sym].amount < 0:
                    if sym_price <= self.stops[sym][0] or sym_price >= self.stops[sym][1]:
                        print day,' Exit Short ',sym
                        q = self.portfolio.positions[sym].amount
                        self.order(sym,-q)
                        self.buy_plot[sym].append(self.day_count)
        self.day_count += 1

if __name__ == '__main__':
    start = datetime(2012, 1, 1, 0, 0, 0, 0, pytz.utc)
    end = datetime(2013, 01, 01, 0, 0, 0, 0, pytz.utc)
    data = load_bars_from_yahoo(stocks=feed, indexes={}, start=start, end=end)
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
    ax1 = plt.subplot(311)
    data.AAPL.price.plot(ax=ax1)
    #ax1.plot(sector_rs.buy_plot[sym], sector_rs.prices[sym],'^', markersize=10, color='g' )
    #ax1.plot(sector_rs.sell_plot[sym], sector_rs.prices[sym],'v', markersize=10, color='r')
    ax2 = plt.subplot(312)
    #
    ax3 = plt.subplot(313)
    results.portfolio_value.plot(ax=ax3)
    plt.legend(loc=0)
    plt.show()