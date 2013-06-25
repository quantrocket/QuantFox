"""
This will be used for testing pairs

Function                        Output            Status
--------------------------------------------------------
Random Walk?                    True/False         DONE
Cointegration Level:            0-100%             CHECK
Pearson Correlation (Price):    0-100%             DONE
Beta (each other):              Beta               FIX
Current Spread:                 Current Spread     DONE
Price-Ratio:                    Current Ratio      DONE
Average Price Ratio:            Average Ratio      DONE
Beta 1                          Beta               DONE
Beta 2                          Beta               DONE
Spread Mean:                    Spread Mean        DONE
Spread Median:                  Spread Maximum     DONE
Spread Maximum:                 Spread Maximum     DONE 
Spread Minimum:                 Spread Minimum     DONE
Half-life:                      Half-life          CHECK
Current z-score                 Current z-score    CHECK
"""

import pandas as pd
from math import ceil
from vratio import vratio
import numpy as np
from scipy.stats import pearsonr, beta, zscore
from urllib import urlopen
import statsmodels.api as sm
import statsmodels.tsa.stattools as ts

results = {'Results':{'Random Walk I[1]':[],'Random Walk I[2]':[],'Cointegration Level':[],
                      'Pearson Correlation':[],'Beta':[],'Current Spread':[],'Price-Ratio':[],
                      'Average Price-Ratio':[],'Beta 1':[],'Beta 2':[],'Spread Mean':[],
                      'Spread Median':[],'Spread Maximum':[],'Spread Minimum':[],
                      'Half-life':[],'Current z-score':[]}}

def run(*args):
    print ""
    sym1 = raw_input("Leg 1: ")
    sym2 = raw_input("Leg 2: ")
    e = float(raw_input("End Years Back: "))
    t = float(raw_input("Start Years Back: "))
    print ""
    index = '^GSPC'
    df = get_data(sym1,sym2,t,e)
    index = get_index(index,t,e)
    results = operators(df,index,sym1,sym2)
    df = pd.DataFrame(results)
    results = df.reindex(index=['Random Walk I[1]','Random Walk I[2]','Cointegration Level',
                               'Pearson Correlation','Beta','Current Spread','Price-Ratio',
                               'Average Price-Ratio','Beta 1','Beta 2','Spread Mean',
                               'Spread Median','Spread Maximum','Spread Minimum',
                               'Half-life','Current z-score'])
    print ""
    print results
    
##############################################################
#                Run calls these functions                   #
##############################################################
def make_url(symbol):
    base_url = "http://ichart.finance.yahoo.com/table.csv?s="
    return base_url + symbol
def data_handler(sym,t,e):
    url = make_url(sym)
    page = urlopen(url)
    df = pd.read_csv(page)['Adj Close'][e:(e+t)]
    print df
    df = pd.DataFrame({sym:df})
    return df
def get_data(sym1,sym2,t,e):
    print 'Getting data...'
    t = int(t*250)
    e = int(e*250)
    df1 = data_handler(sym1,t,e)
    df2 = data_handler(sym2,t,e)
    df = pd.concat((df1,df2),axis=1)
    return df
def get_index(index,t,e):
    t = int(t*250)
    e = int(e*250)
    index = data_handler(index,t,e)
    return index
def ols_transform(df,sym1,sym2):
    """
    Computes regression coefficient (slope and intercept)
    via Ordinary Least Squares between two instruments.
    """
    p0 = df[sym1]
    p1 = sm.add_constant(df[sym2], prepend=True)
    slope, intercept = sm.OLS(p0, p1).fit().params
    return slope, intercept

