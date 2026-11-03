import sys, json; sys.path.insert(0,'/home/claude/verify'); import cxx_lock as C, measure as M
# Chip sealed at (15,15) with junk state s; one monster of type t walks a long corridor (its AI runs whenever aligned)
res = {}
STATES = [s for s in range(256) if s not in range(0x04, 0x08) and s not in range(0x84, 0x88)]
for s in STATES:
    row = ''
    for t in range(2, 12):
        cells = {(15, 15): 0}
        for x in range(2, 30): cells[(x, 5)] = 0
        data = M.level(cells, [(0x04 | M.N, 15, 15), (0x80 | (t << 2) | M.E, 3, 5)])
        r = C.run_both(data, {0: {M.N}}, 12, pokes=[(0x1000, s)])
        n, le, lc, el, cl = r
        e = el[-1] == 'crash'; c = cl[-1] == 'crash'
        row += '=' if n == le == lc else ('D' if e and not c else 'd' if c and not e else '!')
    res[s] = row
json.dump(res, open('/tmp/claude-0/chipjunk2.json', 'w'))
from collections import defaultdict
g = defaultdict(list)
for s, row in res.items(): g[row].append('%02X' % s)
print('columns: monster types 2..11; = match, D = original crashes only, d = remake crashes only, ! other')
for k, v in sorted(g.items(), key=lambda kv: -len(kv[1])): print(k, '|', len(v), ' '.join(v))
