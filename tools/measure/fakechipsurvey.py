"""Random level survey: Chip on skates among redirect tiles 4A / 71, with ice, ice corners, force floors, walls,
blocks and monsters; random input; tick-0 A start; cartridge vs remake lock-step."""
import sys, random, collections
sys.path.insert(0,'/home/claude/remake/tools/measure'); sys.path.insert(0,'/home/claude/verify')
import measure as M, cxx_lock as C
import os
MONS=os.environ.get("MONS","1")=="1"
seed=int(sys.argv[1]); N=int(sys.argv[2]); rng=random.Random(seed)
TILES=[0x00]*10+[0x02]*6+[0x0A,0x0B,0x0C,0x0D]+[0x05,0x06,0x07,0x08]+[0x01]*3+[0x4A]*4+[0x71]*4+[0x14,0x03]
MON=[2,3,4,5,6,7,8,10]
res=collections.Counter(); fails=[]
for it in range(N):
    px,py=rng.randrange(8,24),rng.randrange(8,24)
    cells={(x,y):rng.choice(TILES) for x in range(px-6,px+7) for y in range(py-6,py+7)}
    cells[(px,py)]=0
    for d in range(4):                       # a redirect tile next to Chip in a random direction, often
        if rng.random()<0.5: cells[(px+M.DX[d],py+M.DY[d])]=rng.choice([0x4A,0x71])
    objs=[(0x04|rng.randrange(4),px,py)]; used={(px,py)}
    for _ in range(rng.randrange(2,7)):
        mx,my=px+rng.randrange(-5,6),py+rng.randrange(-5,6)
        if (mx,my) in used or cells.get((mx,my))==0x01: continue
        used.add((mx,my))
        t=1
        objs.append(((0x80 if rng.random()<0.6 else 0)|(t<<2)|rng.randrange(4),mx,my))
    inputs={}; d=None
    for k in range(120):
        if rng.random()<0.25: d=rng.choice([M.N,M.E,M.S,M.W,None,None])
        if d is not None: inputs[k]={d}
    boots={0x20:1}
    if rng.random()<0.2: boots[0x21]=1
    data=M.level(cells,objs)
    r=C.run_both(data,inputs,120,boots=boots,start=True)
    if r is None: res['no start']+=1; continue
    m,le,lc,el,cl=r
    out='crash' if el[-1]=='crash' else 'ran'
    ok=m==le==lc
    res[(out,ok,C.run_both.outofsync is not None)]+=1
    if not ok: fails.append((it,m,C.run_both.outofsync,C.describe(el[m],cl[m])[:150] if m<min(le,lc) else 'len %d/%d'%(le,lc)))
print(seed,dict(res)); [print(" ",f) for f in fails if f[2] is None]
