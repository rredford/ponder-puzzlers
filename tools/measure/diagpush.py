"""Diagonal block push without moving (community report): Chip pushes against a wall, then very briefly pushes
diagonally (wall direction + block direction) against a neighbouring block; the block moves, Chip does not.
Lock-step against the original. Chip at (X,Y), wall on side W, block on a perpendicular side B with floor beyond."""
import sys
sys.path.insert(0, '/home/claude/remake/tools/measure'); sys.path.insert(0, '/home/claude/verify')
import measure as M, cxx_lock as C
X, Y = 12, 12
D = [M.N, M.E, M.S, M.W]
def room(w, b):
    cells = {(x, y): 0 for x in range(6, 19) for y in range(6, 19)}
    cells[(X + M.DX[w], Y + M.DY[w])] = 1                       # the wall
    bx, by = X + M.DX[b], Y + M.DY[b]
    return M.level(cells, [(0x04 | w, X, Y), (0x00 | (7 << 2) | b, bx, by)]), (bx, by)
def pos(s, i): S = bytes.fromhex(s); return S[128 + i], S[256 + i]
if __name__ == '__main__':
    tot = ok = 0; res = {}; ex = []; bad = []
    for w in D:
        for b in D:
            if b in (w, (w + 2) % 4): continue
            data, (bx, by) = room(w, b)
            for pre in (0, 1, 2, 3, 6):                          # ticks pushing the wall first
                for t0 in range(1, 5):                          # when the wall push starts (tick phase)
                    for dl in (1, 2, 3, 4):                     # length of the diagonal press
                        inputs = {t: {w} for t in range(t0, t0 + pre)}
                        inputs.update({t: {w, b} for t in range(t0 + pre, t0 + pre + dl)})
                        r = C.run_both(data, inputs, t0 + pre + dl + 20, start=True)
                        if r is None: continue
                        m, le, lc, el, cl = r; good = m == le == lc; tot += 1; ok += good
                        if not good: bad.append(('NESW'[w], 'NESW'[b], pre, t0, dl, m))
                        S = el[-1] if el[-1] != 'crash' else el[-2]
                        blk = pos(S, 1) != (bx * 8, by * 8); chip = pos(S, 0) != (X * 8, Y * 8)
                        k = ('block moved' if blk else 'block stayed') + ', ' + ('Chip moved' if chip else 'Chip stayed')
                        res[k] = res.get(k, 0) + 1
                        if blk and not chip and len(ex) < 12: ex.append(('wall ' + 'NESW'[w], 'block ' + 'NESW'[b], 'pre', pre, 't0', t0, 'diag', dl))
    print('diagonal push rooms: %d scenarios, %d match' % (tot, ok))
    for k, v in sorted(res.items()): print('  %-30s %d' % (k, v))
    for e in ex: print('  e.g.', e)
    for b_ in bad[:10]: print('DIFF', b_)
