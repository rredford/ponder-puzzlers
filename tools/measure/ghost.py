"""Ghost references: a map cell holding an object reference (80 | k) with no matching object there. k is an empty
slot, a live object elsewhere (any type), a dying effect elsewhere, slot 0 (Chip, elsewhere), or the slot of the
mover itself. Movers: Chip walking into it (random input), every monster type, a block Chip pushes, objects
carried by ice or a force floor. Lock-step cartridge vs remake, with Chip's inventory and the clock."""
import sys, random, collections
sys.path.insert(0,'/home/claude/remake/tools/measure'); sys.path.insert(0,'/home/claude/verify')
import measure as M, cxx_lock as C
seed=int(sys.argv[1]); N=int(sys.argv[2]); rng=random.Random(seed)
res=collections.Counter(); fails=[]
GK=['empty','live elsewhere','dying elsewhere','Chip','self']
for it in range(N):
    gk=GK[it%5]; mk=['chip','monster','pushed block','ice','force'][(it//5)%5]
    cx,cy=15,15
    cells={(x,y):0 for x in range(cx-6,cx+7) for y in range(cy-6,cy+7)}
    for _ in range(8): cells[(cx+rng.randrange(-6,7),cy+rng.randrange(-6,7))]=rng.choice([1,2,0x14,0x13,0x23,0x1E,0x19])
    d=rng.randrange(4); gx,gy=cx+2*M.DX[d],cy+2*M.DY[d]        # ghost two cells ahead of the mover's start
    mx,my=cx,cy
    objs=[]; chip_at=(cx-5,cy-5) if mk!='chip' else (mx,my)
    cells[chip_at]=0
    for p in ((mx,my),(mx+M.DX[d],my+M.DY[d]),(gx,gy),(gx+M.DX[d],gy+M.DY[d])): cells[p]=0
    inputs={}
    if mk=='chip':
        objs=[(0x04|d,mx,my)]
        for k in range(1,60):
            if rng.random()<0.6: inputs[k]={d if rng.random()<0.7 else rng.randrange(4)}
    else:
        objs=[(0x04|M.S,*chip_at)]
        if mk=='monster':
            t=rng.choice([2,3,4,5,6,8,9,10,11]); objs.append(((t<<2)|d,mx,my))
        elif mk=='pushed block':                               # Chip behind the block, pushing toward the ghost
            objs=[(0x04|d,mx-M.DX[d],my-M.DY[d]),((7<<2)|d,mx,my)]; cells[(mx-M.DX[d],my-M.DY[d])]=0
            for k in range(1,40): inputs[k]={d}
        elif mk=='ice':
            cells[(mx+M.DX[d],my+M.DY[d])]=2; cells[(mx,my)]=2
            t=rng.choice([7,2,4,6,8]); objs.append((0x80|(t<<2)|d,mx,my))
        else:
            fc={M.N:5,M.E:6,M.S:7,M.W:8}[d]; cells[(mx,my)]=fc; cells[(mx+M.DX[d],my+M.DY[d])]=fc
            t=rng.choice([7,2,4,6,8]); objs.append((0x80|(t<<2)|d,mx,my))
    # the slot the ghost points at
    n=len(objs)
    if gk=='empty': k=n+rng.randrange(0,5)
    elif gk=='live elsewhere':
        ox,oy=cx+rng.choice([-4,4]),cy+rng.choice([-4,4]); cells[(ox,oy)]=0
        objs.append(((rng.choice([2,3,4,5,6,7,8,9,10,11])<<2)|rng.randrange(4),ox,oy)); k=len(objs)-1
    elif gk=='dying elsewhere':
        ox,oy=cx+rng.choice([-4,4]),cy+rng.choice([-4,4]); cells[(ox,oy)]=0
        objs.append((0x40|rng.choice([0,3,6,9,12]),ox,oy)); k=len(objs)-1
    elif gk=='Chip': k=0
    else: k=1 if n>1 else 0
    cells[(gx,gy)]=0x80|k
    data=M.level(cells,objs)
    r=C.run_both(data,inputs,80,start=True)
    if r is None: res[(gk,mk,'no start')]+=1; continue
    m,le,lc,el,cl=r; ok=m==le==lc; ns=C.run_both.outofsync
    out='crash' if el[-1]=='crash' else 'ran'
    key=(gk,mk,out,'sync' if ok else ('flagged' if ns is not None and ns<=m else 'DIFF'))
    res[key]+=1
    if key[3]=='DIFF': fails.append((it,gk,mk,m,ns,C.describe(el[m],cl[m])[:150] if m<min(le,lc) else 'len %d/%d'%(le,lc)))
for k,v in sorted(res.items()): print(seed,k,v)
for f in fails: print(' FAIL',f)
