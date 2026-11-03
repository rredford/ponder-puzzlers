"""Group 2: teleports while the cell lookup is stale (code 38 at x = 96, doc 04 §4.4).  A ball is made to arrive
on a teleport while the stale cell is S = (20,9) (Chip parked mid-map); the grid varies the tile on S, the link
bytes of S (x, y of the next teleport) and the tile there.  Original and remake are run in lock-step."""
import sys, itertools
sys.path.insert(0, '/home/claude/remake/tools/measure'); sys.path.insert(0, '/home/claude/verify')
import measure as M, cxx_lock as C
S = 9 * 32 + 20
def scenario(tS, link, tD, dest=(5, 20), extra={}):
    cells = {(x, y): 0 for x in range(32) for y in range(32)}
    cells[(15, 14)] = 1; cells[(15, 16)] = 0x0E          # ball's first move (stale = Chip's cell) reads (15,16)
    cells[(20, 9)] = tS; cells[dest] = tD; cells.update(extra)
    data = M.level(cells, [(0x04 | M.N, 15, 15), (0x80 | (6 << 2) | M.S, 18, 11)])
    pokes = [(0x3DE2, 0x60), (0x0400 + S, link[0]), (0x0800 + S, link[1])]
    return data, {0: {M.N}}, pokes
def show(R, objs=2):
    return ' '.join('%02x:%.2f,%.2f/u%02x' % (R.r[0x1000 + i], R.r[0x1080 + i] / 8, R.r[0x1100 + i] / 8, R.r[0x1200 + i]) for i in range(objs))
def emu_trace(data, inputs, pokes, T=10):
    R = M.Run(data)
    for a, v in pokes: R.L.ram[a] = v
    out = []
    for k in range(T):
        b = bytes(R.L.ram[0:0x1300]); ok = R.tick(next(iter(inputs[k])) if k in inputs else None); a = bytes(R.L.ram[0:0x1300])
        if not ok: out.append((k, 'HANG')); break
        ch = ['%04X:%02x>%02x' % (x, b[x], a[x]) for x in range(0x0400, 0x1000) if a[x] != b[x]]
        out.append((k, show(R), ch))
    return out
if __name__ == '__main__':
    res = []
    for tS, link, tD in itertools.product((0, 0x0E, 1), ((0, 0), (40, 160)), (0, 0x0E)):
        data, inputs, pokes = scenario(tS, link, tD)
        m, le, lc, el, cl = C.run_both(data, inputs, 10, pokes=pokes)
        ok = m == le == lc
        tr = emu_trace(data, inputs, pokes)
        print('S=%02x link=%s dest=%02x  %s' % (tS, link, tD, 'MATCH' if ok else 'DIFF at %d' % m))
        for t in tr[2:6]: print('     emu', t)
        if not ok and m < len(cl): print('     c++ tick %d: %s' % (m, C.describe(el[m], cl[m]) if m < len(el) else cl[m][:20]))
