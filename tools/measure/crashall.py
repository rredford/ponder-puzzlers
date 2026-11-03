import sys; sys.path.insert(0,'/tmp/claude-0'); sys.path.insert(0,'/home/claude/remake/tools/measure')
import tws, edgestop
from multiprocessing import Pool
SETS=[('CCLP1','/home/claude/cclp1/CCLP1-Lynx.dac.tws','/tmp/claude-0/lx/CCLP1','oracle_cclp1_strict.tsv'),
      ('CCLP5','/home/claude/packs/CCLP5.tws','/home/claude/packs/lx_CCLP5','oracle_cclp5_strict.tsv'),
      ('geo5-1','/home/claude/packs/geo5-1.tws','/home/claude/packs/lx_geo5-1','oracle_geo5_1_strict.tsv'),
      ('Joshie','/home/claude/packs/Joshie.tws','/home/claude/packs/lx_Joshie','oracle_joshie_ms_strict.tsv'),
      ('Jacques','/home/claude/packs/Jacques.tws','/home/claude/packs/lx_Jacques','oracle_jacques_ms_strict.tsv')]
jobs=[]
for name,tf,bd,of in SETS:
    for line in open('/home/claude/remake/tests/'+of):
        if line.startswith('#'): continue
        p=line.split()
        if 'crash' in p: jobs.append((name,int(p[0]),tf,bd,p))
_recs={}
def work(j):
    name,lv,tf,bd,p=j
    if tf not in _recs: _recs[tf]={r['level']:r for r in tws.parse(tf)['recs'] if r.get('moves')}
    rec=_recs[tf].get(lv)
    if rec is None: return (name,lv,'norec',None,None)
    data=open('%s/%d.bin'%(bd,lv),'rb').read()
    o,t,info=edgestop.run(rec,data)
    return (name,lv,o,t,info)
if __name__=='__main__':
    print(len(jobs),'crash replays',flush=True)
    with Pool(8) as P: res=P.map(work,jobs,chunksize=2)
    import collections, json
    print(collections.Counter(r[2] for r in res))
    json.dump(res,open('/tmp/claude-0/crashall.json','w'))
    for r in res:
        if r[2]!='edge': print(r)
