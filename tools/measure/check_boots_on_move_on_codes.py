import sys; sys.path.insert(0,'/home/claude/verify'); import cxx_lock as C, fit_odd as F
res=[]
for code in (0x4A, 0x71, 0x43):
    for boots in ({0x20:1},{0x21:1},{0x22:1},None):
        for d in range(4):
            if not F.TAB['enter'][str(code)][0][d]: continue
            for extra in ([],[(5,0)],[(5,1)],[(5,2)],[(5,3)]):
                data,inputs=F.scenario(code,1,d,extra)
                n,le,lc,el,cl=C.run_both(data,inputs,16,boots=boots)
                ok = n==le==lc
                res.append((code,boots,d,extra,ok,n,None if ok else (C.describe(el[n],cl[n]) if n<min(le,lc) else 'len %d/%d'%(le,lc))))
from collections import Counter
print(Counter((hex(r[0]), str(r[1]), r[4]) for r in res))
for r in res:
    if not r[4]: print(hex(r[0]), r[1], 'dir', r[2], r[3], 'tick', r[5], r[6][:160])
