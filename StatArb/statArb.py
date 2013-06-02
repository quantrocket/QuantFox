from pyalgotrade.stratanalyzer import returns, trades, drawdown, sharpe
from pyalgotrade.tools import yahoofinance
from pyalgotrade.barfeed import yahoofeed
from pyalgotrade.utils import stats
from pyalgotrade import dataseries
from pyalgotrade import strategy
from pyalgotrade import plotter
from datetime import datetime

from numpy import mean, std
import os
import csv
import correlationFinder

startYear = 2011
endYear = 2012
lookBack = 2
start = startYear - lookBack

etf = 'XLB'
instruments = correlationFinder.highCorrs
orders_file = 'orders.csv'
orders_file = open(orders_file, "w")
orders_file.truncate()
orders_file.close()
print instruments
instFeed = [symbol for symbol in instruments]
instFeed.append(etf)
instPrices = {i:[] for i in instruments}
naInstPrices = {i:[] for i in instruments}
instSpread = {i:[] for i in instruments}
instStock = {i:[0, 0, 0] for i in instruments} # [Shares, EnteredSpread, MarketValue]
etfStock = {i:[0] for i in instruments}
etfPrices = []
naEtfPrices = []
bollingerBands = {i:[[],[],[], []] for i in instruments}
marketValue = {i:[0] for i in instruments}
gain = {i:[0] for i in instruments}

bbandPeriod = 20

stopLoss = False
stop = -.10

