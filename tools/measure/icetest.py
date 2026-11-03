"""Ice collisions, lock-step against the original: two actors meeting on an ice corridor (head-on, or one waiting
at the far end), for Chip, a pushed block and every monster type, with gaps and start ticks varied so the meeting
falls on every sub-step.   usage: icetest.py [quick]"""
import sys, itertools
sys.path.insert(0, '/home/claude/remake/tools/measure'); sys.path.insert(0, '/home/claude/verify')
import measure as M, cxx_lock as C
ROW = 15
NAMES = {1: 'chip', 7: 'block', 2: 'bug', 3: 'paramecium', 4: 'fireball', 5: 'glider', 6: 'ball', 8: 'tank',
         9: 'walker', 10: 'blob', 11: 'teeth'}
def build(left, right, gap, t0, right_moving=True, far=None, ice_from=None):
    """left actor starts at x=6 moving E (Chip / block start on floor and enter the ice at tick t0);
    right actor starts at 6+gap facing W (moving or not). far: tile at the corridor's east end."""
    xl, xr = 6, 6 + gap
    cells = {(x, y): 1 for x in range(2, 30) for y in (ROW - 1, ROW + 1)}
    for x in range(2, 30): cells[(x, ROW)] = 0x02
    cells[(2, ROW)] = 1; cells[(29, ROW)] = 1
    if far is not None: cells[(xr + 1, ROW)] = far
    objs = []; inputs = {}
    chip = None
    if left == 1: chip = (xl, ROW); cells[(xl, ROW)] = 0; cells[(xl - 1, ROW)] = 0; inputs[t0] = {M.E}
    elif left == 7: chip = (xl - 1, ROW); cells[(xl - 1, ROW)] = 0; cells[(xl - 2, ROW)] = 0; inputs[t0] = {M.E}
    if right == 1: chip = (xr, ROW)
    if chip is None:                                   # Chip parked out of the way, level started by a blocked press
        cells[(15, ROW - 3)] = 0; cells[(15, ROW - 4)] = 1; chip = (15, ROW - 3); inputs.setdefault(0, {M.N})
    objs.append((0x04 | M.E, *chip))
    if left == 7: objs.append((0x00 | (7 << 2) | M.E, xl, ROW))
    elif left != 1: objs.append((0x80 | (left << 2) | M.E, xl, ROW))
    if right == 7: objs.append((0x00 | (7 << 2) | M.W, xr, ROW))
    elif right != 1: objs.append(((0x80 if right_moving else 0) | (right << 2) | M.W, xr, ROW))
    elif right == 1: inputs.setdefault(t0, set()).add(M.W)
    return M.level(cells, objs), inputs
def run(cases, T=60):
    res = []
    for args in cases:
        data, inputs = build(*args)
        r = C.run_both(data, inputs, T)
        if r is None: res.append((args, None)); continue
        m, le, lc, el, cl = r
        res.append((args, (m == le == lc, m, le, lc, el, cl)))
    return res
if __name__ == '__main__':
    quick = len(sys.argv) > 1
    actors = [1, 7, 2, 3, 4, 5, 6, 8, 9, 10, 11]
    cases = []
    for left in actors:
        for right in actors:
            if left == right == 1: continue
            for gap in (range(2, 7) if quick else range(2, 10)):
                for t0 in ((0, 1) if quick else (0, 1, 2, 3)):
                    for mv in ((True, False) if right not in (1, 7) else (True,)):
                        cases.append((left, right, gap, t0, mv))
    res = run(cases)
    by = {}
    bad = []
    for args, r in res:
        if r is None: continue
        k = (NAMES[args[0]], NAMES[args[1]])
        t = by.setdefault(k, [0, 0]); t[0] += 1; t[1] += r[0]
        if not r[0]: bad.append((args, r))
    tot = sum(t[0] for t in by.values()); ok = sum(t[1] for t in by.values())
    print('ice corridor: %d scenarios, %d match' % (tot, ok))
    for k, t in sorted(by.items()):
        if t[0] != t[1]: print('   %-10s -> %-10s %d/%d' % (k[0], k[1], t[1], t[0]))
    for args, r in bad[:12]:
        m, le, lc, el, cl = r[1:]
        print('DIFF', (NAMES[args[0]], NAMES[args[1]]) + args[2:], 'tick', m, C.describe(el[m], cl[m]) if m < min(le, lc) else 'len %d/%d' % (le, lc))
