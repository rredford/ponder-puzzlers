"""Chip sliding on ice into a block (the MSCC "bounce or die" question), lock-step against the original.
Chip enters an ice run from the west; a block waits at distance d: on ice or on floor, free to move or wedged
against a wall, with another block or a monster beyond it; also a block sliding at a standing Chip and a monster
sliding at Chip.  Chip's start tick varies so every sub-step meeting is covered."""
import sys
sys.path.insert(0, '/home/claude/remake/tools/measure'); sys.path.insert(0, '/home/claude/verify')
import measure as M, cxx_lock as C
ROW = 15
def lvl(d, t0, block_tile, beyond, skates=False, chip_hold=False):
    cells = {(x, y): 1 for x in range(2, 30) for y in (ROW - 1, ROW + 1)}
    for x in range(2, 30): cells[(x, ROW)] = 0x02
    cells[(2, ROW)] = 1; cells[(29, ROW)] = 1
    xc = 5; cells[(xc, ROW)] = 0; cells[(xc - 1, ROW)] = 0
    xb = xc + d
    cells[(xb, ROW)] = block_tile
    objs = [(0x04 | M.E, xc, ROW), (0x00 | (7 << 2) | M.E, xb, ROW)]
    kind, *rest = beyond
    if kind == 'wall': cells[(xb + 1, ROW)] = 1
    elif kind == 'block': objs.append((0x00 | (7 << 2) | M.E, xb + 1, ROW)); cells[(xb + 2, ROW)] = 1
    elif kind == 'monster': objs.append((0x00 | (rest[0] << 2) | M.W, xb + 1, ROW)); cells[(xb + 2, ROW)] = 1
    inputs = {t0: {M.E}}
    if chip_hold:
        for k in range(t0, t0 + 40): inputs[k] = {M.E}
    boots = {0x20: 1} if skates else None
    return M.level(cells, objs), inputs, boots
if __name__ == '__main__':
    tot = ok = 0; bad = []
    for d in range(1, 8):
        for t0 in range(4):
            for bt in (0x02, 0x00):
                for beyond in (('none',), ('wall',), ('block',), ('monster', 8), ('monster', 11), ('monster', 6)):
                    for skates in (False, True):
                        for hold in (False, True):
                            data, inputs, boots = lvl(d, t0, bt, beyond, skates, hold)
                            r = C.run_both(data, inputs, 50, boots=boots)
                            if r is None: continue
                            m, le, lc, el, cl = r; good = m == le == lc
                            tot += 1; ok += good
                            if not good: bad.append(((d, t0, hex(bt), beyond, skates, hold), m, C.describe(el[m], cl[m]) if m < min(le, lc) else 'len %d/%d' % (le, lc)))
    print('Chip on ice into a block: %d scenarios, %d match' % (tot, ok))
    for b in bad[:15]: print('DIFF', b)
