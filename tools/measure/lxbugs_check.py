import sys; sys.path.insert(0,'/home/claude/remake/tools/measure'); sys.path.insert(0,'/home/claude/verify')
import lxbugs as X, measure as M, cxx_lock as C
X.START=False
L={t:(leg,rows) for t,leg,rows in X.levels('/tmp/claude-0/lxbugs/lxbugs.txt')}
N,E,S,W=M.N,M.E,M.S,M.W
def seq(*steps, start=0):
    inp={}; t=start
    for d,n in steps:
        for k in range(n):
            if d is not None: inp[t]={d}
            t+=1
    return inp
def walk(*dirs): return seq(*[(d,4) for d in dirs])
def run(title, inp, T):
    leg,rows=L[title]; data,cells,slots=X.build(leg,rows)
    ok,m,el,cl,ns=X.lock(data,inp,T)
    Sx=[bytes.fromhex(x) for x in el if x!='crash']
    return ok,m,ns,el[-1]=='crash',len(el),Sx
def objs(B): return [(i,'%02X'%B[i],B[128+i]//8-8,B[256+i]//8-8) for i in range(128) if B[i]]
def tile(B,x,y): return '%02X'%B[512+(8+y)*32+8+x]
for title,inp,T,what in (
  ('Stuck Teleport I',seq((W,1)),800,'death'),('Stuck Teleport II',seq((W,1)),600,'blocks'),('Stuck Teleport III',seq((W,1)),600,'blocks'),
  ('Ghost Block',seq((N,1)),120,'block'),('Ghost Block',walk(W,N,N),120,'block'),('Ghost Block',walk(W,N,N,N),120,'block'),
  ('Mag-Lev',walk(E,S,E,N),80,'water'),('Mag-Lev',walk(E,S,S,E,N,N),100,'water'),
  ('Pass Through',seq((N,1)),60,'end'),('Pass Through',seq((N,20)),60,'end')):
    ok,m,ns,crash,n,Sx=run(title,inp,T)
    head='%-18s %-28s %s notice %s'%(title,str(sorted(set(tuple(v)[0] for v in inp.values())))[:28],'sync' if ok else 'DIFF@%d'%m,ns)
    if what=='death':
        d=next((t for t,B in enumerate(Sx) if B[0]&0x40 or not B[0]),None)
        tp=[(B[128]//8-8,B[256]//8-8) for B in Sx]; alt=sum(1 for a,b in zip(tp,tp[1:]) if a!=b)
        print(head,'| Chip changes cell',alt,'times | dies at tick',d,'at',tp[d] if d is not None else None,'| tiles at the teleports at the end:',tile(Sx[-1],6,3),tile(Sx[-1],6,4))
    elif what=='blocks':
        b0=[o for o in objs(Sx[0]) if o[1] in ('1C','9C')]; b1=[o for o in objs(Sx[-1]) if o[1][1] in 'CDEF' and int(o[1],16)>>2&15==7]
        print(head,'| blocks start',[(o[2],o[3]) for o in b0],'end',[(o[2],o[3]) for o in b1],'| Chip end',(Sx[-1][128]//8-8,Sx[-1][256]//8-8))
    elif what=='block':
        bl=[(B[129]//8-8,B[257]//8-8) for B in Sx]; seen=[]
        for c in bl:
            if not seen or seen[-1]!=c: seen.append(c)
        print(head,'| block cells',seen[:12],'| Chip',('dead' if Sx[-1][0]&0x40 else 'alive'))
    elif what=='water':
        print(head,'| block at',(Sx[-1][129]//8-8,Sx[-1][257]//8-8),'| water cell (4,1) now',tile(Sx[-1],4,1))
    else:
        print(head,'| ends in','CRASH/HANG' if crash else 'no crash','after',n,'ticks | last objs',objs(Sx[-1]) if Sx else '')
