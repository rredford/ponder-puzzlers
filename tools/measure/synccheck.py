"""How well does the remake's "out of sync" flag (a stale lookup read RAM the remake does not track) predict a
mismatch with the original?  Uses drawtest's random scenarios.   usage: synccheck.py N SEED [CODE...]"""
import sys, random
sys.path.insert(0, '/home/claude/remake/tools/measure'); sys.path.insert(0, '/home/claude/verify')
import drawtest as D, cxx_lock as C
n = int(sys.argv[1]); rng = random.Random(int(sys.argv[2])); codes = [int(c, 16) for c in sys.argv[3:]] or D.CODES
t = dict(match_noflag=0, match_flag=0, miss_flag_before=0, miss_flag_after=0, miss_noflag=0)
for it in range(n):
    data, inputs = D.scenario(rng, codes[it % len(codes)])
    r = C.run_both(data, inputs, 48)
    if r is None: continue
    m, le, lc, el, cl = r; f = C.run_both.outofsync
    ok = m == le == lc
    if ok: t['match_flag' if f is not None else 'match_noflag'] += 1
    elif f is None: t['miss_noflag'] += 1
    elif f <= m: t['miss_flag_before'] += 1
    else: t['miss_flag_after'] += 1
print(t)
