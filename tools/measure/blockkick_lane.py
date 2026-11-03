"""Block kick as seen in a recording of CC1 level 45 on the original: Chip above a block that stands on fire, a lane
of monsters running west below it; Chip pushes south.  Monster enters the lane cell below the block from the east
(1-4 cells away) and passes through; every monster type including blob and walker; block on fire or floor;
push tapped or held from start tick 0..15.  Lock-step against the original; a kick = the block moves while Chip,
pushing, stays in place.  Chip taps north into the wall at tick 0 so the game (and the monsters) start
before the push: the game waits for the first input."""
import sys, collections
sys.path.insert(0, '/home/claude/remake/tools/measure'); sys.path.insert(0, '/home/claude/verify')
import measure as M, cxx_lock as C
X, Y = 10, 12
MONS = {2: 'bug', 3: 'paramecium', 4: 'fireball', 5: 'glider', 6: 'ball', 8: 'tank', 9: 'walker', 10: 'blob', 11: 'teeth'}
def lvl(mt, k, under, t0, hold):
    cells = {(X, Y - 1): 0, (X, Y): under}
    for x in range(2, 30): cells[(x, Y + 1)] = 0          # the lane, walled above and below except the block cell
    objs = [(0x04 | M.S, X, Y - 1), (0x00 | (7 << 2) | M.S, X, Y), (0x80 | (mt << 2) | M.W, X + k, Y + 1)]
    inputs = {0: {M.N}}                                    # tap into the wall: the game starts at once
    inputs.update({t: {M.S} for t in range(t0, t0 + (16 if hold else 1))})
    return M.level(cells, objs), inputs
def pos(s, i): S = bytes.fromhex(s); return S[128 + i], S[256 + i]
if __name__ == '__main__':
    tot = ok = 0; kicks = []; bad = []; res = collections.Counter()
    for mt in MONS:
        for k in (1, 2, 3, 4):
            for under in (0x13, 0x00):
                for t0 in range(1, 25):
                    for hold in (False, True):
                        data, inputs = lvl(mt, k, under, t0, hold)
                        r = C.run_both(data, inputs, 48, boots=None)
                        if r is None: continue
                        m, le, lc, el, cl = r; good = m == le == lc
                        tot += 1; ok += good
                        if not good: bad.append((MONS[mt], k, hex(under), t0, hold, m))
                        kick = None
                        for t in range(1, len(el)):
                            if 'crash' in (el[t], el[t - 1]): break
                            if pos(el[t], 1) != pos(el[t - 1], 1) and pos(el[t - 1], 1) == (X * 8, Y * 8) and pos(el[t], 0) == pos(el[t - 1], 0) == (X * 8, (Y - 1) * 8):
                                kick = t; break
                        if kick is not None:
                            # did Chip ever move afterwards?
                            moved = any(pos(e, 0) != (X * 8, (Y - 1) * 8) for e in el[kick:] if e != 'crash')
                            kicks.append((MONS[mt], k, 'fire' if under == 0x13 else 'floor', t0, 'hold' if hold else 'tap', kick, 'chip followed later' if moved else 'chip stayed'))
    print('lane rooms: %d scenarios, %d match' % (tot, ok))
    print('kicks:', len(kicks))
    c = collections.Counter((k[0], k[2], k[4], k[6]) for k in kicks)
    for key, n in sorted(c.items()): print('  ', key, n)
    for k in kicks[:12]: print('  KICK', k)
    for b in bad[:12]: print('DIFF', b)
