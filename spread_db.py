import spread_analyzer
import pandas as pd

sym_list = ['GOOG','EOG','AAPL','IBM']
pairs = []
end_years_back = 1
start_years_back = 1
log = []

def all_pairs(sym_list):
    if len(sym_list) < 2:
        yield sym_list
        return
    a = sym_list[0]
    for i in range(1,len(sym_list)):
        pair = (a,sym_list[i])
        for rest in all_pairs(sym_list[1:i]+sym_list[i+1:]):
            yield [pair] + rest

for x in all_pairs(sym_list):
    for y in x:
        pairs.append(y)
        
print pairs

results = {'Pair':{'Random Walk I[1]':[],'Random Walk I[2]':[],'Cointegration Level':[],
          'Pearson Correlation':[],'Beta':[],'Current Spread':[],'Price-Ratio':[],
          'Average Price-Ratio':[],'Beta 1':[],'Beta 2':[],'Spread Mean':[],
          'Spread Median':[],'Spread Maximum':[],'Spread Minimum':[],
          'Half-life':[],'Current z-score':[]}}

results = pd.DataFrame(results)
                       
for p in pairs:
    sym1 = p[0]
    sym2 = p[1]
    df = spread_analyzer.run(sym1,sym2,end_years_back,start_years_back)
    results = results.join(df)
del results['Pair']
results = results.reindex(index=['Random Walk I[1]','Random Walk I[2]','Cointegration Level',
                           'Pearson Correlation','Beta','Current Spread','Price-Ratio',
                           'Average Price-Ratio','Beta 1','Beta 2','Spread Mean',
                           'Spread Median','Spread Maximum','Spread Minimum',
                           'Half-life','Current z-score'])
results.to_csv('spread_db.csv')
print results