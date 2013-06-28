# https://www.quantopian.com/posts/mebane-fabers-relative-strength-strategy-for-taa?utm_source=All+Active+Members&utm_campaign=d448fcef0b-13-2-19&utm_medium=email
# http://papers.ssrn.com/sol3/papers.cfm?abstract_id=962461
# SPY EFA AGG VNQ GLD
import math
import openpyxl
import matplotlib.pyplot as plt

import pandas as pd
import numpy as np
from zipline.algorithm import TradingAlgorithm
from zipline.transforms import MovingAverage
from zipline.utils.factory import load_from_yahoo
from zipline.transforms import batch_transform

from zipline.finance.slippage import (
    VolumeShareSlippage,
    FixedSlippage,
    transact_partial
)

from datetime import datetime, timedelta

from openpyxl import Workbook
from openpyxl.cell import get_column_letter
import csv
import pytz

debug=False

#==============================================================================
@batch_transform
def trailing_return(datapanel):
        if datapanel['price'] is None: return None
        pricedf = np.log(datapanel['price'])

        return pricedf.ix[-1]-pricedf.ix[0]


#==============================================================================
#==============================================================================
class Faber_TacticalAllocation(TradingAlgorithm):
    """
    """

#==============================================================================
    def initialize(self): #,startDate,endDate,startDateTrading,debug):
        self.secs=['SPY','XLY','XLP','XLE','XLF','XLB','XLK','XLV','XLI','XLU']
        self.slippage=FixedSlippage()
        # self.set_commission(commission.PerShare(cost=.005))
        self.leverage = 1.0
        self.top_k = 1
        self.weight = self.leverage/self.top_k
        self.trailing_return= trailing_return(refresh_period=30, window_length=61)



    def reweight(self,data,wt,min_pct_diff=0.1):
            liquidity = self.portfolio.positions_value+self.portfolio.cash
            if debug: print self.portfolio
            if debug: print "Liquidity: ",liquidity
            orders = {}
            pct_diff = 0
            for sec in wt.keys():
                if debug: print "Sec: ",sec
                if debug: print data
                if debug: print wt[sec]/data[sec].price
                target = liquidity*wt[sec]/data[sec].price
                current = self.portfolio.positions[sec].amount
                orders[sec] = target-current
                pct_diff += abs(orders[sec]*data[sec].price/liquidity)
            if pct_diff > min_pct_diff:
                #log.info(("%s ordering %d" % (sec, target-current)))
                if debug: print ("%s ordering %d" % (sec, target-current))
                for sec in orders.keys(): self.order(sec, orders[sec])


    def handle_data(self, data):
            if debug: print "Data: ",data
            ranks = self.trailing_return.handle_data(data)

            if ranks is None: return
            if debug: print "Ranks: ",ranks
            if debug: print "Self.secs: ",self.secs
            ranked_secs = sorted(self.secs, key=lambda x: ranks[x], reverse=True)
            if debug: print "Ranked_secs: ", ranked_secs
            top_secs = ranked_secs[0:self.top_k]
            if debug: print "top_secs: ", top_secs
            wt = dict(((sec,self.weight if sec in top_secs else 0.0) for sec in self.secs))
            if debug: print "wt: ",wt
            self.reweight(data,wt)



if __name__ == '__main__':
# SPY EFA AGG VNQ GLD
    data = load_from_yahoo(stocks=['SPY','XLY','XLP','XLE','XLF','XLB','XLK','XLV','XLI','XLU'], indexes={}, start= pd.datetime(2002, 1, 1, 0, 0, 0, 0, pytz.utc), end= pd.datetime(2013, 1, 1, 0, 0, 0, 0, pytz.utc))
    dma = Faber_TacticalAllocation()
    results = dma.run(data)

    if debug: print results.transactions
    if debug: print results.returns
    if debug: print results.positions
    fig = plt.figure()
    ax1 = fig.add_subplot(211)
    results.portfolio_value.plot(ax=ax1)

    ax2 = fig.add_subplot(212)
    data['SPY'].plot(ax=ax2)
    # # results[['short_mavg', 'long_mavg']].plot(ax=ax2)

    # ax2.plot(results.ix[results.buy].index, results.short_mavg[results.buy],
    #          '^', markersize=10, color='m')
    # ax2.plot(results.ix[results.sell].index, results.short_mavg[results.sell],
    #          'v', markersize=10, color='k')
    plt.legend(loc=0)
    plt.show()