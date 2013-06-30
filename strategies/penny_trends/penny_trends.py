import key_trends as gt
import matplotlib.pyplot as plt
import numpy as np
import statsmodels.api as sm
from datetime import datetime
import pytz
import operator
import pandas as pd
from scipy.stats import zscore
import talib
import csv

from zipline.algorithm import TradingAlgorithm
from zipline.transforms import batch_transform
from zipline.utils.factory import create_returns_from_list, load_bars_from_yahoo
from zipline.finance import performance, slippage, risk, trading
from zipline.finance.risk import RiskMetricsBase
from zipline.finance.performance import PerformanceTracker, PerformancePeriod

sym_list = ['OCLS']
key_list = ['OCLS','microcyn']
#sym_list = ['CHTP']
#key_list = ['CHTP','northera']
#sym_list = ['TSPT']
#key_list = ['TSPT','zolpidem']
#sym_list = ['CYCC']
#key_list = ['CYCC','sapacitabine','seliciclib']
#sym_list = ['AEZS']
#key_list = ['AEZS','ozarelix','perifosine']



start = datetime(2010, 1, 1, 0, 0, 0, 0, pytz.utc)
end = datetime(2013, 01, 01, 0, 0, 0, 0, pytz.utc)
window_long = 14
window_short = 14

