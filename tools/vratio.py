from numpy import *
from numpy import random
 
def normcdf(X):
    (a1,a2,a3,a4,a5) = (0.31938153, -0.356563782, 1.781477937, 
     -1.821255978, 1.330274429)
    L = abs(X)
    K = 1.0 / (1.0 + 0.2316419 * L)
    w = 1.0 - 1.0 / sqrt(2*pi)*exp(-L*L/2.) * (a1*K + a2*K*K + a3*pow(K,3) +
    a4*pow(K,4) + a5*pow(K,5))
    if X<0:
        w = 1.0-w
    return w
 
 
def vratio(a, lag = 2, cor = 'hom'):
    t = (std((a[lag:]) - (a[1:-lag+1])))**2;
    b = (std((a[2:]) - (a[1:-1]) ))**2;
 
    n = float(len(a))
    mu  = (a[-1]-a[0])/n;
    m=(n-lag+1)*(1-lag/n);
#   print mu, m, lag
    b=sum(square(a[1:n]-a[:n-1]-mu))/(n-1)
    t=sum(square(a[lag:n]-a[:n-lag]-lag*mu))/m
    vratio = t/(lag*b);
 
    la = float(lag)
     
 
    if cor == 'hom':
        varvrt=2*(2*la-1)*(la-1)/(3*la*n)
 
 
    elif cor == 'het':
          varvrt=0;
          sum2=sum(square(a[1:n]-a[:n-1]-mu)); 
          for j in range(lag-1):
             sum1a=square(a[j+1:n-1]-a[j+0:n-2]-mu); 
             sum1b=square(a[2:n-j]-a[1:n-j-1]-mu)
             sum1=dot(sum1a,sum1b); 
             delta=sum1/(sum2**2);
             varvrt=varvrt+(2*(la-j)/la**2)*delta
 
    zscore = (vratio - 1) / sqrt(float(varvrt))
    pval = normcdf(zscore);
 
    return  vratio, zscore, pval
 
if __name__=="__main__":
 
    trend = 0.25  #  The larger this number the stronger the trend, hence larger zscore and pval
    bias = 1000   #  This is to make sure that the time series does not go negative
    a = log((random.randn(1000)+bias)); #Mean reverting: hurst very small, vratio should be small
#   a = log(cumsum(random.randn(10000)+trend)+bias); #trending: hurst > 0.5;
#   a = log(cumsum(random.randn(10000)) + bias); #random walk: hurst ~ 0.5
 
    print vratio(a, cor = 'het', lag = 20)