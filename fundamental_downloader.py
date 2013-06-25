import get_fundamental
import csv
import pandas as pd

df = pd.read_csv('instruments.csv', delimiter='\t')
failed = ['RDS.A','RDS.B','BRK.B','BRK.A','STD','RDS.A','RDS.B','BRK.B','BRK.A',"ABV.C","BF.B","HUB.B","JW.A","FCE.A"
          "MOG.A","BF.A","HEI.A","AKO.B","CIG.C","GEF.B","AKO.A","PRIS.B","MKC.V","BTM.C","CBS.A","HUB.A","STZ.B"
          "LEN.B","BIO.B","CRD.A","JW.B","KV.A","CRD.B","FCE.B","MOG.B","HVT.A","KV.B","TAP.A","GTN.A"]
prog = len(df)
print prog
for idx, row in df.iterrows():
    sym = df['TICKER'][idx]
    if sym in failed:
        pass
    else:
        progress = round(float(idx)/float(prog)*100,4)
        get_fundamental.get_data(sym,progress)