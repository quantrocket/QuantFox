from win32com.client import DispatchWithEvents
from pythoncom import PumpWaitingMessages, Empty, Missing
from time import time
from datetime import datetime
import os, csv
import pandas as pd

list = ["IBM US Equity", "AAPL US Equity"]
frames = {sym:{} for sym in list}
tick = []


entity = 'PX_LAST'
start = datetime(2011, 1, 1)
end = datetime(2012, 12, 31)
bars = 2
csv_file = 'same_test.csv'

def clearCSV(csv_file):
    csv_file = open(csv_file, "w")
    csv_file.truncate()
    writer = csv.writer(open('same_test.csv', 'ab'), delimiter = ',')
    header = ['DATE', 'AAPL_Close', 'IBM_Close']
    writer.writerow(header)
    csv_file.close()
    return
clearCSV(csv_file)

def writeCSV(csv_file):
    write = [str(date)]
    write.append(str(close))
    self.dataWriter(write)
    return

def toPandas(frames):
    df = pd.DataFrame(frames)
    print df
    return

class get_historical_data:

    #def set_sym(self, sym):
        #self.__sym = sym
    tick = 0
        
    
        
    def dataWriter(self, write):
        writer = csv.writer(open('same_test.csv', 'ab'), delimiter = ',')
        writer.writerow(write)
                         
    def OnData(self, Security, cookie, Fields, Data, Status):
        #sym = 0
        for i in range(0, bars):
            date = str(Data[i][-2])[:8]
            close = Data[i][-1]
            frames[tick].update({date:close})
    
    def OnStatus(self, Status, SubStatus, StatusDescription):
        print 'OnStatus'
        
class TestAsync:
    
    def __init__(self):
        clsid = '{F2303261-4969-11D1-B305-00805F815CBF}'
        progid = 'Bloomberg.Data.1'

        print 'connecting to BBCom........'
        print 'getting historical data.....'    
        blp = DispatchWithEvents(clsid, get_historical_data)
        
        for sym in list:
            global tick
            tick = sym
            self.get(blp, sym)
    
    def get(self, blp, sym):
        blp.GetHistoricalData(sym, 1, entity, start, end, Results = Empty)
        self.go(blp)
          
    def go(self, blp):
            
        blp.AutoRelease = True
        blp.Flush()

        end_time = time() + 1
        
        while 1:
            PumpWaitingMessages()
            if end_time < time():
                print 'completed symbol...'
                break
  
if __name__ == "__main__":
    ta = TestAsync()

print ""    
toPandas(frames)

