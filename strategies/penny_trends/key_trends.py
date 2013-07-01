import pyGTrends as gt
import pandas as pd
from datetime import datetime

def run(sym_list):
    get_trends(sym_list)
    df = sync_db(sym_list)
    return df
   
def get_trends(sym_list):
    print 'Getting trend Data...'
    for sym in sym_list:    
        gt.main(sym)

def sync_db(sym_list):
    df = pd.read_csv('trend_data/'+sym_list[0]+'_trends.csv',index_col='Date',parse_dates=True)
    start = df.index[0]
    end = df.index[-1]
    rng = pd.date_range(start,end,freq='D')
    df = df.reindex(rng)
    for sym in sym_list[1:]:
        df1 = pd.read_csv('trend_data/'+sym+'_trends.csv',index_col='Date',parse_dates=True)
        df = df.join(df1)
    df = df.fillna(method='ffill')
    df['sum'] = 0
    for sym in sym_list:
        nn = df[sym].count()
        for i in range (0,nn):
            if df[sym][i] != " ":
                df['sum'][i] = df['sum'][i] + float(df[sym][i])
    df[sym] = df['sum']

    return df