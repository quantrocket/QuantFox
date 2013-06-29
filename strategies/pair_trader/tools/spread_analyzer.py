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



def run(sym1,sym2,e,t):
    print ""
    #sym1 = raw_input("Leg 1: ")
    #sym2 = raw_input("Leg 2: ")
    #e = float(raw_input("End Years Back: "))
    #t = float(raw_input("Start Years Back: "))
    pair_string = sym1+':'+sym2
    global results
    results = {pair_string:{'Random Walk I[1]':0,'Random Walk I[2]':0,'Cointegration Level':0,
              'Pearson Correlation':0,'Beta':0,'Current Spread':0,'Price-Ratio':0,
              'Average Price-Ratio':0,'Beta 1':0,'Beta 2':0,'Spread Mean':0,
              'Spread Median':0,'Spread Maximum':0,'Spread Minimum':0,
              'Half-life':0,'Current z-score':0}}
    print ""
    index = '^GSPC'
    df = get_data(sym1,sym2,t,e)
    index = get_index(index,t,e)
    results = operators(pair_string,df,index,sym1,sym2)
    df = pd.DataFrame(results)
    results = df.reindex(index=['Random Walk I[1]','Random Walk I[2]','Cointegration Level',
                               'Pearson Correlation','Beta','Current Spread','Price-Ratio',
                               'Average Price-Ratio','Beta 1','Beta 2','Spread Mean',
                               'Spread Median','Spread Maximum','Spread Minimum',
                               'Half-life','Current z-score'])
    #print ""
    #print results
    return results
    
##############################################################
#                Run calls these functions                   #
##############################################################
def get_data(sym1,sym2,t,e):
    t = int(t*250)
    e = int(e*250)
    print 'Getting data...'
    df1 = pd.read_csv('/home/vin/git/QuantFox/data/price/'+sym1+'_price.csv')['Adj Close'][e:(e+t)]
    df2 = pd.read_csv('/home/vin/git/QuantFox/data/price/'+sym2+'_price.csv')['Adj Close'][e:(e+t)]
    df = pd.concat((df1,df2),axis=1)
    return df
def get_index(index,t,e):
    t = int(t*250)
    e = int(e*250)
    index = pd.read_csv('/home/vin/git/QuantFox/data/price/'+index+'_price.csv')['Adj Close'][e:(e+t)]
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

def operators(pair_string,df,index,sym1,sym2):
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
    
    #print 'Testing Random Walk Hypothesis...'
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
    results[pair_string]['Random Walk I[1]'] = result1
    results[pair_string]['Random Walk I[2]'] = result2

    #print 'Calculating cointegration...'    
    # Step 1: regress one variable on the other
    ols_result = sm.OLS(sym1_p,sym2_p).fit()
    # Step 2: obtain the residual (ols_resuld.resid)
    # Step 3: apply Augmented Dickey-Fuller test to see whether 
    # the residual is unit root    
    result = ts.adfuller(ols_result.resid)
    pvalue = round(1-result[1],4)
    results[pair_string]['Cointegration Level'] = pvalue
    
    #print 'Calculating Pearson Correlation...'
    r = round(pearsonr(sym1_p,sym2_p)[0],4)
    results[pair_string]['Pearson Correlation'] = r
    
    #print 'Calculating Beta...'
    beta = np.around(np.cov(sym2_returns,sym1_returns)[0,1] / np.var(sym1_returns), decimals = 2)
    beta = round(beta,2)
    results[pair_string]['Beta'] = beta
    
    #print 'Calculating Current Spread'
    spread = round((sym1_p[0]-sym2_p[0]),4)
    results[pair_string]['Current Spread'] = spread
    
    #print 'Calculating Current Price-Ratio...'
    ratio = round((sym1_p[0]/sym2_p[0]),2)
    results[pair_string]['Price-Ratio'] = ratio
    
    #print 'Calculating Average Price-Ratio...'
    array = sym1_p / sym2_p
    ratio = round(np.mean(array),2)
    results[pair_string]['Average Price-Ratio'] = ratio
    
    #print 'Calculating Spread Mean...'
    array = sym1_p - sym2_p
    mean = round(np.mean(array),2)
    results[pair_string]['Spread Mean'] = mean
    
    #print 'Calculating Spread Median...'
    array = sym1_p - sym2_p
    median = round(np.median(array),2)
    results[pair_string]['Spread Median'] = median
    
    #print 'Calculating Spread Maximum...'
    array = sym1_p - sym2_p
    max = round(np.max(array),2)
    results[pair_string]['Spread Maximum'] = max
    
    #print 'Calculating Spread Minimum...'
    array = sym1_p - sym2_p
    min = round(np.min(array),2)
    results[pair_string]['Spread Minimum'] = min
    
    #print 'Calculating Beta 1...'
    beta = np.around(np.cov(sym1_returns,index_returns)[0,1] / np.var(index_returns), decimals = 2)
    beta = round(beta,2)
    results[pair_string]['Beta 1'] = beta

    #print 'Calculating Beta 2...'
    beta = np.around(np.cov(sym2_returns,index_returns)[0,1] / np.var(index_returns), decimals = 2)
    beta = round(beta,2)
    results[pair_string]['Beta 2'] = beta
    
    #print 'Calculating Half-life...'
    array = sym1_p - sym2_p
    x = np.subtract(array[1:],array[:-1])
    y = array[:-1]
    k = np.polyfit(y,x,1)
    half_life = ceil(-np.log(2)/k[0])
    results[pair_string]['Half-life'] = half_life
    
    #print 'Calculating Current z-score...'
    # 1. Calculate slop and intercept
    window = 100
    sym1_p = sym1_p[::-1][-window:]
    sym2_p = sym2_p[::-1][-window:]
    spreads = sym1_p - sym2_p
    current_zscore = round(zscore(spreads)[-1],2)
    results[pair_string]['Current z-score'] = current_zscore
    
    #################################################
    return results 
    #################################################  
#run()
#####################################################
