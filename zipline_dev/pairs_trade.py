import matplotlib.pyplot as plt
import numpy as np
import statsmodels.api as sm
from datetime import datetime
import pytz
import csv
import os


from zipline.algorithm import TradingAlgorithm
from zipline.transforms import batch_transform
from zipline.utils.factory import create_returns_from_list
from zipline.utils.factory import load_from_yahoo
from zipline.finance import performance, slippage, risk
from zipline.finance import trading
from zipline.finance.risk import RiskMetricsBase
from zipline.finance.performance import PerformanceTracker
from matplotlib.backends.backend_pdf import PdfPages

#sym_list = {'GLD':'IAU'}
#sym_list = {'KO':'PEP'}
#sym_list = {'VALE':'RIO'}
#sym_list = {'CH':'ECH'}
sym_list = {'TAL':'TGH','CH':'ECH'}
#sym_list = {'XOM':'COP'}
#sym_list = {'GLD':'IAU','KO':'PEP'}

def build_feed():
    feed = []
    for sym in sym_list:
        feed.append(sym)
        feed.append(sym_list[sym])
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

def clearOrders():
    orders_file = 'orders.csv'
    orders_file = open(orders_file, "w")
    orders_file.truncate()
    writer = csv.writer(open('orders.csv', 'ab'), delimiter = ',')
    header = ['DATE', 'SYMBOL', 'Z-SCORE', 'PRICE', 'AMOUNT', 'TYPE', 'Gain', 'PAIR GAIN']
    writer.writerow(header)
    orders_file.close()
    return
    
