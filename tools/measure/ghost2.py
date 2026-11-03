"""An object starting the level on a ghost reference (its under-tile becomes the reference). Ghost kinds as in
ghost.py; the object on it is Chip (random input), a monster, a block Chip pushes off, or a block / monster on a
force floor arrangement next to it. Lock-step cartridge vs remake, 80 ticks."""
import sys, random, collections
sys.path.insert(0,'/home/claude/remake/tools/measure'); sys.path.insert(0,'/home/claude/verify')
import measure as M, cxx_lock as C
res=collections.Counter(); fails=[]
GK=['empty','live elsewhere','dying elsewhere','Chip','self']
OK_=['chip','monster','pushed block','monster on ice','second visitor']
it=0
for seed in (1,2):
    rng=random.Random(seed)
    for gk in GK:
        for ok_ in OK_:
            cx,cy=15,15; d=rng.randrange(4)
            cells={(x,y):0 for x in range(cx-6,cx+7) for y in range(cy-6,cy+7)}
            for _ in range(6): cells[(cx+rng.randrange(-6,7),cy+rng.randrange(-6,7))]=rng.choice([1,2,0x14,0x23,0x19])
            for p in ((cx,cy),(cx+M.DX[d],cy+M.DY[d]),(cx-M.DX[d],cy-M.DY[d]),(cx+2*M.DX[d],cy+2*M.DY[d])): cells[p]=0
            inputs={}
            if ok_=='chip':
                objs=[(0x04|d,cx,cy)]
                for k in range(1,70):
                    if rng.random()<0.5: inputs[k]={rng.randrange(4)}
            elif ok_=='monster':
                objs=[(0x04|M.S,cx-5,cy-5),((rng.choice([2,3,4,5,6,8,9,10,11])<<2)|d,cx,cy)]; cells[(cx-5,cy-5)]=0
            elif ok_=='pushed block':
                objs=[(0x04|d,cx-M.DX[d],cy-M.DY[d]),((7<<2)|d,cx,cy)]
                for k in range(1,12): inputs[k]={d}
            elif ok_=='monster on ice':
                cells[(cx,cy)]=2; cells[(cx+M.DX[d],cy+M.DY[d])]=2
                objs=[(0x04|M.S,cx-5,cy-5),(0x80|(rng.choice([2,4,6,8])<<2)|d,cx,cy)]; cells[(cx-5,cy-5)]=0
            else:                                    # a monster leaves the cell, then Chip walks into it
                objs=[(0x04|(d^2),cx+2*M.DX[d],cy+2*M.DY[d]),((8<<2)|(d^2),cx,cy)]
                for k in range(10,40): inputs[k]={d^2}
            n=len(objs)
            if gk=='empty': k=n+rng.randrange(0,5)
            elif gk in ('live elsewhere','dying elsewhere'):
                ox,oy=cx+rng.choice([-4,4]),cy+rng.choice([-4,4]); cells[(ox,oy)]=0
                st=((rng.choice([2,3,4,5,6,7,8,9,10,11])<<2)|rng.randrange(4)) if gk=='live elsewhere' else (0x40|rng.choice([0,3,6,9,12]))
                objs.append((st,ox,oy)); k=len(objs)-1
            elif gk=='Chip': k=0
            else: k=0 if ok_=='chip' else 1
            under=cells[(cx,cy)]; cells[(cx,cy)]=0x80|k                     # the object starts on the ghost
            r=C.run_both(M.level(cells,objs),inputs,80,start=True)
            if r is None: res[(gk,ok_,'no start')]+=1; it+=1; continue
            m,le,lc,el,cl=r; okk=m==le==lc; ns=C.run_both.outofsync
            out='crash' if el[-1]=='crash' else 'ran'
            key='sync' if okk else ('flagged' if ns is not None and ns<=m else 'DIFF')
            res[(out,key)]+=1
            if key=='DIFF': fails.append((it,gk,ok_,m,C.describe(el[m],cl[m])[:150] if m<min(le,lc) else 'len %d/%d'%(le,lc)))
            it+=1
print(it,'runs',dict(res))
for f in fails: print(' FAIL',f)
