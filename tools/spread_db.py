import spread_analyzer
import pandas as pd
import csv
import itertools

symReader = csv.reader(open('sp500_financials.csv', "rb"), delimiter = ",")
sym_list = [symbol for line in symReader for symbol in line]
#sym_list = ['GOOG','IBM','AAPL']
pairs = []
end_years_back = 1
start_years_back = 1
log = []
perms = []
use_etf = False
etf = 'XLF'


def all_perms():
    for sym in sym_list:
        pairs.append([sym,'XLF'])
            
 
def all_pairs(lst):
    a = sym_list
    b = sym_list
    c = list(itertools.product(a, b))
    
    idx = c.index((sym_list[0],sym_list[0]))
    return c
        
print 'Generating Pairs...'
if use_etf == True:
    pairs = all_perms()
else:
    pairs = all_pairs(sym_list)
print pairs


results = {'Pair':{'Random Walk I[1]':0,'Random Walk I[2]':0,'Cointegration Level':0,
          'Pearson Correlation':0,'Beta':0,'Current Spread':0,'Price-Ratio':0,
          'Average Price-Ratio':0,'Beta 1':0,'Beta 2':0,'Spread Mean':0,
          'Spread Median':0,'Spread Maximum':0,'Spread Minimum':0,
          'Half-life':0,'Current z-score':0}}

results = pd.DataFrame(results)
                       
for p in pairs:
    sym1 = p[0]
    sym2 = p[1]
    if sym1 != sym2:
        print sym1,':',sym2
        try:
            df = spread_analyzer.run(sym1,sym2,end_years_back,start_years_back)
            results = results.join(df)
        except:
            pass
    
del results['Pair']
results = results.reindex(index=['Random Walk I[1]','Random Walk I[2]','Cointegration Level',
                           'Pearson Correlation','Beta','Current Spread','Price-Ratio',
                           'Average Price-Ratio','Beta 1','Beta 2','Spread Mean',
                           'Spread Median','Spread Maximum','Spread Minimum',
                           'Half-life','Current z-score'])
results.to_csv('spread_db_financials.csv')
print results