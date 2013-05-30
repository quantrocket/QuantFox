from pyalgotrade.stratanalyzer import returns, trades, drawdown, sharpe
from pyalgotrade.tools import yahoofinance
from pyalgotrade.barfeed import yahoofeed
from pyalgotrade.utils import stats
from pyalgotrade import dataseries
from pyalgotrade import strategy
from pyalgotrade import plotter
from numpy import mean, std
import os
import csv

etf = 'XLB'
instrument_list = 'ConsumerDiscretionary.csv'
orders_file = 'orders.csv'
orders_file = open(orders_file, "w")
orders_file.truncate()
orders_file.close()
instReader = csv.reader(open(instrument_list, "rb"), delimiter = ",")
instruments = [symbol for line in instReader for symbol in line]
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
marketValue = {i:[20000] for i in instruments}
gain = {i:[0] for i in instruments}

enterSpread = 0.05
exitSpread = 0.03

stopLoss = False
stop = -.10

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

    def etfInventory(self, symbol, qEtf):
        self.__symbol = symbol
        self.__qEtf = qEtf
        etfStock[symbol] = qEtf
        
    def instValue(self, symbol, enterSpread, spread):
        self.__symbol = symbol
        self.__enterSpread = enterSpread
        self.__spread = spread
        gain = (spread - enterSpread) * 0.5
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
    def tenMA(self, symbol):
        self.__symbol = symbol
        tenMA = mean(instSpread[symbol][-10:])
        return tenMA
    
    
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
            if len(instSpread[symbol]) >= 30:
                middle = self.middleBand(symbol)
                upper = self.upperBand(symbol)
                lower = self.lowerBand(symbol)
                tenMA = self.tenMA(symbol)
                bollingerBands[symbol][1].append(middle)
                bollingerBands[symbol][2].append(upper)
                bollingerBands[symbol][0].append(lower)
                bollingerBands[symbol][3].append(tenMA)
            else:
                lower = 0
                middle = 0
                upper = 0
                tenMA = 0
                bollingerBands[symbol][1].append(0)
                bollingerBands[symbol][2].append(0)
                bollingerBands[symbol][0].append(0)
                bollingerBands[symbol][3].append(tenMA)
                
            # Update Market Value of Inventory
            if instStock[symbol][0] > 0:
                gain = self.instValue(symbol, instStock[symbol][1], spread)
                instStock[symbol][2] = gain
                marketValue[symbol].append(instStock[symbol][2])
            else:
                #gain = 0
                marketValue[symbol].append(instStock[symbol][2])
            # Define trade rules
            if spread <= lower and lower != 0 and instStock[symbol][0] == 0 and notional < 1000000:
                    qInst = round((10000 / instPrice), 2)
                    qEtf = round((10000 / etfPrice), 2)
                    self.order(symbol, qInst)
                    self.order(self.__etf, -qEtf)
                    self.instInventory(symbol, qInst, spread)
                    self.etfInventory(symbol, -qEtf)
                    inst_to_enter = [str(bars[symbol].getDateTime().year), str(bars[symbol].getDateTime().month), str(bars[symbol].getDateTime().day), symbol, round(spread, 4), 'Buy', str(qInst)]
                    etf_to_enter = [str(bars[symbol].getDateTime().year), str(bars[symbol].getDateTime().month), str(bars[symbol].getDateTime().day), etf, round(spread, 4), 'Sell', str(qEtf)]
                    writer.writerow(inst_to_enter)
                    writer.writerow(etf_to_enter)
            elif ((spread >= upper and upper != 0) or (stopLoss == True and 1 < 2)) and instStock[symbol][0] > 0 and notional > 0:
                    qInst = instStock[symbol][0]
                    qEtf = etfStock[symbol]
                    self.order(symbol, -(qInst))
                    self.order(self.__etf, qEtf)
                    self.instInventory(symbol, 0, 0)
                    self.etfInventory(symbol, 0)
                    inst_to_enter = [str(bars[symbol].getDateTime().year), str(bars[symbol].getDateTime().month), str(bars[symbol].getDateTime().day), symbol, round(spread, 4), 'Sell', str(qInst), str(round(gain, 2))]
                    etf_to_enter = [str(bars[symbol].getDateTime().year), str(bars[symbol].getDateTime().month), str(bars[symbol].getDateTime().day), etf, round(spread, 4), 'Buy', str(-qEtf)]
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
    tradesAnalyzer = trades.Trades()
    myStrategy.attachAnalyzer(tradesAnalyzer)
    drawDownAnalyzer = drawdown.DrawDown()
    myStrategy.attachAnalyzer(drawDownAnalyzer)
    
    if plot:
        symbol = "DIS"
        #instPriceDS = dataseries.SequenceDataSeries(instPrices[symbol])
        naInstPriceDS = dataseries.SequenceDataSeries(naInstPrices[symbol])
        naEtfPriceDS = dataseries.SequenceDataSeries(naEtfPrices)
        #etfPriceDS = dataseries.SequenceDataSeries(etfPrices)
        spreadDS = dataseries.SequenceDataSeries(instSpread[symbol])
        returnDS = dataseries.SequenceDataSeries(marketValue[symbol])
        middleBandDS = dataseries.SequenceDataSeries(bollingerBands[symbol][1])
        upperBandDS = dataseries.SequenceDataSeries(bollingerBands[symbol][2])
        lowerBandDS = dataseries.SequenceDataSeries(bollingerBands[symbol][0])
        tenMADS = dataseries.SequenceDataSeries(bollingerBands[symbol][3])
        plt = plotter.StrategyPlotter(myStrategy, False, False, False)
        #plt.getOrCreateSubplot("priceChart").addDataSeries(symbol, instPriceDS)
        #plt.getOrCreateSubplot("priceChart").addDataSeries(etf, etfPriceDS)
        plt.getOrCreateSubplot("naPriceChart").addDataSeries(symbol, naInstPriceDS)
        plt.getOrCreateSubplot("naPriceChart").addDataSeries(etf, naEtfPriceDS)
        plt.getOrCreateSubplot("spread").addDataSeries("Spread", spreadDS)
        plt.getOrCreateSubplot("spread").addDataSeries("Middle", middleBandDS)
        plt.getOrCreateSubplot("spread").addDataSeries("10 MA", tenMADS)
        plt.getOrCreateSubplot("spread").addDataSeries("Upper", upperBandDS)
        plt.getOrCreateSubplot("spread").addDataSeries("Lower", lowerBandDS)
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
            plt.plot()

if __name__ == "__main__":
    main(True)