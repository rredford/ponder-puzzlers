"""A stray Chip-type object (not slot 0) arrives on a counted chip while the real Chip stands on / slides over
various tiles. The cartridge's pickup acts on slot 0 (clears its moving flag, writes floor as the tile under it).
Lock-step against the original."""
import sys, random
sys.path.insert(0, '/home/claude/remake/tools/measure'); sys.path.insert(0, '/home/claude/verify')
import measure as M, cxx_lock as C
TILES = {'floor': 0x00, 'ice': 0x02, 'force N': 0x05, 'force E': 0x06, 'force S': 0x07, 'force W': 0x08, 'force random': 0x09,
         'ice NW': 0x0A, 'ice NE': 0x0B, 'ice SE': 0x0C, 'ice SW': 0x0D, 'dirt': 0x03, 'gravel': 0x28, 'trap': 0x2D,
         'brown button': 0x2E, 'teleport': 0x0E, 'fire': 0x13, 'water': 0x14, 'exit': 0x25, 'hint': 0x33, 'blue key': 0x1F,
         'thin E': 0x29, 'thin S': 0x2A, 'popup wall': 0x16, 'green button': 0x19}
def scenario(rng, tile, lane):
    cells = {(x, y): 0 for x in range(4, 28) for y in range(4, 28)}
    cx, cy = 10, 10
    if lane:            # a lane of the tile for Chip to slide along
        for x in range(6, 22): cells[(x, cy)] = tile
    cells[(cx, cy)] = tile
    if tile == 0x2E: cells[(14, 20)] = 0x2D                      # a trap for the brown button
    if tile == 0x0E: cells[(20, 20)] = 0x0E                      # a second teleport
    k = rng.randrange(1, 4); sx, sy = 6, 16; chipx = sx + k
    cells[(chipx, sy)] = 0x23                                    # the counted chip the stray reaches
    stray = (0x80 | (1 << 2) | M.E, sx, sy)                     # Chip type, moving east
    objs = [(0x04 | rng.randrange(4), cx, cy), stray]
    inputs = {}
    t0 = rng.randrange(1, 10); d = rng.choice([M.N, M.E, M.S, M.W])
    for t in range(t0, t0 + rng.randrange(1, 5)): inputs[t] = {d}
    if rng.random() < 0.5:
        for t in range(rng.randrange(12, 20), rng.randrange(20, 30)): inputs[t] = {rng.choice([M.N, M.E, M.S, M.W])}
    return M.level(cells, objs), inputs
if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 6; rng = random.Random(7)
    tot = ok = 0; per = {}; bad = []
    for name, tile in TILES.items():
        for lane in (False, True):
            for k in range(n):
                data, inputs = scenario(rng, tile, lane)
                r = C.run_both(data, inputs, 60, start=True)
                if r is None: continue
                m, le, lc, el, cl = r; good = m == le == lc
                tot += 1; ok += good; p = per.setdefault(name, [0, 0]); p[0] += 1; p[1] += good
                if not good: bad.append((name, lane, k, m, C.run_both.outofsync, C.describe(el[m], cl[m]) if m < min(le, lc) else 'len %d/%d' % (le, lc)))
    print('fake-Chip pickup rooms: %d scenarios, %d match' % (tot, ok))
    print('  ' + ', '.join('%s %d/%d' % (k, v[1], v[0]) for k, v in per.items()))
    for b in bad[:15]: print('DIFF', b)
