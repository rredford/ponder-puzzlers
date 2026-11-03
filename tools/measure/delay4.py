import sys, json; sys.path.insert(0,'/home/claude/verify'); import measure as M, cxx_lock as C
def level(w):
    cells={(15,15):0,(31,31):0,(30,31):0,(12,13):0}
    for x in range(2,30): cells[(x,5)]=0
    base=[(0x05,15,15),(0x80|(4<<2)|M.E,3,5),(0x00|(8<<2)|M.N,12,13)]   # + one parked tank in view
    if w <= 2: return None
    objs=base+[(0,0,0)]*(w-3)+[(0x80|(8<<2)|M.E,31,31)]
    return M.level(cells,objs)
tab={}
for w in range(3,128):
    for par in (4,5):
        n,le,lc,el,cl=C.run_both(level(w),{0:{M.E}},24,pokes=[(0x2F,par)])
        if n==le==lc: continue
        ecr=len(el)-1 if el[-1]=='crash' else None
        ccr=len(cl)-1 if cl[-1]=='crash' else None
        tab.setdefault(0x80|w,{})[par]=(ecr,ccr,n)
json.dump({str(k):v for k,v in tab.items()},open('/tmp/claude-0/delay4.json','w'))
print('values whose drawing crashes the original first (write at tick 1); emu crash tick / remake crash tick, even|odd write tick:')
for V in sorted(tab):
    print('%02X: '%V + ' | '.join('%s: emu %s cpp %s'%('even' if p==4 else 'odd', tab[V][p][0], tab[V][p][1]) if p in tab[V] else '%s: same'%('even' if p==4 else 'odd') for p in (4,5)))
