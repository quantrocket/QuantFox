import pyGTrends as gt
import pandas as pd
from datetime import datetime

def run(sym_list,update):
    get_trends(sym_list)
    df = sync_db(sym_list)      
    return df

def get_trends(sym_list):
    print 'Getting trend Data...'
    for sym in sym_list:    
        gt.main(sym)
    print 'Downloaded all Data'

def sync_db(sym_list):
    print "Analyzing Trends..."
    df = pd.read_csv('trend_data/'+sym_list[0]+'_trends.csv',index_col='Date',parse_dates=True)
    start = df.index[0]
    end = df.index[-1]
    rng = pd.date_range(start,end,freq='D')
    df = df.reindex(rng)
    print 'Reindexed'
    for sym in sym_list[1:]:
        df1 = pd.read_csv('trend_data/'+sym+'_trends.csv',index_col='Date',parse_dates=True)
        df = df.join(df1)
    print 'Joined'
    df = df.fillna(method='ffill')
    print 'Filled NaN'
    df['sum'] = 0
    for sym in sym_list:
        nn = df[sym].count()
        for i in range (0,nn):
            if df[sym][i] != " ":
                df['sum'][i] = df['sum'][i] + float(df[sym][i])
    print 'Summed'
    df.to_csv('trend_data/processed/'+sym_list[0]+'_trend_df.csv')
    return df
    print 'Done'