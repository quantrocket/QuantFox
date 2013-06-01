from pyalgotrade.tools import yahoofinance
from pyalgotrade.barfeed import yahoofeed
from pyalgotrade import strategy
from numpy import corrcoef


import os
import csv

etf = 'XLB'
start = 2010
end = 2011
instrument_list = 'ConsumerDiscretionary.csv'
instReader = csv.reader(open(instrument_list, "rb"), delimiter = ",")
instruments = [symbol for line in instReader for symbol in line]
instFeed = [symbol for symbol in instruments]
instFeed.append(etf)
instPrices = {i:[] for i in instruments}
etfPrices = []
highCorrs = []


class MyStrategy(strategy.Strategy):
    def __init__(self, feed, etf):
        strategy.Strategy.__init__(self, feed)
        self.getBroker().setUseAdjustedValues(True)
        self.__etf = etf
        
    def onBars(self, bars):
        for symbol in instruments:
            instPrice = bars[symbol].getAdjClose()
            instPrices[symbol].append(instPrice)
        etfPrice = bars[self.__etf].getAdjClose()
        etfPrices.append(etfPrice)

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

feed = build_feed(instFeed, start, end)
myStrategy = MyStrategy(feed, etf)
myStrategy.run()

def correlationFinder(symbol):
    corr = corrcoef(instPrices[symbol], etfPrices)[1,0]
    return corr
    
for symbol in instruments:
    corr = correlationFinder(symbol)
    
    if  corr >= .7:
        highCorrs.append(symbol)
        print symbol + ": " + str(corr)

#print highCorrs
    