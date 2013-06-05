from pyalgotrade.stratanalyzer import returns, trades, drawdown, sharpe
from pyalgotrade.tools import yahoofinance
from pyalgotrade.barfeed import yahoofeed
from pyalgotrade.utils import stats
from pyalgotrade import strategy, plotter, dataseries
from datetime import datetime
from numpy import mean, std
import os, csv
import correlationFinder
import statArbVars as v
from pyalgotrade.talibext import indicator


startYear = v.startYear
endYear = v.endYear
lookBack = v.lookBack
start = startYear - lookBack
end = endYear - lookBack
etf = v.etf
instrument_list = v.instrument_list
orders_file = v.orders_file
instruments = correlationFinder.highCorrs
print instruments
instFeed = [symbol for symbol in instruments]
instFeed.append(etf)
bbandPeriod = v.bbandPeriod
stopLoss = v.stopLoss
stop = v.stop

instPrices = {i:[] for i in instruments}
etfPrices = [] 
naInstPrices = {i:[] for i in instruments}                  # For plotting normalized price                                   
naEtfPrices = []                                            # For plotting normalized price
instSpread = {i:[] for i in instruments}                    # For plotting spread and Bollingers
instStock = {i:[0] for i in instruments}                    # [lastSpread]
etfStock = {i:[0] for i in instruments}                     # For correct order quantities
marketValue = {i:[0] for i in instruments}                  # Tracks cumulative gain
gain = {i:[0] for i in instruments}                         # Tracks net gain
bollingerBands = {i:[[],[],[], []] for i in instruments}
tradeGain = {i:[0, 0] for i in instruments}                 # [enteredSpread]
instMFI = {i:[] for i in instruments}                  # [[1-day],[MFR], [MFI]]
etfMFI = []                                            # [[1-day],[MFR], [MFI]]
spreadMFI = {i:[] for i in instruments}


