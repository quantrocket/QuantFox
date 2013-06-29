import google_trends as gt
import matplotlib.pyplot as plt
import numpy as np
import statsmodels.api as sm
from datetime import datetime
import pytz
import operator
import pandas as pd
from scipy.stats import zscore
import talib

from zipline.algorithm import TradingAlgorithm
from zipline.transforms import batch_transform
from zipline.utils.factory import create_returns_from_list, load_bars_from_yahoo
from zipline.finance import performance, slippage, risk, trading
from zipline.finance.risk import RiskMetricsBase
from zipline.finance.performance import PerformanceTracker, PerformancePeriod

sym_list = ['KO','IBM','FICO','FCX']
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
        self.prices = {sym:np.array([]) for sym in sym_list}
        self.highs = {sym:np.array([]) for sym in sym_list}
        self.lows = {sym:np.array([]) for sym in sym_list}
        self.day_count = 0
        self.last_order = 0
        self.stops = {sym:[0,0] for sym in sym_list}    #[take,stop]
        self.buy_plot = {sym:[] for sym in sym_list}
        self.sell_plot = {sym:[] for sym in sym_list}
        self.atr_plot = {sym:{'profit':[],'loss':[]} for sym in sym_list}
      
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
        
    def get_rsi(self,sym):
        #print sym
        rsi = talib.RSI(self.prices[sym],2)
        return rsi
    
    def get_atr(self,sym):
        atr = talib.ATR(self.highs[sym], self.lows[sym], self.prices[sym], timeperiod=14)
        return atr
    
    def get_macd(self,sym):
        macd, macdsignal, macdhist = talib.MACD(self.prices[sym],fastperiod=12,slowperiod=26,signalperiod=9)
        return macd, macdsignal, macdhist 
    
    def short(self,data,sym):
        price = data[sym].price
        q = 10000/price
        self.order(sym,-q)
        
    def long(self,data,sym):
        #size = (self.portfolio.cash)/2
        price = data[sym].price
        q = 10000/price
        self.order(sym,q)
    
    def handle_data(self, data):  # overload handle_data() method
        #print self.day_count
        date = TradingAlgorithm.get_datetime(self)
        self.dates.append(date)
        #print self.portfolio
        #print str(date)[0:10]
        # Get price and trend data
        for sym in sym_list:
            # Price
            sym_price = data[sym].price
            sym_high = data[sym].high
            sym_low = data[sym].low
            self.prices[sym] = np.append(self.prices[sym],sym_price)
            self.lows[sym] = np.append(self.prices[sym],sym_low)
            self.highs[sym] = np.append(self.prices[sym],sym_high)
            # RSI, MACD
            rsi = self.get_rsi(sym)[-1]
            macd, macdsignal, macdhist = self.get_macd(sym)
            # Trend
            trend = self.trend_df[sym][self.dates[-1]]
            self.trends[sym].append(float(trend))      
            # Get RS and zscore
            if self.day_count >= window:
                rs = self.get_rs
                zscore = self.trend_zscore(sym,date)
                self.zscores[sym].append(zscore)
                # Execute trades
                if self.portfolio.positions[sym].amount == 0 and zscore >= 3:
                    self.long(data,sym)
                    print str(date)[0:10],'LONG:',sym
                elif self.portfolio.positions[sym].amount != 0:
                    if sym_price >= self.atr_plot[sym]['profit'][-1] or sym_price <= self.atr_plot[sym]['loss'][-1]:
                        q = self.portfolio.positions[sym].amount
                        self.order(sym,-q)
                        print str(date)[0:10],'Exit:',sym
            else:
                self.zscores[sym].append(0)
            atr = self.get_atr(sym)[-1]
            self.atr_plot[sym]['profit'].append((atr*3)+sym_price)
            self.atr_plot[sym]['loss'].append(-(atr*1.5)+sym_price)
        self.day_count += 1

if __name__ == '__main__':
    data = load_bars_from_yahoo(stocks=sym_list, indexes={}, start=start, end=end)
    trend_trader = trend_trader()
    results = trend_trader.run(data)

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

    for sym in sym_list:
        ax1 = plt.subplot(311, ylabel='Portfolio Value')
        results.portfolio_value.plot(ax=ax1)
        ax2 = plt.subplot(312, sharex=ax1, ylabel=str(sym+' Price'))
        ax2.plot(trend_trader.dates,trend_trader.prices[sym])
        # Adjust ATR bands
        trend_trader.atr_plot[sym]['profit'].insert(0,trend_trader.atr_plot[sym]['profit'][0])
        trend_trader.atr_plot[sym]['loss'].insert(0,trend_trader.atr_plot[sym]['loss'][0])
        del trend_trader.atr_plot[sym]['profit'][-1]
        del trend_trader.atr_plot[sym]['loss'][-1]
        ax2.plot(trend_trader.dates, trend_trader.atr_plot[sym]['profit'],alpha=0.3)
        ax2.plot(trend_trader.dates, trend_trader.atr_plot[sym]['loss'],alpha=0.3)
        plt.grid(b=True, which='major', color='k')
        ax3 = plt.subplot(313, sharex=ax1, ylabel=str(sym+' gTrend zscore'))
        ax3.plot(trend_trader.dates,trend_trader.zscores[sym])
        plt.grid(b=True, which='major', color='k')
        
    
        plt.gcf().set_size_inches(30, 20)
        plt.show()