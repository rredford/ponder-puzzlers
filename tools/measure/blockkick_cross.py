"""Block kick, monster crossing the cell beyond the block (see blockkick_lane.py)."""
import sys, collections; sys.path.insert(0,'/home/claude/remake/tools/measure'); sys.path.insert(0,'/home/claude/verify')
import blockkick as B, cxx_lock as C, measure as M
B.MONS[9]='walker'; B.MONS[10]='blob'
ROW=15
def lvl(mt, k, d, t0, hold, gap):
    cells = {(x, ROW): 0 for x in range(5, 30)}
    for y in range(ROW - 10, ROW + 11): cells[(7 + gap, y)] = 0
    y0 = ROW - k if d == M.S else ROW + k
    objs = [(0x04 | M.E, 5, ROW), (0x00 | (7 << 2) | M.E, 6, ROW), (0x80 | (mt << 2) | d, 7 + gap, y0)]
    inputs = {0: {M.W}}                       # tap west into the wall: the game starts before the push
    inputs.update({t: {M.E} for t in range(t0, t0 + (14 if hold else 1))})
    return M.level(cells, objs), inputs
tot=ok=0; out=collections.Counter(); kicks=[]; bad=[]
for mt in B.MONS:
    for d in (M.S, M.N):
        for k in (1,2,3):
            for gap in (0,1):
                for t0 in range(1, 17):
                    for hold in (False,True):
                        data,inputs=lvl(mt,k,d,t0,hold,gap)
                        r=C.run_both(data,inputs,44)
                        if r is None: continue
                        m,le,lc,el,cl=r; good=m==le==lc; tot+=1; ok+=good
                        if not good: bad.append((B.MONS[mt],'NESW'[d],k,gap,t0,hold,m))
                        for t in range(1,len(el)):
                            if 'crash' in (el[t],el[t-1]): break
                            b0,b1=B.pos(el[t-1],1),B.pos(el[t],1); c0,c1=B.pos(el[t-1],0),B.pos(el[t],0)
                            if b1!=b0 and b0==(48,120) and c1==c0==(40,120): kicks.append((B.MONS[mt],'NESW'[d],k,gap,t0,hold,t)); break
                        S=bytes.fromhex(el[-1]) if el[-1]!='crash' else None
                        out['chip dead' if S and S[0]&0x40 or (S and S[0]==0) else 'block moved' if S and (S[129],S[257])!=(48,120) else 'block stayed']+=1
print('crossing-monster rooms: %d scenarios, %d match'%(tot,ok)); print(out); print('kicks:',len(kicks),kicks[:10]); print(bad[:10])