class MyStrategy(strategy.Strategy):
    def __init__(self, feed, etf):
        strategy.Strategy.__init__(self, feed)
        self.getBroker().setUseAdjustedValues(True)
        self.__etf = etf
              
    def orderWriter(self, year, month, day, symbol, etf, spread, instType, etfType, qInst, qEtf, gainLog):
        writer = csv.writer(open('orders.csv', 'ab'), delimiter = ',')
        inst_to_enter = [str(year), str(month), str(day), symbol, round(spread, 4), instType, qInst, gainLog]
        etf_to_enter = [str(year), str(month), str(day), etf, round(spread, 4), etfType, qEtf, gainLog]
        writer.writerow(inst_to_enter)
        writer.writerow(etf_to_enter)
        
    def instValue(self, symbol, enterSpread, spread):
        self.__symbol = symbol
        self.__enterSpread = enterSpread
        self.__spread = spread
        
        if self.getBroker().getShares(symbol) > 0:
            gain = (spread - enterSpread) * 0.5
        elif self.getBroker().getShares(symbol) < 0:
            gain = (enterSpread - spread) * 0.5
        else:
            gain = 0
        return gain
         
    def middleBand(self, symbol):
        self.__symbol = symbol
        if len(instSpread[symbol]) >= bbandPeriod:
            middle = mean(instSpread[symbol][-bbandPeriod:])
        else:
            middle = 0
        return middle
    def upperBand(self, symbol):
        self.__symbol = symbol
        if len(instSpread[symbol]) >= bbandPeriod:
            upper = self.middleBand(symbol) + (std(instSpread[symbol][-bbandPeriod:]) * 2)
        else:
            upper = 0
        return upper
    def lowerBand(self, symbol):
        self.__symbol = symbol
        if len(instSpread[symbol]) >= bbandPeriod:
            lower = self.middleBand(symbol) - (std(instSpread[symbol][-bbandPeriod:]) * 2)
        else:
            lower = 0
        return lower

    def tenMA(self, symbol):
        self.__symbol = symbol
        if len(instSpread[symbol]) >= 10:
            tenMA = mean(instSpread[symbol][-10:])
        else:
            tenMA = 0
        return tenMA
        
    def bollingerBands(self, symbol):
        self.__symbol = symbol
        if len(instSpread[symbol]) >= bbandPeriod:
            middle = self.middleBand(symbol)
            upper = self.upperBand(symbol)
            lower = self.lowerBand(symbol)
            tenMA = self.tenMA(symbol)
            bollingerBands[symbol][1].append(middle)
            bollingerBands[symbol][2].append(upper)
            bollingerBands[symbol][0].append(lower)
            bollingerBands[symbol][3].append(tenMA)
            return middle, lower, upper
        else:
            lower = 0
            middle = 0
            upper = 0
            tenMA = 0
            bollingerBands[symbol][1].append(0)
            bollingerBands[symbol][2].append(0)
            bollingerBands[symbol][0].append(0)
            bollingerBands[symbol][3].append(tenMA)
            return middle, lower, upper
    
    
    def onBars(self, bars):
        for symbol in instruments:
            # Get position status for symbol
            instShares = self.getBroker().getShares(symbol)
            # Define shares | get prices
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
            notional = (instShares * instPrice) * 2
            spread = instPrice / etfPrice
            #Update Market Value of Inventory
            instSpread[symbol].append(spread)   # for plotting spread
            gain = self.instValue(symbol, instStock[symbol][1], spread)
            instStock[symbol][1] = spread   # track last spread
            marketValue[symbol].append(marketValue[symbol][-1] + gain)
            middle = self.middleBand(symbol)
            upper = self.upperBand(symbol)
            lower = self.lowerBand(symbol)
            tenMA = self.tenMA(symbol)
            bollingerBands[symbol][0].append(lower)
            bollingerBands[symbol][1].append(middle)
            bollingerBands[symbol][2].append(upper)
            bollingerBands[symbol][3].append(tenMA)

            # Define trade rules
            if bars[symbol].getDateTime().year >= startYear:
                if spread <= lower:
                    if instShares == 0:
                        qInst = round((10000 / instPrice), 2)
                        qEtf = round((10000 / etfPrice), 2)
                        instType = "BUY"
                        etfType = "SELL"
                        gainLog = "N/A"
                        self.enterLong(symbol, qInst, True)
                        self.enterShort(self.__etf, qEtf, True)
                        instStock[symbol][1] = spread
                        etfStock[symbol] = -qEtf
                        self.orderWriter(bars[symbol].getDateTime().year, bars[symbol].getDateTime().month, bars[symbol].getDateTime().day, symbol, etf, spread, instType, etfType, qInst, qEtf, gainLog)
                    elif instShares < 0:
                        qInst = abs(instShares) #round((10000 / instPrice), 2)
                        qEtf = etfStock[symbol] #round((10000 / etfPrice), 2)
                        instType = "BUY"
                        etfType = "SELL"
                        gainLog = "N/A"
                        self.enterLong(symbol, qInst, True)
                        self.enterShort(self.__etf, qEtf, True)
                        instStock[symbol][1] = spread
                        etfStock[symbol] = 0
                        self.orderWriter(bars[symbol].getDateTime().year, bars[symbol].getDateTime().month, bars[symbol].getDateTime().day, symbol, etf, spread, instType, etfType, qInst, qEtf, gainLog)
                        
                #elif spread >= upper and notional > 0:
                elif spread >= upper:
                    if instShares > 0:
                        qInst = instShares #round((10000 / instPrice), 2) + instShares
                        qEtf = abs(etfStock[symbol]) #round((10000 / etfPrice), 2) + abs(etfShares)
                        instType = "SELL"
                        etfType = "Buy"
                        gainLog = gain
                        self.enterShort(symbol, qInst, True)
                        self.enterLong(self.__etf, qEtf, True)
                        instStock[symbol][1] = spread
                        etfStock[symbol] = 0
                        self.orderWriter(bars[symbol].getDateTime().year, bars[symbol].getDateTime().month, bars[symbol].getDateTime().day, symbol, etf, spread, instType, etfType, qInst, qEtf, 0)
                    elif instShares == 0:
                        qInst = round((10000 / instPrice), 2)
                        qEtf = round((10000 / etfPrice), 2)
                        instType = "SELL"
                        etfType = "BUY"
                        gainLog = "N/A"
                        self.enterShort(symbol, qInst, True)
                        self.enterLong(self.__etf, qEtf, True)
                        instStock[symbol][1] = spread
                        etfStock[symbol] = qEtf
                        self.orderWriter(bars[symbol].getDateTime().year, bars[symbol].getDateTime().month, bars[symbol].getDateTime().day, symbol, etf, spread, instType, etfType, qInst, qEtf, gainLog)
                    else:
                        pass
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
    feed = build_feed(instFeed, start, endYear)
    # Define Strategy
    myStrategy = MyStrategy(feed, etf)
    # Attach returns and sharpe ratio analyzers.
    returnsAnalyzer = returns.Returns()
    myStrategy.attachAnalyzer(returnsAnalyzer)
    sharpeRatioAnalyzer = sharpe.SharpeRatio()
    myStrategy.attachAnalyzer(sharpeRatioAnalyzer)
    tradesAnalyzer = trades.Trades()
    myStrategy.attachAnalyzer(tradesAnalyzer)
    drawDownAnalyzer = drawdown.DrawDown()
    myStrategy.attachAnalyzer(drawDownAnalyzer)
    
    if plot:
        symbol = "TIF"
        naInstPriceDS = dataseries.SequenceDataSeries(naInstPrices[symbol])
        naEtfPriceDS = dataseries.SequenceDataSeries(naEtfPrices)
        spreadDS = dataseries.SequenceDataSeries(instSpread[symbol])
        returnDS = dataseries.SequenceDataSeries(marketValue[symbol])
        middleBandDS = dataseries.SequenceDataSeries(bollingerBands[symbol][1])
        upperBandDS = dataseries.SequenceDataSeries(bollingerBands[symbol][2])
        lowerBandDS = dataseries.SequenceDataSeries(bollingerBands[symbol][0])
        tenMADS = dataseries.SequenceDataSeries(bollingerBands[symbol][3])
        plt = plotter.StrategyPlotter(myStrategy, False, False, False)
        plt.getOrCreateSubplot("naPriceChart").addDataSeries(symbol, naInstPriceDS)
        plt.getOrCreateSubplot("naPriceChart").addDataSeries(etf, naEtfPriceDS)
        plt.getOrCreateSubplot("spread").addDataSeries(symbol + ":" + etf, spreadDS)
        plt.getOrCreateSubplot("spread").addDataSeries("Middle", middleBandDS)
        plt.getOrCreateSubplot("spread").addDataSeries("10 MA", tenMADS)
        plt.getOrCreateSubplot("spread").addDataSeries("Upper", upperBandDS)
        plt.getOrCreateSubplot("spread").addDataSeries("Lower", lowerBandDS)
        plt.getOrCreateSubplot("returns").addDataSeries(symbol + "-Return", returnDS)
        plt.getOrCreateSubplot("returns").addDataSeries("Cum. return", returnsAnalyzer.getCumulativeReturns())
    
    # Run the strategy
    print "Running Strategy..."
    myStrategy.run()
    
    print "Final portfolio value: $%.2f" % myStrategy.getResult()
    print "Anual return: %.2f %%" % (returnsAnalyzer.getCumulativeReturns()[-1] * 100)
    print "Average daily return: %.2f %%" % (stats.mean(returnsAnalyzer.getReturns()) * 100)
    print "Std. dev. daily return: %.4f" % (stats.stddev(returnsAnalyzer.getReturns()))
    print "Sharpe ratio: %.2f" % (sharpeRatioAnalyzer.getSharpeRatio(0, 252))
    print
    print "Total trades: %d" % (tradesAnalyzer.getCount())
    if tradesAnalyzer.getCount() > 0:
        profits = tradesAnalyzer.getAll()
        print "Avg. profit: $%2.f" % (profits.mean())
        print "Profits std. dev.: $%2.f" % (profits.std())
        print "Max. profit: $%2.f" % (profits.max())
        print "Min. profit: $%2.f" % (profits.min())
        returnz = tradesAnalyzer.getAllReturns()
        print "Avg. return: %2.f %%" % (returnz.mean() * 100)
        print "Returns std. dev.: %2.f %%" % (returnz.std() * 100)
        print "Max. return: %2.f %%" % (returnz.max() * 100)
        print "Min. return: %2.f %%" % (returnz.min() * 100)
    print
    print "Profitable trades: %d" % (tradesAnalyzer.getProfitableCount())
    if tradesAnalyzer.getProfitableCount() > 0:
        profits = tradesAnalyzer.getProfits()
        print "Avg. profit: $%2.f" % (profits.mean())
        print "Profits std. dev.: $%2.f" % (profits.std())
        print "Max. profit: $%2.f" % (profits.max())
        print "Min. profit: $%2.f" % (profits.min())
        returnz = tradesAnalyzer.getPositiveReturns()
        print "Avg. return: %2.f %%" % (returnz.mean() * 100)
        print "Returns std. dev.: %2.f %%" % (returnz.std() * 100)
        print "Max. return: %2.f %%" % (returnz.max() * 100)
        print "Min. return: %2.f %%" % (returnz.min() * 100)
    print
    print "Unprofitable trades: %d" % (tradesAnalyzer.getUnprofitableCount())
    if tradesAnalyzer.getUnprofitableCount() > 0:
        losses = tradesAnalyzer.getLosses()
        print "Avg. loss: $%2.f" % (losses.mean())
        print "Losses std. dev.: $%2.f" % (losses.std())
        print "Max. loss: $%2.f" % (losses.min())
        print "Min. loss: $%2.f" % (losses.max())
        returnz = tradesAnalyzer.getNegativeReturns()
        print "Avg. return: %2.f %%" % (returnz.mean() * 100)
        print "Returns std. dev.: %2.f %%" % (returnz.std() * 100)
        print "Max. return: %2.f %%" % (returnz.max() * 100)
        print "Min. return: %2.f %%" % (returnz.min() * 100)
    print
    for symbol in instruments:
        print str(symbol)+ ": " + str(round(marketValue[symbol][-1], 4) * 100) + "%"
    
    if plot:
            plt.plot(datetime.strptime('01/01/' + str(startYear), '%m/%d/%Y'))

if __name__ == "__main__":
    main(True)
    
orders_file.close()