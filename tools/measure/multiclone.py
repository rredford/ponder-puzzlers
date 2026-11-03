"""Several clone machines on one edge (row 0 facing N / row 31 facing S), each with its own red button just before it
in reading order (button at even column, machine at the next odd column). Chip walks along the next row and presses
the buttons in a random order, twice. North edge: row 31 also holds teleports and a brown button wired to a trap,
whose link entries the clones overwrite; Chip then walks into them. Lock-step cartridge vs remake."""
import sys, random, collections
sys.path.insert(0,'/home/claude/remake/tools/measure'); sys.path.insert(0,'/home/claude/verify')
import measure as M, cxx_lock as C
def build(edge, rng):
    cells={(x,y):0 for x in range(32) for y in range(32)}
    er=0 if edge=='N' else 31; wr=1 if edge=='N' else 30; d=M.N if edge=='N' else M.S
    machines=[]
    for x in range(0,32,2):
        if rng.random()<0.75:
            cells[(x,er)]=0x30; cells[(x+1,er)]=0x2F; machines.append(x+1)
        else:
            cells[(x,er)]=1; cells[(x+1,er)]=1
    extra=[]
    if edge=='N':                                   # row-31 targets for the overwritten link entries
        tcols=rng.sample([c for c in machines if c not in (31,)],min(3,len(machines)))
        for c in tcols[:2]: cells[(c,31)]=0x0E
        cells[(31,1)]=0x0E                       # partner on row 1: link high byte 08 (an enterable tile code)
        if len(tcols)>2:
            cells[(tcols[2],31)]=0x2E; cells[(tcols[2],20)]=0x2D       # brown button -> trap on row 20 (link high byte 0E)
            extra.append(('trap',tcols[2]))
        extra.append(('tele',tcols[:2]))
    objs=[(0x04|M.E,0,wr)]
    for c in machines:
        t=rng.choice([7,1,7,7,8,6])              # mostly blocks, some fake Chips, tanks, balls
        objs.append((0x80|(t<<2)|d,c,er))
    for k,v in extra:
        if k=='trap': objs.append((0x80|(8<<2)|M.S,v,20))   # tank waiting in the trap
    return M.level(cells,objs), machines, extra, wr
def path(inputs, t, pos, target):
    x,y=pos; tx,ty=target
    while x!=tx:
        dd=M.E if tx>x else M.W
        for k in range(4): inputs[t+k]={dd}
        t+=5; x+=1 if dd==M.E else -1
    while y!=ty:
        dd=M.S if ty>y else M.N
        for k in range(4): inputs[t+k]={dd}
        t+=5; y+=1 if dd==M.S else -1
    return t,(x,y)
res=collections.Counter(); seed0=int(sys.argv[1]); N=int(sys.argv[2])
for it in range(N):
    rng=random.Random(seed0*1000+it)
    edge='N' if it%2==0 else 'S'
    data,machines,extra,wr=build(edge,rng)
    inputs={}; t=2; pos=(0,wr); er=0 if edge=='N' else 31
    order=[m-1 for m in machines]*2; rng.shuffle(order)
    for b in order:
        t,pos=path(inputs,t,pos,(b,wr))
        t,pos=path(inputs,t,pos,(b,er))          # step onto the button
        t,pos=path(inputs,t,pos,(b,wr))          # and back
    tphase=t
    if edge=='N':
        for k,v in extra:
            cols=v if k=='tele' else [v]
            for c in cols:
                t,pos=path(inputs,t,pos,(c,30)); t,pos=path(inputs,t,pos,(c,31)); t+=8
                pos=None; break                    # after a teleport we no longer know where Chip is
            if pos is None: break
    T=t+40
    tcells=[992+c for k,v in extra for c in (v if k=='tele' else [v])]
    R0=M.Run(data); base={c:R0.r[0x0800+c] for c in tcells}; reaimed=0
    if edge=='N' and R0.ok:
        for k in range(tphase):
            jb=0x01 if k==0 else 0
            for dd in inputs.get(k,()): jb|=M.JOYB[dd]
            R0.L.joy=jb
            try:
                if not R0.L.run_to([0x3A11],4_000_000): break
            except RuntimeError: break
        reaimed=sum(1 for c in tcells if R0.r[0x0800+c]!=base[c])
    r=C.run_both(data,inputs,T,start=True)
    if r is None: res[(edge,'no start')]+=1; print(it,edge,'no start'); continue
    m,le,lc,el,cl=r; ok=m==le==lc; ns=C.run_both.outofsync
    S=[bytes.fromhex(x) for x in el if x!='crash']
    nobj=max(sum(1 for i in range(128) if s[i]) for s in S)
    out='crash' if el[-1]=='crash' else 'ran'
    key=(edge,out,'sync' if ok else ('flagged' if ns is not None and ns<=m else 'DIFF'))
    res[key]+=1
    print(it,edge,'machines',len(machines),'re-aimed links',reaimed,'ticks',len(el),out,'max objs',nobj,key[2],'' if ok else (m,ns,C.describe(el[m],cl[m])[:140] if m<min(le,lc) else 'len %d/%d'%(le,lc)),flush=True)
print(dict(res))
