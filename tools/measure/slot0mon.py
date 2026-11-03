"""A real monster type (or a block) in slot 0, the slot the game treats as Chip: random rooms, random joystick input,
some other monsters, tick-0 A start. Lock-step cartridge vs remake."""
import sys, random, collections
sys.path.insert(0,'/home/claude/remake/tools/measure'); sys.path.insert(0,'/home/claude/verify')
import measure as M, cxx_lock as C
TILES=[0x00]*14+[0x01]*3+[0x02]*2+[0x05,0x06,0x07,0x08,0x0A,0x0B,0x0C,0x0D,0x13,0x14,0x03,0x23,0x23,0x1E,0x1A,0x0F,0x10,0x11,0x12,0x19,0x22,0x16,0x15,0x25,0x0E,0x0E,0x2C,0x28]
seed=int(sys.argv[1]); N=int(sys.argv[2]); rng=random.Random(seed)
res=collections.Counter(); fails=[]
for it in range(N):
    t0=[2,3,4,5,6,7,8,9,10,11][it%10]
    px,py=rng.randrange(8,24),rng.randrange(8,24)
    cells={(x,y):rng.choice(TILES) for x in range(px-7,px+8) for y in range(py-7,py+8)}
    cells[(px,py)]=0
    objs=[((0x80 if rng.random()<0.3 and t0!=7 else 0)|(t0<<2)|rng.randrange(4),px,py)]; used={(px,py)}
    for _ in range(rng.randrange(0,4)):
        mx,my=px+rng.randrange(-6,7),py+rng.randrange(-6,7)
        if (mx,my) in used or cells.get((mx,my))==1: continue
        used.add((mx,my)); objs.append(((rng.choice([2,3,4,5,6,8,9,10,11,7])<<2)|rng.randrange(4),mx,my))
    inputs={}; d=None
    for k in range(200):
        if rng.random()<0.25: d=rng.choice([M.N,M.E,M.S,M.W,None])
        if d is not None: inputs[k]={d}
    boots={}
    for b in (0x20,0x21,0x22,0x23):
        if rng.random()<0.2: boots[b]=1
    r=C.run_both(M.level(cells,objs),inputs,200,boots=boots or None,start=True)
    if r is None: res[('type%d'%t0,'no start')]+=1; continue
    m,le,lc,el,cl=r; ok=m==le==lc; ns=C.run_both.outofsync
    out='crash' if el[-1]=='crash' else 'ran'
    res[('type%d'%t0,out,'sync' if ok else ('flagged' if ns is not None and ns<=m else 'DIFF'))]+=1
    if not ok and not (ns is not None and ns<=m): fails.append((it,t0,m,ns,C.describe(el[m],cl[m])[:140] if m<min(le,lc) else 'len %d/%d'%(le,lc)))
for k,v in sorted(res.items()): print(seed,k,v)
for f in fails: print(' FAIL',f)
