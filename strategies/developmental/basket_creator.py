from pulp import *

list = {'a':{'beta':0.9,'zscore':-2},'b':{'beta':1.5,'zscore':-1},'c':{'beta':1.8,'zscore':-1}}
def create_basket(beta,zscore,bE):
    results = {sym:{'w2':0,'z':0} for sym in list}
    for sym in list:
        b1 = beta
        b2 = list[sym]['beta']
        z1 = zscore
        z2 = list[sym]['zscore']
        
        w1 = LpVariable('w1',0,1)
        w2 = LpVariable('w2',0,1)
    
        prob = LpProblem('problem',LpMaximize)
    
        prob += w1 + w2 == 1
        prob += (w1*b1)+(w2*b2) == bE
        
        prob += (b1*w1)+(b2*b2)
        
        status = prob.solve(GLPK(msg=0))
        LpStatus[status]
        zscore = (value(w1)*z1)+(value(w2)*z2)
        results[sym]['w2'] = value(w2)
        results[sym]['z'] = zscore
    print results

create_basket(.9,-2,1.2)