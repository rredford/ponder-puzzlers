"""Ice corners in the path (small sample): an L-shaped ice run - a row heading for an ice corner that turns it into
a column - with two actors meeting around the corner, and Chip sliding round the corner into a block.  Both
mirror images (row heading east or west).  Lock-step against the original."""
import sys, random
sys.path.insert(0, '/home/claude/remake/tools/measure'); sys.path.insert(0, '/home/claude/verify')
import measure as M, cxx_lock as C
ROW, CC = 10, 16                          # the row, and the corner's column
def L(mirror):
    """returns cells of the L run and a mapper: row positions u (approach) and column positions w (after the turn)."""
    sgn = -1 if mirror else 1
    xc = CC
    cells = {}
    def R(u): return (xc - sgn * (CC - u), ROW)          # u < CC on the approach row
    def Cl(w): return (xc, ROW + w)                       # w >= 1 below the corner
    for u in range(3, CC): cells[R(u)] = 0x02; cells[(R(u)[0], ROW - 1)] = 1; cells[(R(u)[0], ROW + 1)] = 1
    for w in range(1, 18): cells[Cl(w)] = 0x02; cells[(xc - 1, ROW + w)] = 1; cells[(xc + 1, ROW + w)] = 1
    cells[R(2)] = 1; cells[Cl(18)] = 1
    cells[(xc, ROW)] = 0x0C if mirror else 0x0B         # walls N+E (heading E turns S); mirrored: N+W (0A)
    if mirror: cells[(xc, ROW)] = 0x0A
    cells[(xc, ROW - 1)] = 1; cells[(xc + sgn, ROW)] = 1; cells[(xc - sgn, ROW + 1)] = 1
    return cells, R, Cl, (M.E if not mirror else M.W)
def meet(left, right, gap, t0, mirror):
    cells, R, Cl, d = L(mirror)
    ul = CC - 4; wr = gap                                  # left actor 4 cells before the corner, right one gap cells below it
    objs = []; inputs = {}; chip = None
    if left == 1: chip = R(ul); cells[R(ul)] = 0; cells[R(ul - 1)] = 0; inputs[t0] = {d}
    elif left == 7: chip = R(ul - 1); cells[R(ul - 1)] = 0; cells[R(ul - 2)] = 0; inputs[t0] = {d}
    if right == 1: chip = Cl(wr); inputs.setdefault(t0, set()).add(M.N)
    if chip is None: cells[(3, 3)] = 0; cells[(3, 2)] = 1; chip = (3, 3); inputs.setdefault(0, {M.N})
    objs.append((0x04 | d, *chip))
    if left == 7: objs.append(((7 << 2) | d, *R(ul)))
    elif left != 1: objs.append((0x80 | (left << 2) | d, *R(ul)))
    if right == 7: objs.append(((7 << 2) | M.N, *Cl(wr)))
    elif right != 1: objs.append((0x80 | (right << 2) | M.N, *Cl(wr)))
    return M.level(cells, objs), inputs, None
def chipblock(dist, t0, bt, beyond, skates, mirror):
    cells, R, Cl, d = L(mirror)
    uc = CC - 3; cells[R(uc)] = 0; cells[R(uc - 1)] = 0
    objs = [(0x04 | d, *R(uc)), ((7 << 2) | M.S, *Cl(dist))]
    cells[Cl(dist)] = bt
    if beyond == 'wall': cells[Cl(dist + 1)] = 1
    elif beyond == 'block': objs.append(((7 << 2) | M.S, *Cl(dist + 1))); cells[Cl(dist + 2)] = 1
    elif beyond == 'tank': objs.append(((8 << 2) | M.N, *Cl(dist + 1))); cells[Cl(dist + 2)] = 1
    return M.level(cells, objs), {t0: {d}}, ({0x20: 1} if skates else None)
if __name__ == '__main__':
    rng = random.Random(1)
    actors = [1, 7, 2, 3, 4, 5, 6, 8, 9, 10, 11]
    tot = ok = 0; bad = []
    for mirror in (False, True):
        for l in actors:
            for r in actors:
                if l == r == 1: continue
                for gap in (2, 3, 4, 5, 6):
                    t0 = rng.randrange(3)
                    data, inp, boots = meet(l, r, gap, t0, mirror)
                    res = C.run_both(data, inp, 60, boots=boots)
                    if res is None: continue
                    m, le, lc, el, cl = res; g = m == le == lc; tot += 1; ok += g
                    if not g and len(bad) < 10: bad.append(('meet', l, r, gap, t0, mirror, m, C.describe(el[m], cl[m]) if m < min(le, lc) else 'len'))
    print('two actors around an ice corner: %d scenarios, %d match' % (tot, ok), flush=True)
    tot2 = ok2 = 0
    for mirror in (False, True):
        for dist in range(1, 6):
            for t0 in range(3):
                for bt in (0x02, 0x00):
                    for beyond in ('none', 'wall', 'block', 'tank'):
                        for sk in (False, True):
                            data, inp, boots = chipblock(dist, t0, bt, beyond, sk, mirror)
                            res = C.run_both(data, inp, 50, boots=boots)
                            if res is None: continue
                            m, le, lc, el, cl = res; g = m == le == lc; tot2 += 1; ok2 += g
                            if not g and len(bad) < 20: bad.append(('block', dist, t0, bt, beyond, sk, mirror, m, C.describe(el[m], cl[m]) if m < min(le, lc) else 'len'))
    print('Chip round an ice corner into a block: %d scenarios, %d match' % (tot2, ok2))
    for b in bad: print('DIFF', b)
