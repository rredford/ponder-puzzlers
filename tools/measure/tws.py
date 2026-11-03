import struct
def parse(path):
    d=open(path,'rb').read()
    sig,rules,last,skip=struct.unpack_from('<IBHB',d,0)
    assert sig==0x999B3335, hex(sig)
    p=8+skip; recs=[]; name=None; first=True
    while p+4<=len(d):
        n=struct.unpack_from('<I',d,p)[0]; p+=4
        if n==0xFFFFFFFF: break
        if n==0: continue
        r=d[p:p+n]; p+=n
        if first and r[:6]==b'\0'*6:
            name=r[16:].split(b'\0')[0].decode(); first=False; continue
        first=False
        lvl=r[0]|r[1]<<8; pw=r[2:6].decode('latin1')
        if n==6: recs.append(dict(level=lvl,pw=pw,moves=None)); continue
        flags=r[6]; sd=r[7]; rng=struct.unpack_from('<I',r,8)[0]; total=struct.unpack_from('<I',r,12)[0]
        moves=[]; q=16; t=-1; firstmove=True
        def add(dirn,tf):
            nonlocal t,firstmove
            t = tf if firstmove else t+tf+1
            firstmove=False; moves.append((t,dirn))
        while q<len(r):
            b=r[q]
            if b&3==0:
                for k in range(3): add((b>>(2+2*k))&3,3)
                q+=1
            elif b&3==1:
                add((b>>2)&7,b>>5); q+=1
            elif b&3==2:
                v=r[q]|r[q+1]<<8; add((v>>2)&7,v>>5); q+=2
            elif b&0x10==0:
                v=struct.unpack_from('<I',r,q)[0]; add((v>>2)&3,(v>>5)&0x7FFFF); q+=4   # top byte: not time (MS solutions set it)
            else:
                nb=((b>>2)&3)+2; v=int.from_bytes(r[q:q+nb],'little'); add((v>>5)&0x1FF,v>>14); q+=nb
        recs.append(dict(level=lvl,pw=pw,slide=sd&7,step=(sd>>3)&7,rng=rng,total=total,moves=moves))
    return dict(rules=rules,last=last,name=name,recs=recs)
if __name__=='__main__':
    s=parse('/home/claude/tws/cc1.tws')
    print('rules',s['rules'],'name',s['name'],'records',len(s['recs']))
    for r in s['recs'][:6]+s['recs'][140:]:
        if r['moves'] is None: print(r['level'],r['pw'],'pw only'); continue
        print(r['level'],r['pw'],'slide',r['slide'],'step',r['step'],'total',r['total'],'nmoves',len(r['moves']),'first',r['moves'][:4],'last',r['moves'][-1])