class trend_trader(TradingAlgorithm):  # inherit from TradingAlgorithm
    def initialize(self):
        self.trend_df = self.get_trends()
        self.set_slippage(slippage.FixedSlippage())
        self.dates = []
        self.trends = {sym:[] for sym in sym_list}
        self.zscores = {sym:[] for sym in sym_list}
        self.zscores_s = {sym:[] for sym in sym_list}
        self.chaikin_plot = {sym:[] for sym in sym_list}
        self.prices = {sym:np.array([]) for sym in sym_list}
        self.volume = {sym:np.array([]) for sym in sym_list}
        self.highs = {sym:np.array([]) for sym in sym_list}
        self.lows = {sym:np.array([]) for sym in sym_list}
        self.day_count = 0
        self.last_order = 0
        self.rsi_plot = {sym:np.array([]) for sym in sym_list}
        self.mfv = {sym:np.array([]) for sym in sym_list}
        self.stops = {sym:[0,0] for sym in sym_list}    #[take,stop]
        self.buy_plot = {sym:[] for sym in sym_list}
        self.sell_plot = {sym:[] for sym in sym_list}
        self.atr_plot = {sym:{'profit':[],'loss':[]} for sym in sym_list}
      
    def get_trends(self):
        trend_df = gt.run(key_list)
        print trend_df
        return trend_df
            
    def trend_zscore(self,sym,date,window):
        slice = self.trends[sym][-window:]
        z = zscore(slice)[-1]
        return z
                    
    def get_rs(self,sym):
        window_price = self.prices[sym][-window_long]
        current_price = self.prices[sym][-window_long]
        rs = (current_price - window_price)/window_price
        return rs
        
    def get_chaikin(self,sym):
        high = self.highs[sym][-1]
        low = self.lows[sym][-1]
        close = self.prices[sym][-1]
        volume = self.volume[sym][-1]
        mfm = ((close-low)-(high-close)) / (high-low)
        mfv = mfm*volume
        self.mfv[sym] = np.append(self.mfv[sym],mfv)
        if self.day_count >= 20:
            vol_period = self.volume[sym][-20:]
            mfv_period = self.mfv[sym][-20:]
            cum_vol = 0
            cum_mfv = 0
            for i in mfv_period:
                cum_mfv += i
            for i in vol_period:
                cum_vol += i
            cmf = cum_mfv / cum_vol
            return cmf
        else:
            return 0
        
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
            sym_volume = data[sym].volume
            self.prices[sym] = np.append(self.prices[sym],sym_price)
            self.lows[sym] = np.append(self.prices[sym],sym_low)
            self.highs[sym] = np.append(self.prices[sym],sym_high)
            # Volume
            self.volume[sym] = np.append(self.volume[sym],sym_volume)
            # RSI, MACD, Chaikin
            cmf = self.get_chaikin(sym)
            self.chaikin_plot[sym] = np.append(self.chaikin_plot[sym],cmf)
            rsi = self.get_rsi(sym)[-1]
            self.rsi_plot[sym] = np.append(self.rsi_plot[sym],rsi)
            macd, macdsignal, macdhist = self.get_macd(sym)
            # Trend
            trend = self.trend_df[sym][self.dates[-1]]
            self.trends[sym].append(float(trend))      
            # Get RS and zscore
            if self.day_count >= window_long:
                rs = self.get_rs
                zscore = self.trend_zscore(sym,date,window_long)
                zscore_s = self.trend_zscore(sym,date,window_short)
                self.zscores[sym].append(zscore)
                self.zscores_s[sym].append(zscore_s)
                # Execute trades
                if self.portfolio.positions[sym].amount == 0 and self.zscores[sym][-1] > 2 and rsi < 70: # and cmf > -0.05:
                    #if self.zscores_s[sym][-1] > self.zscores[sym][-1] and self.zscores_s[sym][-2] < self.zscores[sym][-2]:
                     if 1 == 1:
                        self.long(data,sym)
                        print str(date)[0:10],'LONG:',sym
                elif self.portfolio.positions[sym].amount != 0:
                    if sym_price >= self.atr_plot[sym]['profit'][-1] or sym_price <= self.atr_plot[sym]['loss'][-1]:
                        q = self.portfolio.positions[sym].amount
                        self.order(sym,-q)
                        print str(date)[0:10],'Exit:',sym
            else:
                self.zscores[sym].append(0)
                self.zscores_s[sym].append(0)
            atr = self.get_atr(sym)[-1]
            self.atr_plot[sym]['profit'].append((atr*6)+sym_price)
            self.atr_plot[sym]['loss'].append(-(atr*2)+sym_price)
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
        ax1 = plt.subplot(411, ylabel='Portfolio Value')
        results.portfolio_value.plot(ax=ax1)
        ax2 = plt.subplot(412, sharex=ax1, ylabel=str(sym+' Price'))
        ax2t = ax2.twinx()
        fillcolor = 'darkgoldenrod'
        ax2.plot(trend_trader.dates,trend_trader.prices[sym])
        volume = (trend_trader.prices[sym]*trend_trader.volume[sym])/1e6  # dollar volume in millions
        vmax = volume.max()
        poly = ax2t.fill_between(trend_trader.dates,volume, 0, label='Volume', facecolor=fillcolor, edgecolor=fillcolor, alpha=0.5)
        # Adjust ATR bands
        trend_trader.atr_plot[sym]['profit'].insert(0,trend_trader.atr_plot[sym]['profit'][0])
        trend_trader.atr_plot[sym]['loss'].insert(0,trend_trader.atr_plot[sym]['loss'][0])
        del trend_trader.atr_plot[sym]['profit'][-1]
        del trend_trader.atr_plot[sym]['loss'][-1]
        ax2.plot(trend_trader.dates, trend_trader.atr_plot[sym]['profit'],alpha=0.3)
        ax2.plot(trend_trader.dates, trend_trader.atr_plot[sym]['loss'],alpha=0.3)
        plt.grid(b=True, which='major', color='k')
        ax3 = plt.subplot(413, sharex=ax1, ylabel=str(' gTrend zscore'))
        ax3.plot(trend_trader.dates,trend_trader.zscores[sym])
        ax3.fill_between(trend_trader.dates,2,trend_trader.zscores[sym],facecolor='green',alpha=0.5)
        ax3.fill_between(trend_trader.dates,-2,2,facecolor='white',alpha=1)
        plt.grid(b=True, which='major', color='k')
        #ax4 = plt.subplot(514, sharex=ax1, ylabel=str(sym+' CMF'))
        #ax4.plot(trend_trader.dates,trend_trader.chaikin_plot[sym])
        #ax4.fill_between(trend_trader.dates,trend_trader.chaikin_plot[sym],0,where=trend_trader.chaikin_plot[sym]>0, facecolor='green',alpha=0.5)
        #ax4.fill_between(trend_trader.dates,trend_trader.chaikin_plot[sym],0,where=trend_trader.chaikin_plot[sym]<0, facecolor='red',alpha=0.5)
        #plt.grid(b=True, which='major', color='k')
        ax4 = plt.subplot(414, sharex=ax1, ylabel=str('RSI'))
        ax4.plot(trend_trader.dates,trend_trader.rsi_plot[sym])
        ax4.fill_between(trend_trader.dates,70,trend_trader.rsi_plot[sym],facecolor='green',alpha=0.5)
        ax4.fill_between(trend_trader.dates,30,70,facecolor='white',alpha=1)
        plt.grid(b=True, which='major', color='k')
       
        plt.subplots_adjust(hspace=0) 
        plt.gcf().set_size_inches(30, 20)
        plt.show()
