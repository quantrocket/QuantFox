from pyalgotrade.tools import yahoofinance
from pyalgotrade.barfeed import yahoofeed
from pyalgotrade import strategy
from statsmodels import *
import numpy as np
from numpy import corrcoef


import os
import csv

import statArbVars as v
etf = v.etf
start = v.startYear - v.lookBack
end = v.endYear - v.lookBack
instrument_list = v.instrument_list
instReader = csv.reader(open(instrument_list, "rb"), delimiter = ",")
instruments = [symbol for line in instReader for symbol in line]
instFeed = [symbol for symbol in instruments]
instFeed.append(etf)
instPrices = {i:np.array([]) for i in instruments}
etfPrices = np.array([])
highCorrs = []


pairs_file = 'pairs.csv'
pairs_file = open(pairs_file, "w")
pairs_file.truncate()
pairs_file.close()
writer = csv.writer(open('highCorrFeed.csv', 'ab'), delimiter = ",")


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

        #etfPrices.append(etfPrice)

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

def correlationFinder(symbol):
    corr = corrcoef(instPrices[symbol], etfPrices)[1,0]
    return corr
    
def run(start, end):
    feed = build_feed(instFeed, start, end)
    myStrategy = MyStrategy(feed, etf)
    myStrategy.run()
    for symbol in instruments:
        corr = correlationFinder(symbol)
        if  corr >= .8:
            highCorrs.append(symbol)     
            writer.writerow([symbol])
    return highCorrs

            #print symbol + ": " + str(corr)
run(start, end)
print highCorrs
print etfPrices
print instPrices["DD"]
    