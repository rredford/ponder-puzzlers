import sys; sys.path.insert(0,'/home/claude/verify'); import measure as M
def run(A, vals, T=14, mv=None, chip=(15,15)):
    cells={(x,y):0 for x in range(32) for y in range(32)}
    R=M.Run(M.level(cells,[(0x04|M.E,*chip)]))
    for k in range(T):
        if not R.tick(mv(k) if mv else None): return k
        for i,v in enumerate(vals): R.L.ram[A+i]=v
    return None
def sym(d): return '.' if d is None else ('%x'%d if d<16 else '+')
if __name__=='__main__':
    for A,name in ((0x2F00,'6E'),(0x2FAC,'61')):
        print(name,'x lo sweep (y=75):')
        s=''.join(sym(run(A,[v,0,75,0])) for v in range(256)); print('\n'.join(s[i:i+64] for i in range(0,256,64)))
        print(name,'y lo sweep (x=75):')
        s=''.join(sym(run(A,[75,0,v,0])) for v in range(256)); print('\n'.join(s[i:i+64] for i in range(0,256,64)))
        print(name,'hi bytes FF:', sym(run(A,[75,0xFF,75,0])), sym(run(A,[75,0,75,0xFF])), sym(run(A,[75,0xFF,75,0xFF])))
