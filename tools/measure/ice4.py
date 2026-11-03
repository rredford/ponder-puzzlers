"""icetest.py and iceblock.py in all four orientations: the corridor runs along the axis the first actor moves
on (E, W, S or N); everything else as in those scripts.   usage: ice4.py corridor|block [quick]"""
import sys
sys.path.insert(0, '/home/claude/remake/tools/measure'); sys.path.insert(0, '/home/claude/verify')
import measure as M, cxx_lock as C
FWD = {M.E: M.E, M.W: M.W, M.S: M.S, M.N: M.N}
OPP = {M.E: M.W, M.W: M.E, M.S: M.N, M.N: M.S}
def place(d, u, v):
    """u: position along the run (2..29, increasing in direction d), v: perpendicular offset (row/col 15 + v)."""
    if d == M.E: return (u, 15 + v)
    if d == M.W: return (31 - u, 15 + v)
    if d == M.S: return (15 + v, u)
    return (15 + v, 31 - u)
def corridor(d, left, right, gap, t0, mv):
    P = lambda u, v=0: place(d, u, v)
    cells = {}
    for u in range(2, 30): cells[P(u, -1)] = 1; cells[P(u, 1)] = 1; cells[P(u)] = 0x02
    cells[P(2)] = 1; cells[P(29)] = 1
    ul, ur = 6, 6 + gap
    objs = []; inputs = {}; chip = None
    if left == 1: chip = P(ul); cells[P(ul)] = 0; cells[P(ul - 1)] = 0; inputs[t0] = {d}
    elif left == 7: chip = P(ul - 1); cells[P(ul - 1)] = 0; cells[P(ul - 2)] = 0; inputs[t0] = {d}
    if right == 1: chip = P(ur); inputs.setdefault(t0, set()).add(OPP[d])
    if chip is None:
        side = place(d, 15, -3); wall = place(d, 15, -4)
        cells[side] = 0; cells[wall] = 1; chip = side
        away = {M.E: M.N, M.W: M.S, M.S: M.W, M.N: M.E}[d]     # pressing towards the wall starts the level
        inputs.setdefault(0, {away})
    objs.append((0x04 | d, *chip))
    if left == 7: objs.append(((7 << 2) | d, *P(ul)))
    elif left != 1: objs.append((0x80 | (left << 2) | d, *P(ul)))
    if right == 7: objs.append(((7 << 2) | OPP[d], *P(ur)))
    elif right != 1: objs.append(((0x80 if mv else 0) | (right << 2) | OPP[d], *P(ur)))
    return M.level(cells, objs), inputs, None
def block(d, dist, t0, bt, beyond, skates, hold):
    P = lambda u, v=0: place(d, u, v)
    cells = {}
    for u in range(2, 30): cells[P(u, -1)] = 1; cells[P(u, 1)] = 1; cells[P(u)] = 0x02
    cells[P(2)] = 1; cells[P(29)] = 1
    uc = 5; cells[P(uc)] = 0; cells[P(uc - 1)] = 0
    ub = uc + dist; cells[P(ub)] = bt
    objs = [(0x04 | d, *P(uc)), ((7 << 2) | d, *P(ub))]
    kind = beyond[0]
    if kind == 'wall': cells[P(ub + 1)] = 1
    elif kind == 'block': objs.append(((7 << 2) | d, *P(ub + 1))); cells[P(ub + 2)] = 1
    elif kind == 'monster': objs.append(((beyond[1] << 2) | OPP[d], *P(ub + 1))); cells[P(ub + 2)] = 1
    inputs = {t0: {d}}
    if hold:
        for k in range(t0, t0 + 40): inputs[k] = {d}
    return M.level(cells, objs), inputs, ({0x20: 1} if skates else None)
if __name__ == '__main__':
    which = sys.argv[1]; quick = len(sys.argv) > 2
    res = {}
    bad = []
    for d in (M.E, M.W, M.S, M.N):
        cases = []
        if which == 'corridor':
            actors = [1, 7, 2, 3, 4, 5, 6, 8, 9, 10, 11]
            for l in actors:
                for r in actors:
                    if l == r == 1: continue
                    for gap in range(2, 8 if quick else 10):
                        for t0 in ((0, 1) if quick else (0, 1, 2, 3)):
                            for mv in ((True, False) if r not in (1, 7) else (True,)):
                                cases.append(lambda d=d, a=(l, r, gap, t0, mv): corridor(d, *a))
        else:
            for dist in range(1, 8):
                for t0 in range(4):
                    for bt in (0x02, 0x00):
                        for beyond in (('none',), ('wall',), ('block',), ('monster', 8), ('monster', 11), ('monster', 6)):
                            for sk in (False, True):
                                for hold in (False, True):
                                    cases.append(lambda d=d, a=(dist, t0, bt, beyond, sk, hold): block(d, *a))
        t = [0, 0]
        for mk in cases:
            data, inputs, boots = mk()
            r = C.run_both(data, inputs, 60, boots=boots)
            if r is None: continue
            m, le, lc, el, cl = r; ok = m == le == lc
            t[0] += 1; t[1] += ok
            if not ok and len(bad) < 10: bad.append(('NESW'[d], m, C.describe(el[m], cl[m]) if m < min(le, lc) else 'len %d/%d' % (le, lc)))
        res['NESW'[d]] = t
        print(which, 'direction', 'NESW'[d], ': %d scenarios, %d match' % tuple(t), flush=True)
    for b in bad: print('DIFF', b)
