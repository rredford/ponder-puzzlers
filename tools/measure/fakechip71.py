"""Fake Chip (type 1 in slot 1) carried by force floors onto a redirect code, every direction; real Chip parked
elsewhere, with or without skates; cartridge vs remake trajectories."""
import sys; sys.path.insert(0,'/home/claude/remake/tools/measure'); sys.path.insert(0,'/home/claude/verify')
import measure as M, cxx_lock as C
FF={M.N:5,M.E:6,M.S:7,M.W:8}; NM='NESW'
def run(code, d, boots=None, beyond=0x00, T=14, approach=0x07):
    cx,cy=15,15
    cells={(x,y):0 for x in range(4,28) for y in range(4,28)}
    for k in (1,2,3): cells[(cx-k*M.DX[d],cy-k*M.DY[d])]=FF[d] if approach==0x07 else approach
    cells[(cx,cy)]=code; cells[(cx+M.DX[d],cy+M.DY[d])]=beyond
    sx,sy=cx-3*M.DX[d],cy-3*M.DY[d]
    objs=[(0x04,6,25),(0x80|(1<<2)|d,sx,sy)]
    m,le,lc,el,cl=C.run_both(M.level(cells,objs),{},T,boots=boots,start=True)
    f=lambda L:[('X' if x=='crash' else (NM[bytes.fromhex(x)[1]&3]+('m' if bytes.fromhex(x)[1]&0x80 else ' '),(bytes.fromhex(x)[129]-8*cx)*M.DX[d]+(bytes.fromhex(x)[257]-8*cy)*M.DY[d])) for x in L]
    return m==le==lc, C.run_both.outofsync, f(el), f(cl)
for code in (0x71,0x4A,0x43):
    for d in range(4):
        for b in (None,{0x20:1}):
            ok,ns,e,c=run(code,d,b)
            print('%02X moving %s %s %s notice %s\n   emu %s\n   cxx %s'%(code,NM[d],'skates' if b else 'none  ','sync' if ok else 'DIFF',ns,e[4:12],'' if ok else c[4:12]))
