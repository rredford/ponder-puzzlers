import sys, json; sys.path.insert(0, '/home/claude/verify')
import cxx_lock as C, fit_odd as F, measure as M
res = {'pass': 0, 'fail': []}
def check(name, data, inputs, ticks, pokes=(), boots=None):
    r = C.run_both(data, inputs, ticks, pokes, boots)
    if r is None: return
    n, le, lc, el, cl = r
    if n == le == lc: res['pass'] += 1
    else:
        res['fail'].append((name, n, C.describe(el[n], cl[n]) if n < min(le, lc) else 'length %d vs %d' % (le, lc)))
# 1. odd codes, every mover that can enter, open room
for code in range(0x34, 0x80):
    for who in [1, 0, 2, 4, 6, 7, 8, 10, 12, 13, 14, 15]:
        for d in range(4):
            row = F.TAB['enter'][str(code)][who - 1] if who else [1, 1, 1, 1]
            if who and not row[d]: continue
            extras = ([], [(8, (d + 1) % 4)]) if who == 1 else ([],)
            for ex in extras:
                if who == 0:
                    data, inputs = F.scenario(code, 2, d, ex)
                    data = bytearray(data); data[0x401] = 0x80 | d; data = bytes(data)   # type 0 mover
                else:
                    data, inputs = F.scenario(code, who, d, ex)
                check('code %02X who %d dir %d %s' % (code, who, d, ex), data, inputs, 16)
print('odd codes:', res['pass'], 'pass,', len(res['fail']), 'fail', flush=True)
# 2. effect frames
for f in range(0x40):
    data = M.level({M.CHIP: 0, (4, 4): 0, (4, 3): 0, (5, 4): 0, (4, 5): 0, (3, 4): 0}, [(0x04 | M.N, *M.CHIP), (0x40 | f, 4, 4)])
    check('effect %02X' % f, data, {0: {M.N}}, 12)
# 3. object references as tiles: tanks standing on them; Chip walking onto one
for V in range(0x80, 0x100):
    base = 1 if (V & 0x7F) >= 64 else 100
    cells = {M.CHIP: 0}; objs = [(0x04 | M.N, *M.CHIP)] + [(0, 0, 0)] * (base - 1)
    for d in range(4):
        x, y = 4 + 6 * d, 5
        for xx in range(x - 1, x + 2):
            for yy in range(y - 1, y + 2): cells[(xx, yy)] = 0
        objs.append((0x80 | (8 << 2) | d, x, y))
    check('ref %02X tanks' % V, M.level(cells, objs), {0: {M.N}}, 12, [(0x1200 + base + d, V) for d in range(4)])
    j = V & 0x7F
    if j:
        cx, cy = 20, 20
        cells = {(x, y): 0 for x in range(cx - 1, cx + 4) for y in range(cy - 2, cy + 3)}
        cells[(cx + 1, cy)] = 0x2D
        objs = [(0x04 | M.E, cx, cy)] + [(0, 0, 0)] * (j - 1) + [(0x04 | M.N, cx + 1, cy)]
        check('ref %02X onto' % V, M.level(cells, objs), {0: {M.E}, 6: {M.N}}, 12)
# 4. corrupted links on row 31
for hi in list(range(0x00, 0x14)) + [0x80, 0x9A]:
    cells = {(5, 30): 0, (5, 31): 0x2E, (10, 5): 0x2D, (11, 5): 0, (12, 5): 0, (10, 13): 0x2D, (11, 13): 0, (12, 13): 0}
    objs = [(0x04 | M.S, 5, 30), (0x80 | (8 << 2) | M.E, 10, 5), (0x80 | (8 << 2) | M.E, 10, 13)]
    check('brown hi %02X' % hi, M.level(cells, objs), {0: {M.S}}, 10, [(0x0BE5, hi)])
    cells = {(5, 30): 0, (5, 31): 0x30, (10, 5): 0x2F, (11, 5): 0, (12, 5): 0, (10, 13): 0x2F, (11, 13): 0, (12, 13): 0}
    check('red hi %02X' % hi, M.level(cells, objs), {0: {M.S}}, 10, [(0x0BE5, hi)])
for y in range(0, 256, 8):
    cells = {(5, 30): 0, (5, 31): 0x0E, (10, 5): 0x0E, (10, 6): 0, (10, 13): 0x0E, (10, 14): 0, (5, 8): 0, (5, 9): 0}
    check('teleport y %d' % y, M.level(cells, [(0x04 | M.S, 5, 30)]), {0: {M.S}}, 10, [(0x0BE5, y)])
print('total', res['pass'], 'pass,', len(res['fail']), 'fail')
json.dump(res, open('/tmp/claude-0/-home-claude/4a4b5c09-bdf2-5f61-92c2-02c1c6ac6cfd/scratchpad/suite.json', 'w'), indent=0)
from collections import Counter
print(Counter(f[0].split()[0] + ' ' + (f[0].split()[3] if f[0].startswith('code') else '') for f in res['fail']).most_common(20))
for f in res['fail'][:25]: print(f)
