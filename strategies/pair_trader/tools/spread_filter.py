import pandas as pd

df = pd.read_csv('spread_db.csv',index_col=0)

results = []
dictionary = {}
cl_val = 0.95
hl_val = 50
pc_val = 0.8
for pair in df:
    cl =  float(df[pair]['Cointegration Level'])
    hl = float(df[pair]['Half-life'])
    pc = float(df[pair]['Pearson Correlation'])
    if cl >= cl_val and hl <= hl_val and pc >= pc_val:
        results.append(pair)

for pair in df[results]:
    string = pair.partition(':')  
    print string[0],string[2]
          
print df[results]