class MyStrategy(strategy.Strategy):
    def __init__(self, feed, etf):
        strategy.Strategy.__init__(self, feed)
        self.getBroker().setUseAdjustedValues(True)
        self.__etf = etf
        
    def clearOrders(self, orders_file):
        orders_file = orders_file
        orders_file = open(orders_file, "w")
        orders_file.truncate()
        orders_file.close()
              
    def orderWriter(self, year, month, day, symbol, etf, spread, instType, etfType, qInst, qEtf, gainLog):
        writer = csv.writer(open(orders_file, 'ab'), delimiter = ',')
        inst_to_enter = [str(year), str(month), str(day), symbol, round(spread, 4), instType, qInst, gainLog]
        etf_to_enter = [str(year), str(month), str(day), etf, round(spread, 4), etfType, qEtf, gainLog]
        writer.writerow(inst_to_enter)
        writer.writerow(etf_to_enter)
        
    def instValue(self, symbol, enterSpread, spread):
        self.__symbol = symbol
        self.__enterSpread = enterSpread
        self.__spread = spread
        
        if self.getBroker().getShares(symbol) > 0:
            gain = ((spread - enterSpread) / enterSpread)
        elif self.getBroker().getShares(symbol) < 0:
            gain = ((enterSpread - spread) / enterSpread)
        else:
            gain = 0
        return gain
 
    def tGain(self, symbol, spread):
        self.__symbol = symbol
        self.__spread = spread
        if self.getBroker().getShares(symbol) > 0:
            return (spread - tradeGain[symbol][1]) / tradeGain[symbol][1]
        elif self.getBroker().getShares(symbol) < 0:
            return  (tradeGain[symbol][1] - spread) / tradeGain[symbol][1]
        else:
            return 0
        
    def enterBuyInst(self, symbol, instPrice, etfPrice, spread, qInst, qEtf):
        self.__symbol = symbol
        self.__instPrice = instPrice
        self.__etfPrice = etfPrice
        self.__spread = spread
        self.enterLong(symbol, qInst, True)
        self.enterShort(self.__etf, qEtf, True)
        instStock[symbol] = spread
        etfStock[symbol] = -qEtf
        
    def exitBuyInst(self, symbol, instShares, instPrice, etfPrice, spread, qInst, qEtf):
        self.__symbol = symbol
        self.__instShares = instShares
        self.__instPrice = instPrice
        self.__etfPRice = etfPrice
        self.__spread = spread
        self.enterShort(symbol, qInst, True)
        self.enterLong(self.__etf, qEtf, True)
        instStock[symbol] = spread
        etfStock[symbol] = 0
        
    def exitShortInst(self, symbol, instShares, instPrice, etfPrice, spread, qInst, qEtf):
        self.__symbol = symbol
        self.__instShares = instShares
        self.__instPrice = instPrice
        self.__etfPrice = etfPrice
        self.__spread = spread
        self.enterLong(symbol, qInst, True)
        self.enterShort(self.__etf, qEtf, True)
        instStock[symbol] = spread
        etfStock[symbol] = 0
        
    def enterShortInst(self, symbol, instPrice, etfPrice, spread, qInst, qEtf):
        self.__symbol = symbol
        self.__instPrice = instPrice
        self.__etfPRice = etfPrice
        self.__spread = spread
        self.enterShort(symbol, qInst, True)
        self.enterLong(self.__etf, qEtf, True)
        instStock[symbol] = spread
        etfStock[symbol] = qEtf

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
        etfPrice = bars[self.__etf].getAdjClose()
        etfPrices.append(etfPrice)
        #naEtfPrice = etfPrice / etfPrices[0]
        #naEtfPrices.append(naEtfPrice)
        ebarDs = self.getFeed().getDataSeries(etf)
        eMFI = indicator.MFI(ebarDs, 252, 14)
        etfMFI.append(eMFI[-1])
        
        for symbol in instruments:
            ibarDs = self.getFeed().getDataSeries(symbol)
            iMFI = indicator.MFI(ibarDs, 252, 14)
            instMFI[symbol].append(iMFI[-1])
            sMFI = (iMFI[-1] / eMFI[-1])
            spreadMFI[symbol].append(sMFI)
            # Get position status for symbol
            instShares = self.getBroker().getShares(symbol)
            # Get prices
            instPrice = bars[symbol].getAdjClose()
            # Append prices to list
            instPrices[symbol].append(instPrice)
            # Normalize pricespread
            #naInstPrice = instPrice / instPrices[symbol][0]
            #naInstPrices[symbol].append(naInstPrice)
            # Define Spread
            spread = instPrice / etfPrice
            #Update Market Value of Inventory
            instSpread[symbol].append(spread)                           # for plotting spread
            gain = self.instValue(symbol, instStock[symbol], spread)
            tGain = self.tGain(symbol, spread)
            instStock[symbol] = spread                                  # track last spread
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
                if stopLoss == True and tGain < stop:
                    print "stop"
                    if instShares > 0:
                        qInst = instShares
                        qEtf = abs(etfStock[symbol])
                        instType = "SELL"
                        etfType = "Buy"
                        gainLog = round(tGain, 4) * 100
                        self.exitBuyInst(symbol, instShares, instPrice, etfPrice, spread, qInst, qEtf)
                        self.orderWriter(bars[symbol].getDateTime().year, bars[symbol].getDateTime().month, bars[symbol].getDateTime().day, symbol, etf, spread, instType, etfType, qInst, qEtf, gainLog)
                    elif instShares < 0:
                        qInst = abs(instShares)
                        qEtf = etfStock[symbol]
                        instType = "BUY"
                        etfType = "SELL"
                        gainLog = round(tGain, 4) * 100
                        self.exitShortInst(symbol, instShares, instPrice, etfPrice, spread, qInst, qEtf)
                        self.orderWriter(bars[symbol].getDateTime().year, bars[symbol].getDateTime().month, bars[symbol].getDateTime().day, symbol, etf, spread, instType, etfType, qInst, qEtf, gainLog)
                else:
                    if instShares == 0:
                        if spread <= lower and sMFI > 1:     # Enter Long Inst
                            qInst = round((10000 / instPrice), 2)
                            qEtf = round((10000 / etfPrice), 2)
                            instType = "BUY"
                            etfType = "SELL"
                            gainLog = "N/A"
                            self.enterBuyInst(symbol, instPrice, etfPrice, spread, qInst, qEtf)
                            tradeGain[symbol][0] = 1
                            tradeGain[symbol][1] = spread
                            self.orderWriter(bars[symbol].getDateTime().year, bars[symbol].getDateTime().month, bars[symbol].getDateTime().day, symbol, etf, spread, instType, etfType, qInst, qEtf, gainLog)
                        elif spread >= upper and sMFI < 1:   # Enter Short Inst
                            qInst = round((10000 / instPrice), 2)
                            qEtf = round((10000 / etfPrice), 2)
                            instType = "SELL"
                            etfType = "Buy"
                            tradeGain[symbol][0] = -1
                            tradeGain[symbol][1] = spread
                            gainLog = round(tGain, 4) * 100
                            self.enterShortInst(symbol, instPrice, etfPrice, spread, qInst, qEtf)
                            self.orderWriter(bars[symbol].getDateTime().year, bars[symbol].getDateTime().month, bars[symbol].getDateTime().day, symbol, etf, spread, instType, etfType, qInst, qEtf, gainLog)
                        else:
                            pass
                    elif instShares > 0:        # Exit Long Inst
                        if spread >= middle:
                            qInst = instShares
                            qEtf = abs(etfStock[symbol])
                            instType = "SELL"
                            etfType = "Buy"
                            gainLog = round(tGain, 4) * 100
                            self.exitBuyInst(symbol, instShares, instPrice, etfPrice, spread, qInst, qEtf)
                            self.orderWriter(bars[symbol].getDateTime().year, bars[symbol].getDateTime().month, bars[symbol].getDateTime().day, symbol, etf, spread, instType, etfType, qInst, qEtf, gainLog)
                        else:
                            pass
                    elif instShares < 0:        # Exit Short Inst
                        if spread <= middle:
                            qInst = abs(instShares)
                            qEtf = etfStock[symbol]
                            instType = "BUY"
                            etfType = "SELL"
                            gainLog = round(tGain, 4) * 100
                            self.exitShortInst(symbol, instShares, instPrice, etfPrice, spread, qInst, qEtf)
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
        symbol = "CCL"
        #naInstPriceDS = dataseries.SequenceDataSeries(naInstPrices[symbol])
        #naEtfPriceDS = dataseries.SequenceDataSeries(naEtfPrices)
        spreadDS = dataseries.SequenceDataSeries(instSpread[symbol])
        returnDS = dataseries.SequenceDataSeries(marketValue[symbol])
        instMFIds = dataseries.SequenceDataSeries(instMFI[symbol])
        etfMFIds = dataseries.SequenceDataSeries(etfMFI)
        spreadMFIds = dataseries.SequenceDataSeries(spreadMFI[symbol])
        middleBandDS = dataseries.SequenceDataSeries(bollingerBands[symbol][1])
        upperBandDS = dataseries.SequenceDataSeries(bollingerBands[symbol][2])
        lowerBandDS = dataseries.SequenceDataSeries(bollingerBands[symbol][0])
        tenMADS = dataseries.SequenceDataSeries(bollingerBands[symbol][3])
        plt = plotter.StrategyPlotter(myStrategy, False, False, False)
        #plt.getOrCreateSubplot("naPriceChart").addDataSeries(symbol, naInstPriceDS)
        #plt.getOrCreateSubplot("naPriceChart").addDataSeries(etf, naEtfPriceDS)
        plt.getOrCreateSubplot("spread").addDataSeries(symbol + ":" + etf, spreadDS)
        plt.getOrCreateSubplot("spread").addDataSeries("Middle", middleBandDS)
        plt.getOrCreateSubplot("spread").addDataSeries("10 MA", tenMADS)
        plt.getOrCreateSubplot("spread").addDataSeries("Upper", upperBandDS)
        plt.getOrCreateSubplot("spread").addDataSeries("Lower", lowerBandDS)
        plt.getOrCreateSubplot("returns").addDataSeries(symbol + "-Return", returnDS)
        plt.getOrCreateSubplot("returns").addDataSeries("Cum. return", returnsAnalyzer.getCumulativeReturns())
        plt.getOrCreateSubplot("MFI").addDataSeries(symbol + ":" + etf + "-MFI", spreadMFIds)
        #plt.getOrCreateSubplot("MFI").addDataSeries(symbol + "-MFI", instMFIds)
        #plt.getOrCreateSubplot("MFI").addDataSeries(etf + "-MFI", etfMFIds)
        #plt.getOrCreateSubplot("MFI").addDataSeries("80", 80)
        #plt.getOrCreateSubplot("MFI").addDataSeries("20", 20)
        
        
    
    # Run the strategy
    print "Running Strategy..."
    myStrategy.clearOrders(orders_file)
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
    
