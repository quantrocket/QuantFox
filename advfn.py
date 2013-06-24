from BeautifulSoup import BeautifulSoup as bs
import urllib2

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
    base_url = 'http://www.advfn.com/p.php?pid=financials&btn=istart_date&mode=quarterly_reports&symbol=NYSE%3A'
    data = {}
    data_list = []
    dates = get_dates(sym)
    for n in dates:
        url = base_url + sym + '&istart_date=' + str(n)
        print url
        #print n, dates[n]
        
        
        
        
        
        
        
        
get_data('IBM') 
    
"""
       base_url = 'http://www.advfn.com/p.php?pid=financials&btn=istart_date&mode=quarterly_reports&symbol=NYSE%3A'
       IBM&istart_date=0
    """




get_dates('IBM')

"""
list = []

dict = {}

url = 'http://www.advfn.com/p.php?pid=financials&btn=quarterly_reports&mode=&symbol=NYSE%3AIBM'

"""






"""
page = urllib2.urlopen(url)
soup = bs(page.read())

line = soup.findAll('td',{'class':'s'})

for point in line:
    list.append(str(point.string))
    
for i in list:
    
    
print list"""