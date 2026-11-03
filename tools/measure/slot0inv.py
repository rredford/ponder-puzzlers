"""Does a monster in slot 0 collect chips, keys and boots like Chip? Slot 0 holds a forward-driving monster that
runs east along a row of item tiles (random order); boots, keys, chips left, finished flag and the clock are
compared with the remake every tick, besides objects and map."""
import sys, random, subprocess, tempfile, collections
sys.path.insert(0,'/home/claude/remake/tools/measure'); sys.path.insert(0,'/home/claude/verify')
import measure as M, cxx_lock as C
ITEMS={'chip':0x23,'chip(uncounted)':0x31,'key R':0x1E,'key B':0x1F,'key Y':0x20,'key G':0x21,'skates':0x0F,'fire boots':0x10,
       'suction':0x11,'flippers':0x12,'door R':0x1A,'door B':0x1B,'door Y':0x1C,'door G':0x1D,'thief':0x15,'socket':0x24,
       'exit':0x25,'hint':0x33,'popup wall':0x16,'dirt':0x03,'blue wall fake':0x04,'bomb':0x2C,'fire':0x13,'water':0x14,'floor':0x00}
def run(data, T, boots=None):
    R=M.Run(data,boots); r=R.r
    if not R.ok: return None
    script=['globals %d %d %d %d %d %d %d'%(r[0x2F],r[0x4A]&3,20-r[0x3BDB],C.joy2bits(r[0x1D48]),C.joy2bits(r[0x1D49]),r[0x29],int(r[0x37]!=0))]
    for a in range(0x0400,0x0C00):
        if r[a]: script.append('link %x %x'%(a-0x0400,r[a]))
    for k,v in (boots or {}).items(): script.append('poke %x %x'%(k,v))
    emu=[]
    for t in range(T):
        R.L.joy=0x01 if t==0 else 0
        try: ok=R.L.run_to([0x3A11],4_000_000)
        except RuntimeError: ok=False
        script.append('tick %x'%(0x10 if t==0 else 0)); script.append('dump 20 4'); script.append('dump 26 3'); script.append('dump 2a 4'); script.append('dump 1180 2')
        if not ok: emu.append('crash'); break
        emu.append(C.emu_snap(R)+bytes(r[0x20:0x24]).hex()+bytes(r[0x26:0x29]).hex()+bytes(r[0x2A:0x2E]).hex()+bytes(r[0x1180:0x1182]).hex())
    with tempfile.TemporaryDirectory() as td:
        open(td+'/l.bin','wb').write(data); open(td+'/s.txt','w').write('\n'.join(script)+'\n')
        out=subprocess.run([C.LP,'raw',td+'/l.bin',td+'/s.txt'],capture_output=True,text=True,timeout=60).stdout.split('\n')
    rem=[]; cur=None; dumps=[]
    for l in out:
        if l.startswith('T '):
            if cur is not None: rem.append(cur+''.join(dumps))
            p=l.split(); cur='crash' if p[2]=='crash' else ''.join(p[3:]); dumps=[]
        elif l.startswith('D ') and cur is not None and cur!='crash': dumps.append(''.join(l.split()[2:]))
    if cur is not None: rem.append(cur+''.join(dumps))
    n=0
    for a,b in zip(emu,rem):
        if a!=b: break
        n+=1
    return n,emu,rem
NAMES=['skates','suction','fire','flippers','chips lo','chips hi','finished','key R','key B','key Y','key G','time lo','time hi']
def inv(s): A=bytes.fromhex(s); return {NAMES[i]:A[1536+i] for i in range(13)}
rng=random.Random(int(sys.argv[1])); N=int(sys.argv[2]); res=collections.Counter(); seen=collections.defaultdict(set)
for it in range(N):
    t0=[8,5,4,6,2,3,9,11][it%8]                      # tank, glider, fireball, ball, bug, paramecium, walker, teeth
    names=rng.sample(list(ITEMS),8)
    cells={(x,y):1 for x in range(4,28) for y in range(12,19)}
    for x in range(5,27): cells[(x,15)]=0
    for k,nm in enumerate(names): cells[(7+2*k,15)]=ITEMS[nm]
    cells[(5,13)]=0x23                                # one chip elsewhere so "chips left" starts above 0
    for y in (13,14): cells[(5,y)]=0x23 if y==13 else 0
    boots={}
    for b in (0x20,0x21,0x22,0x23,0x2A,0x2B,0x2C,0x2D):
        if rng.random()<0.15: boots[b]=1
    data=M.level(cells,[((t0<<2)|M.E,6,15)])
    r=run(data,140,boots or None)
    if r is None: res['no start']+=1; continue
    n,emu,rem=r; ok=n==len(emu)==len(rem)
    res[('type%d'%t0,'sync' if ok else 'DIFF')]+=1
    if emu and emu[-1]!='crash':
        a,b=inv(emu[0]),inv(emu[-1])
        ch=tuple(sorted(k for k in a if a[k]!=b[k] and not k.startswith('time')))
        seen['type%d'%t0].add(ch)
    if not ok: print('DIFF',it,t0,names,n,(inv(emu[n]) if n<len(emu) and emu[n]!='crash' else emu[n:n+1]),(inv(rem[n]) if n<len(rem) and rem[n]!='crash' else rem[n:n+1]),flush=True)
print(dict(res))
for k,v in seen.items(): print(k,'inventory changes seen:',sorted(v))
