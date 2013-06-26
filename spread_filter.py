import pandas as pd

df = pd.read_csv('spread_db.csv',index_col=0)

results = []


for pair in df:
    cl =  float(df[pair]['Cointegration Level'])
    hl = float(df[pair]['Half-life'])
    pc = float(df[pair]['Pearson Correlation'])
    if cl > 0.95 and hl <=14 and pc >= 0.8:
        results.append(pair)
        
print df[results]
"""
for pair in df:
    cl = df[pair][3]
    cl = float(cl)
    print cl
    hl = df[pair][[14]]
    if cl > 200:
        results.append(pair)
"""
#print results
        