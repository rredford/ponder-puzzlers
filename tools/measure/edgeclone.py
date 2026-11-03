"""Clone objects off the map edge (the MS "Insanity" idea): a clone machine on row 0 facing N or on row 31 facing S,
template = block or fake Chip; a ball bounces over the red button; Chip slides round an ice loop.
Lock-step cartridge vs remake; also records whether Chip's sliding is stopped on the cartridge."""
import sys, random, collections
sys.path.insert(0,'/home/claude/remake/tools/measure'); sys.path.insert(0,'/home/claude/verify')
import measure as M, cxx_lock as C
T=int(sys.argv[1]) if len(sys.argv)>1 else 300
def level(edge, col, tmpl, idle=False):
    cells={(x,y):0 for x in range(32) for y in range(32)}
    for x in range(32): cells[(x,0)]=1; cells[(x,31)]=1          # walls along both edges ...
    cy=0 if edge=='N' else 31; d=M.N if edge=='N' else M.S
    cells[(col,cy)]=0x2F                                           # ... except the clone machine
    cells[(col,cy+(1 if edge=='N' else -1))]=1                     # wall behind it, so clones can only leave the map
    # ball lane over the red button, rows 12/13 middle
    for x in range(3,9): cells[(x,12)]=0
    cells[(2,12)]=1; cells[(9,12)]=1; cells[(5,12)]=0x30
    # Chip's ice lane: row 25, cols 10..25, walls at both ends: he bounces back and forth forever
    for x in range(10,26): cells[(x,25)]=2
    cells[(9,25)]=0x06; cells[(8,25)]=1; cells[(26,25)]=1
    for x in range(8,27): cells[(x,24)]=1; cells[(x,26)]=1
    objs=[(0x04|M.E,20,20) if idle else (0x04|M.E,9,25),                                         # Chip on the ice lane, pushed east on tick 1
          (0x80|(tmpl<<2)|d,col,cy),                                    # template on the clone machine
          (0x80|(6<<2)|M.E,3,12)]                                  # ball
    return M.level(cells,objs)
res=collections.Counter(); rows=[]
import os
IDLE=os.environ.get('IDLE')=='1'; rng=random.Random(5)
TYPES=[int(x) for x in os.environ.get('TYPES','7,1').split(',')]
for edge in 'NS':
    for tmpl,tn in [(t,'type%d'%t) for t in TYPES]:
        for col in range(32):
            if edge=='N' and col in (12,13,20): pass
            data=level(edge,col,tmpl,IDLE)
            inp={}
            if IDLE and os.environ.get('WALK')=='1':
                d=None
                for k in range(T):
                    if rng.random()<0.2: d=rng.choice([M.N,M.E,M.S,M.W,None,None])
                    if d is not None: inp[k]={d}
            r=C.run_both(data,inp,T,start=True)
            if r is None: res[(edge,tn,'no start')]+=1; continue
            m,le,lc,el,cl=r
            ok=m==le==lc; ns=C.run_both.outofsync
            out='crash' if el[-1]=='crash' else 'ran'
            # did Chip stop sliding on the cartridge? (same position 4 ticks in a row while not dead)
            pos=[(bytes.fromhex(x)[128],bytes.fromhex(x)[256],bytes.fromhex(x)[0]) for x in el if x!='crash']
            stop=next((t for t in range(8,len(pos)) if len(set(p[:2] for p in pos[t-4:t]))==1 and pos[t][2]),None)
            nobj=max(sum(1 for i in range(128) if bytes.fromhex(x)[i]) for x in el if x!='crash')
            res[(edge,tn,out,'sync' if ok else ('flagged' if ns is not None and ns<=m else 'DIFF'))]+=1
            rows.append((edge,tn,col,out,len(el),ok,m,ns,'chip stops @%s'%stop,'max objs %d'%nobj,'' if ok else (C.describe(el[m],cl[m])[:120] if m<min(le,lc) else 'len %d/%d'%(le,lc))))
            print(*rows[-1],flush=True)
print(dict(res))
