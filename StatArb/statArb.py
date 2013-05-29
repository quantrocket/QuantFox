from pyalgotrade import strategy
from pyalgotrade.barfeed import yahoofeed
from pyalgotrade import plotter
from pyalgotrade.tools import yahoofinance
from pyalgotrade.stratanalyzer import returns
from pyalgotrade.stratanalyzer import sharpe
from pyalgotrade.utils import stats
from pyalgotrade import dataseries
from numpy import mean, std


import os
import csv

etf = 'XLB'
instrument_list = 'instruments.csv'
instReader = csv.reader(open(instrument_list, "rb"), delimiter = ",")
instruments = [symbol for line in instReader for symbol in line]
instFeed = [symbol for symbol in instruments]
instFeed.append(etf)
instPrices = {i:[] for i in instruments}
naInstPrices = {i:[] for i in instruments}
instSpread = {i:[] for i in instruments}
instStock = {i:[0, 0, 0] for i in instruments} # [Shares, EnteredSpread, MarketValue]
etfStock = {etf:0}
etfPrices = []
naEtfPrices = []
marketValue = {i:[20000] for i in instruments}
spreadUpper = {i:[] for i in instruments}
spreadLower = {i:[] for i in instruments}
spreadMiddle = {i:[] for i in instruments}

enterSpread = 0.05
exitSpread = 0.03

class MyStrategy(strategy.Strategy):
    def __init__(self, feed, etf):
        strategy.Strategy.__init__(self, feed)
        self.getBroker().setUseAdjustedValues(True)
        self.__etf = etf
        
    def instInventory(self, symbol, qInst, enterSpread):
        self.__symbol = symbol
        self.__qInst = qInst
        instStock[symbol][0] = qInst
        instStock[symbol][1] = enterSpread

    def etfInventory(self, qEtf):
        self.__qEtf = qEtf
        etfStock[etf] = qEtf
        
    def instValue(self, symbol, enterSpread, spread):
        self.__symbol = symbol
        self.__enterSpread = enterSpread
        self.__spread = spread
        gain = (spread - enterSpread) * 10000
        return gain
    
        
    def middleBand(self, symbol):
        self.__symbol = symbol
        middle = mean(instSpread[symbol][-20:])
        return middle
    def upperBand(self, symbol):
        self.__symbol = symbol
        upper = self.middleBand(symbol) + (std(instSpread[symbol][-20:]) * 2)
        return upper
    def lowerBand(self, symbol):
        self.__symbol = symbol
        lower = self.middleBand(symbol) - (std(instSpread[symbol][-20:]) * 2)
        return lower

    def onBars(self, bars):
        writer = csv.writer(open('orders.csv', 'ab'), delimiter = ',')
        for symbol in instruments:
            # Define shares | get prices
            shares = self.getBroker().getShares(symbol)
            instPrice = bars[symbol].getAdjClose()
            etfPrice = bars[self.__etf].getAdjClose()
            # Append prices to list
            instPrices[symbol].append(instPrice)
            etfPrices.append(etfPrice)
            # Normalize price
            naInstPrice = instPrice / instPrices[symbol][0]
            naEtfPrice = etfPrice / etfPrices[0]
            naInstPrices[symbol].append(naInstPrice)
            naEtfPrices.append(naEtfPrice)
            # Define notational, spread
            notional = shares * instPrice
            spread = naInstPrice - naEtfPrice
            instSpread[symbol].append(spread)
            if len(instSpread[symbol]) >= 20:
                middle = self.middleBand(symbol)
                upper = self.upperBand(symbol)
                lower = self.lowerBand(symbol)
                spreadMiddle[symbol].append(middle)
                spreadUpper[symbol].append(upper)
                spreadLower[symbol].append(lower)
            else:
                middle = 0
                upper = 0
                lower = 0
                spreadMiddle[symbol].append(0)
                spreadUpper[symbol].append(0)
                spreadLower[symbol].append(0)
            # Update Market Value of Inventory
            if instStock[symbol][0] > 0:
                gain = self.instValue(symbol, instStock[symbol][1], spread)
                instStock[symbol][2] = ((20000 + gain) / 20000) - 1
                marketValue[symbol].append(((20000 + gain) / 20000) - 1)
            else:
                marketValue[symbol].append(instStock[symbol][2])
            # Define trade rules
            #if spread <= -enterSpread and instStock[symbol][0] == 0 and notional < 1000000:
            if spread <= lower and lower != 0 and instStock[symbol][0] == 0 and notional < 1000000:
                    qInst = 10000 / instPrice
                    qEtf = 10000 / etfPrice
                    self.order(symbol, qInst)
                    self.order(self.__etf, -qEtf)
                    self.instInventory(symbol, qInst, spread)
                    self.etfInventory(etfStock[etf] - qEtf)
                    inst_to_enter = [str(bars[symbol].getDateTime()), symbol, round(spread, 4), 'Buy', str(round(qInst))]
                    etf_to_enter = [str(bars[etf].getDateTime()), etf, round(spread, 4), 'Sell', str(round(qEtf))]
                    writer.writerow(inst_to_enter)
                    writer.writerow(etf_to_enter)
            #elif spread >= -exitSpread and instStock[symbol][0] > 0 and notional > 0:
            elif spread >= upper and upper != 0 and instStock[symbol][0] > 0 and notional > 0:
                    qInst = 10000 / instPrice
                    qEtf = 10000 / etfPrice
                    self.order(symbol, -(instStock[symbol][0]))
                    self.order(self.__etf, qEtf)
                    self.instInventory(symbol, 0, 0)
                    self.etfInventory(etfStock[etf] + qEtf)
                    inst_to_enter = [str(bars[symbol].getDateTime()), symbol, round(spread, 4), 'Sell', str(round(qInst, 2))]
                    etf_to_enter = [str(bars[etf].getDateTime()), etf, round(spread, 4), 'Buy', str(round(qEtf, 2))]
                    writer.writerow(inst_to_enter)
                    writer.writerow(etf_to_enter)
            else:
                pass
 
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

