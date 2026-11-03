"""Random lock-step test for drawing stray objects whose sprite lookup writes into game data (states 68/E8 ->
slot table, 75/F5 -> the cell lookup's row table; doc 04 §4.4).   usage: objdrawtest.py N SEED"""
import sys, random
sys.path.insert(0, '/home/claude/remake/tools/measure'); sys.path.insert(0, '/home/claude/verify')
import measure as M, cxx_lock as C, drawtest as D
n = int(sys.argv[1]); rng = random.Random(int(sys.argv[2]))
tot = {}; fails = []
for it in range(n):
    st = [0x68, 0x75, 0xE8, 0xF5][it % 4]
    px, py = rng.randrange(4, 28), rng.randrange(4, 28)
    cells = {(x, y): rng.choice(D.PAL) for x in range(px - 6, px + 7) for y in range(py - 6, py + 7)}
    cells[(px, py)] = 0
    objs = [(0x04 | rng.randrange(4), px, py)]
    used = {(px, py)}
    while len(objs) < 1 + rng.randrange(2, 6):
        mx, my = px + rng.randrange(-5, 6), py + rng.randrange(-5, 6)
        if (mx, my) in used: continue
        used.add((mx, my)); cells[(mx, my)] = 0
        objs.append((0x80 | (rng.choice([2, 3, 4, 5, 6, 7, 8, 10]) << 2) | rng.randrange(4), mx, my))
    while True:
        sx, sy = px + rng.randrange(-5, 6), py + rng.randrange(-5, 6)
        if (sx, sy) not in used: break
    objs.append((st, sx, sy))
    inputs = {}; d = None
    for k in range(48):
        if rng.random() < 0.3: d = rng.choice([M.N, M.E, M.S, M.W, None])
        if d is not None: inputs[k] = {d}
    cells = {k: v for k, v in cells.items() if 0 <= k[0] < 32 and 0 <= k[1] < 32}
    objs = [o for o in objs if 0 <= o[1] < 32 and 0 <= o[2] < 32]
    data = M.level(cells, objs)
    res = []
    for nd in (False, True):
        r = C.run_both(data, inputs, 48, nodraw=nd)
        if r is None: break
        m, le, lc, el, cl = r; res.append(m == le == lc)
        if not nd and not res[-1]: fails.append((it, '%02X' % st, m))
    if len(res) < 2: continue
    t = tot.setdefault(st, [0, 0, 0]); t[0] += 1; t[1] += res[0]; t[2] += res[1]
for s, t in sorted(tot.items()): print('state %02X: %d runs, match %d (without drawing pass %d)' % (s, *t))
print('fails', fails[:10])
