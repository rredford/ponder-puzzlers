"""Accuracy test for drawing odd tile codes (doc 04 §4.4): random small levels with one of the 17 codes that
affect play somewhere near Chip, random tiles and monsters, random input; the C++ engine is lock-stepped
against the emulated original, with and without its drawing pass.

usage: python3 drawtest.py N [SEED] [CODE...]"""
import sys, random, json
sys.path.insert(0, '/home/claude/verify')
sys.path.insert(0, '/home/claude/remake/tools/measure')
import measure as M, cxx_lock as C
CODES = [0x3F, 0x47, 0x45, 0x39, 0x3B, 0x3D, 0x44, 0x5C, 0x62, 0x64, 0x7B, 0x7D, 0x60, 0x7F, 0x61, 0x6E, 0x38]
LINK = {0x39: 0xBB9, 0x3B: 0xAD7, 0x3D: 0x917, 0x44: 0xB99, 0x7B: 0xA9F, 0x7D: 0x870, 0x5C: 0x52D, 0x62: 0x430, 0x64: 0x4A7}
PAL = [0] * 14 + [1, 1, 0x1E, 0x1F, 0x20, 0x21, 0x2B, 0x2C, 0x2D, 0x2E, 0x0E, 0x02, 0x06, 0x14, 0x13, 0x03, 0x23, 0x0F, 0x29, 0x2A, 0x19, 0x17, 0x18]
def scenario(rng, code):
    if code in LINK:
        k = LINK[code] - (0x400 if LINK[code] < 0x800 else 0x800) + rng.randrange(4)
        fx, fy = k % 32, k // 32
    elif code == 0x138:                     # 38 at column 29 with the camera clamped at the right edge: x = 96
        fx, fy = 29, rng.randrange(1, 31)
    else:
        fx, fy = rng.randrange(1, 31), rng.randrange(1, 31)
    px = min(max(fx + rng.randrange(-3, 4), 1), 30); py = min(max(fy + rng.randrange(-3, 4), 1), 30)
    if code == 0x138: px = rng.randrange(28, 31)
    cells = {}
    for x in range(max(px - 6, 0), min(px + 7, 32)):
        for y in range(max(py - 6, 0), min(py + 7, 32)):
            cells[(x, y)] = rng.choice(PAL)
    if code in LINK: cells[(fx, fy)] = rng.choice([0x2E, 0x0E, 0x30, 0x2E])
    cells[(px, py)] = 0
    while code == 0x138:
        ox, oy = fx, fy
        if (ox, oy) != (px, py): break
        fy = rng.randrange(1, 31)
    while code != 0x138:
        ox = px + rng.randrange(-5, 6); oy = py + rng.randrange(-5, 6)
        if (ox, oy) != (px, py) and 0 <= ox < 32 and 0 <= oy < 32: break
    cells[(ox, oy)] = code & 0xFF
    objs = [(0x04 | rng.randrange(4), px, py)]
    for _ in range(rng.randrange(4)):
        mx = px + rng.randrange(-5, 6); my = py + rng.randrange(-5, 6)
        if (mx, my) in cells and (mx, my) not in ((px, py), (ox, oy)) and all((mx, my) != (o[1], o[2]) for o in objs):
            cells[(mx, my)] = 0
            objs.append((0x80 | (rng.choice([2, 3, 4, 5, 6, 7, 8, 10]) << 2) | rng.randrange(4), mx, my))
    inputs = {}
    d = None
    for k in range(48):
        if rng.random() < 0.3: d = rng.choice([M.N, M.E, M.S, M.W, None, None])
        if d is not None: inputs[k] = {d}
    return M.level(cells, objs), inputs
if __name__ == '__main__':
    n = int(sys.argv[1]); seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    codes = [int(c, 16) for c in sys.argv[3:]] or CODES
    rng = random.Random(seed)
    tot = {}
    fails = []
    for it in range(n):
        code = codes[it % len(codes)]
        data, inputs = scenario(rng, code)
        res = {}
        for nd in (False, True):
            r = C.run_both(data, inputs, 48, nodraw=nd)
            if r is None: res = None; break
            m, le, lc, el, cl = r
            res[nd] = (m == le == lc, m, el, cl)
        if res is None: continue
        t = tot.setdefault(code, [0, 0, 0, 0])
        t[0] += 1; t[1] += res[False][0]; t[2] += res[True][0]
        crashed = 'crash' in res[False][2]
        t[3] += crashed
        if not res[False][0]: fails.append((code, it, res[False][1], C.describe(res[False][2][res[False][1]], res[False][3][res[False][1]]) if res[False][1] < min(len(res[False][2]), len(res[False][3])) else 'length %d/%d' % (len(res[False][2]), len(res[False][3]))))
    print('code  runs  match(draw)  match(no draw)  orig crashed')
    for c in codes:
        if c in tot: t = tot[c]; print('  %03X  %4d  %4d         %4d            %4d' % (c, t[0], t[1], t[2], t[3]))
    T = [sum(v[i] for v in tot.values()) for i in range(4)]
    print('total %d: with drawing %d, without %d (original crashed in %d)' % tuple(T))
    for f in fails[:25]: print('FAIL %03X #%d tick %d: %s' % f)
    json.dump(fails, open('/tmp/claude-0/drawtest_fails.json', 'w'))
