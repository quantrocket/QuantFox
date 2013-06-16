import itertools
from pyalgotrade.barfeed import yahoofeed
from pyalgotrade.optimizer import server

def parameters_generator():
    entrySMA = range(150, 251)
    exitSMA = range(5, 16)
    rsiPeriod = range(2, 11)
    overBoughtThreshold = range(75, 96)
    overSoldThreshold = range(5, 26)
    return itertools.product(entrySMA, exitSMA, rsiPeriod, overBoughtThreshold, overSoldThreshold)

# The if __name__ == '__main__' part is necessary if running on Windows.
if __name__ == '__main__':
    # Load the feed from the CSV files.
    feed = yahoofeed.Feed()
    feed.addBarsFromCSV("COP", "COP-2011.csv")
    feed.addBarsFromCSV("COP", "COP-2012.csv")

    # Run the server.
    server.serve(feed, parameters_generator(), "localhost", 5000)