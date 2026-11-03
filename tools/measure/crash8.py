import sys, subprocess, tempfile, json
sys.path.insert(0,'/home/claude/verify'); sys.path.insert(0,'/home/claude/remake/tools/measure')
import measure as M, cxx_lock as C, tws, emu_only as E
CASES=[('CCLP5',2),('CCLP5',11),('CCLP5',28),('Jacques',258),('Jacques',295),('Jacques',516),('Jacques',644),('Jacques',963)]
def load(p,lv):
    rec=[r for r in tws.parse('/home/claude/packs/%s.tws'%p)['recs'] if r['level']==lv][0]
    data=open('/home/claude/packs/lx_%s/%d.bin'%(p,lv),'rb').read()
    return rec,data
def run(p,lv,extra=400,keep=None):
    rec,data=load(p,lv)
    R=M.Run(data); r=R.r
    script=['globals %d %d %d %d %d %d'%(r[0x2F],r[0x4A]&3,20-r[0x3BDB],C.joy2bits(r[0x1D48]),C.joy2bits(r[0x1D49]),r[0x29])]
    for a in range(0x0400,0x0C00):
        if r[a]: script.append('link %x %x'%(a-0x0400,r[a]))
    moves={}
    for t,d in rec['moves']: moves.setdefault(t,set()).update(E.DM[x] for x in E.dirs(d))
    elog=[]; snaps=[]
    for k in range(rec['moves'][-1][0]+extra):
        jb=0; bits=0
        for d in moves.get(k,()): jb|=M.JOYB[d]; bits|=C.DBIT[d]
        R.L.joy=jb
        try: ok=R.L.run_to([0x3A11],4_000_000)
        except RuntimeError: ok=False
        script.append('tick %x'%bits)
        if not ok: elog.append('crash'); break
        elog.append(C.emu_snap(R))
        if keep: snaps.append(bytes(r[0:0x1400]))
        if r[0x28] or r[0x24]: break
    with tempfile.TemporaryDirectory() as td:
        open(td+'/l.bin','wb').write(data); open(td+'/s.txt','w').write('\n'.join(script)+'\n')
        pr=subprocess.run([C.LP,'raw',td+'/l.bin',td+'/s.txt'],capture_output=True,text=True,timeout=120,env={'CRASH_WHY':'1'})
    out=pr.stdout.split('\n')
    clog=['crash' if l.split()[2]=='crash' else ''.join(l.split()[3:]) for l in out if l.startswith('T ')]
    why=[l for l in pr.stderr.split('\n') if l.startswith('CRASHLINE')]
    sync=[l for l in out if 'outofsync' in l]
    n=0
    for a,b in zip(elog,clog):
        if a!=b: break
        n+=1
    return dict(T=len(elog),emu_last=elog[-1]=='crash',match=n,clen=len(clog),why=why[:1],sync=sync[:1]),snaps
if __name__=='__main__':
    for p,lv in CASES:
        res,_=run(p,lv); print(p,lv,res,flush=True)
