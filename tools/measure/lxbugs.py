"""Tile World's lxbugs.txt test levels (c4 text format, Lynx ruleset) on the emulated original and the remake.
Legend: c4's built-in characters (c4 manual) plus each level's own `tiles` block. Two characters per cell, top
tile first. Objects go into slots in reading order with Chip in slot 0 (as the DAT loader does)."""
import sys, re
sys.path.insert(0,'/home/claude/remake/tools/measure'); sys.path.insert(0,'/home/claude/verify')
import measure as M, cxx_lock as C
N,E_,S,W=M.N,M.E,M.S,M.W
BASE={'#':('t',0x01),'$':('t',0x23),',':('t',0x14),'&':('t',0x13),';':('t',0x03),':':('t',0x28),'?':('t',0x33),'E':('t',0x25),
      'H':('t',0x24),'=':('t',0x02),'6':('t',0x2C),'^':('t',0x05),'v':('t',0x07),'<':('t',0x08),'>':('t',0x06),'@':('o',(1,S)),
      '[':('o',(7,N))}
TWO={'[]':[('o',(7,N))],'^]':[('o',(7,N)),('t',0x2F)],'v]':[('o',(7,S)),('t',0x2F)],'<]':[('o',(7,W)),('t',0x2F)],'>]':[('o',(7,E_)),('t',0x2F)],
     ' |':[('t','thinE')],'_|':[('t',0x2B)],'<>':[('t',0x09)]}
NAMES={'teleport':('t',0x0E),'green button':('t',0x19),'red button':('t',0x30),'toggle wall closed':('t',0x18),'magnet':('t',0x11),
       'fireball east':('o',(4,E_)),'fireball west':('o',(4,W)),'glider east':('o',(5,E_))}
def levels(path):
    txt=open(path).read(); out=[]
    for chunk in txt.split('%%%'):
        m=re.search(r'title\s+(.+)',chunk)
        if not m: continue
        legend={}
        tl=re.search(r'\ntiles\n(.*?)\nend',chunk,re.S)
        if tl:
            for line in tl.group(1).split('\n'):
                ch,nm=line.split('\t',1); legend[ch]=NAMES[nm.strip()]
        rows=re.search(r'\nmap\n(.*?)\nend',chunk,re.S).group(1).split('\n')
        out.append((m.group(1).strip(),legend,rows))
    return out
def build(legend, rows, ox=8, oy=8):
    cells={(x,y):1 for x in range(32) for y in range(32)}; objs=[]
    def look(ch):
        if ch in legend: return legend[ch]
        return BASE.get(ch)
    for y,row in enumerate(rows):
        row=row.ljust(((len(row)+1)//2)*2)
        for x in range(len(row)//2):
            pair=row[2*x:2*x+2]; X,Y=ox+x,oy+y
            parts=TWO.get(pair)
            if parts is None:
                parts=[p for p in (look(pair[0]) if pair[0]!=' ' else None, look(pair[1]) if pair[1]!=' ' else None) if p]
            tile=0x00; ob=None
            for kind,v in parts:
                if kind=='t': tile=0x29 if v=='thinE' else v
                else: ob=v
            cells[(X,Y)]=tile
            if ob: objs.append((ob,X,Y,tile))
    chip=[o for o in objs if o[0][0]==1]; rest=[o for o in objs if o[0][0]!=1]
    slots=[]
    for (t,d),X,Y,tile in chip+rest:
        st=(t<<2)|d
        if tile in (0x2F,0x2D): st|=0x80              # templates and trapped objects carry the moving flag
        slots.append((st,X,Y))
    return M.level(cells,slots), cells, slots
START=True
def lock(data, inputs, T):
    r=C.run_both(data,inputs,T,start=START)
    if r is None: return None
    m,le,lc,el,cl=r
    return m==le==lc, m, el, cl, C.run_both.outofsync