def main(plot):
    # Download the bars.
    feed = build_feed(instFeed, 2011, 2012)
    # Define Strategy
    myStrategy = MyStrategy(feed, etf)
    # Attach returns and sharpe ratio analyzers.
    returnsAnalyzer = returns.Returns()
    myStrategy.attachAnalyzer(returnsAnalyzer)
    sharpeRatioAnalyzer = sharpe.SharpeRatio()
    
    if plot:
        symbol = "FCX"
        enterSpreadDS = [-enterSpread]
        exitSpreadDS = [-exitSpread]
        #instPriceDS = dataseries.SequenceDataSeries(instPrices[symbol])
        naInstPriceDS = dataseries.SequenceDataSeries(naInstPrices[symbol])
        naEtfPriceDS = dataseries.SequenceDataSeries(naEtfPrices)
        #etfPriceDS = dataseries.SequenceDataSeries(etfPrices)
        spreadDS = dataseries.SequenceDataSeries(instSpread[symbol])
        returnDS = dataseries.SequenceDataSeries(marketValue[symbol])
        middleBandDS = dataseries.SequenceDataSeries(spreadMiddle[symbol])
        upperBandDS = dataseries.SequenceDataSeries(spreadUpper[symbol])
        lowerBandDS = dataseries.SequenceDataSeries(spreadLower[symbol])
        plt = plotter.StrategyPlotter(myStrategy, False, False, False)
        #plt.getOrCreateSubplot("priceChart").addDataSeries(symbol, instPriceDS)
        #plt.getOrCreateSubplot("priceChart").addDataSeries(etf, etfPriceDS)
        plt.getOrCreateSubplot("naPriceChart").addDataSeries(symbol, naInstPriceDS)
        plt.getOrCreateSubplot("naPriceChart").addDataSeries(etf, naEtfPriceDS)
        plt.getOrCreateSubplot("naPriceChart").addDataSeries("Spread", spreadDS)
        plt.getOrCreateSubplot("naPriceChart").addDataSeries("Middle", middleBandDS)
        plt.getOrCreateSubplot("naPriceChart").addDataSeries("Upper", upperBandDS)
        plt.getOrCreateSubplot("naPriceChart").addDataSeries("Lower", lowerBandDS)
        #plt.getOrCreateSubplot("naPriceChart").addDataSeries("Enter", enterSpreadDS)
        #plt.getOrCreateSubplot("naPriceChart").addDataSeries("Exit", exitSpreadDS)
        plt.getOrCreateSubplot("returns").addDataSeries(symbol + "-Return", returnDS)
        #plt.getOrCreateSubplot("returns").addDataSeries("Net return", returnsAnalyzer.getReturns())
        plt.getOrCreateSubplot("returns").addDataSeries("Cum. return", returnsAnalyzer.getCumulativeReturns())
    
    myStrategy.attachAnalyzer(sharpeRatioAnalyzer)
    # Run the strategy
    myStrategy.run()
    print "Final portfolio value: $%.2f" % myStrategy.getResult()
    print "Anual return: %.2f %%" % (returnsAnalyzer.getCumulativeReturns()[-1] * 100)
    print "Average daily return: %.2f %%" % (stats.mean(returnsAnalyzer.getReturns()) * 100)
    print "Std. dev. daily return: %.4f" % (stats.stddev(returnsAnalyzer.getReturns()))
    print "Sharpe ratio: %.2f" % (sharpeRatioAnalyzer.getSharpeRatio(0, 252))
    
    if plot:
        plt.plot()

if __name__ == "__main__":
    main(True)