class Pairtrade(TradingAlgorithm):
    
    def initialize(self, window_length=100):
        clearOrders()
        """ Slippage was messing up orders, setting to fixed corrected revisit this
        """    
        self.set_slippage(slippage.FixedSlippage())
        self.day_count = 0
        self.dates = []
        self.spreads = {sym:[] for sym in sym_list}
        self.ratios = {sym:np.array([]) for sym in sym_list}
        self.invested = {sym:[0,0] for sym in sym_list}              # invested[sym,etf]
        self.returns = {sym:[[],[]] for sym in sym_list}             # returns[sym][netReturn,cumReturn]
        self.cumReturns = {sym:[] for sym in sym_list}
        self.zscores = {sym:np.array([0]*(window_length-1)) for sym in sym_list}
        self.window_length = window_length
        self.ols_transform = ols_transform(refresh_period=self.window_length,window_length=self.window_length)
        
    def trade_return(self, sym, etf, currentSym, currentEtf):
        #####################################################
        # Calculate gain since last opened position
        if self.day_count < 1:
            symReturn = 0
            etfReturn = 0
            net_gain = 0
            self.returns[sym][0].append(net_gain)
        else:
            if self.portfolio.positions[sym].amount == 0:
                symReturn = 0
                etfReturn = 0
                net_gain = 0
                self.returns[sym][0].append(net_gain)
            else:
                sym_cost_basis = self.portfolio['positions'][sym]['cost_basis']
                etf_cost_basis = self.portfolio['positions'][etf]['cost_basis']
                if self.portfolio.positions[sym].amount > 0:
                    symReturn = (currentSym-sym_cost_basis)/sym_cost_basis
                    etfReturn = (etf_cost_basis-currentEtf)/etf_cost_basis
                    net_gain = symReturn + etfReturn
                    self.returns[sym][0].append(net_gain)
                elif self.portfolio.positions[sym].amount < 0:
                    symReturn = (sym_cost_basis-currentSym)/sym_cost_basis
                    etfReturn = (currentEtf-etf_cost_basis)/etf_cost_basis
                    net_gain = symReturn + etfReturn
                    self.returns[sym][0].append(net_gain)
        ######################################################
        # Calculate the gain change, keep rolling sum
        if self.day_count < 1:
            self.returns[sym][1].append(0)
        else:
            if self.portfolio.positions[sym].amount == 0:
                delta = 0
                self.returns[sym][1].append(self.returns[sym][1][-1] + delta)
            else:
                delta = self.returns[sym][0][-1] - self.returns[sym][0][-2]
                self.returns[sym][1].append(self.returns[sym][1][-1] + delta)
        return symReturn, etfReturn

    def orderWriter(self, *args):
        writer = csv.writer(open('orders.csv', 'ab'), delimiter = ',')
        #data_to_write = [*args]
        writer.writerow(args)
        return
    
    def handle_data(self, data):
        ####################################################################
        # Keep track of days
        #print self.day_count
        self.dates = np.append(self.dates, TradingAlgorithm.get_datetime(self))
        print self.dates[-1]
        #print 'Progress: ' + str(PerformanceTracker.to_dict(self))
        ####################################################################
        # Get the prices and do some calculations
        for sym in sym_list:
            etf = sym_list[sym]
            #print str(self.dates[-1]) + ': ' + str(self.portfolio['positions'][sym]) #[1][sym]['position'])
            #print str(self.dates[-1]) + ': ' + str(self.portfolio['positions'][etf]) #[1][sym]['position'])
            #print self.portfolio
            sym_price = data[sym].price
            etf_price = data[etf].price
            ratio = sym_price / etf_price
            self.ratios[sym] = np.append(self.ratios[sym], ratio)
        ####################################################################
        # Calculate the trade return for analysis purposes
            gains = self.trade_return(sym, etf, sym_price, data[etf].price)
            sym_gain = gains[0]
            etf_gain = gains[1]
        ####################################################################
        # Trade related calculations loop
        self.day_count += 1
        for sym in sym_list:
            etf = sym_list[sym]
            sym_price = data[sym].price
            etf_price = data[etf].price
            ################################################################
            # 1. Compute regression coefficients between the two instruments
            params = self.ols_transform.handle_data(data, sym, etf)
            if params is None:
                return
            intercept, slope = params
            ################################################################
            # 2. Compute spread and z-score
            zscore = self.compute_zscore(data, sym, etf, sym_price, etf_price, slope, intercept)
            #self.record(zscores[sym]=zscore)
            ################################################################
            # 3. Place orders
            self.place_orders(data, sym, etf, sym_price, etf_price, sym_gain, etf_gain, zscore)
        

    def compute_zscore(self, data, sym, etf, sym_price, etf_price, slope, intercept):
        ####################################################################
        # 1. Compute the spread given slope and intercept.
        # 2. z-score the spread.
        spread = (sym_price - (slope * etf_price + intercept))
        self.spreads[sym].append(spread)
        spread_wind = self.spreads[sym][-self.window_length:]
        zscore = (spread - np.mean(spread_wind)) / np.std(spread_wind)
        self.zscores[sym] = np.append(self.zscores[sym], zscore)
        return zscore

    def place_orders(self, data, sym, etf, sym_price, etf_price, sym_gain, etf_gain, zscore):
        ####################################################################
        # Buy spread if z-score is > 2, sell if z-score < .5.
        etf = sym_list[sym]
        sym_price = data[sym].price
        etf_price = data[etf].price
        if zscore >= 2 and self.portfolio.positions[sym].amount == 0:
            sym_quantity = -int(10000 / sym_price)
            etf_quantity = int(10000 / etf_price)
            self.order(sym, sym_quantity)
            self.order(etf, etf_quantity)
            self.orderWriter(str(self.dates[-1])[:10], sym, zscore, sym_price, sym_quantity, 'Short')
            self.orderWriter(str(self.dates[-1])[:10], etf, zscore, etf_price, etf_quantity, 'Long')
        elif zscore <= -2 and self.portfolio.positions[sym].amount == 0:
            sym_quantity = int(10000 / sym_price)
            etf_quantity = -int(10000 / etf_price)
            self.order(sym, sym_quantity)
            self.order(etf, etf_quantity)
            self.orderWriter(str(self.dates[-1])[:10], sym, zscore, sym_price, sym_quantity, 'Long')
            self.orderWriter(str(self.dates[-1])[:10], etf, zscore, etf_price, etf_quantity, 'Short')
        elif abs(zscore) < .5 and self.portfolio.positions[sym].amount != 0:
            self.sell_spread(sym, etf, sym_price, etf_price, sym_gain, etf_gain, zscore)

    def sell_spread(self, sym, etf, sym_price, etf_price, sym_gain, etf_gain, zscore):
        #####################################################################
        # decrease exposure, regardless of position long/short.
        # buy for a short position, sell for a long.
        etf = sym_list[sym]
        etf_amount = self.portfolio.positions[etf].amount
        self.order(etf, -1 * etf_amount)
        sym_amount = self.portfolio.positions[sym].amount
        self.order(sym, -1 * sym_amount)
        self.orderWriter(str(self.dates[-1])[:10], sym, zscore, sym_price, sym_amount, 'Exit', sym_gain, self.returns[sym][0][-1])
        self.orderWriter(str(self.dates[-1])[:10], etf, zscore, etf_price, etf_amount, 'Exit', etf_gain, self.returns[sym][0][-1])

if __name__ == '__main__':
    start = datetime(2008, 1, 1, 0, 0, 0, 0, pytz.utc)
    end = datetime(2012, 12, 31, 0, 0, 0, 0, pytz.utc)
    feed = build_feed()
    data = load_from_yahoo(stocks=feed, indexes={},
                           start=start, end=end, adjusted=True)
    
    pairtrade = Pairtrade()
    results = pairtrade.run(data)
    
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
        print str(sym)+":"+str(sym_list[sym])+': '+str((round(pairtrade.returns[sym][1][-1]*100,4)))+'%'
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
        plt.plot(pairtrade.dates, pairtrade.returns[sym][1])
        plt.setp(ax3.get_xticklabels(), visible=True)
        plt.xticks(rotation=45)
        plt.grid(b=True, which='major', color='k')
        
        ax4 = plt.subplot(414, ylabel='portfolio value')
        plt.plot(pairtrade.dates, results.portfolio_value/100000)
        plt.setp(ax4.get_xticklabels(), visible=True)
        plt.xticks(rotation=45)
        plt.grid(b=True, which='major', color='k')
        
        plt.gcf().set_size_inches(30, 20)
        
        """pp = PdfPages('charts.pdf')    
        pp.savefig(plt)"""
        
        plt.savefig(str(sym)+'.pdf')
        #plt.show()
        plt.clf()