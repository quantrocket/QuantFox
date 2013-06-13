from pyalgotrade.tools import yahoofinance
from pyalgotrade.barfeed import yahoofeed
from pyalgotrade import strategy
from statsmodels import *
import numpy as np
import statsmodels.api as sm
import statsmodels.tsa.stattools as ts
import os
import csv
import statArbVars as v

etf = v.etf
start = v.startYear - v.lookBack
end = v.endYear - v.lookBack
instrument_list = "BasicMaterials.csv"
instReader = csv.reader(open(instrument_list, "rb"), delimiter = ",")
instruments = [symbol for line in instReader for symbol in line]
instFeed = [symbol for symbol in instruments]
instFeed.append(etf)
instPrices = {i:np.array([]) for i in instruments}
etfPrices = np.array([])
coints = {i:[] for i in instruments}
highCorrs = []

pairs_file = 'pairs.csv'
pairs_file = open(pairs_file, "w")
pairs_file.truncate()
pairs_file.close()
writer = csv.writer(open('pairs.csv', 'ab'), delimiter = ",")



class MyStrategy(strategy.Strategy):
    def __init__(self, feed, etf):
        strategy.Strategy.__init__(self, feed)
        self.getBroker().setUseAdjustedValues(True)
        self.__etf = etf

        
    def onBars(self, bars):
        global etfPrices
        etfPrice = bars[self.__etf].getAdjClose()
        etfPrices = np.append(etfPrices, etfPrice)
        for symbol in instruments:
            instPrice = bars[symbol].getAdjClose()
            instPrices[symbol] = np.append(instPrices[symbol], instPrice)

def build_feed(instFeed, fromYear, toYear):
    feed = yahoofeed.Feed()

    for year in range(fromYear, toYear+1):
        for symbol in instFeed:
            fileName = "%s-%d.csv" % (symbol, year)
            if not os.path.exists(fileName):
                print "Downloading %s %d" % (symbol, year)
                csv = yahoofinance.get_daily_csv(symbol, year)
                f = open(fileName, "w")
                f.write(csv)
                f.close()
            feed.addBarsFromCSV(symbol, fileName)
    return feed

def cointegration_test(symbol, etf):
    # Step 1: regress one variable on the other
    ols_result = sm.OLS(instPrices[symbol], etfPrices).fit()
    # Step 2: obtain the residual (ols_resuld.resid)
    # Step 3: apply Augmented Dickey-Fuller test to see whether 
    # the residual is unit root    
    return ts.adfuller(ols_result.resid)
    
def run(start, end):
    feed = build_feed(instFeed, start, end)
    myStrategy = MyStrategy(feed, etf)
    myStrategy.run()
    for symbol in instruments:
        coint = cointegration_test(symbol, etf)
        coints[symbol].append(coint)
        if coint[1] < 0.05:
            highCorrs.append(symbol)     
            writer.writerow([symbol])
        
def print_adf():
    for symbol in instruments:
        print symbol + str(coints[symbol])
    
def print_highCorrs():
    print highCorrs

run(start, end)
print_highCorrs()


    