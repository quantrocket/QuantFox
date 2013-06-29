"""
Downloads data for all symbols in the specified instrument list
Will download all available daily price data from Yahoo finance
"""
import pandas as pd
from urllib import urlopen
import os

failed = []
def run():
    action = update()
    sym_list = get_sym_list()
    for symbol in sym_list:
        if action == True:
            handle_data(symbol)
        else:
            file = 'price/'+symbol+'_price.csv'
            if os.path.exists(file) == True:
                pass
            else:
                handle_data(symbol)
    error_log(failed)
    n = len(failed)
    print 'Download Completed with %s Errors' %n

def update():
    action = raw_input('Update Existing [y/n]? ')
    if action == 'y':
        return True
    else:
        return False
def handle_data(symbol):
    url = make_url(symbol)
    print 'Getting Data...',symbol
    try:
        df = get_data(url)
        to_csv(symbol,df)
    except:
       failed.append(symbol)
def get_sym_list():
    df = pd.read_csv('instruments/instruments.csv', delimiter='\t')
    sym_list = df['TICKER'].tolist()
    return sym_list
def make_url(symbol):
    base_url = "http://ichart.finance.yahoo.com/table.csv?s="
    return base_url + symbol
def get_data(url):
    page = urlopen(url)
    df = pd.read_csv(page)
    return df
def to_csv(symbol,df):
    file_string = 'price/'+symbol+'_price.csv'
    df.to_csv(file_string)
def error_log(failed):
    log_file = 'yahoo_error_log.txt'
    log_file = open(log_file,'w')
    for symbol in failed:
        print>>log_file,symbol
    
run()