import sys; sys.path.insert(0,'/tmp/claude-0/skr'); sys.path.insert(0,'/home/claude/remake/tools/measure'); sys.path.insert(0,'/home/claude/verify')
import lockrun as LR, measure as M
FF={M.N:5,M.E:6,M.S:7,M.W:8}; NM='NESW'
def chip(src, d, hv, boots, press, code=0x71, T=12):
    cx,cy=15,15
    cells={(x,y):0 for x in range(4,28) for y in range(4,28)}
    p1=(cx-M.DX[d],cy-M.DY[d]); p2=(cx-2*M.DX[d],cy-2*M.DY[d])
    t={'floor':0,'force':FF[d],'ice':2}[src]
    cells[p1]=t; cells[p2]=0 if src=='ice' else t; cells[(cx,cy)]=code
    R=LR.Run(M.level(cells,[(0x04|d,*p2)]),boots,(0x795B,hv)); out=[]
    for k in range(T):
        jb=(0x01 if k==0 else 0)|(M.JOYB[d] if 1<=k<1+press else 0)
        if not R.tick(jb): out.append('X'); break
        out.append((R.r[0x1080]-8*cx)*M.DX[d]+(R.r[0x1100]-8*cy)*M.DY[d])
    return out
def other(who, src, d, hv, code=0x71, T=10):
    cx,cy=15,15
    cells={(x,y):0 for x in range(4,28) for y in range(4,28)}
    sx,sy=cx-M.DX[d],cy-M.DY[d]; t={'floor':0,'force':FF[d],'ice':2}[src]
    cells[(sx,sy)]=t; cells[(sx-M.DX[d],sy-M.DY[d])]=t; cells[(cx,cy)]=code
    ty={'fake':1,'block':7,'tank':8,'ball':6,'glider':5,'fireball':4,'bug':2}[who]
    R=LR.Run(M.level(cells,[(0x04,6,25),(0x80|(ty<<2)|d,sx,sy)]),None,(0x795B,hv)); out=[]
    for k in range(T):
        if not R.tick(0x01 if k==0 else 0): out.append('X'); break
        out.append((R.r[0x1081]-8*cx)*M.DX[d]+(R.r[0x1101]-8*cy)*M.DY[d])
    return out
dep=0; tot=0
for src in ('floor','force','ice'):
    for b,bn in ((None,'none'),({0x20:1},'skates'),({0x21:1},'suction')):
        for d in range(4):
            for press in (1,12):
                a=chip(src,d,0,b,press); c=chip(src,d,0x3C,b,press); tot+=1
                if a!=c: dep+=1
                else: print('chip',src,bn,NM[d],'press',press,'SAME',a)
print('real Chip: byte-dependent',dep,'of',tot)
for who in ('fake','block','tank','ball','glider','fireball','bug'):
    for src in ('floor','force','ice'):
        for d in range(4):
            a=other(who,src,d,0); c=other(who,src,d,0x3C)
            if a!=c: print(who,src,NM[d],'DEPENDS',a,c)
