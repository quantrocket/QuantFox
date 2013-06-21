"""
This will be used for testing pairs

Function                        Output
----------------------------------------------
Random Walk?                    True/False        DONE
Cointegration Level:            0-100%            DONE
Pearson Correlation (Price):    0-100%            DONE
Beta (each other):              Beta              FIX
Current Spread:                 Current Spread    DONE
Price-Ratio:                    Current Ratio     DONE
Average Price Ratio:            Average Ratio     DONE
Beta 1                          Beta              DONE
Beta 2                          Beta              DONE
Spread Mean:                    Spread Mean       DONE
Spread Median:                  Spread Maximum    DONE
Spread Maximum:                 Spread Maximum    DONE 
Spread Minimum:                 Spread Minimum    DONE
Half-life:                      Half-life         DONE
Current z-score                 Current z-score
"""

import pandas as pd
from math import ceil
from vratio import vratio
import numpy as np
from scipy.stats import pearsonr, beta
from urllib import urlopen
import statsmodels.api as sm
import statsmodels.tsa.stattools as ts

results = {'Random Walk I[1]':[],'Random Walk I[2]':[],'Cointegration Level':[],'Pearson Correlation':[],
       'Beta':[],'Current Spread':[],'Price-Ratio':[],'Average Price-Ratio':[],
       'Beta 1':[],'Beta 2':[],'Spread Mean':[],'Spread Median':[],
       'Spread Maximum':[],'Spread Minimum':[],'Half-life':[],'Current zscore':[]}

def run(sym1,sym2,t):
    index = '^GSPC'
    df = get_data(sym1,sym2,t)
    index = get_index(index,t)
    cointegration(df,index,sym1,sym2)
    
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
def get_index(index,t):
    t = int(t*250)
    index = data_handler(index,t)
    return index
def cointegration(df,index,sym1,sym2):
    # Arrange data
    sym_array = df.values
    index_array = index.values
    sym1 = np.array([])
    sym1_returns = np.array([])
    sym2 = np.array([])
    sym2_returns = np.array([])
    index = np.array([])
    index_returns = np.array([])
    y = len(sym_array)
    for x in range(y):
        sym1 = np.append(sym1, sym_array[x][0])
        sym2 = np.append(sym2, sym_array[x][1])
        index = np.append(index, index_array[x])
    for x in range(y-1):
        return1 = (sym1[x+1] / sym1[x])-1
        sym1_returns = np.append(sym1_returns, return1)
        return2 = (sym2[x+1] / sym2[x])-1
        sym2_returns = np.append(sym2_returns, return2)
        returnI = (index[x+1] / index[x])-1
        index_returns = np.append(index_returns, returnI)
    
    print 'Testing Random Walk Hypothesis...'
    v1 = vratio(sym1, cor = 'het')
    v2 = vratio(sym1, cor = 'het')
    if v1[2] < 0.05:
        result1 = False
    else:
        result1 = True
    if v2[2] < 0.05:
        result2 = False
    else:
        result2 = True
    results['Random Walk I[1]'].append(result1)
    results['Random Walk I[2]'].append(result2)

    print 'Calculating cointegration...'    
    # Step 1: regress one variable on the other
    ols_result = sm.OLS(sym1,sym2).fit()
    # Step 2: obtain the residual (ols_resuld.resid)
    # Step 3: apply Augmented Dickey-Fuller test to see whether 
    # the residual is unit root    
    result = ts.adfuller(ols_result.resid)
    pvalue = round(1-result[1],4)*100
    results['Cointegration Level'].append(str(pvalue)+'%')
    
    print 'Calculating Pearson Correlation...'
    r = round(pearsonr(sym1,sym2)[0],4)*100
    results['Pearson Correlation'].append(str(r)+'%')
    
    print 'Calculating Beta...'
    beta = np.around(np.cov(sym2_returns,sym1_returns)[0,1] / np.var(sym2_returns), decimals = 2)
    results['Beta'].append(beta)
    
    print 'Calculating Current Spread'
    spread = round((sym1[0]-sym2[0]),4)
    results['Current Spread'].append(spread)
    
    print 'Calculating Current Price-Ratio...'
    ratio = round((sym1[0]/sym2[0]),2)
    results['Price-Ratio'].append(ratio)
    
    print 'Calculating Average Price-Ratio...'
    array = sym1 / sym2
    ratio = round(np.mean(array),2)
    results['Average Price-Ratio'].append(ratio)
    
    print 'Calculating Spread Mean...'
    array = sym1 - sym2
    mean = round(np.mean(array),2)
    results['Spread Mean'].append(mean)
    
    print 'Calculating Spread Median...'
    array = sym1 - sym2
    median = round(np.median(array),2)
    results['Spread Median'].append(median)
    
    print 'Calculating Spread Maximum...'
    array = sym1 - sym2
    max = round(np.max(array),2)
    results['Spread Maximum'].append(max)
    
    print 'Calculating Spread Minimum...'
    array = sym1 - sym2
    min = round(np.min(array),2)
    results['Spread Minimum'].append(min)
    
    print 'Calculating Beta 1...'
    beta = np.around(np.cov(sym1_returns,index_returns)[0,1] / np.var(index_returns), decimals = 2)
    results['Beta 1'].append(beta)

    print 'Calculating Beta 2...'
    beta = np.around(np.cov(sym2_returns,index_returns)[0,1] / np.var(index_returns), decimals = 2)
    results['Beta 2'].append(beta)
    
    print 'Calculating Half-life...'
    array = sym1 - sym2
    x = np.subtract(array[1:],array[:-1])
    y = array[:-1]
    k = np.polyfit(y,x,1)
    half_life = ceil(-np.log(2)/k[0])
    results['Half-life'].append(half_life)
    
                                          
                                          
    
    return result


print run('JOY','CAT',1)

