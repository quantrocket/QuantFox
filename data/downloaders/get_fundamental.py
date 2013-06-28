import os
import pandas as pd

def get_data(sym,progress):
    file = '/home/vin/git/QuantFox/data/FUND/' + sym + '_FUND-Q.csv'
    print file
    if os.path.exists(file) == True:
        print sym + ': EXISTS'
    else:
        import advfn
        advfn.get_data(sym,progress)