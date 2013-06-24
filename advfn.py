from BeautifulSoup import BeautifulSoup as bs
import urllib2
import csv
import pandas as pd

reader = csv.reader(open('advfn_dictionary.csv', "rb"), delimiter = "\t")
dictionary = [key for line in reader for key in line]
print dictionary

def get_dates(sym):
    dates = {}
    base_url = 'http://www.advfn.com/p.php?pid=financials&btn=quarterly_reports&mode=&symbol=NYSE%3A'
    url = base_url + sym
    page = urllib2.urlopen(url)
    soup = bs(page.read())
    
    line = soup.findAll('option')

    for n in range(len(line)):
        date = str(line[n])[-16:-9]
        dates[n] = date
        
    return dates


def get_data(sym):
    
    base_url = 'http://www.advfn.com/p.php?pid=financials&btn=istart_date&mode=quarterly_reports&symbol='
    dates = get_dates(sym)
    dates_list = [dates[i] for i in dates]
    data = {i:{} for i in dates_list}
    
    years = len(dates)   
    for i in range(years):
        url = base_url + sym + '&istart_date=' + str(i)
        print url
        page = urllib2.urlopen(url)
        soup = bs(page.read())
        
        line = soup.findAll('td',{'class':'s'})
        #point = line.find('quarter end date')
        
        data_list = []
        for point in line:
            #print point.string
            data_list.append(str(point.string))
        
        n = len(data_list)
        for i in range(n):
            key = data_list[i]
            if key == 'quarter end date':
                current_date = str(data_list[i+1])
                print current_date
        for i in range(n):
            key = data_list[i]
            if key in dictionary:
                value = data_list[i+1]
                data[current_date][key] = value
            
    data = pd.DataFrame(data)
    data.to_csv('ibm.csv')
    print data
        
get_data('IBM') 