"""Block kick (Tile World discovery): Chip pushes a block into the cell a monster is just leaving; with the right
timing the block moves forward but Chip does not. Lock-step against the original.
Row corridor: Chip at x=5 facing E, block at 6, monster at 7 leaving east (along the row) or north/south (side
exit); every monster type, Chip's push tapped or held from start tick t0 = 0..11."""
import sys
sys.path.insert(0, '/home/claude/remake/tools/measure'); sys.path.insert(0, '/home/claude/verify')
import measure as M, cxx_lock as C
ROW = 15
MONS = {2: 'bug', 3: 'paramecium', 4: 'fireball', 5: 'glider', 6: 'ball', 8: 'tank', 11: 'teeth'}
def lvl(mt, exitdir, t0, hold, gap):
    cells = {(x, ROW): 0 for x in range(5, 30)}
    if exitdir in (M.N, M.S):
        for y in range(ROW - 8, ROW + 9): cells[(7 + gap, y)] = 0
    objs = [(0x04 | M.E, 5, ROW), (0x00 | (7 << 2) | M.E, 6, ROW), (0x80 | (mt << 2) | exitdir, 7 + gap, ROW)]
    inputs = {0: {M.W}}                       # Chip taps west into the wall: the game starts before the push
    inputs.update({k: {M.E} for k in range(t0, t0 + (12 if hold else 1))})
    return M.level(cells, objs), inputs
def pos(s, i): S = bytes.fromhex(s); return S[128 + i], S[256 + i]
if __name__ == '__main__':
    tot = ok = 0; kicks = []; bad = []
    for mt in MONS:
        for ed in (M.E, M.N, M.S):
            for gap in (0, 1):
                for t0 in range(1, 13):
                    for hold in (False, True):
                        data, inputs = lvl(mt, ed, t0, hold, gap)
                        r = C.run_both(data, inputs, 40)
                        if r is None: continue
                        m, le, lc, el, cl = r; good = m == le == lc
                        tot += 1; ok += good
                        if not good: bad.append((MONS[mt], 'NESW'[ed], gap, t0, hold, m, C.describe(el[m], cl[m]) if m < min(le, lc) else 'len'))
                        # kick: in some tick the block starts moving while Chip, wanting to move, stays aligned in place
                        for t in range(1, len(el)):
                            if el[t] == 'crash' or el[t - 1] == 'crash': break
                            b0, b1 = pos(el[t - 1], 1), pos(el[t], 1); c0, c1 = pos(el[t - 1], 0), pos(el[t], 0)
                            if b1 != b0 and b0 == (48, ROW * 8) and c1 == c0 == (40, ROW * 8):
                                kicks.append((MONS[mt], 'NESW'[ed], gap, t0, hold, t)); break
    print('block kick rooms: %d scenarios, %d match' % (tot, ok))
    print('kicks seen on the original (block moves, Chip pushing stays):', len(kicks))
    for k in kicks[:30]: print('  KICK', k)
    for b in bad[:15]: print('DIFF', b)
