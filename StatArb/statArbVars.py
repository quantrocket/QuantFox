startYear = 2011
endYear = 2012
lookBack = 2
starting_cash = 430000


instrument_list = 'pairs.csv'
orders_file = 'orders.csv'
etf_list = ["XLY", "XLP", "XLE", "XLI", "XLF", "XLV", "XLB", "XLK", "XLU"]


bbandPeriod = 20
stopLoss = False
stop = -0.2


execfile("statArb.py")



