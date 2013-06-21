"""
This will be used for testing pairs

Function                        Output
------------------------------------------
Random Walk?                    True/False
Cointegration Level:            0-100%            DONE
Pearson Correlation (Price):    0-100%
Beta (each other):              Beta
Current Spread:                 Current Spread
Price-Ratio:                    Current Ratio
Average Price Ratio:            Average Ratio
Beta 1                          Beta
Beta 2                          Beta
Spread Mean:                    Spread Mean
Spread Median:                  Spread Maximum
Spread Maximum:                 Spread Maximum
Spread Minimum:                 Spread Minimum
Half-life:                      Half-life
Current z-score                 Current z-score
"""

import pandas as pd
from urllib import urlopen
import statsmodels.api as sm
import statsmodels.tsa.stattools as ts

results = {'Random Walk':[],'Cointegration Level':[],'Pearson Correlation':[],
       'Beta':[],'Current Spread':[],'Price-Ratio':[],'Average Price-Ratio':[],
       'Beta 1':[],'Beta 2':[],'Spread Mean':[],'Spread Median':[],
       'Spread Maximum':[],'Spread Minimum':[],'Half-life':[],'Current zscore':[]}

def run(sym1,sym2,t):
    

    
    df = get_data(sym1,sym2,t)
    cointegration(df,sym1,sym2)
    
    #sresults = pd.DataFrame(results)
    print results
    
    
def make_url(symbol):
    base_url = "http://ichart.finance.yahoo.com/table.csv?s="
    return base_url + symbol
def data_handler(sym,t):
    url = make_url(sym)
    page = urlopen(url)
    df = pd.read_csv(page)['Adj Close'][:t]
    df = pd.DataFrame({sym:df})
    return df
def get_data(sym1,sym2,t):
    print 'Getting data...'
    t = int(t*250)
    df1 = data_handler(sym1,t)
    df2 = data_handler(sym2,t)
    df = pd.concat((df1,df2),axis=1)
    return df

def cointegration(df,sym1,sym2):
    print 'Calculating cointegration...'
    sym1_array = df.values
    sym2_array = df.values
    sym1 = []
    sym2 = []
    y = len(sym1_array)
    for x in range(y):
        sym1.append(sym1_array[x][0])
        sym2.append(sym1_array[x][1])
    # Step 1: regress one variable on the other
    ols_result = sm.OLS(sym1,sym2).fit()
    # Step 2: obtain the residual (ols_resuld.resid)
    # Step 3: apply Augmented Dickey-Fuller test to see whether 
    # the residual is unit root    
    result = ts.adfuller(ols_result.resid)
    pvalue = round(1-result[1],4)*100
    results['Cointegration Level'].append(str(pvalue)+'%')
    return result


print run('CH','ECH',1)

