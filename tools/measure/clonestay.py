"""Chip starts on a clone machine with no button anywhere: can he walk off it?  Lock-step against the original."""
import sys
sys.path.insert(0, '/home/claude/remake/tools/measure'); sys.path.insert(0, '/home/claude/verify')
import measure as M, cxx_lock as C
X, Y = 15, 10
def run(face, push, t0, hold):
    cells = {(x, y): 0 for x in range(10, 21) for y in range(5, 16)}
    cells[(X, Y)] = 0x2F
    for x in range(9, 22): cells[(x, 4)] = cells[(x, 16)] = 1
    for y in range(4, 17): cells[(9, y)] = cells[(21, y)] = 1
    data = M.level(cells, [(0x04 | face, X, Y)])
    inputs = {k: {push} for k in range(t0, t0 + (40 if hold else 1))}
    r = C.run_both(data, inputs, 60)
    m, le, lc, el, cl = r
    S = bytes.fromhex(el[-1]) if el[-1] != 'crash' else None
    pos = (S[128], S[256]) if S else 'crash'
    return pos, m == le == lc, (m, le, lc)
if __name__ == '__main__':
    names = 'NESW'; res = {}; ok = tot = 0
    for face in range(4):
        for push in range(4):
            for t0 in range(4):
                for hold in (False, True):
                    pos, good, info = run(face, push, t0, hold)
                    tot += 1; ok += good
                    res.setdefault((names[push], hold), set()).add(pos)
                    if not good: print('DIFF', names[face], names[push], t0, hold, info)
    for k, v in sorted(res.items()): print('push %s %s -> Chip ends at %s' % (k[0], 'held' if k[1] else 'tap', sorted(v, key=str)))
    print('%d scenarios, %d match' % (tot, ok))