def operators(df,index,sym1,sym2):
    # Arrange data
    sym_array = df.values
    index_array = index.values
    sym1_p = np.array([])
    sym1_returns = np.array([])
    sym2_p = np.array([])
    sym2_returns = np.array([])
    index = np.array([])
    index_returns = np.array([])
    y = len(sym_array)
    for x in range(y):
        sym1_p = np.append(sym1_p, sym_array[x][0])
        sym2_p = np.append(sym2_p, sym_array[x][1])
        index = np.append(index, index_array[x])
    for x in range(y-1):
        return1 = (sym1_p[x+1] / sym1_p[x])-1
        sym1_returns = np.append(sym1_returns, return1)
        return2 = (sym2_p[x+1] / sym2_p[x])-1
        sym2_returns = np.append(sym2_returns, return2)
        returnI = (index[x+1] / index[x])-1
        index_returns = np.append(index_returns, returnI)
    
    print 'Testing Random Walk Hypothesis...'
    v1 = vratio(sym1_p, cor = 'het')
    v2 = vratio(sym2_p, cor = 'het')
    if v1[2] < 0.05:
        result1 = False
    else:
        result1 = True
    if v2[2] < 0.05:
        result2 = False
    else:
        result2 = True
    results['Results']['Random Walk I[1]'].append(result1)
    results['Results']['Random Walk I[2]'].append(result2)

    print 'Calculating cointegration...'    
    # Step 1: regress one variable on the other
    ols_result = sm.OLS(sym1_p,sym2_p).fit()
    # Step 2: obtain the residual (ols_resuld.resid)
    # Step 3: apply Augmented Dickey-Fuller test to see whether 
    # the residual is unit root    
    result = ts.adfuller(ols_result.resid)
    pvalue = round(1-result[1],4)*100
    results['Results']['Cointegration Level'].append(str(pvalue)+'%')
    
    print 'Calculating Pearson Correlation...'
    r = round(pearsonr(sym1_p,sym2_p)[0],4)*100
    results['Results']['Pearson Correlation'].append(str(r)+'%')
    
    print 'Calculating Beta...'
    beta = np.around(np.cov(sym2_returns,sym1_returns)[0,1] / np.var(sym1_returns), decimals = 2)
    results['Results']['Beta'].append(beta)
    
    print 'Calculating Current Spread'
    spread = round((sym1_p[0]-sym2_p[0]),4)
    results['Results']['Current Spread'].append(spread)
    
    print 'Calculating Current Price-Ratio...'
    ratio = round((sym1_p[0]/sym2_p[0]),2)
    results['Results']['Price-Ratio'].append(ratio)
    
    print 'Calculating Average Price-Ratio...'
    array = sym1_p / sym2_p
    ratio = round(np.mean(array),2)
    results['Results']['Average Price-Ratio'].append(ratio)
    
    print 'Calculating Spread Mean...'
    array = sym1_p - sym2_p
    mean = round(np.mean(array),2)
    results['Results']['Spread Mean'].append(mean)
    
    print 'Calculating Spread Median...'
    array = sym1_p - sym2_p
    median = round(np.median(array),2)
    results['Results']['Spread Median'].append(median)
    
    print 'Calculating Spread Maximum...'
    array = sym1_p - sym2_p
    max = round(np.max(array),2)
    results['Results']['Spread Maximum'].append(max)
    
    print 'Calculating Spread Minimum...'
    array = sym1_p - sym2_p
    min = round(np.min(array),2)
    results['Results']['Spread Minimum'].append(min)
    
    print 'Calculating Beta 1...'
    beta = np.around(np.cov(sym1_returns,index_returns)[0,1] / np.var(index_returns), decimals = 2)
    results['Results']['Beta 1'].append(beta)

    print 'Calculating Beta 2...'
    beta = np.around(np.cov(sym2_returns,index_returns)[0,1] / np.var(index_returns), decimals = 2)
    results['Results']['Beta 2'].append(beta)
    
    print 'Calculating Half-life...'
    array = sym1_p - sym2_p
    x = np.subtract(array[1:],array[:-1])
    y = array[:-1]
    k = np.polyfit(y,x,1)
    half_life = ceil(-np.log(2)/k[0])
    results['Results']['Half-life'].append(half_life)
    
    print 'Calculating Current z-score...'
    # 1. Calculate slop and intercept
    window = 100
    sym1_p = sym1_p[::-1][-window:]
    sym2_p = sym2_p[::-1][-window:]
    spreads = sym1_p - sym2_p
    current_zscore = round(zscore(spreads)[-1],2)
    results['Results']['Current z-score'].append(current_zscore)
    
    #################################################
    return results 
    #################################################  
run()
#####################################################
