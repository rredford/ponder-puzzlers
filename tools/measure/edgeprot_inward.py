import sys, os, json, glob, collections
sys.path.insert(0,'/tmp/claude-0/edgeprot'); sys.path.insert(0,'/home/claude/verify'); sys.path.insert(0,'/home/claude/remake/tools/measure')
exec(open('rerun3.py').read().split("if __name__=='__main__':")[0])   # P, tws, M, protect_v2, protect_v3, SL
R=[]
for f in glob.glob('/tmp/claude-0/edgeprot/res_all_*.json'): R+=json.load(open(f))
part=int(sys.argv[1]); R=[row for k,row in enumerate(R) if k%4==part]
cache={}; out=[]
for row in R:
    name,lv=row[0],row[1]
    tf,bd,of,lynx=P.SETS[name]
    if tf not in cache: cache[tf]={x['level']:x for x in tws.parse(tf)['recs']}
    rec=cache[tf][lv]; raw=open('%s/%d.bin'%(bd,lv),'rb').read(); rf=SL[rec['slide']&3] if lynx else None
    a2=protect_v2(raw); lg=[]; a3=protect_v3(raw,lg)
    o2=P.remake_outcome(a2,rec,rf) if M.Run(a2).ok else ('no-start','')
    o3=o2 if not lg else (P.remake_outcome(a3,rec,rf) if M.Run(a3).ok else ('no-start',''))
    out.append((name,lv,len(lg),o2,o3)); print(name,lv,'moved',len(lg),o2,'->',o3,flush=True)
json.dump(out,open('/tmp/claude-0/edgeprot/rerun4_%d.json'%part,'w'))
