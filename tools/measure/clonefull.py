"""Clone machines when the object table fills up (128 slots). Slots pre-filled with parked blocks; a ball bounces
over a red button wired to a clone machine holding a tank (moving south down an open column). Lock-step against
the original for every starting object count."""
import sys
sys.path.insert(0, '/home/claude/remake/tools/measure'); sys.path.insert(0, '/home/claude/verify')
import measure as M, cxx_lock as C
def level(n0, tmpl=(8, M.S)):
    cells = {}
    for x in range(2, 9): cells[(x, 3)] = 0
    cells[(5, 3)] = 0x30                                   # red button in the ball's lane
    cells[(15, 5)] = 0x2F                                   # clone machine (after the button in reading order)
    for y in range(6, 17): cells[(15, y)] = 0               # the clones' column
    cells[(25, 3)] = 0                                      # Chip's safe cell
    objs = [(0x04 | M.S, 25, 3), (0x80 | (6 << 2) | M.E, 2, 3), (0x80 | (tmpl[0] << 2) | tmpl[1], 15, 5)]
    spots = [(x, y) for y in range(19, 31) for x in range(1, 31)]
    for k in range(n0 - 3):
        x, y = spots[k]; cells[(x, y)] = 0; objs.append((0x00 | (7 << 2) | M.N, x, y))
    return M.level(cells, objs)
if __name__ == '__main__':
    for n0 in (120, 123, 125, 126, 127, 128):
        data = level(n0)
        r = C.run_both(data, {}, 400, start=True)
        if r is None: print(n0, 'level does not start'); continue
        m, le, lc, el, cl = r
        used = []
        for s in el:
            if s == 'crash': break
            S = bytes.fromhex(s); used.append(sum(1 for i in range(128) if S[i]))
        col = sum(1 for y in range(6, 17) if bytes.fromhex(el[-1])[512 + y * 32 + 15] >= 0x80) if el[-1] != 'crash' else None
        print('start objects %3d: match %s (%d/%d/%d) | objects max %d end %d | tanks in column %s | %s' % (n0, m == le == lc, m, le, lc, max(used), used[-1], col, 'CRASH at %d' % (len(el) - 1) if el[-1] == 'crash' else 'ran 400 ticks'))
