import sys; sys.path.insert(0,'/home/claude/verify'); import measure as M
def scen(w, crowd, tick0=5, ticks=12):
    cells={(15,15):0,(31,31):0,(30,31):0}
    for x in range(2,30): cells[(x,5)]=0
    objs=[(0x05,15,15),(0x80|(4<<2)|M.E,3,5)]
    extra=[]
    if crowd:   # objects parked in view (walled in, tanks facing walls: drawn every frame, never move)
        for k in range(crowd):
            x,y=10+(k%10),12+2*(k//10)
            cells[(x,y)]=0; extra.append((0x00|(8<<2)|M.N,x,y))
    objs=objs+extra
    objs=objs+[(0,0,0)]*(w-len(objs))+[(0x80|(8<<2)|M.E,31,31)]
    R=M.Run(M.level(cells,objs)); R.r[0x2F]=tick0; wt=None
    for k in range(ticks):
        ok=R.tick(M.E) if k==0 else R.tick(None)
        if not ok: return (k-wt) if wt is not None else 'crash@%d'%k
        if wt is None and R.state(0)==(0x80|w): wt=k
    return 'none'
for V in (0xD6,0xD9,0xF2,0xD7):
    w=V&0x7F
    print('%02X'%V, ' '.join('crowd %d: %s'%(c, scen(w,c)) for c in (0,10,20,30,40)), '| even:', ' '.join(str(scen(w,c,4)) for c in (0,10,20,30,40)))
