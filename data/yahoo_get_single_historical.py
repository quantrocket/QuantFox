"""
Downloads data for all symbols in the specified instrument list
Will download all available daily price data from Yahoo finance
"""
import pandas as pd
from urllib import urlopen
import os


def run():
    sym_list = raw_input('Instruments: ')
    if ',' in sym_list:
        sym_list = sym_list.partition(',')
        for symbol in sym_list:
            if symbol != ',':
                handle_data(symbol)
    else:
        handle_data(sym_list)
    print 'Download Completed'

def handle_data(symbol):
    url = make_url(symbol)
    print 'Getting Data...',symbol
    try:
        df = get_data(url)
        to_csv(symbol,df)
    except:
       print 'Bad Symbol'
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
    
run()