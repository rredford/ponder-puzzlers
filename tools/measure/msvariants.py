"""MS-ruleset solution files (Joshie, Jacques) on deterministic variants of their levels (current replay protocol,
A on tick 0). Only levels whose replay does not win on the original and that have blobs, walkers or random force
floors (09):
  none     - blobs and walkers removed, random force floors turned into plain floor
  override - blobs and walkers removed, random force floors kept, each use given the direction MSCC gave
             (Tile World's MS-mode log of that solution, in order of use; R is set before every tick)
  override+bw - the same with blobs and walkers kept
Wins are checked tick for tick against the remake.  usage: msvariants.py SET PART NPARTS"""
import sys, re, subprocess, tempfile, collections
sys.path.insert(0,'/home/claude/remake/tools/measure'); sys.path.insert(0,'/home/claude/verify')
import measure as M, cxx_lock as C, tws, inject_run as I
TW2R={1:0,8:1,4:2,2:3}
def ms_events(path):
    ev={}; cur=[]
    for line in open(path):
        if line.startswith('RFF'):
            _,chip,x,y,d,cid=line.split(); cur.append(int(d))
        else:
            m=re.match(r'(\d+)\t(\w+)',line)
            if m: ev[int(m.group(1))]=cur; cur=[]
    return ev
def strip_bw(d):
    d=bytearray(d)
    for i in range(1,128):
        st=d[0x400+i]
        if st and not st&0x40 and ((st>>2)&15) in (9,10): d[0x400+i]=0
    return bytes(d)
def has_bw(d): return any(d[0x400+i] and not d[0x400+i]&0x40 and ((d[0x400+i]>>2)&15) in (9,10) for i in range(1,128))
def moves_of(rec):
    mv={}
    for t,dd in rec['moves']: mv.setdefault(t,set()).update(I.TWDIR.get(dd,()))
    return mv
def replay(data, rec, queue, extra=400):
    R=M.Run(data)
    if not R.ok: return 'no-start',None,{}
    r=R.r; mv=moves_of(rec); q=list(queue) if queue is not None else None; pokes={}
    for t in range(rec['moves'][-1][0]+extra):
        if q:
            v=(r[0x4A]&0xFC)|((TW2R[q[0]]-1)&3); r[0x4A]=v; pokes[t]=[(0x4A,v)]
        r0=r[0x4A]&3
        jb=0x01 if t==0 else 0
        for d in mv.get(t,()): jb|=M.JOYB[d]
        R.L.joy=jb
        try: ok=R.L.run_to([0x3A11],4_000_000)
        except RuntimeError: ok=False
        if not ok: return 'crash',t,pokes
        if q is not None:
            n=((r[0x4A]&3)-r0)&3
            if n: del q[:n]
        if r[0x28]: return 'win',t,pokes
        if r[0x24]: return 'death',t,pokes
    return 'stall',None,pokes
def lockstep(data, rec, pokes, T):
    R=M.Run(data); r=R.r
    script=['globals %d %d %d %d %d %d %d'%(r[0x2F],r[0x4A]&3,20-r[0x3BDB],C.joy2bits(r[0x1D48]),C.joy2bits(r[0x1D49]),r[0x29],int(r[0x37]!=0))]
    for a in range(0x0400,0x0C00):
        if r[a]: script.append('link %x %x'%(a-0x0400,r[a]))
    mv=moves_of(rec); elog=[]
    for k in range(T):
        for a,v in pokes.get(k,()): r[a]=v; script.append('poke %x %x'%(a,v))
        jb=0x01 if k==0 else 0; bits=0x10 if k==0 else 0
        for d in mv.get(k,()): jb|=M.JOYB[d]; bits|=C.DBIT[d]
        R.L.joy=jb
        try: ok=R.L.run_to([0x3A11],4_000_000)
        except RuntimeError: ok=False
        script.append('tick %x'%bits)
        if not ok: elog.append('crash'); break
        elog.append(C.emu_snap(R))
    with tempfile.TemporaryDirectory() as td:
        open(td+'/l.bin','wb').write(data); open(td+'/s.txt','w').write('\n'.join(script)+'\n')
        out=subprocess.run([C.LP,'raw',td+'/l.bin',td+'/s.txt'],capture_output=True,text=True,timeout=900).stdout.split('\n')
    clog=['crash' if l.split()[2]=='crash' else ''.join(l.split()[3:]) for l in out if l.startswith('T ')]
    n=0
    for a,b in zip(elog,clog):
        if a!=b: break
        n+=1
    return n==len(elog)==len(clog)
if __name__=='__main__':
    name,part,np_=sys.argv[1],int(sys.argv[2]),int(sys.argv[3])
    tf='/home/claude/packs/%s.tws'%name; bd='/home/claude/packs/lx_%s'%name
    of='/home/claude/remake/tests/oracle_%s_ms_strict.tsv'%name.lower()
    orc={}
    for l in open(of):
        if l.startswith('#') or not l.strip(): continue
        p=l.rstrip('\n').split('\t'); orc[int(p[0])]=p[2]
    ev=ms_events('/tmp/claude-0/twms/%s_ms.txt'%name.lower())
    recs={r['level']:r for r in tws.parse(tf)['recs'] if r.get('moves')}
    res=collections.Counter()
    for k,lv in enumerate(sorted(recs)):
        if k%np_!=part or lv not in orc or orc[lv]=='win': continue
        try: raw=open('%s/%d.bin'%(bd,lv),'rb').read()
        except FileNotFoundError: continue
        rff=0x09 in raw[:1024]; bw=has_bw(raw)
        if not (rff or bw): continue
        variants=[('none',bytes(0x00 if (i<1024 and b==0x09) else b for i,b in enumerate(strip_bw(raw))),None)]
        if rff and lv in ev:
            variants.append(('override',strip_bw(raw),ev[lv]))
            if bw: variants.append(('override+bw',raw,ev[lv]))
        for vn,data,q in variants:
            o,t,pk=replay(data,recs[lv],q)
            sync=lockstep(data,recs[lv],pk,t+1) if o=='win' else None
            res[(vn,o)]+=1
            print(name,lv,'was',orc[lv],'rff' if rff else '','bw' if bw else '','|',vn,'->',o,t,'| remake in sync' if sync else ('| REMAKE DIFFERS' if sync is False else ''),flush=True)
    for k,v in sorted(res.items()): print('TOTAL',name,k,v)
