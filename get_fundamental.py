import os
import pandas as pd




def get_data(sym):
    file = '/home/vin/git/QuantFox/data/FUND/' + sym + '_FUND-Q.csv'
    print file
    if os.path.exists(file) == True:
        print "TRUE"
    else:
        print "FALSE"
        import advfn
        advfn.get_data(sym)


get_data('T')